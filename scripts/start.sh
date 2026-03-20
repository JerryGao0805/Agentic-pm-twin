#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

docker compose up --build -d

echo "App URL: http://localhost:8000"
echo "Health URL: http://localhost:8000/api/health"
