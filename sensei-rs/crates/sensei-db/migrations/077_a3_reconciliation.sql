-- A3 service/schema reconciliation (P0-3): the ops service queries
-- current_state/goal/root_cause_analysis/countermeasures/check_plan/
-- severity/version/evidence columns that 002 never created; its status
-- values ('draft','active','implemented','verified','closed','voided')
-- are not in 002's CHECK; and optimistic concurrency must be persisted.
-- EXPAND -> BACKFILL -> VALIDATE -> CONSTRAINT -> CUT OVER (old columns
-- are kept, defaulted, and contracted in a later migration).

ALTER TABLE a3_reports
    ADD COLUMN IF NOT EXISTS current_state TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS root_cause_analysis TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS countermeasures TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS check_plan TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS version BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS observed_conditions JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS metric_baselines JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS evidence_refs JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS cause_hypotheses JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS experiments JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS verifications JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS standardizations JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS learnings JSONB NOT NULL DEFAULT '[]';

-- The ops service status vocabulary (incl. 'voided' for append-only
-- retention) replaces the 002 CHECK.
ALTER TABLE a3_reports DROP CONSTRAINT IF EXISTS a3_reports_status_check;
ALTER TABLE a3_reports
    ADD CONSTRAINT a3_reports_status_check
    CHECK (status IN ('draft', 'active', 'implemented', 'verified', 'closed', 'voided'));

-- The ops service a3_type vocabulary (002 allowed problem_solving/
-- proposal/status/kaizen; the ops default is 'standard').
ALTER TABLE a3_reports DROP CONSTRAINT IF EXISTS a3_reports_a3_type_check;
ALTER TABLE a3_reports
    ADD CONSTRAINT a3_reports_a3_type_check
    CHECK (a3_type IN ('standard', 'safety', 'quality', 'problem_solving', 'proposal', 'status', 'kaizen'));
