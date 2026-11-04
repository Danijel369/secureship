# Plan: Day 2 Frontend — Minimal Chat Window

## Context

The frontend currently shows the Vite starter page. This plan replaces it with a minimal chat window that calls `POST /chat` via an Orval-generated React Query mutation. No new npm dependencies are added; the existing stack is `@tanstack/react-query ^5`, `orval ^7.13.2`, and `vite ^8`.

---

## Orval 7 configuration note

Orval 7.13.2 exposes the following keys for the `output` block:
- `httpClient: "fetch"` — switches from the default axios to native fetch (key name confirmed from `@orval/core` source: `OutputHttpClient.FETCH = "fetch"`)
- `override.mutator.path` / `override.mutator.name` — points to a custom fetch wrapper

**`baseUrl` is NOT used.** The mutator reads `import.meta.env.VITE_API_URL` at runtime, so the base URL never appears in the generated code or in `orval.config.ts`.

---

## Files changed

| File | Action |
|---|---|
| `frontend/orval.config.ts` | Add `httpClient: "fetch"` and `override.mutator` |
| `frontend/src/api/mutator.ts` | **Create** — custom fetch wrapper |
| `frontend/src/api/generated/index.ts` | **Generated** by `npx orval` (commit, never edit by hand) |
| `frontend/src/main.tsx` | Wrap `<App>` in `<QueryClientProvider>` |
| `frontend/src/components/ChatWindow.tsx` | **Create** — chat UI |
| `frontend/src/App.tsx` | Replace Vite starter with `<ChatWindow />` |
| `frontend/src/index.css` | Replace starter styles with minimal chat CSS |
| `frontend/src/App.css` | **Delete** (no longer imported) |
| `frontend/src/assets/react.svg` | **Delete** |
| `frontend/src/assets/vite.svg` | **Delete** |
| `frontend/src/assets/hero.png` | **Delete** |

---

## Step-by-step

### 1 — `frontend/orval.config.ts`

```ts
import { defineConfig } from "orval";

export default defineConfig({
  api: {
    input: "http://localhost:8000/openapi.json",
    output: {
      target: "./src/api/generated/index.ts",
      client: "react-query",
      httpClient: "fetch",
      override: {
        mutator: {
          path: "./src/api/mutator.ts",
          name: "customFetch",
        },
      },
    },
  },
});
```

### 2 — `frontend/src/api/mutator.ts` (new file)

```ts
export const customFetch = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`${import.meta.env.VITE_API_URL}${url}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw Object.assign(new Error(body.detail ?? 'Request failed'), {
      status: response.status,
      data: body,
    });
  }
  return response.json() as Promise<T>;
};
```

### 3 — Run `npx orval` (backend must be running)

```
cd frontend && npx orval
```

This writes `src/api/generated/index.ts`. FastAPI's default operationId for `def chat` at `POST /chat` is `chat_chat_post`, which Orval camelCases to `chatChatPost`. The generated mutation hook will be **`useChatChatPost`** and the input option type **`UseChatChatPostMutationOptions`**. Confirm from the generated file before writing the component; use whatever name appears there.

The generated file also exports `ChatRequest` and `ChatReply` types — import them in the component.

### 4 — `frontend/src/main.tsx`

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
```

### 5 — `frontend/src/components/ChatWindow.tsx` (new file)

Key design decisions:
- `Message` type: `{ role: 'user' | 'assistant' | 'error'; content: string }`
- `sessionId` lives in a `useRef`, initialized from `localStorage.getItem('secureship_session_id')`; it is never stored in React state (no security concern, but no need for re-renders)
- `input` is controlled state; the Send button is disabled when `isPending || !input.trim()`
- Enter sends (unless Shift+Enter); Shift+Enter inserts a newline
- On success: store `reply.session_id` in localStorage + ref, append assistant bubble
- On error: append a neutral error bubble (`"Something went wrong. Please try again."`), keep input text
- "New conversation": clear localStorage key, reset ref to null, clear messages — does not send a request
- **Known limitation**: after a page refresh, session_id persists but the visible list starts empty (no history endpoint yet)

Mutation hook usage:
```tsx
const { mutate: sendChat, isPending } = useChatChatPost();
// called as: sendChat({ session_id: sessionId.current, message: text }, { onSuccess, onError })
```

### 6 — `frontend/src/App.tsx`

Replace the entire file with:
```tsx
import ChatWindow from './components/ChatWindow'

export default function App() {
  return <ChatWindow />
}
```

Remove all existing imports (`assets/hero.png`, `assets/react.svg`, `assets/vite.svg`, `App.css`).

### 7 — `frontend/src/index.css`

Replace with minimal styles:
- CSS variables for colors (light/dark via `prefers-color-scheme`)
- `body { margin: 0; font: 16px/1.5 system-ui, sans-serif; }`
- `#root { height: 100svh; display: flex; flex-direction: column; }`
- `.chat-window` — flex column, full height
- `.messages` — flex column, flex-grow: 1, overflow-y: auto, padding
- `.bubble` — inline-block, max-width 70%, padding, border-radius, margin
- `.bubble.user` — align-self: flex-end, background: accent color
- `.bubble.assistant` — align-self: flex-start, background: surface color
- `.bubble.error` — align-self: center, color: red
- `.input-row` — flex row, gap, padding; input flex-grow: 1

### 8 — Delete unused files

Delete:
- `frontend/src/App.css`
- `frontend/src/assets/react.svg`
- `frontend/src/assets/vite.svg`
- `frontend/src/assets/hero.png`

---

## Verification

### Automated
```bash
cd frontend
npm run lint     # must pass with 0 errors
npm run build    # tsc + vite build must pass
```

### Manual browser steps
1. Backend running: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
2. Frontend running: `cd frontend && npm run dev` → http://localhost:3000
3. **Happy path**: type a message, press Enter → user bubble appears, "…" shows while pending, assistant reply appears
4. **Session persistence**: reload page → chat history is empty, but `secureship_session_id` is present in localStorage; next message reuses the session (verify in Network tab that `session_id` is sent)
5. **New conversation**: click "New conversation" → messages clear, `secureship_session_id` removed from localStorage
6. **Error path**: stop the backend, send a message → neutral error message appears in chat, typed text is preserved, app does not crash

---

## Limitations (note in plan, comment in code)

After a page refresh the visible chat history starts empty even though the session id persists. This is expected; a history endpoint does not exist yet.
