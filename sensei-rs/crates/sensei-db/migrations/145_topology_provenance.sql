-- Topology ASSIGNMENT PROVENANCE (nineteenth audit item P1): migration
-- 134 backfilled work_centers.site_id with an EARLIEST-SITE fallback, so a
-- non-NULL site_id is NOT proof of a real assignment — it may be
-- fabricated lineage. From here on every work center must record HOW its
-- topology was assigned (provenance), WHEN it was verified and BY WHOM:
--   - 'manifest'             : the site manifest assigned it
--   - 'employee_history'     : derived from employee_assignments
--   - 'manual_reconciliation': a human verified and corrected it
--   - 'legacy_heuristic'     : the unprovable 134 fallback — NOT a
--                              provenance, only a marker of doubt.
-- legacy_heuristic is NEVER admitted into an Active plant: it always
-- carries topology_state = 'needs_reconciliation' + a NULL verified_at,
-- the validation gate refuses any tenant containing it, and the reconcile
-- service function refuses to apply it.
ALTER TABLE work_centers
    ADD COLUMN IF NOT EXISTS topology_assignment_source VARCHAR(40),
    ADD COLUMN IF NOT EXISTS topology_verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS topology_verified_by UUID;

ALTER TABLE work_centers
    ADD CONSTRAINT topology_source_check
    CHECK (topology_assignment_source IN
           ('manifest', 'employee_history', 'manual_reconciliation',
            'legacy_heuristic'));

-- CORRECTIVE step: every pre-existing row whose provenance is NULL cannot
-- PROVE where its site_id came from (134's earliest-site fallback
-- fabricated exactly these) — such rows are marked 'legacy_heuristic' and
-- pushed back to needs_reconciliation until a human or a real source
-- re-asserts the assignment. A NULL source is indistinguishable from an
-- unprovable source, so the honest rule flags all of them: unproven
-- topology never certifies a plant as ready.
UPDATE work_centers
SET topology_assignment_source = 'legacy_heuristic',
    topology_state = 'needs_reconciliation',
    topology_verified_at = NULL
WHERE topology_assignment_source IS NULL;
