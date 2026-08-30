-- Work-order → standard-work immutable binding (item 39): a RELEASED
-- production order carries the exact standard revision it was released
-- under, for the duration of the order. The station resolves takt/steps
-- through THIS reference — a newer published revision never silently
-- changes what the operator is building against.
ALTER TABLE work_orders
    ADD COLUMN IF NOT EXISTS standard_work_id UUID
        REFERENCES standard_work_documents(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_work_orders_standard
    ON work_orders (tenant_id, standard_work_id);
