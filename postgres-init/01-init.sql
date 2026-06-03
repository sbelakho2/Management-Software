-- Initial database setup for Sensei OS

-- Required extensions
CREATE EXTENSION IF NOT EXISTS vector;         -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;       -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- Trigram similarity for fuzzy search (gin_trgm_ops)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Query performance monitoring

-- Performance tuning for connection-heavy workloads
-- These settings are optimized for 4 gunicorn workers × 30 pool connections
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '1536MB';
ALTER SYSTEM SET work_mem = '8MB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET random_page_cost = 1.1;       -- SSD-optimized
ALTER SYSTEM SET effective_io_concurrency = 200; -- SSD-optimized
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET default_statistics_target = 200;
ALTER SYSTEM SET idle_in_transaction_session_timeout = '30s';
ALTER SYSTEM SET statement_timeout = '30s';
ALTER SYSTEM SET lock_timeout = '10s';
ALTER SYSTEM SET log_min_duration_statement = 500; -- Log slow queries > 500ms
ALTER SYSTEM SET jit = on;
SELECT pg_reload_conf();

-- ============================================================================
-- entity_store — Generic JSONB persistence for EntityStore<T>
-- ============================================================================
-- Used by sensei-api's EntityStore<T> to persist any entity type as JSONB.
-- The composite PK (entity_type, id) allows multiple entity types to coexist
-- in a single table while maintaining efficient lookups.
-- ============================================================================

CREATE TABLE IF NOT EXISTS entity_store (
    id          UUID NOT NULL,
    tenant_id   UUID NOT NULL,
    entity_type VARCHAR(255) NOT NULL,
    data        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, entity_type)
);

-- Tenant-scoped lookups (all queries filter by tenant_id)
CREATE INDEX IF NOT EXISTS idx_entity_store_tenant_type
    ON entity_store (tenant_id, entity_type);

-- GIN index for JSONB queries (filtering by data->>'field')
CREATE INDEX IF NOT EXISTS idx_entity_store_data_gin
    ON entity_store USING GIN (data jsonb_path_ops);

-- Lookup by updated_at for sync/incremental-load queries
CREATE INDEX IF NOT EXISTS idx_entity_store_updated_at
    ON entity_store (updated_at);

-- Auto-update updated_at on modification
CREATE OR REPLACE FUNCTION update_entity_store_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_entity_store_updated_at ON entity_store;
CREATE TRIGGER trg_entity_store_updated_at
    BEFORE UPDATE ON entity_store
    FOR EACH ROW
    EXECUTE FUNCTION update_entity_store_updated_at();
