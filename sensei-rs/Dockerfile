# =============================================================================
# Dockerfile — Sensei Rust API (Axum)
# =============================================================================
# Multistage build:
#   Stage 1 (builder): Compile the Rust binary with full optimizations
#   Stage 2 (runtime): Minimal Debian image with only ca-certificates
#
# Build:  docker build -t sensei-api .
# Run:    docker run -p 8080:8080 sensei-api
# =============================================================================

# ─── Stage 1: Build Rust binary ─────────────────────────────────────────────
FROM rust:1.85-slim-bookworm AS builder

# Install system dependencies required for compiling native Rust crates:
#   pkg-config  — macro expansion for build scripts
#   libssl-dev  — OpenSSL development headers (reqwest, lettre HTTPS/TLS)
#   musl-tools  — musl target support (optional, kept for compatibility)
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    musl-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Cache dependency downloads ──────────────────────────────────────────────
# Copy only Cargo.toml files first so that `cargo build` can fetch and compile
# dependencies without needing the full source tree. This layer is cached and
# only invalidated when a Cargo.toml changes.
COPY Cargo.toml Cargo.lock ./
COPY crates/sensei-core/Cargo.toml crates/sensei-core/
COPY crates/sensei-db/Cargo.toml crates/sensei-db/
COPY crates/sensei-event-bus/Cargo.toml crates/sensei-event-bus/
COPY crates/sensei-auth/Cargo.toml crates/sensei-auth/
COPY crates/sensei-api/Cargo.toml crates/sensei-api/
COPY crates/sensei-services/Cargo.toml crates/sensei-services/
COPY crates/sensei-frontend/Cargo.toml crates/sensei-frontend/
COPY crates/sensei-zt/Cargo.toml crates/sensei-zt/
COPY xtask/Cargo.toml xtask/

# Create dummy main.rs so that dependency-only compilation succeeds
RUN mkdir -p crates/sensei-api/src && \
    echo "fn main() {}" > crates/sensei-api/src/main.rs && \
    mkdir -p crates/sensei-core/src && \
    echo "fn main() {}" > crates/sensei-core/src/main.rs && \
    mkdir -p crates/sensei-db/src && \
    echo "fn main() {}" > crates/sensei-db/src/main.rs && \
    mkdir -p crates/sensei-event-bus/src && \
    echo "fn main() {}" > crates/sensei-event-bus/src/main.rs && \
    mkdir -p crates/sensei-auth/src && \
    echo "fn main() {}" > crates/sensei-auth/src/main.rs && \
    mkdir -p crates/sensei-services/src && \
    echo "fn main() {}" > crates/sensei-services/src/main.rs && \
    mkdir -p crates/sensei-zt/src && \
    echo "fn main() {}" > crates/sensei-zt/src/main.rs

# Build dependencies only (this layer is cached)
RUN cargo build --release -p sensei-api -p sensei-workers 2>/dev/null || true

# ── Build the real binary ──────────────────────────────────────────────────
# Copy Zig build files (needed for sensei-zt build script)
COPY zig/ zig/

# Copy all remaining source files
COPY crates/ crates/

# Force recompile of the actual main.rs (dummy was cached above)
RUN touch crates/sensei-api/src/main.rs crates/sensei-workers/src/main.rs

# Build the release binaries
RUN cargo build --release -p sensei-api -p sensei-workers

# ─── Stage 2: Minimal runtime ──────────────────────────────────────────────
FROM debian:bookworm-slim

# Install ca-certificates for TLS support (required by reqwest, lettre, etc.)
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the statically-linked binaries from the builder stage
COPY --from=builder /app/target/release/sensei-api /usr/local/bin/sensei-api
COPY --from=builder /app/target/release/sensei-workers /usr/local/bin/sensei-workers

# Create a non-root user for security
RUN groupadd -r sensei && useradd -r -g sensei -d /home/sensei -s /sbin/nologin sensei && \
    mkdir -p /home/sensei && chown -R sensei:sensei /home/sensei

USER sensei

# The API server listens on port 8080 by default (configurable via API_PORT env)
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --spider --quiet http://localhost:8080/api/v1/health || exit 1

ENTRYPOINT ["sensei-api"]
