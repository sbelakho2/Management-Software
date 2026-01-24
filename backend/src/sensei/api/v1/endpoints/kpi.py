"""
KPI Metrics API Endpoints.

Provides REST API for managing KPIs, recording values, analyzing trends, and dashboards.
"""

from datetime import datetime, date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import get_db
from sensei.services.ops.kpi_metrics import (
    KPIDefinition,
    KPIValue,
    KPIDashboard,
    KPIThreshold,
    KPIDataSource,
    KPICategory,
    KPIUnit,
    KPIDirection,
    KPIStatus,
    AggregationType,
    TrendDirection,
    build_kpi_definition,
    get_default_kpi_ids,
    get_default_dashboard_ids,
)

from sensei.services.ops.kpi_app_services import (
    kpi_service as _service,
    muda_lesson_engine as _muda_lesson_engine,
    muda_nudging_service as _muda_nudging_service,
)

router = APIRouter(prefix="/kpi", tags=["KPI Metrics"])



# --------------------------------------------------------------------------
# Request/Response Schemas
# --------------------------------------------------------------------------

class ThresholdSchema(BaseModel):
    """KPI threshold configuration."""
    
    target: float
    warning_threshold: float = 10.0
    critical_threshold: float = 20.0
    min_value: float | None = None
    max_value: float | None = None


class DataSourceSchema(BaseModel):
    """KPI data source configuration."""
    
    entity_type: str
    fields: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)
    aggregation: str = "average"  # AggregationType value
    timestamp_field: str = "created_at"
    group_by: list[str] = Field(default_factory=list)


class KPIDefinitionCreateRequest(BaseModel):
    """Request to create a KPI definition."""
    
    id: str | None = None
    name: str
    description: str
    category: str  # KPICategory value
    unit: str  # KPIUnit value
    direction: str  # KPIDirection value
    threshold: ThresholdSchema | None = None
    data_source: DataSourceSchema | None = None
    formula: str = ""
    component_kpis: list[str] = Field(default_factory=list)
    decimal_places: int = 2
    display_format: str = ""
    owner_role: str = ""
    frequency: str = "daily"
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)
    custom_calculator: str = ""


class KPIDefinitionUpdateRequest(BaseModel):
    """Request to update a KPI definition."""
    
    name: str | None = None
    description: str | None = None
    threshold: ThresholdSchema | None = None
    decimal_places: int | None = None
    display_format: str | None = None
    frequency: str | None = None
    is_active: bool | None = None
    tags: list[str] | None = None


class KPIDefinitionResponse(BaseModel):
    """KPI definition response."""
    
    id: str
    name: str
    description: str
    category: str
    unit: str
    direction: str
    threshold: ThresholdSchema | None
    formula: str
    component_kpis: list[str]
    decimal_places: int
    display_format: str
    owner_role: str
    frequency: str
    is_active: bool
    tags: list[str]


class KPIValueRecordRequest(BaseModel):
    """Request to record a KPI value."""
    
    kpi_id: str
    value: float
    timestamp: datetime | None = None
    period_start: date | None = None
    period_end: date | None = None
    dimensions: dict[str, str] = Field(default_factory=dict)
    sample_size: int = 0


class KPIValueResponse(BaseModel):
    """KPI value response."""
    
    id: str
    kpi_id: str
    value: float
    timestamp: datetime
    period_start: date | None
    period_end: date | None
    status: str
    dimensions: dict[str, str]
    calculated_at: datetime
    sample_size: int


class KPICalculationRequest(BaseModel):
    """Request to calculate a KPI."""
    
    kpi_id: str
    start_date: date
    end_date: date
    dimensions: dict[str, str] = Field(default_factory=dict)


class KPICalculationResponse(BaseModel):
    """KPI calculation result response."""
    
    kpi_id: str
    success: bool
    value: KPIValueResponse | None = None
    error: str = ""
    calculation_time_ms: float = 0.0


