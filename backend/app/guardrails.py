"""Input PII redaction and the labels code appends to every answer."""
import re
from datetime import datetime

from app.qc.checks import MAX_QUOTE_AGE_MINUTES, is_stale

# Order matters: more specific patterns first so a card number isn't half-eaten by the account pattern.
_PII_PATTERNS = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    ("ACCOUNT", re.compile(r"\b\d{8,17}\b")),
    ("PHONE", re.compile(r"(?:\+?1[-.\s]?)?\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]

DISCLAIMER = "This is not financial advice."


def redact_pii(text: str) -> str:
    for label, pattern in _PII_PATTERNS:
        text = pattern.sub(f"[REDACTED_{label}]", text)
    return text


def footer(quotes: list[dict], now: datetime) -> str:
    lines = []
    for q in quotes:
        label = f"{q['ticker']} quote as of {q['timestamp']}"
        if is_stale(q, now):
            label += f" — NOT CURRENT (older than {MAX_QUOTE_AGE_MINUTES} minutes)"
        if q.get("source") == "sample_data":
            label += " — SAMPLE DATA, not live market prices"
        lines.append(label + ".")
    lines.append(DISCLAIMER)
    return "\n\n---\n" + "\n".join(lines)
