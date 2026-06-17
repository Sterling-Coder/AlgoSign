const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type MomentumRow = {
  rank: number;
  symbol: string;
  price: number;
  r1: number | null;
  r3: number | null;
  r6: number | null;
  r12: number | null;
  above_200dma: boolean;
  score: number;
};

export type SearchHit = {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
};

export type StockDetail = {
  symbol: string;
  name: string;
  last: number;
  change: number;
  change_pct: number;
  r1: number | null;
  r3: number | null;
  r6: number | null;
  r12: number | null;
  above_200dma: boolean;
  ma200: number | null;
  high52: number;
  low52: number;
  verdict: { action: string; reason: string };
  watch: string[];
  us_fundamentals?: {
    source: string;
    groups: { title: string; items: { label: string; value: string }[] }[];
  } | null;
  fundamentals?: {
    currency: string;
    metrics: { label: string; value: string }[];
    recommendation?: string;
    statements?: Record<
      string,
      { periods: string[]; rows: { label: string; values: string[] }[] }
    >;
  } | null;
  news?: NewsItem[];
  gap?: { token: string; token_price: number; implied_open_pct: number } | null;
  series: { t: string; c: number }[];
};

export type Candle = { t: string; o: number; h: number; l: number; c: number };
export type Zone = { type: "bull" | "bear"; t: string; top: number; bottom: number };
export type StructureEvt = {
  type: "BOS" | "CHoCH";
  dir: "bull" | "bear";
  t: string;
  price: number;
};
export type SmcSignal = { side: "BUY" | "SELL"; t: string; price: number; why: string };
export type SmcData = {
  symbol: string;
  name: string;
  trend: "up" | "down" | "flat";
  candles: Candle[];
  order_blocks: Zone[];
  fvgs: Zone[];
  structure: StructureEvt[];
  signals: SmcSignal[];
};

export type Mover = { symbol: string; name: string; last: number; change_pct: number };

export type Sentiment = {
  label: string;
  score: number;
  pct_up: number;
  pct_above_200dma: number;
  count: number;
};

export type MarketSnapshot = {
  region: string;
  gainers: Mover[];
  losers: Mover[];
  active: Mover[];
  sentiment: Sentiment | null;
};

export type Prediction = {
  question: string;
  outcomes: { label: string; pct: number }[];
  volume: number;
};

export type HorizonCall = {
  horizon: number;
  direction: "UP" | "DOWN";
  probability: number;
  hist_hitrate: number;
  avg_fwd_pct: number;
  sample_size: number;
};

export type Forecast = {
  available: boolean;
  symbol: string;
  name?: string;
  basis?: string;
  confidence?: "high" | "medium" | "low";
  headline?: HorizonCall;
  horizons?: HorizonCall[];
  disclaimer?: string;
};

export type Alert = {
  id: number;
  symbol: string;
  kind: "price" | "pct_change";
  direction: "above" | "below";
  threshold: number;
  note: string | null;
  active: boolean;
  created_at: string;
  last_fired_at: string | null;
  last_value: number | null;
};

export type AlertEvent = {
  type: "alert";
  id: number;
  symbol: string;
  kind: "price" | "pct_change";
  direction: "above" | "below";
  threshold: number;
  value: number;
  note: string | null;
};

export type Position = {
  id: number;
  symbol: string;
  side: "long" | "short";
  qty: number;
  entry_price: number;
  stop: number | null;
  target: number | null;
  status: "open" | "closed" | "halted";
  opened_at: string;
  closed_at: string | null;
  exit_price: number | null;
  pnl: number | null;
  current_price?: number;
  unrealized_pnl?: number;
};

export type BotsState = {
  real_money: boolean;
  positions: Position[];
  realized_pnl: number;
  unrealized_pnl: number;
  open_count: number;
};

export type FillEvent = {
  type: "fill";
  id: number;
  symbol: string;
  side: "long" | "short";
  qty: number;
  exit_price: number;
  pnl: number;
  reason: "target" | "stop" | "manual";
};

export type OptionRow = {
  strike: number;
  last: number | null;
  bid: number | null;
  ask: number | null;
  volume: number;
  open_interest: number;
  iv: number | null;
  itm: boolean;
};

export type OptionExp = { ts: number; date: string };

export type OptionChain = {
  available: boolean;
  symbol: string;
  underlying?: number;
  expiration?: number;
  expirations?: OptionExp[];
  calls?: OptionRow[];
  puts?: OptionRow[];
};

export type HeatSector = {
  sector: string;
  avg_change: number;
  stocks: Mover[];
};

export type NewsItem = {
  title: string;
  source: string;
  link: string;
  ago: string;
};