class KPITrendResponse(BaseModel):
    """KPI trend analysis response."""
    
    kpi_id: str
    direction: str
    current_value: float
    previous_value: float
    change_absolute: float
    change_percentage: float
    current_period_start: date | None
    current_period_end: date | None
    previous_period_start: date | None
    previous_period_end: date | None
    moving_average: float | None
    standard_deviation: float | None


class DashboardCreateRequest(BaseModel):
    """Request to create a dashboard."""
    
    id: str | None = None
    name: str
    description: str
    kpi_ids: list[str] = Field(default_factory=list)
    layout: dict[str, dict[str, Any]] = Field(default_factory=dict)
    default_time_range: str = "last_30_days"
    dimension_filters: dict[str, list[str]] = Field(default_factory=dict)
    owner_id: str = ""
    is_public: bool = False


class DashboardUpdateRequest(BaseModel):
    """Request to update a dashboard."""
    
    name: str | None = None
    description: str | None = None
    kpi_ids: list[str] | None = None
    layout: dict[str, dict[str, Any]] | None = None
    default_time_range: str | None = None
    is_public: bool | None = None


class DashboardResponse(BaseModel):
    """Dashboard response."""
    
    id: str
    name: str
    description: str
    kpi_ids: list[str]
    layout: dict[str, dict[str, Any]]
    default_time_range: str
    dimension_filters: dict[str, list[str]]
    owner_id: str
    is_public: bool
    created_at: datetime


class DashboardDataResponse(BaseModel):
    """Dashboard data response."""
    
    dashboard: dict[str, Any]
    period: dict[str, str]
    kpis: dict[str, dict[str, Any]]


# --------------------------------------------------------------------------
# Muda-aware contextual nudges
# --------------------------------------------------------------------------


class MudaNudgesRequest(BaseModel):
    """Request to generate muda-aware micro-lesson nudges."""

    recipient_id: str = Field(..., min_length=1, max_length=100)
    dimensions: dict[str, str] = Field(default_factory=dict)
    overrides: dict[str, Any] = Field(default_factory=dict)
    include_knowledge: bool = True


class MudaNudgeResponse(BaseModel):
    """A generated micro-lesson nudge."""

    trigger: str
    recipient_id: str
    trigger_context: dict[str, Any]

    delivery_id: str | None
    lesson_id: str | None
    lesson_title: str | None
    lesson_summary: str | None
    lesson_category: str | None

    recommended_documents: list[dict[str, Any]]
    generated_at: datetime


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _definition_to_response(d: KPIDefinition) -> KPIDefinitionResponse:
    """Convert definition to response."""
    threshold = None
    if d.threshold:
        threshold = ThresholdSchema(
            target=d.threshold.target,
            warning_threshold=d.threshold.warning_threshold,
            critical_threshold=d.threshold.critical_threshold,
            min_value=d.threshold.min_value,
            max_value=d.threshold.max_value,
        )
    
    return KPIDefinitionResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        category=d.category.value,
        unit=d.unit.value,
        direction=d.direction.value,
        threshold=threshold,
        formula=d.formula,
        component_kpis=d.component_kpis,
        decimal_places=d.decimal_places,
        display_format=d.display_format,
        owner_role=d.owner_role,
        frequency=d.frequency,
        is_active=d.is_active,
        tags=d.tags,
    )


