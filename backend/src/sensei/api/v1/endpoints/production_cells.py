"""
Production Cells API endpoints.

CRUD operations for production cells and cell performance tracking.
Supports OEE metrics, shift-level performance, and capacity management.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator, ConfigDict
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import get_db, get_current_user
from sensei.api.exceptions import NotFoundError, ConflictError, BadRequestError
from sensei.models.production import (
    ProductionCell,
    CellPerformance,
    CellType,
    CellStatus,
    ShiftNumber,
)
from sensei.models.user import User

AllowProductionModule = deps.require_role(
    "ops",
    "supervisor",
    "team_lead",
    "operator",
    "quality",
    "sales_engineer",
    "engineering",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(
                [
                    "ops",
                    "supervisor",
                    "team_lead",
                    "operator",
                    "quality",
                    "sales_engineer",
                    "engineering",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# =============================================================================
# Schemas
# =============================================================================


class ProductionCellCreate(BaseModel):
    """Schema for creating a production cell."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    work_center_id: int = Field(..., gt=0)
    cell_type: CellType = CellType.U_CELL
    status: CellStatus = CellStatus.ACTIVE
    takt_time_seconds: int = Field(default=60, gt=0)
    target_cycle_time_seconds: int = Field(default=60, gt=0)
    target_output_per_shift: int = Field(default=0, ge=0)
    shift_duration_hours: Decimal = Field(default=Decimal("8.0"), gt=0)
    planned_efficiency: Decimal = Field(default=Decimal("85.00"), gt=0, le=100)
    min_operators: int = Field(default=1, gt=0)
    standard_operators: int = Field(default=1, gt=0)
    max_operators: int = Field(default=1, gt=0)

    @field_validator("cell_type", mode="before")
    @classmethod
    def validate_cell_type(cls, v):
        if isinstance(v, str):
            try:
                return CellType(v)
            except ValueError:
                valid = [e.value for e in CellType]
                raise ValueError(f"Invalid cell_type. Must be one of: {valid}")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if isinstance(v, str):
            try:
                return CellStatus(v)
            except ValueError:
                valid = [e.value for e in CellStatus]
                raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class ProductionCellUpdate(BaseModel):
    """Schema for updating a production cell."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cell_type: Optional[CellType] = None
    status: Optional[CellStatus] = None
    takt_time_seconds: Optional[int] = Field(None, gt=0)
    target_cycle_time_seconds: Optional[int] = Field(None, gt=0)
    target_output_per_shift: Optional[int] = Field(None, ge=0)
    shift_duration_hours: Optional[Decimal] = Field(None, gt=0)
    planned_efficiency: Optional[Decimal] = Field(None, gt=0, le=100)
    min_operators: Optional[int] = Field(None, gt=0)
    standard_operators: Optional[int] = Field(None, gt=0)
    max_operators: Optional[int] = Field(None, gt=0)
    current_operators: Optional[int] = Field(None, ge=0)
    current_output: Optional[int] = Field(None, ge=0)
    current_efficiency_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    current_oee_percentage: Optional[Decimal] = Field(None, ge=0, le=100)

    @field_validator("cell_type", mode="before")
    @classmethod
    def validate_cell_type(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return CellType(v)
            except ValueError:
                valid = [e.value for e in CellType]
                raise ValueError(f"Invalid cell_type. Must be one of: {valid}")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return CellStatus(v)
            except ValueError:
                valid = [e.value for e in CellStatus]
                raise ValueError(f"Invalid status. Must be one of: {valid}")
        return v


class ProductionCellResponse(BaseModel):
    """Response schema for a production cell."""

    id: int
    name: str
    code: str
    description: Optional[str]
    work_center_id: int
    cell_type: str
    status: str
    takt_time_seconds: int
    target_cycle_time_seconds: int
    target_output_per_shift: int
    shift_duration_hours: Decimal
    planned_efficiency: Decimal
    current_output: int
    current_efficiency_percentage: Optional[Decimal]
    current_oee_percentage: Optional[Decimal]
    min_operators: int
    standard_operators: int
    max_operators: int
    current_operators: int
    station_count: int
    is_operational: bool
    is_understaffed: bool
    output_vs_target_percentage: Decimal
    theoretical_capacity_per_shift: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionCellListResponse(BaseModel):
    """Response schema for list of production cells."""

    success: bool = True
    cells: list[ProductionCellResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class CellPerformanceCreate(BaseModel):
    """Schema for creating a cell performance record."""

    shift_date: date
    shift_number: ShiftNumber
    planned_output: int = Field(..., ge=0)
    actual_output: int = Field(..., ge=0)
    good_output: int = Field(..., ge=0)
    rework_output: int = Field(default=0, ge=0)
    scrap_output: int = Field(default=0, ge=0)
    planned_time_minutes: int = Field(..., gt=0)
    operating_time_minutes: int = Field(..., ge=0)
    downtime_minutes: int = Field(default=0, ge=0)
    changeover_minutes: int = Field(default=0, ge=0)
    unplanned_downtime_minutes: int = Field(default=0, ge=0)
    planned_downtime_minutes: int = Field(default=0, ge=0)
    operator_count: int = Field(default=0, ge=0)
    labor_hours: Decimal = Field(default=Decimal("0"), ge=0)
    andon_events_count: int = Field(default=0, ge=0)
    quality_issues_count: int = Field(default=0, ge=0)
    notes: Optional[str] = None
    issues_summary: Optional[str] = None

    @field_validator("shift_number", mode="before")
    @classmethod
    def validate_shift_number(cls, v):
        if isinstance(v, str):
            try:
                return ShiftNumber(v)
            except ValueError:
                valid = [e.value for e in ShiftNumber]
                raise ValueError(f"Invalid shift_number. Must be one of: {valid}")
        return v


class CellPerformanceUpdate(BaseModel):
    """Schema for updating a cell performance record."""

    planned_output: Optional[int] = Field(None, ge=0)
    actual_output: Optional[int] = Field(None, ge=0)
    good_output: Optional[int] = Field(None, ge=0)
    rework_output: Optional[int] = Field(None, ge=0)
    scrap_output: Optional[int] = Field(None, ge=0)
    planned_time_minutes: Optional[int] = Field(None, gt=0)
    operating_time_minutes: Optional[int] = Field(None, ge=0)
    downtime_minutes: Optional[int] = Field(None, ge=0)
    changeover_minutes: Optional[int] = Field(None, ge=0)
    unplanned_downtime_minutes: Optional[int] = Field(None, ge=0)
    planned_downtime_minutes: Optional[int] = Field(None, ge=0)
    operator_count: Optional[int] = Field(None, ge=0)
    labor_hours: Optional[Decimal] = Field(None, ge=0)
    andon_events_count: Optional[int] = Field(None, ge=0)
    quality_issues_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    issues_summary: Optional[str] = None


class CellPerformanceResponse(BaseModel):
    """Response schema for a cell performance record."""

    id: int
    cell_id: int
    shift_date: date
    shift_number: str
    planned_output: int
    actual_output: int
    good_output: int
    rework_output: int
    scrap_output: int
    planned_time_minutes: int
    operating_time_minutes: int
    downtime_minutes: int
    changeover_minutes: int
    unplanned_downtime_minutes: int
    planned_downtime_minutes: int
    availability_percentage: Decimal
    performance_percentage: Decimal
    quality_percentage: Decimal
    oee_percentage: Decimal
    efficiency_percentage: Decimal
    operator_count: int
    labor_hours: Decimal
    units_per_labor_hour: Optional[Decimal]
    andon_events_count: int
    quality_issues_count: int
    output_target_ratio: Decimal
    scrap_rate: Decimal
    notes: Optional[str]
    issues_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CellPerformanceListResponse(BaseModel):
    """Response schema for list of cell performance records."""

    success: bool = True
    performances: list[CellPerformanceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class CellStatsResponse(BaseModel):
    """Response schema for cell statistics."""

    success: bool = True
    total_cells: int
    active_cells: int
    inactive_cells: int
    maintenance_cells: int
    reconfiguring_cells: int
    cells_by_type: dict[str, int]
    understaffed_cells: int
    average_oee: Optional[Decimal]
    average_efficiency: Optional[Decimal]
    total_current_output: int


class CellDailyOEEResponse(BaseModel):
    """Response schema for daily OEE data."""

    success: bool = True
    cell_id: int
    cell_code: str
    date_range_start: date
    date_range_end: date
    daily_data: list[dict]
    average_oee: Optional[Decimal]
    average_availability: Optional[Decimal]
    average_performance: Optional[Decimal]
    average_quality: Optional[Decimal]


# =============================================================================
# Helper Functions
# =============================================================================


def cell_to_response(cell: ProductionCell) -> ProductionCellResponse:
    """Convert a ProductionCell model to response schema."""
    cell_type_value = cell.cell_type.value if isinstance(cell.cell_type, CellType) else str(cell.cell_type)
    status_value = cell.status.value if isinstance(cell.status, CellStatus) else str(cell.status)

    return ProductionCellResponse(
        id=cell.id,
        name=cell.name,
        code=cell.code,
        description=cell.description,
        work_center_id=cell.work_center_id,
        cell_type=cell_type_value,
        status=status_value,
        takt_time_seconds=cell.takt_time_seconds,
        target_cycle_time_seconds=cell.target_cycle_time_seconds,
        target_output_per_shift=cell.target_output_per_shift,
        shift_duration_hours=cell.shift_duration_hours,
        planned_efficiency=cell.planned_efficiency,
        current_output=cell.current_output,
        current_efficiency_percentage=cell.current_efficiency_percentage,
        current_oee_percentage=cell.current_oee_percentage,
        min_operators=cell.min_operators,
        standard_operators=cell.standard_operators,
        max_operators=cell.max_operators,
        current_operators=cell.current_operators,
        station_count=cell.station_count,
        is_operational=cell.is_operational,
        is_understaffed=cell.is_understaffed,
        output_vs_target_percentage=cell.output_vs_target_percentage,
        theoretical_capacity_per_shift=cell.theoretical_capacity_per_shift,
        created_at=cell.created_at,
        updated_at=cell.updated_at,
    )


def performance_to_response(perf: CellPerformance) -> CellPerformanceResponse:
    """Convert a CellPerformance model to response schema."""
    shift_value = perf.shift_number.value if isinstance(perf.shift_number, ShiftNumber) else str(perf.shift_number)

    return CellPerformanceResponse(
        id=perf.id,
        cell_id=perf.cell_id,
        shift_date=perf.shift_date,
        shift_number=shift_value,
        planned_output=perf.planned_output,
        actual_output=perf.actual_output,
        good_output=perf.good_output,
        rework_output=perf.rework_output,
        scrap_output=perf.scrap_output,
        planned_time_minutes=perf.planned_time_minutes,
        operating_time_minutes=perf.operating_time_minutes,
        downtime_minutes=perf.downtime_minutes,
        changeover_minutes=perf.changeover_minutes,
        unplanned_downtime_minutes=perf.unplanned_downtime_minutes,
        planned_downtime_minutes=perf.planned_downtime_minutes,
        availability_percentage=perf.availability_percentage,
        performance_percentage=perf.performance_percentage,
        quality_percentage=perf.quality_percentage,
        oee_percentage=perf.oee_percentage,
        efficiency_percentage=perf.efficiency_percentage,
        operator_count=perf.operator_count,
        labor_hours=perf.labor_hours,
        units_per_labor_hour=perf.units_per_labor_hour,
        andon_events_count=perf.andon_events_count,
        quality_issues_count=perf.quality_issues_count,
        output_target_ratio=perf.output_target_ratio,
        scrap_rate=perf.scrap_rate,
        notes=perf.notes,
        issues_summary=perf.issues_summary,
        created_at=perf.created_at,
        updated_at=perf.updated_at,
    )


# =============================================================================
# Production Cell Endpoints
# =============================================================================


@router.get("", response_model=ProductionCellListResponse)
async def list_production_cells(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    work_center_id: Optional[int] = Query(default=None),
    cell_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort_by: str = Query(default="name"),
    sort_order: str = Query(default="asc"),
    include_deleted: bool = Query(default=False),
) -> ProductionCellListResponse:
    """List production cells with filtering and pagination."""
    # Validate cell_type if provided
    if cell_type is not None:
        try:
            CellType(cell_type)
        except ValueError:
            valid = [e.value for e in CellType]
            raise BadRequestError(f"Invalid cell_type. Must be one of: {valid}")

    # Validate status if provided
    if status is not None:
        try:
            CellStatus(status)
        except ValueError:
            valid = [e.value for e in CellStatus]
            raise BadRequestError(f"Invalid status. Must be one of: {valid}")

    # Build query
    query = select(ProductionCell).options(selectinload(ProductionCell.stations))

    # Apply soft delete filter
    if not include_deleted:
        query = query.where(ProductionCell.deleted_at.is_(None))

    # Apply filters
    if work_center_id is not None:
        query = query.where(ProductionCell.work_center_id == work_center_id)

    if cell_type is not None:
        query = query.where(ProductionCell.cell_type == CellType(cell_type))

    if status is not None:
        query = query.where(ProductionCell.status == CellStatus(status))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                ProductionCell.name.ilike(search_term),
                ProductionCell.code.ilike(search_term),
                ProductionCell.description.ilike(search_term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(ProductionCell, sort_by, ProductionCell.name)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    cells = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ProductionCellListResponse(
        success=True,
        cells=[cell_to_response(c) for c in cells],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=dict)
async def create_production_cell(
    data: ProductionCellCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Create a new production cell."""
    # Check for duplicate code
    existing_query = select(ProductionCell).where(ProductionCell.code == data.code)
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise ConflictError(f"Production cell with code '{data.code}' already exists")

    # Validate operator constraints
    if data.standard_operators < data.min_operators:
        raise BadRequestError("standard_operators must be >= min_operators")
    if data.max_operators < data.standard_operators:
        raise BadRequestError("max_operators must be >= standard_operators")

    cell = ProductionCell(
        name=data.name,
        code=data.code,
        description=data.description,
        work_center_id=data.work_center_id,
        cell_type=data.cell_type,
        status=data.status,
        takt_time_seconds=data.takt_time_seconds,
        target_cycle_time_seconds=data.target_cycle_time_seconds,
        target_output_per_shift=data.target_output_per_shift,
        shift_duration_hours=data.shift_duration_hours,
        planned_efficiency=data.planned_efficiency,
        min_operators=data.min_operators,
        standard_operators=data.standard_operators,
        max_operators=data.max_operators,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    db.add(cell)
    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": "Production cell created successfully",
        "cell": cell_to_response(cell),
    }


