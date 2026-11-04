# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An agent for financial advisors preparing for client conversations: it answers questions about a stock using a quote tool and the company's SEC filings, with every number checked before it reaches the advisor. A wrong number in front of a client is the core risk this design guards against.

## API contract

- `POST /chat` — body `{session_id, message}` → `{answer, citations[], quote_as_of, verified, issues[], attempts}`
  - `citations[]`: the filing chunks the answer cites (ticker, filing type, filing date, page, source URL, snippet)
  - `quote_as_of`: timestamp of the quote used, or `null`
  - `verified`: `true` only if the quality-check agent passed the final answer (below)
  - `issues[]`: the QC reasons when `verified` is `false` (each prefixed `check:` or `review:`); empty on pass
  - `attempts`: `1`, or `2` when the first draft failed QC and was retried
- `POST /ingest` — body `{ticker}`; pulls the most recent 10-K and 10-Q from SEC EDGAR, chunks, embeds, stores
- `GET /health`

## Stack

- Front end: React + Vite + Tailwind
- Backend: Python FastAPI
- Database: Postgres with pgvector on Neon
- LLM: Anthropic. The model ID comes from the `MODEL` env var — never hardcode a model ID.
- Embeddings: OpenAI `text-embedding-3-small`, stored as `vector(1536)`

## Tools

Tools are called by the model through Anthropic tool use. App code never calls them directly to build an answer.

1. `get_quote(ticker)` → price, change, volume, timestamp. Implemented behind a `QuoteProvider` interface. The current provider is a stub returning fixed sample data for AAPL, MSFT, NVDA and an error for any other ticker; its results carry `"source": "sample_data"`, and the answer must tell the user the quote is sample data, not live. A real provider must plug into the same interface without changing the tool contract.
2. `search_filings(ticker, query)` → pgvector similarity search over ingested filing chunks; returns text, filing type, filing date, page.

## Guardrails

- Redact PII from user input before it reaches the model or the database.
- Refuse when the ticker is unknown or retrieval returns nothing relevant.
- Claims drawn from filings must carry citations.
- Quote data is labeled with its timestamp.
- Every answer ends with a "not financial advice" disclaimer.
- EDGAR requests send `User-Agent: build-session gillen08@gmail.com` (SEC requirement).

## Verification (quality-check agent, `backend/app/qc/`)

Runs after the answering agent drafts a reply and before it is returned. Input: user question, draft, raw tool results.

1. Deterministic checks (`qc/checks.py`) — the hard gate:
   - every number in the draft appears in a cited chunk or a `get_quote` result (`verify.py`);
   - a quote 15+ minutes old must be labelled "not current" in the final text;
   - a `sample_data` quote must be labelled "sample data" in the final text.
2. Only if those pass: LLM claim review (`qc/review.py`) — fresh context, no tools, structured `{verdict, issues}`. It can add failures but never overrides a deterministic failure. The LLM never validates its own math.

Code (not the model) appends the quote timestamp, "NOT CURRENT", "SAMPLE DATA" and disclaimer labels; the checks verify they are present.
On fail: one retry with the issues passed back to the answering agent. A second fail returns `verified: false` with `issues`, shown in the UI.

## Memory

Conversation history lives in a Postgres table keyed by `session_id`.

## Environment

`.env.local` (gitignored; Neon writes the database vars) holds the real values. `.env.example` lists names only and is the only tracked env file — never put values in it, never commit `.env*`.

Variables: `ANTHROPIC_API_KEY`, `MODEL`, `OPENAI_API_KEY`, `QUOTE_API_KEY` (unused until a live quote provider exists), `DATABASE_URL` (pooled), plus Neon's `DATABASE_URL_UNPOOLED` and `NEON_BRANCH`.

## Neon

- `neon.ts` is the declarative Neon config; `.neon` (gitignored) links the repo to project `square-glitter-34016223`, branch `production`.
- `neon deploy` applies `neon.ts` and pulls env vars into `.env.local`; `neon env pull` refreshes them only; `neon config plan` previews; `neon checkout <name> --create` makes a dev branch.

## Tracks and file ownership

Work is split into tracks that never edit the same file. Stay inside the track you are working on.

- **Backend:** `backend/app/{agent,prompts,verify,guardrails,memory}.py`, `backend/app/tools/`, `backend/app/qc/`, `backend/app/routes/chat.py`, `backend/app/schema/chat.sql`, `backend/tests/`
- **Ingestion:** `backend/app/{edgar,ingest,embeddings}.py`, `backend/app/routes/ingest.py`, `backend/app/schema/filings.sql`
- **Front end:** `frontend/` (talks to the backend only over HTTP)
- **Evals:** `evals/` (talks to the backend over HTTP; component evals may import `app.qc` read-only)
- **Frozen, change only with user sign-off:** `backend/app/{config,db,main}.py`, `backend/app/routes/health.py`, `backend/requirements.txt`, and the API contract above.

## Running

- Backend: `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000` (API docs at `/docs`)
- Ingest a ticker: `$env:PYTHONPATH='backend'; backend\.venv\Scripts\python.exe -m app.ingest AAPL`
- Set up the venv: `uv venv backend\.venv --python 3.12; uv pip install --python backend\.venv\Scripts\python.exe -r backend\requirements.txt`

## Working rules

- After each change, explain it in plain language.
- Keep files small and single-purpose.
- Build in thin vertical slices; stop and show the user before expanding scope.
