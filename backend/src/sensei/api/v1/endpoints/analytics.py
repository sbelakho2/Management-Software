from typing import Any, Annotated, TypeAlias
from fastapi import APIRouter, Depends
from sensei.services.ai.enhanced_ml_pipeline import get_ml_pipeline_service, EnhancedMLPipelineService
from sensei.services.ops.analytics_warehouse import AnalyticsWarehouseService, FactType
from sensei.services.core.role_insights_config import filter_insights_for_role
from sensei.api import deps
from sensei.core.pii import mask_analytics_data

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
    ml_service: EnhancedMLPipelineService = Depends(get_ml_pipeline_service),
):
    """Get ML pipeline health and statistics."""
    return ml_service.get_pipeline_health()

@router.get("/insights", response_model=list[dict[str, Any]])
async def get_ml_insights(
    ml_service: EnhancedMLPipelineService = Depends(get_ml_pipeline_service),
    token_data: deps.TokenData = Depends(deps.get_token_data)
):
    """Get AI/ML driven insights filtered by user role."""
    # No demo/fabricated insights: if the ML service doesn't provide persisted
    # insights yet, return an empty list.
    all_insights: list[dict[str, Any]] = []
    
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
    """Get key performance indicators and their trends."""
    # Attempt to fetch real data from warehouse
    records = await warehouse.get_exported_records(
        db=db,
        actor_roles=token_data.roles,
        fact_type=FactType.QUALITY_METRIC
    )
    
    if records:
        # Transform warehouse records to trend format
        trends = []
        for r in records[:5]: # Take last 5
            trends.append({
                "metric": r.data.get("metric_name", "Unknown"),
                "current_value": r.data.get("value", 0),
                "previous_value": r.data.get("previous_value", 0),
                "change_percent": r.data.get("change_percent", 0),
                "trend": "up" if r.data.get("change_percent", 0) > 0 else "down",
                "prediction_7d": r.data.get("predicted_value", 0)
            })
        return await mask_analytics_data(trends, token_data.roles)

    # No demo fallback: return empty when warehouse has no data.
    return await mask_analytics_data([], token_data.roles)
