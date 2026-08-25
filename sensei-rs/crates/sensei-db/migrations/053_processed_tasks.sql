-- Task idempotency: records which worker tasks have already been executed.
--
-- Side-effecting workers (email, pdf, ml, analytics) claim the task_id
-- BEFORE performing the side effect: `INSERT ... ON CONFLICT DO NOTHING`
-- succeeds only once per task_id. A redelivered or duplicated message is
-- then skipped (and acked) instead of executing the side effect twice.
--
-- `seq` is a monotonically increasing observability counter for processing
-- order; `worker` records which worker type executed the task.

CREATE TABLE IF NOT EXISTS processed_tasks (
    task_id TEXT PRIMARY KEY,
    worker TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    seq BIGSERIAL
);

CREATE INDEX IF NOT EXISTS idx_processed_tasks_worker_processed_at
    ON processed_tasks (worker, processed_at);
