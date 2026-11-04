import type { Citation } from "../api";

export function Citations({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 border-t border-slate-200 pt-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</p>
      <ul className="space-y-2">
        {citations.map((c) => (
          <li key={c.chunk_id}>
            <details className="rounded-md bg-slate-50 px-3 py-2 text-sm">
              <summary className="cursor-pointer">
                <span className="font-mono text-xs text-slate-500">[{c.chunk_id}]</span>{" "}
                {c.ticker} {c.filing_type} filed {c.filing_date}, page {c.page}{" "}
                <a href={c.source_url} target="_blank" rel="noreferrer" className="text-blue-700 underline">
                  EDGAR
                </a>
              </summary>
              <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-600">{c.snippet}…</p>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
}
