"""Smart Money Concepts (SMC) engine — PhantomFlow-style chart analysis.

All computed from OHLC, no special feed. Detects:
  - swing highs/lows (market structure pivots)
  - BOS (break of structure) / CHoCH (change of character)
  - order blocks (last opposing candle before a structure break)
  - fair value gaps (3-candle imbalance)
  - buy/sell signals at trend changes

Works on any timeframe; daily for free data, intraday when F/O data lands.
"""
from __future__ import annotations

import pandas as pd

from .names import name


def _swings(df: pd.DataFrame, k: int = 3) -> tuple[list[int], list[int]]:
    highs, lows = [], []
    h, l = df["high"].values, df["low"].values
    for i in range(k, len(df) - k):
        if h[i] == max(h[i - k : i + k + 1]):
            highs.append(i)
        if l[i] == min(l[i - k : i + k + 1]):
            lows.append(i)
    return highs, lows


def analyze(symbol: str, provider, period: str = "1y", interval: str = "1d", k: int = 3) -> dict | None:
    df = provider.bars(symbol, interval=interval, period=period)
    if df.empty or len(df) < 30:
        return None
    df = df.reset_index().rename(columns={df.index.name or "index": "t"})
    tcol = df.columns[0]
    intraday = interval.endswith("m") or interval.endswith("h")
    fmt = "%Y-%m-%d %H:%M" if intraday else "%Y-%m-%d"
    times = [pd.Timestamp(t).strftime(fmt) for t in df[tcol]]
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]

    sw_h, sw_l = _swings(df, k)
    sw_h_set = {i: float(h[i]) for i in sw_h}
    sw_l_set = {i: float(l[i]) for i in sw_l}

    structure: list[dict] = []
    order_blocks: list[dict] = []
    signals: list[dict] = []

    last_sh = None   # (idx, price) most recent confirmed swing high
    last_sl = None
    trend = 0        # 1 up, -1 down, 0 none

    for i in range(len(df)):
        if i in sw_h_set:
            last_sh = (i, sw_h_set[i])
        if i in sw_l_set:
            last_sl = (i, sw_l_set[i])

        # Bullish break: close takes out the last swing high.
        if last_sh and c[i] > last_sh[1] and i > last_sh[0]:
            kind = "CHoCH" if trend == -1 else "BOS"
            structure.append({"type": kind, "dir": "bull", "t": times[i], "price": round(float(last_sh[1]), 2)})
            ob = _order_block(df, last_sh[0], i, "bull")
            if ob:
                order_blocks.append({**ob, "t": times[ob["idx"]]})
            if kind == "CHoCH":
                signals.append({"side": "BUY", "t": times[i], "price": round(float(c[i]), 2),
                                "why": "Bullish CHoCH — structure flipped up."})
            trend = 1
            last_sh = None

        # Bearish break: close takes out the last swing low.
        if last_sl and c[i] < last_sl[1] and i > last_sl[0]:
            kind = "CHoCH" if trend == 1 else "BOS"
            structure.append({"type": kind, "dir": "bear", "t": times[i], "price": round(float(last_sl[1]), 2)})
            ob = _order_block(df, last_sl[0], i, "bear")
            if ob:
                order_blocks.append({**ob, "t": times[ob["idx"]]})
            if kind == "CHoCH":
                signals.append({"side": "SELL", "t": times[i], "price": round(float(c[i]), 2),
                                "why": "Bearish CHoCH — structure flipped down."})
            trend = -1
            last_sl = None

    fvgs = _fvgs(df, times)
    candles = [
        {"t": times[i], "o": round(float(o[i]), 2), "h": round(float(h[i]), 2),
         "l": round(float(l[i]), 2), "c": round(float(c[i]), 2)}
        for i in range(len(df))
    ]

    return {
        "symbol": symbol,
        "name": name(symbol),
        "trend": "up" if trend == 1 else "down" if trend == -1 else "flat",
        "candles": candles,
        "order_blocks": order_blocks[-6:],
        "fvgs": fvgs[-8:],
        "structure": structure[-8:],
        "signals": signals[-6:],
    }


def _order_block(df: pd.DataFrame, swing_idx: int, break_idx: int, direction: str) -> dict | None:
    """Last opposing candle before the impulsive move that broke structure."""
    o, c, h, l = df["open"], df["close"], df["high"], df["low"]
    for i in range(break_idx, swing_idx, -1):
        if direction == "bull" and c[i] < o[i]:  # last down candle before up-break
            return {"idx": i, "type": "bull", "top": round(float(h[i]), 2), "bottom": round(float(l[i]), 2)}
        if direction == "bear" and c[i] > o[i]:  # last up candle before down-break
            return {"idx": i, "type": "bear", "top": round(float(h[i]), 2), "bottom": round(float(l[i]), 2)}
    return None


def _fvgs(df: pd.DataFrame, times: list[str]) -> list[dict]:
    h, l = df["high"].values, df["low"].values
    out = []
    for i in range(2, len(df)):
        if l[i] > h[i - 2]:  # bullish gap
            out.append({"type": "bull", "t": times[i], "top": round(float(l[i]), 2), "bottom": round(float(h[i - 2]), 2)})
        elif h[i] < l[i - 2]:  # bearish gap
            out.append({"type": "bear", "t": times[i], "top": round(float(l[i - 2]), 2), "bottom": round(float(h[i]), 2)})
    return out
