# Configuration Reference

Complete reference for configuring Starz Morocco Manufacturing Management System.

> **Legacy sections:** The Python/FastAPI (`backend/`), Next.js (`frontend/`) and
> Redis sections below describe the previous stack. The platform has migrated
> to Rust (Axum) + Leptos — the **canonical environment contract is
> `.env.example`** (single source of truth for Compose, Helm and Rust) and the
> authoritative configuration code is `sensei-rs/crates/sensei-core/src/config.rs`.
> The legacy sections are kept for historical reference only; do not use them
> as the basis for new configuration.

## 🔐 Security Headers Policy (Single Source of Truth)

The security header policy is defined **once** and emitted by the **backend**
(`sensei-rs/crates/sensei-api/src/middleware/secure_headers.rs`). Caddy
(`caddy/Caddyfile`, `caddy/Caddyfile.production`) must **not** duplicate or
contradict these headers:

| Header | Value | Owner |
|--------|-------|-------|
| `X-XSS-Protection` | `0` | backend + Caddy (identical) |
| `X-Content-Type-Options` | `nosniff` | backend + Caddy (identical) |
| `X-Frame-Options` | `DENY` | backend + Caddy (identical) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | backend + Caddy (identical) |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | backend + Caddy (identical) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | **backend only** (TLS-aware; Caddy must not set it) |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' ws: wss:; frame-ancestors 'none'` | backend (configurable via `SECURITY_CSP`); Caddy mirrors the backend value |
| CORS headers | `CORS_ALLOWED_ORIGINS` | **backend only** (Caddy adds no `Access-Control-*` headers) |

Rules:
1. `X-XSS-Protection` must stay `0` everywhere — the legacy `1; mode=block`
   was removed because it is ineffective and can create vulnerabilities.
2. HSTS is emitted by the backend only, and only over HTTPS.
3. When the frontend is consolidated (removing `unsafe-inline`/`unsafe-eval`),
   both the backend default CSP **and** the Caddy CSP must drop them together —
   this is tracked as part of the frontend hardening work.

## 📋 Table of Contents

