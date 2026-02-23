#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if command -v docker >/dev/null 2>&1; then
  cd "$ROOT_DIR"
  docker compose build
  docker compose run --rm app python -m ruff format --check /app
  docker compose run --rm app python -m ruff check /app
  docker compose run --rm app python -m mypy /app
  docker compose run --rm app python -m pytest -q --cov=/app --cov-report=term-missing /app
  exit 0
fi

cd "$ROOT_DIR/backend"
LOCAL_DB_PATH="${ROOT_DIR}/data/app.db"
mkdir -p "$(dirname "$LOCAL_DB_PATH")"

if python -c "import pip" >/dev/null 2>&1; then
  python -m pip install --no-cache-dir -r requirements.txt
  python -m ruff format --check .
  python -m ruff check .
  python -m mypy .
  DB_PATH="$LOCAL_DB_PATH" python -m pytest -q --cov=app --cov-report=term-missing
  exit 0
fi

if command -v uv >/dev/null 2>&1; then
  if [ ! -d ".venv" ]; then
    uv venv -q
  fi

  uv pip install -q -r requirements.txt
  uv run ruff format --check .
  uv run ruff check .
  uv run mypy .
  DB_PATH="$LOCAL_DB_PATH" uv run pytest -q --cov=app --cov-report=term-missing
  exit 0
fi

echo "QA: não foi possível rodar localmente (docker indisponível, python sem pip e uv ausente)." >&2
exit 1
