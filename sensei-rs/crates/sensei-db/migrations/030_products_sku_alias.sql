-- Product SKU alias.
--
-- The products table historically stores the product number in
-- `product_number`; the domain model calls the same value `sku`. This
-- migration adds a generated `sku` column that mirrors `product_number`,
-- making the mapping explicit in the schema while the application keeps
-- reading/writing `product_number`.

ALTER TABLE products ADD COLUMN IF NOT EXISTS sku VARCHAR(50) GENERATED ALWAYS AS (product_number) STORED;

CREATE INDEX IF NOT EXISTS idx_products_sku ON products (tenant_id, sku);
