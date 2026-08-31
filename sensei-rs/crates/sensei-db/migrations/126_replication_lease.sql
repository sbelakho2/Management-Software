-- Replication lease/ACK (sixteenth audit items 15-17): claim -> apply ->
-- ACK with at-least-once delivery + idempotent application.
ALTER TABLE site_replication_log
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'claimed', 'acked', 'failed')),
    ADD COLUMN IF NOT EXISTS claim_token UUID,
    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS acked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_error TEXT,
    ADD COLUMN IF NOT EXISTS schema_version INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS projection_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS projection_revision BIGINT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS data_policy VARCHAR(50) NOT NULL DEFAULT 'internal';
DROP INDEX IF EXISTS idx_rep_log_pending;
CREATE UNIQUE INDEX IF NOT EXISTS idx_rep_log_idempotent
    ON site_replication_log (tenant_id, source_event_id, COALESCE(projection_type, entity_type))
    WHERE source_event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rep_log_claimable
    ON site_replication_log (tenant_id, status)
    WHERE status = 'pending' OR status = 'failed';