@router.get("/stats", response_model=CellStatsResponse)
async def get_cell_stats(
    db: DBSession,
    current_user: CurrentUser,
    work_center_id: Optional[int] = Query(default=None),
) -> CellStatsResponse:
    """Get aggregate statistics for production cells."""
    # Base query
    query = select(ProductionCell).where(ProductionCell.deleted_at.is_(None))

    if work_center_id is not None:
        query = query.where(ProductionCell.work_center_id == work_center_id)

    result = await db.execute(query.options(selectinload(ProductionCell.stations)))
    cells = list(result.scalars().all())

    # Count by status
    status_counts = {status.value: 0 for status in CellStatus}
    for cell in cells:
        status_val = cell.status.value if isinstance(cell.status, CellStatus) else str(cell.status)
        status_counts[status_val] = status_counts.get(status_val, 0) + 1

    # Count by type
    type_counts = {cell_type.value: 0 for cell_type in CellType}
    for cell in cells:
        type_val = cell.cell_type.value if isinstance(cell.cell_type, CellType) else str(cell.cell_type)
        type_counts[type_val] = type_counts.get(type_val, 0) + 1

    # Count understaffed
    understaffed = sum(1 for c in cells if c.is_understaffed)

    # Calculate averages
    oee_values = [c.current_oee_percentage for c in cells if c.current_oee_percentage is not None]
    efficiency_values = [c.current_efficiency_percentage for c in cells if c.current_efficiency_percentage is not None]

    avg_oee = sum(oee_values) / len(oee_values) if oee_values else None
    avg_efficiency = sum(efficiency_values) / len(efficiency_values) if efficiency_values else None

    total_output = sum(c.current_output for c in cells)

    return CellStatsResponse(
        success=True,
        total_cells=len(cells),
        active_cells=status_counts.get("active", 0),
        inactive_cells=status_counts.get("inactive", 0),
        maintenance_cells=status_counts.get("maintenance", 0),
        reconfiguring_cells=status_counts.get("reconfiguring", 0),
        cells_by_type=type_counts,
        understaffed_cells=understaffed,
        average_oee=avg_oee,
        average_efficiency=avg_efficiency,
        total_current_output=total_output,
    )


