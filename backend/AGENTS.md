# Backend guide

## Purpose

This directory contains the FastAPI backend for the Project Management MVP.

## Current scope

- `app/main.py`: FastAPI app, static frontend served at `/`, auth/session endpoints, health endpoint, board APIs, `/api/ai/test`, `/api/ai/chat`, and `/api/ai/chat/history`.
- `app/config.py`: environment-backed runtime settings (DB, auth, OpenAI model/key).
- `app/db.py`: MySQL connection helpers, database initialization, schema creation, and startup seeding.
- `app/kanban.py`: board JSON schema validation (fixed column IDs) and default board seed data.
- `app/repositories/board_repository.py`: board load/save persistence.
- `app/repositories/chat_repository.py`: chat history load/append persistence.
- `app/services/board_service.py`: board validation + persistence orchestration.
- `app/services/chat_service.py`: chat message validation + persistence orchestration.
- `app/services/openai_service.py`: basic OpenAI text-response client wrapper.
- `app/services/ai_assistant_service.py`: prompt builder + strict AI JSON output parser for board assistant flow.
- `pyproject.toml`: Python dependencies managed by `uv`.
- `Dockerfile`: multi-stage image build (frontend static export + backend runtime).
- `tests/`: auth, board, AI, chat, and DB init test suites.

## Run (from repository root)

Use `./scripts/start.sh` and `./scripts/stop.sh`.
