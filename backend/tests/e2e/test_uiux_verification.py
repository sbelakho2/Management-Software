"""E2E Tests for UI/UX Verification Service (Development Plan 20.2)."""

from __future__ import annotations

import pytest

from sensei.services.utils.uiux_verification import (
    AccessibilityIssue,
    AccessibilityLevel,
    AuditReport,
    Breakpoint,
    DeviceType,
    InteractionMetrics,
    LayoutIssue,
    TypographyIssue,
    UIUXVerificationService,
)


@pytest.fixture
def svc() -> UIUXVerificationService:
    return UIUXVerificationService()


class TestTypographyAudit:
    def test_heading_weight_too_low(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Page Title", "type": "heading_1", "weight": 400, "size": "var(--font-size-3xl)"},
        ]
        issues = svc.audit_typography("admin", elements=elements)

        assert len(issues) == 1
        assert issues[0].actual_weight == 400
        assert issues[0].severity == "warning"
        assert "weight" in issues[0].message.lower()

    def test_heading_weight_sufficient(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Section Header", "type": "heading_2", "weight": 600, "size": "var(--font-size-2xl)"},
            {"name": "Card Title", "type": "heading_4", "weight": 500, "size": "var(--font-size-lg)"},
        ]
        issues = svc.audit_typography("admin", elements=elements)

        # No issues expected.
        assert len(issues) == 0

    def test_hardcoded_font_size(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Bad Text", "type": "body", "weight": 400, "size": "16px"},
        ]
        issues = svc.audit_typography("admin", elements=elements)

        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert "hardcoded" in issues[0].message.lower()

    def test_token_based_size(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Good Text", "type": "body", "weight": 400, "size": "var(--font-size-base)"},
        ]
        issues = svc.audit_typography("admin", elements=elements)

        assert len(issues) == 0


class TestWhitespaceSurfaces:
    def test_hardcoded_elevation(self, svc: UIUXVerificationService) -> None:
        surfaces = [
            {"name": "Card", "elevation": "0 2px 4px rgba(0,0,0,0.1)", "separator": ""},
        ]
        issues = svc.verify_whitespace_surfaces("admin", surfaces=surfaces)

        assert len(issues) == 1
        assert issues[0].issue_type == "hardcoded_elevation"

    def test_token_based_elevation(self, svc: UIUXVerificationService) -> None:
        surfaces = [
            {"name": "Card", "elevation": "var(--elevation-1)", "separator": ""},
        ]
        issues = svc.verify_whitespace_surfaces("admin", surfaces=surfaces)

        assert len(issues) == 0

    def test_hardcoded_separator(self, svc: UIUXVerificationService) -> None:
        surfaces = [
            {"name": "List Item", "elevation": "var(--elevation-0)", "separator": "border: 1px solid #ccc"},
        ]
        issues = svc.verify_whitespace_surfaces("admin", surfaces=surfaces)

        assert len(issues) == 1
        assert issues[0].issue_type == "hardcoded_separator"


class TestDesignTokenAudit:
    def test_hardcoded_hex_colors(self, svc: UIUXVerificationService) -> None:
        css = """
        .button {
            background-color: #3b82f6;
            color: #ffffff;
        }
        """
        compliant, violations = svc.audit_design_tokens("admin", stylesheet_content=css)

        assert not compliant
        assert len(violations) == 2
        assert any("#3b82f6" in v for v in violations)
        assert any("#ffffff" in v for v in violations)

    def test_token_based_colors(self, svc: UIUXVerificationService) -> None:
        css = """
        .button {
            background-color: var(--color-primary);
            color: var(--color-text-on-primary);
        }
        """
        compliant, violations = svc.audit_design_tokens("admin", stylesheet_content=css)

        assert compliant
        assert len(violations) == 0

    def test_hardcoded_pixels_detected(self, svc: UIUXVerificationService) -> None:
        css = """
        .card {
            padding: 16px;
            margin: 24px;
        }
        """
        compliant, violations = svc.audit_design_tokens("admin", stylesheet_content=css)

        assert not compliant
        assert len(violations) >= 2

    def test_token_definitions_allowed(self, svc: UIUXVerificationService) -> None:
        css = """
        :root {
            --spacing-md: 16px;
            --spacing-lg: 24px;
        }
        """
        compliant, violations = svc.audit_design_tokens("admin", stylesheet_content=css)

        assert compliant


