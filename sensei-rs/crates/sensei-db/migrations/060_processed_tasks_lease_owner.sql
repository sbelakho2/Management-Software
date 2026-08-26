-- Lease ownership: every in-progress claim records WHO holds it. The
-- atomic acquisition returns the row ONLY when the claimant actually
-- acquired the lease; a competing worker sees no row and backs off.
ALTER TABLE processed_tasks
    ADD COLUMN IF NOT EXISTS lease_owner UUID,
    ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0;
