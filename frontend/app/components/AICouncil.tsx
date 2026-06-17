"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";

type Council = Awaited<ReturnType<typeof api.council>>;

const ICONS: Record<string, string> = {
  Technical: "📈",
  Fundamental: "📊",
  News: "📰",
  Risk: "⚠",
};

function stanceColor(s: string): string {
  if (s === "bullish") return "text-forest";
  if (s === "bearish") return "text-brick";
  return "text-sage";
}

function callTone(call: string): { box: string; text: string } {
  if (call === "BUY") return { box: "border-forest/40 bg-forest-soft", text: "text-forest" };
  if (call === "REDUCE" || call === "AVOID")
    return { box: "border-brick/30 bg-brick/5", text: "text-brick" };
  return { box: "border-line bg-mist/40", text: "text-ink" };
}

export default function AICouncil({ symbol }: { symbol: string }) {
  const [d, setD] = useState<Council | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .council(symbol)
      .then((res) => !cancelled && setD(res))
      .catch(() => !cancelled && setD(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (!loading && (!d || !d.configured || d.error || !d.agents)) return null;

  return (
    <div className="mt-6">
      <div className="mb-2 flex items-center gap-2">
        <h2 className="text-sm font-semibold text-ink">AI Analyst Council</h2>
        <span className="rounded-full bg-mist px-2 py-0.5 text-xs text-sage">
          4 agents + verdict
        </span>
      </div>

      {loading ? (
        <div className="h-40 animate-pulse rounded-xl bg-mist/50" />
      ) : (
        <>
          {d!.verdict && (
            <div className={`mb-3 rounded-xl border p-4 ${callTone(d!.verdict.call).box}`}>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase tracking-wide text-sage">Chief verdict</span>
                <span className={`font-bold ${callTone(d!.verdict.call).text}`}>
                  {d!.verdict.call}
                </span>
                <span className="text-xs text-sage">· {d!.verdict.confidence} confidence</span>
              </div>
              <p className="mt-1 text-sm text-ink/80">{d!.verdict.reason}</p>
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {d!.agents!.map((a) => (
              <div key={a.role} className="rounded-xl border border-line bg-paper p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span>{ICONS[a.role] || "•"}</span>
                    <span className="text-sm font-semibold text-ink">{a.role}</span>
                  </div>
                  <span className={`text-xs font-medium capitalize ${stanceColor(a.stance)}`}>
                    {a.stance} · {a.confidence}
                  </span>
                </div>
                <p className="mt-2 text-sm text-ink/80">{a.take}</p>
              </div>
            ))}
          </div>
          <div className="mt-2 text-[10px] text-sage">
            AI synthesis of price, fundamentals, news + risk · informational, not advice
          </div>
        </>
      )}
    </div>
  );
}
