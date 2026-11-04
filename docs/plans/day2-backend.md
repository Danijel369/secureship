# Plan: Build Initial FastAPI Backend Skeleton

## Context

Building the Week 1 FastAPI backend skeleton for SecureShip, a support chat application for carrier MockExpress. This is the foundation for a chat system where visitors can ask questions without logging in, and later (Week 2+) will add identity verification for shipment queries.

**Current State**: Empty backend skeleton exists with `__init__.py` files in `backend/app/`, `backend/app/llm/`, and `backend/tests/`. All dependencies (FastAPI, psycopg, python-dotenv, httpx, pytest) are already defined in `pyproject.toml`. Docker Compose runs Postgres 16 + pgvector on localhost:5432, and Ollama runs on localhost:11434.

**Goal**: Create a working FastAPI backend with:
- Configuration loading from `.env` in repo root
- Database schema for customers, shipments, packages, and chat sessions
- Chat endpoint that stores conversation history in JSONB and calls Ollama
- Health check endpoint
- Test suite with mocked Ollama and real Postgres

**Why**: This establishes the backend foundation for the chat interface. Week 1 is intentionally ungated (no identity verification yet) - the focus is on getting basic chat turns working with persistent storage.

## Implementation Plan

### Files to Create

1. **backend/app/config.py** - Environment variable loading and configuration constants
2. **backend/app/db.py** - Database connection helper using psycopg 3
3. **backend/app/schema.sql** - Database schema with pgvector, customer, shipment, package, chat_session tables
4. **scripts/init_db.py** - Idempotent schema initialization script
5. **backend/app/llm/client.py** - Ollama chat client with explicit timeout and configuration
6. **backend/app/main.py** - FastAPI application with /health and /chat endpoints
7. **backend/tests/test_chat.py** - Test suite with 4 tests (two turns, unknown session, no session, health check)

### Key Implementation Details

**Configuration (backend/app/config.py)**:
- Load `.env` from repo root: `Path(__file__).resolve().parents[2] / ".env"`
- Use `load_dotenv(override=False)` to never override already-set variables
- Expose: `DATABASE_URL`, `OLLAMA_HOST`, `CHAT_MODEL = "qwen3:8b"`, `TEMPERATURE = 0.2`, `NUM_CTX = 8192`
- Raise `RuntimeError` with clear message at import time if DATABASE_URL or OLLAMA_HOST missing
- All config constants are module-level (no class/function)

**Database Connection (backend/app/db.py)**:
- Simple `get_connection()` helper that returns `psycopg.connect(DATABASE_URL)`
- Caller uses as context manager: `with get_connection() as conn:`
- psycopg 3 auto-commits on successful context exit, auto-rolls back on exception
- No connection pool for Week 1 (add later if needed)

**Schema (backend/app/schema.sql)**:
- MUST start with: `CREATE EXTENSION IF NOT EXISTS vector;`
- All statements use `IF NOT EXISTS` for idempotency
- Tables: customer (id, first_name, last_name, phone_number UNIQUE, address), shipment (id, customer_id FK, tracking_number UNIQUE, status CHECK, exception_reason NULL, carrier, origin, destination, estimated_delivery date, last_update timestamptz), package (id, shipment_id FK, description, weight_kg numeric(8,2), declared_value numeric(10,2)), chat_session (id text PRIMARY KEY, customer_id FK NULL, state text DEFAULT 'anonymous', transcript jsonb DEFAULT '[]'::jsonb, created_at timestamptz DEFAULT now())
- Index on shipment(customer_id)
- No DROP or DELETE statements

**Schema Init (scripts/init_db.py)**:
- Read `backend/app/schema.sql` and execute entire content
- Path resolution: script in scripts/, must find backend/app/schema.sql
- Use context manager for connection: auto-commits on success
- Safe to run multiple times (idempotent)
- Exit code 1 on failure with clear error message to stderr
- Run as: `cd backend && uv run python ../scripts/init_db.py`

**Ollama Client (backend/app/llm/client.py)**:
- Function: `chat_ollama(messages: list[dict]) -> str`
- POST to `{OLLAMA_HOST}/api/chat` with payload: `{"model": CHAT_MODEL, "messages": messages, "stream": False, "think": False, "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX}}`
- Explicit 60-second timeout: `httpx.post(..., timeout=60.0)`
- Call `raise_for_status()` to throw on 4xx/5xx
- No retry loops
- Return `response.json()["message"]["content"]`

