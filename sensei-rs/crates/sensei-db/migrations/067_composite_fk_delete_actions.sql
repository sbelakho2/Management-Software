-- Composite tenant FKs must never use ON DELETE SET NULL on a NOT NULL
-- member: `FOREIGN KEY (tenant_id, invoice_id) ... ON DELETE SET NULL`
-- would try to null BOTH columns and fail on tenant_id. Deletion of paid
-- invoices is blocked at the service layer (immutable accounting objects);
-- for draft documents, child rows are meaningless without the parent, so
-- the composite references cascade.
ALTER TABLE payments
    DROP CONSTRAINT IF EXISTS payments_invoice_id_tenant_fk;
ALTER TABLE payments
    ADD CONSTRAINT payments_invoice_id_tenant_fk
    FOREIGN KEY (tenant_id, invoice_id)
    REFERENCES invoices (tenant_id, id)
    ON DELETE CASCADE;

ALTER TABLE journal_entries
    DROP CONSTRAINT IF EXISTS journal_entries_reversal_of_tenant_fk;
ALTER TABLE journal_entries
    ADD CONSTRAINT journal_entries_reversal_of_tenant_fk
    FOREIGN KEY (tenant_id, reversal_of)
    REFERENCES journal_entries (tenant_id, id)
    ON DELETE CASCADE;

ALTER TABLE customer_invoices
    DROP CONSTRAINT IF EXISTS customer_invoices_customer_id_tenant_fk;
ALTER TABLE customer_invoices
    ADD CONSTRAINT customer_invoices_customer_id_tenant_fk
    FOREIGN KEY (tenant_id, customer_id)
    REFERENCES accounts (tenant_id, id)
    ON DELETE CASCADE;

ALTER TABLE supplier_invoices
    DROP CONSTRAINT IF EXISTS supplier_invoices_supplier_id_tenant_fk;
ALTER TABLE supplier_invoices
    ADD CONSTRAINT supplier_invoices_supplier_id_tenant_fk
    FOREIGN KEY (tenant_id, supplier_id)
    REFERENCES suppliers (tenant_id, id)
    ON DELETE CASCADE;
