"""get_quote tool. Providers implement QuoteProvider; the tool contract stays the same when a live one is added."""
from typing import Protocol

# Fixed sample values. Not market data.
_SAMPLE = {
    "AAPL": {"price": 227.48, "change": 1.36, "change_percent": 0.60, "volume": 48213700},
    "MSFT": {"price": 431.95, "change": -2.11, "change_percent": -0.49, "volume": 19874500},
    "NVDA": {"price": 138.62, "change": 3.04, "change_percent": 2.24, "volume": 231560900},
}
_SAMPLE_TIMESTAMP = "2026-10-30T20:00:00Z"


class QuoteProvider(Protocol):
    def get_quote(self, ticker: str) -> dict:
        """Return {ticker, price, change, change_percent, volume, timestamp, source} or raise LookupError."""
        ...


class SampleQuoteProvider:
    def get_quote(self, ticker: str) -> dict:
        data = _SAMPLE.get(ticker)
        if data is None:
            raise LookupError(f"Unknown ticker '{ticker}'. Sample quotes exist only for {', '.join(_SAMPLE)}.")
        return {"ticker": ticker, **data, "timestamp": _SAMPLE_TIMESTAMP, "source": "sample_data"}


provider: QuoteProvider = SampleQuoteProvider()

DEFINITION = {
    "name": "get_quote",
    "description": (
        "Get the latest stock quote for a ticker: price, change, change_percent, volume, timestamp, source. "
        "Returns an error for unknown tickers. If source is 'sample_data' the values are not live."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {"ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"}},
        "required": ["ticker"],
        "additionalProperties": False,
    },
}


def run(ticker: str) -> dict:
    return provider.get_quote(ticker.strip().upper())
