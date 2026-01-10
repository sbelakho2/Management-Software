"""E2E Tests for CEO Strategic Control Plane Service (Development Plan 20.5)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from sensei.services.ceo_control_plane import (
    CEOControlPlaneService,
    EmployeeRiskAssessment,
    MetricType,
    NL2SQLQuery,
    RiskLevel,
    SQDCPMetric,
    SkillMatrixEntry,
    WarRoomDisplay,
)


@pytest.fixture
def svc() -> CEOControlPlaneService:
    return CEOControlPlaneService()


class TestNL2SQLStressTest:
    def test_margin_leakage_query(self, svc: CEOControlPlaneService) -> None:
        query = svc.generate_sql_from_nl(
            "ceo",
            natural_language="Show me margin leakage by supplier for Q3",
        )

        assert query.generated_sql is not None
        assert "supplier" in query.generated_sql.lower()
        assert "margin" in query.generated_sql.lower()
        assert query.plain_english_explanation != ""

    def test_revenue_by_product_query(self, svc: CEOControlPlaneService) -> None:
        query = svc.generate_sql_from_nl(
            "ceo",
            natural_language="Revenue breakdown by product category",
        )

        assert "product" in query.generated_sql.lower()
        assert "revenue" in query.generated_sql.lower()

    def test_quote_conversion_query(self, svc: CEOControlPlaneService) -> None:
        query = svc.generate_sql_from_nl(
            "ceo",
            natural_language="What is our quote conversion rate by month?",
        )

        assert "quote" in query.generated_sql.lower()
        assert "won" in query.generated_sql.lower() or "rate" in query.generated_sql.lower()

    def test_sql_validation_passes(self, svc: CEOControlPlaneService) -> None:
        query = svc.generate_sql_from_nl(
            "ceo",
            natural_language="Margin leakage by supplier",
        )

        is_valid, notes = svc.validate_sql_accuracy("ceo", query=query)

        assert is_valid
        assert "validated" in notes.lower()

    def test_explanation_matches_sql(self, svc: CEOControlPlaneService) -> None:
        query = svc.generate_sql_from_nl(
            "ceo",
            natural_language="Margin leakage by supplier for Q3",
        )

        matches, notes = svc.verify_explanation_matches_sql("ceo", query=query)

        assert matches
        assert "match" in notes.lower()

    def test_50_complex_queries(self, svc: CEOControlPlaneService) -> None:
        """Stress test with 50 varied queries."""
        queries = [
            "Show me margin leakage by supplier for Q3",
            "Revenue breakdown by product category",
            "Quote conversion rate by sales rep",
            "Customer concentration analysis",
            "Production efficiency by cell",
            "Quality defect rate trends",
            "On-time delivery performance",
            "Cost variance by department",
            "Employee productivity metrics",
            "RFQ response time analysis",
        ] * 5  # 50 queries.

        results = []
        for nl in queries:
            query = svc.generate_sql_from_nl("ceo", natural_language=nl)
            is_valid, _ = svc.validate_sql_accuracy("ceo", query=query)
            results.append(is_valid)

        # Expect 100% accuracy.
        accuracy = sum(results) / len(results)
        assert accuracy == 1.0, f"SQL accuracy: {accuracy:.0%}"


class TestEmployeeIntelligence:
    def test_retention_risk_high(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="John Doe", department="Engineering")

        assessment = svc.assess_retention_risk(
            "ceo",
            employee_id=emp_id,
            tenure_months=3,  # New employee.
            overtime_hours_weekly=5,
            skip_rate=0.25,  # High skip rate.
            peer_comparison=0.9,
        )

        assert assessment.retention_risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)
        assert len(assessment.risk_factors) >= 1

    def test_burnout_risk_critical(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="Jane Smith", department="Production")

        assessment = svc.assess_retention_risk(
            "ceo",
            employee_id=emp_id,
            tenure_months=24,
            overtime_hours_weekly=20,  # Excessive overtime.
            skip_rate=0.1,
            peer_comparison=1.4,  # Outperforming significantly.
        )

        assert assessment.burnout_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert any("overtime" in f.lower() for f in assessment.risk_factors)

    def test_healthy_employee(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="Bob Wilson", department="Quality")

        assessment = svc.assess_retention_risk(
            "ceo",
            employee_id=emp_id,
            tenure_months=18,
            overtime_hours_weekly=2,
            skip_rate=0.05,
            peer_comparison=1.0,
        )

        assert assessment.retention_risk == RiskLevel.LOW
        assert assessment.burnout_risk == RiskLevel.LOW

    def test_retention_risk_with_recommendations(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="Test Employee", department="Sales")

        assessment = svc.assess_retention_risk(
            "ceo",
            employee_id=emp_id,
            tenure_months=30,
            overtime_hours_weekly=0,
            skip_rate=0.3,  # Very high skip rate.
            peer_comparison=0.7,  # Underperforming.
        )

        assert len(assessment.recommendations) > 0


class TestSkillMatrix:
    def test_skill_acquisition_from_tasks(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="Test User", department="QA")

        # Record multiple task contributions.
        for _ in range(10):
            svc.record_skill_contribution(
                "ceo",
                employee_id=emp_id,
                skill_name="Quality Inspection",
                contribution_type="task",
            )

        matches, details = svc.verify_skill_matrix_accuracy(
            "ceo",
            employee_id=emp_id,
            skill_name="Quality Inspection",
            expected_tasks=10,
            expected_a3=0,
        )

        assert matches
        assert "10 tasks" in details

    def test_skill_acquisition_from_a3(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="A3 Expert", department="Engineering")

        # Record A3 contributions (worth more).
        for _ in range(3):
            svc.record_skill_contribution(
                "ceo",
                employee_id=emp_id,
                skill_name="Problem Solving",
                contribution_type="a3",
            )

        matches, details = svc.verify_skill_matrix_accuracy(
            "ceo",
            employee_id=emp_id,
            skill_name="Problem Solving",
            expected_tasks=0,
            expected_a3=3,
        )

        assert matches

    def test_proficiency_level_increases(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="Learner", department="Ops")

        # Record many contributions to increase level.
        for _ in range(15):
            entry = svc.record_skill_contribution(
                "ceo",
                employee_id=emp_id,
                skill_name="Machine Operation",
                contribution_type="task",
            )

        assert entry.proficiency_level >= 3  # Should be at least level 3.

    def test_skill_matrix_mismatch_detected(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("ceo", name="New Hire", department="Warehouse")

        svc.record_skill_contribution(
            "ceo",
            employee_id=emp_id,
            skill_name="Inventory Management",
            contribution_type="task",
        )

        matches, details = svc.verify_skill_matrix_accuracy(
            "ceo",
            employee_id=emp_id,
            skill_name="Inventory Management",
            expected_tasks=5,  # Wrong expectation.
            expected_a3=0,
        )

        assert not matches
        assert "Mismatch" in details


class TestExecutiveWarRoom:
    def test_war_room_configuration(self, svc: CEOControlPlaneService) -> None:
        config = svc.configure_war_room(
            "ceo",
            visibility_distance_meters=5.0,
            font_size_px=48,
            contrast_ratio=7.5,
        )

        assert config.visibility_distance_meters == 5.0
        assert config.font_size_px == 48
        assert config.contrast_ratio == 7.5

    def test_sqdcp_metrics_added(self, svc: CEOControlPlaneService) -> None:
        svc.configure_war_room("ceo")

        svc.add_sqdcp_metric("ceo", metric_type=MetricType.SAFETY, name="Incidents", value=0, target=0, unit="count")
        svc.add_sqdcp_metric("ceo", metric_type=MetricType.QUALITY, name="Defect Rate", value=0.02, target=0.05, unit="%")
        svc.add_sqdcp_metric("ceo", metric_type=MetricType.DELIVERY, name="OTD", value=0.95, target=0.95, unit="%")
        svc.add_sqdcp_metric("ceo", metric_type=MetricType.COST, name="Cost Efficiency", value=1.02, target=1.0, unit="ratio")
        svc.add_sqdcp_metric("ceo", metric_type=MetricType.PRODUCTIVITY, name="Output", value=105, target=100, unit="units/hr")

        metrics = svc.get_metrics()
        assert len(metrics) == 5

        # Check all SQDCP categories covered.
        categories = {m.metric_type for m in metrics}
        assert categories == set(MetricType)

    def test_visibility_from_5_meters(self, svc: CEOControlPlaneService) -> None:
        svc.configure_war_room(
            "ceo",
            visibility_distance_meters=5.0,
            font_size_px=48,
            contrast_ratio=8.0,
        )

        # Add all SQDCP metrics.
        for mt in MetricType:
            svc.add_sqdcp_metric("ceo", metric_type=mt, name=f"{mt.value} Metric", value=1.0, target=1.0)

        visible, issues = svc.verify_war_room_visibility(
            "ceo",
            screen_resolution=(3840, 2160),
            viewing_distance_meters=5.0,
        )

        assert visible, f"Visibility issues: {issues}"
        assert len(issues) == 0

    def test_font_too_small_detected(self, svc: CEOControlPlaneService) -> None:
        svc.configure_war_room(
            "ceo",
            font_size_px=24,  # Too small for 5m.
            contrast_ratio=7.0,
        )

        for mt in MetricType:
            svc.add_sqdcp_metric("ceo", metric_type=mt, name=f"{mt.value}", value=1.0, target=1.0)

        visible, issues = svc.verify_war_room_visibility(
            "ceo",
            viewing_distance_meters=5.0,
        )

        assert not visible
        assert any("font size" in i.lower() for i in issues)

    def test_missing_category_detected(self, svc: CEOControlPlaneService) -> None:
        svc.configure_war_room("ceo", font_size_px=48, contrast_ratio=8.0)

        # Only add some metrics.
        svc.add_sqdcp_metric("ceo", metric_type=MetricType.SAFETY, name="Safety", value=0, target=0)
        svc.add_sqdcp_metric("ceo", metric_type=MetricType.QUALITY, name="Quality", value=0.9, target=0.95)

        visible, issues = svc.verify_war_room_visibility("ceo", viewing_distance_meters=5.0)

        assert not visible
        assert any("missing" in i.lower() for i in issues)


class TestRBACEnforcement:
    def test_viewer_cannot_access(self, svc: CEOControlPlaneService) -> None:
        with pytest.raises(PermissionError):
            svc.generate_sql_from_nl("viewer", natural_language="test query")

    def test_operator_cannot_access(self, svc: CEOControlPlaneService) -> None:
        with pytest.raises(PermissionError):
            svc.configure_war_room("operator")

    def test_gm_cannot_access(self, svc: CEOControlPlaneService) -> None:
        with pytest.raises(PermissionError):
            svc.assess_retention_risk("gm", employee_id=uuid4())

    def test_ceo_can_access(self, svc: CEOControlPlaneService) -> None:
        query = svc.generate_sql_from_nl("ceo", natural_language="test")
        assert query is not None

    def test_exec_can_access(self, svc: CEOControlPlaneService) -> None:
        config = svc.configure_war_room("exec")
        assert config is not None

    def test_admin_can_access(self, svc: CEOControlPlaneService) -> None:
        emp_id = svc.register_employee("admin", name="Test", department="Test")
        assert emp_id is not None
