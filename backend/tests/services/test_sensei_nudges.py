"""
Tests for Sensei Nudges Service.

Verifies:
- Rule management (CRUD)
- Nudge generation based on conditions
- Threshold breach detection
- Missing field detection
- Pattern-based detection
- Dependency checks
- Time-based triggers
- User dismissals
- Feedback collection
- Statistics and reporting
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.sensei_nudges import (
    FormContext,
    Nudge,
    NudgeCategory,
    NudgeFeedback,
    NudgeRule,
    NudgeSeverity,
    NudgeStats,
    NudgeTrigger,
    SenseiNudgesService,
)


class TestDefaultRules:
    """Tests for default nudge rules."""

    def test_default_rules_exist(self) -> None:
        """Test that default rules are created."""
        service = SenseiNudgesService()

        rules = service.get_rules()

        assert len(rules) > 0

    def test_quote_margin_rules_exist(self) -> None:
        """Test that quote margin rules exist."""
        service = SenseiNudgesService()

        rules = service.get_rules(form_context=FormContext.QUOTE)

        assert len(rules) > 0
        margin_rules = [r for r in rules if r.category == NudgeCategory.MARGIN]
        assert len(margin_rules) >= 2

    def test_rfq_rules_exist(self) -> None:
        """Test that RFQ rules exist."""
        service = SenseiNudgesService()

        rules = service.get_rules(form_context=FormContext.RFQ)

        assert len(rules) > 0

    def test_rules_sorted_by_priority(self) -> None:
        """Test that rules are sorted by priority descending."""
        service = SenseiNudgesService()

        rules = service.get_rules()

        priorities = [r.priority for r in rules]
        assert priorities == sorted(priorities, reverse=True)


class TestRuleManagement:
    """Tests for rule CRUD operations."""

    def test_create_rule(self) -> None:
        """Test creating a custom rule."""
        service = SenseiNudgesService()

        rule = service.create_rule(
            name="test_rule",
            description="Test rule",
            form_context=FormContext.QUOTE,
            category=NudgeCategory.INFO,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.FIELD_VALUE,
            conditions={"field": "test", "operator": "eq", "value": "x"},
            message_template="Test message",
        )

        assert rule.id is not None
        assert rule.name == "test_rule"
        assert rule.is_active is True

    def test_get_rule(self) -> None:
        """Test retrieving a rule by ID."""
        service = SenseiNudgesService()

        rule = service.create_rule(
            name="get_test",
            description="Get test",
            form_context=FormContext.RFQ,
            category=NudgeCategory.WARNING,
            severity=NudgeSeverity.MEDIUM,
            trigger=NudgeTrigger.THRESHOLD_BREACH,
            conditions={"field": "x", "operator": "gt", "value": 10},
            message_template="Test",
        )

        retrieved = service.get_rule(rule.id)

        assert retrieved is not None
        assert retrieved.id == rule.id

    def test_update_rule(self) -> None:
        """Test updating a rule."""
        service = SenseiNudgesService()

        rule = service.create_rule(
            name="update_test",
            description="Original",
            form_context=FormContext.QUOTE,
            category=NudgeCategory.COST,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.FIELD_VALUE,
            conditions={"field": "x", "operator": "eq", "value": 1},
            message_template="Original message",
        )

        updated = service.update_rule(
            rule.id,
            description="Updated",
            priority=99,
        )

        assert updated is not None
        assert updated.description == "Updated"
        assert updated.priority == 99

    def test_delete_rule(self) -> None:
        """Test deleting a rule."""
        service = SenseiNudgesService()

        rule = service.create_rule(
            name="delete_test",
            description="To delete",
            form_context=FormContext.A3,
            category=NudgeCategory.BEST_PRACTICE,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.FIELD_MISSING,
            conditions={"field": "x", "operator": "missing"},
            message_template="Test",
        )

        result = service.delete_rule(rule.id)

        assert result is True
        assert service.get_rule(rule.id) is None

    def test_deactivate_rule(self) -> None:
        """Test deactivating a rule."""
        service = SenseiNudgesService()

        rule = service.create_rule(
            name="deactivate_test",
            description="Test",
            form_context=FormContext.CTQ,
            category=NudgeCategory.QUALITY,
            severity=NudgeSeverity.MEDIUM,
            trigger=NudgeTrigger.FIELD_MISSING,
            conditions={"field": "x", "operator": "missing"},
            message_template="Test",
        )

        deactivated = service.deactivate_rule(rule.id)

        assert deactivated is not None
        assert deactivated.is_active is False

    def test_activate_rule(self) -> None:
        """Test activating a rule."""
        service = SenseiNudgesService()

        rule = service.create_rule(
            name="activate_test",
            description="Test",
            form_context=FormContext.RISK,
            category=NudgeCategory.RISK,
            severity=NudgeSeverity.HIGH,
            trigger=NudgeTrigger.THRESHOLD_BREACH,
            conditions={"field": "x", "operator": "gte", "value": 5},
            message_template="Test",
        )

        service.deactivate_rule(rule.id)
        activated = service.activate_rule(rule.id)

        assert activated is not None
        assert activated.is_active is True

    def test_filter_rules_by_context(self) -> None:
        """Test filtering rules by form context."""
        service = SenseiNudgesService()

        quote_rules = service.get_rules(form_context=FormContext.QUOTE)
        rfq_rules = service.get_rules(form_context=FormContext.RFQ)

        assert all(r.form_context == FormContext.QUOTE for r in quote_rules)
        assert all(r.form_context == FormContext.RFQ for r in rfq_rules)

    def test_filter_rules_by_category(self) -> None:
        """Test filtering rules by category."""
        service = SenseiNudgesService()

        margin_rules = service.get_rules(category=NudgeCategory.MARGIN)

        assert all(r.category == NudgeCategory.MARGIN for r in margin_rules)


class TestNudgeGeneration:
    """Tests for nudge generation."""

    def test_generate_nudge_for_low_margin(self) -> None:
        """Test nudge generation for low margin."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        margin_nudges = [n for n in nudges if n.category == NudgeCategory.MARGIN]
        assert len(margin_nudges) >= 1
        assert "10" in margin_nudges[0].message

    def test_generate_nudge_for_critical_margin(self) -> None:
        """Test critical nudge for very low margin."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 3},
        )

        critical_nudges = [n for n in nudges if n.severity == NudgeSeverity.CRITICAL]
        assert len(critical_nudges) >= 1

    def test_generate_nudge_for_missing_field(self) -> None:
        """Test nudge for missing required field."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.RFQ,
            {"estimated_annual_volume": None},
        )

        missing_nudges = [n for n in nudges if n.trigger == NudgeTrigger.FIELD_MISSING]
        assert len(missing_nudges) >= 1

    def test_no_nudge_when_field_present(self) -> None:
        """Test no nudge when required field is present."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.RFQ,
            {"estimated_annual_volume": 10000},
        )

        volume_nudges = [n for n in nudges if n.field_name == "estimated_annual_volume"]
        assert len(volume_nudges) == 0

    def test_nudges_sorted_by_priority(self) -> None:
        """Test that nudges are sorted by priority."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 3, "scrap_rate": 15},
        )

        priorities = [n.priority for n in nudges]
        assert priorities == sorted(priorities, reverse=True)

    def test_no_nudges_for_valid_data(self) -> None:
        """Test no nudges when data is valid."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {
                "margin_percentage": 25,
                "scrap_rate": 3,
            },
        )

        # Should have no margin or scrap nudges
        margin_nudges = [n for n in nudges if n.category == NudgeCategory.MARGIN]
        scrap_nudges = [n for n in nudges if n.field_name == "scrap_rate"]
        assert len(margin_nudges) == 0
        assert len(scrap_nudges) == 0


class TestThresholdConditions:
    """Tests for threshold-based conditions."""

    def test_less_than_condition(self) -> None:
        """Test less than operator."""
        service = SenseiNudgesService()

        service.create_rule(
            name="lt_test",
            description="Test",
            form_context=FormContext.QUOTE,
            category=NudgeCategory.INFO,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.THRESHOLD_BREACH,
            conditions={"field": "test_value", "operator": "lt", "value": 50},
            message_template="Value {value} is below 50",
        )

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"test_value": 30},
        )

        assert any("30" in n.message and "below 50" in n.message for n in nudges)

    def test_greater_than_condition(self) -> None:
        """Test greater than operator."""
        service = SenseiNudgesService()

        service.create_rule(
            name="gt_test",
            description="Test",
            form_context=FormContext.QUOTE,
            category=NudgeCategory.WARNING,
            severity=NudgeSeverity.MEDIUM,
            trigger=NudgeTrigger.THRESHOLD_BREACH,
            conditions={"field": "cost", "operator": "gt", "value": 1000},
            message_template="Cost of {value} exceeds limit",
        )

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"cost": 1500},
        )

        assert any("1500" in n.message for n in nudges)

    def test_equal_condition(self) -> None:
        """Test equals operator."""
        service = SenseiNudgesService()

        service.create_rule(
            name="eq_test",
            description="Test",
            form_context=FormContext.RFQ,
            category=NudgeCategory.INFO,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.FIELD_VALUE,
            conditions={"field": "status", "operator": "eq", "value": "draft"},
            message_template="Status is draft",
        )

        nudges = service.generate_nudges(
            FormContext.RFQ,
            {"status": "draft"},
        )

        assert any("draft" in n.message.lower() for n in nudges)


class TestDependencyConditions:
    """Tests for dependency-based conditions."""

    def test_dependency_check(self) -> None:
        """Test dependency check between fields."""
        service = SenseiNudgesService()

        # Create a custom dependency rule for testing
        service.create_rule(
            name="test_dependency",
            description="Test dependency check",
            form_context=FormContext.A3,
            category=NudgeCategory.BEST_PRACTICE,
            severity=NudgeSeverity.MEDIUM,
            trigger=NudgeTrigger.DEPENDENCY_CHECK,
            conditions={"has_solution": True, "has_analysis": False},
            message_template="Solution without analysis detected",
            priority=80,
        )

        nudges = service.generate_nudges(
            FormContext.A3,
            {
                "has_solution": True,
                "has_analysis": False,
            },
        )

        dependency_nudges = [n for n in nudges if n.trigger == NudgeTrigger.DEPENDENCY_CHECK]
        assert len(dependency_nudges) >= 1

    def test_dependency_not_triggered(self) -> None:
        """Test dependency not triggered when conditions not met."""
        service = SenseiNudgesService()

        # Create a custom dependency rule for testing
        service.create_rule(
            name="test_dependency_2",
            description="Test dependency check",
            form_context=FormContext.A3,
            category=NudgeCategory.BEST_PRACTICE,
            severity=NudgeSeverity.MEDIUM,
            trigger=NudgeTrigger.DEPENDENCY_CHECK,
            conditions={"has_solution": True, "has_analysis": False},
            message_template="Solution without analysis detected",
            priority=80,
        )

        nudges = service.generate_nudges(
            FormContext.A3,
            {
                "has_solution": True,
                "has_analysis": True,  # Analysis present - should not trigger
            },
        )

        dependency_nudges = [n for n in nudges if "analysis" in n.message.lower()]
        assert len(dependency_nudges) == 0


class TestTimeBasedConditions:
    """Tests for time-based conditions."""

    def test_past_due_condition(self) -> None:
        """Test past due date condition."""
        service = SenseiNudgesService()

        past_date = datetime.now(timezone.utc) - timedelta(days=5)

        nudges = service.generate_nudges(
            FormContext.WORK_ORDER,
            {"scheduled_end": past_date},
        )

        past_due_nudges = [n for n in nudges if n.trigger == NudgeTrigger.TIME_BASED]
        assert len(past_due_nudges) >= 1

    def test_within_days_condition(self) -> None:
        """Test within days condition."""
        service = SenseiNudgesService()

        upcoming_date = datetime.now(timezone.utc) + timedelta(days=5)

        nudges = service.generate_nudges(
            FormContext.CAPA,
            {"due_date": upcoming_date},
        )

        upcoming_nudges = [n for n in nudges if "7 days" in n.message]
        assert len(upcoming_nudges) >= 1

    def test_older_than_days_condition(self) -> None:
        """Test older than days condition."""
        service = SenseiNudgesService()

        old_date = datetime.now(timezone.utc) - timedelta(days=20)

        nudges = service.generate_nudges(
            FormContext.OPPORTUNITY,
            {"last_activity_date": old_date},
        )

        stale_nudges = [n for n in nudges if n.category == NudgeCategory.EFFICIENCY]
        assert len(stale_nudges) >= 1


class TestUserDismissals:
    """Tests for user dismissal functionality."""

    def test_dismiss_nudge(self) -> None:
        """Test dismissing a nudge."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        assert len(nudges) > 0
        nudge = nudges[0]

        dismissed = service.dismiss_nudge(nudge.id, user_id)

        assert dismissed is not None
        assert dismissed.dismissed is True
        assert dismissed.dismissed_by == user_id

    def test_dismiss_rule_permanently(self) -> None:
        """Test permanently dismissing a rule for user."""
        service = SenseiNudgesService()
        user_id = uuid4()

        # Generate nudges first time
        nudges1 = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
            user_id,
        )

        assert len(nudges1) > 0
        nudge = nudges1[0]

        # Dismiss the rule permanently
        service.dismiss_nudge(nudge.id, user_id, dismiss_rule=True)

        # Generate nudges again - should not include dismissed rule
        nudges2 = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
            user_id,
        )

        # Should have fewer nudges
        assert len(nudges2) < len(nudges1)

    def test_get_user_dismissals(self) -> None:
        """Test getting user's dismissed rules."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
            user_id,
        )

        service.dismiss_nudge(nudges[0].id, user_id, dismiss_rule=True)

        dismissals = service.get_user_dismissals(user_id)

        assert len(dismissals) == 1

    def test_clear_user_dismissals(self) -> None:
        """Test clearing user's dismissals."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
            user_id,
        )

        service.dismiss_nudge(nudges[0].id, user_id, dismiss_rule=True)

        count = service.clear_user_dismissals(user_id)

        assert count == 1
        assert len(service.get_user_dismissals(user_id)) == 0


