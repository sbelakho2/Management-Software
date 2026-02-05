"""Sensei API v1 Router."""

from fastapi import APIRouter

from sensei.api.v1.endpoints import (
    health,
    auth,
    dev_bootstrap,
    dev_e2e,
    users,
    accounts,
    contacts,
    products,
    rfqs,
    opportunities,
    quotes,
    work_centers,
    work_orders,
    production_cells,
    quality,
    andon,
    kanban,
    standard_work,
    training,
    a3,
    ctq,
    risk,
    obeya,
    tasks,
    learning,
    attachments,
    audit_logs,
    state_machines,
    stale_detection,
    escalation_policy,
    training_matrix,
    andon_escalation,
    notification_triggers,
    search,
    saved_views,
    quote_quality,
    lsw,
    kpi,
    conditions,
    today,
    production_handovers,
    pulse,
    backups,
    backup_scheduler,
    exceptions,
    admin,
    hr,
    gm_onboarding,
    rfq_time_tracking,
    quoting_helper,
    quote_approval_time_tracking,
    rbac_security_audit,
    chaos_testing,
    disaster_recovery_drill,
    project_management,
    data_lineage,
    context_bus,
    common_thread,
    executive_intel,
    cognitive_obeya,
    maintenance,
    finance,
    purchase,
    sales,
    mrp,
    supply_chain,
    analytics,
    websockets,
    factory_launchpad,
    edge_ai,
    ai_health,
    ai_email_drafting,
    smart_ingestion,
    knowledge_pack,
    sites,
    warehouse,
    it_monitoring,
    auditor,
    chat,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dev_bootstrap.router, prefix="/dev", tags=["Dev"])
api_router.include_router(dev_e2e.router, prefix="/dev", tags=["Dev"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(rfqs.router, prefix="/rfqs", tags=["RFQs"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
api_router.include_router(quality.router, prefix="/quality", tags=["Quality"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["Quotes"])
api_router.include_router(work_centers.router, prefix="/work-centers", tags=["Work Centers"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["Work Orders"])
api_router.include_router(production_cells.router, prefix="/production-cells", tags=["Production Cells"])
api_router.include_router(andon.router, prefix="/andon", tags=["Andon"])
api_router.include_router(kanban.router, prefix="/kanban", tags=["Kanban"])
api_router.include_router(standard_work.router, prefix="/standard-work", tags=["Standard Work"])
api_router.include_router(training.router, prefix="/training", tags=["Training"])
api_router.include_router(a3.router, prefix="/a3", tags=["A3"])
api_router.include_router(ctq.router, prefix="/ctq", tags=["CTQ"])
api_router.include_router(risk.router, prefix="/risks", tags=["Risk"])
api_router.include_router(obeya.router, prefix="/obeya", tags=["Obeya"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(learning.router, prefix="/learning", tags=["Learning"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["Attachments"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(state_machines.router, prefix="/state-machines", tags=["State Machines"])
api_router.include_router(stale_detection.router, prefix="/stale-detection", tags=["Stale Detection"])
api_router.include_router(escalation_policy.router, prefix="/escalation", tags=["Escalation"])
api_router.include_router(training_matrix.router, prefix="/training-matrix", tags=["Training Matrix"])
api_router.include_router(andon_escalation.router)
api_router.include_router(notification_triggers.router)
api_router.include_router(search.router)
api_router.include_router(saved_views.router)
api_router.include_router(quote_quality.router)
api_router.include_router(lsw.router)
api_router.include_router(kpi.router)
api_router.include_router(conditions.router)
api_router.include_router(today.router)
api_router.include_router(production_handovers.router)
api_router.include_router(pulse.router)
api_router.include_router(backups.router, prefix="/backups", tags=["Backups"])
api_router.include_router(backup_scheduler.router, prefix="/backup-scheduler", tags=["Backup Scheduler"])
api_router.include_router(exceptions.router, prefix="/exceptions", tags=["Exceptions"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(hr.router, prefix="/hr", tags=["HR"])
api_router.include_router(gm_onboarding.router, prefix="/gm-onboarding", tags=["GM Onboarding"])
api_router.include_router(rfq_time_tracking.router, prefix="/rfq-time-tracking", tags=["RFQ Time Tracking"])
api_router.include_router(quoting_helper.router, prefix="/quoting-helper", tags=["Quoting Helper"])
api_router.include_router(quote_approval_time_tracking.router, prefix="/quote-approval", tags=["Quote Approval"])
api_router.include_router(rbac_security_audit.router, prefix="/security-audit", tags=["Security Audit"])
api_router.include_router(chaos_testing.router, prefix="/chaos-testing", tags=["Chaos Testing"])
api_router.include_router(disaster_recovery_drill.router, prefix="/dr-drills", tags=["Disaster Recovery"])
api_router.include_router(project_management.router, prefix="/project-management", tags=["Project Management"])
api_router.include_router(context_bus.router, prefix="/context", tags=["Context"])
api_router.include_router(data_lineage.router, prefix="/data-lineage", tags=["Data Lineage"])
api_router.include_router(common_thread.router, prefix="/common-thread", tags=["Common Thread"])
api_router.include_router(executive_intel.router, prefix="/executive", tags=["Executive"])
api_router.include_router(cognitive_obeya.router, prefix="/cognitive-obeya", tags=["Cognitive Obeya"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["Maintenance"])
api_router.include_router(finance.router, prefix="/finance", tags=["Finance"])
api_router.include_router(purchase.router, prefix="/purchase", tags=["Purchase"])
api_router.include_router(sales.router, prefix="/sales", tags=["Sales"])
api_router.include_router(mrp.router, prefix="/mrp", tags=["MRP"])
api_router.include_router(supply_chain.router, prefix="/supply-chain", tags=["Supply Chain"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(websockets.router, tags=["WebSockets"])
api_router.include_router(factory_launchpad.router, prefix="/launchpad", tags=["Factory Launchpad"])
api_router.include_router(edge_ai.router, prefix="/edge-ai", tags=["Edge AI"])
api_router.include_router(ai_health.router, prefix="/ai", tags=["AI Readiness"])
api_router.include_router(ai_email_drafting.router, prefix="/ai", tags=["AI Email Drafting"])
api_router.include_router(smart_ingestion.router, tags=["Smart Ingestion"])
api_router.include_router(knowledge_pack.router, tags=["Knowledge Pack"])
api_router.include_router(sites.router, tags=["Sites"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["Warehouse"])
api_router.include_router(it_monitoring.router, prefix="/it", tags=["IT Monitoring"])
api_router.include_router(auditor.router, prefix="/auditor", tags=["Auditor"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
