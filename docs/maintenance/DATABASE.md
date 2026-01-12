# Database Maintenance Guide

This document describes maintenance procedures for the Sensei OS PostgreSQL database.

## Overview

Sensei OS uses PostgreSQL 16 as its primary relational database. For high-growth tables, we use native table partitioning to ensure long-term performance and manageable maintenance.

## Table Partitioning

### Implementation
We use **Range Partitioning** on the `created_at` timestamp for high-volume tables:
- `audit_logs`
- `condition_readings`

### Benefits
- **Query Performance**: PostgreSQL can prune entire partitions that don't match the query range.
- **Data Retention**: Dropping old data is as simple as dropping a partition (much faster than `DELETE`).
- **Vacuum Efficiency**: VACUUM operations work on individual partitions.

### Managing Partitions
Partitions are currently managed manually or via migration scripts. In production, we recommend using `pg_partman` for automated partition creation and maintenance.

Example of creating a new partition for `audit_logs`:
```sql
CREATE TABLE audit_logs_y2026m02 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

## Backup and Recovery

### Automated Backups
The system includes a `database_backup.py` service that integrates with S3/MinIO.
- **Daily Full Backups**: Automated pg_dump to S3.
- **RPO (Recovery Point Objective)**: 24 hours.
- **RTO (Recovery Time Objective)**: 4 hours.

### Manual Backup
To perform a manual backup from within the Kubernetes cluster:
```bash
kubectl exec -it <postgres-pod> -- pg_dump -U sensei sensei_db > backup.sql
```

### Restoration Procedure
1. Ensure the database is empty or drop existing tables.
2. Restore from the SQL dump:
```bash
psql -U sensei -d sensei_db < backup.sql
```

## Performance Monitoring

### Slow Query Log
Monitor `pg_stat_statements` to identify slow queries that need optimization or new indexes.

### Vacuuming
Ensure `autovacuum` is enabled and tuned for the workload, especially for partitioned tables.

## Index Maintenance
Reindex tables periodically if bloat is detected, particularly on tables with high update/delete frequency.
