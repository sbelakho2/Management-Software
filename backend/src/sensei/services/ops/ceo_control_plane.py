"""E2E CEO Strategic Control Plane Service (Development Plan 20.5).

This service validates CEO-level strategic capabilities:
- Sensei Query (NL2SQL) with stress testing
- Employee Intelligence (Retention Risk, Burnout Watch, Skill Matrix)
- Executive War Room (SQDCP visibility)
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


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(str, Enum):
    SAFETY = "safety"
    QUALITY = "quality"
    DELIVERY = "delivery"
    COST = "cost"
    PRODUCTIVITY = "productivity"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _severity_from_deviation(abs_deviation_pct: float) -> RiskLevel:
    if abs_deviation_pct >= 0.35:
        return RiskLevel.CRITICAL
    if abs_deviation_pct >= 0.20:
        return RiskLevel.HIGH
    if abs_deviation_pct >= 0.10:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


@dataclass
class NL2SQLQuery:
    """Natural language to SQL query result."""
    id: UUID = field(default_factory=uuid4)
    natural_language: str = ""
    generated_sql: str = ""
    plain_english_explanation: str = ""
    execution_result: list[dict] | None = None
    is_correct: bool = False
    validation_notes: str = ""


@dataclass
class EmployeeRiskAssessment:
    """Employee retention and burnout risk assessment."""
    employee_id: UUID = field(default_factory=uuid4)
    employee_name: str = ""
    retention_risk: RiskLevel = RiskLevel.LOW
    retention_score: float = 0.0
    burnout_risk: RiskLevel = RiskLevel.LOW
    burnout_score: float = 0.0
    risk_factors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class SkillMatrixEntry:
    """Skill matrix entry for an employee."""
    employee_id: UUID = field(default_factory=uuid4)
    skill_name: str = ""
    proficiency_level: int = 1  # 1-5 scale.
    verified_by_tasks: int = 0
    verified_by_a3: int = 0
    last_demonstrated: datetime | None = None


@dataclass
class SQDCPMetric:
    """SQDCP metric for War Room display."""
    id: UUID = field(default_factory=uuid4)
    metric_type: MetricType = MetricType.SAFETY
    name: str = ""
    value: float = 0.0
    target: float = 0.0
    unit: str = ""
    status: str = "green"  # green, yellow, red.
    trend: str = "stable"  # up, down, stable.
    period: str = "daily"


@dataclass
class WarRoomDisplay:
    """War Room 4K display configuration."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    metrics: list[SQDCPMetric] = field(default_factory=list)
    visibility_distance_meters: float = 5.0
    font_size_px: int = 48
    contrast_ratio: float = 7.0  # WCAG AAA requires 7:1.


@dataclass
class VarianceAlert:
    """Variance alert for cost/COGS deviations vs estimates."""

    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_utcnow)

    quote_id: str = ""
    work_order_ids: list[str] = field(default_factory=list)
    correlation_id: str | None = None

    actual_cogs: float = 0.0
    estimated_cogs: float = 0.0
    deviation_pct: float = 0.0
    threshold_pct: float = 0.10
    severity: RiskLevel = RiskLevel.LOW


