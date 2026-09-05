-- Federation application receipts + source confirmation (thirtieth audit
-- item 25): the final production receiving state machine. Until now the
-- target inbox (`replication_inbox`, migration 166) could never leave
-- 'received': `apply_target_projection` refused every application while
-- the projector allowlist was empty, no receipt identity existed, and the
-- source queue's terminal state was the consumer ACK ('acked') — which
-- the twenty-sixth/twenty-seventh audits had already stripped of any
-- application meaning. This migration adds the pieces the honest
-- end-to-end machine needs:
--
--   source queued -> source claimed -> target received -> target applying
--     -> target applied -> TARGET-GENERATED RECEIPT -> source
--        application_confirmed
--
--  1. `site_replication_log.status` gains the terminal SOURCE state
--     'application_confirmed' (+ `confirmed_at`). It is reached ONLY by
--     the confirmation path observing a target-generated receipt — never
--     by `ack()` (the queue-side consume acknowledgement stays exactly
--     that) and never by any source-side worker that has not seen a
--     receipt.
--
--  2. `replication_inbox` gains the delivery binding columns the receipt
--     identity is built on: `source_queue_id` (the source
--     `site_replication_log` row this delivery came from) and
--     `payload_hash` (SHA-256 hex of the canonical projection payload
--     delivered). Delivery writes both; the apply path verifies the hash
--     of the projection it is about to apply against the hash recorded at
--     delivery — a mismatch is recorded 'reconcile_required', never
--     'applied'.
--
--  3. `replication_receipts`: the TARGET-GENERATED application receipt.
--     The row is created ONLY by the target apply path, in the same
--     transaction that lands the projection ('applied'), and binds the
--     receipt identity the audit specifies:
--     source_tenant_id, source_queue_id, source_event_id,
--     target_tenant_id, target_site_id, target_inbox_id,
--     projection_type, projection_revision, payload_hash, received_at.
--     The receipt lives in the TARGET tenant's FORCE-RLS slice (same
--     pattern as migration 166/154) — no source tenant can write one, so
--     a source-side actor can never manufacture the target-application
--     fact. `target_inbox_id` is a logical reference to
--     `replication_inbox.id`; like the migration-166 inbox (and the
--     queue's own target columns) no FK is declared — the federation
--     contract tests fabricate peer tenants that carry no `tenants` rows,
--     and the receipts/inbox/queue tables were designed without FK
--     coupling for exactly that reason.
--
--  4. `federation_application_receipts(p_source_queue_id uuid)`: the ONLY
--     cross-tenant receipt boundary, mirroring the migration-153/156
--     SECURITY DEFINER pattern. It is session-bound: the source tenant is
--     read INSIDE the function from `app.tenant_id`, and only receipts
--     whose `source_tenant_id` equals that context are visible — a source
--     session can observe the application receipts of its own queue rows
--     (and their binding + inbox status) but can never see another
--     tenant's receipts, and can never write to the target's slice.
--     ANTI-MANUFACTURE INVARIANT: the function additionally requires the
--     receipt to be owned by its destination (`r.tenant_id =
--     r.target_tenant_id`) and owned by a tenant OTHER than the calling
--     source (`r.tenant_id <> <session context>`). A receipt row is
--     created ONLY by the target apply in the TARGET tenant's FORCE-RLS
--     slice, so a source session can never write one there; a receipt the
--     source COULD write in its OWN slice is excluded by the ownership
--     filter — the source cannot manufacture the rows that drive its own
--     confirmation.
--
-- Nothing in this migration lets `ack()` (or any source-side write)
-- produce 'target applied' or an application receipt: the receipt is
-- server-created by the target apply, and 'application_confirmed' is only
-- reached through [`replication::confirm_application_receipts`] after a
-- matching receipt is observed.

-- 1. Source queue terminal state: 'application_confirmed' + confirmed_at.
--    The original unnamed column CHECK (migration 126) was auto-named
--    `site_replication_log_status_check`; drop it by that name and
--    re-add it explicitly with the new terminal state. The column is
--    widened to VARCHAR(30) at the same time — 'application_confirmed'
--    is 21 characters and does not fit the migration-126 VARCHAR(20).
ALTER TABLE site_replication_log
    ALTER COLUMN status TYPE VARCHAR(30);
ALTER TABLE site_replication_log
    DROP CONSTRAINT IF EXISTS site_replication_log_status_check;
ALTER TABLE site_replication_log
    ADD CONSTRAINT site_replication_log_status_check
    CHECK (status IN ('pending', 'claimed', 'acked', 'failed',
                      'application_confirmed'));
ALTER TABLE site_replication_log
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

-- 2. Inbox delivery-binding columns (written by the delivery path only),
--    plus the OWNER-SCOPED dedupe arbiter. The migration-166 unique key
--    `(source_tenant_id, source_event_id, projection_type,
--    projection_revision, target_tenant_id, target_site_id)` does NOT
--    include the row's owner (`tenant_id`). A row is legitimately owned
--    by its destination (`tenant_id = target_tenant_id`), but a SOURCE
--    tenant session can write a row in its OWN slice with that exact key
--    (FORCE RLS scopes ownership, it cannot stop the owner writing its
--    own rows) — and the old key would then block the REAL delivery's
--    `ON CONFLICT ... DO NOTHING` reservation in the target's slice. The
--    arbiter is therefore re-created owner-scoped: `(tenant_id, ...)` —
--    per-slice duplicates are still refused, and a squatter row in a
--    different slice no longer collides with the destination's inbox.
ALTER TABLE replication_inbox
    ADD COLUMN IF NOT EXISTS source_queue_id UUID,
    ADD COLUMN IF NOT EXISTS payload_hash TEXT;

DO $$
DECLARE cname text;
BEGIN
    SELECT c.conname INTO cname
    FROM pg_constraint c
    WHERE c.conrelid = 'replication_inbox'::regclass
      AND c.contype = 'u'
      AND pg_get_constraintdef(c.oid) LIKE
          '%source_tenant_id, source_event_id, projection_type, projection_revision, target_tenant_id, target_site_id%'
      AND pg_get_constraintdef(c.oid) NOT LIKE 'UNIQUE (tenant_id%';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE replication_inbox DROP CONSTRAINT %I', cname);
    END IF;
END $$;

ALTER TABLE replication_inbox
    ADD CONSTRAINT uq_replication_inbox_delivery_key
    UNIQUE (tenant_id, source_tenant_id, source_event_id, projection_type,
            projection_revision, target_tenant_id, target_site_id);

-- 3. Target-generated application receipts (thirtieth audit item 25).
CREATE TABLE IF NOT EXISTS replication_receipts (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id            UUID NOT NULL,
    source_tenant_id     UUID NOT NULL,
    source_queue_id      UUID NOT NULL,
    source_site_id       UUID,
    source_event_id      UUID NOT NULL,
    target_tenant_id     UUID NOT NULL,
    target_site_id       UUID,
    target_inbox_id      UUID NOT NULL,
    projection_type      TEXT NOT NULL,
    projection_revision  BIGINT NOT NULL,
    payload_hash         TEXT NOT NULL,
    received_at          TIMESTAMPTZ NOT NULL,
    applied_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- One application receipt per inbox reservation (a re-apply after
    -- reconciliation converges on the original receipt, never a second).
    -- Both receipt uniques are OWNER-scoped (tenant_id first) for the
    -- same reason as the inbox arbiter above: the receipt is created
    -- only in the TARGET tenant's slice, and an owner-scoped key keeps
    -- a row a source session writes in its own slice from ever
    -- colliding with — or masquerading as — the target's receipt.
    UNIQUE (tenant_id, target_inbox_id),
    -- One receipt per delivery key — the same dedupe boundary as the
    -- migration-166 inbox row the receipt is bound to.
    UNIQUE (tenant_id, source_tenant_id, source_event_id,
            projection_type, projection_revision, target_tenant_id,
            target_site_id)
);
ALTER TABLE replication_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE replication_receipts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON replication_receipts
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- 4. Cross-tenant receipt observation (SECURITY DEFINER, session-bound —
--    the migration-153/156 pattern). PUBLIC keeps EXECUTE (the no-argument
--    context binding is the caller's own, exactly as
--    `federation_governance_edges()` relies on it), so a source session
--    can only ever observe receipts of ITS OWN queue rows.
CREATE OR REPLACE FUNCTION federation_application_receipts(p_source_queue_id uuid)
RETURNS TABLE(receipt_id uuid, target_tenant_id uuid, target_site_id uuid,
              source_event_id uuid, projection_type text,
              projection_revision bigint, payload_hash text,
              applied_at timestamptz, inbox_status text)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT r.id, r.target_tenant_id, r.target_site_id, r.source_event_id,
           r.projection_type, r.projection_revision, r.payload_hash,
           r.applied_at, i.status
    FROM replication_receipts r
    JOIN replication_inbox i
         ON i.id = r.target_inbox_id AND i.tenant_id = r.tenant_id
    WHERE r.source_tenant_id =
          NULLIF(current_setting('app.tenant_id', true), '')::uuid
      AND r.source_queue_id = p_source_queue_id
      AND r.tenant_id = r.target_tenant_id
      AND r.tenant_id <>
          NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$;
