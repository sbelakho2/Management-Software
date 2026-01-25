"""
Notification Triggers API endpoints.

Provides REST API for managing notification triggers,
evaluating conditions, and managing snooze settings.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sensei.core.config import settings
from sensei.services.core.notification_triggers import (
    NotificationTriggersService,
    NotificationTriggersJobRunner,
    TriggerType,
    TriggerCondition,
    TriggerEvaluationResult,
    GeneratedNotification,
    NotificationTarget,
    RecipientRole,
    NotificationChannel,
    NotificationPriority,
    SnoozeStatus,
)

def _deny_production() -> None:
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(_deny_production)],
)

# --------------------------------------------------------------------------
# Service Instance (in production, would be dependency injected)
# --------------------------------------------------------------------------

_service = NotificationTriggersService()
_runner = NotificationTriggersJobRunner(service=_service)


def get_service() -> NotificationTriggersService:
    """Get the notification triggers service."""
    return _service


def get_runner() -> NotificationTriggersJobRunner:
    """Get the job runner."""
    return _runner


# --------------------------------------------------------------------------
# Request/Response Schemas
# --------------------------------------------------------------------------

class TaskInput(BaseModel):
    """Task input for evaluation."""
    
    id: str
    title: str
    due_date: str | None = None
    status: str = "pending"
    owner_id: str | None = None
    assignee_id: str | None = None
    manager_id: str | None = None


class RFQInput(BaseModel):
    """RFQ input for evaluation."""
    
    id: str
    rfq_number: str | None = None
    title: str | None = None
    status: str = "open"
    updated_at: str | None = None
    last_activity_at: str | None = None
    completeness_score: int | None = None
    missing_fields: list[str] | None = None
    owner_id: str | None = None
    manager_id: str | None = None


class QuoteInput(BaseModel):
    """Quote input for evaluation."""
    
    id: str
    quote_number: str | None = None
    status: str = "draft"
    margin_percent: float | None = None
    gross_margin: float | None = None
    total_value: float | None = None
    submitted_for_approval_at: str | None = None
    updated_at: str | None = None
    owner_id: str | None = None
    approver_id: str | None = None
    manager_id: str | None = None


class CertificationInput(BaseModel):
    """Certification input for evaluation."""
    
    id: str
    user_id: str
    skill_name: str
    expires_at: str | None = None
    expiration_date: str | None = None


class UserInput(BaseModel):
    """User input for recipient lookup."""
    
    user_id: str
    role: str = "owner"
    email: str | None = None
    name: str | None = None


class EvaluateTriggersRequest(BaseModel):
    """Request to evaluate triggers."""
    
    tasks: list[TaskInput] | None = None
    rfqs: list[RFQInput] | None = None
    quotes: list[QuoteInput] | None = None
    certifications: list[CertificationInput] | None = None
    users: list[UserInput] | None = None
    reference_date: str | None = None


class GeneratedNotificationResponse(BaseModel):
    """Response for a generated notification."""
    
    id: str
    trigger_type: str
    title: str
    message: str
    priority: str
    recipient_id: str | None = None
    recipient_role: str
    entity_type: str | None = None
    entity_id: str | None = None
    action_url: str | None = None
    channels: list[str]
    generated_at: str
    snooze_status: str
    extra_data: dict[str, Any] | None = None


class EvaluationResultResponse(BaseModel):
    """Response for trigger evaluation."""
    
    notifications: list[GeneratedNotificationResponse]
    triggers_checked: int
    triggers_fired: int
    entities_scanned: int
    evaluation_time_ms: float
    errors: list[str]


class TriggerConditionResponse(BaseModel):
    """Response for a trigger condition."""
    
    trigger_type: str
    name: str
    description: str
    recipients: list[str]
    channels: list[str]
    priority: str
    check_interval_minutes: int
    cooldown_minutes: int
    days_before_due: int | None = None
    days_overdue: int | None = None
    margin_threshold: float | None = None
    occurrence_count: int | None = None
    is_enabled: bool


class TriggerUpdateRequest(BaseModel):
    """Request to update a trigger."""
    
    is_enabled: bool | None = None
    recipients: list[str] | None = None
    channels: list[str] | None = None
    priority: str | None = None
    check_interval_minutes: int | None = None
    cooldown_minutes: int | None = None
    days_before_due: int | None = None
    days_overdue: int | None = None
    margin_threshold: float | None = None
    occurrence_count: int | None = None


class SnoozeRequest(BaseModel):
    """Request to snooze notifications."""
    
    user_id: str
    trigger_type: str | None = None
    entity_key: str | None = None
    snooze_hours: int = 24


class AcknowledgeRequest(BaseModel):
    """Request to acknowledge an entity."""
    
    user_id: str
    entity_key: str


class ClearSnoozeRequest(BaseModel):
    """Request to clear snooze settings."""
    
    user_id: str
    trigger_type: str | None = None
    entity_key: str | None = None


class SnoozeSettingsResponse(BaseModel):
    """Response for user snooze settings."""
    
    user_id: str
    global_snooze_until: str | None = None
    trigger_snoozes: dict[str, str]
    entity_snoozes: dict[str, str]
    acknowledged_entities: list[str]


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _parse_uuid(value: str) -> UUID | None:
    """Parse a UUID string, returning None if invalid."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


