-- Tenant-scoped entity store keying.
--
-- The generic entity_store table must use (tenant_id, entity_type, id) as
-- its isolation key so that one tenant can never read or overwrite another
-- tenant's rows (migration 018 originally keyed by (entity_type, id) with a
-- nullable tenant_id).
--
-- This migration:
--   1. Removes legacy rows that carry no tenant (they cannot be attributed
--      to any tenant and would be invisible to every tenant-scoped query;
--      the project has never been deployed, so no real data is lost).
--   2. Makes tenant_id NOT NULL.
--   3. Drops the old (entity_type, id) primary key and recreates it as
--      (tenant_id, entity_type, id) — correct for both fresh databases and
--      databases that already ran migration 018.
--   4. Adds the (tenant_id, entity_type, created_at) index used by the
--      paginated list path.

-- Legacy rows written before tenant keying cannot be attributed to a
-- tenant; keeping them would violate NOT NULL and leave unisolated data.
DELETE FROM entity_store WHERE tenant_id IS NULL;

ALTER TABLE entity_store ALTER COLUMN tenant_id SET NOT NULL;

-- The primary key created by migration 018 was unnamed, so PostgreSQL
-- named it `entity_store_pkey` by default. Drop it if present and recreate
-- with the tenant as the leading key column.
ALTER TABLE entity_store DROP CONSTRAINT IF EXISTS entity_store_pkey;
ALTER TABLE entity_store
    ADD CONSTRAINT entity_store_pkey PRIMARY KEY (tenant_id, entity_type, id);

-- Common query pattern: list a tenant's entities of a type ordered by
-- creation time (list_paginated).
CREATE INDEX IF NOT EXISTS idx_entity_store_tenant_type_created
    ON entity_store (tenant_id, entity_type, created_at);
