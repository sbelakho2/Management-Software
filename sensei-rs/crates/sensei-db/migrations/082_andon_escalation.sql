-- Andon SLA escalation (closed-loop): the same issue escalates upward with
-- its escalation lineage recorded.
DO $$
BEGIN
    IF to_regclass('andons') IS NULL THEN
        RETURN;
    END IF;
    EXECUTE 'ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS escalated_to VARCHAR(100)';
END $$;
