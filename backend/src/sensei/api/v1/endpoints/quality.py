"""Quality Management Endpoints.

Provides CRUD and workflow operations for:
- Non-Conformance (NC) records
- Corrective/Preventive Actions (CAPA) and CAPA actions
- Inspection plans and inspection records

Follows the standard API response schema used across v1 endpoints.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Header
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
from sensei.models.quality_qms import QMSDocument, QualityAudit, AuditFinding, Gauge, CalibrationEvent, SCAR
from sensei.services.quality.msa_service import MSAService
from sensei.services.quality.customer_satisfaction_service import CustomerSatisfactionService
from sensei.services.quality.process_capability_service import ProcessCapabilityService
from sensei.services.quality.first_article_service import FirstArticleService
from sensei.services.quality.self_inspection_service import SelfInspectionService
from sensei.services.quality.lab_management_service import LabManagementService
from sensei.services.quality.aql_sampling_service import AQLSamplingService
from sensei.services.quality.traceability_service import TraceabilityService
from sensei.services.quality.change_point_service import ChangePointService
from sensei.services.quality.management_review_service import ManagementReviewService
from sensei.services.quality.persistent_qms import PersistentQMSService
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
from sensei.services.core.data_lineage import get_data_lineage_service
from sensei.services.core.common_thread import get_common_thread_service
from sensei.services.quality.quality_certification_gate import get_quality_certification_gate


logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# MSA / GRR Schemas
# =============================================================================


class MSAStudyCreate(BaseModel):
    gauge_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    study_type: str = Field(default="grr")
    parts_count: int = Field(default=10, ge=2)
    operators_count: int = Field(default=3, ge=2)
    trials_count: int = Field(default=2, ge=2)
    notes: Optional[str] = None


class MSAMeasurementCreate(BaseModel):
    operator_id: UUID
    part_id: str = Field(..., min_length=1, max_length=100)
    trial_number: int = Field(default=1, ge=1)
    measured_value: Decimal


class MSAResultResponse(BaseModel):
    repeatability_ev: Decimal
    reproducibility_av: Decimal
    grr: Decimal
    part_variation_pv: Decimal
    total_variation_tv: Decimal
    grr_percent: Decimal
    ndc: int

    model_config = ConfigDict(from_attributes=True)


class MSAMeasurementResponse(BaseModel):
    id: UUID
    study_id: UUID
    operator_id: UUID
    part_id: str
    trial_number: int
    measured_value: Decimal
    measured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MSAStudyResponse(BaseModel):
    id: UUID
    gauge_id: UUID
    name: str
    study_type: str
    status: str
    parts_count: int
    operators_count: int
    trials_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    result: Optional[MSAResultResponse] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Process Capability (Cp/Cpk) Schemas
# =============================================================================


class ProcessCapabilityStudyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    process_name: str = Field(..., min_length=1, max_length=255)
    characteristic: str = Field(..., min_length=1, max_length=255)
    lsl: Decimal
    usl: Decimal
    target: Optional[Decimal] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class ProcessCapabilityMeasurementCreate(BaseModel):
    measured_value: Decimal
    sample_label: Optional[str] = None


class ProcessCapabilityResultResponse(BaseModel):
    mean: Decimal
    std_dev: Decimal
    cp: Decimal
    cpk: Decimal
    cpu: Decimal
    cpl: Decimal
    sample_size: int

    model_config = ConfigDict(from_attributes=True)


class ProcessCapabilityMeasurementResponse(BaseModel):
    id: UUID
    study_id: UUID
    sample_label: Optional[str] = None
    measured_value: Decimal
    measured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessCapabilityStudyResponse(BaseModel):
    id: UUID
    name: str
    process_name: str
    characteristic: str
    status: str
    lsl: Decimal
    usl: Decimal
    target: Optional[Decimal] = None
    unit: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    result: Optional[ProcessCapabilityResultResponse] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Customer Satisfaction Schemas
# =============================================================================


class CustomerComplaintCreate(BaseModel):
    customer_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    received_at: Optional[datetime] = None
    status: Optional[str] = Field(default="received")
    lot_id: Optional[str] = Field(None, max_length=100)
    related_nc_id: Optional[int] = None
    related_capa_id: Optional[int] = None
    rma_number: Optional[str] = Field(None, max_length=50)
    root_cause: Optional[str] = None
    containment_actions: Optional[list[str]] = None
    corrective_actions: Optional[list[str]] = None


class CustomerComplaintUpdate(BaseModel):
    status: Optional[str] = None
    root_cause: Optional[str] = None
    containment_actions: Optional[list[str]] = None
    corrective_actions: Optional[list[str]] = None
    closed_at: Optional[datetime] = None


class CustomerComplaintResponse(BaseModel):
    id: UUID
    customer_id: Optional[UUID] = None
    title: str
    description: str
    received_at: datetime
    status: str
    lot_id: Optional[str] = None
    related_nc_id: Optional[int] = None
    related_capa_id: Optional[int] = None
    rma_number: Optional[str] = None
    root_cause: Optional[str] = None
    containment_actions: Optional[list[str]] = None
    corrective_actions: Optional[list[str]] = None
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerSurveyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default="active")
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    target_responses: Optional[int] = None
    notes: Optional[str] = None


class CustomerSurveyResponseCreate(BaseModel):
    customer_id: Optional[UUID] = None
    respondent_name: Optional[str] = None
    respondent_email: Optional[str] = None
    nps_score: int = Field(..., ge=0, le=10)
    comment: Optional[str] = None


class CustomerSurveyResponseOut(BaseModel):
    id: UUID
    survey_id: UUID
    customer_id: Optional[UUID] = None
    respondent_name: Optional[str] = None
    respondent_email: Optional[str] = None
    nps_score: int
    comment: Optional[str] = None
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerSurveyOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    target_responses: Optional[int] = None
    notes: Optional[str] = None
    responses: Optional[list[CustomerSurveyResponseOut]] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# FAI / AS9102 Schemas
# =============================================================================


class FAIInspectionCreate(BaseModel):
    inspection_number: str = Field(..., min_length=1, max_length=50)
    product_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    part_number: str = Field(..., min_length=1, max_length=100)
    revision: Optional[str] = None
    drawing_number: Optional[str] = None
    inspector_id: Optional[UUID] = None
    notes: Optional[str] = None


class FAIInspectionUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class FAICharacteristicCreate(BaseModel):
    characteristic_number: int = Field(..., ge=1)
    requirement: str = Field(..., min_length=1, max_length=255)
    nominal: Optional[Decimal] = None
    tolerance: Optional[str] = None
    actual: Optional[Decimal] = None
    result: str = Field(default="pending")
    method: Optional[str] = None
    tool_id: Optional[UUID] = None
    notes: Optional[str] = None


class FAICharacteristicResponse(BaseModel):
    id: UUID
    inspection_id: UUID
    characteristic_number: int
    requirement: str
    nominal: Optional[Decimal] = None
    tolerance: Optional[str] = None
    actual: Optional[Decimal] = None
    result: str
    method: Optional[str] = None
    tool_id: Optional[UUID] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FAIInspectionResponse(BaseModel):
    id: UUID
    inspection_number: str
    product_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    part_number: str
    revision: Optional[str] = None
    drawing_number: Optional[str] = None
    status: str
    inspector_id: Optional[UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    characteristics: Optional[list[FAICharacteristicResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Operator Self-Inspection Schemas
# =============================================================================


class SelfInspectionCreate(BaseModel):
    inspection_number: str = Field(..., min_length=1, max_length=50)
    work_order_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    operator_id: Optional[UUID] = None
    notes: Optional[str] = None


class SelfInspectionUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class SelfInspectionCheckCreate(BaseModel):
    characteristic: str = Field(..., min_length=1, max_length=255)
    specification: Optional[str] = None
    actual_value: Optional[str] = None
    result: str = Field(default="pending")
    notes: Optional[str] = None


class SelfInspectionCheckResponse(BaseModel):
    id: UUID
    inspection_id: UUID
    characteristic: str
    specification: Optional[str] = None
    actual_value: Optional[str] = None
    result: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SelfInspectionResponse(BaseModel):
    id: UUID
    inspection_number: str
    work_order_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    operator_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    checks: Optional[list[SelfInspectionCheckResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Lab Management Schemas
# =============================================================================


class LabTestMethodCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    standard: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    lower_spec: Optional[Decimal] = None
    upper_spec: Optional[Decimal] = None
    target_value: Optional[Decimal] = None
    status: Optional[str] = Field(default="active")


class LabTestMethodResponse(BaseModel):
    id: UUID
    name: str
    standard: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    lower_spec: Optional[Decimal] = None
    upper_spec: Optional[Decimal] = None
    target_value: Optional[Decimal] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class LabSampleCreate(BaseModel):
    sample_number: str = Field(..., min_length=1, max_length=50)
    product_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    lot_number: Optional[str] = None
    collected_at: Optional[datetime] = None
    collected_by_id: Optional[UUID] = None
    notes: Optional[str] = None


class LabSampleResponse(BaseModel):
    id: UUID
    sample_number: str
    product_id: Optional[UUID] = None
    work_order_id: Optional[UUID] = None
    lot_number: Optional[str] = None
    collected_at: datetime
    collected_by_id: Optional[UUID] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LabTestRunCreate(BaseModel):
    method_id: UUID
    result_value: Optional[Decimal] = None
    result_text: Optional[str] = None
    result_status: str = Field(default="pending")
    tester_id: Optional[UUID] = None
    notes: Optional[str] = None


class LabTestRunResponse(BaseModel):
    id: UUID
    sample_id: UUID
    method_id: UUID
    result_value: Optional[Decimal] = None
    result_text: Optional[str] = None
    result_status: str
    tested_at: datetime
    tester_id: Optional[UUID] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# AQL Sampling Schemas
# =============================================================================


class AQLSamplingPlanCreate(BaseModel):
    plan_code: str = Field(..., min_length=1, max_length=50)
    standard: Optional[str] = Field(default="ANSI/ASQ Z1.4")
    inspection_level: str = Field(default="II", max_length=10)
    aql_level: str = Field(default="1.0", max_length=10)
    lot_size_min: int = Field(..., ge=1)
    lot_size_max: int = Field(..., ge=1)
    sample_size: int = Field(..., ge=1)
    accept_limit: int = Field(..., ge=0)
    reject_limit: int = Field(..., ge=0)
    status: Optional[str] = Field(default="active")
    notes: Optional[str] = None


class AQLSamplingPlanResponse(BaseModel):
    id: UUID
    plan_code: str
    standard: str
    inspection_level: str
    aql_level: str
    lot_size_min: int
    lot_size_max: int
    sample_size: int
    accept_limit: int
    reject_limit: int
    status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AQLLotInspectionCreate(BaseModel):
    plan_id: UUID
    lot_number: str = Field(..., min_length=1, max_length=100)
    lot_size: int = Field(..., ge=1)
    sample_size: Optional[int] = Field(default=None, ge=1)
    defect_count: int = Field(..., ge=0)
    inspected_at: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    defects_json: Optional[list[dict]] = None
    notes: Optional[str] = None


class AQLLotInspectionResponse(BaseModel):
    id: UUID
    plan_id: UUID
    lot_number: str
    lot_size: int
    sample_size: int
    defect_count: int
    accept_limit: int
    reject_limit: int
    result: str
    inspected_at: datetime
    inspector_id: Optional[UUID] = None
    inspection_level: str
    aql_level: str
    defects_json: Optional[list[dict]] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Traceability Schemas
# =============================================================================


class TraceabilityMatrixCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default="active")
    product_id: Optional[int] = None
    work_order_id: Optional[int] = None
    lot_number: Optional[str] = Field(None, max_length=100)
    batch_id: Optional[str] = Field(None, max_length=100)
    external_reference: Optional[str] = Field(None, max_length=100)
    metadata_json: Optional[dict] = None


class TraceabilityMatrixResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    product_id: Optional[int] = None
    work_order_id: Optional[int] = None
    lot_number: Optional[str] = None
    batch_id: Optional[str] = None
    external_reference: Optional[str] = None
    metadata_json: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class TraceabilityLinkCreate(BaseModel):
    matrix_id: UUID
    link_type: str = Field(..., min_length=1, max_length=50)
    reference_id: str = Field(..., min_length=1, max_length=100)
    reference_table: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    metadata_json: Optional[dict] = None


class TraceabilityLinkResponse(BaseModel):
    id: UUID
    matrix_id: UUID
    link_type: str
    reference_id: str
    reference_table: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Change Point Control Schemas
# =============================================================================


class ChangePointStudyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    process_name: str = Field(..., min_length=1, max_length=255)
    characteristic: str = Field(..., min_length=1, max_length=255)
    method: Optional[str] = Field(default="mean_shift")
    sensitivity: Optional[Decimal] = None
    status: Optional[str] = Field(default="active")
    started_at: Optional[datetime] = None
    notes: Optional[str] = None
    metadata_json: Optional[dict] = None


class ChangePointObservationCreate(BaseModel):
    observed_at: Optional[datetime] = None
    value: Decimal
    sample_label: Optional[str] = None


class ChangePointEventResponse(BaseModel):
    id: UUID
    study_id: UUID
    detected_at: datetime
    index_position: int
    change_magnitude: Decimal
    confidence: Optional[Decimal] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChangePointObservationResponse(BaseModel):
    id: UUID
    study_id: UUID
    observed_at: datetime
    value: Decimal
    sample_label: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChangePointStudyResponse(BaseModel):
    id: UUID
    name: str
    process_name: str
    characteristic: str
    method: str
    sensitivity: Optional[Decimal] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    metadata_json: Optional[dict] = None
    observations: Optional[list[ChangePointObservationResponse]] = None
    events: Optional[list[ChangePointEventResponse]] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Management Review Schemas
# =============================================================================


class ManagementReviewCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    period_start: datetime
    period_end: datetime
    scheduled_for: datetime
    status: Optional[str] = Field(default="scheduled")
    notes: Optional[str] = None
    attendees: Optional[list[str]] = None
    metrics_snapshot: Optional[dict] = None


class ManagementReviewActionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    status: Optional[str] = Field(default="open")
    due_date: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    notes: Optional[str] = None


class ManagementReviewActionResponse(BaseModel):
    id: UUID
    review_id: UUID
    title: str
    status: str
    due_date: Optional[datetime] = None
    assignee_id: Optional[UUID] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ManagementReviewResponse(BaseModel):
    id: UUID
    title: str
    period_start: datetime
    period_end: datetime
    status: str
    scheduled_for: datetime
    held_at: Optional[datetime] = None
    notes: Optional[str] = None
    attendees: Optional[list[str]] = None
    metrics_snapshot: Optional[dict] = None
    actions: Optional[list[ManagementReviewActionResponse]] = None

    model_config = ConfigDict(from_attributes=True)


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


class NCRInvestigationData(BaseModel):
    root_cause_category: Optional[RootCauseCategory] = None
    root_cause_description: Optional[str] = None
    investigation_notes: Optional[str] = None

    @field_validator("root_cause_category", mode="before")
    @classmethod
    def validate_root_cause_category(cls, v):
        if v is None:
            return None
        return _parse_enum(RootCauseCategory, v, "root_cause_category")


class NCRDispositionData(BaseModel):
    disposition: NCDisposition
    notes: Optional[str] = None
    disposition_notes: Optional[str] = None

    @field_validator("disposition", mode="before")
    @classmethod
    def validate_disposition(cls, v):
        return _parse_enum(NCDisposition, v, "disposition")


class NCRCloseData(BaseModel):
    notes: Optional[str] = None


class NCRStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    by_disposition: dict[str, int]
    total_cost_impact: float
    average_resolution_days: float
    open_count: int
    overdue_count: int


class TimelineEventResponse(BaseModel):
    id: str
    type: str
    action: str
    description: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime
    metadata: Optional[dict[str, Any]] = None


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


class CAPAVerifyData(BaseModel):
    notes: Optional[str] = None
    verification_evidence: Optional[str] = None


class CAPARejectData(BaseModel):
    reason: str


class CAPACloseData(BaseModel):
    effectiveness_review: Optional[str] = None


class CAPAStatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    completion_rate: float
    average_completion_days: float
    open_count: int
    overdue_count: int
    verification_rate: float


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


class InspectionStatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    pass_rate: float
    total_inspected: int
    total_passed: int
    total_failed: int


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
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
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

    # Best-effort: capture lineage links (do not block NC creation).
    try:
        await get_data_lineage_service().capture_non_conformance_created(
            db,
            non_conformance_id=nc.id,
            product_id=nc.product_id,
            work_order_id=nc.work_order_id,
            created_by_id=getattr(current_user, "id", None),
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="non_conformance",
                entity_id=str(nc.id),
                reasoning_id=x_reasoning_id,
                created_by_id=getattr(current_user, "id", None),
                source="non_conformance_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to capture non-conformance lineage")

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


@router.get("/non-conformances/stats", response_model=APIResponse[NCRStatsResponse])
async def get_ncr_stats(
    db: DBSession,
    current_user: CurrentUser,
    from_date: Optional[date] = Query(None, alias="date_from"),
    to_date: Optional[date] = Query(None, alias="date_to"),
) -> APIResponse[NCRStatsResponse]:
    query = select(NonConformance).where(NonConformance.deleted_at.is_(None))
    if from_date:
        query = query.where(func.date(NonConformance.created_at) >= from_date)
    if to_date:
        query = query.where(func.date(NonConformance.created_at) <= to_date)

    result = await db.execute(query)
    ncs = result.scalars().all()

    stats = NCRStatsResponse(
        total=len(ncs),
        by_status={},
        by_severity={},
        by_disposition={},
        total_cost_impact=0.0,
        average_resolution_days=0.0,
        open_count=0,
        overdue_count=0,
    )

    resolution_times = []

    for nc in ncs:
        status = nc.status.value if hasattr(nc.status, "value") else str(nc.status)
        stats.by_status[status] = stats.by_status.get(status, 0) + 1
        
        severity = nc.severity.value if hasattr(nc.severity, "value") else str(nc.severity)
        stats.by_severity[severity] = stats.by_severity.get(severity, 0) + 1
        
        if nc.disposition:
            disp = nc.disposition.value if hasattr(nc.disposition, "value") else str(nc.disposition)
            stats.by_disposition[disp] = stats.by_disposition.get(disp, 0) + 1
            
        if nc.total_cost:
            stats.total_cost_impact += float(nc.total_cost)
            
        if nc.status != NCStatus.CLOSED:
            stats.open_count += 1
            if nc.investigation_due_date and nc.investigation_due_date < date.today():
                stats.overdue_count += 1
        
        if nc.closed_at:
            delta = nc.closed_at.date() - nc.created_at.date()
            resolution_times.append(delta.days)

    if resolution_times:
        stats.average_resolution_days = sum(resolution_times) / len(resolution_times)

    return build_response(data=stats)


@router.post("/non-conformances/{nc_id}/investigate", response_model=APIResponse[NonConformanceResponse])
async def investigate_non_conformance(
    nc_id: int,
    db: DBSession,
    current_user: CurrentUser,
    data: Optional[NCRInvestigationData] = None,
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

    if data:
        if data.root_cause_category:
            nc.root_cause_category = data.root_cause_category
        if data.root_cause_description:
            nc.root_cause_description = data.root_cause_description
        if data.investigation_notes:
            nc.investigation_notes = data.investigation_notes
    
    nc.investigation_completed_at = now_utc()
    nc.status = NCStatus.PENDING_DISPOSITION
    nc.updated_by_id = getattr(current_user, "id", None)
    nc.updated_at = now_utc()

    await db.commit()
    await db.refresh(nc)
    return build_updated_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.post("/non-conformances/{nc_id}/disposition", response_model=APIResponse[NonConformanceResponse])
async def disposition_non_conformance(
    nc_id: int,
    data: NCRDispositionData,
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

    nc.disposition = data.disposition
    nc.disposition_notes = data.notes or data.disposition_notes
    nc.disposition_at = now_utc()
    nc.disposition_by_id = getattr(current_user, "id", None)
    nc.status = NCStatus.DISPOSITIONED
    nc.updated_by_id = getattr(current_user, "id", None)
    nc.updated_at = now_utc()

    await db.commit()
    await db.refresh(nc)
    return build_updated_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.post("/non-conformances/{nc_id}/close", response_model=APIResponse[NonConformanceResponse])
async def close_non_conformance(
    nc_id: int,
    data: NCRCloseData,
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

    nc.status = NCStatus.CLOSED
    nc.closure_notes = data.notes
    nc.closed_at = now_utc()
    nc.closed_by_id = getattr(current_user, "id", None)
    nc.updated_by_id = getattr(current_user, "id", None)
    nc.updated_at = now_utc()

    await db.commit()
    await db.refresh(nc)
    return build_updated_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.get("/non-conformances/{nc_id}/timeline", response_model=APIResponse[list[TimelineEventResponse]])
async def get_ncr_timeline(
    nc_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[TimelineEventResponse]]:
    from sensei.models.audit_log import AuditLog

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "non_conformance",
            AuditLog.entity_id == str(nc_id)
        ).order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()
    
    events = [
        TimelineEventResponse(
            id=str(log.id),
            type=log.entity_type,
            action=log.action,
            description=log.description or f"{log.action} action on {log.entity_type}",
            user_id=str(log.user_id) if log.user_id else None,
            user_name=log.user_email,
            created_at=log.created_at,
            metadata=log.extra_data,
        )
        for log in logs
    ]
    
    return build_response(data=events)


@router.post("/non-conformances/{nc_id}/create-capa", response_model=APIResponse[CAPAResponse])
async def create_capa_from_nc_endpoint(
    nc_id: int,
    data: CAPACreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    result = await db.execute(
        select(NonConformance).where(
            NonConformance.id == nc_id,
            NonConformance.deleted_at.is_(None),
        )
    )
    nc = result.scalar_one_or_none()
    if not nc:
        raise NotFoundError("Non-conformance", str(nc_id))

    # Create CAPA
    capa = CAPA(
        capa_number=data.capa_number,
        capa_type=data.capa_type,
        source_type=data.source_type,
        priority=data.priority,
        title=data.title,
        description=data.description,
        status=CAPAStatus.OPEN,
        owner_id=data.owner_id,
        due_date=data.due_date,
        source_nc_id=nc.id,
        created_by_id=getattr(current_user, "id", None),
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(capa)
    
    nc.capa_id = capa.id # This might not work if capa.id is not yet available, but it should be on flush or commit
    nc.status = NCStatus.ESCALATED_TO_CAPA
    
    await db.commit()
    await db.refresh(capa)
    
    # We need to refresh NC too to get the linked capa_id correctly if needed, 
    # but we are returning the CAPA response.
    
    return build_created_response(data=capa_to_response(capa), resource_name="CAPA")


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
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
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

    # Best-effort: capture lineage links (do not block CAPA creation).
    try:
        await get_data_lineage_service().capture_capa_created(
            db,
            capa_id=capa.id,
            source_nc_id=capa.source_nc_id,
            created_by_id=getattr(current_user, "id", None),
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="capa",
                entity_id=str(capa.id),
                reasoning_id=x_reasoning_id,
                created_by_id=getattr(current_user, "id", None),
                source="capa_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to capture CAPA lineage")

    return build_created_response(data=capa_to_response(capa), resource_name="CAPA")


@router.get("/capas/stats", response_model=APIResponse[CAPAStatsResponse])
async def get_capa_stats(
    db: DBSession,
    current_user: CurrentUser,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> APIResponse[CAPAStatsResponse]:
    query = select(CAPA).where(CAPA.deleted_at.is_(None))
    if from_date:
        query = query.where(func.date(CAPA.created_at) >= from_date)
    if to_date:
        query = query.where(func.date(CAPA.created_at) <= to_date)

    result = await db.execute(query)
    capas = result.scalars().all()

    stats = CAPAStatsResponse(
        total=len(capas),
        by_type={},
        by_status={},
        completion_rate=0.0,
        average_completion_days=0.0,
        open_count=0,
        overdue_count=0,
        verification_rate=0.0,
    )

    completion_times = []
    verified_count = 0

    for capa in capas:
        ctype = capa.capa_type.value if hasattr(capa.capa_type, "value") else str(capa.capa_type)
        stats.by_type[ctype] = stats.by_type.get(ctype, 0) + 1
        
        status = capa.status.value if hasattr(capa.status, "value") else str(capa.status)
        stats.by_status[status] = stats.by_status.get(status, 0) + 1
        
        if capa.status == CAPAStatus.CLOSED:
            if capa.closed_at:
                delta = capa.closed_at.date() - capa.created_at.date()
                completion_times.append(delta.days)
        else:
            stats.open_count += 1
            if capa.due_date and capa.due_date < date.today():
                stats.overdue_count += 1
                
        if capa.verification_status == VerificationStatus.VERIFIED:
            verified_count += 1

    if stats.total > 0:
        stats.completion_rate = (stats.total - stats.open_count) / stats.total
        stats.verification_rate = verified_count / stats.total

    if completion_times:
        stats.average_completion_days = sum(completion_times) / len(completion_times)

    return build_response(data=stats)


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


@router.post("/capas/{capa_id}/start", response_model=APIResponse[CAPAResponse])
async def start_capa(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    capa.status = CAPAStatus.IN_PROGRESS
    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)
    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.post("/capas/{capa_id}/submit-for-verification", response_model=APIResponse[CAPAResponse])
async def submit_capa_for_verification(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    capa.status = CAPAStatus.VERIFICATION
    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)
    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.post("/capas/{capa_id}/verify", response_model=APIResponse[CAPAResponse])
async def verify_capa(
    capa_id: int,
    data: CAPAVerifyData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    capa.verification_status = VerificationStatus.VERIFIED
    capa.verified_by_id = getattr(current_user, "id", None)
    capa.verified_at = now_utc()
    capa.verification_evidence = data.verification_evidence
    capa.status = CAPAStatus.EFFECTIVENESS_CHECK
    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)
    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.post("/capas/{capa_id}/reject-verification", response_model=APIResponse[CAPAResponse])
async def reject_capa_verification(
    capa_id: int,
    data: CAPARejectData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    capa.verification_status = VerificationStatus.REJECTED
    capa.status = CAPAStatus.IN_PROGRESS
    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)
    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.post("/capas/{capa_id}/close", response_model=APIResponse[CAPAResponse])
async def close_capa_endpoint(
    capa_id: int,
    data: CAPACloseData,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CAPAResponse]:
    query = select(CAPA).where(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).options(selectinload(CAPA.actions))
    capa = (await db.execute(query)).scalar_one_or_none()
    if not capa:
        raise NotFoundError("CAPA", str(capa_id))

    capa.status = CAPAStatus.CLOSED
    capa.effectiveness_evidence = data.effectiveness_review
    capa.closed_at = now_utc()
    capa.closed_by_id = getattr(current_user, "id", None)
    capa.updated_by_id = getattr(current_user, "id", None)
    capa.updated_at = now_utc()

    await db.commit()
    await db.refresh(capa)
    return build_updated_response(data=capa_to_response(capa), resource_name="CAPA")


@router.get("/capas/{capa_id}/timeline", response_model=APIResponse[list[TimelineEventResponse]])
async def get_capa_timeline(
    capa_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[TimelineEventResponse]]:
    from sensei.models.audit_log import AuditLog

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "capa",
            AuditLog.entity_id == str(capa_id)
        ).order_by(AuditLog.created_at.desc())
    )
    logs = result.scalars().all()
    
    events = [
        TimelineEventResponse(
            id=str(log.id),
            type=log.entity_type,
            action=log.action,
            description=log.description or f"{log.action} action on {log.entity_type}",
            user_id=str(log.user_id) if log.user_id else None,
            user_name=log.user_email,
            created_at=log.created_at,
            metadata=log.extra_data,
        )
        for log in logs
    ]
    
    return build_response(data=events)


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
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
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

    # Best-effort: capture lineage links (do not block CAPA action creation).
    try:
        await get_data_lineage_service().capture_capa_action_created(
            db,
            capa_id=capa_id,
            action_id=action.id,
            created_by_id=getattr(current_user, "id", None),
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="capa_action",
                entity_id=str(action.id),
                reasoning_id=x_reasoning_id,
                created_by_id=getattr(current_user, "id", None),
                source="capa_action_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to capture CAPA action lineage")

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
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
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

    # Best-effort: capture lineage links (do not block inspection plan creation).
    try:
        await get_data_lineage_service().capture_inspection_plan_created(
            db,
            plan_id=plan.id,
            product_id=plan.product_id,
            station_id=plan.station_id,
            created_by_id=getattr(current_user, "id", None),
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="inspection_plan",
                entity_id=str(plan.id),
                reasoning_id=x_reasoning_id,
                created_by_id=getattr(current_user, "id", None),
                source="inspection_plan_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to capture inspection plan lineage")

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


@router.get("/inspections/stats", response_model=APIResponse[InspectionStatsResponse])
async def get_inspection_stats(
    db: DBSession,
    current_user: CurrentUser,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> APIResponse[InspectionStatsResponse]:
    query = select(InspectionRecord)
    if from_date:
        query = query.where(func.date(InspectionRecord.inspected_at) >= from_date)
    if to_date:
        query = query.where(func.date(InspectionRecord.inspected_at) <= to_date)

    result = await db.execute(query)
    records = result.scalars().all()

    stats = InspectionStatsResponse(
        total=len(records),
        by_type={},
        by_status={},
        pass_rate=0.0,
        total_inspected=0,
        total_passed=0,
        total_failed=0,
    )

    passed = 0
    for r in records:
        stats.total_inspected += r.sample_size
        if r.overall_result == InspectionResult.PASS:
            passed += 1
            stats.total_passed += r.sample_size
        else:
            stats.total_failed += r.sample_size
        
        stats.by_status["completed"] = stats.by_status.get("completed", 0) + 1

    if stats.total > 0:
        stats.pass_rate = passed / stats.total

    return build_response(data=stats)


@router.get("/inspections", response_model=PaginatedResponse[InspectionRecordResponse])
async def list_inspections(
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


@router.post("/inspections", response_model=APIResponse[InspectionRecordResponse])
async def create_inspection(
    data: InspectionRecordCreate,
    db: DBSession,
    current_user: CurrentUser,
    x_reasoning_id: str | None = Header(default=None, alias="X-Reasoning-Id"),
) -> APIResponse[InspectionRecordResponse]:
    plan = (await db.execute(select(InspectionPlan).where(InspectionPlan.id == data.inspection_plan_id, InspectionPlan.deleted_at.is_(None)))).scalar_one_or_none()
    if not plan:
        raise NotFoundError("Inspection plan", str(data.inspection_plan_id))

    await get_quality_certification_gate().assert_user_can_record_inspection(
        db,
        user_id=getattr(current_user, "id", None),
        station_id=getattr(plan, "station_id", None),
        product_id=getattr(plan, "product_id", None),
    )

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

    try:
        await get_data_lineage_service().capture_inspection_record_created(
            db,
            record_id=record.id,
            inspection_plan_id=record.inspection_plan_id,
            work_order_id=record.work_order_id,
            nc_id=record.nc_id,
            created_by_id=getattr(current_user, "id", None),
            reasoning_id=x_reasoning_id,
        )

        if x_reasoning_id:
            await get_common_thread_service().record_reasoning(
                db,
                entity_type="inspection_record",
                entity_id=str(record.id),
                reasoning_id=x_reasoning_id,
                created_by_id=getattr(current_user, "id", None),
                source="inspection_record_create",
            )

        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to capture inspection record lineage")

    return build_created_response(data=inspection_record_to_response(record), resource_name="Inspection")


@router.get("/inspections/{record_id}", response_model=APIResponse[InspectionRecordResponse])
async def get_inspection(
    record_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection", str(record_id))

    return build_response(data=inspection_record_to_response(record))


@router.post("/inspections/{record_id}/start", response_model=APIResponse[InspectionRecordResponse])
async def start_inspection(
    record_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    # Placeholder for start action
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection", str(record_id))
    return build_response(data=inspection_record_to_response(record))


@router.post("/inspections/{record_id}/complete", response_model=APIResponse[InspectionRecordResponse])
async def complete_inspection(
    record_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    # Placeholder for complete action
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection", str(record_id))
    return build_response(data=inspection_record_to_response(record))


@router.post("/inspections/{record_id}/cancel", response_model=APIResponse[InspectionRecordResponse])
async def cancel_inspection(
    record_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[InspectionRecordResponse]:
    # Placeholder for cancel action
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection", str(record_id))
    return build_response(data=inspection_record_to_response(record))


@router.post("/inspections/{record_id}/create-ncr", response_model=APIResponse[NonConformanceResponse])
async def create_ncr_from_inspection_endpoint(
    record_id: int,
    data: NonConformanceCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[NonConformanceResponse]:
    record = (await db.execute(select(InspectionRecord).where(InspectionRecord.id == record_id))).scalar_one_or_none()
    if not record:
        raise NotFoundError("Inspection", str(record_id))

    # Create NC
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
        detected_by_id=getattr(current_user, "id", None),
        detected_at=now_utc(),
        status=NCStatus.OPEN,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
    )
    db.add(nc)
    await db.flush()
    
    record.nc_id = nc.id
    
    await db.commit()
    await db.refresh(nc)
    
    return build_created_response(data=nc_to_response(nc), resource_name="Non-conformance")


@router.patch("/inspections/{record_id}", response_model=APIResponse[InspectionRecordResponse])
async def update_inspection(
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


@router.delete("/inspections/{record_id}", response_model=APIResponse[None])
async def delete_inspection(
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

# =============================================================================
# Advanced QMS Endpoints
# =============================================================================


@router.get("/documents", response_model=List[dict])
async def list_qms_documents(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """List all QMS documents."""
    svc = PersistentQMSService(db)
    docs = await svc.list_documents()
    return [d.to_dict() for d in docs]


@router.get("/audits", response_model=List[dict])
async def list_qms_audits(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """List all quality audits."""
    svc = PersistentQMSService(db)
    audits = await svc.list_audits()
    return [a.to_dict() for a in audits]


@router.get("/gauges", response_model=List[dict])
async def list_qms_gauges(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """List all measurement equipment."""
    svc = PersistentQMSService(db)
    gauges = await svc.list_gauges()
    return [g.to_dict() for g in gauges]


@router.get("/qms-stats", response_model=dict)
async def get_qms_stats(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Get advanced QMS statistics."""
    svc = PersistentQMSService(db)
    return await svc.get_qms_stats()


