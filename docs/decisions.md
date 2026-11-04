# Decision log

One entry per open decision and per changed default, written when deciding.
Format: Decision / Alternative I rejected / Why / How I will know it was right.

---

### Week 1: primary runtime
Decision: Ollama `qwen3:8b` as primary chat runtime; `nomic-embed-text` (768 dims) for embeddings.
Alternative I rejected: DIAL as primary.
Why: [your words. Facts: no cost vs. 40 USD shared allowance; no VPN needed; reachable from containers
     via host.docker.internal (tested); M4 with 24 GB runs 8B comfortably; tool call worked on first try]
How I will know it was right: a chat turn returns in a few seconds after warm-up, and the get_weather
tool call appears 5 out of 5 times.

### Week 1: DIAL as secondary runtime
Decision: chat `gpt-4.1-mini-2025-04-14`; embedding `text-embedding-3-small-1` (1536 dims), recorded only.
Alternative I rejected: a `gpt-5-*` mini model (or `gpt-4.1-nano`).
Why: [your words. Facts: accepts temperature; no hidden reasoning tokens; cheap; tool call returned
     correctly; nano is cheaper but weaker at tools]
How I will know it was right: in Week 4 the injection and retrieval tests pass on DIAL with
max_tokens kept low, and allowance use stays small.

### Week 1: Ollama runs on the host, not in Docker
Decision: Ollama as the macOS app; host processes use localhost:11434, containers use host.docker.internal:11434.
Alternative I rejected: Ollama in a Docker container.
Why: [your words. Fact: a container on a Mac can't use the Apple GPU (Metal), so it would be much slower]
How I will know it was right: `docker run --rm curlimages/curl -s http://host.docker.internal:11434/api/tags`
returns the model list (it does).

### Week 1: qwen3 thinking off
Decision: send `"think": false` on every Ollama chat call.
Alternative I rejected: default thinking on.
Why: [your words. Facts: thinking adds hidden reasoning text and time; a support reply doesn't need it]
How I will know it was right: no thinking text appears in replies, and the same prompt with thinking on
vs. off shows the time difference (run both once and note the numbers).

### Week 1: web stack
Decision: keep the defaults (FastAPI + uv, React + TS + Vite, Postgres + pgvector, Compose).
Alternative I rejected: [one you actually considered, e.g. a Node/Express backend]
Why: [your words. Facts: LangGraph and model clients are Python; FastAPI generates OpenAPI for Orval;
     mentors support the default fastest; React/TS is my weaker side, so less to invent]
How I will know it was right: Orval generates a working client from /openapi.json and the chat window
uses its hooks.

### Week 1: HTTP, not WebSockets
Decision: HTTP request/response; the server signals the UI through response fields (e.g. show code modal).
Alternative I rejected: WebSockets.
Why: [your words. Facts: simpler, works directly with Orval + React Query, same gate either way]
How I will know it was right: the code modal appears only when a /chat response tells it to,
never on page load.

### ⏳ Week 1: where the browser keeps the session id
Decision: [localStorage (recommended) / memory / httpOnly cookie]
Alternative I rejected: [...]
Why: [your words; say what happens on refresh and what someone could do with a stolen id]
How I will know it was right: refresh keeps the conversation, and editing localStorage can't make
a session verified (the server decides state).

### ⏳ Week 1: extra shipment column exception_reason
Decision: add nullable `exception_reason` to shipment; MX10002 = address_mismatch.
Alternative I rejected: [e.g. encoding the reason inside the status value]
Why: [your words. Facts: the n8n fixture needs it; the FAQ says the cause is described only from a
     tool result; the Week 3 Jordan demo needs "row says address mismatch"]
How I will know it was right: the Jordan query returns MX10002 | exception | address_mismatch.

### ⏳ Week 1: temperature and context window (decide on C2 after testing)
### ⏳ Week 1: what each turn stores
### ⏳ Week 1: system prompt contents
### ⏳ Week 1: seed generation and re-run safety (after the seed script)