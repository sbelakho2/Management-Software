"""
RBAC Security Audit API Endpoints.

Provides REST API for security auditing of RBAC and Audit Logs.
Includes verification, findings management, and compliance reporting.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from sensei.api.deps import CurrentSuperuser
from sensei.services.core.rbac_security_audit import (
    RBACSecurityAuditService,
    AuditSeverity,
    AuditCategory,
    get_rbac_security_audit_service,
)

router = APIRouter()


# ===== Request/Response Schemas =====


class RegisterRoleRequest(BaseModel):
    """Request to register a role for audit."""
    
    role_id: str = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    display_name: str = Field(..., description="Display name")
    role_type: str | None = Field(None, description="Role type")
    is_system: bool = Field(False, description="Is system role")
    is_active: bool = Field(True, description="Is active")
    hierarchy_level: int = Field(100, ge=1, le=1000, description="Hierarchy level")
    permission_count: int = Field(0, ge=0, description="Number of permissions")
    user_count: int = Field(0, ge=0, description="Number of users")


class RegisterPermissionRequest(BaseModel):
    """Request to register a permission for audit."""
    
    permission_id: str = Field(..., description="Permission ID")
    name: str = Field(..., description="Permission name")
    display_name: str = Field(..., description="Display name")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    is_system: bool = Field(False, description="Is system permission")
    role_count: int = Field(0, ge=0, description="Number of roles")


class RegisterUserRoleRequest(BaseModel):
    """Request to register a user-role assignment."""
    
    user_id: str = Field(..., description="User ID")
    user_email: str = Field(..., description="User email")
    role_id: str = Field(..., description="Role ID")
    role_name: str = Field(..., description="Role name")
    assigned_at: str = Field(..., description="Assignment date (ISO format)")
    assigned_by_id: str | None = Field(None, description="Assigned by user ID")
    expires_at: str | None = Field(None, description="Expiration date (ISO format)")
    is_active: bool = Field(True, description="Is active")


class RegisterAuditLogRequest(BaseModel):
    """Request to register an audit log entry."""
    
    log_id: str = Field(..., description="Log ID")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")
    action: str = Field(..., description="Action performed")
    created_at: str = Field(..., description="Created at (ISO format)")
    user_id: str | None = Field(None, description="User ID")
    user_email: str | None = Field(None, description="User email")
    ip_address: str | None = Field(None, description="IP address")
    has_old_values: bool = Field(False, description="Has old values")
    has_new_values: bool = Field(False, description="Has new values")
    has_changed_fields: bool = Field(False, description="Has changed fields")


class RecordAccessRequest(BaseModel):
    """Request to record an access pattern."""
    
    user_id: str = Field(..., description="User ID")
    user_email: str = Field(..., description="User email")
    action: str = Field(..., description="Action")
    resource: str = Field(..., description="Resource")
    access_time: str = Field(..., description="Access time (ISO format)")
    entity_id: str | None = Field(None, description="Entity ID")


class ResolveFindingRequest(BaseModel):
    """Request to resolve a finding."""
    
    resolved_by: str = Field(..., description="User resolving the finding")


class RoleResponse(BaseModel):
    """Role response."""
    
    id: str
    name: str
    display_name: str
    role_type: str | None
    is_system: bool
    is_active: bool
    hierarchy_level: int
    permission_count: int
    user_count: int


class PermissionResponse(BaseModel):
    """Permission response."""
    
    id: str
    name: str
    display_name: str
    resource: str
    action: str
    is_system: bool
    role_count: int


class UserRoleResponse(BaseModel):
    """User role assignment response."""
    
    user_id: str
    user_email: str
    role_id: str
    role_name: str
    assigned_at: str
    assigned_by_id: str | None
    expires_at: str | None
    is_active: bool
    is_expired: bool


class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    
    id: str
    entity_type: str
    entity_id: str
    action: str
    user_id: str | None
    user_email: str | None
    created_at: str
    ip_address: str | None
    has_old_values: bool
    has_new_values: bool
    has_changed_fields: bool


class AccessPatternResponse(BaseModel):
    """Access pattern response."""
    
    user_id: str
    user_email: str
    action: str
    resource: str
    count: int
    first_access: str
    last_access: str
    unique_entities: int


class FindingResponse(BaseModel):
    """Audit finding response."""
    
    id: str
    category: str
    severity: str
    title: str
    description: str
    affected_entity_type: str | None
    affected_entity_id: str | None
    recommendation: str | None
    evidence: dict
    detected_at: str
    resolved: bool
    resolved_at: str | None
    resolved_by: str | None


class FindingsSummaryResponse(BaseModel):
    """Findings summary response."""
    
    critical: int
    high: int
    medium: int
    low: int
    info: int


class ComplianceReportResponse(BaseModel):
    """Compliance report response."""
    
    report_id: str
    generated_at: str
    status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    findings_by_severity: dict
    findings: list[FindingResponse]
    role_summary: dict
    permission_summary: dict
    user_assignment_summary: dict
    audit_log_summary: dict
    recommendations: list[str]


class VerificationResultResponse(BaseModel):
    """Verification result response."""
    
    check_name: str
    findings_count: int
    findings: list[FindingResponse]


# ===== Helper Functions =====


def get_service() -> RBACSecurityAuditService:
    """Get the RBAC security audit service instance."""
    return get_rbac_security_audit_service()


def validate_uuid(uuid_str: str, field_name: str) -> UUID:
    """Validate and convert UUID string."""
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID for {field_name}: {uuid_str}",
        )


def validate_severity(severity: str) -> AuditSeverity:
    """Validate and convert severity string."""
    try:
        return AuditSeverity(severity)
    except ValueError:
        valid = [s.value for s in AuditSeverity]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity: {severity}. Valid: {valid}",
        )


def validate_category(category: str) -> AuditCategory:
    """Validate and convert category string."""
    try:
        return AuditCategory(category)
    except ValueError:
        valid = [c.value for c in AuditCategory]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}. Valid: {valid}",
        )


# ===== Role Registration Endpoints =====


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a role",
    description="Register a role for security audit verification.",
)
def register_role(request: RegisterRoleRequest, current_user: CurrentSuperuser) -> RoleResponse:
    """Register a role for audit."""
    service = get_service()
    
    role_id = validate_uuid(request.role_id, "role_id")
    
    role = service.register_role(
        role_id=role_id,
        name=request.name,
        display_name=request.display_name,
        role_type=request.role_type,
        is_system=request.is_system,
        is_active=request.is_active,
        hierarchy_level=request.hierarchy_level,
        permission_count=request.permission_count,
        user_count=request.user_count,
    )
    
    return RoleResponse(**role.to_dict())


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="Get all roles",
    description="Get all registered roles.",
)
def get_roles(current_user: CurrentSuperuser) -> list[RoleResponse]:
    """Get all registered roles."""
    service = get_service()
    roles = service.get_all_roles()
    return [RoleResponse(**r.to_dict()) for r in roles]


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Get a role",
    description="Get a role by ID.",
)
def get_role(role_id: str, current_user: CurrentSuperuser) -> RoleResponse:
    """Get a role by ID."""
    service = get_service()
    
    rid = validate_uuid(role_id, "role_id")
    role = service.get_role(rid)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role not found: {role_id}",
        )
    
    return RoleResponse(**role.to_dict())


# ===== Permission Registration Endpoints =====


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a permission",
    description="Register a permission for security audit verification.",
)
def register_permission(request: RegisterPermissionRequest, current_user: CurrentSuperuser) -> PermissionResponse:
    """Register a permission for audit."""
    service = get_service()
    
    perm_id = validate_uuid(request.permission_id, "permission_id")
    
    perm = service.register_permission(
        permission_id=perm_id,
        name=request.name,
        display_name=request.display_name,
        resource=request.resource,
        action=request.action,
        is_system=request.is_system,
        role_count=request.role_count,
    )
    
    return PermissionResponse(**perm.to_dict())


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    summary="Get all permissions",
    description="Get all registered permissions.",
)
def get_permissions(current_user: CurrentSuperuser) -> list[PermissionResponse]:
    """Get all registered permissions."""
    service = get_service()
    perms = service.get_all_permissions()
    return [PermissionResponse(**p.to_dict()) for p in perms]


# ===== User-Role Assignment Endpoints =====


@router.post(
    "/user-roles",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user-role assignment",
    description="Register a user-role assignment for audit.",
)
def register_user_role(request: RegisterUserRoleRequest, current_user: CurrentSuperuser) -> UserRoleResponse:
    """Register a user-role assignment."""
    service = get_service()
    
    user_id = validate_uuid(request.user_id, "user_id")
    role_id = validate_uuid(request.role_id, "role_id")
    assigned_by_id = validate_uuid(request.assigned_by_id, "assigned_by_id") if request.assigned_by_id else None
    
    assigned_at = datetime.fromisoformat(request.assigned_at)
    expires_at = datetime.fromisoformat(request.expires_at) if request.expires_at else None
    
    assignment = service.register_user_role(
        user_id=user_id,
        user_email=request.user_email,
        role_id=role_id,
        role_name=request.role_name,
        assigned_at=assigned_at,
        assigned_by_id=assigned_by_id,
        expires_at=expires_at,
        is_active=request.is_active,
    )
    
    return UserRoleResponse(**assignment.to_dict())


@router.get(
    "/user-roles",
    response_model=list[UserRoleResponse],
    summary="Get all user-role assignments",
    description="Get all user-role assignments.",
)
def get_user_roles(current_user: CurrentSuperuser) -> list[UserRoleResponse]:
    """Get all user-role assignments."""
    service = get_service()
    assignments = service.get_all_user_roles()
    return [UserRoleResponse(**a.to_dict()) for a in assignments]


@router.get(
    "/user-roles/{user_id}",
    response_model=list[UserRoleResponse],
    summary="Get user roles",
    description="Get roles for a specific user.",
)
def get_user_role_assignments(user_id: str, current_user: CurrentSuperuser) -> list[UserRoleResponse]:
    """Get role assignments for a user."""
    service = get_service()
    
    uid = validate_uuid(user_id, "user_id")
    assignments = service.get_user_roles(uid)
    
    return [UserRoleResponse(**a.to_dict()) for a in assignments]


# ===== Audit Log Endpoints =====


@router.post(
    "/audit-logs",
    response_model=AuditLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an audit log",
    description="Register an audit log entry for verification.",
)
def register_audit_log(request: RegisterAuditLogRequest, current_user: CurrentSuperuser) -> AuditLogResponse:
    """Register an audit log entry."""
    service = get_service()
    
    log_id = validate_uuid(request.log_id, "log_id")
    entity_id = validate_uuid(request.entity_id, "entity_id")
    user_id = validate_uuid(request.user_id, "user_id") if request.user_id else None
    
    created_at = datetime.fromisoformat(request.created_at)
    
    entry = service.register_audit_log(
        log_id=log_id,
        entity_type=request.entity_type,
        entity_id=entity_id,
        action=request.action,
        created_at=created_at,
        user_id=user_id,
        user_email=request.user_email,
        ip_address=request.ip_address,
        has_old_values=request.has_old_values,
        has_new_values=request.has_new_values,
        has_changed_fields=request.has_changed_fields,
    )
    
    return AuditLogResponse(**entry.to_dict())


@router.get(
    "/audit-logs",
    response_model=list[AuditLogResponse],
    summary="Get audit logs",
    description="Get audit logs with optional filters.",
)
def get_audit_logs(
    current_user: CurrentSuperuser,
    entity_type: Annotated[str | None, Query(description="Entity type filter")] = None,
    action: Annotated[str | None, Query(description="Action filter")] = None,
    user_id: Annotated[str | None, Query(description="User ID filter")] = None,
    start_date: Annotated[str | None, Query(description="Start date (ISO format)")] = None,
    end_date: Annotated[str | None, Query(description="End date (ISO format)")] = None,
) -> list[AuditLogResponse]:
    """Get audit logs with filters."""
    service = get_service()
    
    uid = validate_uuid(user_id, "user_id") if user_id else None
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    logs = service.get_audit_logs(
        entity_type=entity_type,
        user_id=uid,
        action=action,
        start_date=start,
        end_date=end,
    )
    
    return [AuditLogResponse(**l.to_dict()) for l in logs]


# ===== Access Pattern Endpoints =====


@router.post(
    "/access-patterns",
    response_model=AccessPatternResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record access pattern",
    description="Record an access event for pattern analysis.",
)
def record_access_pattern(request: RecordAccessRequest, current_user: CurrentSuperuser) -> AccessPatternResponse:
    """Record an access pattern."""
    service = get_service()
    
    user_id = validate_uuid(request.user_id, "user_id")
    entity_id = validate_uuid(request.entity_id, "entity_id") if request.entity_id else None
    access_time = datetime.fromisoformat(request.access_time)
    
    pattern = service.record_access_pattern(
        user_id=user_id,
        user_email=request.user_email,
        action=request.action,
        resource=request.resource,
        access_time=access_time,
        entity_id=entity_id,
    )
    
    return AccessPatternResponse(**pattern.to_dict())


@router.get(
    "/access-patterns",
    response_model=list[AccessPatternResponse],
    summary="Get access patterns",
    description="Get access patterns, optionally filtered by user.",
)
def get_access_patterns(
    current_user: CurrentSuperuser,
    user_id: Annotated[str | None, Query(description="User ID filter")] = None,
) -> list[AccessPatternResponse]:
    """Get access patterns."""
    service = get_service()
    
    uid = validate_uuid(user_id, "user_id") if user_id else None
    patterns = service.get_access_patterns(uid)
    
    return [AccessPatternResponse(**p.to_dict()) for p in patterns]


# ===== Verification Endpoints =====


@router.post(
    "/verify/roles",
    response_model=VerificationResultResponse,
    summary="Verify role configuration",
    description="Verify role configuration for security issues.",
)
def verify_role_configuration(current_user: CurrentSuperuser) -> VerificationResultResponse:
    """Verify role configuration."""
    service = get_service()
    findings = service.verify_role_configuration()
    
    return VerificationResultResponse(
        check_name="role_configuration",
        findings_count=len(findings),
        findings=[FindingResponse(**f.to_dict()) for f in findings],
    )


@router.post(
    "/verify/permissions",
    response_model=VerificationResultResponse,
    summary="Verify permission configuration",
    description="Verify permission configuration for security issues.",
)
def verify_permission_configuration(current_user: CurrentSuperuser) -> VerificationResultResponse:
    """Verify permission configuration."""
    service = get_service()
    findings = service.verify_permission_configuration()
    
    return VerificationResultResponse(
        check_name="permission_configuration",
        findings_count=len(findings),
        findings=[FindingResponse(**f.to_dict()) for f in findings],
    )


@router.post(
    "/verify/user-assignments",
    response_model=VerificationResultResponse,
    summary="Verify user assignments",
    description="Verify user-role assignments for security issues.",
)
def verify_user_assignments(current_user: CurrentSuperuser) -> VerificationResultResponse:
    """Verify user assignments."""
    service = get_service()
    findings = service.verify_user_assignments()
    
    return VerificationResultResponse(
        check_name="user_assignments",
        findings_count=len(findings),
        findings=[FindingResponse(**f.to_dict()) for f in findings],
    )


@router.post(
    "/verify/audit-logs",
    response_model=VerificationResultResponse,
    summary="Verify audit log integrity",
    description="Verify audit log integrity and completeness.",
)
def verify_audit_logs(current_user: CurrentSuperuser) -> VerificationResultResponse:
    """Verify audit log integrity."""
    service = get_service()
    findings = service.verify_audit_log_integrity()
    
    return VerificationResultResponse(
        check_name="audit_log_integrity",
        findings_count=len(findings),
        findings=[FindingResponse(**f.to_dict()) for f in findings],
    )


@router.post(
    "/verify/access-patterns",
    response_model=VerificationResultResponse,
    summary="Detect access anomalies",
    description="Detect anomalies in access patterns.",
)
def detect_access_anomalies(
    current_user: CurrentSuperuser,
    threshold_multiplier: Annotated[float, Query(ge=1.0, le=10.0, description="Threshold multiplier")] = 3.0,
) -> VerificationResultResponse:
    """Detect access anomalies."""
    service = get_service()
    findings = service.detect_access_anomalies(threshold_multiplier)
    
    return VerificationResultResponse(
        check_name="access_anomalies",
        findings_count=len(findings),
        findings=[FindingResponse(**f.to_dict()) for f in findings],
    )


# ===== Findings Endpoints =====


@router.get(
    "/findings",
    response_model=list[FindingResponse],
    summary="Get all findings",
    description="Get all audit findings with optional filters.",
)
def get_findings(
    current_user: CurrentSuperuser,
    severity: Annotated[str | None, Query(description="Severity filter")] = None,
    category: Annotated[str | None, Query(description="Category filter")] = None,
    resolved: Annotated[bool | None, Query(description="Resolved filter")] = None,
) -> list[FindingResponse]:
    """Get all findings."""
    service = get_service()
    
    sev = validate_severity(severity) if severity else None
    cat = validate_category(category) if category else None
    
    findings = service.get_all_findings(
        severity=sev,
        category=cat,
        resolved=resolved,
    )
    
    return [FindingResponse(**f.to_dict()) for f in findings]


@router.get(
    "/findings/summary",
    response_model=FindingsSummaryResponse,
    summary="Get findings summary",
    description="Get summary of unresolved findings by severity.",
)
def get_findings_summary(current_user: CurrentSuperuser) -> FindingsSummaryResponse:
    """Get findings summary."""
    service = get_service()
    summary = service.get_findings_summary()
    
    return FindingsSummaryResponse(**summary)


@router.post(
    "/findings/{finding_id}/resolve",
    response_model=FindingResponse,
    summary="Resolve a finding",
    description="Mark a finding as resolved.",
)
def resolve_finding(finding_id: str, request: ResolveFindingRequest, current_user: CurrentSuperuser) -> FindingResponse:
    """Resolve a finding."""
    service = get_service()
    
    finding = service.resolve_finding(finding_id, request.resolved_by)
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding not found: {finding_id}",
        )
    
    return FindingResponse(**finding.to_dict())


# ===== Compliance Report Endpoints =====


@router.post(
    "/report",
    response_model=ComplianceReportResponse,
    summary="Generate compliance report",
    description="Run a full security audit and generate a compliance report.",
)
def generate_compliance_report(current_user: CurrentSuperuser) -> ComplianceReportResponse:
    """Generate compliance report."""
    service = get_service()
    report = service.run_full_audit()
    
    return ComplianceReportResponse(**report.to_dict())


# ===== Maintenance Endpoints =====


@router.delete(
    "/data",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all data",
    description="Clear all registered data and findings. Use with caution.",
)
def clear_all_data(current_user: CurrentSuperuser) -> None:
    """Clear all data."""
    service = get_service()
    service.clear_data()
