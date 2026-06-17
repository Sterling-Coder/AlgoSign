"""Single-stock detail: price, day change, returns, trend, 52-week range, series."""
from __future__ import annotations

import pandas as pd

from .names import name

_LB = {"r1": 21, "r3": 63, "r6": 126, "r12": 252}


def _ret(close: pd.Series, lb: int):
    if len(close) <= lb:
        return None
    past = close.iloc[-lb - 1]
    if past == 0 or pd.isna(past):
        return None
    return round(float(close.iloc[-1] / past - 1.0) * 100, 2)


def _verdict(above_200: bool, r3, r1) -> dict:
    r3 = r3 or 0
    r1 = r1 or 0
    if above_200 and r3 > 0:
        return {
            "action": "ACCUMULATE",
            "reason": f"Uptrend confirmed — above its 200-day average, +{r3}% over 3 months.",
        }
    if not above_200 and r3 < 0:
        return {
            "action": "REDUCE",
            "reason": f"Downtrend — below its 200-day average, {r3}% over 3 months.",
        }
    if above_200 and r3 <= 0:
        return {
            "action": "HOLD",
            "reason": "Above 200-day avg but momentum is cooling. Wait for it to turn back up.",
        }
    return {
        "action": "AVOID",
        "reason": "Below 200-day avg and weak. No trend to ride yet — watch for a base.",
    }


def _watch(last, ma200, high52, low52) -> list[str]:
    pts = []
    if ma200:
        side = "above" if last > ma200 else "below"
        pts.append(
            f"200-day avg at {ma200:,.0f} — price is {side} it; a cross flips the trend signal."
        )
    if high52:
        off = (last / high52 - 1) * 100
        pts.append(f"52-week high {high52:,.0f} — {abs(off):.1f}% {'below' if off < 0 else 'above'} it.")
    if low52:
        off = (last / low52 - 1) * 100
        pts.append(f"52-week low {low52:,.0f} — {off:.1f}% above it (downside cushion).")
    return pts


def detail(symbol: str, provider) -> dict | None:
    df = provider.bars(symbol, interval="1d", period="2y")
    if df.empty or len(df) < 2:
        return None
    close = df["close"].dropna()
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    window = close.iloc[-252:] if len(close) >= 252 else close
    series = [
        {"t": ts.strftime("%Y-%m-%d"), "c": round(float(c), 2)}
        for ts, c in close.iloc[-180:].items()
    ]
    r1 = _ret(close, _LB["r1"])
    r3 = _ret(close, _LB["r3"])
    above = ma200 is not None and last > ma200
    high52 = round(float(window.max()), 2)
    low52 = round(float(window.min()), 2)
    return {
        "symbol": symbol,
        "name": name(symbol),
        "last": round(last, 2),
        "change": round(last - prev, 2),
        "change_pct": round((last / prev - 1) * 100, 2) if prev else 0.0,
        "r1": r1,
        "r3": r3,
        "r6": _ret(close, _LB["r6"]),
        "r12": _ret(close, _LB["r12"]),
        "above_200dma": above,
        "ma200": round(ma200, 2) if ma200 else None,
        "high52": high52,
        "low52": low52,
        "verdict": _verdict(above, r3, r1),
        "watch": _watch(last, ma200, high52, low52),
        "series": series,
    }
