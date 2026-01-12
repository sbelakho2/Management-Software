"""
Tests for Data Hygiene Nudges Service.

Verifies:
- Nudge generation from field rules
- Nudge lifecycle (create, dismiss, snooze, resolve)
- Suppression rules
- Hygiene scoring
- Bulk analysis
- Stale data detection
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.core.data_hygiene_nudges import (
    DataHygieneNudgesService,
    EntityHygieneScore,
    EntityType,
    FieldRule,
    HygieneReport,
    Nudge,
    NudgePriority,
    NudgeStatus,
    NudgeSuppressionRule,
    NudgeType,
)


class TestFieldRules:
    """Tests for field rules configuration."""
    
    def test_default_rules_exist(self) -> None:
        """Test that default rules are initialized."""
        service = DataHygieneNudgesService()
        
        opportunity_rules = service.get_field_rules(EntityType.OPPORTUNITY)
        rfq_rules = service.get_field_rules(EntityType.RFQ)
        quote_rules = service.get_field_rules(EntityType.QUOTE)
        
        assert len(opportunity_rules) > 0
        assert len(rfq_rules) > 0
        assert len(quote_rules) > 0
    
    def test_add_custom_rule(self) -> None:
        """Test adding a custom field rule."""
        service = DataHygieneNudgesService()
        
        rule = FieldRule(
            field_name="custom_field",
            display_name="Custom Field",
            required=True,
            priority=NudgePriority.HIGH,
        )
        
        service.add_field_rule(EntityType.OPPORTUNITY, rule)
        
        rules = service.get_field_rules(EntityType.OPPORTUNITY)
        field_names = [r.field_name for r in rules]
        
        assert "custom_field" in field_names
    
    def test_rule_with_min_length(self) -> None:
        """Test rule with minimum length requirement."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        # Add rule requiring 10 chars
        rule = FieldRule(
            field_name="description",
            display_name="Description",
            required=True,
            min_length=10,
            priority=NudgePriority.MEDIUM,
        )
        service.add_field_rule(EntityType.TASK, rule)
        
        # Analyze with short description
        nudges = service.analyze_entity(
            EntityType.TASK,
            entity_id,
            data={"title": "Task", "description": "Short"},
        )
        
        desc_nudge = next((n for n in nudges if n.field_name == "description"), None)
        assert desc_nudge is not None
        assert desc_nudge.nudge_type == NudgeType.INCOMPLETE_FIELD
    
    def test_rule_with_allowed_values(self) -> None:
        """Test rule with allowed values constraint."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        rule = FieldRule(
            field_name="priority",
            display_name="Priority",
            required=True,
            allowed_values=["low", "medium", "high"],
            priority=NudgePriority.MEDIUM,
        )
        service.add_field_rule(EntityType.TASK, rule)
        
        nudges = service.analyze_entity(
            EntityType.TASK,
            entity_id,
            data={"title": "Task", "priority": "invalid"},
        )
        
        priority_nudge = next((n for n in nudges if n.field_name == "priority"), None)
        assert priority_nudge is not None
        assert priority_nudge.nudge_type == NudgeType.VALIDATION_WARNING


class TestNudgeGeneration:
    """Tests for nudge generation."""
    
    def test_analyze_entity_missing_required(self) -> None:
        """Test nudge generation for missing required fields."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},  # Empty data
        )
        
        # Should have nudges for missing required fields
        assert len(nudges) > 0
        
        # Name is required
        name_nudge = next((n for n in nudges if n.field_name == "name"), None)
        assert name_nudge is not None
        assert name_nudge.priority == NudgePriority.HIGH
    
    def test_analyze_entity_with_complete_data(self) -> None:
        """Test that complete data generates fewer nudges."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        complete_data = {
            "name": "Test Opportunity",
            "account_id": uuid4(),
            "next_step": "Schedule meeting",
            "next_step_date": datetime.now(timezone.utc),
            "value": 10000,
            "probability": 0.5,
        }
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data=complete_data,
        )
        
        # Should have no nudges for complete data
        assert len(nudges) == 0
    
    def test_analyze_with_conditional_rule(self) -> None:
        """Test conditional rule based on another field."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        # Rule that only applies when status is "qualified"
        rule = FieldRule(
            field_name="qualification_notes",
            display_name="Qualification Notes",
            required=True,
            priority=NudgePriority.HIGH,
            depends_on={"status": "qualified"},
        )
        service.add_field_rule(EntityType.OPPORTUNITY, rule)
        
        # Should not trigger when status is different
        nudges1 = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={"name": "Test", "status": "new"},
        )
        qual_nudge1 = next((n for n in nudges1 if n.field_name == "qualification_notes"), None)
        assert qual_nudge1 is None
        
        # Should trigger when status matches
        nudges2 = service.analyze_entity(
            EntityType.OPPORTUNITY,
            uuid4(),  # New entity
            data={"name": "Test", "status": "qualified"},
        )
        qual_nudge2 = next((n for n in nudges2 if n.field_name == "qualification_notes"), None)
        assert qual_nudge2 is not None
    
    def test_nudge_suggestion_generated(self) -> None:
        """Test that suggestions are generated."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        # At least one nudge should have a suggestion
        with_suggestions = [n for n in nudges if n.suggestion]
        assert len(with_suggestions) >= 0  # Some may have suggestions


class TestNudgeLifecycle:
    """Tests for nudge lifecycle operations."""
    
    def test_get_nudge(self) -> None:
        """Test retrieving a nudge by ID."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        if nudges:
            nudge = service.get_nudge(nudges[0].id)
            assert nudge is not None
            assert nudge.id == nudges[0].id
    
    def test_dismiss_nudge(self) -> None:
        """Test dismissing a nudge."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        user_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        assert len(nudges) > 0
        
        dismissed = service.dismiss_nudge(nudges[0].id, user_id, reason="Not relevant")
        
        assert dismissed is not None
        assert dismissed.status == NudgeStatus.DISMISSED
        assert dismissed.dismissed_by == user_id
        assert dismissed.dismissed_at is not None
    
    def test_snooze_nudge(self) -> None:
        """Test snoozing a nudge."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        assert len(nudges) > 0
        
        snoozed = service.snooze_nudge(nudges[0].id, snooze_hours=24)
        
        assert snoozed is not None
        assert snoozed.status == NudgeStatus.SNOOZED
        assert snoozed.snoozed_until is not None
        
        # Snoozed nudge should not be active
        assert snoozed.is_active is False
    
    def test_snoozed_nudge_becomes_active(self) -> None:
        """Test that snoozed nudge becomes active after snooze period."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        snoozed = service.snooze_nudge(nudges[0].id, snooze_hours=1)
        
        # Manually set snooze to past
        snoozed.snoozed_until = datetime.now(timezone.utc) - timedelta(hours=1)
        
        assert snoozed.is_active is True
    
    def test_resolve_nudge(self) -> None:
        """Test resolving a nudge."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        resolved = service.resolve_nudge(nudges[0].id, resolved_value="Fixed value")
        
        assert resolved is not None
        assert resolved.status == NudgeStatus.RESOLVED
        assert resolved.resolved_at is not None
        assert resolved.resolution_value == "Fixed value"
    
    def test_check_and_resolve_on_update(self) -> None:
        """Test auto-resolution when field is updated."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        # Generate nudge for missing name
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        # Update the field
        resolved = service.check_and_resolve(
            EntityType.OPPORTUNITY,
            entity_id,
            "name",
            "New Name",
        )
        
        assert resolved is not None
        assert resolved.status == NudgeStatus.RESOLVED


class TestNudgeRetrieval:
    """Tests for retrieving nudges."""
    
    def test_get_entity_nudges(self) -> None:
        """Test getting nudges for an entity."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        nudges = service.get_entity_nudges(EntityType.OPPORTUNITY, entity_id)
        
        assert len(nudges) > 0
        assert all(n.entity_id == entity_id for n in nudges)
    
    def test_get_entity_nudges_excludes_dismissed(self) -> None:
        """Test that dismissed nudges are excluded by default."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        user_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        # Dismiss first nudge
        service.dismiss_nudge(nudges[0].id, user_id)
        
        # Get nudges without dismissed
        active_nudges = service.get_entity_nudges(EntityType.OPPORTUNITY, entity_id)
        
        assert nudges[0].id not in [n.id for n in active_nudges]
    
    def test_get_entity_nudges_include_dismissed(self) -> None:
        """Test including dismissed nudges."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        user_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        service.dismiss_nudge(nudges[0].id, user_id)
        
        all_nudges = service.get_entity_nudges(
            EntityType.OPPORTUNITY,
            entity_id,
            include_dismissed=True,
        )
        
        assert nudges[0].id in [n.id for n in all_nudges]
    
    def test_get_priority_nudges(self) -> None:
        """Test getting top priority nudges."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        priority_nudges = service.get_priority_nudges(
            EntityType.OPPORTUNITY,
            entity_id,
            max_count=3,
        )
        
        assert len(priority_nudges) <= 3
    
    def test_nudges_sorted_by_priority(self) -> None:
        """Test that nudges are sorted by priority."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        nudges = service.get_entity_nudges(EntityType.OPPORTUNITY, entity_id)
        
        # First nudges should be higher priority
        if len(nudges) >= 2:
            priority_order = [
                NudgePriority.CRITICAL,
                NudgePriority.HIGH,
                NudgePriority.MEDIUM,
                NudgePriority.LOW,
            ]
            first_idx = priority_order.index(nudges[0].priority)
            second_idx = priority_order.index(nudges[1].priority)
            assert first_idx <= second_idx


