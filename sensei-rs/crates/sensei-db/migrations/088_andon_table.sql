-- Andons table (missing from the chain — created here so a FRESH database
-- survives the entire migration sequence; 070/079/075/082 reference it).
--
-- NOTE: on already-deployed databases this table was never created by the
-- migration chain either (the ops DB service INSERT would fail at runtime);
-- this migration heals both fresh and existing databases.
CREATE TABLE IF NOT EXISTS andons (
    id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                 UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    andon_number              VARCHAR(50) NOT NULL,
    work_center_id            UUID NOT NULL,
    issue_type                VARCHAR(50) NOT NULL,
    severity                  VARCHAR(20) NOT NULL,
    description               TEXT,
    status                    VARCHAR(30) NOT NULL DEFAULT 'active'
                              CHECK (status IN ('active', 'acknowledged', 'resolved', 'voided')),
    raised_by                 UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_by               UUID REFERENCES users(id) ON DELETE SET NULL,
    resolution                TEXT,
    response_time_seconds     BIGINT,
    resolution_time_seconds   BIGINT,
    restart_authorized_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    restart_authorized_at     TIMESTAMPTZ,
    escalated_at              TIMESTAMPTZ,
    escalated_to              VARCHAR(100),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at           TIMESTAMPTZ,
    resolved_at               TIMESTAMPTZ,
    UNIQUE (tenant_id, andon_number)
);

CREATE INDEX IF NOT EXISTS idx_andons_tenant_status
    ON andons (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_andons_work_center
    ON andons (tenant_id, work_center_id);

-- Isolation established by the CREATING migration (item 8): 070/079 run
-- BEFORE this table exists on a fresh chain and skip it — the table must
-- not remain without RLS. Andons are critical-safety records: fail-closed
-- policy (missing tenant context = DENY), FORCED for the owner too.
ALTER TABLE andons ENABLE ROW LEVEL SECURITY;
ALTER TABLE andons FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON andons;
CREATE POLICY tenant_isolation ON andons
    USING (
        tenant_id = current_setting('app.tenant_id', true)::uuid
    );
