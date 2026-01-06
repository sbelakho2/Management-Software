"""
API endpoints for Conditions Library.

Provides endpoints for managing condition templates and applying conditions
to quotes, qualifications, and other entities.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sensei.services.conditions_library import (
    ConditionsLibraryService,
    ConditionTemplate,
    AppliedCondition,
    ConditionSet,
    Placeholder,
    ConditionCategory,
    ConditionType,
    ConditionScope,
    PlaceholderType,
    get_conditions_library_service,
)

router = APIRouter(prefix="/conditions", tags=["conditions"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class PlaceholderSchema(BaseModel):
    """Schema for a placeholder in a condition template."""
    
    name: str
    display_label: str
    placeholder_type: str
    required: bool = True
    default_value: str | None = None
    options: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    validation_regex: str | None = None
    help_text: str | None = None


class ConditionTemplateResponse(BaseModel):
    """Response schema for a condition template."""
    
    id: str
    code: str
    name: str
    category: str
    condition_type: str
    scope: str
    template_text: str
    placeholders: list[PlaceholderSchema]
    description: str | None = None
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    applies_to_categories: list[str] | None = None
    applies_to_customers: list[str] | None = None
    version: int = 1
    translations: dict[str, str] | None = None


class CreateTemplateRequest(BaseModel):
    """Request to create a new condition template."""
    
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    category: str
    condition_type: str = "standard"
    scope: str = "quote"
    template_text: str = Field(..., min_length=1)
    placeholders: list[PlaceholderSchema] = Field(default_factory=list)
    description: str | None = None
    applies_to_categories: list[str] | None = None
    applies_to_customers: list[str] | None = None
    translations: dict[str, str] | None = None


class UpdateTemplateRequest(BaseModel):
    """Request to update a condition template."""
    
    name: str | None = None
    template_text: str | None = None
    placeholders: list[PlaceholderSchema] | None = None
    description: str | None = None
    condition_type: str | None = None
    scope: str | None = None
    applies_to_categories: list[str] | None = None
    applies_to_customers: list[str] | None = None
    translations: dict[str, str] | None = None
    is_active: bool | None = None


class AppliedConditionResponse(BaseModel):
    """Response schema for an applied condition."""
    
    id: str
    template_id: str | None = None
    entity_type: str
    entity_id: str
    condition_text: str
    placeholder_values: dict[str, Any] = Field(default_factory=dict)
    category: str
    condition_type: str
    is_acknowledged: bool = False
    acknowledged_by_id: str | None = None
    acknowledged_at: str | None = None
    is_resolved: bool = False
    resolved_by_id: str | None = None
    resolved_at: str | None = None
    resolution_notes: str | None = None
    sort_order: int = 0
    applied_at: str
    applied_by_id: str | None = None


class ApplyConditionRequest(BaseModel):
    """Request to apply a condition to an entity."""
    
    entity_type: str
    entity_id: str
    template_id: str | None = None
    placeholder_values: dict[str, Any] | None = None
    custom_text: str | None = None
    category: str = "custom"
    condition_type: str = "standard"
    sort_order: int = 0
    language: str = "en"


class ApplyConditionSetRequest(BaseModel):
    """Request to apply a condition set to an entity."""
    
    entity_type: str
    entity_id: str
    placeholder_values_map: dict[str, dict[str, Any]] | None = None
    language: str = "en"


class AcknowledgeConditionRequest(BaseModel):
    """Request to acknowledge a warning condition."""
    
    acknowledged_by_id: str


class ResolveHardStopRequest(BaseModel):
    """Request to resolve a hard stop condition."""
    
    resolved_by_id: str
    resolution_notes: str | None = None


class UpdateConditionTextRequest(BaseModel):
    """Request to update condition text."""
    
    new_text: str = Field(..., min_length=1)


class ReorderConditionsRequest(BaseModel):
    """Request to reorder conditions."""
    
    condition_order: list[str]


class ConditionSetResponse(BaseModel):
    """Response schema for a condition set."""
    
    id: str
    name: str
    description: str | None = None
    condition_template_ids: list[str]
    is_default: bool = False
    is_active: bool = True
    created_at: str
    updated_at: str


class CreateConditionSetRequest(BaseModel):
    """Request to create a condition set."""
    
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    condition_template_ids: list[str]


class UpdateConditionSetRequest(BaseModel):
    """Request to update a condition set."""
    
    name: str | None = None
    description: str | None = None
    condition_template_ids: list[str] | None = None
    is_active: bool | None = None


class CopyConditionsRequest(BaseModel):
    """Request to copy conditions between entities."""
    
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str


class RenderTemplateRequest(BaseModel):
    """Request to render a template with placeholder values."""
    
    placeholder_values: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


class ValidationResult(BaseModel):
    """Result of entity validation."""
    
    entity_type: str
    entity_id: str
    total_conditions: int
    hard_stops: int
    unresolved_hard_stops: int
    warnings: int
    unacknowledged_warnings: int
    can_proceed: bool
    requires_acknowledgment: bool
    issues: list[dict[str, Any]]


class TemplateUsageStats(BaseModel):
    """Template usage statistics."""
    
    template_id: str
    template_code: str
    template_name: str
    usage_count: int


class CategoryStats(BaseModel):
    """Statistics by category."""
    
    category: str
    count: int


# ============================================================================
# Helper Functions
# ============================================================================

def _template_to_response(template: ConditionTemplate) -> ConditionTemplateResponse:
    """Convert a ConditionTemplate to response schema."""
    return ConditionTemplateResponse(
        id=str(template.id),
        code=template.code,
        name=template.name,
        category=template.category.value,
        condition_type=template.condition_type.value,
        scope=template.scope.value,
        template_text=template.template_text,
        placeholders=[
            PlaceholderSchema(
                name=p.name,
                display_label=p.display_label,
                placeholder_type=p.placeholder_type.value,
                required=p.required,
                default_value=p.default_value,
                options=p.options,
                min_value=p.min_value,
                max_value=p.max_value,
                validation_regex=p.validation_regex,
                help_text=p.help_text,
            )
            for p in template.placeholders
        ],
        description=template.description,
        is_default=template.is_default,
        is_active=template.is_active,
        sort_order=template.sort_order,
        applies_to_categories=template.applies_to_categories,
        applies_to_customers=template.applies_to_customers,
        version=template.version,
        translations=template.translations,
    )


def _applied_to_response(applied: AppliedCondition) -> AppliedConditionResponse:
    """Convert an AppliedCondition to response schema."""
    return AppliedConditionResponse(
        id=str(applied.id),
        template_id=str(applied.template_id) if applied.template_id else None,
        entity_type=applied.entity_type,
        entity_id=str(applied.entity_id),
        condition_text=applied.condition_text,
        placeholder_values=applied.placeholder_values,
        category=applied.category.value,
        condition_type=applied.condition_type.value,
        is_acknowledged=applied.is_acknowledged,
        acknowledged_by_id=str(applied.acknowledged_by_id) if applied.acknowledged_by_id else None,
        acknowledged_at=applied.acknowledged_at.isoformat() if applied.acknowledged_at else None,
        is_resolved=applied.is_resolved,
        resolved_by_id=str(applied.resolved_by_id) if applied.resolved_by_id else None,
        resolved_at=applied.resolved_at.isoformat() if applied.resolved_at else None,
        resolution_notes=applied.resolution_notes,
        sort_order=applied.sort_order,
        applied_at=applied.applied_at.isoformat(),
        applied_by_id=str(applied.applied_by_id) if applied.applied_by_id else None,
    )


def _set_to_response(condition_set: ConditionSet) -> ConditionSetResponse:
    """Convert a ConditionSet to response schema."""
    return ConditionSetResponse(
        id=str(condition_set.id),
        name=condition_set.name,
        description=condition_set.description,
        condition_template_ids=[str(tid) for tid in condition_set.condition_template_ids],
        is_default=condition_set.is_default,
        is_active=condition_set.is_active,
        created_at=condition_set.created_at.isoformat(),
        updated_at=condition_set.updated_at.isoformat(),
    )


def _get_service() -> ConditionsLibraryService:
    """Get the conditions library service."""
    return get_conditions_library_service()


def _parse_category(value: str) -> ConditionCategory:
    """Parse category string to enum."""
    try:
        return ConditionCategory(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid category: {value}"},
        )


def _parse_condition_type(value: str) -> ConditionType:
    """Parse condition type string to enum."""
    try:
        return ConditionType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid condition type: {value}"},
        )


def _parse_scope(value: str) -> ConditionScope:
    """Parse scope string to enum."""
    try:
        return ConditionScope(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid scope: {value}"},
        )


def _parse_placeholder_type(value: str) -> PlaceholderType:
    """Parse placeholder type string to enum."""
    try:
        return PlaceholderType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Invalid placeholder type: {value}"},
        )


def _schema_to_placeholder(schema: PlaceholderSchema) -> Placeholder:
    """Convert PlaceholderSchema to Placeholder dataclass."""
    return Placeholder(
        name=schema.name,
        display_label=schema.display_label,
        placeholder_type=_parse_placeholder_type(schema.placeholder_type),
        required=schema.required,
        default_value=schema.default_value,
        options=schema.options,
        min_value=schema.min_value,
        max_value=schema.max_value,
        validation_regex=schema.validation_regex,
        help_text=schema.help_text,
    )


# ============================================================================
# Template Endpoints
# ============================================================================

@router.post("/templates", response_model=ConditionTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(request: CreateTemplateRequest) -> ConditionTemplateResponse:
    """Create a new condition template."""
    service = _get_service()
    
    try:
        template = service.create_template(
            code=request.code,
            name=request.name,
            category=_parse_category(request.category),
            condition_type=_parse_condition_type(request.condition_type),
            scope=_parse_scope(request.scope),
            template_text=request.template_text,
            placeholders=[_schema_to_placeholder(p) for p in request.placeholders],
            description=request.description,
            applies_to_categories=request.applies_to_categories,
            applies_to_customers=request.applies_to_customers,
            translations=request.translations,
        )
        return _template_to_response(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.get("/templates", response_model=list[ConditionTemplateResponse])
async def list_templates(
    category: str | None = None,
    condition_type: str | None = None,
    scope: str | None = None,
    is_active: bool | None = None,
    include_defaults: bool = True,
    search: str | None = None,
) -> list[ConditionTemplateResponse]:
    """List condition templates with optional filtering."""
    service = _get_service()
    
    templates = service.list_templates(
        category=_parse_category(category) if category else None,
        condition_type=_parse_condition_type(condition_type) if condition_type else None,
        scope=_parse_scope(scope) if scope else None,
        is_active=is_active,
        include_defaults=include_defaults,
        search=search,
    )
    
    return [_template_to_response(t) for t in templates]


@router.get("/templates/defaults", response_model=list[str])
async def list_default_template_codes() -> list[str]:
    """List all default template codes."""
    service = _get_service()
    return [t.code for t in service.list_templates() if t.is_default]


@router.get("/templates/{template_id}", response_model=ConditionTemplateResponse)
async def get_template(template_id: str) -> ConditionTemplateResponse:
    """Get a condition template by ID."""
    service = _get_service()
    
    template = service.get_template(UUID(template_id))
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Template {template_id} not found"},
        )
    
    return _template_to_response(template)


@router.get("/templates/by-code/{code}", response_model=ConditionTemplateResponse)
async def get_template_by_code(code: str) -> ConditionTemplateResponse:
    """Get a condition template by code."""
    service = _get_service()
    
    template = service.get_template_by_code(code)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Template with code '{code}' not found"},
        )
    
    return _template_to_response(template)


@router.put("/templates/{template_id}", response_model=ConditionTemplateResponse)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
) -> ConditionTemplateResponse:
    """Update a condition template."""
    service = _get_service()
    
    try:
        template = service.update_template(
            template_id=UUID(template_id),
            name=request.name,
            template_text=request.template_text,
            placeholders=[_schema_to_placeholder(p) for p in request.placeholders] if request.placeholders else None,
            description=request.description,
            condition_type=_parse_condition_type(request.condition_type) if request.condition_type else None,
            scope=_parse_scope(request.scope) if request.scope else None,
            applies_to_categories=request.applies_to_categories,
            applies_to_customers=request.applies_to_customers,
            translations=request.translations,
            is_active=request.is_active,
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Template {template_id} not found"},
            )
        
        return _template_to_response(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str) -> None:
    """Delete a condition template."""
    service = _get_service()
    
    try:
        result = service.delete_template(UUID(template_id))
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Template {template_id} not found"},
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.post("/templates/{template_id}/render", response_model=dict)
async def render_template(
    template_id: str,
    request: RenderTemplateRequest,
) -> dict:
    """Render a template with placeholder values."""
    service = _get_service()
    
    template = service.get_template(UUID(template_id))
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Template {template_id} not found"},
        )
    
    try:
        text = service.render_template(
            template,
            request.placeholder_values,
            request.language,
        )
        return {"rendered_text": text}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


# ============================================================================
# Applied Conditions Endpoints
# ============================================================================

@router.post("/applied", response_model=AppliedConditionResponse, status_code=status.HTTP_201_CREATED)
async def apply_condition(request: ApplyConditionRequest) -> AppliedConditionResponse:
    """Apply a condition to an entity."""
    service = _get_service()
    
    try:
        applied = service.apply_condition(
            entity_type=request.entity_type,
            entity_id=UUID(request.entity_id),
            template_id=UUID(request.template_id) if request.template_id else None,
            placeholder_values=request.placeholder_values,
            custom_text=request.custom_text,
            category=_parse_category(request.category),
            condition_type=_parse_condition_type(request.condition_type),
            sort_order=request.sort_order,
            language=request.language,
        )
        return _applied_to_response(applied)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.get("/applied/{entity_type}/{entity_id}", response_model=list[AppliedConditionResponse])
async def get_conditions_for_entity(
    entity_type: str,
    entity_id: str,
    category: str | None = None,
    condition_type: str | None = None,
    unresolved_only: bool = False,
) -> list[AppliedConditionResponse]:
    """Get all conditions applied to an entity."""
    service = _get_service()
    
    conditions = service.get_conditions_for_entity(
        entity_type=entity_type,
        entity_id=UUID(entity_id),
        category=_parse_category(category) if category else None,
        condition_type=_parse_condition_type(condition_type) if condition_type else None,
        unresolved_only=unresolved_only,
    )
    
    return [_applied_to_response(c) for c in conditions]


@router.get("/applied/{entity_type}/{entity_id}/hard-stops", response_model=list[AppliedConditionResponse])
async def get_hard_stops(entity_type: str, entity_id: str) -> list[AppliedConditionResponse]:
    """Get unresolved hard stops for an entity."""
    service = _get_service()
    
    hard_stops = service.get_hard_stops_for_entity(entity_type, UUID(entity_id))
    return [_applied_to_response(hs) for hs in hard_stops]


@router.get("/applied/{entity_type}/{entity_id}/validate", response_model=ValidationResult)
async def validate_entity(entity_type: str, entity_id: str) -> ValidationResult:
    """Validate an entity's conditions."""
    service = _get_service()
    
    result = service.validate_entity(entity_type, UUID(entity_id))
    return ValidationResult(**result)


