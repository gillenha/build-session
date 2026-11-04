"""Conversation history in Postgres, keyed by session_id. Stores only final user/assistant text."""
import re

from app.db import pool

HISTORY_LIMIT = 20


def load(session_id: str) -> list[dict]:
    with pool().connection() as conn:
        rows = conn.execute(
            """SELECT role, content FROM (
                   SELECT id, role, content FROM chat_messages WHERE session_id = %s ORDER BY id DESC LIMIT %s
               ) recent ORDER BY id""",
            (session_id, HISTORY_LIMIT),
        ).fetchall()
    messages = [{"role": r, "content": c} for r, c in rows]
    # The API requires the first message to be from the user.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


APP_NOTE_RE = re.compile(r"\n*\[app note:[^\]]*\]\s*")


def strip_app_notes(text: str) -> str:
    """The model sometimes imitates the note it sees in history; remove any it writes."""
    return APP_NOTE_RE.sub("\n", text).strip()


def tool_note(calls: list[str]) -> str:
    return f"\n\n[app note: tools run this turn: {'; '.join(calls) or 'none'}]"


def save_turn(session_id: str, user_text: str, assistant_text: str) -> None:
    with pool().connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, 'user', %s), (%s, 'assistant', %s)",
            (session_id, user_text, session_id, assistant_text),
        )
