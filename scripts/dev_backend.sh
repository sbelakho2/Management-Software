#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env"

PY="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$BACKEND_DIR/.venv/bin/python"
fi

if [[ ! -x "$PY" ]]; then
  echo "No Python virtualenv found. Expected $ROOT_DIR/.venv or $BACKEND_DIR/.venv" >&2
  exit 1
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"

cd "$BACKEND_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

echo "Starting backend dev server on http://$HOST:$PORT"
echo "Health: http://localhost:$PORT/health"
echo "Ready:  http://localhost:$PORT/api/v1/health/ready"
echo "Live:   http://localhost:$PORT/api/v1/health/live"

echo "Using Python: $PY"

while true; do
  "$PY" -m uvicorn sensei.main:app \
    --reload \
    --reload-dir "$BACKEND_DIR/src" \
    --host "$HOST" \
    --port "$PORT"

  exit_code=$?
  echo "uvicorn exited with code $exit_code; restarting in 1s..." >&2
  sleep 1
done
