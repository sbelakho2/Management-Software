-- A3 becomes evidence-native: beyond the seven text boxes, cases carry
-- structured observed conditions, metric baselines, evidence references,
-- cause hypotheses, experiments, verifications, standardizations and
-- learnings. AI can then distinguish OBSERVATION from DERIVED FACT from
-- HYPOTHESIS — and an A3 cannot close on text alone.
ALTER TABLE a3_reports
    ADD COLUMN IF NOT EXISTS observed_conditions JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS metric_baselines JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS evidence_refs JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS cause_hypotheses JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS experiments JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS verifications JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS standardizations JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS learnings JSONB NOT NULL DEFAULT '[]';
