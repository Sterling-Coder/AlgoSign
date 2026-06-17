"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type MarketSnapshot, type Prediction, type Mover } from "../lib/api";
import Watchlist from "./Watchlist";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="mb-3 text-sm font-semibold text-ink">{title}</div>
      {children}
    </div>
  );
}

function MoverRow({ m }: { m: Mover }) {
  const up = m.change_pct >= 0;
  return (
    <Link
      href={`/stock/${encodeURIComponent(m.symbol)}`}
      className="flex items-center justify-between py-1.5 hover:opacity-70"
    >
      <div className="min-w-0">
        <div className="truncate font-mono text-sm text-ink">{m.symbol}</div>
        <div className="truncate text-xs text-sage">{m.name}</div>
      </div>
      <div className={`shrink-0 font-mono text-sm ${up ? "text-forest" : "text-brick"}`}>
        {up ? "+" : ""}
        {m.change_pct}%
      </div>
    </Link>
  );
}

export default function RightRail({ region }: { region: string }) {
  const [snap, setSnap] = useState<MarketSnapshot | null>(null);
  const [preds, setPreds] = useState<Prediction[]>([]);
  const [tab, setTab] = useState<"gainers" | "losers" | "active">("gainers");

  useEffect(() => {
    let cancelled = false;
    api.market(region).then((d) => !cancelled && setSnap(d)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [region]);

  useEffect(() => {
    let cancelled = false;
    api.predictions().then((d) => !cancelled && setPreds(d.markets)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const s = snap?.sentiment;
  const rows = snap ? snap[tab] : [];

  return (
    <div className="space-y-4">
      <Watchlist />

      <Card title="Market sentiment">
        {s ? (
          <div>
            <div className="flex items-baseline justify-between">
              <span
                className={`text-lg font-bold ${
                  s.label === "Bullish"
                    ? "text-forest"
                    : s.label === "Bearish"
                      ? "text-brick"
                      : "text-ink"
                }`}
              >
                {s.label}
              </span>
              <span className="font-mono text-sm text-sage">{s.score}/100</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-mist">
              <div
                className="h-full rounded-full bg-forest"
                style={{ width: `${s.score}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-sage">
              {s.pct_up}% rising · {s.pct_above_200dma}% in uptrend
            </div>
          </div>
        ) : (
          <div className="text-sm text-sage">…</div>
        )}
      </Card>

      <Card title="Movers">
        <div className="mb-2 flex gap-1 text-xs">
          {(["gainers", "losers", "active"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-2 py-1 capitalize transition ${
                tab === t ? "bg-forest-soft font-medium text-forest" : "text-sage hover:text-ink"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="divide-y divide-line">
          {rows.length ? rows.map((m) => <MoverRow key={m.symbol} m={m} />) : (
            <div className="py-2 text-sm text-sage">…</div>
          )}
        </div>
      </Card>

      {/* Only render when there are markets carrying real signal; else hide. */}
      {preds.length > 0 && (
        <Card title="Prediction markets">
          <div className="space-y-3">
            {preds.map((p, i) => (
              <div key={i} className="border-b border-line pb-3 last:border-0 last:pb-0">
                <div className="mb-1.5 text-sm text-ink">{p.question}</div>
                {p.outcomes.map((o, j) => (
                  <div key={j} className="flex justify-between text-xs">
                    <span className="text-sage">{o.label}</span>
                    <span className="font-mono font-medium text-ink">{o.pct}%</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="mt-2 text-right text-[10px] text-sage">via Polymarket</div>
        </Card>
      )}
    </div>
  );
}
