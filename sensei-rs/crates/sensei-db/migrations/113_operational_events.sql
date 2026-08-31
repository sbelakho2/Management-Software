-- Canonical operational event envelope (fifteenth audit 31-33):
-- bitemporal — occurred_at (when it happened) differs from recorded_at
-- (when we learned it). objects links every object the event touches.
CREATE TABLE IF NOT EXISTS operational_events (
    id            UUID PRIMARY KEY,
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type    VARCHAR(80) NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scope_site_id UUID,
    actor_id      UUID,
    objects       JSONB NOT NULL DEFAULT '[]',
    source_system VARCHAR(50),
    source_id     VARCHAR(100),
    sensitivity   VARCHAR(20) NOT NULL DEFAULT 'internal',
    payload       JSONB NOT NULL DEFAULT '{}',
    sequence      BIGINT NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_op_events_tenant_type ON operational_events (tenant_id, event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_op_events_objects ON operational_events USING GIN (objects);
ALTER TABLE operational_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE operational_events FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON operational_events
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
