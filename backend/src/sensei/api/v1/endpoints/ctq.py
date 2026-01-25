"""CTQ (Critical to Quality) Endpoints.

Provides CRUD and workflow operations for:
- CTQ definitions (quality characteristic specifications)
- CTQ measurements (actual measurement records)

Implements quality management following Six Sigma and SPC principles.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload

from sensei.api import deps
from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_response,
    build_updated_response,
    escape_like_pattern,
)
from sensei.models.ctq import (
    CTQ,
    CTQMeasurement,
    CTQCategory,
    CTQPriority,
    CTQStatus,
    MeasurementResult,
)

AllowCTQModule = deps.require_role(
    "ops",
    "quality",
    "supervisor",
    "team_lead",
    "operator",
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
                    "quality",
                    "supervisor",
                    "team_lead",
                    "operator",
                    "engineering",
                    "gm",
                    "exec",
                ]
            )
        )
    ]
)


# =============================================================================
# Utility helpers
# =============================================================================


def _now_utc() -> datetime:
    """Get current UTC datetime."""
    from datetime import timezone
    return datetime.now(timezone.utc)


def _parse_enum(enum_cls: Any, value: Any, field_name: str):
    """Parse string value to enum."""
    if value is None or isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            valid = [e.value for e in enum_cls]
            raise ValueError(f"Invalid {field_name}. Must be one of: {valid}")
    return value


# =============================================================================
# CTQ Schemas
# =============================================================================


class CTQCreate(BaseModel):
    """Schema for creating a CTQ."""

    ctq_number: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    rfq_id: Optional[UUID] = None
    part_number: Optional[str] = Field(default=None, max_length=100)
    drawing_reference: Optional[str] = Field(default=None, max_length=100)
    operation_number: Optional[str] = Field(default=None, max_length=50)
    category: CTQCategory = CTQCategory.DIMENSIONAL
    priority: CTQPriority = CTQPriority.MAJOR
    nominal_value: Optional[Decimal] = None
    unit_of_measure: str = Field(default="mm", max_length=50)
    upper_spec_limit: Optional[Decimal] = None
    lower_spec_limit: Optional[Decimal] = None
    tolerance_type: Optional[str] = Field(default=None, max_length=50)
    gdt_symbol: Optional[str] = Field(default=None, max_length=50)
    gdt_value: Optional[Decimal] = None
    datum_reference: Optional[str] = Field(default=None, max_length=100)
    target_cpk: Optional[Decimal] = None
    target_ppk: Optional[Decimal] = None
    sample_size: Optional[int] = None
    sample_frequency: Optional[str] = Field(default=None, max_length=100)
    measurement_method: Optional[str] = None
    measurement_equipment: Optional[str] = Field(default=None, max_length=255)
    gauge_id: Optional[str] = Field(default=None, max_length=100)
    gauge_r_and_r: Optional[Decimal] = None
    control_method: Optional[str] = None
    reaction_plan: Optional[str] = None
    customer_requirement: Optional[str] = None
    customer_specification: Optional[str] = Field(default=None, max_length=255)
    is_customer_critical: bool = False
    notes: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        return _parse_enum(CTQCategory, v, "category")

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v):
        return _parse_enum(CTQPriority, v, "priority")


class CTQUpdate(BaseModel):
    """Schema for updating a CTQ."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    part_number: Optional[str] = Field(default=None, max_length=100)
    drawing_reference: Optional[str] = Field(default=None, max_length=100)
    operation_number: Optional[str] = Field(default=None, max_length=50)
    category: Optional[CTQCategory] = None
    priority: Optional[CTQPriority] = None
    nominal_value: Optional[Decimal] = None
    unit_of_measure: Optional[str] = Field(default=None, max_length=50)
    upper_spec_limit: Optional[Decimal] = None
    lower_spec_limit: Optional[Decimal] = None
    tolerance_type: Optional[str] = Field(default=None, max_length=50)
    gdt_symbol: Optional[str] = Field(default=None, max_length=50)
    gdt_value: Optional[Decimal] = None
    datum_reference: Optional[str] = Field(default=None, max_length=100)
    target_cpk: Optional[Decimal] = None
    target_ppk: Optional[Decimal] = None
    sample_size: Optional[int] = None
    sample_frequency: Optional[str] = Field(default=None, max_length=100)
    measurement_method: Optional[str] = None
    measurement_equipment: Optional[str] = Field(default=None, max_length=255)
    gauge_id: Optional[str] = Field(default=None, max_length=100)
    gauge_r_and_r: Optional[Decimal] = None
    control_method: Optional[str] = None
    reaction_plan: Optional[str] = None
    customer_requirement: Optional[str] = None
    customer_specification: Optional[str] = Field(default=None, max_length=255)
    is_customer_critical: Optional[bool] = None
    notes: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        return _parse_enum(CTQCategory, v, "category")

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v):
        return _parse_enum(CTQPriority, v, "priority")


