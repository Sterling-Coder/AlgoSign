"""Binance bStocks (tokenized US equities) provider — the 24/7 gap signal.

Reads PUBLIC market data only (no account, no trading). bStocks launched
2026-06-11; symbols/endpoints may shift, so every call degrades gracefully:
on any failure the gap radar shows the row as unavailable instead of crashing.
"""
from __future__ import annotations

import httpx

# bStock token symbol -> underlying US ticker. Extend as Binance lists more.
BSTOCK_MAP: dict[str, str] = {
    "TSLAB": "TSLA",
    "NVDAB": "NVDA",
    "MUB": "MU",
    "CRCLB": "CRCL",
    "SNDKB": "SNDK",
}

_BASE = "https://api.binance.com/api/v3/ticker/24hr"
_TIMEOUT = httpx.Timeout(6.0)


class BinanceProvider:
    def ticker_24hr(self, token: str) -> dict | None:
        """Return {price, volume, change_pct} for a bStock token, or None."""
        pair = f"{token}USDT"
        try:
            r = httpx.get(_BASE, params={"symbol": pair}, timeout=_TIMEOUT)
            if r.status_code != 200:
                return None
            d = r.json()
            return {
                "price": float(d["lastPrice"]),
                "volume": float(d["quoteVolume"]),
                "change_pct": float(d["priceChangePercent"]),
            }
        except (httpx.HTTPError, KeyError, ValueError):
            return None
