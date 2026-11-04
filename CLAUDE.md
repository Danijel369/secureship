# Project
SecureShip: a support chat for carrier MockExpress, built for the Applied AI Fluency Workshop.
Visitors chat without logging in. Parcel questions require an identity check (first name,
last name, address, phone) plus a mock 6-digit code; after that, only that customer's
shipments may be shown. Public policy questions are answered for anyone, citing a policy
chunk. An admin panel behind Auth0 comes later. All data is synthetic.

Status: Week 1 (setup, backend skeleton, seed, first live chat). The access gate
is NOT built yet; ungated shipment answers are expected this week.
(Update this line each week.)

# Stack
- Backend: Python 3.12, FastAPI, uv, psycopg, httpx (in `backend/`)
- Frontend: React + TypeScript + Vite, React Query, Orval-generated client (in `frontend/`)
- Database: Postgres 16 + pgvector, Docker Compose service `postgres`
- Chat runtime: Ollama `qwen3:8b` (primary); EPAM DIAL `gpt-4.1-mini-2025-04-14` (secondary, VPN only)
- Embeddings: Ollama `nomic-embed-text` (768 dims). Embeddings never switch runtime.
- Transport: HTTP (no WebSockets)
- Later: LangGraph orchestrator, n8n workflow, Auth0 (admin only), policy MCP server

# Layout
- `backend/app/`        FastAPI app (`main.py`, `config.py`, `db.py`, `schema.sql`, `llm/`, ...; flat layout, no `backend/src/`)
- `backend/tests/`      pytest tests
- `frontend/src/`       React app; `src/api/generated/` is Orval output (do not edit by hand)
- `scripts/`            DB init, seed, (later) ingest; run from `backend/` with `uv run python ../scripts/...`
- `scripts/fixtures/`   demo-identities.json (do not modify)
- `corpus/`, `evals/`   policy documents and provided tests (later; do not modify)
- `docs/`               decisions.md, design/, labs/
- `docs/plans/`         approved Claude Code plans, saved before building (Jira evidence)

# How to run (hybrid dev mode)
1. Ollama running on the host: `curl -s http://localhost:11434/api/tags`
2. Database: `docker compose up -d postgres`
3. Schema + seed: `cd backend && uv run python ../scripts/init_db.py && uv run python ../scripts/seed_data.py`
4. Backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000` (API docs at `/docs`)
5. Frontend (planned): `cd frontend && npm run dev` → http://localhost:3000
6. Tests (Postgres must be running, schema applied): `cd backend && uv run pytest`
7. DIAL: connect to the EPAM VPN first.

Environment: `.env` lives in the repo root. The backend loads it via python-dotenv in
`backend/app/config.py` (resolved relative to that file, never overriding variables already set).
For manual curl calls, run `set -a; source .env; set +a` from the repo root.

Addresses: processes on the host use `localhost` (Ollama :11434, Postgres :5432).
Containers use `host.docker.internal:11434` for Ollama and `postgres:5432` for the DB.
The browser always reaches the backend at `localhost:8000`.

# Rules that must not break
Access and privacy:
- Access rules are enforced in backend code (route/tool layer), never only in a prompt.
  A prompt cannot defend against prompt injection.
- Shipment data is read only through one gated function that receives the server-side
  session and uses the session's customer id. It never accepts a customer id from the
  model, the request body, or the user's text.
- The frontend holds only the session id: no verified flag, no customer id, no keys.
  Only `VITE_` variables reach the browser, and they are public.
- Session ids are generated server-side with `secrets.token_urlsafe(32)`. Never accept a
  client-chosen id for a new session.
- Identity failures use neutral copy ("We couldn't verify that."), never "no customer found".
- Never log names, addresses, phone numbers, codes, or message content. Log session id
  and state only.
- The `chat_session.transcript` column is the one deliberate place message content is
  stored. It is not a log; do not copy transcripts elsewhere.
- Exception (from Week 2): the mock 2FA code is printed to the dev console only, never
  written to a log file or sent to the model.
- All data is synthetic. No real personal data anywhere.

Database:
- Schema (`backend/app/schema.sql`) must always start with `CREATE EXTENSION IF NOT EXISTS vector;`.
- Every schema statement is re-runnable (`IF NOT EXISTS`); never `DROP` in schema or init.
- `scripts/init_db.py` must be idempotent and safe to run multiple times without failing.
- Tests use the dev database from `DATABASE_URL` and delete only the rows they create.
  Exception: `tests/test_seed.py` re-runs the seed, which is idempotent and leaves the
  seeded state unchanged. Tests never truncate tables or drop anything.

Secrets and cost:
- Never commit `.env` or keys. Hosts, keys, and passwords come from environment variables,
  never hard-coded. If a key is committed: treat it as leaked, escalate, rotate it.
- DIAL has a shared 40 USD allowance: small deployment, low `max_tokens`, and never a
  retry loop without an upper limit.

Model calls:
- Ollama: `stream: false`, `think: false`, temperature and `num_ctx` set explicitly from
  one config place (`backend/app/config.py`).
- Send the model only `{role, content}` (plus tool fields when needed); stored metadata
  such as timestamps is never sent.
- Tool-call `arguments`: DIAL returns a JSON string, Ollama returns an object. Handle both.
- Any loop around model calls or tool calls has a fixed maximum number of rounds.

Working style:
- Use plan mode for any change bigger than a few lines. Show the file list before building.
- After a plan is approved, save it to `docs/plans/<name>.md` before writing code.
- Only change the files named in the request. No unrelated refactors.
- Do not add a dependency without asking first.
- Anything the frontend must react to belongs in the response model, so Orval generates it.
  After an API change: run the backend, run `npx orval` in `frontend/`, commit the client.
- Every behavior change comes with a test; run `uv run pytest` before saying it's done.