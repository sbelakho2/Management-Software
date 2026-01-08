"""Sensei API v1 Router."""

from fastapi import APIRouter

from sensei.api.v1.endpoints import (
    health,
    auth,
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
    backups,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
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
api_router.include_router(backups.router, prefix="/backups", tags=["Backups"])
