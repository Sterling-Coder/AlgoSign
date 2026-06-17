"""Deep US/World fundamentals via stockanalysis.com — free, no key.

Two public JSON calls (/overview + /statistics) give a Screener.in-grade
snapshot: ROCE, ROIC, ROE, margins, debt ratios, EV ratios, and income/balance/
cash-flow highlights. US tickers only (plain symbol); foreign-listed/.NS use
other sources. Cached 6h.
"""
from __future__ import annotations

import time

import httpx

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_BASE = "https://stockanalysis.com/api/symbol/s/{}"
_TTL = 6 * 60 * 60

_LABELS = {
    "marketcap": "Market Cap", "enterpriseValue": "Enterprise Value",
    "pe": "P/E", "peForward": "Fwd P/E", "pb": "P/B", "ps": "P/S",
    "evEbitda": "EV/EBITDA", "evFcf": "EV/FCF", "evSales": "EV/Sales",
    "roe": "ROE", "roa": "ROA", "roic": "ROIC", "roce": "ROCE", "wacc": "WACC",
    "grossMargin": "Gross Margin", "operatingMargin": "Op Margin",
    "profitMargin": "Profit Margin", "fcfMargin": "FCF Margin",
    "currentRatio": "Current Ratio", "quickRatio": "Quick Ratio",
    "debtEquity": "Debt/Equity", "debtEbitda": "Debt/EBITDA",
    "interestCoverage": "Interest Cov",
    "revenue": "Revenue", "gp": "Gross Profit", "opinc": "Op Income",
    "netinc": "Net Income", "ebitda": "EBITDA", "eps": "EPS",
    "totalcash": "Total Cash", "debt": "Total Debt", "netcash": "Net Cash",
    "equity": "Equity", "bvps": "Book Value/sh", "workingcapital": "Working Capital",
    "ncfo": "Operating CF", "capex": "Capex", "fcf": "Free Cash Flow",
    "fcfps": "FCF/share", "beta": "Beta", "taxrate": "Tax Rate",
}
_GROUPS = [
    ("Valuation", ["marketcap", "enterpriseValue", "pe", "peForward", "pb", "ps", "evEbitda", "evFcf"]),
    ("Profitability", ["roe", "roa", "roic", "roce", "grossMargin", "operatingMargin", "profitMargin", "fcfMargin"]),
    ("Financial Health", ["currentRatio", "quickRatio", "debtEquity", "debtEbitda", "interestCoverage", "totalcash", "debt", "equity"]),
    ("Income & Cash Flow", ["revenue", "netinc", "ebitda", "ncfo", "fcf", "eps", "fcfps", "capex"]),
]


class StockAnalysisProvider:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict]] = {}

    def get(self, symbol: str) -> dict | None:
        if "." in symbol or "-" in symbol or "^" in symbol:
            return None  # US-listed plain tickers only
        sym = symbol.upper()
        hit = self._cache.get(sym)
        if hit and time.time() - hit[0] < _TTL:
            return hit[1]
        merged: dict[str, str] = {}
        try:
            with httpx.Client(headers={"User-Agent": _UA}, timeout=httpx.Timeout(10.0)) as c:
                ov = c.get(_BASE.format(sym) + "/overview")
                st = c.get(_BASE.format(sym) + "/statistics")
                if ov.status_code == 200:
                    merged["marketcap"] = ov.json().get("data", {}).get("marketCap", "")
                if st.status_code != 200:
                    return None
                for sec in st.json().get("data", {}).values():
                    if isinstance(sec, dict):
                        for it in sec.get("data", []):
                            if it.get("id") and it.get("value") not in (None, "", "n/a"):
                                merged.setdefault(it["id"], it["value"])
        except (httpx.HTTPError, ValueError):
            return None
        if not merged:
            return None

        groups = []
        for title, ids in _GROUPS:
            items = [{"label": _LABELS.get(i, i), "value": merged[i]} for i in ids if merged.get(i)]
            if items:
                groups.append({"title": title, "items": items})
        if not groups:
            return None
        payload = {"source": "stockanalysis.com", "groups": groups}
        self._cache[sym] = (time.time(), payload)
        return payload
