# Plan: Day 5 — System Prompt

## Context
`docs/decisions.md` ("Week 1: system prompt contents") records the decision: one `SYSTEM_PROMPT` constant in `backend/app/prompts.py`, prepended as `{"role": "system"}` at index 0 on every model call, never stored in the transcript. The tested v2 text lives in `docs/labs/drafts/system-message.txt`.

## Files to change

| File | Action |
|------|--------|
| `backend/app/prompts.py` | **Create** — one constant `SYSTEM_PROMPT`, text copied verbatim from `docs/labs/drafts/system-message.txt` |
| `backend/app/main.py` | **Edit** — import `SYSTEM_PROMPT`; prepend system message at `messages[0]` |
| `backend/tests/test_chat.py` | **Edit** — update one block in `test_two_turns_same_session`; add `test_system_prompt_sent_first` |

Do not touch: `llm/client.py`, `config.py`, `test_llm_client.py`, `schema.sql`, `scripts/`, `frontend/`, `docs/` (except saving this plan).

---

## 1. `backend/app/prompts.py` (new)

One constant, text verbatim from `docs/labs/drafts/system-message.txt` including curly apostrophes (U+2019) in `don't` and `can't`. No trailing newline after "Keep replies short and clear."

---

## 2. `backend/app/main.py` changes

Add import near top:
```python
from app.prompts import SYSTEM_PROMPT
```

In `chat()`, replace:
```python
messages = [{"role": msg["role"], "content": msg["content"]} for msg in transcript]
messages.append({"role": "user", "content": req.message})
```
with:
```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]
messages += [{"role": msg["role"], "content": msg["content"]} for msg in transcript]
messages.append({"role": "user", "content": req.message})
```

Transcript write block is untouched — still appends only `user_turn` and `assistant_turn`.

---

## 3. `backend/tests/test_chat.py` changes

`SYSTEM_PROMPT` imported once at module level, next to `from app.main import app`.

### 3a. Update `test_two_turns_same_session` — "messages sent to model on second turn" block only

New block:
```python
messages_sent = mock_ollama.call_args[0][0]
assert len(messages_sent) == 4
assert messages_sent[0] == {"role": "system", "content": SYSTEM_PROMPT}
assert messages_sent[1] == {"role": "user", "content": "Hello"}
assert messages_sent[2] == {"role": "assistant", "content": "Reply 1"}
assert messages_sent[3] == {"role": "user", "content": "How are you?"}
assert sum(1 for m in messages_sent if m["role"] == "system") == 1
for msg in messages_sent:
    assert set(msg.keys()) == {"role", "content"}
```

Transcript assertions above this block are unchanged.

### 3b. Add `test_system_prompt_sent_first`

```python
def test_system_prompt_sent_first(cleanup_test_sessions):
    """First turn: messages[0] is the system prompt; grounding sentence is present."""
    with patch("app.main.chat_ollama") as mock_ollama:
        mock_ollama.return_value = "Hello!"
        response = client.post("/chat", json={"message": "Hi"})
        assert response.status_code == 200
        cleanup_test_sessions.append(response.json()["session_id"])
        messages_sent = mock_ollama.call_args[0][0]
        assert messages_sent[0] == {"role": "system", "content": SYSTEM_PROMPT}
        assert "Answer policy questions only from the policy documents you are given" in SYSTEM_PROMPT
```

---

## Invariants verified by the final test suite

| Rule | Covered by |
|------|-----------|
| System prompt is `messages[0]` on the first turn | `test_system_prompt_sent_first` |
| System prompt is `messages[0]` on the second turn, exactly once | `test_two_turns_same_session` (updated block) |
| Transcript has 4 entries after 2 turns, all user/assistant | `test_two_turns_same_session` (unchanged transcript block) |
| Model receives only `{role, content}` | `test_two_turns_same_session` (unchanged key check) |
| Model failure → 502, nothing stored | `test_model_failure_no_session_created` (unchanged) |

---

## Verification

```
cd backend && uv run pytest
```
All tests must pass.
