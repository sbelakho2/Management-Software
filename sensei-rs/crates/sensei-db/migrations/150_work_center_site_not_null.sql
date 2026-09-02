-- Work Center site/topology index (twentieth audit P0 — Work Center
-- split-brain): the public Work Center API now persists through the
-- relational WorkCenterRepository (crates/sensei-services/src/tps/
-- work_center_repository.rs) into THIS table — the same system of
-- record that RequestContext topology validation (request_context.rs),
-- site readiness (site_manifest.rs), capability checks and skills read.
--
-- The site-readiness gate scans for unreconciled topology; resolved
-- work centers are looked up per (tenant, site). This partial index
-- serves exactly that resolved subset.
--
-- site_id is deliberately NOT set NOT NULL here:
--   * legacy rows created before migration 134 (and rows whose site was
--     never provable) legitimately keep site_id NULL with
--     topology_state = 'needs_reconciliation' — unknown lineage is never
--     certified, and NULL is the only honest encoding of "no site";
--   * crates/sensei-db/tests/db_contract.rs inserts work centers WITHOUT
--     a site_id in several tests, and the repository itself creates
--     site-less rows in 'needs_reconciliation' when a create request
--     carries no site_id.
-- NOT NULL would force a fabricated site; the repository, the composite
-- FK (work_centers_tenant_site_fk) and the readiness gate enforce the
-- invariant instead.
CREATE INDEX IF NOT EXISTS idx_work_centers_site_topology
    ON work_centers (tenant_id, site_id)
    WHERE topology_state = 'resolved';
