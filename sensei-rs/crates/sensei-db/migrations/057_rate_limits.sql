-- Shared rate-limit counters: with multiple API replicas a per-process
-- counter allows the effective limit to scale with replica count. This
-- table is the shared sliding-window counter (atomic UPSERT).
CREATE TABLE IF NOT EXISTS rate_limits (
    key TEXT PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    count BIGINT NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '5 minutes')
);
CREATE INDEX IF NOT EXISTS idx_rate_limits_expires_at ON rate_limits (expires_at);
