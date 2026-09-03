-- Federation inbox (twenty-seventh audit P0): the honest successor of the
-- `replication_applied` table (migration 163). The old table conflated an
-- INBOX RECEIPT with an APPLICATION — its only state was the row's
-- existence, and nothing in the workspace could ever transition it, so an
-- "applied" name was pinned on records that only ever meant "delivered".
--
-- `replication_inbox` is the TARGET tenant's explicit inbox with a real
-- state machine:
--
--   received           delivery landed the projection in the inbox
--                      (`deliver_to_target_inbox` INSERTs 'received');
--   applying           a REGISTERED target projector claimed the row
--                      (received -> applying, apply_started_at);
--   applied            the projector succeeded (applying -> applied,
--                      applied_at) — the ONLY terminal 'this projection
--                      really landed' state;
--   reconcile_required the projector failed (applying ->
--                      reconcile_required, failed_at) — the row needs
--                      reconciliation, never a silent retry as if nothing
--                      had happened.
--
-- Nothing transitions out of 'received' while no target projector exists
-- (`apply_target_projection` refuses every apply against the empty
-- projector allowlist) — an application that never happened is never
-- recorded as 'applied'. `ack()` still never writes this table: the
-- source queue row's 'acked' is the consume acknowledgement, and the
-- inbox is reserved separately and honestly by the delivery path under
-- the TARGET tenant's context.
--
-- The RLS pattern is the migration-154 one (ENABLE + FORCE +
-- tenant_isolation USING tenant_id = current_setting('app.tenant_id')) —
-- the inbox lives in the TARGET tenant's FORCE-RLS slice (tenant_id is
-- the destination, same tenant as target_tenant_id on every receipt the
-- service writes), so tenant A can never see, dedupe against, or
-- transition tenant B's inbox rows.
CREATE TABLE IF NOT EXISTS replication_inbox (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id            UUID NOT NULL,
    source_tenant_id     UUID NOT NULL,
    source_site_id       UUID,
    source_event_id      UUID NOT NULL,
    projection_type      TEXT,
    projection_revision  BIGINT,
    target_tenant_id     UUID NOT NULL,
    target_site_id       UUID,
    policy_revision      BIGINT,
    payload_digest       TEXT,
    authorization_digest TEXT,
    status               VARCHAR(30) NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'applying', 'applied', 'reconcile_required')),
    received_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    apply_started_at     TIMESTAMPTZ,
    applied_at           TIMESTAMPTZ,
    failed_at            TIMESTAMPTZ,
    UNIQUE (source_tenant_id, source_event_id, projection_type,
            projection_revision, target_tenant_id, target_site_id)
);
ALTER TABLE replication_inbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE replication_inbox FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON replication_inbox
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- The migration-163 table is fully superseded: the code no longer
-- references it, and keeping it would leave a second, ambiguous record
-- of the same delivery. Dropped AFTER the inbox exists so a failed
-- migration can never leave the chain without either record.
DROP TABLE IF EXISTS replication_applied;

-- Twenty-seventh-audit P0.3 wiring: the durable pre-dispatch journal gate
-- (reserved -> dispatching -> mutation -> complete) needs 'dispatching' in
-- the command_journal status CHECK — without it PgExecutionJournal's
-- begin_dispatch UPDATE would fail against a migrated DB.
ALTER TABLE command_journal DROP CONSTRAINT IF EXISTS command_journal_status_check;
ALTER TABLE command_journal ADD CONSTRAINT command_journal_status_check
    CHECK (status IN ('reserved','dispatching','executing','succeeded','failed','unknown_outcome','reconcile_required'));
