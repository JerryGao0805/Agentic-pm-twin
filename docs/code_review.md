# Code Review Report

## Executive Summary

I reviewed the full source + config surface of the repository (`backend`, `frontend`, runtime scripts/configs, and tests), excluding vendor/generated artifacts (`node_modules`, `.next`, `out`).

Current state:

- Core backend and frontend unit/integration suites are healthy.
- There are important issues in security posture and test/tooling reliability.
- The highest-priority risks are exposed secrets in local config, custom session design limitations, and broken frontend E2E execution.

Command evidence snapshot:

- `cd backend && uv run pytest` -> **105 passed**, **1 warning** (deprecation warning).
- `cd frontend && npm run test:unit` -> **26 passed**.
- `cd frontend && npm run lint` -> passes now, but showed an intermittent tooling path issue in an earlier run.
- `cd frontend && npm run test:e2e` -> **fails** (web server boot/build resolution failures and timeout).

---

## Findings (Ordered by Severity)

### Critical

#### F-001
- Location: `.env:1`
- Issue: A live-looking `OPENAI_API_KEY` is present in plaintext in workspace config.
- Impact/Risk: High likelihood of credential leakage through logs, screenshots, shell history, backups, or accidental commit/share. Potential unauthorized API usage and billing exposure.
- Evidence:
  - `.env:1` contained a full OpenAI secret-like value in plaintext.
- Recommended Action:
  1. Rotate/revoke this key immediately.
  2. Replace `.env` with non-sensitive local values only.
  3. Use a secrets manager or developer-local secret injection workflow.
  4. Add a CI secret scan gate (`gitleaks` or similar); optional local pre-commit scanning can be added later.
- Effort: `S`

### High

#### F-002
- Location: `backend/app/config.py:48-65`, `backend/app/main.py:196-204`, `backend/app/main.py:231-239`
- Issue: Custom cookie token signing uses `username:HMAC(username)` with no embedded expiry, nonce, or server-side revocation state.
- Impact/Risk: Session invalidation is coarse-grained (secret rotation/global cookie expiry). Compromised cookies can be replayed until expiration; no per-session revoke/logout-all support.
- Evidence:
  - `sign_session`/`verify_session` are deterministic on username and secret only.
  - Cookie `max_age` is set, but token itself contains no temporal claim.
- Recommended Action:
  1. Move to server-side session storage (session ID + DB/Redis) or signed JWT with `exp`, `iat`, and rotation strategy.
  2. Add session revocation/versioning by user.
  3. Keep `HttpOnly` and enforce `Secure` in non-local deployments.
- Effort: `M`

#### F-003
- Location: `frontend/playwright.config.ts:13-18`, `frontend/next.config.ts:3-5`, root `package-lock.json` (no root `package.json`)
- Issue: Frontend E2E suite cannot run reliably due Next workspace root inference and module resolution failures (`Can't resolve 'tailwindcss'`) during Playwright `webServer` startup.
- Impact/Risk: E2E coverage is effectively unavailable in CI/local verification paths, increasing regression risk for real user flows.
- Evidence:
  - `npm run test:e2e` fails with repeated `Can't resolve 'tailwindcss' in '/.../pm_twin'` and web server timeout.
  - Next warning indicates inferred workspace root from root lockfile and multiple lockfiles detected.
- Recommended Action:
  1. Set `turbopack.root` in `frontend/next.config.ts` to the frontend directory.
  2. Remove accidental/unused root Node lockfile or formalize workspace with root `package.json`.
  3. Revalidate Playwright startup path after root fix.
- Effort: `S`

#### F-004
- Location: `backend/app/repositories/board_repository.py:111-146`, `backend/app/main.py:337-343`
- Issue: Legacy `PUT /api/board` can create new boards if payload lacks `id`/`board_id`, because `save_board(..., board_id=None)` inserts a new row.
- Impact/Risk: Silent board duplication and data drift for clients using legacy endpoint shape without metadata.
- Evidence:
  - `save_board` inserts when `board_id is None`.
  - Legacy endpoint path invokes `save_board(username, body)` without explicit `board_id`.
- Recommended Action:
  1. For legacy endpoint, resolve target board deterministically (latest board id) and force update-only semantics.
  2. Alternatively, reject payloads missing board identity on update endpoints.
  3. Add regression tests for no-id legacy update behavior.
- Effort: `M`

### Medium

#### F-005
- Location: `backend/app/main.py:424-442`
- Issue: AI board update and chat message persistence are not wrapped in a single transaction.
- Impact/Risk: Partial-write states are possible (board saved but chat append fails, or vice versa), reducing data consistency and debuggability.
- Evidence:
  - Board save and two chat appends are separate service/repository calls with independent commits.
- Recommended Action:
  1. Introduce transactional unit-of-work for AI chat flow.
  2. Ensure all-or-nothing persistence for `board_after` + `user/assistant` chat rows.
  3. Add failure-injection tests for mid-flow DB errors.
- Effort: `M`

#### F-006
- Location: `backend/app/main.py:32-48`, `backend/app/main.py:179`, `backend/app/main.py:210`
- Issue: Login/register throttling is in-memory and IP-only.
- Impact/Risk: Ineffective in multi-instance deployments, restart resets counters, and shared-NAT users may be unfairly throttled.
- Evidence:
  - `_login_attempts` is process-local dict.