class CTQResponse(BaseModel):
    """Response schema for CTQ."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ctq_number: str
    name: str
    description: Optional[str]
    rfq_id: Optional[UUID]
    part_number: Optional[str]
    drawing_reference: Optional[str]
    operation_number: Optional[str]
    category: str
    priority: str
    status: str
    nominal_value: Optional[Decimal]
    unit_of_measure: str
    upper_spec_limit: Optional[Decimal]
    lower_spec_limit: Optional[Decimal]
    tolerance_type: Optional[str]
    gdt_symbol: Optional[str]
    gdt_value: Optional[Decimal]
    datum_reference: Optional[str]
    target_cpk: Optional[Decimal]
    target_ppk: Optional[Decimal]
    sample_size: Optional[int]
    sample_frequency: Optional[str]
    measurement_method: Optional[str]
    measurement_equipment: Optional[str]
    gauge_id: Optional[str]
    gauge_r_and_r: Optional[Decimal]
    control_method: Optional[str]
    reaction_plan: Optional[str]
    customer_requirement: Optional[str]
    customer_specification: Optional[str]
    is_customer_critical: bool
    approved_by_id: Optional[UUID]
    approved_at: Optional[datetime]
    notes: Optional[str]
    custom_fields: Optional[dict[str, Any]]
    tolerance_range: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# CTQ Measurement Schemas
# =============================================================================


class MeasurementCreate(BaseModel):
    """Schema for creating a CTQ measurement."""

    measurement_number: Optional[str] = Field(default=None, max_length=50)
    batch_number: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    sample_number: Optional[int] = None
    measured_value: Decimal
    measured_at: Optional[datetime] = None
    equipment_id: Optional[str] = Field(default=None, max_length=100)
    calibration_date: Optional[datetime] = None
    temperature: Optional[Decimal] = None
    humidity: Optional[Decimal] = None
    notes: Optional[str] = None
    attachments: Optional[list[Any]] = None


class MeasurementUpdate(BaseModel):
    """Schema for updating a CTQ measurement."""

    batch_number: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    sample_number: Optional[int] = None
    notes: Optional[str] = None
    corrective_action: Optional[str] = None
    disposition: Optional[str] = Field(default=None, max_length=50)
    attachments: Optional[list[Any]] = None


class MeasurementResponse(BaseModel):
    """Response schema for CTQ measurement."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ctq_id: UUID
    measurement_number: Optional[str]
    batch_number: Optional[str]
    serial_number: Optional[str]
    sample_number: Optional[int]
    measured_value: Decimal
    deviation: Optional[Decimal]
    result: str
    measured_at: datetime
    measured_by_id: Optional[UUID]
    equipment_id: Optional[str]
    calibration_date: Optional[datetime]
    temperature: Optional[Decimal]
    humidity: Optional[Decimal]
    notes: Optional[str]
    corrective_action: Optional[str]
    disposition: Optional[str]
    attachments: Optional[list[Any]]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# CTQ CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=APIResponse[CTQResponse],
    status_code=201,
    summary="Create CTQ",
    description="Create a new Critical to Quality characteristic.",
)
async def create_ctq(
    data: CTQCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    # Check for duplicate ctq_number
    stmt = select(CTQ).where(
        and_(
            CTQ.ctq_number == data.ctq_number,
            CTQ.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise ConflictError(f"CTQ with number '{data.ctq_number}' already exists")

    ctq = CTQ(
        ctq_number=data.ctq_number,
        name=data.name,
        description=data.description,
        rfq_id=data.rfq_id,
        part_number=data.part_number,
        drawing_reference=data.drawing_reference,
        operation_number=data.operation_number,
        category=(
            data.category.value
            if isinstance(data.category, CTQCategory)
            else data.category
        ),
        priority=(
            data.priority.value
            if isinstance(data.priority, CTQPriority)
            else data.priority
        ),
        status=CTQStatus.DRAFT.value,
        nominal_value=data.nominal_value,
        unit_of_measure=data.unit_of_measure,
        upper_spec_limit=data.upper_spec_limit,
        lower_spec_limit=data.lower_spec_limit,
        tolerance_type=data.tolerance_type,
        gdt_symbol=data.gdt_symbol,
        gdt_value=data.gdt_value,
        datum_reference=data.datum_reference,
        target_cpk=data.target_cpk,
        target_ppk=data.target_ppk,
        sample_size=data.sample_size,
        sample_frequency=data.sample_frequency,
        measurement_method=data.measurement_method,
        measurement_equipment=data.measurement_equipment,
        gauge_id=data.gauge_id,
        gauge_r_and_r=data.gauge_r_and_r,
        control_method=data.control_method,
        reaction_plan=data.reaction_plan,
        customer_requirement=data.customer_requirement,
        customer_specification=data.customer_specification,
        is_customer_critical=data.is_customer_critical,
        notes=data.notes,
        custom_fields=data.custom_fields,
        created_by_id=current_user.id,
    )
    db.add(ctq)
    await db.flush()
    await db.refresh(ctq)

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_created_response(data=response, resource_name="CTQ")


@router.get(
    "/{ctq_id}",
    response_model=APIResponse[CTQResponse],
    summary="Get CTQ",
    description="Get a CTQ by ID.",
)
async def get_ctq(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_response(response)


@router.get(
    "",
    response_model=PaginatedResponse[CTQResponse],
    summary="List CTQs",
    description="List CTQ characteristics with filtering and pagination.",
)
async def list_ctqs(
    db: DBSession,
    current_user: CurrentUser,
    category: Optional[CTQCategory] = Query(default=None),
    priority: Optional[CTQPriority] = Query(default=None),
    status: Optional[CTQStatus] = Query(default=None),
    part_number: Optional[str] = Query(default=None),
    rfq_id: Optional[UUID] = Query(default=None),
    is_customer_critical: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CTQResponse]:
    base_conditions: list[Any] = [CTQ.deleted_at.is_(None)]

    if category and isinstance(category, CTQCategory):
        base_conditions.append(CTQ.category == category.value)
    if priority and isinstance(priority, CTQPriority):
        base_conditions.append(CTQ.priority == priority.value)
    if status and isinstance(status, CTQStatus):
        base_conditions.append(CTQ.status == status.value)
    if part_number:
        base_conditions.append(CTQ.part_number == part_number)
    if rfq_id:
        base_conditions.append(CTQ.rfq_id == rfq_id)
    if is_customer_critical is not None:
        base_conditions.append(CTQ.is_customer_critical == is_customer_critical)
    if search:
        escaped_search = escape_like_pattern(search)
        search_filter = or_(
            CTQ.name.ilike(f"%{escaped_search}%"),
            CTQ.ctq_number.ilike(f"%{escaped_search}%"),
            CTQ.description.ilike(f"%{escaped_search}%"),
        )
        base_conditions.append(search_filter)

    count_stmt = select(func.count(CTQ.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(CTQ)
        .where(and_(*base_conditions))
        .order_by(CTQ.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    ctqs = data_result.scalars().all()

    items = []
    for ctq in ctqs:
        response = CTQResponse.model_validate(ctq)
        response.tolerance_range = ctq.tolerance_range
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{ctq_id}",
    response_model=APIResponse[CTQResponse],
    summary="Update CTQ",
    description="Update a CTQ characteristic.",
)
async def update_ctq(
    ctq_id: UUID,
    data: CTQUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "category" and isinstance(value, CTQCategory):
            value = value.value
        elif field == "priority" and isinstance(value, CTQPriority):
            value = value.value
        setattr(ctq, field, value)

    ctq.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(ctq)

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_updated_response(response, "CTQ")


@router.delete(
    "/{ctq_id}",
    response_model=APIResponse[None],
    summary="Delete CTQ",
    description="Soft delete a CTQ characteristic.",
)
async def delete_ctq(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    ctq.deleted_at = _now_utc()
    ctq.deleted_by_id = current_user.id
    await db.flush()

    return build_deleted_response("CTQ")


# =============================================================================
# CTQ Workflow Endpoints
# =============================================================================


@router.post(
    "/{ctq_id}/activate",
    response_model=APIResponse[CTQResponse],
    summary="Activate CTQ",
    description="Move CTQ from draft to active status.",
)
async def activate_ctq(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    if ctq.status != CTQStatus.DRAFT.value:
        raise ConflictError(f"Cannot activate CTQ in '{ctq.status}' status")

    ctq.status = CTQStatus.ACTIVE.value
    ctq.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(ctq)

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_response(response, "CTQ activated")


@router.post(
    "/{ctq_id}/submit-for-review",
    response_model=APIResponse[CTQResponse],
    summary="Submit CTQ for review",
    description="Submit CTQ for approval review.",
)
async def submit_for_review(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    if ctq.status not in [CTQStatus.DRAFT.value, CTQStatus.ACTIVE.value]:
        raise ConflictError(f"Cannot submit CTQ in '{ctq.status}' status for review")

    ctq.status = CTQStatus.UNDER_REVIEW.value
    ctq.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(ctq)

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_response(response, "CTQ submitted for review")


@router.post(
    "/{ctq_id}/approve",
    response_model=APIResponse[CTQResponse],
    summary="Approve CTQ",
    description="Approve the CTQ specification.",
)
async def approve_ctq(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    if ctq.status != CTQStatus.UNDER_REVIEW.value:
        raise ConflictError(f"Cannot approve CTQ in '{ctq.status}' status")

    ctq.status = CTQStatus.APPROVED.value
    ctq.approved_by_id = current_user.id
    ctq.approved_at = _now_utc()
    ctq.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(ctq)

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_response(response, "CTQ approved")


@router.post(
    "/{ctq_id}/obsolete",
    response_model=APIResponse[CTQResponse],
    summary="Mark CTQ obsolete",
    description="Mark the CTQ as obsolete.",
)
async def obsolete_ctq(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    ctq.status = CTQStatus.OBSOLETE.value
    ctq.updated_by_id = current_user.id
    await db.flush()
    await db.refresh(ctq)

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_response(response, "CTQ marked obsolete")


# =============================================================================
# CTQ Measurement Endpoints
# =============================================================================


@router.post(
    "/{ctq_id}/measurements",
    response_model=APIResponse[MeasurementResponse],
    status_code=201,
    summary="Record measurement",
    description="Record a new measurement against a CTQ.",
)
async def create_measurement(
    ctq_id: UUID,
    data: MeasurementCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MeasurementResponse]:
    # Check CTQ exists
    ctq_stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    ctq_result = await db.execute(ctq_stmt)
    ctq = ctq_result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    measurement = CTQMeasurement(
        ctq_id=ctq_id,
        measurement_number=data.measurement_number,
        batch_number=data.batch_number,
        serial_number=data.serial_number,
        sample_number=data.sample_number,
        measured_value=data.measured_value,
        measured_at=data.measured_at or _now_utc(),
        measured_by_id=current_user.id,
        equipment_id=data.equipment_id,
        calibration_date=data.calibration_date,
        temperature=data.temperature,
        humidity=data.humidity,
        notes=data.notes,
        attachments=data.attachments,
    )

    # Calculate deviation if nominal value exists
    if ctq.nominal_value is not None:
        measurement.calculate_deviation(ctq.nominal_value)

    # Determine pass/fail result
    measurement.determine_result(ctq)

    db.add(measurement)
    await db.flush()
    await db.refresh(measurement)

    return build_created_response(
        data=MeasurementResponse.model_validate(measurement),
        resource_name="Measurement"
    )


@router.get(
    "/{ctq_id}/measurements",
    response_model=PaginatedResponse[MeasurementResponse],
    summary="List measurements",
    description="List measurements for a CTQ with filtering and pagination.",
)
async def list_measurements(
    ctq_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    result: Optional[MeasurementResult] = Query(default=None),
    batch_number: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[MeasurementResponse]:
    # Check CTQ exists
    ctq_stmt = select(CTQ).where(
        and_(CTQ.id == ctq_id, CTQ.deleted_at.is_(None))
    )
    ctq_result = await db.execute(ctq_stmt)
    ctq = ctq_result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ {ctq_id} not found")

    base_conditions: list[Any] = [CTQMeasurement.ctq_id == ctq_id]

    if result and isinstance(result, MeasurementResult):
        base_conditions.append(CTQMeasurement.result == result.value)
    if batch_number:
        base_conditions.append(CTQMeasurement.batch_number == batch_number)

    count_stmt = select(func.count(CTQMeasurement.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(CTQMeasurement)
        .where(and_(*base_conditions))
        .order_by(CTQMeasurement.measured_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    measurements = data_result.scalars().all()

    items = [MeasurementResponse.model_validate(m) for m in measurements]

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{ctq_id}/measurements/{measurement_id}",
    response_model=APIResponse[MeasurementResponse],
    summary="Get measurement",
    description="Get a specific measurement by ID.",
)
async def get_measurement(
    ctq_id: UUID,
    measurement_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MeasurementResponse]:
    stmt = select(CTQMeasurement).where(
        and_(
            CTQMeasurement.id == measurement_id,
            CTQMeasurement.ctq_id == ctq_id,
        )
    )
    result = await db.execute(stmt)
    measurement = result.scalar_one_or_none()
    if not measurement:
        raise NotFoundError(f"Measurement {measurement_id} not found")

    return build_response(MeasurementResponse.model_validate(measurement))


@router.patch(
    "/{ctq_id}/measurements/{measurement_id}",
    response_model=APIResponse[MeasurementResponse],
    summary="Update measurement",
    description="Update a measurement record.",
)
async def update_measurement(
    ctq_id: UUID,
    measurement_id: UUID,
    data: MeasurementUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MeasurementResponse]:
    stmt = select(CTQMeasurement).where(
        and_(
            CTQMeasurement.id == measurement_id,
            CTQMeasurement.ctq_id == ctq_id,
        )
    )
    result = await db.execute(stmt)
    measurement = result.scalar_one_or_none()
    if not measurement:
        raise NotFoundError(f"Measurement {measurement_id} not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(measurement, field, value)

    await db.flush()
    await db.refresh(measurement)

    return build_updated_response(
        MeasurementResponse.model_validate(measurement),
        "Measurement"
    )


@router.delete(
    "/{ctq_id}/measurements/{measurement_id}",
    response_model=APIResponse[None],
    summary="Delete measurement",
    description="Delete a measurement record.",
)
async def delete_measurement(
    ctq_id: UUID,
    measurement_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    stmt = select(CTQMeasurement).where(
        and_(
            CTQMeasurement.id == measurement_id,
            CTQMeasurement.ctq_id == ctq_id,
        )
    )
    result = await db.execute(stmt)
    measurement = result.scalar_one_or_none()
    if not measurement:
        raise NotFoundError(f"Measurement {measurement_id} not found")

    await db.delete(measurement)
    await db.flush()

    return build_deleted_response("Measurement")


# =============================================================================
# Query Endpoints
# =============================================================================


@router.get(
    "/by-number/{ctq_number}",
    response_model=APIResponse[CTQResponse],
    summary="Get CTQ by number",
    description="Get a CTQ by its document number.",
)
async def get_ctq_by_number(
    ctq_number: str,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CTQResponse]:
    stmt = select(CTQ).where(
        and_(CTQ.ctq_number == ctq_number, CTQ.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    ctq = result.scalar_one_or_none()
    if not ctq:
        raise NotFoundError(f"CTQ with number '{ctq_number}' not found")

    response = CTQResponse.model_validate(ctq)
    response.tolerance_range = ctq.tolerance_range

    return build_response(response)


@router.get(
    "/critical",
    response_model=PaginatedResponse[CTQResponse],
    summary="Get critical CTQs",
    description="Get customer-critical CTQs.",
)
async def get_critical_ctqs(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[CTQResponse]:
    base_conditions: list[Any] = [
        CTQ.deleted_at.is_(None),
        CTQ.is_customer_critical.is_(True),
    ]

    count_stmt = select(func.count(CTQ.id)).where(and_(*base_conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    data_stmt = (
        select(CTQ)
        .where(and_(*base_conditions))
        .order_by(CTQ.priority.asc(), CTQ.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_stmt)
    ctqs = data_result.scalars().all()

    items = []
    for ctq in ctqs:
        response = CTQResponse.model_validate(ctq)
        response.tolerance_range = ctq.tolerance_range
        items.append(response)

    return build_paginated_response(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
    )
