# Frontend codebase guide

## Purpose

This directory contains the current Kanban MVP frontend built with Next.js.
Sign-in and board data are now API-backed when served by FastAPI.

## Tech stack

- Next.js App Router (`src/app`)
- React + TypeScript
- Tailwind CSS v4 (via `@tailwindcss/postcss`)
- Drag and drop with `@dnd-kit/*`
- Testing: Vitest + Testing Library + Playwright

## Current behavior

- Renders a single Kanban board at `/`.
- Requires sign-in (`user` / `password`) before showing the board.
- Uses backend auth endpoints (`/api/auth/*`) when available.
- Loads and saves board data via backend endpoint (`/api/board`) when available.
- Renders an AI sidebar chat that loads history from `/api/ai/chat/history` and sends prompts to `/api/ai/chat`.
- Applies AI-returned board updates in-place without a page reload.
- Keeps a localStorage fallback mode in non-production when backend endpoints are missing (for standalone `next dev`).
- Uses fixed column IDs from `src/lib/kanban.ts` and supports:
  - renaming column titles
  - adding cards
  - deleting cards
  - dragging cards within and across columns

## Structure

- `src/app/page.tsx`: app entry; renders `AuthGate`.
- `src/components/AuthGate.tsx`: login/logout gate and auth state handling.
- `src/components/KanbanBoard.tsx`: board loading/saving + drag/drop orchestration.
- `src/components/AISidebarChat.tsx`: sidebar chat UI, AI request flow, and local fallback chat mode.
- `src/components/KanbanColumn.tsx`: droppable column with editable title.
- `src/components/KanbanCard.tsx`: sortable card item.
- `src/components/KanbanCardPreview.tsx`: drag overlay preview.
- `src/components/NewCardForm.tsx`: add-card inline form.
- `src/lib/kanban.ts`: board types, seed data, move helpers, ID creation.

## Styling

- Global theme tokens are in `src/app/globals.css`.
- Core palette matches project colors:
  - `--accent-yellow: #ecad0a`
  - `--primary-blue: #209dd7`
  - `--secondary-purple: #753991`
  - `--navy-dark: #032147`
  - `--gray-text: #888888`

## Tests

- Unit tests:
  - `src/components/AuthGate.test.tsx`
  - `src/components/AISidebarChat.test.tsx`
  - `src/lib/kanban.test.ts`
  - `src/components/KanbanBoard.test.tsx`
- E2E tests:
  - `tests/kanban.spec.ts`
- Commands:
  - `npm run test:unit`
  - `npm run test:e2e`
  - `npm run test:all`

## Notes

- Keep `data-testid` patterns stable unless tests are updated (`column-*`, `card-*`).
- Playwright is currently configured for local Next dev at `http://127.0.0.1:3000`.
- In Docker/runtime integration, the frontend is served by FastAPI at port `8000`.
