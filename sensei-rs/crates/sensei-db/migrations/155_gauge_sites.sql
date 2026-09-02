-- Site-linked calibration proof (twenty-first audit item 13): gauges are
-- owned by SITES, so a passing calibration on a gauge assigned to another
-- plant can never certify THIS site's capability readiness.
ALTER TABLE gauges
    ADD COLUMN IF NOT EXISTS site_id UUID REFERENCES sites(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_gauges_site ON gauges (tenant_id, site_id);