@router.post("/applied/{condition_id}/acknowledge", response_model=AppliedConditionResponse)
async def acknowledge_condition(
    condition_id: str,
    request: AcknowledgeConditionRequest,
) -> AppliedConditionResponse:
    """Acknowledge a warning condition."""
    service = _get_service()
    
    try:
        condition = service.acknowledge_condition(
            UUID(condition_id),
            UUID(request.acknowledged_by_id),
        )
        
        if not condition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Condition {condition_id} not found"},
            )
        
        return _applied_to_response(condition)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.post("/applied/{condition_id}/resolve", response_model=AppliedConditionResponse)
async def resolve_hard_stop(
    condition_id: str,
    request: ResolveHardStopRequest,
) -> AppliedConditionResponse:
    """Resolve a hard stop condition."""
    service = _get_service()
    
    try:
        condition = service.resolve_hard_stop(
            UUID(condition_id),
            UUID(request.resolved_by_id),
            request.resolution_notes,
        )
        
        if not condition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Condition {condition_id} not found"},
            )
        
        return _applied_to_response(condition)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.put("/applied/{condition_id}/text", response_model=AppliedConditionResponse)
async def update_condition_text(
    condition_id: str,
    request: UpdateConditionTextRequest,
) -> AppliedConditionResponse:
    """Update the text of an applied condition."""
    service = _get_service()
    
    condition = service.update_condition_text(UUID(condition_id), request.new_text)
    
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Condition {condition_id} not found"},
        )
    
    return _applied_to_response(condition)


