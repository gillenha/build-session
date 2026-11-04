"""OpenAI text-embedding-3-small (1536 dims)."""
import numpy as np
from openai import OpenAI

from app.config import require

EMBED_MODEL = "text-embedding-3-small"
_client: OpenAI | None = None


def _openai() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=require("OPENAI_API_KEY"))
    return _client


def embed(texts: list[str], batch_size: int = 100) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for i in range(0, len(texts), batch_size):
        resp = _openai().embeddings.create(model=EMBED_MODEL, input=texts[i : i + batch_size])
        out.extend(np.array(d.embedding, dtype=np.float32) for d in resp.data)
    return out
