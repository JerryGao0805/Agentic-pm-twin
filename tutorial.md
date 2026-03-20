# PM Twin Codebase Tutorial (Beginner-Friendly)

## 1. What This Project Is

This project is a **full-stack Kanban app** (like a lightweight Trello) with:

- user authentication (register/login/logout)
- multiple boards per user
- drag-and-drop cards
- card metadata (priority, due date, assignee)
- an AI assistant that can chat and propose board updates
- MySQL persistence
- automated tests (backend + frontend)

If you are new to coding, think of this as:

- **Frontend** = what users see and click
- **Backend** = API that receives requests and returns data
- **Database** = long-term storage

---

## 2. Technology Summary

| Layer | Technology | Why it is used |
|---|---|---|
| Frontend | Next.js 16 + React 19 + TypeScript | UI, components, page rendering |
| Styling | Tailwind CSS v4 | Fast utility-first styling |
| Drag/Drop | `@dnd-kit/*` | Reordering cards by mouse/keyboard |
| Backend API | FastAPI (Python) | HTTP endpoints and validation |
| Data Validation | Pydantic | Enforces board/card schema rules |
| Database | MySQL 8.4 | Persistent users, boards, chat history |
| AI Integration | OpenAI Python SDK (`responses.create`) | AI assistant and board update proposals |
| Backend Tests | Pytest + FastAPI TestClient | API/service/repository verification |
| Frontend Unit Tests | Vitest + Testing Library | Component/logic tests |
| Frontend E2E | Playwright | Browser-level user-flow tests |
| Runtime | Docker Compose | Starts MySQL + app together |

---

## 3. High-Level Architecture

```
Browser (Next.js UI)
   -> calls /api/* endpoints
FastAPI backend
   -> services (business logic)
   -> repositories (SQL read/write)
MySQL
```

Important folders:

- `frontend/src/app` -> app entry + global styling
- `frontend/src/components` -> UI building blocks
- `frontend/src/lib` -> shared board types/helpers
- `backend/app/main.py` -> API routes and wiring
- `backend/app/services` -> orchestration/business logic
- `backend/app/repositories` -> SQL layer
- `backend/app/db.py` -> DB initialization + migrations
- `backend/tests` and `frontend/*test*` -> tests

---

## 4. What Has Been Implemented in This Codebase

### Core product features

1. Authentication flow
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session`

2. Board management
- `GET /api/boards` (list)
- `POST /api/boards` (create)
- `GET /api/boards/{board_id}` (read)
- `PUT /api/boards/{board_id}` (update)
- `PATCH /api/boards/{board_id}` (rename)
- `DELETE /api/boards/{board_id}` (delete)
- Legacy support: `GET/PUT /api/board`

3. AI assistant
- `POST /api/ai/test`
- `POST /api/ai/chat`
- `GET /api/ai/chat/history`

4. Infrastructure/runtime
- Dockerized deployment with MySQL + backend + built frontend assets
- Auto schema setup and migration-like upgrades on backend startup

5. Testing foundation
- Backend tests for auth, boards, AI, repositories, DB init, integration flows
- Frontend unit tests + Playwright E2E tests for major user paths

---

## 5. End-to-End Walkthrough (Beginner View)

### Step 1: Start the app

From repo root:

```bash
./scripts/start.sh
```

This runs Docker Compose, starts:

- `mysql` container (port `3307` on host)
- `app` container (FastAPI serving APIs + static frontend on `8000`)

### Step 2: Open the app and sign in

UI entrypoint:

- `frontend/src/app/page.tsx` -> renders `AuthGate`

`AuthGate` checks session:

```tsx
const response = await fetch("/api/auth/session", { credentials: "include" });
```

If unauthenticated, it shows login/register form. On success, backend sets an HTTP-only cookie.

### Step 3: Load boards

After auth, frontend requests board(s):

- board list: `/api/boards`
- selected board data: `/api/boards/{id}` (or `/api/board` for legacy path)

### Step 4: Edit board in UI

You can:

- rename columns
- add/remove cards
- drag cards within/across columns
- edit card priority, due date, assignee
- add/remove columns

Each change updates React state, then persists via `PUT` API.

### Step 5: Use AI sidebar

In `AISidebarChat`, sending a message posts to `/api/ai/chat`. Backend:

1. loads current board + chat history
2. builds prompt
3. calls OpenAI
4. validates assistant JSON output
5. optionally applies/persists board update
6. stores chat messages

### Step 6: Data is stored in MySQL

Tables (created in `backend/app/db.py`):

- `users`
- `boards`
- `chat_messages`

So data survives container restarts (via Docker volume).

---

## 6. Detailed Code Review with Samples

## 6.1 Backend API Layer (`backend/app/main.py`)

`main.py` wires routes, auth checks, services, and startup behavior.

### Authentication guard

```python
def _require_authenticated_username(request: Request) -> str:
    token = request.cookies.get(settings.auth_cookie_name)
    username = settings.verify_session(token or "")
    if username is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return username
