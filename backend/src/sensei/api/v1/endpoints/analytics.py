from typing import Any, Annotated, TypeAlias
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, case
from sensei.services.ai.enhanced_ml_pipeline import get_ml_pipeline_service, EnhancedMLPipelineService
from sensei.services.ops.analytics_warehouse import AnalyticsWarehouseService, FactType
from sensei.services.ops.insight_generator import generate_insights
from sensei.services.core.role_insights_config import filter_insights_for_role
from sensei.api import deps
from sensei.core.pii import mask_analytics_data
from sensei.models.work_order import WorkOrder, WorkOrderStatus
from sensei.models.quality import NonConformance
from sensei.models.andon import AndonEvent

# Role requirements
AllowAnalytics: TypeAlias = deps.require_role("admin", "ceo", "gm", "exec", "ops", "finance", "quality")  # type: ignore[valid-type]
AllowAdminAnalytics: TypeAlias = deps.require_role("admin", "ceo", "gm")  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                ["admin", "ceo", "gm", "exec", "ops", "finance", "quality"]
            )
        )
    ]
)

# Simple singleton for AnalyticsWarehouseService as well
_analytics_warehouse_service = AnalyticsWarehouseService()

def get_analytics_warehouse_service() -> AnalyticsWarehouseService:
    return _analytics_warehouse_service

@router.get("/health", response_model=dict[str, Any])
async def get_analytics_health(
    db: deps.DBSession,
    ml_service: EnhancedMLPipelineService = Depends(get_ml_pipeline_service),
):
    """Get ML pipeline health, overall health score, and health history.

    Returns real DB-backed metrics:
    - overall_health_score: 0-1 composite score from WO completion, NC rate, andon rate
    - health_history: list of 10 daily composite scores (most recent last)
    """
    base = ml_service.get_pipeline_health()
    now = datetime.now(timezone.utc)
    history: list[float] = []

    for day_offset in range(9, -1, -1):
        day_start = (now - timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # WO completion ratio for this day
        wo_total = (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.created_at < day_end
            )
        )).scalar() or 1
        wo_completed = (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.COMPLETED,
                WorkOrder.actual_end >= day_start,
                WorkOrder.actual_end < day_end,
            )
        )).scalar() or 0

        # NC count for this day (lower is healthier)
        nc_count = (await db.execute(
            select(func.count()).select_from(NonConformance).where(
                NonConformance.created_at >= day_start,
                NonConformance.created_at < day_end,
            )
        )).scalar() or 0

        # Composite score: 70% WO health + 30% NC health
        wo_health = min(wo_completed / max(wo_total, 1), 1.0)
        nc_health = max(1.0 - nc_count / 10.0, 0.0)  # 10+ NCs/day = 0 health
        score = round(0.7 * wo_health + 0.3 * nc_health, 3)
        history.append(score)

    base["health_history"] = history
    base["overall_health_score"] = history[-1] if history else 0.5
    return base

@router.get("/insights", response_model=list[dict[str, Any]])
async def get_ml_insights(
    db: deps.DBSession,
    ml_service: EnhancedMLPipelineService = Depends(get_ml_pipeline_service),
    token_data: deps.TokenData = Depends(deps.get_token_data)
):
    """Get AI/ML driven insights generated from live database metrics."""
    # Generate real insights from database state
    all_insights = await generate_insights(db)
    
    # INTEGRATED: Filter insights based on user's roles
    filtered_insights = filter_insights_for_role(all_insights, token_data.roles)
    
    return await mask_analytics_data(filtered_insights, token_data.roles)

@router.get("/trends", response_model=list[dict[str, Any]])
async def get_performance_trends(
    _: AllowAnalytics,
    db: deps.DBSession,
    warehouse: AnalyticsWarehouseService = Depends(get_analytics_warehouse_service),
    token_data: deps.TokenData = Depends(deps.get_token_data)
):
    """Get key performance indicators and their trends.

    Always includes an OEE metric computed from real work-order data.
    """
    # Attempt to fetch real data from warehouse
    records = await warehouse.get_exported_records(
        db=db,
        actor_roles=token_data.roles,
        fact_type=FactType.QUALITY_METRIC
    )

    trends: list[dict[str, Any]] = []
    if records:
        for r in records[:5]:
            trends.append({
                "metric": r.data.get("metric_name", "Unknown"),
                "current_value": r.data.get("value", 0),
                "previous_value": r.data.get("previous_value", 0),
                "change_percent": r.data.get("change_percent", 0),
                "trend": "up" if r.data.get("change_percent", 0) > 0 else "down",
                "prediction_7d": r.data.get("predicted_value", 0)
            })

    # Always compute OEE from real work-order data (if not already in trends)
    has_oee = any("oee" in (t.get("metric", "")).lower() for t in trends)
    if not has_oee:
        now = datetime.now(timezone.utc)
        period_end = now
        period_start = now - timedelta(days=30)
        prev_start = period_start - timedelta(days=30)

        wo_total_cur = (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.created_at >= period_start,
                WorkOrder.created_at < period_end,
            )
        )).scalar() or 0
        wo_completed_cur = (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.COMPLETED,
                WorkOrder.actual_end >= period_start,
                WorkOrder.actual_end < period_end,
            )
        )).scalar() or 0
        wo_total_prev = (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.created_at >= prev_start,
                WorkOrder.created_at < period_start,
            )
        )).scalar() or 0
        wo_completed_prev = (await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.COMPLETED,
                WorkOrder.actual_end >= prev_start,
                WorkOrder.actual_end < period_start,
            )
        )).scalar() or 0

        cur_oee = round((wo_completed_cur / max(wo_total_cur, 1)) * 100, 1)
        prev_oee = round((wo_completed_prev / max(wo_total_prev, 1)) * 100, 1)
        change = round(cur_oee - prev_oee, 1)

        trends.insert(0, {
            "metric": "OEE (Overall Equipment Effectiveness)",
            "current_value": cur_oee,
            "previous_value": prev_oee,
            "change_percent": change,
            "trend": "up" if change > 0 else ("down" if change < 0 else "stable"),
            "prediction_7d": round(cur_oee + change * 0.5, 1),
        })

    return await mask_analytics_data(trends, token_data.roles)
