# AlgoSign

Worldwide market radar — pre-market edges for global retail. Spot what's about to
move and why, before the open, across every market. See `DESIGN.md` for the full plan.

**MVP-1 shipped:** Momentum Screener + Gap Radar (Binance bStocks → implied US open),
on live free data. Other pages are stubs (see milestones in `DESIGN.md`).

## Stack
- **Frontend:** Next.js 16 (App Router, TypeScript, Tailwind) — `frontend/`
- **Backend:** FastAPI + pandas — `backend/`
- **Data:** Yahoo chart API (free, no key) for OHLCV; Binance public API for bStocks.

## Run (two terminals)

**Backend** (port 8000):
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # first time
.venv/bin/uvicorn main:app --reload --port 8000
```

**Frontend** (port 3000):
```bash
cd frontend
npm install        # first time
npm run dev
```

Open http://localhost:3000.

## API
| Endpoint | What |
|---|---|
| `GET /health` | liveness |
| `GET /bars?symbol=SPY&period=2y&interval=1d` | OHLCV bars |
| `GET /screener/momentum?region=ALL` | momentum-ranked basket (ALL/US/WORLD/ASSETS) |
| `GET /gap-radar` | tokenized bStock implied-open signals |

## Layout
```
backend/   FastAPI: providers/ (yahoo, binance), signals/ (momentum, gap, baskets)
frontend/  Next.js: app/ (screener, gap-radar, + stubs), components/, lib/api.ts
data/      parquet cache (gitignored)
DESIGN.md  full product + build plan
```

## Known TODOs (next session)
- Verify bStock→underlying symbol map (SNDK/MU last-close values look off — `backend/providers/binance_provider.py`).
- M2: backtest engine to validate every signal (walk-forward, real costs).
- Charts on screener rows (`lightweight-charts`).

> Signals are informational, not financial advice. v1 = no auto-execution.
