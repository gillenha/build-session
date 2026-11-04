from fastapi import APIRouter

from app import db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    with db.pool().connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}
