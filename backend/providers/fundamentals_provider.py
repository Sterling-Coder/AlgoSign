"""Fundamentals via Yahoo quoteSummary — Screener.in-style ratios, free.

Yahoo now gates quoteSummary behind a cookie + crumb handshake. We fetch the
crumb once, reuse it, and refresh on a 401. Results cached in-memory (6h) since
ratios move slowly. Works for India (.NS), US, and World symbols.
"""
from __future__ import annotations

import time

import httpx

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_MODULES = "summaryDetail,financialData,defaultKeyStatistics,price"
_STMT_MODULES = (
    "incomeStatementHistory,balanceSheetHistory,cashflowStatementHistory,price"
)
_TTL = 6 * 60 * 60

# (display label, yahoo field) per statement
_INCOME = [
    ("Total Revenue", "totalRevenue"), ("Cost of Revenue", "costOfRevenue"),
    ("Gross Profit", "grossProfit"), ("R&D", "researchDevelopment"),
    ("SG&A", "sellingGeneralAdministrative"), ("Operating Income", "operatingIncome"),
    ("Pretax Income", "incomeBeforeTax"), ("Tax", "incomeTaxExpense"),
    ("Net Income", "netIncome"),
]
_BALANCE = [
    ("Total Assets", "totalAssets"), ("Total Liabilities", "totalLiab"),
    ("Total Equity", "totalStockholderEquity"), ("Cash", "cash"),
    ("Short-term Debt", "shortLongTermDebt"), ("Long-term Debt", "longTermDebt"),
    ("Retained Earnings", "retainedEarnings"),
]
_CASHFLOW = [
    ("Operating Cash Flow", "totalCashFromOperatingActivities"),
    ("Investing Cash Flow", "totalCashflowsFromInvestingActivities"),
    ("Financing Cash Flow", "totalCashFromFinancingActivities"),
    ("Capex", "capitalExpenditures"), ("Change in Cash", "changeInCash"),
]


