"""Andon System Endpoints.

Provides CRUD and workflow operations for:
- Andon Events (report, acknowledge, resolve, escalate)
- Andon Escalations
- Andon Recurrence Patterns

Implements the Stop-Call-Wait workflow following TPS principles.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload

from sensei.api.deps import CurrentUser, DBSession
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.api.schemas import APIResponse, PaginatedResponse
from sensei.api.utils import (
    build_created_response,
    build_deleted_response,
    build_paginated_response,
    build_response,
    build_updated_response,
)
from sensei.models.andon import (
    AndonEvent,
    AndonType,
    AndonSeverity,
    AndonStatus,
    EscalationLevel,
    AndonEscalation,
    ResponseStatus,
    AndonRecurrencePattern,
)

router = APIRouter()


# =============================================================================
# Utility helpers
# =============================================================================


def _now_utc() -> datetime:
    """Get current UTC datetime (naive) for consistency with model timestamps."""
    return datetime.utcnow()


# =============================================================================
# Enum parsing helpers
# =============================================================================


def _parse_enum(enum_cls: Any, value: Any, field_name: str):
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
# Andon Event Schemas
# =============================================================================


class AndonEventBase(BaseModel):
    event_number: str = Field(..., min_length=1, max_length=50)
    andon_type: AndonType
    severity: AndonSeverity = AndonSeverity.YELLOW
    station_id: int = Field(..., gt=0)
    product_id: Optional[int] = Field(default=None, gt=0)
    work_order_id: Optional[int] = Field(default=None, gt=0)
    symptom: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    affected_quantity: Optional[int] = Field(default=None, gt=0)
    photo_attachment_id: Optional[UUID] = None

    @field_validator("andon_type", mode="before")
    @classmethod
    def validate_andon_type(cls, v):
        return _parse_enum(AndonType, v, "andon_type")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        return _parse_enum(AndonSeverity, v, "severity")


class AndonEventCreate(AndonEventBase):
    pass


class AndonEventUpdate(BaseModel):
    andon_type: Optional[AndonType] = None
    severity: Optional[AndonSeverity] = None
    symptom: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    affected_quantity: Optional[int] = Field(default=None, gt=0)
    photo_attachment_id: Optional[UUID] = None
    root_cause_category: Optional[str] = Field(default=None, max_length=100)
    root_cause_notes: Optional[str] = None
    downtime_minutes: Optional[int] = Field(default=None, ge=0)
    estimated_cost_impact: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator("andon_type", mode="before")
    @classmethod
    def validate_andon_type(cls, v):
        return _parse_enum(AndonType, v, "andon_type")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        return _parse_enum(AndonSeverity, v, "severity")


class AndonAcknowledge(BaseModel):
    notes: Optional[str] = None


class AndonResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=1)
    resolution_category: Optional[str] = Field(default=None, max_length=100)
    downtime_minutes: Optional[int] = Field(default=None, ge=0)
    root_cause_category: Optional[str] = Field(default=None, max_length=100)
    root_cause_notes: Optional[str] = None


class AndonEscalate(BaseModel):
    escalation_level: EscalationLevel
    escalated_to_user_id: UUID
    notes: Optional[str] = None

    @field_validator("escalation_level", mode="before")
    @classmethod
    def validate_escalation_level(cls, v):
        return _parse_enum(EscalationLevel, v, "escalation_level")


class AndonEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_number: str
    andon_type: str
    severity: str
    station_id: int
    product_id: Optional[int]
    work_order_id: Optional[int]
    symptom: str
    description: Optional[str]
    affected_quantity: Optional[int]
    photo_attachment_id: Optional[UUID]
    status: str
    escalation_level: str
    reported_by_id: UUID
    reported_at: datetime
    acknowledged_by_id: Optional[UUID]
    acknowledged_at: Optional[datetime]
    resolved_by_id: Optional[UUID]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    resolution_category: Optional[str]
    escalated_to_a3_id: Optional[UUID]
    downtime_minutes: Optional[int]
    estimated_cost_impact: Optional[Decimal]
    root_cause_category: Optional[str]
    root_cause_notes: Optional[str]
    is_recurrence: bool
    related_event_id: Optional[int]
    recurrence_count: int
    created_at: datetime
    updated_at: datetime

    # Computed properties
    is_open: bool = False
    is_critical: bool = False
    response_time_minutes: Optional[int] = None
    resolution_time_minutes: Optional[int] = None
    elapsed_time_minutes: int = 0

    @classmethod
    def from_model(cls, event: AndonEvent) -> "AndonEventResponse":
        return cls(
            id=event.id,
            event_number=event.event_number,
            andon_type=event.andon_type.value,
            severity=event.severity.value,
            station_id=event.station_id,
            product_id=event.product_id,
            work_order_id=event.work_order_id,
            symptom=event.symptom,
            description=event.description,
            affected_quantity=event.affected_quantity,
            photo_attachment_id=event.photo_attachment_id,
            status=event.status.value,
            escalation_level=event.escalation_level.value,
            reported_by_id=event.reported_by_id,
            reported_at=event.reported_at,
            acknowledged_by_id=event.acknowledged_by_id,
            acknowledged_at=event.acknowledged_at,
            resolved_by_id=event.resolved_by_id,
            resolved_at=event.resolved_at,
            resolution_notes=event.resolution_notes,
            resolution_category=event.resolution_category,
            escalated_to_a3_id=event.escalated_to_a3_id,
            downtime_minutes=event.downtime_minutes,
            estimated_cost_impact=event.estimated_cost_impact,
            root_cause_category=event.root_cause_category,
            root_cause_notes=event.root_cause_notes,
            is_recurrence=event.is_recurrence,
            related_event_id=event.related_event_id,
            recurrence_count=event.recurrence_count,
            created_at=event.created_at,
            updated_at=event.updated_at,
            is_open=event.is_open,
            is_critical=event.is_critical,
            response_time_minutes=event.response_time_minutes,
            resolution_time_minutes=event.resolution_time_minutes,
            elapsed_time_minutes=event.elapsed_time_minutes,
        )


# =============================================================================
# Andon Escalation Schemas
# =============================================================================


class AndonEscalationCreate(BaseModel):
    andon_event_id: int = Field(..., gt=0)
    escalation_level: EscalationLevel
    escalated_to_user_id: UUID
    notes: Optional[str] = None

    @field_validator("escalation_level", mode="before")
    @classmethod
    def validate_escalation_level(cls, v):
        return _parse_enum(EscalationLevel, v, "escalation_level")


class AndonEscalationUpdate(BaseModel):
    response_status: Optional[ResponseStatus] = None
    response_notes: Optional[str] = None
    delegated_to_user_id: Optional[UUID] = None

    @field_validator("response_status", mode="before")
    @classmethod
    def validate_response_status(cls, v):
        return _parse_enum(ResponseStatus, v, "response_status")


class AndonEscalationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    andon_event_id: int
    escalation_level: str
    escalated_to_user_id: UUID
    escalated_at: datetime
    response_status: str
    responded_at: Optional[datetime]
    response_notes: Optional[str]
    delegated_to_user_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    response_time_minutes: Optional[int] = None

    @classmethod
    def from_model(cls, esc: AndonEscalation) -> "AndonEscalationResponse":
        return cls(
            id=esc.id,
            andon_event_id=esc.andon_event_id,
            escalation_level=esc.escalation_level.value,
            escalated_to_user_id=esc.escalated_to_user_id,
            escalated_at=esc.escalated_at,
            response_status=esc.response_status.value,
            responded_at=esc.responded_at,
            response_notes=esc.response_notes,
            delegated_to_user_id=esc.delegated_to_user_id,
            created_at=esc.created_at,
            updated_at=esc.updated_at,
            response_time_minutes=esc.response_time_minutes,
        )


# =============================================================================
# Andon Recurrence Pattern Schemas
# =============================================================================


class RecurrencePatternCreate(BaseModel):
    station_id: int = Field(..., gt=0)
    andon_type: AndonType
    symptom_pattern: str = Field(..., min_length=1, max_length=255)
    window_days: int = Field(default=7, gt=0)
    escalation_threshold: int = Field(default=3, gt=0)

    @field_validator("andon_type", mode="before")
    @classmethod
    def validate_andon_type(cls, v):
        return _parse_enum(AndonType, v, "andon_type")


class RecurrencePatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    andon_type: str
    symptom_pattern: str
    occurrence_count: int
    first_occurrence_at: datetime
    last_occurrence_at: datetime
    window_days: int
    escalation_threshold: int
    escalated_to_a3: bool
    a3_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    should_escalate: bool = False

    @classmethod
    def from_model(cls, pattern: AndonRecurrencePattern) -> "RecurrencePatternResponse":
        return cls(
            id=pattern.id,
            station_id=pattern.station_id,
            andon_type=pattern.andon_type.value,
            symptom_pattern=pattern.symptom_pattern,
            occurrence_count=pattern.occurrence_count,
            first_occurrence_at=pattern.first_occurrence_at,
            last_occurrence_at=pattern.last_occurrence_at,
            window_days=pattern.window_days,
            escalation_threshold=pattern.escalation_threshold,
            escalated_to_a3=pattern.escalated_to_a3,
            a3_id=pattern.a3_id,
            created_at=pattern.created_at,
            updated_at=pattern.updated_at,
            should_escalate=pattern.should_escalate,
        )


# =============================================================================
# Andon Event Endpoints
# =============================================================================


@router.get("", response_model=PaginatedResponse[AndonEventResponse])
async def list_andon_events(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    station_id: Optional[int] = None,
    product_id: Optional[int] = None,
    work_order_id: Optional[int] = None,
    andon_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    is_open: Optional[bool] = None,
    search: Optional[str] = None,
    include_deleted: bool = False,
) -> PaginatedResponse[AndonEventResponse]:
    """List Andon events with filters."""
    query = select(AndonEvent)

    if not include_deleted:
        query = query.where(AndonEvent.deleted_at.is_(None))

    if station_id:
        query = query.where(AndonEvent.station_id == station_id)
    if product_id:
        query = query.where(AndonEvent.product_id == product_id)
    if work_order_id:
        query = query.where(AndonEvent.work_order_id == work_order_id)
    if andon_type:
        query = query.where(AndonEvent.andon_type == _parse_enum(AndonType, andon_type, "andon_type"))
    if severity:
        query = query.where(AndonEvent.severity == _parse_enum(AndonSeverity, severity, "severity"))
    if status:
        query = query.where(AndonEvent.status == _parse_enum(AndonStatus, status, "status"))
    if is_open is True:
        query = query.where(
            AndonEvent.status.in_([AndonStatus.OPEN, AndonStatus.ACKNOWLEDGED, AndonStatus.IN_PROGRESS])
        )
    elif is_open is False:
        query = query.where(
            AndonEvent.status.in_([AndonStatus.RESOLVED, AndonStatus.ESCALATED, AndonStatus.CANCELLED])
        )
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                AndonEvent.event_number.ilike(search_term),
                AndonEvent.symptom.ilike(search_term),
                AndonEvent.description.ilike(search_term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AndonEvent.reported_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    return build_paginated_response(
        data=[AndonEventResponse.from_model(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=APIResponse[AndonEventResponse], status_code=201)
async def create_andon_event(
    data: AndonEventCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Report a new Andon event (STOP signal)."""
    # Check for duplicate event number
    existing = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.event_number == data.event_number)
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Andon event with event_number {data.event_number} already exists")

    now = _now_utc()
    event = AndonEvent(
        event_number=data.event_number,
        andon_type=data.andon_type,
        severity=data.severity,
        station_id=data.station_id,
        product_id=data.product_id,
        work_order_id=data.work_order_id,
        symptom=data.symptom,
        description=data.description,
        affected_quantity=data.affected_quantity,
        photo_attachment_id=data.photo_attachment_id,
        status=AndonStatus.OPEN,
        escalation_level=EscalationLevel.NONE,
        reported_by_id=current_user.id,
        reported_at=now,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    db.add(event)
    await db.flush()
    await db.refresh(event)

    # Check for recurrence pattern
    await _check_and_update_recurrence(db, event)

    await db.commit()
    await db.refresh(event)

    return build_created_response(AndonEventResponse.from_model(event))


@router.get("/{event_id}", response_model=APIResponse[AndonEventResponse])
async def get_andon_event(
    event_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Get an Andon event by ID."""
    event = (
        await db.execute(
            select(AndonEvent)
            .where(AndonEvent.id == event_id)
            .options(selectinload(AndonEvent.escalations))
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)
    return build_response(AndonEventResponse.from_model(event))


@router.patch("/{event_id}", response_model=APIResponse[AndonEventResponse])
async def update_andon_event(
    event_id: int,
    data: AndonEventUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Update an Andon event."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    event.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(event)

    return build_updated_response(AndonEventResponse.from_model(event))


@router.delete("/{event_id}", response_model=APIResponse[None])
async def delete_andon_event(
    event_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    """Soft-delete an Andon event."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    event.deleted_at = _now_utc()
    event.deleted_by_id = current_user.id
    await db.commit()

    return build_deleted_response()


@router.post("/{event_id}/restore", response_model=APIResponse[AndonEventResponse])
async def restore_andon_event(
    event_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Restore a soft-deleted Andon event."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    event.deleted_at = None
    event.deleted_by_id = None
    event.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(event)

    return build_response(AndonEventResponse.from_model(event))


# =============================================================================
# Andon Workflow Endpoints
# =============================================================================


@router.post("/{event_id}/acknowledge", response_model=APIResponse[AndonEventResponse])
async def acknowledge_andon_event(
    event_id: int,
    data: AndonAcknowledge,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Acknowledge an Andon event (CALL response)."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    if event.status != AndonStatus.OPEN:
        raise ConflictError(f"Cannot acknowledge event in status: {event.status.value}")

    now = _now_utc()
    event.status = AndonStatus.ACKNOWLEDGED
    event.acknowledged_by_id = current_user.id
    event.acknowledged_at = now
    event.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(event)

    return build_response(AndonEventResponse.from_model(event))


@router.post("/{event_id}/start-progress", response_model=APIResponse[AndonEventResponse])
async def start_andon_progress(
    event_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Mark Andon event as in-progress."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    if event.status not in [AndonStatus.OPEN, AndonStatus.ACKNOWLEDGED]:
        raise ConflictError(
            f"Cannot start progress on event in status: {event.status.value}"
        )

    now = _now_utc()
    event.status = AndonStatus.IN_PROGRESS
    if not event.acknowledged_at:
        event.acknowledged_by_id = current_user.id
        event.acknowledged_at = now
    event.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(event)

    return build_response(AndonEventResponse.from_model(event))


@router.post("/{event_id}/resolve", response_model=APIResponse[AndonEventResponse])
async def resolve_andon_event(
    event_id: int,
    data: AndonResolve,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Resolve an Andon event."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    if event.status in [AndonStatus.RESOLVED, AndonStatus.CANCELLED]:
        raise ConflictError(
            f"Cannot resolve event in status: {event.status.value}"
        )

    now = _now_utc()
    event.status = AndonStatus.RESOLVED
    event.resolved_by_id = current_user.id
    event.resolved_at = now
    event.resolution_notes = data.resolution_notes
    event.resolution_category = data.resolution_category
    if data.downtime_minutes is not None:
        event.downtime_minutes = data.downtime_minutes
    if data.root_cause_category:
        event.root_cause_category = data.root_cause_category
    if data.root_cause_notes:
        event.root_cause_notes = data.root_cause_notes
    event.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(event)

    return build_response(AndonEventResponse.from_model(event))


@router.post("/{event_id}/cancel", response_model=APIResponse[AndonEventResponse])
async def cancel_andon_event(
    event_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Cancel an Andon event (false alarm)."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    if event.status == AndonStatus.RESOLVED:
        raise ConflictError("Cannot cancel a resolved event")

    event.status = AndonStatus.CANCELLED
    event.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(event)

    return build_response(AndonEventResponse.from_model(event))


@router.post("/{event_id}/escalate", response_model=APIResponse[AndonEventResponse])
async def escalate_andon_event(
    event_id: int,
    data: AndonEscalate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEventResponse]:
    """Escalate an Andon event to a higher level."""
    event = (
        await db.execute(
            select(AndonEvent)
            .where(AndonEvent.id == event_id)
            .options(selectinload(AndonEvent.escalations))
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    if event.status in [AndonStatus.RESOLVED, AndonStatus.CANCELLED]:
        raise ConflictError(
            f"Cannot escalate event in status: {event.status.value}"
        )

    # Check if this escalation level already exists
    existing_esc = next(
        (e for e in event.escalations if e.escalation_level == data.escalation_level),
        None
    )
    if existing_esc:
        raise ConflictError(
            f"Already escalated to {data.escalation_level.value}"
        )

    now = _now_utc()
    escalation = AndonEscalation(
        andon_event_id=event.id,
        escalation_level=data.escalation_level,
        escalated_to_user_id=data.escalated_to_user_id,
        escalated_at=now,
        response_status=ResponseStatus.PENDING,
    )
    db.add(escalation)

    event.escalation_level = data.escalation_level
    if event.status == AndonStatus.OPEN:
        event.status = AndonStatus.ESCALATED
    event.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(event)

    return build_response(AndonEventResponse.from_model(event))


# =============================================================================
# Andon Escalation Endpoints
# =============================================================================


@router.get("/{event_id}/escalations", response_model=APIResponse[list[AndonEscalationResponse]])
async def list_event_escalations(
    event_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[AndonEscalationResponse]]:
    """List all escalations for an Andon event."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", event_id)

    result = await db.execute(
        select(AndonEscalation)
        .where(AndonEscalation.andon_event_id == event_id)
        .order_by(AndonEscalation.escalated_at)
    )
    escalations = result.scalars().all()

    return build_response([AndonEscalationResponse.from_model(e) for e in escalations])


@router.post("/escalations", response_model=APIResponse[AndonEscalationResponse], status_code=201)
async def create_escalation(
    data: AndonEscalationCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEscalationResponse]:
    """Create a new escalation for an Andon event."""
    event = (
        await db.execute(
            select(AndonEvent).where(AndonEvent.id == data.andon_event_id)
        )
    ).scalar_one_or_none()
    if not event:
        raise NotFoundError("Andon event", data.andon_event_id)

    # Check for existing escalation at this level
    existing = (
        await db.execute(
            select(AndonEscalation).where(
                and_(
                    AndonEscalation.andon_event_id == data.andon_event_id,
                    AndonEscalation.escalation_level == data.escalation_level,
                )
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"Already escalated to {data.escalation_level.value}"
        )

    now = _now_utc()
    escalation = AndonEscalation(
        andon_event_id=data.andon_event_id,
        escalation_level=data.escalation_level,
        escalated_to_user_id=data.escalated_to_user_id,
        escalated_at=now,
        response_status=ResponseStatus.PENDING,
    )
    db.add(escalation)

    event.escalation_level = data.escalation_level
    event.updated_by_id = current_user.id

    await db.flush()
    await db.refresh(escalation)
    await db.commit()

    return build_created_response(AndonEscalationResponse.from_model(escalation))


@router.patch("/escalations/{escalation_id}", response_model=APIResponse[AndonEscalationResponse])
async def update_escalation(
    escalation_id: int,
    data: AndonEscalationUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AndonEscalationResponse]:
    """Update an escalation (respond, delegate, etc.)."""
    escalation = (
        await db.execute(
            select(AndonEscalation).where(AndonEscalation.id == escalation_id)
        )
    ).scalar_one_or_none()
    if not escalation:
        raise NotFoundError("Andon escalation", escalation_id)

    update_data = data.model_dump(exclude_unset=True)

    if "response_status" in update_data:
        update_data["responded_at"] = _now_utc()

    for field, value in update_data.items():
        setattr(escalation, field, value)

    await db.commit()
    await db.refresh(escalation)

    return build_updated_response(AndonEscalationResponse.from_model(escalation))


@router.delete("/escalations/{escalation_id}", response_model=APIResponse[None])
async def delete_escalation(
    escalation_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    """Delete an escalation."""
    escalation = (
        await db.execute(
            select(AndonEscalation).where(AndonEscalation.id == escalation_id)
        )
    ).scalar_one_or_none()
    if not escalation:
        raise NotFoundError("Andon escalation", escalation_id)

    await db.delete(escalation)
    await db.commit()

    return build_deleted_response()


# =============================================================================
# Andon Recurrence Pattern Endpoints
# =============================================================================


@router.get("/recurrence-patterns", response_model=PaginatedResponse[RecurrencePatternResponse])
async def list_recurrence_patterns(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    station_id: Optional[int] = None,
    andon_type: Optional[str] = None,
    escalated: Optional[bool] = None,
) -> PaginatedResponse[RecurrencePatternResponse]:
    """List Andon recurrence patterns."""
    query = select(AndonRecurrencePattern)

    if station_id:
        query = query.where(AndonRecurrencePattern.station_id == station_id)
    if andon_type:
        query = query.where(
            AndonRecurrencePattern.andon_type == _parse_enum(AndonType, andon_type, "andon_type")
        )
    if escalated is not None:
        query = query.where(AndonRecurrencePattern.escalated_to_a3 == escalated)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AndonRecurrencePattern.last_occurrence_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    patterns = result.scalars().all()

    return build_paginated_response(
        data=[RecurrencePatternResponse.from_model(p) for p in patterns],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/recurrence-patterns/{pattern_id}", response_model=APIResponse[RecurrencePatternResponse])
async def get_recurrence_pattern(
    pattern_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RecurrencePatternResponse]:
    """Get a recurrence pattern by ID."""
    pattern = (
        await db.execute(
            select(AndonRecurrencePattern).where(AndonRecurrencePattern.id == pattern_id)
        )
    ).scalar_one_or_none()
    if not pattern:
        raise NotFoundError("Andon recurrence pattern", pattern_id)
    return build_response(RecurrencePatternResponse.from_model(pattern))


@router.post("/recurrence-patterns", response_model=APIResponse[RecurrencePatternResponse], status_code=201)
async def create_recurrence_pattern(
    data: RecurrencePatternCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[RecurrencePatternResponse]:
    """Create a recurrence pattern manually."""
    # Check for existing pattern
    existing = (
        await db.execute(
            select(AndonRecurrencePattern).where(
                and_(
                    AndonRecurrencePattern.station_id == data.station_id,
                    AndonRecurrencePattern.andon_type == data.andon_type,
                    AndonRecurrencePattern.symptom_pattern == data.symptom_pattern,
                )
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(
            "Pattern already exists for this station/type/symptom combination"
        )

    now = _now_utc()
    pattern = AndonRecurrencePattern(
        station_id=data.station_id,
        andon_type=data.andon_type,
        symptom_pattern=data.symptom_pattern,
        occurrence_count=1,
        first_occurrence_at=now,
        last_occurrence_at=now,
        window_days=data.window_days,
        escalation_threshold=data.escalation_threshold,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(pattern)
    await db.flush()
    await db.refresh(pattern)
    await db.commit()

    return build_created_response(RecurrencePatternResponse.from_model(pattern))


@router.delete("/recurrence-patterns/{pattern_id}", response_model=APIResponse[None])
async def delete_recurrence_pattern(
    pattern_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    """Delete a recurrence pattern."""
    pattern = (
        await db.execute(
            select(AndonRecurrencePattern).where(AndonRecurrencePattern.id == pattern_id)
        )
    ).scalar_one_or_none()
    if not pattern:
        raise NotFoundError("Andon recurrence pattern", pattern_id)

    await db.delete(pattern)
    await db.commit()

    return build_deleted_response()


@router.post("/recurrence-patterns/{pattern_id}/mark-escalated", response_model=APIResponse[RecurrencePatternResponse])
async def mark_pattern_escalated(
    pattern_id: int,
    a3_id: Optional[UUID] = None,
    db: DBSession = None,
    current_user: CurrentUser = None,
) -> APIResponse[RecurrencePatternResponse]:
    """Mark a recurrence pattern as escalated to A3."""
    pattern = (
        await db.execute(
            select(AndonRecurrencePattern).where(AndonRecurrencePattern.id == pattern_id)
        )
    ).scalar_one_or_none()
    if not pattern:
        raise NotFoundError("Andon recurrence pattern", pattern_id)

    pattern.escalated_to_a3 = True
    pattern.a3_id = a3_id
    pattern.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(pattern)

    return build_response(RecurrencePatternResponse.from_model(pattern))


# =============================================================================
# Dashboard/Metrics Endpoints
# =============================================================================


class AndonDashboardStats(BaseModel):
    total_open: int = 0
    total_red: int = 0
    total_yellow: int = 0
    total_blue: int = 0
    avg_response_time_minutes: Optional[float] = None
    avg_resolution_time_minutes: Optional[float] = None
    events_by_type: dict[str, int] = {}
    events_by_station: dict[int, int] = {}


@router.get("/dashboard/stats", response_model=APIResponse[AndonDashboardStats])
async def get_dashboard_stats(
    db: DBSession,
    current_user: CurrentUser,
    days: int = Query(default=7, ge=1, le=365),
) -> APIResponse[AndonDashboardStats]:
    """Get Andon dashboard statistics."""
    cutoff = _now_utc() - timedelta(days=days)

    # Open events by severity
    open_statuses = [AndonStatus.OPEN, AndonStatus.ACKNOWLEDGED, AndonStatus.IN_PROGRESS]

    total_open = (await db.execute(
        select(func.count())
        .select_from(AndonEvent)
        .where(AndonEvent.status.in_(open_statuses))
        .where(AndonEvent.deleted_at.is_(None))
    )).scalar() or 0

    total_red = (await db.execute(
        select(func.count())
        .select_from(AndonEvent)
        .where(AndonEvent.status.in_(open_statuses))
        .where(AndonEvent.severity == AndonSeverity.RED)
        .where(AndonEvent.deleted_at.is_(None))
    )).scalar() or 0

    total_yellow = (await db.execute(
        select(func.count())
        .select_from(AndonEvent)
        .where(AndonEvent.status.in_(open_statuses))
        .where(AndonEvent.severity == AndonSeverity.YELLOW)
        .where(AndonEvent.deleted_at.is_(None))
    )).scalar() or 0

    total_blue = (await db.execute(
        select(func.count())
        .select_from(AndonEvent)
        .where(AndonEvent.status.in_(open_statuses))
        .where(AndonEvent.severity == AndonSeverity.BLUE)
        .where(AndonEvent.deleted_at.is_(None))
    )).scalar() or 0

    # Events by type
    type_result = await db.execute(
        select(AndonEvent.andon_type, func.count())
        .where(AndonEvent.reported_at >= cutoff)
        .where(AndonEvent.deleted_at.is_(None))
        .group_by(AndonEvent.andon_type)
    )
    events_by_type = {str(row[0].value): row[1] for row in type_result.all()}

    # Events by station
    station_result = await db.execute(
        select(AndonEvent.station_id, func.count())
        .where(AndonEvent.reported_at >= cutoff)
        .where(AndonEvent.deleted_at.is_(None))
        .group_by(AndonEvent.station_id)
    )
    events_by_station = {row[0]: row[1] for row in station_result.all()}

    return build_response(AndonDashboardStats(
        total_open=total_open,
        total_red=total_red,
        total_yellow=total_yellow,
        total_blue=total_blue,
        events_by_type=events_by_type,
        events_by_station=events_by_station,
    ))


# =============================================================================
# Helper Functions
# =============================================================================


async def _check_and_update_recurrence(db: DBSession, event: AndonEvent) -> None:
    """Check if this event matches an existing recurrence pattern and update it."""
    # Look for existing pattern
    pattern = (
        await db.execute(
            select(AndonRecurrencePattern).where(
                and_(
                    AndonRecurrencePattern.station_id == event.station_id,
                    AndonRecurrencePattern.andon_type == event.andon_type,
                    AndonRecurrencePattern.symptom_pattern == event.symptom,
                )
            )
        )
    ).scalar_one_or_none()

    now = _now_utc()

    if pattern:
        # Check if within window
        window_start = now - timedelta(days=pattern.window_days)
        if pattern.last_occurrence_at >= window_start:
            pattern.occurrence_count += 1
            pattern.last_occurrence_at = now
            event.is_recurrence = True
            event.recurrence_count = pattern.occurrence_count
        else:
            # Reset the pattern
            pattern.occurrence_count = 1
            pattern.first_occurrence_at = now
            pattern.last_occurrence_at = now
    else:
        # Create new pattern
        pattern = AndonRecurrencePattern(
            station_id=event.station_id,
            andon_type=event.andon_type,
            symptom_pattern=event.symptom,
            occurrence_count=1,
            first_occurrence_at=now,
            last_occurrence_at=now,
            created_by_id=event.created_by_id,
            updated_by_id=event.updated_by_id,
        )
        db.add(pattern)

    await db.flush()