**FastAPI App (backend/app/main.py)**:
- FastAPI titled "SecureShip" with CORSMiddleware: `allow_origins=["http://localhost:3000"]`, `allow_methods=["GET", "POST"]`, `allow_headers=["Content-Type"]`
- Request model: `ChatRequest(session_id: str | None = Field(default=None, max_length=64), message: str = Field(min_length=1, max_length=2000))`
- Response model: `ChatReply(session_id: str, reply: str)`
- GET /health → `{"status": "ok"}`
- POST /chat logic:
  1. **Short connection (a)**: Look up session (if session_id provided and non-empty) and read transcript, then close connection
  2. **Call model (b)**: Build messages from transcript (strip "at" field), append user message with timestamp `request_at = datetime.now(timezone.utc).isoformat()`, call `chat_ollama(messages)` with no DB connection open
  3. **On model failure**: Log session_id only, return HTTP 502 with neutral message ("The chat service is temporarily unavailable. Please try again."), do NOT create row or modify transcript
  4. **On model success (c)**: One transaction:
     - If session_id was None, empty, or not found: INSERT new row with `new_id = secrets.token_urlsafe(32)`, both turns in transcript
     - If session_id was found: UPDATE that row, append both turns to transcript
     - User turn timestamp: `request_at` (when request arrived)
     - Assistant turn timestamp: `datetime.now(timezone.utc).isoformat()` (when reply returned)
     - Format: `[{"role": "user", "content": req.message, "at": request_at}, {"role": "assistant", "content": assistant_reply, "at": reply_at}]`
  5. Return `ChatReply(session_id=final_session_id, reply=assistant_reply)`
- Logging: only session_id and error types, NEVER message content

**Tests (backend/tests/test_chat.py)**:
- Use `TestClient` from FastAPI
- Mock `app.main.chat_ollama` (where imported, not defined)
- Use real Postgres from DATABASE_URL
- `cleanup_test_sessions` fixture with `autouse=True`: tracks session IDs, deletes only those rows in teardown using `DELETE FROM chat_session WHERE id = ANY(%s)`
- Test 1: Two turns in same session → verify same session_id returned, transcript has 4 entries [user, assistant, user, assistant] with role/content/at
- Test 2: Unknown session_id → verify new different session_id returned, fake id never inserted
- Test 3: No session_id → verify new session_id returned and row exists in DB
- Test 4: GET /health → verify `{"status": "ok"}`
- Test 5: Model failure → chat_ollama raises exception → returns 502, no new chat_session row created, and existing session's transcript unchanged

### Critical Files

1. `backend/app/config.py` - Foundation for all configuration
2. `backend/app/main.py` - Core FastAPI app with chat logic
3. `backend/app/schema.sql` - Database structure
4. `backend/app/db.py` - Database connection pattern
5. `backend/app/llm/client.py` - Ollama integration
6. `scripts/init_db.py` - Schema initialization
7. `backend/tests/test_chat.py` - Verification of correctness

### Session ID Pattern

- **New session**: If `session_id` is `None`, empty string (`""`), or not found in DB → generate new ID with `secrets.token_urlsafe(32)` and INSERT new row
- **Existing session**: If `session_id` found in DB → load transcript from that row
- **Security**: Never INSERT a client-provided session_id. Client-provided IDs are used only for lookup; if lookup fails, generate new server-side ID

### Transcript Storage Pattern

- JSONB array of objects: `[{"role": "user"|"assistant", "content": "...", "at": "ISO8601"}, ...]`
- Send to model: strip "at" field, send only `{role, content}`
- Store turns: append both user and assistant turns in single transaction using PostgreSQL JSONB concatenation operator: `transcript || %s::jsonb`
- Each turn has: `role` (user|assistant), `content` (message text), `at` (ISO 8601 UTC timestamp from `datetime.now(timezone.utc).isoformat()`)

### Error Handling Strategy

- **Config errors**: Raise `RuntimeError` at import time if required env vars missing (fail fast)
- **Database errors**: Let psycopg exceptions bubble up (FastAPI converts to HTTP 500)
- **Ollama timeout/errors**: Catch all exceptions from `chat_ollama()`, log session_id only, return HTTP 502 with neutral message
- **Message length**: Pydantic Field validates 1-2000 characters
- **Logging**: Never log message content, only session_id and error types

### Verification Steps

After implementation:

1. **Config**: `cd backend && uv run python -c "from app.config import DATABASE_URL, OLLAMA_HOST, CHAT_MODEL; print(f'OK: {CHAT_MODEL}')"`
2. **Schema init**: `cd backend && uv run python ../scripts/init_db.py` (run twice to verify idempotency)
3. **Tables**: `docker compose exec postgres psql -U app -d secureship -c "\dt"` (should show customer, shipment, package, chat_session)
4. **Ollama client**: `cd backend && uv run python -c "from app.llm.client import chat_ollama; print(chat_ollama([{'role':'user','content':'Hi'}]))"`
5. **Server start**: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
6. **Health**: `curl http://localhost:8000/health` → `{"status":"ok"}`
7. **Chat new session**: `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"Hello"}'` → returns session_id and reply
8. **Chat existing session**: Use session_id from step 7 → same session_id returned
9. **Tests**: `cd backend && uv run pytest -v` → 5 tests pass

## Notes

- No new dependencies needed (all already in pyproject.toml)
- No system prompt yet (Week 1 Day 5 feature)
- No identity verification or access gate (Week 2+ feature)
- Tests use real Postgres, not SQLite (need pgvector extension)
- Transcript column is the ONE place message content is stored (not logged elsewhere)
- All data is synthetic (demo-identities.json used later by seed_data.py script)
- CORS is restrictive: only GET/POST methods, only Content-Type header
- Model call happens with no DB connection open (connection closed before model call)
- Two different timestamps: user turn when request arrives, assistant turn when reply returns
