from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.models.user import User, RoleType
from sensei.services.ai.ai_email_drafting import (
    AIEmailDraftingService,
    EmailContext,
    EmailPurpose,
    EmailTone,
    GenerationRequest,
    Language,
    Recipient,
)
from sensei.services.core.common_thread import get_common_thread_service

AllowEmailDrafting: deps.RoleDependency = deps.require_role(
    "admin",
    "ceo",
    "sales",
    "sales_engineer",
    "estimator",
    "gm",
    "exec",
)  # type: ignore[valid-type]

router = APIRouter(
    dependencies=[
        Depends(
            deps.RoleChecker(["admin", "ceo", "sales", "sales_engineer", "estimator", "gm", "exec"])
        )
    ]
)

_service = AIEmailDraftingService()

_ALLOWED_EMAIL_ROLES = {role.value for role in RoleType}

_ALLOWED_THREAD_ENTITY_TYPES = {
    "rfq",
    "quote",
    "work_order",
    "opportunity",
    "non_conformance",
    "shipment",
    "invoice",
}


class RecipientInput(BaseModel):
    email: str
    name: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    relationship: Optional[str] = None
    language_preference: Optional[Language] = None
    previous_interactions: int = 0


class EmailGenerationRequest(BaseModel):
    recipient: RecipientInput
    purpose: EmailPurpose = EmailPurpose.CUSTOM
    tone: EmailTone = EmailTone.PROFESSIONAL
    key_points: list[str] = Field(default_factory=list)
    reference_number: Optional[str] = None
    deadline: Optional[datetime] = None
    attachments: list[str] = Field(default_factory=list)
    sender_name: str
    sender_title: Optional[str] = None
    sender_email: str
    company_name: Optional[str] = None
    subject_hint: Optional[str] = None
    language: Language = Language.ENGLISH
    include_signature: bool = True
    max_paragraphs: int = 4
    additional_context: dict[str, Any] = Field(default_factory=dict)
    thread_entity_type: Optional[str] = None
    thread_entity_id: Optional[str] = None
    thread_reasoning_id: Optional[str] = None


class EmailGenerationResponse(BaseModel):
    id: UUID
    subject: str
    body: str
    body_html: str
    salutation: str
    opening: str
    main_content: list[str]
    closing: str
    signature: str
    status: str
    confidence_score: float
    alternatives: list[str]
    compliance_issues: list[str]
    suggestions: list[str]
    tokens_used: int
    generation_time_ms: int
    model_version: str
    reasoning_id: Optional[str] = None


def _get_user_roles(user: Any) -> set[str]:
    if hasattr(user, "get_role_names"):
        return {role.lower() for role in user.get_role_names()}
    roles = getattr(user, "roles", None) or []
    return {getattr(role, "name", str(role)).lower() for role in roles}


@router.post(
    "/email/generate",
    response_model=APIResponse[EmailGenerationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_email_draft(
    request: EmailGenerationRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> APIResponse[EmailGenerationResponse]:
    """Generate an AI email draft."""
    roles = _get_user_roles(current_user)
    if not roles and not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Access denied")
    if roles and not (roles & _ALLOWED_EMAIL_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient role for email drafting")

    recipient = Recipient(
        email=request.recipient.email,
        name=request.recipient.name,
        title=request.recipient.title,
        company=request.recipient.company,
        relationship=request.recipient.relationship,
        language_preference=request.recipient.language_preference or request.language,
        previous_interactions=request.recipient.previous_interactions,
    )

    context = EmailContext(
        purpose=request.purpose,
        recipient=recipient,
        subject_hint=request.subject_hint,
        key_points=request.key_points,
        attachments=request.attachments,
        reference_number=request.reference_number,
        deadline=request.deadline,
        tone=request.tone,
        language=request.language,
        include_signature=request.include_signature,
        max_paragraphs=request.max_paragraphs,
        additional_context=request.additional_context,
    )

    generation_request = GenerationRequest(
        context=context,
        sender_name=request.sender_name,
        sender_title=request.sender_title,
        sender_email=request.sender_email,
        company_name=request.company_name or "",
        requested_by=current_user.id,
    )

    reasoning_id = request.thread_reasoning_id or str(uuid4())
    if request.thread_entity_type and request.thread_entity_id:
        entity_type = request.thread_entity_type.strip().lower()
        if entity_type not in _ALLOWED_THREAD_ENTITY_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported thread entity type")
        await get_common_thread_service().record_reasoning(
            db,
            entity_type=entity_type,
            entity_id=request.thread_entity_id,
            reasoning_id=reasoning_id,
            created_by_id=current_user.id,
            source="email_drafting",
        )
        await db.commit()

    try:
        draft = _service.generate_draft(generation_request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = EmailGenerationResponse(
        id=draft.id,
        subject=draft.subject,
        body=draft.body_plain,
        body_html=draft.body_html,
        salutation=draft.salutation,
        opening=draft.opening,
        main_content=draft.main_content,
        closing=draft.closing,
        signature=draft.signature,
        status=draft.status.value,
        confidence_score=draft.confidence_score,
        alternatives=draft.alternatives,
        compliance_issues=draft.compliance_issues,
        suggestions=draft.suggestions,
        tokens_used=draft.tokens_used,
        generation_time_ms=draft.generation_time_ms,
        model_version="v1.0",
        reasoning_id=reasoning_id if request.thread_entity_type and request.thread_entity_id else None,
    )

    return build_response(response)
