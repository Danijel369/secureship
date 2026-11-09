# Platforms and tools

Copy to `docs/platform-and-tooling.md` in Week 1. It records which runtime you use and how it fits into the wider picture of where models are hosted.

## The shape this program runs

| Piece | This program |
|---|---|
| Chat model | One of the two runtimes below, chosen in Week 1 |
| Embeddings | A model from the same runtime, stored next to your document chunks |
| Tools | Python functions that your code runs when the model asks |
| Build assistant | Claude Code |
| Source control | Git |

## Runtime A: Ollama on your machine

Open models served locally. Recommended chat model `qwen3:8b`, or `llama3.2:3b` on an 8 GB machine, with weaker tool calls. Embeddings from a local model such as `nomic-embed-text`. Free, private, and it works offline. Slower on a small machine. From a Docker container it is reached at `http://host.docker.internal:11434`.

## Runtime B: EPAM DIAL

A hosted gateway to several models. You need a key, the EPAM VPN, and you stay within a 40 USD allowance. Request a key in Week 1 from the [EPAM Support catalog](https://support.epam.com/ess?id=sc_cat_item&table=sc_cat_item&sys_id=910603f1c3789e907509583bb001310c). Approval is automatic and takes a few minutes.

The API reference is the [DIAL Core API](https://dialx.ai/dial_api) (latest release). These are the operations you use:

| What | Operation | Reference |
|---|---|---|
| Send the key | `Api-Key` header | [Authorization](https://dialx.ai/dial_api#section/Authorization) |
| Chat, including tool calls | `POST /openai/deployments/{deployment_name}/chat/completions` | [`sendChatCompletionRequest`](https://dialx.ai/dial_api#tag/LLM/operation/sendChatCompletionRequest) |
| Embeddings | `POST /openai/deployments/{deployment_name}/embeddings` | [`createEmbedding`](https://dialx.ai/dial_api#tag/LLM/operation/createEmbedding) |
| Which deployments exist | `GET /openai/deployments` | [`getDeployments`](https://dialx.ai/dial_api#tag/Deployment-listing/operation/getDeployments) |

`api-version` is a required query parameter on the deployment routes. The reference example is `2023-12-01-preview`. The vector is `data[].embedding`, and its length is the dimension of your vector column. The server URL in the published spec is a placeholder. The host to call is `https://ai-proxy.lab.epam.com`, on the VPN. The [setup guide](../../setup.md) shows how to test it.

## What I run

- Primary runtime: **Ollama** (runtime A), macOS app on the host. The backend reaches it at `localhost:11434`; a container would use `host.docker.internal:11434`.
- Chat deployment or model: `qwen3:8b`, `think: false`, temperature 0.2, `num_ctx` 8192, `num_predict` 400 (all in `backend/app/config.py`).
- Embedding deployment or model, and dimension: `nomic-embed-text`, **768** dimensions. Embeddings never switch runtime, even when chat runs on DIAL.
- Why: free, private and offline, and my M4 with 24 GB runs `qwen3:8b` fast enough. Tool calls work (Day 3 lab).
- Secondary runtime: **DIAL** (runtime B), `gpt-4.1-mini-2025-04-14` at `https://ai-proxy.lab.epam.com`, VPN only. Chat, embeddings and a tool call were tested. The shared 40 USD allowance means short tests, low `max_tokens` and never a retry loop without a limit. Tool-call arguments differ: Ollama returns an object, DIAL returns a JSON string.

## Where else this shape is hosted

The same shape, a chat model, an embedding model, and your own code holding the tools and the gate, can run on other platforms. This program does not use them. The table is for comparison.

| Platform | What would stand in for the pieces above |
|---|---|
| Azure AI Foundry | A Foundry model deployment for chat and embeddings, a project for tools and evaluation, your own service still enforcing the shipment gate |
| AWS | Bedrock, or an equivalent managed model API, for chat and embeddings, with your service owning the tools and the gate |
| Google Cloud AI | Vertex AI model endpoints for chat and embeddings, with your service owning the tools and the gate |

Moving the model to another host does not move the gate. The shipment lookup still reads the customer from the session, never from the model.

## Editors and assistants

| Tool | Role in this program |
|---|---|
| Claude Code | Required build assistant |
| Git | Required |
| Cursor | A named alternative editor. Not required. |
| VS Code | A named alternative editor. Not required. |
| GitHub Copilot | A named alternative assistant. Not required. |

Use Claude Code for the build even if another assistant is installed. The review rule is the same for any of them: read the diff before you keep it.
