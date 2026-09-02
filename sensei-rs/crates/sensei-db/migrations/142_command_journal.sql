-- Durable command/idempotency journal (eighteenth audit P1-14): the
-- bounded RAM replay map is a PERFORMANCE cache — it may forget. This
-- table is the SYSTEM OF RECORD for idempotent tool executions: a
-- retried mutating tool with the same execution key must replay the
-- journaled result even after the RAM entry was evicted.
CREATE TABLE IF NOT EXISTS command_journal (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    execution_key VARCHAR(200) NOT NULL,
    tool_name     VARCHAR(100) NOT NULL,
    result        JSONB NOT NULL,
    executed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, execution_key)
);
CREATE INDEX IF NOT EXISTS idx_command_journal_key
    ON command_journal (tenant_id, execution_key);
ALTER TABLE command_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE command_journal FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON command_journal
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
