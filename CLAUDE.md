# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An agent for financial advisors preparing for client conversations: it answers questions about a stock using a quote tool and the company's SEC filings, with every number checked before it reaches the advisor. A wrong number in front of a client is the core risk this design guards against.

## API contract

- `POST /chat` — body `{session_id, message}` → `{answer, citations[], quote_as_of, verified}`
  - `citations[]`: the filing chunks the answer cites (ticker, filing type, filing date, page, source URL, snippet)
  - `quote_as_of`: timestamp of the quote used, or `null`
  - `verified`: result of the deterministic number check (below)
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

## Verification

Deterministic Python checks that every number in the answer appears in a cited chunk or in a `get_quote` result; the result sets `verified`. The LLM never validates its own math. Labels the code appends itself (sample-data notice, quote timestamp, disclaimer) are added after the check.

## Memory

Conversation history lives in a Postgres table keyed by `session_id`.

## Environment

`.env.local` (gitignored; Neon writes the database vars) holds the real values. `.env.example` lists names only and is the only tracked env file — never put values in it, never commit `.env*`.

Variables: `ANTHROPIC_API_KEY`, `MODEL`, `OPENAI_API_KEY`, `QUOTE_API_KEY` (unused until a live quote provider exists), `DATABASE_URL` (pooled), plus Neon's `DATABASE_URL_UNPOOLED` and `NEON_BRANCH`.

## Neon

- `neon.ts` is the declarative Neon config; `.neon` (gitignored) links the repo to project `square-glitter-34016223`, branch `production`.
- `neon deploy` applies `neon.ts` and pulls env vars into `.env.local`; `neon env pull` refreshes them only; `neon config plan` previews; `neon checkout <name> --create` makes a dev branch.

## Working rules

- After each change, explain it in plain language.
- Keep files small and single-purpose.
- Build in thin vertical slices; stop and show the user before expanding scope.