@router.delete("/applied/{condition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_condition(condition_id: str) -> None:
    """Remove an applied condition."""
    service = _get_service()
    
    result = service.remove_condition(UUID(condition_id))
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Condition {condition_id} not found"},
        )


@router.post("/applied/{entity_type}/{entity_id}/reorder", response_model=list[AppliedConditionResponse])
async def reorder_conditions(
    entity_type: str,
    entity_id: str,
    request: ReorderConditionsRequest,
) -> list[AppliedConditionResponse]:
    """Reorder conditions for an entity."""
    service = _get_service()
    
    conditions = service.reorder_conditions(
        entity_type,
        UUID(entity_id),
        [UUID(cid) for cid in request.condition_order],
    )
    
    return [_applied_to_response(c) for c in conditions]


@router.post("/applied/copy", response_model=list[AppliedConditionResponse])
async def copy_conditions(request: CopyConditionsRequest) -> list[AppliedConditionResponse]:
    """Copy conditions from one entity to another."""
    service = _get_service()
    
    copied = service.copy_conditions(
        source_entity_type=request.source_entity_type,
        source_entity_id=UUID(request.source_entity_id),
        target_entity_type=request.target_entity_type,
        target_entity_id=UUID(request.target_entity_id),
    )
    
    return [_applied_to_response(c) for c in copied]


