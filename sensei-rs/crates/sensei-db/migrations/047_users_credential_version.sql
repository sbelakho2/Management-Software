-- User credential versioning.
--
-- Incremented on every password change / credential rotation so the auth
-- layer can invalidate previously issued refresh tokens and sessions (the
-- credential_version is embedded in token claims and checked at
-- refresh/session-validation time).

ALTER TABLE users ADD COLUMN IF NOT EXISTS credential_version BIGINT NOT NULL DEFAULT 0;
