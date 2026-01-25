"""
LSW (Leader Standard Work) Scheduling API Endpoints.

Provides REST API for managing LSW checklists, templates, and compliance tracking.
"""

from datetime import datetime, date, time, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.core.config import settings
from sensei.services.production.lsw_scheduling import (
    LSWSchedulingService,
    LSWChecklistTemplate,
    LSWChecklistInstance,
    LSWChecklist,
    LSWReminder,
    LSWFrequency,
    LSWCategory,
    LSWItemStatus,
    DayOfWeek,
    build_lsw_template,
    get_default_template_ids,
)

def _deny_production() -> None:
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")


router = APIRouter(
    prefix="/lsw",
    tags=["LSW Scheduling"],
    dependencies=[Depends(_deny_production)],
)

# Global service instance
_service = LSWSchedulingService()


# --------------------------------------------------------------------------
# Request/Response Schemas
# --------------------------------------------------------------------------

class TemplateCreateRequest(BaseModel):
    """Request to create an LSW template."""
    
    id: str | None = None
    name: str
    description: str
    category: str  # LSWCategory value
    frequency: str  # LSWFrequency value
    estimated_duration_minutes: int = 15
    required: bool = True
    preferred_time: str | None = None  # HH:MM format
    days_of_week: list[str] = Field(default_factory=list)  # DayOfWeek values
    day_of_month: int | None = None
    week_of_month: int | None = None
    role_id: str | None = None
    owner_id: str | None = None
    requires_notes: bool = False
    requires_evidence: bool = False
    evidence_prompt: str = ""
    sub_items: list[str] = Field(default_factory=list)
    linked_area_id: str | None = None
    linked_kpi_id: str | None = None
    is_active: bool = True
    effective_from: date | None = None
    effective_until: date | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdateRequest(BaseModel):
    """Request to update an LSW template."""
    
    name: str | None = None
    description: str | None = None
    estimated_duration_minutes: int | None = None
    required: bool | None = None
    preferred_time: str | None = None
    days_of_week: list[str] | None = None
    day_of_month: int | None = None
    week_of_month: int | None = None
    requires_notes: bool | None = None
    requires_evidence: bool | None = None
    evidence_prompt: str | None = None
    sub_items: list[str] | None = None
    is_active: bool | None = None
    effective_from: date | None = None
    effective_until: date | None = None


class TemplateResponse(BaseModel):
    """LSW template response."""
    
    id: str
    name: str
    description: str
    category: str
    frequency: str
    estimated_duration_minutes: int
    required: bool
    preferred_time: str | None
    days_of_week: list[str]
    day_of_month: int | None
    week_of_month: int | None
    role_id: str | None
    owner_id: str | None
    requires_notes: bool
    requires_evidence: bool
    evidence_prompt: str
    sub_items: list[str]
    linked_area_id: str | None
    linked_kpi_id: str | None
    is_active: bool
    effective_from: date | None
    effective_until: date | None
    custom_fields: dict[str, Any]


class InstanceResponse(BaseModel):
    """LSW checklist instance response."""
    
    id: str
    template_id: str
    template_name: str
    scheduled_date: date
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    completed_by_id: str | None
    notes: str
    evidence_attachment_ids: list[str]
    sub_items_completed: list[str]
    skip_reason: str
    deferred_to: date | None
    actual_duration_minutes: int | None
    findings: list[dict[str, Any]]
    generated_task_ids: list[str]
    generated_a3_ids: list[str]


class ChecklistResponse(BaseModel):
    """LSW checklist response."""
    
    id: str
    owner_id: str
    date: date
    items: list[InstanceResponse]
    created_at: datetime
    total_items: int
    completed_count: int
    skipped_count: int
    overdue_count: int
    total_estimated_minutes: int
    total_actual_minutes: int


class GenerationResultResponse(BaseModel):
    """Checklist generation result response."""
    
    date: date
    owner_id: str
    generated_count: int
    items: list[InstanceResponse]


