"use client";

import { useEffect, useState } from "react";
import { api, type Alert } from "../lib/api";
import SymbolAutocomplete from "../components/SymbolAutocomplete";

function AlertRow({ a, onDelete }: { a: Alert; onDelete: (id: number) => void }) {
  const unit = a.kind === "price" ? "" : "%";
  const word = a.kind === "price" ? "price" : "day change";
  const dir = a.direction === "above" ? "rises above" : "falls below";
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-ink">{a.symbol}</span>
          {a.active ? (
            <span className="rounded-full bg-forest-soft px-2 py-0.5 text-[10px] font-medium text-forest">
              armed
            </span>
          ) : (
            <span className="rounded-full bg-mist px-2 py-0.5 text-[10px] text-sage">
              fired{a.last_value != null ? ` @ ${a.last_value}${unit}` : ""}
            </span>
          )}
        </div>
        <div className="mt-0.5 text-xs text-sage">
          when {word} {dir}{" "}
          <span className="font-mono text-ink/80">
            {a.threshold}
            {unit}
          </span>
          {a.note ? ` · ${a.note}` : ""}
        </div>
      </div>
      <button
        onClick={() => onDelete(a.id)}
        className="shrink-0 rounded-lg border border-line px-2.5 py-1 text-xs text-sage hover:border-brick/40 hover:text-brick"
      >
        Delete
      </button>
    </div>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [symbol, setSymbol] = useState("");
  const [kind, setKind] = useState<"price" | "pct_change">("price");
  const [direction, setDirection] = useState<"above" | "below">("above");
  const [threshold, setThreshold] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function load() {
    api
      .alerts()
      .then((d) => setAlerts(d.alerts))
      .catch(() => setAlerts([]))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const thr = parseFloat(threshold);
    if (!symbol) return setErr("Pick a symbol.");
    if (!Number.isFinite(thr)) return setErr("Enter a numeric threshold.");
    setSaving(true);
    try {
      await api.createAlert({ symbol, kind, direction, threshold: thr, note: note || undefined });
      setThreshold("");
      setNote("");
      load();
    } catch {
      setErr("Could not create alert.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: number) {
    await api.deleteAlert(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  return (
    <div>
      <h1 className="mb-1 font-display text-2xl font-bold text-ink">Alerts</h1>
      <p className="mb-5 text-sm text-sage">
        We watch the market for you. When a rule triggers, a toast pops up live — no
        need to keep this tab open on the chart.
      </p>

      <form
        onSubmit={submit}
        className="mb-6 rounded-xl border border-line bg-paper p-4"
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <label className="mb-1 block text-xs text-sage">Symbol</label>
            <SymbolAutocomplete
              placeholder="Search a stock… (e.g. AAPL, RELIANCE.NS)"
              onSelect={(s) => setSymbol(s)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-sage">Trigger on</label>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as "price" | "pct_change")}
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none focus:border-forest/50"
            >
              <option value="price">Price</option>
              <option value="pct_change">Day change %</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="mb-1 block text-xs text-sage">Direction</label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value as "above" | "below")}
                className="w-full rounded-lg border border-line bg-paper px-2 py-2 text-sm text-ink outline-none focus:border-forest/50"
              >
                <option value="above">Above</option>
                <option value="below">Below</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-sage">
                {kind === "price" ? "Price" : "%"}
              </label>
              <input
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                inputMode="decimal"
                placeholder={kind === "price" ? "300" : "5"}
                className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none placeholder:text-sage focus:border-forest/50"
              />
            </div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-sage">Note (optional)</label>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={140}
              placeholder="e.g. add on breakout"
              className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink outline-none placeholder:text-sage focus:border-forest/50"
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-forest/90 disabled:opacity-50"
          >
            {saving ? "Setting…" : "Set alert"}
          </button>
        </div>
        {err && <p className="mt-2 text-xs text-brick">{err}</p>}
      </form>

      {loading ? (
        <div className="h-24 animate-pulse rounded-xl bg-mist/50" />
      ) : alerts.length === 0 ? (
        <div className="rounded-xl border border-line bg-paper p-6 text-center text-sm text-sage">
          No alerts yet. Set one above and we’ll watch it for you.
        </div>
      ) : (
        <div className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper">
          {alerts.map((a) => (
            <AlertRow key={a.id} a={a} onDelete={remove} />
          ))}
        </div>
      )}
    </div>
  );
}
