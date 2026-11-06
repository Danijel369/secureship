"""Unit test: chat_ollama sends the settings from config.py."""
from unittest.mock import patch, MagicMock

import app.llm.client as llm_client
from app.config import CHAT_MODEL, TEMPERATURE, NUM_CTX, NUM_PREDICT


def test_chat_ollama_payload():
    messages = [{"role": "user", "content": "hi"}]

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "ok"}}

    with patch("app.llm.client.httpx.post", return_value=mock_response) as mock_post:
        llm_client.chat_ollama(messages)

    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]

    assert payload["model"] == CHAT_MODEL
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"]["temperature"] == TEMPERATURE
    assert payload["options"]["num_ctx"] == NUM_CTX
    assert payload["options"]["num_predict"] == NUM_PREDICT
    assert payload["messages"] == messages
