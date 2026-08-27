-- Production truth: scrap must never vanish and completion must never
-- fabricate output.
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS quantity_scrapped BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS short_close_qty BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS short_close_reason TEXT,
    ADD COLUMN IF NOT EXISTS short_close_approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS short_close_at TIMESTAMPTZ;

ALTER TABLE production_orders
    ADD COLUMN IF NOT EXISTS short_close_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS short_close_reason TEXT,
    ADD COLUMN IF NOT EXISTS short_close_approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS short_close_at TIMESTAMPTZ;
