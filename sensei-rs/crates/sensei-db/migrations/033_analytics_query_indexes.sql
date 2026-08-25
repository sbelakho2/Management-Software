-- Analytics query indexes.
--
-- Support the time-bounded aggregates used by the analytics worker:
-- completed work orders per day, quality NCR counts per day, paid
-- invoices per day, and sales order line-item scans.
--
-- Column notes (matching the real schema):
--   * work_orders has no completed_at: 'completed' is a status
--     transition via UPDATE, so updated_at is the completion timestamp.
--   * quality state lives in ncr_reports / capas (plain status columns);
--     there is no quality_ncrs / quality_capas pair.
--   * invoices has no paid_at: updated_at records the payment transition.

CREATE INDEX IF NOT EXISTS idx_work_orders_completed_date
    ON work_orders (tenant_id, updated_at) WHERE status = 'completed';
CREATE INDEX IF NOT EXISTS idx_ncr_reports_created_date
    ON ncr_reports (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ncr_reports_updated_date
    ON ncr_reports (tenant_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_invoices_paid_date
    ON invoices (tenant_id, updated_at) WHERE status = 'paid';
CREATE INDEX IF NOT EXISTS idx_sales_orders_created
    ON sales_orders (tenant_id, created_at);
