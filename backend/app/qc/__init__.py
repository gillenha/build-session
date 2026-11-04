"""Quality-check agent: runs after the answering agent drafts a reply, before it is returned.

Deterministic checks are the hard gate; the LLM review only runs once they pass and can only add failures.
"""
from datetime import datetime

from app.qc import checks
from app.qc.review import review


def run_qc(question: str, draft: str, final: str, quotes: list[dict], chunks: dict[str, dict],
           now: datetime | None = None) -> dict:
    """draft = the model's text; final = draft plus the labels code appends (what the user sees).

    Returns {"verdict": "pass" | "fail", "issues": [...]}; issues are prefixed "check:" or "review:".
    """
    hard = checks.run(draft, final, chunks, quotes, now)
    if hard:
        return {"verdict": "fail", "issues": [f"check: {i}" for i in hard]}
    result = review(question, draft, {"get_quote": quotes, "search_filings": list(chunks.values())})
    if result.verdict == "fail":
        return {"verdict": "fail", "issues": [f"review: {i}" for i in result.issues] or ["review: failed"]}
    return {"verdict": "pass", "issues": []}
