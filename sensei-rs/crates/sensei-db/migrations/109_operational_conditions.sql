-- OperationalCondition — the nervous system connecting every abnormality
-- surface (thirteenth audit): Andon, NCR, risk, maintenance, supplier
-- signal, sales-flow warning, integration conflict, A3. The user does not
-- care which module owns the abnormality; one condition acquires
-- perspectives and one recurrence signature prevents the same underlying
-- condition from spawning a new ticket every time it resurfaces.
CREATE TABLE IF NOT EXISTS operational_conditions (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id             UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    condition_number      VARCHAR(50) NOT NULL,
    scope_site_id         UUID,
    scope_value_stream_id UUID,
    scope_work_center_id  UUID,
    scope_shift_id        UUID,
    -- subject: customer | order | product | work_order | operation |
    --          equipment | supplier | material | process | integration
    subject_type          VARCHAR(30) NOT NULL,
    subject_id            UUID,
    -- expected_condition: {reference_type, reference_id, version,
    --                      expected_value}
    expected_condition    JSONB NOT NULL DEFAULT '{}',
    -- observed_condition: {actual_value, observed_at, source}
    observed_condition    JSONB NOT NULL DEFAULT '{}',
    -- gap: {magnitude, direction, persistence}
    gap                   JSONB NOT NULL DEFAULT '{}',
    -- risk: {customer, quality, safety, flow, cost, people} — 0..1
    risk                  JSONB NOT NULL DEFAULT '{}',
    status                VARCHAR(20) NOT NULL DEFAULT 'open'
                          CHECK (status IN ('open', 'responding', 'contained',
                                            'investigating', 'resolved', 'closed')),
    help_required         BOOLEAN NOT NULL DEFAULT FALSE,
    containment_required  BOOLEAN NOT NULL DEFAULT FALSE,
    expertise_required    VARCHAR(100),
    owner_id              UUID REFERENCES users(id) ON DELETE SET NULL,
    response_due_at       TIMESTAMPTZ,
    -- learning: {recurrence_signature, recurrence_count,
    --            problem_solving_id, experiment_id, verification_id,
    --            standardization_id}
    learning              JSONB NOT NULL DEFAULT '{}',
    -- The authoritative source event (andon, ncr, ...) that opened it.
    source_entity_type    VARCHAR(50),
    source_entity_id      UUID,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, condition_number)
);
CREATE INDEX IF NOT EXISTS idx_opcond_tenant_status
    ON operational_conditions (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_opcond_work_center
    ON operational_conditions (tenant_id, scope_work_center_id);
CREATE INDEX IF NOT EXISTS idx_opcond_signature
    ON operational_conditions (tenant_id, (learning ->> 'recurrence_signature'));

ALTER TABLE operational_conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE operational_conditions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON operational_conditions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
