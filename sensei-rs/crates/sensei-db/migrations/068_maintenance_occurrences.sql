-- Maintenance evidence ledger: every PM completion records an occurrence
-- so work can be verified (Leader Standard Work / TPM agent), not merely
-- inferred from a rolled-forward next_due date.
CREATE TABLE IF NOT EXISTS maintenance_occurrences (
    id               UUID PRIMARY KEY,
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    schedule_id      UUID REFERENCES pm_schedules(id) ON DELETE SET NULL,
    equipment_id     UUID NOT NULL,
    occurrence_type  VARCHAR(30) NOT NULL
                     CHECK (occurrence_type IN ('pm_completion', 'work_request', 'corrective', 'return_to_service')),
    technician_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    actual_start_at  TIMESTAMPTZ,
    actual_end_at    TIMESTAMPTZ,
    findings         TEXT NOT NULL DEFAULT '',
    parts_used       JSONB NOT NULL DEFAULT '[]',
    labor_minutes    INT NOT NULL DEFAULT 0,
    downtime_minutes INT NOT NULL DEFAULT 0,
    return_to_service BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_maintenance_occurrences_tenant_equipment
    ON maintenance_occurrences (tenant_id, equipment_id, created_at DESC);
