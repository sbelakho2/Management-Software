-- Scheduled-run deduplication for the leader-elected task scheduler.
--
-- Only the scheduler leader (PostgreSQL advisory lock, see scheduler.rs)
-- runs the schedule loops. When a leader dies, a follower takes over after
-- the advisory lock is released on connection close; the takeover must not
-- re-run a schedule slot that the dead leader already fired.
--
-- Each scheduled fire is claimed by (task_type, run_key) where run_key is
-- the wall-clock slot (e.g. "2026-08-25T02:00" for daily@02:00). The leader
-- inserts the row BEFORE publishing the task message and only publishes when
-- the insert succeeds, so a takeover never double-publishes a slot and a
-- crash between insert and publish simply skips that slot.

CREATE TABLE IF NOT EXISTS scheduler_run_log (
    task_type TEXT NOT NULL,
    run_key TEXT NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_type, run_key)
);

CREATE INDEX IF NOT EXISTS idx_scheduler_run_log_executed_at
    ON scheduler_run_log (executed_at);
