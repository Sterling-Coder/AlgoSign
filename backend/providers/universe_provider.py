"""Live stock universe via Yahoo's screener — no hard-coded ticker lists.

Replaces the fixed baskets/sectors with live queries:
  - movers(region, kind):   real day gainers / losers / most-active
  - by_sector(region):      top names per GICS sector, for the heatmap
  - top(region, n):         broad large-cap universe, for the momentum screener

Yahoo's screener POST endpoint needs a crumb (cookie + token). We do the dance
once and cache it, refreshing on 401. Results cache short so pages stay live but
don't hammer Yahoo. Every method degrades to None so callers can fall back to
the static baskets if Yahoo is unreachable.
"""
from __future__ import annotations

import threading
import time

import httpx

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_SCREENER = "https://query1.finance.yahoo.com/v1/finance/screener"
_QUOTE = "https://query1.finance.yahoo.com/v7/finance/quote"
_OPTIONS = "https://query1.finance.yahoo.com/v7/finance/options/{}"
_CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
_COOKIE_URL = "https://fc.yahoo.com"
_TIMEOUT = httpx.Timeout(12.0)

_CRUMB_TTL = 30 * 60          # re-auth every 30 min
_MOVERS_TTL = 5 * 60         # gainers/losers refresh every 5 min
_SECTOR_TTL = 12 * 60 * 60   # sector membership barely moves
_TOP_TTL = 6 * 60 * 60       # universe for momentum
_OPTIONS_TTL = 5 * 60        # option chains move intraday
_STRIKE_WINDOW = 10          # strikes to keep each side of at-the-money

# region key -> Yahoo region code(s). WORLD = ex-US majors.
_REGION_CODES: dict[str, list[str]] = {
    "IN": ["in"],
    "US": ["us"],
    "WORLD": ["gb", "jp", "de", "fr", "hk", "ca", "au", "ch", "nl"],
    "ALL": ["us", "in", "gb", "jp", "de", "fr", "hk", "ca", "au"],
}
# Drop penny/illiquid junk from movers (local currency; modest floors).
_MCAP_FLOOR: dict[str, float] = {"IN": 1e10, "US": 1e9, "WORLD": 1e9, "ALL": 1e9}

# Restrict to primary listing venues so OTC pink-sheets never show up. For India
# NSI also pins results to NSE (.NS). WORLD spans many venues, so it relies on
# the OTC + suffix filters below instead of a whitelist.
_EXCHANGES: dict[str, list[str]] = {
    "US": ["NMS", "NYQ", "ASE"],
    "IN": ["NSI"],
    "ALL": ["NMS", "NYQ", "ASE", "NSI", "LSE", "GER", "JPX", "HKG"],
}
_OTC = {"PNK", "OTC", "OBB", "PINK"}
# Warrant / right / unit / SME-series suffixes — not common shares.
_NONCOMMON_SUFFIXES = ("-WT", "-WS", "-RT", "-RTWI", "-UN", "-U", "-RE", "-RE1",
                       "-SM", "-BE", "-BZ", "-IT")


def _is_common(symbol: str, exchange: str | None) -> bool:
    if exchange in _OTC:
        return False
    base = symbol.rsplit(".", 1)[0]  # strip .NS/.BO/.L etc
    return not any(base.endswith(s) for s in _NONCOMMON_SUFFIXES)

# Yahoo GICS sectors -> short heatmap label.
_SECTORS: dict[str, str] = {
    "Technology": "Tech",
    "Communication Services": "Comm",
    "Consumer Cyclical": "Consumer",
    "Consumer Defensive": "Staples",
    "Financial Services": "Financials",
    "Healthcare": "Health",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Basic Materials": "Materials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
}


def _or_eq(field: str, codes: list[str]) -> dict:
    eqs = [{"operator": "eq", "operands": [field, c]} for c in codes]
    return eqs[0] if len(eqs) == 1 else {"operator": "OR", "operands": eqs}


def _venue_operands(region: str) -> list[dict]:
    """Region filter + (where known) a primary-exchange whitelist."""
    region = region.upper()
    ops = [_or_eq("region", _REGION_CODES.get(region, ["us"]))]
    exchanges = _EXCHANGES.get(region)
    if exchanges:
        ops.append(_or_eq("exchange", exchanges))
    return ops


def _quote_name(q: dict) -> str:
    return q.get("shortName") or q.get("longName") or q.get("symbol", "")


