"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type MomentumRow } from "../lib/api";
import { Pct, PageHead } from "../components/ui";
import { Explainer } from "../components/Explainer";
import { useRegion, REGION_LABEL } from "../components/RegionContext";

export default function ScreenerPage() {
  const router = useRouter();
  const { region } = useRegion();
  const [rows, setRows] = useState<MomentumRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    api
      .momentum(region)
      .then((d) => !cancelled && setRows(d.results))
      .catch((e) => !cancelled && setErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [region]);

  return (
    <div>
      <PageHead
        title="Momentum Screener"
        sub={`What's winning in ${REGION_LABEL[region]} — ranked by trend-confirmed momentum.`}
      >
        <span className="rounded-full bg-forest-soft px-3 py-1 text-sm font-semibold text-forest">
          {REGION_LABEL[region]}
        </span>
      </PageHead>

      <Explainer
        what={
          <p>
            Global ETFs (baskets of stocks) ranked by momentum — which are
            trending up hardest now. <b>Score</b> = strength (higher is
            stronger). <b>1M–12M</b> = % return. <b>↑200DMA</b> = price above its
            200-day average = healthy uptrend.
          </p>
        }
        use={
          <p>
            Money flows to the top of the list. Favor leaders marked{" "}
            <span className="text-forest">↑200DMA</span>; avoid the red names at
            the bottom. Switch <b>market</b> (India / US / World) in the sidebar.
          </p>
        }
      />

      {err && (
        <div className="mb-4 rounded-lg border border-brick/30 bg-brick/5 p-4 text-sm text-brick">
          {err} — is the backend running on :8000?
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-line bg-paper">
        <table className="w-full text-sm">
          <thead className="bg-mist text-left text-xs uppercase tracking-wide text-sage">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3 text-right">Price</th>
              <th className="px-4 py-3 text-right">Score</th>
              <th className="px-4 py-3 text-right">1M</th>
              <th className="px-4 py-3 text-right">3M</th>
              <th className="px-4 py-3 text-right">6M</th>
              <th className="px-4 py-3 text-right">12M</th>
              <th className="px-4 py-3 text-center">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line font-mono">
            {loading ? (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-sage">
                  Loading…
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr
                  key={r.symbol}
                  onClick={() => router.push(`/stock/${encodeURIComponent(r.symbol)}`)}
                  className="cursor-pointer transition-colors hover:bg-mist/60"
                >
                  <td className="px-4 py-2 text-sage">{r.rank}</td>
                  <td className="px-4 py-2 font-semibold text-ink">{r.symbol}</td>
                  <td className="px-4 py-2 text-right text-ink/70">
                    {r.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right font-semibold text-forest">
                    {r.score >= 0 ? "+" : ""}
                    {r.score.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-right"><Pct v={r.r1} /></td>
                  <td className="px-4 py-2 text-right"><Pct v={r.r3} /></td>
                  <td className="px-4 py-2 text-right"><Pct v={r.r6} /></td>
                  <td className="px-4 py-2 text-right"><Pct v={r.r12} /></td>
                  <td className="px-4 py-2 text-center">
                    {r.above_200dma ? (
                      <span className="rounded bg-forest-soft px-2 py-0.5 text-xs font-medium text-forest">
                        ↑ 200DMA
                      </span>
                    ) : (
                      <span className="rounded bg-mist px-2 py-0.5 text-xs text-sage">
                        ↓ 200DMA
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
