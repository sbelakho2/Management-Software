-- Scheduler slot lease: a claimed slot is NOT "finished" — it is
-- 'claimed' with a lease. Only a successful publication marks it
-- 'published'. A crashed scheduler leaves 'claimed' slots whose lease
-- expires, so another replica can reclaim and publish them (a scheduled
-- job is never permanently skipped by a crash between claim and publish).
ALTER TABLE scheduler_run_log
    ADD COLUMN IF NOT EXISTS state TEXT NOT NULL DEFAULT 'published'
        CHECK (state IN ('claimed', 'published')),
    ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS lease_owner UUID;
