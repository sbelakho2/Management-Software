-- Organizational memory (fifteenth audit 42-47): memory lives at
-- personal / role / process / site / corporate tiers. Promotion between
-- tiers is DETERMINISTIC or reviewed — a model can propose, never
-- unilaterally promote. Memory is attached to the ROLE SLOT / process,
-- never deleted by an employee departure.
CREATE TABLE IF NOT EXISTS organizational_memory (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tier         VARCHAR(20) NOT NULL
                 CHECK (tier IN ('personal','role','process','site','corporate')),
    slot_id      UUID,               -- role slot for role-tier memory
    process      VARCHAR(100),       -- process-tier anchor
    kind         VARCHAR(50) NOT NULL, -- observation | lesson | countermeasure | exception
    status       VARCHAR(20) NOT NULL DEFAULT 'observation'
                 CHECK (status IN ('observation','repeated','verified','proposed','approved')),
    content      TEXT NOT NULL,
    context_signature JSONB NOT NULL DEFAULT '{}',
    confidence   DOUBLE PRECISION,
    source_problem_id UUID,
    occurrence_count INT NOT NULL DEFAULT 1,
    created_by   UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_org_memory_tier ON organizational_memory (tenant_id, tier, status);
ALTER TABLE organizational_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizational_memory FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON organizational_memory
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
