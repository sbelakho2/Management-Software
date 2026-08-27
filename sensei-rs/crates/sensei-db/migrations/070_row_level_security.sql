-- Row Level Security: a second barrier beyond application tenant filters.
--
-- Every tenant-owned table gets RLS enabled with a policy that filters on
-- the transaction-scoped context `app.tenant_id` (set via
-- `SET LOCAL app.tenant_id = '<uuid>'` inside critical transactions).
--
-- Compatibility rule: when the context is UNSET the policy allows access
-- (status quo for paths not yet migrated to set the context); when it IS
-- set, ONLY the matching tenant is visible. A tool bug that forgets
-- `WHERE tenant_id = ...` therefore cannot read another tenant as soon as
-- the calling path sets the context.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users', 'invoices', 'payments', 'budgets', 'journal_entries',
        'cost_rollups', 'work_orders', 'production_orders',
        'production_events', 'stock_moves', 'purchase_orders',
        'sales_orders', 'customer_invoices', 'supplier_invoices',
        'business_audit_log', 'outbox_events', 'maintenance_occurrences',
        'a3_reports', 'andons', 'chat_conversations', 'chat_messages',
        'scheduler_run_log', 'processed_tasks'
    ] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
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