class CompleteItemRequest(BaseModel):
    """Request to complete an item."""
    
    completed_by_id: str
    notes: str = ""
    evidence_attachment_ids: list[str] = Field(default_factory=list)
    actual_duration_minutes: int | None = None
    findings: list[dict[str, Any]] = Field(default_factory=list)


class SkipItemRequest(BaseModel):
    """Request to skip an item."""
    
    reason: str


class DeferItemRequest(BaseModel):
    """Request to defer an item."""
    
    defer_to: date
    reason: str = ""


class AddFindingRequest(BaseModel):
    """Request to add a finding."""
    
    finding: dict[str, Any]


class ComplianceStatsResponse(BaseModel):
    """Compliance statistics response."""
    
    owner_id: str
    start_date: str
    end_date: str
    total_items: int
    completed: int
    skipped: int
    pending: int
    completion_rate: float
    on_time_rate: float
    by_category: dict[str, dict[str, int]]


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def _template_to_response(template: LSWChecklistTemplate) -> TemplateResponse:
    """Convert template to response."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category.value,
        frequency=template.frequency.value,
        estimated_duration_minutes=template.estimated_duration_minutes,
        required=template.required,
        preferred_time=template.preferred_time.strftime("%H:%M") if template.preferred_time else None,
        days_of_week=[d.value for d in template.days_of_week],
        day_of_month=template.day_of_month,
        week_of_month=template.week_of_month,
        role_id=template.role_id,
        owner_id=template.owner_id,
        requires_notes=template.requires_notes,
        requires_evidence=template.requires_evidence,
        evidence_prompt=template.evidence_prompt,
        sub_items=template.sub_items,
        linked_area_id=template.linked_area_id,
        linked_kpi_id=template.linked_kpi_id,
        is_active=template.is_active,
        effective_from=template.effective_from,
        effective_until=template.effective_until,
        custom_fields=template.custom_fields,
    )


def _instance_to_response(
    instance: LSWChecklistInstance,
    service: LSWSchedulingService,
) -> InstanceResponse:
    """Convert instance to response."""
    template = service.get_template(instance.template_id)
    template_name = template.name if template else "Unknown"
    
    return InstanceResponse(
        id=instance.id,
        template_id=instance.template_id,
        template_name=template_name,
        scheduled_date=instance.scheduled_date,
        status=instance.status.value,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
        completed_by_id=instance.completed_by_id,
        notes=instance.notes,
        evidence_attachment_ids=instance.evidence_attachment_ids,
        sub_items_completed=instance.sub_items_completed,
        skip_reason=instance.skip_reason,
        deferred_to=instance.deferred_to,
        actual_duration_minutes=instance.actual_duration_minutes,
        findings=instance.findings,
        generated_task_ids=instance.generated_task_ids,
        generated_a3_ids=instance.generated_a3_ids,
    )


def _checklist_to_response(
    checklist: LSWChecklist,
    service: LSWSchedulingService,
) -> ChecklistResponse:
    """Convert checklist to response."""
    return ChecklistResponse(
        id=checklist.id,
        owner_id=checklist.owner_id,
        date=checklist.date,
        items=[_instance_to_response(i, service) for i in checklist.items],
        created_at=checklist.created_at,
        total_items=checklist.total_items,
        completed_count=checklist.completed_count,
        skipped_count=checklist.skipped_count,
        overdue_count=checklist.overdue_count,
        total_estimated_minutes=checklist.total_estimated_minutes,
        total_actual_minutes=checklist.total_actual_minutes,
    )


# --------------------------------------------------------------------------
# Template Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create LSW template",
    description="Create a new LSW checklist template.",
)
async def create_template(request: TemplateCreateRequest) -> TemplateResponse:
    """Create a new LSW template."""
    preferred_time = None
    if request.preferred_time:
        try:
            parts = request.preferred_time.split(":")
            preferred_time = time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time format. Use HH:MM.",
            )
    
    template = build_lsw_template(
        name=request.name,
        description=request.description,
        category=request.category,
        frequency=request.frequency,
        id=request.id,
        estimated_duration_minutes=request.estimated_duration_minutes,
        required=request.required,
        preferred_time=preferred_time,
        days_of_week=request.days_of_week,
        day_of_month=request.day_of_month,
        week_of_month=request.week_of_month,
        role_id=request.role_id,
        owner_id=request.owner_id,
        requires_notes=request.requires_notes,
        requires_evidence=request.requires_evidence,
        evidence_prompt=request.evidence_prompt,
        sub_items=request.sub_items,
        linked_area_id=request.linked_area_id,
        linked_kpi_id=request.linked_kpi_id,
        is_active=request.is_active,
        effective_from=request.effective_from,
        effective_until=request.effective_until,
        custom_fields=request.custom_fields,
    )
    
    result = _service.create_template(template)
    return _template_to_response(result)


@router.get(
    "/templates",
    response_model=list[TemplateResponse],
    summary="List LSW templates",
    description="List all LSW templates with optional filtering.",
)
async def list_templates(
    frequency: str | None = Query(None, description="Filter by frequency"),
    category: str | None = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Only return active templates"),
) -> list[TemplateResponse]:
    """List LSW templates."""
    freq = LSWFrequency(frequency) if frequency else None
    cat = LSWCategory(category) if category else None
    
    templates = _service.list_templates(
        frequency=freq,
        category=cat,
        active_only=active_only,
    )
    
    return [_template_to_response(t) for t in templates]


@router.get(
    "/templates/defaults",
    response_model=list[str],
    summary="Get default template IDs",
    description="Get the IDs of default LSW templates.",
)
async def get_default_templates() -> list[str]:
    """Get default template IDs."""
    return get_default_template_ids()


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Get LSW template",
    description="Get a specific LSW template by ID.",
)
async def get_template(template_id: str) -> TemplateResponse:
    """Get a template by ID."""
    template = _service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    return _template_to_response(template)


@router.put(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Update LSW template",
    description="Update an existing LSW template.",
)
async def update_template(
    template_id: str,
    request: TemplateUpdateRequest,
) -> TemplateResponse:
    """Update a template."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    
    if "preferred_time" in updates and updates["preferred_time"]:
        try:
            parts = updates["preferred_time"].split(":")
            updates["preferred_time"] = time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time format. Use HH:MM.",
            )
    
    if "days_of_week" in updates:
        updates["days_of_week"] = [DayOfWeek(d) for d in updates["days_of_week"]]
    
    result = _service.update_template(template_id, updates)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    return _template_to_response(result)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete LSW template",
    description="Delete an LSW template.",
)
async def delete_template(template_id: str) -> None:
    """Delete a template."""
    # Prevent deletion of default templates
    if template_id in get_default_template_ids():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default templates",
        )
    
    result = _service.delete_template(template_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )


# --------------------------------------------------------------------------
# Checklist Generation Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/checklists/generate",
    response_model=GenerationResultResponse,
    summary="Generate checklist",
    description="Generate LSW checklist items for a specific date and owner.",
)
async def generate_checklist(
    owner_id: str = Query(..., description="Owner ID"),
    target_date: date = Query(default_factory=date.today, description="Target date"),
    template_ids: list[str] | None = Query(None, description="Specific template IDs to generate"),
) -> GenerationResultResponse:
    """Generate a checklist for a date."""
    result = _service.generate_checklist(owner_id, target_date, template_ids)
    
    return GenerationResultResponse(
        date=result.date,
        owner_id=result.owner_id,
        generated_count=result.generated_count,
        items=[_instance_to_response(i, _service) for i in result.items],
    )


@router.post(
    "/checklists/generate-week",
    response_model=list[GenerationResultResponse],
    summary="Generate week checklists",
    description="Generate LSW checklists for a full week.",
)
async def generate_week_checklists(
    owner_id: str = Query(..., description="Owner ID"),
    start_date: date = Query(default_factory=date.today, description="Week start date"),
) -> list[GenerationResultResponse]:
    """Generate checklists for a week."""
    results = _service.generate_week_checklists(owner_id, start_date)
    
    return [
        GenerationResultResponse(
            date=r.date,
            owner_id=r.owner_id,
            generated_count=r.generated_count,
            items=[_instance_to_response(i, _service) for i in r.items],
        )
        for r in results
    ]


