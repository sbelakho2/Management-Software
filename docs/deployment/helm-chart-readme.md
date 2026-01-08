# Sensei - Manufacturing Management System

Helm chart for deploying Sensei on Kubernetes with PostgreSQL, Redis, and MinIO.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure
- cert-manager (for automatic TLS certificate management)
- Ingress controller (NGINX recommended)

## Installing the Chart

### Add Bitnami repository

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Install cert-manager (if not already installed)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml
```

### Install NGINX Ingress Controller (if not already installed)

```bash
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

### Install Sensei

```bash
# Install with default values
helm install sensei ./k8s/helm/sensei

# Install with custom values
helm install sensei ./k8s/helm/sensei -f my-values.yaml

# Install to specific namespace
helm install sensei ./k8s/helm/sensei --namespace sensei --create-namespace
```

## Configuration

The following table lists the main configurable parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount.backend` | Number of backend replicas | `2` |
| `replicaCount.frontend` | Number of frontend replicas | `2` |
| `image.backend.repository` | Backend image repository | `sensei-backend` |
| `image.backend.tag` | Backend image tag | `Chart.appVersion` |
| `image.frontend.repository` | Frontend image repository | `sensei-frontend` |
| `image.frontend.tag` | Frontend image tag | `Chart.appVersion` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.hosts[0].host` | Hostname for ingress | `sensei.example.com` |
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.database` | PostgreSQL database name | `sensei` |
| `redis.enabled` | Enable Redis | `true` |
| `minio.enabled` | Enable MinIO | `true` |

## Upgrading

```bash
helm upgrade sensei ./k8s/helm/sensei

# Upgrade with new values
helm upgrade sensei ./k8s/helm/sensei -f my-values.yaml
```

## Uninstalling

```bash
helm uninstall sensei

# If installed in a specific namespace
helm uninstall sensei --namespace sensei
```

## Post-Installation Steps

### 1. Run Database Migrations

```bash
kubectl exec -it deployment/sensei-backend -- alembic upgrade head
```

### 2. Create Admin User

```bash
kubectl exec -it deployment/sensei-backend -- python -m sensei.cli.user create-admin \
  --email admin@example.com \
  --password YourSecurePassword
```

### 3. Access the Application

Get the application URL:

```bash
# If using Ingress
echo https://$(kubectl get ingress sensei -o jsonpath='{.spec.rules[0].host}')

# If using NodePort
export NODE_PORT=$(kubectl get --namespace default -o jsonpath="{.spec.ports[0].nodePort}" services sensei-frontend)
export NODE_IP=$(kubectl get nodes --namespace default -o jsonpath="{.items[0].status.addresses[0].address}")
echo http://$NODE_IP:$NODE_PORT

# If using port-forward
kubectl port-forward svc/sensei-frontend 3000:3000
# Access at http://localhost:3000
```

## Architecture

The chart deploys the following components:

- **Backend**: FastAPI application (2+ replicas with HPA)
- **Frontend**: Next.js application (2+ replicas with HPA)
- **Worker**: Background task processor (1 replica)
- **PostgreSQL**: Primary database with pgvector extension (Bitnami chart)
- **Redis**: Cache and session store (Bitnami chart)
- **MinIO**: S3-compatible object storage

## Security

- All containers run as non-root users
- Network policies restrict inter-pod communication
- Secrets are managed via Kubernetes Secrets
- TLS certificates auto-provisioned via cert-manager
- Pod Security Policies enforce security standards

## Monitoring

The chart exposes Prometheus metrics on:
- Backend: `/metrics`
- Frontend: `/metrics` (if enabled)

## High Availability

- Multiple replicas for backend and frontend
- Pod anti-affinity rules spread pods across nodes
- Pod Disruption Budgets ensure minimum availability
- Horizontal Pod Autoscaler for dynamic scaling
- Database backups configured via CronJob

## Storage

- PostgreSQL: 20Gi persistent volume
- Redis: 8Gi persistent volume
- MinIO: 50Gi persistent volume
- Uploads: 10Gi persistent volume (ReadWriteMany)

## Backup and Recovery

### Database Backups

Automated backups are configured via CronJob to S3-compatible storage:

```bash
# Trigger manual backup
kubectl create job --from=cronjob/sensei-postgres-backup manual-backup-$(date +%Y%m%d-%H%M%S)
```

### Restore from Backup

```bash
# List available backups
kubectl exec -it deployment/sensei-backend -- aws s3 ls s3://backups/postgresql/

# Restore specific backup
kubectl exec -it deployment/sensei-backend -- pg_restore -d sensei /path/to/backup.dump
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/name=sensei
```

### View logs

```bash
# Backend logs
kubectl logs -l app.kubernetes.io/component=backend --tail=100

# Frontend logs
kubectl logs -l app.kubernetes.io/component=frontend --tail=100

# Worker logs
kubectl logs -l app.kubernetes.io/component=worker --tail=100
```

### Database connection issues

```bash
# Test database connectivity
kubectl exec -it deployment/sensei-backend -- python -c "from sensei.core.database import engine; print(engine.url)"

# Check PostgreSQL status
kubectl get pods -l app.kubernetes.io/name=postgresql
```

### Ingress issues

```bash
# Check ingress configuration
kubectl describe ingress sensei

# Check cert-manager certificate status
kubectl get certificate
kubectl describe certificate sensei-tls
```

## Development

### Local Testing with Minikube

```bash
# Start minikube
minikube start --cpus=4 --memory=8192

# Enable ingress addon
minikube addons enable ingress

# Install the chart
helm install sensei ./k8s/helm/sensei --set ingress.hosts[0].host=sensei.local

# Add to /etc/hosts
echo "$(minikube ip) sensei.local" | sudo tee -a /etc/hosts

# Access application
open http://sensei.local
```

### Validating the Chart

```bash
# Lint the chart
helm lint ./k8s/helm/sensei

# Dry run installation
helm install sensei ./k8s/helm/sensei --dry-run --debug

# Template rendering
helm template sensei ./k8s/helm/sensei > rendered.yaml
```

## License

Copyright © 2024 Sensei Manufacturing Management System
