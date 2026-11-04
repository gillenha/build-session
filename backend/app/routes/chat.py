import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent import chat as run_chat

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    chunk_id: str
    ticker: str
    filing_type: str
    filing_date: str
    page: int
    source_url: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    quote_as_of: str | None
    verified: bool


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> dict:
    try:
        return run_chat(req.session_id, req.message)
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e.__class__.__name__}")
