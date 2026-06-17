"""AlgoSign API — region-agnostic market data + signals.

Run: uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()  # loads backend/.env (OPENAI_API_KEY, OPENAI_MODEL)

from providers import YahooProvider, BinanceProvider, BSTOCK_MAP, UniverseProvider
from providers.news_provider import NewsProvider
from providers.predictions_provider import PredictionsProvider
from providers.ai_provider import AIProvider
from providers.fundamentals_provider import FundamentalsProvider
from providers.india_fundamentals import IndiaFundamentals
from providers.stockanalysis_provider import StockAnalysisProvider
from signals.market import snapshot as market_snapshot_fn
from signals.baskets import basket
from signals.momentum import rank_basket
from signals.gap import gap_radar
from signals.actions import build_actions
from signals.overview import overview as market_overview
from signals.stock import detail as stock_detail
from signals.smc import analyze as smc_analyze
from signals.heatmap import heatmap as heatmap_fn
from signals.predict import predict as predict_fn
from signals import names as _names
from core import db, scheduler, alerts as alerts_mod, bots as bots_mod
from core.device import DeviceMiddleware, get_device
from core.sse import hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    scheduler.register("alerts", lambda: alerts_mod.scan(universe, hub), every_seconds=60)
    scheduler.register("bots", lambda: bots_mod.manage(universe, hub), every_seconds=60)
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="AlgoSign API", version="0.1.0", lifespan=lifespan)

# Order matters: CORS outermost, then device identity.
app.add_middleware(DeviceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,  # required so the signed device cookie crosses 3000->8000
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/stream")
async def stream(request: Request, device: str = Depends(get_device)):
    """Server-Sent Events: live push channel (alerts, fills) for this device."""
    return StreamingResponse(
        hub.stream(device, request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class AlertIn(BaseModel):
    symbol: str
    kind: str = "price"          # price | pct_change
    direction: str = "above"     # above | below
    threshold: float
    note: str | None = None


@app.get("/alerts")
def alerts_list(device: str = Depends(get_device)):
    """This device's alert rules (active first)."""
    return {"alerts": alerts_mod.list_for(device)}


@app.post("/alerts")
def alerts_create(body: AlertIn, device: str = Depends(get_device)):
    """Create a one-shot price/percent alert for this device."""
    try:
        a = alerts_mod.create(device, body.symbol, body.kind, body.direction,
                              body.threshold, body.note)
    except alerts_mod.AlertError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    return {"alert": a}


@app.delete("/alerts/{alert_id}")
def alerts_delete(alert_id: int, device: str = Depends(get_device)):
    """Delete one of this device's alerts."""
    return {"deleted": alerts_mod.delete(device, alert_id)}


class BotOrderIn(BaseModel):
    symbol: str
    side: str = "long"           # long | short
    qty: float
    stop: float | None = None
    target: float | None = None


@app.get("/bots")
def bots_list(device: str = Depends(get_device)):
    """Paper positions for this device + realized/unrealized P&L."""
    return {"real_money": bots_mod.REAL_MONEY, **bots_mod.list_positions(device, universe=universe)}


@app.post("/bots")
def bots_open(body: BotOrderIn, device: str = Depends(get_device)):
    """Open a simulated position (filled at the live price)."""
    try:
        p = bots_mod.open_position(device, body.symbol, body.side, body.qty,
                                   body.stop, body.target, universe=universe)
    except bots_mod.BotError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    return {"position": p}


@app.post("/bots/{pos_id}/close")
def bots_close(pos_id: int, device: str = Depends(get_device)):
    """Manually close an open paper position at the live price."""
    try:
        p = bots_mod.close_position(device, pos_id, universe=universe)
    except bots_mod.BotError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    if p is None:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return {"position": p}

yf = YahooProvider()
binance = BinanceProvider()
universe = UniverseProvider()


def scan_universe(region: str) -> list[str]:
    """Live large-cap universe for the momentum screener; static basket as fallback."""
    region = region.upper()
    if region == "ALL":
        syms: list[str] = []
        for r in ("US", "IN", "WORLD"):
            syms.extend(universe.top(r, n=15) or [])
        _names.register(universe.names)
        return syms if syms else basket("ALL")
    live = universe.top(region, n=40)
    _names.register(universe.names)
    return live if live else basket(region)
news = NewsProvider()
predictions = PredictionsProvider()
ai = AIProvider()
fundamentals = FundamentalsProvider()
india_fund = IndiaFundamentals()
us_fund = StockAnalysisProvider()


