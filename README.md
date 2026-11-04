# SecureShip

A support chat for the fictional carrier MockExpress, built for the Applied AI
Fluency Workshop. Anyone can ask public shipping-policy questions. Shipment
details are shown only after the visitor proves who they are (identity details
plus a one-time code), and only for that visitor's own shipments.
All data is synthetic.

## Status: Week 1
- [x] Ollama (`qwen3:8b`, `nomic-embed-text`) and EPAM DIAL reachable from the host
- [ ] Postgres + pgvector running in Docker Compose
- [ ] Backend: `GET /health`, `POST /chat` calling the model and storing each turn
- [ ] Seed data: 3 demo people + generated customers and shipments
- [ ] Frontend chat window using the Orval-generated client

Not built yet: identity verification, the shipment gate, policy retrieval, admin
panel, n8n alert, MCP server. **This week the chat is ungated by design.**

## Prerequisites
macOS (Apple Silicon), Git, Docker Desktop, Python 3.12+ with `uv`, Node 20+, Ollama.
Optional: EPAM VPN + DIAL key for the DIAL runtime.

## Setup
1. `cp .env.example .env` and fill in the values (never commit `.env`).
2. `ollama pull qwen3:8b && ollama pull nomic-embed-text`
3. `docker compose up -d postgres`
4. `cd backend && uv sync`
5. `uv run python ../scripts/init_db.py && uv run python ../scripts/seed_data.py`

## Run
- Backend: `cd backend && uv run uvicorn app.main:app --reload --port 8000` → http://localhost:8000/docs
- Frontend (planned): `cd frontend && npm run dev` → http://localhost:3000
- DIAL runtime: connect to the VPN, set `LLM_PROVIDER=dial` in `.env`

## Tests
`cd backend && uv run pytest`

## Project layout
See `CLAUDE.md`. Design notes and the decision log are in `docs/`.

## Acceptance criteria
To be written for outcomes A–H (public chat, identity, 2FA, verified shipment access,
admin, tools and guardrails, human handoff, policy answers).