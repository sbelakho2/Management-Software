-- Equipment maintenance lifecycle columns.
--
-- Adds the maintenance tracking fields used by the maintenance service:
-- `last_maintenance` is stamped when equipment enters `under_maintenance`,
-- `maintenance_completed_at` when it returns to `operational`, and
-- `oee_percentage` for effectiveness tracking. The status check is
-- extended with `decommissioned` so domain values round-trip cleanly.

ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_status_check;
ALTER TABLE equipment ADD CONSTRAINT equipment_status_check
    CHECK (status IN ('operational', 'under_maintenance', 'out_of_service', 'retired', 'decommissioned'));

ALTER TABLE equipment ADD COLUMN IF NOT EXISTS last_maintenance TIMESTAMPTZ;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS maintenance_completed_at TIMESTAMPTZ;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS oee_percentage DOUBLE PRECISION NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_equipment_maintenance
    ON equipment (tenant_id, status) WHERE status = 'under_maintenance';
