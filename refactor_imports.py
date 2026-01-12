import os
import re

mapping = {
    "ai": [
        "ai_reasoning", "ai_content_drafting", "ai_ctq_summarization", "ai_email_drafting",
        "ai_learning_recommendations", "ai_qualification_advisory", "reasoning_engine",
        "enhanced_ml_pipeline", "onnx_text_embeddings", "xai_service",
        "visual_quality_inspection", "nlp_command_palette", "advanced_rag",
        "socratic_pedagogy_rag", "self_improving_rag", "knowledge_embeddings",
        "knowledge_enrichment", "knowledge_ingestion", "semantic_anomaly_detection",
        "hybrid_search", "document_intelligence", "world_class_document_ai",
        "virtual_assistant", "meta_sensei"
    ],
    "sales": [
        "rfq_completeness", "rfq_time_tracking", "multi_agent_rfq",
        "quote_approval_time_tracking", "quote_quality", "predictive_win_loss",
        "smart_supplier_matchmaker"
    ],
    "production": [
        "production_scheduling", "productionization", "mrp_lite",
        "scheduling_maintenance_sync", "lsw_scheduling", "jidoka_error_proofing",
        "standard_work_evolution", "standard_work_evolution_worker",
        "shift_handover_tier_meetings", "spc_scrap_rework", "dispatch_traveler",
        "label_printing", "wms_integration", "lot_serial_traceability"
    ],
    "quality": [
        "qms_quality", "quality_certification_gate", "capa_workflow", "change_control",
        "audit_evidence", "audit_trail_timeline", "npi_risk_register", "npi_stage_gates"
    ],
    "finance": [
        "accounting_ledger", "accounts_payable", "accounts_receivable", "cost_accounting",
        "financial_operational_feedback", "fixed_assets", "payroll_labor_costing",
        "integration_reconciliation"
    ],
    "hr": [
        "employee_lifecycle", "training_matrix", "compensation_management", "recruiting",
        "talent_performance", "hr_case_management", "leave_management", "staffing_roster"
    ],
    "core": [
        "rbac_enhanced", "rbac_security_audit", "identity_access", "pii_controls",
        "privacy_compliance", "security_logging", "access_review", "backup_scheduler",
        "database_backup", "health_checks", "infrastructure_resilience",
        "disaster_recovery_drill", "business_continuity", "local_first_infrastructure",
        "persona_management", "edge_ai", "state_machine", "activity_feed",
        "notification_triggers", "alerting_config", "search", "template_cloning",
        "setup_wizard", "factory_launchpad", "common_thread", "context_bus",
        "data_lineage", "data_quality", "data_retention", "data_hygiene_nudges",
        "query_optimization"
    ],
    "ops": [
        "ceo_control_plane", "cognitive_obeya", "gm_onboarding", "today_screen",
        "tps_teacher", "tps_knowledge_sources", "jit_lean_learning",
        "a3_reasoning_gates", "andon_a3_escalation", "muda_contextual_nudging",
        "muda_nudging_scheduler", "muda_nudging_worker", "sensei_autopilot",
        "sensei_command", "sensei_nudges", "kpi_app_services", "kpi_metric_sources",
        "kpi_metrics", "metric_sources"
    ],
    "supply_chain": [
        "supply_chain_simulation", "supplier_portal_token", "predictive_utility_forecasting"
    ],
    "maintenance": [
        "maintenance_tpm"
    ],
    "utils": [
        "csv_export", "csv_import", "pdf_generation", "digest_export",
        "i18n_backend", "locale_formats", "industrial_ux", "ui_backend_integration",
        "uiux_verification", "chaos_testing", "integration_tests", "job_health",
        "job_idempotency"
    ]
}

# Inverse mapping
inv_mapping = {}
for cat, services in mapping.items():
    for service in services:
        inv_mapping[service] = cat

def refactor_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    modified = False
    
    # Replace from sensei.services.xxx
    # Handle from sensei.services import xxx
    # Handle import sensei.services.xxx
    
    # Pattern: from sensei.services.XXX import ...
    def replace_from_stmt(match):
        service = match.group(1)
        if service in inv_mapping:
            nonlocal modified
            modified = True
            return f"from sensei.services.{inv_mapping[service]}.{service}"
        return match.group(0)

    content = re.sub(r'from sensei\.services\.([a-zA_0-9_]+)', replace_from_stmt, content)
    
    # Pattern: from sensei.services import XXX
    def replace_from_import(match):
        services_str = match.group(1)
        # Handle multiple imports: from sensei.services import a, b, c
        parts = [s.strip() for s in services_str.split(',')]
        new_imports = []
        for p in parts:
            if p in inv_mapping:
                nonlocal modified
                modified = True
                new_imports.append(f"from sensei.services.{inv_mapping[p]} import {p}")
            else:
                new_imports.append(f"from sensei.services import {p}")
        return "\n".join(new_imports)

    content = re.sub(r'from sensei\.services import ([a-zA-Z0-9_, ]+)', replace_from_import, content)
    
    # Handle: import sensei.services.xxx
    def replace_import_stmt(match):
        service = match.group(1)
        if service in inv_mapping:
            nonlocal modified
            modified = True
            return f"import sensei.services.{inv_mapping[service]}.{service}"
        return match.group(0)
    
    content = re.sub(r'import sensei\.services\.([a-zA_0-9_]+)', replace_import_stmt, content)

    # Handle: patch("sensei.services.xxx...") and other string references
    def replace_string_ref(match):
        service = match.group(1)
        rest = match.group(2)
        if service in inv_mapping:
            nonlocal modified
            modified = True
            return f"sensei.services.{inv_mapping[service]}.{service}{rest}"
        return match.group(0)

    content = re.sub(r'sensei\.services\.([a-zA-Z0-9_]+)(\.[a-zA-Z0-9_.]+)?', replace_string_ref, content)

    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Refactored {filepath}")

for root, dirs, files in os.walk('backend/src'):
    for file in files:
        if file.endswith('.py'):
            refactor_file(os.path.join(root, file))

for root, dirs, files in os.walk('backend/tests'):
    for file in files:
        if file.endswith('.py'):
            refactor_file(os.path.join(root, file))