class TestBreakpointStressTest:
    def test_missing_breakpoints(self, svc: UIUXVerificationService) -> None:
        layouts = {
            Breakpoint.MOBILE: {"has_overflow": False},
            Breakpoint.DESKTOP: {"has_overflow": False},
        }
        issues = svc.breakpoint_stress_test("admin", layouts=layouts)

        # Should report missing breakpoints.
        missing_issues = [i for i in issues if i.issue_type == "missing_breakpoint"]
        assert len(missing_issues) >= 4  # At least 4 missing.

    def test_all_breakpoints_covered(self, svc: UIUXVerificationService) -> None:
        layouts = {bp: {"has_overflow": False, "has_overlap": False} for bp in Breakpoint}
        issues = svc.breakpoint_stress_test("admin", layouts=layouts)

        assert len(issues) == 0

    def test_horizontal_overflow_detected(self, svc: UIUXVerificationService) -> None:
        layouts = {bp: {"has_overflow": False} for bp in Breakpoint}
        layouts[Breakpoint.MOBILE_XS] = {"has_overflow": True}

        issues = svc.breakpoint_stress_test("admin", layouts=layouts)

        overflow_issues = [i for i in issues if i.issue_type == "horizontal_overflow"]
        assert len(overflow_issues) == 1
        assert overflow_issues[0].breakpoint == Breakpoint.MOBILE_XS

    def test_element_overlap_detected(self, svc: UIUXVerificationService) -> None:
        layouts = {bp: {"has_overlap": False} for bp in Breakpoint}
        layouts[Breakpoint.TABLET] = {"has_overlap": True}

        issues = svc.breakpoint_stress_test("admin", layouts=layouts)

        overlap_issues = [i for i in issues if i.issue_type == "element_overlap"]
        assert len(overlap_issues) == 1


class TestSafeAreas:
    def test_iphone_15_safe_area_respected(self, svc: UIUXVerificationService) -> None:
        compliant, message = svc.verify_safe_areas(
            "admin",
            device=DeviceType.IPHONE_15,
            nav_top=60,
            nav_bottom=40,
        )

        assert compliant
        assert "respects" in message.lower()

    def test_iphone_15_top_collision(self, svc: UIUXVerificationService) -> None:
        compliant, message = svc.verify_safe_areas(
            "admin",
            device=DeviceType.IPHONE_15,
            nav_top=50,  # 59 required.
            nav_bottom=40,
        )

        assert not compliant
        assert "top" in message.lower()

    def test_iphone_16_bottom_collision(self, svc: UIUXVerificationService) -> None:
        compliant, message = svc.verify_safe_areas(
            "admin",
            device=DeviceType.IPHONE_16,
            nav_top=60,
            nav_bottom=30,  # 34 required.
        )

        assert not compliant
        assert "bottom" in message.lower()

    def test_desktop_no_safe_area(self, svc: UIUXVerificationService) -> None:
        compliant, _ = svc.verify_safe_areas(
            "admin",
            device=DeviceType.DESKTOP,
            nav_top=0,
            nav_bottom=0,
        )

        assert compliant


class TestContainerMaxWidth:
    def test_optimal_line_length(self, svc: UIUXVerificationService) -> None:
        # 16px font, 800px container = ~100 chars.
        compliant, chars = svc.verify_container_max_width(
            "admin",
            container_width=800,
            font_size=16,
        )

        assert compliant
        assert 80 <= chars <= 100

    def test_too_wide_container(self, svc: UIUXVerificationService) -> None:
        compliant, chars = svc.verify_container_max_width(
            "admin",
            container_width=1200,
            font_size=16,
        )

        assert not compliant
        assert chars > 100

    def test_too_narrow_container(self, svc: UIUXVerificationService) -> None:
        compliant, chars = svc.verify_container_max_width(
            "admin",
            container_width=400,
            font_size=16,
        )

        assert not compliant
        assert chars < 80


