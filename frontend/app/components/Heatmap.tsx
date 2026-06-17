"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type HeatSector } from "../lib/api";

function tile(change: number): string {
  // Theme-aware intensity: stronger move = more saturated.
  const v = Math.min(Math.abs(change) * 22 + 14, 80);
  const c = change >= 0 ? "var(--color-forest)" : "var(--color-brick)";
  return `color-mix(in srgb, ${c} ${v}%, transparent)`;
}

export default function Heatmap({ region }: { region: string }) {
  const [sectors, setSectors] = useState<HeatSector[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .heatmap(region)
      .then((d) => !cancelled && setSectors(d.sectors))
      .catch(() => !cancelled && setSectors([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [region]);

  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="mb-3 text-sm font-semibold text-ink">Sector heatmap</div>
      {loading && sectors.length === 0 ? (
        <div className="h-40 animate-pulse rounded-lg bg-mist/50" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sectors.map((s) => (
            <div key={s.sector} className="rounded-lg border border-line p-2">
              <div className="mb-1.5 flex items-baseline justify-between px-1">
                <span className="text-xs font-semibold text-ink">{s.sector}</span>
                <span
                  className={`font-mono text-xs ${s.avg_change >= 0 ? "text-forest" : "text-brick"}`}
                >
                  {s.avg_change >= 0 ? "+" : ""}
                  {s.avg_change}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-1">
                {s.stocks.map((st) => (
                  <Link
                    key={st.symbol}
                    href={`/stock/${encodeURIComponent(st.symbol)}`}
                    className="rounded px-2 py-1.5 transition hover:opacity-80"
                    style={{ backgroundColor: tile(st.change_pct) }}
                    title={st.name}
                  >
                    <div className="truncate font-mono text-[11px] font-medium text-ink">
                      {st.symbol.replace(".NS", "").replace("-USD", "")}
                    </div>
                    <div className="font-mono text-[10px] text-ink/80">
                      {st.change_pct >= 0 ? "+" : ""}
                      {st.change_pct}%
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
