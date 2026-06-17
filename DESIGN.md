# AlgoSign — Design Doc

_Your worldwide market command center. Spot → verify → test → act._
_Date: 2026-06-13 · Mode: Builder · Owner: aman_

---

## 1. What this is

A global investing + algo platform. You use it to **understand world markets,
build a portfolio, and test systematic strategies to crack extra edge.**

Markets are global from day one: **US · World · India**. (Indian F/O data is one
dataset that plugs in later — nothing is India-specific.)

Five pages, all global:

| Page | Job |
|------|-----|
| **Screener** ⭐ | Rank global ETFs/stocks by momentum + trend. The radar. (FIRST WIN) |
| **Gap Radar** 🌙 | 24/7 tokenized-stock prices (Binance bStocks) → predict US open gaps. Unique edge. |
| **AlgoTrading** | Backtest momentum/trend strategies, get live signals. |
| **Fundamentals** | Are the winners real businesses? Financials + ratios. |
| **News** | Global catalysts per region, tagged to instruments. |
| **ChatBot** | Claude over your data + news. "Rank world ETFs by 6mo momentum above 200-DMA." |

Plus a **Portfolio** view (core-satellite tracker) as the home base.

## 2. The money thesis (what we're actually capturing)

Not "predict tomorrow" (hard, thin). Instead **ride what's already winning** —
systematic edges retail CAN capture:

1. **Cross-sectional momentum** — rank global assets by 3/6mo return, hold winners, rotate.
2. **Trend-following** — own assets above 200-DMA, exit below. Catches bulls, dodges crashes.
3. **Dual momentum** (Antonacci) — combine both. Decades of evidence, retail-accessible.

Structure for safety AND upside — **core-satellite**:
```
CORE (70%)  compounding base: VTI (US), VXUS (world), VWO (EM), BND/GLD (ballast)
SATELLITE (30%)  the hunt: momentum/thematic ETFs, screener picks, algo signals
```
Core keeps you rich slowly. Satellite is where you take swings without blowing up.

## 3. Stack (locked)

```
Next.js (React, TS)                FastAPI (Python)
  - 5 pages + Portfolio              - region-agnostic data layer
  - charts (lightweight-charts)      - momentum/trend ranking
  - calls FastAPI                    - backtest engine (vectorbt/backtesting.py)
  - ChatBot UI                       - news, fundamentals, screener rules
        |------------ REST/JSON ------------|
```
- Frontend: Next.js (App Router) + TypeScript + Tailwind. Charts: `lightweight-charts`.
- Backend: FastAPI + pandas. Strategy/backtest: `vectorbt` or `backtesting.py`.
- Data: `yfinance` (free, covers US + world ETFs/stocks) to start. Parquet/SQLite store.
- LLM: Claude (`claude-sonnet-4-6`) for ChatBot.
- Dev: `next dev` (3000) + `uvicorn` (8000).

## 4. Region-agnostic data layer (the architecture spine)

```python
class MarketDataProvider(Protocol):
    def bars(symbol, start, end, interval) -> DataFrame
    def fundamentals(symbol) -> dict
    def news(region, query) -> list

PROVIDERS = {
  "US":    YFinanceProvider(),
  "WORLD": YFinanceProvider(),
  "IN":    YFinanceProvider(),     # + your F/O files later
  "CRYPTO": BinanceProvider(),     # bStocks (TSLAB/USDT...) + crypto, 24/7
}
```
Frontend asks `GET /bars?region=US&symbol=SPY`. Add a market = add a provider. Zero UI change.
`BinanceProvider` uses Binance's free public REST + websocket API — real-time, no cost.

## 5. FIRST WIN — Global Momentum Screener (the radar)

The thing you open daily. "What's winning worldwide right now?"

For a basket of global ETFs (start ~30: SPY, QQQ, VTI, VXUS, VWO, EFA, GLD, TLT,
sector + country ETFs):
- Compute **1mo / 3mo / 6mo / 12mo returns**.
- Flag **above / below 200-day MA** (trend filter).
- Rank, color-code, sortable table + sparkline per row.
- "Momentum score" = blend of returns, trend-confirmed.

