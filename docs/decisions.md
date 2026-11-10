# Decision log

One entry per open decision and per changed default, written when deciding.
Format: Decision / Alternative I rejected / Why / How I will know it was right.

---

### Week 1: delayed design check
Decision: Continue Day 2 using the workshop defaults and finalize the architecture only after the mentor design check.
Alternative I rejected: Pause all implementation until the design check is available.
Why: I am catching up and can make progress on the concept, stack, chat, and seed data without finalizing the architecture.
How I will know it was right: the mentor design check does not require a structural change to the core data or route design.

### Week 1: primary runtime
Decision: Ollama `qwen3:8b` as primary chat runtime; `nomic-embed-text` (768 dims) for embeddings.
Alternative I rejected: DIAL as primary.
Why: No cost vs. 40 USD shared allowance; no VPN needed; reachable from containers via host.docker.internal (tested); M4 with 24 GB runs 8B comfortably; tool call worked on first try
How I will know it was right: a chat turn returns in a few seconds after warm-up, and the get_weather
tool call appears 5 out of 5 times.

### Week 1: DIAL as secondary runtime
Decision: chat `gpt-4.1-mini-2025-04-14`; embedding `text-embedding-3-small-1` (1536 dims), recorded only.
Alternative I rejected: a `gpt-5-*` mini model (or `gpt-4.1-nano`).
Why: Accepts temperature; no hidden reasoning tokens; cheap; tool call returned correctly; nano is cheaper but weaker at tools.
How I will know it was right: in Week 4 the injection and retrieval tests pass on DIAL with
max_tokens kept low, and allowance use stays small.

### Week 1: Ollama runs on the host, not in Docker
Decision: Ollama as the macOS app; host processes use localhost:11434, containers use host.docker.internal:11434.
Alternative I rejected: Ollama in a Docker container.
Why: A container on a Mac can't use the Apple GPU, so it would be much slower.
How I will know it was right: `docker run --rm curlimages/curl -s http://host.docker.internal:11434/api/tags` returns the model list (it does).

### Week 1: qwen3 thinking off
Decision: send `"think": false` on every Ollama chat call.
Alternative I rejected: default thinking on.
Why: Thinking adds hidden reasoning text and time and support reply doesn't need it.
How I will know it was right: no thinking text appears in replies, and the same prompt with thinking on
vs. off shows the time difference (run both once and note the numbers).

### Week 1: web stack
Decision: keep the defaults (FastAPI + uv, React + TS + Vite, Postgres + pgvector, Compose).
Alternative I rejected: Node/Express backend
Why: Model clients are Python; FastAPI generates OpenAPI for Orval; React/TS is my weaker side, so less to invent.
How I will know it was right: Orval generates a working client from /openapi.json and the chat window uses its hooks.

### Week 1: HTTP, not WebSockets
Decision: HTTP request/response.
Alternative I rejected: WebSockets.
Why: Works directly with Orval + React Query, same gate either way, I am less familiar with WebSockets.
How I will know it was right: the code modal appears only when a /chat response tells it to, never on page load.

### Week 1: browser session id storage
Decision: Store only the server-generated session id in browser localStorage.
Alternative I rejected: Keeping it only in React memory.
Why: localStorage keeps the same session (and its stored transcript) after a refresh while the backend remains the only source of truth for session state, verification, and customer identity. A stolen id could access that session until it expires, so no verified flag or customer data is stored in the browser.
How I will know it was right: refreshing the browser keeps the same session id, while editing localStorage cannot make a session verified.
Accepted scope (Day 4): the visible chat history is not restored after a page refresh, because there is no history endpoint yet. The transcript stays stored in Postgres.

### Week 1: shipment exception reason
Decision: Add a nullable `exception_reason` column to `shipment`; Jordan Patel’s MX10002 has `address_mismatch`.
Alternative I rejected: Encoding the exception reason inside the shipment status.
Why: the official seed fixture includes the field, and the Week 2 n8n flow and Week 3 Jordan policy-and-shipment demo need the reason as separate trusted shipment data.
How I will know it was right: the seeded MX10002 row returns `exception | address_mismatch`, and non-exception shipments have a null reason.

### Week 1: TypeScript compatibility
Decision: Pin TypeScript to 6.0.3 for the Vite frontend.
Alternative I rejected: Using TypeScript 7 with `--force` or `--legacy-peer-deps`.
Why: the installed `typescript-eslint` version does not support TypeScript 7, and forcing the dependency tree would hide a potentially broken lint setup.
How I will know it was right: `npm install`, `npm run build`, and `npm run lint` all pass.