@router.post(
    "/muda-nudges",
    response_model=list[MudaNudgeResponse],
    summary="Generate muda-aware micro-lesson nudges",
)
async def generate_muda_nudges(
    request: MudaNudgesRequest,
    db: AsyncSession = Depends(get_db),
) -> list[MudaNudgeResponse]:
    """Generate contextual micro-lesson nudges from KPI variance.

    Uses latest KPI values from the in-memory KPI store and optional overrides.
    """

    nudges = await _muda_nudging_service.generate_nudges(
        db,
        recipient_id=UUID(request.recipient_id),
        dimensions=request.dimensions or None,
        overrides=request.overrides or None,
        include_knowledge=request.include_knowledge,
    )

    return [
        MudaNudgeResponse(
            trigger=nudge.trigger.value,
            recipient_id=nudge.recipient_id,
            trigger_context=nudge.trigger_context,
            delivery_id=nudge.delivery_id,
            lesson_id=nudge.lesson_id,
            lesson_title=nudge.lesson_title,
            lesson_summary=nudge.lesson_summary,
            lesson_category=nudge.lesson_category,
            recommended_documents=nudge.recommended_documents,
            generated_at=nudge.generated_at,
        )
        for nudge in nudges
    ]


def _value_to_response(v: KPIValue) -> KPIValueResponse:
    """Convert value to response."""
    return KPIValueResponse(
        id=v.id,
        kpi_id=v.kpi_id,
        value=v.value,
        timestamp=v.timestamp,
        period_start=v.period_start,
        period_end=v.period_end,
        status=v.status.value,
        dimensions=v.dimensions,
        calculated_at=v.calculated_at,
        sample_size=v.sample_size,
    )


def _dashboard_to_response(d: KPIDashboard) -> DashboardResponse:
    """Convert dashboard to response."""
    return DashboardResponse(
        id=d.id,
        name=d.name,
        description=d.description,
        kpi_ids=d.kpi_ids,
        layout=d.layout,
        default_time_range=d.default_time_range,
        dimension_filters=d.dimension_filters,
        owner_id=d.owner_id,
        is_public=d.is_public,
        created_at=d.created_at,
    )


# --------------------------------------------------------------------------
# KPI Definition Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/definitions",
    response_model=KPIDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create KPI definition",
    description="Create a new KPI definition.",
)
async def create_definition(request: KPIDefinitionCreateRequest) -> KPIDefinitionResponse:
    """Create a new KPI definition."""
    threshold = None
    if request.threshold:
        threshold = KPIThreshold(
            target=request.threshold.target,
            warning_threshold=request.threshold.warning_threshold,
            critical_threshold=request.threshold.critical_threshold,
            min_value=request.threshold.min_value,
            max_value=request.threshold.max_value,
        )
    
    data_source = None
    if request.data_source:
        data_source = KPIDataSource(
            entity_type=request.data_source.entity_type,
            fields=request.data_source.fields,
            filters=request.data_source.filters,
            aggregation=AggregationType(request.data_source.aggregation),
            timestamp_field=request.data_source.timestamp_field,
            group_by=request.data_source.group_by,
        )
    
    definition = KPIDefinition(
        id=request.id or "",
        name=request.name,
        description=request.description,
        category=KPICategory(request.category),
        unit=KPIUnit(request.unit),
        direction=KPIDirection(request.direction),
        threshold=threshold,
        data_source=data_source,
        formula=request.formula,
        component_kpis=request.component_kpis,
        decimal_places=request.decimal_places,
        display_format=request.display_format,
        owner_role=request.owner_role,
        frequency=request.frequency,
        is_active=request.is_active,
        tags=request.tags,
        custom_calculator=request.custom_calculator,
    )
    
    result = _service.create_definition(definition)
    return _definition_to_response(result)


@router.get(
    "/definitions",
    response_model=list[KPIDefinitionResponse],
    summary="List KPI definitions",
    description="List all KPI definitions with optional filtering.",
)
async def list_definitions(
    category: str | None = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only active KPIs"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
) -> list[KPIDefinitionResponse]:
    """List KPI definitions."""
    cat = KPICategory(category) if category else None
    definitions = _service.list_definitions(
        category=cat,
        active_only=active_only,
        tags=tags,
    )
    return [_definition_to_response(d) for d in definitions]


