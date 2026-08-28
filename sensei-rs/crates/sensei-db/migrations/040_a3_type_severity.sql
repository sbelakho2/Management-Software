-- Add problem-solving discipline and severity metadata to A3 reports.
-- 002_domain_tables.sql already creates a3_type (VARCHAR(30) + CHECK), so a
-- fresh migration chain must not re-add it without IF NOT EXISTS.
ALTER TABLE a3_reports
    ADD COLUMN IF NOT EXISTS a3_type TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS severity TEXT NOT NULL DEFAULT '';