# --------------------------------------------------------------------------
# Checklist Retrieval Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/checklists",
    response_model=ChecklistResponse | None,
    summary="Get checklist",
    description="Get the checklist for a specific owner and date.",
)
async def get_checklist(
    owner_id: str = Query(..., description="Owner ID"),
    target_date: date = Query(default_factory=date.today, description="Target date"),
) -> ChecklistResponse | None:
    """Get a checklist for a specific date."""
    checklist = _service.get_checklist(owner_id, target_date)
    if not checklist:
        return None
    return _checklist_to_response(checklist, _service)


@router.get(
    "/items/pending",
    response_model=list[InstanceResponse],
    summary="Get pending items",
    description="Get all pending LSW items for an owner.",
)
async def get_pending_items(
    owner_id: str = Query(..., description="Owner ID"),
    include_overdue: bool = Query(True, description="Include overdue items"),
) -> list[InstanceResponse]:
    """Get pending items."""
    items = _service.get_pending_items(owner_id, include_overdue)
    return [_instance_to_response(i, _service) for i in items]


@router.get(
    "/items/overdue",
    response_model=list[InstanceResponse],
    summary="Get overdue items",
    description="Get all overdue LSW items.",
)
async def get_overdue_items(
    owner_id: str | None = Query(None, description="Owner ID (optional)"),
) -> list[InstanceResponse]:
    """Get overdue items."""
    items = _service.get_overdue_items(owner_id)
    return [_instance_to_response(i, _service) for i in items]


@router.get(
    "/items/{instance_id}",
    response_model=InstanceResponse,
    summary="Get item",
    description="Get a specific checklist item by ID.",
)
async def get_item(instance_id: str) -> InstanceResponse:
    """Get a checklist item."""
    instance = _service.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(instance, _service)