@app.get("/health")
def health():
    return {"status": "ok", "service": "algosign-api", "version": "0.1.0"}


@app.get("/bars")
def bars(
    symbol: str,
    interval: str = "1d",
    period: str = "2y",
    start: str | None = None,
    end: str | None = None,
):
    df = yf.bars(symbol, start=start, end=end, interval=interval, period=period)
    if df.empty:
        return {"symbol": symbol, "bars": []}
    out = [
        {
            "t": ts.strftime("%Y-%m-%d"),
            "o": round(float(r.open), 2),
            "h": round(float(r.high), 2),
            "l": round(float(r.low), 2),
            "c": round(float(r.close), 2),
            "v": int(r.volume) if r.volume == r.volume else 0,
        }
        for ts, r in df.iterrows()
    ]
    return {"symbol": symbol, "bars": out}


@app.get("/screener/momentum")
def screener_momentum(region: str = Query("ALL")):
    syms = scan_universe(region)
    return {"region": region.upper(), "count": len(syms), "results": rank_basket(syms, yf)}


@app.get("/gap-radar")
def gap(min_pct: float = 0.0):
    return {"signals": gap_radar(binance, yf, min_pct=min_pct)}


@app.get("/search")
def search(q: str = Query(..., min_length=1)):
    """Resolve a query to symbols, e.g. 'TCS' -> TCS.NS."""
    return {"query": q, "results": yf.search(q)}


_UNDERLYING_TO_TOKEN = {v: k for k, v in BSTOCK_MAP.items()}


@app.get("/stock")
def stock(symbol: str = Query(...)):
    """Full detail for one symbol: verdict, levels, returns, news, gap, series."""
    d = stock_detail(symbol, yf)
    if d is None:
        return {"error": "not_found", "symbol": symbol}

    # Fundamentals (Yahoo ratios; + full statements for non-India)
    fund = fundamentals.fundamentals(symbol)
    if fund and not symbol.upper().endswith((".NS", ".BO")):
        fund["statements"] = fundamentals.statements(symbol)
    d["fundamentals"] = fund

    # Deep US/World fundamentals (stockanalysis.com) for plain tickers
    d["us_fundamentals"] = us_fund.get(symbol)

    # News for this name
    d["news"] = news.for_query(d.get("name") or symbol, limit=5)

    # 24/7 tokenized gap, if this is a bStock underlying
    token = _UNDERLYING_TO_TOKEN.get(symbol.upper())
    d["gap"] = None
    if token:
        tick = binance.ticker_24hr(token)
        if tick and d["last"]:
            d["gap"] = {
                "token": token,
                "token_price": round(tick["price"], 2),
                "implied_open_pct": round((tick["price"] / d["last"] - 1) * 100, 2),
            }
    return d


@app.get("/smc")
def smc(symbol: str = Query(...), period: str = Query("1y"), interval: str = Query("1d")):
    """Smart Money Concepts analysis: structure, order blocks, FVGs, signals."""
    d = smc_analyze(symbol, yf, period=period, interval=interval)
    if d is None:
        return {"error": "not_found", "symbol": symbol}
    return d


@app.get("/india-fundamentals")
def india_fundamentals(symbol: str = Query(...)):
    """Deep Indian fundamentals (Screener.in): ROCE, pros/cons, quarterly, holding."""
    d = india_fund.get(symbol)
    if d is None:
        return {"available": False}
    return {"available": True, **d}


@app.get("/overview")
def overview(region: str = Query("US")):
    """Headline index/asset cards with sparklines for the region."""
    return {"region": region.upper(), "cards": market_overview(region, yf, universe=universe)}


@app.get("/quotes")
def quotes(symbols: str = Query(..., description="comma-separated symbols")):
    """Lightweight last + day-change for a watchlist of symbols."""
    out = []
    for sym in [s.strip() for s in symbols.split(",") if s.strip()][:30]:
        df = yf.bars(sym, interval="1d", period="5d")
        if df.empty or len(df) < 2:
            continue
        c = df["close"].dropna()
        last, prev = float(c.iloc[-1]), float(c.iloc[-2])
        from signals.names import name as _nm
        out.append({
            "symbol": sym,
            "name": _nm(sym),
            "last": round(last, 2),
            "change_pct": round((last / prev - 1) * 100, 2) if prev else 0.0,
        })
    return {"quotes": out}


