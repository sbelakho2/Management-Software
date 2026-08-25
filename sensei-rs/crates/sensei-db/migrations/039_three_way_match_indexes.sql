-- AP 3-way matching indexes.
--
-- The finance 3-way match verifies receipts against purchase orders and
-- loads PO lines per order; these indexes keep those lookups fast.

CREATE INDEX IF NOT EXISTS idx_goods_receipts_po_tenant
    ON goods_receipts (tenant_id, purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_po_items_order
    ON purchase_order_items (purchase_order_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice
    ON payments (tenant_id, invoice_id);
