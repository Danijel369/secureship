# Project
SecureShip: a support chat for carrier MockExpress, built for Applied AI Fluency Workshop. Visitors chat without logging in. Parcel questions
require an identity check (first name, last name, address, phone) plus a mock 6-digit code; after that, only that customer's shipments may be shown. Public policy questions are answered by anyone, citing a policy chunk. An admin panel behind Auth0 comes later. All data is synthetic.

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
- `backend/app/`        FastAPI app (`main.py`, `db.py`, `llm/`, ...)
- `backend/tests/`      pytest tests
- `frontend/src/`       React app; `src/api/generated/` is Orval output (do not edit by hand)
- `scripts/`            DB init, seed, (later) ingest; run from `backend/` with `uv run python ../scripts/...`
- `scripts/fixtures/`   demo-identities.json (do not modify)
- `corpus/`, `evals/`   policy documents and provided tests (later; do not modify)
- `docs/`               decisions.md, design/, labs/

# How to run (hybrid dev mode)
1. Ollama running on the host: `curl -s http://localhost:11434/api/tags`
2. Database: `docker compose up -d postgres`
3. Schema + seed: `cd backend && uv run python ../scripts/init_db.py && uv run python ../scripts/seed_data.py`
4. Backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000` (API docs at `/docs`)
5. Frontend (planned): `cd frontend && npm run dev` → http://localhost:3000
6. Tests: `cd backend && uv run pytest`
7. DIAL: connect to the EPAM VPN, then `set -a; source .env; set +a`

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
- All data is synthetic. No real personal data anywhere.

Secrets and cost:
- Never commit `.env` or keys. Hosts, keys, and passwords come from environment variables,
  never hard-coded. If a key is committed: treat it as leaked, escalate, rotate it.
- DIAL has a shared 40 USD allowance: small deployment, low `max_tokens`, and never a
  retry loop without an upper limit.

Model calls:
- Ollama: `stream: false`, `think: false`, temperature and `num_ctx` set explicitly from
  one config place.
- Tool-call `arguments`: DIAL returns a JSON string, Ollama returns an object. Handle both.
- Any loop around model calls or tool calls has a fixed maximum number of rounds.

Working style:
- Use plan mode for any change bigger than a few lines. Show the file list before building.
- Only change the files named in the request. No unrelated refactors.
- Do not add a dependency without asking first.
- Anything the frontend must react to belongs in the response model, so Orval generates it.
  After an API change: run the backend, run `npx orval` in `frontend/`, commit the client.
- Every behavior change comes with a test; run `uv run pytest` before saying it's done.