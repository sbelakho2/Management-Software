#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-3000}"

# Ensure frontend points at the locally-running backend.
# Note: the frontend also reads frontend/.env.local automatically.
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8001}"
export API_INTERNAL_URL="${API_INTERNAL_URL:-http://localhost:8001}"

cd "$FRONTEND_DIR"

echo "Starting frontend dev server on http://$HOST:$PORT"
echo "Using NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL"

while true; do
  npm run dev -- --hostname "$HOST" --port "$PORT"
  exit_code=$?
  echo "next dev exited with code $exit_code; restarting in 1s..." >&2
  sleep 1
done
