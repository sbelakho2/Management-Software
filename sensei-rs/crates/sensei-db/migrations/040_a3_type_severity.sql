-- Add problem-solving discipline and severity metadata to A3 reports.
ALTER TABLE a3_reports
    ADD COLUMN a3_type TEXT NOT NULL DEFAULT '',
    ADD COLUMN severity TEXT NOT NULL DEFAULT '';
