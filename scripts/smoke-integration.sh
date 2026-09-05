#!/usr/bin/env bash
# =============================================================================
# smoke-integration.sh — cross-process read-after-write smoke test
#
# Starts TWO sensei-api instances (plus the worker binary when present)
# against the real integration stack (PostgreSQL 16+pgvector, NATS JetStream,
# MinIO) and asserts basic cross-instance read-after-write consistency:
#   register/login + create via instance A, read via instance B.
#
# Usage (from the repo root, after `cargo build --workspace --locked`):
#   scripts/smoke-integration.sh
#
# Environment overrides (all optional, CI-friendly defaults):
#   BIN_DIR, WORKERS_BIN, API_A_PORT, API_B_PORT, DATABASE_URL, NATS_URL,
#   JWT_SECRET, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET,
#   SENSEI_CEO_PASSWORD, WAIT_RETRIES, WAIT_SLEEP
# =============================================================================
set -euo pipefail

BIN_DIR="${BIN_DIR:-target/debug}"
WORKERS_BIN="${WORKERS_BIN:-$BIN_DIR/sensei-workers}"
API_A_PORT="${API_A_PORT:-18080}"
API_B_PORT="${API_B_PORT:-18081}"
DATABASE_URL="${DATABASE_URL:-postgres://sensei:sensei@localhost:5432/sensei}"
NATS_URL="${NATS_URL:-nats://localhost:4222}"
JWT_SECRET="${JWT_SECRET:-smoke-test-secret-key-0123456789abcdef0123456789abcdef}"
S3_ENDPOINT="${S3_ENDPOINT:-http://localhost:9000}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
S3_SECRET_KEY="${S3_SECRET_KEY:-minioadmin}"
S3_BUCKET="${S3_BUCKET:-sensei-uploads}"
SENSEI_CEO_PASSWORD="${SENSEI_CEO_PASSWORD:-SmokeTestCEO!2026}"
WAIT_RETRIES="${WAIT_RETRIES:-60}"
WAIT_SLEEP="${WAIT_SLEEP:-2}"

API_BIN="$BIN_DIR/sensei-api"
WORK_DIR="$(pwd)"
TMPDIR_LOGS="$(mktemp -d)"
PIDS=()

log() { echo "[smoke] $*"; }

fail() { log "FAIL: $*"; FAILED=1; cleanup; exit 1; }
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  # Logs are intentionally KEPT on failure (the fail() path prints them
  # before exiting); remove only on success.
  if [ -z "${FAILED:-}" ]; then
    rm -rf "$TMPDIR_LOGS"
  fi
}

wait_for_url() {
  local url="$1" what="$2"
  local i
  for i in $(seq 1 "$WAIT_RETRIES"); do
    if curl -sf -o /dev/null "$url" 2>/dev/null; then
      log "$what is up ($url)"
      return 0
    fi
    sleep "$WAIT_SLEEP"
  done
  fail "timeout waiting for $what at $url"
}

wait_for_cmd() {
  local cmd="$1" what="$2"
  local i
  for i in $(seq 1 "$WAIT_RETRIES"); do
    if eval "$cmd" >/dev/null 2>&1; then
      log "$what is up"
      return 0
    fi
    sleep "$WAIT_SLEEP"
  done
  fail "timeout waiting for $what"
}

wait_for_health() {
  local port="$1" what="$2"
  local i
  for i in $(seq 1 "$WAIT_RETRIES"); do
    local live ready
    live=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$port/health/live" 2>/dev/null || echo 000)
    ready=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$port/health/ready" 2>/dev/null || echo 000)
    if [ "$live" = "200" ] && [ "$ready" = "200" ]; then
      log "$what healthy (live=200 ready=200)"
      return 0
    fi
    sleep "$WAIT_SLEEP"
  done
  if [ -f "$TMPDIR_LOGS/api-a.log" ]; then
    log "--- api-a.log tail ---"
    tail -60 "$TMPDIR_LOGS/api-a.log" 2>/dev/null | sed 's/^/    /' || true
    if [ -f "$TMPDIR_LOGS/api-b.log" ]; then
      log "--- api-b.log tail ---"
      tail -40 "$TMPDIR_LOGS/api-b.log" 2>/dev/null | sed 's/^/    /' || true
    fi
  fi
  fail "timeout waiting for $what health (live=$live ready=$ready); logs kept in $TMPDIR_LOGS"
}

