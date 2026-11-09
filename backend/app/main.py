"""SecureShip FastAPI application."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import secrets
from datetime import datetime, timezone
import logging
import json

from app.db import get_connection
from app.llm.client import chat_ollama
from app.prompts import SYSTEM_PROMPT

# Configure logging - never log message content
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SecureShip")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# Request/Response models
class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=2000)


class ChatReply(BaseModel):
    session_id: str
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatReply)
def chat(req: ChatRequest):
    session_id = req.session_id
    request_at = datetime.now(timezone.utc).isoformat()

    # (a) Short connection: look up session and read transcript
    transcript = []
    session_exists = False

    if session_id and session_id.strip():
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT transcript FROM chat_session WHERE id = %s",
                        (session_id,)
                    )
                    row = cur.fetchone()
                    if row is not None:
                        session_exists = True
                        transcript = row[0] if row[0] else []
        except Exception as e:
            logger.error(f"Database error loading session {session_id}: {type(e).__name__}")
            raise HTTPException(status_code=500, detail="Database error")

    # (b) Call model with no DB connection open
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": msg["role"], "content": msg["content"]} for msg in transcript]
    messages.append({"role": "user", "content": req.message})

    try:
        assistant_reply = chat_ollama(messages)
    except Exception as e:
        # Log only session_id, never content
        logger.error(f"Model call failed for session {session_id}: {type(e).__name__}")
        raise HTTPException(
            status_code=502,
            detail="The chat service is temporarily unavailable. Please try again."
        )

    # (c) On success: one transaction to store both turns
    reply_at = datetime.now(timezone.utc).isoformat()
    user_turn = {"role": "user", "content": req.message, "at": request_at}
    assistant_turn = {"role": "assistant", "content": assistant_reply, "at": reply_at}
    both_turns = [user_turn, assistant_turn]

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if session_exists:
                    # UPDATE existing session
                    cur.execute(
                        "UPDATE chat_session SET transcript = transcript || %s::jsonb WHERE id = %s",
                        (json.dumps(both_turns), session_id)
                    )
                else:
                    # INSERT new session with server-generated ID
                    session_id = secrets.token_urlsafe(32)
                    cur.execute(
                        "INSERT INTO chat_session (id, state, transcript) VALUES (%s, %s, %s)",
                        (session_id, "anonymous", json.dumps(both_turns))
                    )
    except Exception as e:
        logger.error(f"Failed to store transcript for session {session_id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to store conversation")

    return ChatReply(session_id=session_id, reply=assistant_reply)
