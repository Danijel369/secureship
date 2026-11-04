# SecureShip

A support chat for the fictional carrier MockExpress, built for the Applied AI
Fluency Workshop. Anyone can ask public shipping-policy questions. Shipment
details are shown only after the visitor proves who they are (identity details
plus a one-time code), and only for that visitor's own shipments.
All data is synthetic.

## Status: Week 1
- [x] Ollama (`qwen3:8b`, `nomic-embed-text`) and EPAM DIAL reachable from the host
- [x] Postgres + pgvector running in Docker Compose
- [x] Backend: `GET /health`, `POST /chat` calling Ollama and storing each turn in a JSONB transcript
- [x] Seed data: 3 demo people + generated data (27 customers, 50 shipments), safe to re-run
- [x] Frontend chat window using the Orval-generated client (browser stores only the session id)
- [ ] Temperature and context window chosen and tested (foundations lab)
- [ ] System prompt with the grounding rule

Not built yet: identity verification, the shipment gate, policy retrieval, admin
panel, n8n alert, MCP server, DIAL runtime switch. **This week the chat is ungated by design.**

## Prerequisites
macOS (Apple Silicon), Git, Docker Desktop, Python 3.12+ with `uv`, Node 20+, Ollama.
Optional: EPAM VPN + DIAL key (DIAL is used from Week 4).

## Setup
1. `cp .env.example .env` and fill in the values (never commit `.env`).
2. `ollama pull qwen3:8b && ollama pull nomic-embed-text`
3. `docker compose up -d postgres`
4. `cd backend && uv sync`
5. `uv run python ../scripts/init_db.py && uv run python ../scripts/seed_data.py`
6. `cd ../frontend && npm install`
7. Create `frontend/.env.local` with `VITE_API_URL=http://localhost:8000` (not committed).

## Run
- Backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000` → http://localhost:8000/docs
- Frontend: `cd frontend && npm run dev` → http://localhost:3000
- After a backend API change: with the backend running, `cd frontend && npx orval`, then commit the generated client.

## Tests
Postgres must be running and the schema applied.
`cd backend && uv run pytest` (chat tests mock the model; `test_seed.py` re-runs the idempotent seed).

## Project layout
See `CLAUDE.md`. Design notes, approved plans, and the decision log are in `docs/`.

## Acceptance criteria
To be written for outcomes A–H (public chat, identity, 2FA, verified shipment access,
admin, tools and guardrails, human handoff, policy answers).