export type OverviewCard = {
  symbol: string;
  label: string;
  last: number;
  change: number;
  change_pct: number;
  spark: number[];
};

export type ActionRow = {
  action: "BUY" | "REDUCE" | "WATCH";
  symbol: string;
  name: string;
  reason: string;
  confidence: "high" | "medium" | "low";
  source: "momentum" | "gap";
};

export type GapRow = {
  token: string;
  underlying: string;
  available: boolean;
  token_price: number | null;
  last_close: number | null;
  implied_open_pct: number | null;
  volume: number | null;
  actionable: boolean;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    credentials: "include", // carry the signed device cookie
  });
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include", // carry the signed device cookie
  });
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error(`API ${res.status} on ${path}`);
  return res.json() as Promise<T>;
}

export const STREAM_URL = `${BASE}/stream`;

export const api = {
  momentum: (region: string) =>
    get<{ region: string; count: number; results: MomentumRow[] }>(
      `/screener/momentum?region=${region}`
    ),
  gapRadar: () => get<{ signals: GapRow[] }>(`/gap-radar`),
  overview: (region: string) =>
    get<{ region: string; cards: OverviewCard[] }>(`/overview?region=${region}`),
  actions: (region: string) =>
    get<{ region: string; actions: ActionRow[] }>(`/actions?region=${region}`),
  news: (region: string) =>
    get<{ region: string; items: NewsItem[] }>(`/news?region=${region}`),
  newsBrief: (region: string) =>
    get<{
      configured: boolean;
      summary?: string;
      themes?: { title: string; detail: string }[];
    }>(`/news-brief?region=${region}`),
  market: (region: string) => get<MarketSnapshot>(`/market?region=${region}`),
  heatmap: (region: string) =>
    get<{ region: string; sectors: HeatSector[] }>(`/heatmap?region=${region}`),
  quotes: (symbols: string[]) =>
    get<{ quotes: Mover[] }>(`/quotes?symbols=${encodeURIComponent(symbols.join(","))}`),
  predictions: () => get<{ markets: Prediction[] }>(`/predictions`),
  predict: (symbol: string) =>
    get<Forecast>(`/predict?symbol=${encodeURIComponent(symbol)}`),
  options: (symbol: string, expiration?: number) =>
    get<OptionChain>(
      `/options?symbol=${encodeURIComponent(symbol)}` +
        (expiration ? `&expiration=${expiration}` : "")
    ),
  bots: () => get<BotsState>(`/bots`),
  openBot: (body: {
    symbol: string;
    side: "long" | "short";
    qty: number;
    stop?: number;
    target?: number;
  }) => post<{ position: Position }>(`/bots`, body),
  closeBot: (id: number) => post<{ position: Position }>(`/bots/${id}/close`, {}),
  alerts: () => get<{ alerts: Alert[] }>(`/alerts`),
  createAlert: (body: {
    symbol: string;
    kind: "price" | "pct_change";
    direction: "above" | "below";
    threshold: number;
    note?: string;
  }) => post<{ alert: Alert }>(`/alerts`, body),
  deleteAlert: (id: number) => del<{ deleted: boolean }>(`/alerts/${id}`),
  search: (q: string) =>
    get<{ query: string; results: SearchHit[] }>(`/search?q=${encodeURIComponent(q)}`),
  stock: (symbol: string) =>
    get<StockDetail>(`/stock?symbol=${encodeURIComponent(symbol)}`),
  smc: (symbol: string, period = "1y", interval = "1d") =>
    get<SmcData>(
      `/smc?symbol=${encodeURIComponent(symbol)}&period=${period}&interval=${interval}`
    ),
  indiaFundamentals: (symbol: string) =>
    get<{
      available: boolean;
      name?: string;
      ratios?: { label: string; value: string }[];
      pros?: string[];
      cons?: string[];
      quarterly_sales?: { q: string; v: string }[];
      promoter_holding?: string | null;
      about?: string;
      statements?: Record<
        string,
        { periods: string[]; rows: { label: string; values: string[] }[] }
      >;
      documents?: Record<
        string,
        { label: string; url: string; date: string }[]
      >;
    }>(`/india-fundamentals?symbol=${encodeURIComponent(symbol)}`),
  chat: (message: string, region: string) =>
    post<{ configured: boolean; reply: string }>(`/chat`, { message, region }),
  council: (symbol: string) =>
    get<{
      configured: boolean;
      error?: string;
      agents?: { role: string; stance: string; confidence: string; take: string }[];
      verdict?: { call: string; confidence: string; reason: string };
    }>(`/council?symbol=${encodeURIComponent(symbol)}`),
  health: () => get<{ status: string }>(`/health`),
};
