"use client";

import { useRef, useState } from "react";
import { api } from "../lib/api";
import { PageHead } from "../components/ui";
import { useRegion, REGION_LABEL } from "../components/RegionContext";

type Msg = { role: "user" | "ai"; text: string };

const SUGGESTIONS = [
  "What's the strongest sector today?",
  "Summarize today's market in plain English.",
  "What should I be cautious about right now?",
  "Which of today's calls has the best setup?",
];

export default function ChatPage() {
  const { region } = useRegion();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const d = await api.chat(text, region);
      setMsgs((m) => [...m, { role: "ai", text: d.reply }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "ai", text: `Error: ${e}` }]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="flex h-[calc(100vh-9rem)] flex-col">
      <PageHead
        title="Market ChatBot"
        sub={`Ask anything about ${REGION_LABEL[region]} markets — grounded in today's live data.`}
      />

      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-line bg-paper p-4">
        {msgs.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <p className="text-sage">Ask about today&apos;s market, calls, sectors, or news.</p>
            <div className="grid max-w-lg gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-lg border border-line px-3 py-2 text-left text-sm text-ink/80 hover:bg-mist"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
                  m.role === "user"
                    ? "bg-forest text-white"
                    : "border border-line bg-mist/40 text-ink"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))
        )}
        {busy && <div className="text-sm text-sage">Thinking…</div>}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about the market…"
          className="flex-1 rounded-lg border border-line bg-paper px-4 py-3 text-sm text-ink outline-none placeholder:text-sage"
        />
        <button
          disabled={busy}
          className="rounded-lg bg-forest px-5 py-3 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
