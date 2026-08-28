-- Plant topology: operational facts need "where" — tenant -> site ->
-- value stream -> product family -> line/cell -> work center.
-- NOTE: the sites table is created by migration 011 (system tables); this
-- block reconciles it with the composite tenant key the children below
-- need to reference, so the database itself enforces same-tenant FKs.
CREATE TABLE IF NOT EXISTS sites (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_code  VARCHAR(50) NOT NULL,
    name       VARCHAR(255) NOT NULL,
    address    TEXT,
    timezone   VARCHAR(64) NOT NULL DEFAULT 'UTC',
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_code)
);
-- Cross-tenant guard (item 9): composite tenant key so children can
-- reference (tenant_id, id) and the database enforces same-tenant.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'sites_tenant_id_id_key'
    ) THEN
        ALTER TABLE sites ADD CONSTRAINT sites_tenant_id_id_key UNIQUE (tenant_id, id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS value_streams (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- Composite FK: the site must belong to the SAME tenant — a tenant-A
    -- value stream can never reference tenant-B's site (item 9).
    site_id       UUID NOT NULL,
    name          VARCHAR(255) NOT NULL,
    description   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_id, name),
    FOREIGN KEY (tenant_id, site_id) REFERENCES sites(tenant_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_families (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- Composite FK: same-tenant site reference (item 9).
    site_id     UUID,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_id, name),
    FOREIGN KEY (tenant_id, site_id) REFERENCES sites(tenant_id, id) ON DELETE SET NULL
);
