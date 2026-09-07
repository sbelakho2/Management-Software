#!/usr/bin/env bash
# =============================================================================
# validate-tenant-db-access.sh — thirtieth-first audit items 7-9 enforcement.
#
# Hard architecture gate: every SQL statement touching a tenant-owned
# table must execute through TenantTx (sensei_core::db::TenantTx — or the
# equivalent tenant-scoped tx helpers such as
# sensei_services::tps::replication::with_tenant_tx, which begin a
# transaction and establish SET LOCAL app.tenant_id at construction).
# A raw-pool statement (fetch/execute on &self.pool, or self.pool.begin())
# runs WITHOUT the FORCE-RLS tenant context of migration 175: reads
# silently return zero rows and writes silently admit zero rows under the
# production sensei_app role.
#
# The allowlist is the EXPLICITLY REVIEWED exception surface:
#   - crates/sensei-services/src/tenants/database.rs — the tenants table
#     has no tenant_id column and no RLS (documented exception; leave it
#     untouched);
#   - crates/sensei-services/src/users/pretenant_lookup.rs — the migration
#     175 narrow exception: the SECURITY DEFINER identity functions
#     (auth_user_by_email / auth_user_by_id / auth_users_all), whose
#     BYPASSRLS-owner bodies are the ONLY tenant-context-free readers of
#     `users`, called over the raw pool from a single dedicated module.
#
# Usage: scripts/validate-tenant-db-access.sh  (run from the repo root)
#
# Local verification during a parallel conversion wave: set
# SENSEI_ALLOW_PENDING_CONVERSIONS=1 to list (but not fail on) offenders
# in files NOT on the allowlist — CI never sets this variable, so the
# merged tree must be fully clean.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_SRC="$ROOT/sensei-rs/crates/sensei-services/src"
API_SRC="$ROOT/sensei-rs/crates/sensei-api/src"

if [ ! -d "$SERVICE_SRC" ] || [ ! -d "$API_SRC" ]; then
    echo "tenant-db-access: expected sensei-rs sources under $ROOT/sensei-rs" >&2
    exit 1
fi

# Allowlisted raw-pool files (see the header): every other file must run
# its tenant SQL through TenantTx.
ALLOWED=(
    "sensei-rs/crates/sensei-services/src/tenants/database.rs"
    "sensei-rs/crates/sensei-services/src/users/pretenant_lookup.rs"
)

violations=0

# Collapse a matched file path to its repo-root-relative form (rg is run
# against the two src trees from the repo root).
relative() {
    local f="$1"
    case "$f" in
        "$ROOT/"*) echo "${f#"$ROOT"/}" ;;
        *) echo "$f" ;;
    esac
}

allowed() {
    local rel a
    rel="$(relative "$1")"
    for a in "${ALLOWED[@]}"; do
        [ "$rel" = "$a" ] && return 0
    done
    return 1
}

# Scan one rg pattern; every hit whose file is not allowlisted is a
# violation. Runs in the CURRENT shell (no pipe), so the counter sticks.
scan() {
    local label="$1"
    local pattern="$2"
    local hits
    hits="$(rg -n "$pattern" "$SERVICE_SRC" "$API_SRC" 2>/dev/null || true)"
    if [ -n "$hits" ]; then
        while IFS= read -r line; do
            [ -z "$line" ] && continue
            file="${line%%:*}"
            if allowed "$file"; then
                echo "tenant-db-access ALLOWED ($label): $line"
            else
                echo "tenant-db-access VIOLATION ($label): $line" >&2
                violations=1
            fi
        done <<< "$hits"
    fi
}

# Every direct-pool execution in the two application crates.
scan "direct &self.pool fetch/execute" \
    '\.(fetch_one|fetch_all|fetch_optional|fetch_many|execute)\(&self\.pool\)'
# Raw transaction begins on the service's own pool handle.
scan "self.pool.begin()" \
    'self\.pool\.begin\(\)'

if [ "$violations" -eq 1 ]; then
    if [ "${SENSEI_ALLOW_PENDING_CONVERSIONS:-0}" = "1" ]; then
        echo "tenant-db-access: PENDING CONVERSIONS PRESENT (SENSEI_ALLOW_PENDING_CONVERSIONS=1 — local parallel-wave verification only; CI fails on these)" >&2
        exit 0
    fi
    echo "tenant-db-access FAIL: every tenant-owned SQL statement must execute through TenantTx (sensei_core::db::TenantTx); only the migration-175 pre-tenant lookups (users/pretenant_lookup.rs) and tenants/database.rs are exempt" >&2
    exit 1
fi

echo "tenant-db-access OK: no raw-pool tenant SQL outside the reviewed allowlist"
echo "  scanned: sensei-rs/crates/sensei-services/src + sensei-rs/crates/sensei-api/src"
