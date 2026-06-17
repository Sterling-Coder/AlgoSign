"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type SearchHit } from "../lib/api";

export default function SearchBar() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (q.trim().length < 1) {
      setHits([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      api
        .search(q.trim())
        .then((d) => !cancelled && (setHits(d.results), setOpen(true)))
        .catch(() => !cancelled && setHits([]));
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function go(symbol: string) {
    setOpen(false);
    setQ("");
    router.push(`/stock/${encodeURIComponent(symbol)}`);
  }

  return (
    <div ref={boxRef} className="relative w-full max-w-xl">
      <div className="flex items-center gap-2 rounded-lg border border-line bg-paper px-3 py-2">
        <span className="text-sage">⌕</span>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => hits.length && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && hits[0]) go(hits[0].symbol);
          }}
          placeholder="Search a stock, ETF, index… (e.g. TCS, AAPL, Nifty)"
          className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-sage"
        />
      </div>

      {open && hits.length > 0 && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-line bg-paper shadow-lg">
          {hits.map((h) => (
            <button
              key={h.symbol}
              onClick={() => go(h.symbol)}
              className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-mist"
            >
              <div>
                <span className="font-mono text-sm font-semibold text-ink">
                  {h.symbol}
                </span>
                <span className="ml-2 text-xs text-sage">{h.name}</span>
              </div>
              <span className="text-xs text-sage">
                {h.type?.toLowerCase()} · {h.exchange}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
