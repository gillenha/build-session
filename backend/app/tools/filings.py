"""search_filings tool: pgvector cosine search over ingested filing chunks."""
from app.db import pool
from app.embeddings import embed

TOP_K = 5
# Cosine similarity floor below which a chunk is treated as not relevant. Tune against real queries.
MIN_SIMILARITY = 0.30

DEFINITION = {
    "name": "search_filings",
    "description": (
        "Search the company's ingested SEC filings (10-K, 10-Q). Returns passages with chunk_id, filing_type, "
        "filing_date, page and text. Cite passages by chunk_id. Returns an error if nothing relevant is found."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"},
            "query": {"type": "string", "description": "What to look for in the filings"},
        },
        "required": ["ticker", "query"],
        "additionalProperties": False,
    },
}


def run(ticker: str, query: str) -> list[dict]:
    ticker = ticker.strip().upper()
    with pool().connection() as conn:
        if conn.execute("SELECT 1 FROM filing_chunks WHERE ticker = %s LIMIT 1", (ticker,)).fetchone() is None:
            raise LookupError(f"No filings have been ingested for '{ticker}'.")
        [vec] = embed([query])
        rows = conn.execute(
            """SELECT id, filing_type, filing_date, page, source_url, text, 1 - (embedding <=> %s) AS similarity
               FROM filing_chunks WHERE ticker = %s ORDER BY embedding <=> %s LIMIT %s""",
            (vec, ticker, vec, TOP_K),
        ).fetchall()
    hits = [
        {"chunk_id": f"C{r[0]}", "ticker": ticker, "filing_type": r[1], "filing_date": r[2].isoformat(), "page": r[3],
         "source_url": r[4], "text": r[5], "similarity": round(float(r[6]), 3)}
        for r in rows if r[6] >= MIN_SIMILARITY
    ]
    if not hits:
        raise LookupError(f"Nothing relevant found in {ticker} filings for: {query}")
    return hits
