"""
RBAC Security Audit Service.

Provides comprehensive verification of Role-Based Access Control (RBAC)
and Audit Log integrity for security compliance.

Features:
- Role and permission configuration verification
- User-role assignment audit
- Permission gap analysis
- Audit log integrity checks
- Access pattern anomaly detection
- Security compliance reporting
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID


class AuditSeverity(str, Enum):
    """Severity level for audit findings."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditCategory(str, Enum):
    """Category of audit finding."""
    
    RBAC_CONFIG = "rbac_configuration"
    PERMISSION_GAP = "permission_gap"
    USER_ASSIGNMENT = "user_assignment"
    AUDIT_LOG = "audit_log"
    ACCESS_PATTERN = "access_pattern"
    COMPLIANCE = "compliance"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ORPHANED_ENTITY = "orphaned_entity"


class ComplianceStatus(str, Enum):
    """Overall compliance status."""
    
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class AuditFinding:
    """A security audit finding."""
    
    id: str
    category: AuditCategory
    severity: AuditSeverity
    title: str
    description: str
    affected_entity_type: str | None = None
    affected_entity_id: str | None = None
    recommendation: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "affected_entity_type": self.affected_entity_type,
            "affected_entity_id": self.affected_entity_id,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }


@dataclass
class RoleConfig:
    """Role configuration for verification."""
    
    id: UUID
    name: str
    display_name: str
    role_type: str | None
    is_system: bool
    is_active: bool
    hierarchy_level: int
    permission_count: int = 0
    user_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "role_type": self.role_type,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "hierarchy_level": self.hierarchy_level,
            "permission_count": self.permission_count,
            "user_count": self.user_count,
        }


@dataclass
class PermissionConfig:
    """Permission configuration for verification."""
    
    id: UUID
    name: str
    display_name: str
    resource: str
    action: str
    is_system: bool
    role_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "resource": self.resource,
            "action": self.action,
            "is_system": self.is_system,
            "role_count": self.role_count,
        }


@dataclass
class UserRoleAssignment:
    """User-role assignment for audit."""
    
    user_id: UUID
    user_email: str
    role_id: UUID
    role_name: str
    assigned_at: datetime
    assigned_by_id: UUID | None
    expires_at: datetime | None
    is_active: bool
    is_expired: bool
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id),
            "user_email": self.user_email,
            "role_id": str(self.role_id),
            "role_name": self.role_name,
            "assigned_at": self.assigned_at.isoformat(),
            "assigned_by_id": str(self.assigned_by_id) if self.assigned_by_id else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
        }


@dataclass
class AuditLogEntry:
    """Audit log entry for verification."""
    
    id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    user_id: UUID | None
    user_email: str | None
    created_at: datetime
    ip_address: str | None
    has_old_values: bool
    has_new_values: bool
    has_changed_fields: bool
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "action": self.action,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_email": self.user_email,
            "created_at": self.created_at.isoformat(),
            "ip_address": self.ip_address,
            "has_old_values": self.has_old_values,
            "has_new_values": self.has_new_values,
            "has_changed_fields": self.has_changed_fields,
        }


@dataclass
class AccessPattern:
    """Access pattern for anomaly detection."""
    
    user_id: UUID
    user_email: str
    action: str
    resource: str
    count: int
    first_access: datetime
    last_access: datetime
    unique_entities: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id),
            "user_email": self.user_email,
            "action": self.action,
            "resource": self.resource,
            "count": self.count,
            "first_access": self.first_access.isoformat(),
            "last_access": self.last_access.isoformat(),
            "unique_entities": self.unique_entities,
        }


@dataclass
class ComplianceReport:
    """Security compliance report."""
    
    report_id: str
    generated_at: datetime
    status: ComplianceStatus
    total_checks: int
    passed_checks: int
    failed_checks: int
    findings_by_severity: dict[str, int]
    findings: list[AuditFinding]
    role_summary: dict[str, Any]
    permission_summary: dict[str, Any]
    user_assignment_summary: dict[str, Any]
    audit_log_summary: dict[str, Any]
    recommendations: list[str]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "status": self.status.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "findings_by_severity": self.findings_by_severity,
            "findings": [f.to_dict() for f in self.findings],
            "role_summary": self.role_summary,
            "permission_summary": self.permission_summary,
            "user_assignment_summary": self.user_assignment_summary,
            "audit_log_summary": self.audit_log_summary,
            "recommendations": self.recommendations,
        }


