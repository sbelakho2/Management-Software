-- Durable audit log.
--
-- Append-only log of state-changing HTTP requests (POST / PUT / PATCH /
-- DELETE). Written by the audit middleware; rows are never updated or
-- deleted. In dev mode (no database pool) the middleware falls back to an
-- in-memory ring buffer instead.
--
-- NOTE: migration 001 already creates the base audit_logs table; this
-- migration RECONCILES it with the production middleware contract
-- (occurred_at, actor, session, request, result, source_ip) instead of
-- attempting a duplicate CREATE (which would silently no-op and leave the
-- middleware INSERT broken).

-- Reconcile the base table with the middleware contract — additive and
-- idempotent so the migration chain succeeds on a fresh database AND on a
-- database that already ran the old chain.
ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS actor_id UUID,
    ADD COLUMN IF NOT EXISTS session_id TEXT,
    ADD COLUMN IF NOT EXISTS request_id TEXT,
    ADD COLUMN IF NOT EXISTS result TEXT,
    ADD COLUMN IF NOT EXISTS source_ip TEXT,
    ADD COLUMN IF NOT EXISTS tenant_id UUID;

-- The middleware writes resource_id as TEXT (path/id strings) — align the
-- base schema with the runtime contract.
ALTER TABLE audit_logs ALTER COLUMN resource_id TYPE TEXT USING resource_id::text;

-- The audit-logs API and compliance queries filter by tenant and time.
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_timestamp
    ON audit_logs (tenant_id, occurred_at);