@app.get("/market")
def market(region: str = Query("US")):
    """Live gainers, losers, most-active + breadth sentiment for the region."""
    snap = market_snapshot_fn(region, scan_universe(region), yf, universe=universe)
    return {"region": region.upper(), **snap}


@app.get("/heatmap")
def heatmap(region: str = Query("US")):
    """Stocks grouped by sector with day change, for the heatmap (live membership)."""
    return {"region": region.upper(), "sectors": heatmap_fn(region, yf, universe=universe)}


@app.get("/options")
def options(symbol: str = Query(...), expiration: int | None = Query(None)):
    """Option chain (calls/puts near the money) for a symbol; None if no options."""
    d = universe.options(symbol, expiration)
    if d is None:
        return {"available": False, "symbol": symbol}
    return {"available": True, **d}


@app.get("/predict")
def predict(symbol: str = Query(...)):
    """Probabilistic, backtested forward-return call for one symbol."""
    d = predict_fn(symbol, yf)
    if d is None:
        return {"available": False, "symbol": symbol}
    return {"available": True, **d}


@app.get("/predictions")
def predictions_feed():
    """Finance-relevant prediction-market odds (Polymarket)."""
    return {"markets": predictions.markets()}


def _market_context(region: str) -> str:
    """Compact live snapshot fed to the assistant so answers are grounded."""
    region = region.upper()
    syms = scan_universe(region)
    mom = rank_basket(syms, yf)
    snap = market_snapshot_fn(region, syms, yf, universe=universe)
    calls = build_actions(mom, gap_radar(binance, yf) if region in ("US", "ALL") else [])
    headlines = news.headlines(region, limit=5)

    s = snap.get("sentiment") or {}
    lines = [f"REGION: {region}"]
    if s:
        lines.append(f"SENTIMENT: {s.get('label')} ({s.get('score')}/100, {s.get('pct_up')}% rising)")
    lines.append("TODAY'S CALLS:")
    for a in calls[:8]:
        lines.append(f"  {a['action']} {a['symbol']} ({a['name']}) — {a['reason']}")
    lines.append("GAINERS: " + ", ".join(f"{g['symbol']} {g['change_pct']:+}%" for g in snap.get("gainers", [])[:5]))
    lines.append("LOSERS: " + ", ".join(f"{g['symbol']} {g['change_pct']:+}%" for g in snap.get("losers", [])[:5]))
    lines.append("HEADLINES:")
    for h in headlines:
        lines.append(f"  - {h['title']} ({h['source']})")
    return "\n".join(lines)


_SYSTEM = (
    "You are AlgoSign's market assistant. Answer the user's question using ONLY the "
    "live market data below plus general market knowledge. Be concise, concrete, and "
    "honest about uncertainty. Signals are informational, NOT financial advice. If the "
    "data does not cover the question, say so. Never invent prices.\n\n--- LIVE DATA ---\n"
)


class ChatIn(BaseModel):
    message: str
    region: str = "US"


@app.post("/chat")
def chat(body: ChatIn):
    if not ai.available():
        return {"configured": False,
                "reply": "Add OPENAI_API_KEY to backend/.env to enable the assistant."}
    try:
        ctx = _market_context(body.region)
        reply = ai.chat(_SYSTEM + ctx, body.message)
    except Exception as e:  # noqa: BLE001 — surface a friendly message
        return {"configured": True, "reply": f"Assistant error: {type(e).__name__}. Check your key/model."}
    return {"configured": True, "reply": reply or "(no response)"}


@app.get("/ai-summary")
def ai_summary(region: str = Query("US")):
    if not ai.available():
        return {"configured": False, "summary": ""}
    try:
        ctx = _market_context(region)
        summary = ai.chat(
            _SYSTEM + ctx,
            "Give a 2-3 sentence plain-English summary of what's happening in this "
            "market today and the single most important thing to watch.",
        )
    except Exception as e:  # noqa: BLE001
        return {"configured": True, "summary": f"(summary unavailable: {type(e).__name__})"}
    return {"configured": True, "summary": summary}


_NEWS_SYSTEM = (
    "You are a market editor. Given today's headlines + sentiment for a region, "
    "explain what's happening so a non-expert instantly gets it. Return ONLY valid "
    "JSON (no markdown), shape: "
    '{"summary": "3-4 plain sentences: what moved and why", '
    '"themes": [{"title": "short theme", "detail": "one sentence"}]}. '
    "Give exactly 3 themes. Be concrete, use the headlines. Not financial advice."
)