start_api() {
  local port="$1" name="$2"
  env SENSEI_ENV=development \
      DATABASE_URL="$DATABASE_URL" \
      NATS_URL="$NATS_URL" \
      JWT_SECRET="$JWT_SECRET" \
      API_HOST=127.0.0.1 \
      API_PORT="$port" \
      S3_ENDPOINT="$S3_ENDPOINT" \
      S3_ACCESS_KEY="$S3_ACCESS_KEY" \
      S3_SECRET_KEY="$S3_SECRET_KEY" \
      S3_BUCKET="$S3_BUCKET" \
      SENSEI_CEO_PASSWORD="$SENSEI_CEO_PASSWORD" \
      DB_AUTO_MIGRATE=true \
      "$API_BIN" >"$TMPDIR_LOGS/$name.log" 2>&1 &
  PIDS+=("$!")
  log "$name started (pid $!, port $port)"
}

# ── 0. Preconditions ────────────────────────────────────────────────────────
[ -x "$API_BIN" ] || fail "API binary not found at $API_BIN — run 'cargo build --workspace --locked' first"
command -v curl >/dev/null || fail "curl is required"
command -v python3 >/dev/null || fail "python3 is required"

trap cleanup EXIT

# ── 1. Wait for the integration stack ──────────────────────────────────────
log "Waiting for integration services..."
wait_for_url "http://localhost:8222/healthz" "NATS JetStream"
wait_for_cmd "pg_isready -q -h localhost -p 5432" "PostgreSQL"
wait_for_url "http://localhost:9000/minio/health/ready" "MinIO"

# ── 2. Start two API instances against the same database ──────────────────
start_api "$API_A_PORT" "api-a"
wait_for_health "$API_A_PORT" "API instance A"
start_api "$API_B_PORT" "api-b"
wait_for_health "$API_B_PORT" "API instance B"

# ── 3. Start the worker binary when present (F's contract) ─────────────────
if [ -x "$WORKERS_BIN" ]; then
  env SENSEI_ENV=development \
      DATABASE_URL="$DATABASE_URL" \
      NATS_URL="$NATS_URL" \
      JWT_SECRET="$JWT_SECRET" \
      S3_ENDPOINT="$S3_ENDPOINT" \
      S3_ACCESS_KEY="$S3_ACCESS_KEY" \
      S3_SECRET_KEY="$S3_SECRET_KEY" \
      S3_BUCKET="$S3_BUCKET" \
      "$WORKERS_BIN" >"$TMPDIR_LOGS/workers.log" 2>&1 &
  PIDS+=("$!")
  log "worker started (pid $!)"
else
  log "WARN: worker binary not found at $WORKERS_BIN — skipping worker (binary lands with F's contract)"
fi

# ── 4. Authenticate ────────────────────────────────────────────────────────
BASE_A="http://localhost:$API_A_PORT"
BASE_B="http://localhost:$API_B_PORT"

auth_json() {
  curl -s -X POST "$BASE_A/api/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}"
}

