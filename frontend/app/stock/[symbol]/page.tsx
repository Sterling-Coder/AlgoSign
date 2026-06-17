"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type StockDetail } from "../../lib/api";
import { Pct } from "../../components/ui";
import { StarButton } from "../../components/Watchlist";
import IndiaFundamentals from "../../components/IndiaFundamentals";
import { StatementTabs } from "../../components/Statements";
import AICouncil from "../../components/AICouncil";
import Forecast from "../../components/Forecast";
import Options from "../../components/Options";

const US_STMT_TABS = [
  { key: "income", label: "Income Statement" },
  { key: "balance", label: "Balance Sheet" },
  { key: "cashflow", label: "Cash Flow" },
];

function LineChart({ data, up }: { data: number[]; up: boolean }) {
  if (data.length < 2) return null;
  const w = 800;
  const h = 240;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 16) - 8;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const color = up ? "var(--color-forest)" : "var(--color-brick)";
  const areaPts = `0,${h} ${pts} ${w},${h}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-60 w-full">
      <polygon points={areaPts} fill={color} opacity="0.07" />
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-line bg-paper px-4 py-3">
      <div className="text-xs text-sage">{label}</div>
      <div className="mt-0.5 font-mono text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}

export default function StockPage() {
  const params = useParams();
  const symbol = decodeURIComponent(
    Array.isArray(params.symbol) ? params.symbol[0] : (params.symbol ?? "")
  );
  const [d, setD] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    api
      .stock(symbol)
      .then((res) => {
        if (cancelled) return;
        if ("error" in (res as object)) setErr("Symbol not found");
        else setD(res);
      })
      .catch((e) => !cancelled && setErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
  }, [symbol]);

  if (loading) return <p className="text-sage">Loading {symbol}…</p>;
  if (err || !d)
    return (
      <p className="text-brick">
        {err ?? "No data"} — try searching again (Indian stocks end in .NS).
      </p>
    );

  const up = d.change_pct >= 0;
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-3">
            <h1 className="font-mono text-2xl font-bold text-ink">{d.symbol}</h1>
            <span className="text-sage">{d.name}</span>
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="font-mono text-3xl font-bold text-ink">
              {d.last.toLocaleString()}
            </span>
            <span className={`font-mono ${up ? "text-forest" : "text-brick"}`}>
              {up ? "+" : ""}
              {d.change.toLocaleString()} (<Pct v={d.change_pct} />)
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StarButton symbol={d.symbol} />
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              d.above_200dma ? "bg-forest-soft text-forest" : "bg-mist text-sage"
            }`}
          >
            {d.above_200dma ? "↑ uptrend (above 200-DMA)" : "↓ below 200-DMA"}
          </span>
        </div>
      </div>

      {(() => {
        const a = d.verdict.action;
        const tone =
          a === "ACCUMULATE"
            ? "border-forest/40 bg-forest-soft"
            : a === "REDUCE" || a === "AVOID"
              ? "border-brick/30 bg-brick/5"
              : "border-line bg-mist/40";
        const txt =
          a === "ACCUMULATE"
            ? "text-forest"
            : a === "REDUCE" || a === "AVOID"
              ? "text-brick"
              : "text-ink";
        return (
          <div className={`mb-4 rounded-xl border p-4 ${tone}`}>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-sage">
                AlgoSign view
              </span>
              <span className={`font-bold ${txt}`}>{a}</span>
            </div>
            <p className="mt-1 text-sm text-ink/80">{d.verdict.reason}</p>
          </div>
        );
      })()}

      <Forecast symbol={d.symbol} />

      <div className="mt-4 rounded-xl border border-line bg-paper p-4">
        <LineChart data={d.series.map((p) => p.c)} up={up} />
        <div className="mt-1 text-center text-xs text-sage">last ~6 months</div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <Stat label="1M" value={<Pct v={d.r1} />} />
        <Stat label="3M" value={<Pct v={d.r3} />} />
        <Stat label="6M" value={<Pct v={d.r6} />} />
        <Stat label="12M" value={<Pct v={d.r12} />} />
        <Stat label="52w high" value={d.high52.toLocaleString()} />
        <Stat label="52w low" value={d.low52.toLocaleString()} />
      </div>

      {d.fundamentals && d.fundamentals.metrics.length > 0 && (
        <div className="mt-6">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ink">Fundamentals</h2>
            {d.fundamentals.recommendation && (
              <span className="rounded-full bg-mist px-2 py-0.5 text-xs capitalize text-ink/70">
                analysts: {d.fundamentals.recommendation}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            {d.fundamentals.metrics.map((m) => (
              <div key={m.label} className="rounded-lg border border-line bg-paper px-3 py-2.5">
                <div className="text-xs text-sage">{m.label}</div>
                <div className="mt-0.5 font-mono text-sm font-semibold text-ink">
                  {m.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <AICouncil symbol={d.symbol} />

      {d.us_fundamentals && (
        <div className="mt-6">
          <div className="mb-2 flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ink">Deep fundamentals</h2>
            <span className="rounded-full bg-mist px-2 py-0.5 text-xs text-sage">
              stockanalysis.com
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {d.us_fundamentals.groups.map((g) => (
              <div key={g.title} className="rounded-xl border border-line bg-paper p-4">
                <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-sage">
                  {g.title}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {g.items.map((it) => {
                    const hot = ["ROCE", "ROIC", "ROE"].includes(it.label);
                    return (
                      <div
                        key={it.label}
                        className={`rounded-lg border px-2.5 py-1.5 ${
                          hot ? "border-forest/40 bg-forest-soft" : "border-line"
                        }`}
                      >
                        <div className="text-[10px] text-sage">{it.label}</div>
                        <div className="font-mono text-sm font-semibold text-ink">
                          {it.value}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {d.fundamentals?.statements &&
        (() => {
          const stmts = d.fundamentals!.statements!;
          const tabs = US_STMT_TABS.filter((t) => stmts[t.key]?.rows?.length);
          return tabs.length ? (
            <div className="mt-4">
              <StatementTabs statements={stmts} tabs={tabs} unit="Annual figures" />
            </div>
          ) : null;
        })()}

      {(d.symbol.endsWith(".NS") || d.symbol.endsWith(".BO")) && (
        <IndiaFundamentals symbol={d.symbol} />
      )}

      <Options symbol={d.symbol} />

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-semibold text-ink">What to watch</h2>
          <ul className="space-y-2 rounded-xl border border-line bg-paper p-4">
            {d.watch.map((w, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80">
                <span className="text-forest">•</span>
                {w}
              </li>
            ))}
          </ul>

          {d.gap && (
            <div className="mt-4 rounded-xl border border-forest/40 bg-forest-soft p-4">
              <div className="text-sm font-semibold text-ink">
                🌙 24/7 gap signal ({d.gap.token})
              </div>
              <div className="mt-1 font-mono text-2xl font-bold">
                <Pct v={d.gap.implied_open_pct} />
              </div>
              <div className="text-xs text-sage">
                implied next US open vs last close (token {d.gap.token_price})
              </div>
            </div>
          )}
        </div>

        <div>
          <h2 className="mb-2 text-sm font-semibold text-ink">News &amp; stories</h2>
          {d.news && d.news.length > 0 ? (
            <div className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper">
              {d.news.map((n, i) => (
                <a
                  key={i}
                  href={n.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 hover:bg-mist/60"
                >
                  <p className="text-sm font-medium text-ink">{n.title}</p>
                  <p className="mt-0.5 text-xs text-sage">
                    {n.source}
                    {n.source && n.ago ? " · " : ""}
                    {n.ago}
                  </p>
                </a>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-line bg-paper p-4 text-sm text-sage">
              No recent stories.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
