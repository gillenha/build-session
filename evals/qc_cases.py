"""Eval cases for the quality-check agent. Each feeds run_qc a hand-built draft and tool results."""
from datetime import datetime, timedelta, timezone

NOW = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)

_LIVE_MSFT = {"ticker": "MSFT", "price": 431.95, "change": -2.11, "change_percent": -0.49, "volume": 19874500,
              "source": "yfinance", "timestamp": (NOW - timedelta(hours=2)).isoformat().replace("+00:00", "Z")}
_FRESH_MSFT = {**_LIVE_MSFT, "timestamp": (NOW - timedelta(minutes=3)).isoformat().replace("+00:00", "Z")}
_CHUNK = {"C1": {"chunk_id": "C1", "ticker": "AAPL", "filing_type": "10-K", "filing_date": "2026-11-03", "page": 55,
                 "source_url": "https://www.sec.gov/", "text": "Total net sales were $478,834 million in 2026, "
                 "compared to $416,161 million in 2025. iPhone net sales were $254,098 million."}}

CASES = [
    {
        "name": "stale quote without 'not current' label",
        "question": "What is Microsoft trading at now?",
        "draft": "MSFT is trading at $431.95, down $2.11 (0.49%).",
        # Simulates a labelling regression: the footer shows the timestamp but not the staleness warning.
        "final_suffix": "\n\n---\nMSFT quote as of 2026-11-04T13:00:00Z.\nThis is not financial advice.",
        "quotes": [_LIVE_MSFT], "chunks": {},
        "expect": "fail", "expect_issue": "check: MSFT quote is 120 minutes old",
    },
    {
        "name": "number not in source",
        "question": "What were Apple's net sales last year?",
        "draft": "Apple's total net sales were $512,000 million in fiscal 2026 [C1].",
        "final_suffix": "\n\n---\nThis is not financial advice.",
        "quotes": [], "chunks": _CHUNK,
        "expect": "fail", "expect_issue": "check: number not found in evidence: $512,000",
    },
    {
        "name": "unsupported claim (numbers are fine, the cause is invented)",
        "question": "What were Apple's net sales last year?",
        "draft": "Apple's total net sales were $478,834 million in fiscal 2026 [C1], driven by record "
                 "Vision Pro demand in China, which management expects to double next year.",
        "final_suffix": "\n\n---\nThis is not financial advice.",
        "quotes": [], "chunks": _CHUNK,
        "expect": "fail", "expect_issue": "review:",
    },
    {
        "name": "control: supported answer with fresh quote passes",
        "question": "MSFT price and Apple net sales?",
        "draft": "MSFT is at $431.95, down $2.11 (0.49%). Apple's total net sales were $478,834 million "
                 "in fiscal 2026 [C1].",
        "final_suffix": "\n\n---\nMSFT quote as of 2026-11-04T14:57:00Z.\nThis is not financial advice.",
        "quotes": [_FRESH_MSFT], "chunks": _CHUNK,
        "expect": "pass", "expect_issue": None,
    },
]
