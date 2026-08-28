-- Restart authorization for critical-safety Andons (hard rule: the line
-- stays stopped until an authorized restart exists).
ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS restart_authorized_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS restart_authorized_at TIMESTAMPTZ;
