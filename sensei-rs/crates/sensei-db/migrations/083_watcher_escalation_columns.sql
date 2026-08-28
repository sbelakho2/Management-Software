-- Watcher escalation markers (dedupe: each overdue item escalates once).
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ;
ALTER TABLE pm_schedules
    ADD COLUMN IF NOT EXISTS pm_escalated_at TIMESTAMPTZ;
