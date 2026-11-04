"""The /chat agent: a manual tool-use loop, then the QC agent, with one retry on a QC failure."""
import logging
from datetime import datetime, timezone

import anthropic

from app import config, memory
from app.guardrails import footer, redact_pii
from app.prompts import SYSTEM
from app.qc import run_qc
from app.tools import DEFINITIONS, run_tool
from app.verify import cited_ids

log = logging.getLogger(__name__)
MAX_STEPS = 8
MAX_ATTEMPTS = 2  # first draft + one retry with the QC issues
_client: anthropic.Anthropic | None = None


def _anthropic() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.require("ANTHROPIC_API_KEY"))
    return _client


class _Run:
    """Everything the tools returned during one /chat request (the QC agent's evidence)."""

    def __init__(self) -> None:
        self.quotes: list[dict] = []
        self.chunks: dict[str, dict] = {}
        self.calls: list[str] = []


def _draft(messages: list, run: _Run) -> str:
    """Run the tool loop until the model stops; appends the final assistant turn to messages."""
    for _ in range(MAX_STEPS):
        response = _anthropic().messages.create(
            model=config.model(), max_tokens=16000, system=SYSTEM, tools=DEFINITIONS, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            data, content, is_error = run_tool(block.name, block.input)
            run.calls.append(f"{block.name}({', '.join(map(str, block.input.values()))})" + (" -> error" if is_error else ""))
            if not is_error and block.name == "get_quote":
                run.quotes.append(data)
            elif not is_error and block.name == "search_filings":
                run.chunks.update({hit["chunk_id"]: hit for hit in data})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error})
        messages.append({"role": "user", "content": results})
    else:
        raise RuntimeError(f"Agent did not finish within {MAX_STEPS} steps")

    if response.stop_reason == "refusal":
        return "I can't help with that request."
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Model hit max_tokens before finishing")
    return memory.strip_app_notes("\n".join(b.text for b in response.content if b.type == "text").strip())


def _qc_feedback(issues: list[str]) -> str:
    return ("[quality check] Your draft failed review and was not shown to the advisor. Issues:\n"
            + "\n".join(f"- {i}" for i in issues)
            + "\nRewrite the full answer fixing these. Remove or source any unsupported claim; "
              "call tools again if you need evidence.")


def chat(session_id: str, message: str) -> dict:
    user_text = redact_pii(message)
    messages = memory.load(session_id) + [{"role": "user", "content": user_text}]
    run = _Run()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        draft = _draft(messages, run)
        now = datetime.now(timezone.utc)
        final = draft + footer(run.quotes, now)
        qc = run_qc(user_text, draft, final, run.quotes, run.chunks, now)
        log.info("session %s attempt %d QC %s %s", session_id, attempt, qc["verdict"], qc["issues"])
        if qc["verdict"] == "pass" or attempt == MAX_ATTEMPTS:
            break
        messages.append({"role": "user", "content": _qc_feedback(qc["issues"])})

    citations = [
        {k: run.chunks[c][k] for k in ("chunk_id", "ticker", "filing_type", "filing_date", "page", "source_url")}
        | {"snippet": run.chunks[c]["text"][:300]}
        for c in cited_ids(draft) if c in run.chunks
    ]
    # History stores the model's own text plus a note of tools run, not the appended footer
    # (the model would otherwise copy the footer, and forget it had called tools).
    memory.save_turn(session_id, user_text, draft + memory.tool_note(run.calls))
    return {
        "answer": final,
        "citations": citations,
        "quote_as_of": min((q["timestamp"] for q in run.quotes), default=None),
        "verified": qc["verdict"] == "pass",
        "issues": qc["issues"],
        "attempts": attempt,
    }
