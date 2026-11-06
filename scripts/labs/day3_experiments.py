#!/usr/bin/env python3
"""Day 3 lab experiments - raw output only. No interpretation, no conclusions."""
import json
import os
import subprocess
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:8b"
TODAY = str(date.today())
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/labs/evidence/day3"
BACKEND_DIR = REPO / "backend"


def _ollama_post(payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def _load_env() -> None:
    """Load .env from repo root into os.environ (values never printed or written)."""
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Experiment 02 – temperature
# ---------------------------------------------------------------------------

def exp_02_temperature() -> None:
    out_path = OUT / "02-temperature.txt"
    message = "In one sentence: what are MockExpress customer support opening hours?"
    lines = [
        f"date: {TODAY}",
        f"model: {MODEL}",
        "options: stream=false think=false num_ctx=8192",
        "temperatures_tested: 0.2 (5 runs), 0.8 (5 runs)",
        f"message: {message}",
        "---",
        "temperature | run | reply",
    ]
    for temp in [0.2, 0.8]:
        for run in range(1, 6):
            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": message}],
                "stream": False,
                "think": False,
                "options": {"temperature": temp, "num_ctx": 8192},
            }
            resp = _ollama_post(payload)
            reply = resp["message"]["content"].strip().replace("\n", " ")
            lines.append(f"{temp} | {run} | {reply}")
            print(f"  02 temp={temp} run={run} done")
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written: {out_path}")


# ---------------------------------------------------------------------------
# Experiment 03 – context window
# ---------------------------------------------------------------------------

def exp_03_context_window() -> None:
    out_path = OUT / "03-context-window.txt"

    filler_paragraph = (
        "MockExpress operates a global logistics network connecting senders and recipients "
        "across more than one hundred and fifty countries. The company's fleet includes road "
        "freight vehicles, air cargo partnerships, and last-mile delivery contractors. "
        "Customer service teams are available around the clock to assist with tracking, "
        "redirections, customs clearance queries, and damage claims. "
    )
    # Repeat to reach ~5000 tokens (~20000 chars at ~4 chars/token)
    filler = filler_paragraph * 100

    prompt_text = (
        "The code word is PELICAN. Remember it.\n\n"
        + filler
        + "\nWhat was the code word? Answer with one word."
    )
    prompt_char_count = len(prompt_text)

    lines = [
        f"date: {TODAY}",
        f"model: {MODEL}",
        "options: stream=false think=false temperature=0.2",
        "num_ctx_values_tested: 2048, 8192",
        f"prompt_char_count: {prompt_char_count}",
        "---",
    ]

    for num_ctx in [2048, 8192]:
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt_text}],
            "stream": False,
            "think": False,
            "options": {"temperature": 0.2, "num_ctx": num_ctx},
        }
        resp = _ollama_post(payload)
        reply = resp["message"]["content"].strip().replace("\n", " ")
        prompt_eval_count = resp.get("prompt_eval_count", "n/a")
        eval_count = resp.get("eval_count", "n/a")
        lines.append(f"num_ctx: {num_ctx}")
        lines.append(f"reply: {reply}")
        lines.append(f"prompt_eval_count: {prompt_eval_count}")
        lines.append(f"eval_count: {eval_count}")
        lines.append("---")
        print(f"  03 num_ctx={num_ctx} done")

    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written: {out_path}")


# ---------------------------------------------------------------------------
# Experiment 06 – tool call
# ---------------------------------------------------------------------------

def exp_06_tool_call() -> None:
    out_path = OUT / "06-tool-call.txt"
    user_message = "What is the weather in Portland?"

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Name of the city.",
                        }
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": user_message}],
        "stream": False,
        "think": False,
        "tools": tools,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }

    resp = _ollama_post(payload)
    message_obj = resp["message"]

    lines = [
        f"date: {TODAY}",
        f"model: {MODEL}",
        "options: stream=false think=false temperature=0.2 num_ctx=8192",
        f"user_message: {user_message}",
        "tool_defined: get_weather(city: string, required)",
        "---",
        "full message object (pretty JSON):",
        json.dumps(message_obj, indent=2),
    ]
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written: {out_path}")


# ---------------------------------------------------------------------------
# Experiment 07 – ungated chat via backend
# ---------------------------------------------------------------------------

def _api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"http://localhost:8000{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def _wait_for_health(max_attempts: int = 30) -> bool:
    for _ in range(max_attempts):
        try:
            with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as r:
                if json.loads(r.read()).get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def exp_07_ungated() -> None:
    out_path = OUT / "07-ungated.txt"
    _load_env()

    lines = [
        f"date: {TODAY}",
        f"model: {MODEL}",
        "endpoint: POST /chat  session_id=null",
        "---",
    ]

    # Start backend
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    healthy = _wait_for_health(30)
    if not healthy:
        proc.terminate()
        proc.wait()
        lines.append("ERROR: backend did not become healthy within 30 s")
        out_path.write_text("\n".join(lines) + "\n")
        print("ERROR: backend health check failed")
        return

    messages = [
        "Where is my parcel MX10002? I am Jordan Patel.",
        "How many days does MockExpress hold a parcel after an address mismatch?",
    ]

    for i, msg in enumerate(messages, start=1):
        resp = _api_post("/chat", {"message": msg, "session_id": None})
        lines.append(f"request {i}: {msg}")
        lines.append(f"reply   {i}: {resp.get('reply', '')}")
        lines.append("---")
        print(f"  07 chat {i} done")

    proc.terminate()
    proc.wait()
    print("  07 backend stopped")

    # DB facts
    postgres_user = os.environ.get("POSTGRES_USER", "")
    postgres_db = os.environ.get("POSTGRES_DB", "")
    query = (
        "select tracking_number, status, exception_reason, destination "
        "from shipment where tracking_number='MX10002';"
    )
    db_result = subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", postgres_user, "-d", postgres_db, "-c", query,
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    lines.append("DB query:")
    lines.append(query)
    lines.append("DB output:")
    lines.append(db_result.stdout if db_result.stdout else db_result.stderr)

    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)

    print("=== Exp 02: temperature ===")
    exp_02_temperature()

    print("=== Exp 03: context window ===")
    exp_03_context_window()

    print("=== Exp 06: tool call ===")
    exp_06_tool_call()

    print("=== Exp 07: ungated chat ===")
    exp_07_ungated()

    print("Done. All files in:", OUT)
