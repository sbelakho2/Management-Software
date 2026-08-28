-- RLS hardening (P0-5): FORCE ROW LEVEL SECURITY so even the table OWNER
-- is subject to the policies (the Compose topology previously connected as
-- the owner, which PostgreSQL exempts from RLS — eliminating the barrier).
-- The critical accounting/audit/production tables get a FAIL-CLOSED policy:
-- when the transaction-scoped app.tenant_id context is missing, access is
-- DENIED. Their write paths set the context via SET LOCAL.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'invoices', 'payments', 'budgets', 'journal_entries', 'cost_rollups',
        'business_audit_log', 'outbox_events', 'production_events',
        'maintenance_occurrences', 'a3_reports', 'andons'
    ] LOOP
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'DROP POLICY IF EXISTS tenant_isolation ON %I', t
        );
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I
             USING (
                 tenant_id = current_setting(''app.tenant_id'', true)::uuid
             )',
            t
        );
    END LOOP;

    -- The remaining tenant tables keep the compatibility clause (context
    -- unset = visible) but are FORCED, so once a caller sets the context
    -- the filter applies to EVERYONE, including the owner.
    FOREACH t IN ARRAY ARRAY[
        'users', 'work_orders', 'production_orders', 'stock_moves',
        'purchase_orders', 'sales_orders', 'customer_invoices',
        'supplier_invoices', 'scheduler_run_log', 'processed_tasks'
    ] LOOP
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'DROP POLICY IF EXISTS tenant_isolation ON %I', t
        );
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I
             USING (
                 tenant_id = COALESCE(
                     NULLIF(current_setting(''app.tenant_id'', true), ''''),
                     ''00000000-0000-0000-0000-000000000000''
                 )::uuid
                 OR current_setting(''app.tenant_id'', true) = ''''
             )',
            t
        );
    END LOOP;
END $$;
