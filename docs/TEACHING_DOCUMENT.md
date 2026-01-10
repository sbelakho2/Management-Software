# Sensei OS: Complete System Teaching Document

> **A Comprehensive Guide to the Factory Management Operating System**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Technology Stack](#2-architecture--technology-stack)
3. [Role-Based Access Control (RBAC)](#3-role-based-access-control-rbac)
4. [Core Modules](#4-core-modules)
5. [Enterprise Integrations](#5-enterprise-integrations)
6. [Deployment Maturity Model](#6-deployment-maturity-model)
7. [E2E Testing Strategy](#7-e2e-testing-strategy)
8. [Service Catalog](#8-service-catalog)
9. [Operations & DevOps](#9-operations--devops)
10. [Security Model](#10-security-model)
11. [Best Practices & Patterns](#11-best-practices--patterns)

---

## 1. System Overview

### 1.1 What is Sensei OS?

**Sensei OS** is a comprehensive Manufacturing Execution System (MES) and Enterprise Resource Planning (ERP) integration platform designed specifically for manufacturing environments. The name "Sensei" (先生, meaning "teacher" in Japanese) reflects the system's core philosophy of continuous improvement and operational excellence following Lean Manufacturing and Toyota Production System (TPS) principles.

### 1.2 Core Principles

1. **Continuous Improvement (Kaizen)**: The system is designed to identify and eliminate waste
2. **Respect for People**: RBAC ensures the right information reaches the right people
3. **Just-in-Time**: Features unlock only when needed (Maturity Model)
4. **Built-in Quality (Jidoka)**: Automated quality checks at every step
5. **Visual Management**: Real-time dashboards and Andon systems

### 1.3 Key Capabilities

| Capability | Description |
|------------|-------------|
| **CRM & Sales** | Opportunity management, RFQ processing, quoting |
| **Quality Management** | NC handling, CAPA, 8D reports, inspection plans |
| **Production** | Work orders, standard work, Andon, OEE tracking |
| **Warehouse** | Inventory, lot traceability, cycle counting |
| **Learning & Training** | AI-powered knowledge base, skill matrix |
| **Executive Intelligence** | War rooms, NL2SQL queries, burnout detection |

---

## 2. Architecture & Technology Stack

### 2.1 Backend Architecture

```
backend/
├── src/sensei/
│   ├── api/           # FastAPI REST endpoints
│   ├── core/          # Core utilities (auth, config, security)
│   ├── middleware/    # Request/response middleware
│   ├── ml/            # Machine learning services
│   ├── models/        # SQLAlchemy ORM models
│   ├── services/      # Business logic services
│   └── cli/           # Command-line tools
├── tests/
│   ├── api/           # API endpoint tests
│   ├── core/          # Core module tests
│   ├── e2e/           # End-to-end verification tests
│   ├── services/      # Service layer tests
│   └── functional/    # Workflow tests
└── alembic/           # Database migrations
```

### 2.2 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Runtime** | Python 3.12+ | Backend execution |
| **Web Framework** | FastAPI | Async REST API |
| **Database** | PostgreSQL 15+ | Primary data store |
| **Cache** | Redis | Session, cache, rate limiting |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Auth** | JWT + TOTP | Stateless authentication |
| **File Storage** | S3-compatible | Attachments, documents |
| **Deployment** | Kubernetes (Helm) | Container orchestration |

### 2.3 Service Pattern

All business logic follows the **Pure Python Service** pattern:

```python
@dataclass
class ServiceResult:
    """Standard result wrapper."""
    success: bool
    data: Any = None
    error: str | None = None

class SomeService:
    """
    Service docstring explaining purpose.
    
    RBAC: Defines which roles can access this service.
    """
    ALLOWED_ROLES = {"admin", "ceo", "gm", "exec"}
    
    def __init__(self):
        self._internal_state: dict[str, Any] = {}
    
    def _check_role(self, user_role: str) -> bool:
        """Normalize and check role."""
        normalized = user_role.lower().replace("-", "_").strip()
        return normalized in self.ALLOWED_ROLES
    
    def perform_action(
        self,
        param: str,
        user_role: str = "admin"
    ) -> ServiceResult:
        """Public method with RBAC check."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' not allowed")
        
        # Business logic here
        return ServiceResult(success=True, data={"result": "value"})
```

---

## 3. Role-Based Access Control (RBAC)

### 3.1 Role Hierarchy

The system implements a comprehensive role hierarchy with 20+ distinct roles:

```
                    ┌─────────────┐
                    │   SUPERUSER │  ← Full system access
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │    ADMIN    │ │     CEO     │ │   SECOPS    │
    └──────┬──────┘ └──────┬──────┘ └─────────────┘
           │               │
    ┌──────▼──────┐ ┌──────▼──────┐
    │     IT      │ │    EXEC     │
    └─────────────┘ └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼───┐ ┌──────▼──────┐
       │     GM      │ │  HR   │ │ ACCOUNTANT  │
       └──────┬──────┘ └───────┘ └─────────────┘
              │
    ┌─────────┼─────────┬──────────┐
    │         │         │          │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌────▼────┐
│ SALES │ │  OPS  │ │QUALITY│ │WAREHOUSE│
└───────┘ └───┬───┘ └───────┘ └─────────┘
              │
       ┌──────┼──────┐
       │      │      │
   ┌───▼──┐ ┌─▼───┐ ┌▼────────┐
   │SUPER-│ │OPER-│ │MAINTEN- │
   │VISOR │ │ATOR │ │  ANCE   │
   └──────┘ └─────┘ └─────────┘
```

### 3.2 Role Definitions

| Role | Code | Access Level | Primary Functions |
|------|------|--------------|-------------------|
| **Superuser** | `superuser` | Full | System administration |
| **Admin** | `admin` | Full | User/role management |
| **CEO** | `ceo` | Strategic | All data, persona switching |
| **Executive** | `exec` | Strategic | Cross-department visibility |
| **General Manager** | `gm` | Tactical | Factory-wide management |
| **HR** | `hr` | Department | Personnel, training |
| **Accountant** | `accountant` | Department | Financial data |
| **Sales** | `sales` | Functional | CRM, quotes, orders |
| **Operations** | `ops` | Functional | Production, scheduling |
| **Quality** | `quality` | Functional | NC, CAPA, inspections |
| **Warehouse** | `warehouse` | Functional | Inventory, shipping |
| **Supervisor** | `supervisor` | Team | Team management |
| **Operator** | `operator` | Execution | Work instructions |
| **Maintenance** | `maintenance` | Execution | Equipment, repairs |
| **Viewer** | `viewer` | Read-only | Dashboard viewing |
| **IT** | `it` | Technical | System configuration |
| **BI/Analyst** | `bi`, `analyst` | Analytical | Reports, analytics |
| **Auditor** | `auditor` | Compliance | Audit trails |
| **SecOps** | `secops` | Security | Security monitoring |

### 3.3 Persona System

The CEO and GM roles can "switch personas" to view the system as different roles:

```python
class Persona(Enum):
    CEO = "ceo"           # Full visibility
    GM = "gm"             # Factory-level visibility
    SALES = "sales"       # Sales pipeline, quotes
    OPERATOR = "operator" # Work instructions only
    QUALITY = "quality"   # Quality dashboards
    HR = "hr"             # Personnel, training
    ACCOUNTANT = "accountant"
    WAREHOUSE = "warehouse"
    SUPERVISOR = "supervisor"
    MAINTENANCE = "maintenance"
```

This allows executives to understand exactly what each role sees, without creating fake accounts.

---

## 4. Core Modules

### 4.1 CRM & Sales Module

**Purpose**: Manage customer relationships, opportunities, and sales pipeline.

**Key Components**:
- **Opportunity Kanban**: Visual pipeline with drag-and-drop stages
- **Account Management**: Customer and contact database
- **RFQ Processing**: Request for Quote handling with scoring
- **Quote Builder**: Line-item pricing with approval workflows

**RBAC**: `sales`, `gm`, `exec`, `ceo`, `admin`

### 4.2 Quality Management Module

**Purpose**: Ensure product quality through systematic defect prevention and correction.

**Key Components**:
- **Non-Conformance (NC)**: Defect recording and disposition
- **CAPA**: Corrective/Preventive Action tracking
- **8D Reports**: Structured problem-solving documentation
- **Inspection Plans**: Sampling-based quality checks (AQL)

**RBAC**: `quality`, `supervisor`, `gm`, `exec`, `ceo`, `admin`

### 4.3 Production Module

**Purpose**: Execute and track manufacturing operations.

**Key Components**:
- **Work Centers**: Station configuration and capacity
- **Standard Work**: Digital work instructions
- **Work Orders**: Production job tracking
- **Andon System**: Real-time alerts and escalation
- **OEE Tracking**: Availability × Performance × Quality

**RBAC**: `operator`, `supervisor`, `ops`, `gm`, `admin`

### 4.4 Warehouse Module

**Purpose**: Manage inventory, locations, and material flow.

**Key Components**:
- **Location Mapping**: Aisle/Bin/Rack hierarchy
- **Lot Traceability**: Full genealogy (1-up/1-down)
- **Transactions**: Putaway, picking, issues
- **Cycle Counting**: Smart inventory verification

**RBAC**: `warehouse`, `ops`, `quality`, `gm`, `admin`

### 4.5 Knowledge & Training Module

**Purpose**: AI-powered learning and skill development.

**Key Components**:
- **Knowledge Ingestion**: Document indexing CLI
- **Semantic Search**: Vector-based retrieval
- **Training Matrix**: Skill gap analysis
- **AI Recommendations**: Personalized learning paths

**RBAC**: `hr`, `supervisor`, `gm`, `exec`, `admin`

---

## 5. Enterprise Integrations

### 5.1 ERP Integration Layer

The system provides bi-directional synchronization with external ERP systems:

```python
class ERPIntegrationService:
    """
    Handles bi-directional ERP synchronization.
    
    Sync Types:
    - Master Data: Customers, Suppliers, Parts, BOMs
    - Transactional: Orders, Receipts, Shipments
    - Financial: Quality costs, labor hours
    """
    
    def sync_master_data(self, entity_type: str) -> SyncResult:
        """Synchronize master data entities."""
        ...
    
    def push_transaction(self, transaction: ERPTransaction) -> bool:
        """Push transaction to ERP."""
        ...
```

### 5.2 PLM Integration

Drawing and revision control integration:

- **Revision Linking**: Immutable hash-linking between systems
- **Impact Analysis**: AI-driven change impact detection
- **Controlled Distribution**: Only released revisions on shop floor

### 5.3 Accounting Integration

- **Multi-currency**: EUR base with MAD/USD conversion
- **Cost Tracking**: Scrap/rework cost attribution
- **Labor Export**: Time-and-attendance to payroll

---

## 6. Deployment Maturity Model

### 6.1 The L0-L5 Model

Sensei OS implements a **Deployment Maturity Model** that progressively unlocks features:

```
L0: STRATEGIC     →  CRM, RFQ, Quotes (Sales focus)
L1: DESIGN        →  Orders, Onboarding, Training
L2: ENGINEERING   →  BOM, Routing, Quality Planning
L3: REHEARSAL     →  Work Orders, Standard Work (Simulation)
L4: PRODUCTION    →  Live Production, Metrics
L5: TPS           →  Andon, Jidoka, Kaizen, Heijunka
```

### 6.2 Feature Visibility

Each level has specific features enabled:

| Level | Features Unlocked |
|-------|-------------------|
| **L0** | CRM, RFQ, Quotes, Accounts |
| **L1** | Orders, Onboarding, Training |
| **L2** | BOM, Routing, Quality Planning |
| **L3** | Work Orders, Standard Work, Rehearsal Mode |
| **L4** | Production, Live Tracking, Metrics |
| **L5** | Andon, Jidoka, Kaizen, Heijunka |

### 6.3 Level-Up Checklists

Transitioning between levels requires completing checklists:

```python
DEFAULT_LEVEL_UP_CHECKLISTS = {
    (L0_STRATEGIC, L1_PLANNING): [
        {"id": "org-chart", "title": "Define organization structure"},
        {"id": "site-layout", "title": "Upload site layout drawings"},
        {"id": "training-plan", "title": "Create initial training plan"},
    ],
    (L1_PLANNING, L2_ENGINEERING): [
        {"id": "bom-structure", "title": "Import BOM hierarchy"},
        {"id": "routing-setup", "title": "Define production routings"},
    ],
    # ... more transitions
}
```

---

## 7. E2E Testing Strategy

### 7.1 Test Categories

The E2E test suite covers all critical functionality:

| Category | Test File | Tests | Coverage |
|----------|-----------|-------|----------|
| **Persona Management** | `test_persona_management.py` | 15 | CEO account, persona switching |
| **UI/UX Verification** | `test_uiux_verification.py` | 48 | Typography, accessibility, responsiveness |
| **Infrastructure** | `test_infrastructure_resilience.py` | 30 | Performance, failover, backup |
| **AI Reasoning** | `test_ai_reasoning.py` | 22 | Hybrid search, explanations |
| **CEO Control Plane** | `test_ceo_control_plane.py` | 25 | NL2SQL, war room, retention |
| **Factory Launchpad** | `test_factory_launchpad_e2e.py` | 41 | Maturity gates, level-up |
| **Feature Matrix** | `test_feature_matrix.py` | 78 | All 46 features verified |

### 7.2 Running Tests

```bash
# Run all E2E tests
cd backend
PYTHONPATH=src python3 -m pytest tests/e2e/ -v

# Run specific category
PYTHONPATH=src python3 -m pytest tests/e2e/test_feature_matrix.py -v

# Run with coverage
PYTHONPATH=src python3 -m pytest tests/e2e/ --cov=src/sensei --cov-report=html
```

### 7.3 Test Pattern

All E2E tests follow a consistent pattern:

```python
@pytest.fixture
def service() -> SomeE2EService:
    """Create service instance."""
    return create_some_e2e_service()

class TestSomeFeature:
    """Test feature verification."""
    
    def test_feature_works(self, service: SomeE2EService):
        """Test that feature functions correctly."""
        result = service.verify_feature("feature-id")
        assert result.passed is True
    
    def test_rbac_enforcement(self, service: SomeE2EService):
        """Test RBAC is enforced."""
        with pytest.raises(PermissionError):
            service.verify_feature("feature-id", user_role="viewer")
```

---

## 8. Service Catalog

### 8.1 Core Services

| Service | Location | Purpose |
|---------|----------|---------|
| `AuthService` | `core/auth.py` | Authentication, JWT, 2FA |
| `RBACService` | `core/rbac.py` | Permission checking |
| `StorageService` | `core/storage.py` | S3 file handling |
| `RedisService` | `core/redis.py` | Caching, sessions |

### 8.2 Business Services

| Service | Location | Purpose |
|---------|----------|---------|
| `ERPIntegrationService` | `services/erp_integration.py` | ERP sync |
| `WarehouseManagementService` | `services/warehouse_management.py` | WMS |
| `LotSerialTraceabilityService` | `services/lot_serial_traceability.py` | Genealogy |
| `FactoryLaunchpad` | `services/factory_launchpad.py` | Maturity model |
| `WorkflowGateService` | `services/workflow_gates.py` | State machines |

### 8.3 E2E Verification Services

| Service | Location | Purpose |
|---------|----------|---------|
| `PersonaManagementService` | `tests/e2e/test_persona_management.py` | CEO personas |
| `UIUXVerificationService` | `tests/e2e/test_uiux_verification.py` | UI audits |
| `InfrastructureResilienceService` | `tests/e2e/test_infrastructure_resilience.py` | Performance |
| `AIReasoningService` | `tests/e2e/test_ai_reasoning.py` | AI verification |
| `CEOControlPlaneService` | `tests/e2e/test_ceo_control_plane.py` | Executive tools |
| `FeatureMatrixVerificationService` | `tests/e2e/test_feature_matrix.py` | All features |

---

## 9. Operations & DevOps

### 9.1 Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Frontend   │  │   Backend    │  │   Worker     │   │
│  │   (Next.js)  │  │   (FastAPI)  │  │   (Celery)   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │           │
│  ┌──────▼─────────────────▼─────────────────▼───────┐   │
│  │                 Ingress (Traefik)                 │   │
│  └───────────────────────┬───────────────────────────┘   │
│                          │                              │
│  ┌───────────────────────▼───────────────────────────┐   │
│  │  PostgreSQL  │  Redis  │  S3 (MinIO)  │  MLflow   │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 9.2 Helm Chart Structure

```
k8s/helm/sensei/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── hpa.yaml
└── charts/
    ├── postgresql/
    └── redis/
```

### 9.3 Health Monitoring

The system includes comprehensive health checks:

```python
class HealthWatchdogService:
    """Monitors system health across components."""
    
    def check_database_health(self) -> HealthStatus:
        """Check database connectivity and performance."""
        ...
    
    def check_redis_health(self) -> HealthStatus:
        """Check Redis availability."""
        ...
    
    def check_s3_health(self) -> HealthStatus:
        """Check S3 storage access."""
        ...
    
    def get_overall_health(self) -> SystemHealth:
        """Aggregate all health checks."""
        ...
```

---

## 10. Security Model

### 10.1 Authentication

```
┌─────────────────────────────────────────────────────────┐
│                  Authentication Flow                     │
│                                                         │
│  User → Login Form → Password Check → 2FA (if enabled) │
│                           ↓                             │
│                    JWT Token Issued                     │
│                           ↓                             │
│              Token stored in HttpOnly Cookie            │
│                           ↓                             │
│         Subsequent requests include JWT automatically    │
└─────────────────────────────────────────────────────────┘
```

### 10.2 JWT Structure

```json
{
  "sub": "user-uuid",
  "role": "gm",
  "site_id": "site-001",
  "permissions": ["read:orders", "write:orders", "read:production"],
  "exp": 1704067200,
  "iat": 1704063600
}
```

### 10.3 Security Features

| Feature | Implementation |
|---------|----------------|
| **Password Hashing** | Argon2id with secure parameters |
| **2FA** | TOTP (Google Authenticator compatible) |
| **Rate Limiting** | Redis-backed, per-user/IP |
| **CSRF Protection** | SameSite cookies + header validation |
| **XSS Prevention** | CSP headers, input sanitization |
| **SQL Injection** | Parameterized queries (SQLAlchemy) |
| **Audit Logging** | Immutable, append-only logs |

---

## 11. Best Practices & Patterns

### 11.1 Service Design Principles

1. **Single Responsibility**: Each service handles one domain
2. **Dependency Injection**: Services receive dependencies via constructor
3. **Explicit RBAC**: Every public method checks permissions
4. **Comprehensive Testing**: 100% coverage goal for services
5. **Dataclass Models**: Use dataclasses for data transfer

### 11.2 Error Handling Pattern

```python
from dataclasses import dataclass
from enum import Enum

class ErrorCode(Enum):
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"

@dataclass
class ServiceError:
    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class Result[T]:
    success: bool
    data: T | None = None
    error: ServiceError | None = None
    
    @classmethod
    def ok(cls, data: T) -> "Result[T]":
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: ServiceError) -> "Result[T]":
        return cls(success=False, error=error)
```

### 11.3 Testing Best Practices

1. **Use fixtures** for common setup
2. **Test happy path first**, then edge cases
3. **Always test RBAC** - verify allowed AND denied roles
4. **Use descriptive names**: `test_<method>_<scenario>_<expected>`
5. **Isolate tests**: No shared mutable state

### 11.4 Code Organization

```python
# Good: Organized by domain
from sensei.services.quality import NCService, CAPAService
from sensei.services.production import WorkOrderService, AndonService

# Each service in its own file or module
# services/
#   quality/
#     __init__.py
#     nc_service.py
#     capa_service.py
#   production/
#     __init__.py
#     work_order_service.py
#     andon_service.py
```

---

## Summary

Sensei OS is a comprehensive manufacturing management platform built on:

- **Python 3.12+** with FastAPI for high-performance async APIs
- **20+ RBAC roles** with persona switching for executives
- **6-level maturity model** (L0-L5) for progressive feature deployment
- **10 feature categories** with 46 verified features
- **Comprehensive E2E testing** with 259+ automated tests
- **Enterprise integrations** for ERP, PLM, and accounting
- **Security-first design** with JWT, 2FA, and audit logging

The system follows Lean Manufacturing principles (TPS) and is designed to scale from small facilities to enterprise-wide deployments.

---

*Document Version: 1.0*  
*Last Updated: January 2025*  
*Total E2E Tests: 259 (all passing)*
