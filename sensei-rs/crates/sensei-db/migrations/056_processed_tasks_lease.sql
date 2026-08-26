-- processed_tasks becomes a lease-based idempotency state machine.
-- A claim records in_progress + lease_until; only after the side effect
-- SUCCEEDS is the row flipped to completed. A transient failure leaves the
-- row in_progress; once the lease expires the next redelivery takes over —
-- a retry is never mistaken for an already-completed duplicate.
ALTER TABLE processed_tasks
    ADD COLUMN IF NOT EXISTS state TEXT NOT NULL DEFAULT 'in_progress',
    ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '5 minutes'),
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_processed_tasks_state ON processed_tasks (state);
