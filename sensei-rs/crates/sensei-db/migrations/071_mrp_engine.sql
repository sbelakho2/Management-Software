-- Real MRP inputs: lead time, safety stock, lot sizing (0 = lot-for-lot).
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS lead_time_days INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS safety_stock NUMERIC(20,6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS lot_size NUMERIC(20,6) NOT NULL DEFAULT 0;

-- Immutable MRP run snapshots: every run persists its inputs (demands,
-- inventory, scheduled receipts) and results so historic runs are
-- reproducible — an old result never changes because today's stock moved.
CREATE TABLE IF NOT EXISTS mrp_runs (
    id             UUID PRIMARY KEY,
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id     UUID NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'completed',
    input_snapshot JSONB NOT NULL DEFAULT '{}',
    result         JSONB NOT NULL DEFAULT '[]',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mrp_runs_tenant_product
    ON mrp_runs (tenant_id, product_id, created_at DESC);
