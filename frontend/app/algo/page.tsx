"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type SmcData } from "../lib/api";
import { PageHead } from "../components/ui";
import SMCChart from "../components/SMCChart";
import SymbolAutocomplete from "../components/SymbolAutocomplete";
import { useRegion } from "../components/RegionContext";

const DEFAULTS: Record<string, string> = {
  IN: "RELIANCE.NS",
  US: "AAPL",
  WORLD: "AAPL",
};
const TIMEFRAMES = [
  { key: "15m", label: "15m", interval: "15m", period: "1mo" },
  { key: "1h", label: "1H", interval: "1h", period: "3mo" },
  { key: "1d", label: "1D", interval: "1d", period: "1y" },
  { key: "1wk", label: "1W", interval: "1wk", period: "5y" },
];

export default function AlgoPage() {
  const { region } = useRegion();
  const [symbol, setSymbol] = useState(DEFAULTS[region] || "AAPL");
  const [tf, setTf] = useState("1d");
  const [data, setData] = useState<SmcData | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback((sym: string, tfKey: string) => {
    const t = TIMEFRAMES.find((x) => x.key === tfKey) || TIMEFRAMES[2];
    setLoading(true);
    setErr(null);
    api
      .smc(sym, t.period, t.interval)
      .then((d) => {
        if ("error" in (d as object)) setErr(`No data for ${sym}`);
        else setData(d as SmcData);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(symbol, tf);
  }, [symbol, tf, load]);

  return (
    <div>
      <PageHead
        title="AlgoTrading — Smart Money Concepts"
        sub="Order blocks, fair value gaps, structure (BOS/CHoCH) and buy/sell signals — auto-detected from price."
      >
        <div className="flex gap-1 rounded-lg border border-line bg-paper p-1">
          {TIMEFRAMES.map((t) => (
            <button
              key={t.key}
              onClick={() => setTf(t.key)}
              className={`rounded-md px-3 py-1 text-sm transition ${
                tf === t.key ? "bg-forest-soft font-semibold text-forest" : "text-sage hover:text-ink"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </PageHead>

      <div className="mb-4">
        <SymbolAutocomplete
          initial={symbol}
          placeholder="Search a stock to analyze… (e.g. Reliance, AAPL, Nifty)"
          onSelect={(sym) => setSymbol(sym)}
        />
      </div>

      {err && (
        <div className="mb-4 rounded-lg border border-brick/30 bg-brick/5 p-4 text-sm text-brick">
          {err}
        </div>
      )}

      {loading || !data ? (
        <p className="text-sage">Analyzing structure…</p>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <span className="font-mono text-lg font-bold text-ink">{data.symbol}</span>
            <span className="text-sage">{data.name}</span>
            <span
              className={`rounded-full px-3 py-1 text-sm font-medium ${
                data.trend === "up"
                  ? "bg-forest-soft text-forest"
                  : data.trend === "down"
                    ? "bg-brick/10 text-brick"
                    : "bg-mist text-sage"
              }`}
            >
              trend: {data.trend}
            </span>
            <div className="ml-auto flex items-center gap-3 text-xs text-sage">
              <Legend color="var(--color-forest)" label="Bull OB / FVG / Buy" />
              <Legend color="var(--color-brick)" label="Bear OB / FVG / Sell" />
            </div>
          </div>

          <div className="rounded-xl border border-line bg-paper p-3">
            <SMCChart data={data} />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel title="Signals">
              {data.signals.length === 0 ? (
                <Empty>No recent signals.</Empty>
              ) : (
                [...data.signals].reverse().map((s, i) => (
                  <div key={i} className="flex items-center gap-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-bold text-white ${
                        s.side === "BUY" ? "bg-forest" : "bg-brick"
                      }`}
                    >
                      {s.side}
                    </span>
                    <span className="font-mono text-sm text-ink">{s.price}</span>
                    <span className="text-xs text-sage">{s.t}</span>
                    <span className="ml-auto text-xs text-ink/70">{s.why}</span>
                  </div>
                ))
              )}
            </Panel>

            <Panel title="Market structure">
              {data.structure.length === 0 ? (
                <Empty>No structure breaks yet.</Empty>
              ) : (
                [...data.structure].reverse().map((s, i) => (
                  <div key={i} className="flex items-center gap-3 py-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        s.dir === "bull" ? "bg-forest-soft text-forest" : "bg-brick/10 text-brick"
                      }`}
                    >
                      {s.type}
                    </span>
                    <span className="text-xs text-sage">{s.dir}</span>
                    <span className="font-mono text-sm text-ink">{s.price}</span>
                    <span className="ml-auto text-xs text-sage">{s.t}</span>
                  </div>
                ))
              )}
            </Panel>
          </div>

          <p className="mt-4 text-xs text-sage">
            SMC patterns auto-detected from OHLC. Informational, not advice. Backtested
            hit-rates come with the M2 engine — that&apos;s our edge over chart-only tools.
          </p>
        </>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="mb-1 text-sm font-semibold text-ink">{title}</div>
      <div className="divide-y divide-line">{children}</div>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <div className="py-3 text-sm text-sage">{children}</div>;
}
