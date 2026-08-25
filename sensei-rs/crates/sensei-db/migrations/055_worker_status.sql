-- Worker process status and readiness surface.
--
-- Worker processes (the sensei-workers binary and any future service) upsert
-- a heartbeat row here so operators and health checks can see, per worker
-- type, whether the process is subscribed to JetStream, whether it holds the
-- scheduler leadership advisory lock, and when it last reported.
--
-- `instance_id` distinguishes multiple replicas of the same worker type
-- (e.g. two worker pods), matching the `instance` field the binary reports.

CREATE TABLE IF NOT EXISTS worker_status (
    worker_name TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    subscribed BOOLEAN NOT NULL DEFAULT FALSE,
    is_leader BOOLEAN NOT NULL DEFAULT FALSE,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_worker_status_heartbeat
    ON worker_status (last_heartbeat);