@router.get("/{cell_id}", response_model=dict)
async def get_production_cell(
    cell_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
) -> dict:
    """Get a specific production cell by ID."""
    query = select(ProductionCell).where(ProductionCell.id == cell_id)
    query = query.options(selectinload(ProductionCell.stations))

    if not include_deleted:
        query = query.where(ProductionCell.deleted_at.is_(None))

    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    return {
        "success": True,
        "cell": cell_to_response(cell),
    }


@router.patch("/{cell_id}", response_model=dict)
async def update_production_cell(
    cell_id: int,
    data: ProductionCellUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Update a production cell."""
    query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    update_data = data.model_dump(exclude_unset=True)

    # Validate operator constraints if any are being updated
    min_ops = update_data.get("min_operators", cell.min_operators)
    std_ops = update_data.get("standard_operators", cell.standard_operators)
    max_ops = update_data.get("max_operators", cell.max_operators)

    if std_ops < min_ops:
        raise BadRequestError("standard_operators must be >= min_operators")
    if max_ops < std_ops:
        raise BadRequestError("max_operators must be >= standard_operators")

    for field, value in update_data.items():
        setattr(cell, field, value)

    cell.updated_by_id = current_user.id
    cell.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": "Production cell updated successfully",
        "cell": cell_to_response(cell),
    }


@router.delete("/{cell_id}", response_model=dict)
async def delete_production_cell(
    cell_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
) -> dict:
    """Delete a production cell (soft or hard delete)."""
    query = select(ProductionCell).where(ProductionCell.id == cell_id)

    if not hard_delete:
        query = query.where(ProductionCell.deleted_at.is_(None))

    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    if hard_delete:
        await db.delete(cell)
        message = "Production cell permanently deleted"
    else:
        cell.deleted_at = datetime.now(timezone.utc)
        cell.deleted_by_id = current_user.id
        message = "Production cell deleted successfully"

    await db.commit()

    return {
        "success": True,
        "message": message,
    }


@router.post("/{cell_id}/restore", response_model=dict)
async def restore_production_cell(
    cell_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Restore a soft-deleted production cell."""
    query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.isnot(None),
    )
    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Deleted production cell with ID {cell_id} not found")

    cell.deleted_at = None
    cell.deleted_by_id = None
    cell.updated_by_id = current_user.id
    cell.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": "Production cell restored successfully",
        "cell": cell_to_response(cell),
    }


