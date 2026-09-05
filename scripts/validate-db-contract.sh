#!/usr/bin/env bash
# =============================================================================
# validate-db-contract.sh — thirtieth-audit item 28 enforcement.
#
# The DB capability contract lives in .github/.db-capability (PG_MAJOR,
# PG_IMAGE with pinned digest, required extensions). This script verifies
# that EVERY environment which chooses a PostgreSQL product carries the exact
# PG_IMAGE literal:
#   - GitHub Actions service containers (.github/workflows/*.yml)
#   - Compose services (docker-compose.yml, docker-compose.prod.yml)
#   - Helm values image pin (k8s/helm/sensei/values.yaml -> database.imagePin)
#
# A drift (e.g. a workflow reverting to `postgres:16` or an unpinned
# pgvector tag) fails the run. Exits 1 on any violation.
#
# Usage: scripts/validate-db-contract.sh  (run from the repo root)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/.github/.db-capability"

# Read the pinned capability from the manifest.
get() { awk -F= -v key="$1" '$1==key {print $2; exit}' "$MANIFEST"; }
PG_MAJOR="$(get PG_MAJOR)"
PG_IMAGE="$(get PG_IMAGE)"
PG_EXTENSIONS="$(get PG_REQUIRED_EXTENSIONS)"

if [ -z "$PG_MAJOR" ] || [ -z "$PG_IMAGE" ]; then
    echo "db-contract: .github/.db-capability is missing PG_MAJOR or PG_IMAGE" >&2
    exit 1
fi
if ! grep -q '^vector' <<<"$PG_EXTENSIONS"; then
    echo "db-contract: .github/.db-capability must list 'vector' in PG_REQUIRED_EXTENSIONS" >&2
    exit 1
fi

violations=0
check_literal() {
    # $1 = file, $2 = label; finds every PostgreSQL image reference and
    # requires it to be the exact PG_IMAGE literal.
    local file="$1" label="$2"
    local hits
    hits="$(grep -nE 'image:[[:space:]]*["'"'"']?(postgres|pgvector)[^"'"'"']*' "$file" 2>/dev/null || true)"
    if [ -n "$hits" ]; then
        while IFS= read -r line; do
            if ! grep -qF "image: $PG_IMAGE" <<<"$line" \
               && ! grep -qF "image: \"$PG_IMAGE\"" <<<"$line"; then
                echo "db-contract VIOLATION ($label): $file" >&2
                echo "  $line" >&2
                echo "  expected the pinned capability image: $PG_IMAGE" >&2
                violations=1
            fi
        done <<< "$hits"
    fi
}

for f in "$ROOT"/.github/workflows/*.yml; do
    check_literal "$f" "GitHub Actions service container"
done
for f in "$ROOT"/docker-compose.yml "$ROOT"/docker-compose.prod.yml; do
    check_literal "$f" "Compose service"
done

# Helm: values.yaml carries the pin as `database.imagePin:` — the values file
# cannot RUN a non-Bitnami image under the bundled subchart, so the pin is the
# declared reference every K8s PostgreSQL provisioning must consume.
VALUES_PIN="$(awk -F': ' '/^[[:space:]]*imagePin:/{gsub(/[",]/, "", $2); print $2; exit}' "$ROOT/k8s/helm/sensei/values.yaml" 2>/dev/null || true)"
if [ "$VALUES_PIN" != "$PG_IMAGE" ]; then
    echo "db-contract VIOLATION (Helm values): k8s/helm/sensei/values.yaml database.imagePin is '$VALUES_PIN', expected '$PG_IMAGE'" >&2
    violations=1
fi

if [ "$violations" -eq 1 ]; then
    echo "db-contract FAIL: every PostgreSQL consumer must pin the capability image from .github/.db-capability" >&2
    exit 1
fi

echo "db-contract OK: all environments consume the pinned capability image"
echo "  PG_MAJOR=$PG_MAJOR"
echo "  PG_IMAGE=$PG_IMAGE"
echo "  extensions: $PG_EXTENSIONS"
