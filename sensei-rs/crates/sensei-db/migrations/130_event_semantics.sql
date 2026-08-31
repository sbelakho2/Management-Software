-- Event envelope semantics (sixteenth audit items 23-24): stream
-- identity + idempotency + supersession. Corrective/superseding events
-- reference what they replace (valid-time semantics).
ALTER TABLE operational_events
    ADD COLUMN IF NOT EXISTS event_schema_version INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS stream_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS stream_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS stream_sequence BIGINT,
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(200),
    ADD COLUMN IF NOT EXISTS supersedes_event_id UUID,
    ADD COLUMN IF NOT EXISTS effective_from TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS effective_to TIMESTAMPTZ;

-- Idempotent source dedupe: a source (system, id) produces one event.
CREATE UNIQUE INDEX IF NOT EXISTS idx_op_events_source
    ON operational_events (tenant_id, source_system, source_id)
    WHERE source_system IS NOT NULL AND source_id IS NOT NULL;

-- Stream ordering: per (tenant, stream_type, stream_id) the sequence is
-- unique.
CREATE UNIQUE INDEX IF NOT EXISTS idx_op_events_stream
    ON operational_events (tenant_id, stream_type, stream_id, stream_sequence)
    WHERE stream_type IS NOT NULL AND stream_id IS NOT NULL;

-- Relational object projection (sixteenth audit item 45): events link
-- MANY objects; JSONB is flexible but slow for multi-hop traversal.
CREATE TABLE IF NOT EXISTS operational_event_objects (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_id    UUID NOT NULL REFERENCES operational_events(id) ON DELETE CASCADE,
    object_type VARCHAR(50) NOT NULL,
    object_id   UUID NOT NULL,
    role        VARCHAR(30)
);
CREATE INDEX IF NOT EXISTS idx_event_objects_object
    ON operational_event_objects (tenant_id, object_type, object_id, event_id);
CREATE INDEX IF NOT EXISTS idx_event_objects_event
    ON operational_event_objects (tenant_id, event_id);
ALTER TABLE operational_event_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE operational_event_objects FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON operational_event_objects
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
