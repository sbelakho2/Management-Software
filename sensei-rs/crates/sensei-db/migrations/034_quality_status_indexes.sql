-- Quality status indexes.
--
-- The ncr_reports / capas tables carry quality workflow state in plain
-- `status` columns; these indexes speed up status-filtered queries
-- (including the analytics worker's open-NCR/CAPA counts). Earlier drafts
-- referenced a JSONB-backed quality_ncrs / quality_capas pair that does
-- not exist in the schema.

CREATE INDEX IF NOT EXISTS idx_ncr_reports_status
    ON ncr_reports (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_capas_status
    ON capas (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_ncr_reports_number
    ON ncr_reports (tenant_id, ncr_number);
CREATE INDEX IF NOT EXISTS idx_capas_number
    ON capas (tenant_id, capa_number);