def _build_users_map(users: list[UserInput] | None) -> dict[UUID, NotificationTarget]:
    """Build a users lookup map from input."""
    if not users:
        return {}
    
    result = {}
    for u in users:
        user_id = _parse_uuid(u.user_id)
        if user_id:
            try:
                role = RecipientRole(u.role)
            except ValueError:
                role = RecipientRole.OWNER
            result[user_id] = NotificationTarget(
                user_id=user_id,
                role=role,
                email=u.email,
                name=u.name,
            )
    return result


def _notification_to_response(notif: GeneratedNotification) -> GeneratedNotificationResponse:
    """Convert a GeneratedNotification to response."""
    return GeneratedNotificationResponse(
        id=notif.id,
        trigger_type=notif.trigger_type.value,
        title=notif.title,
        message=notif.message,
        priority=notif.priority.value,
        recipient_id=str(notif.recipient_id) if notif.recipient_id else None,
        recipient_role=notif.recipient_role.value,
        entity_type=notif.entity_type,
        entity_id=notif.entity_id,
        action_url=notif.action_url,
        channels=[c.value for c in notif.channels],
        generated_at=notif.generated_at.isoformat() if notif.generated_at else "",
        snooze_status=notif.snooze_status.value,
        extra_data=notif.extra_data,
    )


