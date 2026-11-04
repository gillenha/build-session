"""App wiring only. Each track adds endpoints in its own module under app/routes/."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, db
from app.routes import chat, health, ingest


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_schema()
    yield
    db.close()


app = FastAPI(title="build-session", lifespan=lifespan)
if origins := config.cors_origins():
    # Only the listed front-end origins may call the API from a browser. Unset = same-origin only (local dev).
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(ingest.router)
