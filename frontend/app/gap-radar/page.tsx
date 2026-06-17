"use client";

import { useEffect, useState } from "react";
import { api, type GapRow } from "../lib/api";
import { Pct, PageHead } from "../components/ui";
import { Explainer } from "../components/Explainer";
import { useRegion } from "../components/RegionContext";

export default function GapRadarPage() {
  const { region } = useRegion();
  const [rows, setRows] = useState<GapRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  function load() {
    setErr(null);
    api
      .gapRadar()
      .then((d) => setRows(d.signals))
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000); // refresh every 30s, 24/7 signal
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <PageHead
        title="Gap Radar"
        sub="Tokenized stocks trade 24/7 (Binance bStocks). Their move forecasts the US open."
      >
        <button
          onClick={load}
          className="rounded-md border border-line bg-paper px-3 py-1.5 text-sm text-ink/70 hover:bg-mist"
        >
          Refresh
        </button>
      </PageHead>

      <Explainer
        what={
          <p>
            Tokenized US stocks trade 24/7 on Binance even when the US market is
            closed. The big % = <b>implied open</b>: where the stock will likely
            open vs its last US close. <span className="text-forest">+</span> up,{" "}
            <span className="text-brick">−</span> down.
          </p>
        }
        use={
          <p>
            Check before the US opens to see what&apos;s gapping overnight.{" "}
            <b>⚡ actionable</b> = move over 1.5%, worth attention. Act in
            pre-market or just know what&apos;s coming. It&apos;s a forecast, not
            a guarantee.
          </p>
        }
      />

      {region !== "US" && (
        <div className="mb-4 rounded-lg border border-line bg-mist/50 p-3 text-sm text-ink/70">
          Tokenized stocks (bStocks) are US names — Gap Radar always shows the US
          set, regardless of the market selected in the sidebar.
        </div>
      )}

      {err && (
        <div className="mb-4 rounded-lg border border-brick/30 bg-brick/5 p-4 text-sm text-brick">
          {err} — is the backend running on :8000?
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {loading && rows.length === 0 ? (
          <p className="text-sage">Loading…</p>
        ) : (
          rows.map((r) => (
            <div
              key={r.token}
              className={`rounded-xl border p-4 ${
                r.actionable
                  ? "border-forest/40 bg-forest-soft"
                  : "border-line bg-paper"
              }`}
            >
              <div className="flex items-baseline justify-between">
                <div className="font-semibold text-ink">{r.underlying}</div>
                <div className="font-mono text-xs text-sage">{r.token}</div>
              </div>
              {r.available ? (
                <>
                  <div className="mt-3 font-mono text-2xl font-bold">
                    <Pct v={r.implied_open_pct} />
                  </div>
                  <div className="mt-1 text-xs text-sage">implied US open</div>
                  <div className="mt-3 flex justify-between font-mono text-xs text-sage">
                    <span>tok {r.token_price}</span>
                    <span>close {r.last_close}</span>
                  </div>
                  {r.actionable && (
                    <div className="mt-2 text-xs font-semibold text-forest">
                      ⚡ actionable (&gt;1.5%)
                    </div>
                  )}
                </>
              ) : (
                <div className="mt-4 text-sm text-sage">feed unavailable</div>
              )}
            </div>
          ))
        )}
      </div>

      <p className="mt-6 text-xs text-sage">
        Forecast, not a promise — thin liquidity can distort the token. Signals
        informational only. Backtest validation comes in M2.
      </p>
    </div>
  );
}
