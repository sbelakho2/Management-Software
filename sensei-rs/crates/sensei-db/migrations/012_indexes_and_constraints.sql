-- Performance indexes and constraints for Sensei ERP
--
-- This migration creates indexes for foreign keys, unique business keys,
-- common query patterns, JSONB columns, and vector columns across all
-- tables created in migrations 003-011.

-- ── CRM Indexes ───────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_accounts_tenant_type ON accounts(tenant_id, account_type);
CREATE INDEX IF NOT EXISTS idx_contacts_name_trgm ON contacts USING gin(last_name gin_trgm_ops);

-- ── RFQ / Quote Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_rfq_line_items_part ON rfq_line_items(part_number);
CREATE INDEX IF NOT EXISTS idx_supplier_quotes_embedding ON supplier_quotes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── Production Indexes ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_routings_product_active ON routings(product_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_wo_ops_work_order_status ON work_order_operations(work_order_id, status);
CREATE INDEX IF NOT EXISTS idx_stations_wc_status ON stations(work_center_id, status);

-- ── Quality Indexes ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_non_conformances_type ON non_conformances(tenant_id, nc_type);
CREATE INDEX IF NOT EXISTS idx_capa_actions_type ON capa_actions(capa_id, action_type);
CREATE INDEX IF NOT EXISTS idx_inspection_records_plan_result ON inspection_records(plan_id, result);
CREATE INDEX IF NOT EXISTS idx_inspection_measurements_pass ON inspection_measurements(pass_fail);
CREATE INDEX IF NOT EXISTS idx_gauges_type ON gauges(tenant_id, gauge_type);
CREATE INDEX IF NOT EXISTS idx_calibration_events_gauge_date ON calibration_events(gauge_id, calibration_date DESC);
CREATE INDEX IF NOT EXISTS idx_msa_measurements_study_part ON msa_measurements(study_id, part_number);
CREATE INDEX IF NOT EXISTS idx_qms_documents_category_status ON qms_documents(tenant_id, category, status);
CREATE INDEX IF NOT EXISTS idx_quality_audits_scheduled ON quality_audits(tenant_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_customer_complaints_product ON customer_complaints(product_id);
CREATE INDEX IF NOT EXISTS idx_eight_d_reports_owner ON eight_d_reports(owner_id);
CREATE INDEX IF NOT EXISTS idx_management_reviews_next ON management_reviews(next_review_date);
CREATE INDEX IF NOT EXISTS idx_pfmea_rpn_product ON pfmea_lite(product_id, rpn DESC);
CREATE INDEX IF NOT EXISTS idx_npi_projects_stage ON npi_projects(tenant_id, stage);
CREATE INDEX IF NOT EXISTS idx_self_inspections_result ON self_inspections(tenant_id, result);
CREATE INDEX IF NOT EXISTS idx_self_inspections_characteristics ON self_inspections USING gin(characteristics);
CREATE INDEX IF NOT EXISTS idx_control_plans_characteristics ON control_plans USING gin(characteristics);
CREATE INDEX IF NOT EXISTS idx_eight_d_reports_d1 ON eight_d_reports USING gin(d1_team);
CREATE INDEX IF NOT EXISTS idx_eight_d_reports_d8 ON eight_d_reports USING gin(d8_closure);

-- ── Finance Indexes ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_gl_accounts_type_active ON gl_accounts(tenant_id, account_type, is_active);
CREATE INDEX IF NOT EXISTS idx_journal_lines_entity_type ON journal_lines(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_po_line_items_part ON po_line_items(part_number);
CREATE INDEX IF NOT EXISTS idx_so_line_items_part ON so_line_items(part_number);
CREATE INDEX IF NOT EXISTS idx_customer_invoices_due_status ON customer_invoices(due_date, status);
CREATE INDEX IF NOT EXISTS idx_supplier_invoices_due_status ON supplier_invoices(due_date, status);
CREATE INDEX IF NOT EXISTS idx_fx_rates_latest ON fx_rates(from_currency, to_currency, date DESC);
CREATE INDEX IF NOT EXISTS idx_budget_allocations_spent ON budget_allocations(budget_id, spent);

-- ── Maintenance Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_mwo_asset_status ON maintenance_work_orders(asset_id, status);
CREATE INDEX IF NOT EXISTS idx_mwo_type ON maintenance_work_orders(tenant_id, type);
CREATE INDEX IF NOT EXISTS idx_downtime_events_duration ON downtime_events(tenant_id, duration_minutes DESC);
CREATE INDEX IF NOT EXISTS idx_loto_procedures_workers ON loto_procedures USING gin(authorized_workers);
CREATE INDEX IF NOT EXISTS idx_maintenance_work_orders_parts ON maintenance_work_orders USING gin(parts_used);
CREATE INDEX IF NOT EXISTS idx_asset_warranties_end ON asset_warranties(end_date) WHERE is_active = TRUE;

-- ── HR Indexes ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_employee_comp_current ON employee_compensation(employee_id, end_date)
    WHERE end_date IS NULL;
CREATE INDEX IF NOT EXISTS idx_training_enrollments_completed ON training_enrollments(employee_id, completed_at)
    WHERE status = 'completed';

-- ── Ops Indexes ───────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_obeya_items_board_status ON obeya_items(board_id, status);
CREATE INDEX IF NOT EXISTS idx_standard_works_steps ON standard_works USING gin(steps);
CREATE INDEX IF NOT EXISTS idx_kpi_values_date ON kpi_values(kpi_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_tags ON tasks USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_tasks_entity_type ON tasks(related_entity_type, related_entity_id);

-- ── System Indexes ────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_notification_prefs_user_event ON notification_preferences(user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_data_lineage_composite ON data_lineage_links(source_entity, source_id, target_entity, target_id);
CREATE INDEX IF NOT EXISTS idx_reasoning_traces_agent_date ON reasoning_traces(agent_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_service_state_lookup ON service_state(tenant_id, service_name, state_key);
CREATE INDEX IF NOT EXISTS idx_saved_views_user_entity ON saved_views(user_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_escalation_policies_entity_active ON escalation_policies(entity_type)
    WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_notification_triggers_event_active ON notification_triggers(event_type)
    WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_knowledge_packs_embedding ON knowledge_packs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_knowledge_packs_content ON knowledge_packs USING gin(content);
CREATE INDEX IF NOT EXISTS idx_learning_modules_content ON learning_modules USING gin(content);
CREATE INDEX IF NOT EXISTS idx_training_matrix_role_skill ON training_matrix(tenant_id, role, skill);
CREATE INDEX IF NOT EXISTS idx_training_matrix_gap_status ON training_matrix(tenant_id, gap DESC, status);

-- ── Unique Business Key Indexes ───────────────────────────────────────────
-- These supplement the UNIQUE constraints already defined on tables with
-- additional composite indexes for common lookup patterns.

-- CRM lookups
CREATE INDEX IF NOT EXISTS idx_accounts_tenant_name ON accounts(tenant_id, name);
CREATE INDEX IF NOT EXISTS idx_opportunities_stage_close ON opportunities(tenant_id, stage, close_date);

-- Production lookups
CREATE INDEX IF NOT EXISTS idx_routings_product_seq ON routings(product_id, sequence);
CREATE INDEX IF NOT EXISTS idx_wo_ops_wo_seq ON work_order_operations(work_order_id, sequence);

-- Quality lookups
CREATE INDEX IF NOT EXISTS idx_nc_status_severity ON non_conformances(tenant_id, status, severity);
CREATE INDEX IF NOT EXISTS idx_capa_actions_capa_status ON capa_actions(capa_id, status);
CREATE INDEX IF NOT EXISTS idx_inspection_records_plan_wo ON inspection_records(plan_id, work_order_id);
CREATE INDEX IF NOT EXISTS idx_calibration_events_gauge_result ON calibration_events(gauge_id, result);
CREATE INDEX IF NOT EXISTS idx_npi_projects_product_stage ON npi_projects(product_id, stage);

-- Finance lookups
CREATE INDEX IF NOT EXISTS idx_customer_invoices_customer_status ON customer_invoices(customer_id, status);
CREATE INDEX IF NOT EXISTS idx_supplier_invoices_supplier_status ON supplier_invoices(supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_supplier_date ON supplier_payments(supplier_id, paid_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account_entry ON journal_lines(account_id, entry_id);

-- Maintenance lookups
CREATE INDEX IF NOT EXISTS idx_mwo_scheduled_range ON maintenance_work_orders(tenant_id, scheduled_start, scheduled_end);
CREATE INDEX IF NOT EXISTS idx_downtime_events_range ON downtime_events(tenant_id, start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_spare_parts_low_stock ON spare_parts(tenant_id)
    WHERE quantity_on_hand <= reorder_point AND is_active = TRUE;

-- Ops lookups
CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status ON tasks(assignee_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_status ON tasks(tenant_id, due_date, status);
CREATE INDEX IF NOT EXISTS idx_kpi_definitions_category_freq ON kpi_definitions(tenant_id, category, frequency);

-- ── Status + Created_at Composite Indexes ─────────────────────────────────
-- Common pattern: filter by status, sort by created_at
CREATE INDEX IF NOT EXISTS idx_accounts_status_created ON accounts(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_status_created ON opportunities(tenant_id, stage, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_non_conformances_status_created ON non_conformances(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_capa_actions_status_created ON capa_actions(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mwo_status_created ON maintenance_work_orders(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_complaints_status_created ON customer_complaints(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quality_audits_status_created ON quality_audits(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_npi_projects_status_created ON npi_projects(tenant_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_obeya_items_status_created ON obeya_items(tenant_id, status, created_at DESC);