def _trigger_to_response(trigger: TriggerCondition) -> TriggerConditionResponse:
    """Convert a TriggerCondition to response."""
    return TriggerConditionResponse(
        trigger_type=trigger.trigger_type.value,
        name=trigger.name,
        description=trigger.description,
        recipients=[r.value for r in trigger.recipients],
        channels=[c.value for c in trigger.channels],
        priority=trigger.priority.value,
        check_interval_minutes=trigger.check_interval_minutes,
        cooldown_minutes=trigger.cooldown_minutes,
        days_before_due=trigger.days_before_due,
        days_overdue=trigger.days_overdue,
        margin_threshold=trigger.margin_threshold,
        occurrence_count=trigger.occurrence_count,
        is_enabled=trigger.is_enabled,
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.post("/evaluate", response_model=EvaluationResultResponse)
async def evaluate_triggers(
    request: EvaluateTriggersRequest,
) -> EvaluationResultResponse:
    """
    Evaluate notification triggers against provided data.
    
    Checks all enabled triggers and returns generated notifications.
    """
    service = get_service()
    users_map = _build_users_map(request.users)
    
    # Parse reference date
    ref_date = None
    if request.reference_date:
        try:
            ref_date = datetime.fromisoformat(
                request.reference_date.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reference_date format",
            )
    
    if ref_date is None:
        ref_date = datetime.now(timezone.utc).replace(tzinfo=None)
    
    notifications: list[GeneratedNotification] = []
    entities_scanned = 0
    triggers_checked = 0
    
    # Evaluate tasks
    if request.tasks:
        task_dicts = [t.model_dump() for t in request.tasks]
        entities_scanned += len(task_dicts)
        triggers_checked += 2
        notifications.extend(service.evaluate_tasks(task_dicts, users_map, ref_date))
    
    # Evaluate RFQs
    if request.rfqs:
        rfq_dicts = [r.model_dump() for r in request.rfqs]
        entities_scanned += len(rfq_dicts)
        triggers_checked += 2
        notifications.extend(service.evaluate_rfqs(rfq_dicts, users_map, ref_date))
    
    # Evaluate quotes
    if request.quotes:
        quote_dicts = [q.model_dump() for q in request.quotes]
        entities_scanned += len(quote_dicts)
        triggers_checked += 3
        notifications.extend(service.evaluate_quotes(quote_dicts, users_map, ref_date))
    
    # Evaluate certifications
    if request.certifications:
        cert_dicts = [c.model_dump() for c in request.certifications]
        entities_scanned += len(cert_dicts)
        triggers_checked += 1
        notifications.extend(service.evaluate_certifications(cert_dicts, users_map, ref_date))
    
    return EvaluationResultResponse(
        notifications=[_notification_to_response(n) for n in notifications],
        triggers_checked=triggers_checked,
        triggers_fired=len(notifications),
        entities_scanned=entities_scanned,
        evaluation_time_ms=0.0,
        errors=[],
    )


@router.get("/triggers", response_model=list[TriggerConditionResponse])
async def list_triggers() -> list[TriggerConditionResponse]:
    """
    List all registered notification triggers.
    """
    service = get_service()
    triggers = service.get_all_triggers()
    return [_trigger_to_response(t) for t in triggers]


@router.get("/triggers/{trigger_type}", response_model=TriggerConditionResponse)
async def get_trigger(
    trigger_type: str,
) -> TriggerConditionResponse:
    """
    Get a specific trigger by type.
    """
    service = get_service()
    
    try:
        tt = TriggerType(trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {trigger_type}",
        )
    
    trigger = service.get_trigger(tt)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_type}",
        )
    
    return _trigger_to_response(trigger)


@router.put("/triggers/{trigger_type}", response_model=TriggerConditionResponse)
async def update_trigger(
    trigger_type: str,
    request: TriggerUpdateRequest,
) -> TriggerConditionResponse:
    """
    Update a trigger's settings.
    """
    service = get_service()
    
    try:
        tt = TriggerType(trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {trigger_type}",
        )
    
    trigger = service.get_trigger(tt)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_type}",
        )
    
    # Update fields
    if request.is_enabled is not None:
        trigger.is_enabled = request.is_enabled
    
    if request.recipients is not None:
        try:
            trigger.recipients = [RecipientRole(r) for r in request.recipients]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid recipient role: {e}",
            )
    
    if request.channels is not None:
        try:
            trigger.channels = [NotificationChannel(c) for c in request.channels]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channel: {e}",
            )
    
    if request.priority is not None:
        try:
            trigger.priority = NotificationPriority(request.priority)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority: {request.priority}",
            )
    
    if request.check_interval_minutes is not None:
        trigger.check_interval_minutes = request.check_interval_minutes
    
    if request.cooldown_minutes is not None:
        trigger.cooldown_minutes = request.cooldown_minutes
    
    if request.days_before_due is not None:
        trigger.days_before_due = request.days_before_due
    
    if request.days_overdue is not None:
        trigger.days_overdue = request.days_overdue
    
    if request.margin_threshold is not None:
        trigger.margin_threshold = request.margin_threshold
    
    if request.occurrence_count is not None:
        trigger.occurrence_count = request.occurrence_count
    
    return _trigger_to_response(trigger)


@router.post("/triggers/{trigger_type}/enable")
async def enable_trigger(trigger_type: str) -> dict[str, Any]:
    """
    Enable a trigger.
    """
    service = get_service()
    
    try:
        tt = TriggerType(trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {trigger_type}",
        )
    
    result = service.enable_trigger(tt)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_type}",
        )
    
    return {"trigger_type": trigger_type, "is_enabled": True}


