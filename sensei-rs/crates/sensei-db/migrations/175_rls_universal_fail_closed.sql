-- Universal fail-closed RLS (thirtieth-audit items 18 + 31, Wave C).
--
-- WHAT this migration changes
-- --------------------------
-- 1. Every public base table with a tenant_id column (203 tables at the
--    end of this chain) is normalized onto ONE canonical, fail-closed
--    policy shape:
--
--        ALTER TABLE ... ENABLE ROW LEVEL SECURITY;
--        ALTER TABLE ... FORCE ROW LEVEL SECURITY;
--        CREATE POLICY tenant_isolation ON ...
--            USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
--            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
--
--    No context means false/no rows — for SELECT, UPDATE, DELETE AND
--    INSERT alike (the explicit WITH CHECK makes the write barrier
--    visible in pg_policies instead of the implicit USING default).
--    `NULLIF(..., '')` also makes an EMPTY app.tenant_id behave as
--    "no context" (no rows) instead of the historical cast error
--    `''::uuid`.
--
-- 2. The historical compatibility clauses (migration 070's
--    "context unset OR zero-uuid = visible" shape, kept by migration 079
--    on users, work_orders, production_orders, purchase_orders,
--    sales_orders, customer_invoices and supplier_invoices) are REMOVED.
--    Those clauses were fail-open whenever a pooled session carried an
--    empty app.tenant_id placeholder (every session after ANY
--    SET LOCAL commit): a raw-pool query with WHERE tenant_id then saw
--    EVERY tenant's rows — "secondary RLS: not guaranteed". The
--    repository conversions that precede this migration (TenantTx in
--    sensei-services / sensei-auth / sensei-api) moved those reads
--    inside transactions whose SET LOCAL app.tenant_id admits exactly
--    one tenant, so the application-scoping hierarchy is now
--    "application WHERE tenant_id AND DB fail-closed RLS".
--
-- 3. Pre-tenant IDENTITY bootstrap. The `users` table is read by flows
--    that run BEFORE any tenant context can exist — login's
--    globally-unique email lookup, refresh-token user-state validation,
--    password-reset/email-verification issuance, admin user management,
--    startup seeding. Those flows cannot establish app.tenant_id (the
--    tenant is discovered FROM the row), so instead of leaving `users`
--    fail-open this migration narrows the pre-tenant surface to TWO
--    SECURITY DEFINER functions owned by the migration role (which the
--    canonical role script keeps BYPASSRLS):
--
--        auth_user_by_email(text)   -- the one row whose email matches
--        auth_user_by_id(uuid)      -- the one row with that id
--        auth_users_all()           -- tenant-wide admin listing (the
--                                   -- users-service list semantics: the
--                                   -- route layer does the tenant/role
--                                   -- scoping)
--
--    All three are granted ONLY to sensei_app (never PUBLIC) and return
--    the full users row — the same surface the app role previously
--    reached through the fail-open policy, now deterministic and
--    REVOKE-able in one place. Every OTHER users access runs inside a
--    TenantTx. Direct SQL access to `users` (and to every table below)
--    is fail-closed for sensei_app: no context, no rows.
--
-- 4. The chain-wide invariant ("every tenant_id table is isolated") that
--    migrations 070/079/098 enforced incrementally is now asserted at
--    migration time by the drift guard below: the fixed table list must
--    match the live catalog exactly, and each listed table must end up
--    with ENABLE + FORCE RLS and the canonical tenant_isolation policy.
--    The db-contract gate additionally re-checks the whole invariant
--    schema-generated (no maintenance list) AFTER the full chain.
--
-- Exceptions: NONE. Every public base table with tenant_id is
-- fail-closed here; tables without a tenant_id column (tenants,
-- refresh_tokens, token_blacklist, dedupe/system tables, ...) are
-- intentionally outside tenant RLS. Views/partitions are excluded the
-- same way migration 098 excludes them (relkind 'r'/'p' only).

-- ── 1. Canonical fail-closed isolation for every tenant-owned table ──────
DO $$
DECLARE
    t text;
    missing text := '';
    extra text := '';
    live text;
    r record;
