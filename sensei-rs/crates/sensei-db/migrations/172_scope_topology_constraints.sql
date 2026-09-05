-- Thirtieth-audit P0 item 2 (DB topology constraints for role-slot WC
-- grants): a role slot whose explicit scope_kind is 'work_center' claims
-- (tenant, work center, SITE) — the site must be the work center's REAL
-- site, never a fabricated one. Migration 169 enforced the SHAPE (a
-- work-center slot carries both ids); this migration enforces the
-- TOPOLOGY (the pair must exist as a work_centers row).
--
-- Mechanics:
--   * A composite FK needs a UNIQUE index on the referenced columns, so
--     work_centers first gets UNIQUE (tenant_id, id, site_id). Existing
--     rows are trivially unique: id is the primary key, so every
--     (tenant_id, id) pair — and hence every (tenant_id, id, site_id)
--     triple, NULLs included — already differs.
--   * The FK is declared MATCH SIMPLE (the default): a row is only
--     checked when NONE of its FK columns is NULL. role_slots.tenant_id
--     is NOT NULL, so:
--       - 'none' / 'tenant' kind rows (scope_work_center_id NULL) skip
--         the check entirely;
--       - 'site' kind rows (scope_site_id set, scope_work_center_id
--         NULL) also skip it — a site slot is not a work-center claim;
--       - ONLY 'work_center' kind rows are validated: the 169 shape
--         check guarantees both ids are present, and the FK then proves
--         (tenant_id, scope_work_center_id, scope_site_id) exists in
--         work_centers — i.e. the denormalized site IS the carrier's
--         real site. A mismatched site can no longer be written.
--   * Every statement is guarded (DROP CONSTRAINT IF EXISTS first / DO
--     blocks) so re-running the file by hand is safe.

-- ── 1. Work-center rows are a valid composite FK target ──────────────
-- Backfill first: any pre-existing work-center-kind slot whose
-- denormalized scope_site_id disagrees with the carrier's real site is
-- REPAIRED to the truth (the carrier owns the site, migration 134) —
-- the constraint must never ratify a fabricated site, and honest rows
-- must not block the chain.
DO $$
BEGIN
    UPDATE role_slots rs
       SET scope_site_id = wc.site_id
      FROM work_centers wc
     WHERE rs.scope_kind = 'work_center'
       AND rs.scope_work_center_id IS NOT NULL
       AND wc.id = rs.scope_work_center_id
       AND wc.tenant_id = rs.tenant_id
       AND wc.site_id IS NOT NULL
       AND rs.scope_site_id IS DISTINCT FROM wc.site_id;
END $$;

ALTER TABLE work_centers
    DROP CONSTRAINT IF EXISTS work_centers_tenant_id_id_site_id_key;
ALTER TABLE work_centers
    ADD CONSTRAINT work_centers_tenant_id_id_site_id_key
    UNIQUE (tenant_id, id, site_id);

-- ── 2. Work-center-kind role slots must name a REAL (tenant, wc, site)
--       work-center row ────────────────────────────────────────────────
ALTER TABLE role_slots
    DROP CONSTRAINT IF EXISTS role_slots_scope_work_center_topology_fk;
ALTER TABLE role_slots
    ADD CONSTRAINT role_slots_scope_work_center_topology_fk
    FOREIGN KEY (tenant_id, scope_work_center_id, scope_site_id)
    REFERENCES work_centers (tenant_id, id, site_id);
