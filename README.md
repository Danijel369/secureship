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

Before you start: Docker Desktop is running, and Ollama is running
(`brew services start ollama` or open the Ollama app; check with `curl -s http://localhost:11434/api/tags`).

## Setup (once)
All commands start from the repository root.
1. `cp .env.example .env`. The defaults work for local development; `DIAL_API_KEY` can stay
   empty until Week 4. Never commit `.env`.
2. `ollama pull qwen3:8b && ollama pull nomic-embed-text`
3. `docker compose up -d postgres && docker compose ps` (wait until postgres shows `healthy`)
4. `(cd backend && uv sync && uv run python ../scripts/init_db.py && uv run python ../scripts/seed_data.py)`
5. `(cd frontend && npm install && echo "VITE_API_URL=http://localhost:8000" > .env.local)`

The seed prints `customers: 27` and shipment counts; it is safe to run again.

## Run
Requires Postgres (`docker compose up -d postgres`) and Ollama running.
- Backend (terminal 1): `cd backend && uv run uvicorn app.main:app --reload --port 8000` → http://localhost:8000/docs
- Frontend (terminal 2): `cd frontend && npm run dev` → http://localhost:3000
- After a backend API change: with the backend running, `cd frontend && npx orval`, then commit the generated client.
- Stop: Ctrl+C in both terminals, then `docker compose stop` (data is kept in the `pgdata` volume).

## Tests
Requires Postgres running with the schema applied (setup step 4). Ollama is not needed: the chat tests mock the model.
`cd backend && uv run pytest` (`test_seed.py` re-runs the idempotent seed).

## Project layout
See `CLAUDE.md`. Design notes, approved plans, and the decision log are in `docs/`.

## Acceptance criteria
To be written for outcomes A–H (public chat, identity, 2FA, verified shipment access,
admin, tools and guardrails, human handoff, policy answers).