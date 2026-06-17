"""Probabilistic forward-return prediction — honest, backtested, self-proving.

We never invent a price target. Instead we ask: in this symbol's own history,
when it was in the SAME setup (trend vs 200-DMA + 3-month momentum sign), how
often did it close higher N trading days later? That conditional base rate IS
the probability, and the historical hit-rate IS the track record — both computed
live from data/bars, both falsifiable.

Output per horizon: direction, probability, sample size, historical hit-rate,
average forward return. Returns None when there isn't enough history to be honest.
"""
from __future__ import annotations

import pandas as pd

from .names import name

_HORIZONS = (5, 10, 20)   # trading days
_MIN_SAMPLE = 20          # below this, not enough signal to publish a number
_MA_WINDOW = 200
_MOM_WINDOW = 63          # ~3 months


def _state(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Two binary setup features, computed for every day in the series."""
    ma = close.rolling(_MA_WINDOW).mean()
    above = close > ma
    mom_up = close.pct_change(_MOM_WINDOW) > 0
    return above, mom_up


def _horizon_call(close: pd.Series, above: pd.Series, mom_up: pd.Series,
                  horizon: int) -> dict | None:
    cur_above = bool(above.iloc[-1])
    cur_mom = bool(mom_up.iloc[-1])
    fwd = close.shift(-horizon) / close - 1.0  # forward return, NaN in last `horizon` rows

    mask = (above == cur_above) & (mom_up == cur_mom) & fwd.notna()
    sample = fwd[mask]
    n = int(sample.shape[0])
    if n < _MIN_SAMPLE:
        return None

    hit = float((sample > 0).mean())          # P(up) in this setup, historically
    avg = float(sample.mean())
    direction = "UP" if hit >= 0.5 else "DOWN"
    prob = hit if direction == "UP" else 1.0 - hit
    return {
        "horizon": horizon,
        "direction": direction,
        "probability": round(prob * 100, 1),
        "hist_hitrate": round(hit * 100, 1),   # the track record of this setup
        "avg_fwd_pct": round(avg * 100, 2),
        "sample_size": n,
    }


def _confidence(sample_size: int) -> str:
    if sample_size >= 120:
        return "high"
    if sample_size >= 50:
        return "medium"
    return "low"


def predict(symbol: str, provider) -> dict | None:
    df = provider.bars(symbol, interval="1d", period="2y")
    if df.empty or len(df) < _MA_WINDOW + max(_HORIZONS) + _MIN_SAMPLE:
        return None
    close = df["close"].dropna()
    above, mom_up = _state(close)
    if pd.isna(above.iloc[-1]) or pd.isna(mom_up.iloc[-1]):
        return None

    calls = [c for h in _HORIZONS if (c := _horizon_call(close, above, mom_up, h))]
    if not calls:
        return None

    cur_above = bool(above.iloc[-1])
    cur_mom = bool(mom_up.iloc[-1])
    basis = (f"setup: {'above' if cur_above else 'below'} 200-DMA, "
             f"3-month momentum {'positive' if cur_mom else 'negative'}")
    headline = next((c for c in calls if c["horizon"] == 10), calls[0])
    return {
        "symbol": symbol,
        "name": name(symbol),
        "basis": basis,
        "confidence": _confidence(headline["sample_size"]),
        "headline": headline,
        "horizons": calls,
        "disclaimer": "Historical base rate, not a guarantee. Informational, not financial advice.",
    }
