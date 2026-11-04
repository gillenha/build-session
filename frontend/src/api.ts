// Mirrors the backend contract in CLAUDE.md (POST /chat).
export type Citation = {
  chunk_id: string;
  ticker: string;
  filing_type: string;
  filing_date: string;
  page: number;
  source_url: string;
  snippet: string;
};

export type ChatResponse = {
  answer: string;
  citations: Citation[];
  quote_as_of: string | null;
  verified: boolean;
  issues: string[];
  attempts: number;
};

// Backend base URL, baked in at build time (e.g. https://api.example.up.railway.app).
// Unset in local dev, where "/api" goes through the Vite proxy in vite.config.ts.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

export async function postChat(sessionId: string, message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    const detail = await res.json().then((b) => b.detail, () => res.statusText);
    throw new Error(`Request failed (${res.status}): ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
  }
  return res.json();
}