class TestFeedback:
    """Tests for nudge feedback."""

    def test_add_feedback(self) -> None:
        """Test adding feedback to a nudge."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        feedback = service.add_feedback(
            nudges[0].id,
            user_id,
            "helpful",
            "Great suggestion!",
        )

        assert feedback is not None
        assert feedback.feedback_type == "helpful"
        assert feedback.comment == "Great suggestion!"

    def test_get_feedback(self) -> None:
        """Test getting feedback for a nudge."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        service.add_feedback(nudges[0].id, user_id, "followed")
        service.add_feedback(nudges[0].id, uuid4(), "helpful")

        feedback_list = service.get_feedback(nudges[0].id)

        assert len(feedback_list) == 2

    def test_feedback_types(self) -> None:
        """Test various feedback types."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        for feedback_type in ["helpful", "not_helpful", "incorrect", "followed", "ignored"]:
            feedback = service.add_feedback(nudges[0].id, user_id, feedback_type)
            assert feedback.feedback_type == feedback_type


class TestPatterns:
    """Tests for historical pattern tracking."""

    def test_record_pattern(self) -> None:
        """Test recording a pattern."""
        service = SenseiNudgesService()

        service.record_pattern("quote:margin", {"value": 15})
        service.record_pattern("quote:margin", {"value": 12})
        service.record_pattern("quote:margin", {"value": 18})

        insights = service.get_pattern_insights("quote:margin")

        assert insights["count"] == 3

    def test_pattern_insights(self) -> None:
        """Test getting pattern insights."""
        service = SenseiNudgesService()

        # Record enough patterns to trigger insights
        for _ in range(5):
            service.record_pattern("test:field", {"value": "test"})

        insights = service.get_pattern_insights("test:field")

        assert insights["count"] == 5
        assert len(insights["insights"]) >= 1

    def test_pattern_limit(self) -> None:
        """Test that patterns are limited to 100."""
        service = SenseiNudgesService()

        for i in range(150):
            service.record_pattern("limit:test", {"value": i})

        insights = service.get_pattern_insights("limit:test")

        assert insights["count"] == 100


class TestSuggestedValues:
    """Tests for suggested value functionality."""

    def test_default_suggested_value(self) -> None:
        """Test getting default suggested value."""
        service = SenseiNudgesService()

        suggested = service.get_suggested_value(
            FormContext.QUOTE,
            "margin_percentage",
            {},
        )

        assert suggested == 20.0

    def test_suggested_value_from_patterns(self) -> None:
        """Test suggested value from historical patterns."""
        service = SenseiNudgesService()

        # Record patterns with common value
        for _ in range(5):
            service.record_pattern("quote:custom_field", {"value": 42})

        suggested = service.get_suggested_value(
            FormContext.QUOTE,
            "custom_field",
            {},
        )

        assert suggested == 42

    def test_suggested_value_no_data(self) -> None:
        """Test suggested value when no data available."""
        service = SenseiNudgesService()

        suggested = service.get_suggested_value(
            FormContext.QUOTE,
            "unknown_field",
            {},
        )

        assert suggested is None


class TestStatistics:
    """Tests for nudge statistics."""

    def test_get_statistics(self) -> None:
        """Test getting nudge statistics."""
        service = SenseiNudgesService()

        # Generate some nudges
        service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10, "scrap_rate": 15},
        )

        stats = service.get_statistics()

        assert isinstance(stats, NudgeStats)
        assert stats.total_generated > 0
        assert len(stats.by_category) > 0

    def test_statistics_by_context(self) -> None:
        """Test statistics filtered by context."""
        service = SenseiNudgesService()

        service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )
        service.generate_nudges(
            FormContext.RFQ,
            {"estimated_annual_volume": None},
        )

        quote_stats = service.get_statistics(FormContext.QUOTE)
        rfq_stats = service.get_statistics(FormContext.RFQ)

        assert quote_stats.total_generated > 0
        assert rfq_stats.total_generated > 0

    def test_statistics_follow_rate(self) -> None:
        """Test follow rate calculation."""
        service = SenseiNudgesService()
        user_id = uuid4()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        # Add feedback
        service.add_feedback(nudges[0].id, user_id, "followed")

        stats = service.get_statistics()

        assert stats.total_followed > 0
        assert stats.follow_rate > 0


class TestBulkOperations:
    """Tests for bulk operations."""

    def test_bulk_generate_nudges(self) -> None:
        """Test generating nudges for multiple items."""
        service = SenseiNudgesService()

        items = [
            (FormContext.QUOTE, {"margin_percentage": 10}),
            (FormContext.RFQ, {"estimated_annual_volume": None}),
            (FormContext.CTQ, {"measurement_method": None}),
        ]

        results = service.bulk_generate_nudges(items)

        assert len(results) == 3
        assert "0" in results
        assert "1" in results
        assert "2" in results


class TestCriticalNudges:
    """Tests for critical nudge handling."""

    def test_get_critical_nudges(self) -> None:
        """Test getting only critical nudges."""
        service = SenseiNudgesService()

        # Generate critical and non-critical nudges
        service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 3},  # Critical margin
        )

        critical = service.get_critical_nudges()

        assert all(n.severity == NudgeSeverity.CRITICAL for n in critical)

    def test_critical_nudges_by_context(self) -> None:
        """Test getting critical nudges by context."""
        service = SenseiNudgesService()

        service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 3},
        )

        critical = service.get_critical_nudges(FormContext.QUOTE)

        assert all(n.form_context == FormContext.QUOTE for n in critical)


class TestExportImport:
    """Tests for rule export/import."""

    def test_export_rules(self) -> None:
        """Test exporting rules."""
        service = SenseiNudgesService()

        exported = service.export_rules()

        assert len(exported) > 0
        assert all("name" in r for r in exported)
        assert all("conditions" in r for r in exported)

    def test_import_rules(self) -> None:
        """Test importing rules."""
        service = SenseiNudgesService()

        rules_data = [
            {
                "name": "imported_rule",
                "description": "Imported",
                "form_context": "quote",
                "category": "info",
                "severity": "low",
                "trigger": "field_value",
                "conditions": {"field": "x", "operator": "eq", "value": 1},
                "message_template": "Imported rule triggered",
            }
        ]

        count = service.import_rules(rules_data)

        assert count == 1

        # Verify imported rule works
        rules = service.get_rules(form_context=FormContext.QUOTE)
        assert any(r.name == "imported_rule" for r in rules)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_dismiss_nonexistent_nudge(self) -> None:
        """Test dismissing non-existent nudge."""
        service = SenseiNudgesService()

        result = service.dismiss_nudge(uuid4(), uuid4())

        assert result is None

    def test_feedback_nonexistent_nudge(self) -> None:
        """Test feedback on non-existent nudge."""
        service = SenseiNudgesService()

        result = service.add_feedback(uuid4(), uuid4(), "helpful")

        assert result is None

    def test_get_nudge(self) -> None:
        """Test getting a nudge by ID."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        nudge = service.get_nudge(nudges[0].id)

        assert nudge is not None
        assert nudge.id == nudges[0].id

    def test_update_nonexistent_rule(self) -> None:
        """Test updating non-existent rule."""
        service = SenseiNudgesService()

        result = service.update_rule(uuid4(), name="New Name")

        assert result is None

    def test_delete_nonexistent_rule(self) -> None:
        """Test deleting non-existent rule."""
        service = SenseiNudgesService()

        result = service.delete_rule(uuid4())

        assert result is False

    def test_empty_form_data(self) -> None:
        """Test nudge generation with empty form data."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(FormContext.QUOTE, {})

        # Should still generate nudges for missing fields
        assert isinstance(nudges, list)

    def test_null_values(self) -> None:
        """Test handling of null values in conditions."""
        service = SenseiNudgesService()

        nudges = service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": None},
        )

        # Should not crash
        assert isinstance(nudges, list)

    def test_contains_operator(self) -> None:
        """Test contains operator."""
        service = SenseiNudgesService()

        service.create_rule(
            name="contains_test",
            description="Test",
            form_context=FormContext.RFQ,
            category=NudgeCategory.WARNING,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.FIELD_VALUE,
            conditions={"field": "notes", "operator": "contains", "value": "urgent"},
            message_template="Urgent item detected",
        )

        nudges = service.generate_nudges(
            FormContext.RFQ,
            {"notes": "This is urgent please review"},
        )

        assert any("Urgent" in n.message for n in nudges)

    def test_in_operator(self) -> None:
        """Test in operator."""
        service = SenseiNudgesService()

        service.create_rule(
            name="in_test",
            description="Test",
            form_context=FormContext.OPPORTUNITY,
            category=NudgeCategory.INFO,
            severity=NudgeSeverity.LOW,
            trigger=NudgeTrigger.FIELD_VALUE,
            conditions={"field": "status", "operator": "in", "value": ["draft", "pending"]},
            message_template="Status requires attention",
        )

        nudges = service.generate_nudges(
            FormContext.OPPORTUNITY,
            {"status": "draft"},
        )

        assert any("requires attention" in n.message for n in nudges)

    def test_get_user_nudges(self) -> None:
        """Test getting nudges for a user."""
        service = SenseiNudgesService()
        user_id = uuid4()

        service.generate_nudges(
            FormContext.QUOTE,
            {"margin_percentage": 10},
        )

        nudges = service.get_user_nudges(user_id)

        # Should return all nudges since user hasn't dismissed any
        assert isinstance(nudges, list)

    def test_clear_dismissals_no_user(self) -> None:
        """Test clearing dismissals for user with no dismissals."""
        service = SenseiNudgesService()

        count = service.clear_user_dismissals(uuid4())

        assert count == 0
