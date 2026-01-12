#!/bin/bash
# Move AI services
mv backend/src/sensei/services/ai_reasoning.py \
   backend/src/sensei/services/ai_content_drafting.py \
   backend/src/sensei/services/ai_ctq_summarization.py \
   backend/src/sensei/services/ai_email_drafting.py \
   backend/src/sensei/services/ai_learning_recommendations.py \
   backend/src/sensei/services/ai_qualification_advisory.py \
   backend/src/sensei/services/reasoning_engine.py \
   backend/src/sensei/services/enhanced_ml_pipeline.py \
   backend/src/sensei/services/onnx_text_embeddings.py \
   backend/src/sensei/services/xai_service.py \
   backend/src/sensei/services/visual_quality_inspection.py \
   backend/src/sensei/services/nlp_command_palette.py \
   backend/src/sensei/services/advanced_rag.py \
   backend/src/sensei/services/socratic_pedagogy_rag.py \
   backend/src/sensei/services/self_improving_rag.py \
   backend/src/sensei/services/knowledge_embeddings.py \
   backend/src/sensei/services/knowledge_enrichment.py \
   backend/src/sensei/services/knowledge_ingestion.py \
   backend/src/sensei/services/semantic_anomaly_detection.py \
   backend/src/sensei/services/hybrid_search.py \
   backend/src/sensei/services/document_intelligence.py \
   backend/src/sensei/services/world_class_document_ai.py \
   backend/src/sensei/services/virtual_assistant.py \
   backend/src/sensei/services/meta_sensei.py \
   backend/src/sensei/services/ai/

# Move Sales services
mv backend/src/sensei/services/rfq_completeness.py \
   backend/src/sensei/services/rfq_time_tracking.py \
   backend/src/sensei/services/multi_agent_rfq.py \
   backend/src/sensei/services/quote_approval_time_tracking.py \
   backend/src/sensei/services/quote_quality.py \
   backend/src/sensei/services/predictive_win_loss.py \
   backend/src/sensei/services/smart_supplier_matchmaker.py \
   backend/src/sensei/services/sales/

# Move Production services
mv backend/src/sensei/services/production_scheduling.py \
   backend/src/sensei/services/productionization.py \
   backend/src/sensei/services/mrp_lite.py \
   backend/src/sensei/services/scheduling_maintenance_sync.py \
   backend/src/sensei/services/lsw_scheduling.py \
   backend/src/sensei/services/jidoka_error_proofing.py \
   backend/src/sensei/services/standard_work_evolution.py \
   backend/src/sensei/services/standard_work_evolution_worker.py \
   backend/src/sensei/services/shift_handover_tier_meetings.py \
   backend/src/sensei/services/spc_scrap_rework.py \
   backend/src/sensei/services/dispatch_traveler.py \
   backend/src/sensei/services/label_printing.py \
   backend/src/sensei/services/wms_integration.py \
   backend/src/sensei/services/lot_serial_traceability.py \
   backend/src/sensei/services/production/

# Move Quality services
mv backend/src/sensei/services/qms_quality.py \
   backend/src/sensei/services/quality_certification_gate.py \
   backend/src/sensei/services/capa_workflow.py \
   backend/src/sensei/services/change_control.py \
   backend/src/sensei/services/audit_evidence.py \
   backend/src/sensei/services/audit_trail_timeline.py \
   backend/src/sensei/services/npi_risk_register.py \
   backend/src/sensei/services/npi_stage_gates.py \
   backend/src/sensei/services/quality/

# Move Finance services
mv backend/src/sensei/services/accounting_ledger.py \
   backend/src/sensei/services/accounts_payable.py \
   backend/src/sensei/services/accounts_receivable.py \
   backend/src/sensei/services/cost_accounting.py \
   backend/src/sensei/services/financial_operational_feedback.py \
   backend/src/sensei/services/fixed_assets.py \
   backend/src/sensei/services/payroll_labor_costing.py \
   backend/src/sensei/services/integration_reconciliation.py \
   backend/src/sensei/services/finance/

# Move HR services
mv backend/src/sensei/services/employee_lifecycle.py \
   backend/src/sensei/services/training_matrix.py \
   backend/src/sensei/services/compensation_management.py \
   backend/src/sensei/services/recruiting.py \
   backend/src/sensei/services/talent_performance.py \
   backend/src/sensei/services/hr_case_management.py \
   backend/src/sensei/services/leave_management.py \
   backend/src/sensei/services/staffing_roster.py \
   backend/src/sensei/services/hr/

