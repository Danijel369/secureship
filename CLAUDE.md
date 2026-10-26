# Project
A support chat for parcel/shipment questions, built for the Applied AI Fluency
Workshop. It must never show shipment details to someone who has not proven who
they are. All data is synthetic.

Status: Week 1 (setup and first live chat). The access gate is not built yet.

# Stack
Current: Ollama (local model), EPAM DIAL (hosted models, VPN only), Claude Code
via CodeMie.

# How to run
Current state (model runtime only):
1. Start Ollama: `brew services start ollama`
2. Pull models once: `ollama pull qwen3:8b` and `ollama pull nomic-embed-text`
3. Check it answers: `curl -s http://localhost:11434/api/tags`
4. For DIAL: connect to the EPAM VPN, copy `.env.example` to `.env`, fill in
   `DIAL_API_KEY`, and load it into your shell.

Once the stack exists (planned): `docker compose up`.
The backend container reaches Ollama at `http://host.docker.internal:11434`.
If a container cannot reach DIAL through the VPN, run the backend directly on
the host.

# Rules
- Access rules (identity verification, data gating) are enforced in code, in
  the backend/tool layer, and not only in a prompt. A prompt cannot defend
  against prompt injection.
- Never commit `.env` or API keys. If a key is committed, treat it as leaked,
  tell a mentor, and request a new one.
- Use plan mode for any change bigger than a few lines. Name the files to
  change and say what must not change.
- Keep model temperature low and set the context window explicitly.
- DIAL has a shared 40 USD allowance: use small deployments, keep `max_tokens`
  low, and never add a retry loop without an upper limit.
- All data is synthetic. No real personal data anywhere.