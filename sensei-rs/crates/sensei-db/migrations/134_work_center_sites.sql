-- Work centers belong to SITES (seventeenth audit item 6/12): the typed
-- WorkCenterScope is DB-resolved from work_centers.site_id, so
-- { site: Bizerte, work_center: <Tangier line 2> } is unconstructible.
-- Backfill: derive the site from employee_assignments (the historical
-- user -> (site, work_center) assignments), then fall back to the
-- tenant's earliest site so existing rows keep a valid parent.
ALTER TABLE work_centers ADD COLUMN IF NOT EXISTS site_id UUID;

UPDATE work_centers wc
SET site_id = derived.site_id
FROM (
    SELECT DISTINCT ON (ea.work_center_id) ea.work_center_id, ea.site_id
    FROM employee_assignments ea
    WHERE ea.work_center_id IS NOT NULL AND ea.site_id IS NOT NULL
    ORDER BY ea.work_center_id, ea.created_at ASC
) derived
WHERE wc.id = derived.work_center_id AND wc.site_id IS NULL;

UPDATE work_centers wc
SET site_id = first_site.id
FROM (
    SELECT DISTINCT ON (s.tenant_id) s.tenant_id, s.id
    FROM sites s
    ORDER BY s.tenant_id, s.created_at ASC
) first_site
WHERE wc.site_id IS NULL AND first_site.tenant_id = wc.tenant_id;

ALTER TABLE work_centers
    ADD CONSTRAINT work_centers_tenant_site_fk
    FOREIGN KEY (tenant_id, site_id) REFERENCES sites(tenant_id, id)
    NOT VALID;

-- Only enforced for rows that have a site (defensive); a tenant with no
-- sites and no assignments keeps NULL site_id rows valid until a site is
-- provisioned.
ALTER TABLE work_centers VALIDATE CONSTRAINT work_centers_tenant_site_fk;