Output: a ranked board of what's hot, trend-confirmed, across world markets.
This single page seeds Screener + AlgoTrading + Portfolio.

## 5.5 Gap Radar — the unique edge (Binance bStocks)

Binance launched **bStocks** (tokenized US stocks, 24/7) on 2026-06-11. Tickers:
TSLAB, NVDAB, MUB, CRCLB, SNDKB (vs USDT). They trade while NYSE/Nasdaq are CLOSED.

The signal: token moves overnight/weekend → forecasts the US cash open.

```
implied_open_pct = (bStock_price_now / last_US_close - 1) * 100
# e.g. TSLAB -4.1%  →  Tesla likely opens ~4% down
```

Page does:
- Stream bStock prices 24/7 from Binance free API (REST + websocket).
- Show each: last US close, live token price, **implied open %**, volume.
- **Alert** on big overnight/weekend moves before US opens.
- The unique window = **weekends + deep night**, when pre-market/futures are dark.

Honest guardrails (keep it real, not blind):
- Token can trade at premium/discount when liquidity thin → implied % is a forecast, not a promise.
- Filter by volume; ignore thin-book spikes.
- **Backtest it**: does overnight token move actually predict the open? Measure hit-rate + avg error before trusting. (Brand new data — validate, don't assume.)

Two money angles: (a) **predictive** — position in US pre-market/options ahead of the gap; (b) **arbitrage** — fade token-vs-share divergence during overlap hours.

## 5.6 Signals Engine — the edges board (the core product)

One module scans every high-probability edge and ranks today's opportunities.
Each signal scored by: **probability, freshness, conviction, data source.**

Ranked by money-probability × buildability (honest — edges decay, freshness noted):

| Signal | Edge | Prob | Decay | Data (free?) |
|---|---|---|---|---|
| **Tokenized overnight gap** 🌙 | Token move → US open gap | High | Low (new!) | Binance/Kraken API ✅ |
| **Index futures gap** | /ES /NQ → index open | High | Low | yfinance/free ✅ |
| **ADR gap** | US ADR → home-mkt open | High | Low | yfinance ✅ |
| **Index rebalancing front-run** | Stock added to S&P → pre-pop | High | Med | index announce dates ✅ |
| **Post-earnings drift (PEAD)** | Surprise → weeks of drift | High | Low | earnings + price ✅ |
| **Overnight drift** | Returns happen overnight | High | Low | OHLC ✅ |
| **Momentum / trend** | Winners keep winning | High | Med | yfinance ✅ |
| **Insider buying clusters** | Form 4 cluster = bullish | Med | Low | SEC EDGAR ✅ |
| **IPO lockup expiry** | Forced selling, dated | Med | Low | IPO calendars ✅ |
| **Sector rotation** | Ride leading sector | Med | Med | sector ETFs ✅ |
| **Cross-asset lead** | Oil→energy, copper→industrials | Med | Med | yfinance ✅ |
| **BTC weekend sentiment** | Risk-on/off for Monday | Low | — | Binance ✅ |
| **Seasonality / turn-of-month** | Calendar flows | Low | Med | dates ✅ |

Output: a daily **Edges Board** — "Today's highest-conviction setups," each with the
signal, direction, strength, and the honest backtested hit-rate next to it. Click →
chart + fundamentals + news for that name. Every signal gets validated by the
backtest engine before it's trusted (no signal ships on faith).

## 5.7 Where AlgoSign stands — the gap (our moat)

The market gap we exploit:

- **TradingView / Bloomberg** = charts + data, but **you** hunt the edges manually.
- **Screeners** = filter on metrics, but no overnight/structural/cross-venue signals.
- **Tokenized-equity overnight signals are 2 DAYS OLD** (bStocks 2026-06-11). Almost
  no retail tool watches them yet. **First-mover window is open right now.**
- Nobody aggregates **tokenized gaps + futures + ADRs + earnings-drift + calendar
  edges** into one ranked board for global retail.

**Our stand**: AlgoSign = the **pre-market edges radar for global retail.** It tells
you *what's about to move and why*, before the open, across every market — then
backtests every claim so you trust it. That's the niche no one owns yet.

## 6. Build plan

- **M0 Scaffold** — Next.js + FastAPI talking. Region switcher. 5 stub pages + Portfolio. Health green.
- **M1 Screener (FIRST WIN)** — data layer + yfinance + momentum/trend ranking endpoint + the radar table UI.
- **M1.5 Gap Radar** — `BinanceProvider` + bStocks feed + implied-open calc + alerts. Fast, novel, free data. (First signal in the Edges Board.)
- **M2 AlgoTrading + backtest core** — engine that validates ANY signal. Dual-momentum/trend backtest, equity curve vs buy-and-hold, drawdown, hit-rate. Plus: does the gap signal predict the open? (Honest costs baked in.) This engine scores every Signals Engine edge.
- **M2.5 Signals Engine** — add futures gap, ADR gap, PEAD, overnight drift, index-rebalance calendar → the ranked daily Edges Board, each with backtested hit-rate.
- **M3 Portfolio** — enter holdings, track value/allocation/P&L, rebalance alerts.
- **M4 Fundamentals + News** — wire providers, tag catalysts to instruments.
- **M5 ChatBot** — Claude over data + news (RAG-lite). Natural-language screening.
- **M-later** — Indian F/O data behind India provider; options-income module with risk metrics.

## 6b. Pro Dashboard ("everything" upgrade — Perplexity-Finance grade)

Goal: make AlgoSign read like a pro finance terminal. Sequenced.

**Step 1 — Everything sections (free data):**
- Movers: Gainers / Losers / Most-active per region (day % from basket).
- Market sentiment gauge (breadth: % up + % above 200-DMA).
- Watchlist: pin any symbol (localStorage), live quotes, click → detail.
- Sector heatmap: green/red treemap of stocks by sector.
- Prediction markets: real Polymarket odds (free Gamma API).
- Dashboard becomes multi-column: Top Assets + Market Summary (news) + Heatmap (left), Watchlist + Predictions + Movers + Sentiment (right rail).
- Stock detail enrich: news (Stories), peers, prediction markets.

**Step 2 — Polish pass:** finance-grade type/density, dividers, hover, logos.

**Step 3 — AI brain:** "Ask anything" chat + AI market summary + news digest.
Needs ONE key: ANTHROPIC_API_KEY (Claude, recommended) or OPENAI_API_KEY, in
backend/.env. Steps 1-2 need no key.

## 7. How the pages compound

Screener (find winners) → Fundamentals (verify real) → News (catch catalyst) →
AlgoTrading (backtest + signal) → Portfolio (act + track) → ChatBot (ask it all).
One dashboard, the full loop.

## 8. Realism guardrails (kept, not preached)

Honest backtests: time-split, walk-forward, real costs, no lookahead, beat buy-and-hold.
v1 = signals only, you act manually. Reuse libraries. These keep the upside real.

## 9. Build Spec (sharpened — concrete decisions for coding)

### 9.1 Repo layout (monorepo)
```
algosign/
  frontend/              Next.js (App Router, TS, Tailwind)
    app/                 pages: screener, gap-radar, algo, portfolio, news, chat
    components/          charts, tables, region-switcher
    lib/api.ts           typed client for backend
  backend/               FastAPI
    main.py              app + routes
    providers/           yfinance.py, binance.py, base.py (Protocol)
    signals/             momentum.py, gap.py, overnight.py, pead.py
    backtest/            engine.py, costs.py, walkforward.py
    cache/               parquet read/write helpers
  data/                  parquet cache + sqlite (watchlist/portfolio)
  docker-compose.yml     run both with one command
```

### 9.2 API contract (v1 — frozen for MVP)
```
GET  /health                                  -> {status}
GET  /bars?region&symbol&interval&start&end   -> [{t,o,h,l,c,v}]
GET  /screener/momentum?region&basket         -> [{symbol,score,r1,r3,r6,r12,above200dma}]
GET  /gap-radar                               -> [{symbol,token,last_close,implied_open_pct,vol}]
# later: /signals  /fundamentals  /news  POST /chat
```
Frontend is dumb: calls these, renders tables/charts. All logic in Python.

### 9.3 Signal formulas (precise — no ambiguity)
- **Momentum score** = `0.5·z(r6) + 0.3·z(r3) + 0.2·z(r12)`, z-scored across the basket. Returns = total return over 3/6/12 months. **Buy-eligible only if `price > 200-day MA`** (trend filter). Rank desc.
- **Gap signal** = `implied_open_pct = (token_price / last_us_close − 1) · 100`. Surface only when `|implied_open_pct| ≥ 1.5%` AND `token_24h_volume ≥ min_vol`. Cross-check Binance vs Kraken token; flag divergence.
- **Overnight drift** = `close[t] → open[t+1]` return series; signal = rolling mean > 0 sustained.
- **PEAD** = on earnings date, sign of surprise (actual−estimate); hold direction N days; measure drift.

### 9.4 Backtest methodology (frozen)
- **Walk-forward**: train window ≥ 2y, test on next 1–3mo, roll forward. Never random split.
- **Rebalance**: monthly for momentum, daily check for gap/trend.
- **Costs**: equities/ETFs commission $0 + **slippage 5 bps/side**; tokenized 10 bps (wider). Subtract every trade.
- **Benchmark**: must beat buy-and-hold (SPY) AND random-entry baseline.
- **Metrics reported**: CAGR, Sharpe, max drawdown, hit-rate, avg win/loss, turnover.

### 9.5 Default radar basket (~28, region-tagged)
```
US broad:   SPY QQQ VTI IWM DIA
Sectors:    XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
Country/Wld:VXUS EFA VWO INDA(India) FXI(China) EWJ(Japan) EWG(Germany) EWU(UK) EWZ(Brazil)
Assets:     GLD SLV TLT USO BITO
```
Editable in `backend/signals/baskets.py`. This is the M1 universe.

### 9.6 Tech specifics
- **Data**: `yfinance` for OHLC/fundamentals; cache to parquet, refresh daily (cron/manual). Binance public REST (`/api/v3/ticker/24hr`) for bStocks — no account needed for market data.
- **Charts**: `lightweight-charts` (TradingView, free).
- **Store**: parquet cache + SQLite (watchlist/portfolio). No Postgres until needed.
- **LLM**: Claude `claude-sonnet-4-6` for ChatBot (later milestone).
- **Run**: `docker-compose up` → frontend:3000, backend:8000. Local first; deploy later (Vercel + Render/Fly).

### 9.7 Risk / legal notes (personal use)
- Tokenized equities (bStocks/xStocks) are **geo-restricted** — we read only *public market data*, no trading through the app. Signals are informational.
- Respect API rate limits → cache aggressively.
- Not financial advice. v1 = signals only, you act manually (premise P3).

### 9.8 MVP-1 cut line (the first build target)
**In**: M0 scaffold + M1 momentum screener (real yfinance data) + M1.5 Gap Radar (bStocks implied-open). Region switcher. Health check.
**Stubbed**: AlgoTrading, Portfolio, Fundamentals, News, ChatBot (empty pages with "coming soon").
**Done =** you open localhost, see a ranked global momentum board + a live tokenized-gap board, on real data. That's the shippable first slice.

## 10. The Assignment

1. Confirm local tooling: `node -v`, `python3 --version`, `docker --version`.
2. Veto/approve the default basket (§9.5) or hand me your own list.
3. Comfortable with React/TypeScript, or want frontend hand-holding?

Then say **"build it"** → we scaffold M0, then go straight to the momentum screener.
