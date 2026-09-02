-- Server-attested integration runs (twenty-fifth audit P1): the bridge no
-- longer declares which configuration it tested. Starting a run issues a
-- server token bound to the instance's CURRENT configuration revision and
-- digest; completion must present that exact token and the instance must
-- still be on the attested revision — a run started at rev1 that finishes
-- after the manifest moved to rev2 is rejected.
CREATE TABLE IF NOT EXISTS integration_runs (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    instance_id            UUID NOT NULL REFERENCES integration_instances(id) ON DELETE CASCADE,
    run_token              UUID NOT NULL,
    configuration_revision BIGINT NOT NULL,
    configuration_digest   TEXT NOT NULL DEFAULT '',
    run_id                 TEXT NOT NULL,
    started_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at           TIMESTAMPTZ,
    result                 VARCHAR(20),
    UNIQUE (tenant_id, run_token),
    UNIQUE (tenant_id, instance_id, run_id)
);
ALTER TABLE integration_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON integration_runs
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
CREATE INDEX IF NOT EXISTS idx_integration_runs_instance
    ON integration_runs (tenant_id, instance_id, started_at);
