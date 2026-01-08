# Project Architecture

## Overview

Starz Morocco is a modern manufacturing management system built with a microservices-inspired architecture, featuring:

- **Backend**: FastAPI (Python) - RESTful API server
- **Frontend**: Next.js (React/TypeScript) - Server-side rendered web application
- **Database**: PostgreSQL 15 with pgvector - Relational database with vector search
- **Cache**: Redis 7 - In-memory cache and job queue
- **Storage**: MinIO/S3 - Object storage for attachments
- **Orchestration**: Kubernetes with Helm - Container orchestration

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                            │
│                    (Hetzner / NGINX Ingress)                     │
└────────────────┬────────────────────────┬───────────────────────┘
                 │                        │
         ┌───────▼──────┐         ┌──────▼───────┐
         │   Frontend    │         │    Backend   │
         │   (Next.js)   │◄───────►│   (FastAPI)  │
         │   2+ replicas │         │  2-10 replicas│
         └──────┬────────┘         └──────┬───────┘
                │                         │
                │                 ┌───────┴──────┬──────────┬─────────┐
                │                 │              │          │         │
         ┌──────▼──────┐    ┌─────▼─────┐  ┌───▼────┐ ┌──▼─────┐ ┌─▼────┐
         │   Browser   │    │PostgreSQL │  │ Redis  │ │ MinIO  │ │Worker│
         │   Clients   │    │ (pgvector)│  │ Cache  │ │   S3   │ │Tasks │
         └─────────────┘    └───────────┘  └────────┘ └────────┘ └──────┘
```

## Technology Stack

See [technology-stack.md](./1.1-technology-stack.md) for detailed breakdown.

### Backend Stack

- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: JWT (python-jose)
- **File Storage**: boto3 (S3-compatible)
- **Task Queue**: Redis + Celery (future)
- **OCR**: PaddleOCR, Tesseract, EasyOCR
- **AI**: OpenAI GPT-4o-mini
- **ML**: sentence-transformers, PyTorch
- **Testing**: pytest, pytest-asyncio, httpx

### Frontend Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5+
- **UI Library**: React 18
- **Styling**: Tailwind CSS 3
- **Components**: shadcn/ui, Radix UI
- **State**: Zustand, React Query
- **Forms**: React Hook Form, Zod
- **Testing**: Jest, React Testing Library, Playwright
- **PWA**: next-pwa
- **Charts**: Recharts

### Infrastructure Stack

- **Orchestration**: Kubernetes 1.19+
- **Package Manager**: Helm 3
- **Ingress**: NGINX Ingress Controller
- **TLS**: cert-manager + Let's Encrypt
- **Monitoring**: Prometheus + Grafana (optional)
- **Logging**: Loki + Grafana (optional)

## Data Architecture

### Database Schema

See [database-schema.md](./1.2-database-schema.md) for complete schema.

Key entities:
- **Accounts**: Customers and suppliers
- **Opportunities**: Sales pipeline
- **RFQs**: Requests for Quote
- **Quotes**: Quote versions and approvals
- **Products**: Product catalog
- **Work Orders**: Manufacturing orders
- **Quality**: Inspections and NCRs
- **Learning**: Training and skills
- **Knowledge**: Documents and embeddings

### Data Flow

```
User Action → Frontend → API Gateway → Backend Service → Database
                                    ↓
                            Cache (Redis) ← Redis
                                    ↓
                          File Storage (S3) ← MinIO
