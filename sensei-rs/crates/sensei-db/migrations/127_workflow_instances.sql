-- Sixteenth audit item 48 (optimistic checkpoint concurrency): the
-- checkpoint sequence must NOT be derived from MAX(checkpoint) + 1 (racy
-- under concurrent resume writers). Every workflow has exactly one row
-- here whose current_version is bumped ATOMICALLY by the transition
-- UPSERT (ON CONFLICT ... current_version = current_version + 1) — the
-- checkpoint number in workflow_checkpoints IS that version.
--
-- The CAS form (record_transition_expected) compares current_version
-- before advancing: a stale writer updates 0 rows and the workflow
-- engine fails the transition instead of silently corrupting history.
--
-- Tenant isolation is FAIL-CLOSED like every other tenant-owned table
-- (see migration 118): all reads/writes must run with SET LOCAL
-- app.tenant_id established.
CREATE TABLE IF NOT EXISTS workflow_instances (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_id     VARCHAR(100) NOT NULL,
    current_step    VARCHAR(100) NOT NULL,
    current_version BIGINT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, workflow_id)
);
ALTER TABLE workflow_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_instances FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workflow_instances
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
