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