- Recommended Action:
  1. Move to shared limiter (Redis or API gateway).
  2. Add username-based and IP-based dimensions with tuned windows.
  3. Emit rate-limit telemetry.
- Effort: `M`

#### F-007
- Location: `backend/app/main.py:190-194`
- Issue: Default-board creation failure during registration is swallowed with `except Exception: pass`.
- Impact/Risk: Successful registration can leave user in partially initialized state without observability; root causes become hard to diagnose.
- Evidence:
  - Broad catch suppresses all exceptions without logging.
- Recommended Action:
  1. At minimum log structured warning with error details and username.
  2. Prefer compensating behavior (retry/queue) or explicit partial-init status.
- Effort: `S`

#### F-008
- Location: `backend/app/db.py:181-202`
- Issue: Migration FK application failures are swallowed (`except Error: pass`) for both `boards` and `chat_messages` constraints.
- Impact/Risk: Deployments can continue with degraded relational integrity, causing subtle orphaning/consistency bugs later.
- Evidence:
  - FK create failures are explicitly ignored in migration path.
- Recommended Action:
  1. Log and surface migration warnings with enough context.
  2. Add post-migration health checks for expected constraints.
  3. Fail startup in strict mode for production.
- Effort: `M`

#### F-009
- Location: `frontend/src/components/AuthGate.tsx:8-10, 20, 105-114`; `frontend/src/components/KanbanBoard.tsx:21, 87-117`; `frontend/src/components/AISidebarChat.tsx:34, 207-235`
- Issue: Development fallback mode allows local auth/data flows with hardcoded credentials and localStorage state when API is unavailable.
- Impact/Risk: Useful for local UX continuity, but can mask backend outages/misconfigurations and reduce signal in manual QA.
- Evidence:
  - `canUseLocalFallback` gate and `DEV_USERNAME/DEV_PASSWORD` local auth path.
- Recommended Action:
  1. Keep fallback, but add explicit visual banner and telemetry event when in fallback mode.
  2. Add env flag to disable fallback in staging-like environments.
- Effort: `S`

### Low

#### F-010
- Location: `backend/app/main.py:289, 345, 370, 387` (status constant usage)
- Issue: Deprecated status constant path appears in runtime warning context (`HTTP_422_UNPROCESSABLE_ENTITY`).
- Impact/Risk: No immediate functional break, but noisy warnings and future compatibility risk.
- Evidence:
  - Backend pytest reports deprecation warning from FastAPI/Starlette path.
- Recommended Action:
  1. Replace with `HTTP_422_UNPROCESSABLE_CONTENT` where appropriate.
  2. Keep tests asserting behavior (status and error payload).
- Effort: `S`

#### F-011
- Location: `.gitignore:1-176` (root), `frontend/.gitignore` (separate)
- Issue: Ignore strategy is split across root/frontend, and tooling behavior differed depending on generated folder presence (`frontend/test-results`).
- Impact/Risk: Inconsistent local developer experience and intermittent lint/test friction.
- Evidence:
  - Earlier `npm run lint` failed on missing `frontend/test-results` path scan; later passed once directory existed.
- Recommended Action:
  1. Harmonize ignore policy for frontend artifacts at one clear layer.
  2. Add deterministic lint invocation in CI and document required working directory.
- Effort: `S`

---

## Prioritized Action Plan

### Immediate (0-2 days)

1. Rotate and revoke exposed OpenAI key; scrub local plaintext secret usage (`F-001`).
2. Repair E2E startup path (`turbopack.root` and lockfile/root-node consistency) so Playwright is runnable (`F-003`).
3. Remove broad exception swallowing for registration board init and add logging (`F-007`).

### Near-term (this sprint)

1. Harden session architecture (expirable/revocable sessions) and set strict secure-cookie deployment guardrails (`F-002`).
2. Fix legacy `/api/board` update semantics to avoid accidental inserts (`F-004`).
3. Add transactional boundary for AI board+chat persistence (`F-005`).

### Follow-up (next sprint+)

1. Move rate limiting to shared infra (Redis/gateway) with telemetry (`F-006`).
2. Promote migration integrity checks and strict-mode startup for FK guarantees (`F-008`).
3. Add explicit fallback-mode UX/telemetry controls (`F-009`).
4. Clean deprecations and normalize ignore/tooling behavior (`F-010`, `F-011`).

---

## Validation Checklist

For each remediated high/critical item:

1. `F-001`: secret scanners report clean; rotated key confirmed invalid for previous token.
2. `F-002`: automated tests cover session expiry/revocation and replay rejection.
3. `F-003`: `npm run test:e2e` boots webServer and executes tests on a clean checkout.
4. `F-004`: legacy endpoint tests confirm update does not create new board when id absent.
5. `F-005`: failure-injection tests confirm atomic rollback semantics.

Regression baseline after fixes:

- `cd backend && uv run pytest`
- `cd frontend && npm run test:unit`
- `cd frontend && npm run lint`
- `cd frontend && npm run test:e2e`

---

## Residual Risks / Not Fully Verified

- Git history/commit metadata is unavailable in this workspace path (`.git` not present), so I cannot verify whether the `.env` secret was previously committed/pushed.
- Security posture was reviewed from source/config behavior; no live penetration testing or runtime traffic analysis was performed.
- E2E failure analysis is based on reproducible local command output; CI-specific environment differences were not observed directly.

---

Public API changes: **None** (review-only deliverable).
