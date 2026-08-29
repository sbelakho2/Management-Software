-- Sales-flow linkage (item 37): products need their value-stream family
-- and primary supplier so sales impact can compute capacity effect and
-- supplier dependencies — a quote must answer what the system can
-- deliver, not just a price.
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS product_family_id UUID,
    ADD COLUMN IF NOT EXISTS primary_supplier_id UUID;
