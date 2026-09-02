-- OTD commitment anchors (eighteenth audit item P1-8): OtdV1 used to be a
-- delivery-completion ratio (delivered/eligible) that reported 100% even
-- when every shipment was months late. The metric is now REAL on-time
-- delivery: actual_delivery_date <= committed_date. The columns added
-- here are the COMMITMENT anchors; delivered_at / shipped_at (migration
-- 133) remain the CANONICAL shipment stamps.
--
-- ANTI-GAMING RULE (executable, not just a comment): committed_date and
-- original_requested_date are written ONCE at first confirmation and
-- NEVER updated by later edits — enforced by COALESCE in the executable
-- status-transition path (update_sales_order_status), so the OTD metric
-- can never be improved by rewriting dates afterwards.
ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS original_requested_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS committed_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS commitment_revision INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS customer_change_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_ship_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS actual_delivery_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS fulfilling_site_id UUID,
    ADD COLUMN IF NOT EXISTS quantity_due NUMERIC NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quantity_delivered NUMERIC NOT NULL DEFAULT 0;