@router.delete("/applied/{entity_type}/{entity_id}/clear", response_model=dict)
async def clear_conditions(entity_type: str, entity_id: str) -> dict:
    """Clear all conditions from an entity."""
    service = _get_service()
    
    count = service.clear_conditions(entity_type, UUID(entity_id))
    return {"cleared_count": count}


@router.get("/applied/{entity_type}/{entity_id}/export", response_model=dict)
async def export_conditions(
    entity_type: str,
    entity_id: str,
    format: str = "text",
) -> dict:
    """Export conditions for an entity."""
    service = _get_service()
    
    result = service.export_conditions(entity_type, UUID(entity_id), format)
    
    if isinstance(result, str):
        return {"format": "text", "content": result}
    else:
        return {"format": "json", "conditions": result}


# ============================================================================
# Condition Sets Endpoints
# ============================================================================

@router.post("/sets", response_model=ConditionSetResponse, status_code=status.HTTP_201_CREATED)
async def create_condition_set(request: CreateConditionSetRequest) -> ConditionSetResponse:
    """Create a new condition set."""
    service = _get_service()
    
    try:
        condition_set = service.create_condition_set(
            name=request.name,
            description=request.description,
            condition_template_ids=[UUID(tid) for tid in request.condition_template_ids],
        )
        return _set_to_response(condition_set)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.get("/sets", response_model=list[ConditionSetResponse])
