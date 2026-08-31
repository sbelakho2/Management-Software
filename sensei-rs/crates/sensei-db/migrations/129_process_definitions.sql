-- Versioned process definitions (sixteenth audit item 46): the expected
-- path is DATA, not a hardcoded Rust array. Conformance compares against
-- the process revision applicable AT THE EVENT TIME.
CREATE TABLE IF NOT EXISTS process_definitions (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    process_id       VARCHAR(100) NOT NULL,
    revision         BIGINT NOT NULL DEFAULT 1,
    applicable_from  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    states           JSONB NOT NULL DEFAULT '[]',   -- ordered state list
    allowed_transitions JSONB NOT NULL DEFAULT '[]', -- [[from,to],...]
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, process_id, revision)
);
ALTER TABLE process_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE process_definitions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON process_definitions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
