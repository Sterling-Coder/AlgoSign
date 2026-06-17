"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { StatementTabs } from "./Statements";

type Data = Awaited<ReturnType<typeof api.indiaFundamentals>>;

const STMT_TABS: { key: string; label: string }[] = [
  { key: "quarterly", label: "Quarterly" },
  { key: "pnl", label: "Profit & Loss" },
  { key: "balance_sheet", label: "Balance Sheet" },
  { key: "cash_flow", label: "Cash Flow" },
  { key: "ratios", label: "Ratios" },
  { key: "shareholding", label: "Shareholding" },
];

export default function IndiaFundamentals({ symbol }: { symbol: string }) {
  const [d, setD] = useState<Data | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .indiaFundamentals(symbol)
      .then((res) => !cancelled && setD(res))
      .catch(() => !cancelled && setD(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (loading)
    return <div className="mt-6 h-24 animate-pulse rounded-xl bg-mist/50" />;
  if (!d || !d.available) return null;

  return (
    <div className="mt-6">
      <div className="mb-2 flex items-center gap-2">
        <h2 className="text-sm font-semibold text-ink">Deep fundamentals</h2>
        <span className="rounded-full bg-mist px-2 py-0.5 text-xs text-sage">
          Screener.in
        </span>
        {d.promoter_holding && (
          <span className="text-xs text-sage">
            · promoter holding {d.promoter_holding}
          </span>
        )}
      </div>

      {d.ratios && d.ratios.length > 0 && (
        <div className="mb-3 grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-9">
          {d.ratios.map((r) => (
            <div
              key={r.label}
              className={`rounded-lg border px-2.5 py-2 ${
                r.label === "ROCE" || r.label === "ROE"
                  ? "border-forest/40 bg-forest-soft"
                  : "border-line bg-paper"
              }`}
            >
              <div className="truncate text-[10px] text-sage">{r.label}</div>
              <div className="font-mono text-sm font-semibold text-ink">{r.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-paper p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-forest">
            Pros
          </div>
          <ul className="space-y-1.5">
            {(d.pros || []).map((p, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80">
                <span className="text-forest">✓</span>
                {p}
              </li>
            ))}
            {(!d.pros || d.pros.length === 0) && <li className="text-sm text-sage">—</li>}
          </ul>
        </div>
        <div className="rounded-xl border border-line bg-paper p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brick">
            Cons
          </div>
          <ul className="space-y-1.5">
            {(d.cons || []).map((c, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80">
                <span className="text-brick">✕</span>
                {c}
              </li>
            ))}
            {(!d.cons || d.cons.length === 0) && <li className="text-sm text-sage">—</li>}
          </ul>
        </div>
      </div>

      {d.statements && (
        <div className="mt-3">
          <StatementTabs
            statements={d.statements}
            tabs={STMT_TABS}
            unit="Figures in Rs. Cr"
          />
        </div>
      )}

      {d.about && (
        <div className="mt-3 rounded-xl border border-line bg-paper p-4">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-sage">
            About
          </div>
          <p className="text-sm text-ink/80">{d.about}</p>
        </div>
      )}

      {d.documents && (
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          <DocList title="Announcements" items={d.documents.announcements} />
          <DocList title="Annual reports" items={d.documents.annual_reports} />
          <DocList title="Credit ratings" items={d.documents.credit_ratings} />
        </div>
      )}
    </div>
  );
}

function DocList({
  title,
  items,
}: {
  title: string;
  items?: { label: string; url: string; date: string }[];
}) {
  if (!items || items.length === 0) return null;
  return (
    <div className="rounded-xl border border-line bg-paper p-4">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-sage">
        {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i}>
            <a
              href={it.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-forest hover:underline"
            >
              {it.label}
              {it.date ? ` · ${it.date}` : ""} ↗
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
