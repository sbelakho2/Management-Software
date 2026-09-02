-- Federation-edge replication governance (twentieth audit P0): the
-- replication decision is PER FEDERATION EDGE — the queue row names the
-- destination it was authorized for, and the membership row carries the
-- governance (allowed_data_classes + residency_policy + allowed_countries)
-- that the source's edge evaluation runs against. The enqueued row is no
-- longer a destination-less projection: target_tenant_id/target_site_id
-- record WHICH edge received it, target_jurisdiction the typed code the
-- residency decision was made against, and edge_policy the full audit
-- snapshot of the edge (policy revision, residency policy, allowed data
-- classes) at enqueue time.
ALTER TABLE site_replication_log
    ADD COLUMN IF NOT EXISTS target_tenant_id UUID,
    ADD COLUMN IF NOT EXISTS target_site_id UUID,
    ADD COLUMN IF NOT EXISTS target_jurisdiction VARCHAR(10),
    ADD COLUMN IF NOT EXISTS edge_policy JSONB;

-- The federation membership row is the edge's POLICY RECORD. Allowed data
-- classes default to every class (the legacy behavior: nothing is blocked
-- until an operator narrows the list); residency defaults to
-- corporate_allowed (the legacy cross-tenant behavior). Operators narrow
-- per membership — never per request, never per client.
ALTER TABLE federation_memberships
    ADD COLUMN IF NOT EXISTS allowed_data_classes JSONB NOT NULL
        DEFAULT '["public","internal","confidential","restricted","personal"]',
    ADD COLUMN IF NOT EXISTS residency_policy VARCHAR(40) NOT NULL
        DEFAULT 'corporate_allowed'
        CHECK (residency_policy IN ('local_only','allowed_countries','corporate_allowed')),
    ADD COLUMN IF NOT EXISTS allowed_countries JSONB NOT NULL DEFAULT '[]';

-- Per-edge idempotency: the same source event may now project to MULTIPLE
-- federation edges (one queue row per edge), so the dedupe key must name
-- the DESTINATION edge — (source_event, projection_type, target_tenant,
-- target_site) — instead of (source_event, projection_type), which would
-- make the second edge's row a hard UNIQUE rejection.
DROP INDEX IF EXISTS idx_rep_log_idempotent;
CREATE UNIQUE INDEX IF NOT EXISTS idx_rep_log_idempotent_edge
    ON site_replication_log
       (tenant_id, source_event_id,
        COALESCE(projection_type, entity_type),
        COALESCE(target_tenant_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(target_site_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE source_event_id IS NOT NULL;
