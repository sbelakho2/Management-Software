#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8001}"

# Find pids listening on the port and kill them.
pids=$(ss -ltnp 2>/dev/null | grep ":$PORT " || true)
pids=$(printf '%s\n' "$pids" | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)
if [[ -n "${pids}" ]]; then
  echo "Killing processes on port $PORT: ${pids}"
  kill -TERM ${pids} 2>/dev/null || true
  sleep 1
  still=$(ss -ltnp 2>/dev/null | grep ":$PORT " || true)
  still=$(printf '%s\n' "$still" | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)
  if [[ -n "${still}" ]]; then
    echo "Force killing remaining pids on port $PORT: ${still}"
    kill -KILL ${still} 2>/dev/null || true
  fi
else
  echo "Port $PORT is already free"
fi

echo "Starting backend on port $PORT"
PORT="$PORT" exec "$ROOT_DIR/scripts/dev_backend.sh"
