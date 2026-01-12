from __future__ import annotations

from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.utils import APIResponse, build_response
from sensei.services.ops.cognitive_obeya import (
    get_cognitive_obeya,
    MetricCategory,
    DepartmentType,
    AlertSeverity
)
from sensei.models.quality import NonConformance
from sensei.models.work_order import WorkOrder
from sensei.models.rfq import RFQ

router = APIRouter()

@router.get("/dashboard", response_model=APIResponse)
async def get_obeya_dashboard(
    db: DBSession,
    user: CurrentUser
):
    """
    Get Cognitive Obeya dashboard with real-time prescriptive analytics.
    """
    obeya = get_cognitive_obeya()
    
    # 1. Pull real metrics from database
    # Quality: count of open NCs
    ncr_count = await db.scalar(
        select(func.count(NonConformance.id)).where(NonConformance.status != "closed")
    )
    obeya.record_metric(
        category=MetricCategory.QUALITY,
        name="Open NCRs",
        value=float(ncr_count or 0),
        target=2.0,
        unit=""
    )
    
    # Delivery: On-time delivery rate (simplified)
    total_wo = await db.scalar(select(func.count(WorkOrder.id)))
    on_time_wo = await db.scalar(
        select(func.count(WorkOrder.id)).where(WorkOrder.status == "completed") # Placeholder logic
    )
    otd_rate = (on_time_wo / total_wo * 100) if total_wo and total_wo > 0 else 95.0
    obeya.record_metric(
        category=MetricCategory.DELIVERY,
        name="On-Time Delivery",
        value=float(otd_rate),
        target=98.0,
        unit="%"
    )
    
    # 2. Register real events for cross-functional analysis
    # E.g. find high-priority open RFQs
    rfq_count = await db.scalar(select(func.count(RFQ.id)).where(RFQ.status == "draft"))
    if rfq_count and rfq_count > 5:
        obeya.register_cross_functional_event(
            department=DepartmentType.SALES,
            event_type="rfq_backlog",
            description=f"Sales has {rfq_count} draft RFQs pending",
            severity=AlertSeverity.WARNING
        )

    # 3. Trigger analysis
    insights = obeya.get_obeya_dashboard()
    silo_alerts = obeya.get_silo_alerts()
    rebalance_suggestions = obeya.analyze_resource_rebalancing()
    heijunka = obeya.get_heijunka_suggestions()
    
    return build_response(
        data={
            "summary": insights,
            "silo_alerts": silo_alerts,
            "resource_rebalancing": rebalance_suggestions,
            "heijunka_suggestions": heijunka
        }
    )

@router.get("/metrics/{metric_id}/insights", response_model=APIResponse)
async def get_metric_insights(
    metric_id: str,
    db: DBSession,
    user: CurrentUser
):
    """Get prescriptive insights for a specific metric."""
    obeya = get_cognitive_obeya()
    # In production, we'd populate history here
    insights = obeya.get_metric_insights(metric_id)
    return build_response(data=insights)