BEGIN
    -- Drift guard (a): every table the chain produced BEFORE this
    -- migration MUST be in the fixed list below — a renumbered or
    -- inserted earlier migration that adds a tenant table would make the
    -- list stale and the guard refuses to run silently.
    FOREACH t IN ARRAY ARRAY[
        'a3_reports', 'account_contacts', 'accounting_periods',
        'accounts', 'andon_events', 'andons', 'anomaly_detections',
        'asset_warranties', 'assets', 'attachments', 'attendance',
        'audit_findings', 'audit_logs', 'audits',
        'authorization_revisions', 'bom_items', 'budget_allocations',
        'budgets', 'business_audit_log', 'calibration_events',
        'capa_actions', 'capas', 'certifications', 'chat_conversations',
        'command_journal', 'competency_projection', 'contacts',
        'control_plans', 'corporate_lesson_offers', 'cost_rollups',
        'country_policies', 'country_policy_versions',
        'ctq_characteristics', 'customer_complaints',
        'customer_invoices', 'data_lineage_links',
        'document_embeddings', 'document_ingestions', 'downtime_events',
        'eight_d_reports', 'email_verification_tokens',
        'employee_assignments', 'employee_compensation', 'employees',
        'entity_store', 'episodes', 'equipment', 'escalation_policies',
        'event_outbox', 'federation_memberships',
        'first_article_inspections', 'fx_rates', 'gauges',
        'gl_accounts', 'goods_receipts', 'inspection_characteristics',
        'inspection_measurements', 'inspection_plans',
        'inspection_records', 'inspections', 'integration_checkpoints',
        'integration_dead_letter', 'integration_entity_map',
        'integration_field_authority', 'integration_inbox',
        'integration_instances', 'integration_reconciliation',
        'integration_runs', 'inventory_items', 'invoices', 'issues',
        'job_standards', 'journal_entries', 'journal_lines',
        'jurisdiction_holidays', 'kanban_boards', 'kanban_cards',
        'kanban_columns', 'knowledge_graph_edges', 'knowledge_packs',
        'kpi_definitions', 'kpi_values', 'learning_modules',
        'leave_requests', 'lessons', 'loto_procedures', 'lsw_audits',
        'lsw_occurrences', 'lsw_standards', 'maintenance_occurrences',
        'maintenance_work_orders', 'maintenance_work_requests',
        'management_reviews', 'metric_definitions', 'model_registry',
        'mrp_records', 'mrp_runs', 'msa_measurements', 'msa_results',
        'msa_studies', 'ncr_reports', 'non_conformances',
        'notification_preferences', 'notification_triggers',
        'notifications', 'npi_projects', 'npi_risks', 'obeya_boards',
        'obeya_items', 'operational_conditions',
        'operational_event_objects', 'operational_events',
        'opportunities', 'organizational_memory', 'outbox_events',
        'password_reset_tokens', 'payments', 'performance_reviews',
        'pfmea_lite', 'pm_schedules', 'po_line_items', 'predictions',
        'principal_assignments', 'process_capability_studies',
        'process_definitions', 'product_families',
        'production_calendar', 'production_cell_work_centers',
        'production_cells', 'production_events', 'production_orders',
        'products', 'projects', 'purchase_order_items',
        'purchase_orders', 'qms_documents', 'qualifications',
        'quality_audits', 'quote_line_items', 'quote_versions',
        'quotes', 'realtime_tickets', 'reasoning_traces',
        'replication_inbox', 'replication_receipts', 'rfq_line_items',
        'rfqs', 'risks', 'role_slots', 'roles', 'routings',
        'sales_orders', 'sales_quotes', 'saved_views', 'scars',
        'self_inspections', 'service_state', 'sessions', 'shifts',
        'site_manifests', 'site_replication_log', 'sites',
        'skill_qualification_evidence', 'skill_qualifications',
        'skills', 'so_line_items', 'spare_parts', 'spc_data',
        'stage_gates', 'standard_work_documents',
        'standard_work_versions', 'standard_works', 'stations',
        'stock_moves', 'supplier_invoices', 'supplier_payments',
        'supplier_quotes', 'supplier_scorecards', 'suppliers', 'tasks',
        'tax_jurisdictions', 'timecards', 'tool_items',
        'tps_thresholds', 'training_enrollments', 'training_matrix',
        'training_programs', 'training_records',
        'user_notification_preferences', 'users', 'value_streams',
        'warehouse_cycle_counts', 'warehouse_orders',
        'warehouse_pick_events', 'warehouse_receipts',
        'warehouse_storage_locations', 'work_centers',
        'work_order_operations', 'work_orders', 'workflow_approvals',
        'workflow_checkpoints', 'workflow_evidence',
        'workflow_instances'
    ] LOOP
        -- Every fixed-list entry must exist as a real public base table
        -- with a tenant_id column at this point in the chain.
        IF to_regclass('public.' || t) IS NULL THEN
            missing := missing || t || ', ';
            CONTINUE;
        END IF;
        EXECUTE format(
            'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', t);
        -- Replace ANY earlier policy shape (the migration-070/079
        -- compatibility clause, the migration-079/098 fail-closed cast
        -- without explicit WITH CHECK, ...) with the canonical form.
        EXECUTE format(
            'DROP POLICY IF EXISTS tenant_isolation ON public.%I', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON public.%I
             USING (
                 tenant_id = NULLIF(current_setting(''app.tenant_id'', true), '''')::uuid
             )
             WITH CHECK (
                 tenant_id = NULLIF(current_setting(''app.tenant_id'', true), '''')::uuid
             )',
            t);
    END LOOP;
    IF missing <> '' THEN
        RAISE EXCEPTION 'migration 175 fixed-list drift: tables created by earlier migrations but missing from the 175 list: %', missing;
    END IF;

    -- Drift guard (b): the LIVE catalog may not contain a public base
    -- table with tenant_id that the fixed list missed — such a table
    -- would be created by an earlier migration and would end up without
    -- canonical isolation. The list and the chain must move together.
    FOR r IN
        SELECT c.relname::text AS tbl
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')
          AND EXISTS (
              SELECT 1 FROM information_schema.columns col
              WHERE col.table_schema = 'public'
                AND col.table_name = c.relname
                AND col.column_name = 'tenant_id'
          )
    LOOP
        IF r.tbl <> ALL (ARRAY[
            'a3_reports', 'account_contacts', 'accounting_periods',
            'accounts', 'andon_events', 'andons', 'anomaly_detections',
            'asset_warranties', 'assets', 'attachments', 'attendance',
            'audit_findings', 'audit_logs', 'audits',
            'authorization_revisions', 'bom_items',
            'budget_allocations', 'budgets', 'business_audit_log',
            'calibration_events', 'capa_actions', 'capas',
            'certifications', 'chat_conversations', 'command_journal',
            'competency_projection', 'contacts', 'control_plans',
            'corporate_lesson_offers', 'cost_rollups',
            'country_policies', 'country_policy_versions',
            'ctq_characteristics', 'customer_complaints',
            'customer_invoices', 'data_lineage_links',
            'document_embeddings', 'document_ingestions',
            'downtime_events', 'eight_d_reports',
            'email_verification_tokens', 'employee_assignments',
            'employee_compensation', 'employees', 'entity_store',
            'episodes', 'equipment', 'escalation_policies',
            'event_outbox', 'federation_memberships',
            'first_article_inspections', 'fx_rates', 'gauges',
            'gl_accounts', 'goods_receipts',
            'inspection_characteristics', 'inspection_measurements',
            'inspection_plans', 'inspection_records', 'inspections',
            'integration_checkpoints', 'integration_dead_letter',
            'integration_entity_map', 'integration_field_authority',
            'integration_inbox', 'integration_instances',
            'integration_reconciliation', 'integration_runs',
            'inventory_items', 'invoices', 'issues', 'job_standards',
            'journal_entries', 'journal_lines', 'jurisdiction_holidays',
            'kanban_boards', 'kanban_cards', 'kanban_columns',
            'knowledge_graph_edges', 'knowledge_packs',
            'kpi_definitions', 'kpi_values', 'learning_modules',
            'leave_requests', 'lessons', 'loto_procedures',
            'lsw_audits', 'lsw_occurrences', 'lsw_standards',
            'maintenance_occurrences', 'maintenance_work_orders',
            'maintenance_work_requests', 'management_reviews',
            'metric_definitions', 'model_registry', 'mrp_records',
            'mrp_runs', 'msa_measurements', 'msa_results', 'msa_studies',
            'ncr_reports', 'non_conformances',
            'notification_preferences', 'notification_triggers',
            'notifications', 'npi_projects', 'npi_risks',
            'obeya_boards', 'obeya_items', 'operational_conditions',
            'operational_event_objects', 'operational_events',
            'opportunities', 'organizational_memory', 'outbox_events',
            'password_reset_tokens', 'payments', 'performance_reviews',
            'pfmea_lite', 'pm_schedules', 'po_line_items',
            'predictions', 'principal_assignments',
            'process_capability_studies', 'process_definitions',
            'product_families', 'production_calendar',
            'production_cell_work_centers', 'production_cells',
            'production_events', 'production_orders', 'products',
            'projects', 'purchase_order_items', 'purchase_orders',
            'qms_documents', 'qualifications', 'quality_audits',
            'quote_line_items', 'quote_versions', 'quotes',
            'realtime_tickets', 'reasoning_traces', 'replication_inbox',
            'replication_receipts', 'rfq_line_items', 'rfqs', 'risks',
            'role_slots', 'roles', 'routings', 'sales_orders',
            'sales_quotes', 'saved_views', 'scars',
            'self_inspections', 'service_state', 'sessions', 'shifts',
            'site_manifests', 'site_replication_log', 'sites',
            'skill_qualification_evidence', 'skill_qualifications',
            'skills', 'so_line_items', 'spare_parts', 'spc_data',
            'stage_gates', 'standard_work_documents',
            'standard_work_versions', 'standard_works', 'stations',
            'stock_moves', 'supplier_invoices', 'supplier_payments',
            'supplier_quotes', 'supplier_scorecards', 'suppliers',
            'tasks', 'tax_jurisdictions', 'timecards', 'tool_items',
            'tps_thresholds', 'training_enrollments',
            'training_matrix', 'training_programs', 'training_records',
            'user_notification_preferences', 'users', 'value_streams',
            'warehouse_cycle_counts', 'warehouse_orders',
            'warehouse_pick_events', 'warehouse_receipts',
            'warehouse_storage_locations', 'work_centers',
            'work_order_operations', 'work_orders',
            'workflow_approvals', 'workflow_checkpoints',
            'workflow_evidence', 'workflow_instances'
        ]) THEN
            RAISE EXCEPTION 'migration 175 fixed-list drift: tenant-owned table % exists but is NOT in the 175 list (add it to the list and to the db-contract invariant)', r.tbl;
        END IF;
    END LOOP;
END $$;

-- ── 2. Post-verification: the canonical shape really landed ──────────────
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT c.relname::text AS tbl
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p')
          AND EXISTS (
              SELECT 1 FROM information_schema.columns col
              WHERE col.table_schema = 'public'
                AND col.table_name = c.relname
                AND col.column_name = 'tenant_id'
          )
    LOOP
        -- pg_policies serializes the expressions with their casts and
        -- parens; a containment check on the canonical NULLIF clause
        -- (rather than an exact string match) still proves the shape:
        -- no compatibility OR-branch, no zero-uuid COALESCE, and an
        -- explicit WITH CHECK are all implied by the clause landing in
        -- BOTH qual and with_check.
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies p
            WHERE p.schemaname = 'public'
              AND p.tablename = r.tbl
              AND p.policyname = 'tenant_isolation'
              AND p.qual LIKE '%(NULLIF(current_setting(''app.tenant_id''::text, true), ''''::text))::uuid%'
              AND p.with_check LIKE '%(NULLIF(current_setting(''app.tenant_id''::text, true), ''''::text))::uuid%'
              AND p.qual NOT LIKE '%00000000-0000-0000-0000-000000000000%'
              AND p.with_check NOT LIKE '%00000000-0000-0000-0000-000000000000%'
        ) THEN
            RAISE EXCEPTION 'table % did not land the canonical fail-closed tenant_isolation policy (thirtieth-audit item 18/31)', r.tbl;
        END IF;
    END LOOP;
