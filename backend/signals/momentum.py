"""Momentum + trend ranking — the screener radar.

Score = 0.5*z(r6) + 0.3*z(r3) + 0.2*z(r12), z-scored across the basket.
Buy-eligible only when price > 200-day MA (trend filter). See DESIGN.md 9.3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_TRADING_DAYS = {"r1": 21, "r3": 63, "r6": 126, "r12": 252}


def _ret(close: pd.Series, lookback: int) -> float | None:
    if len(close) <= lookback:
        return None
    past = close.iloc[-lookback - 1]
    if past == 0 or pd.isna(past):
        return None
    return float(close.iloc[-1] / past - 1.0)


def _zscore(values: list[float | None]) -> list[float]:
    arr = np.array([v if v is not None else np.nan for v in values], dtype=float)
    mean = np.nanmean(arr)
    std = np.nanstd(arr)
    if not std or np.isnan(std):
        return [0.0] * len(values)
    z = (arr - mean) / std
    return [0.0 if np.isnan(x) else float(x) for x in z]


def rank_basket(symbols: list[str], provider) -> list[dict]:
    rows = []
    for sym in symbols:
        df = provider.bars(sym, interval="1d", period="2y")
        if df.empty or len(df) < 60:
            continue
        close = df["close"].dropna()
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
        price = float(close.iloc[-1])
        rows.append({
            "symbol": sym,
            "price": round(price, 2),
            "r1": _ret(close, _TRADING_DAYS["r1"]),
            "r3": _ret(close, _TRADING_DAYS["r3"]),
            "r6": _ret(close, _TRADING_DAYS["r6"]),
            "r12": _ret(close, _TRADING_DAYS["r12"]),
            "above_200dma": (ma200 is not None and price > ma200),
        })

    if not rows:
        return []

    z6 = _zscore([r["r6"] for r in rows])
    z3 = _zscore([r["r3"] for r in rows])
    z12 = _zscore([r["r12"] for r in rows])
    for r, a, b, c in zip(rows, z6, z3, z12):
        r["score"] = round(0.5 * a + 0.3 * b + 0.2 * c, 3)
        for k in ("r1", "r3", "r6", "r12"):
            r[k] = round(r[k] * 100, 2) if r[k] is not None else None

    rows.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows
