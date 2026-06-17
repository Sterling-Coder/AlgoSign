"use client";

import { useEffect, useState } from "react";
import { api, type Forecast as ForecastData } from "../lib/api";

const CONF_LABEL: Record<string, string> = {
  high: "high confidence",
  medium: "medium confidence",
  low: "low confidence",
};

export default function Forecast({ symbol }: { symbol: string }) {
  const [f, setF] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .predict(symbol)
      .then((res) => !cancelled && setF(res))
      .catch(() => !cancelled && setF(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (loading)
    return <div className="mt-4 h-28 animate-pulse rounded-xl bg-mist/50" />;

  // Not enough history to publish an honest number — say so, don't fake it.
  if (!f || !f.available || !f.headline) {
    return (
      <div className="mt-4 rounded-xl border border-line bg-paper p-4 text-sm text-sage">
        Not enough price history to forecast {symbol} honestly.
      </div>
    );
  }

  const h = f.headline;
  const up = h.direction === "UP";
  const tone = up ? "text-forest" : "text-brick";

  return (
    <div className="mt-4 rounded-xl border border-line bg-paper p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-ink">Probability forecast</h2>
          <span className="rounded-full bg-mist px-2 py-0.5 text-xs capitalize text-ink/70">
            {CONF_LABEL[f.confidence ?? "low"]}
          </span>
        </div>
        <span className="text-[10px] uppercase tracking-wide text-sage">
          backtested · not advice
        </span>
      </div>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className={`font-mono text-3xl font-bold ${tone}`}>
          {up ? "▲" : "▼"} {h.probability}%
        </span>
        <span className="text-sm text-ink/80">
          chance {symbol} closes {up ? "higher" : "lower"} over the next{" "}
          {h.horizon} trading days
        </span>
      </div>

      <p className="mt-1 text-xs text-sage">{f.basis}</p>
      <p className="mt-0.5 text-xs text-sage">
        Track record: {h.sample_size} similar setups in history, closed up{" "}
        {h.hist_hitrate}% of the time (avg {h.avg_fwd_pct > 0 ? "+" : ""}
        {h.avg_fwd_pct}% over {h.horizon}d).
      </p>

      {f.horizons && f.horizons.length > 1 && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          {f.horizons.map((c) => {
            const cup = c.direction === "UP";
            return (
              <div
                key={c.horizon}
                className="rounded-lg border border-line px-2.5 py-1.5 text-center"
              >
                <div className="text-[10px] text-sage">{c.horizon}d</div>
                <div
                  className={`font-mono text-sm font-semibold ${
                    cup ? "text-forest" : "text-brick"
                  }`}
                >
                  {cup ? "▲" : "▼"} {c.probability}%
                </div>
                <div className="text-[10px] text-sage">n={c.sample_size}</div>
              </div>
            );
          })}
        </div>
      )}

      <p className="mt-3 text-[11px] text-sage">{f.disclaimer}</p>
    </div>
  );
}
