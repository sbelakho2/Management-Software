-- Stock movement and inventory indexes.
--
-- Support the inventory turnover aggregate (stock_moves scanned by move
-- type and date per product) and location-scoped inventory lookups used by
-- the receiving flow.

CREATE INDEX IF NOT EXISTS idx_stock_moves_product_date
    ON stock_moves (product_id, moved_at);
CREATE INDEX IF NOT EXISTS idx_inventory_items_product_location
    ON inventory_items (tenant_id, product_id, location);