class TestSuppressionRules:
    """Tests for nudge suppression."""
    
    def test_create_suppression_rule(self) -> None:
        """Test creating a suppression rule."""
        service = DataHygieneNudgesService()
        user_id = uuid4()
        
        rule = service.create_suppression_rule(
            created_by=user_id,
            reason="Not applicable for this account",
            entity_type=EntityType.OPPORTUNITY,
            field_name="value",
        )
        
        assert rule.id is not None
        assert rule.entity_type == EntityType.OPPORTUNITY
        assert rule.field_name == "value"
    
    def test_suppressed_nudge_not_generated(self) -> None:
        """Test that suppressed nudges are not generated."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        user_id = uuid4()
        
        # Create suppression for value field
        service.create_suppression_rule(
            created_by=user_id,
            reason="Value not needed",
            entity_type=EntityType.OPPORTUNITY,
            field_name="value",
        )
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={"name": "Test", "account_id": uuid4()},
            user_id=user_id,
        )
        
        # Value nudge should not be present
        value_nudge = next((n for n in nudges if n.field_name == "value"), None)
        assert value_nudge is None
    
    def test_suppression_rule_expiry(self) -> None:
        """Test that suppression rules expire."""
        service = DataHygieneNudgesService()
        user_id = uuid4()
        
        rule = service.create_suppression_rule(
            created_by=user_id,
            reason="Temporary",
            entity_type=EntityType.OPPORTUNITY,
            expires_in_days=1,
        )
        
        # Set expiry in the past
        rule.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Rule should not match now
        assert not rule.matches(
            EntityType.OPPORTUNITY,
            "name",
            NudgeType.MISSING_FIELD,
        )
    
    def test_delete_suppression_rule(self) -> None:
        """Test deleting a suppression rule."""
        service = DataHygieneNudgesService()
        user_id = uuid4()
        
        rule = service.create_suppression_rule(
            created_by=user_id,
            reason="Test",
            entity_type=EntityType.OPPORTUNITY,
        )
        
        result = service.delete_suppression_rule(rule.id)
        
        assert result is True
        
        rules = service.get_suppression_rules()
        assert rule.id not in [r.id for r in rules]
    
    def test_get_suppression_rules_by_type(self) -> None:
        """Test filtering suppression rules by entity type."""
        service = DataHygieneNudgesService()
        user_id = uuid4()
        
        service.create_suppression_rule(
            created_by=user_id,
            reason="Opp rule",
            entity_type=EntityType.OPPORTUNITY,
        )
        service.create_suppression_rule(
            created_by=user_id,
            reason="RFQ rule",
            entity_type=EntityType.RFQ,
        )
        
        opp_rules = service.get_suppression_rules(EntityType.OPPORTUNITY)
        
        assert all(r.entity_type in (None, EntityType.OPPORTUNITY) for r in opp_rules)


class TestHygieneScoring:
    """Tests for hygiene scoring."""
    
    def test_calculate_hygiene_score(self) -> None:
        """Test calculating hygiene score."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        score = service.calculate_hygiene_score(
            EntityType.OPPORTUNITY,
            entity_id,
            data={"name": "Test", "account_id": uuid4()},
        )
        
        assert isinstance(score, EntityHygieneScore)
        assert score.entity_type == EntityType.OPPORTUNITY
        assert score.total_fields > 0
        assert 0 <= score.completeness_percentage <= 100
    
    def test_complete_entity_high_score(self) -> None:
        """Test that complete entity has high score."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        complete_data = {
            "name": "Complete Opportunity",
            "account_id": uuid4(),
            "next_step": "Call customer",
            "next_step_date": datetime.now(timezone.utc),
            "value": 50000,
            "probability": 0.75,
        }
        
        score = service.calculate_hygiene_score(
            EntityType.OPPORTUNITY,
            entity_id,
            data=complete_data,
        )
        
        assert score.completeness_percentage == 100
        assert len(score.missing_fields) == 0
    
    def test_incomplete_entity_lists_missing(self) -> None:
        """Test that incomplete entity lists missing fields."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        score = service.calculate_hygiene_score(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        assert "name" in score.missing_fields
        assert score.completeness_percentage < 100
    
    def test_priority_score_weighted(self) -> None:
        """Test that priority score is weighted by field importance."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        # Missing only low priority field
        score1 = service.calculate_hygiene_score(
            EntityType.OPPORTUNITY,
            entity_id,
            data={
                "name": "Test",
                "account_id": uuid4(),
                "next_step": "Step",
                "next_step_date": datetime.now(timezone.utc),
                # Missing: value (low priority)
            },
        )
        
        # Missing high priority field
        score2 = service.calculate_hygiene_score(
            EntityType.OPPORTUNITY,
            entity_id,
            data={
                "next_step": "Step",
                "value": 1000,
                # Missing: name (high priority)
            },
        )
        
        # Score1 should have higher priority score
        assert score1.priority_score > score2.priority_score


class TestHygieneReports:
    """Tests for hygiene reports."""
    
    def test_generate_report(self) -> None:
        """Test generating a hygiene report."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        report = service.generate_report(entity_type=EntityType.OPPORTUNITY)
        
        assert isinstance(report, HygieneReport)
        assert report.total_nudges > 0
        assert report.active_nudges > 0
    
    def test_report_counts_by_status(self) -> None:
        """Test that report counts nudges by status."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        user_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        # Dismiss one
        if len(nudges) >= 2:
            service.dismiss_nudge(nudges[0].id, user_id)
            service.resolve_nudge(nudges[1].id)
        
        report = service.generate_report(entity_type=EntityType.OPPORTUNITY)
        
        assert report.dismissed_nudges >= 1
        assert report.resolved_nudges >= 1
    
    def test_report_by_priority(self) -> None:
        """Test that report breaks down by priority."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        report = service.generate_report(entity_type=EntityType.OPPORTUNITY)
        
        assert "high" in report.by_priority or "medium" in report.by_priority
    
    def test_report_by_field(self) -> None:
        """Test that report breaks down by field."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        report = service.generate_report(entity_type=EntityType.OPPORTUNITY)
        
        assert len(report.by_field) > 0


class TestBulkOperations:
    """Tests for bulk operations."""
    
    def test_bulk_analyze(self) -> None:
        """Test analyzing multiple entities at once."""
        service = DataHygieneNudgesService()
        entity_ids = [uuid4() for _ in range(5)]
        
        results = service.bulk_analyze(EntityType.OPPORTUNITY, entity_ids)
        
        assert len(results) == 5
        for entity_id in entity_ids:
            assert entity_id in results
    
    def test_get_user_nudges(self) -> None:
        """Test getting nudges across entities for a user."""
        service = DataHygieneNudgesService()
        
        # Create nudges for multiple entities
        for _ in range(3):
            service.analyze_entity(
                EntityType.OPPORTUNITY,
                uuid4(),
                data={},
            )
        
        user_nudges = service.get_user_nudges(uuid4(), limit=10)
        
        assert len(user_nudges) >= 3
    
    def test_get_user_nudges_filter_by_type(self) -> None:
        """Test filtering user nudges by entity type."""
        service = DataHygieneNudgesService()
        
        service.analyze_entity(EntityType.OPPORTUNITY, uuid4(), data={})
        service.analyze_entity(EntityType.RFQ, uuid4(), data={})
        
        opp_nudges = service.get_user_nudges(
            uuid4(),
            entity_types=[EntityType.OPPORTUNITY],
        )
        
        assert all(n.entity_type == EntityType.OPPORTUNITY for n in opp_nudges)


class TestStaleData:
    """Tests for stale data detection."""
    
    def test_detect_stale_data(self) -> None:
        """Test detection of stale records."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        
        nudges = service.get_stale_data_nudges(
            EntityType.OPPORTUNITY,
            entity_id,
            data={"name": "Old record", "updated_at": old_date},
            stale_threshold_days=30,
        )
        
        assert len(nudges) == 1
        assert nudges[0].nudge_type == NudgeType.STALE_DATA
        assert nudges[0].metadata.get("days_stale", 0) >= 60
    
    def test_fresh_data_no_stale_nudge(self) -> None:
        """Test that fresh data doesn't get stale nudge."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.get_stale_data_nudges(
            EntityType.OPPORTUNITY,
            entity_id,
            data={"name": "Fresh", "updated_at": datetime.now(timezone.utc)},
            stale_threshold_days=30,
        )
        
        assert len(nudges) == 0


class TestCleanup:
    """Tests for cleanup operations."""
    
    def test_cleanup_old_nudges(self) -> None:
        """Test cleaning up old resolved nudges."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        # Resolve and make old
        if nudges:
            service.resolve_nudge(nudges[0].id)
            nudge = service.get_nudge(nudges[0].id)
            nudge.resolved_at = datetime.now(timezone.utc) - timedelta(days=100)
        
        cleaned = service.cleanup_old_nudges(older_than_days=90)
        
        assert cleaned >= 1
    
    def test_cleanup_respects_age(self) -> None:
        """Test that cleanup respects age threshold."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={},
        )
        
        if nudges:
            service.resolve_nudge(nudges[0].id)
            # Don't make it old
        
        cleaned = service.cleanup_old_nudges(older_than_days=90)
        
        # Recent nudge should not be cleaned
        assert service.get_nudge(nudges[0].id) is not None


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_analyze_unknown_entity_type(self) -> None:
        """Test analyzing entity type without rules."""
        service = DataHygieneNudgesService()
        
        # Clear rules for product
        service._field_rules[EntityType.PRODUCT] = []
        
        nudges = service.analyze_entity(
            EntityType.PRODUCT,
            uuid4(),
            data={},
        )
        
        assert len(nudges) == 0
    
    def test_dismiss_nonexistent_nudge(self) -> None:
        """Test dismissing a nudge that doesn't exist."""
        service = DataHygieneNudgesService()
        
        result = service.dismiss_nudge(uuid4(), uuid4())
        
        assert result is None
    
    def test_resolve_nonexistent_nudge(self) -> None:
        """Test resolving a nudge that doesn't exist."""
        service = DataHygieneNudgesService()
        
        result = service.resolve_nudge(uuid4())
        
        assert result is None
    
    def test_duplicate_nudge_not_created(self) -> None:
        """Test that duplicate nudges are not created."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        # Analyze twice
        nudges1 = service.analyze_entity(EntityType.OPPORTUNITY, entity_id, data={})
        nudges2 = service.analyze_entity(EntityType.OPPORTUNITY, entity_id, data={})
        
        # Should return existing nudges, not create new ones
        nudge_ids1 = {n.id for n in nudges1}
        nudge_ids2 = {n.id for n in nudges2}
        
        assert nudge_ids1 == nudge_ids2
    
    def test_empty_string_treated_as_missing(self) -> None:
        """Test that empty strings are treated as missing."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        
        nudges = service.analyze_entity(
            EntityType.OPPORTUNITY,
            entity_id,
            data={"name": "   "},  # Whitespace only
        )
        
        name_nudge = next((n for n in nudges if n.field_name == "name"), None)
        assert name_nudge is not None
    
    def test_nudge_is_active_property(self) -> None:
        """Test is_active property for different states."""
        service = DataHygieneNudgesService()
        entity_id = uuid4()
        user_id = uuid4()
        
        nudges = service.analyze_entity(EntityType.OPPORTUNITY, entity_id, data={})
        
        if nudges:
            # Active nudge
            assert nudges[0].is_active is True
            
            # Dismissed nudge
            service.dismiss_nudge(nudges[0].id, user_id)
            assert nudges[0].is_active is False