@router.post("/{cell_id}/set-status", response_model=dict)
async def set_cell_status(
    cell_id: int,
    status: str,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Update the status of a production cell."""
    # Validate status
    try:
        new_status = CellStatus(status)
    except ValueError:
        valid = [e.value for e in CellStatus]
        raise BadRequestError(f"Invalid status. Must be one of: {valid}")

    query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    old_status = cell.status.value if isinstance(cell.status, CellStatus) else str(cell.status)
    cell.status = new_status
    cell.updated_by_id = current_user.id
    cell.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": f"Production cell status changed from {old_status} to {status}",
        "cell": cell_to_response(cell),
    }


@router.post("/{cell_id}/update-operators", response_model=dict)
async def update_operators(
    cell_id: int,
    operator_count: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Update the current operator count for a production cell."""
    if operator_count < 0:
        raise BadRequestError("Operator count cannot be negative")

    query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    cell.current_operators = operator_count
    cell.updated_by_id = current_user.id
    cell.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": f"Operator count updated to {operator_count}",
        "cell": cell_to_response(cell),
        "is_understaffed": cell.is_understaffed,
    }


@router.post("/{cell_id}/update-output", response_model=dict)
async def update_output(
    cell_id: int,
    output: int,
    db: DBSession,
    current_user: CurrentUser,
    efficiency_percentage: Optional[Decimal] = Query(default=None),
    oee_percentage: Optional[Decimal] = Query(default=None),
) -> dict:
    """Update the current output and optionally efficiency/OEE for a production cell."""
    if output < 0:
        raise BadRequestError("Output cannot be negative")

    query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    cell.current_output = output
    if efficiency_percentage is not None:
        cell.current_efficiency_percentage = efficiency_percentage
    if oee_percentage is not None:
        cell.current_oee_percentage = oee_percentage

    cell.updated_by_id = current_user.id
    cell.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": f"Output updated to {output}",
        "cell": cell_to_response(cell),
        "output_vs_target_percentage": cell.output_vs_target_percentage,
    }


