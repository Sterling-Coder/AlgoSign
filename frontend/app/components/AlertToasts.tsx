"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { STREAM_URL, type AlertEvent, type FillEvent } from "../lib/api";

type Toast = (AlertEvent | FillEvent) & { key: number };

function AlertCard({ t }: { t: AlertEvent }) {
  const unit = t.kind === "price" ? "" : "%";
  const dirWord = t.direction === "above" ? "rose above" : "fell below";
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm font-bold text-ink">{t.symbol}</span>
        <span className="text-xs text-forest">◉ alert</span>
      </div>
      <div className="mt-0.5 text-sm text-ink/80">
        {dirWord} {t.threshold}
        {unit} · now{" "}
        <span className="font-mono font-semibold text-ink">
          {t.value}
          {unit}
        </span>
      </div>
      {t.note && <div className="mt-0.5 text-xs text-sage">{t.note}</div>}
    </>
  );
}

function FillCard({ t }: { t: FillEvent }) {
  const win = t.pnl >= 0;
  return (
    <>
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm font-bold text-ink">{t.symbol}</span>
        <span className="text-xs text-sage">⚙ {t.reason} fill</span>
      </div>
      <div className="mt-0.5 text-sm text-ink/80">
        closed {t.side} {t.qty} @{" "}
        <span className="font-mono text-ink">{t.exit_price}</span> ·{" "}
        <span className={`font-mono font-semibold ${win ? "text-forest" : "text-brick"}`}>
          {win ? "+" : ""}
          {t.pnl}
        </span>
      </div>
    </>
  );
}

export default function AlertToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    // EventSource auto-reconnects; withCredentials carries the device cookie.
    const es = new EventSource(STREAM_URL, { withCredentials: true });
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data?.type !== "alert" && data?.type !== "fill") return;
        const t: Toast = { ...data, key: Date.now() + Math.random() };
        setToasts((prev) => [...prev, t]);
        setTimeout(
          () => setToasts((prev) => prev.filter((x) => x.key !== t.key)),
          12000
        );
      } catch {
        /* ignore heartbeat / non-JSON frames */
      }
    };
    es.onerror = () => {
      /* browser retries automatically; nothing to do */
    };
    return () => es.close();
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <Link
          key={t.key}
          href={`/stock/${encodeURIComponent(t.symbol)}`}
          className="block rounded-xl border border-forest/40 bg-paper p-3 shadow-lg transition hover:border-forest"
          onClick={() => setToasts((prev) => prev.filter((x) => x.key !== t.key))}
        >
          {t.type === "alert" ? <AlertCard t={t} /> : <FillCard t={t} />}
        </Link>
      ))}
    </div>
  );
}
