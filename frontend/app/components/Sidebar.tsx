"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRegion, REGION_LABEL, type Region } from "./RegionContext";
import ThemeToggle from "./ThemeToggle";

const REGIONS: Region[] = ["IN", "US", "WORLD"];

type Item = { href: string; label: string; icon: string; live?: boolean };

const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: "Radar",
    items: [
      { href: "/", label: "Dashboard", icon: "▤" },
      { href: "/screener", label: "Screener", icon: "▦", live: true },
      { href: "/gap-radar", label: "Gap Radar", icon: "◐", live: true },
    ],
  },
  {
    title: "Trade",
    items: [
      { href: "/algo", label: "AlgoTrading", icon: "↗" },
      { href: "/portfolio", label: "Portfolio", icon: "◆" },
      { href: "/alerts", label: "Alerts", icon: "◉", live: true },
      { href: "/bots", label: "Paper Bots", icon: "⚙", live: true },
    ],
  },
  {
    title: "Intel",
    items: [
      { href: "/news", label: "News", icon: "❋" },
      { href: "/chat", label: "ChatBot", icon: "✦" },
    ],
  },
];

export default function Sidebar() {
  const path = usePathname();
  const { region, setRegion } = useRegion();
  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col self-start border-r border-line bg-paper">
      <div className="flex items-center gap-2 px-5 py-5">
        <span className="font-display text-xl font-extrabold tracking-tight text-ink">
          Algo<span className="text-forest">Sign</span>
        </span>
        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-forest shadow-[0_0_8px_var(--color-forest)]" />
      </div>

      <div className="px-4 pb-3">
        <div className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-sage">
          Market
        </div>
        <div className="flex gap-1 rounded-lg border border-line bg-chalk p-1">
          {REGIONS.map((r) => (
            <button
              key={r}
              onClick={() => setRegion(r)}
              className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition ${
                region === r
                  ? "bg-forest text-white"
                  : "text-sage hover:text-ink"
              }`}
            >
              {REGION_LABEL[r]}
            </button>
          ))}
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-2">
        {GROUPS.map((g) => (
          <div key={g.title}>
            <div className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-sage">
              {g.title}
            </div>
            <div className="space-y-0.5">
              {g.items.map((it) => {
                const active = path === it.href;
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                      active
                        ? "bg-forest-soft font-semibold text-forest"
                        : "text-ink/70 hover:bg-mist hover:text-ink"
                    }`}
                  >
                    <span
                      className={`w-4 text-center ${active ? "text-forest" : "text-sage"}`}
                    >
                      {it.icon}
                    </span>
                    <span className="flex-1">{it.label}</span>
                    {it.live && (
                      <span className="h-1.5 w-1.5 rounded-full bg-forest" title="live data" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="space-y-3 border-t border-line px-4 py-4">
        <ThemeToggle />
        <div className="px-1 text-xs text-sage">
          <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-forest align-middle" />
          live market data
        </div>
      </div>
    </aside>
  );
}