@router.post("/triggers/{trigger_type}/disable")
async def disable_trigger(trigger_type: str) -> dict[str, Any]:
    """
    Disable a trigger.
    """
    service = get_service()
    
    try:
        tt = TriggerType(trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {trigger_type}",
        )
    
    result = service.disable_trigger(tt)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger not found: {trigger_type}",
        )
    
    return {"trigger_type": trigger_type, "is_enabled": False}


@router.get("/trigger-types")
async def list_trigger_types() -> list[dict[str, str]]:
    """
    List all available trigger types.
    """
    return [
        {"value": tt.value, "name": tt.name}
        for tt in TriggerType
    ]


@router.get("/recipient-roles")
async def list_recipient_roles() -> list[dict[str, str]]:
    """
    List all available recipient roles.
    """
    return [
        {"value": r.value, "name": r.name}
        for r in RecipientRole
    ]


@router.get("/channels")
async def list_channels() -> list[dict[str, str]]:
    """
    List all available notification channels.
    """
    return [
        {"value": c.value, "name": c.name}
        for c in NotificationChannel
    ]


@router.get("/priorities")
async def list_priorities() -> list[dict[str, str]]:
    """
    List all available notification priorities.
    """
    return [
        {"value": p.value, "name": p.name}
        for p in NotificationPriority
    ]


# --------------------------------------------------------------------------
# Snooze Endpoints
# --------------------------------------------------------------------------

@router.post("/snooze")
async def snooze_notifications(request: SnoozeRequest) -> dict[str, Any]:
    """
    Snooze notifications for a user.
    
    Can snooze globally, by trigger type, or by specific entity.
    """
    service = get_service()
    
    user_id = _parse_uuid(request.user_id)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id",
        )
    
    trigger_type = None
    if request.trigger_type:
        try:
            trigger_type = TriggerType(request.trigger_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trigger type: {request.trigger_type}",
            )
    
    service.snooze_for_user(
        user_id=user_id,
        trigger_type=trigger_type,
        entity_key=request.entity_key,
        snooze_hours=request.snooze_hours,
    )
    
    snooze_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=request.snooze_hours)
    
    return {
        "user_id": str(user_id),
        "snooze_until": snooze_until.isoformat(),
        "trigger_type": request.trigger_type,
        "entity_key": request.entity_key,
    }


@router.post("/acknowledge")
async def acknowledge_entity(request: AcknowledgeRequest) -> dict[str, Any]:
    """
    Acknowledge an entity to stop notifications permanently.
    """
    service = get_service()
    
    user_id = _parse_uuid(request.user_id)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id",
        )
    
    service.acknowledge_entity(user_id, request.entity_key)
    
    return {
        "user_id": str(user_id),
        "entity_key": request.entity_key,
        "acknowledged": True,
    }


@router.post("/clear-snooze")
async def clear_snooze(request: ClearSnoozeRequest) -> dict[str, Any]:
    """
    Clear snooze settings for a user.
    """
    service = get_service()
    
    user_id = _parse_uuid(request.user_id)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id",
        )
    
    trigger_type = None
    if request.trigger_type:
        try:
            trigger_type = TriggerType(request.trigger_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trigger type: {request.trigger_type}",
            )
    
    service.clear_snooze(
        user_id=user_id,
        trigger_type=trigger_type,
        entity_key=request.entity_key,
    )
    
    return {
        "user_id": str(user_id),
        "trigger_type": request.trigger_type,
        "entity_key": request.entity_key,
        "cleared": True,
    }


@router.get("/snooze/{user_id}", response_model=SnoozeSettingsResponse)
async def get_snooze_settings(user_id: str) -> SnoozeSettingsResponse:
    """
    Get snooze settings for a user.
    """
    service = get_service()
    
    uid = _parse_uuid(user_id)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id",
        )
    
    settings = service.get_user_snooze_settings(uid)
    
    return SnoozeSettingsResponse(
        user_id=str(settings.user_id),
        global_snooze_until=settings.global_snooze_until.isoformat() if settings.global_snooze_until else None,
        trigger_snoozes={k: v.isoformat() for k, v in settings.trigger_snoozes.items()},
        entity_snoozes={k: v.isoformat() for k, v in settings.entity_snoozes.items()},
        acknowledged_entities=list(settings.acknowledged_entities),
    )
