"use client";

import { useEffect, useState } from "react";
import { api, type BotsState, type Position } from "../lib/api";
import SymbolAutocomplete from "../components/SymbolAutocomplete";

function pnlClass(v: number | null | undefined): string {
  if (v === null || v === undefined) return "text-sage";
  return v >= 0 ? "text-forest" : "text-brick";
}
function money(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function PositionRow({ p, onClose }: { p: Position; onClose: (id: number) => void }) {
  const open = p.status === "open";
  const pnl = open ? p.unrealized_pnl : p.pnl;
  return (
    <tr className="border-b border-line/60 last:border-0">
      <td className="px-3 py-2">
        <span className="font-mono text-sm font-semibold text-ink">{p.symbol}</span>
        <span
          className={`ml-2 rounded px-1.5 py-0.5 text-[10px] font-medium ${
            p.side === "long" ? "bg-forest-soft text-forest" : "bg-brick/10 text-brick"
          }`}
        >
          {p.side}
        </span>
      </td>
      <td className="px-3 py-2 text-right font-mono text-sm text-ink">{p.qty}</td>
      <td className="px-3 py-2 text-right font-mono text-sm text-ink">{p.entry_price}</td>
      <td className="px-3 py-2 text-right font-mono text-sm text-ink">
        {open ? (p.current_price ?? "—") : p.exit_price ?? "—"}
      </td>
      <td className="px-3 py-2 text-right font-mono text-xs text-sage">
        {p.stop ?? "—"} / {p.target ?? "—"}
      </td>
      <td className={`px-3 py-2 text-right font-mono text-sm font-semibold ${pnlClass(pnl)}`}>
        {money(pnl)}
      </td>
      <td className="px-3 py-2 text-right">
        {open ? (
          <button
            onClick={() => onClose(p.id)}
            className="rounded-lg border border-line px-2.5 py-1 text-xs text-sage hover:border-brick/40 hover:text-brick"
          >
            Close
          </button>
        ) : (
          <span className="text-xs text-sage">{p.status}</span>
        )}
      </td>
    </tr>
  );
}

export default function BotsPage() {
  const [state, setState] = useState<BotsState | null>(null);
  const [loading, setLoading] = useState(true);
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState<"long" | "short">("long");
  const [qty, setQty] = useState("");
  const [stop, setStop] = useState("");
  const [target, setTarget] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function load() {
    api
      .bots()
      .then(setState)
      .catch(() => setState(null))
      .finally(() => setLoading(false));
  }
  useEffect(() => {
    load();
    const t = setInterval(load, 30000); // refresh live P&L
    return () => clearInterval(t);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const q = parseFloat(qty);
    if (!symbol) return setErr("Pick a symbol.");
    if (!Number.isFinite(q) || q <= 0) return setErr("Quantity must be positive.");
    setSaving(true);
    try {
      await api.openBot({
        symbol,
        side,
        qty: q,
        stop: stop ? parseFloat(stop) : undefined,
        target: target ? parseFloat(target) : undefined,
      });
      setQty("");
      setStop("");
      setTarget("");
      load();
    } catch {
      setErr("Could not open position (need a live price for that symbol).");
    } finally {
      setSaving(false);
    }
  }

  async function close(id: number) {
    await api.closeBot(id);
    load();
  }

  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <h1 className="font-display text-2xl font-bold text-ink">Paper Bots</h1>
        <span className="rounded-full bg-mist px-2 py-0.5 text-xs text-sage">
          simulated · no real money
        </span>
      </div>
      <p className="mb-5 text-sm text-sage">
        Open a simulated trade with an optional stop and target. The bot watches it for
        you and auto-closes at your levels, tracking live P&amp;L. Risk-free practice.
      </p>

      {state && (
        <div className="mb-5 grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-line bg-paper p-4">
            <div className="text-xs text-sage">Open positions</div>
            <div className="mt-0.5 font-mono text-xl font-bold text-ink">{state.open_count}</div>
          </div>
          <div className="rounded-xl border border-line bg-paper p-4">
            <div className="text-xs text-sage">Unrealized P&amp;L</div>
            <div className={`mt-0.5 font-mono text-xl font-bold ${pnlClass(state.unrealized_pnl)}`}>
              {money(state.unrealized_pnl)}
            </div>
          </div>
          <div className="rounded-xl border border-line bg-paper p-4">
            <div className="text-xs text-sage">Realized P&amp;L</div>
            <div className={`mt-0.5 font-mono text-xl font-bold ${pnlClass(state.realized_pnl)}`}>
              {money(state.realized_pnl)}
            </div>
          </div>
        </div>
      )}

      <form onSubmit={submit} className="mb-6 rounded-xl border border-line bg-paper p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <label className="mb-1 block text-xs text-sage">Symbol</label>
            <SymbolAutocomplete
              placeholder="Search a stock… (e.g. AAPL, RELIANCE.NS)"
              onSelect={(s) => setSymbol(s)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-sage">Side</label>
            <select
              value={side}
              onChange={(e) => setSide(e.target.value as "long" | "short")}
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest/50"
            >
              <option value="long">Long</option>
              <option value="short">Short</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-sage">Quantity</label>
            <input
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              inputMode="decimal"
              placeholder="10"
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none placeholder:text-sage focus:border-forest/50"
            />
          </div>
          <div className="grid grid-cols-2 gap-2 lg:col-span-1">
            <div>
              <label className="mb-1 block text-xs text-sage">Stop</label>
              <input
                value={stop}
                onChange={(e) => setStop(e.target.value)}
                inputMode="decimal"
                placeholder="opt."
                className="w-full rounded-lg border border-line bg-paper px-2 py-2 text-sm text-ink outline-none placeholder:text-sage focus:border-forest/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-sage">Target</label>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                inputMode="decimal"
                placeholder="opt."
                className="w-full rounded-lg border border-line bg-paper px-2 py-2 text-sm text-ink outline-none placeholder:text-sage focus:border-forest/50"
              />
            </div>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest/90 disabled:opacity-50"
          >
            {saving ? "Opening…" : "Open paper trade"}
          </button>
          {err && <p className="text-xs text-brick">{err}</p>}
        </div>
      </form>

      {loading ? (
        <div className="h-24 animate-pulse rounded-xl bg-mist/50" />
      ) : !state || state.positions.length === 0 ? (
        <div className="rounded-xl border border-line bg-paper p-6 text-center text-sm text-sage">
          No positions yet. Open a paper trade above.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line bg-paper">
          <table className="w-full">
            <thead className="text-xs text-sage">
              <tr className="border-b border-line text-left">
                <th className="px-3 py-2 font-normal">Position</th>
                <th className="px-3 py-2 text-right font-normal">Qty</th>
                <th className="px-3 py-2 text-right font-normal">Entry</th>
                <th className="px-3 py-2 text-right font-normal">Now/Exit</th>
                <th className="px-3 py-2 text-right font-normal">Stop/Tgt</th>
                <th className="px-3 py-2 text-right font-normal">P&amp;L</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {state.positions.map((p) => (
                <PositionRow key={p.id} p={p} onClose={close} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
