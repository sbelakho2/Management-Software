"""
Work Center Management Endpoints

Provides work center and station management including:
- List work centers with filtering and pagination
- Create/read/update/delete work centers
- Station management within work centers
- Performance analytics
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from sensei.api.deps import (
    CurrentUser,
    DBSession,
    Pagination,
    RoleChecker,
)
from sensei.api.exceptions import (
    ConflictError,
    NotFoundError,
    ForbiddenError,
)
from sensei.api.schemas import (
    APIResponse,
    FilterOperator,
    PaginatedResponse,
    PaginationMeta,
    SortOrder,
    BulkDeleteRequest,
    success_response,
    error_response,
)
from sensei.api.utils import (
    parse_sort_param,
    parse_filter_param,
    build_response,
    build_paginated_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    now_utc,
)
from sensei.models.work_center import (
    WorkCenter,
    WorkCenterStatus,
    Station,
    StationType,
    StationStatus,
)


router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================


class WorkCenterBase(BaseModel):
    """Base work center fields."""
    
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    capacity_units: Optional[str] = Field("units/hour", max_length=50)
    capacity_value: Optional[float] = Field(None, ge=0)
    efficiency_target: float = Field(default=85.0, ge=0, le=100)
    status: str = Field(default=WorkCenterStatus.ACTIVE.value)
    account_id: Optional[UUID] = None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [s.value for s in WorkCenterStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class WorkCenterCreate(WorkCenterBase):
    """Work center creation request."""
    pass


class WorkCenterUpdate(BaseModel):
    """Work center update request (all fields optional)."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=255)
    capacity_units: Optional[str] = Field(None, max_length=50)
    capacity_value: Optional[float] = Field(None, ge=0)
    efficiency_target: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[str] = None
    account_id: Optional[UUID] = None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_statuses = [s.value for s in WorkCenterStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class WorkCenterResponse(BaseModel):
    """Work center response."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    code: str
    description: Optional[str]
    location: Optional[str]
    capacity_units: Optional[str]
    capacity_value: Optional[float]
    efficiency_target: float
    status: str
    account_id: Optional[UUID]
    
    # Computed
    active_stations_count: int
    is_operational: bool
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    updated_by_id: Optional[UUID]
    


class WorkCenterListResponse(BaseModel):
    """Simplified work center for list views."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    code: str
    status: str
    location: Optional[str]
    efficiency_target: float
    active_stations_count: int
    is_operational: bool
    created_at: datetime
    


class StationBase(BaseModel):
    """Base station fields."""
    
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    station_type: str = Field(default=StationType.ASSEMBLY.value)
    takt_time_seconds: int = Field(default=60, gt=0)
    cycle_time_seconds: int = Field(default=60, gt=0)
    setup_time_seconds: int = Field(default=0, ge=0)
    status: str = Field(default=StationStatus.ACTIVE.value)
    yellow_ack_minutes: int = Field(default=5, gt=0)
    red_ack_minutes: int = Field(default=2, gt=0)
    resolution_target_minutes: int = Field(default=30, gt=0)
    production_cell_id: Optional[int] = None
    
    @field_validator("station_type")
    @classmethod
    def validate_station_type(cls, v: str) -> str:
        valid_types = [t.value for t in StationType]
        if v not in valid_types:
            raise ValueError(f"Invalid station type. Must be one of: {valid_types}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [s.value for s in StationStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class StationCreate(StationBase):
    """Station creation request."""
    work_center_id: int = Field(..., gt=0)


class StationUpdate(BaseModel):
    """Station update request (all fields optional)."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    station_type: Optional[str] = None
    takt_time_seconds: Optional[int] = Field(None, gt=0)
    cycle_time_seconds: Optional[int] = Field(None, gt=0)
    setup_time_seconds: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None
    yellow_ack_minutes: Optional[int] = Field(None, gt=0)
    red_ack_minutes: Optional[int] = Field(None, gt=0)
    resolution_target_minutes: Optional[int] = Field(None, gt=0)
    production_cell_id: Optional[int] = None
    
    @field_validator("station_type")
    @classmethod
    def validate_station_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_types = [t.value for t in StationType]
        if v not in valid_types:
            raise ValueError(f"Invalid station type. Must be one of: {valid_types}")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_statuses = [s.value for s in StationStatus]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v


class StationResponse(BaseModel):
    """Station response."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    code: str
    description: Optional[str]
    station_type: str
    takt_time_seconds: int
    cycle_time_seconds: int
    setup_time_seconds: int
    status: str
    yellow_ack_minutes: int
    red_ack_minutes: int
    resolution_target_minutes: int
    work_center_id: int
    production_cell_id: Optional[int]
    
    # Computed
    efficiency_ratio: float
    is_bottleneck: bool
    is_available: bool
    
    # Audit
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID]
    updated_by_id: Optional[UUID]
    


class StationListResponse(BaseModel):
    """Simplified station for list views."""

    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    code: str
    station_type: str
    status: str
    takt_time_seconds: int
    cycle_time_seconds: int
    is_bottleneck: bool
    is_available: bool
    work_center_id: int
    created_at: datetime
    


class WorkCenterStatsResponse(BaseModel):
    """Work center statistics."""
    
    total_work_centers: int
    by_status: dict[str, int]
    total_stations: int
    stations_by_type: dict[str, int]
    stations_by_status: dict[str, int]
    active_work_centers: int
    bottleneck_stations: int


# =============================================================================
# Helper Functions
# =============================================================================


def work_center_to_response(work_center: WorkCenter) -> WorkCenterResponse:
    """Convert WorkCenter model to response schema."""
    return WorkCenterResponse(
        id=work_center.id,
        name=work_center.name,
        code=work_center.code,
        description=work_center.description,
        location=work_center.location,
        capacity_units=work_center.capacity_units,
        capacity_value=float(work_center.capacity_value) if work_center.capacity_value else None,
        efficiency_target=float(work_center.efficiency_target),
        status=work_center.status.value if isinstance(work_center.status, WorkCenterStatus) else work_center.status,
        account_id=work_center.account_id,
        active_stations_count=work_center.active_stations_count,
        is_operational=work_center.is_operational,
        created_at=work_center.created_at,
        updated_at=work_center.updated_at,
        created_by_id=work_center.created_by_id,
        updated_by_id=work_center.updated_by_id,
    )


def work_center_to_list_response(work_center: WorkCenter) -> WorkCenterListResponse:
    """Convert WorkCenter model to list response schema."""
    return WorkCenterListResponse(
        id=work_center.id,
        name=work_center.name,
        code=work_center.code,
        status=work_center.status.value if isinstance(work_center.status, WorkCenterStatus) else work_center.status,
        location=work_center.location,
        efficiency_target=float(work_center.efficiency_target),
        active_stations_count=work_center.active_stations_count,
        is_operational=work_center.is_operational,
        created_at=work_center.created_at,
    )


def station_to_response(station: Station) -> StationResponse:
    """Convert Station model to response schema."""
    return StationResponse(
        id=station.id,
        name=station.name,
        code=station.code,
        description=station.description,
        station_type=station.station_type.value if isinstance(station.station_type, StationType) else station.station_type,
        takt_time_seconds=station.takt_time_seconds,
        cycle_time_seconds=station.cycle_time_seconds,
        setup_time_seconds=station.setup_time_seconds,
        status=station.status.value if isinstance(station.status, StationStatus) else station.status,
        yellow_ack_minutes=station.yellow_ack_minutes,
        red_ack_minutes=station.red_ack_minutes,
        resolution_target_minutes=station.resolution_target_minutes,
        work_center_id=station.work_center_id,
        production_cell_id=station.production_cell_id,
        efficiency_ratio=float(station.efficiency_ratio),
        is_bottleneck=station.is_bottleneck,
        is_available=station.is_available,
        created_at=station.created_at,
        updated_at=station.updated_at,
        created_by_id=station.created_by_id,
        updated_by_id=station.updated_by_id,
    )


def station_to_list_response(station: Station) -> StationListResponse:
    """Convert Station model to list response schema."""
    return StationListResponse(
        id=station.id,
        name=station.name,
        code=station.code,
        station_type=station.station_type.value if isinstance(station.station_type, StationType) else station.station_type,
        status=station.status.value if isinstance(station.status, StationStatus) else station.status,
        takt_time_seconds=station.takt_time_seconds,
        cycle_time_seconds=station.cycle_time_seconds,
        is_bottleneck=station.is_bottleneck,
        is_available=station.is_available,
        work_center_id=station.work_center_id,
        created_at=station.created_at,
    )


# =============================================================================
# Work Center Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse[WorkCenterListResponse])
async def list_work_centers(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    account_id: Optional[UUID] = Query(default=None, description="Filter by account"),
    search: Optional[str] = Query(default=None, description="Search name, code, location"),
    sort: Optional[str] = Query(default=None, description="Sort field (prefix with - for desc)"),
    include_deleted: bool = Query(default=False, description="Include soft-deleted records"),
) -> PaginatedResponse[WorkCenterListResponse]:
    """
    List work centers with optional filtering and pagination.
    """
    query = select(WorkCenter).options(selectinload(WorkCenter.stations))
    
    # Apply soft-delete filter
    if not include_deleted:
        query = query.where(WorkCenter.deleted_at.is_(None))
    
    # Apply filters
    if status:
        query = query.where(WorkCenter.status == status)
    
    if account_id:
        query = query.where(WorkCenter.account_id == account_id)
    
    if search:
        search_filter = or_(
            WorkCenter.name.ilike(f"%{search}%"),
            WorkCenter.code.ilike(f"%{search}%"),
            WorkCenter.location.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    if sort:
        if sort.startswith("-"):
            query = query.order_by(getattr(WorkCenter, sort[1:]).desc())
        else:
            query = query.order_by(getattr(WorkCenter, sort).asc())
    else:
        query = query.order_by(WorkCenter.name.asc())
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    
    result = await db.execute(query)
    work_centers = result.scalars().all()
    
    items = [work_center_to_list_response(wc) for wc in work_centers]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=APIResponse[WorkCenterResponse], status_code=status.HTTP_201_CREATED)
async def create_work_center(
    data: WorkCenterCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkCenterResponse]:
    """
    Create a new work center.
    """
    # Check for duplicate code
    existing = await db.execute(
        select(WorkCenter).where(
            and_(
                WorkCenter.code == data.code,
                WorkCenter.deleted_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Work center with code '{data.code}' already exists")
    
    # Create work center
    work_center = WorkCenter(
        name=data.name,
        code=data.code,
        description=data.description,
        location=data.location,
        capacity_units=data.capacity_units,
        capacity_value=Decimal(str(data.capacity_value)) if data.capacity_value else None,
        efficiency_target=Decimal(str(data.efficiency_target)),
        status=WorkCenterStatus(data.status),
        account_id=data.account_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    
    db.add(work_center)
    await db.commit()
    await db.refresh(work_center, ["stations"])
    
    return build_created_response(
        data=work_center_to_response(work_center),
        resource_name="Work center",
    )


@router.get("/{work_center_id}", response_model=APIResponse[WorkCenterResponse])
async def get_work_center(
    work_center_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
) -> APIResponse[WorkCenterResponse]:
    """
    Get a work center by ID.
    """
    query = select(WorkCenter).where(WorkCenter.id == work_center_id).options(
        selectinload(WorkCenter.stations)
    )
    
    if not include_deleted:
        query = query.where(WorkCenter.deleted_at.is_(None))
    
    result = await db.execute(query)
    work_center = result.scalar_one_or_none()
    
    if not work_center:
        raise NotFoundError(f"Work center with ID {work_center_id} not found")
    
    return build_response(
        data=work_center_to_response(work_center),
    )


@router.patch("/{work_center_id}", response_model=APIResponse[WorkCenterResponse])
async def update_work_center(
    work_center_id: int,
    data: WorkCenterUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkCenterResponse]:
    """
    Update a work center.
    """
    query = select(WorkCenter).where(
        and_(
            WorkCenter.id == work_center_id,
            WorkCenter.deleted_at.is_(None),
        )
    ).options(selectinload(WorkCenter.stations))
    
    result = await db.execute(query)
    work_center = result.scalar_one_or_none()
    
    if not work_center:
        raise NotFoundError(f"Work center with ID {work_center_id} not found")
    
    # Check for duplicate code if updating
    if data.code and data.code != work_center.code:
        existing = await db.execute(
            select(WorkCenter).where(
                and_(
                    WorkCenter.code == data.code,
                    WorkCenter.id != work_center_id,
                    WorkCenter.deleted_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Work center with code '{data.code}' already exists")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            value = WorkCenterStatus(value)
        elif field == "efficiency_target" and value is not None:
            value = Decimal(str(value))
        elif field == "capacity_value" and value is not None:
            value = Decimal(str(value))
        setattr(work_center, field, value)
    
    work_center.updated_by_id = current_user.id
    work_center.updated_at = now_utc()
    
    await db.commit()
    await db.refresh(work_center, ["stations"])
    
    return build_updated_response(
        data=work_center_to_response(work_center),
        resource_name="Work center",
    )


@router.delete("/{work_center_id}", response_model=APIResponse[None])
async def delete_work_center(
    work_center_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False, description="Permanently delete"),
) -> APIResponse[None]:
    """
    Delete a work center (soft delete by default).
    """
    query = select(WorkCenter).where(WorkCenter.id == work_center_id)
    
    if not hard_delete:
        query = query.where(WorkCenter.deleted_at.is_(None))
    
    result = await db.execute(query)
    work_center = result.scalar_one_or_none()
    
    if not work_center:
        raise NotFoundError(f"Work center with ID {work_center_id} not found")
    
    if hard_delete:
        await db.delete(work_center)
    else:
        work_center.deleted_at = now_utc()
        work_center.updated_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Work center")


@router.post("/{work_center_id}/restore", response_model=APIResponse[WorkCenterResponse])
async def restore_work_center(
    work_center_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[WorkCenterResponse]:
    """
    Restore a soft-deleted work center.
    """
    query = select(WorkCenter).where(
        and_(
            WorkCenter.id == work_center_id,
            WorkCenter.deleted_at.isnot(None),
        )
    ).options(selectinload(WorkCenter.stations))
    
    result = await db.execute(query)
    work_center = result.scalar_one_or_none()
    
    if not work_center:
        raise NotFoundError(f"Deleted work center with ID {work_center_id} not found")
    
    work_center.deleted_at = None
    work_center.updated_by_id = current_user.id
    work_center.updated_at = now_utc()
    
    await db.commit()
    await db.refresh(work_center, ["stations"])
    
    return build_response(
        data=work_center_to_response(work_center),
        message="Work center restored successfully",
    )


@router.get("/stats/summary", response_model=APIResponse[WorkCenterStatsResponse])
async def get_work_center_stats(
    db: DBSession,
    current_user: CurrentUser,
    account_id: Optional[UUID] = Query(default=None),
) -> APIResponse[WorkCenterStatsResponse]:
    """
    Get work center statistics.
    """
    # Base filter
    base_filter = WorkCenter.deleted_at.is_(None)
    if account_id:
        base_filter = and_(base_filter, WorkCenter.account_id == account_id)
    
    # Total work centers
    total_result = await db.execute(
        select(func.count(WorkCenter.id)).where(base_filter)
    )
    total_work_centers = total_result.scalar() or 0
    
    # By status
    status_result = await db.execute(
        select(WorkCenter.status, func.count(WorkCenter.id))
        .where(base_filter)
        .group_by(WorkCenter.status)
    )
    by_status = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in status_result.all()}
    
    # Station statistics
    station_filter = Station.deleted_at.is_(None)
    
    # Total stations
    station_count_result = await db.execute(
        select(func.count(Station.id)).where(station_filter)
    )
    total_stations = station_count_result.scalar() or 0
    
    # Stations by type
    type_result = await db.execute(
        select(Station.station_type, func.count(Station.id))
        .where(station_filter)
        .group_by(Station.station_type)
    )
    stations_by_type = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in type_result.all()}
    
    # Stations by status
    station_status_result = await db.execute(
        select(Station.status, func.count(Station.id))
        .where(station_filter)
        .group_by(Station.status)
    )
    stations_by_status = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in station_status_result.all()}
    
    # Active work centers
    active_result = await db.execute(
        select(func.count(WorkCenter.id)).where(
            and_(base_filter, WorkCenter.status == WorkCenterStatus.ACTIVE)
        )
    )
    active_work_centers = active_result.scalar() or 0
    
    # Bottleneck stations (cycle_time > takt_time)
    bottleneck_result = await db.execute(
        select(func.count(Station.id)).where(
            and_(
                station_filter,
                Station.cycle_time_seconds > Station.takt_time_seconds,
            )
        )
    )
    bottleneck_stations = bottleneck_result.scalar() or 0
    
    stats = WorkCenterStatsResponse(
        total_work_centers=total_work_centers,
        by_status=by_status,
        total_stations=total_stations,
        stations_by_type=stations_by_type,
        stations_by_status=stations_by_status,
        active_work_centers=active_work_centers,
        bottleneck_stations=bottleneck_stations,
    )
    
    return build_response(
        data=stats,
    )


# =============================================================================
# Station Endpoints
# =============================================================================


@router.get("/{work_center_id}/stations", response_model=PaginatedResponse[StationListResponse])
async def list_stations(
    work_center_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    station_type: Optional[str] = Query(default=None, description="Filter by station type"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    search: Optional[str] = Query(default=None, description="Search name or code"),
    include_deleted: bool = Query(default=False),
) -> PaginatedResponse[StationListResponse]:
    """
    List stations within a work center.
    """
    # Verify work center exists
    wc_query = select(WorkCenter).where(
        and_(
            WorkCenter.id == work_center_id,
            WorkCenter.deleted_at.is_(None),
        )
    )
    wc_result = await db.execute(wc_query)
    if not wc_result.scalar_one_or_none():
        raise NotFoundError(f"Work center with ID {work_center_id} not found")
    
    query = select(Station).where(Station.work_center_id == work_center_id)
    
    if not include_deleted:
        query = query.where(Station.deleted_at.is_(None))
    
    if station_type:
        query = query.where(Station.station_type == station_type)
    
    if status:
        query = query.where(Station.status == status)
    
    if search:
        search_filter = or_(
            Station.name.ilike(f"%{search}%"),
            Station.code.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.order_by(Station.code.asc()).offset(skip).limit(page_size)
    
    result = await db.execute(query)
    stations = result.scalars().all()
    
    items = [station_to_list_response(s) for s in stations]
    
    return build_paginated_response(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/{work_center_id}/stations", response_model=APIResponse[StationResponse], status_code=status.HTTP_201_CREATED)
async def create_station(
    work_center_id: int,
    data: StationBase,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StationResponse]:
    """
    Create a new station within a work center.
    """
    # Verify work center exists
    wc_query = select(WorkCenter).where(
        and_(
            WorkCenter.id == work_center_id,
            WorkCenter.deleted_at.is_(None),
        )
    )
    wc_result = await db.execute(wc_query)
    if not wc_result.scalar_one_or_none():
        raise NotFoundError(f"Work center with ID {work_center_id} not found")
    
    # Check for duplicate code within work center
    existing = await db.execute(
        select(Station).where(
            and_(
                Station.work_center_id == work_center_id,
                Station.code == data.code,
                Station.deleted_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Station with code '{data.code}' already exists in this work center")
    
    # Create station
    station = Station(
        name=data.name,
        code=data.code,
        description=data.description,
        station_type=StationType(data.station_type),
        takt_time_seconds=data.takt_time_seconds,
        cycle_time_seconds=data.cycle_time_seconds,
        setup_time_seconds=data.setup_time_seconds,
        status=StationStatus(data.status),
        yellow_ack_minutes=data.yellow_ack_minutes,
        red_ack_minutes=data.red_ack_minutes,
        resolution_target_minutes=data.resolution_target_minutes,
        work_center_id=work_center_id,
        production_cell_id=data.production_cell_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    
    db.add(station)
    await db.commit()
    await db.refresh(station)
    
    return build_created_response(
        data=station_to_response(station),
        resource_name="Station",
    )


@router.get("/{work_center_id}/stations/{station_id}", response_model=APIResponse[StationResponse])
async def get_station(
    work_center_id: int,
    station_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
) -> APIResponse[StationResponse]:
    """
    Get a station by ID.
    """
    query = select(Station).where(
        and_(
            Station.id == station_id,
            Station.work_center_id == work_center_id,
        )
    )
    
    if not include_deleted:
        query = query.where(Station.deleted_at.is_(None))
    
    result = await db.execute(query)
    station = result.scalar_one_or_none()
    
    if not station:
        raise NotFoundError(f"Station with ID {station_id} not found in work center {work_center_id}")
    
    return build_response(
        data=station_to_response(station),
    )


@router.patch("/{work_center_id}/stations/{station_id}", response_model=APIResponse[StationResponse])
async def update_station(
    work_center_id: int,
    station_id: int,
    data: StationUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StationResponse]:
    """
    Update a station.
    """
    query = select(Station).where(
        and_(
            Station.id == station_id,
            Station.work_center_id == work_center_id,
            Station.deleted_at.is_(None),
        )
    )
    
    result = await db.execute(query)
    station = result.scalar_one_or_none()
    
    if not station:
        raise NotFoundError(f"Station with ID {station_id} not found in work center {work_center_id}")
    
    # Check for duplicate code if updating
    if data.code and data.code != station.code:
        existing = await db.execute(
            select(Station).where(
                and_(
                    Station.work_center_id == work_center_id,
                    Station.code == data.code,
                    Station.id != station_id,
                    Station.deleted_at.is_(None),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Station with code '{data.code}' already exists in this work center")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value is not None:
            value = StationStatus(value)
        elif field == "station_type" and value is not None:
            value = StationType(value)
        setattr(station, field, value)
    
    station.updated_by_id = current_user.id
    station.updated_at = now_utc()
    
    await db.commit()
    await db.refresh(station)
    
    return build_updated_response(
        data=station_to_response(station),
        resource_name="Station",
    )


@router.delete("/{work_center_id}/stations/{station_id}", response_model=APIResponse[None])
async def delete_station(
    work_center_id: int,
    station_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
) -> APIResponse[None]:
    """
    Delete a station (soft delete by default).
    """
    query = select(Station).where(
        and_(
            Station.id == station_id,
            Station.work_center_id == work_center_id,
        )
    )
    
    if not hard_delete:
        query = query.where(Station.deleted_at.is_(None))
    
    result = await db.execute(query)
    station = result.scalar_one_or_none()
    
    if not station:
        raise NotFoundError(f"Station with ID {station_id} not found in work center {work_center_id}")
    
    if hard_delete:
        await db.delete(station)
    else:
        station.deleted_at = now_utc()
        station.updated_by_id = current_user.id
    
    await db.commit()
    
    return build_deleted_response(resource_name="Station")


@router.post("/{work_center_id}/stations/{station_id}/restore", response_model=APIResponse[StationResponse])
async def restore_station(
    work_center_id: int,
    station_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StationResponse]:
    """
    Restore a soft-deleted station.
    """
    query = select(Station).where(
        and_(
            Station.id == station_id,
            Station.work_center_id == work_center_id,
            Station.deleted_at.isnot(None),
        )
    )
    
    result = await db.execute(query)
    station = result.scalar_one_or_none()
    
    if not station:
        raise NotFoundError(f"Deleted station with ID {station_id} not found in work center {work_center_id}")
    
    station.deleted_at = None
    station.updated_by_id = current_user.id
    station.updated_at = now_utc()
    
    await db.commit()
    await db.refresh(station)
    
    return build_response(
        data=station_to_response(station),
        message="Station restored successfully",
    )


@router.post("/stations", response_model=APIResponse[StationResponse], status_code=status.HTTP_201_CREATED)
async def create_station_direct(
    data: StationCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[StationResponse]:
    """
    Create a new station (direct endpoint with work_center_id in body).
    """
    # Verify work center exists
    wc_query = select(WorkCenter).where(
        and_(
            WorkCenter.id == data.work_center_id,
            WorkCenter.deleted_at.is_(None),
        )
    )
    wc_result = await db.execute(wc_query)
    if not wc_result.scalar_one_or_none():
        raise NotFoundError(f"Work center with ID {data.work_center_id} not found")
    
    # Check for duplicate code within work center
    existing = await db.execute(
        select(Station).where(
            and_(
                Station.work_center_id == data.work_center_id,
                Station.code == data.code,
                Station.deleted_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Station with code '{data.code}' already exists in this work center")
    
    # Create station
    station = Station(
        name=data.name,
        code=data.code,
        description=data.description,
        station_type=StationType(data.station_type),
        takt_time_seconds=data.takt_time_seconds,
        cycle_time_seconds=data.cycle_time_seconds,
        setup_time_seconds=data.setup_time_seconds,
        status=StationStatus(data.status),
        yellow_ack_minutes=data.yellow_ack_minutes,
        red_ack_minutes=data.red_ack_minutes,
        resolution_target_minutes=data.resolution_target_minutes,
        work_center_id=data.work_center_id,
        production_cell_id=data.production_cell_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    
    db.add(station)
    await db.commit()
    await db.refresh(station)
    
    return build_created_response(
        data=station_to_response(station),
        resource_name="Station",
    )
