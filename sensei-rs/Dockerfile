# =============================================================================
# Dockerfile — Sensei OS (API + Workers)
# =============================================================================
# Multistage build:
#   Stage 1 (builder): compile the Rust workspace (pinned 1.96.0 + Zig 0.15.2)
#   Stage 2 (runtime): minimal Debian image with CA certs, curl and a
#                      non-root user; ships the API, the worker binary and
#                      the static frontend under /app/static.
#
# Build:  docker build -t sensei-api .
# Run:    docker run -p 8080:8080 sensei-api
# =============================================================================

# ─── Stage 1: Build Rust binary ─────────────────────────────────────────────
FROM rust:1.96.0-slim-bookworm AS builder

# Install system dependencies required for compiling native Rust crates:
#   pkg-config  — macro expansion for build scripts
#   libssl-dev  — OpenSSL development headers (reqwest, lettre HTTPS/TLS)
#   curl        — Zig toolchain download
#   xz-utils    — Zig archive extraction
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install the pinned Zig toolchain (required by sensei-zt's build script).
ENV ZIG_VERSION=0.15.2
RUN curl -fsSL -o /tmp/zig.tar.xz \
      "https://ziglang.org/download/${ZIG_VERSION}/zig-linux-x86_64-${ZIG_VERSION}.tar.xz" \
    && tar -xJf /tmp/zig.tar.xz -C /opt \
    && mv "/opt/zig-linux-x86_64-${ZIG_VERSION}" /opt/zig \
    && ln -s /opt/zig/zig /usr/local/bin/zig \
    && rm /tmp/zig.tar.xz \
    && zig version

WORKDIR /app

# ── Cache dependency downloads (BuildKit) ──────────────────────────────────
# The cache mount survives between builds; its failure is NOT hidden —
# every cargo invocation below reports its real exit status.
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    mkdir -p crates

COPY Cargo.toml Cargo.lock ./
COPY rust-toolchain.toml ./
COPY crates/sensei-core/Cargo.toml crates/sensei-core/
COPY crates/sensei-db/Cargo.toml crates/sensei-db/
COPY crates/sensei-event-bus/Cargo.toml crates/sensei-event-bus/
COPY crates/sensei-auth/Cargo.toml crates/sensei-auth/
COPY crates/sensei-api/Cargo.toml crates/sensei-api/
COPY crates/sensei-services/Cargo.toml crates/sensei-services/
COPY crates/sensei-frontend/Cargo.toml crates/sensei-frontend/
COPY crates/sensei-zt/Cargo.toml crates/sensei-zt/
COPY crates/sensei-workers/Cargo.toml crates/sensei-workers/
COPY xtask/Cargo.toml xtask/

# Build dependencies only (this layer is cached).
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo fetch --locked

# ── Build the real binaries ────────────────────────────────────────────────
COPY zig/ zig/
COPY crates/ crates/

# Compile the API and worker release binaries (locked to the committed lock).
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo build --release --locked -p sensei-api -p sensei-workers

# ── Stage 2: Minimal runtime ──────────────────────────────────────────────
FROM debian:bookworm-slim

# CA certificates for TLS (reqwest, lettre) + curl for the healthcheck.
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the release binaries from the builder stage.
COPY --from=builder /app/target/release/sensei-api /usr/local/bin/sensei-api
COPY --from=builder /app/target/release/sensei-workers /usr/local/bin/sensei-workers

# Static frontend served by the API at /app/static (STATIC_DIR env).
COPY --from=builder /app/crates/sensei-frontend/dist /app/static

# Create a non-root user for security.
RUN groupadd -r sensei && useradd -r -g sensei -d /home/sensei -s /sbin/nologin sensei && \
    mkdir -p /home/sensei /app/static && chown -R sensei:sensei /home/sensei /app/static

USER sensei

ENV STATIC_DIR=/app/static

# The API server listens on port 8080 by default (configurable via API_PORT env)
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8080/health/live > /dev/null || exit 1

ENTRYPOINT ["sensei-api"]
