-- Target-side apply idempotency (twenty-fifth audit P0/P1-2): the queue
-- is at-least-once — a worker crash after CLAIM loses only the lease, so
-- the same projection can be redelivered and re-applied. A retried apply
-- must be refused ATOMICALLY: `replication_applied` is the durable record
-- that an apply already landed for one (tenant, source_event,
-- projection_type, projection_revision, target_tenant, target_site) key.
-- The apply path INSERTs it FIRST (`mark_target_applied`, with
-- INSERT ... ON CONFLICT DO NOTHING RETURNING id); a duplicate mark
-- (false) refuses the retried apply, so at-least-once delivery never
-- becomes double application. The record lives in the APPLYING tenant's
-- slice — RLS mirrors the integration_instances pattern (migration 154:
-- ENABLE + FORCE + tenant_isolation USING tenant_id = app.tenant_id) —
-- so tenant A can never see or dedupe against tenant B's apply records.
CREATE TABLE IF NOT EXISTS replication_applied (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    source_tenant_id    UUID NOT NULL,
    source_site_id      UUID,
    source_event_id     UUID NOT NULL,
    projection_type     TEXT NOT NULL,
    projection_revision BIGINT NOT NULL,
    target_tenant_id    UUID NOT NULL,
    target_site_id      UUID,
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, source_event_id, projection_type, projection_revision,
            target_tenant_id, target_site_id)
);
ALTER TABLE replication_applied ENABLE ROW LEVEL SECURITY;
ALTER TABLE replication_applied FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON replication_applied
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
