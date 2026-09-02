-- Fanout idempotency (twenty-third audit P1): the enqueue route now
-- publishes ONE source event across EVERY federation edge inside a SINGLE
-- transaction with INSERT ... ON CONFLICT (tenant_id, source_event_id,
-- target_tenant_id, target_site_id) DO NOTHING — a retry after a partial
-- success (or a repeated publish) must converge to the same complete set,
-- never fail on the first duplicate.
--
-- The migration-148 dedupe index (idx_rep_log_idempotent_edge) is
-- expression-based (COALESCE columns over projection_type/entity_type and
-- the target ids) and partial, so PostgreSQL cannot infer it from a plain
-- ON CONFLICT column list. This migration adds a PLAIN unique index on
-- exactly the four fanout idempotency columns so the conflict target can
-- be spelled out verbatim. NULLS DISTINCT (the default) keeps legacy
-- destination-less rows (NULL target_tenant_id/target_site_id) from
-- colliding with each other or with fanout rows, and idx_rep_log_idempotent_edge
-- is retained unchanged: it still rejects the legacy duplicate enqueue of
-- the same (tenant, source_event_id, projection_type) toward a NULL-target
-- row, so existing per-edge duplicate-rejection semantics are preserved.
CREATE UNIQUE INDEX IF NOT EXISTS idx_rep_log_fanout_idempotent
    ON site_replication_log (tenant_id, source_event_id, target_tenant_id, target_site_id);
