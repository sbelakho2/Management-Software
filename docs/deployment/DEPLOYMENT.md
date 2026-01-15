# Kubernetes Deployment Guide

This guide covers deploying the Sensei Manufacturing Management System to a Kubernetes cluster using Helm.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cluster Setup](#cluster-setup)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Post-Installation](#post-installation)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **kubectl** 1.19+: Kubernetes command-line tool
- **Helm** 3.0+: Kubernetes package manager
- **Docker**: For building container images
- **Git**: For cloning the repository

### Cluster Requirements

- Kubernetes cluster 1.19+ (managed or self-hosted)
- Minimum 4 CPU cores and 8GB RAM available
- Storage class supporting dynamic provisioning
- LoadBalancer or NodePort support for external access

### Optional Components

- **cert-manager**: For automatic TLS certificate management
- **NGINX Ingress Controller**: For HTTP/HTTPS routing
- **Prometheus**: For monitoring
- **Grafana**: For dashboards

## Cluster Setup

### 1. Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml

# Verify installation
kubectl get pods -n cert-manager
```

### 2. Install NGINX Ingress Controller

```bash
# Add Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install ingress controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# Verify installation
kubectl get svc -n ingress-nginx
```

### 3. Add Bitnami Repository

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

## Installation

### 1. Build Container Images

```bash
# Backend image
cd backend
docker build -t your-registry/sensei-backend:v1.0.0 .
docker push your-registry/sensei-backend:v1.0.0

# Frontend image
cd ../frontend
docker build -t your-registry/sensei-frontend:v1.0.0 .
docker push your-registry/sensei-frontend:v1.0.0
```

### 2. Create Custom Values File

Create `my-values.yaml`:

```yaml
# Image configuration
image:
  backend:
    repository: your-registry/sensei-backend
    tag: v1.0.0
  frontend:
    repository: your-registry/sensei-frontend
    tag: v1.0.0

# Ingress configuration
ingress:
  enabled: true
  hosts:
    - host: sensei.yourdomain.com
      paths:
        - path: /api
          pathType: Prefix
          backend: backend
        - path: /
          pathType: Prefix
          backend: frontend
  tls:
    - secretName: sensei-tls
      hosts:
        - sensei.yourdomain.com

# PostgreSQL configuration
postgresql:
  auth:
    password: "ChangeMe123!"  # Use strong password in production
    database: sensei
  primary:
    persistence:
      size: 50Gi  # Adjust based on needs

# Redis configuration
redis:
  auth:
    password: "ChangeMe456!"  # Use strong password in production

# MinIO configuration
minio:
  auth:
    rootUser: admin
    rootPassword: "ChangeMe789!"  # Use strong password in production
  persistence:
    size: 100Gi  # Adjust based on needs

# Application configuration
config:
  environment: production
  debug: false
  corsOrigins: "https://sensei.yourdomain.com"
  secretKey: ""  # Will be auto-generated if empty
```

### 3. Install Helm Chart

```bash
# Create namespace
kubectl create namespace sensei

# Install chart
helm install sensei ./k8s/helm/sensei \
  --namespace sensei \
  --values my-values.yaml \
  --timeout 10m

# Watch installation progress
kubectl get pods -n sensei --watch
```

### 4. Verify Installation

```bash
# Check all pods are running
kubectl get pods -n sensei

# Check services
kubectl get svc -n sensei

# Check ingress
kubectl get ingress -n sensei

# View logs
kubectl logs -n sensei -l app.kubernetes.io/component=backend --tail=50
```

## Configuration

### Environment Variables

Key configuration options in `values.yaml`:

```yaml
config:
  environment: production  # production, staging, development
  debug: false             # Enable debug mode
  logLevel: info           # Log level: debug, info, warning, error
  
  features:
    phase2Npi: true        # Enable Phase 2 NPI features
    phase3Production: true # Enable Phase 3 Production features
    smartIngestion: true   # Enable Smart Ingestion OCR
    knowledgePack: true    # Enable Knowledge Pack features
  
  corsOrigins: "https://app.example.com,https://www.example.com"
  
  storage:
    type: s3               # s3 or filesystem
    bucket: sensei-attachments
```

### Resource Limits

Adjust resource allocation based on workload:

```yaml
resources:
  backend:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "2000m"
  
  frontend:
    requests:
      memory: "256Mi"
      cpu: "200m"
    limits:
      memory: "1Gi"
      cpu: "1000m"
```

### Auto-scaling

Configure Horizontal Pod Autoscaler:

```yaml
autoscaling:
  backend:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
  
  frontend:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

### Database Configuration

PostgreSQL settings:

```yaml
postgresql:
  enabled: true
  auth:
    database: sensei
    username: sensei
    password: "SecurePassword"
  
  primary:
    persistence:
      enabled: true
      size: 50Gi
      storageClass: "fast-ssd"  # Use your storage class
    
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"
      limits:
        memory: "8Gi"
        cpu: "4000m"
  
  backup:
    enabled: true
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention: 30  # Keep 30 days
```

## Post-Installation

### 1. Run Database Migrations

```bash
kubectl exec -n sensei -it deployment/sensei-backend -- \
  alembic upgrade head
```

### 2. Create Admin User

```bash
kubectl exec -n sensei -it deployment/sensei-backend -- \
  python -m sensei.cli.user create-admin \
    --email admin@example.com \
    --password AdminPassword123
```

### 3. Initialize Knowledge Base (Optional)

```bash
# Ingest documentation
kubectl exec -n sensei -it deployment/sensei-backend -- \
  python -m sensei.cli.knowledge ingest \
    --url https://example.com/docs

# Generate embeddings
kubectl exec -n sensei -it deployment/sensei-backend -- \
  python -m sensei.cli.knowledge embed
```

### 4. Configure DNS

Point your domain to the Ingress LoadBalancer:

```bash
# Get LoadBalancer IP
kubectl get svc -n ingress-nginx ingress-nginx-controller

# Create DNS A record
# sensei.yourdomain.com -> LoadBalancer IP
```

### 5. Verify TLS Certificate

```bash
# Check certificate status
kubectl get certificate -n sensei

# View certificate details
kubectl describe certificate -n sensei sensei-tls

# If certificate is not ready, check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

## Monitoring & Maintenance

### Health Checks

```bash
# Check backend health
kubectl exec -n sensei deployment/sensei-backend -- \
  curl http://localhost:8000/api/health

# Check frontend health
kubectl exec -n sensei deployment/sensei-frontend -- \
  curl http://localhost:3000/health
```

### View Metrics

```bash
# Get HPA status
kubectl get hpa -n sensei

# View detailed metrics
kubectl top pods -n sensei
kubectl top nodes
```

### Database Backup

```bash
# Trigger manual backup
kubectl create job -n sensei \
  --from=cronjob/sensei-postgres-backup \
  manual-backup-$(date +%Y%m%d-%H%M%S)

# List backups
kubectl exec -n sensei deployment/sensei-backend -- \
  ls -lh /backups/postgresql/
```

### Update Application

```bash
# Build new images
docker build -t your-registry/sensei-backend:v1.1.0 backend/
docker push your-registry/sensei-backend:v1.1.0

# Update values.yaml with new tag
# image.backend.tag: v1.1.0

# Upgrade release
helm upgrade sensei ./k8s/helm/sensei \
  --namespace sensei \
  --values my-values.yaml

# Verify rollout
kubectl rollout status -n sensei deployment/sensei-backend
```

### Scale Application

```bash
# Manual scaling
kubectl scale -n sensei deployment/sensei-backend --replicas=5

# Or update HPA limits in values.yaml and upgrade
```

## Troubleshooting

### Pod Issues

```bash
# Check pod status
kubectl get pods -n sensei

# View pod events
kubectl describe pod -n sensei <pod-name>

# View pod logs
kubectl logs -n sensei <pod-name> --tail=100 --follow

# Access pod shell
kubectl exec -n sensei -it <pod-name> -- /bin/bash
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -n sensei -it deployment/sensei-backend -- \
  python -c "from sensei.core.database import engine; print(engine.url)"

# Check PostgreSQL logs
kubectl logs -n sensei -l app.kubernetes.io/name=postgresql

# Connect to database directly
kubectl exec -n sensei -it statefulset/sensei-postgresql-0 -- \
  psql -U sensei -d sensei
```

### Ingress Issues

```bash
# Check ingress status
kubectl get ingress -n sensei
kubectl describe ingress -n sensei sensei

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Test internal connectivity
kubectl run -n sensei -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://sensei-backend:8000/api/health
```

### Certificate Issues

```bash
# Check certificate status
kubectl get certificate -n sensei
kubectl describe certificate -n sensei sensei-tls

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager

# Check certificate challenge
kubectl get challenge -n sensei
kubectl describe challenge -n sensei <challenge-name>
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n sensei

# View PVC details
kubectl describe pvc -n sensei <pvc-name>

# Check storage class
kubectl get storageclass

# View persistent volumes
kubectl get pv
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -n sensei
kubectl top nodes

# View HPA status
kubectl get hpa -n sensei
kubectl describe hpa -n sensei sensei-backend

# Check for pod evictions
kubectl get events -n sensei --sort-by='.lastTimestamp' | grep Evicted
```

### Reset/Cleanup

```bash
# Delete release (keeps PVCs)
helm uninstall sensei --namespace sensei

# Delete namespace (removes everything including PVCs)
kubectl delete namespace sensei

# Cleanup cert-manager resources
kubectl delete certificate -n sensei --all
kubectl delete secret -n sensei sensei-tls
```

## Production Checklist

- [ ] Strong passwords configured for all services
- [ ] TLS certificates configured and validated
- [ ] DNS records properly configured
- [ ] Resource limits tuned for workload
- [ ] Auto-scaling configured and tested
- [ ] Backup schedule configured
- [ ] Monitoring and alerting set up
- [ ] Network policies enabled
- [ ] Pod security policies enforced
- [ ] RBAC properly configured
- [ ] Secrets rotation policy in place
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security scanning performed

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [NGINX Ingress Documentation](https://kubernetes.github.io/ingress-nginx/)
- [Bitnami Charts](https://github.com/bitnami/charts)
