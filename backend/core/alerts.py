"""Price/percent alerts — rules the scheduler watches while you're away.

A rule is one row in `alerts`, scoped to a device. The scheduler calls scan()
on a cadence: it pulls every active rule, fetches live quotes once, and fires
any that crossed — pushing an SSE event to that device and disarming the rule
(one-shot, so you get told once, not every tick). Re-arm by creating it again.

Every read/write is filtered by device: device A can never see or delete device
B's alerts. Inputs are validated and rejected loudly, never coerced silently.
"""
from __future__ import annotations

import logging
import math

from . import db
from .sse import hub as _default_hub

log = logging.getLogger("algosign.alerts")

_VALID_KIND = {"price", "pct_change"}
_VALID_DIR = {"above", "below"}
_NOTE_MAX = 140


class AlertError(ValueError):
    """Bad alert input — surfaced to the client as a 400, never a 500."""


def _row(r) -> dict:
    d = {k: r[k] for k in r.keys()}
    d["active"] = bool(d["active"])
    return d


def create(device: str, symbol: str, kind: str, direction: str,
           threshold, note: str | None = None) -> dict:
    sym = (symbol or "").strip().upper()
    if not sym or len(sym) > 24:
        raise AlertError("invalid symbol")
    if kind not in _VALID_KIND:
        raise AlertError(f"kind must be one of {sorted(_VALID_KIND)}")
    if direction not in _VALID_DIR:
        raise AlertError("direction must be 'above' or 'below'")
    try:
        thr = float(threshold)
    except (TypeError, ValueError):
        raise AlertError("threshold must be a number")
    if not math.isfinite(thr):
        raise AlertError("threshold must be finite")
    note = (note or "").strip()[:_NOTE_MAX] or None

    aid = db.execute(
        "INSERT INTO alerts(device,symbol,kind,direction,threshold,note,created_at) "
        "VALUES(?,?,?,?,?,?,datetime('now'))",
        (device, sym, kind, direction, thr, note),
    )
    return get(device, aid)


def list_for(device: str) -> list[dict]:
    rows = db.query(
        "SELECT * FROM alerts WHERE device=? ORDER BY active DESC, id DESC", (device,)
    )
    return [_row(r) for r in rows]


def get(device: str, alert_id: int) -> dict | None:
    rows = db.query("SELECT * FROM alerts WHERE device=? AND id=?", (device, alert_id))
    return _row(rows[0]) if rows else None


def delete(device: str, alert_id: int) -> bool:
    return db.execute("DELETE FROM alerts WHERE device=? AND id=?", (device, alert_id)) > 0


def _crossed(value: float, direction: str, threshold: float) -> bool:
    return value >= threshold if direction == "above" else value <= threshold


def scan(universe, hub=None) -> int:
    """Scheduler job: fire any active alert whose live value crossed. Returns
    the number fired. Skips the tick (fires nothing) if quotes are unavailable,
    so we never alert on stale data."""
    hub = hub or _default_hub
    rows = db.query("SELECT * FROM alerts WHERE active=1")
    if not rows:
        return 0
    quotes = universe.quotes(sorted({r["symbol"] for r in rows}))
    if not quotes:
        return 0

    fired = 0
    for r in rows:
        info = quotes.get(r["symbol"])
        if not info:
            continue
        value = info["price"] if r["kind"] == "price" else info["change_pct"]
        if not _crossed(value, r["direction"], r["threshold"]):
            continue
        # Disarm first so a crash mid-loop can't double-fire on the next tick.
        db.execute(
            "UPDATE alerts SET active=0, last_fired_at=datetime('now'), last_value=? WHERE id=?",
            (value, r["id"]),
        )
        hub.publish(r["device"], {
            "type": "alert",
            "id": r["id"],
            "symbol": r["symbol"],
            "kind": r["kind"],
            "direction": r["direction"],
            "threshold": r["threshold"],
            "value": value,
            "note": r["note"],
        })
        fired += 1
    if fired:
        log.info("alerts fired: %d", fired)
    return fired
