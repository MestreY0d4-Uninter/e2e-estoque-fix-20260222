#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if command -v docker >/dev/null 2>&1; then
  cd "$ROOT_DIR"
  docker compose build
  docker compose run --rm app python -m ruff format --check /app
  docker compose run --rm app python -m ruff check /app
  docker compose run --rm app python -m mypy /app
  docker compose run --rm app python -m pytest -q /app
  exit 0
fi

cd "$ROOT_DIR/backend"

if python -c "import pip" >/dev/null 2>&1; then
  python -m pip install --no-cache-dir -r requirements.txt
  python -m ruff format --check .
  python -m ruff check .
  python -m mypy .
  python -m pytest
  exit 0
fi

echo "QA: não foi possível rodar localmente (python sem pip e docker indisponível)." >&2
exit 0
