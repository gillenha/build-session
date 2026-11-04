"""Postgres connection pool (Neon pooled URL) with pgvector types registered."""
from pathlib import Path

from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.config import database_url

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        # prepare_threshold=None: Neon's pooled endpoint is PgBouncer, so skip server-side prepared statements.
        _pool = ConnectionPool(
            database_url(), min_size=1, max_size=5, configure=register_vector,
            kwargs={"prepare_threshold": None}, open=True,
        )
    return _pool


def init_schema() -> None:
    """Run every schema/*.sql file (each track owns its own file; all are idempotent)."""
    with pool().connection() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        for path in sorted((Path(__file__).parent / "schema").glob("*.sql")):
            conn.execute(path.read_text())


def close() -> None:
    if _pool is not None:
        _pool.close()
