-- Twenty-first audit item 5 (per-site integration INSTANCES): site
-- readiness must be proven per integration instance, never per kind.
-- integration_checkpoints are keyed (tenant, source_system, source_table)
-- — a checkpoint has no site or instance anchor, so ONE healthy SAP
-- checkpoint could certify BOTH Tangier's and Bizerte's SAP. This
-- migration materializes the manifest's declared integrations PER SITE:
-- integration_instances rows are the provisioned instances (one per
-- (tenant, site, integration_type), fail-closed RLS like every other
-- tenant-owned table — see migration 121), and integration_checkpoints
-- gain an optional instance_id so readiness can require each instance's
-- OWN checkpoint (instance_id NULL = legacy pre-instance rows that no
-- longer certify anything).
CREATE TABLE IF NOT EXISTS integration_instances (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    site_id                UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    integration_type       VARCHAR(60) NOT NULL,
    endpoint               VARCHAR(500),
    configuration_revision INT NOT NULL DEFAULT 1,
    UNIQUE (tenant_id, site_id, integration_type)
);
ALTER TABLE integration_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_instances FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON integration_instances
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

ALTER TABLE integration_checkpoints
    ADD COLUMN IF NOT EXISTS instance_id UUID REFERENCES integration_instances(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_integration_checkpoints_instance
    ON integration_checkpoints (tenant_id, instance_id, last_run_at);
