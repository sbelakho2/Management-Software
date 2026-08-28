-- Outbox claim lease (P0-6): a relay claims events atomically
-- (claimed_by + claim_until) so two replicas can never publish the same
-- event; the claim expires for crash recovery. The published_dedupe table
-- is the durable consumer-side deduplication record (at-least-once
-- delivery: every consumer records the event_id it processed).
ALTER TABLE outbox_events
    ADD COLUMN IF NOT EXISTS claimed_by TEXT,
    ADD COLUMN IF NOT EXISTS claim_until TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS outbox_published (
    event_id     UUID PRIMARY KEY,
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
