# Helm Chart Dependencies

This Helm chart depends on Bitnami charts for PostgreSQL and Redis. These dependencies must be downloaded before installation.

## Downloading Dependencies

Before installing the chart, download the required dependencies:

```bash
cd k8s/helm/sensei
helm dependency build
```

This will download:
- PostgreSQL 15.5.0 from Bitnami
- Redis 19.0.0 from Bitnami

The charts will be stored in the `charts/` directory.

## Alternative: Update Dependencies

To update to the latest versions of dependencies:

```bash
cd k8s/helm/sensei
helm dependency update
```

## Verifying Dependencies

Check that dependencies are available:

```bash
ls -l charts/
# Should show:
# postgresql-15.5.0.tgz
# redis-19.0.0.tgz
```

## Without Dependencies

If you want to use external PostgreSQL/Redis instead:

```yaml
# In your values.yaml or via --set
postgresql:
  enabled: false

redis:
  enabled: false

# Configure external connections
config:
  database:
    external: true
    host: your-postgres.example.com
    port: 5432
    database: sensei
    username: sensei
    password: "password"
  
  redis:
    external: true
    host: your-redis.example.com
    port: 6379
    password: "password"
```
