import type { ChatResponse } from "../api";

// Shows why the quality check failed, or that the answer was revised before passing.
export function QcIssues({ response }: { response: ChatResponse }) {
  if (!response.verified && response.issues.length > 0) {
    return (
      <div role="alert" className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
        <p className="mb-1 font-semibold">Quality check failed{response.attempts > 1 ? " after a retry" : ""}:</p>
        <ul className="ml-4 list-disc space-y-0.5">
          {response.issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      </div>
    );
  }
  if (response.verified && response.attempts > 1) {
    return <p className="mt-2 text-xs text-slate-500">Revised once after the quality check flagged the first draft.</p>;
  }
  return null;
}
