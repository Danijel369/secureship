"""Test suite for chat endpoints."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.db import get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_sessions():
    """Track and cleanup sessions created during tests"""
    session_ids = []
    yield session_ids
    # Cleanup after test
    if session_ids:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM chat_session WHERE id = ANY(%s)",
                    (session_ids,)
                )


def test_two_turns_same_session(cleanup_test_sessions):
    """Test two turns in one session - transcript has 4 entries"""
    with patch("app.main.chat_ollama") as mock_ollama:
        mock_ollama.side_effect = ["Reply 1", "Reply 2"]

        # First turn
        response1 = client.post("/chat", json={"message": "Hello"})
        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]
        assert data1["reply"] == "Reply 1"
        cleanup_test_sessions.append(session_id)

        # Second turn with same session_id
        response2 = client.post("/chat", json={
            "session_id": session_id,
            "message": "How are you?"
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        assert data2["reply"] == "Reply 2"

        # Check transcript in database
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT transcript FROM chat_session WHERE id = %s",
                    (session_id,)
                )
                row = cur.fetchone()
                assert row is not None
                transcript = row[0]

        assert len(transcript) == 4
        assert transcript[0]["role"] == "user"
        assert transcript[0]["content"] == "Hello"
        assert "at" in transcript[0]
        assert transcript[1]["role"] == "assistant"
        assert transcript[1]["content"] == "Reply 1"
        assert transcript[2]["role"] == "user"
        assert transcript[2]["content"] == "How are you?"
        assert transcript[3]["role"] == "assistant"
        assert transcript[3]["content"] == "Reply 2"

        # Verify messages sent to model on second turn
        messages_sent = mock_ollama.call_args[0][0]
        assert len(messages_sent) == 3
        assert messages_sent[0] == {"role": "user", "content": "Hello"}
        assert messages_sent[1] == {"role": "assistant", "content": "Reply 1"}
        assert messages_sent[2] == {"role": "user", "content": "How are you?"}
        # Verify each dict has only role and content keys
        for msg in messages_sent:
            assert set(msg.keys()) == {"role", "content"}


def test_unknown_session_id(cleanup_test_sessions):
    """Test unknown session_id creates new session with different id"""
    with patch("app.main.chat_ollama") as mock_ollama:
        mock_ollama.return_value = "Hello!"

        fake_session_id = "nonexistent-session-id-12345"
        response = client.post("/chat", json={
            "session_id": fake_session_id,
            "message": "Hi"
        })

        assert response.status_code == 200
        data = response.json()
        returned_session_id = data["session_id"]
        cleanup_test_sessions.append(returned_session_id)

        # Should get a different session_id
        assert returned_session_id != fake_session_id

        # Verify the fake session_id was never inserted
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM chat_session WHERE id = %s",
                    (fake_session_id,)
                )
                assert cur.fetchone() is None


def test_no_session_id(cleanup_test_sessions):
    """Test no session_id creates new session"""
    with patch("app.main.chat_ollama") as mock_ollama:
        mock_ollama.return_value = "Welcome!"

        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        cleanup_test_sessions.append(session_id)
        assert session_id  # Not empty
        assert data["reply"] == "Welcome!"

        # Verify session exists in database
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, state FROM chat_session WHERE id = %s",
                    (session_id,)
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == session_id
                assert row[1] == "anonymous"


def test_health_endpoint():
    """Test GET /health returns ok status"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_model_failure_no_session_created(cleanup_test_sessions):
    """Test chat_ollama raises -> 502, no new session row, existing session unchanged"""
    with patch("app.main.chat_ollama") as mock_ollama:
        # Test 1: Model failure with no session_id - no row should be created
        mock_ollama.side_effect = Exception("Ollama timeout")

        # Count rows before
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chat_session")
                count_before = cur.fetchone()[0]

        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 502
        assert "temporarily unavailable" in response.json()["detail"]

        # Count rows after - should be unchanged
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chat_session")
                count_after = cur.fetchone()[0]

        assert count_after == count_before

        # Test 2: Model failure with existing session - transcript should be unchanged
        mock_ollama.reset_mock()
        mock_ollama.side_effect = None  # Clear the exception
        mock_ollama.return_value = "First reply"

        # Create a session first
        response1 = client.post("/chat", json={"message": "First message"})
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        cleanup_test_sessions.append(session_id)

        # Get initial transcript
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT transcript FROM chat_session WHERE id = %s",
                    (session_id,)
                )
                initial_transcript = cur.fetchone()[0]

        assert len(initial_transcript) == 2  # user + assistant

        # Now make model fail
        mock_ollama.side_effect = Exception("Ollama error")

        response2 = client.post("/chat", json={
            "session_id": session_id,
            "message": "Second message"
        })

        assert response2.status_code == 502

        # Verify transcript is unchanged
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT transcript FROM chat_session WHERE id = %s",
                    (session_id,)
                )
                final_transcript = cur.fetchone()[0]

        assert len(final_transcript) == 2  # Still just 2 entries
        assert final_transcript == initial_transcript
