-- Request-level Andon idempotency (seventeenth audit item 11): a client
-- command key is generated ONCE per raise and persisted with the result —
-- a retry after a dropped connection replays the SAME andon instead of
-- creating a duplicate with a fresh UUID.
ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS request_key TEXT,
    ADD COLUMN IF NOT EXISTS request_key_tenant TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_andons_request_key
    ON andons (tenant_id, request_key)
    WHERE request_key IS NOT NULL;
