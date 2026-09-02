-- Topology reconciliation (eighteenth audit P1-12): migration 134
-- silently assigned work centers with unknown lineage to the tenant's
-- EARLIEST site. Unknown does NOT equal first plant. From here on:
--   - work centers whose site was never provable keep site_id = NULL
--   - topology_state marks them NeedsReconciliation
--   - site activation REFUSES to proceed while any work center in the
--     site's tenant remains unreconciled (enforced in the service).
ALTER TABLE work_centers
    ADD COLUMN IF NOT EXISTS topology_state VARCHAR(40) NOT NULL DEFAULT 'resolved'
        CHECK (topology_state IN ('resolved', 'needs_reconciliation'));

-- Identify the work centers that were backfilled by the EARLIEST-SITE
-- fallback in 134: we cannot retroactively distinguish them, so any
-- work center whose site_id is NULL is flagged; additionally the
-- fallback's heuristic rows are indistinguishable from real ones, so
-- the honest rule is: a site_id that is NULL means NeedsReconciliation,
-- and activation refuses while any exist. Existing NULL-site work
-- centers (from pre-134 rows or 134's non-backfilled cases) are marked.
UPDATE work_centers
SET topology_state = 'needs_reconciliation'
WHERE site_id IS NULL;

-- Foreign sites that get DELETED also orphan their work centers:
-- FK on site_id is ON DELETE SET NULL (added in 134), so mark those too.
UPDATE work_centers wc
SET topology_state = 'needs_reconciliation'
WHERE wc.site_id IS NULL;
