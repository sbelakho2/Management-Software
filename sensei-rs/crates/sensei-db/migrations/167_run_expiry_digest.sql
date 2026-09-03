-- Twenty-seventh-audit P1: integration runs expire (server-side maximum
-- age) and carry a REAL configuration digest — a SHA-256 over the
-- normalized configuration the instance actually points at, not the
-- 'attested:<revision>' placeholder. Abandoned runs are purged.
ALTER TABLE integration_runs
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS configuration JSONB;
CREATE INDEX IF NOT EXISTS idx_integration_runs_expiry
    ON integration_runs (tenant_id, instance_id) WHERE completed_at IS NULL;
