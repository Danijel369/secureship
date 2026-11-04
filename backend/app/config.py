"""Configuration loader for SecureShip backend."""
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from repo root (2 levels up from this file)
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path, override=False)

# Required variables - raise clear error at import time if missing
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in environment or .env file")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST")
if not OLLAMA_HOST:
    raise RuntimeError("OLLAMA_HOST must be set in environment or .env file")

# Chat model configuration
CHAT_MODEL = "qwen3:8b"
TEMPERATURE = 0.2
NUM_CTX = 8192
