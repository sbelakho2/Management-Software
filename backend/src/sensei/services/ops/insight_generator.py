"""Insight generator — produces actionable AI-style insights from live DB data.

Each insight is a dict matching the contract expected by
``filter_insights_for_role`` (category + severity + body).  All queries run
through the ORM — no raw SQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.quality import (
    CAPA,
    CAPAStatus,
    NCStatus,
    NCSeverity,
    NonConformance,
)
from sensei.models.work_order import WorkOrder, WorkOrderStatus
from sensei.models.rfq import RFQ, RFQStatus
from sensei.models.quote import Quote, QuoteStatus
from sensei.models.task import Task, TaskStatus
from sensei.models.opportunity import Opportunity, OpportunityStage
from sensei.models.accounts_receivable import CustomerInvoice, Shipment
from sensei.models.accounts_payable import PurchaseOrder, SupplierInvoice
from sensei.models.andon import AndonEvent, AndonStatus
from sensei.models.inventory import InventoryLevel, StockMove
from sensei.models.hr import EmployeeProfile, HRJobOpening
from sensei.models.mrp import MRPSuggestion
from sensei.models.user import User, UserStatus
from sensei.models.maintenance import (
    Asset,
    MaintenanceWorkOrder,
    PMSchedule,
    DowntimeEvent,
    SparePart,
    FailureRecord,
)
from sensei.models.training import (
    Training,
    TrainingParticipant,
    UserSkill,
    Skill,
)
from sensei.models.project_management import (
    Project,
    ProjectStatus,
    UserStory,
    UserStoryStatus,
    Sprint,
    SprintStatus,
    Issue,
    IssueStatus,
    IssueSeverity as PMIssueSeverity,
)
from sensei.services.core.role_insights_config import InsightCategory


def _insight(
    category: InsightCategory,
    title: str,
    description: str,
    severity: str = "info",
    metric_value: Any = None,
    metric_label: str | None = None,
    recommendation: str | None = None,
) -> dict[str, Any]:
    """Build a single insight dict in the canonical shape."""
    d: dict[str, Any] = {
        "category": category.value,
        "title": title,
        "description": description,
        "severity": severity,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if metric_value is not None:
        d["metric_value"] = metric_value
    if metric_label:
        d["metric_label"] = metric_label
    if recommendation:
        d["recommendation"] = recommendation
    return d


async def generate_insights(db: AsyncSession) -> list[dict[str, Any]]:
    """Generate insights from live database state.

    Returns a list of insight dicts.  Callers are expected to run
    ``filter_insights_for_role`` and ``mask_analytics_data`` afterwards.
    """

    insights: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # ── Quality Insights ─────────────────────────────────────
    open_ncs = int(
        (await db.execute(
            select(func.count()).select_from(NonConformance).where(
                NonConformance.status == NCStatus.OPEN
            )
        )).scalar() or 0
    )
    critical_ncs = int(
        (await db.execute(
            select(func.count()).select_from(NonConformance).where(
                NonConformance.severity == NCSeverity.CRITICAL
            )
        )).scalar() or 0
    )
    open_capas = int(
        (await db.execute(
            select(func.count()).select_from(CAPA).where(
                CAPA.status == CAPAStatus.OPEN
            )
        )).scalar() or 0
    )

    if critical_ncs > 0:
        insights.append(_insight(
            InsightCategory.QUALITY_TRENDS,
            f"{critical_ncs} Critical Non-Conformance{'s' if critical_ncs != 1 else ''} Detected",
            f"There {'are' if critical_ncs != 1 else 'is'} {critical_ncs} critical-severity NC{'s' if critical_ncs != 1 else ''} in the system. "
            "Critical NCs can affect product safety and regulatory compliance.",
            severity="critical",
            metric_value=critical_ncs,
            metric_label="Critical NCs",
            recommendation="Escalate to quality manager and initiate CAPA for each critical NC immediately.",
        ))

    if open_ncs > 10:
        insights.append(_insight(
            InsightCategory.QUALITY_TRENDS,
            f"{open_ncs} Open Non-Conformances",
            f"NC backlog has reached {open_ncs} open items. Consider prioritising investigation and disposition.",
            severity="warning",
            metric_value=open_ncs,
            metric_label="Open NCs",
            recommendation="Schedule a quality review meeting to disposition the top NCs by severity.",
        ))
    elif open_ncs > 0:
        insights.append(_insight(
            InsightCategory.QUALITY_TRENDS,
            f"{open_ncs} Open Non-Conformance{'s' if open_ncs != 1 else ''}",
            f"{open_ncs} NC{'s' if open_ncs != 1 else ''} currently open and awaiting disposition.",
            severity="info",
            metric_value=open_ncs,
            metric_label="Open NCs",
        ))

    if open_capas > 5:
        insights.append(_insight(
            InsightCategory.CAPA_RECOMMENDATIONS,
            f"{open_capas} Open CAPAs Require Attention",
            f"CAPA backlog is elevated at {open_capas} open items. Effectiveness verification may be lagging.",
            severity="warning",
            metric_value=open_capas,
            metric_label="Open CAPAs",
            recommendation="Assign dedicated resources to close the oldest CAPAs first.",
        ))
    elif open_capas > 0:
        insights.append(_insight(
            InsightCategory.CAPA_RECOMMENDATIONS,
            f"{open_capas} Open CAPA{'s' if open_capas != 1 else ''}",
            f"{open_capas} corrective/preventive action{'s' if open_capas != 1 else ''} in the pipeline.",
            severity="info",
            metric_value=open_capas,
            metric_label="Open CAPAs",
        ))

    # ── Operations Insights ──────────────────────────────────
    in_progress_wo = int(
        (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.IN_PROGRESS
            )
        )).scalar() or 0
    )
    on_hold_wo = int(
        (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.ON_HOLD
            )
        )).scalar() or 0
    )
    active_andons = int(
        (await db.execute(
            select(func.count()).select_from(AndonEvent).where(
                AndonEvent.status.in_([AndonStatus.OPEN, AndonStatus.ACKNOWLEDGED, AndonStatus.ESCALATED])
            )
        )).scalar() or 0
    )

    if on_hold_wo > 0:
        insights.append(_insight(
            InsightCategory.BOTTLENECK_DETECTION,
            f"{on_hold_wo} Work Order{'s' if on_hold_wo != 1 else ''} On Hold",
            f"{on_hold_wo} work order{'s are' if on_hold_wo != 1 else ' is'} on hold. "
            "Common causes: material shortage, equipment breakdown, or quality issue.",
            severity="warning" if on_hold_wo > 3 else "info",
            metric_value=on_hold_wo,
            metric_label="WOs On Hold",
            recommendation="Review hold reasons and unblock highest-priority work orders first.",
        ))

    if in_progress_wo > 0:
        insights.append(_insight(
            InsightCategory.PRODUCTION_EFFICIENCY,
            f"{in_progress_wo} Work Order{'s' if in_progress_wo != 1 else ''} In Progress",
            f"Shop floor is actively processing {in_progress_wo} work order{'s' if in_progress_wo != 1 else ''}.",
            severity="info",
            metric_value=in_progress_wo,
            metric_label="Active WOs",
        ))

    if active_andons > 0:
        sev = "critical" if active_andons > 3 else "warning"
        insights.append(_insight(
            InsightCategory.BOTTLENECK_DETECTION,
            f"{active_andons} Active Andon Event{'s' if active_andons != 1 else ''}",
            f"{active_andons} andon call{'s' if active_andons != 1 else ''} currently active on the shop floor. "
            "Unresolved andons reduce throughput.",
            severity=sev,
            metric_value=active_andons,
            metric_label="Active Andons",
            recommendation="Dispatch support team to the affected stations immediately.",
        ))

    # ── Sales / Pipeline Insights ────────────────────────────
    open_rfqs = int(
        (await db.execute(
            select(func.count()).select_from(RFQ).where(
                RFQ.status.in_([RFQStatus.RECEIVED, RFQStatus.UNDER_REVIEW, RFQStatus.QUALIFYING, RFQStatus.QUOTING])
            )
        )).scalar() or 0
    )
    pending_quotes = int(
        (await db.execute(
            select(func.count()).select_from(Quote).where(
                Quote.status == QuoteStatus.PENDING_APPROVAL
            )
        )).scalar() or 0
    )
    pipeline_value = float(
        (await db.execute(
            select(func.coalesce(func.sum(Opportunity.amount), 0)).where(
                Opportunity.stage.notin_([OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
            )
        )).scalar() or 0
    )

    if pending_quotes > 3:
        insights.append(_insight(
            InsightCategory.PIPELINE_HEALTH,
            f"{pending_quotes} Quotes Awaiting Approval",
            f"{pending_quotes} quotes are stuck in the approval queue. Delayed approvals risk losing deals.",
            severity="warning",
            metric_value=pending_quotes,
            metric_label="Pending Quotes",
            recommendation="Review and approve or reject the oldest pending quotes within 24 hours.",
        ))
    elif pending_quotes > 0:
        insights.append(_insight(
            InsightCategory.PIPELINE_HEALTH,
            f"{pending_quotes} Quote{'s' if pending_quotes != 1 else ''} Pending Approval",
            f"{pending_quotes} quote{'s' if pending_quotes != 1 else ''} awaiting management approval.",
            severity="info",
            metric_value=pending_quotes,
            metric_label="Pending Quotes",
        ))

    if open_rfqs > 0:
        insights.append(_insight(
            InsightCategory.PIPELINE_HEALTH,
            f"{open_rfqs} Active RFQ{'s' if open_rfqs != 1 else ''} in Pipeline",
            f"{open_rfqs} request{'s' if open_rfqs != 1 else ''} for quote currently being processed.",
            severity="info",
            metric_value=open_rfqs,
            metric_label="Active RFQs",
        ))

    if pipeline_value > 0:
        insights.append(_insight(
            InsightCategory.REVENUE_TRENDS,
            f"Pipeline Value: ${pipeline_value:,.0f}",
            f"Total value of open opportunities in the sales pipeline: ${pipeline_value:,.2f}.",
            severity="info",
            metric_value=pipeline_value,
            metric_label="Pipeline $",
        ))

    # ── Finance Insights ─────────────────────────────────────
    outstanding_invoices = int(
        (await db.execute(
            select(func.count()).select_from(CustomerInvoice).where(
                CustomerInvoice.status.in_(["issued"])
            )
        )).scalar() or 0
    )
    overdue_invoices = int(
        (await db.execute(
            select(func.count()).select_from(CustomerInvoice).where(
                and_(
                    CustomerInvoice.status == "issued",
                    CustomerInvoice.due_date < now,
                )
            )
        )).scalar() or 0
    )
    open_pos = int(
        (await db.execute(
            select(func.count()).select_from(PurchaseOrder).where(
                PurchaseOrder.status.in_(["draft", "approved", "sent", "partially_received"])
            )
        )).scalar() or 0
    )

    if overdue_invoices > 0:
        insights.append(_insight(
            InsightCategory.CASH_FLOW_FORECAST,
            f"{overdue_invoices} Overdue Customer Invoice{'s' if overdue_invoices != 1 else ''}",
            f"{overdue_invoices} customer invoice{'s are' if overdue_invoices != 1 else ' is'} past due. "
            "This impacts cash flow and may require collection follow-up.",
            severity="warning",
            metric_value=overdue_invoices,
            metric_label="Overdue Invoices",
            recommendation="Initiate collection calls for the oldest overdue invoices.",
        ))

    if outstanding_invoices > 0:
        insights.append(_insight(
            InsightCategory.FINANCIAL_KPIs,
            f"{outstanding_invoices} Outstanding Invoice{'s' if outstanding_invoices != 1 else ''}",
            f"{outstanding_invoices} customer invoice{'s' if outstanding_invoices != 1 else ''} not yet fully paid.",
            severity="info",
            metric_value=outstanding_invoices,
            metric_label="Outstanding Invoices",
        ))

    if open_pos > 0:
        insights.append(_insight(
            InsightCategory.COST_OPTIMIZATION,
            f"{open_pos} Open Purchase Order{'s' if open_pos != 1 else ''}",
            f"{open_pos} purchase order{'s are' if open_pos != 1 else ' is'} currently open with suppliers.",
            severity="info",
            metric_value=open_pos,
            metric_label="Open POs",
        ))

    # ── Supply Chain Insights ────────────────────────────────
    pending_shipments = int(
        (await db.execute(
            select(func.count()).select_from(Shipment).where(
                Shipment.status.in_(["pending", "picked", "packed"])
            )
        )).scalar() or 0
    )

    if pending_shipments > 5:
        insights.append(_insight(
            InsightCategory.LOGISTICS_EFFICIENCY,
            f"{pending_shipments} Shipments Awaiting Dispatch",
            f"Shipping backlog has {pending_shipments} orders waiting. "
            "Delivery SLA compliance may be at risk.",
            severity="warning",
            metric_value=pending_shipments,
            metric_label="Pending Shipments",
            recommendation="Prioritise shipments by customer tier and due date.",
        ))
    elif pending_shipments > 0:
        insights.append(_insight(
            InsightCategory.LOGISTICS_EFFICIENCY,
            f"{pending_shipments} Pending Shipment{'s' if pending_shipments != 1 else ''}",
            f"{pending_shipments} shipment{'s' if pending_shipments != 1 else ''} in the outbound queue.",
            severity="info",
            metric_value=pending_shipments,
            metric_label="Pending Shipments",
        ))

    # ── Workforce Insights ───────────────────────────────────
    overdue_tasks = int(
        (await db.execute(
            select(func.count()).select_from(Task).where(
                and_(
                    Task.status.in_([TaskStatus.OPEN, TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                    Task.due_date < now,
                )
            )
        )).scalar() or 0
    )
    blocked_tasks = int(
        (await db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.BLOCKED)
        )).scalar() or 0
    )

    if overdue_tasks > 0:
        insights.append(_insight(
            InsightCategory.WORKFORCE_ANALYTICS,
            f"{overdue_tasks} Overdue Task{'s' if overdue_tasks != 1 else ''}",
            f"{overdue_tasks} task{'s have' if overdue_tasks != 1 else ' has'} passed their due date without completion.",
            severity="warning" if overdue_tasks > 5 else "info",
            metric_value=overdue_tasks,
            metric_label="Overdue Tasks",
            recommendation="Reassign or escalate overdue tasks to prevent cascading delays.",
        ))

    if blocked_tasks > 0:
        insights.append(_insight(
            InsightCategory.WORKFORCE_ANALYTICS,
            f"{blocked_tasks} Blocked Task{'s' if blocked_tasks != 1 else ''}",
            f"{blocked_tasks} task{'s are' if blocked_tasks != 1 else ' is'} blocked and cannot proceed.",
            severity="warning",
            metric_value=blocked_tasks,
            metric_label="Blocked Tasks",
            recommendation="Identify and resolve blockers; escalate to management if dependencies are cross-team.",
        ))

    # ── Company Health (always generated, executive-level) ───
    total_open_ncs = open_ncs
    total_on_hold = on_hold_wo
    total_active_andons = active_andons
    risk_count = (
        (1 if critical_ncs > 0 else 0)
        + (1 if on_hold_wo > 3 else 0)
        + (1 if active_andons > 3 else 0)
        + (1 if overdue_invoices > 0 else 0)
        + (1 if overdue_tasks > 5 else 0)
    )
    if risk_count == 0:
        health_label = "HEALTHY"
        health_sev = "info"
    elif risk_count <= 2:
        health_label = "MODERATE RISK"
        health_sev = "warning"
    else:
        health_label = "ELEVATED RISK"
        health_sev = "critical"

    insights.append(_insight(
        InsightCategory.COMPANY_HEALTH,
        f"Company Health: {health_label}",
        f"Overall operational health assessment based on {risk_count} risk indicator{'s' if risk_count != 1 else ''}. "
        f"Quality: {open_ncs} open NCs ({critical_ncs} critical). "
        f"Ops: {in_progress_wo} WOs active, {on_hold_wo} on hold. "
        f"Finance: {overdue_invoices} overdue invoices. "
        f"Workforce: {overdue_tasks} overdue tasks.",
        severity=health_sev,
        metric_value=risk_count,
        metric_label="Risk Indicators",
    ))

    # ── HR Insights (data thread harmonization) ──────────────
    active_employees = int(
        (await db.execute(
            select(func.count()).select_from(EmployeeProfile).where(
                EmployeeProfile.status == "active"
            )
        )).scalar() or 0
    )
    terminated_recent = int(
        (await db.execute(
            select(func.count()).select_from(EmployeeProfile).where(
                and_(
                    EmployeeProfile.status == "terminated",
                    EmployeeProfile.termination_date >= (now - timedelta(days=90)),
                )
            )
        )).scalar() or 0
    )
    open_positions = int(
        (await db.execute(
            select(func.count()).select_from(HRJobOpening).where(
                HRJobOpening.status == "open"
            )
        )).scalar() or 0
    )
    turnover_rate = round((terminated_recent / max(active_employees, 1)) * 100, 1)

    if turnover_rate > 10:
        insights.append(_insight(
            InsightCategory.RETENTION_RISK,
            f"Elevated Turnover Rate: {turnover_rate}%",
            f"{terminated_recent} employee{'s' if terminated_recent != 1 else ''} terminated in the last 90 days "
            f"({active_employees} active). Turnover rate of {turnover_rate}% exceeds healthy threshold.",
            severity="warning" if turnover_rate <= 20 else "critical",
            metric_value=turnover_rate,
            metric_label="Turnover %",
            recommendation="Conduct stay interviews and review compensation competitiveness.",
        ))
    elif active_employees > 0:
        insights.append(_insight(
            InsightCategory.WORKFORCE_ANALYTICS,
            f"Headcount: {active_employees} Active Employees",
            f"{active_employees} employees active. {terminated_recent} departed in 90 days. "
            f"Turnover rate: {turnover_rate}%.",
            severity="info",
            metric_value=active_employees,
            metric_label="Headcount",
        ))

    if open_positions > 3:
        insights.append(_insight(
            InsightCategory.HEADCOUNT_PLANNING,
            f"{open_positions} Open Positions",
            f"{open_positions} job opening{'s require' if open_positions != 1 else ' requires'} active recruiting.",
            severity="warning" if open_positions > 5 else "info",
            metric_value=open_positions,
            metric_label="Open Positions",
            recommendation="Prioritize critical roles and consider internal mobility.",
        ))

    # ── Inventory / Supply Chain Insights (data thread harmonization) ─
    zero_stock = int(
        (await db.execute(
            select(func.count()).select_from(InventoryLevel).where(
                InventoryLevel.quantity_on_hand <= 0
            )
        )).scalar() or 0
    )
    pending_moves = int(
        (await db.execute(
            select(func.count()).select_from(StockMove).where(
                StockMove.status.in_(["draft", "waiting", "confirmed"])
            )
        )).scalar() or 0
    )
    open_mrp = int(
        (await db.execute(
            select(func.count()).select_from(MRPSuggestion).where(
                MRPSuggestion.status == "pending"
            )
        )).scalar() or 0
    )
    ap_unpaid = int(
        (await db.execute(
            select(func.count()).select_from(SupplierInvoice).where(
                SupplierInvoice.status.in_(["draft", "submitted", "approved", "posted"])
            )
        )).scalar() or 0
    )

    if zero_stock > 5:
        insights.append(_insight(
            InsightCategory.INVENTORY_OPTIMIZATION,
            f"{zero_stock} SKUs at Zero Stock",
            f"{zero_stock} items have zero quantity on hand. Production may be at risk of material shortages.",
            severity="warning" if zero_stock <= 15 else "critical",
            metric_value=zero_stock,
            metric_label="Zero-Stock Items",
            recommendation="Review MRP suggestions and expedite purchase orders for critical items.",
        ))
    elif zero_stock > 0:
        insights.append(_insight(
            InsightCategory.INVENTORY_OPTIMIZATION,
            f"{zero_stock} SKU{'s' if zero_stock != 1 else ''} at Zero Stock",
            f"{zero_stock} item{'s have' if zero_stock != 1 else ' has'} zero quantity on hand.",
            severity="info",
            metric_value=zero_stock,
            metric_label="Zero-Stock Items",
        ))

    if open_mrp > 5:
        insights.append(_insight(
            InsightCategory.REORDER_RECOMMENDATIONS,
            f"{open_mrp} Pending MRP Suggestions",
            f"MRP has generated {open_mrp} buy/build suggestions awaiting approval. "
            "Delays in processing may cascade into production schedules.",
            severity="warning" if open_mrp <= 15 else "critical",
            metric_value=open_mrp,
            metric_label="MRP Suggestions",
            recommendation="Review and approve/reject MRP suggestions within the planning horizon.",
        ))

    if ap_unpaid > 10:
        insights.append(_insight(
            InsightCategory.COST_OPTIMIZATION,
            f"{ap_unpaid} Unpaid Supplier Invoices",
            f"{ap_unpaid} supplier invoice{'s are' if ap_unpaid != 1 else ' is'} unpaid. "
            "Late payments risk supplier relationship damage and potential supply disruption.",
            severity="warning",
            metric_value=ap_unpaid,
            metric_label="AP Backlog",
            recommendation="Prioritize payment runs for suppliers with critical material delivery.",
        ))

    # ── Strategic Overview ───────────────────────────────────
    active_users = int(
        (await db.execute(
            select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
        )).scalar() or 0
    )

    insights.append(_insight(
        InsightCategory.STRATEGIC_OVERVIEW,
        "Executive Dashboard Summary",
        f"{active_users} active users. Pipeline: ${pipeline_value:,.0f}. "
        f"WOs in flight: {in_progress_wo}. Open NCs: {open_ncs}. "
        f"Pending shipments: {pending_shipments}.",
        severity="info",
        metric_value={
            "active_users": active_users,
            "pipeline_value": pipeline_value,
            "active_work_orders": in_progress_wo,
            "open_ncs": open_ncs,
            "pending_shipments": pending_shipments,
        },
        metric_label="Summary",
    ))

    # ── Maintenance Insights ─────────────────────────────────
    overdue_pms = int(
        (await db.execute(
            select(func.count()).select_from(PMSchedule).where(
                and_(
                    PMSchedule.is_active.is_(True),
                    PMSchedule.next_due < now,
                )
            )
        )).scalar() or 0
    )
    open_maint_wos = int(
        (await db.execute(
            select(func.count()).select_from(MaintenanceWorkOrder).where(
                MaintenanceWorkOrder.status.in_(["open", "in_progress"])
            )
        )).scalar() or 0
    )
    emergency_maint = int(
        (await db.execute(
            select(func.count()).select_from(MaintenanceWorkOrder).where(
                and_(
                    MaintenanceWorkOrder.work_order_type == "emergency",
                    MaintenanceWorkOrder.status.in_(["open", "in_progress"]),
                )
            )
        )).scalar() or 0
    )
    low_spare_parts = int(
        (await db.execute(
            select(func.count()).select_from(SparePart).where(
                SparePart.quantity_on_hand <= SparePart.reorder_point
            )
        )).scalar() or 0
    )
    recent_failures = int(
        (await db.execute(
            select(func.count()).select_from(FailureRecord).where(
                FailureRecord.failure_date >= thirty_days_ago
            )
        )).scalar() or 0
    )
    recent_downtime_hours = float(
        (await db.execute(
            select(func.coalesce(func.sum(DowntimeEvent.duration_minutes), 0)).where(
                DowntimeEvent.start_time >= thirty_days_ago
            )
        )).scalar() or 0
    ) / 60.0

    if overdue_pms > 0:
        insights.append(_insight(
            InsightCategory.MAINTENANCE_SCHEDULE,
            f"{overdue_pms} Overdue PM Schedule{'s' if overdue_pms != 1 else ''}",
            f"{overdue_pms} preventive maintenance schedule{'s have' if overdue_pms != 1 else ' has'} "
            "passed their due date. Equipment reliability is at risk.",
            severity="critical" if overdue_pms > 5 else "warning",
            metric_value=overdue_pms,
            metric_label="Overdue PMs",
            recommendation="Prioritize overdue PMs by asset criticality and schedule execution immediately.",
        ))

    if emergency_maint > 0:
        insights.append(_insight(
            InsightCategory.PREDICTIVE_MAINTENANCE,
            f"{emergency_maint} Emergency Maintenance WO{'s' if emergency_maint != 1 else ''}",
            f"{emergency_maint} emergency work order{'s are' if emergency_maint != 1 else ' is'} active. "
            "High emergency-to-planned ratio indicates reactive maintenance culture.",
            severity="critical",
            metric_value=emergency_maint,
            metric_label="Emergency WOs",
            recommendation="Analyze root causes and strengthen the PM program to prevent recurrence.",
        ))

    if open_maint_wos > 0:
        insights.append(_insight(
            InsightCategory.EQUIPMENT_HEALTH,
            f"{open_maint_wos} Open Maintenance Work Order{'s' if open_maint_wos != 1 else ''}",
            f"{open_maint_wos} maintenance work order{'s are' if open_maint_wos != 1 else ' is'} "
            "currently open or in progress.",
            severity="info" if open_maint_wos <= 10 else "warning",
            metric_value=open_maint_wos,
            metric_label="Open Maint WOs",
        ))

    if recent_failures > 0:
        insights.append(_insight(
            InsightCategory.MTBF_ANALYSIS,
            f"{recent_failures} Equipment Failure{'s' if recent_failures != 1 else ''} (30 days)",
            f"{recent_failures} failure{'s' if recent_failures != 1 else ''} recorded in the last 30 days. "
            f"Total downtime: {recent_downtime_hours:.1f} hours.",
            severity="warning" if recent_failures <= 5 else "critical",
            metric_value=recent_failures,
            metric_label="Failures (30d)",
            recommendation="Review MTBF trends and consider predictive maintenance for high-failure assets.",
        ))

    if low_spare_parts > 0:
        insights.append(_insight(
            InsightCategory.SPARE_PARTS_FORECAST,
            f"{low_spare_parts} Spare Part{'s' if low_spare_parts != 1 else ''} Below Reorder Point",
            f"{low_spare_parts} spare part{'s have' if low_spare_parts != 1 else ' has'} "
            "dropped below their reorder point. Maintenance delays may result.",
            severity="warning",
            metric_value=low_spare_parts,
            metric_label="Low Spares",
            recommendation="Generate purchase requisitions for critical spare parts immediately.",
        ))

    if recent_downtime_hours > 0:
        insights.append(_insight(
            InsightCategory.DOWNTIME_PREDICTION,
            f"{recent_downtime_hours:.1f}h Total Downtime (30 days)",
            f"Equipment downtime totalled {recent_downtime_hours:.1f} hours over the last 30 days.",
            severity="info" if recent_downtime_hours < 40 else "warning",
            metric_value=round(recent_downtime_hours, 1),
            metric_label="Downtime Hours",
        ))

    # ── Training / Certification Insights ────────────────────
    expiring_certs = int(
        (await db.execute(
            select(func.count()).select_from(UserSkill).where(
                and_(
                    UserSkill.certification_status == "certified",
                    UserSkill.expiration_date.isnot(None),
                    UserSkill.expiration_date < (now + timedelta(days=30)),
                    UserSkill.expiration_date >= now,
                )
            )
        )).scalar() or 0
    )
    expired_certs = int(
        (await db.execute(
            select(func.count()).select_from(UserSkill).where(
                and_(
                    UserSkill.certification_status == "expired",
                )
            )
        )).scalar() or 0
    )
    scheduled_trainings = int(
        (await db.execute(
            select(func.count()).select_from(Training).where(
                Training.status == "scheduled"
            )
        )).scalar() or 0
    )

    if expired_certs > 0:
        insights.append(_insight(
            InsightCategory.TRAINING_GAPS,
            f"{expired_certs} Expired Certification{'s' if expired_certs != 1 else ''}",
            f"{expired_certs} employee certification{'s have' if expired_certs != 1 else ' has'} expired. "
            "Non-compliant operators may be working on controlled processes.",
            severity="critical" if expired_certs > 3 else "warning",
            metric_value=expired_certs,
            metric_label="Expired Certs",
            recommendation="Schedule recertification training for affected employees immediately.",
        ))

    if expiring_certs > 0:
        insights.append(_insight(
            InsightCategory.TRAINING_GAPS,
            f"{expiring_certs} Certification{'s' if expiring_certs != 1 else ''} Expiring Within 30 Days",
            f"{expiring_certs} certification{'s will' if expiring_certs != 1 else ' will'} expire "
            "within 30 days. Plan recertification proactively.",
            severity="warning",
            metric_value=expiring_certs,
            metric_label="Expiring Certs",
            recommendation="Enroll affected employees in upcoming training sessions.",
        ))

    if scheduled_trainings > 0:
        insights.append(_insight(
            InsightCategory.TRAINING_GAPS,
            f"{scheduled_trainings} Scheduled Training Session{'s' if scheduled_trainings != 1 else ''}",
            f"{scheduled_trainings} training session{'s are' if scheduled_trainings != 1 else ' is'} "
            "upcoming.",
            severity="info",
            metric_value=scheduled_trainings,
            metric_label="Scheduled Trainings",
        ))

    # ── Project Management Insights ──────────────────────────
    active_projects = int(
        (await db.execute(
            select(func.count()).select_from(Project).where(
                Project.status == ProjectStatus.ACTIVE.value
            )
        )).scalar() or 0
    )
    on_hold_projects = int(
        (await db.execute(
            select(func.count()).select_from(Project).where(
                Project.status == ProjectStatus.ON_HOLD.value
            )
        )).scalar() or 0
    )
    open_issues_critical = int(
        (await db.execute(
            select(func.count()).select_from(Issue).where(
                and_(
                    Issue.status.in_([IssueStatus.NEW.value, IssueStatus.IN_PROGRESS.value]),
                    Issue.severity == PMIssueSeverity.CRITICAL.value,
                )
            )
        )).scalar() or 0
    )
    blocked_stories = int(
        (await db.execute(
            select(func.count()).select_from(UserStory).where(
                UserStory.is_blocked.is_(True)
            )
        )).scalar() or 0
    )

    if active_projects > 0:
        insights.append(_insight(
            InsightCategory.RESOURCE_UTILIZATION,
            f"{active_projects} Active Project{'s' if active_projects != 1 else ''}",
            f"{active_projects} project{'s are' if active_projects != 1 else ' is'} currently active. "
            f"{on_hold_projects} on hold.",
            severity="info",
            metric_value=active_projects,
            metric_label="Active Projects",
        ))

    if open_issues_critical > 0:
        insights.append(_insight(
            InsightCategory.RISK_ASSESSMENT,
            f"{open_issues_critical} Critical Issue{'s' if open_issues_critical != 1 else ''} Open",
            f"{open_issues_critical} critical-severity issue{'s require' if open_issues_critical != 1 else ' requires'} "
            "immediate attention across projects.",
            severity="critical",
            metric_value=open_issues_critical,
            metric_label="Critical Issues",
            recommendation="Escalate critical issues to project owners and assign resolution owners.",
        ))

    if blocked_stories > 0:
        insights.append(_insight(
            InsightCategory.SCHEDULE_OPTIMIZATION,
            f"{blocked_stories} Blocked User Stor{'ies' if blocked_stories != 1 else 'y'}",
            f"{blocked_stories} user stor{'ies are' if blocked_stories != 1 else 'y is'} blocked. "
            "Sprint velocity may be impacted.",
            severity="warning",
            metric_value=blocked_stories,
            metric_label="Blocked Stories",
            recommendation="Identify and resolve dependencies; re-prioritize sprint backlog if needed.",
        ))

    # ── Task / Personal Productivity Insights ────────────────
    if overdue_tasks > 0:
        insights.append(_insight(
            InsightCategory.UPCOMING_DEADLINES,
            f"{overdue_tasks} Task{'s' if overdue_tasks != 1 else ''} Past Due",
            f"{overdue_tasks} task{'s have' if overdue_tasks != 1 else ' has'} missed their deadline.",
            severity="warning" if overdue_tasks <= 5 else "critical",
            metric_value=overdue_tasks,
            metric_label="Overdue Tasks",
            recommendation="Review and reassign overdue tasks; update stakeholders on revised timelines.",
        ))

    if blocked_tasks > 0:
        insights.append(_insight(
            InsightCategory.TASK_RECOMMENDATIONS,
            f"Unblock {blocked_tasks} Task{'s' if blocked_tasks != 1 else ''}",
            f"{blocked_tasks} task{'s are' if blocked_tasks != 1 else ' is'} blocked. "
            "Resolving blockers will improve team throughput.",
            severity="warning",
            metric_value=blocked_tasks,
            metric_label="Blocked Tasks",
            recommendation="Escalate blockers to the responsible manager for resolution.",
        ))

    return insights
