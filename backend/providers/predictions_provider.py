"""Prediction markets via Polymarket Gamma API — free, no key.

Surfaces only markets that carry *signal*: finance/economy-relevant, genuinely
uncertain (not pinned near 0/100), and liquid. The cluster of separate Fed
rate-decision markets is collapsed into a single rate-path entry. When nothing
qualifies we return [] and the frontend hides the widget entirely — better an
absent card than a wall of 99.9% noise.
"""
from __future__ import annotations

import json
import re

import httpx

_URL = "https://gamma-api.polymarket.com/markets"
_TIMEOUT = httpx.Timeout(10.0)
_KEYWORDS = (
    "fed", "rate", "rates", "inflation", "recession", "stock", "s&p", "nasdaq",
    "dow", "bitcoin", "btc", "crypto", "ethereum", "oil", "gold", "economy",
    "gdp", "tariff", "interest", "treasury", "nvidia", "tesla", "ipo", "powell",
)

# A market is worth showing only if it's still contested and has real liquidity.
_MIN_PCT, _MAX_PCT = 5.0, 95.0   # top outcome must sit inside this band
_MIN_VOL24 = 5000.0              # 24h volume floor, USD

_FED_RE = re.compile(r"\bfed\b.*interest rate.*meeting", re.I)
_MONTH_RE = re.compile(r"after the ([A-Z][a-z]+(?:\s+\d{4})?) meeting", re.I)


class PredictionsProvider:
    def markets(self, limit: int = 6) -> list[dict]:
        items = self._fetch()
        if not items:
            return []

        finance = [m for m in items if _is_finance(m.get("question"))]
        fed = [m for m in finance if _FED_RE.search(m.get("question") or "")]
        others = [m for m in finance if m not in fed]

        out: list[dict] = []

        fed_entry = _collapse_fed(fed)
        if fed_entry:
            out.append(fed_entry)

        for m in others:
            outcomes = _parse(m.get("outcomes"), m.get("outcomePrices"))
            if not outcomes:
                continue
            top = max(o["pct"] for o in outcomes)
            vol = float(m.get("volume24hr") or 0)
            if _MIN_PCT < top < _MAX_PCT and vol >= _MIN_VOL24:
                out.append({
                    "question": (m.get("question") or "").strip(),
                    "outcomes": outcomes,
                    "volume": round(vol),
                })
            if len(out) >= limit:
                break

        return out[:limit]

    def _fetch(self) -> list[dict]:
        try:
            r = httpx.get(
                _URL,
                params={
                    "closed": "false", "active": "true",
                    "order": "volume24hr", "ascending": "false", "limit": 200,
                },
                timeout=_TIMEOUT,
            )
            if r.status_code != 200:
                return []
            data = r.json()
            return data if isinstance(data, list) else data.get("data", [])
        except (httpx.HTTPError, ValueError):
            return []


def _is_finance(question: str | None) -> bool:
    if not question:
        return False
    ql = question.lower()
    return any(k in ql for k in _KEYWORDS)


def _fed_scenario(question: str) -> str | None:
    """Map a Fed rate-decision question to a short scenario label."""
    ql = question.lower()
    if "no change" in ql:
        return "Hold"
    m = re.search(r"(decrease|increase).*?(\d+)\+?\s*bps", ql)
    if not m:
        return None
    verb, bps = m.group(1), m.group(2)
    plus = "+" if "+" in ql.split("bps")[0][-4:] else ""
    return f"{'Cut' if verb == 'decrease' else 'Hike'} {bps}{plus} bps"


def _collapse_fed(markets: list[dict]) -> dict | None:
    """Fold the separate Fed rate-decision binaries into one rate-path entry.

    Each binary's Yes price is the probability of that scenario. We only surface
    the combined entry when the decision is still contested (top scenario < 95%).
    """
    scenarios: list[dict] = []
    month = ""
    for m in markets:
        q = m.get("question") or ""
        label = _fed_scenario(q)
        if not label:
            continue
        prices = _parse(m.get("outcomes"), m.get("outcomePrices"))
        yes = next((o["pct"] for o in prices if o["label"].lower() == "yes"), None)
        if yes is None:
            continue
        scenarios.append({"label": label, "pct": yes})
        if not month:
            mm = _MONTH_RE.search(q)
            if mm:
                month = mm.group(1)

    if len(scenarios) < 2:
        return None
    scenarios.sort(key=lambda s: s["pct"], reverse=True)
    if scenarios[0]["pct"] >= _MAX_PCT:
        return None  # decision effectively settled — no signal

    return {
        "question": f"Fed rate decision{f' — {month}' if month else ''}",
        "outcomes": scenarios[:3],
        "volume": 0,
    }


def _parse(outcomes, prices) -> list[dict]:
    """Polymarket returns outcomes + prices as JSON-encoded strings."""
    try:
        o = json.loads(outcomes) if isinstance(outcomes, str) else (outcomes or [])
        p = json.loads(prices) if isinstance(prices, str) else (prices or [])
    except (ValueError, TypeError):
        return []
    res = []
    for label, price in zip(o, p):
        try:
            res.append({"label": str(label), "pct": round(float(price) * 100, 1)})
        except (ValueError, TypeError):
            continue
    return res[:3]