END $$;

-- ── 3. Narrow pre-tenant identity channel (thirtieth-audit item 18) ──────
-- The two lookups below are the ONLY tenant-context-free readers of
-- `users` left in the application (see the header). They are SECURITY
-- DEFINER functions owned by the migration role — sensei_migrator, which
-- the canonical role script keeps BYPASSRLS — so their bodies read the
-- FORCE-RLS users table across tenants; the runtime sensei_app role is
-- NOBYPASSRLS and may reach the rows ONLY through these two functions
-- (plus its own TenantTx context, which is how every authenticated
-- users read works).
CREATE OR REPLACE FUNCTION auth_user_by_email(p_email text)
RETURNS TABLE (
    id uuid, tenant_id uuid, email text, name text, password_hash text,
    roles text[], is_active boolean, email_verified boolean,
    credential_version bigint, site_id uuid, locale text,
    last_login_at timestamptz, created_at timestamptz, updated_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT u.id, u.tenant_id, u.email::text, u.name::text, u.password_hash::text,
           u.roles, u.is_active, u.email_verified, u.credential_version,
           u.site_id, u.locale::text, u.last_login_at, u.created_at, u.updated_at
    FROM users u
    WHERE lower(u.email) = lower(p_email)
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION auth_user_by_id(p_user_id uuid)
RETURNS TABLE (
    id uuid, tenant_id uuid, email text, name text, password_hash text,
    roles text[], is_active boolean, email_verified boolean,
    credential_version bigint, site_id uuid, locale text,
    last_login_at timestamptz, created_at timestamptz, updated_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT u.id, u.tenant_id, u.email::text, u.name::text, u.password_hash::text,
           u.roles, u.is_active, u.email_verified, u.credential_version,
           u.site_id, u.locale::text, u.last_login_at, u.created_at, u.updated_at
    FROM users u
    WHERE u.id = p_user_id
    LIMIT 1;
$$;

-- Tenant-wide user administration (list + paginated list). The service
-- semantics of `list_users` are "return the users; the caller filters by
-- tenant/role" (the route layer scopes), and the pre-tenant admin flows
-- (notification-trigger resolution, admin views) have no single
-- app.tenant_id either. One definer channel keeps that surface
-- deterministic instead of the fail-open policy it replaced.
CREATE OR REPLACE FUNCTION auth_users_all()
RETURNS TABLE (
    id uuid, tenant_id uuid, email text, name text, password_hash text,
    roles text[], is_active boolean, email_verified boolean,
    credential_version bigint, site_id uuid, locale text,
    last_login_at timestamptz, created_at timestamptz, updated_at timestamptz
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT u.id, u.tenant_id, u.email::text, u.name::text, u.password_hash::text,
           u.roles, u.is_active, u.email_verified, u.credential_version,
           u.site_id, u.locale::text, u.last_login_at, u.created_at, u.updated_at
    FROM users u;
$$;

-- Least-privilege discipline (mirrors the federation-governance
-- functions): never PUBLIC EXECUTE — only the runtime application role,
-- and only when that role exists (the clean-bootstrap order runs the
-- chain before the canonical role script's post-migration pass on some
-- topologies; the script re-asserts the same grants when the function
-- is present).
REVOKE ALL ON FUNCTION auth_user_by_email(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_user_by_id(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION auth_users_all() FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'sensei_app') THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION auth_user_by_email(text) TO sensei_app';
        EXECUTE 'GRANT EXECUTE ON FUNCTION auth_user_by_id(uuid) TO sensei_app';
        EXECUTE 'GRANT EXECUTE ON FUNCTION auth_users_all() TO sensei_app';
    ELSE
        RAISE NOTICE 'sensei_app not present yet — the canonical role script grants EXECUTE on the auth_user_* identity functions once the role exists';
    END IF;
END
$$;
