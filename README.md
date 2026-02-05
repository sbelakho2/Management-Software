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
- Multilingual embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (50+ languages)
- ONNX Runtime (INT8 quantization) for CPU inference
- Optional translation: `Helsinki-NLP/opus-mt-*` models

## Architecture

- **Backend**: FastAPI + SQLAlchemy (async), Celery, Redis
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind
- **Database**: PostgreSQL 16 with pgvector
- **Storage**: S3-compatible (MinIO)

## Quick Start (Local)

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ with pgvector
- Redis 7+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# Option A: run directly
python -m uvicorn sensei.main:app --reload --host 0.0.0.0 --port 8001

# Option B: auto-restart loop (recommended for long-lived dev sessions)
cd ..
./scripts/dev_backend.sh

# If you need to free the port first
./scripts/restart_backend.sh
```

Health endpoints:
- http://localhost:8001/health
- http://localhost:8001/api/v1/health/ready
- http://localhost:8001/api/v1/health/live

### Frontend

```bash
cd frontend
npm install

# Option A: run directly
npm run dev

# Option B: auto-restart loop (recommended for long-lived dev sessions)
cd ..
./scripts/dev_frontend.sh

# If you need to free the port first
./scripts/restart_frontend.sh
```

Visit http://localhost:3000

## Docker Compose (Development)

```bash
docker-compose up -d

docker-compose exec api alembic upgrade head
```

## Documentation

- [Documentation Index](docs/README.md)
- [Architecture](docs/architecture/README.md)
- [API Reference](docs/api/README.md)
- [Development Guide](docs/development/getting-started.md)
- [Deployment](docs/deployment/DEPLOYMENT.md)
- [Testing](docs/testing/e2e-testing.md)
- [AI/ML Services Analysis](docs/AI_ML_ONNX_SERVICES_ANALYSIS.md)
- [Chatbot Integration](docs/CHATBOT_INTEGRATION.md)

## Testing

```bash
# Backend
cd backend
pytest tests/ -v

# Frontend
cd frontend
npm test

# E2E
npm run test:e2e
```

## License

Proprietary - Starz Morocco. All rights reserved.
