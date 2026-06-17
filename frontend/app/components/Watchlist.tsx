"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type Mover } from "../lib/api";
import { getWatchlist, onWatchlistChange, removeWatch } from "../lib/watchlist";

export function StarButton({ symbol }: { symbol: string }) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    import("../lib/watchlist").then((m) => setOn(m.isWatched(symbol)));
  }, [symbol]);
  return (
    <button
      onClick={() =>
        import("../lib/watchlist").then((m) => setOn(m.toggleWatch(symbol)))
      }
      className={`rounded-md border px-3 py-1.5 text-sm transition ${
        on
          ? "border-forest bg-forest-soft text-forest"
          : "border-line text-sage hover:text-ink"
      }`}
      title={on ? "Remove from watchlist" : "Add to watchlist"}
    >
      {on ? "★ Watching" : "☆ Watch"}
    </button>
  );
}

export default function Watchlist() {
  const [quotes, setQuotes] = useState<Mover[]>([]);
  const [empty, setEmpty] = useState(false);

  const load = useCallback(() => {
    const syms = getWatchlist();
    if (syms.length === 0) {
      setQuotes([]);
      setEmpty(true);
      return;
    }
    setEmpty(false);
    api.quotes(syms).then((d) => setQuotes(d.quotes)).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    return onWatchlistChange(load);
  }, [load]);

  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="mb-3 text-sm font-semibold text-ink">Watchlist</div>
      {empty ? (
        <div className="text-sm text-sage">
          Search a stock and tap ☆ Watch to pin it here.
        </div>
      ) : (
        <div className="divide-y divide-line">
          {quotes.map((q) => {
            const up = q.change_pct >= 0;
            return (
              <div key={q.symbol} className="flex items-center justify-between py-1.5">
                <Link
                  href={`/stock/${encodeURIComponent(q.symbol)}`}
                  className="min-w-0 hover:opacity-70"
                >
                  <div className="truncate font-mono text-sm text-ink">{q.symbol}</div>
                  <div className="truncate text-xs text-sage">{q.name}</div>
                </Link>
                <div className="flex items-center gap-2">
                  <span className={`font-mono text-sm ${up ? "text-forest" : "text-brick"}`}>
                    {up ? "+" : ""}
                    {q.change_pct}%
                  </span>
                  <button
                    onClick={() => removeWatch(q.symbol)}
                    className="text-sage hover:text-brick"
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
