"""Tests for Identity & Access Management service (identity_access.py)."""

from __future__ import annotations

from ipaddress import ip_network
from uuid import uuid4

import pytest

from sensei.services.identity_access import (
    AccessDecision,
    ConditionalAccessPolicy,
    DevicePosture,
    IdentityAccessService,
    SSOProtocol,
    SSOProvider,
)


@pytest.fixture
def svc() -> IdentityAccessService:
    return IdentityAccessService()


ADMIN_ROLES = ("admin",)
SECOPS_ROLES = ("secops",)
VIEWER_ROLES = ("viewer",)


class TestSSOProvider:
    def test_create_requires_admin_role(self, svc: IdentityAccessService) -> None:
        with pytest.raises(PermissionError):
            svc.create_sso_provider(
                name="Okta",
                protocol=SSOProtocol.OIDC,
                issuer="https://okta.example.com",
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

        provider = svc.create_sso_provider(
            name="Okta",
            protocol=SSOProtocol.OIDC,
            issuer="https://okta.example.com",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
            client_id="abc123",
        )

        assert isinstance(provider, SSOProvider)
        assert provider.name == "Okta"
        assert provider.protocol == SSOProtocol.OIDC
        assert provider.enabled is True

    def test_toggle_and_list_sso_provider(self, svc: IdentityAccessService) -> None:
        p1 = svc.create_sso_provider(
            name="Azure AD",
            protocol=SSOProtocol.SAML,
            issuer="https://login.microsoftonline.com",
            actor_user_id=uuid4(),
            actor_roles=SECOPS_ROLES,
            enabled=True,
        )

        disabled = svc.toggle_sso_provider(p1.id, enabled=False, actor_roles=ADMIN_ROLES)
        assert disabled.enabled is False

        all_providers = svc.list_sso_providers(actor_roles=ADMIN_ROLES)
        assert len(all_providers) == 1

        enabled_only = svc.list_sso_providers(actor_roles=ADMIN_ROLES, only_enabled=True)
        assert len(enabled_only) == 0


class TestConditionalAccess:
    def test_create_policy_requires_role(self, svc: IdentityAccessService) -> None:
        with pytest.raises(PermissionError):
            svc.create_conditional_access_policy(
                name="Block External",
                description="Block non-plant IPs",
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

    def test_policy_network_validation(self, svc: IdentityAccessService) -> None:
        # Invalid CIDR should raise ValueError.
        with pytest.raises(ValueError):
            svc.create_conditional_access_policy(
                name="Bad CIDR",
                description="Test",
                allowed_networks=["not-a-cidr"],
                actor_user_id=uuid4(),
                actor_roles=ADMIN_ROLES,
            )

    def test_policy_blocks_outside_network(self, svc: IdentityAccessService) -> None:
        svc.create_conditional_access_policy(
            name="Plant Subnet Only",
            description="Block external IPs",
            allowed_networks=["10.0.0.0/8"],
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        result_ok = svc.evaluate_access(
            user_roles=["operator"],
            source_ip="10.0.5.42",
            device_posture=DevicePosture.UNKNOWN,
        )
        assert result_ok.decision == AccessDecision.ALLOW

        result_blocked = svc.evaluate_access(
            user_roles=["operator"],
            source_ip="203.0.113.50",
            device_posture=DevicePosture.UNKNOWN,
        )
        assert result_blocked.decision == AccessDecision.DENY
        assert result_blocked.matched_policy_id is not None

    def test_policy_requires_compliant_device(self, svc: IdentityAccessService) -> None:
        svc.create_conditional_access_policy(
            name="Compliant Only",
            description="Require compliant device",
            require_compliant_device=True,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        compliant = svc.evaluate_access(
            user_roles=["operator"],
            source_ip="10.0.0.1",
            device_posture=DevicePosture.COMPLIANT,
        )
        assert compliant.decision == AccessDecision.ALLOW

        non_compliant = svc.evaluate_access(
            user_roles=["operator"],
            source_ip="10.0.0.1",
            device_posture=DevicePosture.NON_COMPLIANT,
        )
        assert non_compliant.decision == AccessDecision.DENY

    def test_invalid_ip_denied(self, svc: IdentityAccessService) -> None:
        result = svc.evaluate_access(
            user_roles=["operator"],
            source_ip="garbage",
            device_posture=DevicePosture.COMPLIANT,
        )
        assert result.decision == AccessDecision.DENY
        assert "Invalid source IP" in result.reason
