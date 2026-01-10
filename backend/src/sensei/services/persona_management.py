"""E2E Test Suite: CEO Account & Persona Setup (Development Plan 20.1).

Implements E2E validation for:
- CEO Account Creation: superuser with ADMIN/EXEC/GM roles.
- Persona Overlay Switching: Sales, GM, Operator, Quality views.
- Audit Log Attribution: actions during impersonation correctly attributed.

This module provides E2E test scenarios for persona and role switching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4


class Persona(str, Enum):
    CEO = "ceo"
    GM = "gm"
    SALES = "sales"
    OPERATOR = "operator"
    QUALITY = "quality"
    HR = "hr"
    ACCOUNTANT = "accountant"
    WAREHOUSE = "warehouse"
    SUPERVISOR = "supervisor"
    MAINTENANCE = "maintenance"


class AuditEventType(str, Enum):
    PERSONA_SWITCH = "persona_switch"
    ACTION_PERFORMED = "action_performed"
    LOGIN = "login"
    LOGOUT = "logout"
    IMPERSONATION_START = "impersonation_start"
    IMPERSONATION_END = "impersonation_end"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Role definitions for each persona.
PERSONA_ROLE_MAP: dict[Persona, set[str]] = {
    Persona.CEO: {"admin", "exec", "gm", "ceo"},
    Persona.GM: {"gm", "supervisor", "ops"},
    Persona.SALES: {"sales", "viewer"},
    Persona.OPERATOR: {"operator", "viewer"},
    Persona.QUALITY: {"quality", "viewer"},
    Persona.HR: {"hr", "viewer"},
    Persona.ACCOUNTANT: {"accountant", "viewer"},
    Persona.WAREHOUSE: {"warehouse", "operator", "viewer"},
    Persona.SUPERVISOR: {"supervisor", "ops", "viewer"},
    Persona.MAINTENANCE: {"maintenance", "operator", "viewer"},
}

# Feature visibility per persona.
PERSONA_FEATURES: dict[Persona, set[str]] = {
    Persona.CEO: {
        "dashboard", "pipeline", "quotes", "quality", "obeya", "analytics",
        "admin", "exceptions", "production", "warehouse", "hr", "finance",
        "war_room", "maturity_control", "strategic_reports", "employee_intelligence",
    },
    Persona.GM: {
        "dashboard", "pipeline", "quotes", "quality", "obeya", "analytics",
        "production", "warehouse", "exceptions", "maturity_control",
    },
    Persona.SALES: {
        "dashboard", "pipeline", "quotes", "rfq", "contacts", "accounts",
    },
    Persona.OPERATOR: {
        "dashboard", "production", "andon", "standard_work", "work_orders",
    },
    Persona.QUALITY: {
        "dashboard", "quality", "nc", "capa", "inspections", "calibration",
    },
    Persona.HR: {
        "dashboard", "hr", "employees", "training", "certifications", "attendance",
    },
    Persona.ACCOUNTANT: {
        "dashboard", "finance", "payroll", "costing", "reports",
    },
    Persona.WAREHOUSE: {
        "dashboard", "warehouse", "inventory", "receiving", "shipping", "kanban",
    },
    Persona.SUPERVISOR: {
        "dashboard", "production", "quality", "obeya", "andon", "team_schedule",
    },
    Persona.MAINTENANCE: {
        "dashboard", "maintenance", "equipment", "work_orders", "calibration",
    },
}


@dataclass
class User:
    id: UUID
    email: str
    name: str
    roles: set[str]
    active_persona: Persona
    is_impersonating: bool = False
    impersonating_user_id: UUID | None = None
    original_persona: Persona | None = None


@dataclass(frozen=True)
class AuditLogEntry:
    id: UUID
    timestamp: datetime
    user_id: UUID
    actual_user_id: UUID  # The real user (if impersonating).
    event_type: AuditEventType
    persona: Persona
    action: str
    resource: str | None
    resource_id: UUID | None
    metadata: dict[str, Any]


class PersonaManagementService:
    """Manages personas, impersonation, and audit logging for E2E testing."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._audit_log: list[AuditLogEntry] = []

    # ---- User Management ----

    def create_user(
        self,
        *,
        email: str,
        name: str,
        persona: Persona,
        additional_roles: set[str] | None = None,
    ) -> User:
        roles = PERSONA_ROLE_MAP.get(persona, set()).copy()
        if additional_roles:
            roles.update(additional_roles)

        user = User(
            id=uuid4(),
            email=email.lower().strip(),
            name=name,
            roles=roles,
            active_persona=persona,
            original_persona=persona,  # Track original for persona switching checks.
        )
        self._users[user.id] = user

        self._log_audit(
            user_id=user.id,
            actual_user_id=user.id,
            event_type=AuditEventType.LOGIN,
            persona=persona,
            action="user_created",
            resource="user",
            resource_id=user.id,
            metadata={"email": email},
        )

        return user

    def create_ceo_account(
        self,
        *,
        email: str = "ceo@sensei.os",
        name: str = "CEO User",
    ) -> User:
        """Create the superuser CEO account with all admin roles."""
        return self.create_user(
            email=email,
            name=name,
            persona=Persona.CEO,
            additional_roles={"superuser"},
        )

    def get_user(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def list_users(self) -> list[User]:
        return list(self._users.values())

    # ---- Persona Switching ----

    def switch_persona(
        self,
        user_id: UUID,
        *,
        new_persona: Persona,
    ) -> User:
        if user_id not in self._users:
            raise KeyError("User not found")

        user = self._users[user_id]
        old_persona = user.active_persona

        # CEO can switch to any persona.
        # Others can only switch within their allowed personas.
        allowed_personas = self._get_allowed_personas(user)
        if new_persona not in allowed_personas:
            raise PermissionError(f"User cannot switch to {new_persona.value} persona")

        user.active_persona = new_persona
        user.roles = PERSONA_ROLE_MAP.get(new_persona, set()).copy()

        # Keep superuser role if originally had it.
        if "superuser" in self._users[user_id].roles:
            user.roles.add("superuser")

        self._log_audit(
            user_id=user_id,
            actual_user_id=user.impersonating_user_id or user_id,
            event_type=AuditEventType.PERSONA_SWITCH,
            persona=new_persona,
            action="persona_switched",
            resource="persona",
            resource_id=None,
            metadata={"from_persona": old_persona.value, "to_persona": new_persona.value},
        )

        return user

    def _get_allowed_personas(self, user: User) -> set[Persona]:
        """Determine which personas a user can switch to."""
        # Check both original and active persona for privileges.
        original = user.original_persona or user.active_persona

        if "superuser" in user.roles or original == Persona.CEO:
            return set(Persona)

        if original == Persona.GM:
            return {Persona.GM, Persona.OPERATOR, Persona.QUALITY, Persona.SUPERVISOR}

        if original == Persona.SUPERVISOR:
            return {Persona.SUPERVISOR, Persona.OPERATOR}

        return {original}

    # ---- Impersonation ----

    def start_impersonation(
        self,
        admin_user_id: UUID,
        *,
        target_user_id: UUID,
    ) -> User:
        if admin_user_id not in self._users or target_user_id not in self._users:
            raise KeyError("User not found")

        admin_user = self._users[admin_user_id]
        target_user = self._users[target_user_id]

        # Only CEO/admin can impersonate.
        if "superuser" not in admin_user.roles and "admin" not in admin_user.roles:
            raise PermissionError("Only admins can impersonate users")

        # Cannot impersonate yourself.
        if admin_user_id == target_user_id:
            raise ValueError("Cannot impersonate yourself")

        target_user.is_impersonating = True
        target_user.impersonating_user_id = admin_user_id
        target_user.original_persona = target_user.active_persona

        self._log_audit(
            user_id=target_user_id,
            actual_user_id=admin_user_id,
            event_type=AuditEventType.IMPERSONATION_START,
            persona=target_user.active_persona,
            action="impersonation_started",
            resource="user",
            resource_id=target_user_id,
            metadata={
                "admin_email": admin_user.email,
                "target_email": target_user.email,
            },
        )

        return target_user

    def end_impersonation(self, target_user_id: UUID) -> User:
        if target_user_id not in self._users:
            raise KeyError("User not found")

        user = self._users[target_user_id]
        if not user.is_impersonating:
            raise ValueError("User is not being impersonated")

        admin_user_id = user.impersonating_user_id

        self._log_audit(
            user_id=target_user_id,
            actual_user_id=admin_user_id or target_user_id,
            event_type=AuditEventType.IMPERSONATION_END,
            persona=user.active_persona,
            action="impersonation_ended",
            resource="user",
            resource_id=target_user_id,
            metadata={},
        )

        user.is_impersonating = False
        user.impersonating_user_id = None
        if user.original_persona:
            user.active_persona = user.original_persona
            user.original_persona = None

        return user

    # ---- Feature Visibility ----

    def get_visible_features(self, user_id: UUID) -> set[str]:
        if user_id not in self._users:
            raise KeyError("User not found")

        user = self._users[user_id]
        return PERSONA_FEATURES.get(user.active_persona, set())

    def can_access_feature(self, user_id: UUID, feature: str) -> bool:
        visible = self.get_visible_features(user_id)
        return feature in visible

    # ---- Action Logging ----

    def log_action(
        self,
        user_id: UUID,
        *,
        action: str,
        resource: str | None = None,
        resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        if user_id not in self._users:
            raise KeyError("User not found")

        user = self._users[user_id]

        return self._log_audit(
            user_id=user_id,
            actual_user_id=user.impersonating_user_id or user_id,
            event_type=AuditEventType.ACTION_PERFORMED,
            persona=user.active_persona,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata=metadata or {},
        )

    def _log_audit(
        self,
        *,
        user_id: UUID,
        actual_user_id: UUID,
        event_type: AuditEventType,
        persona: Persona,
        action: str,
        resource: str | None,
        resource_id: UUID | None,
        metadata: dict[str, Any],
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            id=uuid4(),
            timestamp=_utcnow(),
            user_id=user_id,
            actual_user_id=actual_user_id,
            event_type=event_type,
            persona=persona,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata=metadata,
        )
        self._audit_log.append(entry)
        return entry

    def get_audit_log(
        self,
        *,
        user_id: UUID | None = None,
        actual_user_id: UUID | None = None,
        event_type: AuditEventType | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        result = self._audit_log.copy()

        if user_id:
            result = [e for e in result if e.user_id == user_id]
        if actual_user_id:
            result = [e for e in result if e.actual_user_id == actual_user_id]
        if event_type:
            result = [e for e in result if e.event_type == event_type]

        result.sort(key=lambda e: e.timestamp, reverse=True)
        return result[:limit]

    def verify_audit_attribution(
        self,
        entry_id: UUID,
        *,
        expected_user_id: UUID,
        expected_actual_user_id: UUID,
    ) -> bool:
        """Verify that an audit entry correctly attributes both visible and actual user."""
        for entry in self._audit_log:
            if entry.id == entry_id:
                return (
                    entry.user_id == expected_user_id
                    and entry.actual_user_id == expected_actual_user_id
                )
        return False