class TestMicroInteractions:
    def test_fast_response_time(self, svc: UIUXVerificationService) -> None:
        interactions = [
            InteractionMetrics(
                element="Save Button",
                response_time_ms=50,
                layout_shift=0.02,
                has_haptic_feedback=True,
                has_skeleton_loader=True,
                is_optimistic=True,
            ),
        ]
        issues = svc.audit_micro_interactions("admin", interactions=interactions)

        assert len(issues) == 0

    def test_slow_response_time(self, svc: UIUXVerificationService) -> None:
        interactions = [
            InteractionMetrics(
                element="Slow Action",
                response_time_ms=250,
                layout_shift=0.01,
                has_haptic_feedback=True,
                has_skeleton_loader=True,
                is_optimistic=True,
            ),
        ]
        issues = svc.audit_micro_interactions("admin", interactions=interactions)

        assert len(issues) == 1
        assert "250" in issues[0]
        assert "100ms" in issues[0]

    def test_high_layout_shift(self, svc: UIUXVerificationService) -> None:
        interactions = [
            InteractionMetrics(
                element="Shifty Element",
                response_time_ms=50,
                layout_shift=0.15,
                has_haptic_feedback=True,
                has_skeleton_loader=True,
                is_optimistic=True,
            ),
        ]
        issues = svc.audit_micro_interactions("admin", interactions=interactions)

        assert len(issues) == 1
        assert "CLS" in issues[0]


class TestSkeletonTransitions:
    def test_zero_layout_shift(self, svc: UIUXVerificationService) -> None:
        transitions = [
            {"name": "Card Loader", "cls": 0.02},
            {"name": "List Loader", "cls": 0.05},
        ]
        max_cls, violations = svc.verify_skeleton_transitions("admin", transitions=transitions)

        assert max_cls == 0.05
        assert len(violations) == 0

    def test_high_layout_shift(self, svc: UIUXVerificationService) -> None:
        transitions = [
            {"name": "Bad Loader", "cls": 0.25},
        ]
        max_cls, violations = svc.verify_skeleton_transitions("admin", transitions=transitions)

        assert max_cls == 0.25
        assert len(violations) == 1


class TestHapticFeedback:
    def test_andon_has_haptic(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Andon Button", "type": "andon_trigger", "has_haptic": True},
        ]
        missing = svc.verify_haptic_feedback("admin", elements=elements)

        assert len(missing) == 0

    def test_andon_missing_haptic(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Andon Button", "type": "andon_trigger", "has_haptic": False},
        ]
        missing = svc.verify_haptic_feedback("admin", elements=elements)

        assert len(missing) == 1
        assert "Andon Button" in missing[0]

    def test_error_missing_haptic(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Error Alert", "type": "error", "has_haptic": False},
        ]
        missing = svc.verify_haptic_feedback("admin", elements=elements)

        assert len(missing) == 1


class TestOptimisticUI:
    def test_optimistic_with_rollback(self, svc: UIUXVerificationService) -> None:
        operations = [
            {
                "name": "Task Complete",
                "is_optimistic": True,
                "has_rollback": True,
                "sync_confirmed": True,
            },
        ]
        issues = svc.verify_optimistic_ui("admin", operations=operations)

        assert len(issues) == 0

    def test_optimistic_without_rollback(self, svc: UIUXVerificationService) -> None:
        operations = [
            {
                "name": "Task Complete",
                "is_optimistic": True,
                "has_rollback": False,
                "sync_confirmed": True,
            },
        ]
        issues = svc.verify_optimistic_ui("admin", operations=operations)

        assert len(issues) == 1
        assert "rollback" in issues[0].lower()


class TestKeyboardNavigation:
    def test_all_steps_navigable(self, svc: UIUXVerificationService) -> None:
        flow = [
            "RFQ Form",
            "Submit Button",
            "Quote List",
            "Quote Detail",
            "Approve Button",
        ]
        navigable, blocked = svc.keyboard_navigation_test("admin", flow=flow)

        assert navigable
        assert len(blocked) == 0

    def test_modal_without_focus_trap(self, svc: UIUXVerificationService) -> None:
        flow = [
            "Open Button",
            "Modal Content",  # Missing focus trap.
        ]
        navigable, blocked = svc.keyboard_navigation_test("admin", flow=flow)

        assert not navigable
        assert len(blocked) == 1
        assert "Modal" in blocked[0]


