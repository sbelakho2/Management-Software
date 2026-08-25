-- Idempotency records.
--
-- Backs the Idempotency-Key middleware in PostgreSQL mode. The claim is
-- made atomically with INSERT ... ON CONFLICT DO NOTHING (state
-- 'in_progress'); on handler success the row is flipped to 'completed'
-- with the cached status and response body. Rows expire via expires_at
-- (TTL) and are never written for 5xx responses.

CREATE TABLE IF NOT EXISTS idempotency_records (
    key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    state TEXT NOT NULL,
    status INT,
    response_body BYTEA,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Supports TTL-based cleanup of expired records.
CREATE INDEX IF NOT EXISTS idx_idempotency_records_expires_at
    ON idempotency_records (expires_at);
