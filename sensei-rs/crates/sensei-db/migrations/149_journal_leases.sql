-- Command journal leases + recovery (twentieth audit P1): a claim now
-- carries an OWNER, a FENCING TOKEN and a LEASE. A process crash after
-- reservation previously left a row permanently 'reserved' — now the
-- lease expires and recover() reclaims it. 'executing' becomes a REAL
-- leased state (recovery/attempt >= 2). A network timeout after dispatch
-- records 'unknown_outcome'/'reconcile_required' — the mutation MAY have
-- happened — instead of a plain retryable failure, and such rows are
-- immediately recoverable by the next worker. complete()/heartbeat() are
-- token-fenced: a stale owner can never finish or renew a claim another
-- worker recovered.
ALTER TABLE command_journal
    ADD COLUMN IF NOT EXISTS claim_owner      VARCHAR(100),
    ADD COLUMN IF NOT EXISTS claim_token      VARCHAR(64),
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS attempt          INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS last_heartbeat   TIMESTAMPTZ;
-- Rebuild the status constraint with the reconciliation states.
ALTER TABLE command_journal
    DROP CONSTRAINT IF EXISTS command_journal_status_check;
ALTER TABLE command_journal
    ADD CONSTRAINT command_journal_status_check
    CHECK (status IN ('reserved', 'executing', 'succeeded', 'failed',
                      'unknown_outcome', 'reconcile_required'));
