#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Build script for Sensei MOS – Tauri v2 mobile & desktop targets
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TAURI_DIR="$PROJECT_ROOT/src-tauri"

echo "=== Sensei MOS – Tauri v2 Build ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# ── Verify prerequisites ───────────────────────────────────────────────
if ! command -v cargo &>/dev/null; then
    echo "ERROR: cargo is not installed. Install Rust via https://rustup.rs"
    exit 1
fi

if ! command -v trunk &>/dev/null; then
    echo "ERROR: trunk is not installed. Install with: cargo install trunk"
    exit 1
fi

# ── Build the Leptos WASM frontend ─────────────────────────────────────
echo ">>> Building Leptos WASM frontend..."
cd "$PROJECT_ROOT/crates/sensei-frontend"
trunk build --release
echo "    Frontend built successfully."
echo ""

# ── Build for Desktop (macOS universal binary) ────────────────────────
echo ">>> Building for Desktop (macOS universal)..."
cd "$TAURI_DIR"
cargo tauri build --target universal-apple-darwin
echo "    Desktop build complete."
echo ""

# ── Build for iOS ──────────────────────────────────────────────────────
echo ">>> Building for iOS..."
cd "$TAURI_DIR"
cargo tauri build --target universal-apple-darwin --features ios
echo "    iOS build complete."
echo ""

# ── Build for Android ──────────────────────────────────────────────────
echo ">>> Building for Android (aarch64)..."
cd "$TAURI_DIR"
cargo tauri build --target aarch64-linux-android
echo "    Android build complete."
echo ""

echo "=== All builds finished successfully ==="
