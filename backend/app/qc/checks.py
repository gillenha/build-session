"""Deterministic QC checks: the hard gate. Each returns a list of issue strings (empty = pass)."""
from datetime import datetime, timezone

from app.verify import verify

MAX_QUOTE_AGE_MINUTES = 15


def quote_age_minutes(quote: dict, now: datetime) -> float:
    ts = datetime.fromisoformat(quote["timestamp"].replace("Z", "+00:00"))
    return (now - ts).total_seconds() / 60


def is_stale(quote: dict, now: datetime) -> bool:
    return quote_age_minutes(quote, now) >= MAX_QUOTE_AGE_MINUTES


def numbers(draft: str, chunks: dict[str, dict], quotes: list[dict]) -> list[str]:
    """Every number in the model's draft must appear in a cited chunk or a quote result."""
    _, problems = verify(draft, chunks, quotes)
    return problems


def freshness(final: str, quotes: list[dict], now: datetime) -> list[str]:
    """A quote 15+ minutes old must be labelled as not current in what the user sees."""
    stale = [q for q in quotes if is_stale(q, now)]
    if stale and "not current" not in final.lower():
        return [f"{q['ticker']} quote is {quote_age_minutes(q, now):.0f} minutes old but the answer "
                "does not say it is not current" for q in stale]
    return []


def sample_label(final: str, quotes: list[dict]) -> list[str]:
    """Any sample_data quote forces a visible sample-data label."""
    sample = [q["ticker"] for q in quotes if q.get("source") == "sample_data"]
    if sample and "sample data" not in final.lower():
        return [f"quote for {', '.join(sample)} is sample data but the answer is not labelled as sample data"]
    return []


def run(draft: str, final: str, chunks: dict[str, dict], quotes: list[dict], now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    return numbers(draft, chunks, quotes) + freshness(final, quotes, now) + sample_label(final, quotes)
