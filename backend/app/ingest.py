"""Ingest a ticker's latest 10-K and 10-Q into filing_chunks.  Usage: python -m app.ingest AAPL"""
import sys

from app import db, edgar
from app.embeddings import embed

CHUNK_CHARS = 1500
OVERLAP_CHARS = 200
MIN_CHUNK_CHARS = 200  # skip near-empty pages (covers, separators)


def chunk_page(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        piece = text[start : start + CHUNK_CHARS]
        if len(piece) >= MIN_CHUNK_CHARS:
            chunks.append(piece)
        start += CHUNK_CHARS - OVERLAP_CHARS
    return chunks


def ingest(ticker: str) -> list[dict]:
    ticker = ticker.strip().upper()
    db.init_schema()
    summary = []
    for filing in edgar.latest_filings(edgar.cik_for(ticker)):
        rows = [(page_no, text) for page_no, page in enumerate(edgar.pages(filing["url"]), start=1)
                for text in chunk_page(page)]
        vectors = embed([text for _, text in rows])
        with db.pool().connection() as conn:
            conn.execute("DELETE FROM filing_chunks WHERE accession = %s", (filing["accession"],))
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO filing_chunks (ticker, filing_type, filing_date, accession, source_url,
                                                  page, chunk_index, text, embedding)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [(ticker, filing["form"], filing["filing_date"], filing["accession"], filing["url"],
                      page_no, i, text, vec) for i, ((page_no, text), vec) in enumerate(zip(rows, vectors))],
                )
        summary.append({**filing, "chunks": len(rows), "pages": max((p for p, _ in rows), default=0)})
    return summary


if __name__ == "__main__":
    for item in ingest(sys.argv[1]):
        print(f"{item['form']} {item['filing_date']} {item['accession']}: {item['chunks']} chunks, "
              f"{item['pages']} pages  {item['url']}")
