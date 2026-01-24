"""
Sensei Nudges Service.

Provides real-time, context-aware tips and suggestions inside forms.
Analyzes current form data to detect potential issues and recommend actions.

Features:
- Context-aware tip generation
- Form field analysis
- Margin and cost alerts
- Best practice recommendations
- Historical pattern detection
- Dynamic tip prioritization
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class NudgeCategory(str, Enum):
    """Categories for nudge tips."""

    COST = "cost"
    MARGIN = "margin"
    RISK = "risk"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    EFFICIENCY = "efficiency"
    BEST_PRACTICE = "best_practice"
    WARNING = "warning"
    INFO = "info"


class NudgeSeverity(str, Enum):
    """Severity levels for nudges."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NudgeTrigger(str, Enum):
    """What triggered the nudge."""

    FIELD_VALUE = "field_value"
    FIELD_MISSING = "field_missing"
    THRESHOLD_BREACH = "threshold_breach"
    PATTERN_DETECTED = "pattern_detected"
    HISTORICAL_ISSUE = "historical_issue"
    BEST_PRACTICE = "best_practice"
    DEPENDENCY_CHECK = "dependency_check"
    TIME_BASED = "time_based"


class FormContext(str, Enum):
    """Form contexts where nudges can appear."""

    QUOTE = "quote"
    RFQ = "rfq"
    QUALIFICATION = "qualification"
    CTQ = "ctq"
    A3 = "a3"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    WORK_ORDER = "work_order"
    ANDON = "andon"
    CAPA = "capa"


@dataclass
class NudgeRule:
    """A rule that generates nudges based on conditions."""

    id: UUID
    name: str
    description: str
    form_context: FormContext
    category: NudgeCategory
    severity: NudgeSeverity
    trigger: NudgeTrigger
    conditions: dict[str, Any]
    message_template: str
    action_text: str | None = None
    action_url: str | None = None
    is_active: bool = True
    priority: int = 50
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Nudge:
    """A generated nudge/tip for the user."""

    id: UUID
    rule_id: UUID
    form_context: FormContext
    category: NudgeCategory
    severity: NudgeSeverity
    trigger: NudgeTrigger
    title: str
    message: str
    field_name: str | None = None
    current_value: Any = None
    suggested_value: Any = None
    action_text: str | None = None
    action_url: str | None = None
    priority: int = 50
    is_dismissible: bool = True
    dismissed: bool = False
    dismissed_at: datetime | None = None
    dismissed_by: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NudgeFeedback:
    """User feedback on a nudge."""

    id: UUID
    nudge_id: UUID
    user_id: UUID
    feedback_type: str  # helpful, not_helpful, incorrect, followed, ignored
    comment: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NudgeStats:
    """Statistics about nudge effectiveness."""

    total_generated: int = 0
    total_dismissed: int = 0
    total_followed: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    follow_rate: float = 0.0


