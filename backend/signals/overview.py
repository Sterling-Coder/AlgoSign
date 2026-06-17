"""Market overview — the headline index/asset cards per region.

Each card carries last price, day change %, and a sparkline series so the
home page reads at a glance, like a finance terminal.
"""
from __future__ import annotations

# region -> [(yahoo symbol, display label)]
HEADLINES: dict[str, list[tuple[str, str]]] = {
    "IN": [
        ("^NSEI", "NIFTY 50"),
        ("^BSESN", "S&P BSE Sensex"),
        ("^NSEBANK", "Nifty Bank"),
        ("BTC-USD", "Bitcoin"),
    ],
    "US": [
        ("^GSPC", "S&P 500"),
        ("^IXIC", "Nasdaq"),
        ("^DJI", "Dow 30"),
        ("BTC-USD", "Bitcoin"),
    ],
    "WORLD": [
        ("^FTSE", "FTSE 100"),
        ("^N225", "Nikkei 225"),
        ("GC=F", "Gold"),
        ("BTC-USD", "Bitcoin"),
    ],
}

_SPARK_POINTS = 30


def overview(region: str, provider, universe=None) -> list[dict]:
    """Headline cards. Price + day change come LIVE (so the home page matches the
    open market); the sparkline still comes from daily bars. Falls back to the
    last two daily closes only if the live quote is unavailable."""
    syms_labels = HEADLINES.get(region.upper(), HEADLINES["US"])
    quotes = universe.quotes([s for s, _ in syms_labels]) if universe is not None else {}

    cards = []
    for sym, label in syms_labels:
        df = provider.bars(sym, interval="1d", period="2mo")
        closes = [round(float(c), 2) for c in df["close"].dropna().tolist()] if not df.empty else []
        spark = closes[-_SPARK_POINTS:]

        live = quotes.get(sym)
        if live:
            last = live["price"]
            change = live["change"]
            change_pct = live["change_pct"]
        elif len(closes) >= 2:  # fallback: last two daily closes
            last, prev = closes[-1], closes[-2]
            change = round(last - prev, 2)
            change_pct = round((last / prev - 1) * 100, 2) if prev else 0.0
        else:
            continue  # no live quote and no bars — skip rather than show nothing

        cards.append({
            "symbol": sym,
            "label": label,
            "last": last,
            "change": change,
            "change_pct": change_pct,
            "spark": spark or [last],
        })
    return cards
