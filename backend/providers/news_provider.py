"""Market news per region via Google News RSS — free, no API key.

Returns recent headlines with source and relative time. Region-aware so the
News page follows the sidebar market switch.
"""
from __future__ import annotations

import time
from email.utils import parsedate_to_datetime

import httpx
from defusedxml import ElementTree as DET
from xml.etree.ElementTree import ParseError

# region -> (search query, hl, gl, ceid)
_FEEDS: dict[str, tuple[str, str, str, str]] = {
    "IN": ("India stock market Nifty Sensex", "en-IN", "IN", "IN:en"),
    "US": ("US stock market S&P 500 Nasdaq", "en-US", "US", "US:en"),
    "WORLD": ("global stock markets economy", "en-US", "US", "US:en"),
}

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_TIMEOUT = httpx.Timeout(10.0)


def _ago(pubdate: str) -> str:
    try:
        dt = parsedate_to_datetime(pubdate)
        secs = time.time() - dt.timestamp()
    except (TypeError, ValueError):
        return ""
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


class NewsProvider:
    def headlines(self, region: str, limit: int = 20) -> list[dict]:
        query, hl, gl, ceid = _FEEDS.get(region.upper(), _FEEDS["US"])
        return self._fetch(query, hl, gl, ceid, limit)

    def for_query(self, query: str, limit: int = 6) -> list[dict]:
        """Headlines for a specific company/symbol search."""
        return self._fetch(f"{query} stock", "en-US", "US", "US:en", limit)

    def _fetch(self, query: str, hl: str, gl: str, ceid: str, limit: int) -> list[dict]:
        url = "https://news.google.com/rss/search"
        params = {"q": query, "hl": hl, "gl": gl, "ceid": ceid}
        try:
            r = httpx.get(url, params=params, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
            if r.status_code != 200:
                return []
            root = DET.fromstring(r.content)
        except (httpx.HTTPError, ParseError):
            return []

        out = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = item.findtext("pubDate") or ""
            src_el = item.find("source")
            source = (src_el.text or "").strip() if src_el is not None else ""
            # Google titles are "Headline - Source"; strip trailing source.
            if source and title.endswith(f" - {source}"):
                title = title[: -(len(source) + 3)]
            if not title or not link:
                continue
            out.append({
                "title": title,
                "source": source,
                "link": link,
                "ago": _ago(pub),
            })
            if len(out) >= limit:
                break
        return out