```

## Security Architecture

### Authentication Flow

```
1. User submits credentials
2. Backend validates against database
3. JWT token generated with claims
4. Token returned to frontend
5. Token stored in httpOnly cookie
6. Token sent with each API request
7. Backend validates token signature
8. User identity extracted from claims
```

### Authorization

- **RBAC**: Role-Based Access Control
- **Roles**: Admin, Manager, User, Viewer
- **Permissions**: Create, Read, Update, Delete, Approve
- **Scope**: Global, Account-level, Resource-level

### Security Measures

- **Encryption in Transit**: TLS 1.3
- **Encryption at Rest**: Database encryption, encrypted volumes
- **Secret Management**: Kubernetes Secrets, sealed secrets
- **Network Policies**: Pod-to-pod traffic control
- **Input Validation**: Pydantic schemas, SQL injection prevention
- **XSS Protection**: React escaping, CSP headers
- **CSRF Protection**: SameSite cookies, CSRF tokens
- **Rate Limiting**: Per-user, per-IP limits

## API Architecture

### RESTful Design

```
GET    /api/v1/products       # List products
POST   /api/v1/products       # Create product
GET    /api/v1/products/:id   # Get product
PUT    /api/v1/products/:id   # Update product
DELETE /api/v1/products/:id   # Delete product
```

### Request/Response Cycle

```
┌─────────┐     ┌──────────┐     ┌────────┐     ┌──────────┐
│ Client  │────►│ Ingress  │────►│Backend │────►│ Database │
│         │     │  NGINX   │     │FastAPI │     │PostgreSQL│
└─────────┘     └──────────┘     └────────┘     └──────────┘
     │                                 │               │
     │         ┌──────────┐           │               │
     │◄────────│ Response │◄──────────┴───────────────┘
                └──────────┘
```

### Middleware Stack

1. **Correlation ID**: Request tracking
2. **Timing**: Request duration
3. **Logging**: Request/response logging
4. **Authentication**: JWT validation
5. **CORS**: Cross-origin headers
6. **Security Headers**: HSTS, CSP, etc.
7. **Rate Limiting**: Request throttling
8. **Error Handling**: Exception catching

## Frontend Architecture

### Component Hierarchy

```
App Layout
├── Navigation (Sidebar, Header)
├── Pages (Route-based)
│   ├── Dashboard
│   │   ├── Today Screen
│   │   ├── Metrics Cards
│   │   └── Task List
│   ├── Pipeline
│   │   ├── Kanban Board
│   │   └── Opportunity Cards
│   └── Settings
│       ├── Profile
│       ├── Team
│       └── Security
└── Global Components
    ├── Command Palette
    ├── Notifications
    └── Toast Messages
```

### State Management

- **Server State**: React Query (caching, invalidation)
- **UI State**: Zustand (modals, sidebar, theme)
- **Form State**: React Hook Form (validation, submission)
- **URL State**: Next.js router (query params, pathname)

### Data Fetching

```typescript
// Server-side (RSC)
async function ProductsPage() {
  const products = await api.products.list();
  return <ProductList products={products} />;
}

// Client-side (React Query)
function ProductList() {
  const { data, isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => api.products.list(),
  });
  
  if (isLoading) return <Skeleton />;
  return <Table data={data} />;
}
```

## Deployment Architecture

### Kubernetes Structure

```
Namespace: sensei
├── Deployments
│   ├── backend (2-10 replicas, auto-scaled)
│   ├── frontend (2-5 replicas, auto-scaled)
│   └── worker (1 replica, background tasks)
├── StatefulSets
│   ├── postgresql (1 replica, 20Gi volume)
│   └── redis (1 replica, 8Gi volume)
├── Services
│   ├── backend (ClusterIP, internal)
│   ├── frontend (ClusterIP, internal)
│   ├── postgresql (ClusterIP, internal)
│   └── redis (ClusterIP, internal)
├── Ingress
│   └── sensei (NGINX, TLS termination)
├── ConfigMaps
│   └── sensei-config (environment variables)
├── Secrets
│   └── sensei-secrets (credentials)
└── PersistentVolumeClaims
    ├── postgres-data (20Gi)
    ├── redis-data (8Gi)
    └── uploads (10Gi)
