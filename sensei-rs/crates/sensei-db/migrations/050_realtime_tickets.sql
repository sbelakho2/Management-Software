-- Realtime connection tickets (WebSocket / SSE).
--
-- A ticket is a one-time credential minted by POST /api/v1/realtime/ticket
-- for an authenticated user, scoped to either the WS or SSE transport. It
-- is consumed atomically on first use and expires shortly after issuance
-- (30s TTL), so a stolen ticket is only usable within a narrow window and
-- never twice.

CREATE TABLE IF NOT EXISTS realtime_tickets (
    ticket UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    scope TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ
);

-- Supports TTL-based cleanup and the expires_at > NOW() consume guard.
CREATE INDEX IF NOT EXISTS idx_realtime_tickets_expires_at
    ON realtime_tickets (expires_at);
