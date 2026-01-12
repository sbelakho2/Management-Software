"""Enhanced RBAC, Visibility, and Segregation of Duties Service (Development Plan 22.8).

Provides:
- Permission matrix for Finance/AP/AR/GL, HR, MES modules
- Role-based permission checking
- UI feature visibility enforcement
- Field-level security with PII/financial masking
- Segregation of Duties (SoD) rule enforcement
- Immutable audit trail with correlation IDs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _norm_roles(roles: Iterable[str]) -> frozenset[str]:
    return frozenset(r.lower().strip() for r in roles if r)


# ============================================================
# Role Definitions
# ============================================================


class Role(str, Enum):
    """Standard system roles."""

    ADMIN = "admin"
    CEO = "ceo"
    GM = "gm"
    FINANCE = "finance"
    ACCOUNTANT = "accountant"
    HR = "hr"
    OPS = "ops"
    QUALITY = "quality"
    AUDITOR = "auditor"
    IT = "it"
    SUPERVISOR = "supervisor"
    TEAM_LEAD = "team_lead"
    OPERATOR = "operator"
    VIEWER = "viewer"


# ============================================================
# Module/Resource Definitions
# ============================================================


class Module(str, Enum):
    """System modules for permission grouping."""

    # Finance Modules
    FINANCE_GL = "finance.gl"
    FINANCE_AP = "finance.ap"
    FINANCE_AR = "finance.ar"
    FINANCE_PERIOD = "finance.period"
    FINANCE_REPORTS = "finance.reports"
    FINANCE_BANK = "finance.bank"

    # HR Modules
    HR_EMPLOYEE = "hr.employee"
    HR_COMPENSATION = "hr.compensation"
    HR_LEAVE = "hr.leave"
    HR_RECRUITING = "hr.recruiting"
    HR_PERFORMANCE = "hr.performance"
    HR_ORG = "hr.org"

    # MES Modules
    MES_PRODUCTION = "mes.production"
    MES_QUALITY = "mes.quality"
    MES_INVENTORY = "mes.inventory"
    MES_MRP = "mes.mrp"
    MES_TRAVELER = "mes.traveler"
    MES_SPC = "mes.spc"

    # Admin Modules
    ADMIN_USERS = "admin.users"
    ADMIN_ROLES = "admin.roles"
    ADMIN_AUDIT = "admin.audit"
    ADMIN_SYSTEM = "admin.system"


class Permission(str, Enum):
    """Permission actions."""

    VIEW = "view"
    LIST = "list"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    EXPORT = "export"
    IMPORT = "import"
    CLOSE = "close"  # For period close
    POST = "post"  # For GL posting


# ============================================================
# Field Security Categories
# ============================================================


class FieldSecurityCategory(str, Enum):
    """Categories of sensitive fields."""

    PII = "pii"  # Personal Identifiable Information
    FINANCIAL = "financial"  # Pay rates, bank info
    CONFIDENTIAL = "confidential"  # Performance reviews, medical
    SENSITIVE = "sensitive"  # General sensitive data


# ============================================================
# SoD Rule Types
# ============================================================


class SoDRuleType(str, Enum):
    """Segregation of Duties rule types."""

    CREATE_APPROVE = "create_approve"  # Cannot create and approve same item
    SUBMIT_APPROVE = "submit_approve"  # Cannot submit and approve same item
    MAKER_CHECKER = "maker_checker"  # Two-person rule for sensitive ops


# ============================================================
# Data Classes
# ============================================================


@dataclass(frozen=True)
class PermissionGrant:
    """A permission granted to a role for a module."""

    id: UUID
    role: str
    module: str
    permission: str
    conditions: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class FeatureVisibility:
    """UI feature visibility configuration."""

    id: UUID
    feature_key: str  # e.g., "nav.finance.gl", "btn.approve_payment"
    required_permissions: tuple[str, ...] = field(default_factory=tuple)
    required_roles: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class FieldSecurityRule:
    """Field-level security rule for masking."""

    id: UUID
    entity_type: str  # e.g., "employee", "supplier"
    field_name: str  # e.g., "ssn", "bank_account"
    category: FieldSecurityCategory
    view_roles: tuple[str, ...] = field(default_factory=tuple)
    mask_pattern: str = "***"  # How to mask when hidden
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class SoDRule:
    """Segregation of Duties rule."""

    id: UUID
    name: str
    rule_type: SoDRuleType
    module: str
    action1: str  # First action (e.g., "create")
    action2: str  # Second action (e.g., "approve")
    description: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class SoDViolation:
    """Recorded SoD violation attempt."""

    id: UUID
    rule_id: UUID
    actor_id: str
    entity_type: str
    entity_id: str
    action1_ts: datetime
    action2_ts: datetime
    blocked: bool
    created_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class ImmutableAuditEntry:
    """Immutable audit trail entry."""

    id: UUID
    timestamp: datetime
    correlation_id: str
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    module: str
    entity_type: str
    entity_id: str
    outcome: str  # "success", "denied", "blocked_sod"
    metadata: dict[str, Any] = field(default_factory=dict)
    signature: str = ""  # Hash for tamper detection


# ============================================================
# Permission Matrix (Default)
# ============================================================


# Roles that can view/access each module
_DEFAULT_VIEW_PERMISSIONS: dict[str, frozenset[str]] = {
    # Finance - restricted
    Module.FINANCE_GL.value: frozenset(
        {"admin", "ceo", "gm", "finance", "accountant", "auditor"}
    ),
    Module.FINANCE_AP.value: frozenset(
        {"admin", "ceo", "gm", "finance", "accountant", "auditor"}
    ),
    Module.FINANCE_AR.value: frozenset(
        {"admin", "ceo", "gm", "finance", "accountant", "auditor"}
    ),
    Module.FINANCE_PERIOD.value: frozenset(
        {"admin", "ceo", "finance", "accountant", "auditor"}
    ),
    Module.FINANCE_REPORTS.value: frozenset(
        {"admin", "ceo", "gm", "finance", "accountant", "auditor"}
    ),
    Module.FINANCE_BANK.value: frozenset({"admin", "ceo", "finance", "auditor"}),
    # HR - restricted for PII
    Module.HR_EMPLOYEE.value: frozenset(
        {"admin", "ceo", "gm", "hr", "auditor", "supervisor"}
    ),
    Module.HR_COMPENSATION.value: frozenset({"admin", "ceo", "hr", "auditor"}),
    Module.HR_LEAVE.value: frozenset(
        {"admin", "ceo", "gm", "hr", "supervisor", "team_lead", "auditor"}
    ),
    Module.HR_RECRUITING.value: frozenset({"admin", "ceo", "gm", "hr", "auditor"}),
    Module.HR_PERFORMANCE.value: frozenset(
        {"admin", "ceo", "gm", "hr", "supervisor", "auditor"}
    ),
    Module.HR_ORG.value: frozenset(
        {"admin", "ceo", "gm", "hr", "ops", "auditor", "viewer"}
    ),
    # MES - broader access
    Module.MES_PRODUCTION.value: frozenset(
        {
            "admin",
            "ceo",
            "gm",
            "ops",
            "quality",
            "supervisor",
            "team_lead",
            "operator",
            "auditor",
        }
    ),
    Module.MES_QUALITY.value: frozenset(
        {
            "admin",
            "ceo",
            "gm",
            "ops",
            "quality",
            "supervisor",
            "team_lead",
            "auditor",
        }
    ),
    Module.MES_INVENTORY.value: frozenset(
        {
            "admin",
            "ceo",
            "gm",
            "ops",
            "quality",
            "supervisor",
            "team_lead",
            "auditor",
        }
    ),
    Module.MES_MRP.value: frozenset(
        {"admin", "ceo", "gm", "ops", "supervisor", "auditor"}
    ),
    Module.MES_TRAVELER.value: frozenset(
        {
            "admin",
            "ceo",
            "gm",
            "ops",
            "quality",
            "supervisor",
            "team_lead",
            "operator",
            "auditor",
        }
    ),
    Module.MES_SPC.value: frozenset(
        {
            "admin",
            "ceo",
            "gm",
            "ops",
            "quality",
            "supervisor",
            "team_lead",
            "auditor",
        }
    ),
    # Admin - highly restricted
    Module.ADMIN_USERS.value: frozenset({"admin", "it"}),
    Module.ADMIN_ROLES.value: frozenset({"admin"}),
    Module.ADMIN_AUDIT.value: frozenset({"admin", "ceo", "auditor", "it"}),
    Module.ADMIN_SYSTEM.value: frozenset({"admin", "it"}),
}

# Roles that can write (create/update/delete) to each module
_DEFAULT_WRITE_PERMISSIONS: dict[str, frozenset[str]] = {
    # Finance write
    Module.FINANCE_GL.value: frozenset({"admin", "finance", "accountant"}),
    Module.FINANCE_AP.value: frozenset({"admin", "finance", "accountant"}),
    Module.FINANCE_AR.value: frozenset({"admin", "finance", "accountant"}),
    Module.FINANCE_PERIOD.value: frozenset({"admin", "finance"}),
    Module.FINANCE_REPORTS.value: frozenset({"admin", "finance"}),
    Module.FINANCE_BANK.value: frozenset({"admin", "finance"}),
    # HR write
    Module.HR_EMPLOYEE.value: frozenset({"admin", "hr"}),
    Module.HR_COMPENSATION.value: frozenset({"admin", "hr"}),
    Module.HR_LEAVE.value: frozenset({"admin", "hr", "supervisor"}),
    Module.HR_RECRUITING.value: frozenset({"admin", "hr"}),
    Module.HR_PERFORMANCE.value: frozenset({"admin", "hr", "supervisor"}),
    Module.HR_ORG.value: frozenset({"admin", "hr"}),
    # MES write
    Module.MES_PRODUCTION.value: frozenset(
        {"admin", "ops", "supervisor", "team_lead", "operator"}
    ),
    Module.MES_QUALITY.value: frozenset(
        {"admin", "quality", "ops", "supervisor", "team_lead"}
    ),
    Module.MES_INVENTORY.value: frozenset({"admin", "ops", "supervisor"}),
    Module.MES_MRP.value: frozenset({"admin", "ops"}),
    Module.MES_TRAVELER.value: frozenset(
        {"admin", "ops", "quality", "supervisor", "team_lead", "operator"}
    ),
    Module.MES_SPC.value: frozenset({"admin", "quality", "ops"}),
    # Admin write
    Module.ADMIN_USERS.value: frozenset({"admin"}),
    Module.ADMIN_ROLES.value: frozenset({"admin"}),
    Module.ADMIN_AUDIT.value: frozenset(),  # Audit is immutable
    Module.ADMIN_SYSTEM.value: frozenset({"admin"}),
}

# Roles that can approve in each module
_DEFAULT_APPROVE_PERMISSIONS: dict[str, frozenset[str]] = {
    Module.FINANCE_GL.value: frozenset({"admin", "ceo", "finance"}),
    Module.FINANCE_AP.value: frozenset({"admin", "ceo", "gm", "finance"}),
    Module.FINANCE_AR.value: frozenset({"admin", "ceo", "gm", "finance"}),
    Module.FINANCE_PERIOD.value: frozenset({"admin", "ceo", "finance"}),
    Module.FINANCE_BANK.value: frozenset({"admin", "ceo", "finance"}),
    Module.HR_COMPENSATION.value: frozenset({"admin", "ceo", "hr"}),
    Module.HR_LEAVE.value: frozenset({"admin", "hr", "gm", "supervisor"}),
    Module.MES_MRP.value: frozenset({"admin", "ceo", "gm", "ops"}),
    Module.MES_QUALITY.value: frozenset({"admin", "quality", "ops"}),
}


# ============================================================
# Service
# ============================================================


class EnhancedRBACService:
    """Enhanced RBAC with visibility, field security, and SoD."""

    def __init__(self) -> None:
        # Permission grants (beyond defaults)
        self._permission_grants: dict[UUID, PermissionGrant] = {}

        # UI visibility rules
        self._visibility_rules: dict[UUID, FeatureVisibility] = {}

        # Field security rules
        self._field_rules: dict[UUID, FieldSecurityRule] = {}

        # SoD rules
        self._sod_rules: dict[UUID, SoDRule] = {}
        self._sod_violations: dict[UUID, SoDViolation] = {}

        # Actor action history for SoD tracking (entity_id -> (action, actor_id, ts))
        self._action_history: dict[str, list[tuple[str, str, datetime]]] = {}

        # Immutable audit trail
        self._audit_trail: list[ImmutableAuditEntry] = []

        # Initialize default SoD rules
        self._init_default_sod_rules()

    def _init_default_sod_rules(self) -> None:
        """Initialize default Segregation of Duties rules."""
        default_rules = [
            SoDRule(
                id=uuid4(),
                name="Payment Create-Approve",
                rule_type=SoDRuleType.CREATE_APPROVE,
                module=Module.FINANCE_AP.value,
                action1="create",
                action2="approve",
                description="Cannot create and approve same payment",
            ),
            SoDRule(
                id=uuid4(),
                name="Period Close Create-Approve",
                rule_type=SoDRuleType.CREATE_APPROVE,
                module=Module.FINANCE_PERIOD.value,
                action1="create",
                action2="close",
                description="Cannot initiate and close same period",
            ),
            SoDRule(
                id=uuid4(),
                name="Payroll Rate Create-Approve",
                rule_type=SoDRuleType.CREATE_APPROVE,
                module=Module.HR_COMPENSATION.value,
                action1="create",
                action2="approve",
                description="Cannot create and approve same payroll rate change",
            ),
            SoDRule(
                id=uuid4(),
                name="MRP Suggestion Create-Approve",
                rule_type=SoDRuleType.CREATE_APPROVE,
                module=Module.MES_MRP.value,
                action1="create",
                action2="approve",
                description="Cannot create and approve same MRP suggestion",
            ),
            SoDRule(
                id=uuid4(),
                name="Journal Entry Create-Post",
                rule_type=SoDRuleType.CREATE_APPROVE,
                module=Module.FINANCE_GL.value,
                action1="create",
                action2="post",
                description="Cannot create and post same journal entry",
            ),
        ]
        for rule in default_rules:
            self._sod_rules[rule.id] = rule

    # ----------------------------------------------------------------
    # Permission Checking
    # ----------------------------------------------------------------

    def check_permission(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        module: str,
        permission: str,
        correlation_id: str,
        entity_id: str | None = None,
    ) -> bool:
        """Check if actor has permission for module/action."""
        roles = _norm_roles(actor_roles)

        # Map permission to permission set
        if permission in ("view", "list"):
            allowed = _DEFAULT_VIEW_PERMISSIONS.get(module, frozenset())
        elif permission in ("create", "update", "delete"):
            allowed = _DEFAULT_WRITE_PERMISSIONS.get(module, frozenset())
        elif permission in ("approve", "post", "close"):
            allowed = _DEFAULT_APPROVE_PERMISSIONS.get(module, frozenset())
        elif permission == "export":
            # Export requires view permission
            allowed = _DEFAULT_VIEW_PERMISSIONS.get(module, frozenset())
        else:
            allowed = frozenset()

        # Check role overlap
        has_permission = bool(roles & allowed)

        # Check custom grants
        for grant in self._permission_grants.values():
            if grant.role in roles and grant.module == module:
                if grant.permission == permission or grant.permission == "*":
                    has_permission = True
                    break

        # Log the permission check
        outcome = "success" if has_permission else "denied"
        self._emit_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action=f"permission_check.{permission}",
            module=module,
            entity_type="permission",
            entity_id=entity_id or "n/a",
            outcome=outcome,
            correlation_id=correlation_id,
        )

        return has_permission

    def require_permission(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        module: str,
        permission: str,
        correlation_id: str,
        entity_id: str | None = None,
    ) -> None:
        """Require permission or raise PermissionError."""
        if not self.check_permission(
            actor_id=actor_id,
            actor_roles=actor_roles,
            module=module,
            permission=permission,
            correlation_id=correlation_id,
            entity_id=entity_id,
        ):
            raise PermissionError(
                f"Permission denied: {permission} on {module}"
            )

    # ----------------------------------------------------------------
    # Permission Grant Management
    # ----------------------------------------------------------------

    def add_permission_grant(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        role: str,
        module: str,
        permission: str,
        conditions: dict[str, Any] | None = None,
    ) -> PermissionGrant:
        """Add a custom permission grant. Admin only."""
        roles = _norm_roles(actor_roles)
        if "admin" not in roles:
            raise PermissionError("Admin role required to manage permissions")

        grant = PermissionGrant(
            id=uuid4(),
            role=role.lower().strip(),
            module=module,
            permission=permission,
            conditions=conditions or {},
        )
        self._permission_grants[grant.id] = grant

        self._emit_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="permission.grant.create",
            module="admin.roles",
            entity_type="permission_grant",
            entity_id=str(grant.id),
            outcome="success",
            correlation_id=correlation_id,
            metadata={"role": role, "module": module, "permission": permission},
        )

        return grant

    def list_permission_grants(
        self, *, actor_roles: Iterable[str]
    ) -> list[PermissionGrant]:
        """List all custom permission grants."""
        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor"}:
            raise PermissionError("Admin or auditor role required")
        return list(self._permission_grants.values())

    # ----------------------------------------------------------------
    # UI Visibility
    # ----------------------------------------------------------------

    def register_feature_visibility(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        feature_key: str,
        required_permissions: list[str] | None = None,
        required_roles: list[str] | None = None,
        description: str = "",
    ) -> FeatureVisibility:
        """Register a UI feature visibility rule."""
        roles = _norm_roles(actor_roles)
        if "admin" not in roles:
            raise PermissionError("Admin role required")

        rule = FeatureVisibility(
            id=uuid4(),
            feature_key=feature_key,
            required_permissions=tuple(required_permissions or []),
            required_roles=tuple(required_roles or []),
            description=description,
        )
        self._visibility_rules[rule.id] = rule

        self._emit_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="visibility.register",
            module="admin.system",
            entity_type="feature_visibility",
            entity_id=str(rule.id),
            outcome="success",
            correlation_id=correlation_id,
        )

        return rule

    def check_feature_visibility(
        self,
        *,
        actor_roles: Iterable[str],
        feature_key: str,
    ) -> bool:
        """Check if a UI feature should be visible to the actor."""
        roles = _norm_roles(actor_roles)

        # Find matching rule
        for rule in self._visibility_rules.values():
            if rule.feature_key == feature_key:
                # Check required roles
                if rule.required_roles:
                    if not roles & frozenset(rule.required_roles):
                        return False

                # All checks passed
                return True

        # No rule defined - default to visible (permissive)
        return True

    def get_visible_features(
        self, *, actor_roles: Iterable[str]
    ) -> list[str]:
        """Get list of visible feature keys for the actor."""
        roles = _norm_roles(actor_roles)
        visible = []

        for rule in self._visibility_rules.values():
            if rule.required_roles:
                if roles & frozenset(rule.required_roles):
                    visible.append(rule.feature_key)
            else:
                visible.append(rule.feature_key)

        return visible

    # ----------------------------------------------------------------
    # Field-Level Security
    # ----------------------------------------------------------------

    def register_field_security(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        entity_type: str,
        field_name: str,
        category: FieldSecurityCategory,
        view_roles: list[str],
        mask_pattern: str = "***",
    ) -> FieldSecurityRule:
        """Register a field security rule for PII/financial masking."""
        roles = _norm_roles(actor_roles)
        if "admin" not in roles:
            raise PermissionError("Admin role required")

        rule = FieldSecurityRule(
            id=uuid4(),
            entity_type=entity_type,
            field_name=field_name,
            category=category,
            view_roles=tuple(r.lower().strip() for r in view_roles),
            mask_pattern=mask_pattern,
        )
        self._field_rules[rule.id] = rule

        self._emit_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="field_security.register",
            module="admin.system",
            entity_type="field_security_rule",
            entity_id=str(rule.id),
            outcome="success",
            correlation_id=correlation_id,
            metadata={
                "entity": entity_type,
                "field": field_name,
                "category": category.value,
            },
        )

        return rule

    def apply_field_masking(
        self,
        *,
        actor_roles: Iterable[str],
        entity_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply field-level masking to data based on actor roles."""
        roles = _norm_roles(actor_roles)
        result = dict(data)

        for rule in self._field_rules.values():
            if rule.entity_type != entity_type:
                continue

            if rule.field_name not in result:
                continue

            # Check if actor can view this field
            allowed_roles = frozenset(rule.view_roles)
            if not roles & allowed_roles:
                # Mask the field
                result[rule.field_name] = rule.mask_pattern

        return result

    def list_field_security_rules(
        self, *, actor_roles: Iterable[str]
    ) -> list[FieldSecurityRule]:
        """List all field security rules."""
        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor"}:
            raise PermissionError("Admin or auditor role required")
        return list(self._field_rules.values())

    # ----------------------------------------------------------------
    # Segregation of Duties (SoD)
    # ----------------------------------------------------------------

    def record_action(
        self,
        *,
        actor_id: str,
        entity_id: str,
        action: str,
    ) -> None:
        """Record an action for SoD tracking."""
        if entity_id not in self._action_history:
            self._action_history[entity_id] = []

        self._action_history[entity_id].append((action, actor_id, _utcnow()))

    def check_sod(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        module: str,
        action: str,
        entity_id: str,
        correlation_id: str,
    ) -> bool:
        """Check if action would violate SoD rules. Returns True if allowed."""
        roles = _norm_roles(actor_roles)

        # Find applicable SoD rules
        for rule in self._sod_rules.values():
            if not rule.enabled:
                continue
            if rule.module != module:
                continue

            # Check if this is the second action in a pair
            if action not in (rule.action2,):
                continue

            # Look for first action by same actor
            history = self._action_history.get(entity_id, [])
            for hist_action, hist_actor, hist_ts in history:
                if hist_action == rule.action1 and hist_actor == actor_id:
                    # SoD violation - same actor did action1
                    violation = SoDViolation(
                        id=uuid4(),
                        rule_id=rule.id,
                        actor_id=actor_id,
                        entity_type=module,
                        entity_id=entity_id,
                        action1_ts=hist_ts,
                        action2_ts=_utcnow(),
                        blocked=True,
                    )
                    self._sod_violations[violation.id] = violation

                    self._emit_audit(
                        actor_id=actor_id,
                        actor_roles=roles,
                        action=f"sod.violation.{rule.name}",
                        module=module,
                        entity_type="sod_violation",
                        entity_id=entity_id,
                        outcome="blocked_sod",
                        correlation_id=correlation_id,
                        metadata={
                            "rule": rule.name,
                            "action1": rule.action1,
                            "action2": action,
                        },
                    )

                    return False

        return True

    def require_sod_compliance(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        module: str,
        action: str,
        entity_id: str,
        correlation_id: str,
    ) -> None:
        """Require SoD compliance or raise PermissionError."""
        if not self.check_sod(
            actor_id=actor_id,
            actor_roles=actor_roles,
            module=module,
            action=action,
            entity_id=entity_id,
            correlation_id=correlation_id,
        ):
            raise PermissionError(
                "Segregation of duties violation: cannot perform both actions on same entity"
            )

    def add_sod_rule(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        name: str,
        rule_type: SoDRuleType,
        module: str,
        action1: str,
        action2: str,
        description: str = "",
    ) -> SoDRule:
        """Add a custom SoD rule."""
        roles = _norm_roles(actor_roles)
        if "admin" not in roles:
            raise PermissionError("Admin role required")

        rule = SoDRule(
            id=uuid4(),
            name=name,
            rule_type=rule_type,
            module=module,
            action1=action1,
            action2=action2,
            description=description,
        )
        self._sod_rules[rule.id] = rule

        self._emit_audit(
            actor_id=actor_id,
            actor_roles=roles,
            action="sod.rule.create",
            module="admin.roles",
            entity_type="sod_rule",
            entity_id=str(rule.id),
            outcome="success",
            correlation_id=correlation_id,
        )

        return rule

    def list_sod_rules(self, *, actor_roles: Iterable[str]) -> list[SoDRule]:
        """List all SoD rules."""
        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor"}:
            raise PermissionError("Admin or auditor role required")
        return list(self._sod_rules.values())

    def list_sod_violations(
        self, *, actor_roles: Iterable[str]
    ) -> list[SoDViolation]:
        """List all recorded SoD violations."""
        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor", "ceo"}:
            raise PermissionError("Admin, auditor, or CEO role required")
        return list(self._sod_violations.values())

    # ----------------------------------------------------------------
    # Immutable Audit Trail
    # ----------------------------------------------------------------

    def _emit_audit(
        self,
        *,
        actor_id: str,
        actor_roles: frozenset[str],
        action: str,
        module: str,
        entity_type: str,
        entity_id: str,
        outcome: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> ImmutableAuditEntry:
        """Emit an immutable audit entry."""
        import hashlib

        ts = _utcnow()

        # Create signature for tamper detection
        sig_content = f"{ts.isoformat()}{actor_id}{action}{entity_id}{correlation_id}"
        signature = hashlib.sha256(sig_content.encode()).hexdigest()[:32]

        entry = ImmutableAuditEntry(
            id=uuid4(),
            timestamp=ts,
            correlation_id=correlation_id,
            actor_id=actor_id,
            actor_roles=tuple(sorted(actor_roles)),
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=outcome,
            metadata=metadata or {},
            signature=signature,
        )
        self._audit_trail.append(entry)
        return entry

    def get_audit_trail(
        self,
        *,
        actor_roles: Iterable[str],
        correlation_id: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[ImmutableAuditEntry]:
        """Query the immutable audit trail."""
        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor", "ceo"}:
            raise PermissionError("Admin, auditor, or CEO role required")

        result = list(self._audit_trail)

        if correlation_id:
            result = [e for e in result if e.correlation_id == correlation_id]

        if entity_id:
            result = [e for e in result if e.entity_id == entity_id]

        if module:
            result = [e for e in result if e.module == module]

        if start_date:
            result = [e for e in result if e.timestamp >= start_date]

        if end_date:
            result = [e for e in result if e.timestamp <= end_date]

        return result

    def verify_audit_integrity(
        self, *, actor_roles: Iterable[str]
    ) -> tuple[bool, int]:
        """Verify audit trail integrity. Returns (all_valid, invalid_count)."""
        import hashlib

        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor"}:
            raise PermissionError("Admin or auditor role required")

        invalid_count = 0
        for entry in self._audit_trail:
            sig_content = (
                f"{entry.timestamp.isoformat()}{entry.actor_id}"
                f"{entry.action}{entry.entity_id}{entry.correlation_id}"
            )
            expected_sig = hashlib.sha256(sig_content.encode()).hexdigest()[:32]
            if entry.signature != expected_sig:
                invalid_count += 1

        return (invalid_count == 0, invalid_count)

    # ----------------------------------------------------------------
    # Convenience: Permission Matrix Export
    # ----------------------------------------------------------------

    def get_permission_matrix(
        self, *, actor_roles: Iterable[str]
    ) -> dict[str, dict[str, list[str]]]:
        """Export the full permission matrix for documentation."""
        roles = _norm_roles(actor_roles)
        if not roles & {"admin", "auditor"}:
            raise PermissionError("Admin or auditor role required")

        matrix: dict[str, dict[str, list[str]]] = {}

        for module in Module:
            module_perms: dict[str, list[str]] = {}

            view_roles = _DEFAULT_VIEW_PERMISSIONS.get(module.value, frozenset())
            module_perms["view"] = sorted(view_roles)

            write_roles = _DEFAULT_WRITE_PERMISSIONS.get(module.value, frozenset())
            module_perms["write"] = sorted(write_roles)

            approve_roles = _DEFAULT_APPROVE_PERMISSIONS.get(module.value, frozenset())
            module_perms["approve"] = sorted(approve_roles)

            matrix[module.value] = module_perms

        return matrix
