"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ActionRow } from "./lib/api";
import { useRegion, REGION_LABEL } from "./components/RegionContext";
import { TopAssets } from "./components/TopAssets";
import RightRail from "./components/RightRail";
import Heatmap from "./components/Heatmap";
import MarketSummary from "./components/MarketSummary";

const STYLE: Record<
  ActionRow["action"],
  { badge: string; label: string; verb: string }
> = {
  BUY: { badge: "bg-forest text-white", label: "BUY", verb: "Consider buying" },
  REDUCE: { badge: "bg-brick text-white", label: "REDUCE", verb: "Consider trimming" },
  WATCH: {
    badge: "border border-forest text-forest bg-forest-soft",
    label: "WATCH",
    verb: "Keep an eye on",
  },
};

const CONF: Record<ActionRow["confidence"], string> = {
  high: "bg-forest-soft text-forest",
  medium: "bg-mist text-ink/70",
  low: "bg-mist text-sage",
};

function Group({ rows, kind }: { rows: ActionRow[]; kind: ActionRow["action"] }) {
  const items = rows.filter((r) => r.action === kind);
  if (items.length === 0) return null;
  const s = STYLE[kind];
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className={`rounded-md px-2 py-0.5 text-xs font-bold ${s.badge}`}>
          {s.label}
        </span>
        <span className="text-sm text-sage">{s.verb}</span>
      </div>
      <div className="space-y-2">
        {items.map((r) => (
          <Link
            key={`${r.action}-${r.symbol}`}
            href={`/stock/${encodeURIComponent(r.symbol)}`}
            className="flex items-center gap-4 rounded-xl border border-line bg-paper p-3.5 transition-all hover:border-forest/40 hover:shadow-sm"
          >
            <div className="w-44 shrink-0">
              <div className="font-mono font-semibold text-ink">{r.symbol}</div>
              <div className="text-xs text-sage">{r.name}</div>
            </div>
            <p className="flex-1 text-sm text-ink/80">{r.reason}</p>
            <span
              className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${CONF[r.confidence]}`}
            >
              {r.confidence}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const { region } = useRegion();
  const [rows, setRows] = useState<ActionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    api
      .actions(region)
      .then((d) => !cancelled && setRows(d.actions))
      .catch((e) => !cancelled && setErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [region]);

  const [today, setToday] = useState("");
  useEffect(() => {
    setToday(
      new Date().toLocaleDateString(undefined, {
        weekday: "long",
        month: "short",
        day: "numeric",
      })
    );
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight text-ink">
          Today&apos;s calls
          <span className="ml-3 rounded-full bg-forest-soft px-3 py-1 align-middle text-sm font-semibold text-forest">
            {REGION_LABEL[region]}
          </span>
        </h1>
        <p className="mt-1 text-sage">
          {today} · clear moves in {REGION_LABEL[region]} markets, with the
          reason. You decide and act.
        </p>
      </div>

      <TopAssets region={region} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold text-ink">What to do today</h2>

          {err && (
            <div className="mb-4 rounded-lg border border-brick/30 bg-brick/5 p-4 text-sm text-brick">
              {err} — is the backend running on :8000?
            </div>
          )}

          {loading ? (
            <p className="text-sage">Reading the markets…</p>
          ) : rows.length === 0 ? (
            <p className="text-sage">No strong calls right now — markets are quiet.</p>
          ) : (
            <div className="space-y-6">
              <Group rows={rows} kind="BUY" />
              <Group rows={rows} kind="WATCH" />
              <Group rows={rows} kind="REDUCE" />
            </div>
          )}

          <div className="mt-6 rounded-xl border border-line bg-mist/40 p-4 text-xs text-sage">
            Rule-based signals from momentum + 24/7 gap data — informational, not
            financial advice. Measured hit-rates come with the backtest engine
            (M2). Dig deeper:{" "}
            <Link href="/screener" className="text-forest underline">
              Screener
            </Link>{" "}
            ·{" "}
            <Link href="/gap-radar" className="text-forest underline">
              Gap Radar
            </Link>
          </div>
        </div>

        <RightRail region={region} />
      </div>

      <div className="mt-6 space-y-6">
        <Heatmap region={region} />
        <MarketSummary region={region} />
      </div>
    </div>
  );
}
