import { useEffect, useRef, useState } from "react";

import { postChat, type ChatResponse } from "./api";
import { AssistantMessage } from "./components/AssistantMessage";
import { Composer } from "./components/Composer";
import { loadSessionId, newSessionId } from "./session";

type Turn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: ChatResponse }
  | { role: "error"; text: string };

export default function App() {
  const [sessionId, setSessionId] = useState(loadSessionId);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pending, setPending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, pending]);

  async function send(text: string) {
    setTurns((t) => [...t, { role: "user", text }]);
    setPending(true);
    try {
      const response = await postChat(sessionId, text);
      setTurns((t) => [...t, { role: "assistant", response }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "error", text: e instanceof Error ? e.message : String(e) }]);
    } finally {
      setPending(false);
    }
  }

  function reset() {
    setSessionId(newSessionId());
    setTurns([]);
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4">
      <header className="flex items-center justify-between border-b border-slate-200 py-4">
        <div>
          <h1 className="text-lg font-semibold">Stock Briefing</h1>
          <p className="text-xs text-slate-500">Quotes and SEC filings, with every number checked against its source.</p>
        </div>
        <button onClick={reset} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100">
          New conversation
        </button>
      </header>

      <main className="flex-1 space-y-4 py-6">
        {turns.length === 0 && (
          <p className="text-center text-sm text-slate-500">
            Ask about a stock to prepare for a client conversation. Quotes are sample data for now.
          </p>
        )}
        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={i} className="ml-auto max-w-[85%] rounded-lg bg-blue-700 px-4 py-2 text-sm text-white">
              {turn.text}
            </div>
          ) : turn.role === "assistant" ? (
            <AssistantMessage key={i} response={turn.response} />
          ) : (
            <div key={i} role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-800">
              {turn.text}
            </div>
          ),
        )}
        {pending && <p className="text-sm text-slate-500">Checking quotes and filings…</p>}
        <div ref={endRef} />
      </main>

      <footer className="sticky bottom-0 border-t border-slate-200 bg-slate-50 py-4">
        <Composer disabled={pending} onSend={send} />
      </footer>
    </div>
  );
}
