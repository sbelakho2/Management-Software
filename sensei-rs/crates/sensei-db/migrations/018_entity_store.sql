-- Generic entity store for persisting domain entities as JSONB.
-- Used by EntityStore<T> for database-backed storage of entities
-- that don't yet have dedicated domain service implementations.
--
-- Each row stores one entity identified by (entity_type, id).
-- The full entity is serialised as JSONB in the `data` column.

CREATE TABLE IF NOT EXISTS entity_store (
    entity_type VARCHAR NOT NULL,
    id UUID NOT NULL,
    data JSONB NOT NULL,
    tenant_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (entity_type, id)
);

CREATE INDEX IF NOT EXISTS idx_entity_store_entity_type ON entity_store (entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_store_tenant_id ON entity_store (tenant_id) WHERE tenant_id IS NOT NULL;