### Week 1: temperature, context window and output limit
Decision: temperature 0.2, num_ctx 8192, num_predict 400, all set in backend/app/config.py and sent on every Ollama call.
Alternative I rejected: Ollama defaults (temperature 0.8, a smaller default context window, no output limit).
Why: 0.2 gave the same answer 5 of 5 times, while 0.8 changed the answer and invented details. With 2048 my prompt start was cut silently, and with 8192 it fit. 400 tokens stops runaway replies and limits DIAL cost. Low temperature does not make answers true; grounding does that.
How I will know it was right: test_llm_client.py passes, prompt_eval_count stays below 8192 in normal chats, and replies are not cut mid-sentence.

### Week 1: system prompt contents
Decision: one constant SYSTEM_PROMPT in backend/app/prompts.py, based on the tested v2 draft (docs/labs/drafts/system-message.txt). It is prepended as the first message {role: "system"} on every model call and is never stored in the transcript. It includes the grounding sentence: answer policy questions only from the policy documents you are given, and cite the section.
Alternative I rejected: storing the prompt as the first transcript entry; a text file loaded at startup.
Why: v1 leaked its rules on injection and v2 refused (Day 3 evidence). Keeping the prompt out of the transcript means a prompt change applies to every session and the transcript holds only the real conversation. The prompt is not a security control: access rules stay in backend code.
How I will know it was right: a test shows messages[0] is the system prompt and the transcript holds no system entry; a live policy question gets "I don't know" instead of an invented section.

### Week 1: what each turn stores
Decision: each successful turn appends two entries to chat_session.transcript (JSONB):
{role, content, at} for the user and for the assistant, in one transaction, only after
the model replies. If the model fails: HTTP 502, nothing stored, no session row created.
Only {role, content} is sent to the model; "at" is stored, never sent.
Alternative I rejected: store the user message first, then the reply (two writes).
Why: saving both turns together after the reply means the transcript never has a question without an answer; a half-saved turn would send the model a dangling question next time.
How I will know it was right: test_model_failure_no_session_created passes, and after a
real chat the transcript length is always even.

### Week 1: seed generation and re-run safety
Decision: scripts/seed_data.py loads the 3 fixture people unchanged, then generates 24 customers and
47 shipments with random.Random(42) and a fixed base date (2026-10-01). Upsert on phone_number and
tracking_number; packages are deleted and re-inserted per seeded shipment; all in one transaction.
Alternative I rejected: truncate all tables and reload on every run.
Why: a fixed seed gives the same data on every machine and every run, so demos and tests are repeatable;
truncate would also wipe chat sessions and anything an admin adds later.
How I will know it was right: two runs print identical counts (27 / 50 / 103) and test_seed.py passes.

### Week 2: session states
Decision: six states: anonymous, collecting, code_sent, verified, locked, escalated. A parcel question moves anonymous to collecting; four matching details move collecting to code_sent; a correct code within 5 minutes moves code_sent to verified. Missing details or no match stay in collecting with "We couldn't verify that." A wrong code stays in code_sent until the 3rd wrong try, which moves to locked. An expired code goes back to collecting. Asking for a human moves any state except locked to escalated, which is final. Every change goes through one move() function with an allowed-transitions table.
Alternative I rejected: after the 3rd wrong code, go back to collecting.
Why: going back would let someone ask for fresh codes forever at no cost; locked forces a new conversation and all four details again. Expiry is usually an innocent slow user, so it goes back to collecting.
How I will know it was right: each failure path has a test and none ends in verified; move() raises on any transition not in the table. Known limit: a new conversation can start again, so real systems would add rate limits per IP or customer.

### Week 2: how typed text becomes trusted data
Decision: the model extracts identity fields only through the submit_details tool (all four fields optional). Code validates every argument as untrusted input: trimmed, length limits, allowed characters, phone normalised to E.164. Missing fields get a reply asking only for those. A missing tool call, bad JSON or invalid values count as no fields, with no retry. Fields are re-extracted from the visitor's messages since entering collecting; no new column stores identity details.
Alternative I rejected: let the model decide whether the details belong to a real customer.
Why: the model cannot know who is a customer and will happily say yes; only code that matches against the database can decide.
How I will know it was right: tests for object args, string args, bad JSON, missing fields, invalid values and no tool call all pass, and no identity details appear in the logs.