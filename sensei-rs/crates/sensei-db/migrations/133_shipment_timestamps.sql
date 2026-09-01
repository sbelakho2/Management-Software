-- Immutable shipment timestamps (sixteenth audit item 25): OTD and lead
-- time need HISTORICAL anchors that cannot be rewritten by a later
-- update to the order row. updated_at changes after shipment, so it is
-- not a lead-time source.
ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS released_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS shipped_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMPTZ;
