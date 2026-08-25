-- Product stock and catalog extensions.

ALTER TABLE products ADD COLUMN IF NOT EXISTS max_stock_level DOUBLE PRECISION;
ALTER TABLE products ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE INDEX IF NOT EXISTS idx_products_stock_level
    ON products (tenant_id, quantity_on_hand) WHERE quantity_on_hand IS NOT NULL;
