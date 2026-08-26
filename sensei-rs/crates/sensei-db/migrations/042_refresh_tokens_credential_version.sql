-- Refresh-token records carry the user's credential version so a password
-- change/reset invalidates every previously issued refresh token.
ALTER TABLE refresh_tokens
    ADD COLUMN IF NOT EXISTS credential_version BIGINT NOT NULL DEFAULT 0;

-- Support logout-all / password-change revocation.
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON refresh_tokens (user_id);