# Standard permissions expected for each role type
EXPECTED_ROLE_PERMISSIONS = {
    "admin": [
        "users:create", "users:read", "users:update", "users:delete",
        "roles:create", "roles:read", "roles:update", "roles:delete",
        "permissions:read", "permissions:assign",
        "audit:read", "audit:export",
        "settings:read", "settings:update",
    ],
    "gm": [
        "dashboard:read", "reports:read", "reports:export",
        "quotes:read", "quotes:approve", "quotes:reject",
        "rfq:read", "rfq:approve", "rfq:reject",
        "work_orders:read", "work_orders:approve",
        "tasks:read", "tasks:create", "tasks:update",
    ],
    "sales_engineer": [
        "rfq:create", "rfq:read", "rfq:update",
        "quotes:create", "quotes:read", "quotes:update",
        "accounts:read", "contacts:read",
        "opportunities:create", "opportunities:read", "opportunities:update",
    ],
    "estimator": [
        "quotes:create", "quotes:read", "quotes:update",
        "products:read",
        "work_centers:read",
    ],
    "quality": [
        "quality:create", "quality:read", "quality:update",
        "a3:create", "a3:read", "a3:update",
        "ctq:create", "ctq:read", "ctq:update",
    ],
    "supply_chain": [
        "kanban:read", "kanban:update",
        "inventory:read", "inventory:update",
        "suppliers:read",
    ],
    "ops": [
        "work_orders:create", "work_orders:read", "work_orders:update",
        "production_cells:read",
        "andon:create", "andon:read", "andon:update",
        "standard_work:read",
    ],
    "exec": [
        "dashboard:read", "reports:read", "reports:export",
        "obeya:read",
        "kpi:read",
    ],
    "viewer": [
        "dashboard:read", "reports:read",
    ],
}

# Actions that should always be audit-logged
AUDITED_ACTIONS = [
    "create", "update", "delete", "soft_delete", "restore",
    "login", "logout", "failed_login", "password_change",
    "permission_change", "status_change", "approval", "rejection",
    "export", "import",
]

# Sensitive resources requiring audit
SENSITIVE_RESOURCES = [
    "users", "roles", "permissions", "settings",
    "quotes", "rfq", "work_orders", "accounts",
]


