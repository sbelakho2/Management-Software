"""E2E UI/UX Verification Service (Development Plan 20.2).

This service provides validation tools for the "Sensei Gold" UI/UX audit:
- Visual hierarchy & typography verification
- Responsive & device integrity testing
- Interaction & feedback validation
- Accessibility (WCAG 2.1 AA) compliance scanning
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    pass


class Breakpoint(str, Enum):
    MOBILE_XS = "320px"
    MOBILE = "375px"
    TABLET = "768px"
    DESKTOP = "1024px"
    DESKTOP_LG = "1280px"
    DESKTOP_XL = "1440px"
    FOUR_K = "3840px"


class DeviceType(str, Enum):
    IPHONE_15 = "iphone_15"
    IPHONE_16 = "iphone_16"
    IPAD = "ipad"
    ANDROID_TABLET = "android_tablet"
    DESKTOP = "desktop"
    WAR_ROOM = "war_room"


class AccessibilityLevel(str, Enum):
    WCAG_A = "A"
    WCAG_AA = "AA"
    WCAG_AAA = "AAA"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Design tokens that must be used (no hardcoded values).
DESIGN_TOKENS = {
    "colors": {
        "primary": "var(--color-primary)",
        "secondary": "var(--color-secondary)",
        "danger": "var(--color-danger)",
        "success": "var(--color-success)",
        "warning": "var(--color-warning)",
        "surface": "var(--color-surface)",
        "background": "var(--color-background)",
    },
    "spacing": {
        "xs": "var(--spacing-xs)",
        "sm": "var(--spacing-sm)",
        "md": "var(--spacing-md)",
        "lg": "var(--spacing-lg)",
        "xl": "var(--spacing-xl)",
    },
    "typography": {
        "heading_1": {"size": "var(--font-size-3xl)", "weight": 700},
        "heading_2": {"size": "var(--font-size-2xl)", "weight": 600},
        "heading_3": {"size": "var(--font-size-xl)", "weight": 600},
        "heading_4": {"size": "var(--font-size-lg)", "weight": 500},
        "body": {"size": "var(--font-size-base)", "weight": 400},
        "caption": {"size": "var(--font-size-sm)", "weight": 400},
    },
    "elevation": {
        "surface": "var(--elevation-0)",
        "raised": "var(--elevation-1)",
        "overlay": "var(--elevation-2)",
        "modal": "var(--elevation-3)",
        "popover": "var(--elevation-4)",
    },
}

# Safe areas for various devices (Dynamic Island, Home Indicator).
DEVICE_SAFE_AREAS = {
    DeviceType.IPHONE_15: {"top": 59, "bottom": 34},
    DeviceType.IPHONE_16: {"top": 59, "bottom": 34},
    DeviceType.IPAD: {"top": 24, "bottom": 20},
    DeviceType.ANDROID_TABLET: {"top": 24, "bottom": 0},
    DeviceType.DESKTOP: {"top": 0, "bottom": 0},
    DeviceType.WAR_ROOM: {"top": 0, "bottom": 0},
}


@dataclass
class TypographyIssue:
    id: UUID = field(default_factory=uuid4)
    element: str = ""
    expected_weight: int = 500
    actual_weight: int = 400
    expected_token: str = ""
    actual_value: str = ""
    severity: str = "warning"
    message: str = ""


@dataclass
class LayoutIssue:
    id: UUID = field(default_factory=uuid4)
    element: str = ""
    breakpoint: Breakpoint = Breakpoint.MOBILE
    issue_type: str = ""
    expected: str = ""
    actual: str = ""
    severity: str = "error"
    message: str = ""


@dataclass
class AccessibilityIssue:
    id: UUID = field(default_factory=uuid4)
    element: str = ""
    wcag_criterion: str = ""
    level: AccessibilityLevel = AccessibilityLevel.WCAG_AA
    severity: str = "error"
    message: str = ""
    suggested_fix: str = ""


@dataclass
class InteractionMetrics:
    element: str
    response_time_ms: float
    layout_shift: float  # CLS score.
    has_haptic_feedback: bool
    has_skeleton_loader: bool
    is_optimistic: bool


@dataclass
class AuditReport:
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    typography_issues: list[TypographyIssue] = field(default_factory=list)
    layout_issues: list[LayoutIssue] = field(default_factory=list)
    accessibility_issues: list[AccessibilityIssue] = field(default_factory=list)
    interaction_issues: list[str] = field(default_factory=list)
    tokens_compliant: bool = True
    overall_passed: bool = True


class UIUXVerificationService:
    """E2E verification service for Sensei Gold UI/UX audit."""

    ALLOWED_ROLES = {"admin", "ceo", "exec", "bi", "analyst", "secops"}

    def __init__(self) -> None:
        self._audit_reports: dict[UUID, AuditReport] = {}
        self._typography_scans: list[TypographyIssue] = []
        self._layout_scans: list[LayoutIssue] = []
        self._accessibility_scans: list[AccessibilityIssue] = []

    def _check_role(self, role: str) -> None:
        if role.lower() not in self.ALLOWED_ROLES:
            raise PermissionError(f"Role '{role}' cannot access UI/UX verification")

    # ---- Typography Audit ----

    def audit_typography(
        self,
        role: str,
        *,
        elements: list[dict],
    ) -> list[TypographyIssue]:
        """Audit font weights and type scale adherence.

        Args:
            role: User role performing audit.
            elements: List of dicts with 'name', 'type', 'weight', 'size'.

        Returns:
            List of typography issues found.
        """
        self._check_role(role)
        issues: list[TypographyIssue] = []

        for el in elements:
            el_name = el.get("name", "unknown")
            el_type = el.get("type", "body")
            weight = el.get("weight", 400)
            size = el.get("size", "")

            # Check heading weight >= 500.
            if el_type.startswith("heading") and weight < 500:
                expected = DESIGN_TOKENS["typography"].get(el_type.replace("_", "_"), {})
                issues.append(TypographyIssue(
                    element=el_name,
                    expected_weight=expected.get("weight", 500),
                    actual_weight=weight,
                    expected_token=el_type,
                    actual_value=str(weight),
                    severity="warning",
                    message=f"Heading '{el_name}' has weight {weight}, expected >= 500",
                ))

            # Check for hardcoded pixel values.
            if size and not size.startswith("var(--"):
                issues.append(TypographyIssue(
                    element=el_name,
                    expected_token="var(--font-size-*)",
                    actual_value=size,
                    severity="error",
                    message=f"Hardcoded size '{size}' found; use design tokens",
                ))

        self._typography_scans.extend(issues)
        return issues

    def verify_whitespace_surfaces(
        self,
        role: str,
        *,
        surfaces: list[dict],
    ) -> list[LayoutIssue]:
        """Verify 'Calm Surfaces' with token-based elevation.

        Args:
            role: User role performing audit.
            surfaces: List of dicts with 'name', 'elevation', 'separator'.

        Returns:
            List of layout issues found.
        """
        self._check_role(role)
        issues: list[LayoutIssue] = []

        for surface in surfaces:
            name = surface.get("name", "unknown")
            elevation = surface.get("elevation", "")
            separator = surface.get("separator", "")

            # Elevation must use tokens.
            if elevation and not elevation.startswith("var(--elevation"):
                issues.append(LayoutIssue(
                    element=name,
                    issue_type="hardcoded_elevation",
                    expected="var(--elevation-*)",
                    actual=elevation,
                    severity="error",
                    message=f"Surface '{name}' uses hardcoded elevation: {elevation}",
                ))

            # Separator must be subtle (token-based).
            if separator and "border" in separator.lower():
                if not separator.startswith("var(--"):
                    issues.append(LayoutIssue(
                        element=name,
                        issue_type="hardcoded_separator",
                        expected="var(--color-border)",
                        actual=separator,
                        severity="warning",
                        message=f"Surface '{name}' uses hardcoded separator color",
                    ))

        self._layout_scans.extend(issues)
        return issues

    def audit_design_tokens(
        self,
        role: str,
        *,
        stylesheet_content: str,
    ) -> tuple[bool, list[str]]:
        """Verify 100% design token adherence (no hardcoded hex/pixel values).

        Args:
            role: User role performing audit.
            stylesheet_content: CSS content to audit.

        Returns:
            Tuple of (compliant, list of violations).
        """
        self._check_role(role)
        violations: list[str] = []

        # Check for hardcoded hex colors.
        hex_pattern = r"#[0-9a-fA-F]{3,8}"
        hex_matches = re.findall(hex_pattern, stylesheet_content)
        for match in hex_matches:
            violations.append(f"Hardcoded hex color: {match}")

        # Check for hardcoded pixel values (but allow in var definitions).
        # Match px values not inside var() definitions.
        px_pattern = r"(?<!var\()[0-9]+px"
        lines = stylesheet_content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if ":root" in line or "--" in line:
                continue  # Skip token definitions.
            px_matches = re.findall(px_pattern, line)
            for match in px_matches:
                violations.append(f"Line {line_num}: Hardcoded pixel value: {match}")

        return len(violations) == 0, violations

    # ---- Responsive & Device Integrity ----

    def breakpoint_stress_test(
        self,
        role: str,
        *,
        layouts: dict[Breakpoint, dict],
    ) -> list[LayoutIssue]:
        """Test layout at all breakpoints from 320px to 4K.

        Args:
            role: User role performing test.
            layouts: Dict mapping breakpoints to layout info.

        Returns:
            List of layout issues found.
        """
        self._check_role(role)
        issues: list[LayoutIssue] = []

        required_breakpoints = set(Breakpoint)
        provided_breakpoints = set(layouts.keys())

        # Check all breakpoints are covered.
        missing = required_breakpoints - provided_breakpoints
        for bp in missing:
            issues.append(LayoutIssue(
                breakpoint=bp,
                issue_type="missing_breakpoint",
                expected="layout defined",
                actual="none",
                severity="error",
                message=f"No layout defined for breakpoint {bp.value}",
            ))

        # Check each layout for issues.
        for bp, layout in layouts.items():
            # Check for overflow.
            if layout.get("has_overflow", False):
                issues.append(LayoutIssue(
                    breakpoint=bp,
                    issue_type="horizontal_overflow",
                    severity="error",
                    message=f"Horizontal overflow at {bp.value}",
                ))

            # Check for overlapping elements.
            if layout.get("has_overlap", False):
                issues.append(LayoutIssue(
                    breakpoint=bp,
                    issue_type="element_overlap",
                    severity="error",
                    message=f"Element overlap at {bp.value}",
                ))

            # Check text truncation.
            if layout.get("truncated_text", False):
                issues.append(LayoutIssue(
                    breakpoint=bp,
                    issue_type="text_truncation",
                    severity="warning",
                    message=f"Unintended text truncation at {bp.value}",
                ))

        self._layout_scans.extend(issues)
        return issues

    def verify_safe_areas(
        self,
        role: str,
        *,
        device: DeviceType,
        nav_top: int,
        nav_bottom: int,
    ) -> tuple[bool, str]:
        """Verify navigation clears safe areas (Dynamic Island, Home Indicator).

        Args:
            role: User role performing test.
            device: Device type to test.
            nav_top: Top navigation clearance in pixels.
            nav_bottom: Bottom navigation clearance in pixels.

        Returns:
            Tuple of (compliant, message).
        """
        self._check_role(role)

        safe = DEVICE_SAFE_AREAS.get(device, {"top": 0, "bottom": 0})

        if nav_top < safe["top"]:
            return False, f"Top nav ({nav_top}px) collides with safe area ({safe['top']}px)"

        if nav_bottom < safe["bottom"]:
            return False, f"Bottom nav ({nav_bottom}px) collides with safe area ({safe['bottom']}px)"

        return True, "Navigation respects all safe areas"

    def verify_container_max_width(
        self,
        role: str,
        *,
        container_width: int,
        font_size: int = 16,
    ) -> tuple[bool, int]:
        """Verify container max-width limits line length to 80-100 characters.

        Args:
            role: User role performing test.
            container_width: Container width in pixels.
            font_size: Base font size in pixels.

        Returns:
            Tuple of (compliant, estimated characters per line).
        """
        self._check_role(role)

        # Average character width is ~0.5em.
        avg_char_width = font_size * 0.5
        chars_per_line = int(container_width / avg_char_width)

        return 80 <= chars_per_line <= 100, chars_per_line

    # ---- Interaction & Feedback ----

    def audit_micro_interactions(
        self,
        role: str,
        *,
        interactions: list[InteractionMetrics],
    ) -> list[str]:
        """Audit micro-interactions for 100ms response time.

        Args:
            role: User role performing audit.
            interactions: List of interaction metrics.

        Returns:
            List of issues found.
        """
        self._check_role(role)
        issues: list[str] = []

        for interaction in interactions:
            if interaction.response_time_ms > 100:
                issues.append(
                    f"'{interaction.element}' response time {interaction.response_time_ms}ms > 100ms"
                )

            # CLS should be < 0.1.
            if interaction.layout_shift >= 0.1:
                issues.append(
                    f"'{interaction.element}' has CLS {interaction.layout_shift} >= 0.1"
                )

        return issues

    def verify_skeleton_transitions(
        self,
        role: str,
        *,
        transitions: list[dict],
    ) -> tuple[float, list[str]]:
        """Verify skeleton transitions have zero layout shift.

        Args:
            role: User role performing verification.
            transitions: List of transition measurements.

        Returns:
            Tuple of (max CLS, list of violations).
        """
        self._check_role(role)
        violations: list[str] = []
        max_cls = 0.0

        for transition in transitions:
            name = transition.get("name", "unknown")
            cls = transition.get("cls", 0.0)

            if cls > max_cls:
                max_cls = cls

            if cls >= 0.1:
                violations.append(f"'{name}' has CLS {cls} (expected < 0.1)")

        return max_cls, violations

    def verify_haptic_feedback(
        self,
        role: str,
        *,
        elements: list[dict],
    ) -> list[str]:
        """Verify haptic feedback on mobile for Andon triggers and errors.

        Args:
            role: User role performing verification.
            elements: List of element configurations.

        Returns:
            List of missing haptic feedback.
        """
        self._check_role(role)
        missing: list[str] = []

        for el in elements:
            name = el.get("name", "unknown")
            el_type = el.get("type", "")
            has_haptic = el.get("has_haptic", False)

            # Andon triggers and errors must have haptic.
            if el_type in ("andon_trigger", "error", "critical_action"):
                if not has_haptic:
                    missing.append(f"'{name}' ({el_type}) missing haptic feedback")

        return missing

    def verify_optimistic_ui(
        self,
        role: str,
        *,
        operations: list[dict],
    ) -> list[str]:
        """Verify optimistic UI with sync rollback logic.

        Args:
            role: User role performing verification.
            operations: List of optimistic operations.

        Returns:
            List of issues found.
        """
        self._check_role(role)
        issues: list[str] = []

        for op in operations:
            name = op.get("name", "unknown")
            is_optimistic = op.get("is_optimistic", False)
            has_rollback = op.get("has_rollback", False)
            sync_confirmed = op.get("sync_confirmed", False)

            if is_optimistic:
                if not has_rollback:
                    issues.append(f"'{name}' is optimistic but lacks rollback logic")
                if not sync_confirmed:
                    issues.append(f"'{name}' optimistic update not confirmed by sync")

        return issues

    # ---- Accessibility (WCAG 2.1 AA) ----

    def keyboard_navigation_test(
        self,
        role: str,
        *,
        flow: list[str],
        keyboard_only: bool = True,
    ) -> tuple[bool, list[str]]:
        """Test keyboard-only navigation through a workflow.

        Args:
            role: User role performing test.
            flow: List of steps in the workflow.
            keyboard_only: Whether to enforce keyboard-only navigation.

        Returns:
            Tuple of (all navigable, list of blocked steps).
        """
        self._check_role(role)

        # Simulated keyboard navigation test.
        blocked: list[str] = []

        for step in flow:
            # Simulate checking if step is keyboard navigable.
            # In real implementation, would check tabindex, focus management.
            step_lower = step.lower()
            if "modal" in step_lower and "trap" not in step_lower:
                blocked.append(f"'{step}': Modal without focus trap")
            if "dropdown" in step_lower and "aria" not in step_lower:
                blocked.append(f"'{step}': Dropdown not keyboard accessible")

        return len(blocked) == 0, blocked

    def screen_reader_audit(
        self,
        role: str,
        *,
        elements: list[dict],
    ) -> list[AccessibilityIssue]:
        """Audit elements for screen reader compatibility.

        Args:
            role: User role performing audit.
            elements: List of element configurations.

        Returns:
            List of accessibility issues.
        """
        self._check_role(role)
        issues: list[AccessibilityIssue] = []

        for el in elements:
            name = el.get("name", "unknown")
            el_type = el.get("type", "")
            aria_label = el.get("aria_label", "")
            role_attr = el.get("role", "")
            landmark = el.get("landmark", "")

            # Icons must have aria-label.
            if el_type == "icon" and not aria_label:
                issues.append(AccessibilityIssue(
                    element=name,
                    wcag_criterion="1.1.1",
                    level=AccessibilityLevel.WCAG_A,
                    message=f"Icon '{name}' missing aria-label",
                    suggested_fix="Add descriptive aria-label attribute",
                ))

            # Verify semantic landmarks.
            if el_type in ("header", "nav", "main", "footer") and not landmark:
                issues.append(AccessibilityIssue(
                    element=name,
                    wcag_criterion="1.3.1",
                    level=AccessibilityLevel.WCAG_A,
                    message=f"'{name}' missing semantic landmark",
                    suggested_fix=f"Use <{el_type}> element or role='{el_type}'",
                ))

            # Interactive elements need role.
            if el_type in ("button", "link", "menu") and not role_attr:
                if el.get("is_custom", False):
                    issues.append(AccessibilityIssue(
                        element=name,
                        wcag_criterion="4.1.2",
                        level=AccessibilityLevel.WCAG_A,
                        message=f"Custom interactive '{name}' missing role",
                        suggested_fix=f"Add role='{el_type}'",
                    ))

        self._accessibility_scans.extend(issues)
        return issues

    def hit_target_enforcement(
        self,
        role: str,
        *,
        targets: list[dict],
        is_shop_floor: bool = False,
    ) -> list[AccessibilityIssue]:
        """Verify hit targets meet size requirements.

        Args:
            role: User role performing verification.
            targets: List of interactive target measurements.
            is_shop_floor: Whether this is a shop-floor context.

        Returns:
            List of accessibility issues.
        """
        self._check_role(role)
        issues: list[AccessibilityIssue] = []

        min_size = 48 if is_shop_floor else 44

        for target in targets:
            name = target.get("name", "unknown")
            width = target.get("width", 0)
            height = target.get("height", 0)

            if width < min_size or height < min_size:
                issues.append(AccessibilityIssue(
                    element=name,
                    wcag_criterion="2.5.5",
                    level=AccessibilityLevel.WCAG_AAA,
                    message=f"Target '{name}' is {width}x{height}px, requires >= {min_size}x{min_size}px",
                    suggested_fix=f"Increase touch target to at least {min_size}x{min_size}px",
                ))

        self._accessibility_scans.extend(issues)
        return issues

    # ---- Comprehensive Audit ----

    def run_full_audit(
        self,
        role: str,
        *,
        typography_elements: list[dict] | None = None,
        surfaces: list[dict] | None = None,
        layouts: dict[Breakpoint, dict] | None = None,
        interactions: list[InteractionMetrics] | None = None,
        accessibility_elements: list[dict] | None = None,
        targets: list[dict] | None = None,
    ) -> AuditReport:
        """Run comprehensive UI/UX audit.

        Args:
            role: User role performing audit.
            Various element/layout configurations.

        Returns:
            Complete audit report.
        """
        self._check_role(role)

        report = AuditReport()

        if typography_elements:
            report.typography_issues.extend(
                self.audit_typography(role, elements=typography_elements)
            )

        if surfaces:
            report.layout_issues.extend(
                self.verify_whitespace_surfaces(role, surfaces=surfaces)
            )

        if layouts:
            report.layout_issues.extend(
                self.breakpoint_stress_test(role, layouts=layouts)
            )

        if interactions:
            report.interaction_issues.extend(
                self.audit_micro_interactions(role, interactions=interactions)
            )

        if accessibility_elements:
            report.accessibility_issues.extend(
                self.screen_reader_audit(role, elements=accessibility_elements)
            )

        if targets:
            report.accessibility_issues.extend(
                self.hit_target_enforcement(role, targets=targets)
            )

        # Determine overall pass/fail.
        has_errors = (
            any(i.severity == "error" for i in report.typography_issues)
            or any(i.severity == "error" for i in report.layout_issues)
            or any(i.level in {AccessibilityLevel.WCAG_A, AccessibilityLevel.WCAG_AA}
                   for i in report.accessibility_issues)
        )
        report.overall_passed = not has_errors

        self._audit_reports[report.id] = report
        return report

    def get_audit_report(self, report_id: UUID) -> AuditReport | None:
        return self._audit_reports.get(report_id)
