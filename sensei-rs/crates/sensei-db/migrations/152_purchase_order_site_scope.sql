-- Receiving-site dimension for purchase orders (twentieth audit P1/P2):
-- procurement is a SITE operation — a PO is bought FOR a plant. With
-- receiving_site_id the buyer analytics can be scoped honestly instead
-- of failing closed with not_available_site_required.
ALTER TABLE purchase_orders
    ADD COLUMN IF NOT EXISTS receiving_site_id UUID REFERENCES sites(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_purchase_orders_site
    ON purchase_orders (tenant_id, receiving_site_id);