@router.get(
    "/definitions/defaults",
    response_model=list[str],
    summary="Get default KPI IDs",
    description="Get the IDs of all default KPIs.",
)
async def get_default_kpis() -> list[str]:
    """Get default KPI IDs."""
    return get_default_kpi_ids()


@router.get(
    "/definitions/{kpi_id}",
    response_model=KPIDefinitionResponse,
    summary="Get KPI definition",
    description="Get a specific KPI definition.",
)
async def get_definition(kpi_id: str) -> KPIDefinitionResponse:
    """Get a KPI definition."""
    definition = _service.get_definition(kpi_id)
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KPI {kpi_id} not found",
        )
    return _definition_to_response(definition)


@router.put(
    "/definitions/{kpi_id}",
    response_model=KPIDefinitionResponse,
    summary="Update KPI definition",
    description="Update an existing KPI definition.",
)
async def update_definition(
    kpi_id: str,
    request: KPIDefinitionUpdateRequest,
) -> KPIDefinitionResponse:
    """Update a KPI definition."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if "threshold" in updates and updates["threshold"]:
        updates["threshold"] = KPIThreshold(**updates["threshold"])
    
    result = _service.update_definition(kpi_id, updates)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KPI {kpi_id} not found",
        )
    return _definition_to_response(result)


@router.delete(
    "/definitions/{kpi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete KPI definition",
    description="Delete a KPI definition.",
)
async def delete_definition(kpi_id: str) -> None:
    """Delete a KPI definition."""
    # Prevent deletion of default KPIs
    if kpi_id in get_default_kpi_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default KPIs",
        )
    
    result = _service.delete_definition(kpi_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"KPI {kpi_id} not found",
        )


# --------------------------------------------------------------------------
# Value Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/values",
    response_model=KPIValueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record KPI value",
    description="Record a new KPI value.",
)
async def record_value(request: KPIValueRecordRequest) -> KPIValueResponse:
    """Record a KPI value."""
    from uuid import uuid4
    
    value = KPIValue(
        id=str(uuid4()),
        kpi_id=request.kpi_id,
        value=request.value,
        timestamp=request.timestamp or datetime.now(),
        period_start=request.period_start,
        period_end=request.period_end,
        dimensions=request.dimensions,
        sample_size=request.sample_size,
    )
    
    result = _service.record_value(value)
    return _value_to_response(result)


@router.get(
    "/values/{kpi_id}/latest",
    response_model=KPIValueResponse | None,
    summary="Get latest value",
    description="Get the most recent value for a KPI.",
)
async def get_latest_value(
    kpi_id: str,
    dimensions: str | None = Query(None, description="Dimensions as JSON"),
) -> KPIValueResponse | None:
    """Get the latest KPI value."""
    import json
    
    dims = None
    if dimensions:
        try:
            dims = json.loads(dimensions)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid dimensions JSON",
            )
    
    value = _service.get_latest_value(kpi_id, dims)
    if not value:
        return None
    return _value_to_response(value)


@router.get(
    "/values/{kpi_id}",
    response_model=list[KPIValueResponse],
    summary="Get KPI values",
    description="Get KPI values with optional filters.",
)
async def get_values(
    kpi_id: str,
    start_date: date | None = Query(None, description="Start date"),
    end_date: date | None = Query(None, description="End date"),
    limit: int | None = Query(None, description="Maximum values to return"),
) -> list[KPIValueResponse]:
    """Get KPI values."""
    values = _service.get_values(
        kpi_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [_value_to_response(v) for v in values]


# --------------------------------------------------------------------------
# Calculation Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/calculate",
    response_model=KPICalculationResponse,
    summary="Calculate KPI",
    description="Calculate a KPI value for a given period.",
)
async def calculate_kpi(request: KPICalculationRequest) -> KPICalculationResponse:
    """Calculate a KPI value."""
    result = _service.calculate_kpi(
        request.kpi_id,
        request.start_date,
        request.end_date,
        dimensions=request.dimensions or None,
    )
    
    return KPICalculationResponse(
        kpi_id=result.kpi_id,
        success=result.success,
        value=_value_to_response(result.value) if result.value else None,
        error=result.error,
        calculation_time_ms=result.calculation_time_ms,
    )


@router.post(
    "/calculate-batch",
    response_model=list[KPICalculationResponse],
    summary="Calculate multiple KPIs",
    description="Calculate multiple KPIs at once.",
)
async def calculate_batch(
    kpi_ids: list[str],
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
) -> list[KPICalculationResponse]:
    """Calculate multiple KPIs."""
    results = []
    for kpi_id in kpi_ids:
        result = _service.calculate_kpi(kpi_id, start_date, end_date)
        results.append(KPICalculationResponse(
            kpi_id=result.kpi_id,
            success=result.success,
            value=_value_to_response(result.value) if result.value else None,
            error=result.error,
            calculation_time_ms=result.calculation_time_ms,
        ))
    return results


# --------------------------------------------------------------------------
# Trend Analysis Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/trends/{kpi_id}",
    response_model=KPITrendResponse | None,
    summary="Analyze KPI trend",
    description="Analyze trend for a KPI by comparing periods.",
)
async def analyze_trend(
    kpi_id: str,
    start_date: date = Query(..., description="Current period start"),
    end_date: date = Query(..., description="Current period end"),
    comparison_periods: int = Query(1, description="Number of periods to compare"),
) -> KPITrendResponse | None:
    """Analyze KPI trend."""
    trend = _service.analyze_trend(kpi_id, start_date, end_date, comparison_periods)
    
    if not trend:
        return None
    
    return KPITrendResponse(
        kpi_id=trend.kpi_id,
        direction=trend.direction.value,
        current_value=trend.current_value,
        previous_value=trend.previous_value,
        change_absolute=trend.change_absolute,
        change_percentage=trend.change_percentage,
        current_period_start=trend.current_period[0] if trend.current_period else None,
        current_period_end=trend.current_period[1] if trend.current_period else None,
        previous_period_start=trend.previous_period[0] if trend.previous_period else None,
        previous_period_end=trend.previous_period[1] if trend.previous_period else None,
        moving_average=trend.moving_average,
        standard_deviation=trend.standard_deviation,
    )


# --------------------------------------------------------------------------
# Dashboard Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/dashboards",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create dashboard",
    description="Create a new KPI dashboard.",
)
async def create_dashboard(request: DashboardCreateRequest) -> DashboardResponse:
    """Create a dashboard."""
    dashboard = KPIDashboard(
        id=request.id or "",
        name=request.name,
        description=request.description,
        kpi_ids=request.kpi_ids,
        layout=request.layout,
        default_time_range=request.default_time_range,
        dimension_filters=request.dimension_filters,
        owner_id=request.owner_id,
        is_public=request.is_public,
    )
    
    result = _service.create_dashboard(dashboard)
    return _dashboard_to_response(result)


@router.get(
    "/dashboards",
    response_model=list[DashboardResponse],
    summary="List dashboards",
    description="List all dashboards.",
)
async def list_dashboards(
    owner_id: str | None = Query(None, description="Filter by owner"),
    include_public: bool = Query(True, description="Include public dashboards"),
) -> list[DashboardResponse]:
    """List dashboards."""
    dashboards = _service.list_dashboards(
        owner_id=owner_id,
        include_public=include_public,
    )
    return [_dashboard_to_response(d) for d in dashboards]


@router.get(
    "/dashboards/defaults",
    response_model=list[str],
    summary="Get default dashboard IDs",
    description="Get the IDs of all default dashboards.",
)
async def get_default_dashboards() -> list[str]:
    """Get default dashboard IDs."""
    return get_default_dashboard_ids()


@router.get(
    "/dashboards/{dashboard_id}",
    response_model=DashboardResponse,
    summary="Get dashboard",
    description="Get a specific dashboard.",
)
async def get_dashboard(dashboard_id: str) -> DashboardResponse:
    """Get a dashboard."""
    dashboard = _service.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found",
        )
    return _dashboard_to_response(dashboard)


@router.put(
    "/dashboards/{dashboard_id}",
    response_model=DashboardResponse,
    summary="Update dashboard",
    description="Update an existing dashboard.",
)
async def update_dashboard(
    dashboard_id: str,
    request: DashboardUpdateRequest,
) -> DashboardResponse:
    """Update a dashboard."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    result = _service.update_dashboard(dashboard_id, updates)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found",
        )
    return _dashboard_to_response(result)