# Move Core services
mv backend/src/sensei/services/rbac_enhanced.py \
   backend/src/sensei/services/rbac_security_audit.py \
   backend/src/sensei/services/identity_access.py \
   backend/src/sensei/services/pii_controls.py \
   backend/src/sensei/services/privacy_compliance.py \
   backend/src/sensei/services/security_logging.py \
   backend/src/sensei/services/access_review.py \
   backend/src/sensei/services/backup_scheduler.py \
   backend/src/sensei/services/database_backup.py \
   backend/src/sensei/services/health_checks.py \
   backend/src/sensei/services/infrastructure_resilience.py \
   backend/src/sensei/services/disaster_recovery_drill.py \
   backend/src/sensei/services/business_continuity.py \
   backend/src/sensei/services/local_first_infrastructure.py \
   backend/src/sensei/services/persona_management.py \
   backend/src/sensei/services/edge_ai.py \
   backend/src/sensei/services/state_machine.py \
   backend/src/sensei/services/activity_feed.py \
   backend/src/sensei/services/notification_triggers.py \
   backend/src/sensei/services/alerting_config.py \
   backend/src/sensei/services/search.py \
   backend/src/sensei/services/template_cloning.py \
   backend/src/sensei/services/setup_wizard.py \
   backend/src/sensei/services/factory_launchpad.py \
   backend/src/sensei/services/common_thread.py \
   backend/src/sensei/services/context_bus.py \
   backend/src/sensei/services/data_lineage.py \
   backend/src/sensei/services/data_quality.py \
   backend/src/sensei/services/data_retention.py \
   backend/src/sensei/services/data_hygiene_nudges.py \
   backend/src/sensei/services/query_optimization.py \
   backend/src/sensei/services/core/

# Move Ops services
mv backend/src/sensei/services/ceo_control_plane.py \
   backend/src/sensei/services/cognitive_obeya.py \
   backend/src/sensei/services/gm_onboarding.py \
   backend/src/sensei/services/today_screen.py \
   backend/src/sensei/services/tps_teacher.py \
   backend/src/sensei/services/tps_knowledge_sources.py \
   backend/src/sensei/services/jit_lean_learning.py \
   backend/src/sensei/services/a3_reasoning_gates.py \
   backend/src/sensei/services/andon_a3_escalation.py \
   backend/src/sensei/services/muda_contextual_nudging.py \
   backend/src/sensei/services/muda_nudging_scheduler.py \
   backend/src/sensei/services/muda_nudging_worker.py \
   backend/src/sensei/services/sensei_autopilot.py \
   backend/src/sensei/services/sensei_command.py \
   backend/src/sensei/services/sensei_nudges.py \
   backend/src/sensei/services/kpi_app_services.py \
   backend/src/sensei/services/kpi_metric_sources.py \
   backend/src/sensei/services/kpi_metrics.py \
   backend/src/sensei/services/metric_sources.py \
   backend/src/sensei/services/ops/

# Move Supply Chain services
mv backend/src/sensei/services/supply_chain_simulation.py \
   backend/src/sensei/services/supplier_portal_token.py \
   backend/src/sensei/services/predictive_utility_forecasting.py \
   backend/src/sensei/services/supply_chain/

# Move Maintenance services
mv backend/src/sensei/services/maintenance_tpm.py \
   backend/src/sensei/services/maintenance/

# Move Utils services
mv backend/src/sensei/services/csv_export.py \
   backend/src/sensei/services/csv_import.py \
   backend/src/sensei/services/pdf_generation.py \
   backend/src/sensei/services/digest_export.py \
   backend/src/sensei/services/i18n_backend.py \
   backend/src/sensei/services/locale_formats.py \
   backend/src/sensei/services/industrial_ux.py \
   backend/src/sensei/services/ui_backend_integration.py \
   backend/src/sensei/services/uiux_verification.py \
   backend/src/sensei/services/chaos_testing.py \
   backend/src/sensei/services/integration_tests.py \
   backend/src/sensei/services/job_health.py \
   backend/src/sensei/services/job_idempotency.py \
   backend/src/sensei/services/utils/
