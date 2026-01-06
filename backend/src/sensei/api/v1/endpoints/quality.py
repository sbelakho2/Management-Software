"""Quality Management Endpoints.

Provides CRUD and workflow operations for:
- Non-Conformance (NC) records
- Corrective/Preventive Actions (CAPA) and CAPA actions
- Inspection plans and inspection records

Follows the standard API response schema used across v1 endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
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
    now_utc,
)
from sensei.models.quality import (
    CAPA,
    CAPAAction,
    CAPAActionStatus,
    CAPAActionType,
    CAPAPriority,
    CAPASourceType,
    CAPAStatus,
    CAPAType,
    EffectivenessStatus,
    InspectionPlan,
    InspectionRecord,
    InspectionResult,
    InspectionType,
    NCDisposition,
    NCSeverity,
    NCSource,
    NCStatus,
    NCType,
    NonConformance,
    RootCauseCategory,
    VerificationStatus,
)

router = APIRouter()


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
# Non-Conformance Schemas
# =============================================================================


class NonConformanceBase(BaseModel):
    nc_number: str = Field(..., min_length=1, max_length=50)
    nc_type: NCType
    source: NCSource
    severity: NCSeverity = NCSeverity.MINOR

    product_id: Optional[int] = None
    work_order_id: Optional[int] = None
    station_id: Optional[int] = None
    lot_number: Optional[str] = Field(None, max_length=100)

    quantity_affected: int = Field(default=1, gt=0)
    quantity_inspected: Optional[int] = Field(default=None, ge=0)

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    specification_requirement: Optional[str] = None
    actual_condition: Optional[str] = None

    root_cause_category: Optional[RootCauseCategory] = None
    root_cause_description: Optional[str] = None

    status: NCStatus = NCStatus.OPEN

    investigator_id: Optional[UUID] = None
    investigation_due_date: Optional[date] = None
    investigation_notes: Optional[str] = None

    disposition: Optional[NCDisposition] = None
    disposition_notes: Optional[str] = None
    disposition_evidence: Optional[str] = None

    containment_actions: Optional[str] = None
    containment_verified: bool = False

    cost_impact: Optional[Decimal] = Field(default=None, ge=0)
    scrap_cost: Optional[Decimal] = Field(default=None, ge=0)
    rework_cost: Optional[Decimal] = Field(default=None, ge=0)
    rework_hours: Optional[Decimal] = Field(default=None, ge=0)

    customer_notified: bool = False
    customer_notification_date: Optional[date] = None
    customer_notification_notes: Optional[str] = None

    closure_notes: Optional[str] = None

    capa_id: Optional[int] = None

    supplier_name: Optional[str] = Field(None, max_length=255)
    supplier_po_number: Optional[str] = Field(None, max_length=100)

    @field_validator("nc_type", mode="before")
    @classmethod
    def validate_nc_type(cls, v):
        return _parse_enum(NCType, v, "nc_type")

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v):
        return _parse_enum(NCSource, v, "source")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        return _parse_enum(NCSeverity, v, "severity")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        return _parse_enum(NCStatus, v, "status")

    @field_validator("disposition", mode="before")
    @classmethod
    def validate_disposition(cls, v):
        return _parse_enum(NCDisposition, v, "disposition")

    @field_validator("root_cause_category", mode="before")
    @classmethod
    def validate_root_cause_category(cls, v):
        return _parse_enum(RootCauseCategory, v, "root_cause_category")


class NonConformanceCreate(NonConformanceBase):
    pass


class NonConformanceUpdate(BaseModel):
    nc_type: Optional[NCType] = None
    source: Optional[NCSource] = None
    severity: Optional[NCSeverity] = None

    product_id: Optional[int] = None
    work_order_id: Optional[int] = None
    station_id: Optional[int] = None
    lot_number: Optional[str] = Field(None, max_length=100)

    quantity_affected: Optional[int] = Field(default=None, gt=0)
    quantity_inspected: Optional[int] = Field(default=None, ge=0)

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    specification_requirement: Optional[str] = None
    actual_condition: Optional[str] = None

    root_cause_category: Optional[RootCauseCategory] = None
    root_cause_description: Optional[str] = None

    status: Optional[NCStatus] = None

    investigator_id: Optional[UUID] = None
    investigation_due_date: Optional[date] = None
    investigation_completed_at: Optional[datetime] = None
    investigation_notes: Optional[str] = None

    disposition: Optional[NCDisposition] = None
    disposition_by_id: Optional[UUID] = None
    disposition_at: Optional[datetime] = None
    disposition_notes: Optional[str] = None
    disposition_evidence: Optional[str] = None

    containment_actions: Optional[str] = None
    containment_verified: Optional[bool] = None
    containment_verified_by_id: Optional[UUID] = None

    cost_impact: Optional[Decimal] = Field(default=None, ge=0)
    scrap_cost: Optional[Decimal] = Field(default=None, ge=0)
    rework_cost: Optional[Decimal] = Field(default=None, ge=0)
    rework_hours: Optional[Decimal] = Field(default=None, ge=0)

    customer_notified: Optional[bool] = None
    customer_notification_date: Optional[date] = None
    customer_notification_notes: Optional[str] = None

    closed_by_id: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None

    capa_id: Optional[int] = None

    supplier_name: Optional[str] = Field(None, max_length=255)
    supplier_po_number: Optional[str] = Field(None, max_length=100)

    @field_validator("nc_type", mode="before")
    @classmethod
    def validate_nc_type(cls, v):
        return _parse_enum(NCType, v, "nc_type")

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v):
        return _parse_enum(NCSource, v, "source")

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v):
        return _parse_enum(NCSeverity, v, "severity")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        return _parse_enum(NCStatus, v, "status")

    @field_validator("disposition", mode="before")
    @classmethod
    def validate_disposition(cls, v):
        return _parse_enum(NCDisposition, v, "disposition")

    @field_validator("root_cause_category", mode="before")
    @classmethod
    def validate_root_cause_category(cls, v):
        return _parse_enum(RootCauseCategory, v, "root_cause_category")


class NonConformanceResponse(BaseModel):
    id: int
    nc_number: str
    nc_type: str
    source: str
    severity: str
    status: str

    product_id: Optional[int] = None
    work_order_id: Optional[int] = None
    station_id: Optional[int] = None
    lot_number: Optional[str] = None

    quantity_affected: int
    quantity_inspected: Optional[int] = None

    title: str
    description: str
    specification_requirement: Optional[str] = None
    actual_condition: Optional[str] = None

    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None

    investigator_id: Optional[UUID] = None
    investigation_due_date: Optional[date] = None
    investigation_completed_at: Optional[datetime] = None
    investigation_notes: Optional[str] = None

    disposition: Optional[str] = None
    disposition_by_id: Optional[UUID] = None
    disposition_at: Optional[datetime] = None
    disposition_notes: Optional[str] = None
    disposition_evidence: Optional[str] = None

    containment_actions: Optional[str] = None
    containment_verified: bool
    containment_verified_by_id: Optional[UUID] = None

    cost_impact: Optional[Decimal] = None
    scrap_cost: Optional[Decimal] = None
    rework_cost: Optional[Decimal] = None
    rework_hours: Optional[Decimal] = None
    total_cost: Decimal

    customer_notified: bool
    customer_notification_date: Optional[date] = None
    customer_notification_notes: Optional[str] = None

    closed_by_id: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None

    capa_id: Optional[int] = None

    supplier_name: Optional[str] = None
    supplier_po_number: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    is_open: bool
    requires_capa: bool
    age_days: int

    model_config = ConfigDict(from_attributes=True)


def nc_to_response(nc: NonConformance) -> NonConformanceResponse:
    def _val(v):
        return v.value if hasattr(v, "value") else v

    return NonConformanceResponse(
        id=nc.id,
        nc_number=nc.nc_number,
        nc_type=_val(nc.nc_type),
        source=_val(nc.source),
        severity=_val(nc.severity),
        status=_val(nc.status),
        product_id=nc.product_id,
        work_order_id=nc.work_order_id,
        station_id=nc.station_id,
        lot_number=nc.lot_number,
        quantity_affected=nc.quantity_affected,
        quantity_inspected=nc.quantity_inspected,
        title=nc.title,
        description=nc.description,
        specification_requirement=nc.specification_requirement,
        actual_condition=nc.actual_condition,
        root_cause_category=_val(nc.root_cause_category) if nc.root_cause_category else None,
        root_cause_description=nc.root_cause_description,
        investigator_id=nc.investigator_id,
        investigation_due_date=nc.investigation_due_date,
        investigation_completed_at=nc.investigation_completed_at,
        investigation_notes=nc.investigation_notes,
        disposition=_val(nc.disposition) if nc.disposition else None,
        disposition_by_id=nc.disposition_by_id,
        disposition_at=nc.disposition_at,
        disposition_notes=nc.disposition_notes,
        disposition_evidence=nc.disposition_evidence,
        containment_actions=nc.containment_actions,
        containment_verified=nc.containment_verified,
        containment_verified_by_id=nc.containment_verified_by_id,
        cost_impact=nc.cost_impact,
        scrap_cost=nc.scrap_cost,
        rework_cost=nc.rework_cost,
        rework_hours=nc.rework_hours,
        total_cost=nc.total_cost,
        customer_notified=nc.customer_notified,
        customer_notification_date=nc.customer_notification_date,
        customer_notification_notes=nc.customer_notification_notes,
        closed_by_id=nc.closed_by_id,
        closed_at=nc.closed_at,
        closure_notes=nc.closure_notes,
        capa_id=nc.capa_id,
        supplier_name=nc.supplier_name,
        supplier_po_number=nc.supplier_po_number,
        created_at=nc.created_at,
        updated_at=nc.updated_at,
        deleted_at=nc.deleted_at,
        is_open=nc.is_open,
        requires_capa=nc.requires_capa,
        age_days=nc.age_days,
    )


# =============================================================================
# CAPA Schemas
# =============================================================================


class CAPABase(BaseModel):
    capa_number: str = Field(..., min_length=1, max_length=50)
    capa_type: CAPAType = CAPAType.CORRECTIVE
    source_type: CAPASourceType
    priority: CAPAPriority = CAPAPriority.MEDIUM

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)

    status: CAPAStatus = CAPAStatus.OPEN

    owner_id: UUID
    due_date: date
    target_close_date: Optional[date] = None

    root_cause_analysis: Optional[str] = None
    root_cause_category: Optional[RootCauseCategory] = None
    five_why_analysis: Optional[dict[str, Any]] = None

    containment_actions: Optional[str] = None
    corrective_actions: Optional[str] = None
    preventive_actions: Optional[str] = None

    verification_method: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verified_by_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    verification_evidence: Optional[str] = None

    effectiveness_check_date: Optional[date] = None
    effectiveness_status: EffectivenessStatus = EffectivenessStatus.PENDING
    effectiveness_checked_by_id: Optional[UUID] = None
    effectiveness_evidence: Optional[str] = None

    closure_notes: Optional[str] = None
    lessons_learned: Optional[str] = None

    source_nc_id: Optional[int] = None

    estimated_cost_savings: Optional[Decimal] = Field(default=None, ge=0)
    actual_cost_savings: Optional[Decimal] = Field(default=None, ge=0)
    implementation_cost: Optional[Decimal] = Field(default=None, ge=0)

    team_members: Optional[list[int]] = None

    @field_validator("capa_type", mode="before")
    @classmethod
    def validate_capa_type(cls, v):
        return _parse_enum(CAPAType, v, "capa_type")

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, v):
        return _parse_enum(CAPASourceType, v, "source_type")

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v):
        return _parse_enum(CAPAPriority, v, "priority")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        return _parse_enum(CAPAStatus, v, "status")

    @field_validator("root_cause_category", mode="before")
    @classmethod
    def validate_root_cause_category(cls, v):
        return _parse_enum(RootCauseCategory, v, "root_cause_category")

    @field_validator("verification_status", mode="before")
    @classmethod
    def validate_verification_status(cls, v):
        return _parse_enum(VerificationStatus, v, "verification_status")

    @field_validator("effectiveness_status", mode="before")
    @classmethod
    def validate_effectiveness_status(cls, v):
        return _parse_enum(EffectivenessStatus, v, "effectiveness_status")


class CAPACreate(CAPABase):
    pass


class CAPAUpdate(BaseModel):
    capa_type: Optional[CAPAType] = None
    source_type: Optional[CAPASourceType] = None
    priority: Optional[CAPAPriority] = None

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)

    status: Optional[CAPAStatus] = None

    owner_id: Optional[UUID] = None
    due_date: Optional[date] = None
    target_close_date: Optional[date] = None

    root_cause_analysis: Optional[str] = None
    root_cause_category: Optional[RootCauseCategory] = None
    five_why_analysis: Optional[dict[str, Any]] = None

    containment_actions: Optional[str] = None
    corrective_actions: Optional[str] = None
    preventive_actions: Optional[str] = None

    verification_method: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    verified_by_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    verification_evidence: Optional[str] = None

    effectiveness_check_date: Optional[date] = None
    effectiveness_status: Optional[EffectivenessStatus] = None
    effectiveness_checked_by_id: Optional[UUID] = None
    effectiveness_evidence: Optional[str] = None

    closed_by_id: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None
    lessons_learned: Optional[str] = None

    source_nc_id: Optional[int] = None

    estimated_cost_savings: Optional[Decimal] = Field(default=None, ge=0)
    actual_cost_savings: Optional[Decimal] = Field(default=None, ge=0)
    implementation_cost: Optional[Decimal] = Field(default=None, ge=0)

    team_members: Optional[list[int]] = None

    @field_validator("capa_type", mode="before")
    @classmethod
    def validate_capa_type(cls, v):
        return _parse_enum(CAPAType, v, "capa_type")

    @field_validator("source_type", mode="before")
    @classmethod
    def validate_source_type(cls, v):
        return _parse_enum(CAPASourceType, v, "source_type")

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v):
        return _parse_enum(CAPAPriority, v, "priority")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        return _parse_enum(CAPAStatus, v, "status")

    @field_validator("root_cause_category", mode="before")
    @classmethod
    def validate_root_cause_category(cls, v):
        return _parse_enum(RootCauseCategory, v, "root_cause_category")

    @field_validator("verification_status", mode="before")
    @classmethod
    def validate_verification_status(cls, v):
        return _parse_enum(VerificationStatus, v, "verification_status")

    @field_validator("effectiveness_status", mode="before")
    @classmethod
    def validate_effectiveness_status(cls, v):
        return _parse_enum(EffectivenessStatus, v, "effectiveness_status")


class CAPAActionResponse(BaseModel):
    id: int
    capa_id: int
    action_type: str
    description: str
    expected_result: Optional[str] = None
    owner_id: UUID
    due_date: date
    status: str
    completion_evidence: Optional[str] = None
    completed_at: Optional[datetime] = None
    verified: bool
    verified_by_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    notes: Optional[str] = None
    is_overdue: bool
    days_until_due: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CAPAResponse(BaseModel):
    id: int
    capa_number: str
    capa_type: str
    source_type: str
    priority: str
    title: str
    description: str
    status: str
    owner_id: UUID
    opened_at: datetime
    due_date: date
    target_close_date: Optional[date] = None

    root_cause_analysis: Optional[str] = None
    root_cause_category: Optional[str] = None
    five_why_analysis: Optional[dict[str, Any]] = None

    containment_actions: Optional[str] = None
    corrective_actions: Optional[str] = None
    preventive_actions: Optional[str] = None

    verification_method: Optional[str] = None
    verification_status: str
    verified_by_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    verification_evidence: Optional[str] = None

    effectiveness_check_date: Optional[date] = None
    effectiveness_status: str
    effectiveness_checked_by_id: Optional[UUID] = None
    effectiveness_evidence: Optional[str] = None

    closed_by_id: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    closure_notes: Optional[str] = None
    lessons_learned: Optional[str] = None

    source_nc_id: Optional[int] = None

    estimated_cost_savings: Optional[Decimal] = None
    actual_cost_savings: Optional[Decimal] = None
    implementation_cost: Optional[Decimal] = None

    team_members: Optional[list[int]] = None

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    is_open: bool
    is_overdue: bool
    age_days: int
    open_actions_count: int
    overdue_actions_count: int
    can_verify: bool
    can_close: bool

    actions: list[CAPAActionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


def _capa_action_to_response(action: CAPAAction) -> CAPAActionResponse:
    def _val(v):
        return v.value if hasattr(v, "value") else v

    return CAPAActionResponse(
        id=action.id,
        capa_id=action.capa_id,
        action_type=_val(action.action_type),
        description=action.description,
        expected_result=action.expected_result,
        owner_id=action.owner_id,
        due_date=action.due_date,
        status=_val(action.status),
        completion_evidence=action.completion_evidence,
        completed_at=action.completed_at,
        verified=action.verified,
        verified_by_id=action.verified_by_id,
        verified_at=action.verified_at,
        verification_notes=action.verification_notes,
        notes=action.notes,
        is_overdue=action.is_overdue,
        days_until_due=action.days_until_due,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def capa_to_response(capa: CAPA) -> CAPAResponse:
    def _val(v):
        return v.value if hasattr(v, "value") else v

    actions = list(getattr(capa, "actions", []) or [])

    return CAPAResponse(
        id=capa.id,
        capa_number=capa.capa_number,
        capa_type=_val(capa.capa_type),
        source_type=_val(capa.source_type),
        priority=_val(capa.priority),
        title=capa.title,
        description=capa.description,
        status=_val(capa.status),
        owner_id=capa.owner_id,
        opened_at=capa.opened_at,
        due_date=capa.due_date,
        target_close_date=capa.target_close_date,
        root_cause_analysis=capa.root_cause_analysis,
        root_cause_category=_val(capa.root_cause_category) if capa.root_cause_category else None,
        five_why_analysis=capa.five_why_analysis,
        containment_actions=capa.containment_actions,
        corrective_actions=capa.corrective_actions,
        preventive_actions=capa.preventive_actions,
        verification_method=capa.verification_method,
        verification_status=_val(capa.verification_status),
        verified_by_id=capa.verified_by_id,
        verified_at=capa.verified_at,
        verification_evidence=capa.verification_evidence,
        effectiveness_check_date=capa.effectiveness_check_date,
        effectiveness_status=_val(capa.effectiveness_status),
        effectiveness_checked_by_id=capa.effectiveness_checked_by_id,
        effectiveness_evidence=capa.effectiveness_evidence,
        closed_by_id=capa.closed_by_id,
        closed_at=capa.closed_at,
        closure_notes=capa.closure_notes,
        lessons_learned=capa.lessons_learned,
        source_nc_id=capa.source_nc_id,
        estimated_cost_savings=capa.estimated_cost_savings,
        actual_cost_savings=capa.actual_cost_savings,
        implementation_cost=capa.implementation_cost,
        team_members=capa.team_members,
        created_at=capa.created_at,
        updated_at=capa.updated_at,
        deleted_at=capa.deleted_at,
        is_open=capa.is_open,
        is_overdue=capa.is_overdue,
        age_days=capa.age_days,
        open_actions_count=capa.open_actions_count,
        overdue_actions_count=capa.overdue_actions_count,
        can_verify=capa.can_verify,
        can_close=capa.can_close,
        actions=[_capa_action_to_response(a) for a in actions],
    )


class CAPAActionCreate(BaseModel):
    action_type: CAPAActionType
    description: str = Field(..., min_length=1)
    expected_result: Optional[str] = None
    owner_id: UUID
    due_date: date
    notes: Optional[str] = None

    @field_validator("action_type", mode="before")
    @classmethod
    def validate_action_type(cls, v):
        return _parse_enum(CAPAActionType, v, "action_type")


class CAPAActionUpdate(BaseModel):
    action_type: Optional[CAPAActionType] = None
    description: Optional[str] = Field(None, min_length=1)
    expected_result: Optional[str] = None
    owner_id: Optional[UUID] = None
    due_date: Optional[date] = None
    status: Optional[CAPAActionStatus] = None
    completion_evidence: Optional[str] = None
    completed_at: Optional[datetime] = None
    verified: Optional[bool] = None
    verified_by_id: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("action_type", mode="before")
    @classmethod
    def validate_action_type(cls, v):
        return _parse_enum(CAPAActionType, v, "action_type")

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v):
        return _parse_enum(CAPAActionStatus, v, "status")


# =============================================================================
# Inspection Schemas
# =============================================================================


class InspectionPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    product_id: Optional[int] = None
    station_id: Optional[int] = None
    inspection_type: InspectionType
    frequency: Optional[str] = Field(default=None, max_length=100)
    sampling_plan: Optional[dict[str, Any]] = None
    checkpoints_json: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True
    effective_date: Optional[date] = None
    revision: int = Field(default=1, ge=1)

    @field_validator("inspection_type", mode="before")
    @classmethod
    def validate_insp_type(cls, v):
        return _parse_enum(InspectionType, v, "inspection_type")


class InspectionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    product_id: Optional[int] = None
    station_id: Optional[int] = None
    inspection_type: Optional[InspectionType] = None
    frequency: Optional[str] = Field(default=None, max_length=100)
    sampling_plan: Optional[dict[str, Any]] = None
    checkpoints_json: Optional[list[dict[str, Any]]] = None
    is_active: Optional[bool] = None
    effective_date: Optional[date] = None
    revision: Optional[int] = Field(default=None, ge=1)

    @field_validator("inspection_type", mode="before")
    @classmethod
    def validate_insp_type(cls, v):
        return _parse_enum(InspectionType, v, "inspection_type")


class InspectionPlanResponse(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    product_id: Optional[int] = None
    station_id: Optional[int] = None
    inspection_type: str
    frequency: Optional[str] = None
    sampling_plan: Optional[dict[str, Any]] = None
    checkpoints_json: list[dict[str, Any]]
    is_active: bool
    effective_date: Optional[date] = None
    revision: int
    checkpoint_count: int
    critical_checkpoint_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def inspection_plan_to_response(plan: InspectionPlan) -> InspectionPlanResponse:
    def _val(v):
        return v.value if hasattr(v, "value") else v

    return InspectionPlanResponse(
        id=plan.id,
        name=plan.name,
        code=plan.code,
        description=plan.description,
        product_id=plan.product_id,
        station_id=plan.station_id,
        inspection_type=_val(plan.inspection_type),
        frequency=plan.frequency,
        sampling_plan=plan.sampling_plan,
        checkpoints_json=list(plan.checkpoints_json or []),
        is_active=plan.is_active,
        effective_date=plan.effective_date,
        revision=plan.revision,
        checkpoint_count=plan.checkpoint_count,
        critical_checkpoint_count=plan.critical_checkpoint_count,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        deleted_at=plan.deleted_at,
    )


class InspectionRecordCreate(BaseModel):
    inspection_plan_id: int = Field(..., gt=0)
    work_order_id: Optional[int] = None
    lot_number: Optional[str] = Field(None, max_length=100)
    sample_size: int = Field(..., gt=0)
    sample_ids: Optional[list[str]] = None
    overall_result: InspectionResult
    measurements_json: list[dict[str, Any]] = Field(default_factory=list)
    defects_found: int = Field(default=0, ge=0)
    defect_details: Optional[str] = None
    nc_id: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("overall_result", mode="before")
    @classmethod
    def validate_result(cls, v):
        return _parse_enum(InspectionResult, v, "overall_result")


class InspectionRecordUpdate(BaseModel):
    work_order_id: Optional[int] = None
    lot_number: Optional[str] = Field(None, max_length=100)
    sample_size: Optional[int] = Field(default=None, gt=0)
    sample_ids: Optional[list[str]] = None
    overall_result: Optional[InspectionResult] = None
    measurements_json: Optional[list[dict[str, Any]]] = None
    defects_found: Optional[int] = Field(default=None, ge=0)
    defect_details: Optional[str] = None
    nc_id: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("overall_result", mode="before")
    @classmethod
    def validate_result(cls, v):
        return _parse_enum(InspectionResult, v, "overall_result")


class InspectionRecordResponse(BaseModel):
    id: int
    inspection_plan_id: int
    work_order_id: Optional[int] = None
    lot_number: Optional[str] = None
    sample_size: int
    sample_ids: Optional[list[str]] = None
    inspected_by_id: UUID
    inspected_at: datetime
    overall_result: str
    measurements_json: list[dict[str, Any]]
    defects_found: int
    defect_details: Optional[str] = None
    nc_id: Optional[int] = None
    notes: Optional[str] = None
    pass_rate: Decimal
    is_pass: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def inspection_record_to_response(record: InspectionRecord) -> InspectionRecordResponse:
    def _val(v):
        return v.value if hasattr(v, "value") else v

    return InspectionRecordResponse(
        id=record.id,
        inspection_plan_id=record.inspection_plan_id,
        work_order_id=record.work_order_id,
        lot_number=record.lot_number,
        sample_size=record.sample_size,
        sample_ids=record.sample_ids,
        inspected_by_id=record.inspected_by_id,
        inspected_at=record.inspected_at,
        overall_result=_val(record.overall_result),
        measurements_json=list(record.measurements_json or []),
        defects_found=record.defects_found,
        defect_details=record.defect_details,
        nc_id=record.nc_id,
        notes=record.notes,
        pass_rate=record.pass_rate,
        is_pass=record.is_pass,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# =============================================================================
# Non-Conformance endpoints
# =============================================================================


@router.get("/non-conformances", response_model=PaginatedResponse[NonConformanceResponse])
async def list_non_conformances(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    nc_type: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    work_order_id: Optional[int] = Query(default=None),
    station_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> PaginatedResponse[NonConformanceResponse]:
    query = select(NonConformance)

    if not include_deleted:
        query = query.where(NonConformance.deleted_at.is_(None))

    if status is not None:
        _parse_enum(NCStatus, status, "status")
        query = query.where(NonConformance.status == NCStatus(status))

    if severity is not None:
        _parse_enum(NCSeverity, severity, "severity")
        query = query.where(NonConformance.severity == NCSeverity(severity))

    if nc_type is not None:
        _parse_enum(NCType, nc_type, "nc_type")
        query = query.where(NonConformance.nc_type == NCType(nc_type))

    if source is not None:
        _parse_enum(NCSource, source, "source")
        query = query.where(NonConformance.source == NCSource(source))

    if product_id is not None:
        query = query.where(NonConformance.product_id == product_id)

    if work_order_id is not None:
        query = query.where(NonConformance.work_order_id == work_order_id)

    if station_id is not None:
        query = query.where(NonConformance.station_id == station_id)

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                NonConformance.nc_number.ilike(term),
                NonConformance.title.ilike(term),
                NonConformance.description.ilike(term),
                NonConformance.lot_number.ilike(term),
                NonConformance.supplier_name.ilike(term),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(NonConformance.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return build_paginated_response(
        data=[nc_to_response(nc) for nc in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/non-conformances", response_model=APIResponse[NonConformanceResponse])
async def create_non_conformance(
    data: NonConformanceCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[NonConformanceResponse]:
    existing = await db.execute(
        select(NonConformance).where(NonConformance.nc_number == data.nc_number)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Non-conformance '{data.nc_number}' already exists")

    nc = NonConformance(
        nc_number=data.nc_number,
        nc_type=data.nc_type,
        source=data.source,
        severity=data.severity,
        product_id=data.product_id,
        work_order_id=data.work_order_id,
        station_id=data.station_id,
        lot_number=data.lot_number,
        quantity_affected=data.quantity_affected,
        quantity_inspected=data.quantity_inspected,
        title=data.title,
        description=data.description,
        specification_requirement=data.specification_requirement,
        actual_condition=data.actual_condition,
        root_cause_category=data.root_cause_category,
        root_cause_description=data.root_cause_description,
        detected_by_id=getattr(current_user, "id", None),
        detected_at=now_utc(),
        status=data.status,
        investigator_id=data.investigator_id,
        investigation_due_date=data.investigation_due_date,
        investigation_notes=data.investigation_notes,
        disposition=data.disposition,
        disposition_notes=data.disposition_notes,
        disposition_evidence=data.disposition_evidence,
        containment_actions=data.containment_actions,
        containment_verified=data.containment_verified,
        cost_impact=data.cost_impact,
        scrap_cost=data.scrap_cost,
        rework_cost=data.rework_cost,
        rework_hours=data.rework_hours,
        customer_notified=data.customer_notified,
        customer_notification_date=data.customer_notification_date,
        customer_notification_notes=data.customer_notification_notes,
        closure_notes=data.closure_notes,
        capa_id=data.capa_id,
        supplier_name=data.supplier_name,
        supplier_po_number=data.supplier_po_number,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
    )

    db.add(nc)
    await db.commit()
    await db.refresh(nc)

    return build_created_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.get("/non-conformances/{nc_id}", response_model=APIResponse[NonConformanceResponse])
async def get_non_conformance(
    nc_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
) -> APIResponse[NonConformanceResponse]:
    query = select(NonConformance).where(NonConformance.id == nc_id)
    if not include_deleted:
        query = query.where(NonConformance.deleted_at.is_(None))

    result = await db.execute(query)
    nc = result.scalar_one_or_none()

    if not nc:
        raise NotFoundError("Non-conformance", str(nc_id))

    return build_response(data=nc_to_response(nc))


@router.patch("/non-conformances/{nc_id}", response_model=APIResponse[NonConformanceResponse])
async def update_non_conformance(
    nc_id: int,
    data: NonConformanceUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[NonConformanceResponse]:
    result = await db.execute(
        select(NonConformance).where(
            NonConformance.id == nc_id,
            NonConformance.deleted_at.is_(None),
        )
    )
    nc = result.scalar_one_or_none()

    if not nc:
        raise NotFoundError("Non-conformance", str(nc_id))

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(nc, field, value)

    nc.updated_by_id = getattr(current_user, "id", None)
    nc.updated_at = now_utc()

    await db.commit()
    await db.refresh(nc)

    return build_updated_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.delete("/non-conformances/{nc_id}", response_model=APIResponse[None])
async def delete_non_conformance(
    nc_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
) -> APIResponse[None]:
    query = select(NonConformance).where(NonConformance.id == nc_id)
    if not hard_delete:
        query = query.where(NonConformance.deleted_at.is_(None))

    result = await db.execute(query)
    nc = result.scalar_one_or_none()

    if not nc:
        raise NotFoundError("Non-conformance", str(nc_id))

    if hard_delete:
        await db.delete(nc)
    else:
        nc.deleted_at = now_utc()
        nc.deleted_by_id = getattr(current_user, "id", None)

    await db.commit()

    return build_deleted_response(resource_name="Non-conformance")


@router.post("/non-conformances/{nc_id}/restore", response_model=APIResponse[NonConformanceResponse])
async def restore_non_conformance(
    nc_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[NonConformanceResponse]:
    result = await db.execute(
        select(NonConformance).where(
            NonConformance.id == nc_id,
            NonConformance.deleted_at.isnot(None),
        )
    )
    nc = result.scalar_one_or_none()

    if not nc:
        raise NotFoundError("Non-conformance", str(nc_id))

    nc.deleted_at = None
    nc.deleted_by_id = None
    nc.updated_by_id = getattr(current_user, "id", None)
    nc.updated_at = now_utc()

    await db.commit()
    await db.refresh(nc)

    return build_updated_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.post("/non-conformances/{nc_id}/close", response_model=APIResponse[NonConformanceResponse])
async def close_non_conformance(
    nc_id: int,
    db: DBSession,
    current_user: CurrentUser,
    closure_notes: Optional[str] = None,
) -> APIResponse[NonConformanceResponse]:
    result = await db.execute(
        select(NonConformance).where(
            NonConformance.id == nc_id,
            NonConformance.deleted_at.is_(None),
        )
    )
    nc = result.scalar_one_or_none()

    if not nc:
        raise NotFoundError("Non-conformance", str(nc_id))

    nc.status = NCStatus.CLOSED
    nc.closed_at = now_utc()
    nc.closed_by_id = getattr(current_user, "id", None)
    nc.closure_notes = closure_notes
    nc.updated_by_id = getattr(current_user, "id", None)
    nc.updated_at = now_utc()

    await db.commit()
    await db.refresh(nc)

    return build_updated_response(data=nc_to_response(nc), resource_name="Non-conformance")


# =============================================================================
# CAPA endpoints
# =============================================================================


@router.get("/capas", response_model=PaginatedResponse[CAPAResponse])
async def list_capas(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    source_type: Optional[str] = Query(default=None),
    overdue: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> PaginatedResponse[CAPAResponse]:
    query = select(CAPA).options(selectinload(CAPA.actions))

    if not include_deleted:
        query = query.where(CAPA.deleted_at.is_(None))

    if status is not None:
        _parse_enum(CAPAStatus, status, "status")
        query = query.where(CAPA.status == CAPAStatus(status))

    if priority is not None:
        _parse_enum(CAPAPriority, priority, "priority")
        query = query.where(CAPA.priority == CAPAPriority(priority))

    if source_type is not None:
        _parse_enum(CAPASourceType, source_type, "source_type")
        query = query.where(CAPA.source_type == CAPASourceType(source_type))

    if overdue is True:
        query = query.where(CAPA.due_date < date.today()).where(CAPA.closed_at.is_(None))
    if overdue is False:
        query = query.where(or_(CAPA.due_date >= date.today(), CAPA.closed_at.isnot(None)))

    if search:
        term = f"%{search}%"
        query = query.where(or_(CAPA.capa_number.ilike(term), CAPA.title.ilike(term), CAPA.description.ilike(term)))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(CAPA.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().unique().all()

    return build_paginated_response(
        data=[capa_to_response(c) for c in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/capas", response_model=APIResponse[CAPAResponse])
async def create_capa(
    data: CAPACreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    existing = await db.execute(select(CAPA).where(CAPA.capa_number == data.capa_number))
    if existing.scalar_one_or_none():
        raise ConflictError(f"CAPA '{data.capa_number}' already exists")

    capa = CAPA(
        capa_number=data.capa_number,
        capa_type=data.capa_type,
        source_type=data.source_type,
        priority=data.priority,
        title=data.title,
        description=data.description,
        status=data.status,
        owner_id=data.owner_id,
        opened_at=now_utc(),
        due_date=data.due_date,
        target_close_date=data.target_close_date,
        root_cause_analysis=data.root_cause_analysis,
        root_cause_category=data.root_cause_category,
        five_why_analysis=data.five_why_analysis,
        containment_actions=data.containment_actions,
        corrective_actions=data.corrective_actions,
        preventive_actions=data.preventive_actions,
        verification_method=data.verification_method,
        verification_status=data.verification_status,
        verified_by_id=data.verified_by_id,
        verified_at=data.verified_at,
        verification_evidence=data.verification_evidence,
        effectiveness_check_date=data.effectiveness_check_date,
        effectiveness_status=data.effectiveness_status,
        effectiveness_checked_by_id=data.effectiveness_checked_by_id,
        effectiveness_evidence=data.effectiveness_evidence,
        closure_notes=data.closure_notes,
        lessons_learned=data.lessons_learned,
        source_nc_id=data.source_nc_id,
        estimated_cost_savings=data.estimated_cost_savings,
        actual_cost_savings=data.actual_cost_savings,
        implementation_cost=data.implementation_cost,
        team_members=data.team_members,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
    )

    db.add(capa)
    await db.commit()
    await db.refresh(capa)

    return build_created_response(data=capa_to_response(capa), resource_name="CAPA")


@router.get("/capas/{capa_id}", response_model=APIResponse[CAPAResponse])
async def get_capa(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id).options(selectinload(CAPA.actions))
    if not include_deleted:
        query = query.where(CAPA.deleted_at.is_(None))

    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    return build_response(data=capa_to_response(capa))


@router.patch("/capas/{capa_id}", response_model=APIResponse[CAPAResponse])
async def update_capa(
    capa_id: int,
    data: CAPAUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(capa, field, value)

    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)

    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.delete("/capas/{capa_id}", response_model=APIResponse[None])
async def delete_capa(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
) -> APIResponse[None]:
    query = select(CAPA).where(CAPA.id == capa_id)
    if not hard_delete:
        query = query.where(CAPA.deleted_at.is_(None))

    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    if hard_delete:
        await db.delete(capa)
    else:
        capa.deleted_at = now_utc()
        capa.deleted_by_id = getattr(current_user, "id", None)

    await db.commit()

    return build_deleted_response(resource_name="CAPA")


@router.post("/capas/{capa_id}/restore", response_model=APIResponse[CAPAResponse])
async def restore_capa(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.isnot(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    capa.deleted_at = None
    capa.deleted_by_id = None
    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)

    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.get("/capas/{capa_id}/actions", response_model=PaginatedResponse[CAPAActionResponse])
async def list_capa_actions(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[CAPAActionResponse]:
    capa_exists = (await db.execute(select(CAPA.id).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)))).scalar_one_or_none()
    if not capa_exists:
        raise NotFoundError("CAPA", str(capa_id))

    query = select(CAPAAction).where(CAPAAction.capa_id == capa_id)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(CAPAAction.due_date.asc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return build_paginated_response(
        data=[_capa_action_to_response(a) for a in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/capas/{capa_id}/actions", response_model=APIResponse[CAPAActionResponse])
async def create_capa_action(
    capa_id: int,
    data: CAPAActionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAActionResponse]:
    capa = (await db.execute(select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)))).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    action = CAPAAction(
        capa_id=capa_id,
        action_type=data.action_type,
        description=data.description,
        expected_result=data.expected_result,
        owner_id=data.owner_id,
        due_date=data.due_date,
        status=CAPAActionStatus.OPEN,
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
    )

    db.add(action)
    await db.commit()
    await db.refresh(action)

    return build_created_response(data=_capa_action_to_response(action), resource_name="CAPA action")


@router.patch("/capas/{capa_id}/actions/{action_id}", response_model=APIResponse[CAPAActionResponse])
async def update_capa_action(
    capa_id: int,
    action_id: int,
    data: CAPAActionUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAActionResponse]:
    query = select(CAPAAction).where(CAPAAction.id == action_id, CAPAAction.capa_id == capa_id)
    action = (await db.execute(query)).scalar_one_or_none()
    if not action:
        raise NotFoundError("CAPA action", str(action_id))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(action, field, value)

    action.updated_by_id = getattr(current_user, "id", None)
    action.updated_at = now_utc()

    await db.commit()
    await db.refresh(action)

    return build_updated_response(data=_capa_action_to_response(action), resource_name="CAPA action")


@router.delete("/capas/{capa_id}/actions/{action_id}", response_model=APIResponse[None])
async def delete_capa_action(
    capa_id: int,
    action_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    query = select(CAPAAction).where(CAPAAction.id == action_id, CAPAAction.capa_id == capa_id)
    action = (await db.execute(query)).scalar_one_or_none()
    if not action:
        raise NotFoundError("CAPA action", str(action_id))

    await db.delete(action)
    await db.commit()

    return build_deleted_response(resource_name="CAPA action")


@router.post("/capas/{capa_id}/actions/{action_id}/complete", response_model=APIResponse[CAPAActionResponse])
async def complete_capa_action(
    capa_id: int,
    action_id: int,
    db: DBSession,
    current_user: CurrentUser,
    completion_evidence: Optional[str] = None,
) -> APIResponse[CAPAActionResponse]:
    action = (await db.execute(select(CAPAAction).where(CAPAAction.id == action_id, CAPAAction.capa_id == capa_id))).scalar_one_or_none()
    if not action:
        raise NotFoundError("CAPA action", str(action_id))

    action.status = CAPAActionStatus.COMPLETED
    action.completed_at = now_utc()
    action.completion_evidence = completion_evidence
    action.updated_by_id = getattr(current_user, "id", None)
    action.updated_at = now_utc()

    await db.commit()
    await db.refresh(action)

    return build_updated_response(data=_capa_action_to_response(action), resource_name="CAPA action")


# =============================================================================
# Inspection endpoints
# =============================================================================


@router.get("/inspection-plans", response_model=PaginatedResponse[InspectionPlanResponse])
async def list_inspection_plans(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    inspection_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
    station_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> PaginatedResponse[InspectionPlanResponse]:
    query = select(InspectionPlan)
    if not include_deleted:
        query = query.where(InspectionPlan.deleted_at.is_(None))

    if inspection_type is not None:
        _parse_enum(InspectionType, inspection_type, "inspection_type")
        query = query.where(InspectionPlan.inspection_type == InspectionType(inspection_type))

    if is_active is not None:
        query = query.where(InspectionPlan.is_active == is_active)

    if product_id is not None:
        query = query.where(InspectionPlan.product_id == product_id)

    if station_id is not None:
        query = query.where(InspectionPlan.station_id == station_id)

    if search:
        term = f"%{search}%"
        query = query.where(or_(InspectionPlan.name.ilike(term), InspectionPlan.code.ilike(term)))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0

    query = query.order_by(InspectionPlan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return build_paginated_response(
        data=[inspection_plan_to_response(p) for p in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/inspection-plans", response_model=APIResponse[InspectionPlanResponse])
async def create_inspection_plan(
    data: InspectionPlanCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionPlanResponse]:
    if data.code:
        existing = (await db.execute(select(InspectionPlan).where(InspectionPlan.code == data.code))).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Inspection plan code '{data.code}' already exists")

    plan = InspectionPlan(
        name=data.name,
        code=data.code,
        description=data.description,
        product_id=data.product_id,
        station_id=data.station_id,
        inspection_type=data.inspection_type,
        frequency=data.frequency,
        sampling_plan=data.sampling_plan,
        checkpoints_json=data.checkpoints_json,
        is_active=data.is_active,
        effective_date=data.effective_date,
        revision=data.revision,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return build_created_response(data=inspection_plan_to_response(plan), resource_name="Inspection plan")


@router.get("/inspection-plans/{plan_id}", response_model=APIResponse[InspectionPlanResponse])
async def get_inspection_plan(
    plan_id: int,
    db: DBSession,
    current_user: CurrentUser,
    include_deleted: bool = Query(default=False),
) -> APIResponse[InspectionPlanResponse]:
    query = select(InspectionPlan).where(InspectionPlan.id == plan_id)
    if not include_deleted:
        query = query.where(InspectionPlan.deleted_at.is_(None))

    plan = (await db.execute(query)).scalar_one_or_none()
    if not plan:
        raise NotFoundError("Inspection plan", str(plan_id))

    return build_response(data=inspection_plan_to_response(plan))


@router.patch("/inspection-plans/{plan_id}", response_model=APIResponse[InspectionPlanResponse])
async def update_inspection_plan(
    plan_id: int,
    data: InspectionPlanUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionPlanResponse]:
    plan = (await db.execute(select(InspectionPlan).where(InspectionPlan.id == plan_id, InspectionPlan.deleted_at.is_(None)))).scalar_one_or_none()
    if not plan:
        raise NotFoundError("Inspection plan", str(plan_id))

    update_data = data.model_dump(exclude_unset=True)

    if "code" in update_data and update_data["code"]:
        existing = (await db.execute(select(InspectionPlan).where(InspectionPlan.code == update_data["code"], InspectionPlan.id != plan_id))).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Inspection plan code '{update_data['code']}' already exists")

    for field, value in update_data.items():
        setattr(plan, field, value)

    plan.updated_by_id = getattr(current_user, "id", None)
    plan.updated_at = now_utc()

    await db.commit()
    await db.refresh(plan)

    return build_updated_response(data=inspection_plan_to_response(plan), resource_name="Inspection plan")


@router.delete("/inspection-plans/{plan_id}", response_model=APIResponse[None])
async def delete_inspection_plan(
    plan_id: int,
    db: DBSession,
    current_user: CurrentUser,
    hard_delete: bool = Query(default=False),
) -> APIResponse[None]:
    query = select(InspectionPlan).where(InspectionPlan.id == plan_id)
    if not hard_delete:
        query = query.where(InspectionPlan.deleted_at.is_(None))

    plan = (await db.execute(query)).scalar_one_or_none()
    if not plan:
        raise NotFoundError("Inspection plan", str(plan_id))

    if hard_delete:
        await db.delete(plan)
    else:
        plan.deleted_at = now_utc()
        plan.deleted_by_id = getattr(current_user, "id", None)

    await db.commit()

    return build_deleted_response(resource_name="Inspection plan")


@router.post("/inspection-plans/{plan_id}/restore", response_model=APIResponse[InspectionPlanResponse])
async def restore_inspection_plan(
    plan_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionPlanResponse]:
    plan = (await db.execute(select(InspectionPlan).where(InspectionPlan.id == plan_id, InspectionPlan.deleted_at.isnot(None)))).scalar_one_or_none()
    if not plan:
        raise NotFoundError("Inspection plan", str(plan_id))

    plan.deleted_at = None
    plan.deleted_by_id = None
    plan.updated_by_id = getattr(current_user, "id", None)
    plan.updated_at = now_utc()

    await db.commit()
    await db.refresh(plan)

    return build_updated_response(data=inspection_plan_to_response(plan), resource_name="Inspection plan")


@router.get("/inspection-records", response_model=PaginatedResponse[InspectionRecordResponse])
async def list_inspection_records(
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    inspection_plan_id: Optional[int] = Query(default=None),
    work_order_id: Optional[int] = Query(default=None),
    nc_id: Optional[int] = Query(default=None),
    overall_result: Optional[str] = Query(default=None),
) -> PaginatedResponse[InspectionRecordResponse]:
    query = select(InspectionRecord)

    if inspection_plan_id is not None:
        query = query.where(InspectionRecord.inspection_plan_id == inspection_plan_id)
    if work_order_id is not None:
        query = query.where(InspectionRecord.work_order_id == work_order_id)
    if nc_id is not None:
        query = query.where(InspectionRecord.nc_id == nc_id)
    if overall_result is not None:
        _parse_enum(InspectionResult, overall_result, "overall_result")
        query = query.where(InspectionRecord.overall_result == InspectionResult(overall_result))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0

    query = query.order_by(InspectionRecord.inspected_at.desc()).offset((page - 1) * page_size).limit(page_size)
    records = (await db.execute(query)).scalars().all()

    return build_paginated_response(
        data=[inspection_record_to_response(r) for r in records],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/inspection-records", response_model=APIResponse[InspectionRecordResponse])
async def create_inspection_record(
    data: InspectionRecordCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    plan = (await db.execute(select(InspectionPlan).where(InspectionPlan.id == data.inspection_plan_id, InspectionPlan.deleted_at.is_(None)))).scalar_one_or_none()
    if not plan:
        raise NotFoundError("Inspection plan", str(data.inspection_plan_id))

    record = InspectionRecord(
        inspection_plan_id=data.inspection_plan_id,
        work_order_id=data.work_order_id,
        lot_number=data.lot_number,
        sample_size=data.sample_size,
        sample_ids=data.sample_ids,
        inspected_by_id=getattr(current_user, "id", None),
        inspected_at=now_utc(),
        overall_result=data.overall_result,
        measurements_json=data.measurements_json,
        defects_found=data.defects_found,
        defect_details=data.defect_details,
        nc_id=data.nc_id,
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    return build_created_response(data=inspection_record_to_response(record), resource_name="Inspection record")


@router.get("/inspection-records/{record_id}", response_model=APIResponse[InspectionRecordResponse])
async def get_inspection_record(
    record_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection record", str(record_id))

    return build_response(data=inspection_record_to_response(record))


@router.patch("/inspection-records/{record_id}", response_model=APIResponse[InspectionRecordResponse])
async def update_inspection_record(
    record_id: int,
    data: InspectionRecordUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection record", str(record_id))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    record.updated_by_id = getattr(current_user, "id", None)
    record.updated_at = now_utc()

    await db.commit()
    await db.refresh(record)

    return build_updated_response(data=inspection_record_to_response(record), resource_name="Inspection record")


@router.delete("/inspection-records/{record_id}", response_model=APIResponse[None])
async def delete_inspection_record(
    record_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[None]:
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection record", str(record_id))

    await db.delete(record)
    await db.commit()

    return build_deleted_response(resource_name="Inspection record")