@router.delete(
    "/dashboards/{dashboard_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete dashboard",
    description="Delete a dashboard.",
)
async def delete_dashboard(dashboard_id: str) -> None:
    """Delete a dashboard."""
    # Prevent deletion of default dashboards
    if dashboard_id in get_default_dashboard_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default dashboards",
        )
    
    result = _service.delete_dashboard(dashboard_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found",
        )


@router.get(
    "/dashboards/{dashboard_id}/data",
    response_model=DashboardDataResponse,
    summary="Get dashboard data",
    description="Get all KPI data for a dashboard.",
)
async def get_dashboard_data(
    dashboard_id: str,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    dimensions: str | None = Query(None, description="Dimensions as JSON"),
) -> DashboardDataResponse:
    """Get dashboard data."""
    import json
    
    dims = None
    if dimensions:
        try:
            dims = json.loads(dimensions)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid dimensions JSON",
            )
    
    dashboard = _service.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard {dashboard_id} not found",
        )
    
    data = _service.get_dashboard_data(dashboard_id, start_date, end_date, dims)
    
    return DashboardDataResponse(
        dashboard=data.get("dashboard", {}),
        period=data.get("period", {}),
        kpis=data.get("kpis", {}),
    )


# --------------------------------------------------------------------------
# Metadata Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/categories",
    response_model=list[dict[str, str]],
    summary="Get categories",
    description="Get available KPI categories.",
)
async def get_categories() -> list[dict[str, str]]:
    """Get available categories."""
    return [
        {"value": c.value, "name": c.name}
        for c in KPICategory
    ]


