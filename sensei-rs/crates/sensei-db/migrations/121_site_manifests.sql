-- Declarative SITE MANIFEST (fifteenth audit 83/93/A17): a new plant
-- comes onto Starz Forge WITHOUT modifying core domain code — the manifest
-- IS the configuration. Locale (country/timezone/languages/currency),
-- capabilities, integrations and the policy bundle are RECORDS, not code:
-- `site_id` is the only domain reference, so bootstrapping a new site is
-- an upsert of records, never a redeploy.
CREATE TABLE IF NOT EXISTS site_manifests (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id      UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    country      VARCHAR(100) NOT NULL,
    timezone     VARCHAR(100) NOT NULL DEFAULT 'UTC',
    languages    JSONB NOT NULL DEFAULT '[]',
    currency     VARCHAR(10) NOT NULL DEFAULT 'USD',
    capabilities JSONB NOT NULL DEFAULT '[]',
    integrations JSONB NOT NULL DEFAULT '[]',
    policy_bundle VARCHAR(100),
    manifest_version INT NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, site_id)
);
ALTER TABLE site_manifests ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_manifests FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON site_manifests
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
