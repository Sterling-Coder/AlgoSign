"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type OverviewCard } from "../lib/api";

function Sparkline({ data, up }: { data: number[]; up: boolean }) {
  if (data.length < 2) return null;
  const w = 240;
  const h = 48;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const color = up ? "var(--color-forest)" : "var(--color-brick)";
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      className="h-12 w-full"
    >
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

export function TopAssets({ region }: { region: string }) {
  const [cards, setCards] = useState<OverviewCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .overview(region)
      .then((d) => !cancelled && setCards(d.cards))
      .catch(() => !cancelled && setCards([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [region]);

  if (loading && cards.length === 0)
    return <div className="mb-8 h-32 animate-pulse rounded-xl bg-mist/50" />;

  return (
    <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => {
        const up = c.change_pct >= 0;
        return (
          <Link
            key={c.symbol}
            href={`/stock/${encodeURIComponent(c.symbol)}`}
            className="rounded-xl border border-line bg-paper p-4 transition-all hover:border-forest/40 hover:shadow-sm"
          >
            <div className="flex items-baseline justify-between">
              <div className="text-sm font-semibold text-ink">{c.label}</div>
              <div
                className={`text-xs font-medium ${up ? "text-forest" : "text-brick"}`}
              >
                {up ? "▲" : "▼"} {Math.abs(c.change_pct).toFixed(2)}%
              </div>
            </div>
            <div className="mt-1 font-mono text-xl font-bold text-ink">
              {c.last.toLocaleString()}
            </div>
            <div className={`text-xs ${up ? "text-forest" : "text-brick"}`}>
              {up ? "+" : ""}
              {c.change.toLocaleString()}
            </div>
            <div className="mt-2">
              <Sparkline data={c.spark} up={up} />
            </div>
          </Link>
        );
      })}
    </div>
  );
}