async def list_condition_sets(
    is_active: bool | None = None,
    include_defaults: bool = True,
) -> list[ConditionSetResponse]:
    """List condition sets."""
    service = _get_service()
    
    sets = service.list_condition_sets(
        is_active=is_active,
        include_defaults=include_defaults,
    )
    
    return [_set_to_response(s) for s in sets]


@router.get("/sets/{set_id}", response_model=ConditionSetResponse)
async def get_condition_set(set_id: str) -> ConditionSetResponse:
    """Get a condition set by ID."""
    service = _get_service()
    
    condition_set = service.get_condition_set(UUID(set_id))
    if not condition_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Condition set {set_id} not found"},
        )
    
    return _set_to_response(condition_set)


@router.put("/sets/{set_id}", response_model=ConditionSetResponse)
async def update_condition_set(
    set_id: str,
    request: UpdateConditionSetRequest,
) -> ConditionSetResponse:
    """Update a condition set."""
    service = _get_service()
    
    try:
        condition_set = service.update_condition_set(
            set_id=UUID(set_id),
            name=request.name,
            description=request.description,
            condition_template_ids=[UUID(tid) for tid in request.condition_template_ids] if request.condition_template_ids else None,
            is_active=request.is_active,
        )
        
        if not condition_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Condition set {set_id} not found"},
            )
        
        return _set_to_response(condition_set)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_condition_set(set_id: str) -> None:
    """Delete a condition set."""
    service = _get_service()
    
    try:
        result = service.delete_condition_set(UUID(set_id))
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": f"Condition set {set_id} not found"},
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