```

Why it matters:

- centralizes auth protection
- reused by board/AI routes

### AI chat endpoint flow

```python
assistant_output = ai_assistant_service.generate_reply(
    board=board,
    chat_history=prompt_history,
    user_message=user_message,
)

if assistant_output.board is not None:
    saved = board_service.save_board(username, assistant_output.board, board_id=board_id)
```

Why it matters:

- AI can suggest a full board update
- backend still validates before saving

---

## 6.2 Configuration and Session Signing (`backend/app/config.py`)

Session cookie values are signed using HMAC.

```python
def sign_session(self, username: str) -> str:
    key = self._get_secret_key().encode()
    signature = hmac.new(key, username.encode(), hashlib.sha256).hexdigest()
    return f"{username}:{signature}"
```

This prevents simple tampering (user cannot just change username without breaking signature).

---

## 6.3 Database Bootstrap and Schema (`backend/app/db.py`)

On startup, backend initializes DB and tables if missing.

```python
schema_statements = (
    """
    CREATE TABLE IF NOT EXISTS users (...)
    """,
    """
    CREATE TABLE IF NOT EXISTS boards (...)
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (...)
    """,
)
```

It also applies migration-style checks (adding missing columns/constraints) so older schemas can be upgraded.

---

## 6.4 Board Validation Model (`backend/app/kanban.py`)

This is a key reliability layer. The app enforces board consistency.

```python
if len(all_column_card_ids) != len(set(all_column_card_ids)):
    raise ValueError("Each card ID must appear in at most one column.")

if set(self.cards.keys()) != set(all_column_card_ids):
    raise ValueError("Every card must appear in exactly one column.")
```

Why it matters:

- prevents corrupted board data
- guards against bad client payloads and bad AI output

---

## 6.5 Repository + Service Pattern

### Repository example (`board_repository.py`)

Repositories run SQL and map DB rows to Python dicts.

```python
cursor.execute(
    "SELECT id, name, board_json FROM boards WHERE id = %s AND user_id = %s",
    (board_id, user_id),
)
```

### Service example (`board_service.py`)

Services validate and orchestrate repository calls.

```python
validated_board = BoardPayload.model_validate(board_data)
saved = self._repository.save_board(username, board_payload, board_id=effective_board_id)
```

Why this split is good:

- easier testing
- cleaner responsibilities

---

## 6.6 OpenAI Wrapper and Assistant Parser

### OpenAI service (`openai_service.py`)

```python
response = client.responses.create(
    model=self._model,
    input=prompt_text,
)
```

It translates low-level exceptions into app-specific errors (`OpenAIConfigError`, `OpenAIUpstreamError`).

### Assistant output schema (`ai_assistant_service.py`)

```python
class AIAssistantOutput(BaseModel):
    assistant_message: str = Field(min_length=1)
    board: dict[str, Any] | None = None
```

This is strict and protects downstream logic from malformed AI output.

---

## 6.7 Frontend Auth Gate (`frontend/src/components/AuthGate.tsx`)

`AuthGate` decides whether to show login UI or the full board app.

```tsx
if (authState === "unauthenticated") {
  return <SignInOrRegisterUI />;
}

