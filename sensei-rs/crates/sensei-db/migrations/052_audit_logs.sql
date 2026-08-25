-- Durable audit log.
--
-- Append-only log of state-changing HTTP requests (POST / PUT / PATCH /
-- DELETE). Written by the audit middleware; rows are never updated or
-- deleted. In dev mode (no database pool) the middleware falls back to an
-- in-memory ring buffer instead.
--
-- NOTE: migration 049 (which was to create this table) never landed; the
-- audit_logs table is created here instead, per the production-readiness
-- overhaul coordination.

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id UUID,
    actor_id UUID,
    session_id TEXT,
    request_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    result TEXT,
    source_ip TEXT,
    details JSONB
);

-- The audit-logs API and compliance queries filter by tenant and time.
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_timestamp
    ON audit_logs (tenant_id, timestamp);
