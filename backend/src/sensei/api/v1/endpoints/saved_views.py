"""
Saved Views/Filters API endpoints.

Provides REST API for creating, managing, and applying saved views.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.services.saved_views import (
    SavedViewsService,
    SavedView,
    SavedViewEntityType,
    FilterCondition,
    FilterOperator,
    FilterLogic,
    DatePreset,
    SortField,
    SortDirection,
    ColumnConfig,
    ViewVisibility,
)

router = APIRouter(prefix="/saved-views", tags=["Saved Views"])

# --------------------------------------------------------------------------
# Service Instance (in production, would be dependency injected)
# --------------------------------------------------------------------------

_service = SavedViewsService()


def get_service() -> SavedViewsService:
    """Get the saved views service."""
    return _service


# --------------------------------------------------------------------------
# Request/Response Schemas
# --------------------------------------------------------------------------

class FilterConditionRequest(BaseModel):
    """Request schema for a filter condition."""
    
    field: str
    operator: str
    value: Any | None = None
    second_value: Any | None = None
    date_preset: str | None = None
    case_sensitive: bool = False


class SortFieldRequest(BaseModel):
    """Request schema for a sort field."""
    
    field: str
    direction: str = "asc"


class ColumnConfigRequest(BaseModel):
    """Request schema for column configuration."""
    
    field: str
    label: str | None = None
    width: int | None = None
    visible: bool = True
    order: int = 0


class CreateViewRequest(BaseModel):
    """Request to create a saved view."""
    
    name: str
    entity_type: str
    owner_id: str
    description: str = ""
    conditions: list[FilterConditionRequest] = []
    condition_logic: str = "and"
    sort_fields: list[SortFieldRequest] = []
    columns: list[ColumnConfigRequest] = []
    visibility: str = "private"
    page_size: int = 25
    icon: str | None = None
    color: str | None = None
    team_ids: list[str] = []


class UpdateViewRequest(BaseModel):
    """Request to update a saved view."""
    
    name: str | None = None
    description: str | None = None
    conditions: list[FilterConditionRequest] | None = None
    condition_logic: str | None = None
    sort_fields: list[SortFieldRequest] | None = None
    columns: list[ColumnConfigRequest] | None = None
    visibility: str | None = None
    page_size: int | None = None
    icon: str | None = None
    color: str | None = None
    team_ids: list[str] | None = None
    is_default: bool | None = None
    pinned: bool | None = None


class DuplicateViewRequest(BaseModel):
    """Request to duplicate a view."""
    
    new_owner_id: str
    new_name: str | None = None


class SetDefaultRequest(BaseModel):
    """Request to set default view."""
    
    user_id: str
    entity_type: str
    view_id: str


class ApplyViewRequest(BaseModel):
    """Request to apply a view to entities."""
    
    entities: list[dict[str, Any]]
    page: int = 1
    page_size: int | None = None


class FilterConditionResponse(BaseModel):
    """Response schema for a filter condition."""
    
    field: str
    operator: str
    value: Any | None = None
    second_value: Any | None = None
    date_preset: str | None = None
    case_sensitive: bool = False


class SortFieldResponse(BaseModel):
    """Response schema for a sort field."""
    
    field: str
    direction: str


class ColumnConfigResponse(BaseModel):
    """Response schema for column configuration."""
    
    field: str
    label: str | None = None
    width: int | None = None
    visible: bool = True
    order: int = 0


class SavedViewResponse(BaseModel):
    """Response schema for a saved view."""
    
    id: str
    name: str
    entity_type: str
    owner_id: str
    visibility: str
    description: str
    conditions: list[FilterConditionResponse]
    condition_logic: str
    sort_fields: list[SortFieldResponse]
    columns: list[ColumnConfigResponse]
    page_size: int
    is_default: bool
    icon: str | None = None
    color: str | None = None
    created_at: str
    updated_at: str
    use_count: int
    last_used_at: str | None = None
    team_ids: list[str]
    pinned: bool


class ViewFilterResultResponse(BaseModel):
    """Response schema for view filter results."""
    
    view_id: str
    view_name: str
    total_count: int
    matched_count: int
    entities: list[dict[str, Any]]
    page: int
    page_size: int
    has_more: bool


class ViewListResponse(BaseModel):
    """Response schema for list of views."""
    
    views: list[SavedViewResponse]
    total_count: int


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _parse_uuid(value: str | None) -> UUID | None:
    """Parse a UUID string."""
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID: {value}",
        )


def _parse_entity_type(value: str) -> SavedViewEntityType:
    """Parse an entity type string."""
    try:
        return SavedViewEntityType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type: {value}",
        )


def _parse_operator(value: str) -> FilterOperator:
    """Parse a filter operator string."""
    try:
        return FilterOperator(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid operator: {value}",
        )


def _parse_filter_logic(value: str) -> FilterLogic:
    """Parse a filter logic string."""
    try:
        return FilterLogic(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filter logic: {value}",
        )


def _parse_date_preset(value: str | None) -> DatePreset | None:
    """Parse a date preset string."""
    if not value:
        return None
    try:
        return DatePreset(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date preset: {value}",
        )


def _parse_sort_direction(value: str) -> SortDirection:
    """Parse a sort direction string."""
    try:
        return SortDirection(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort direction: {value}",
        )


def _parse_visibility(value: str) -> ViewVisibility:
    """Parse a visibility string."""
    try:
        return ViewVisibility(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid visibility: {value}",
        )


def _condition_from_request(req: FilterConditionRequest) -> FilterCondition:
    """Convert request to filter condition."""
    return FilterCondition(
        field=req.field,
        operator=_parse_operator(req.operator),
        value=req.value,
        second_value=req.second_value,
        date_preset=_parse_date_preset(req.date_preset),
        case_sensitive=req.case_sensitive,
    )


def _sort_field_from_request(req: SortFieldRequest) -> SortField:
    """Convert request to sort field."""
    return SortField(
        field=req.field,
        direction=_parse_sort_direction(req.direction),
    )


def _column_from_request(req: ColumnConfigRequest) -> ColumnConfig:
    """Convert request to column config."""
    return ColumnConfig(
        field=req.field,
        label=req.label,
        width=req.width,
        visible=req.visible,
        order=req.order,
    )


def _view_to_response(view: SavedView) -> SavedViewResponse:
    """Convert saved view to response."""
    return SavedViewResponse(
        id=view.id,
        name=view.name,
        entity_type=view.entity_type.value,
        owner_id=str(view.owner_id),
        visibility=view.visibility.value,
        description=view.description,
        conditions=[
            FilterConditionResponse(
                field=c.field,
                operator=c.operator.value,
                value=c.value,
                second_value=c.second_value,
                date_preset=c.date_preset.value if c.date_preset else None,
                case_sensitive=c.case_sensitive,
            )
            for c in view.conditions
        ],
        condition_logic=view.condition_logic.value,
        sort_fields=[
            SortFieldResponse(field=s.field, direction=s.direction.value)
            for s in view.sort_fields
        ],
        columns=[
            ColumnConfigResponse(
                field=col.field,
                label=col.label,
                width=col.width,
                visible=col.visible,
                order=col.order,
            )
            for col in view.columns
        ],
        page_size=view.page_size,
        is_default=view.is_default,
        icon=view.icon,
        color=view.color,
        created_at=view.created_at.isoformat(),
        updated_at=view.updated_at.isoformat(),
        use_count=view.use_count,
        last_used_at=view.last_used_at.isoformat() if view.last_used_at else None,
        team_ids=[str(tid) for tid in view.team_ids],
        pinned=view.pinned,
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.post("", response_model=SavedViewResponse, status_code=status.HTTP_201_CREATED)
async def create_view(request: CreateViewRequest) -> SavedViewResponse:
    """
    Create a new saved view.
    """
    service = get_service()
    
    owner_id = _parse_uuid(request.owner_id)
    if not owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="owner_id is required",
        )
    
    entity_type = _parse_entity_type(request.entity_type)
    visibility = _parse_visibility(request.visibility)
    condition_logic = _parse_filter_logic(request.condition_logic)
    
    conditions = [_condition_from_request(c) for c in request.conditions]
    sort_fields = [_sort_field_from_request(s) for s in request.sort_fields]
    columns = [_column_from_request(col) for col in request.columns]
    team_ids = [_parse_uuid(tid) for tid in request.team_ids if tid]
    team_ids = [tid for tid in team_ids if tid is not None]
    
    view = service.create_view(
        name=request.name,
        entity_type=entity_type,
        owner_id=owner_id,
        description=request.description,
        conditions=conditions,
        condition_logic=condition_logic,
        sort_fields=sort_fields,
        columns=columns,
        visibility=visibility,
        page_size=request.page_size,
        icon=request.icon,
        color=request.color,
        team_ids=team_ids,
    )
    
    return _view_to_response(view)


@router.get("", response_model=ViewListResponse)
async def list_views(
    user_id: str = Query(..., description="User ID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    include_system: bool = Query(True, description="Include system views"),
    include_team: bool = Query(True, description="Include team views"),
    include_organization: bool = Query(True, description="Include organization views"),
) -> ViewListResponse:
    """
    List saved views accessible to a user.
    """
    service = get_service()
    
    uid = _parse_uuid(user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )
    
    et = _parse_entity_type(entity_type) if entity_type else None
    
    views = service.list_views(
        user_id=uid,
        entity_type=et,
        include_system=include_system,
        include_team=include_team,
        include_organization=include_organization,
    )
    
    return ViewListResponse(
        views=[_view_to_response(v) for v in views],
        total_count=len(views),
    )


@router.get("/system", response_model=ViewListResponse)
async def list_system_views(
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> ViewListResponse:
    """
    List system (built-in) views.
    """
    service = get_service()
    
    et = _parse_entity_type(entity_type) if entity_type else None
    views = service.get_system_views(et)
    
    return ViewListResponse(
        views=[_view_to_response(v) for v in views],
        total_count=len(views),
    )


@router.get("/pinned", response_model=ViewListResponse)
async def list_pinned_views(
    user_id: str = Query(..., description="User ID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
) -> ViewListResponse:
    """
    List pinned views for a user.
    """
    service = get_service()
    
    uid = _parse_uuid(user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )
    
    et = _parse_entity_type(entity_type) if entity_type else None
    views = service.get_pinned_views(uid, et)
    
    return ViewListResponse(
        views=[_view_to_response(v) for v in views],
        total_count=len(views),
    )


@router.get("/default")
async def get_default_view(
    user_id: str = Query(..., description="User ID"),
    entity_type: str = Query(..., description="Entity type"),
) -> SavedViewResponse | None:
    """
    Get the default view for a user and entity type.
    """
    service = get_service()
    
    uid = _parse_uuid(user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )
    
    et = _parse_entity_type(entity_type)
    view = service.get_default_view(uid, et)
    
    if not view:
        return None
    
    return _view_to_response(view)


@router.post("/default")
async def set_default_view(request: SetDefaultRequest) -> dict[str, Any]:
    """
    Set the default view for a user and entity type.
    """
    service = get_service()
    
    uid = _parse_uuid(request.user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id is required",
        )
    
    et = _parse_entity_type(request.entity_type)
    
    result = service.set_default_view(uid, et, request.view_id)
    
    return {
        "success": result,
        "view_id": request.view_id,
        "user_id": request.user_id,
        "entity_type": request.entity_type,
    }


@router.get("/entity-types")
async def list_entity_types() -> list[dict[str, str]]:
    """
    List all entity types that support saved views.
    """
    return [
        {"value": et.value, "name": et.name}
        for et in SavedViewEntityType
    ]


@router.get("/operators")
async def list_operators() -> list[dict[str, str]]:
    """
    List all available filter operators.
    """
    return [
        {"value": op.value, "name": op.name}
        for op in FilterOperator
    ]


@router.get("/date-presets")
async def list_date_presets() -> list[dict[str, str]]:
    """
    List all available date presets.
    """
    return [
        {"value": dp.value, "name": dp.name}
        for dp in DatePreset
    ]


@router.get("/{view_id}", response_model=SavedViewResponse)
async def get_view(view_id: str) -> SavedViewResponse:
    """
    Get a saved view by ID.
    """
    service = get_service()
    
    view = service.get_view(view_id)
    
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View not found: {view_id}",
        )
    
    return _view_to_response(view)


@router.put("/{view_id}", response_model=SavedViewResponse)
async def update_view(view_id: str, request: UpdateViewRequest) -> SavedViewResponse:
    """
    Update a saved view.
    """
    service = get_service()
    
    conditions = None
    if request.conditions is not None:
        conditions = [_condition_from_request(c) for c in request.conditions]
    
    sort_fields = None
    if request.sort_fields is not None:
        sort_fields = [_sort_field_from_request(s) for s in request.sort_fields]
    
    columns = None
    if request.columns is not None:
        columns = [_column_from_request(col) for col in request.columns]
    
    team_ids = None
    if request.team_ids is not None:
        team_ids = [_parse_uuid(tid) for tid in request.team_ids if tid]
        team_ids = [tid for tid in team_ids if tid is not None]
    
    visibility = None
    if request.visibility:
        visibility = _parse_visibility(request.visibility)
    
    condition_logic = None
    if request.condition_logic:
        condition_logic = _parse_filter_logic(request.condition_logic)
    
    view = service.update_view(
        view_id=view_id,
        name=request.name,
        description=request.description,
        conditions=conditions,
        condition_logic=condition_logic,
        sort_fields=sort_fields,
        columns=columns,
        visibility=visibility,
        page_size=request.page_size,
        icon=request.icon,
        color=request.color,
        team_ids=team_ids,
        is_default=request.is_default,
        pinned=request.pinned,
    )
    
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View not found: {view_id}",
        )
    
    return _view_to_response(view)


@router.delete("/{view_id}")
async def delete_view(view_id: str) -> dict[str, Any]:
    """
    Delete a saved view.
    """
    service = get_service()
    
    result = service.delete_view(view_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View not found: {view_id}",
        )
    
    return {"deleted": True, "view_id": view_id}


@router.post("/{view_id}/duplicate", response_model=SavedViewResponse)
async def duplicate_view(view_id: str, request: DuplicateViewRequest) -> SavedViewResponse:
    """
    Duplicate a view for another user.
    """
    service = get_service()
    
    new_owner_id = _parse_uuid(request.new_owner_id)
    if not new_owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_owner_id is required",
        )
    
    view = service.duplicate_view(view_id, new_owner_id, request.new_name)
    
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View not found: {view_id}",
        )
    
    return _view_to_response(view)


@router.post("/{view_id}/toggle-pin")
async def toggle_pin(view_id: str) -> dict[str, Any]:
    """
    Toggle the pinned status of a view.
    """
    service = get_service()
    
    result = service.toggle_pin(view_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View not found: {view_id}",
        )
    
    view = service.get_view(view_id)
    
    return {
        "view_id": view_id,
        "pinned": view.pinned if view else False,
    }


@router.post("/{view_id}/apply", response_model=ViewFilterResultResponse)
async def apply_view(view_id: str, request: ApplyViewRequest) -> ViewFilterResultResponse:
    """
    Apply a view's filters to a list of entities.
    """
    service = get_service()
    
    result = service.apply_view(
        view_id=view_id,
        entities=request.entities,
        page=request.page,
        page_size=request.page_size,
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View not found: {view_id}",
        )
    
    return ViewFilterResultResponse(
        view_id=result.view.id,
        view_name=result.view.name,
        total_count=result.total_count,
        matched_count=result.matched_count,
        entities=result.entities,
        page=result.page,
        page_size=result.page_size,
        has_more=result.has_more,
    )