class CEOControlPlaneService:
    """E2E validation service for CEO strategic capabilities."""

    ALLOWED_ROLES = {"ceo", "exec", "superuser", "admin"}

    # SQL patterns for common queries.
    SQL_PATTERNS = {
        "margin_leakage": r"SELECT.*margin.*supplier.*GROUP BY",
        "revenue_by_product": r"SELECT.*revenue.*product.*GROUP BY",
        "customer_concentration": r"SELECT.*customer.*SUM.*ORDER BY",
        "quote_conversion": r"SELECT.*quote.*won.*rate",
        "production_efficiency": r"SELECT.*efficiency.*cell.*",
    }

    def __init__(self) -> None:
        self._queries: list[NL2SQLQuery] = []
        self._employees: dict[UUID, dict] = {}
        self._risk_assessments: dict[UUID, EmployeeRiskAssessment] = {}
        self._skill_matrix: dict[UUID, list[SkillMatrixEntry]] = {}
        self._metrics: list[SQDCPMetric] = []
        self._war_room: WarRoomDisplay | None = None
        self._variance_alerts: list[VarianceAlert] = []

    # ---- Variance Alerts (Cost/COGS) ----

    def record_variance_alert(
        self,
        role: str,
        *,
        quote_id: str,
        actual_cogs: float,
        estimated_cogs: float,
        threshold_pct: float,
        work_order_ids: list[str] | None = None,
        correlation_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> "VarianceAlert":
        """Record a cost variance alert for CEO/Exec visibility.

        This is a lightweight ingestion point used by reconciliation/feedback-loop services.
        """
        self._check_role(role)

        qid = (quote_id or "").strip()
        if not qid:
            raise ValueError("quote_id is required")
        if estimated_cogs <= 0:
            raise ValueError("estimated_cogs must be > 0")
        if threshold_pct <= 0:
            raise ValueError("threshold_pct must be > 0")

        deviation_pct = (actual_cogs - estimated_cogs) / estimated_cogs
        severity = _severity_from_deviation(abs(deviation_pct))

        alert = VarianceAlert(
            quote_id=qid,
            actual_cogs=float(actual_cogs),
            estimated_cogs=float(estimated_cogs),
            deviation_pct=float(deviation_pct),
            threshold_pct=float(threshold_pct),
            severity=severity,
            occurred_at=occurred_at or _utcnow(),
            work_order_ids=[w for w in (work_order_ids or []) if w and w.strip()],
            correlation_id=(correlation_id or "").strip() or None,
        )
        self._variance_alerts.append(alert)

        # Also surface as a COST metric in the War Room display.
        self._metrics.append(
            SQDCPMetric(
                metric_type=MetricType.COST,
                name=f"COGS variance alert (Quote {qid})",
                value=round(deviation_pct * 100.0, 2),
                target=round(threshold_pct * 100.0, 2),
                unit="%",
                status="red" if abs(deviation_pct) >= threshold_pct else "yellow",
                trend="up" if deviation_pct > 0 else "down",
                period="event",
            )
        )
        return alert

    def list_variance_alerts(self, role: str) -> list["VarianceAlert"]:
        self._check_role(role)
        return list(self._variance_alerts)

    def _check_role(self, role: str) -> None:
        if role.lower() not in self.ALLOWED_ROLES:
            raise PermissionError(f"Role '{role}' cannot access CEO control plane")

    # ---- Sensei Query (NL2SQL) ----

    def generate_sql_from_nl(
        self,
        role: str,
        *,
        natural_language: str,
    ) -> NL2SQLQuery:
        """Generate SQL from natural language query.

        Args:
            role: User role performing query.
            natural_language: Natural language query.

        Returns:
            NL2SQL query result with generated SQL.
        """
        self._check_role(role)

        nl_lower = natural_language.lower()

        # Generate SQL based on query patterns.
        if "margin" in nl_lower and "supplier" in nl_lower:
            sql = """
SELECT 
    s.supplier_name,
    SUM(li.unit_price - li.unit_cost) as margin_amount,
    AVG((li.unit_price - li.unit_cost) / li.unit_price * 100) as margin_pct
FROM line_items li
JOIN suppliers s ON li.supplier_id = s.id
WHERE li.created_at >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')
GROUP BY s.supplier_name
ORDER BY margin_amount DESC;
""".strip()
            explanation = "This query calculates margin leakage by summing the difference between selling price and cost for each supplier in Q3, showing which suppliers have the highest margin erosion."

        elif "revenue" in nl_lower and "product" in nl_lower:
            sql = """
SELECT 
    p.product_name,
    SUM(o.total_amount) as revenue,
    COUNT(DISTINCT o.id) as order_count
FROM orders o
JOIN products p ON o.product_id = p.id
GROUP BY p.product_name
ORDER BY revenue DESC;
""".strip()
            explanation = "This query aggregates total revenue and order count by product, sorted by highest revenue."

        elif "quote" in nl_lower and ("conversion" in nl_lower or "won" in nl_lower):
            sql = """
SELECT 
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as total_quotes,
    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) as won_quotes,
    ROUND(SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2) as win_rate
FROM quotes
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;
""".strip()
            explanation = "This query calculates monthly quote conversion rates by counting won quotes versus total quotes."

        else:
            # Generic query.
            sql = f"SELECT * FROM data WHERE description LIKE '%{natural_language[:20]}%' LIMIT 100;"
            explanation = "Generic query matching the natural language description."

        query = NL2SQLQuery(
            natural_language=natural_language,
            generated_sql=sql,
            plain_english_explanation=explanation,
        )

        self._queries.append(query)
        return query

    def validate_sql_accuracy(
        self,
        role: str,
        *,
        query: NL2SQLQuery,
        expected_patterns: list[str] | None = None,
    ) -> tuple[bool, str]:
        """Validate generated SQL accuracy.

        Args:
            role: User role performing validation.
            query: Query to validate.
            expected_patterns: Optional regex patterns to match.

        Returns:
            Tuple of (is_valid, notes).
        """
        self._check_role(role)

        sql = query.generated_sql.upper()

        # Basic SQL syntax validation.
        if not sql.strip().startswith("SELECT"):
            query.is_correct = False
            query.validation_notes = "SQL must start with SELECT"
            return False, query.validation_notes

        # Check for essential clauses.
        has_from = "FROM" in sql
        has_valid_structure = has_from

        if not has_valid_structure:
            query.is_correct = False
            query.validation_notes = "Missing required SQL clauses"
            return False, query.validation_notes

        # Check against expected patterns.
        if expected_patterns:
            sql_lower = query.generated_sql.lower()
            all_match = all(re.search(p, sql_lower, re.IGNORECASE) for p in expected_patterns)
            if not all_match:
                query.is_correct = False
                query.validation_notes = "SQL doesn't match expected patterns"
                return False, query.validation_notes

        query.is_correct = True
        query.validation_notes = "SQL validated successfully"
        return True, query.validation_notes

    def verify_explanation_matches_sql(
        self,
        role: str,
        *,
        query: NL2SQLQuery,
    ) -> tuple[bool, str]:
        """Verify plain English explanation matches SQL logic.

        Args:
            role: User role performing verification.
            query: Query to verify.

        Returns:
            Tuple of (matches, notes).
        """
        self._check_role(role)

        sql_lower = query.generated_sql.lower()
        explanation_lower = query.plain_english_explanation.lower()

        # Check key concepts match.
        checks = []

        if "group by" in sql_lower:
            checks.append("aggregat" in explanation_lower or "group" in explanation_lower or "by" in explanation_lower)

        if "sum(" in sql_lower:
            checks.append("sum" in explanation_lower or "total" in explanation_lower or "aggregat" in explanation_lower)

        if "order by" in sql_lower:
            checks.append("sort" in explanation_lower or "order" in explanation_lower or "highest" in explanation_lower)

        if "where" in sql_lower:
            checks.append("filter" in explanation_lower or "where" in explanation_lower or "match" in explanation_lower or "q3" in explanation_lower)

        if not checks:
            return True, "No specific clauses to verify"

        match_rate = sum(checks) / len(checks)
        matches = match_rate >= 0.5

        return matches, f"Match rate: {match_rate:.0%}"

    # ---- Employee Intelligence ----

    def register_employee(
        self,
        role: str,
        *,
        name: str,
        department: str,
    ) -> UUID:
        """Register an employee for intelligence tracking.

        Args:
            role: User role performing action.
            name: Employee name.
            department: Department name.

        Returns:
            Employee ID.
        """
        self._check_role(role)

        emp_id = uuid4()
        self._employees[emp_id] = {
            "name": name,
            "department": department,
            "tenure_months": 12,
            "overtime_hours": 0,
            "task_completion_rate": 0.85,
            "a3_contributions": 0,
        }

        return emp_id

    def assess_retention_risk(
        self,
        role: str,
        *,
        employee_id: UUID,
        tenure_months: int = 12,
        overtime_hours_weekly: float = 0,
        skip_rate: float = 0,
        peer_comparison: float = 1.0,
    ) -> EmployeeRiskAssessment:
        """Assess employee retention and burnout risk.

        Args:
            role: User role performing assessment.
            employee_id: Employee to assess.
            tenure_months: Employee tenure in months.
            overtime_hours_weekly: Weekly overtime hours.
            skip_rate: Rate of skipped meetings/tasks.
            peer_comparison: Performance vs peers (1.0 = average).

        Returns:
            Risk assessment.
        """
        self._check_role(role)

        emp = self._employees.get(employee_id)
        if not emp:
            raise KeyError("Employee not found")

        risk_factors = []
        recommendations = []

        # Calculate retention risk.
        retention_score = 0.0

        if tenure_months < 6:
            retention_score += 0.3
            risk_factors.append("New employee (< 6 months)")

        if tenure_months > 24 and peer_comparison < 0.8:
            retention_score += 0.4
            risk_factors.append("Experienced but underperforming")
            recommendations.append("Schedule career development discussion")

        if skip_rate > 0.2:
            retention_score += 0.3
            risk_factors.append("High meeting/task skip rate")
            recommendations.append("Check for engagement issues")

        retention_risk = (
            RiskLevel.CRITICAL if retention_score >= 0.7 else
            RiskLevel.HIGH if retention_score >= 0.5 else
            RiskLevel.MEDIUM if retention_score >= 0.3 else
            RiskLevel.LOW
        )

        # Calculate burnout risk.
        burnout_score = 0.0

        if overtime_hours_weekly > 15:
            burnout_score += 0.5
            risk_factors.append("Excessive overtime (> 15h/week)")
            recommendations.append("Redistribute workload")
        elif overtime_hours_weekly > 10:
            burnout_score += 0.3
            risk_factors.append("High overtime (> 10h/week)")

        if peer_comparison > 1.3:
            burnout_score += 0.3
            risk_factors.append("Outperforming peers significantly (may be overworked)")

        burnout_risk = (
            RiskLevel.CRITICAL if burnout_score >= 0.7 else
            RiskLevel.HIGH if burnout_score >= 0.5 else
            RiskLevel.MEDIUM if burnout_score >= 0.3 else
            RiskLevel.LOW
        )

        assessment = EmployeeRiskAssessment(
            employee_id=employee_id,
            employee_name=emp["name"],
            retention_risk=retention_risk,
            retention_score=retention_score,
            burnout_risk=burnout_risk,
            burnout_score=burnout_score,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )

        self._risk_assessments[employee_id] = assessment
        return assessment

    def record_skill_contribution(
        self,
        role: str,
        *,
        employee_id: UUID,
        skill_name: str,
        contribution_type: str,  # "task" or "a3".
    ) -> SkillMatrixEntry:
        """Record a skill contribution from task or A3.

        Args:
            role: User role performing action.
            employee_id: Employee ID.
            skill_name: Skill demonstrated.
            contribution_type: Type of contribution.

        Returns:
            Updated skill matrix entry.
        """
        self._check_role(role)

        if employee_id not in self._skill_matrix:
            self._skill_matrix[employee_id] = []

        # Find or create entry.
        entry = None
        for e in self._skill_matrix[employee_id]:
            if e.skill_name == skill_name:
                entry = e
                break

        if not entry:
            entry = SkillMatrixEntry(
                employee_id=employee_id,
                skill_name=skill_name,
            )
            self._skill_matrix[employee_id].append(entry)

        # Update based on contribution.
        if contribution_type == "task":
            entry.verified_by_tasks += 1
        elif contribution_type == "a3":
            entry.verified_by_a3 += 1

        entry.last_demonstrated = _utcnow()

        # Calculate proficiency level based on contributions.
        total = entry.verified_by_tasks + (entry.verified_by_a3 * 2)  # A3 worth more.
        entry.proficiency_level = min(5, 1 + total // 5)

        return entry

    def verify_skill_matrix_accuracy(
        self,
        role: str,
        *,
        employee_id: UUID,
        skill_name: str,
        expected_tasks: int,
        expected_a3: int,
    ) -> tuple[bool, str]:
        """Verify skill matrix matches actual contributions.

        Args:
            role: User role performing verification.
            employee_id: Employee to verify.
            skill_name: Skill to verify.
            expected_tasks: Expected task contributions.
            expected_a3: Expected A3 contributions.

        Returns:
            Tuple of (matches, details).
        """
        self._check_role(role)

        entries = self._skill_matrix.get(employee_id, [])
        entry = next((e for e in entries if e.skill_name == skill_name), None)

        if not entry:
            return False, f"No skill entry found for '{skill_name}'"

        tasks_match = entry.verified_by_tasks == expected_tasks
        a3_match = entry.verified_by_a3 == expected_a3

        if tasks_match and a3_match:
            return True, f"Skill matrix accurate: {expected_tasks} tasks, {expected_a3} A3s"

        return False, f"Mismatch: expected {expected_tasks} tasks/{expected_a3} A3s, got {entry.verified_by_tasks} tasks/{entry.verified_by_a3} A3s"

    # ---- Executive War Room ----

    def configure_war_room(
        self,
        role: str,
        *,
        visibility_distance_meters: float = 5.0,
        font_size_px: int = 48,
        contrast_ratio: float = 7.0,
    ) -> WarRoomDisplay:
        """Configure War Room 4K display.

        Args:
            role: User role performing configuration.
            visibility_distance_meters: Required visibility distance.
            font_size_px: Font size for metrics.
            contrast_ratio: Contrast ratio for accessibility.

        Returns:
            War Room configuration.
        """
        self._check_role(role)

        self._war_room = WarRoomDisplay(
            visibility_distance_meters=visibility_distance_meters,
            font_size_px=font_size_px,
            contrast_ratio=contrast_ratio,
        )

        return self._war_room

    def add_sqdcp_metric(
        self,
        role: str,
        *,
        metric_type: MetricType,
        name: str,
        value: float,
        target: float,
        unit: str = "",
    ) -> SQDCPMetric:
        """Add an SQDCP metric to War Room.

        Args:
            role: User role performing action.
            metric_type: Type of metric (S/Q/D/C/P).
            name: Metric name.
            value: Current value.
            target: Target value.
            unit: Unit of measurement.

        Returns:
            Created metric.
        """
        self._check_role(role)

        # Determine status based on value vs target.
        ratio = value / target if target > 0 else 1.0

        if metric_type in (MetricType.SAFETY, MetricType.QUALITY):
            # Lower is better for incidents.
            status = "green" if ratio <= 1.0 else "yellow" if ratio <= 1.2 else "red"
        else:
            # Higher is better for delivery, cost efficiency, productivity.
            status = "green" if ratio >= 1.0 else "yellow" if ratio >= 0.9 else "red"

        metric = SQDCPMetric(
            metric_type=metric_type,
            name=name,
            value=value,
            target=target,
            unit=unit,
            status=status,
        )

        self._metrics.append(metric)

        if self._war_room:
            self._war_room.metrics.append(metric)

        return metric

    def verify_war_room_visibility(
        self,
        role: str,
        *,
        screen_resolution: tuple[int, int] = (3840, 2160),  # 4K.
        viewing_distance_meters: float = 5.0,
    ) -> tuple[bool, list[str]]:
        """Verify all SQDCP metrics visible from specified distance.

        Args:
            role: User role performing verification.
            screen_resolution: Screen resolution (width, height).
            viewing_distance_meters: Viewing distance in meters.

        Returns:
            Tuple of (all_visible, issues).
        """
        self._check_role(role)

        if not self._war_room:
            return False, ["War Room not configured"]

        issues = []

        # Calculate minimum font size for visibility at distance.
        # Rule of thumb: 1 point per 0.3 meters viewing distance.
        min_font_size = int(viewing_distance_meters / 0.3) * 2

        if self._war_room.font_size_px < min_font_size:
            issues.append(f"Font size {self._war_room.font_size_px}px too small for {viewing_distance_meters}m (need >= {min_font_size}px)")

        # Check contrast ratio.
        if self._war_room.contrast_ratio < 7.0:
            issues.append(f"Contrast ratio {self._war_room.contrast_ratio} below WCAG AAA (7.0)")

        # Check metric count fits on screen.
        metrics_count = len(self._metrics)
        max_metrics = (screen_resolution[1] // (self._war_room.font_size_px * 2)) * 3  # 3 columns.

        if metrics_count > max_metrics:
            issues.append(f"Too many metrics ({metrics_count}) for display (max {max_metrics})")

        # Check all SQDCP categories are represented.
        categories = {m.metric_type for m in self._metrics}
        missing = set(MetricType) - categories
        if missing:
            issues.append(f"Missing SQDCP categories: {[m.value for m in missing]}")

        return len(issues) == 0, issues

    # ---- Getters ----

    def get_queries(self) -> list[NL2SQLQuery]:
        return list(self._queries)

    def get_risk_assessments(self) -> dict[UUID, EmployeeRiskAssessment]:
        return dict(self._risk_assessments)

    def get_metrics(self) -> list[SQDCPMetric]:
        return list(self._metrics)
