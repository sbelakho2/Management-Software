-- Andon escalation (item 41): the escalate action needs a REAL state —
-- an Andon escalated to tier review carries an escalated flag + timestamp,
-- surfaced by the team-lead and obeya surfaces.
ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS escalated BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ;
