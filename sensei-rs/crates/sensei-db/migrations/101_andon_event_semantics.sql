-- Andon event semantics (items 47/48): detection latency must measure
-- WHEN THE ABNORMAL CONDITION WAS OBSERVED, not "first production event
-- of the day" — and containment (customer/process risk controlled) is a
-- DIFFERENT timestamp from resolution (root cause fixed).
ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS abnormal_condition_observed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS contained_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS contained_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS contained_note TEXT;
