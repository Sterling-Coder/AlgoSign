"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("algosign.theme", next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      className="flex w-full items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-ink/70 transition hover:bg-mist"
      title="Toggle night mode"
    >
      <span>{dark ? "☀" : "☾"}</span>
      <span>{dark ? "Light mode" : "Night mode"}</span>
    </button>
  );
}