```

### High Availability

- **Backend**: 2+ replicas with HPA (2-10 based on CPU/memory)
- **Frontend**: 2+ replicas with HPA (2-5 based on CPU)
- **Database**: Single instance with automated backups (HA in future)
- **Redis**: Single instance with persistence (HA in future)
- **Load Balancer**: Hetzner Cloud Load Balancer (HA by default)

### Disaster Recovery

- **Database Backups**: Daily to S3, 30-day retention
- **Volume Snapshots**: Weekly Hetzner snapshots
- **Configuration Backup**: Helm charts in Git
- **RTO**: 4 hours (Recovery Time Objective)
- **RPO**: 24 hours (Recovery Point Objective)

## Scaling Strategy

### Horizontal Scaling

```yaml
# Auto-scaling configuration
autoscaling:
  backend:
    minReplicas: 2
    maxReplicas: 10
    targetCPU: 70%
    targetMemory: 80%
  
  frontend:
    minReplicas: 2
    maxReplicas: 5
    targetCPU: 70%
```

### Vertical Scaling

- **Database**: Scale up to larger PostgreSQL instance
- **Redis**: Increase memory allocation
- **Storage**: Add more volume capacity

### Caching Strategy

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     Cache Hit
│ Redis Cache │────────────────┐
└──────┬──────┘                │
       │ Cache Miss            │
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│  Database   │         │  Response   │
└──────┬──────┘         └─────────────┘
       │
       └──────────────────────►
           Update Cache
```

## Performance Optimization

### Backend Optimizations

- **Database Indexing**: Strategic indexes on frequently queried columns
- **Query Optimization**: Use select_related, avoid N+1 queries
- **Async Operations**: Non-blocking I/O for database and API calls
- **Connection Pooling**: Reuse database connections
- **Caching**: Redis for frequently accessed data
- **Compression**: Gzip response compression

### Frontend Optimizations

- **Code Splitting**: Dynamic imports for routes and components
- **Tree Shaking**: Remove unused code
- **Image Optimization**: Next.js Image component, WebP format
- **Bundle Analysis**: Minimize bundle size
- **SSR/SSG**: Server-side rendering for initial load
- **Lazy Loading**: Load components on demand
- **Memoization**: React.memo, useMemo, useCallback

## Monitoring & Observability

### Metrics

- **System**: CPU, memory, disk, network
- **Application**: Request rate, error rate, response time
- **Business**: Users, orders, revenue, conversions
- **Database**: Query time, connection pool, cache hit rate

### Logging

```
Levels: DEBUG < INFO < WARNING < ERROR < CRITICAL

Format (JSON):
{
  "timestamp": "2024-01-08T10:30:00Z",
  "level": "INFO",
  "service": "backend",
  "correlation_id": "abc123",
  "user_id": 42,
  "message": "Order created",
  "context": {
    "order_id": 1001,
    "amount": 1500.00
  }
}
```

### Tracing

- **Correlation IDs**: Track requests across services
- **Span Tracking**: Measure component execution time
- **Error Tracking**: Sentry integration (optional)

## Future Enhancements

### Phase 2

- [ ] **Microservices**: Split monolith into services (auth, orders, inventory)
- [ ] **Event Sourcing**: Event-driven architecture with Kafka
- [ ] **CQRS**: Separate read/write models
- [ ] **GraphQL**: Alternative to REST API
- [ ] **Websockets**: Real-time updates

### Phase 3

- [ ] **Multi-tenancy**: Separate schemas per customer
- [ ] **Multi-region**: Geographic distribution
- [ ] **Edge Computing**: CloudFlare Workers for static content
- [ ] **ML Pipeline**: Automated model training and deployment
- [ ] **Advanced Analytics**: Data warehouse and BI tools

## References

- [Technology Stack Details](./1.1-technology-stack.md)
- [Database Schema](./1.2-database-schema.md)
- [API Documentation](../api/README.md)
- [Deployment Guide](../deployment/DEPLOYMENT.md)
- [Development Guide](../development/getting-started.md)