class RBACSecurityAuditService:
    """
    Service for verifying RBAC configuration and audit log integrity.
    
    Provides comprehensive security auditing including:
    - Role and permission verification
    - User assignment auditing
    - Permission gap analysis
    - Audit log integrity checking
    - Access pattern analysis
    - Compliance reporting
    """
    
    def __init__(self) -> None:
        """Initialize the security audit service."""
        self._roles: dict[UUID, RoleConfig] = {}
        self._permissions: dict[UUID, PermissionConfig] = {}
        self._user_roles: list[UserRoleAssignment] = []
        self._audit_logs: list[AuditLogEntry] = []
        self._findings: list[AuditFinding] = []
        self._finding_counter = 0
        self._access_patterns: dict[str, AccessPattern] = {}
    
    def _generate_finding_id(self) -> str:
        """Generate a unique finding ID."""
        self._finding_counter += 1
        return f"FINDING-{self._finding_counter:04d}"
    
    # ===== Role Management =====
    
    def register_role(
        self,
        role_id: UUID,
        name: str,
        display_name: str,
        role_type: str | None = None,
        is_system: bool = False,
        is_active: bool = True,
        hierarchy_level: int = 100,
        permission_count: int = 0,
        user_count: int = 0,
    ) -> RoleConfig:
        """Register a role for audit verification."""
        role = RoleConfig(
            id=role_id,
            name=name,
            display_name=display_name,
            role_type=role_type,
            is_system=is_system,
            is_active=is_active,
            hierarchy_level=hierarchy_level,
            permission_count=permission_count,
            user_count=user_count,
        )
        self._roles[role_id] = role
        return role
    
    def get_role(self, role_id: UUID) -> RoleConfig | None:
        """Get a role configuration."""
        return self._roles.get(role_id)
    
    def get_all_roles(self) -> list[RoleConfig]:
        """Get all registered roles."""
        return list(self._roles.values())
    
    # ===== Permission Management =====
    
    def register_permission(
        self,
        permission_id: UUID,
        name: str,
        display_name: str,
        resource: str,
        action: str,
        is_system: bool = False,
        role_count: int = 0,
    ) -> PermissionConfig:
        """Register a permission for audit verification."""
        permission = PermissionConfig(
            id=permission_id,
            name=name,
            display_name=display_name,
            resource=resource,
            action=action,
            is_system=is_system,
            role_count=role_count,
        )
        self._permissions[permission_id] = permission
        return permission
    
    def get_permission(self, permission_id: UUID) -> PermissionConfig | None:
        """Get a permission configuration."""
        return self._permissions.get(permission_id)
    
    def get_all_permissions(self) -> list[PermissionConfig]:
        """Get all registered permissions."""
        return list(self._permissions.values())
    
    # ===== User-Role Assignment Management =====
    
    def register_user_role(
        self,
        user_id: UUID,
        user_email: str,
        role_id: UUID,
        role_name: str,
        assigned_at: datetime,
        assigned_by_id: UUID | None = None,
        expires_at: datetime | None = None,
        is_active: bool = True,
    ) -> UserRoleAssignment:
        """Register a user-role assignment for audit."""
        now = datetime.now(timezone.utc)
        is_expired = expires_at is not None and expires_at < now
        
        assignment = UserRoleAssignment(
            user_id=user_id,
            user_email=user_email,
            role_id=role_id,
            role_name=role_name,
            assigned_at=assigned_at,
            assigned_by_id=assigned_by_id,
            expires_at=expires_at,
            is_active=is_active,
            is_expired=is_expired,
        )
        self._user_roles.append(assignment)
        return assignment
    
    def get_user_roles(self, user_id: UUID) -> list[UserRoleAssignment]:
        """Get all role assignments for a user."""
        return [ur for ur in self._user_roles if ur.user_id == user_id]
    
    def get_all_user_roles(self) -> list[UserRoleAssignment]:
        """Get all user-role assignments."""
        return list(self._user_roles)
    
    # ===== Audit Log Management =====
    
    def register_audit_log(
        self,
        log_id: UUID,
        entity_type: str,
        entity_id: UUID,
        action: str,
        created_at: datetime,
        user_id: UUID | None = None,
        user_email: str | None = None,
        ip_address: str | None = None,
        has_old_values: bool = False,
        has_new_values: bool = False,
        has_changed_fields: bool = False,
    ) -> AuditLogEntry:
        """Register an audit log entry for verification."""
        entry = AuditLogEntry(
            id=log_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            user_email=user_email,
            created_at=created_at,
            ip_address=ip_address,
            has_old_values=has_old_values,
            has_new_values=has_new_values,
            has_changed_fields=has_changed_fields,
        )
        self._audit_logs.append(entry)
        return entry
    
    def get_audit_logs(
        self,
        entity_type: str | None = None,
        user_id: UUID | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AuditLogEntry]:
        """Get audit logs with optional filters."""
        logs = self._audit_logs
        
        if entity_type:
            logs = [l for l in logs if l.entity_type == entity_type]
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        if action:
            logs = [l for l in logs if l.action == action]
        if start_date:
            logs = [l for l in logs if l.created_at >= start_date]
        if end_date:
            logs = [l for l in logs if l.created_at <= end_date]
        
        return logs
    
    # ===== RBAC Verification =====
    
    def verify_role_configuration(self) -> list[AuditFinding]:
        """Verify role configuration for security issues."""
        findings: list[AuditFinding] = []
        
        # Check for roles without permissions
        for role in self._roles.values():
            if role.is_active and role.permission_count == 0:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.RBAC_CONFIG,
                    severity=AuditSeverity.MEDIUM,
                    title="Role without permissions",
                    description=f"Role '{role.name}' is active but has no permissions assigned.",
                    affected_entity_type="role",
                    affected_entity_id=str(role.id),
                    recommendation="Assign appropriate permissions or deactivate the role.",
                    evidence={"role": role.to_dict()},
                ))
        
        # Check for non-standard system roles
        standard_role_types = set(EXPECTED_ROLE_PERMISSIONS.keys())
        for role in self._roles.values():
            if role.is_system and role.role_type and role.role_type not in standard_role_types:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.RBAC_CONFIG,
                    severity=AuditSeverity.INFO,
                    title="Non-standard system role type",
                    description=f"System role '{role.name}' has non-standard type '{role.role_type}'.",
                    affected_entity_type="role",
                    affected_entity_id=str(role.id),
                    recommendation="Verify this is intentional.",
                    evidence={"role": role.to_dict(), "standard_types": list(standard_role_types)},
                ))
        
        # Check for roles with high privilege (low hierarchy) and many users
        for role in self._roles.values():
            if role.hierarchy_level < 20 and role.user_count > 5:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.PRIVILEGE_ESCALATION,
                    severity=AuditSeverity.HIGH,
                    title="High-privilege role with many users",
                    description=f"Role '{role.name}' (hierarchy={role.hierarchy_level}) has {role.user_count} users.",
                    affected_entity_type="role",
                    affected_entity_id=str(role.id),
                    recommendation="Review if all users require this level of access.",
                    evidence={"role": role.to_dict()},
                ))
        
        self._findings.extend(findings)
        return findings
    
    def verify_permission_configuration(self) -> list[AuditFinding]:
        """Verify permission configuration for security issues."""
        findings: list[AuditFinding] = []
        
        # Check for unused permissions
        for perm in self._permissions.values():
            if perm.role_count == 0:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.PERMISSION_GAP,
                    severity=AuditSeverity.LOW,
                    title="Unused permission",
                    description=f"Permission '{perm.name}' is not assigned to any role.",
                    affected_entity_type="permission",
                    affected_entity_id=str(perm.id),
                    recommendation="Consider removing if no longer needed.",
                    evidence={"permission": perm.to_dict()},
                ))
        
        # Check for sensitive permissions with wide assignment
        sensitive_actions = ["delete", "approve", "reject", "admin"]
        for perm in self._permissions.values():
            if any(a in perm.action for a in sensitive_actions) and perm.role_count > 5:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.PRIVILEGE_ESCALATION,
                    severity=AuditSeverity.MEDIUM,
                    title="Sensitive permission widely assigned",
                    description=f"Permission '{perm.name}' is assigned to {perm.role_count} roles.",
                    affected_entity_type="permission",
                    affected_entity_id=str(perm.id),
                    recommendation="Review role assignments for this sensitive permission.",
                    evidence={"permission": perm.to_dict()},
                ))
        
        self._findings.extend(findings)
        return findings
    
    def verify_user_assignments(self) -> list[AuditFinding]:
        """Verify user-role assignments for security issues."""
        findings: list[AuditFinding] = []
        
        # Check for expired but active assignments
        for assignment in self._user_roles:
            if assignment.is_active and assignment.is_expired:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.USER_ASSIGNMENT,
                    severity=AuditSeverity.HIGH,
                    title="Expired role assignment still active",
                    description=f"User '{assignment.user_email}' has expired role '{assignment.role_name}' still marked active.",
                    affected_entity_type="user_role",
                    affected_entity_id=f"{assignment.user_id}:{assignment.role_id}",
                    recommendation="Deactivate expired role assignments.",
                    evidence={"assignment": assignment.to_dict()},
                ))
        
        # Check for users with multiple high-privilege roles
        user_high_priv: dict[UUID, list[str]] = {}
        for assignment in self._user_roles:
            if assignment.is_active and not assignment.is_expired:
                role = self._roles.get(assignment.role_id)
                if role and role.hierarchy_level < 30:
                    if assignment.user_id not in user_high_priv:
                        user_high_priv[assignment.user_id] = []
                    user_high_priv[assignment.user_id].append(assignment.role_name)
        
        for user_id, roles in user_high_priv.items():
            if len(roles) > 1:
                user_assignment = next((a for a in self._user_roles if a.user_id == user_id), None)
                if user_assignment:
                    findings.append(AuditFinding(
                        id=self._generate_finding_id(),
                        category=AuditCategory.PRIVILEGE_ESCALATION,
                        severity=AuditSeverity.MEDIUM,
                        title="User with multiple high-privilege roles",
                        description=f"User '{user_assignment.user_email}' has multiple high-privilege roles: {roles}.",
                        affected_entity_type="user",
                        affected_entity_id=str(user_id),
                        recommendation="Review if user needs all these roles.",
                        evidence={"roles": roles, "user_email": user_assignment.user_email},
                    ))
        
        # Check for self-assigned roles
        for assignment in self._user_roles:
            if assignment.assigned_by_id and assignment.assigned_by_id == assignment.user_id:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.PRIVILEGE_ESCALATION,
                    severity=AuditSeverity.CRITICAL,
                    title="Self-assigned role detected",
                    description=f"User '{assignment.user_email}' assigned role '{assignment.role_name}' to themselves.",
                    affected_entity_type="user_role",
                    affected_entity_id=f"{assignment.user_id}:{assignment.role_id}",
                    recommendation="Investigate potential privilege escalation.",
                    evidence={"assignment": assignment.to_dict()},
                ))
        
        self._findings.extend(findings)
        return findings
    
    # ===== Audit Log Verification =====
    
    def verify_audit_log_integrity(self) -> list[AuditFinding]:
        """Verify audit log integrity and completeness."""
        findings: list[AuditFinding] = []
        
        # Check for missing user attribution
        anonymous_logs = [l for l in self._audit_logs if l.user_id is None and l.action not in ["login", "failed_login"]]
        if anonymous_logs:
            findings.append(AuditFinding(
                id=self._generate_finding_id(),
                category=AuditCategory.AUDIT_LOG,
                severity=AuditSeverity.MEDIUM,
                title="Audit logs without user attribution",
                description=f"Found {len(anonymous_logs)} audit log entries without user ID.",
                affected_entity_type="audit_log",
                affected_entity_id=None,
                recommendation="Ensure all actions are properly attributed to users.",
                evidence={"sample_logs": [l.to_dict() for l in anonymous_logs[:5]]},
            ))
        
        # Check for updates without change details
        updates_without_details = [
            l for l in self._audit_logs
            if l.action == "update" and not l.has_old_values and not l.has_changed_fields
        ]
        if updates_without_details:
            findings.append(AuditFinding(
                id=self._generate_finding_id(),
                category=AuditCategory.AUDIT_LOG,
                severity=AuditSeverity.MEDIUM,
                title="Update logs without change details",
                description=f"Found {len(updates_without_details)} update logs without change details.",
                affected_entity_type="audit_log",
                affected_entity_id=None,
                recommendation="Ensure update operations log old values and changed fields.",
                evidence={"sample_logs": [l.to_dict() for l in updates_without_details[:5]]},
            ))
        
        # Check for sensitive resources without audit coverage
        logged_resources = set(l.entity_type for l in self._audit_logs)
        missing_sensitive = [r for r in SENSITIVE_RESOURCES if r not in logged_resources]
        if missing_sensitive:
            findings.append(AuditFinding(
                id=self._generate_finding_id(),
                category=AuditCategory.AUDIT_LOG,
                severity=AuditSeverity.HIGH,
                title="Sensitive resources without audit logs",
                description=f"Sensitive resources not found in audit logs: {missing_sensitive}.",
                affected_entity_type="audit_log",
                affected_entity_id=None,
                recommendation="Ensure all sensitive resource changes are logged.",
                evidence={"missing": missing_sensitive, "logged": list(logged_resources)},
            ))
        
        # Check for gaps in audit timeline
        if self._audit_logs:
            sorted_logs = sorted(self._audit_logs, key=lambda l: l.created_at)
            for i in range(1, len(sorted_logs)):
                gap = sorted_logs[i].created_at - sorted_logs[i - 1].created_at
                if gap > timedelta(hours=24):
                    findings.append(AuditFinding(
                        id=self._generate_finding_id(),
                        category=AuditCategory.AUDIT_LOG,
                        severity=AuditSeverity.MEDIUM,
                        title="Gap in audit log timeline",
                        description=f"Found {gap.days}+ day gap in audit logs.",
                        affected_entity_type="audit_log",
                        affected_entity_id=None,
                        recommendation="Investigate if this represents missing logs or expected downtime.",
                        evidence={
                            "before": sorted_logs[i - 1].to_dict(),
                            "after": sorted_logs[i].to_dict(),
                            "gap_hours": gap.total_seconds() / 3600,
                        },
                    ))
                    break  # Only report first significant gap
        
        self._findings.extend(findings)
        return findings
    
    # ===== Access Pattern Analysis =====
    
    def record_access_pattern(
        self,
        user_id: UUID,
        user_email: str,
        action: str,
        resource: str,
        access_time: datetime,
        entity_id: UUID | None = None,
    ) -> AccessPattern:
        """Record an access event for pattern analysis."""
        key = f"{user_id}:{action}:{resource}"
        
        if key in self._access_patterns:
            pattern = self._access_patterns[key]
            pattern.count += 1
            pattern.last_access = max(pattern.last_access, access_time)
            pattern.first_access = min(pattern.first_access, access_time)
            if entity_id:
                pattern.unique_entities += 1  # Simplified; real impl would track unique IDs
        else:
            self._access_patterns[key] = AccessPattern(
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource=resource,
                count=1,
                first_access=access_time,
                last_access=access_time,
                unique_entities=1 if entity_id else 0,
            )
        
        return self._access_patterns[key]
    
    def detect_access_anomalies(self, threshold_multiplier: float = 3.0) -> list[AuditFinding]:
        """Detect anomalies in access patterns."""
        findings: list[AuditFinding] = []
        
        if not self._access_patterns:
            return findings
        
        # Calculate average access count per pattern
        total_access = sum(p.count for p in self._access_patterns.values())
        avg_access = total_access / len(self._access_patterns) if self._access_patterns else 0
        threshold = avg_access * threshold_multiplier
        
        # Find patterns significantly above average
        for pattern in self._access_patterns.values():
            if pattern.count > threshold and pattern.count > 10:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.ACCESS_PATTERN,
                    severity=AuditSeverity.MEDIUM,
                    title="Unusual access pattern detected",
                    description=f"User '{pattern.user_email}' has {pattern.count} '{pattern.action}' accesses on '{pattern.resource}'.",
                    affected_entity_type="user",
                    affected_entity_id=str(pattern.user_id),
                    recommendation="Review if this access pattern is expected.",
                    evidence={"pattern": pattern.to_dict(), "threshold": threshold},
                ))
        
        # Detect off-hours access
        for pattern in self._access_patterns.values():
            if pattern.last_access.hour < 6 or pattern.last_access.hour > 22:
                findings.append(AuditFinding(
                    id=self._generate_finding_id(),
                    category=AuditCategory.ACCESS_PATTERN,
                    severity=AuditSeverity.LOW,
                    title="Off-hours access detected",
                    description=f"User '{pattern.user_email}' accessed '{pattern.resource}' at {pattern.last_access.hour}:00.",
                    affected_entity_type="user",
                    affected_entity_id=str(pattern.user_id),
                    recommendation="Verify if off-hours access is authorized.",
                    evidence={"pattern": pattern.to_dict()},
                ))
        
        self._findings.extend(findings)
        return findings
    
    def get_access_patterns(self, user_id: UUID | None = None) -> list[AccessPattern]:
        """Get access patterns, optionally filtered by user."""
        patterns = list(self._access_patterns.values())
        if user_id:
            patterns = [p for p in patterns if p.user_id == user_id]
        return patterns
    
    # ===== Findings Management =====
    
    def get_all_findings(
        self,
        severity: AuditSeverity | None = None,
        category: AuditCategory | None = None,
        resolved: bool | None = None,
    ) -> list[AuditFinding]:
        """Get all findings with optional filters."""
        findings = self._findings
        
        if severity:
            findings = [f for f in findings if f.severity == severity]
        if category:
            findings = [f for f in findings if f.category == category]
        if resolved is not None:
            findings = [f for f in findings if f.resolved == resolved]
        
        return findings
    
    def resolve_finding(
        self,
        finding_id: str,
        resolved_by: str,
    ) -> AuditFinding | None:
        """Mark a finding as resolved."""
        for finding in self._findings:
            if finding.id == finding_id:
                finding.resolved = True
                finding.resolved_at = datetime.now(timezone.utc)
                finding.resolved_by = resolved_by
                return finding
        return None
    
    def get_findings_summary(self) -> dict[str, int]:
        """Get summary of findings by severity."""
        summary = {s.value: 0 for s in AuditSeverity}
        for finding in self._findings:
            if not finding.resolved:
                summary[finding.severity.value] += 1
        return summary
    
    # ===== Compliance Reporting =====
    
    def run_full_audit(self) -> ComplianceReport:
        """Run a complete security audit and generate compliance report."""
        # Clear previous findings
        self._findings = []
        self._finding_counter = 0
        
        # Run all verification checks
        self.verify_role_configuration()
        self.verify_permission_configuration()
        self.verify_user_assignments()
        self.verify_audit_log_integrity()
        self.detect_access_anomalies()
        
        # Calculate totals
        total_checks = 5  # Number of verification methods
        failed_checks = len(set(f.category for f in self._findings))
        passed_checks = total_checks - min(failed_checks, total_checks)
        
        # Determine status
        critical_count = len([f for f in self._findings if f.severity == AuditSeverity.CRITICAL])
        high_count = len([f for f in self._findings if f.severity == AuditSeverity.HIGH])
        
        if critical_count > 0:
            status = ComplianceStatus.NON_COMPLIANT
        elif high_count > 3:
            status = ComplianceStatus.NON_COMPLIANT
        elif high_count > 0 or len(self._findings) > 10:
            status = ComplianceStatus.PARTIAL
        else:
            status = ComplianceStatus.COMPLIANT
        
        # Generate recommendations
        recommendations = []
        if critical_count > 0:
            recommendations.append("Address critical findings immediately.")
        if high_count > 0:
            recommendations.append("Review and remediate high-severity findings within 24 hours.")
        
        unresolved = [f for f in self._findings if not f.resolved]
        categories = set(f.category for f in unresolved)
        
        if AuditCategory.PRIVILEGE_ESCALATION in categories:
            recommendations.append("Conduct thorough review of privilege assignments.")
        if AuditCategory.AUDIT_LOG in categories:
            recommendations.append("Improve audit log completeness and integrity.")
        if AuditCategory.USER_ASSIGNMENT in categories:
            recommendations.append("Review and clean up user-role assignments.")
        
        if not recommendations:
            recommendations.append("Maintain current security posture with regular audits.")
        
        # Build summaries
        role_summary = {
            "total": len(self._roles),
            "active": len([r for r in self._roles.values() if r.is_active]),
            "system": len([r for r in self._roles.values() if r.is_system]),
        }
        
        permission_summary = {
            "total": len(self._permissions),
            "system": len([p for p in self._permissions.values() if p.is_system]),
            "unused": len([p for p in self._permissions.values() if p.role_count == 0]),
        }
        
        user_assignment_summary = {
            "total": len(self._user_roles),
            "active": len([a for a in self._user_roles if a.is_active and not a.is_expired]),
            "expired": len([a for a in self._user_roles if a.is_expired]),
        }
        
        audit_log_summary = {
            "total_entries": len(self._audit_logs),
            "unique_users": len(set(l.user_id for l in self._audit_logs if l.user_id)),
            "unique_resources": len(set(l.entity_type for l in self._audit_logs)),
        }
        
        return ComplianceReport(
            report_id=f"AUDIT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            generated_at=datetime.now(timezone.utc),
            status=status,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            findings_by_severity=self.get_findings_summary(),
            findings=self._findings,
            role_summary=role_summary,
            permission_summary=permission_summary,
            user_assignment_summary=user_assignment_summary,
            audit_log_summary=audit_log_summary,
            recommendations=recommendations,
        )
    
    def clear_data(self) -> None:
        """Clear all registered data and findings."""
        self._roles.clear()
        self._permissions.clear()
        self._user_roles.clear()
        self._audit_logs.clear()
        self._findings.clear()
        self._access_patterns.clear()
        self._finding_counter = 0


# Singleton instance
_rbac_security_audit_service: RBACSecurityAuditService | None = None


def get_rbac_security_audit_service() -> RBACSecurityAuditService:
    """Get the singleton RBAC security audit service."""
    global _rbac_security_audit_service
    if _rbac_security_audit_service is None:
        _rbac_security_audit_service = RBACSecurityAuditService()
    return _rbac_security_audit_service


def reset_rbac_security_audit_service() -> None:
    """Reset the singleton for testing."""
    global _rbac_security_audit_service
    if _rbac_security_audit_service:
        _rbac_security_audit_service.clear_data()
    _rbac_security_audit_service = None
