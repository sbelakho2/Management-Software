-- Typed attachment metadata (replaces the generic EntityStore for
-- attachments): tenant-scoped, no cross-replica cache semantics.
CREATE TABLE IF NOT EXISTS attachments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream',
    file_size BIGINT NOT NULL DEFAULT 0,
    storage_path TEXT NOT NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_attachments_tenant_entity ON attachments (tenant_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attachments_tenant_created ON attachments (tenant_id, created_at DESC);
