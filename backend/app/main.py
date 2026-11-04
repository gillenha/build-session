"""App wiring only. Each track adds endpoints in its own module under app/routes/."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.routes import chat, health, ingest


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_schema()
    yield
    db.close()


app = FastAPI(title="build-session", lifespan=lifespan)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(ingest.router)
