-- Twenty-ninth-audit Wave B items 6-8 (quality resource scope): the
-- quality lifecycle records gain an AUTHORITATIVE site / work-center
-- anchor, stamped SERVER-SIDE at creation (never accepted from client
-- input), so a site-scoped caller's list/get/update/close surface can be
-- intersected with their entitlement at the SQL level.
--
-- Column semantics (the same convention as stock_moves.site_id /
-- gauges.site_id / supplier POs):
--   * scope_site_id        — the SITE that owns the quality record
--                            (the work order's resolved site, or the
--                            caller's validated operating site).
--   * scope_work_center_id — the WORK CENTER that owns the record
--                            (the work order's work_center_id); NULL
--                            for site-level quality records.
--   * BOTH NULL            — a genuinely CORPORATE (tenant-level) record:
--                            visible only to an explicit tenant-wide
--                            grant, never to a site-scoped caller. No
--                            scope_kind companion column is added: a
--                            NULL scope pair is the honest encoding of
--                            the corporate claim (a NULL site can never
--                            be confused with a fabricated one), which
--                            is exactly ResourceScope::Tenant semantics
--                            in AuthorizedScope::enforce_resource.
--
-- Existing tables found by grepping the migration chain for the audit's
-- quality families (actual table names only — nothing is fabricated):
--   ncr_reports (001), non_conformances (006)  ← non_conformances/ncrs
--   capas (001)                                ← capas
--   quality_audits (006), audits (002)         ← quality_audits/audits
--   inspections (002)                          ← inspections
--
-- No quality_reviews / supplier_corrective_actions tables exist in the
-- migration chain (closest neighbors management_reviews / scars are
-- review/SCAR tables with their own lifecycle and are NOT in this wave's
-- resource family), so no columns are added for them. The JSONB-backed
-- quality_* tables the vestigial DatabaseQualityService predates also do
-- not exist in this schema and are intentionally NOT created here.

-- ── ncr_reports ────────────────────────────────────────────────────────────
ALTER TABLE ncr_reports
    ADD COLUMN IF NOT EXISTS scope_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS scope_work_center_id UUID REFERENCES work_centers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ncr_reports_scope_site
    ON ncr_reports (tenant_id, scope_site_id);

-- ── non_conformances (extended NCR table) ─────────────────────────────────
ALTER TABLE non_conformances
    ADD COLUMN IF NOT EXISTS scope_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS scope_work_center_id UUID REFERENCES work_centers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_non_conformances_scope_site
    ON non_conformances (tenant_id, scope_site_id);

-- ── capas ──────────────────────────────────────────────────────────────────
ALTER TABLE capas
    ADD COLUMN IF NOT EXISTS scope_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS scope_work_center_id UUID REFERENCES work_centers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_capas_scope_site
    ON capas (tenant_id, scope_site_id);

-- ── quality_audits ─────────────────────────────────────────────────────────
ALTER TABLE quality_audits
    ADD COLUMN IF NOT EXISTS scope_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS scope_work_center_id UUID REFERENCES work_centers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_quality_audits_scope_site
    ON quality_audits (tenant_id, scope_site_id);

-- ── audits ─────────────────────────────────────────────────────────────────
ALTER TABLE audits
    ADD COLUMN IF NOT EXISTS scope_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS scope_work_center_id UUID REFERENCES work_centers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_audits_scope_site
    ON audits (tenant_id, scope_site_id);

-- ── inspections ────────────────────────────────────────────────────────────
ALTER TABLE inspections
    ADD COLUMN IF NOT EXISTS scope_site_id UUID REFERENCES sites(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS scope_work_center_id UUID REFERENCES work_centers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_inspections_scope_site
    ON inspections (tenant_id, scope_site_id);