@router.post("/sets/{set_id}/apply", response_model=list[AppliedConditionResponse])
async def apply_condition_set(
    set_id: str,
    request: ApplyConditionSetRequest,
) -> list[AppliedConditionResponse]:
    """Apply all conditions from a set to an entity."""
    service = _get_service()
    
    try:
        applied = service.apply_condition_set(
            set_id=UUID(set_id),
            entity_type=request.entity_type,
            entity_id=UUID(request.entity_id),
            placeholder_values_map=request.placeholder_values_map,
            language=request.language,
        )
        return [_applied_to_response(a) for a in applied]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e)},
        )


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get("/stats/usage", response_model=list[TemplateUsageStats])
async def get_template_usage_stats() -> list[TemplateUsageStats]:
    """Get usage statistics for templates."""
    service = _get_service()
    
    usage = service.get_template_usage_stats()
    
    result = []
    for template_id, count in usage.items():
        template = service.get_template(template_id)
        if template:
            result.append(TemplateUsageStats(
                template_id=str(template_id),
                template_code=template.code,
                template_name=template.name,
                usage_count=count,
            ))
    
    return sorted(result, key=lambda x: x.usage_count, reverse=True)


@router.get("/stats/categories", response_model=list[CategoryStats])
async def get_category_stats() -> list[CategoryStats]:
    """Get statistics by category."""
    service = _get_service()
    
    stats = service.get_category_stats()
    
    return [
        CategoryStats(category=cat.value, count=count)
        for cat, count in stats.items()
    ]


# ============================================================================
# Metadata Endpoints
# ============================================================================

@router.get("/categories", response_model=list[dict])
async def get_categories() -> list[dict]:
    """Get all condition categories."""
    return [
        {"value": cat.value, "name": cat.name.replace("_", " ").title()}
        for cat in ConditionCategory
    ]


@router.get("/types", response_model=list[dict])
async def get_condition_types() -> list[dict]:
    """Get all condition types."""
    return [
        {"value": ct.value, "name": ct.name.replace("_", " ").title()}
        for ct in ConditionType
    ]


@router.get("/scopes", response_model=list[dict])
async def get_scopes() -> list[dict]:
    """Get all condition scopes."""
    return [
        {"value": scope.value, "name": scope.name.replace("_", " ").title()}
        for scope in ConditionScope
    ]


@router.get("/placeholder-types", response_model=list[dict])
async def get_placeholder_types() -> list[dict]:
    """Get all placeholder types."""
    return [
        {"value": pt.value, "name": pt.name.replace("_", " ").title()}
        for pt in PlaceholderType
    ]
