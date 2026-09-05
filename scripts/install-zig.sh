#!/usr/bin/env bash
# =============================================================================
# install-zig.sh — canonical Zig toolchain installer (thirtieth-audit item 27)
#
# The obsolete Zig archive naming (zig-linux-x86_64-${VERSION}.tar.xz) stopped
# existing at 0.15.x. The canonical 0.15.2+ archive is
# zig-x86_64-linux-${ZIG_VERSION}.tar.xz and the extracted directory follows
# the SAME naming (zig-x86_64-linux-${ZIG_VERSION}).
#
# Single source of the Zig version AND its pinned archive checksum:
#   .github/.tool-versions  (zig <version> / zig_archive_sha256 <hex>)
#
# Consumers (one implementation, never re-implemented inline):
#   - .github/workflows/sensei-rs-ci.yml (every job that builds sensei-zt)
#   - .github/workflows/cd.yml            (every job that builds sensei-zt)
#   - local developer machines (adds zig to PATH, verifies the checksum)
#   - sensei-rs/Dockerfile mirrors the SAME version + pinned checksum inline
#     because its build context is sensei-rs/ and cannot COPY this file.
#
# Usage:
#   bash scripts/install-zig.sh
#     - GitHub Actions: appends the zig bin dir to $GITHUB_PATH and prints
#       `zig version`.
#     - Local shells: exports PATH for the current process only (run via
#       `source scripts/install-zig.sh` to persist into the shell).
#     - Cache: extracted toolchain lands in .cache/toolchains/zig-*/ (repo
#       .cache/ is gitignored); re-runs skip the download when present.
# =============================================================================
set -euo pipefail

# This installer provisions the Linux x86_64 Zig toolchain that CI
# (ubuntu-latest) and the Docker builder consume. On other platforms
# (e.g. an Apple Silicon dev machine) the archive itself cannot run — skip
# cleanly instead of failing after a pointless download.
if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
    echo "install-zig: host is $(uname -s)/$(uname -m) — the pinned archive is x86_64-linux only; skipping (CI/Docker install this toolchain)" >&2
    exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${ZIG_VERSIONS_FILE:-$ROOT/.github/.tool-versions}"
CACHE_BASE="${ZIG_CACHE_DIR:-$ROOT/.cache/toolchains}"

[ -f "$VERSIONS_FILE" ] || { echo "install-zig: toolchain manifest not found: $VERSIONS_FILE" >&2; exit 1; }

ZIG_VERSION="$(awk '$1=="zig"{print $2}' "$VERSIONS_FILE")"
ZIG_SHA256="$(awk '$1=="zig_archive_sha256"{print $2}' "$VERSIONS_FILE")"

if [ -z "$ZIG_VERSION" ]; then
    echo "install-zig: no 'zig' entry in $VERSIONS_FILE" >&2
    exit 1
fi

ARCHIVE="zig-x86_64-linux-${ZIG_VERSION}.tar.xz"
URL="https://ziglang.org/download/${ZIG_VERSION}/${ARCHIVE}"
ZIG_DIR="$CACHE_BASE/${ARCHIVE%.tar.xz}"
ZIG_BIN="$ZIG_DIR/zig"

if [ ! -x "$ZIG_BIN" ]; then
    echo "install-zig: downloading ${URL}"
    mkdir -p "$CACHE_BASE"
    TMP_ARCHIVE="$(mktemp "$CACHE_BASE/zig-XXXXXX.tar.xz")"
    TMP_EXTRACT="$(mktemp -d "$CACHE_BASE/zig-extract-XXXXXX")"
    trap 'rm -f "$TMP_ARCHIVE"; rm -rf "$TMP_EXTRACT"' EXIT

    curl -fL --retry 3 -o "$TMP_ARCHIVE" "$URL"

    # Verify the pinned checksum when the manifest pins one (it does).
    if [ -n "$ZIG_SHA256" ]; then
        if command -v sha256sum >/dev/null 2>&1; then
            CHECK="$(sha256sum "$TMP_ARCHIVE" | awk '{print $1}')"
        elif command -v shasum >/dev/null 2>&1; then
            CHECK="$(shasum -a 256 "$TMP_ARCHIVE" | awk '{print $1}')"
        else
            echo "install-zig: no sha256sum/shasum available — cannot verify the pinned checksum" >&2
            exit 1
        fi
        if [ "$CHECK" != "$ZIG_SHA256" ]; then
            echo "install-zig: checksum mismatch for ${ARCHIVE}" >&2
            echo "  expected: $ZIG_SHA256" >&2
            echo "  actual:   $CHECK" >&2
            exit 1
        fi
        echo "install-zig: checksum OK (${ZIG_SHA256})"
    else
        echo "install-zig: WARNING — no zig_archive_sha256 pin in $VERSIONS_FILE; skipping checksum verification" >&2
    fi

    tar -xf "$TMP_ARCHIVE" -C "$TMP_EXTRACT"
    mkdir -p "$(dirname "$ZIG_DIR")"
    rm -rf "$ZIG_DIR"
    mv "$TMP_EXTRACT/zig-x86_64-linux-${ZIG_VERSION}" "$ZIG_DIR"
    rm -f "$TMP_ARCHIVE"
    rm -rf "$TMP_EXTRACT"
    trap - EXIT
fi

if [ -n "${GITHUB_PATH:-}" ]; then
    # GitHub Actions: later steps inherit the PATH automatically.
    echo "$ZIG_DIR" >> "$GITHUB_PATH"
    echo "install-zig: added $ZIG_DIR to GITHUB_PATH"
else
    # Local shells: export for the current process.
    export PATH="$ZIG_DIR:$PATH"
    echo "install-zig: added $ZIG_DIR to PATH (source this script to persist)"
fi

"$ZIG_BIN" version
