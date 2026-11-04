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

export async function postChat(sessionId: string, message: string): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
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