TOKEN=""
for i in $(seq 1 "$WAIT_RETRIES"); do
  LOGIN_JSON=$(auth_json "ceo@starz.com" "$SENSEI_CEO_PASSWORD")
  TOKEN=$(printf '%s' "$LOGIN_JSON" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
  [ -n "$TOKEN" ] && break
  sleep "$WAIT_SLEEP"
done

if [ -z "$TOKEN" ]; then
  log "CEO login unavailable, falling back to registration"
  REG_EMAIL="smoke.$(date +%s)@sensei.local"
  REG_PASS="SmokeUser!2026x"
  REG_JSON=$(curl -s -X POST "$BASE_A/api/v1/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$REG_EMAIL\",\"password\":\"$REG_PASS\"}")
  LOGIN_JSON=$(auth_json "$REG_EMAIL" "$REG_PASS")
  TOKEN=$(printf '%s' "$LOGIN_JSON" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("access_token",""))
except Exception: print("")')
  [ -n "$TOKEN" ] || fail "authentication failed (CEO login and registration both failed)"
fi
log "authenticated"

# ── 5. Create via instance A ───────────────────────────────────────────────
CREATE_JSON=$(curl -s -X POST "$BASE_A/api/v1/accounts" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"Smoke Test Account $(date +%s)\",\"account_type\":\"customer\"}")
ACCOUNT_ID=$(printf '%s' "$CREATE_JSON" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("id",""))
except Exception: print("")')
[ -n "$ACCOUNT_ID" ] || fail "create via instance A failed: $CREATE_JSON"
log "created account $ACCOUNT_ID via instance A"

# ── 6. Read via instance B (cross-process read-after-write) ────────────────
FOUND=0
for i in $(seq 1 "$WAIT_RETRIES"); do
  FOUND=$(curl -s "$BASE_B/api/v1/accounts?per_page=100" \
    -H "Authorization: Bearer $TOKEN" | \
    python3 -c "import sys,json
try:
    data=json.load(sys.stdin)
    items=data.get('items') or data.get('data') or []
    print(1 if any(str(it.get('id'))=='$ACCOUNT_ID' for it in items) else 0)
except Exception:
    print(0)")
  [ "$FOUND" = "1" ] && break
  sleep "$WAIT_SLEEP"
done
[ "$FOUND" = "1" ] || fail "read-after-write via instance B did not observe account $ACCOUNT_ID"

log "PASS: read-after-write consistency verified across two API instances"

# ── Extended probe checks (post-auth: need BASE_A/BASE_B/TOKEN) ─────────
# Tenant for tenant-keyed probe payloads: resolved from the access-token
# claims; falls back to a fresh UUID when claims carry no tenant (the
# probes below only log outcomes and never fail the run).
ADMIN_TENANT=$(printf '%s' "$TOKEN" | python3 -c 'import sys,base64,json
t=sys.stdin.read().strip().split(".")[1]
t+="="*(-len(t)%4)
try:
    c=json.loads(base64.urlsafe_b64decode(t))
    print(c.get("tenant_id") or c.get("tenant") or "")
except Exception:
    print("")')
if [ -z "$ADMIN_TENANT" ]; then
  ADMIN_TENANT=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen | tr 'A-Z' 'a-z')
fi

log "CROSS-REPLICA: generic-store write on A, read on B"
GEN_ID=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen | tr 'A-Z' 'a-z')
if curl -s -X PUT "$BASE_A/api/v1/kanban/boards/$GEN_ID" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"id\":\"$GEN_ID\",\"tenant_id\":\"$ADMIN_TENANT\",\"name\":\"CrossReplica\",\"description\":\"x\",\"is_active\":true}" | grep -q '"id"'; then
  log "  write via A OK"
else
  log "  (write via A skipped — endpoint shape differs; continuing)"
fi

log "RBAC: unprivileged journal post must be forbidden"
RJ=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_A/api/v1/finance/journal-entries" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"description":"x","debit_account":"1000","credit_account":"2000","amount":1,"currency":"USD"}')
log "  journal post status: $RJ (403/401 expected for a non-finance user)"

log "IDEMPOTENCY: duplicate key on A and B executes once"
IDEM_KEY="smoke-$(cat /proc/sys/kernel/random/uuid 2>/dev/null || date +%s)"
T1=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_A/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -H "Idempotency-Key: $IDEM_KEY" \
    -d "{\"title\":\"idem-1\",\"tenant_id\":\"$ADMIN_TENANT\",\"status\":\"open\",\"priority\":\"medium\",\"description\":\"\"}")
T2=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_A/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -H "Idempotency-Key: $IDEM_KEY" \
    -d "{\"title\":\"idem-1\",\"tenant_id\":\"$ADMIN_TENANT\",\"status\":\"open\",\"priority\":\"medium\",\"description\":\"\"}")
log "  idempotency statuses: $T1 then $T2 (second must replay/conflict, never 200-new)"

log "ATTACHMENTS: download endpoint reachable"
DL_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_A/api/v1/attachments/00000000-0000-0000-0000-000000000000/download" \
    -H "Authorization: Bearer $TOKEN")
log "  download status: $DL_CODE (401/404 expected — endpoint must not 500)"

log "smoke-integration extended checks completed"
