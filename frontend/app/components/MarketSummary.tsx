"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type NewsItem } from "../lib/api";

export default function MarketSummary({ region }: { region: string }) {
  const [items, setItems] = useState<NewsItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    api
      .news(region)
      .then((d) => !cancelled && setItems(d.items.slice(0, 6)))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [region]);

  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-ink">Market summary</span>
        <Link href="/news" className="text-xs text-forest hover:underline">
          all news →
        </Link>
      </div>
      <div className="divide-y divide-line">
        {items.map((n, i) => (
          <a
            key={i}
            href={n.link}
            target="_blank"
            rel="noopener noreferrer"
            className="block py-2 hover:opacity-70"
          >
            <p className="text-sm text-ink">{n.title}</p>
            <p className="mt-0.5 text-xs text-sage">
              {n.source}
              {n.source && n.ago ? " · " : ""}
              {n.ago}
            </p>
          </a>
        ))}
      </div>
    </div>
  );
}
