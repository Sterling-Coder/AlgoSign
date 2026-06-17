"""Paper-trading engine — real order/fill/reconcile logic, simulated money.

You open a position; the scheduler is the bot that watches it and closes it when
your stop or target hits, marking live P&L the whole way. This builds the exact
order-management + reconciliation machinery a real broker integration would need,
with zero financial or regulatory exposure.

Real money is gated behind BOTS_REAL_MONEY (default off). Until a broker is wired
and reviewed, the flag being on just refuses to open — we never silently route a
live order. Fills in paper mode happen at the live market price.
"""
from __future__ import annotations

import logging
import math
import os

from . import db
from .sse import hub as _default_hub

log = logging.getLogger("algosign.bots")

REAL_MONEY = os.environ.get("BOTS_REAL_MONEY", "false").lower() == "true"

_VALID_SIDE = {"long", "short"}


class BotError(ValueError):
    """Bad order input — surfaced to the client as a 400, never a 500."""


def _row(r) -> dict:
    return {k: r[k] for k in r.keys()}


def _pnl(side: str, entry: float, exit_price: float, qty: float) -> float:
    delta = (exit_price - entry) if side == "long" else (entry - exit_price)
    return round(delta * qty, 2)


def _live_price(universe, symbol: str) -> float | None:
    q = universe.quotes([symbol])
    info = q.get(symbol)
    return info["price"] if info else None


def open_position(device: str, symbol: str, side: str, qty,
                  stop=None, target=None, *, universe) -> dict:
    if REAL_MONEY:
        # Hard stop: live execution is a one-way door and no broker is wired.
        raise BotError("real-money trading is not enabled on this server")

    sym = (symbol or "").strip().upper()
    if not sym or len(sym) > 24:
        raise BotError("invalid symbol")
    if side not in _VALID_SIDE:
        raise BotError("side must be 'long' or 'short'")
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        raise BotError("qty must be a number")
    if not math.isfinite(qty) or qty <= 0:
        raise BotError("qty must be positive")

    def _opt(v, label):
        if v in (None, ""):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            raise BotError(f"{label} must be a number")
        if not math.isfinite(f) or f <= 0:
            raise BotError(f"{label} must be positive")
        return f

    stop = _opt(stop, "stop")
    target = _opt(target, "target")

    entry = _live_price(universe, sym)
    if entry is None:
        raise BotError(f"no live price for {sym}")

    aid = db.execute(
        "INSERT INTO bot_positions(device,symbol,side,qty,entry_price,stop,target,status,opened_at) "
        "VALUES(?,?,?,?,?,?,?, 'open', datetime('now'))",
        (device, sym, side, qty, entry, stop, target),
    )
    log.info("paper open: device=%s %s %s %g @ %.2f", device, side, sym, qty, entry)
    return get(device, aid, universe=universe)


def get(device: str, pos_id: int, *, universe=None) -> dict | None:
    rows = db.query("SELECT * FROM bot_positions WHERE device=? AND id=?", (device, pos_id))
    if not rows:
        return None
    return _decorate(_row(rows[0]), universe)


def _decorate(p: dict, universe) -> dict:
    """Attach live price + unrealised P&L to an open position."""
    if p["status"] == "open" and universe is not None:
        price = _live_price(universe, p["symbol"])
        if price is not None:
            p["current_price"] = price
            p["unrealized_pnl"] = _pnl(p["side"], p["entry_price"], price, p["qty"])
    return p


def list_positions(device: str, *, universe) -> dict:
    rows = db.query(
        "SELECT * FROM bot_positions WHERE device=? ORDER BY (status='open') DESC, id DESC",
        (device,),
    )
    positions = [_decorate(_row(r), universe) for r in rows]
    realized = round(sum(p["pnl"] or 0 for p in positions if p["status"] == "closed"), 2)
    unrealized = round(sum(p.get("unrealized_pnl", 0) or 0 for p in positions if p["status"] == "open"), 2)
    return {
        "positions": positions,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "open_count": sum(1 for p in positions if p["status"] == "open"),
    }


def _close(p: dict, exit_price: float, reason: str, hub) -> None:
    pnl = _pnl(p["side"], p["entry_price"], exit_price, p["qty"])
    db.execute(
        "UPDATE bot_positions SET status='closed', closed_at=datetime('now'), "
        "exit_price=?, pnl=? WHERE id=? AND status='open'",
        (exit_price, pnl, p["id"]),
    )
    hub.publish(p["device"], {
        "type": "fill",
        "id": p["id"],
        "symbol": p["symbol"],
        "side": p["side"],
        "qty": p["qty"],
        "exit_price": exit_price,
        "pnl": pnl,
        "reason": reason,   # target | stop | manual
    })
    log.info("paper close (%s): %s %s pnl=%.2f", reason, p["device"], p["symbol"], pnl)


def close_position(device: str, pos_id: int, *, universe, hub=None) -> dict | None:
    hub = hub or _default_hub
    p = get(device, pos_id, universe=None)
    if not p or p["status"] != "open":
        return p
    price = _live_price(universe, p["symbol"])
    if price is None:
        raise BotError("no live price to close at")
    _close(p, price, "manual", hub)
    return get(device, pos_id, universe=universe)


def _hit(side: str, price: float, stop, target) -> str | None:
    if side == "long":
        if target is not None and price >= target:
            return "target"
        if stop is not None and price <= stop:
            return "stop"
    else:  # short
        if target is not None and price <= target:
            return "target"
        if stop is not None and price >= stop:
            return "stop"
    return None


def manage(universe, hub=None) -> int:
    """Scheduler job: close any open position whose stop/target hit. Returns the
    number closed. Skips the tick on missing quotes (never closes on stale data)."""
    hub = hub or _default_hub
    rows = db.query("SELECT * FROM bot_positions WHERE status='open'")
    if not rows:
        return 0
    quotes = universe.quotes(sorted({r["symbol"] for r in rows}))
    if not quotes:
        return 0

    closed = 0
    for r in rows:
        p = _row(r)
        info = quotes.get(p["symbol"])
        if not info:
            continue
        reason = _hit(p["side"], info["price"], p["stop"], p["target"])
        if reason:
            _close(p, info["price"], reason, hub)
            closed += 1
    return closed
