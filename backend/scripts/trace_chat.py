"""Trace one question through the /chat code path, printing every stage of the agent orchestration.

Usage (from the repo root):
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\trace_chat.py "What is Microsoft trading at now?"
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\trace_chat.py --inject-bad-number "What is Microsoft trading at now?"

Observability only: app code is not modified. This script wraps the app's functions and Anthropic clients at
runtime, then calls the real route handler (app.routes.chat.chat). --inject-bad-number is a test harness that
appends a number found in no tool result to the answering agent's first final reply.
"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

import app.agent as agent  # noqa: E402
import app.memory as memory  # noqa: E402
import app.qc as qc  # noqa: E402
import app.qc.checks as checks  # noqa: E402
from app.routes.chat import ChatRequest  # noqa: E402
from app.routes.chat import chat as chat_route  # noqa: E402

review_mod = sys.modules["app.qc.review"]  # app.qc.review the *attribute* is the function; this is the module
INJECTED_TEXT = " Microsoft's market capitalization is $9,876 billion."

_step = 0
_qc_state = {"reviewer_called": False}


def _rel(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return path


def _where(fn) -> str:
    return f"{_rel(fn.__code__.co_filename)}:{fn.__code__.co_firstlineno}"


def _caller(depth: int = 2) -> str:
    f = sys._getframe(depth)
    return f"{_rel(f.f_code.co_filename)}:{f.f_lineno}"


def emit(stage: str, location: str, lines: list[str] | None = None) -> None:
    global _step
    _step += 1
    print(f"\n[{_step:02d}] {stage}  ({location})")
    for line in lines or []:
        print(f"     {line}")


def _short(text: str, n: int) -> str:
    text = str(text).replace("\n", "\\n")
    return text if len(text) <= n else text[:n] + f"... [{len(text) - n} more chars]"


# ---- LLM clients -------------------------------------------------------------------------------------------

class TracedMessages:
    def __init__(self, real, role: str, inject: bool):
        self._real, self._role, self._inject = real, role, inject

    def _trace(self, method: str, kw: dict, call):
        caller = _caller(3)
        tools = [t["name"] for t in kw.get("tools", [])] or ["(none)"]
        t0 = time.perf_counter()
        response = call(**kw)
        ms = (time.perf_counter() - t0) * 1000
        if self._inject and response.stop_reason != "tool_use":
            response = self._inject_number(response)
        blocks = [b.type for b in response.content]
        text = " ".join(b.text for b in response.content if b.type == "text")
        lines = [
            f"role:          {self._role}",
            f"api:           client.messages.{method}",
            f"model:         {kw['model']}",
            f"system[:300]:  {_short(kw.get('system', ''), 300)}",
            f"tools:         {', '.join(tools)}",
            f"messages in context: {len(kw['messages'])}  (roles: {' > '.join(m['role'] for m in kw['messages'])})",
            f"latency:       {ms:.0f} ms",
            f"stop_reason:   {response.stop_reason}",
            f"content:       {blocks}",
        ]
        if text:
            lines.append(f"text:          {_short(text, 400)}")
        for b in response.content:
            if b.type == "tool_use":
                lines.append(f"requests tool: {b.name}({json.dumps(b.input)})")
        emit(f"LLM CALL - {self._role}", caller, lines)
        return response

    def _inject_number(self, response):
        self._inject = False
        content = list(response.content)
        idx = max(i for i, b in enumerate(content) if b.type == "text")
        content[idx] = content[idx].model_copy(update={"text": content[idx].text + INJECTED_TEXT})
        emit("TEST HARNESS - injected unsupported number into answering agent's reply", "backend/scripts/trace_chat.py",
             [f"appended: {INJECTED_TEXT.strip()!r}"])
        return response.model_copy(update={"content": content})

    def create(self, **kw):
        return self._trace("create", kw, self._real.create)

    def parse(self, **kw):
        return self._trace("parse", kw, self._real.parse)


class TracedClient:
    def __init__(self, real, role: str, inject: bool = False):
        self.messages = TracedMessages(real.messages, role, inject)


# ---- function wrappers -------------------------------------------------------------------------------------

def wrap(module, name: str, describe):
    orig = getattr(module, name)

    def wrapper(*args, **kwargs):
        caller = _caller()
        result = orig(*args, **kwargs)
        stage, lines = describe(args, kwargs, result)
        emit(stage, f"called at {caller} -> {name} defined at {_where(orig)}", lines)
        return result

    setattr(module, name, wrapper)


def _tool(args, _kw, result):
    name, tool_args = args
    data, _content, is_error = result
    lines = [f"name:   {name}", f"args:   {json.dumps(tool_args)}", f"error:  {is_error}"]
    if is_error:
        lines.append(f"result: {_content}")
    elif name == "search_filings":
        for hit in data:
            lines.append(f"result: {hit['chunk_id']} {hit['filing_type']} {hit['filing_date']} p.{hit['page']} "
                         f"sim={hit['similarity']}  {_short(hit['text'], 160)}")
    else:
        lines.append(f"result: {json.dumps(data)}")
    return "TOOL CALL", lines


def _check(label):
    def describe(_args, _kw, issues):
        return f"HARD GATE - {label}: {'FAIL' if issues else 'PASS'}", [f"why: {i}" for i in issues] or ["no issues"]
    return describe


def _review(args, _kw, result):
    _qc_state["reviewer_called"] = True
    return "REVIEWER VERDICT", [f"verdict: {result.verdict}"] + [f"issue:   {i}" for i in result.issues]


def _run_qc_wrap():
    orig = agent.run_qc

    def wrapper(*args, **kwargs):
        caller = _caller()
        _qc_state["reviewer_called"] = False
        emit("QC AGENT START", f"called at {caller} -> run_qc defined at {_where(orig)}",
             ["input: question, draft, final (draft + code labels), quotes, chunks"])
        result = orig(*args, **kwargs)
        lines = [f"verdict: {result['verdict']}"] + [f"issue:   {i}" for i in result["issues"]]
        if not _qc_state["reviewer_called"]:
            lines.append("reviewer: NOT called (hard gate failed first)")
        emit("QC AGENT RESULT", _where(orig), lines)
        return result

    agent.run_qc = wrapper


def install(inject: bool) -> None:
    agent._client = TracedClient(agent._anthropic(), "answering agent", inject)
    review_mod._client = TracedClient(review_mod._anthropic(), "reviewer")
    wrap(agent, "redact_pii", lambda a, k, r: ("INPUT GUARD - redact_pii", [f"in:  {a[0]!r}", f"out: {r!r}"]))
    wrap(memory, "load", lambda a, k, r: ("MEMORY LOAD", [f"session: {a[0]}", f"messages loaded: {len(r)}"]))
    wrap(agent, "run_tool", _tool)
    wrap(agent, "footer", lambda a, k, r: ("CODE LABELS - footer appended", [_short(r.strip(), 300)]))
    _run_qc_wrap()
    wrap(checks, "numbers", _check("numbers in tool results"))
    wrap(checks, "freshness", _check("quote under 15 minutes old or labelled not current"))
    wrap(checks, "sample_label", _check("sample_data labelled"))
    wrap(qc, "review", _review)  # run_qc looks up `review` in app.qc's globals, so patch it there
    wrap(agent, "_qc_feedback", lambda a, k, r: ("RETRY - exact message passed back to answering agent",
                                                 r.splitlines()))
    wrap(memory, "save_turn", lambda a, k, r: ("MEMORY SAVE", [f"session: {a[0]}", f"assistant text: {_short(a[2], 200)}"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--inject-bad-number", action="store_true")
    args = parser.parse_args()

    install(args.inject_bad_number)
    session = f"trace-{uuid.uuid4().hex[:8]}"
    emit("REQUEST", f"{_rel(chat_route.__code__.co_filename)}:{chat_route.__code__.co_firstlineno} (route handler, no HTTP)",
         [f"session_id: {session}", f"message: {args.question!r}"])
    out = chat_route(ChatRequest(session_id=session, message=args.question))
    emit("FINAL OUTPUT", "returned by route handler", [
        f"verified: {out['verified']}", f"attempts: {out['attempts']}", f"issues:   {out['issues']}",
        f"citations: {[c['chunk_id'] + ' p.' + str(c['page']) for c in out['citations']]}",
        f"answer:   {_short(out['answer'], 600)}",
    ])


if __name__ == "__main__":
    main()