return (
  <>
    <BoardSelector ... />
    <KanbanBoard ... />
  </>
);
```

Also includes local fallback mode for non-production when backend routes are unavailable.

---

## 6.8 Frontend Board State + Persist (`KanbanBoard.tsx`)

Local state is updated optimistically and persisted asynchronously.

```tsx
const applyBoardUpdate = useCallback((updater) => {
  setBoard((previousBoard) => {
    const nextBoard = updater(previousBoard);
    queueMicrotask(() => void persistBoard(nextBoard));
    return nextBoard;
  });
}, [persistBoard]);
```

Why it matters:

- UI feels immediate
- network save happens in background

---

## 6.9 Drag-and-Drop Core Logic (`frontend/src/lib/kanban.ts`)

Card movement logic is centralized in `moveCard`.

```ts
if (activeColumnId === overColumnId) {
  // reorder inside same column
} else {
  // move between columns
}
```

This keeps DnD logic testable and independent from UI components.

---

## 6.10 AI Sidebar (`AISidebarChat.tsx`)

The component supports both API mode and local fallback mode.

```tsx
const response = await fetch(chatUrl, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  credentials: "include",
  body: JSON.stringify({ message: trimmedMessage }),
});
```

If backend returns board updates, it calls:

```tsx
onBoardUpdate(payload.board, { persist: false });
```

This avoids double-saving because backend already persisted board changes.

---

## 6.11 Testing Strategy

### Backend (Pytest)

- endpoint behavior (`test_auth.py`, `test_board_api.py`, `test_ai_chat_api.py`)
- service and repository logic (`test_board_service.py`, `test_board_repository.py`, etc.)
- startup/DB initialization (`test_db_init.py`)
- multi-step integration journey (`test_integration.py`)

### Frontend (Vitest + Playwright)

- unit/component tests for auth, board, selector, AI chat
- e2e browser flows (`frontend/tests/kanban.spec.ts`) such as:
  - login
  - add card
  - AI rename
  - drag card
  - logout

---

## 7. Self-Review: Improvement Suggestions

Here are the most important improvements I would make next.

1. Security hardening
- Replace custom signed cookie format with server-side sessions or JWTs with expiry/rotation.
- Add CSRF protection for auth-changing endpoints.
- Never store real keys in `.env` committed/shared workspaces; rotate exposed keys immediately.

2. Rate limiting and abuse protection
- Current login/register limiter is in-memory (resets on restart, not shared across instances).
- Move to Redis-based rate limiting for production.

3. Authentication model cleanup
- Remove legacy fallback credentials path once DB-backed users are mandatory.
- Add account lockout/backoff policy after repeated failures.

4. Data integrity and transactions
- Wrap multi-step DB writes (especially AI update + chat writes) in explicit transactions.
- Add stricter DB constraints for board ownership and message consistency.

5. API and architecture polish
- Introduce explicit API versioning (`/api/v1/...`).
- Split `main.py` into router modules (`auth`, `boards`, `ai`) for maintainability.

6. Observability
- Add structured logging, correlation IDs, and metrics (latency/error rates per endpoint).
- Add audit logs for board mutations and AI-applied changes.

7. Frontend robustness
- Add retry/backoff for transient save failures.
- Show finer-grained save states per action, not only global “saving”.

8. Testing depth
- Add DB-backed integration tests against real MySQL in CI.
- Add more negative tests around malformed AI JSON and partial update conflicts.

---

## 8. Quick “How To Explore” Checklist for Beginners

1. Start app with `./scripts/start.sh`.
2. Open `http://localhost:8000`.
3. Register a user and create a board.
4. Edit cards and inspect network calls in browser devtools.
5. Open `backend/app/main.py` and match each request to route handlers.
6. Open `backend/app/services` to see business logic.
7. Run tests:
   - backend: `cd backend && uv run pytest`
   - frontend unit: `cd frontend && npm run test:unit`
   - frontend e2e: `cd frontend && npm run test:e2e`

That path gives you the fastest understanding of how the full stack works together.
