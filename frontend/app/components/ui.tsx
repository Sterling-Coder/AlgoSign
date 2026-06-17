export function Pct({ v }: { v: number | null }) {
  if (v === null || v === undefined)
    return <span className="text-sage/60">—</span>;
  const up = v >= 0;
  return (
    <span className={up ? "text-forest" : "text-brick"}>
      {up ? "+" : ""}
      {v.toFixed(2)}%
    </span>
  );
}

export function PageHead({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">{title}</h1>
        {sub && <p className="mt-1 text-sm text-sage">{sub}</p>}
      </div>
      {children}
    </div>
  );
}

export function Stub({ title, note }: { title: string; note: string }) {
  return (
    <div>
      <PageHead title={title} />
      <div className="rounded-xl border border-dashed border-line bg-paper p-12 text-center">
        <p className="text-ink/70">{note}</p>
        <p className="mt-2 text-xs text-sage">Coming in a later milestone.</p>
      </div>
    </div>
  );
}
