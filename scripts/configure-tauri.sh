#!/usr/bin/env bash
# =============================================================================
# configure-tauri.sh
#
# Environment-specific Tauri CSP origin scoping. The default CSP permits only
# the local development API; production builds set SENSEI_TAURI_API_ORIGINS
# (space-separated https/wss origins) so the webview can reach the real API —
# without reopening https:/wss: globally.
#
# Usage:  SENSEI_TAURI_API_ORIGINS="https://api.example.com wss://api.example.com" \
#             scripts/configure-tauri.sh
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONF="$ROOT/sensei-rs/src-tauri/tauri.conf.json"

if [ -n "${SENSEI_TAURI_API_ORIGINS:-}" ]; then
  python3 - "$CONF" "$SENSEI_TAURI_API_ORIGINS" <<'PY'
import json, sys
conf_path, origins = sys.argv[1], sys.argv[2].split()
conf = json.load(open(conf_path))
connect = " ".join(f"'{o}'" for o in origins)
conf["app"]["security"]["csp"] = (
    f"default-src 'self'; connect-src 'self' {connect}; "
    "img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; font-src 'self' data:"
)
json.dump(conf, open(conf_path, "w"), indent=2)
PY
  echo "Tauri CSP configured for: $SENSEI_TAURI_API_ORIGINS"
else
  echo "SENSEI_TAURI_API_ORIGINS unset — using the dev localhost CSP (see tauri.conf.json)"
fi