class UniverseProvider:
    """Live, query-driven equity universe. Thread-safe; caches in-process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._crumb: str | None = None
        self._crumb_at = 0.0
        self._client = httpx.Client(headers={"User-Agent": _UA}, timeout=_TIMEOUT)
        self._cache: dict[str, tuple[float, object]] = {}
        # symbol -> live display name, harvested from every screener response.
        self.names: dict[str, str] = {}

    # --- auth -------------------------------------------------------------
    def _ensure_crumb(self, force: bool = False) -> str | None:
        if not force and self._crumb and time.time() - self._crumb_at < _CRUMB_TTL:
            return self._crumb
        try:
            self._client.get(_COOKIE_URL)  # sets the consent cookie
            r = self._client.get(_CRUMB_URL)
            if r.status_code == 200 and r.text and "<" not in r.text:
                self._crumb = r.text.strip()
                self._crumb_at = time.time()
                return self._crumb
        except httpx.HTTPError:
            pass
        return None

    # --- raw query --------------------------------------------------------
    def _screen(self, query: dict, sort_field: str, sort_type: str,
                count: int) -> list[dict]:
        """Run one screener query, return quote dicts (empty on any failure)."""
        body = {
            "size": count, "offset": 0,
            "sortField": sort_field, "sortType": sort_type,
            "quoteType": "EQUITY", "query": query,
        }
        for attempt in range(2):
            crumb = self._ensure_crumb(force=attempt == 1)
            if not crumb:
                return []
            try:
                r = self._client.post(
                    _SCREENER, params={"crumb": crumb, "count": count}, json=body,
                )
            except httpx.HTTPError:
                return []
            if r.status_code == 401:
                continue  # stale crumb -> force refresh and retry once
            if r.status_code != 200:
                return []
            try:
                result = r.json()["finance"]["result"]
            except (KeyError, ValueError, TypeError):
                return []
            if not result:
                return []
            quotes = [q for q in result[0].get("quotes", [])
                      if q.get("symbol") and _is_common(q["symbol"], q.get("exchange"))]
            for q in quotes:
                self.names[q["symbol"]] = _quote_name(q)
            return quotes
        return []

    def _get_json(self, url: str, params: dict) -> dict | None:
        """Authed GET. Yahoo throttles cold requests with a transient 401, so we
        retry a few times with a short backoff, refreshing the crumb on 401.
        None on persistent failure."""
        for attempt in range(3):
            crumb = self._ensure_crumb(force=attempt > 0)
            if not crumb:
                time.sleep(0.4 * (attempt + 1))
                continue
            try:
                r = self._client.get(url, params={**params, "crumb": crumb})
            except httpx.HTTPError:
                return None
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return None
            if r.status_code in (401, 429) and attempt < 2:
                time.sleep(0.4 * (attempt + 1))  # transient throttle, back off
                continue
            return None
        return None

    # --- public API -------------------------------------------------------
    def _cached(self, key: str, ttl: float, build):
        now = time.time()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < ttl:
                return hit[1]
        value = build()
        if value:  # never cache an empty/failed result
            with self._lock:
                self._cache[key] = (now, value)
        return value

    @staticmethod
    def _dedupe_in(quotes: list[dict]) -> list[dict]:
        """India returns both .NS and .BO; keep .NS, drop the duplicate."""
        seen: set[str] = set()
        out = []
        for q in quotes:
            sym = q.get("symbol", "")
            base = sym.rsplit(".", 1)[0]
            if sym.endswith(".BO") and (base + ".NS") in {s.rsplit(".", 1)[0] + ".NS" for s in seen}:
                continue
            if base in seen:
                continue
            seen.add(base)
            out.append(q)
        return out

    def movers(self, region: str, kind: str, count: int = 8) -> list[dict] | None:
        """kind in {gainers, losers, active}; live price + day change."""
        region = region.upper()
        sort_field, sort_type = {
            "gainers": ("percentchange", "DESC"),
            "losers": ("percentchange", "ASC"),
            "active": ("dayvolume", "DESC"),
        }.get(kind, ("percentchange", "DESC"))

        def build():
            floor = _MCAP_FLOOR.get(region, 1e9)
            query = {"operator": "AND", "operands": _venue_operands(region) + [
                {"operator": "GT", "operands": ["intradaymarketcap", floor]},
            ]}
            quotes = self._screen(query, sort_field, sort_type, count * 3)
            if region == "IN":
                quotes = self._dedupe_in(quotes)
            rows = []
            for q in quotes[:count]:
                pct = q.get("regularMarketChangePercent")
                last = q.get("regularMarketPrice")
                if pct is None or last is None:
                    continue
                rows.append({
                    "symbol": q["symbol"],
                    "name": _quote_name(q),
                    "last": round(float(last), 2),
                    "change_pct": round(float(pct), 2),
                })
            return rows

        return self._cached(f"movers:{region}:{kind}:{count}", _MOVERS_TTL, build)

    def by_sector(self, region: str, per_sector: int = 5) -> list[dict] | None:
        """[{sector, symbols, names}] — top names per GICS sector, live."""
        region = region.upper()

        def build():
            out = []
            for gics, label in _SECTORS.items():
                query = {"operator": "AND", "operands": _venue_operands(region) + [
                    {"operator": "EQ", "operands": ["sector", gics]},
                ]}
                quotes = self._screen(query, "intradaymarketcap", "DESC", per_sector * 3)
                if region == "IN":
                    quotes = self._dedupe_in(quotes)
                syms = [q["symbol"] for q in quotes[:per_sector] if q.get("symbol")]
                if syms:
                    out.append({"sector": label, "symbols": syms})
            return out

        return self._cached(f"sectors:{region}:{per_sector}", _SECTOR_TTL, build)

    def top(self, region: str, n: int = 40) -> list[str] | None:
        """Broad large-cap universe for the momentum screener."""
        region = region.upper()

        def build():
            query = {"operator": "AND", "operands": _venue_operands(region)}
            quotes = self._screen(query, "intradaymarketcap", "DESC", n * 2)
            if region == "IN":
                quotes = self._dedupe_in(quotes)
            return [q["symbol"] for q in quotes[:n] if q.get("symbol")]

        return self._cached(f"top:{region}:{n}", _TOP_TTL, build)

    def label(self, symbol: str) -> str | None:
        return self.names.get(symbol)

    def quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Live last price + day change% for a batch of symbols (for alerts).

        Uncached: alerts need fresh values. Returns {} on failure so the scan
        simply skips this tick rather than firing on stale data.
        """
        syms = [s for s in dict.fromkeys(symbols) if s][:50]
        if not syms:
            return {}
        data = self._get_json(_QUOTE, {"symbols": ",".join(syms)})
        try:
            results = data["quoteResponse"]["result"]
        except (KeyError, TypeError):
            return {}
        out: dict[str, dict] = {}
        for q in results:
            sym = q.get("symbol")
            price = q.get("regularMarketPrice")
            if not sym or price is None:
                continue
            out[sym] = {
                "price": round(float(price), 2),
                "change": round(float(q.get("regularMarketChange") or 0), 2),
                "change_pct": round(float(q.get("regularMarketChangePercent") or 0), 2),
                "market_state": q.get("marketState", ""),
            }
            if q.get("shortName") or q.get("longName"):
                self.names[sym] = q.get("shortName") or q.get("longName")
        return out

    # --- options ----------------------------------------------------------
    @staticmethod
    def _opt_row(o: dict) -> dict:
        return {
            "strike": o.get("strike"),
            "last": o.get("lastPrice"),
            "bid": o.get("bid"),
            "ask": o.get("ask"),
            "volume": o.get("volume") or 0,
            "open_interest": o.get("openInterest") or 0,
            "iv": round(float(o["impliedVolatility"]) * 100, 1) if o.get("impliedVolatility") else None,
            "itm": bool(o.get("inTheMoney")),
        }

    def _window(self, rows: list[dict], underlying: float) -> list[dict]:
        """Keep the strikes nearest the money so the table stays readable."""
        rows = [r for r in rows if r.get("strike") is not None]
        rows.sort(key=lambda r: abs(r["strike"] - underlying))
        near = rows[: _STRIKE_WINDOW * 2]
        near.sort(key=lambda r: r["strike"])
        return near

    def options(self, symbol: str, expiration: int | None = None) -> dict | None:
        """Option chain for a symbol, trimmed to strikes around the money."""
        sym = symbol.upper()

        def build():
            params = {"date": expiration} if expiration else {}
            data = self._get_json(_OPTIONS.format(sym), params)
            try:
                res = data["optionChain"]["result"][0]
            except (KeyError, IndexError, TypeError):
                return None
            chains = res.get("options") or []
            if not chains:
                return None
            chain = chains[0]
            underlying = res.get("quote", {}).get("regularMarketPrice")
            if underlying is None:
                return None
            exps = [
                {"ts": ts, "date": time.strftime("%Y-%m-%d", time.gmtime(ts))}
                for ts in res.get("expirationDates", [])
            ]
            calls = self._window([self._opt_row(o) for o in chain.get("calls", [])], underlying)
            puts = self._window([self._opt_row(o) for o in chain.get("puts", [])], underlying)
            if not calls and not puts:
                return None
            return {
                "symbol": sym,
                "underlying": round(float(underlying), 2),
                "expiration": chain.get("expirationDate"),
                "expirations": exps,
                "calls": calls,
                "puts": puts,
            }

        return self._cached(f"options:{sym}:{expiration or 0}", _OPTIONS_TTL, build)
