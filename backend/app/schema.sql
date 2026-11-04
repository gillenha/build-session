CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS filing_chunks (
    id           BIGSERIAL PRIMARY KEY,
    ticker       TEXT NOT NULL,
    filing_type  TEXT NOT NULL,
    filing_date  DATE NOT NULL,
    accession    TEXT NOT NULL,
    source_url   TEXT NOT NULL,
    page         INT  NOT NULL,
    chunk_index  INT  NOT NULL,
    text         TEXT NOT NULL,
    embedding    vector(1536) NOT NULL,
    UNIQUE (accession, chunk_index)
);
CREATE INDEX IF NOT EXISTS filing_chunks_ticker_idx ON filing_chunks (ticker);
CREATE INDEX IF NOT EXISTS filing_chunks_embedding_idx
    ON filing_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chat_messages_session_idx ON chat_messages (session_id, id);
