"""E2E Tests for CEO Account & Persona Setup (Development Plan 20.1)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from sensei.services.core.persona_management import (
    AuditEventType,
    Persona,
    PersonaManagementService,
    PERSONA_FEATURES,
    PERSONA_ROLE_MAP,
    User,
)


@pytest.fixture
def svc() -> PersonaManagementService:
    return PersonaManagementService()


class TestCEOAccountCreation:
    def test_create_ceo_superuser(self, svc: PersonaManagementService) -> None:
        ceo = svc.create_ceo_account()

        assert ceo.email == "ceo@sensei.os"
        assert ceo.active_persona == Persona.CEO
        assert "superuser" in ceo.roles
        assert "admin" in ceo.roles
        assert "exec" in ceo.roles
        assert "gm" in ceo.roles

    def test_ceo_has_all_features(self, svc: PersonaManagementService) -> None:
        ceo = svc.create_ceo_account()
        features = svc.get_visible_features(ceo.id)

        # CEO should see all top-level features.
        assert "dashboard" in features
        assert "admin" in features
        assert "war_room" in features
        assert "employee_intelligence" in features
        assert "strategic_reports" in features


class TestGlobalPersonaVerification:
    def test_persona_overlay_switching(self, svc: PersonaManagementService) -> None:
        ceo = svc.create_ceo_account()

        # CEO can switch to any persona.
        for persona in [Persona.SALES, Persona.GM, Persona.OPERATOR, Persona.QUALITY]:
            switched = svc.switch_persona(ceo.id, new_persona=persona)
            assert switched.active_persona == persona

            # Features should change based on persona.
            features = svc.get_visible_features(ceo.id)
            expected_features = PERSONA_FEATURES[persona]
            assert features == expected_features

    def test_operator_cannot_switch_to_ceo(self, svc: PersonaManagementService) -> None:
        operator = svc.create_user(
            email="operator@sensei.os",
            name="Operator",
            persona=Persona.OPERATOR,
        )

        with pytest.raises(PermissionError):
            svc.switch_persona(operator.id, new_persona=Persona.CEO)

    def test_gm_limited_persona_switching(self, svc: PersonaManagementService) -> None:
        gm = svc.create_user(
            email="gm@sensei.os",
            name="General Manager",
            persona=Persona.GM,
        )

        # GM can switch to operator, quality, supervisor.
        for persona in [Persona.OPERATOR, Persona.QUALITY, Persona.SUPERVISOR]:
            switched = svc.switch_persona(gm.id, new_persona=persona)
            assert switched.active_persona == persona

        # GM cannot switch to CEO.
        with pytest.raises(PermissionError):
            svc.switch_persona(gm.id, new_persona=Persona.CEO)


class TestAuditLogAttribution:
    def test_impersonation_audit_attribution(self, svc: PersonaManagementService) -> None:
        ceo = svc.create_ceo_account()
        operator = svc.create_user(
            email="operator@sensei.os",
            name="Operator",
            persona=Persona.OPERATOR,
        )

        # CEO starts impersonating operator.
        svc.start_impersonation(ceo.id, target_user_id=operator.id)

        # Perform an action as the impersonated user.
        action_entry = svc.log_action(
            operator.id,
            action="created_work_order",
            resource="work_order",
            resource_id=uuid4(),
        )

        # Audit should show operator as user_id but CEO as actual_user_id.
        assert action_entry.user_id == operator.id
        assert action_entry.actual_user_id == ceo.id

        # Verify attribution.
        verified = svc.verify_audit_attribution(
            action_entry.id,
            expected_user_id=operator.id,
            expected_actual_user_id=ceo.id,
        )
        assert verified is True

    def test_impersonation_logs_start_and_end(self, svc: PersonaManagementService) -> None:
        ceo = svc.create_ceo_account()
        quality = svc.create_user(
            email="quality@sensei.os",
            name="Quality Engineer",
            persona=Persona.QUALITY,
        )

        svc.start_impersonation(ceo.id, target_user_id=quality.id)
        svc.end_impersonation(quality.id)

        # Check audit log for impersonation events.
        impersonation_events = svc.get_audit_log(event_type=AuditEventType.IMPERSONATION_START)
        assert len(impersonation_events) == 1
        assert impersonation_events[0].user_id == quality.id
        assert impersonation_events[0].actual_user_id == ceo.id

        end_events = svc.get_audit_log(event_type=AuditEventType.IMPERSONATION_END)
        assert len(end_events) == 1

    def test_persona_switch_logged(self, svc: PersonaManagementService) -> None:
        ceo = svc.create_ceo_account()
        svc.switch_persona(ceo.id, new_persona=Persona.GM)

        switch_events = svc.get_audit_log(event_type=AuditEventType.PERSONA_SWITCH)
        assert len(switch_events) == 1
        assert switch_events[0].metadata["from_persona"] == "ceo"
        assert switch_events[0].metadata["to_persona"] == "gm"


class TestAllPersonaRoles:
    def test_all_personas_have_defined_roles(self) -> None:
        for persona in Persona:
            assert persona in PERSONA_ROLE_MAP
            assert len(PERSONA_ROLE_MAP[persona]) > 0

    def test_all_personas_have_defined_features(self) -> None:
        for persona in Persona:
            assert persona in PERSONA_FEATURES
            # All personas should at least see dashboard.
            assert "dashboard" in PERSONA_FEATURES[persona]

    def test_create_all_persona_users(self, svc: PersonaManagementService) -> None:
        for persona in Persona:
            user = svc.create_user(
                email=f"{persona.value}@sensei.os",
                name=f"{persona.value.title()} User",
                persona=persona,
            )

            assert user.active_persona == persona
            assert user.roles == PERSONA_ROLE_MAP[persona]

            features = svc.get_visible_features(user.id)
            assert features == PERSONA_FEATURES[persona]


class TestFeatureAccessControl:
    def test_operator_cannot_see_admin(self, svc: PersonaManagementService) -> None:
        operator = svc.create_user(
            email="op@sensei.os",
            name="Op",
            persona=Persona.OPERATOR,
        )

        assert not svc.can_access_feature(operator.id, "admin")
        assert not svc.can_access_feature(operator.id, "hr")
        assert not svc.can_access_feature(operator.id, "finance")

    def test_hr_cannot_see_production(self, svc: PersonaManagementService) -> None:
        hr = svc.create_user(
            email="hr@sensei.os",
            name="HR",
            persona=Persona.HR,
        )

        assert not svc.can_access_feature(hr.id, "production")
        assert not svc.can_access_feature(hr.id, "andon")
        assert svc.can_access_feature(hr.id, "employees")
        assert svc.can_access_feature(hr.id, "training")

    def test_accountant_sees_finance_only(self, svc: PersonaManagementService) -> None:
        accountant = svc.create_user(
            email="acct@sensei.os",
            name="Accountant",
            persona=Persona.ACCOUNTANT,
        )

        assert svc.can_access_feature(accountant.id, "finance")
        assert svc.can_access_feature(accountant.id, "payroll")
        assert not svc.can_access_feature(accountant.id, "production")
        assert not svc.can_access_feature(accountant.id, "quality")

    def test_warehouse_sees_inventory(self, svc: PersonaManagementService) -> None:
        warehouse = svc.create_user(
            email="wh@sensei.os",
            name="Warehouse",
            persona=Persona.WAREHOUSE,
        )

        assert svc.can_access_feature(warehouse.id, "warehouse")
        assert svc.can_access_feature(warehouse.id, "inventory")
        assert svc.can_access_feature(warehouse.id, "kanban")
        assert not svc.can_access_feature(warehouse.id, "admin")
