# Troubleshooting Guide

Common issues and solutions for Starz Morocco Manufacturing Management System.

## 📋 Table of Contents

- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Database Issues](#database-issues)
- [Authentication Issues](#authentication-issues)
- [Deployment Issues](#deployment-issues)
- [Performance Issues](#performance-issues)
- [Network Issues](#network-issues)
- [Development Issues](#development-issues)

## 🔧 Backend Issues

### Application Won't Start

**Problem**: Backend fails to start with error messages

**Common Causes & Solutions**:

1. **Missing Environment Variables**
   ```bash
   # Error: "SECRET_KEY must be set"
   # Solution: Create .env file with required variables
   cp backend/.env.example backend/.env
   nano backend/.env  # Add SECRET_KEY and other required vars
   ```

2. **Database Connection Failed**
   ```bash
   # Error: "connection refused" or "could not connect to server"
   # Solution: Verify PostgreSQL is running
   docker ps | grep postgres
   
   # Start PostgreSQL if not running
   docker-compose up -d postgres
   
   # Check DATABASE_URL format
   # postgresql+asyncpg://user:password@localhost:5432/database
   ```

3. **Port Already in Use**
   ```bash
   # Error: "Address already in use"
   # Solution: Find and kill process using port 8000
   lsof -i :8000
   kill -9 <PID>
   
   # Or use a different port
   PORT=8001 uvicorn sensei.main:app --reload
   ```

4. **Python Version Mismatch**
   ```bash
   # Error: "Python 3.11 required"
   # Solution: Install correct Python version
   python --version  # Check current version
   
   # Use pyenv to install Python 3.11
   pyenv install 3.11.7
   pyenv local 3.11.7
   ```

### Import Errors

**Problem**: ModuleNotFoundError or ImportError

**Solutions**:

```bash
# 1. Reinstall dependencies
cd backend
pip install -e ".[dev]"

# 2. Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 3. Check if virtual environment is activated
which python  # Should point to .venv/bin/python

# 4. Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name '*.pyc' -delete
```

### Database Migration Errors

**Problem**: Alembic migration fails

**Solutions**:

```bash
# 1. Check current database state
alembic current

# 2. Downgrade and re-apply
alembic downgrade -1
alembic upgrade head

# 3. Generate new migration if needed
alembic revision --autogenerate -m "description"

# 4. Reset database (CAUTION: loses data)
alembic downgrade base
alembic upgrade head

# 5. Check for conflicting migrations
alembic history

# 6. Force specific version
alembic stamp head
```

### API Returns 500 Errors

**Problem**: Internal server errors on API requests

**Debugging Steps**:

```bash
# 1. Check application logs
tail -f logs/sensei.log

# 2. Enable debug mode
DEBUG=true uvicorn sensei.main:app --reload

# 3. Check database connections
# In Python shell:
from sensei.core.database import engine
await engine.connect()  # Should succeed

# 4. Verify Redis connection
redis-cli ping  # Should return PONG

# 5. Check for uncaught exceptions
grep "ERROR" logs/sensei.log
```

## 🌐 Frontend Issues

### Frontend Won't Start

**Problem**: npm run dev fails

**Solutions**:

```bash
# 1. Delete node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# 2. Check Node version
node --version  # Should be 18+

# 3. Clear Next.js cache
rm -rf .next

# 4. Check for port conflicts
lsof -i :3000
kill -9 <PID>

# 5. Try different port
PORT=3001 npm run dev
```

### Build Failures

**Problem**: npm run build fails

**Common Issues**:

1. **TypeScript Errors**
   ```bash
   # Check for type errors
   npm run type-check
   
   # Fix common issues:
   # - Add missing type imports
   # - Fix any type mismatches
   # - Update type definitions
   ```

2. **ESLint Errors**
   ```bash
   # Run linter
   npm run lint
   
   # Auto-fix issues
   npm run lint -- --fix
   ```

3. **Memory Issues**
   ```bash
   # Increase Node memory
   NODE_OPTIONS="--max-old-space-size=4096" npm run build
   ```

### API Connection Issues

**Problem**: Frontend can't connect to backend

**Solutions**:

```bash
# 1. Verify API URL
cat frontend/.env.local
# Should have: NEXT_PUBLIC_API_URL=http://localhost:8000

# 2. Check CORS settings
# Backend should allow frontend origin

# 3. Test API directly
curl http://localhost:8000/health

# 4. Check browser console for errors
# Open DevTools > Console > Network tab

# 5. Verify backend is running
curl http://localhost:8000/api/v1/health
```

### Blank Page or White Screen

**Problem**: Frontend loads but shows blank page

**Debugging**:

```bash
# 1. Check browser console
# Look for JavaScript errors

# 2. Check if API is accessible
# Network tab should show successful API calls

# 3. Clear browser cache
# Hard refresh: Ctrl+Shift+R (Linux/Windows)
# or Cmd+Shift+R (Mac)

# 4. Check for authentication issues
# Clear cookies and local storage

# 5. Run in development mode
npm run dev  # Provides more detailed errors
```

## 🗄️ Database Issues

### Connection Refused

**Problem**: Can't connect to PostgreSQL

**Solutions**:

```bash
# 1. Check if PostgreSQL is running
docker ps | grep postgres
# Or: systemctl status postgresql

# 2. Check port
netstat -tuln | grep 5432

# 3. Test connection
psql -h localhost -U sensei -d sensei

# 4. Check DATABASE_URL format
# postgresql+asyncpg://username:password@host:port/database

# 5. Verify credentials
# Check .env file or Kubernetes secret

# 6. Check PostgreSQL logs
docker logs sensei-postgres
# Or: tail -f /var/log/postgresql/postgresql-15-main.log
```

### pgvector Extension Missing

**Problem**: Vector search fails with "extension not found"

**Solutions**:

```bash
# 1. Install pgvector extension
docker exec -it sensei-postgres psql -U sensei
CREATE EXTENSION IF NOT EXISTS vector;
\dx  # List extensions

# 2. Use ankane/pgvector image
docker run -d \
  --name sensei-postgres \
  -e POSTGRES_PASSWORD=postgres \
  ankane/pgvector

# 3. Verify extension
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Slow Queries

**Problem**: Database queries are slow

**Debugging**:

```sql
-- 1. Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- 2. Check current queries
SELECT pid, age(clock_timestamp(), query_start), usename, query 
FROM pg_stat_activity 
WHERE query != '<IDLE>' AND query NOT ILIKE '%pg_stat_activity%'
ORDER BY query_start desc;

-- 3. Find missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
AND n_distinct IS NOT NULL
ORDER BY abs(correlation) DESC;

-- 4. Analyze table statistics
ANALYZE VERBOSE table_name;

-- 5. Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### Database Locks

**Problem**: Queries timing out due to locks

**Solutions**:

```sql
-- 1. Find blocking queries
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- 2. Kill blocking query
SELECT pg_terminate_backend(blocking_pid);

-- 3. Reduce lock duration
-- Use shorter transactions
-- Add timeouts: SET statement_timeout = '30s';
```

## 🔐 Authentication Issues

### Login Fails

**Problem**: Can't log in with correct credentials

**Solutions**:

```bash
# 1. Check if user exists
docker exec -it sensei-postgres psql -U sensei
SELECT id, email, is_active FROM users WHERE email = 'user@example.com';

# 2. Reset password
python -m sensei.cli.user reset-password \
  --email user@example.com \
  --password newpassword

# 3. Check account status
SELECT email, is_active, failed_login_attempts, locked_until 
FROM users 
WHERE email = 'user@example.com';

# 4. Unlock account
UPDATE users SET failed_login_attempts = 0, locked_until = NULL 
WHERE email = 'user@example.com';

# 5. Verify JWT secret
# Ensure SECRET_KEY is set correctly in backend/.env
```

### Token Expired Errors

**Problem**: Authentication tokens expire too quickly

**Solutions**:

```bash
# 1. Increase token expiration
# In backend/.env:
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS=7

# 2. Implement token refresh
# Frontend should automatically refresh tokens before expiry

# 3. Clear old tokens
# In browser: Clear localStorage and cookies

# 4. Check server time
date  # Ensure server time is correct
```

### CORS Errors

**Problem**: Cross-Origin Request Blocked

**Solutions**:

```python
# backend/src/sensei/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Development
        "https://app.example.com",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## ☸️ Deployment Issues

### Pod CrashLoopBackOff

**Problem**: Kubernetes pod keeps restarting

**Debugging**:

```bash
# 1. Check pod status
kubectl get pods -n sensei

# 2. View pod logs
kubectl logs -n sensei <pod-name>
kubectl logs -n sensei <pod-name> --previous  # Previous container

# 3. Describe pod
kubectl describe pod -n sensei <pod-name>

# 4. Check events
kubectl get events -n sensei --sort-by='.lastTimestamp'

# 5. Common fixes:
# - Fix environment variables (missing secrets)
# - Increase resource limits
# - Fix liveness/readiness probes
# - Check image pull policy
```

### ImagePullBackOff

**Problem**: Can't pull Docker image

**Solutions**:

```bash
# 1. Check image name and tag
kubectl describe pod -n sensei <pod-name>

# 2. Verify image exists
docker pull sensei/backend:latest

# 3. Check image pull secrets
kubectl get secrets -n sensei
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password>

# 4. Update deployment to use secret
spec:
  imagePullSecrets:
    - name: regcred
```

### Ingress Not Working

**Problem**: Can't access application via domain

**Debugging**:

```bash
# 1. Check Ingress status
kubectl get ingress -n sensei
kubectl describe ingress -n sensei sensei-ingress

# 2. Check Ingress controller
kubectl get pods -n ingress-nginx

# 3. Test internal service
kubectl port-forward -n sensei svc/sensei-backend 8000:8000
curl http://localhost:8000/health

# 4. Check DNS
nslookup app.example.com
dig app.example.com

# 5. Check TLS certificate
kubectl get certificate -n sensei
kubectl describe certificate -n sensei sensei-tls

# 6. Check cert-manager
kubectl get pods -n cert-manager
kubectl logs -n cert-manager <cert-manager-pod>
```

## ⚡ Performance Issues

### Slow API Responses

**Problem**: API endpoints respond slowly

**Debugging**:

```bash
# 1. Enable timing logs
# Check X-Process-Time header in response

# 2. Identify slow queries
# Check PostgreSQL slow query log

# 3. Add database indexes
# Analyze query patterns and add indexes

# 4. Enable Redis caching
# Cache frequently accessed data

# 5. Profile code
python -m cProfile -o profile.stats sensei/main.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"

# 6. Check resource usage
docker stats sensei-backend
```

### High Memory Usage

**Problem**: Application consumes too much memory

**Solutions**:

```bash
# 1. Monitor memory usage
docker stats
kubectl top pods -n sensei

# 2. Reduce connection pool size
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# 3. Increase worker processes (distribute load)
WORKERS=4

# 4. Implement pagination
# Limit query results

# 5. Profile memory usage
python -m memory_profiler sensei/main.py
```

## 🌐 Network Issues

### Can't Connect to External Services

**Problem**: Can't reach external APIs or services

**Solutions**:

```bash
# 1. Test connectivity
curl -v https://api.openai.com

# 2. Check DNS resolution
nslookup api.openai.com

# 3. Check firewall rules
iptables -L -n

# 4. Check Kubernetes network policies
kubectl get networkpolicies -n sensei

# 5. Test from pod
kubectl exec -it -n sensei <pod-name> -- curl https://api.openai.com

# 6. Check proxy settings
env | grep -i proxy
```

## 💻 Development Issues

### Tests Failing

**Problem**: Test suite fails

**Solutions**:

```bash
# 1. Run specific test
pytest tests/api/test_quotes.py::test_create_quote -v

# 2. Show print statements
pytest tests/ -v -s

# 3. Stop on first failure
pytest tests/ -x

# 4. Run with coverage
pytest tests/ --cov=sensei --cov-report=html

# 5. Clear pytest cache
rm -rf .pytest_cache
pytest --cache-clear

# 6. Update test database
TEST_DATABASE_URL="postgresql://..." pytest tests/
```

### Hot Reload Not Working

**Problem**: Changes don't reflect during development

**Solutions**:

```bash
# 1. Backend: Ensure --reload flag
uvicorn sensei.main:app --reload

# 2. Frontend: Clear cache and restart
rm -rf .next
npm run dev

# 3. Check file watchers
# Increase limit if needed
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 4. Docker: Use volume mounts
# docker-compose.yml should have:
volumes:
  - ./backend:/app
```

## 📞 Getting Help

If you can't resolve an issue:

1. **Search Documentation**: Check [docs/](../../docs/)
2. **Search Issues**: [GitHub Issues](https://github.com/sbelakho2/Management-Software/issues)
3. **Ask Community**: [GitHub Discussions](https://github.com/sbelakho2/Management-Software/discussions)
4. **Contact Support**: contact@starzmorocco.com

### Providing Information

When reporting issues, include:

- **Description**: Clear description of the problem
- **Steps to Reproduce**: Exact steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**:
  - OS (Linux, macOS, Windows)
  - Python version
  - Node.js version
  - Docker version
  - Kubernetes version (if applicable)
- **Logs**: Relevant log output
- **Screenshots**: If UI-related

### Log Collection

```bash
# Backend logs
tail -f logs/sensei.log

# Frontend logs
# Check browser console

# Docker logs
docker logs sensei-backend

# Kubernetes logs
kubectl logs -n sensei <pod-name> --tail=100
```

---

**Still having issues?** Open an [issue on GitHub](https://github.com/sbelakho2/Management-Software/issues/new) with details.
