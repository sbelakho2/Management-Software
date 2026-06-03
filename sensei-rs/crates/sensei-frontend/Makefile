# WASM build pipeline for sensei-frontend (Leptos)
#
# Prerequisites:
#   wasm-pack  (install via: cargo install wasm-pack)
#   rustup target add wasm32-unknown-unknown
#
# Usage:
#   make build-wasm          # development build
#   make build-wasm-release  # release build (optimized)
#   make clean               # remove build artifacts
#   make serve               # start a local dev server with wasm-pack
#   make check               # cargo check (no wasm target needed)

.PHONY: build-wasm build-wasm-release clean serve check

WASM_TARGET  := wasm32-unknown-unknown
OUT_DIR      := pkg
INDEX_HTML   := index.html
STYLES_DIR   := styles

# ── Development build ──────────────────────────────────────────────
build-wasm:
	wasm-pack build \
		--target web \
		--dev \
		--out-dir $(OUT_DIR) \
		-- --features "console_error_panic_hook"

# ── Release build (optimized) ──────────────────────────────────────
build-wasm-release:
	wasm-pack build \
		--target web \
		--release \
		--out-dir $(OUT_DIR) \
		-- --features "console_error_panic_hook"

# ── Clean artifacts ─────────────────────────────────────────────────
clean:
	rm -rf $(OUT_DIR) target
	cargo clean 2>/dev/null || true

# ── Quick cargo check (host target, faster) ─────────────────────────
check:
	cargo check -p sensei-frontend

# ── Local dev server (requires basic-http-server or similar) ────────
serve: build-wasm
	@echo "Starting dev server at http://localhost:8080"
	@echo "Open http://localhost:8080/ in your browser"
	python3 -m http.server 8080 --directory $(OUT_DIR) 2>/dev/null || \
	basic-http-server --addr 0.0.0.0:8080 $(OUT_DIR) 2>/dev/null || \
	echo "Install python3 or basic-http-server to serve the WASM build"