class SenseiNudgesService:
    """
    Service for generating context-aware tips and nudges.

    Analyzes form data in real-time to provide helpful suggestions,
    warnings, and best practice recommendations.
    """

    def __init__(self) -> None:
        """Initialize the Sensei Nudges service."""
        self._rules: dict[UUID, NudgeRule] = {}
        self._nudges: dict[UUID, Nudge] = {}
        self._feedback: dict[UUID, list[NudgeFeedback]] = {}
        self._user_dismissals: dict[UUID, set[UUID]] = {}  # user_id -> set of rule_ids
        self._historical_patterns: dict[str, list[dict[str, Any]]] = {}

        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Set up default nudge rules."""
        default_rules = [
            # Quote margin rules
            NudgeRule(
                id=uuid4(),
                name="low_margin_warning",
                description="Warn when margin is below threshold",
                form_context=FormContext.QUOTE,
                category=NudgeCategory.MARGIN,
                severity=NudgeSeverity.HIGH,
                trigger=NudgeTrigger.THRESHOLD_BREACH,
                conditions={"field": "margin_percentage", "operator": "lt", "value": 15},
                message_template="Margin of {value}% is below the 15% threshold. Have you checked material costs and scrap rates?",
                action_text="Review costing breakdown",
                priority=90,
            ),
            NudgeRule(
                id=uuid4(),
                name="very_low_margin_alert",
                description="Critical alert when margin is dangerously low",
                form_context=FormContext.QUOTE,
                category=NudgeCategory.MARGIN,
                severity=NudgeSeverity.CRITICAL,
                trigger=NudgeTrigger.THRESHOLD_BREACH,
                conditions={"field": "margin_percentage", "operator": "lt", "value": 5},
                message_template="Critical: Margin of {value}% requires GM approval. Consider renegotiating terms.",
                action_text="Request GM approval",
                priority=100,
            ),
            NudgeRule(
                id=uuid4(),
                name="high_scrap_rate",
                description="Warn about high scrap rate assumptions",
                form_context=FormContext.QUOTE,
                category=NudgeCategory.COST,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.THRESHOLD_BREACH,
                conditions={"field": "scrap_rate", "operator": "gt", "value": 10},
                message_template="Scrap rate of {value}% is high. Consider process improvements or adjust pricing.",
                action_text="Review process capability",
                priority=70,
            ),
            # RFQ completeness rules
            NudgeRule(
                id=uuid4(),
                name="missing_volume_estimate",
                description="Warn about missing volume information",
                form_context=FormContext.RFQ,
                category=NudgeCategory.INFO,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.FIELD_MISSING,
                conditions={"field": "estimated_annual_volume", "operator": "missing"},
                message_template="Volume estimate is missing. This affects pricing accuracy and capacity planning.",
                action_text="Request from customer",
                priority=75,
            ),
            NudgeRule(
                id=uuid4(),
                name="missing_target_price",
                description="Suggest requesting target price",
                form_context=FormContext.RFQ,
                category=NudgeCategory.BEST_PRACTICE,
                severity=NudgeSeverity.LOW,
                trigger=NudgeTrigger.FIELD_MISSING,
                conditions={"field": "target_price", "operator": "missing"},
                message_template="Consider requesting customer's target price to align expectations early.",
                action_text="Add to info request",
                priority=50,
            ),
            # Qualification rules
            NudgeRule(
                id=uuid4(),
                name="capability_gap_detected",
                description="Warn about capability gaps",
                form_context=FormContext.QUALIFICATION,
                category=NudgeCategory.RISK,
                severity=NudgeSeverity.HIGH,
                trigger=NudgeTrigger.THRESHOLD_BREACH,
                conditions={"field": "capability_score", "operator": "lt", "value": 60},
                message_template="Capability score of {value}% indicates gaps. Consider conditions or subcontracting.",
                action_text="Add conditions",
                priority=85,
            ),
            NudgeRule(
                id=uuid4(),
                name="strategic_fit_low",
                description="Flag low strategic fit",
                form_context=FormContext.QUALIFICATION,
                category=NudgeCategory.INFO,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.THRESHOLD_BREACH,
                conditions={"field": "strategic_score", "operator": "lt", "value": 50},
                message_template="Strategic fit is low. Document rationale if proceeding with quote.",
                action_text="Add rationale",
                priority=60,
            ),
            # Risk register rules
            NudgeRule(
                id=uuid4(),
                name="high_risk_no_mitigation",
                description="Warn about unmitigated high risks",
                form_context=FormContext.RISK,
                category=NudgeCategory.RISK,
                severity=NudgeSeverity.HIGH,
                trigger=NudgeTrigger.DEPENDENCY_CHECK,
                conditions={"field": "severity", "operator": "gte", "value": 4, "mitigation_required": True},
                message_template="High severity risk (level {value}) requires mitigation plan.",
                action_text="Add mitigation",
                priority=88,
            ),
            # CTQ rules
            NudgeRule(
                id=uuid4(),
                name="ctq_missing_measurement",
                description="Warn about CTQs without measurement method",
                form_context=FormContext.CTQ,
                category=NudgeCategory.QUALITY,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.FIELD_MISSING,
                conditions={"field": "measurement_method", "operator": "missing"},
                message_template="Measurement method not defined. How will this CTQ be verified?",
                action_text="Define method",
                priority=72,
            ),
            NudgeRule(
                id=uuid4(),
                name="ctq_missing_criteria",
                description="Warn about CTQs without acceptance criteria",
                form_context=FormContext.CTQ,
                category=NudgeCategory.QUALITY,
                severity=NudgeSeverity.HIGH,
                trigger=NudgeTrigger.FIELD_MISSING,
                conditions={"field": "acceptance_criteria", "operator": "missing"},
                message_template="Acceptance criteria not defined. This CTQ cannot be properly verified.",
                action_text="Define criteria",
                priority=82,
            ),
            # A3 problem solving rules
            NudgeRule(
                id=uuid4(),
                name="a3_missing_root_cause",
                description="Warn about jumping to solutions",
                form_context=FormContext.A3,
                category=NudgeCategory.BEST_PRACTICE,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.DEPENDENCY_CHECK,
                conditions={"has_countermeasures": True, "has_root_cause": False},
                message_template="Countermeasures defined without root cause analysis. Apply 5-Why first.",
                action_text="Add root cause",
                priority=78,
            ),
            NudgeRule(
                id=uuid4(),
                name="a3_generic_problem",
                description="Suggest specificity in problem statement",
                form_context=FormContext.A3,
                category=NudgeCategory.BEST_PRACTICE,
                severity=NudgeSeverity.LOW,
                trigger=NudgeTrigger.PATTERN_DETECTED,
                conditions={"field": "problem_statement", "pattern": "generic"},
                message_template="Problem statement could be more specific. Include what, where, when, and magnitude.",
                action_text="Refine problem",
                priority=55,
            ),
            # Work order rules
            NudgeRule(
                id=uuid4(),
                name="wo_past_due",
                description="Alert about past due work orders",
                form_context=FormContext.WORK_ORDER,
                category=NudgeCategory.WARNING,
                severity=NudgeSeverity.HIGH,
                trigger=NudgeTrigger.TIME_BASED,
                conditions={"field": "scheduled_end", "operator": "past"},
                message_template="Work order is past scheduled end date. Update status or reschedule.",
                action_text="Update schedule",
                priority=85,
            ),
            # CAPA rules
            NudgeRule(
                id=uuid4(),
                name="capa_approaching_due",
                description="Warn about approaching CAPA due dates",
                form_context=FormContext.CAPA,
                category=NudgeCategory.COMPLIANCE,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.TIME_BASED,
                conditions={"field": "due_date", "operator": "within_days", "value": 7},
                message_template="CAPA due date is within 7 days. Ensure all actions are on track.",
                action_text="Review actions",
                priority=75,
            ),
            NudgeRule(
                id=uuid4(),
                name="capa_missing_verification",
                description="Warn about missing verification plan",
                form_context=FormContext.CAPA,
                category=NudgeCategory.COMPLIANCE,
                severity=NudgeSeverity.HIGH,
                trigger=NudgeTrigger.FIELD_MISSING,
                conditions={"field": "verification_method", "operator": "missing"},
                message_template="Verification method not defined. How will CAPA effectiveness be measured?",
                action_text="Add verification",
                priority=80,
            ),
            # Opportunity rules
            NudgeRule(
                id=uuid4(),
                name="opportunity_stale",
                description="Flag stale opportunities",
                form_context=FormContext.OPPORTUNITY,
                category=NudgeCategory.EFFICIENCY,
                severity=NudgeSeverity.MEDIUM,
                trigger=NudgeTrigger.TIME_BASED,
                conditions={"field": "last_activity_date", "operator": "older_than_days", "value": 14},
                message_template="No activity in {value} days. Update next steps or mark as lost.",
                action_text="Update status",
                priority=65,
            ),
        ]

        for rule in default_rules:
            self._rules[rule.id] = rule

    def create_rule(
        self,
        name: str,
        description: str,
        form_context: FormContext,
        category: NudgeCategory,
        severity: NudgeSeverity,
        trigger: NudgeTrigger,
        conditions: dict[str, Any],
        message_template: str,
        action_text: str | None = None,
        action_url: str | None = None,
        priority: int = 50,
    ) -> NudgeRule:
        """Create a new nudge rule."""
        rule = NudgeRule(
            id=uuid4(),
            name=name,
            description=description,
            form_context=form_context,
            category=category,
            severity=severity,
            trigger=trigger,
            conditions=conditions,
            message_template=message_template,
            action_text=action_text,
            action_url=action_url,
            priority=priority,
        )
        self._rules[rule.id] = rule
        return rule

    def get_rule(self, rule_id: UUID) -> NudgeRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def get_rules(
        self,
        form_context: FormContext | None = None,
        category: NudgeCategory | None = None,
        active_only: bool = True,
    ) -> list[NudgeRule]:
        """Get rules matching filters."""
        rules = list(self._rules.values())

        if form_context:
            rules = [r for r in rules if r.form_context == form_context]

        if category:
            rules = [r for r in rules if r.category == category]

        if active_only:
            rules = [r for r in rules if r.is_active]

        return sorted(rules, key=lambda r: -r.priority)

    def update_rule(
        self,
        rule_id: UUID,
        **updates: Any,
    ) -> NudgeRule | None:
        """Update an existing rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        return rule

    def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def deactivate_rule(self, rule_id: UUID) -> NudgeRule | None:
        """Deactivate a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.is_active = False
        return rule

    def activate_rule(self, rule_id: UUID) -> NudgeRule | None:
        """Activate a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.is_active = True
        return rule

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        form_data: dict[str, Any],
    ) -> tuple[bool, Any]:
        """
        Evaluate a single condition against form data.

        Returns (matches, value).
        """
        field = condition.get("field")
        operator = condition.get("operator")
        threshold = condition.get("value")

        value = form_data.get(field or "")

        if operator == "missing":
            return value is None or value == "" or value == [], value

        if operator == "present":
            return value is not None and value != "" and value != [], value

        if value is None:
            return False, value

        if operator == "lt":
            return float(value) < float(threshold or 0), value

        if operator == "lte":
            return float(value) <= float(threshold or 0), value

        if operator == "gt":
            return float(value) > float(threshold or 0), value

        if operator == "gte":
            return float(value) >= float(threshold or 0), value

        if operator == "eq":
            return value == threshold, value

        if operator == "ne":
            return value != threshold, value

        if operator == "in":
            return value in threshold if threshold is not None else False, value

        if operator == "contains":
            return threshold in str(value) if threshold is not None else False, value

        if operator == "past":
            if isinstance(value, datetime):
                return value < datetime.now(timezone.utc), value
            return False, value

        if operator == "within_days":
            if isinstance(value, datetime) and threshold is not None:
                days_diff = (value - datetime.now(timezone.utc)).days
                return 0 <= days_diff <= threshold, days_diff
            return False, value

        if operator == "older_than_days":
            if isinstance(value, datetime) and threshold is not None:
                days_diff = (datetime.now(timezone.utc) - value).days
                return days_diff > threshold, days_diff
            return False, value

        if operator == "pattern":
            # Check for common patterns
            text = str(value).lower()
            if threshold == "generic":
                generic_words = ["issue", "problem", "bad", "wrong", "error"]
                return any(w in text for w in generic_words) and len(text) < 50, value

        return False, value

    def _evaluate_dependency_condition(
        self,
        condition: dict[str, Any],
        form_data: dict[str, Any],
    ) -> tuple[bool, Any]:
        """Evaluate dependency conditions (multiple fields)."""
        results = []

        for key, expected in condition.items():
            if key in ("field", "operator", "value"):
                continue

            actual = form_data.get(key)

            if isinstance(expected, bool):
                # For boolean conditions, check if field value is truthy/falsy
                if expected:
                    # Expected True: field should be truthy (not None, empty, or False)
                    matches = bool(actual)
                else:
                    # Expected False: field should be falsy (None, empty, False, or 0)
                    matches = not bool(actual)
                results.append(matches)
            else:
                results.append(actual == expected)

        return all(results), form_data

    def generate_nudges(
        self,
        form_context: FormContext,
        form_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> list[Nudge]:
        """
        Generate nudges for the given form context and data.

        Args:
            form_context: The form type (quote, rfq, etc.)
            form_data: Current form field values
            user_id: Optional user ID to filter out dismissed rules

        Returns:
            List of applicable nudges sorted by priority
        """
        applicable_rules = self.get_rules(form_context=form_context)
        nudges: list[Nudge] = []

        # Get user's dismissed rules
        dismissed_rules = self._user_dismissals.get(user_id, set()) if user_id else set()

        for rule in applicable_rules:
            # Skip if user has dismissed this rule
            if rule.id in dismissed_rules:
                continue

            # Evaluate conditions
            if rule.trigger == NudgeTrigger.DEPENDENCY_CHECK:
                matches, value = self._evaluate_dependency_condition(
                    rule.conditions, form_data
                )
            else:
                matches, value = self._evaluate_condition(rule.conditions, form_data)

            if matches:
                # Format message with value
                message = rule.message_template
                if value is not None:
                    if isinstance(value, float):
                        message = message.format(value=f"{value:.1f}")
                    else:
                        message = message.format(value=value)

                nudge = Nudge(
                    id=uuid4(),
                    rule_id=rule.id,
                    form_context=form_context,
                    category=rule.category,
                    severity=rule.severity,
                    trigger=rule.trigger,
                    title=rule.name.replace("_", " ").title(),
                    message=message,
                    field_name=rule.conditions.get("field"),
                    current_value=value,
                    action_text=rule.action_text,
                    action_url=rule.action_url,
                    priority=rule.priority,
                )
                self._nudges[nudge.id] = nudge
                nudges.append(nudge)

        return sorted(nudges, key=lambda n: -n.priority)

    def dismiss_nudge(
        self,
        nudge_id: UUID,
        user_id: UUID,
        dismiss_rule: bool = False,
    ) -> Nudge | None:
        """
        Dismiss a nudge.

        Args:
            nudge_id: The nudge to dismiss
            user_id: The user dismissing
            dismiss_rule: If True, permanently dismiss the rule for this user
        """
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return None

        nudge.dismissed = True
        nudge.dismissed_at = datetime.now(timezone.utc)
        nudge.dismissed_by = user_id

        if dismiss_rule:
            if user_id not in self._user_dismissals:
                self._user_dismissals[user_id] = set()
            self._user_dismissals[user_id].add(nudge.rule_id)

        return nudge

    def get_nudge(self, nudge_id: UUID) -> Nudge | None:
        """Get a nudge by ID."""
        return self._nudges.get(nudge_id)

    def get_user_nudges(
        self,
        user_id: UUID,
        form_context: FormContext | None = None,
        include_dismissed: bool = False,
    ) -> list[Nudge]:
        """Get nudges for a user."""
        nudges = list(self._nudges.values())

        if form_context:
            nudges = [n for n in nudges if n.form_context == form_context]

        if not include_dismissed:
            nudges = [n for n in nudges if not n.dismissed]

        return sorted(nudges, key=lambda n: -n.priority)

    def add_feedback(
        self,
        nudge_id: UUID,
        user_id: UUID,
        feedback_type: str,
        comment: str | None = None,
    ) -> NudgeFeedback | None:
        """Add feedback for a nudge."""
        nudge = self._nudges.get(nudge_id)
        if not nudge:
            return None

        feedback = NudgeFeedback(
            id=uuid4(),
            nudge_id=nudge_id,
            user_id=user_id,
            feedback_type=feedback_type,
            comment=comment,
        )

        if nudge_id not in self._feedback:
            self._feedback[nudge_id] = []
        self._feedback[nudge_id].append(feedback)

        return feedback

    def get_feedback(self, nudge_id: UUID) -> list[NudgeFeedback]:
        """Get feedback for a nudge."""
        return self._feedback.get(nudge_id, [])

    def record_pattern(
        self,
        pattern_key: str,
        data: dict[str, Any],
    ) -> None:
        """Record a historical pattern for future analysis."""
        if pattern_key not in self._historical_patterns:
            self._historical_patterns[pattern_key] = []

        entry = {
            "timestamp": datetime.now(timezone.utc),
            "data": data,
        }
        self._historical_patterns[pattern_key].append(entry)

        # Keep only last 100 entries per pattern
        if len(self._historical_patterns[pattern_key]) > 100:
            self._historical_patterns[pattern_key] = self._historical_patterns[pattern_key][-100:]

    def get_pattern_insights(self, pattern_key: str) -> dict[str, Any]:
        """Get insights from historical patterns."""
        patterns = self._historical_patterns.get(pattern_key, [])

        if not patterns:
            return {"count": 0, "insights": []}

        return {
            "count": len(patterns),
            "first_seen": patterns[0]["timestamp"],
            "last_seen": patterns[-1]["timestamp"],
            "insights": self._analyze_patterns(patterns),
        }

    def _analyze_patterns(self, patterns: list[dict[str, Any]]) -> list[str]:
        """Analyze patterns to generate insights."""
        insights = []

        if len(patterns) >= 5:
            insights.append(f"This pattern has occurred {len(patterns)} times")

        # Check for recent frequency
        now = datetime.now(timezone.utc)
        recent = [p for p in patterns if (now - p["timestamp"]).days <= 7]
        if len(recent) >= 3:
            insights.append(f"Occurred {len(recent)} times in the last week")

        return insights

    def get_statistics(
        self,
        form_context: FormContext | None = None,
    ) -> NudgeStats:
        """Get nudge statistics."""
        nudges = list(self._nudges.values())

        if form_context:
            nudges = [n for n in nudges if n.form_context == form_context]

        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        dismissed_count = 0
        followed_count = 0
        helpful_count = 0
        not_helpful_count = 0

        for nudge in nudges:
            by_category[nudge.category.value] = by_category.get(nudge.category.value, 0) + 1
            by_severity[nudge.severity.value] = by_severity.get(nudge.severity.value, 0) + 1

            if nudge.dismissed:
                dismissed_count += 1

            # Check feedback
            feedback_list = self._feedback.get(nudge.id, [])
            for feedback in feedback_list:
                if feedback.feedback_type == "followed":
                    followed_count += 1
                elif feedback.feedback_type == "helpful":
                    helpful_count += 1
                elif feedback.feedback_type == "not_helpful":
                    not_helpful_count += 1

        total = len(nudges)
        follow_rate = followed_count / total if total > 0 else 0.0

        return NudgeStats(
            total_generated=total,
            total_dismissed=dismissed_count,
            total_followed=followed_count,
            helpful_count=helpful_count,
            not_helpful_count=not_helpful_count,
            by_category=by_category,
            by_severity=by_severity,
            follow_rate=follow_rate,
        )

    def get_suggested_value(
        self,
        form_context: FormContext,
        field_name: str,
        current_data: dict[str, Any],
    ) -> Any | None:
        """
        Get a suggested value for a field based on patterns and best practices.

        Args:
            form_context: The form type
            field_name: The field to suggest value for
            current_data: Current form data

        Returns:
            Suggested value or None
        """
        # Check historical patterns
        pattern_key = f"{form_context.value}:{field_name}"
        patterns = self._historical_patterns.get(pattern_key, [])

        if patterns:
            # Return most common recent value
            recent_values = [p["data"].get("value") for p in patterns[-10:] if p["data"].get("value")]
            if recent_values:
                from collections import Counter
                most_common = Counter(recent_values).most_common(1)
                if most_common:
                    return most_common[0][0]

        # Default suggestions based on field
        defaults = {
            (FormContext.QUOTE, "margin_percentage"): 20.0,
            (FormContext.QUOTE, "scrap_rate"): 5.0,
            (FormContext.QUOTE, "lead_time_days"): 30,
            (FormContext.RFQ, "validity_days"): 90,
            (FormContext.QUALIFICATION, "capability_score"): 70,
            (FormContext.CTQ, "check_frequency"): "per_lot",
        }

        return defaults.get((form_context, field_name))

    def clear_user_dismissals(self, user_id: UUID) -> int:
        """Clear all dismissals for a user."""
        if user_id in self._user_dismissals:
            count = len(self._user_dismissals[user_id])
            del self._user_dismissals[user_id]
            return count
        return 0

    def get_user_dismissals(self, user_id: UUID) -> list[NudgeRule]:
        """Get rules dismissed by a user."""
        rule_ids = self._user_dismissals.get(user_id, set())
        return [self._rules[rid] for rid in rule_ids if rid in self._rules]

    def bulk_generate_nudges(
        self,
        items: list[tuple[FormContext, dict[str, Any]]],
        user_id: UUID | None = None,
    ) -> dict[str, list[Nudge]]:
        """
        Generate nudges for multiple items.

        Args:
            items: List of (form_context, form_data) tuples
            user_id: Optional user ID

        Returns:
            Dictionary mapping item index to nudges
        """
        results: dict[str, list[Nudge]] = {}

        for i, (context, data) in enumerate(items):
            nudges = self.generate_nudges(context, data, user_id)
            results[str(i)] = nudges

        return results

    def get_critical_nudges(
        self,
        form_context: FormContext | None = None,
    ) -> list[Nudge]:
        """Get all critical severity nudges."""
        nudges = list(self._nudges.values())

        if form_context:
            nudges = [n for n in nudges if n.form_context == form_context]

        return [n for n in nudges if n.severity == NudgeSeverity.CRITICAL and not n.dismissed]

    def export_rules(self) -> list[dict[str, Any]]:
        """Export all rules as dictionaries."""
        return [
            {
                "id": str(rule.id),
                "name": rule.name,
                "description": rule.description,
                "form_context": rule.form_context.value,
                "category": rule.category.value,
                "severity": rule.severity.value,
                "trigger": rule.trigger.value,
                "conditions": rule.conditions,
                "message_template": rule.message_template,
                "action_text": rule.action_text,
                "action_url": rule.action_url,
                "is_active": rule.is_active,
                "priority": rule.priority,
            }
            for rule in self._rules.values()
        ]

    def import_rules(self, rules_data: list[dict[str, Any]]) -> int:
        """Import rules from dictionaries."""
        imported = 0

        for data in rules_data:
            rule = NudgeRule(
                id=UUID(data["id"]) if "id" in data else uuid4(),
                name=data["name"],
                description=data["description"],
                form_context=FormContext(data["form_context"]),
                category=NudgeCategory(data["category"]),
                severity=NudgeSeverity(data["severity"]),
                trigger=NudgeTrigger(data["trigger"]),
                conditions=data["conditions"],
                message_template=data["message_template"],
                action_text=data.get("action_text"),
                action_url=data.get("action_url"),
                is_active=data.get("is_active", True),
                priority=data.get("priority", 50),
            )
            self._rules[rule.id] = rule
            imported += 1

        return imported
