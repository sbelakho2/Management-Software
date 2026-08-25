-- PM schedule query indexes.
--
-- The maintenance worker computes hours since the last performed PM per
-- equipment (per-equipment schedule lookups), and the maintenance service
-- lists overdue schedules by next_due_at.

CREATE INDEX IF NOT EXISTS idx_pm_schedules_equipment_last
    ON pm_schedules (equipment_id, last_performed_at);
CREATE INDEX IF NOT EXISTS idx_pm_schedules_due
    ON pm_schedules (tenant_id, next_due_at) WHERE is_active = TRUE;
