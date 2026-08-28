-- Restart authorization for critical-safety Andons (hard rule: the line
-- stays stopped until an authorized restart exists).
-- The andons table itself is created in migration 088 (it was missing from
-- the chain); this migration heals the column set when the table already
-- exists and no-ops otherwise.
DO $$
BEGIN
    IF to_regclass('andons') IS NULL THEN
        RETURN;
    END IF;
    EXECUTE 'ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS restart_authorized_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS restart_authorized_at TIMESTAMPTZ';
END $$;
