-- Twenty-second audit P1 (integration lifecycle + instance-keyed
-- checkpoints): the integration INSTANCE becomes a lifecycle object, not
-- a passive registry row.
--
-- 1. integration_instances gains lifecycle state: `enabled` (a disabled
--    instance is decommissioned — it can never be advanced by the bridge
--    and must NOT keep blocking site readiness), `required` (a
--    non-required instance is optional — readiness is proven per
--    enabled AND required instance only) and `last_verified_revision`
--    (the instance's configuration_revision when its checkpoint was last
--    verified — NULL = never verified).
--
-- 2. integration_checkpoints become INSTANCE-keyed: the readiness proof
--    is the checkpoint's instance_id, not the legacy
--    (source_system, source_table) cursor. The legacy UNIQUE cursor
--    constraint is removed (two sites' instances of the SAME kind must
--    be able to checkpoint independently) and each instance owns at most
--    one cursor row (UNIQUE (tenant_id, instance_id)). The legacy
--    source_system/source_table fields are retained as OPTIONAL legacy
--    metadata — the readiness proof is instance_id, so they are no
--    longer required (NULL = instance-keyed row that never declared a
--    legacy cursor).
--
-- 3. site_manifests.integrations becomes nullable: a NULL integrations
--    policy means "integration policy not configured" (fail-closed —
--    readiness cannot be certified), while an EXPLICIT '[]' means "no
--    integrations required" (the site legitimately passes). The column
--    keeps its '[]' DEFAULT for legacy writers that omit it; a NULL can
--    only be written deliberately (manifest row provisioned without an
--    integration policy).
ALTER TABLE integration_instances
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS required BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_verified_revision INT;

ALTER TABLE integration_checkpoints
    ALTER COLUMN source_system DROP NOT NULL,
    ALTER COLUMN source_table DROP NOT NULL;

ALTER TABLE integration_checkpoints
    DROP CONSTRAINT IF EXISTS integration_checkpoints_tenant_id_source_system_source_table_key;

ALTER TABLE integration_checkpoints
    ADD CONSTRAINT integration_checkpoints_instance_cursor UNIQUE (tenant_id, instance_id);

ALTER TABLE site_manifests
    ALTER COLUMN integrations DROP NOT NULL;
