-- Operational scope (fifteenth audit A1): every operational object is
-- explicitly scoped to site/area/line/cell — never implicitly company-wide.
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS site_id UUID,
    ADD COLUMN IF NOT EXISTS area_id UUID,
    ADD COLUMN IF NOT EXISTS line_id UUID,
    ADD COLUMN IF NOT EXISTS cell_id UUID;
ALTER TABLE andons
    ADD COLUMN IF NOT EXISTS site_id UUID,
    ADD COLUMN IF NOT EXISTS area_id UUID,
    ADD COLUMN IF NOT EXISTS line_id UUID,
    ADD COLUMN IF NOT EXISTS cell_id UUID;
ALTER TABLE production_events
    ADD COLUMN IF NOT EXISTS site_id UUID;
ALTER TABLE work_order_operations
    ADD COLUMN IF NOT EXISTS site_id UUID;
ALTER TABLE inventory_items
    ADD COLUMN IF NOT EXISTS site_id UUID;
ALTER TABLE operational_conditions
    ADD COLUMN IF NOT EXISTS site_id UUID,
    ADD COLUMN IF NOT EXISTS area_id UUID,
    ADD COLUMN IF NOT EXISTS line_id UUID,
    ADD COLUMN IF NOT EXISTS cell_id UUID;
ALTER TABLE ctq_characteristics
    ADD COLUMN IF NOT EXISTS site_id UUID;
ALTER TABLE standard_work_documents
    ADD COLUMN IF NOT EXISTS site_id UUID;
CREATE INDEX IF NOT EXISTS idx_work_orders_site ON work_orders (tenant_id, site_id);
CREATE INDEX IF NOT EXISTS idx_andons_site ON andons (tenant_id, site_id);
CREATE INDEX IF NOT EXISTS idx_prod_events_site ON production_events (tenant_id, site_id);