@router.get(
    "/units",
    response_model=list[dict[str, str]],
    summary="Get units",
    description="Get available KPI units.",
)
async def get_units() -> list[dict[str, str]]:
    """Get available units."""
    return [
        {"value": u.value, "name": u.name}
        for u in KPIUnit
    ]


@router.get(
    "/directions",
    response_model=list[dict[str, str]],
    summary="Get directions",
    description="Get available KPI directions.",
)
async def get_directions() -> list[dict[str, str]]:
    """Get available directions."""
    return [
        {"value": d.value, "name": d.name}
        for d in KPIDirection
    ]


@router.get(
    "/statuses",
    response_model=list[dict[str, str]],
    summary="Get statuses",
    description="Get available KPI statuses.",
)
async def get_statuses() -> list[dict[str, str]]:
    """Get available statuses."""
    return [
        {"value": s.value, "name": s.name}
        for s in KPIStatus
    ]


@router.get(
    "/aggregation-types",
    response_model=list[dict[str, str]],
    summary="Get aggregation types",
    description="Get available aggregation types.",
)
async def get_aggregation_types() -> list[dict[str, str]]:
    """Get available aggregation types."""
    return [
        {"value": a.value, "name": a.name}
        for a in AggregationType
    ]


@router.get(
    "/trend-directions",
    response_model=list[dict[str, str]],
    summary="Get trend directions",
    description="Get available trend directions.",
)
async def get_trend_directions() -> list[dict[str, str]]:
    """Get available trend directions."""
    return [
        {"value": t.value, "name": t.name}
        for t in TrendDirection
    ]