- [Backend Configuration](#backend-configuration)
- [Frontend Configuration](#frontend-configuration)
- [Database Configuration](#database-configuration)
- [Redis Configuration](#redis-configuration)
- [Storage Configuration](#storage-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Email Configuration](#email-configuration)
- [AI/ML Configuration](#ai-ml-configuration)
- [Kubernetes Configuration](#kubernetes-configuration)
- [Environment Variables](#environment-variables)

## 🔧 Backend Configuration

### Configuration File Location

Backend configuration is managed through environment variables or a `.env` file in the `backend/` directory.

### Core Settings

```bash
# Application
APP_NAME="Starz Morocco Manufacturing"
APP_VERSION="1.0.0"
SENSEI_ENV="production"  # development/dev, staging/test, production/prod (parsed strictly)
DEBUG=false  # Enable debug mode (development only)
LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Server
HOST="0.0.0.0"
PORT=8000
WORKERS=4  # Number of uvicorn workers
RELOAD=false  # Auto-reload on code changes (development only)

# API
API_V1_PREFIX="/api/v1"
CORS_ALLOWED_ORIGINS='["https://app.flopsen.tech", "https://flopsen.tech"]'
ALLOWED_HOSTS='["app.flopsen.tech", "flopsen.tech"]'
```

### Configuration Class

Located in `backend/src/sensei/core/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Starz Morocco"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis
    redis_url: str
    redis_ttl: int = 3600  # Default cache TTL in seconds
    
    # Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 7
    
    # CORS
    cors_origins: list[str] = []
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## 🌐 Frontend Configuration

### Environment Files

Frontend uses multiple environment files:

- `.env.local` - Local development (not committed)
- `.env.development` - Development environment
- `.env.staging` - Staging environment
- `.env.production` - Production environment

### Core Settings

```bash
# API
NEXT_PUBLIC_API_URL=https://api.flopsen.tech
NEXT_PUBLIC_API_TIMEOUT=30000

# App
NEXT_PUBLIC_APP_NAME="Starz Morocco Manufacturing"
NEXT_PUBLIC_APP_VERSION="1.0.0"

# Features
NEXT_PUBLIC_ENABLE_PWA=true
NEXT_PUBLIC_ENABLE_OFFLINE=true
NEXT_PUBLIC_ENABLE_ANALYTICS=true

# Analytics (optional)
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx

# Auth
NEXT_PUBLIC_AUTH_COOKIE_NAME="sensei-auth"
NEXT_PUBLIC_REFRESH_TOKEN_KEY="sensei-refresh-token"
```

### Next.js Configuration

Located in `frontend/next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // PWA configuration
  pwa: {
    dest: 'public',
    disable: process.env.NODE_ENV === 'development',
    register: true,
    skipWaiting: true,
  },
  
  // Image optimization
  images: {
    domains: ['api.example.com', 's3.example.com'],
    formats: ['image/avif', 'image/webp'],
  },
  
  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  
  // Internationalization
  i18n: {
    locales: ['en', 'es', 'fr'],
    defaultLocale: 'en',
  },
  
  // Headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

## 🗄️ Database Configuration

### PostgreSQL Connection

```bash
# Connection URL format:
# postgresql+asyncpg://user:password@host:port/database

DATABASE_URL="postgresql+asyncpg://sensei:password@localhost:5432/sensei"

# Connection Pool
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# SSL (production)
DATABASE_SSL_MODE="require"  # disable, allow, prefer, require, verify-ca, verify-full
```

### SQLAlchemy Configuration

Located in `backend/src/sensei/core/database.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,  # Verify connections before using
)
```

### Database Tuning

PostgreSQL configuration (`postgresql.conf`):

```ini
# Connection Settings
max_connections = 100
superuser_reserved_connections = 3

# Memory Settings
shared_buffers = 512MB  # 25% of RAM for small instances
effective_cache_size = 1536MB  # 75% of RAM
work_mem = 16MB
maintenance_work_mem = 128MB

# Query Planner
random_page_cost = 1.1  # For SSD storage
effective_io_concurrency = 200

# Write Ahead Log
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 1GB
min_wal_size = 256MB

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'all'  # development only
log_duration = on
log_min_duration_statement = 1000  # Log slow queries (>1s)

# Autovacuum
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
```

## 💾 Redis Configuration

### Connection

```bash
REDIS_URL="redis://localhost:6379/0"
REDIS_PASSWORD=""  # Leave empty if no password
REDIS_TTL=3600  # Default TTL in seconds
REDIS_MAX_CONNECTIONS=10
```

### Redis Configuration File

Redis configuration (`redis.conf`):

```ini
# Network
bind 0.0.0.0
port 6379
protected-mode yes
requirepass yourpassword

# General
daemonize no
databases 16
timeout 300

# Snapshotting
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
dbfilename dump.rdb
dir ./

# Replication (for HA)
# replicaof <masterip> <masterport>
# masterauth <master-password>

# Memory Management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Append Only File (durability)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Slow Log
slowlog-log-slower-than 10000  # Log queries > 10ms
slowlog-max-len 128

# Latency Monitor
latency-monitor-threshold 100
```

## 📦 Storage Configuration

### MinIO (S3-Compatible)

```bash
# MinIO Connection
MINIO_ENDPOINT="localhost:9000"
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="minioadmin"
MINIO_BUCKET_NAME="sensei-attachments"
MINIO_USE_SSL=false
MINIO_REGION="us-east-1"

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB in bytes
ALLOWED_EXTENSIONS='["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg"]'
```

### Hetzner Object Storage

```bash
# Hetzner S3-Compatible Storage
MINIO_ENDPOINT="fsn1.your-objectstorage.com"
MINIO_ACCESS_KEY="your-access-key"
MINIO_SECRET_KEY="your-secret-key"
MINIO_BUCKET_NAME="sensei-production"
MINIO_USE_SSL=true
MINIO_REGION="eu-central-1"
```

### Local File Storage

```bash
# Alternative: Local file storage (not recommended for production)
STORAGE_TYPE="local"  # local or s3
UPLOAD_DIR="/var/sensei/uploads"
```

## 🔐 Authentication Configuration

### JWT Settings

```bash
# JWT Secret (CHANGE THIS!)
SECRET_KEY="your-secret-key-here-change-this"  # Generate with: openssl rand -hex 32
ALGORITHM="HS256"

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true

# Rate Limiting
LOGIN_RATE_LIMIT=5  # Max attempts
LOGIN_RATE_WINDOW=900  # 15 minutes in seconds
ACCOUNT_LOCKOUT_DURATION=3600  # 1 hour
```

### OAuth Configuration (Optional)

```bash
# Google OAuth
GOOGLE_CLIENT_ID="your-client-id"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REDIRECT_URI="https://app.flopsen.tech/auth/google/callback"

# Microsoft OAuth
MICROSOFT_CLIENT_ID="your-client-id"
MICROSOFT_CLIENT_SECRET="your-client-secret"
MICROSOFT_TENANT_ID="your-tenant-id"
```

## 📧 Email Configuration

### SMTP Settings

```bash
# SMTP Server
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="noreply@flopsen.tech"
SMTP_PASSWORD="your-app-password"
SMTP_TLS=true
SMTP_SSL=false

# Email Settings
EMAIL_FROM="Starz Morocco <noreply@flopsen.tech>"
EMAIL_FROM_NAME="Starz Morocco Manufacturing"

# Templates
EMAIL_TEMPLATES_DIR="backend/src/sensei/templates/email"
```

### SendGrid (Alternative)

```bash
SENDGRID_API_KEY="your-api-key"
EMAIL_FROM="noreply@flopsen.tech"
```

## 🤖 AI/ML Configuration

### OpenAI

```bash
# OpenAI API
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o-mini"
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.3
OPENAI_TIMEOUT=30

# Features
ENABLE_SMART_INGESTION=true
ENABLE_KNOWLEDGE_SEARCH=true
```

### Sentence Transformers

```bash
# Embedding Model
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION=384
EMBEDDING_DEVICE="cpu"  # cpu or cuda

# Vector Search
VECTOR_SEARCH_K=10  # Top K results
VECTOR_SEARCH_THRESHOLD=0.7  # Minimum similarity score
```

## ☸️ Kubernetes Configuration

### Helm Values

Located in `k8s/helm/sensei/values.yaml`:

```yaml
# Global settings
global:
  storageClass: "standard"

# Backend
backend:
  replicaCount: 2
  image:
    repository: sensei/backend
    tag: latest
    pullPolicy: IfNotPresent
  
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "1000m"
  
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  
  env:
    - name: SENSEI_ENV
      value: "production"
    - name: LOG_LEVEL
      value: "INFO"
  
  envFrom:
    - secretRef:
        name: sensei-secrets

# Frontend
frontend:
  replicaCount: 2
  image:
    repository: sensei/frontend
    tag: latest
  
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"

# PostgreSQL
postgresql:
  enabled: true
  auth:
    username: sensei
    password: changeMe
    database: sensei
  
  primary:
    persistence:
      size: 20Gi
    resources:
      requests:
        memory: "1Gi"
        cpu: "500m"

# Redis
redis:
  enabled: true
  auth:
    password: changeMe
  
  master:
    persistence:
      size: 8Gi
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"

# Ingress
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: app.flopsen.tech
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: starzmorocco-tls
      hosts:
        - app.flopsen.tech
```

## 📝 Environment Variables

### Complete List

#### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | "Starz Morocco" | Application name |
| `SENSEI_ENV` | No | "production" | Environment (development/dev, staging/test, production/prod — parsed strictly) |
| `DEBUG` | No | false | Debug mode |
| `LOG_LEVEL` | No | "INFO" | Logging level |
| `HOST` | No | "0.0.0.0" | Server host |
| `PORT` | No | 8000 | Server port |
| `DATABASE_URL` | **Yes** | - | PostgreSQL connection URL |
| `REDIS_URL` | **Yes** | - | Redis connection URL |
| `SECRET_KEY` | **Yes** | - | JWT secret key |
| `MINIO_ENDPOINT` | **Yes** | - | S3 endpoint |
| `MINIO_ACCESS_KEY` | **Yes** | - | S3 access key |
| `MINIO_SECRET_KEY` | **Yes** | - | S3 secret key |
| `OPENAI_API_KEY` | No | - | OpenAI API key (for AI features) |
| `SMTP_HOST` | No | - | SMTP server host |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |

#### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | **Yes** | - | Backend API URL |
| `NEXT_PUBLIC_APP_NAME` | No | "Starz Morocco" | Application name |
| `NEXT_PUBLIC_ENABLE_PWA` | No | true | Enable PWA |
| `NEXT_PUBLIC_GA_ID` | No | - | Google Analytics ID |

### Loading Environment Variables

#### Backend (.env file)

```bash
# Create .env file
cp backend/.env.example backend/.env

# Edit with your values
nano backend/.env
```

#### Frontend (.env.local file)

```bash
# Create .env.local file
cp frontend/.env.example frontend/.env.local

# Edit with your values
nano frontend/.env.local
```

#### Kubernetes (Secrets)

```bash
# Create secret from file
kubectl create secret generic sensei-secrets \
  --from-env-file=backend/.env \
  --namespace=sensei

# Or create directly
kubectl create secret generic sensei-secrets \
  --from-literal=DATABASE_URL='postgresql://...' \
  --from-literal=REDIS_URL='redis://...' \
  --from-literal=SECRET_KEY='...' \
  --namespace=sensei
```

## 🔍 Configuration Validation

### Backend Validation

The backend validates configuration on startup:

```python
from sensei.core.config import settings

# Validate required settings
assert settings.secret_key, "SECRET_KEY must be set"
assert settings.database_url, "DATABASE_URL must be set"
assert len(settings.secret_key) >= 32, "SECRET_KEY must be at least 32 characters"
```

### Frontend Validation

Check configuration in browser console:

```javascript
console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
console.log('Environment:', process.env.NODE_ENV);
```

## 📚 Additional Resources

- [Backend Configuration Code](../../../backend/src/sensei/core/config.py)
- [Frontend Configuration](../../../frontend/next.config.js)
- [Helm Values](../../../k8s/helm/sensei/values.yaml)
- [Environment Examples](../../../backend/.env.example)

---

**Need Help?** See [Getting Started Guide](../development/getting-started.md) or [Deployment Guide](../deployment/DEPLOYMENT.md).
