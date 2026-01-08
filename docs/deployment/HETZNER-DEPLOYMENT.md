# Hetzner Cloud Deployment Guide

Complete guide for deploying Sensei Manufacturing Management System on Hetzner Cloud infrastructure.

## Table of Contents

1. [Why Hetzner Cloud?](#why-hetzner-cloud)
2. [Prerequisites](#prerequisites)
3. [Hetzner Setup](#hetzner-setup)
4. [Kubernetes Cluster Setup](#kubernetes-cluster-setup)
5. [Storage Configuration](#storage-configuration)
6. [Installation](#installation)
7. [Cost Optimization](#cost-optimization)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)

## Why Hetzner Cloud?

Hetzner offers excellent value for European deployments:

- **Cost-Effective**: 50-70% cheaper than AWS/GCP/Azure
- **High Performance**: AMD EPYC CPUs, NVMe SSDs, 20 Gbps network
- **GDPR Compliant**: Data centers in Germany and Finland
- **Simple Pricing**: No hidden costs or complex pricing tiers
- **Excellent Support**: Responsive support team
- **Green Energy**: Powered by renewable energy

### Recommended Configuration

**Small Deployment** (5-10 users):
- 3x CPX21 nodes (3 vCPU, 4GB RAM) - €19.17/month total
- 40GB Block Storage - €1.60/month
- Load Balancer - €5.83/month
- **Total**: ~€27/month (~$30/month)

**Production Deployment** (50+ users):
- 3x CPX31 nodes (4 vCPU, 8GB RAM) - €38.34/month total
- 100GB Block Storage - €4.00/month
- Load Balancer - €5.83/month
- Object Storage (250GB) - €5.00/month
- **Total**: ~€53/month (~$58/month)

**High Availability** (100+ users):
- 5x CPX41 nodes (8 vCPU, 16GB RAM) - €95.85/month total
- 200GB Block Storage - €8.00/month
- Load Balancer - €5.83/month
- Object Storage (1TB) - €20.00/month
- **Total**: ~€130/month (~$142/month)

## Prerequisites

### Required Tools

```bash
# Install Hetzner CLI
brew install hcloud  # macOS
# or
wget https://github.com/hetznercloud/cli/releases/latest/download/hcloud-linux-amd64.tar.gz
tar xzf hcloud-linux-amd64.tar.gz
sudo mv hcloud /usr/local/bin/

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Hetzner Account Setup

1. **Create Account**: Sign up at https://console.hetzner.cloud
2. **Create Project**: Create a new project (e.g., "Sensei Production")
3. **Generate API Token**:
   - Go to Security → API Tokens
   - Create new token with Read & Write permissions
   - Save token securely

```bash
# Set API token
export HCLOUD_TOKEN=your-api-token-here

# Verify access
hcloud context create sensei
hcloud server list
```

## Hetzner Setup

### 1. Create Network

```bash
# Create private network
hcloud network create \
  --name sensei-network \
  --ip-range 10.0.0.0/16

# Create subnet
hcloud network add-subnet sensei-network \
  --network-zone eu-central \
  --type cloud \
  --ip-range 10.0.1.0/24
```

### 2. Create Firewall

```bash
# Create firewall for Kubernetes nodes
hcloud firewall create \
  --name sensei-firewall

# Allow Kubernetes API (port 6443)
hcloud firewall add-rule sensei-firewall \
  --direction in \
  --protocol tcp \
  --port 6443 \
  --source-ips 0.0.0.0/0

# Allow HTTP/HTTPS
hcloud firewall add-rule sensei-firewall \
  --direction in \
  --protocol tcp \
  --port 80 \
  --source-ips 0.0.0.0/0

hcloud firewall add-rule sensei-firewall \
  --direction in \
  --protocol tcp \
  --port 443 \
  --source-ips 0.0.0.0/0

# Allow SSH (restrict to your IP in production)
hcloud firewall add-rule sensei-firewall \
  --direction in \
  --protocol tcp \
  --port 22 \
  --source-ips 0.0.0.0/0

# Allow inter-node communication
hcloud firewall add-rule sensei-firewall \
  --direction in \
  --protocol tcp \
  --port any \
  --source-ips 10.0.0.0/16
```

### 3. Create SSH Key

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "sensei-cluster" -f ~/.ssh/sensei

# Add to Hetzner
hcloud ssh-key create \
  --name sensei-key \
  --public-key-from-file ~/.ssh/sensei.pub
```

## Kubernetes Cluster Setup

### Option 1: Hetzner Managed Kubernetes (Recommended)

Hetzner doesn't offer managed Kubernetes yet, so we'll use k3s for a managed-like experience.

### Option 2: k3s Installation (Recommended for Hetzner)

```bash
# Create master node
hcloud server create \
  --name k8s-master-1 \
  --type cpx31 \
  --image ubuntu-22.04 \
  --ssh-key sensei-key \
  --network sensei-network \
  --firewall sensei-firewall \
  --location nbg1

# Get server IP
MASTER_IP=$(hcloud server ip k8s-master-1)

# Install k3s on master
ssh root@$MASTER_IP << 'EOF'
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --disable traefik \
  --disable servicelb \
  --flannel-backend=wireguard-native \
  --node-taint node-role.kubernetes.io/master=true:NoSchedule" sh -
EOF

# Get k3s token
K3S_TOKEN=$(ssh root@$MASTER_IP "cat /var/lib/rancher/k3s/server/node-token")

# Copy kubeconfig
ssh root@$MASTER_IP "cat /etc/rancher/k3s/k3s.yaml" > ~/.kube/sensei-config
sed -i "s/127.0.0.1/$MASTER_IP/g" ~/.kube/sensei-config
export KUBECONFIG=~/.kube/sensei-config

# Verify master node
kubectl get nodes
```

### Create Worker Nodes

```bash
# Create worker nodes
for i in {1..2}; do
  hcloud server create \
    --name k8s-worker-$i \
    --type cpx31 \
    --image ubuntu-22.04 \
    --ssh-key sensei-key \
    --network sensei-network \
    --firewall sensei-firewall \
    --location nbg1
done

# Install k3s on workers
for i in {1..2}; do
  WORKER_IP=$(hcloud server ip k8s-worker-$i)
  ssh root@$WORKER_IP << EOF
curl -sfL https://get.k3s.io | K3S_URL=https://$MASTER_IP:6443 \
  K3S_TOKEN=$K3S_TOKEN \
  sh -
EOF
done

# Verify cluster
kubectl get nodes
```

### Install Hetzner Cloud Controller Manager

```bash
# Create secret with Hetzner API token
kubectl create secret generic hcloud \
  --namespace kube-system \
  --from-literal=token=$HCLOUD_TOKEN \
  --from-literal=network=sensei-network

# Install CCM
kubectl apply -f https://github.com/hetznercloud/hcloud-cloud-controller-manager/releases/latest/download/ccm.yaml

# Verify
kubectl get pods -n kube-system | grep hcloud
```

## Storage Configuration

### 1. Install CSI Driver for Block Storage

```bash
# Create secret for CSI driver
kubectl create secret generic hcloud-csi \
  --namespace kube-system \
  --from-literal=token=$HCLOUD_TOKEN

# Install CSI driver
kubectl apply -f https://raw.githubusercontent.com/hetznercloud/csi-driver/main/deploy/kubernetes/hcloud-csi.yml

# Verify
kubectl get pods -n kube-system | grep hcloud-csi
kubectl get storageclass
```

### 2. Configure Object Storage (Optional)

For production, use Hetzner Object Storage for attachments:

```bash
# Create Object Storage bucket via Hetzner Console or API
# https://console.hetzner.cloud/projects/<project-id>/object-storage

# Get credentials from Hetzner Console
# - Access Key ID
# - Secret Access Key
# - Endpoint URL (e.g., https://fsn1.your-objectstorage.com)
```

## Installation

### 1. Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/instance=cert-manager \
  -n cert-manager \
  --timeout=300s
```

### 2. Create Let's Encrypt ClusterIssuer

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com  # Change this
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 3. Install NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install with Hetzner Load Balancer support
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."load-balancer\.hetzner\.cloud/name"=sensei-lb \
  --set controller.service.annotations."load-balancer\.hetzner\.cloud/location"=nbg1 \
  --set controller.service.annotations."load-balancer\.hetzner\.cloud/use-private-ip"=false

# Get Load Balancer IP
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

### 4. Configure DNS

```bash
# Get LoadBalancer external IP
LB_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Configure your DNS:"
echo "  A record: sensei.yourdomain.com -> $LB_IP"
```

### 5. Build and Push Container Images

```bash
# Option 1: Use Docker Hub
docker build -t yourusername/sensei-backend:v1.0.0 backend/
docker build -t yourusername/sensei-frontend:v1.0.0 frontend/
docker push yourusername/sensei-backend:v1.0.0
docker push yourusername/sensei-frontend:v1.0.0

# Option 2: Use Hetzner Registry (when available)
# Currently Hetzner doesn't offer a container registry
# Consider using Harbor on Hetzner or Docker Hub
```

### 6. Create Secrets

```bash
# Create namespace
kubectl create namespace sensei

# Create database password
kubectl create secret generic sensei-db-secret \
  --namespace sensei \
  --from-literal=password=$(openssl rand -base64 32)

# Create Redis password
kubectl create secret generic sensei-redis-secret \
  --namespace sensei \
  --from-literal=password=$(openssl rand -base64 32)

# Create application secret key
kubectl create secret generic sensei-app-secret \
  --namespace sensei \
  --from-literal=secret-key=$(openssl rand -base64 64)

# Create S3 credentials (if using Hetzner Object Storage)
kubectl create secret generic sensei-s3-secret \
  --namespace sensei \
  --from-literal=access-key=YOUR_ACCESS_KEY \
  --from-literal=secret-key=YOUR_SECRET_KEY
```

### 7. Install Sensei with Hetzner-Optimized Values

```bash
# Add Bitnami repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Download Helm chart dependencies
cd k8s/helm/sensei
helm dependency build

# Create custom values file
cat > my-hetzner-values.yaml <<EOF
# Image configuration
image:
  backend:
    repository: yourusername/sensei-backend
    tag: v1.0.0
  frontend:
    repository: yourusername/sensei-frontend
    tag: v1.0.0

# Ingress configuration
ingress:
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

# Database configuration
postgresql:
  auth:
    existingSecret: sensei-db-secret
    secretKeys:
      adminPasswordKey: password
      userPasswordKey: password

# Redis configuration
redis:
  auth:
    existingSecret: sensei-redis-secret
    existingSecretPasswordKey: password

# Object Storage configuration (if using Hetzner)
config:
  storage:
    type: s3
    endpoint: https://fsn1.your-objectstorage.com
    bucket: sensei-attachments
    region: eu-central
EOF

# Install Sensei
helm install sensei . \
  --namespace sensei \
  --values values-hetzner.yaml \
  --values my-hetzner-values.yaml \
  --timeout 10m

# Watch installation
kubectl get pods -n sensei --watch
```

### 8. Initialize Application

```bash
# Run database migrations
kubectl exec -n sensei -it deployment/sensei-backend -- \
  alembic upgrade head

# Create admin user
kubectl exec -n sensei -it deployment/sensei-backend -- \
  python -m sensei.cli.user create-admin \
    --email admin@yourdomain.com \
    --password YourSecurePassword123

# Verify application
curl https://sensei.yourdomain.com/api/health
```

## Cost Optimization

### 1. Right-Size Your Deployment

```bash
# Monitor resource usage
kubectl top nodes
kubectl top pods -n sensei

# Adjust resources in values file based on actual usage
```

### 2. Use Spot Instances (When Available)

Hetzner doesn't currently offer spot instances, but keep an eye on:
- Reserved instances (if they introduce them)
- Volume pricing tiers
- Traffic pricing (free up to 20TB/month)

### 3. Storage Optimization

```bash
# Use Hetzner Block Storage instead of local storage
# Snapshots cost €0.0119/GB/month - cheaper than running larger volumes

# For object storage:
# - First 1TB: €0.02/GB/month
# - Next 49TB: €0.015/GB/month
# - Over 50TB: €0.01/GB/month
```

### 4. Traffic Optimization

```bash
# Enable gzip compression in Ingress
kubectl patch configmap ingress-nginx-controller \
  -n ingress-nginx \
  --type merge \
  -p '{"data":{"use-gzip":"true","gzip-level":"6"}}'

# Use CloudFlare for CDN (free tier available)
# Configure CloudFlare DNS proxy for static assets
```

### 5. Autoscaling Configuration

```yaml
# Adjust HPA targets for cost optimization
autoscaling:
  backend:
    minReplicas: 1  # Scale down to 1 during off-hours
    maxReplicas: 4
    targetCPUUtilizationPercentage: 80  # Higher threshold = fewer replicas
```

## Monitoring & Maintenance

### Install Monitoring Stack (Optional)

```bash
# Install kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=hcloud-volumes \
  --set prometheus.prometheusSpec.retention=7d \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.storageClassName=hcloud-volumes

# Access Grafana
kubectl port-forward -n monitoring svc/kube-prometheus-grafana 3000:80
# Default credentials: admin / prom-operator
```

### Regular Maintenance Tasks

```bash
# 1. Update cluster nodes (monthly)
# SSH to each node and update
ssh root@node-ip "apt update && apt upgrade -y && reboot"

# 2. Update Kubernetes components (quarterly)
# Update k3s version
ssh root@$MASTER_IP "curl -sfL https://get.k3s.io | sh -"

# 3. Backup databases (automated via CronJob)
kubectl get cronjobs -n sensei

# 4. Monitor costs via Hetzner API
hcloud server list
hcloud volume list
hcloud load-balancer list

# 5. Review resource usage and adjust
kubectl top nodes
kubectl describe node <node-name>
```

### Backup Strategy

```bash
# PostgreSQL backups to Hetzner Object Storage
# Already configured in Helm chart

# Verify backups
kubectl get cronjobs -n sensei
kubectl logs -n sensei job/sensei-postgres-backup-<timestamp>

# Manual backup
kubectl create job -n sensei \
  --from=cronjob/sensei-postgres-backup \
  manual-backup-$(date +%Y%m%d-%H%M%S)

# Restore from backup
# 1. List available backups
kubectl exec -n sensei deployment/sensei-backend -- \
  aws s3 ls s3://backups/postgresql/ --endpoint-url=https://your-endpoint

# 2. Restore specific backup
kubectl exec -n sensei statefulset/sensei-postgresql-0 -- \
  pg_restore -U sensei -d sensei /path/to/backup.dump
```

## Troubleshooting

### Node Issues

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# SSH to node
hcloud server ssh k8s-master-1

# Check k3s service
systemctl status k3s
journalctl -u k3s -f
```

### Storage Issues

```bash
# Check CSI driver
kubectl get pods -n kube-system | grep hcloud-csi
kubectl logs -n kube-system <csi-pod-name>

# Check volumes
hcloud volume list
kubectl get pv
kubectl get pvc -n sensei
```

### Load Balancer Issues

```bash
# Check Load Balancer status
hcloud load-balancer list
hcloud load-balancer describe sensei-lb

# Check service
kubectl get svc -n ingress-nginx
kubectl describe svc -n ingress-nginx ingress-nginx-controller
```

### Networking Issues

```bash
# Check network
hcloud network list
hcloud network describe sensei-network

# Test connectivity between nodes
kubectl run test-pod --image=busybox --rm -it -- /bin/sh
# Inside pod:
# ping 10.0.1.2
# nslookup kubernetes.default
```

### Application Issues

```bash
# Check pod status
kubectl get pods -n sensei
kubectl describe pod -n sensei <pod-name>

# Check logs
kubectl logs -n sensei <pod-name> --tail=100 --follow

# Check ingress
kubectl get ingress -n sensei
kubectl describe ingress -n sensei sensei

# Test internal connectivity
kubectl run -n sensei -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://sensei-backend:8000/api/health
```

## Performance Tuning

### 1. Optimize PostgreSQL for Hetzner NVMe

```yaml
postgresql:
  primary:
    extendedConfiguration: |
      # Optimized for NVMe SSDs
      shared_buffers = 2GB
      effective_cache_size = 6GB
      maintenance_work_mem = 512MB
      checkpoint_completion_target = 0.9
      wal_buffers = 16MB
      default_statistics_target = 100
      random_page_cost = 1.1  # Lower for NVMe
      effective_io_concurrency = 200  # Higher for NVMe
      work_mem = 16MB
      min_wal_size = 2GB
      max_wal_size = 8GB
      max_worker_processes = 4
      max_parallel_workers_per_gather = 2
      max_parallel_workers = 4
```

### 2. Network Optimization

```bash
# Enable BBR congestion control on nodes
ssh root@node-ip << 'EOF'
echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
sysctl -p
EOF
```

### 3. Monitoring Queries

```sql
-- Check slow queries
SELECT
  calls,
  mean_exec_time,
  max_exec_time,
  query
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## Next Steps

1. **Set up monitoring**: Install Prometheus and Grafana
2. **Configure alerts**: Set up PagerDuty/Slack notifications
3. **Implement CI/CD**: Use GitHub Actions with Hetzner
4. **Security hardening**: Enable Pod Security Standards
5. **Documentation**: Document runbooks for common operations
6. **Disaster recovery**: Test backup restoration procedures
7. **Load testing**: Verify performance under expected load

## Hetzner-Specific Resources

- **Documentation**: https://docs.hetzner.com/cloud/
- **API Reference**: https://docs.hetzner.cloud/
- **Community Forum**: https://community.hetzner.com/
- **Status Page**: https://status.hetzner.com/
- **Support**: https://console.hetzner.cloud/support/tickets

## Cost Calculator

Use the Hetzner Cloud Pricing Calculator:
https://www.hetzner.com/cloud#pricing

Example calculation for production setup:
- 3x CPX31 (4 vCPU, 8GB): €12.78 each = €38.34/month
- 100GB Block Storage: €4.00/month
- Load Balancer: €5.83/month
- 500GB Object Storage: €10.00/month
- **Total**: ~€58/month

Compare to AWS equivalent: ~$350/month (6x more expensive)
