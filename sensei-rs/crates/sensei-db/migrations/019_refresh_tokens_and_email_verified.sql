-- Email verification and refresh-token store
--
-- 1. Adds email_verified to users (default false, matching the email
--    verification flow added alongside the auth refactor).
-- 2. Creates the refresh_tokens table backing RefreshTokenStore. Only
--    SHA-256 hashes of refresh tokens are stored (never raw tokens),
--    along with the rotation chain (rotated_to_hash) used for
--    reuse/theft detection.

-- ── Users: email verification ───────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- ── Refresh token store ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id       UUID NOT NULL,
    user_id         UUID NOT NULL,
    token_hash      TEXT NOT NULL UNIQUE,
    expires_at      TIMESTAMPTZ NOT NULL,
    rotated_to_hash TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family_id ON refresh_tokens (family_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens (user_id);
