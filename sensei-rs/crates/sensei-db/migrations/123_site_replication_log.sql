-- Site-edge replication (fifteenth audit 29/A15): sites enqueue
-- AUTHORIZED state projections; corporate pulls them. The log is
-- durable and per-tenant; site operations never depend on the corporate
-- link.
CREATE TABLE IF NOT EXISTS site_replication_log (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id       UUID,
    entity_type   VARCHAR(50) NOT NULL,
    entity_id     UUID,
    projection    JSONB NOT NULL DEFAULT '{}',
    source_event_id VARCHAR(100),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pulled_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_rep_log_pending ON site_replication_log (tenant_id, pulled_at) WHERE pulled_at IS NULL;
ALTER TABLE site_replication_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_replication_log FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON site_replication_log
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
