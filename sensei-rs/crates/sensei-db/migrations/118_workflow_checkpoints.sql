-- Fifteenth audit items 1-2 (law A11): model workflows are checkpointable
-- and resumable. Every workflow step is a durable checkpoint row; evidence
-- and approvals are separate ledgers. The engine is deliberately small
-- (5-10% of LangGraph's generality): one checkpoints table, one evidence
-- table, one approvals table — no graph machinery.
--
-- Tenant isolation is FAIL-CLOSED like every other tenant-owned table:
-- all workflow writes/reads must run with SET LOCAL app.tenant_id
-- established (the sensei-workflow crate replicates the
-- sensei-services with_tenant_tx pattern).
CREATE TABLE IF NOT EXISTS workflow_checkpoints (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_id  VARCHAR(100) NOT NULL,
    workflow_type VARCHAR(100) NOT NULL,
    step         VARCHAR(100) NOT NULL,
    status       VARCHAR(30) NOT NULL DEFAULT 'pending',
    actor_id     UUID,
    payload      JSONB NOT NULL DEFAULT '{}',
    checkpoint   BIGINT NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, workflow_id, checkpoint)
);
CREATE TABLE IF NOT EXISTS workflow_evidence (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_id  VARCHAR(100) NOT NULL,
    kind         VARCHAR(50) NOT NULL,
    source       VARCHAR(200) NOT NULL,
    captured_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    value        JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS workflow_approvals (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_id  VARCHAR(100) NOT NULL,
    step         VARCHAR(100) NOT NULL,
    required_role VARCHAR(100) NOT NULL,
    rationale    TEXT,
    status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    decided_by   UUID,
    decided_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE workflow_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_checkpoints FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workflow_checkpoints
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
ALTER TABLE workflow_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_evidence FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workflow_evidence
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
ALTER TABLE workflow_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_approvals FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON workflow_approvals
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
