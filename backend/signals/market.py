"""Market snapshot for a region: gainers, losers, most-active, sentiment.

Gainers/losers/active come live from the screener (real market movers, not a
fixed basket). Sentiment is still measured over a broad live universe. Falls
back to scanning a static basket only if the live universe is unreachable.
"""
from __future__ import annotations

from .names import name, register


def _row(sym: str, provider) -> dict | None:
    df = provider.bars(sym, interval="1d", period="1y")
    if df.empty or len(df) < 2:
        return None
    close = df["close"].dropna()
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    vol = float(df["volume"].iloc[-1]) if "volume" in df else 0.0
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    return {
        "symbol": sym,
        "name": name(sym),
        "last": round(last, 2),
        "change_pct": round((last / prev - 1) * 100, 2) if prev else 0.0,
        "volume": vol,
        "above_200dma": (ma200 is not None and last > ma200),
    }


def _sentiment(symbols: list[str], provider) -> dict | None:
    """Breadth gauge over a universe: % rising and % above 200-DMA."""
    rows = [r for s in symbols if (r := _row(s, provider))]
    if not rows:
        return None
    up = sum(1 for r in rows if r["change_pct"] > 0)
    above = sum(1 for r in rows if r["above_200dma"])
    n = len(rows)
    pct_up = round(up / n * 100)
    pct_above = round(above / n * 100)
    score = round((pct_up + pct_above) / 2)
    label = "Bullish" if score >= 66 else "Neutral" if score >= 45 else "Bearish"
    return {"label": label, "score": score, "pct_up": pct_up,
            "pct_above_200dma": pct_above, "count": n}


def snapshot(region: str, symbols: list[str], provider, universe=None) -> dict:
    """Live gainers/losers/active from the screener; static basket as fallback."""
    if universe is not None:
        gainers = universe.movers(region, "gainers", count=5)
        losers = universe.movers(region, "losers", count=5)
        active = universe.movers(region, "active", count=5)
        if gainers is not None and losers is not None:
            register(universe.names)
            return {
                "gainers": gainers,
                "losers": losers,
                "active": active or [],
                "sentiment": _sentiment(symbols, provider),
            }

    # Fallback: rank within the static basket (legacy behaviour).
    rows = [r for s in symbols if (r := _row(s, provider))]
    if not rows:
        return {"gainers": [], "losers": [], "active": [], "sentiment": None}
    by_chg = sorted(rows, key=lambda r: r["change_pct"], reverse=True)
    by_vol = sorted(rows, key=lambda r: r["volume"], reverse=True)

    def clean(lst):
        return [{k: r[k] for k in ("symbol", "name", "last", "change_pct")} for r in lst]

    return {
        "gainers": clean(by_chg[:5]),
        "losers": clean(by_chg[-5:][::-1]),
        "active": clean(by_vol[:5]),
        "sentiment": _sentiment(symbols, provider),
    }
