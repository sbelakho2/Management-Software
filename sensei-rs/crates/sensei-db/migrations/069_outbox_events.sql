-- Transactional outbox: business state + audit + outbox row commit in the
-- SAME transaction. A relay publishes outbox events to NATS; an event is
-- never lost because the publication failed after the business commit
-- (the old "commit mutation, then publish, warn on failure" pattern).
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id       UUID PRIMARY KEY,
    tenant_id      UUID NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id   UUID NOT NULL,
    event_type     VARCHAR(100) NOT NULL,
    payload        JSONB NOT NULL,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at   TIMESTAMPTZ,
    attempt_count  INT NOT NULL DEFAULT 0,
    last_error     TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbox_unpublished
    ON outbox_events (occurred_at) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_outbox_tenant
    ON outbox_events (tenant_id, occurred_at);
