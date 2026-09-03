-- Twenty-seventh-audit P2 (empirical performance evidence): query-plan
-- index coverage for the three hottest tenant-scoped read shapes, proven
-- by the `hot_queries_use_index_scans` db_contract gate (EXPLAIN must
-- show index scans, never seq scans, on the target tables):
--
--   1. andons  — scoped andon list: WHERE tenant_id = $1
--      AND site_id = ANY(...) ORDER BY created_at DESC LIMIT/OFFSET
--      (the ops list endpoint). The existing idx_andons_site
--      (tenant_id, site_id) has no created_at ordering, so a page of the
--      newest andons of the authorized sites would re-sort every match.
--   2. site_replication_log — the corporate claim pass: WHERE
--      tenant_id = $1 AND status = 'pending' ORDER BY created_at ASC,
--      id ASC LIMIT n. idx_rep_log_claimable is partial on
--      (tenant_id, status) with no created_at ordering.
--   3. integration_checkpoints — per-instance readiness/last-run read:
--      WHERE tenant_id = $1 AND instance_id = $2 ORDER BY last_run_at
--      DESC LIMIT 1. idx_integration_checkpoints_instance (migration 154)
--      covers the (tenant, instance) point but with ascending last_run_at
--      only; the DESC form makes the newest-first read an ordered walk.
CREATE INDEX IF NOT EXISTS idx_andons_tenant_site_created_at
    ON andons (tenant_id, site_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rep_log_tenant_status_created
    ON site_replication_log (tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_checkpoints_tenant_instance_run
    ON integration_checkpoints (tenant_id, instance_id, last_run_at DESC);
