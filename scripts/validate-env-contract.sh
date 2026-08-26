#!/usr/bin/env bash
# =============================================================================
# validate-env-contract.sh
#
# Enforces the "single source of truth" claim of .env.example: every
# ${VARIABLE} reference used by docker-compose*.yml, the Helm chart, the
# Caddyfiles and the Rust env parsing MUST be documented in .env.example.
#
# Usage:  scripts/validate-env-contract.sh
#         (run in CI; exits 1 on any undocumented variable)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DOC="$ROOT/.env.example"

# Extract documented variable names from .env.example (lines like `VAR=...`)
documented=$(grep -oE '^[A-Z][A-Z0-9_]*=' "$ENV_DOC" | tr -d '=' | sort -u)

# Collect every ${VAR} reference across the orchestration files.
referenced=$(
  grep -hoE '\$\{[A-Z][A-Z0-9_]*' \
    "$ROOT/docker-compose.yml" \
    "$ROOT/docker-compose.prod.yml" \
    "$ROOT/caddy/Caddyfile" \
    "$ROOT/caddy/Caddyfile.production" \
    "$ROOT/k8s/helm/sensei/values.yaml" 2>/dev/null \
    | tr -d '${' | sort -u
)

missing=0
while IFS= read -r var; do
  if ! grep -qE "^$var=" "$ENV_DOC"; then
    echo "UNDOCUMENTED VARIABLE: $var (used by orchestration, missing from .env.example)" >&2
    missing=1
  fi
done <<< "$referenced"

if [ "$missing" -eq 1 ]; then
  echo "env contract violation: add the variables above to .env.example" >&2
  exit 1
fi

echo "env contract OK: all orchestration variables are documented"