@router.post("/{cell_id}/reset-shift", response_model=dict)
async def reset_shift(
    cell_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Reset the current shift metrics for a production cell."""
    query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    result = await db.execute(query)
    cell = result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    cell.current_output = 0
    cell.current_efficiency_percentage = None
    cell.current_oee_percentage = None
    cell.updated_by_id = current_user.id
    cell.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(cell)

    return {
        "success": True,
        "message": "Shift metrics reset successfully",
        "cell": cell_to_response(cell),
    }


# =============================================================================
# Cell Performance Endpoints
# =============================================================================


@router.get("/{cell_id}/performances", response_model=CellPerformanceListResponse)
async def list_cell_performances(
    cell_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    shift_number: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    sort_by: str = Query(default="shift_date"),
    sort_order: str = Query(default="desc"),
) -> CellPerformanceListResponse:
    """List performance records for a production cell."""
    # Verify cell exists
    cell_query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    cell_result = await db.execute(cell_query)
    if not cell_result.scalar_one_or_none():
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    # Validate shift_number if provided
    if shift_number is not None:
        try:
            ShiftNumber(shift_number)
        except ValueError:
            valid = [e.value for e in ShiftNumber]
            raise BadRequestError(f"Invalid shift_number. Must be one of: {valid}")

    # Build query
    query = select(CellPerformance).where(CellPerformance.cell_id == cell_id)

    if shift_number is not None:
        query = query.where(CellPerformance.shift_number == ShiftNumber(shift_number))

    if start_date is not None:
        query = query.where(CellPerformance.shift_date >= start_date)

    if end_date is not None:
        query = query.where(CellPerformance.shift_date <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(CellPerformance, sort_by, CellPerformance.shift_date)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    performances = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return CellPerformanceListResponse(
        success=True,
        performances=[performance_to_response(p) for p in performances],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/{cell_id}/performances", response_model=dict)
async def create_cell_performance(
    cell_id: int,
    data: CellPerformanceCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Create a new performance record for a production cell."""
    # Verify cell exists
    cell_query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    cell_result = await db.execute(cell_query)
    cell = cell_result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    # Check for duplicate shift record
    duplicate_query = select(CellPerformance).where(
        CellPerformance.cell_id == cell_id,
        CellPerformance.shift_date == data.shift_date,
        CellPerformance.shift_number == data.shift_number,
    )
    duplicate_result = await db.execute(duplicate_query)
    if duplicate_result.scalar_one_or_none():
        raise ConflictError(
            f"Performance record already exists for cell {cell_id} on {data.shift_date} {data.shift_number.value}"
        )

    # Calculate OEE components
    availability, performance, quality, oee = CellPerformance.calculate_oee(
        planned_time=data.planned_time_minutes,
        operating_time=data.operating_time_minutes,
        actual_output=data.actual_output,
        good_output=data.good_output,
        ideal_cycle_time_seconds=cell.target_cycle_time_seconds,
    )

    # Calculate efficiency
    if data.planned_output > 0:
        efficiency = (Decimal(data.actual_output) / Decimal(data.planned_output)) * 100
    else:
        efficiency = Decimal("0")

    # Calculate units per labor hour
    if data.labor_hours > 0:
        units_per_labor_hour = Decimal(data.good_output) / data.labor_hours
    else:
        units_per_labor_hour = None

    perf = CellPerformance(
        cell_id=cell_id,
        shift_date=data.shift_date,
        shift_number=data.shift_number,
        planned_output=data.planned_output,
        actual_output=data.actual_output,
        good_output=data.good_output,
        rework_output=data.rework_output,
        scrap_output=data.scrap_output,
        planned_time_minutes=data.planned_time_minutes,
        operating_time_minutes=data.operating_time_minutes,
        downtime_minutes=data.downtime_minutes,
        changeover_minutes=data.changeover_minutes,
        unplanned_downtime_minutes=data.unplanned_downtime_minutes,
        planned_downtime_minutes=data.planned_downtime_minutes,
        availability_percentage=availability,
        performance_percentage=performance,
        quality_percentage=quality,
        oee_percentage=oee,
        efficiency_percentage=min(efficiency, Decimal("100")),
        operator_count=data.operator_count,
        labor_hours=data.labor_hours,
        units_per_labor_hour=units_per_labor_hour,
        andon_events_count=data.andon_events_count,
        quality_issues_count=data.quality_issues_count,
        notes=data.notes,
        issues_summary=data.issues_summary,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    db.add(perf)
    await db.commit()
    await db.refresh(perf)

    return {
        "success": True,
        "message": "Performance record created successfully",
        "performance": performance_to_response(perf),
    }


@router.get("/{cell_id}/performances/{performance_id}", response_model=dict)
async def get_cell_performance(
    cell_id: int,
    performance_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Get a specific performance record."""
    query = select(CellPerformance).where(
        CellPerformance.id == performance_id,
        CellPerformance.cell_id == cell_id,
    )
    result = await db.execute(query)
    perf = result.scalar_one_or_none()

    if not perf:
        raise NotFoundError(f"Performance record with ID {performance_id} not found")

    return {
        "success": True,
        "performance": performance_to_response(perf),
    }


@router.patch("/{cell_id}/performances/{performance_id}", response_model=dict)
async def update_cell_performance(
    cell_id: int,
    performance_id: int,
    data: CellPerformanceUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Update a performance record."""
    # Get performance record
    query = select(CellPerformance).where(
        CellPerformance.id == performance_id,
        CellPerformance.cell_id == cell_id,
    )
    result = await db.execute(query)
    perf = result.scalar_one_or_none()

    if not perf:
        raise NotFoundError(f"Performance record with ID {performance_id} not found")

    # Get cell for cycle time
    cell_query = select(ProductionCell).where(ProductionCell.id == cell_id)
    cell_result = await db.execute(cell_query)
    cell = cell_result.scalar_one_or_none()

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(perf, field, value)

    # Recalculate OEE if relevant fields changed
    oee_fields = {"planned_time_minutes", "operating_time_minutes", "actual_output", "good_output"}
    if oee_fields & set(update_data.keys()):
        availability, performance, quality, oee = CellPerformance.calculate_oee(
            planned_time=perf.planned_time_minutes,
            operating_time=perf.operating_time_minutes,
            actual_output=perf.actual_output,
            good_output=perf.good_output,
            ideal_cycle_time_seconds=cell.target_cycle_time_seconds if cell else 60,
        )
        perf.availability_percentage = availability
        perf.performance_percentage = performance
        perf.quality_percentage = quality
        perf.oee_percentage = oee

    # Recalculate efficiency if relevant fields changed
    if "planned_output" in update_data or "actual_output" in update_data:
        if perf.planned_output > 0:
            perf.efficiency_percentage = min(
                (Decimal(perf.actual_output) / Decimal(perf.planned_output)) * 100,
                Decimal("100"),
            )
        else:
            perf.efficiency_percentage = Decimal("0")

    # Recalculate units per labor hour
    if "labor_hours" in update_data or "good_output" in update_data:
        if perf.labor_hours > 0:
            perf.units_per_labor_hour = Decimal(perf.good_output) / perf.labor_hours
        else:
            perf.units_per_labor_hour = None

    perf.updated_by_id = current_user.id
    perf.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(perf)

    return {
        "success": True,
        "message": "Performance record updated successfully",
        "performance": performance_to_response(perf),
    }


@router.delete("/{cell_id}/performances/{performance_id}", response_model=dict)
async def delete_cell_performance(
    cell_id: int,
    performance_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Delete a performance record."""
    query = select(CellPerformance).where(
        CellPerformance.id == performance_id,
        CellPerformance.cell_id == cell_id,
    )
    result = await db.execute(query)
    perf = result.scalar_one_or_none()

    if not perf:
        raise NotFoundError(f"Performance record with ID {performance_id} not found")

    await db.delete(perf)
    await db.commit()

    return {
        "success": True,
        "message": "Performance record deleted successfully",
    }


@router.get("/{cell_id}/oee-trend", response_model=CellDailyOEEResponse)
async def get_cell_oee_trend(
    cell_id: int,
    db: DBSession,
    current_user: CurrentUser,
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> CellDailyOEEResponse:
    """Get OEE trend data for a production cell over a date range."""
    # Verify cell exists
    cell_query = select(ProductionCell).where(
        ProductionCell.id == cell_id,
        ProductionCell.deleted_at.is_(None),
    )
    cell_result = await db.execute(cell_query)
    cell = cell_result.scalar_one_or_none()

    if not cell:
        raise NotFoundError(f"Production cell with ID {cell_id} not found")

    if start_date > end_date:
        raise BadRequestError("start_date must be before or equal to end_date")

    # Get performance records
    query = select(CellPerformance).where(
        CellPerformance.cell_id == cell_id,
        CellPerformance.shift_date >= start_date,
        CellPerformance.shift_date <= end_date,
    ).order_by(CellPerformance.shift_date.asc(), CellPerformance.shift_number.asc())

    result = await db.execute(query)
    performances = list(result.scalars().all())

    # Build daily data
    daily_data = []
    for perf in performances:
        shift_val = perf.shift_number.value if isinstance(perf.shift_number, ShiftNumber) else str(perf.shift_number)
        daily_data.append({
            "date": perf.shift_date.isoformat(),
            "shift": shift_val,
            "oee": float(perf.oee_percentage),
            "availability": float(perf.availability_percentage),
            "performance": float(perf.performance_percentage),
            "quality": float(perf.quality_percentage),
            "actual_output": perf.actual_output,
            "good_output": perf.good_output,
        })

    # Calculate averages
    if performances:
        avg_oee = sum(p.oee_percentage for p in performances) / len(performances)
        avg_availability = sum(p.availability_percentage for p in performances) / len(performances)
        avg_performance = sum(p.performance_percentage for p in performances) / len(performances)
        avg_quality = sum(p.quality_percentage for p in performances) / len(performances)
    else:
        avg_oee = None
        avg_availability = None
        avg_performance = None
        avg_quality = None

    return CellDailyOEEResponse(
        success=True,
        cell_id=cell_id,
        cell_code=cell.code,
        date_range_start=start_date,
        date_range_end=end_date,
        daily_data=daily_data,
        average_oee=avg_oee,
        average_availability=avg_availability,
        average_performance=avg_performance,
        average_quality=avg_quality,
    )
