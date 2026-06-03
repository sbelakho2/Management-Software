#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# build-frontend-wasm.sh
#
# Build the Leptos WASM frontend (sensei-frontend crate) for the web.
# Automatically installs wasm-pack if missing.
#
# Usage:
#   ./scripts/build-frontend-wasm.sh [dev|release]
#
# Examples:
#   ./scripts/build-frontend-wasm.sh         # defaults to dev
#   ./scripts/build-frontend-wasm.sh dev     # development build
#   ./scripts/build-frontend-wasm.sh release # optimized release build
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CRATE_DIR="$REPO_ROOT/sensei-rs/crates/sensei-frontend"

BUILD_MODE="${1:-dev}"
OUT_DIR="$CRATE_DIR/pkg"
SERVED_DIR="$REPO_ROOT/frontend/public/wasm"

# ── Color helpers ───────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Check / install wasm-pack ───────────────────────────────────────
if ! command -v wasm-pack &>/dev/null; then
    warn "wasm-pack not found — installing via cargo..."
    cargo install wasm-pack
    echo ""
fi

# Verify wasm-pack is now available
if ! command -v wasm-pack &>/dev/null; then
    error "wasm-pack installation failed. Please install manually:"
    error "  cargo install wasm-pack"
    exit 1
fi

info "Using wasm-pack: $(wasm-pack --version)"

# ── Ensure wasm32 target is installed ───────────────────────────────
if ! rustup target list --installed 2>/dev/null | grep -q "wasm32-unknown-unknown"; then
    info "Adding wasm32-unknown-unknown target..."
    rustup target add wasm32-unknown-unknown
fi

# ── Build ───────────────────────────────────────────────────────────
cd "$CRATE_DIR"

case "$BUILD_MODE" in
    dev|development)
        info "Building WASM frontend (development)..."
        wasm-pack build \
            --target web \
            --dev \
            --out-dir "$OUT_DIR" \
            -- --features "console_error_panic_hook"
        ;;
    release)
        info "Building WASM frontend (release — optimized)..."
        wasm-pack build \
            --target web \
            --release \
            --out-dir "$OUT_DIR" \
            -- --features "console_error_panic_hook"
        ;;
    *)
        error "Unknown build mode: '$BUILD_MODE'. Use 'dev' or 'release'."
        exit 1
        ;;
esac

# ── Copy output to served directory ─────────────────────────────────
if [ -d "$SERVED_DIR" ]; then
    info "Copying WASM output to $SERVED_DIR ..."
    mkdir -p "$SERVED_DIR"
    cp -r "$OUT_DIR"/* "$SERVED_DIR/"
    info "WASM bundle copied to $SERVED_DIR"
else
    warn "Served directory not found at $SERVED_DIR — skipping copy."
    info "WASM bundle remains at $OUT_DIR"
fi

echo ""
info "✅ WASM frontend build complete! (mode: $BUILD_MODE)"
info "   Output: $OUT_DIR"
