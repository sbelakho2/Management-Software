-- Composite cursor (fourteenth audit): a timestamp-only watermark loses
-- records when > batch-size rows share the same updated_at. The cursor
-- is (updated_at, primary_key) — the bridge persists both and advances
-- only past terminally-handled records.
ALTER TABLE integration_checkpoints
    ADD COLUMN IF NOT EXISTS watermark_id VARCHAR(100);