_COUNCIL_SYSTEM = (
    "You are a stock Analyst Council. Four analysts each give a take, then a Chief "
    "synthesizes a verdict. Use the data provided; be concrete with the numbers. "
    "Return ONLY valid JSON (no markdown): "
    '{"agents":[{"role":"Technical","stance":"bullish|bearish|neutral",'
    '"confidence":"low|medium|high","take":"1-2 sentences"}, '
    '{"role":"Fundamental",...},{"role":"News",...},{"role":"Risk",...}], '
    '"verdict":{"call":"BUY|HOLD|REDUCE|AVOID","confidence":"low|medium|high",'
    '"reason":"1-2 sentences"}}. Informational, not financial advice.'
)


@app.get("/council")
def council(symbol: str = Query(...)):
    """AI Analyst Council: technical/fundamental/news/risk agents + verdict."""
    if not ai.available():
        return {"configured": False}
    det = stock_detail(symbol, yf)
    if det is None:
        return {"configured": True, "error": "not_found"}
    sm = smc_analyze(symbol, yf, period="1y") or {}
    lines = [
        f"{det['name']} ({symbol}) — price {det['last']}, day {det['change_pct']}%",
        f"Returns: 1M {det['r1']}% 3M {det['r3']}% 6M {det['r6']}% 12M {det['r12']}%",
        f"Trend: {'above' if det['above_200dma'] else 'below'} 200-DMA; "
        f"52w high {det['high52']} / low {det['low52']}",
    ]
    if sm.get("signals"):
        lines.append("SMC signals: " + ", ".join(f"{s['side']}@{s['t']}" for s in sm["signals"][-3:]))
    if sm.get("trend"):
        lines.append(f"SMC structure trend: {sm['trend']}")

    if symbol.upper().endswith((".NS", ".BO")):
        f = india_fund.get(symbol)
        if f:
            lines.append("Fundamentals: " + ", ".join(f"{r['label']} {r['value']}" for r in f["ratios"][:8]))
            if f.get("pros"):
                lines.append("Pros: " + " | ".join(f["pros"][:2]))
            if f.get("cons"):
                lines.append("Cons: " + " | ".join(f["cons"][:2]))
    else:
        f = us_fund.get(symbol)
        if f:
            for g in f["groups"]:
                lines.append(f"{g['title']}: " + ", ".join(f"{i['label']} {i['value']}" for i in g["items"][:5]))

    heads = news.for_query(det.get("name") or symbol, limit=5)
    if heads:
        lines.append("Headlines: " + " | ".join(h["title"] for h in heads[:5]))

    try:
        raw = ai.chat(_COUNCIL_SYSTEM, "\n".join(lines)).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        import json as _json
        parsed = _json.loads(raw)
        return {"configured": True, "symbol": symbol, **parsed}
    except Exception:  # noqa: BLE001
        return {"configured": True, "error": "parse_failed"}


@app.get("/news-brief")
def news_brief(region: str = Query("US")):
    """AI brief + key themes synthesized from today's headlines."""
    if not ai.available():
        return {"configured": False}
    items = news.headlines(region, limit=12)
    snap = market_snapshot_fn(region, scan_universe(region), yf, universe=universe)
    s = snap.get("sentiment") or {}
    ctx = f"REGION: {region.upper()}\n"
    if s:
        ctx += f"SENTIMENT: {s.get('label')} ({s.get('pct_up')}% rising)\n"
    ctx += "HEADLINES:\n" + "\n".join(f"- {h['title']} ({h['source']})" for h in items)
    try:
        raw = ai.chat(_NEWS_SYSTEM, ctx).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        import json as _json
        parsed = _json.loads(raw)
        return {"configured": True, "summary": parsed.get("summary", ""),
                "themes": parsed.get("themes", [])}
    except Exception:  # noqa: BLE001
        return {"configured": True, "summary": "", "themes": []}


@app.get("/news")
def news_feed(region: str = Query("US")):
    """Recent market headlines for the region."""
    return {"region": region.upper(), "items": news.headlines(region)}


@app.get("/actions")
def actions(region: str = Query("US")):
    """Today's plain calls for a region: BUY / REDUCE / WATCH + why."""
    mom = rank_basket(scan_universe(region), yf)
    # Gap signals come from tokenized US stocks, so only relevant for US / ALL.
    gaps = gap_radar(binance, yf) if region.upper() in ("US", "ALL") else []
    return {"region": region.upper(), "actions": build_actions(mom, gaps)}
