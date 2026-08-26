-- Systematic same-tenant relationship integrity: every tenant-owned child
-- reference must point at a parent of the SAME tenant. Composite FKs make
-- cross-tenant references impossible even if the application has a bug.
-- (Parent UNIQUE(tenant_id, id) + child FK (tenant_id, fk) -> parent.)

-- Parent uniqueness supports.
CREATE UNIQUE INDEX IF NOT EXISTS accounts_tenant_id_id_unique ON accounts (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS suppliers_tenant_id_id_unique ON suppliers (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS sales_orders_tenant_id_id_unique ON sales_orders (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS purchase_orders_tenant_id_id_unique ON purchase_orders (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS invoices_tenant_id_id_unique ON invoices (tenant_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS journal_entries_tenant_id_id_unique ON journal_entries (tenant_id, id);

-- payments.invoice_id must belong to the same tenant as the payment.
ALTER TABLE payments
    DROP CONSTRAINT IF EXISTS payments_invoice_id_tenant_fk;
ALTER TABLE payments
    ADD CONSTRAINT payments_invoice_id_tenant_fk
    FOREIGN KEY (tenant_id, invoice_id)
    REFERENCES invoices (tenant_id, id)
    ON DELETE SET NULL;

-- sales_orders.customer_id must belong to the same tenant.
ALTER TABLE sales_orders
    DROP CONSTRAINT IF EXISTS sales_orders_customer_id_tenant_fk;
ALTER TABLE sales_orders
    ADD CONSTRAINT sales_orders_customer_id_tenant_fk
    FOREIGN KEY (tenant_id, customer_id)
    REFERENCES accounts (tenant_id, id)
    ON DELETE CASCADE;

-- purchase_orders.supplier_id must belong to the same tenant.
ALTER TABLE purchase_orders
    DROP CONSTRAINT IF EXISTS purchase_orders_supplier_id_tenant_fk;
ALTER TABLE purchase_orders
    ADD CONSTRAINT purchase_orders_supplier_id_tenant_fk
    FOREIGN KEY (tenant_id, supplier_id)
    REFERENCES suppliers (tenant_id, id)
    ON DELETE CASCADE;

-- journal_entries.reversal_of must reference a same-tenant entry.
ALTER TABLE journal_entries
    DROP CONSTRAINT IF EXISTS journal_entries_reversal_of_tenant_fk;
ALTER TABLE journal_entries
    ADD CONSTRAINT journal_entries_reversal_of_tenant_fk
    FOREIGN KEY (tenant_id, reversal_of)
    REFERENCES journal_entries (tenant_id, id)
    ON DELETE SET NULL;

-- customer_invoices.customer_id must belong to the same tenant.
ALTER TABLE customer_invoices
    DROP CONSTRAINT IF EXISTS customer_invoices_customer_id_tenant_fk;
ALTER TABLE customer_invoices
    ADD CONSTRAINT customer_invoices_customer_id_tenant_fk
    FOREIGN KEY (tenant_id, customer_id)
    REFERENCES accounts (tenant_id, id)
    ON DELETE CASCADE;

-- supplier_invoices.supplier_id must belong to the same tenant.
ALTER TABLE supplier_invoices
    DROP CONSTRAINT IF EXISTS supplier_invoices_supplier_id_tenant_fk;
ALTER TABLE supplier_invoices
    ADD CONSTRAINT supplier_invoices_supplier_id_tenant_fk
    FOREIGN KEY (tenant_id, supplier_id)
    REFERENCES suppliers (tenant_id, id)
    ON DELETE CASCADE;