# --------------------------------------------------------------------------
# Item Action Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/items/{instance_id}/start",
    response_model=InstanceResponse,
    summary="Start item",
    description="Mark an LSW item as in progress.",
)
async def start_item(instance_id: str) -> InstanceResponse:
    """Start working on an item."""
    result = _service.start_item(instance_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/complete",
    response_model=InstanceResponse,
    summary="Complete item",
    description="Mark an LSW item as completed.",
)
async def complete_item(
    instance_id: str,
    request: CompleteItemRequest,
) -> InstanceResponse:
    """Complete an item."""
    result = _service.complete_item(
        instance_id,
        completed_by_id=request.completed_by_id,
        notes=request.notes,
        evidence_attachment_ids=request.evidence_attachment_ids or None,
        actual_duration_minutes=request.actual_duration_minutes,
        findings=request.findings or None,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/sub-items/{sub_item}",
    response_model=InstanceResponse,
    summary="Complete sub-item",
    description="Mark a sub-item as completed.",
)
async def complete_sub_item(
    instance_id: str,
    sub_item: str,
) -> InstanceResponse:
    """Complete a sub-item."""
    result = _service.complete_sub_item(instance_id, sub_item)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/skip",
    response_model=InstanceResponse,
    summary="Skip item",
    description="Skip an LSW item with a reason.",
)
async def skip_item(
    instance_id: str,
    request: SkipItemRequest,
) -> InstanceResponse:
    """Skip an item."""
    result = _service.skip_item(instance_id, request.reason)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/defer",
    response_model=InstanceResponse,
    summary="Defer item",
    description="Defer an LSW item to a later date.",
)
async def defer_item(
    instance_id: str,
    request: DeferItemRequest,
) -> InstanceResponse:
    """Defer an item."""
    result = _service.defer_item(instance_id, request.defer_to, request.reason)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/findings",
    response_model=InstanceResponse,
    summary="Add finding",
    description="Add a finding/observation to an LSW item.",
)
async def add_finding(
    instance_id: str,
    request: AddFindingRequest,
) -> InstanceResponse:
    """Add a finding."""
    result = _service.add_finding(instance_id, request.finding)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/tasks/{task_id}",
    response_model=InstanceResponse,
    summary="Link task",
    description="Link a generated task to an LSW item.",
)
async def link_task(
    instance_id: str,
    task_id: str,
) -> InstanceResponse:
    """Link a task."""
    result = _service.link_generated_task(instance_id, task_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


@router.post(
    "/items/{instance_id}/a3s/{a3_id}",
    response_model=InstanceResponse,
    summary="Link A3",
    description="Link a generated A3 to an LSW item.",
)
async def link_a3(
    instance_id: str,
    a3_id: str,
) -> InstanceResponse:
    """Link an A3."""
    result = _service.link_generated_a3(instance_id, a3_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {instance_id} not found",
        )
    return _instance_to_response(result, _service)


# --------------------------------------------------------------------------
# Status Update Endpoints
# --------------------------------------------------------------------------

@router.post(
    "/items/update-overdue",
    response_model=list[InstanceResponse],
    summary="Update overdue items",
    description="Mark past-due items as overdue.",
)
async def update_overdue_items() -> list[InstanceResponse]:
    """Update overdue items."""
    updated = _service.update_overdue_items()
    return [_instance_to_response(i, _service) for i in updated]


# --------------------------------------------------------------------------
# Analytics Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/stats/compliance",
    response_model=ComplianceStatsResponse,
    summary="Get compliance stats",
    description="Get LSW compliance statistics for a date range.",
)
async def get_compliance_stats(
    owner_id: str = Query(..., description="Owner ID"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
) -> ComplianceStatsResponse:
    """Get compliance statistics."""
    stats = _service.get_compliance_stats(owner_id, start_date, end_date)
    return ComplianceStatsResponse(**stats)


@router.get(
    "/stats/findings",
    response_model=list[dict[str, Any]],
    summary="Get findings summary",
    description="Get all findings from LSW items in a date range.",
)
async def get_findings_summary(
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    owner_id: str | None = Query(None, description="Owner ID (optional)"),
) -> list[dict[str, Any]]:
    """Get findings summary."""
    return _service.get_findings_summary(owner_id, start_date, end_date)


# --------------------------------------------------------------------------
# Metadata Endpoints
# --------------------------------------------------------------------------

@router.get(
    "/frequencies",
    response_model=list[dict[str, str]],
    summary="Get frequencies",
    description="Get available LSW frequencies.",
)
async def get_frequencies() -> list[dict[str, str]]:
    """Get available frequencies."""
    return [
        {"value": f.value, "name": f.name}
        for f in LSWFrequency
    ]


@router.get(
    "/categories",
    response_model=list[dict[str, str]],
    summary="Get categories",
    description="Get available LSW categories.",
)
async def get_categories() -> list[dict[str, str]]:
    """Get available categories."""
    return [
        {"value": c.value, "name": c.name}
        for c in LSWCategory
    ]


@router.get(
    "/statuses",
    response_model=list[dict[str, str]],
    summary="Get statuses",
    description="Get available LSW item statuses.",
)
async def get_statuses() -> list[dict[str, str]]:
    """Get available statuses."""
    return [
        {"value": s.value, "name": s.name}
        for s in LSWItemStatus
    ]


@router.get(
    "/days-of-week",
    response_model=list[dict[str, str]],
    summary="Get days of week",
    description="Get available days of week.",
)
async def get_days_of_week() -> list[dict[str, str]]:
    """Get days of week."""
    return [
        {"value": d.value, "name": d.name}
        for d in DayOfWeek
    ]
