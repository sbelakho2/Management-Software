# Quick Start Guide - Local Development

Deploy Sensei locally using Minikube for development and testing.

## Prerequisites

- Docker Desktop or Docker Engine
- Minikube
- kubectl
- Helm 3

## Installation

### 1. Install Required Tools

**macOS (Homebrew)**:
```bash
brew install minikube kubectl helm
```

**Linux**:
```bash
# Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

**Windows (Chocolatey)**:
```powershell
choco install minikube kubernetes-cli kubernetes-helm
```

### 2. Start Minikube

```bash
# Start with sufficient resources
minikube start --cpus=4 --memory=8192 --disk-size=50g

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable storage-provisioner

# Verify cluster
kubectl cluster-info
kubectl get nodes
```

### 3. Build Container Images

Build and load images directly into Minikube:

```bash
# Set Docker to use Minikube's Docker daemon
eval $(minikube docker-env)

# Build backend image
cd backend
docker build -t sensei-backend:dev .

# Build frontend image
cd ../frontend
docker build -t sensei-frontend:dev .

# Verify images
docker images | grep sensei
```

### 4. Add Bitnami Repository

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 5. Create Development Values

Create `dev-values.yaml`:

```yaml
# Use local images
image:
  backend:
    repository: sensei-backend
    tag: dev
    pullPolicy: Never  # Don't try to pull from registry
  frontend:
    repository: sensei-frontend
    tag: dev
    pullPolicy: Never

# Smaller resource requirements for local dev
replicaCount:
  backend: 1
  frontend: 1

resources:
  backend:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"
  frontend:
    requests:
      memory: "128Mi"
      cpu: "50m"
    limits:
      memory: "256Mi"
      cpu: "200m"
  worker:
    requests:
      memory: "256Mi"
      cpu: "100m"
    limits:
      memory: "512Mi"
      cpu: "500m"

# Disable autoscaling for local dev
autoscaling:
  backend:
    enabled: false
  frontend:
    enabled: false

# Smaller storage for local dev
postgresql:
  enabled: true
  auth:
    database: sensei
    username: sensei
    password: sensei-dev
  primary:
    persistence:
      size: 5Gi
    resources:
      requests:
        memory: "256Mi"
        cpu: "100m"
      limits:
        memory: "512Mi"
        cpu: "500m"

redis:
  enabled: true
  auth:
    enabled: false  # Disable auth for simpler local dev
  master:
    persistence:
      size: 1Gi
    resources:
      requests:
        memory: "128Mi"
        cpu: "50m"
      limits:
        memory: "256Mi"
        cpu: "100m"

minio:
  enabled: true
  auth:
    rootUser: admin
    rootPassword: password
  persistence:
    size: 5Gi
  resources:
    requests:
      memory: "128Mi"
      cpu: "50m"
    limits:
      memory: "256Mi"
      cpu: "100m"

# Simple ingress for local dev
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: ""  # Disable cert-manager
  hosts:
    - host: sensei.local
      paths:
        - path: /api
          pathType: Prefix
          backend: backend
        - path: /
          pathType: Prefix
          backend: frontend
  tls: []  # Disable TLS for local dev

# Development configuration
config:
  environment: development
  debug: true
  logLevel: debug
  corsOrigins: "http://sensei.local,http://localhost:3000"

# Disable production features for faster startup
networkPolicy:
  enabled: false

podDisruptionBudget:
  enabled: false
```

### 6. Install Sensei

```bash
# Install the chart
helm install sensei ./k8s/helm/sensei \
  --values dev-values.yaml \
  --timeout 10m

# Watch pods starting
kubectl get pods --watch
```

### 7. Configure Local Access

Add to `/etc/hosts` (or `C:\Windows\System32\drivers\etc\hosts` on Windows):

```bash
echo "$(minikube ip) sensei.local" | sudo tee -a /etc/hosts
```

Or use Minikube tunnel:

```bash
# In a separate terminal, keep this running
minikube tunnel
```

### 8. Initialize Application

```bash
# Run database migrations
kubectl exec -it deployment/sensei-backend -- alembic upgrade head

# Create admin user
kubectl exec -it deployment/sensei-backend -- \
  python -m sensei.cli.user create-admin \
    --email admin@local.dev \
    --password admin123

# Verify backend health
kubectl exec -it deployment/sensei-backend -- \
  curl http://localhost:8000/api/health
