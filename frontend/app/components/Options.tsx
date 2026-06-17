"use client";

import { useEffect, useState } from "react";
import { api, type OptionChain, type OptionRow } from "../lib/api";

function fmt(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function OptionTable({ rows, kind }: { rows: OptionRow[]; kind: "calls" | "puts" }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line">
      <div
        className={`px-3 py-1.5 text-xs font-semibold ${
          kind === "calls" ? "bg-forest-soft text-forest" : "bg-brick/5 text-brick"
        }`}
      >
        {kind === "calls" ? "Calls" : "Puts"}
      </div>
      <table className="w-full text-right font-mono text-xs">
        <thead className="text-sage">
          <tr className="border-b border-line">
            <th className="px-2 py-1 text-left font-normal">Strike</th>
            <th className="px-2 py-1 font-normal">Last</th>
            <th className="px-2 py-1 font-normal">Bid/Ask</th>
            <th className="px-2 py-1 font-normal">OI</th>
            <th className="px-2 py-1 font-normal">IV</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.strike}
              className={`border-b border-line/50 last:border-0 ${
                r.itm ? "bg-mist/50" : ""
              }`}
            >
              <td className="px-2 py-1 text-left font-semibold text-ink">{fmt(r.strike)}</td>
              <td className="px-2 py-1 text-ink">{fmt(r.last)}</td>
              <td className="px-2 py-1 text-sage">
                {fmt(r.bid)}/{fmt(r.ask)}
              </td>
              <td className="px-2 py-1 text-sage">{r.open_interest.toLocaleString()}</td>
              <td className="px-2 py-1 text-sage">{r.iv === null ? "—" : `${r.iv}%`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Options({ symbol }: { symbol: string }) {
  const [chain, setChain] = useState<OptionChain | null>(null);
  const [exp, setExp] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .options(symbol, exp)
      .then((res) => !cancelled && setChain(res))
      .catch(() => !cancelled && setChain(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [symbol, exp]);

  // Hide entirely for symbols with no options (e.g. Indian equities).
  if (!loading && (!chain || !chain.available)) return null;

  return (
    <div className="mt-6">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-ink">Options chain</h2>
          {chain?.underlying != null && (
            <span className="rounded-full bg-mist px-2 py-0.5 text-xs text-ink/70">
              spot {chain.underlying.toLocaleString()}
            </span>
          )}
        </div>
        {chain?.expirations && chain.expirations.length > 0 && (
          <select
            value={exp ?? chain.expiration ?? chain.expirations[0].ts}
            onChange={(e) => setExp(Number(e.target.value))}
            className="rounded-lg border border-line bg-paper px-2 py-1 text-xs text-ink outline-none focus:border-forest/50"
          >
            {chain.expirations.map((x) => (
              <option key={x.ts} value={x.ts}>
                {x.date}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className="h-40 animate-pulse rounded-xl bg-mist/50" />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          <OptionTable rows={chain!.calls ?? []} kind="calls" />
          <OptionTable rows={chain!.puts ?? []} kind="puts" />
        </div>
      )}
      <p className="mt-2 text-[11px] text-sage">
        Strikes nearest the money · live via Yahoo · not financial advice.
      </p>
    </div>
  );
}