class TestScreenReaderAudit:
    def test_icon_with_aria_label(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Settings Icon", "type": "icon", "aria_label": "Open settings"},
        ]
        issues = svc.screen_reader_audit("admin", elements=elements)

        assert len(issues) == 0

    def test_icon_without_aria_label(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Settings Icon", "type": "icon", "aria_label": ""},
        ]
        issues = svc.screen_reader_audit("admin", elements=elements)

        assert len(issues) == 1
        assert issues[0].wcag_criterion == "1.1.1"

    def test_missing_landmark(self, svc: UIUXVerificationService) -> None:
        elements = [
            {"name": "Header", "type": "header", "landmark": ""},
        ]
        issues = svc.screen_reader_audit("admin", elements=elements)

        assert len(issues) == 1
        assert issues[0].wcag_criterion == "1.3.1"


class TestHitTargetEnforcement:
    def test_mobile_target_44px(self, svc: UIUXVerificationService) -> None:
        targets = [
            {"name": "Button", "width": 44, "height": 44},
        ]
        issues = svc.hit_target_enforcement("admin", targets=targets, is_shop_floor=False)

        assert len(issues) == 0

    def test_mobile_target_too_small(self, svc: UIUXVerificationService) -> None:
        targets = [
            {"name": "Tiny Button", "width": 32, "height": 32},
        ]
        issues = svc.hit_target_enforcement("admin", targets=targets, is_shop_floor=False)

        assert len(issues) == 1
        assert "44x44" in issues[0].message

    def test_shop_floor_target_48px(self, svc: UIUXVerificationService) -> None:
        targets = [
            {"name": "Shop Button", "width": 48, "height": 48},
        ]
        issues = svc.hit_target_enforcement("admin", targets=targets, is_shop_floor=True)

        assert len(issues) == 0

    def test_shop_floor_target_too_small(self, svc: UIUXVerificationService) -> None:
        targets = [
            {"name": "Shop Button", "width": 44, "height": 44},
        ]
        issues = svc.hit_target_enforcement("admin", targets=targets, is_shop_floor=True)

        assert len(issues) == 1
        assert "48x48" in issues[0].message


class TestComprehensiveAudit:
    def test_full_audit_passed(self, svc: UIUXVerificationService) -> None:
        report = svc.run_full_audit(
            "admin",
            typography_elements=[
                {"name": "Title", "type": "heading_1", "weight": 700, "size": "var(--font-size-3xl)"},
            ],
            surfaces=[
                {"name": "Card", "elevation": "var(--elevation-1)", "separator": ""},
            ],
            layouts={bp: {"has_overflow": False, "has_overlap": False} for bp in Breakpoint},
            interactions=[
                InteractionMetrics(
                    element="Button",
                    response_time_ms=50,
                    layout_shift=0.01,
                    has_haptic_feedback=True,
                    has_skeleton_loader=True,
                    is_optimistic=True,
                ),
            ],
            accessibility_elements=[
                {"name": "Icon", "type": "icon", "aria_label": "Settings"},
            ],
            targets=[
                {"name": "Button", "width": 48, "height": 48},
            ],
        )

        assert report.overall_passed
        assert len(report.typography_issues) == 0
        assert len(report.layout_issues) == 0

    def test_full_audit_failed(self, svc: UIUXVerificationService) -> None:
        report = svc.run_full_audit(
            "admin",
            typography_elements=[
                {"name": "Bad Title", "type": "heading_1", "weight": 300, "size": "18px"},
            ],
        )

        assert not report.overall_passed
        assert len(report.typography_issues) >= 1


class TestRBACEnforcement:
    def test_viewer_cannot_audit(self, svc: UIUXVerificationService) -> None:
        with pytest.raises(PermissionError):
            svc.audit_typography("viewer", elements=[])

    def test_operator_cannot_audit(self, svc: UIUXVerificationService) -> None:
        with pytest.raises(PermissionError):
            svc.breakpoint_stress_test("operator", layouts={})

    def test_admin_can_audit(self, svc: UIUXVerificationService) -> None:
        issues = svc.audit_typography("admin", elements=[])
        assert issues == []

    def test_analyst_can_audit(self, svc: UIUXVerificationService) -> None:
        issues = svc.audit_typography("analyst", elements=[])
        assert issues == []

    def test_ceo_can_audit(self, svc: UIUXVerificationService) -> None:
        issues = svc.audit_typography("ceo", elements=[])
        assert issues == []
