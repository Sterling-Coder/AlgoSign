"""Sector heatmap — stocks grouped by sector, colored by day % change.

Sector membership comes live from the screener (top names per GICS sector).
The static SECTORS map below is only a fallback for when Yahoo is unreachable.
"""
from __future__ import annotations

from .names import name, register

SECTORS: dict[str, dict[str, list[str]]] = {
    "IN": {
        "IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],
        "Banks": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"],
        "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS"],
        "Auto": ["TATAMOTORS.NS", "MARUTI.NS", "M&M.NS"],
        "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
        "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS"],
        "Metals": ["TATASTEEL.NS", "JSWSTEEL.NS"],
    },
    "US": {
        "Tech": ["AAPL", "MSFT", "NVDA", "AVGO"],
        "Comm": ["GOOGL", "META", "NFLX"],
        "Consumer": ["AMZN", "TSLA", "HD", "MCD"],
        "Staples": ["PG", "KO", "WMT"],
        "Financials": ["JPM", "BAC", "V", "MA"],
        "Health": ["UNH", "JNJ", "LLY"],
        "Energy": ["XOM", "CVX"],
    },
    "WORLD": {
        "US Mega": ["AAPL", "MSFT", "NVDA"],
        "China": ["BABA", "PDD", "JD"],
        "Europe": ["ASML", "SAP", "NVO"],
        "Japan": ["TM", "SONY"],
        "Energy": ["XOM", "SHEL"],
        "Crypto": ["BTC-USD", "ETH-USD"],
    },
}


def _chg(sym: str, provider) -> dict | None:
    df = provider.bars(sym, interval="1d", period="5d")
    if df.empty or len(df) < 2:
        return None
    c = df["close"].dropna()
    last, prev = float(c.iloc[-1]), float(c.iloc[-2])
    return {
        "symbol": sym,
        "name": name(sym),
        "change_pct": round((last / prev - 1) * 100, 2) if prev else 0.0,
    }


def heatmap(region: str, provider, universe=None) -> list[dict]:
    # Live sector membership; fall back to the static map on failure.
    live = universe.by_sector(region) if universe is not None else None
    if live:
        register(universe.names)
        groups = [(g["sector"], g["symbols"]) for g in live]
    else:
        groups = list(SECTORS.get(region.upper(), SECTORS["US"]).items())

    out = []
    for sector, syms in groups:
        stocks = [r for s in syms if (r := _chg(s, provider))]
        if not stocks:
            continue
        avg = round(sum(s["change_pct"] for s in stocks) / len(stocks), 2)
        out.append({"sector": sector, "avg_change": avg, "stocks": stocks})
    return out
