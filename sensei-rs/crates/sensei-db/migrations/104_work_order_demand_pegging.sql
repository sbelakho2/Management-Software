-- Demand pegging (item 31): a work order generated from a sales-order
-- line carries the SO it serves, so MRP knows which supply is already
-- allocated against which demand — instead of combining demand and
-- backlog with the max() heuristic that cannot distinguish "in-flight
-- SO supply" from "independent internal work".
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS source_sales_order_id UUID
        REFERENCES sales_orders(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_work_orders_so_source
    ON work_orders (tenant_id, source_sales_order_id);
