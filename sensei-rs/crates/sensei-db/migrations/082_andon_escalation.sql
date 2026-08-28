-- Andon SLA escalation (closed-loop): the same issue escalates upward with
-- its escalation lineage recorded.
ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS escalated_to VARCHAR(100);
