"use client";

import { useEffect, useRef, useState } from "react";
import { api, type SearchHit } from "../lib/api";

export default function SymbolAutocomplete({
  initial = "",
  placeholder = "Search a stock… (e.g. Reliance, AAPL, Nifty)",
  onSelect,
}: {
  initial?: string;
  placeholder?: string;
  onSelect: (symbol: string, name: string) => void;
}) {
  const [q, setQ] = useState(initial);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
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
        .then((d) => {
          if (cancelled) return;
          setHits(d.results);
          setOpen(true);
          setActive(0);
        })
        .catch(() => !cancelled && setHits([]));
    }, 180);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function pick(h: SearchHit) {
    setQ(h.symbol);
    setOpen(false);
    onSelect(h.symbol, h.name);
  }

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => hits.length && setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, hits.length - 1));
          else if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
          else if (e.key === "Enter" && hits[active]) {
            e.preventDefault();
            pick(hits[active]);
          }
        }}
        placeholder={placeholder}
        className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none placeholder:text-sage focus:border-forest/50"
      />
      {open && hits.length > 0 && (
        <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-line bg-paper shadow-lg">
          {hits.map((h, i) => (
            <button
              key={h.symbol}
              onMouseEnter={() => setActive(i)}
              onClick={() => pick(h)}
              className={`flex w-full items-center justify-between px-3 py-2 text-left ${
                i === active ? "bg-mist" : ""
              }`}
            >
              <div className="min-w-0">
                <span className="font-mono text-sm font-semibold text-ink">{h.symbol}</span>
                <span className="ml-2 text-xs text-sage">{h.name}</span>
              </div>
              <span className="shrink-0 text-xs text-sage">
                {h.type?.toLowerCase()} · {h.exchange}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
