# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend .
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/backend

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend .
COPY --from=frontend-builder /app/frontend/out /app/frontend-dist

RUN addgroup --system app && adduser --system --ingroup app app && \
    chown -R app:app /app

ENV PATH="/app/backend/.venv/bin:$PATH" \
    FRONTEND_DIST_DIR="/app/frontend-dist"

USER app

EXPOSE 8000

CMD ["/app/backend/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
