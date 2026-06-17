"use client";

import { useState } from "react";

export type Table = { periods: string[]; rows: { label: string; values: string[] }[] };

const BOLD = [
  "operating profit", "operating income", "profit before tax", "pretax",
  "net profit", "net income", "opm", "gross profit", "total revenue",
  "total liabilities", "total assets", "total equity", "net cash flow",
  "free cash flow", "operating cash flow", "roce", "promoters",
];

export function FinancialTable({ data, unit }: { data: Table; unit?: string }) {
  if (!data || data.rows.length === 0)
    return <div className="p-4 text-sm text-sage">No data.</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-sage">
            <th className="sticky left-0 z-10 bg-paper px-3 py-2 text-left font-medium">
              {unit || "Figures"}
            </th>
            {data.periods.map((p, i) => (
              <th key={i} className="whitespace-nowrap px-3 py-2 text-right font-medium">
                {p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {data.rows.map((r) => {
            const bold = BOLD.some((b) => r.label.toLowerCase().includes(b));
            return (
              <tr key={r.label} className="hover:bg-mist/50">
                <td
                  className={`sticky left-0 z-10 bg-paper px-3 py-1.5 text-left text-ink ${
                    bold ? "font-semibold" : ""
                  }`}
                >
                  {r.label}
                </td>
                {r.values.map((v, i) => (
                  <td
                    key={i}
                    className={`whitespace-nowrap px-3 py-1.5 text-right font-mono text-ink/80 ${
                      bold ? "font-semibold text-ink" : ""
                    }`}
                  >
                    {v || "—"}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function StatementTabs({
  statements,
  tabs,
  unit,
}: {
  statements: Record<string, Table>;
  tabs: { key: string; label: string }[];
  unit?: string;
}) {
  const first = tabs.find((t) => statements[t.key]?.rows?.length)?.key || tabs[0].key;
  const [tab, setTab] = useState(first);
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-paper">
      <div className="flex flex-wrap gap-1 border-b border-line p-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              tab === t.key
                ? "bg-forest-soft font-semibold text-forest"
                : "text-sage hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {statements[tab] && <FinancialTable data={statements[tab]} unit={unit} />}
    </div>
  );
}