class FundamentalsProvider:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None
        self._crumb: str | None = None
        self._cache: dict[str, tuple[float, dict]] = {}

    def _ensure(self) -> None:
        if self._client and self._crumb:
            return
        c = httpx.Client(headers={"User-Agent": _UA}, timeout=httpx.Timeout(10.0),
                         follow_redirects=True)
        try:
            c.get("https://fc.yahoo.com/")
        except httpx.HTTPError:
            pass
        crumb = c.get("https://query2.finance.yahoo.com/v1/test/getcrumb").text.strip()
        self._client = c
        self._crumb = crumb

    def fundamentals(self, symbol: str) -> dict | None:
        hit = self._cache.get(symbol)
        if hit and time.time() - hit[0] < _TTL:
            return hit[1]
        data = self._fetch(symbol)
        if data:
            self._cache[symbol] = (time.time(), data)
        return data

    def _fetch(self, symbol: str) -> dict | None:
        self._ensure()
        url = (f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
               f"?modules={_MODULES}&crumb={self._crumb}")
        try:
            r = self._client.get(url)  # type: ignore[union-attr]
            if r.status_code == 401:  # crumb expired — refresh once
                self._client = self._crumb = None
                self._ensure()
                r = self._client.get(url.replace(url.split("crumb=")[1], self._crumb or ""))  # type: ignore[union-attr]
            if r.status_code != 200:
                return None
            res = r.json()["quoteSummary"]["result"]
        except (httpx.HTTPError, KeyError, ValueError, IndexError):
            return None
        if not res:
            return None
        m = res[0]
        sd = m.get("summaryDetail", {})
        fd = m.get("financialData", {})
        ks = m.get("defaultKeyStatistics", {})
        pr = m.get("price", {})
        cur = pr.get("currency", "USD")

        def raw(o, k):
            v = (o.get(k) or {})
            return v.get("raw") if isinstance(v, dict) else None

        def pct(o, k):
            v = raw(o, k)
            return f"{v * 100:.2f}%" if v is not None else "—"

        def num(o, k, d=2):
            v = raw(o, k)
            return f"{v:.{d}f}" if v is not None else "—"

        metrics = [
            {"label": "Market Cap", "value": _mcap(raw(sd, "marketCap") or raw(pr, "marketCap"), cur)},
            {"label": "P/E (TTM)", "value": num(sd, "trailingPE")},
            {"label": "P/B", "value": num(ks, "priceToBook")},
            {"label": "ROE", "value": pct(fd, "returnOnEquity")},
            {"label": "Debt/Equity", "value": num(fd, "debtToEquity")},
            {"label": "Div Yield", "value": pct(sd, "dividendYield")},
            {"label": "Profit Margin", "value": pct(fd, "profitMargins")},
            {"label": "Op Margin", "value": pct(fd, "operatingMargins")},
            {"label": "Rev Growth", "value": pct(fd, "revenueGrowth")},
            {"label": "EPS (TTM)", "value": num(ks, "trailingEps")},
            {"label": "Beta", "value": num(sd, "beta")},
            {"label": "Forward P/E", "value": num(sd, "forwardPE")},
        ]
        return {
            "symbol": symbol,
            "currency": cur,
            "metrics": metrics,
            "recommendation": fd.get("recommendationKey", ""),
        }


    def statements(self, symbol: str) -> dict | None:
        ck = f"stmt:{symbol}"
        hit = self._cache.get(ck)
        if hit and time.time() - hit[0] < _TTL:
            return hit[1]
        self._ensure()
        url = (f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
               f"?modules={_STMT_MODULES}&crumb={self._crumb}")
        try:
            r = self._client.get(url)  # type: ignore[union-attr]
            if r.status_code == 401:
                self._client = self._crumb = None
                self._ensure()
                url = url.split("&crumb=")[0] + f"&crumb={self._crumb}"
                r = self._client.get(url)  # type: ignore[union-attr]
            if r.status_code != 200:
                return None
            m = r.json()["quoteSummary"]["result"][0]
        except (httpx.HTTPError, KeyError, ValueError, IndexError):
            return None
        cur = m.get("price", {}).get("currency", "USD")
        out = {
            "income": _stmt_table(m.get("incomeStatementHistory", {}).get("incomeStatementHistory", []), _INCOME, cur),
            "balance": _stmt_table(m.get("balanceSheetHistory", {}).get("balanceSheetStatements", []), _BALANCE, cur),
            "cashflow": _stmt_table(m.get("cashflowStatementHistory", {}).get("cashflowStatements", []), _CASHFLOW, cur),
        }
        out = {k: v for k, v in out.items() if v["rows"]}  # drop empty (Yahoo gutted some)
        self._cache[ck] = (time.time(), out or None)
        return out or None


def _stmt_table(stmts: list, fields: list, cur: str) -> dict:
    if not stmts:
        return {"periods": [], "rows": []}
    periods, cols = [], []
    for s in stmts:
        ed = s.get("endDate", {})
        periods.append((ed.get("fmt") or "")[:7] or "—")
        cols.append(s)
    rows = []
    for label, key in fields:
        vals = []
        any_val = False
        for s in cols:
            raw = (s.get(key) or {}).get("raw")
            if raw is not None:
                any_val = True
            vals.append(_scale(raw, cur))
        if any_val:
            rows.append({"label": label, "values": vals})
    return {"periods": periods, "rows": rows}


def _scale(v, cur: str) -> str:
    if v is None:
        return "—"
    sym = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(cur, "")
    neg = "-" if v < 0 else ""
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{neg}{sym}{a / div:.2f}{suf}"
    return f"{neg}{sym}{a:.0f}"


def _mcap(v, cur: str) -> str:
    if not v:
        return "—"
    if cur == "INR":  # Indian convention: crore / lakh crore
        cr = v / 1e7
        return f"₹{cr / 1e5:.2f} L Cr" if cr >= 1e5 else f"₹{cr:,.0f} Cr"
    sym = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(cur, "")
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if v >= div:
            return f"{sym}{v / div:.2f}{suf}"
    return f"{sym}{v:,.0f}"
