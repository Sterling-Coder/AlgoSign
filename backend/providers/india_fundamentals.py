"""Deep Indian fundamentals via Screener.in (wraps the user's scraper).

Screener.in gives India-specific data Yahoo lacks: ROCE, pros/cons, quarterly
trend, promoter holding. Slow (scrapes HTML) so we cache 6h in memory and serve
it from a dedicated endpoint the frontend loads lazily.
"""
from __future__ import annotations

import time

from .screener_in import ScreenerFundamentalData

_TTL = 6 * 60 * 60


class IndiaFundamentals:
    def __init__(self) -> None:
        self._s = ScreenerFundamentalData()
        self._cache: dict[str, tuple[float, dict]] = {}

    def get(self, symbol: str) -> dict | None:
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        hit = self._cache.get(sym)
        if hit and time.time() - hit[0] < _TTL:
            return hit[1]
        try:
            r = self._s.get_fundamentals_with_json(sym)
        except Exception:  # noqa: BLE001 — scraper can throw on odd pages
            return None
        if not r.get("success"):
            return None
        payload = self._shape(r["data"])
        self._cache[sym] = (time.time(), payload)
        return payload

    def _shape(self, d: dict) -> dict:
        ci = d.get("company_info", {}) or {}
        name = ci.get("name", "")
        ratios = [
            {"label": k, "value": v}
            for k, v in ci.items()
            if k != "name" and v not in (None, "", "-")
        ]
        pc = d.get("pros_cons", {}) or {}

        # Quarterly sales trend (the row whose label looks like "Sales").
        q = d.get("financial_statements", {}).get("quarterly_results", []) or []
        sales_row = next((r for r in q if "sales" in (r.get("") or "").lower()), None)
        quarterly_sales = (
            [{"q": k, "v": v} for k, v in sales_row.items() if k] if sales_row else []
        )[-8:]

        # Latest promoter holding.
        sh = d.get("shareholding", []) or []
        prom_row = next((r for r in sh if "promoter" in (r.get("") or "").lower()), None)
        promoter = None
        if prom_row:
            vals = [v for k, v in prom_row.items() if k]
            promoter = vals[-1] if vals else None

        fs = d.get("financial_statements", {})
        statements = {
            "quarterly": _table(fs.get("quarterly_results", [])),
            "pnl": _table(fs.get("profit_loss", [])),
            "balance_sheet": _table(fs.get("balance_sheet", [])),
            "cash_flow": _table(fs.get("cash_flow", [])),
            "ratios": _table(d.get("ratios", [])),
            "shareholding": _table(sh),
        }

        about = d.get("about", {})
        desc = about.get("meta_description", "") if isinstance(about, dict) else ""
        docs = d.get("documents", {}) or {}

        def doclist(key, limit=6):
            items = docs.get(key) or []
            if isinstance(items, dict):
                items = [items]
            out = []
            for it in items[:limit]:
                if isinstance(it, dict) and it.get("url"):
                    label = (it.get("label") or "").split("\n")[0].strip()[:120]
                    out.append({"label": label or "Document", "url": it["url"], "date": it.get("date", "")})
            return out

        return {
            "source": "Screener.in",
            "name": name,
            "about": desc,
            "ratios": ratios,
            "pros": pc.get("pros", []),
            "cons": pc.get("cons", []),
            "quarterly_sales": quarterly_sales,
            "promoter_holding": promoter,
            "statements": statements,
            "documents": {
                "announcements": doclist("recent_announcements"),
                "annual_reports": doclist("annual_reports"),
                "credit_ratings": doclist("credit_ratings"),
            },
        }


def _table(rows: list[dict]) -> dict:
    """Turn scraper rows ({'': label, 'Mar 2023': val, ...}) into a table shape."""
    if not rows:
        return {"periods": [], "rows": []}
    periods = [k for k in rows[0].keys() if k and k.lower() != "raw pdf"]
    out = []
    for r in rows:
        label = (r.get("") or "").replace("+", "").strip()
        if not label or label.lower() == "raw pdf":
            continue
        out.append({"label": label, "values": [r.get(p, "") for p in periods]})
    return {"periods": periods, "rows": out}
