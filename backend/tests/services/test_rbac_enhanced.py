"""Tests for Enhanced RBAC, Visibility, and SoD Service (Development Plan 22.8)."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from sensei.services.rbac_enhanced import (
    EnhancedRBACService,
    Module,
    Permission,
    FieldSecurityCategory,
    SoDRuleType,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def svc() -> EnhancedRBACService:
    return EnhancedRBACService()


@pytest.fixture
def admin_roles() -> set[str]:
    return {"admin"}


@pytest.fixture
def finance_roles() -> set[str]:
    return {"finance"}


@pytest.fixture
def hr_roles() -> set[str]:
    return {"hr"}


@pytest.fixture
def ops_roles() -> set[str]:
    return {"ops"}


@pytest.fixture
def auditor_roles() -> set[str]:
    return {"auditor"}


@pytest.fixture
def viewer_roles() -> set[str]:
    return {"viewer"}


# ============================================================
# Permission Matrix Tests
# ============================================================


class TestPermissionMatrix:
    def test_admin_can_view_all_modules(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        for module in Module:
            assert svc.check_permission(
                actor_id="admin1",
                actor_roles=admin_roles,
                module=module.value,
                permission="view",
                correlation_id="cor-1",
            )

    def test_finance_can_view_finance_modules(
        self, svc: EnhancedRBACService, finance_roles: set[str]
    ) -> None:
        finance_modules = [
            Module.FINANCE_GL,
            Module.FINANCE_AP,
            Module.FINANCE_AR,
            Module.FINANCE_PERIOD,
            Module.FINANCE_REPORTS,
        ]
        for module in finance_modules:
            assert svc.check_permission(
                actor_id="finance1",
                actor_roles=finance_roles,
                module=module.value,
                permission="view",
                correlation_id="cor-1",
            )

    def test_finance_cannot_view_hr_compensation(
        self, svc: EnhancedRBACService, finance_roles: set[str]
    ) -> None:
        assert not svc.check_permission(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.HR_COMPENSATION.value,
            permission="view",
            correlation_id="cor-1",
        )

    def test_hr_can_write_to_hr_modules(
        self, svc: EnhancedRBACService, hr_roles: set[str]
    ) -> None:
        hr_modules = [
            Module.HR_EMPLOYEE,
            Module.HR_COMPENSATION,
            Module.HR_LEAVE,
            Module.HR_RECRUITING,
            Module.HR_PERFORMANCE,
            Module.HR_ORG,
        ]
        for module in hr_modules:
            assert svc.check_permission(
                actor_id="hr1",
                actor_roles=hr_roles,
                module=module.value,
                permission="create",
                correlation_id="cor-1",
            )

    def test_viewer_cannot_write(
        self, svc: EnhancedRBACService, viewer_roles: set[str]
    ) -> None:
        assert not svc.check_permission(
            actor_id="viewer1",
            actor_roles=viewer_roles,
            module=Module.HR_ORG.value,
            permission="create",
            correlation_id="cor-1",
        )

    def test_require_permission_raises_on_denial(
        self, svc: EnhancedRBACService, viewer_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Permission denied"):
            svc.require_permission(
                actor_id="viewer1",
                actor_roles=viewer_roles,
                module=Module.ADMIN_USERS.value,
                permission="view",
                correlation_id="cor-1",
            )


# ============================================================
# Permission Grant Tests
# ============================================================


class TestPermissionGrants:
    def test_add_permission_grant(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        grant = svc.add_permission_grant(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            role="viewer",
            module=Module.FINANCE_GL.value,
            permission="view",
        )

        assert grant.role == "viewer"
        assert grant.module == Module.FINANCE_GL.value

    def test_custom_grant_enables_permission(
        self, svc: EnhancedRBACService, admin_roles: set[str], viewer_roles: set[str]
    ) -> None:
        # Initially viewer cannot view GL
        assert not svc.check_permission(
            actor_id="viewer1",
            actor_roles=viewer_roles,
            module=Module.FINANCE_GL.value,
            permission="view",
            correlation_id="cor-1",
        )

        # Add grant
        svc.add_permission_grant(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            role="viewer",
            module=Module.FINANCE_GL.value,
            permission="view",
        )

        # Now viewer can view GL
        assert svc.check_permission(
            actor_id="viewer1",
            actor_roles=viewer_roles,
            module=Module.FINANCE_GL.value,
            permission="view",
            correlation_id="cor-3",
        )

    def test_non_admin_cannot_add_grant(
        self, svc: EnhancedRBACService, finance_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Admin role required"):
            svc.add_permission_grant(
                actor_id="finance1",
                actor_roles=finance_roles,
                correlation_id="cor-1",
                role="viewer",
                module=Module.FINANCE_GL.value,
                permission="view",
            )


# ============================================================
# UI Visibility Tests
# ============================================================


class TestUIVisibility:
    def test_register_feature_visibility(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        rule = svc.register_feature_visibility(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            feature_key="nav.finance.gl",
            required_roles=["admin", "finance", "accountant"],
            description="GL navigation menu item",
        )

        assert rule.feature_key == "nav.finance.gl"

    def test_feature_visible_when_role_matches(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.register_feature_visibility(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            feature_key="nav.finance.gl",
            required_roles=["admin", "finance"],
        )

        assert svc.check_feature_visibility(
            actor_roles=finance_roles, feature_key="nav.finance.gl"
        )

    def test_feature_hidden_when_role_missing(
        self, svc: EnhancedRBACService, admin_roles: set[str], viewer_roles: set[str]
    ) -> None:
        svc.register_feature_visibility(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            feature_key="nav.finance.gl",
            required_roles=["admin", "finance"],
        )

        assert not svc.check_feature_visibility(
            actor_roles=viewer_roles, feature_key="nav.finance.gl"
        )

    def test_get_visible_features(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.register_feature_visibility(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            feature_key="nav.finance.gl",
            required_roles=["admin", "finance"],
        )
        svc.register_feature_visibility(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-2",
            feature_key="nav.hr.employees",
            required_roles=["admin", "hr"],
        )

        visible = svc.get_visible_features(actor_roles=finance_roles)
        assert "nav.finance.gl" in visible
        assert "nav.hr.employees" not in visible


# ============================================================
# Field-Level Security Tests
# ============================================================


class TestFieldSecurity:
    def test_register_field_security(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        rule = svc.register_field_security(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type="employee",
            field_name="ssn",
            category=FieldSecurityCategory.PII,
            view_roles=["admin", "hr"],
            mask_pattern="***-**-****",
        )

        assert rule.field_name == "ssn"
        assert rule.category == FieldSecurityCategory.PII

    def test_field_visible_to_authorized_role(
        self, svc: EnhancedRBACService, admin_roles: set[str], hr_roles: set[str]
    ) -> None:
        svc.register_field_security(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type="employee",
            field_name="ssn",
            category=FieldSecurityCategory.PII,
            view_roles=["admin", "hr"],
        )

        data = {"name": "John Doe", "ssn": "123-45-6789"}
        result = svc.apply_field_masking(
            actor_roles=hr_roles, entity_type="employee", data=data
        )

        assert result["ssn"] == "123-45-6789"
        assert result["name"] == "John Doe"

    def test_field_masked_for_unauthorized_role(
        self, svc: EnhancedRBACService, admin_roles: set[str], viewer_roles: set[str]
    ) -> None:
        svc.register_field_security(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type="employee",
            field_name="ssn",
            category=FieldSecurityCategory.PII,
            view_roles=["admin", "hr"],
            mask_pattern="***-**-****",
        )

        data = {"name": "John Doe", "ssn": "123-45-6789"}
        result = svc.apply_field_masking(
            actor_roles=viewer_roles, entity_type="employee", data=data
        )

        assert result["ssn"] == "***-**-****"
        assert result["name"] == "John Doe"

    def test_financial_masking(
        self, svc: EnhancedRBACService, admin_roles: set[str], ops_roles: set[str]
    ) -> None:
        svc.register_field_security(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            entity_type="employee",
            field_name="hourly_rate",
            category=FieldSecurityCategory.FINANCIAL,
            view_roles=["admin", "hr", "finance"],
            mask_pattern="$**.** ",
        )

        data = {"name": "John Doe", "hourly_rate": "$45.00"}
        result = svc.apply_field_masking(
            actor_roles=ops_roles, entity_type="employee", data=data
        )

        assert result["hourly_rate"] == "$**.** "


# ============================================================
# Segregation of Duties (SoD) Tests
# ============================================================


class TestSoD:
    def test_default_sod_rules_exist(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        rules = svc.list_sod_rules(actor_roles=admin_roles)
        assert len(rules) >= 5  # 5 default rules

        rule_names = [r.name for r in rules]
        assert "Payment Create-Approve" in rule_names
        assert "Payroll Rate Create-Approve" in rule_names

    def test_sod_allows_different_actors(
        self, svc: EnhancedRBACService, finance_roles: set[str]
    ) -> None:
        # Actor 1 creates
        svc.record_action(
            actor_id="finance1", entity_id="PAYMENT-001", action="create"
        )

        # Actor 2 can approve
        assert svc.check_sod(
            actor_id="finance2",
            actor_roles=finance_roles,
            module=Module.FINANCE_AP.value,
            action="approve",
            entity_id="PAYMENT-001",
            correlation_id="cor-1",
        )

    def test_sod_blocks_same_actor(
        self, svc: EnhancedRBACService, finance_roles: set[str]
    ) -> None:
        # Same actor creates
        svc.record_action(
            actor_id="finance1", entity_id="PAYMENT-002", action="create"
        )

        # Same actor tries to approve - blocked
        assert not svc.check_sod(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.FINANCE_AP.value,
            action="approve",
            entity_id="PAYMENT-002",
            correlation_id="cor-1",
        )

    def test_sod_violation_recorded(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.record_action(
            actor_id="finance1", entity_id="PAYMENT-003", action="create"
        )

        svc.check_sod(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.FINANCE_AP.value,
            action="approve",
            entity_id="PAYMENT-003",
            correlation_id="cor-1",
        )

        violations = svc.list_sod_violations(actor_roles=admin_roles)
        assert len(violations) == 1
        assert violations[0].actor_id == "finance1"
        assert violations[0].blocked is True

    def test_require_sod_raises(
        self, svc: EnhancedRBACService, finance_roles: set[str]
    ) -> None:
        svc.record_action(
            actor_id="finance1", entity_id="PAYMENT-004", action="create"
        )

        with pytest.raises(PermissionError, match="Segregation of duties"):
            svc.require_sod_compliance(
                actor_id="finance1",
                actor_roles=finance_roles,
                module=Module.FINANCE_AP.value,
                action="approve",
                entity_id="PAYMENT-004",
                correlation_id="cor-1",
            )

    def test_add_custom_sod_rule(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        rule = svc.add_sod_rule(
            actor_id="admin1",
            actor_roles=admin_roles,
            correlation_id="cor-1",
            name="Custom Rule",
            rule_type=SoDRuleType.CREATE_APPROVE,
            module="custom.module",
            action1="submit",
            action2="validate",
            description="Test custom rule",
        )

        assert rule.name == "Custom Rule"
        rules = svc.list_sod_rules(actor_roles=admin_roles)
        assert any(r.name == "Custom Rule" for r in rules)


# ============================================================
# Audit Trail Tests
# ============================================================


class TestAuditTrail:
    def test_permission_check_creates_audit_entry(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.check_permission(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.FINANCE_GL.value,
            permission="view",
            correlation_id="trace-123",
        )

        audit = svc.get_audit_trail(
            actor_roles=admin_roles, correlation_id="trace-123"
        )
        assert len(audit) >= 1
        assert any(e.action == "permission_check.view" for e in audit)

    def test_audit_includes_correlation_id(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.check_permission(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.FINANCE_AP.value,
            permission="create",
            correlation_id="cor-specific-789",
        )

        audit = svc.get_audit_trail(actor_roles=admin_roles)
        assert any(e.correlation_id == "cor-specific-789" for e in audit)

    def test_audit_records_denied_actions(
        self, svc: EnhancedRBACService, admin_roles: set[str], viewer_roles: set[str]
    ) -> None:
        # This should be denied
        svc.check_permission(
            actor_id="viewer1",
            actor_roles=viewer_roles,
            module=Module.ADMIN_USERS.value,
            permission="view",
            correlation_id="cor-denied",
        )

        audit = svc.get_audit_trail(actor_roles=admin_roles)
        denied = [e for e in audit if e.outcome == "denied"]
        assert len(denied) >= 1

    def test_audit_filter_by_module(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        svc.check_permission(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.FINANCE_GL.value,
            permission="view",
            correlation_id="cor-1",
        )
        svc.check_permission(
            actor_id="finance1",
            actor_roles=finance_roles,
            module=Module.FINANCE_AP.value,
            permission="view",
            correlation_id="cor-2",
        )

        audit = svc.get_audit_trail(
            actor_roles=admin_roles, module=Module.FINANCE_GL.value
        )
        assert all(e.module == Module.FINANCE_GL.value for e in audit)

    def test_audit_integrity_verification(
        self, svc: EnhancedRBACService, admin_roles: set[str], finance_roles: set[str]
    ) -> None:
        # Create some audit entries
        for i in range(5):
            svc.check_permission(
                actor_id="finance1",
                actor_roles=finance_roles,
                module=Module.FINANCE_GL.value,
                permission="view",
                correlation_id=f"cor-{i}",
            )

        valid, invalid_count = svc.verify_audit_integrity(actor_roles=admin_roles)
        assert valid is True
        assert invalid_count == 0


# ============================================================
# Permission Matrix Export Tests
# ============================================================


class TestPermissionMatrixExport:
    def test_get_permission_matrix(
        self, svc: EnhancedRBACService, admin_roles: set[str]
    ) -> None:
        matrix = svc.get_permission_matrix(actor_roles=admin_roles)

        assert Module.FINANCE_GL.value in matrix
        assert "view" in matrix[Module.FINANCE_GL.value]
        assert "write" in matrix[Module.FINANCE_GL.value]
        assert "approve" in matrix[Module.FINANCE_GL.value]

        # Check that finance has write to GL
        assert "finance" in matrix[Module.FINANCE_GL.value]["write"]

    def test_non_admin_cannot_export_matrix(
        self, svc: EnhancedRBACService, viewer_roles: set[str]
    ) -> None:
        with pytest.raises(PermissionError, match="Admin or auditor role required"):
            svc.get_permission_matrix(actor_roles=viewer_roles)
