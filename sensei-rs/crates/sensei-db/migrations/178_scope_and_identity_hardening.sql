-- 178_scope_and_identity_hardening.sql
-- 1. Make existing Andon scope authoritative from work_centers.
UPDATE andons a SET site_id = wc.site_id FROM work_centers wc WHERE wc.tenant_id = a.tenant_id AND wc.id = a.work_center_id AND a.site_id IS DISTINCT FROM wc.site_id;
-- 2. Refuse migration if any Andon points at an invalid WC.
DO $$ BEGIN IF EXISTS (SELECT 1 FROM andons a LEFT JOIN work_centers wc ON wc.tenant_id = a.tenant_id AND wc.id = a.work_center_id WHERE wc.id IS NULL OR a.site_id IS NULL) THEN RAISE EXCEPTION 'Cannot harden andons: orphaned work_center_id or unresolved site_id exists'; END IF; END $$;
-- 3. Make the WC topology usable as one composite FK target.
ALTER TABLE work_centers ADD CONSTRAINT uq_work_centers_tenant_site_wc UNIQUE (tenant_id, site_id, id);
-- 4. No operational Andon may be site-less.
ALTER TABLE andons ALTER COLUMN site_id SET NOT NULL;
-- 5. One FK proves tenant + site + WC are mutually consistent.
ALTER TABLE andons ADD CONSTRAINT fk_andons_operational_scope FOREIGN KEY (tenant_id, site_id, work_center_id) REFERENCES work_centers (tenant_id, site_id, id) ON DELETE RESTRICT;
CREATE INDEX IF NOT EXISTS idx_andons_authorized_lookup ON andons (tenant_id, site_id, work_center_id, status, created_at DESC);
-- 6. A user must resolve to at most one employee record per tenant.
DO $$ BEGIN IF EXISTS (SELECT tenant_id, user_id FROM employees WHERE user_id IS NOT NULL GROUP BY tenant_id, user_id HAVING COUNT(*) > 1) THEN RAISE EXCEPTION 'Cannot harden employees: duplicate (tenant_id,user_id) mappings exist'; END IF; END $$;
CREATE UNIQUE INDEX IF NOT EXISTS uq_employees_tenant_user ON employees (tenant_id, user_id) WHERE user_id IS NOT NULL;
