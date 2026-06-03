# Starz Morocco Manufacturing Management System (Sensei OS)

Enterprise manufacturing management platform grounded in Lean/TPS principles. Sensei OS unifies sales, RFQ, quoting, production, quality, and continuous improvement with advanced analytics and AI assistance.

## Key Capabilities

- **Sales Pipeline**: Opportunities, RFQs, quotes, and approvals
- **Production**: Work orders, digital shift handover, standard work, training matrix, Andon alerts
- **Quality**: NCR/CAPA workflow, inspections, audits, traceability
- **Project Management**: Obeya room, A3 problem solving, milestones, backlog
- **Today Screen**: Operations command center (priorities, risks, commitments, real-time pulse)
- **AI/ML**: Multilingual on-device training, document intelligence, edge inference, coaching
- **PWA**: Offline-ready experience for shop-floor teams

**Key Technologies**:
- Rust (Axum) for high-performance backend API and workers
- Leptos (WASM) for the web frontend with Tauri for desktop/mobile
- Zig for cross-compilation and native build tooling
- ONNX Runtime (INT8 quantization) for CPU inference
- NATS JetStream for async event-driven processing

## Architecture

- **Backend**: Rust (Axum) with SQLx, NATS JetStream workers
- **Frontend**: Leptos (WebAssembly) + Tauri (desktop/mobile)
- **Database**: PostgreSQL 16 with pgvector
- **Event Bus**: NATS JetStream
- **Storage**: S3-compatible (MinIO)
- **Build Tooling**: Zig cross-compilation, Cargo workspace

## Quick Start (Local)

### Prerequisites

- Rust 1.80+ (via rustup)
- Zig 0.13+ (for cross-compilation)
- PostgreSQL 16+ with pgvector
- NATS server (or use Docker Compose)

### Using Docker Compose (Recommended)

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Start the full stack
docker-compose up -d
```

### Manual Setup

```bash
# Build the Rust workspace
cd sensei-rs
cargo build

# Run the API server
cargo run -p sensei-api

# Run the NATS workers
cargo run -p sensei-workers
```

Health endpoint: http://localhost:8080/api/v1/health

### Frontend Development

```bash
cd sensei-rs

# Build WASM frontend
./scripts/build-frontend-wasm.sh

# Or run Tauri desktop app
cargo tauri dev
```

## Project Structure

```
sensei-rs/
├── crates/
│   ├── sensei-api/        # Axum HTTP API server
│   ├── sensei-frontend/   # Leptos WASM frontend
│   ├── sensei-services/   # Shared business logic
│   ├── sensei-workers/    # NATS JetStream workers
│   └── sensei-zt/         # Zig build tooling
├── src-tauri/             # Tauri desktop/mobile shell
├── zig/                   # Zig build configuration
└── xtask/                 # Cargo automation tasks
```

## Docker Compose (Development)

```bash
docker-compose up -d
```

Services started:
- **sensei-api** — Rust Axum API on port 8080
- **sensei-workers** — Rust NATS background workers
- **db** — PostgreSQL 16 with pgvector
- **nats** — NATS JetStream message broker
- **minio** — S3-compatible file storage
- **caddy** — Reverse proxy (ports 80/443)

## Documentation

- [Documentation Index](docs/README.md)
- [Architecture](docs/architecture/README.md)
- [API Reference](docs/api/README.md)
- [Deployment](docs/deployment/DEPLOYMENT.md)
- [Testing](docs/testing/e2e-testing.md)
- [Chatbot Integration](docs/CHATBOT_INTEGRATION.md)

## Testing

```bash
# Run all Rust tests
cd sensei-rs
cargo test --workspace

# Run with specific crate
cargo test -p sensei-api
cargo test -p sensei-services
```

## License

Proprietary - Starz Morocco. All rights reserved.
