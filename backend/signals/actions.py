"""Turn raw signals into plain calls: BUY / REDUCE / WATCH, with a reason.

Rule-based and honest — no black box. Derived from momentum (trend strength +
200-DMA) and the gap radar (overnight tokenized moves). Not yet backtested:
these are informational opportunities to act on, not guarantees. M2 adds
measured hit-rates.
"""
from __future__ import annotations

from .names import name


def _conf(score_abs: float) -> str:
    if score_abs >= 1.2:
        return "high"
    if score_abs >= 0.6:
        return "medium"
    return "low"


def build_actions(momentum_rows: list[dict], gap_rows: list[dict]) -> list[dict]:
    actions: list[dict] = []

    # BUY: strong uptrend, confirmed above the 200-day average.
    buys = [
        r for r in momentum_rows
        if r.get("score", 0) >= 0.5 and r.get("above_200dma")
    ]
    buys.sort(key=lambda r: r["score"], reverse=True)
    for r in buys[:6]:
        r3 = r.get("r3")
        actions.append({
            "action": "BUY",
            "symbol": r["symbol"],
            "name": name(r["symbol"]),
            "reason": f"Strong uptrend{f', +{r3}% in 3 months' if r3 and r3 > 0 else ''}, "
                      f"price above its 200-day average.",
            "confidence": _conf(abs(r["score"])),
            "source": "momentum",
        })

    # REDUCE: weak / falling, below the 200-day average.
    sells = [
        r for r in momentum_rows
        if r.get("score", 0) <= -0.5 and not r.get("above_200dma")
    ]
    sells.sort(key=lambda r: r["score"])
    for r in sells[:4]:
        r3 = r.get("r3")
        actions.append({
            "action": "REDUCE",
            "symbol": r["symbol"],
            "name": name(r["symbol"]),
            "reason": f"Downtrend{f', {r3}% in 3 months' if r3 and r3 < 0 else ''}, "
                      f"price below its 200-day average.",
            "confidence": _conf(abs(r["score"])),
            "source": "momentum",
        })

    # WATCH: big overnight gap on a tokenized stock — act around the US open.
    for g in gap_rows:
        if g.get("actionable") and g.get("implied_open_pct") is not None:
            pct = g["implied_open_pct"]
            direction = "up" if pct > 0 else "down"
            actions.append({
                "action": "WATCH",
                "symbol": g["underlying"],
                "name": name(g["underlying"]),
                "reason": f"Likely opens {direction} ~{abs(pct):.1f}% "
                          f"(24/7 tokenized price vs last US close).",
                "confidence": "medium",
                "source": "gap",
            })

    return actions