```

### 9. Access Application

Open your browser:
- **Application**: http://sensei.local
- **Backend API**: http://sensei.local/api
- **API Docs**: http://sensei.local/api/docs

Or use port forwarding:

```bash
# Frontend
kubectl port-forward svc/sensei-frontend 3000:3000
# Access at http://localhost:3000

# Backend
kubectl port-forward svc/sensei-backend 8000:8000
# Access at http://localhost:8000
```

## Development Workflow

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/sensei-backend

# Frontend logs
kubectl logs -f deployment/sensei-frontend

# All logs
kubectl logs -f -l app.kubernetes.io/name=sensei
```

### Update Code

After making changes:

```bash
# Rebuild image (with minikube docker-env)
eval $(minikube docker-env)
cd backend
docker build -t sensei-backend:dev .

# Restart pods to use new image
kubectl rollout restart deployment/sensei-backend

# Watch rollout
kubectl rollout status deployment/sensei-backend
```

### Database Access

```bash
# Connect to PostgreSQL
kubectl exec -it statefulset/sensei-postgresql-0 -- \
  psql -U sensei -d sensei

# Run migrations
kubectl exec -it deployment/sensei-backend -- \
  alembic upgrade head

# Create migration
kubectl exec -it deployment/sensei-backend -- \
  alembic revision --autogenerate -m "description"
```

### Debug Container

```bash
# Open shell in backend pod
kubectl exec -it deployment/sensei-backend -- /bin/bash

# Open shell in frontend pod
kubectl exec -it deployment/sensei-frontend -- /bin/sh

# Run Python REPL
kubectl exec -it deployment/sensei-backend -- python
```

### Access Services

```bash
# PostgreSQL
kubectl port-forward svc/sensei-postgresql 5432:5432
# Connect: postgresql://sensei:sensei-dev@localhost:5432/sensei

# Redis
kubectl port-forward svc/sensei-redis-master 6379:6379
# Connect: redis://localhost:6379

# MinIO Console
kubectl port-forward svc/sensei-minio 9001:9001
# Access: http://localhost:9001 (admin/password)
```

## Testing

### Run Backend Tests

```bash
kubectl exec -it deployment/sensei-backend -- \
  pytest tests/ -v --cov=sensei
```

### Run Frontend Tests

```bash
kubectl exec -it deployment/sensei-frontend -- \
  npm test
```

## Cleanup

### Restart Everything

```bash
helm upgrade sensei ./k8s/helm/sensei --values dev-values.yaml
```

### Uninstall

```bash
# Remove release
helm uninstall sensei

# Delete PVCs
kubectl delete pvc --all

# Or delete entire namespace
kubectl delete namespace default --cascade=foreground
```

### Stop Minikube

```bash
minikube stop
```

### Delete Cluster

```bash
minikube delete
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check image pull issues
kubectl get events --sort-by=.metadata.creationTimestamp

# Verify images exist in Minikube
eval $(minikube docker-env)
docker images | grep sensei
```

### Cannot Access Application

```bash
# Check ingress
kubectl get ingress
minikube addons enable ingress

# Check /etc/hosts
cat /etc/hosts | grep sensei

# Use port-forward as alternative
kubectl port-forward svc/sensei-frontend 3000:3000
```

### Database Connection Errors

```bash
# Check PostgreSQL status
kubectl get pods -l app.kubernetes.io/name=postgresql

# View PostgreSQL logs
kubectl logs -l app.kubernetes.io/name=postgresql

# Test connection
kubectl exec -it deployment/sensei-backend -- \
  python -c "from sensei.core.database import engine; print(engine.pool.status())"
```

### Out of Resources

```bash
# Check resource usage
kubectl top nodes
kubectl top pods

# Increase Minikube resources
minikube stop
minikube start --cpus=6 --memory=16384

# Or reduce resource requests in dev-values.yaml
```

## Tips

1. **Use Skaffold**: For automated rebuild/redeploy on code changes
2. **Enable Dev Mode**: Set DEBUG=true for hot reloading
3. **Local Storage**: Use host paths for faster development
4. **Mock External Services**: Use in-cluster mocks instead of external APIs
5. **Parallel Builds**: Use BuildKit for faster Docker builds

## Next Steps

- [Full Deployment Guide](DEPLOYMENT.md) for production deployment
- [Architecture Documentation](../docs/architecture/) for system design
- [API Documentation](http://sensei.local/api/docs) for API reference
