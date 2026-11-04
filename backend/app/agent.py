"""The /chat agent: a manual tool-use loop that records every tool result for verification."""
import logging

import anthropic

from app import config, memory
from app.guardrails import footer, redact_pii
from app.prompts import SYSTEM
from app.tools import DEFINITIONS, run_tool
from app.verify import cited_ids, verify

log = logging.getLogger(__name__)
MAX_STEPS = 8
_client: anthropic.Anthropic | None = None


def _anthropic() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.require("ANTHROPIC_API_KEY"))
    return _client


def _final_text(response) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


def chat(session_id: str, message: str) -> dict:
    user_text = redact_pii(message)
    messages = memory.load(session_id) + [{"role": "user", "content": user_text}]
    quotes: list[dict] = []
    chunks: dict[str, dict] = {}
    calls: list[str] = []

    for _ in range(MAX_STEPS):
        response = _anthropic().messages.create(
            model=config.model(), max_tokens=16000, system=SYSTEM, tools=DEFINITIONS, messages=messages,
        )
        if response.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            data, content, is_error = run_tool(block.name, block.input)
            calls.append(f"{block.name}({', '.join(map(str, block.input.values()))})" + (" -> error" if is_error else ""))
            if not is_error and block.name == "get_quote":
                quotes.append(data)
            elif not is_error and block.name == "search_filings":
                chunks.update({hit["chunk_id"]: hit for hit in data})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error})
        messages.append({"role": "user", "content": results})
    else:
        raise RuntimeError(f"Agent did not finish within {MAX_STEPS} steps")

    if response.stop_reason == "refusal":
        answer = "I can't help with that request."
    elif response.stop_reason == "max_tokens":
        raise RuntimeError("Model hit max_tokens before finishing")
    else:
        answer = memory.strip_app_notes(_final_text(response))

    verified, problems = verify(answer, chunks, quotes)
    if problems:
        log.warning("session %s unverified: %s", session_id, problems)

    citations = [
        {k: chunks[c][k] for k in ("chunk_id", "ticker", "filing_type", "filing_date", "page", "source_url")}
        | {"snippet": chunks[c]["text"][:300]}
        for c in cited_ids(answer) if c in chunks
    ]
    # History stores the model's own text plus a note of tools run, not the appended footer
    # (the model would otherwise copy the footer, and forget it had called tools).
    memory.save_turn(session_id, user_text, answer + memory.tool_note(calls))
    return {
        "answer": answer + footer(quotes),
        "citations": citations,
        "quote_as_of": min((q["timestamp"] for q in quotes), default=None),
        "verified": verified,
    }
