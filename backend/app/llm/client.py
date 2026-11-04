"""Ollama chat client with explicit configuration."""
import httpx
from app.config import OLLAMA_HOST, CHAT_MODEL, TEMPERATURE, NUM_CTX


def chat_ollama(messages: list[dict]) -> str:
    """
    Send messages to Ollama chat endpoint and return assistant reply.

    Args:
        messages: List of {role: str, content: str} dicts

    Returns:
        Assistant's reply text

    Raises:
        httpx.HTTPError: On request failure or timeout
    """
    url = f"{OLLAMA_HOST}/api/chat"

    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
        }
    }

    response = httpx.post(url, json=payload, timeout=60.0)
    response.raise_for_status()

    data = response.json()
    return data["message"]["content"]
