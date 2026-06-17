"""Yahoo Finance chart API provider — free OHLCV for US + World, no key.

Hits the public chart endpoint directly with a browser User-Agent. This is more
robust than the yfinance package (no crumb/cookie dance) and covers ETFs, stocks,
indices, FX, and futures via Yahoo symbols. Caches to parquet, refreshes daily.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "bars"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_MAX_AGE_S = 60 * 60 * 12  # 12h
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
_SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"
_TIMEOUT = httpx.Timeout(10.0)


class YahooProvider:
    def _cache_path(self, symbol: str, rng: str, interval: str) -> Path:
        safe = symbol.replace("/", "_").replace("^", "_")
        return _CACHE_DIR / f"{safe}_{rng}_{interval}.parquet"

    def bars(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        interval: str = "1d",
        period: str = "2y",
    ) -> pd.DataFrame:
        rng = period or "2y"
        path = self._cache_path(symbol, rng, interval)
        if path.exists() and (time.time() - path.stat().st_mtime) < _MAX_AGE_S:
            df = pd.read_parquet(path)
        else:
            df = self._fetch(symbol, rng, interval)
            if df.empty:
                return df
            df.to_parquet(path)
        if start:
            df = df.loc[df.index >= pd.Timestamp(start)]
        if end:
            df = df.loc[df.index <= pd.Timestamp(end)]
        return df

    def _fetch(self, symbol: str, rng: str, interval: str) -> pd.DataFrame:
        params = {"range": rng, "interval": interval}
        try:
            r = httpx.get(
                _BASE + symbol, params=params,
                headers={"User-Agent": _UA}, timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                return pd.DataFrame()
            data = r.json()["chart"]["result"][0]
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError):
            return pd.DataFrame()
        ts = data.get("timestamp")
        quote = data.get("indicators", {}).get("quote", [{}])[0]
        if not ts or not quote:
            return pd.DataFrame()
        df = pd.DataFrame({
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        }, index=pd.to_datetime(ts, unit="s"))
        return df.dropna(subset=["close"])

    def last_close(self, symbol: str) -> float | None:
        df = self.bars(symbol, interval="1d", period="5d")
        if df.empty:
            return None
        return float(df["close"].iloc[-1])

    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Resolve a free-text query to tradable symbols (e.g. 'TCS' -> TCS.NS)."""
        try:
            r = httpx.get(
                _SEARCH,
                params={"q": query, "quotesCount": limit, "newsCount": 0},
                headers={"User-Agent": _UA}, timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                return []
            quotes = r.json().get("quotes", [])
        except (httpx.HTTPError, KeyError, ValueError):
            return []
        out = []
        for q in quotes:
            sym = q.get("symbol")
            if not sym:
                continue
            out.append({
                "symbol": sym,
                "name": q.get("shortname") or q.get("longname") or sym,
                "exchange": q.get("exchange", ""),
                "type": q.get("quoteType", ""),
            })
        return out
