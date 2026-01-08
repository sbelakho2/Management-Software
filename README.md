# Starz Morocco Manufacturing Management System

[![Build Status](https://github.com/sbelakho2/Management-Software/workflows/CI/badge.svg)](https://github.com/sbelakho2/Management-Software/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

Enterprise manufacturing management system built on Lean/TPS principles. Track opportunities, RFQs, quotes, production, quality, and continuous improvement—all in one platform.

## ✨ Features

### Core Functionality
- **Sales Pipeline**: Opportunity management with kanban visualization
- **RFQ Management**: Request for Quote processing and tracking
- **Quote Management**: Multi-version quotes with approvals and PDF generation
- **Product Catalog**: Product and BOM management
- **Work Orders**: Production planning and tracking
- **Quality Management**: Inspections, NCRs, and CAPA workflow
- **Obeya Room**: Visual project management
- **A3 Thinking**: Structured problem-solving
- **Training Matrix**: Skills tracking and certification

### Advanced Features
- **Smart Ingestion**: OCR + AI for document processing (GPT-4o-mini)
- **Knowledge Base**: Semantic search with ML embeddings (sentence-transformers)
- **Today Screen**: Daily operational dashboard (Leader Standard Work)
- **Andon System**: Real-time alerts and escalation
- **Kanban Boards**: Visual workflow management
- **Audit Trail**: Complete activity history

### Technical Highlights
- **Modern Stack**: FastAPI + Next.js + PostgreSQL + Redis
- **Cloud Native**: Kubernetes with Helm charts
- **AI/ML Integration**: OpenAI GPT-4o, sentence-transformers, PyTorch
- **Vector Search**: pgvector for semantic search
- **Type Safety**: Full TypeScript frontend, Pydantic backend
- **Testing**: 359 tests (Unit, Integration, E2E)
- **PWA Support**: Offline-capable progressive web app

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (with pgvector)
- Redis 7+

### Local Development

```bash
# Clone repository
git clone https://github.com/sbelakho2/Management-Software.git
cd Management-Software

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn sensei.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

See [Development Guide](./docs/development/getting-started.md) for detailed setup.

### Docker Compose (Development)

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Create admin user
docker-compose exec backend python -m sensei.cli.user create-admin \
  --email admin@local.dev \
  --password admin123
```

### Kubernetes (Production)

```bash
# Install with Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency build k8s/helm/sensei
helm install sensei ./k8s/helm/sensei \
  --namespace sensei \
  --create-namespace \
  --values my-values.yaml
```

See [Deployment Guide](./docs/deployment/DEPLOYMENT.md) for production setup.

## 📚 Documentation

- **[Complete Documentation](./docs/README.md)** - Documentation index
- **[Getting Started](./docs/development/getting-started.md)** - Development guide
- **[Architecture](./docs/architecture/README.md)** - System design
- **[API Reference](./docs/API/README.md)** - API documentation
- **[Deployment](./docs/deployment/DEPLOYMENT.md)** - Production deployment
- **[Hetzner Cloud](./docs/deployment/HETZNER-DEPLOYMENT.md)** - Deploy on Hetzner
- **[Testing](./docs/testing/e2e-testing.md)** - Test documentation

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend  │─────►│    Backend   │─────►│  PostgreSQL  │
│  (Next.js)  │      │   (FastAPI)  │      │  (pgvector)  │
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                    ┌───────┴────────┬─────────┐
                    ▼                ▼         ▼
               ┌────────┐      ┌────────┐  ┌────────┐
               │ Redis  │      │ MinIO  │  │Worker  │
               │ Cache  │      │   S3   │  │ Tasks  │
               └────────┘      └────────┘  └────────┘
```

- **Backend**: FastAPI (async Python) with SQLAlchemy ORM
- **Frontend**: Next.js 14 (React/TypeScript) with Server Components
- **Database**: PostgreSQL 15 with pgvector extension
- **Cache**: Redis 7 for caching and job queue
- **Storage**: MinIO (S3-compatible) for attachments
- **Orchestration**: Kubernetes with Helm charts

See [Architecture Documentation](./docs/architecture/README.md) for details.

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=sensei

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

**Test Coverage**:
- Unit tests: 307 passing
- Integration tests: 52 passing
- E2E tests: 22 passing
- **Total**: 359 tests

## 🛠️ Tech Stack

### Backend
- FastAPI 0.104+ (async web framework)
- SQLAlchemy 2.0 (async ORM)
- PostgreSQL 15 + pgvector (database with vector search)
- Redis 7 (cache and job queue)
- Pydantic v2 (validation)
- Alembic (migrations)
- OpenAI GPT-4o-mini (AI parsing)
- sentence-transformers (ML embeddings)
- PyTorch 2.9 (deep learning)

### Frontend
- Next.js 14 (React framework)
- TypeScript 5 (type safety)
- Tailwind CSS 3 (styling)
- shadcn/ui (components)
- Zustand (state management)
- React Query (data fetching)
- Playwright (E2E testing)

### Infrastructure
- Kubernetes 1.19+ (orchestration)
- Helm 3 (package manager)
- Docker (containerization)
- NGINX Ingress (routing)
- cert-manager (TLS certificates)

See [Technology Stack](./docs/architecture/1.1-technology-stack.md) for complete list.

## 🚢 Deployment

### Cloud Providers

- **Hetzner Cloud** ✅ (Recommended - optimized configuration included)
- **AWS/GCP/Azure** ✅ (Standard Kubernetes)
- **On-Premises** ✅ (Self-hosted Kubernetes)

### Deployment Options

1. **Production (Kubernetes + Helm)**
   - Auto-scaling: 2-10 backend replicas
   - High availability: Multi-replica deployments
   - Cost: ~$58/month on Hetzner Cloud

2. **Staging (Kubernetes)**
   - Reduced resources
   - Single replicas
   - Cost: ~$30/month on Hetzner Cloud

3. **Development (Docker Compose)**
   - Local laptop/workstation
   - All services in containers
   - Cost: Free

See deployment guides:
- [Production Deployment](./docs/deployment/DEPLOYMENT.md)
- [Hetzner Cloud](./docs/deployment/HETZNER-DEPLOYMENT.md)
- [Quick Start (Minikube)](./docs/deployment/QUICKSTART.md)

## 📈 Roadmap

### ✅ Completed (Phase 1)

- [x] Core data models (Accounts, RFQs, Quotes, Products, etc.)
- [x] RESTful API with FastAPI
- [x] React frontend with Next.js
- [x] Authentication & RBAC
- [x] Smart document ingestion (OCR + AI)
- [x] Knowledge base with semantic search
- [x] E2E test suite (Playwright)
- [x] Kubernetes deployment with Helm
- [x] Premium UI components

### 🔨 In Progress (Phase 2)

- [ ] Production phase 2 features
  - [ ] NPI (New Product Introduction) workflow
  - [ ] Production cell management
  - [ ] Advanced quality control
- [ ] Mobile PWA enhancements
- [ ] Supplier portal
- [ ] Advanced reporting

### 🔮 Future (Phase 3)

- [ ] Production phase 3 features
  - [ ] Real-time production tracking
  - [ ] MES integration
  - [ ] IoT sensor integration
- [ ] Advanced AI features
  - [ ] Automated A3 analysis
  - [ ] Predictive quality alerts
  - [ ] Smart scheduling
- [ ] Multi-tenant support
- [ ] Advanced analytics & BI

See [Development Plan](./Development_Plan.md) for complete roadmap.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./docs/development/getting-started.md#contributing).

### Development Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run test suite (`pytest`, `npm test`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Quality

- **Backend**: Black (formatting), Ruff (linting), MyPy (type checking)
- **Frontend**: ESLint (linting), Prettier (formatting), TypeScript (type checking)
- **Tests**: pytest, Jest, Playwright
- **Coverage**: Aim for >80% coverage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Development Team** - Initial work and maintenance

## 🙏 Acknowledgments

- Toyota Production System (TPS) principles
- Lean Manufacturing methodology
- Open source community
- Bitnami Helm charts
- FastAPI and Next.js teams

## 📧 Contact

- **Project Homepage**: https://flopsen.tech
- **Documentation**: https://docs.flopsen.tech
- **Issue Tracker**: https://github.com/sbelakho2/Management-Software/issues
- **Email**: contact@starzmorocco.com

## 📊 Project Stats

- **Lines of Code**: 12,355+
- **Files**: 60+ source files
- **Tests**: 359 tests
- **Languages**: Python, TypeScript
- **Frameworks**: FastAPI, Next.js, React
- **Database**: PostgreSQL with pgvector
- **Deployment**: Kubernetes with Helm

---

**Built with ❤️ by Starz Morocco using Lean Manufacturing principles**

[⭐ Star this repo](https://github.com/sbelakho2/Management-Software) if you find it useful!
