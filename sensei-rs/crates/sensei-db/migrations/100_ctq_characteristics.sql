-- CTQ characteristics as a REAL table (item 38): the station quality
-- check must be bound to the CURRENT JOB's product family — not an
-- arbitrary tenant-global pick. CTQs previously lived only in the generic
-- entity_store, which cannot be joined for product-scoped queries.
CREATE TABLE IF NOT EXISTS ctq_characteristics (
    id                         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                       VARCHAR(255) NOT NULL,
    description                TEXT,
    category                   VARCHAR(100),
    product_family_id          UUID REFERENCES product_families(id) ON DELETE SET NULL,
    specification_limit_lower  DOUBLE PRECISION,
    specification_limit_upper  DOUBLE PRECISION,
    target_value               DOUBLE PRECISION,
    unit                       VARCHAR(20),
    measurement_method         VARCHAR(100),
    is_active                  BOOLEAN NOT NULL DEFAULT TRUE,
    created_by                 UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ctq_tenant ON ctq_characteristics (tenant_id, product_family_id);
CREATE INDEX IF NOT EXISTS idx_ctq_active ON ctq_characteristics (tenant_id, is_active);

-- Fail-closed RLS (item 26): the creating migration establishes isolation.
ALTER TABLE ctq_characteristics ENABLE ROW LEVEL SECURITY;
ALTER TABLE ctq_characteristics FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ctq_characteristics
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
