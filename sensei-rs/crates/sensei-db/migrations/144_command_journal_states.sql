-- Command journal state machine (nineteenth audit P1): reserve() inserts
-- a row with status='reserved' (ON CONFLICT DO NOTHING) so exactly one
-- concurrent caller claims an execution key; the winner dispatches and
-- complete() transitions the row to 'succeeded' or 'failed'. A duplicate
-- loads the row and replays/conflicts instead of re-executing. Pre-existing
-- rows (completed executions from migration 142) get the 'succeeded'
-- default — they are finished executions.
ALTER TABLE command_journal
    ADD COLUMN IF NOT EXISTS status     VARCHAR(20) NOT NULL DEFAULT 'succeeded',
    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
ALTER TABLE command_journal
    ADD CONSTRAINT command_journal_status_check
    CHECK (status IN ('reserved', 'executing', 'succeeded', 'failed'));
