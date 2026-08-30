-- Frozen manufacturing configuration on the work order (thirteenth audit
-- P0): a RELEASED work order must persist the exact configuration it was
-- released under — not "whatever is currently latest". Every revision is
-- frozen at release and immutable for the duration of the order unless an
-- explicit controlled deviation authorizes a change.
--
--   standard_work_id            (added in 102) — exact Standard Work revision
--   product_revision_id         — product master revision
--   bom_revision_id             — the BOM revision exploded at release
--   routing_revision_id         — the routing revision used for operations
--   control_plan_revision_id    — the control plan in force at release
--   ctq_characteristic_set      — the CTQ/characteristic set bound to the
--                                 released order (JSONB snapshot of ids)
--   tooling_revision            — fixture/tool/program revision reference
--   source_sales_order_line_id  — demand pegging at LINE granularity
--                                 (item: whole-order FK is not granular
--                                 enough for partial/mixed fulfillment)
--   customer_requirement_revision — customer spec/contract revision
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS product_revision_id UUID,
    ADD COLUMN IF NOT EXISTS bom_revision_id UUID,
    ADD COLUMN IF NOT EXISTS routing_revision_id UUID,
    ADD COLUMN IF NOT EXISTS control_plan_revision_id UUID,
    ADD COLUMN IF NOT EXISTS ctq_characteristic_set JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS tooling_revision VARCHAR(100),
    ADD COLUMN IF NOT EXISTS source_sales_order_line_id UUID,
    ADD COLUMN IF NOT EXISTS customer_requirement_revision VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_work_orders_frozen_bom
    ON work_orders (tenant_id, bom_revision_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_frozen_routing
    ON work_orders (tenant_id, routing_revision_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_so_line
    ON work_orders (tenant_id, source_sales_order_line_id);
