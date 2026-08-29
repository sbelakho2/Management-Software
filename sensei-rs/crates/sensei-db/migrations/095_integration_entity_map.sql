-- Legacy-system interoperability (entity map): deterministic, idempotent
-- mapping between the legacy systems' records and Sensei's canonical
-- entities. A legacy record (system + type + legacy id) maps to EXACTLY
-- one Sensei entity — re-importing the same legacy id never duplicates.
CREATE TABLE IF NOT EXISTS integration_entity_map (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id         UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    legacy_system     VARCHAR(50) NOT NULL,   -- 'starzerp' | 'crm_v2'
    legacy_entity     VARCHAR(50) NOT NULL,   -- 'article', 'customer', 'lead', 'quote', ...
    legacy_id         VARCHAR(100) NOT NULL,  -- the legacy row's string id
    sensei_entity     VARCHAR(50) NOT NULL,   -- 'product', 'account', 'contact', ...
    sensei_id         UUID NOT NULL,
    imported_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_payload_hash VARCHAR(64),
    UNIQUE (tenant_id, legacy_system, legacy_entity, legacy_id)
);
CREATE INDEX IF NOT EXISTS idx_integration_map_sensei
    ON integration_entity_map (tenant_id, sensei_entity, sensei_id);
