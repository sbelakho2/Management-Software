-- Reconcile the `projects` table with the OPS service contract (the
-- service model is canonical): the service persists project_code, category,
-- owner_id, team_members, planned/actual dates, budget and savings_realized.
-- Old semantic columns are NEVER destroyed in the same migration — they
-- stay (defaulted) until the app has fully cut over (EXPAND -> BACKFILL ->
-- VALIDATE -> CONSTRAINT -> CUT OVER -> CONTRACT in a later migration).
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS project_code VARCHAR(50) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS category VARCHAR(100) NOT NULL DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS team_members JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS planned_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS planned_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_start TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS budget NUMERIC(19,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS savings_realized NUMERIC(19,4) NOT NULL DEFAULT 0;