# =============================================================================
# MSA / GRR Endpoints
# =============================================================================


@router.get("/msa-studies", response_model=APIResponse[list[MSAStudyResponse]])
async def list_msa_studies(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[MSAStudyResponse]]:
    """List MSA studies."""
    svc = MSAService(db)
    studies = await svc.list_studies()
    response = [MSAStudyResponse.model_validate(study) for study in studies]
    return build_response(data=response)


@router.get("/msa-studies/{study_id}", response_model=APIResponse[MSAStudyResponse])
async def get_msa_study(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MSAStudyResponse]:
    """Get MSA study details."""
    svc = MSAService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("MSA study", str(study_id))
    return build_response(data=MSAStudyResponse.model_validate(study))


@router.post("/msa-studies", response_model=APIResponse[MSAStudyResponse])
async def create_msa_study(
    data: MSAStudyCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MSAStudyResponse]:
    """Create a new MSA study."""
    svc = MSAService(db)
    study = await svc.create_study(
        gauge_id=data.gauge_id,
        name=data.name,
        study_type=data.study_type,
        parts_count=data.parts_count,
        operators_count=data.operators_count,
        trials_count=data.trials_count,
        started_at=now_utc(),
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(study)
    return build_created_response(
        data=MSAStudyResponse.model_validate(study),
        resource_name="MSA study",
    )


@router.post("/msa-studies/{study_id}/measurements", response_model=APIResponse[MSAMeasurementResponse])
async def add_msa_measurement(
    study_id: UUID,
    data: MSAMeasurementCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MSAMeasurementResponse]:
    """Add measurement to an MSA study."""
    svc = MSAService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("MSA study", str(study_id))
    measurement = await svc.add_measurement(
        study_id=study_id,
        operator_id=data.operator_id,
        part_id=data.part_id,
        trial_number=data.trial_number,
        measured_value=data.measured_value,
    )
    await db.commit()
    await db.refresh(measurement)
    return build_created_response(
        data=MSAMeasurementResponse.model_validate(measurement),
        resource_name="MSA measurement",
    )


@router.post("/msa-studies/{study_id}/compute", response_model=APIResponse[MSAResultResponse])
async def compute_msa_grr(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[MSAResultResponse]:
    """Compute GRR results for an MSA study."""
    svc = MSAService(db)
    result = await svc.compute_grr(study_id)
    if not result:
        raise NotFoundError("MSA study", str(study_id))
    await db.commit()
    await db.refresh(result)
    return build_response(data=MSAResultResponse.model_validate(result))


# =============================================================================
# Process Capability (Cp/Cpk) Endpoints
# =============================================================================


@router.get("/capability-studies", response_model=APIResponse[list[ProcessCapabilityStudyResponse]])
async def list_capability_studies(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[ProcessCapabilityStudyResponse]]:
    """List process capability studies."""
    svc = ProcessCapabilityService(db)
    studies = await svc.list_studies()
    response = [ProcessCapabilityStudyResponse.model_validate(study) for study in studies]
    return build_response(data=response)


@router.get("/capability-studies/{study_id}", response_model=APIResponse[ProcessCapabilityStudyResponse])
async def get_capability_study(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProcessCapabilityStudyResponse]:
    """Get process capability study details."""
    svc = ProcessCapabilityService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("Process capability study", str(study_id))
    return build_response(data=ProcessCapabilityStudyResponse.model_validate(study))


@router.post("/capability-studies", response_model=APIResponse[ProcessCapabilityStudyResponse])
async def create_capability_study(
    data: ProcessCapabilityStudyCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProcessCapabilityStudyResponse]:
    """Create a new process capability study."""
    svc = ProcessCapabilityService(db)
    study = await svc.create_study(
        name=data.name,
        process_name=data.process_name,
        characteristic=data.characteristic,
        lsl=data.lsl,
        usl=data.usl,
        target=data.target,
        unit=data.unit,
        notes=data.notes,
        started_at=now_utc(),
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(study)
    return build_created_response(
        data=ProcessCapabilityStudyResponse.model_validate(study),
        resource_name="Process capability study",
    )


@router.post(
    "/capability-studies/{study_id}/measurements",
    response_model=APIResponse[ProcessCapabilityMeasurementResponse],
)
async def add_capability_measurement(
    study_id: UUID,
    data: ProcessCapabilityMeasurementCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProcessCapabilityMeasurementResponse]:
    """Add measurement to a process capability study."""
    svc = ProcessCapabilityService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("Process capability study", str(study_id))
    measurement = await svc.add_measurement(
        study_id=study_id,
        measured_value=data.measured_value,
        sample_label=data.sample_label,
    )
    await db.commit()
    await db.refresh(measurement)
    return build_created_response(
        data=ProcessCapabilityMeasurementResponse.model_validate(measurement),
        resource_name="Process capability measurement",
    )


@router.post(
    "/capability-studies/{study_id}/compute",
    response_model=APIResponse[ProcessCapabilityResultResponse],
)
async def compute_process_capability(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ProcessCapabilityResultResponse]:
    """Compute Cp/Cpk results for a process capability study."""
    svc = ProcessCapabilityService(db)
    result = await svc.compute_capability(study_id)
    if not result:
        raise NotFoundError("Process capability study", str(study_id))
    await db.commit()
    await db.refresh(result)
    return build_response(data=ProcessCapabilityResultResponse.model_validate(result))


# =============================================================================
# Customer Satisfaction Endpoints
# =============================================================================


@router.get("/customer-complaints", response_model=APIResponse[list[CustomerComplaintResponse]])
async def list_customer_complaints(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[CustomerComplaintResponse]]:
    svc = CustomerSatisfactionService(db)
    complaints = await svc.list_complaints()
    response = [CustomerComplaintResponse.model_validate(c) for c in complaints]
    return build_response(data=response)


@router.get("/customer-complaints/{complaint_id}", response_model=APIResponse[CustomerComplaintResponse])
async def get_customer_complaint(
    complaint_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerComplaintResponse]:
    svc = CustomerSatisfactionService(db)
    complaint = await svc.get_complaint(complaint_id)
    if not complaint:
        raise NotFoundError("Customer complaint", str(complaint_id))
    return build_response(data=CustomerComplaintResponse.model_validate(complaint))


@router.post("/customer-complaints", response_model=APIResponse[CustomerComplaintResponse])
async def create_customer_complaint(
    data: CustomerComplaintCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerComplaintResponse]:
    svc = CustomerSatisfactionService(db)
    complaint = await svc.create_complaint(
        customer_id=data.customer_id,
        title=data.title,
        description=data.description,
        received_at=data.received_at or now_utc(),
        status=data.status or "received",
        lot_id=data.lot_id,
        related_nc_id=data.related_nc_id,
        related_capa_id=data.related_capa_id,
        rma_number=data.rma_number,
        root_cause=data.root_cause,
        containment_actions=data.containment_actions,
        corrective_actions=data.corrective_actions,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(complaint)
    return build_created_response(
        data=CustomerComplaintResponse.model_validate(complaint),
        resource_name="Customer complaint",
    )


@router.patch("/customer-complaints/{complaint_id}", response_model=APIResponse[CustomerComplaintResponse])
async def update_customer_complaint(
    complaint_id: UUID,
    data: CustomerComplaintUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerComplaintResponse]:
    svc = CustomerSatisfactionService(db)
    complaint = await svc.get_complaint(complaint_id)
    if not complaint:
        raise NotFoundError("Customer complaint", str(complaint_id))

    update_payload = data.model_dump(exclude_unset=True)
    if "closed_at" in update_payload and update_payload["closed_at"] is None:
        update_payload.pop("closed_at")
    update_payload["updated_by_id"] = getattr(current_user, "id", None)
    update_payload["updated_at"] = now_utc()

    complaint = await svc.update_complaint(complaint, **update_payload)
    await db.commit()
    await db.refresh(complaint)
    return build_updated_response(
        data=CustomerComplaintResponse.model_validate(complaint),
        resource_name="Customer complaint",
    )


@router.post("/customer-complaints/{complaint_id}/close", response_model=APIResponse[CustomerComplaintResponse])
async def close_customer_complaint(
    complaint_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerComplaintResponse]:
    svc = CustomerSatisfactionService(db)
    complaint = await svc.get_complaint(complaint_id)
    if not complaint:
        raise NotFoundError("Customer complaint", str(complaint_id))
    complaint.updated_by_id = getattr(current_user, "id", None)
    complaint.updated_at = now_utc()
    complaint = await svc.close_complaint(complaint)
    await db.commit()
    await db.refresh(complaint)
    return build_updated_response(
        data=CustomerComplaintResponse.model_validate(complaint),
        resource_name="Customer complaint",
    )


@router.get("/customer-surveys", response_model=APIResponse[list[CustomerSurveyOut]])
async def list_customer_surveys(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[CustomerSurveyOut]]:
    svc = CustomerSatisfactionService(db)
    surveys = await svc.list_surveys()
    response = [CustomerSurveyOut.model_validate(s) for s in surveys]
    return build_response(data=response)


@router.get("/customer-surveys/{survey_id}", response_model=APIResponse[CustomerSurveyOut])
async def get_customer_survey(
    survey_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerSurveyOut]:
    svc = CustomerSatisfactionService(db)
    survey = await svc.get_survey(survey_id)
    if not survey:
        raise NotFoundError("Customer survey", str(survey_id))
    return build_response(data=CustomerSurveyOut.model_validate(survey))


@router.post("/customer-surveys", response_model=APIResponse[CustomerSurveyOut])
async def create_customer_survey(
    data: CustomerSurveyCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerSurveyOut]:
    svc = CustomerSatisfactionService(db)
    survey = await svc.create_survey(
        title=data.title,
        description=data.description,
        status=data.status or "active",
        period_start=data.period_start,
        period_end=data.period_end,
        target_responses=data.target_responses,
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(survey)
    return build_created_response(
        data=CustomerSurveyOut.model_validate(survey),
        resource_name="Customer survey",
    )


@router.post("/customer-surveys/{survey_id}/responses", response_model=APIResponse[CustomerSurveyResponseOut])
async def add_customer_survey_response(
    survey_id: UUID,
    data: CustomerSurveyResponseCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[CustomerSurveyResponseOut]:
    svc = CustomerSatisfactionService(db)
    survey = await svc.get_survey(survey_id)
    if not survey:
        raise NotFoundError("Customer survey", str(survey_id))
    response = await svc.add_response(
        survey_id=survey_id,
        nps_score=data.nps_score,
        customer_id=data.customer_id,
        respondent_name=data.respondent_name,
        respondent_email=data.respondent_email,
        comment=data.comment,
    )
    await db.commit()
    await db.refresh(response)
    return build_created_response(
        data=CustomerSurveyResponseOut.model_validate(response),
        resource_name="Customer survey response",
    )


@router.get("/customer-satisfaction/stats", response_model=APIResponse[dict])
async def get_customer_satisfaction_stats(
    db: DBSession,
    current_user: CurrentUser,
    survey_id: Optional[UUID] = None,
) -> APIResponse[dict]:
    svc = CustomerSatisfactionService(db)
    nps = await svc.compute_nps_stats(survey_id)
    complaints = await svc.complaint_stats()
    return build_response(data={"nps": nps, "complaints": complaints})


# =============================================================================
# FAI / AS9102 Endpoints
# =============================================================================


@router.get("/fai-inspections", response_model=APIResponse[list[FAIInspectionResponse]])
async def list_fai_inspections(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[FAIInspectionResponse]]:
    svc = FirstArticleService(db)
    inspections = await svc.list_inspections()
    response = [FAIInspectionResponse.model_validate(i) for i in inspections]
    return build_response(data=response)


@router.get("/fai-inspections/{inspection_id}", response_model=APIResponse[FAIInspectionResponse])
async def get_fai_inspection(
    inspection_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[FAIInspectionResponse]:
    svc = FirstArticleService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("FAI inspection", str(inspection_id))
    return build_response(data=FAIInspectionResponse.model_validate(inspection))


@router.post("/fai-inspections", response_model=APIResponse[FAIInspectionResponse])
async def create_fai_inspection(
    data: FAIInspectionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[FAIInspectionResponse]:
    svc = FirstArticleService(db)
    inspection = await svc.create_inspection(
        inspection_number=data.inspection_number,
        product_id=data.product_id,
        work_order_id=data.work_order_id,
        part_number=data.part_number,
        revision=data.revision,
        drawing_number=data.drawing_number,
        status="in_progress",
        inspector_id=data.inspector_id or getattr(current_user, "id", None),
        started_at=now_utc(),
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(inspection)
    return build_created_response(
        data=FAIInspectionResponse.model_validate(inspection),
        resource_name="FAI inspection",
    )


@router.patch("/fai-inspections/{inspection_id}", response_model=APIResponse[FAIInspectionResponse])
async def update_fai_inspection(
    inspection_id: UUID,
    data: FAIInspectionUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[FAIInspectionResponse]:
    svc = FirstArticleService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("FAI inspection", str(inspection_id))

    update_payload = data.model_dump(exclude_unset=True)
    update_payload["updated_by_id"] = getattr(current_user, "id", None)
    update_payload["updated_at"] = now_utc()
    inspection = await svc.update_inspection(inspection, **update_payload)
    await db.commit()
    await db.refresh(inspection)
    return build_updated_response(
        data=FAIInspectionResponse.model_validate(inspection),
        resource_name="FAI inspection",
    )


@router.post(
    "/fai-inspections/{inspection_id}/characteristics",
    response_model=APIResponse[FAICharacteristicResponse],
)
async def add_fai_characteristic(
    inspection_id: UUID,
    data: FAICharacteristicCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[FAICharacteristicResponse]:
    svc = FirstArticleService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("FAI inspection", str(inspection_id))
    characteristic = await svc.add_characteristic(
        inspection_id=inspection_id,
        characteristic_number=data.characteristic_number,
        requirement=data.requirement,
        nominal=data.nominal,
        tolerance=data.tolerance,
        actual=data.actual,
        result=data.result,
        method=data.method,
        tool_id=data.tool_id,
        notes=data.notes,
    )
    await db.commit()
    await db.refresh(characteristic)
    return build_created_response(
        data=FAICharacteristicResponse.model_validate(characteristic),
        resource_name="FAI characteristic",
    )


@router.post("/fai-inspections/{inspection_id}/close", response_model=APIResponse[FAIInspectionResponse])
async def close_fai_inspection(
    inspection_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[FAIInspectionResponse]:
    svc = FirstArticleService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("FAI inspection", str(inspection_id))
    inspection.updated_by_id = getattr(current_user, "id", None)
    inspection.updated_at = now_utc()
    inspection = await svc.close_inspection(inspection)
    await db.commit()
    await db.refresh(inspection)
    return build_updated_response(
        data=FAIInspectionResponse.model_validate(inspection),
        resource_name="FAI inspection",
    )


# =============================================================================
# Operator Self-Inspection Endpoints
# =============================================================================


@router.get("/self-inspections", response_model=APIResponse[list[SelfInspectionResponse]])
async def list_self_inspections(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[SelfInspectionResponse]]:
    svc = SelfInspectionService(db)
    inspections = await svc.list_inspections()
    response = [SelfInspectionResponse.model_validate(i) for i in inspections]
    return build_response(data=response)


@router.get("/self-inspections/{inspection_id}", response_model=APIResponse[SelfInspectionResponse])
async def get_self_inspection(
    inspection_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SelfInspectionResponse]:
    svc = SelfInspectionService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("Self inspection", str(inspection_id))
    return build_response(data=SelfInspectionResponse.model_validate(inspection))


@router.post("/self-inspections", response_model=APIResponse[SelfInspectionResponse])
async def create_self_inspection(
    data: SelfInspectionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SelfInspectionResponse]:
    svc = SelfInspectionService(db)
    inspection = await svc.create_inspection(
        inspection_number=data.inspection_number,
        work_order_id=data.work_order_id,
        product_id=data.product_id,
        operator_id=data.operator_id or getattr(current_user, "id", None),
        status="in_progress",
        started_at=now_utc(),
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(inspection)
    return build_created_response(
        data=SelfInspectionResponse.model_validate(inspection),
        resource_name="Self inspection",
    )


@router.patch("/self-inspections/{inspection_id}", response_model=APIResponse[SelfInspectionResponse])
async def update_self_inspection(
    inspection_id: UUID,
    data: SelfInspectionUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SelfInspectionResponse]:
    svc = SelfInspectionService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("Self inspection", str(inspection_id))
    update_payload = data.model_dump(exclude_unset=True)
    update_payload["updated_by_id"] = getattr(current_user, "id", None)
    update_payload["updated_at"] = now_utc()
    inspection = await svc.update_inspection(inspection, **update_payload)
    await db.commit()
    await db.refresh(inspection)
    return build_updated_response(
        data=SelfInspectionResponse.model_validate(inspection),
        resource_name="Self inspection",
    )


@router.post(
    "/self-inspections/{inspection_id}/checks",
    response_model=APIResponse[SelfInspectionCheckResponse],
)
async def add_self_inspection_check(
    inspection_id: UUID,
    data: SelfInspectionCheckCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SelfInspectionCheckResponse]:
    svc = SelfInspectionService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("Self inspection", str(inspection_id))
    check = await svc.add_check(
        inspection_id=inspection_id,
        characteristic=data.characteristic,
        specification=data.specification,
        actual_value=data.actual_value,
        result=data.result,
        notes=data.notes,
    )
    await db.commit()
    await db.refresh(check)
    return build_created_response(
        data=SelfInspectionCheckResponse.model_validate(check),
        resource_name="Self inspection check",
    )


@router.post("/self-inspections/{inspection_id}/close", response_model=APIResponse[SelfInspectionResponse])
async def close_self_inspection(
    inspection_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[SelfInspectionResponse]:
    svc = SelfInspectionService(db)
    inspection = await svc.get_inspection(inspection_id)
    if not inspection:
        raise NotFoundError("Self inspection", str(inspection_id))
    inspection.updated_by_id = getattr(current_user, "id", None)
    inspection.updated_at = now_utc()
    inspection = await svc.close_inspection(inspection)
    await db.commit()
    await db.refresh(inspection)
    return build_updated_response(
        data=SelfInspectionResponse.model_validate(inspection),
        resource_name="Self inspection",
    )


# =============================================================================
# Lab Management Endpoints
# =============================================================================


@router.get("/lab-methods", response_model=APIResponse[list[LabTestMethodResponse]])
async def list_lab_methods(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[LabTestMethodResponse]]:
    svc = LabManagementService(db)
    methods = await svc.list_methods()
    response = [LabTestMethodResponse.model_validate(m) for m in methods]
    return build_response(data=response)


@router.post("/lab-methods", response_model=APIResponse[LabTestMethodResponse])
async def create_lab_method(
    data: LabTestMethodCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[LabTestMethodResponse]:
    svc = LabManagementService(db)
    method = await svc.create_method(
        name=data.name,
        standard=data.standard,
        description=data.description,
        unit=data.unit,
        lower_spec=data.lower_spec,
        upper_spec=data.upper_spec,
        target_value=data.target_value,
        status=data.status or "active",
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(method)
    return build_created_response(
        data=LabTestMethodResponse.model_validate(method),
        resource_name="Lab test method",
    )


@router.get("/lab-samples", response_model=APIResponse[list[LabSampleResponse]])
async def list_lab_samples(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[LabSampleResponse]]:
    svc = LabManagementService(db)
    samples = await svc.list_samples()
    response = [LabSampleResponse.model_validate(s) for s in samples]
    return build_response(data=response)


@router.post("/lab-samples", response_model=APIResponse[LabSampleResponse])
async def create_lab_sample(
    data: LabSampleCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[LabSampleResponse]:
    svc = LabManagementService(db)
    sample = await svc.create_sample(
        sample_number=data.sample_number,
        product_id=data.product_id,
        work_order_id=data.work_order_id,
        lot_number=data.lot_number,
        collected_at=data.collected_at or now_utc(),
        collected_by_id=data.collected_by_id or getattr(current_user, "id", None),
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(sample)
    return build_created_response(
        data=LabSampleResponse.model_validate(sample),
        resource_name="Lab sample",
    )


@router.post("/lab-samples/{sample_id}/tests", response_model=APIResponse[LabTestRunResponse])
async def add_lab_test_run(
    sample_id: UUID,
    data: LabTestRunCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[LabTestRunResponse]:
    svc = LabManagementService(db)
    sample = await svc.get_sample(sample_id)
    if not sample:
        raise NotFoundError("Lab sample", str(sample_id))
    test_run = await svc.add_test_run(
        sample_id=sample_id,
        method_id=data.method_id,
        result_value=data.result_value,
        result_text=data.result_text,
        result_status=data.result_status,
        tester_id=data.tester_id or getattr(current_user, "id", None),
        notes=data.notes,
    )
    await db.commit()
    await db.refresh(test_run)
    return build_created_response(
        data=LabTestRunResponse.model_validate(test_run),
        resource_name="Lab test run",
    )


# =============================================================================
# AQL Sampling Endpoints
# =============================================================================


@router.get("/aql/plans", response_model=APIResponse[list[AQLSamplingPlanResponse]])
async def list_aql_plans(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[AQLSamplingPlanResponse]]:
    svc = AQLSamplingService(db)
    plans = await svc.list_plans()
    response = [AQLSamplingPlanResponse.model_validate(plan) for plan in plans]
    return build_response(data=response)


@router.post("/aql/plans", response_model=APIResponse[AQLSamplingPlanResponse])
async def create_aql_plan(
    data: AQLSamplingPlanCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AQLSamplingPlanResponse]:
    if data.lot_size_min > data.lot_size_max:
        raise ConflictError("lot_size_min cannot exceed lot_size_max")
    svc = AQLSamplingService(db)
    plan = await svc.create_plan(
        plan_code=data.plan_code,
        standard=data.standard or "ANSI/ASQ Z1.4",
        inspection_level=data.inspection_level,
        aql_level=data.aql_level,
        lot_size_min=data.lot_size_min,
        lot_size_max=data.lot_size_max,
        sample_size=data.sample_size,
        accept_limit=data.accept_limit,
        reject_limit=data.reject_limit,
        status=data.status or "active",
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(plan)
    return build_created_response(
        data=AQLSamplingPlanResponse.model_validate(plan),
        resource_name="AQL sampling plan",
    )


@router.get("/aql/inspections", response_model=APIResponse[list[AQLLotInspectionResponse]])
async def list_aql_inspections(
    db: DBSession,
    current_user: CurrentUser,
    plan_id: Optional[UUID] = Query(default=None),
) -> APIResponse[list[AQLLotInspectionResponse]]:
    svc = AQLSamplingService(db)
    inspections = await svc.list_inspections(plan_id=plan_id)
    response = [AQLLotInspectionResponse.model_validate(i) for i in inspections]
    return build_response(data=response)


@router.post("/aql/inspections", response_model=APIResponse[AQLLotInspectionResponse])
async def create_aql_inspection(
    data: AQLLotInspectionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[AQLLotInspectionResponse]:
    svc = AQLSamplingService(db)
    plan = await svc.get_plan(data.plan_id)
    if not plan:
        raise NotFoundError("AQL sampling plan", str(data.plan_id))
    try:
        inspection = await svc.create_inspection(
            plan=plan,
            lot_number=data.lot_number,
            lot_size=data.lot_size,
            sample_size=data.sample_size,
            defect_count=data.defect_count,
            inspected_at=data.inspected_at or now_utc(),
            inspector_id=data.inspector_id or getattr(current_user, "id", None),
            defects_json=data.defects_json,
            notes=data.notes,
            created_by_id=getattr(current_user, "id", None),
            updated_by_id=getattr(current_user, "id", None),
            owner_id=getattr(current_user, "id", None),
        )
    except ValueError as exc:
        raise ConflictError(str(exc))
    await db.commit()
    await db.refresh(inspection)
    return build_created_response(
        data=AQLLotInspectionResponse.model_validate(inspection),
        resource_name="AQL lot inspection",
    )


# =============================================================================
# Traceability Endpoints
# =============================================================================


@router.get("/traceability/matrices", response_model=APIResponse[list[TraceabilityMatrixResponse]])
async def list_traceability_matrices(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[TraceabilityMatrixResponse]]:
    svc = TraceabilityService(db)
    matrices = await svc.list_matrices()
    response = [TraceabilityMatrixResponse.model_validate(m) for m in matrices]
    return build_response(data=response)


@router.post("/traceability/matrices", response_model=APIResponse[TraceabilityMatrixResponse])
async def create_traceability_matrix(
    data: TraceabilityMatrixCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TraceabilityMatrixResponse]:
    svc = TraceabilityService(db)
    matrix = await svc.create_matrix(
        name=data.name,
        description=data.description,
        status=data.status or "active",
        product_id=data.product_id,
        work_order_id=data.work_order_id,
        lot_number=data.lot_number,
        batch_id=data.batch_id,
        external_reference=data.external_reference,
        metadata_json=data.metadata_json,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(matrix)
    return build_created_response(
        data=TraceabilityMatrixResponse.model_validate(matrix),
        resource_name="Traceability matrix",
    )


@router.get("/traceability/links", response_model=APIResponse[list[TraceabilityLinkResponse]])
async def list_traceability_links(
    db: DBSession,
    current_user: CurrentUser,
    matrix_id: Optional[UUID] = Query(default=None),
) -> APIResponse[list[TraceabilityLinkResponse]]:
    svc = TraceabilityService(db)
    links = await svc.list_links(matrix_id=matrix_id)
    response = [TraceabilityLinkResponse.model_validate(l) for l in links]
    return build_response(data=response)


@router.post("/traceability/links", response_model=APIResponse[TraceabilityLinkResponse])
async def create_traceability_link(
    data: TraceabilityLinkCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[TraceabilityLinkResponse]:
    svc = TraceabilityService(db)
    matrix = await svc.get_matrix(data.matrix_id)
    if not matrix:
        raise NotFoundError("Traceability matrix", str(data.matrix_id))
    link = await svc.add_link(
        matrix_id=data.matrix_id,
        link_type=data.link_type,
        reference_id=data.reference_id,
        reference_table=data.reference_table,
        notes=data.notes,
        metadata_json=data.metadata_json,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(link)
    return build_created_response(
        data=TraceabilityLinkResponse.model_validate(link),
        resource_name="Traceability link",
    )


# =============================================================================
# Change Point Control Endpoints
# =============================================================================


@router.get("/change-point/studies", response_model=APIResponse[list[ChangePointStudyResponse]])
async def list_change_point_studies(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[ChangePointStudyResponse]]:
    svc = ChangePointService(db)
    studies = await svc.list_studies()
    response = [ChangePointStudyResponse.model_validate(s) for s in studies]
    return build_response(data=response)


@router.post("/change-point/studies", response_model=APIResponse[ChangePointStudyResponse])
async def create_change_point_study(
    data: ChangePointStudyCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ChangePointStudyResponse]:
    svc = ChangePointService(db)
    study = await svc.create_study(
        name=data.name,
        process_name=data.process_name,
        characteristic=data.characteristic,
        method=data.method or "mean_shift",
        sensitivity=data.sensitivity,
        status=data.status or "active",
        started_at=data.started_at or now_utc(),
        notes=data.notes,
        metadata_json=data.metadata_json,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(study)
    return build_created_response(
        data=ChangePointStudyResponse.model_validate(study),
        resource_name="Change point study",
    )


@router.post("/change-point/studies/{study_id}/observations", response_model=APIResponse[ChangePointObservationResponse])
async def add_change_point_observation(
    study_id: UUID,
    data: ChangePointObservationCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ChangePointObservationResponse]:
    svc = ChangePointService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("Change point study", str(study_id))
    obs = await svc.add_observation(
        study_id=study_id,
        observed_at=data.observed_at or now_utc(),
        value=data.value,
        sample_label=data.sample_label,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(obs)
    return build_created_response(
        data=ChangePointObservationResponse.model_validate(obs),
        resource_name="Change point observation",
    )


@router.get("/change-point/studies/{study_id}/observations", response_model=APIResponse[list[ChangePointObservationResponse]])
async def list_change_point_observations(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[ChangePointObservationResponse]]:
    svc = ChangePointService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("Change point study", str(study_id))
    observations = await svc.list_observations(study_id)
    response = [ChangePointObservationResponse.model_validate(o) for o in observations]
    return build_response(data=response)


@router.get("/change-point/studies/{study_id}/events", response_model=APIResponse[list[ChangePointEventResponse]])
async def list_change_point_events(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[ChangePointEventResponse]]:
    svc = ChangePointService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("Change point study", str(study_id))
    events = await svc.list_events(study_id)
    response = [ChangePointEventResponse.model_validate(e) for e in events]
    return build_response(data=response)


@router.post("/change-point/studies/{study_id}/detect", response_model=APIResponse[ChangePointEventResponse | None])
async def detect_change_point(
    study_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ChangePointEventResponse | None]:
    svc = ChangePointService(db)
    study = await svc.get_study(study_id)
    if not study:
        raise NotFoundError("Change point study", str(study_id))
    event = await svc.detect_change_points(study)
    await db.commit()
    if event:
        await db.refresh(event)
    response = ChangePointEventResponse.model_validate(event) if event else None
    return build_response(data=response)


# =============================================================================
# Management Review Endpoints
# =============================================================================


@router.get("/management-reviews", response_model=APIResponse[list[ManagementReviewResponse]])
async def list_management_reviews(
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[list[ManagementReviewResponse]]:
    svc = ManagementReviewService(db)
    reviews = await svc.list_reviews()
    response = [ManagementReviewResponse.model_validate(r) for r in reviews]
    return build_response(data=response)


@router.post("/management-reviews", response_model=APIResponse[ManagementReviewResponse])
async def create_management_review(
    data: ManagementReviewCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ManagementReviewResponse]:
    svc = ManagementReviewService(db)
    review = await svc.create_review(
        title=data.title,
        period_start=data.period_start,
        period_end=data.period_end,
        status=data.status or "scheduled",
        scheduled_for=data.scheduled_for,
        notes=data.notes,
        attendees=data.attendees,
        metrics_snapshot=data.metrics_snapshot,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(review)
    return build_created_response(
        data=ManagementReviewResponse.model_validate(review),
        resource_name="Management review",
    )


@router.post("/management-reviews/{review_id}/actions", response_model=APIResponse[ManagementReviewActionResponse])
async def add_management_review_action(
    review_id: UUID,
    data: ManagementReviewActionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ManagementReviewActionResponse]:
    svc = ManagementReviewService(db)
    review = await svc.get_review(review_id)
    if not review:
        raise NotFoundError("Management review", str(review_id))
    action = await svc.add_action(
        review_id=review_id,
        title=data.title,
        status=data.status or "open",
        due_date=data.due_date,
        assignee_id=data.assignee_id,
        notes=data.notes,
        created_by_id=getattr(current_user, "id", None),
        updated_by_id=getattr(current_user, "id", None),
        owner_id=getattr(current_user, "id", None),
    )
    await db.commit()
    await db.refresh(action)
    return build_created_response(
        data=ManagementReviewActionResponse.model_validate(action),
        resource_name="Management review action",
    )


@router.get("/management-reviews/actions", response_model=APIResponse[list[ManagementReviewActionResponse]])
async def list_management_review_actions(
    db: DBSession,
    current_user: CurrentUser,
    review_id: Optional[UUID] = Query(default=None),
) -> APIResponse[list[ManagementReviewActionResponse]]:
    svc = ManagementReviewService(db)
    actions = await svc.list_actions(review_id=review_id)
    response = [ManagementReviewActionResponse.model_validate(a) for a in actions]
    return build_response(data=response)


@router.post("/management-reviews/{review_id}/close", response_model=APIResponse[ManagementReviewResponse])
async def close_management_review(
    review_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> APIResponse[ManagementReviewResponse]:
    svc = ManagementReviewService(db)
    review = await svc.get_review(review_id)
    if not review:
        raise NotFoundError("Management review", str(review_id))
    review.updated_by_id = getattr(current_user, "id", None)
    review.updated_at = now_utc()
    review = await svc.close_review(review)
    await db.commit()
    await db.refresh(review)
    return build_updated_response(
        data=ManagementReviewResponse.model_validate(review),
        resource_name="Management review",
    )
