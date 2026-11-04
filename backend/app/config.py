"""Settings read from the repo-root .env.local (falling back to .env). No defaults for secrets or the model."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")

EDGAR_USER_AGENT = "build-session gillen08@gmail.com"


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var {name} (set it in .env.local)")
    return value


def model() -> str:
    return require("MODEL")


def database_url() -> str:
    return require("DATABASE_URL")


def cors_origins() -> list[str]:
    """Comma-separated CORS_ALLOWED_ORIGINS, e.g. "https://web.up.railway.app". Empty = no cross-origin access."""
    return [o.strip().rstrip("/") for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
