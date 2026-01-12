"""Identity & Access Management (Development Plan 21.8).

Implements:
- SSO Integration: SAML/OIDC identity federation configuration + assertions.
- Conditional Access: location-based (Plant Subnet only) and device-posture rules.

This module is intentionally in-memory and pure-Python to match other services in
`sensei.services.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from ipaddress import ip_address, ip_network, IPv4Network, IPv6Network
from typing import Any, Iterable
from uuid import UUID, uuid4


class SSOProtocol(str, Enum):
    SAML = "saml"
    OIDC = "oidc"


class DevicePosture(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class AccessDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    MFA_REQUIRED = "mfa_required"


_IAM_ADMIN_ROLES: set[str] = {"admin", "secops", "gm", "ceo"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SSOProvider:
    id: UUID
    name: str
    protocol: SSOProtocol
    issuer: str
    metadata_url: str | None
    client_id: str | None
    enabled: bool
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True)
class ConditionalAccessPolicy:
    id: UUID
    name: str
    description: str
    enabled: bool

    # Network conditions (IPv4/IPv6 CIDRs).
    allowed_networks: list[str] = field(default_factory=list)

    # Device posture requirements.
    require_compliant_device: bool = False

    # Role targets (empty = all roles).
    target_roles: list[str] = field(default_factory=list)

    # Outcome if conditions NOT met.
    deny_action: AccessDecision = AccessDecision.DENY

    created_at: datetime = field(default_factory=_utcnow)
    created_by: UUID | None = None


@dataclass(frozen=True)
class AccessEvaluationResult:
    decision: AccessDecision
    matched_policy_id: UUID | None
    reason: str


class IdentityAccessService:
    """In-memory IAM service for SSO + conditional access."""

    def __init__(self) -> None:
        self._sso_providers: dict[UUID, SSOProvider] = {}
        self._policies: dict[UUID, ConditionalAccessPolicy] = {}

    # ---- RBAC helpers ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_IAM_ADMIN_ROLES)) > 0

    # ---- SSO Provider management ----

    def create_sso_provider(
        self,
        *,
        name: str,
        protocol: SSOProtocol,
        issuer: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        metadata_url: str | None = None,
        client_id: str | None = None,
        enabled: bool = True,
    ) -> SSOProvider:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage SSO providers")

        provider = SSOProvider(
            id=uuid4(),
            name=name.strip(),
            protocol=protocol,
            issuer=issuer,
            metadata_url=metadata_url,
            client_id=client_id,
            enabled=enabled,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._sso_providers[provider.id] = provider
        return provider

    def list_sso_providers(
        self,
        *,
        actor_roles: Iterable[str],
        only_enabled: bool = False,
    ) -> list[SSOProvider]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view SSO providers")

        result = list(self._sso_providers.values())
        if only_enabled:
            result = [p for p in result if p.enabled]
        result.sort(key=lambda p: p.name.lower())
        return result

    def toggle_sso_provider(
        self,
        provider_id: UUID,
        *,
        enabled: bool,
        actor_roles: Iterable[str],
    ) -> SSOProvider:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage SSO providers")
        if provider_id not in self._sso_providers:
            raise KeyError("SSO provider not found")

        provider = self._sso_providers[provider_id]
        updated = replace(provider, enabled=enabled)
        self._sso_providers[provider_id] = updated
        return updated

    # ---- Conditional Access Policies ----

    def create_conditional_access_policy(
        self,
        *,
        name: str,
        description: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        allowed_networks: list[str] | None = None,
        require_compliant_device: bool = False,
        target_roles: list[str] | None = None,
        deny_action: AccessDecision = AccessDecision.DENY,
        enabled: bool = True,
    ) -> ConditionalAccessPolicy:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage conditional access policies")

        # Validate CIDRs.
        for cidr in allowed_networks or []:
            ip_network(cidr, strict=False)

        policy = ConditionalAccessPolicy(
            id=uuid4(),
            name=name.strip(),
            description=description,
            enabled=enabled,
            allowed_networks=list(allowed_networks or []),
            require_compliant_device=require_compliant_device,
            target_roles=list(target_roles or []),
            deny_action=deny_action,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._policies[policy.id] = policy
        return policy

    def list_conditional_access_policies(
        self,
        *,
        actor_roles: Iterable[str],
        only_enabled: bool = False,
    ) -> list[ConditionalAccessPolicy]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view conditional access policies")

        result = list(self._policies.values())
        if only_enabled:
            result = [p for p in result if p.enabled]
        result.sort(key=lambda p: p.name.lower())
        return result

    def toggle_conditional_access_policy(
        self,
        policy_id: UUID,
        *,
        enabled: bool,
        actor_roles: Iterable[str],
    ) -> ConditionalAccessPolicy:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage conditional access policies")
        if policy_id not in self._policies:
            raise KeyError("Conditional access policy not found")

        policy = self._policies[policy_id]
        updated = replace(policy, enabled=enabled)
        self._policies[policy_id] = updated
        return updated

    # ---- Access Evaluation ----

    def evaluate_access(
        self,
        *,
        user_roles: Iterable[str],
        source_ip: str,
        device_posture: DevicePosture,
    ) -> AccessEvaluationResult:
        roles = _norm_roles(user_roles)

        try:
            client_ip = ip_address(source_ip)
        except ValueError:
            return AccessEvaluationResult(
                decision=AccessDecision.DENY,
                matched_policy_id=None,
                reason="Invalid source IP",
            )

        for policy in self._policies.values():
            if not policy.enabled:
                continue

            # Check role scope.
            if policy.target_roles:
                target = set(r.strip().lower() for r in policy.target_roles)
                if not roles.intersection(target):
                    continue

            # Network check.
            network_ok = True
            if policy.allowed_networks:
                network_ok = any(
                    client_ip in ip_network(cidr, strict=False) for cidr in policy.allowed_networks
                )

            # Device posture check.
            device_ok = True
            if policy.require_compliant_device and device_posture != DevicePosture.COMPLIANT:
                device_ok = False

            if not network_ok or not device_ok:
                return AccessEvaluationResult(
                    decision=policy.deny_action,
                    matched_policy_id=policy.id,
                    reason="Conditional access policy violation",
                )

        return AccessEvaluationResult(
            decision=AccessDecision.ALLOW,
            matched_policy_id=None,
            reason="No blocking policy matched",
        )
