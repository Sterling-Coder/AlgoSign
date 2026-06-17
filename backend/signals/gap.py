"""Gap Radar — tokenized 24/7 price vs last US close => implied open gap.

implied_open_pct = (token_price / last_us_close - 1) * 100   (DESIGN.md 5.5)
Only meaningful with liquidity; we surface volume so thin spikes can be ignored.
"""
from __future__ import annotations

from providers import BSTOCK_MAP

_MIN_ABS_PCT = 1.5  # below this, not actionable noise


def gap_radar(binance, yf, min_pct: float = 0.0) -> list[dict]:
    rows = []
    for token, underlying in BSTOCK_MAP.items():
        tick = binance.ticker_24hr(token)
        last_close = yf.last_close(underlying)
        if tick is None or last_close is None or last_close == 0:
            rows.append({
                "token": token,
                "underlying": underlying,
                "available": False,
                "token_price": None,
                "last_close": last_close,
                "implied_open_pct": None,
                "volume": None,
                "actionable": False,
            })
            continue
        implied = (tick["price"] / last_close - 1.0) * 100
        rows.append({
            "token": token,
            "underlying": underlying,
            "available": True,
            "token_price": round(tick["price"], 2),
            "last_close": round(last_close, 2),
            "implied_open_pct": round(implied, 2),
            "volume": round(tick["volume"], 0),
            "actionable": abs(implied) >= _MIN_ABS_PCT,
        })

    rows = [r for r in rows if r["implied_open_pct"] is None
            or abs(r["implied_open_pct"]) >= min_pct]
    rows.sort(
        key=lambda x: abs(x["implied_open_pct"]) if x["implied_open_pct"] is not None else -1,
        reverse=True,
    )
    return rows
