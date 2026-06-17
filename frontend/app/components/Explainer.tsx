"use client";

import { useState } from "react";

export function Explainer({
  what,
  use,
}: {
  what: React.ReactNode;
  use: React.ReactNode;
}) {
  const [open, setOpen] = useState(true);
  return (
    <div className="mb-6 rounded-xl border border-line bg-forest-soft/50 p-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left text-sm font-semibold text-forest"
      >
        <span>💡 How to read this</span>
        <span className="text-xs">{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div className="mt-3 grid gap-3 text-sm text-ink/80 sm:grid-cols-2">
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-sage">
              What you&apos;re seeing
            </div>
            {what}
          </div>
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-sage">
              How to use it
            </div>
            {use}
          </div>
        </div>
      )}
    </div>
  );
}
