-- Standard Work → product binding (thirteenth audit P0): release must
-- freeze the EXACT effective standard for the product — the resolution
-- needs a real product link, not a tenant-wide "latest" pick.
ALTER TABLE standard_work_documents
    ADD COLUMN IF NOT EXISTS product_id UUID REFERENCES products(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_swd_product_effective
    ON standard_work_documents (tenant_id, product_id, status);
