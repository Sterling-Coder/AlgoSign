"use client";

import { useEffect, useState } from "react";
import { api, type NewsItem } from "../lib/api";
import { PageHead } from "../components/ui";
import { useRegion, REGION_LABEL } from "../components/RegionContext";

type Brief = { summary?: string; themes?: { title: string; detail: string }[] };

function dedupe(items: NewsItem[]): NewsItem[] {
  const seen = new Set<string>();
  const out: NewsItem[] = [];
  for (const n of items) {
    const key = n.title
      .toLowerCase()
      .replace(/[^a-z0-9 ]/g, "")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 6)
      .join(" ");
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(n);
  }
  return out;
}

export default function NewsPage() {
  const { region } = useRegion();
  const [items, setItems] = useState<NewsItem[]>([]);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [briefLoading, setBriefLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    api
      .news(region)
      .then((d) => !cancelled && setItems(dedupe(d.items)))
      .catch((e) => !cancelled && setErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [region]);

  useEffect(() => {
    let cancelled = false;
    setBriefLoading(true);
    api
      .newsBrief(region)
      .then((d) => !cancelled && setBrief(d.configured ? d : null))
      .catch(() => !cancelled && setBrief(null))
      .finally(() => !cancelled && setBriefLoading(false));
    return () => {
      cancelled = true;
    };
  }, [region]);

  return (
    <div>
      <PageHead
        title="Market News"
        sub={`What's moving ${REGION_LABEL[region]} markets — explained.`}
      >
        <span className="rounded-full bg-forest-soft px-3 py-1 text-sm font-semibold text-forest">
          {REGION_LABEL[region]}
        </span>
      </PageHead>

      {/* AI brief */}
      {briefLoading ? (
        <div className="mb-4 h-28 animate-pulse rounded-xl bg-mist/50" />
      ) : (
        brief?.summary && (
          <div className="mb-4 rounded-xl border border-forest/30 bg-forest-soft/40 p-5">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-forest">
              <span>✦</span> The brief — what&apos;s happening
            </div>
            <p className="text-sm leading-relaxed text-ink/90">{brief.summary}</p>
            {brief.themes && brief.themes.length > 0 && (
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {brief.themes.map((t, i) => (
                  <div key={i} className="rounded-lg border border-line bg-paper p-3">
                    <div className="text-sm font-semibold text-ink">{t.title}</div>
                    <div className="mt-1 text-xs text-sage">{t.detail}</div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-3 text-[10px] text-sage">
              AI summary of today&apos;s headlines · informational, not advice
            </div>
          </div>
        )
      )}

      {err && (
        <div className="mb-4 rounded-lg border border-brick/30 bg-brick/5 p-4 text-sm text-brick">
          {err} — is the backend running on :8000?
        </div>
      )}

      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-sage">
        Headlines
      </div>
      {loading ? (
        <p className="text-sage">Loading headlines…</p>
      ) : items.length === 0 ? (
        <p className="text-sage">No headlines right now.</p>
      ) : (
        <div className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper">
          {items.map((n, i) => (
            <a
              key={i}
              href={n.link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-4 p-4 transition hover:bg-mist/60"
            >
              <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-forest" />
              <div className="flex-1">
                <p className="text-sm font-medium text-ink">{n.title}</p>
                <p className="mt-1 text-xs text-sage">
                  {n.source}
                  {n.source && n.ago ? " · " : ""}
                  {n.ago}
                </p>
              </div>
              <span className="text-sage">↗</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
