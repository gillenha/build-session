import Markdown from "react-markdown";

import type { ChatResponse } from "../api";
import { Citations } from "./Citations";
import { QcIssues } from "./QcIssues";

// The backend appends quote labels and the disclaimer after a "---" line; show them as a muted footer.
const FOOTER_SEPARATOR = "\n\n---\n";

function VerifiedBadge({ response }: { response: ChatResponse }) {
  const { verified, citations, quote_as_of } = response;
  // A refusal passes the check trivially; "verified" would overstate it.
  if (verified && citations.length === 0 && !quote_as_of) {
    return (
      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
        No figures to verify
      </span>
    );
  }
  return verified ? (
    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
      ✓ Numbers verified against sources
    </span>
  ) : (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
      ⚠ Unverified: check numbers against sources before using
    </span>
  );
}

export function AssistantMessage({ response }: { response: ChatResponse }) {
  const [body, footer] = response.answer.split(FOOTER_SEPARATOR);
  const isSample = footer?.includes("SAMPLE DATA");
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <VerifiedBadge response={response} />
        {response.quote_as_of && (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              isSample ? "bg-rose-100 text-rose-800" : "bg-slate-100 text-slate-700"
            }`}
          >
            Quote as of {response.quote_as_of}
            {isSample && " · SAMPLE DATA"}
          </span>
        )}
      </div>
      <div className="prose-sm space-y-2 text-sm leading-relaxed [&_li]:ml-5 [&_ul]:list-disc">
        <Markdown>{body}</Markdown>
      </div>
      {footer && <p className="mt-3 whitespace-pre-line text-xs text-slate-500">{footer}</p>}
      <QcIssues response={response} />
      <Citations citations={response.citations} />
    </div>
  );
}
