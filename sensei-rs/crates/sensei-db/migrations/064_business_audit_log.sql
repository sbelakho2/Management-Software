-- Business audit / outbox rows: critical accounting mutations write an
-- audit record in the SAME transaction as the business state, so the
-- financial trail is committed atomically with the mutation (no detached
-- spawn, no lost audit rows on crash between commit and telemetry write).
CREATE TABLE IF NOT EXISTS business_audit_log (
    id          UUID PRIMARY KEY,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    actor_id    UUID NOT NULL,
    action      VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id   UUID NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_business_audit_tenant_entity
    ON business_audit_log (tenant_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_business_audit_tenant_created
    ON business_audit_log (tenant_id, created_at DESC);
