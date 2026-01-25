"""
Escalation Policy API Endpoints.

Provides REST API for:
- Viewing and configuring escalation policies
- Detecting items needing escalation
- Getting escalation thresholds
- Running escalation scans
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sensei.core.config import settings
from sensei.services.escalation_policy import (
    EscalationPolicyService,
    EscalationJobRunner,
    EscalationPolicy,
    EscalationLevelConfig,
    EscalationItem,
    EscalationResult,
    EscalationTargetType,
    EscalationReason,
    EscalationLevel,
    EscalationStatus,
    EscalationPriority,
)


router = APIRouter(tags=["Escalation"])


def _deny_production_mutations() -> None:
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class EscalationLevelConfigSchema(BaseModel):
    """Schema for escalation level configuration."""
    
    level: str
    wait_hours: int
    escalate_to_role: str | None = None
    escalate_to_user_id: UUID | None = None
    notification_channels: list[str] = Field(default_factory=lambda: ["in_app", "email"])
    require_acknowledgment: bool = True
    acknowledgment_timeout_hours: int = 4


class EscalationPolicyResponse(BaseModel):
    """Response schema for an escalation policy."""
    
    name: str
    description: str
    target_type: str
    enabled: bool
    conditions: dict[str, Any]
    escalation_levels: list[EscalationLevelConfigSchema]
    notification_template: str | None
    auto_create_task: bool
    metadata: dict[str, Any]


class EscalationThresholdsResponse(BaseModel):
    """Response schema for escalation thresholds."""
    
    approval_thresholds: dict[str, dict[str, Any]]
    risk_thresholds: dict[str, str | None]


class EscalationItemResponse(BaseModel):
    """Response schema for an escalation item."""
    
    entity_id: UUID
    entity_type: str
    entity_name: str
    reason: str
    priority: str
    current_level: str
    status: str = "pending"
    owner_id: UUID | None = None
    owner_name: str | None = None
    escalated_to_id: UUID | None = None
    escalated_to_name: str | None = None
    escalated_at: datetime | None = None
    acknowledged_at: datetime | None = None
    due_at: datetime | None = None
    days_overdue: int = 0
    value: Decimal | None = None
    severity: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class EscalationResultResponse(BaseModel):
    """Response schema for escalation result."""
    
    policy_name: str
    target_type: str
    total_evaluated: int
    items_escalated: int
    items: list[EscalationItemResponse]
    evaluated_at: datetime
    errors: list[str]


class ApprovalInput(BaseModel):
    """Input schema for an approval to check."""
    
    id: UUID
    name: str
    status: str
    value: Decimal
    requested_at: datetime
    owner_id: UUID | None = None
    owner_name: str | None = None
    current_escalation_level: str | None = None
    account_name: str | None = None


class RiskInput(BaseModel):
    """Input schema for a risk to check."""
    
    id: UUID
    risk_number: str
    title: str
    status: str
    risk_level: str
    inherent_risk_score: int
    residual_risk_score: int | None = None
    risk_owner_id: UUID | None = None
    risk_owner_name: str | None = None
    target_resolution_date: datetime | None = None
    identified_date: datetime
    category: str
    current_escalation_level: str | None = None


class AndonInput(BaseModel):
    """Input schema for an Andon to check."""
    
    id: int
    andon_number: str
    description: str
    status: str
    severity: str
    reported_at: datetime
    acknowledged_at: datetime | None = None
    station_id: int
    station_name: str
    red_ack_minutes: int = 5
    yellow_ack_minutes: int = 15
    current_escalation_level: str | None = None
    assigned_to_id: UUID | None = None
    assigned_to_name: str | None = None


class DetectApprovalsRequest(BaseModel):
    """Request to detect aging approvals."""
    
    approvals: list[ApprovalInput]
    reference_time: datetime | None = None


class DetectRisksRequest(BaseModel):
    """Request to detect high-severity or overdue risks."""
    
    risks: list[RiskInput]
    reference_time: datetime | None = None


class DetectAndonsRequest(BaseModel):
    """Request to detect Andon SLA breaches."""
    
    andons: list[AndonInput]
    reference_time: datetime | None = None


class FullScanRequest(BaseModel):
    """Request for full escalation scan."""
    
    approvals: list[ApprovalInput] | None = None
    risks: list[RiskInput] | None = None
    andons: list[AndonInput] | None = None
    reference_time: datetime | None = None


class FullScanResponse(BaseModel):
    """Response for full escalation scan."""
    
    scan_time: str
    total_evaluated: int
    total_escalated: int
    by_policy: dict[str, dict[str, Any]]
    errors: list[str]


class UpdateThresholdRequest(BaseModel):
    """Request to update escalation thresholds."""
    
    level: str
    hours: int | None = None
    value: Decimal | None = None


class UpdateRiskThresholdRequest(BaseModel):
    """Request to update risk escalation threshold."""
    
    severity: str
    escalation_level: str | None = None


# ==============================================================================
# Helper Functions
# ==============================================================================

def _item_to_response(item: EscalationItem) -> EscalationItemResponse:
    """Convert EscalationItem to response schema."""
    return EscalationItemResponse(
        entity_id=item.entity_id,
        entity_type=item.entity_type.value,
        entity_name=item.entity_name,
        reason=item.reason.value,
        priority=item.priority.value,
        current_level=item.current_level.value,
        status=item.status.value,
        owner_id=item.owner_id,
        owner_name=item.owner_name,
        escalated_to_id=item.escalated_to_id,
        escalated_to_name=item.escalated_to_name,
        escalated_at=item.escalated_at,
        acknowledged_at=item.acknowledged_at,
        due_at=item.due_at,
        days_overdue=item.days_overdue,
        value=item.value,
        severity=item.severity,
        context=item.context,
    )


def _result_to_response(result: EscalationResult) -> EscalationResultResponse:
    """Convert EscalationResult to response schema."""
    return EscalationResultResponse(
        policy_name=result.policy_name,
        target_type=result.target_type.value,
        total_evaluated=result.total_evaluated,
        items_escalated=result.items_escalated,
        items=[_item_to_response(item) for item in result.items],
        evaluated_at=result.evaluated_at,
        errors=result.errors,
    )


def _policy_to_response(policy: EscalationPolicy) -> EscalationPolicyResponse:
    """Convert EscalationPolicy to response schema."""
    return EscalationPolicyResponse(
        name=policy.name,
        description=policy.description,
        target_type=policy.target_type.value,
        enabled=policy.enabled,
        conditions=policy.conditions,
        escalation_levels=[
            EscalationLevelConfigSchema(
                level=lc.level.value,
                wait_hours=lc.wait_hours,
                escalate_to_role=lc.escalate_to_role,
                escalate_to_user_id=lc.escalate_to_user_id,
                notification_channels=lc.notification_channels,
                require_acknowledgment=lc.require_acknowledgment,
                acknowledgment_timeout_hours=lc.acknowledgment_timeout_hours,
            )
            for lc in policy.escalation_levels
        ],
        notification_template=policy.notification_template,
        auto_create_task=policy.auto_create_task,
        metadata=policy.metadata,
    )


# Service singleton
_service = EscalationPolicyService()


# ==============================================================================
# Policy Endpoints
# ==============================================================================

@router.get("/policies", response_model=list[EscalationPolicyResponse])
def list_policies() -> list[EscalationPolicyResponse]:
    """List all configured escalation policies."""
    policies = _service.get_all_policies()
    return [_policy_to_response(p) for p in policies.values()]


@router.get("/policies/{name}", response_model=EscalationPolicyResponse)
def get_policy(name: str) -> EscalationPolicyResponse:
    """Get a specific escalation policy by name."""
    policy = _service.get_policy(name)
    if not policy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Policy '{name}' not found")
    return _policy_to_response(policy)


# ==============================================================================
# Threshold Endpoints
# ==============================================================================

@router.get("/thresholds", response_model=EscalationThresholdsResponse)
def get_thresholds() -> EscalationThresholdsResponse:
    """Get current escalation thresholds."""
    approval_thresholds = _service.get_approval_thresholds()
    risk_thresholds = _service.get_risk_thresholds()
    
    # Convert Decimal to float for JSON serialization
    for level, config in approval_thresholds.items():
        if isinstance(config.get("value"), Decimal):
            config["value"] = float(config["value"])
    
    # Convert EscalationLevel to string
    risk_thresh_str = {
        k: v.value if v else None
        for k, v in risk_thresholds.items()
    }
    
    return EscalationThresholdsResponse(
        approval_thresholds=approval_thresholds,
        risk_thresholds=risk_thresh_str,
    )


@router.put("/thresholds/approval")
def update_approval_threshold(request: UpdateThresholdRequest) -> dict[str, str]:
    """Update approval escalation threshold for a specific level."""
    _deny_production_mutations()
    try:
        level = EscalationLevel(request.level)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level: {request.level}. Must be one of: l1, l2, l3, l4",
        )
    
    _service.set_approval_threshold(level, hours=request.hours, value=request.value)
    return {"status": "updated", "level": level.value}


@router.put("/thresholds/risk")
def update_risk_threshold(request: UpdateRiskThresholdRequest) -> dict[str, str]:
    """Update risk severity escalation threshold."""
    _deny_production_mutations()
    valid_severities = ["low", "medium", "high", "critical"]
    if request.severity not in valid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity: {request.severity}. Must be one of: {valid_severities}",
        )
    
    escalation_level = None
    if request.escalation_level:
        try:
            escalation_level = EscalationLevel(request.escalation_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid level: {request.escalation_level}. Must be one of: l1, l2, l3, l4",
            )
    
    _service.set_risk_threshold(request.severity, escalation_level)
    return {"status": "updated", "severity": request.severity}


# ==============================================================================
# Detection Endpoints
# ==============================================================================

@router.post("/detect/approvals/aging", response_model=EscalationResultResponse)
def detect_aging_approvals(request: DetectApprovalsRequest) -> EscalationResultResponse:
    """Detect approvals needing escalation due to aging."""
    approvals = [a.model_dump() for a in request.approvals]
    result = _service.detect_aging_approvals(approvals, request.reference_time)
    return _result_to_response(result)


@router.post("/detect/approvals/value", response_model=EscalationResultResponse)
def detect_value_based_approvals(request: DetectApprovalsRequest) -> EscalationResultResponse:
    """Detect approvals needing escalation based on value thresholds."""
    approvals = [a.model_dump() for a in request.approvals]
    result = _service.detect_value_based_approvals(approvals)
    return _result_to_response(result)


@router.post("/detect/risks/severity", response_model=EscalationResultResponse)
def detect_high_severity_risks(request: DetectRisksRequest) -> EscalationResultResponse:
    """Detect high-severity risks needing escalation."""
    risks = [r.model_dump() for r in request.risks]
    result = _service.detect_high_severity_risks(risks, request.reference_time)
    return _result_to_response(result)


@router.post("/detect/risks/overdue", response_model=EscalationResultResponse)
def detect_overdue_risks(request: DetectRisksRequest) -> EscalationResultResponse:
    """Detect overdue risks needing escalation."""
    risks = [r.model_dump() for r in request.risks]
    result = _service.detect_overdue_risks(risks, request.reference_time)
    return _result_to_response(result)


@router.post("/detect/andons/sla-breach", response_model=EscalationResultResponse)
def detect_andon_sla_breaches(request: DetectAndonsRequest) -> EscalationResultResponse:
    """Detect Andons that have breached SLA."""
    andons = [a.model_dump() for a in request.andons]
    result = _service.detect_andon_sla_breaches(andons, request.reference_time)
    return _result_to_response(result)


@router.post("/detect/full-scan", response_model=FullScanResponse)
async def run_full_scan(request: FullScanRequest) -> FullScanResponse:
    """Run a full escalation scan across all entity types."""
    runner = EscalationJobRunner(service=_service)
    
    approvals = [a.model_dump() for a in request.approvals] if request.approvals else None
    risks = [r.model_dump() for r in request.risks] if request.risks else None
    andons = [a.model_dump() for a in request.andons] if request.andons else None
    
    summary = await runner.run_full_escalation_scan(
        approvals=approvals,
        risks=risks,
        andons=andons,
        reference_time=request.reference_time,
    )
    
    # Convert items to serializable format
    for policy_name, policy_data in summary.get("by_policy", {}).items():
        if "items" in policy_data:
            policy_data["items"] = [
                _item_to_response(item).model_dump()
                for item in policy_data["items"]
            ]
    
    return FullScanResponse(
        scan_time=summary["scan_time"],
        total_evaluated=summary["total_evaluated"],
        total_escalated=summary["total_escalated"],
        by_policy=summary["by_policy"],
        errors=summary["errors"],
    )


# ==============================================================================
# Reference Data Endpoints
# ==============================================================================

@router.get("/target-types")
def get_target_types() -> list[dict[str, str]]:
    """Get all escalation target types."""
    return [
        {"value": t.value, "label": t.value.replace("_", " ").title()}
        for t in EscalationTargetType
    ]


@router.get("/reasons")
def get_escalation_reasons() -> list[dict[str, str]]:
    """Get all escalation reasons."""
    return [
        {"value": r.value, "label": r.value.replace("_", " ").title()}
        for r in EscalationReason
    ]


@router.get("/levels")
def get_escalation_levels() -> list[dict[str, str]]:
    """Get all escalation levels."""
    level_descriptions = {
        "l1": "Direct Supervisor / Team Lead",
        "l2": "Department Manager",
        "l3": "Director / General Manager",
        "l4": "Executive",
    }
    return [
        {"value": l.value, "label": l.value.upper(), "description": level_descriptions.get(l.value, "")}
        for l in EscalationLevel
    ]


@router.get("/priorities")
def get_escalation_priorities() -> list[dict[str, str]]:
    """Get all escalation priorities."""
    return [
        {"value": p.value, "label": p.value.title()}
        for p in EscalationPriority
    ]


@router.get("/statuses")
def get_escalation_statuses() -> list[dict[str, str]]:
    """Get all escalation statuses."""
    return [
        {"value": s.value, "label": s.value.replace("_", " ").title()}
        for s in EscalationStatus
    ]


@router.get("/target-role/{level}/{target_type}")
def get_target_role(level: str, target_type: str) -> dict[str, str]:
    """Get the target role for an escalation level and target type."""
    try:
        esc_level = EscalationLevel(level)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid level: {level}")
    
    try:
        esc_type = EscalationTargetType(target_type)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid target type: {target_type}")
    
    role = _service.get_escalation_target_role(esc_level, esc_type)
    return {"level": level, "target_type": target_type, "role": role}
