-- Refresh-token revocation support.
--
-- The refresh_token_store code (migration-175 hardening wave) reads and
-- writes `revoked_at` on `refresh_tokens` for family revocation and
-- per-user revoke-on-password-change, but no migration ever ADDED the
-- column: validation SELECTed `rt.revoked_at` and failed with a SQL error
-- on every refresh, surfacing as 401 "Invalid or expired refresh token".
ALTER TABLE refresh_tokens
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;

-- Family-wide revocation scans by family_id.
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family_id_revoked
    ON refresh_tokens (family_id) WHERE revoked_at IS NOT NULL;
