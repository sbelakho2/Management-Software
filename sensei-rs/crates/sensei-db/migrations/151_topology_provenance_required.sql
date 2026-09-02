-- Topology structural enforcement (twentieth audit P1-16): 'resolved'
-- topology must be PROVEN, not merely declared — a work center whose
-- lineage was assigned by the legacy heuristic can never be certified,
-- and a 'resolved' state requires a verified provenance record.
-- The DEFAULT is now 'needs_reconciliation': a row created without
-- provenance starts unreconciled — certification is never the default.
ALTER TABLE work_centers
    ALTER COLUMN topology_state SET DEFAULT 'needs_reconciliation';
ALTER TABLE work_centers
    ADD CONSTRAINT topology_resolved_requires_provenance CHECK (
        topology_state <> 'resolved'
        OR (
            topology_assignment_source IS NOT NULL
            AND topology_assignment_source <> 'legacy_heuristic'
            AND topology_verified_at IS NOT NULL
            AND topology_verified_by IS NOT NULL
        )
    ) NOT VALID;
ALTER TABLE work_centers VALIDATE CONSTRAINT topology_resolved_requires_provenance;
