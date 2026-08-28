-- Plant topology: operational facts need "where" — tenant -> site ->
-- value stream -> product family -> line/cell -> work center.
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

CREATE TABLE IF NOT EXISTS value_streams (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id       UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    description   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_id, name)
);

CREATE TABLE IF NOT EXISTS product_families (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id     UUID REFERENCES sites(id) ON DELETE SET NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_id, name)
);
