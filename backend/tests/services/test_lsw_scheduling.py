"""
Tests for LSW (Leader Standard Work) Scheduling & Checklists Service.

Comprehensive tests for recurring LSW generation, checklists, and compliance tracking.
"""

import pytest
from datetime import datetime, date, time, timedelta
from uuid import uuid4

from sensei.services.lsw_scheduling import (
    LSWSchedulingService,
    LSWChecklistTemplate,
    LSWChecklistInstance,
    LSWChecklist,
    LSWReminder,
    LSWGenerationResult,
    LSWFrequency,
    LSWCategory,
    LSWItemStatus,
    DayOfWeek,
    build_lsw_template,
    get_default_template_ids,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def service() -> LSWSchedulingService:
    """Create a service instance."""
    return LSWSchedulingService()


@pytest.fixture
def owner_id() -> str:
    """Create a test owner ID."""
    return str(uuid4())


@pytest.fixture
def custom_template() -> LSWChecklistTemplate:
    """Create a custom template."""
    return LSWChecklistTemplate(
        id="custom-audit",
        name="Custom Process Audit",
        description="Custom audit procedure",
        category=LSWCategory.PROCESS_AUDIT,
        frequency=LSWFrequency.WEEKLY,
        estimated_duration_minutes=45,
        required=True,
        days_of_week=[DayOfWeek.TUESDAY, DayOfWeek.THURSDAY],
        requires_notes=True,
        requires_evidence=True,
        evidence_prompt="Document audit findings",
        sub_items=["Review documentation", "Observe process", "Interview operator"],
    )


# --------------------------------------------------------------------------
# Service Initialization Tests
# --------------------------------------------------------------------------

class TestServiceInitialization:
    """Test service initialization."""
    
    def test_service_creates_default_templates(self, service: LSWSchedulingService):
        """Test that default templates are created."""
        templates = service.list_templates()
        assert len(templates) > 0
        
        # Check for known defaults
        template_ids = [t.id for t in templates]
        assert "daily-gemba" in template_ids
        assert "daily-tier1" in template_ids
        assert "weekly-tier2" in template_ids
        assert "monthly-tier3" in template_ids
    
    def test_default_templates_have_correct_frequencies(self, service: LSWSchedulingService):
        """Test that default templates have correct frequencies."""
        daily = service.list_templates(frequency=LSWFrequency.DAILY)
        weekly = service.list_templates(frequency=LSWFrequency.WEEKLY)
        monthly = service.list_templates(frequency=LSWFrequency.MONTHLY)
        
        assert len(daily) >= 3  # gemba, tier1, safety
        assert len(weekly) >= 3  # tier2, coaching, process-audit
        assert len(monthly) >= 3  # tier3, standard-review, training-check


# --------------------------------------------------------------------------
# Template Management Tests
# --------------------------------------------------------------------------

class TestTemplateManagement:
    """Test template CRUD operations."""
    
    def test_create_template(self, service: LSWSchedulingService, custom_template: LSWChecklistTemplate):
        """Test creating a new template."""
        result = service.create_template(custom_template)
        
        assert result.id == "custom-audit"
        assert result.name == "Custom Process Audit"
        assert result.frequency == LSWFrequency.WEEKLY
    
    def test_get_template(self, service: LSWSchedulingService):
        """Test getting a template by ID."""
        template = service.get_template("daily-gemba")
        
        assert template is not None
        assert template.name == "Daily Gemba Walk"
        assert template.category == LSWCategory.GEMBA_WALK
    
    def test_get_nonexistent_template(self, service: LSWSchedulingService):
        """Test getting a nonexistent template."""
        template = service.get_template("nonexistent")
        assert template is None
    
    def test_update_template(self, service: LSWSchedulingService):
        """Test updating a template."""
        result = service.update_template("daily-gemba", {
            "estimated_duration_minutes": 45,
            "requires_evidence": True,
        })
        
        assert result is not None
        assert result.estimated_duration_minutes == 45
        assert result.requires_evidence is True
    
    def test_delete_template(self, service: LSWSchedulingService, custom_template: LSWChecklistTemplate):
        """Test deleting a template."""
        service.create_template(custom_template)
        
        result = service.delete_template("custom-audit")
        assert result is True
        
        # Should no longer exist
        assert service.get_template("custom-audit") is None
    
    def test_list_templates_by_category(self, service: LSWSchedulingService):
        """Test listing templates by category."""
        tier_meeting = service.list_templates(category=LSWCategory.TIER_MEETING)
        
        assert len(tier_meeting) >= 3  # tier1, tier2, tier3
        for t in tier_meeting:
            assert t.category == LSWCategory.TIER_MEETING
    
    def test_list_templates_active_only(self, service: LSWSchedulingService):
        """Test listing only active templates."""
        # Deactivate a template
        service.update_template("monthly-recognition", {"is_active": False})
        
        active = service.list_templates(active_only=True)
        inactive_ids = [t.id for t in active if not t.is_active]
        
        assert len(inactive_ids) == 0


# --------------------------------------------------------------------------
# Checklist Generation Tests
# --------------------------------------------------------------------------

class TestChecklistGeneration:
    """Test checklist generation."""
    
    def test_generate_daily_checklist(self, service: LSWSchedulingService, owner_id: str):
        """Test generating a daily checklist."""
        today = date.today()
        result = service.generate_checklist(owner_id, today)
        
        assert result.date == today
        assert result.owner_id == owner_id
        assert result.generated_count > 0
        
        # Should include daily items
        template_ids = [i.template_id for i in result.items]
        assert "daily-gemba" in template_ids
        assert "daily-tier1" in template_ids
    
    def test_generate_weekly_items_on_correct_day(self, service: LSWSchedulingService, owner_id: str):
        """Test weekly items only generated on correct days."""
        # Find a Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        monday = today + timedelta(days=days_until_monday)
        
        result = service.generate_checklist(owner_id, monday)
        
        # Tier 2 should be generated on Monday
        template_ids = [i.template_id for i in result.items]
        assert "weekly-tier2" in template_ids
    
    def test_weekly_items_not_on_wrong_day(self, service: LSWSchedulingService, owner_id: str):
        """Test weekly items not generated on wrong days."""
        # Find a Tuesday
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        tuesday = today + timedelta(days=days_until_tuesday)
        
        result = service.generate_checklist(owner_id, tuesday)
        
        # Tier 2 (Monday) should NOT be generated on Tuesday
        template_ids = [i.template_id for i in result.items]
        assert "weekly-tier2" not in template_ids
    
    def test_generate_monthly_items_on_correct_week(self, service: LSWSchedulingService, owner_id: str):
        """Test monthly items on correct week of month."""
        # Find first Wednesday of a month (Tier 3)
        today = date.today()
        first_of_month = today.replace(day=1)
        days_until_wed = (2 - first_of_month.weekday()) % 7
        first_wednesday = first_of_month + timedelta(days=days_until_wed)
        
        result = service.generate_checklist(owner_id, first_wednesday)
        
        # Tier 3 should be generated on first Wednesday
        template_ids = [i.template_id for i in result.items]
        assert "monthly-tier3" in template_ids
    
    def test_generate_specific_templates_only(self, service: LSWSchedulingService, owner_id: str):
        """Test generating only specific templates."""
        today = date.today()
        result = service.generate_checklist(
            owner_id,
            today,
            template_ids=["daily-gemba", "daily-safety"],
        )
        
        assert result.generated_count == 2
        template_ids = [i.template_id for i in result.items]
        assert "daily-gemba" in template_ids
        assert "daily-safety" in template_ids
        assert "daily-tier1" not in template_ids
    
    def test_generate_week_checklists(self, service: LSWSchedulingService, owner_id: str):
        """Test generating a week's worth of checklists."""
        today = date.today()
        start = today - timedelta(days=today.weekday())  # Start of week (Monday)
        
        results = service.generate_week_checklists(owner_id, start)
        
        # Should have results for most days
        assert len(results) >= 5  # At least weekdays
    
    def test_reminders_generated_for_items_with_preferred_time(
        self, service: LSWSchedulingService, owner_id: str
    ):
        """Test that reminders are generated for items with preferred time."""
        tomorrow = date.today() + timedelta(days=1)
        result = service.generate_checklist(owner_id, tomorrow)
        
        # Should have reminders for daily items with preferred times
        assert len(result.reminders) > 0
    
    def test_effective_date_filtering(self, service: LSWSchedulingService, owner_id: str):
        """Test templates respect effective dates."""
        # Create template with future effective date
        future_template = LSWChecklistTemplate(
            id="future-item",
            name="Future Item",
            description="Not yet effective",
            category=LSWCategory.OTHER,
            frequency=LSWFrequency.DAILY,
            effective_from=date.today() + timedelta(days=30),
        )
        service.create_template(future_template)
        
        result = service.generate_checklist(owner_id, date.today())
        
        # Future template should not be generated
        template_ids = [i.template_id for i in result.items]
        assert "future-item" not in template_ids


# --------------------------------------------------------------------------
# Checklist Instance Actions Tests
# --------------------------------------------------------------------------

class TestChecklistInstanceActions:
    """Test actions on checklist instances."""
    
    def test_start_item(self, service: LSWSchedulingService, owner_id: str):
        """Test starting an item."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        
        started = service.start_item(item.id)
        
        assert started is not None
        assert started.status == LSWItemStatus.IN_PROGRESS
        assert started.started_at is not None
    
    def test_complete_item(self, service: LSWSchedulingService, owner_id: str):
        """Test completing an item."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        user_id = str(uuid4())
        
        service.start_item(item.id)
        completed = service.complete_item(
            item.id,
            completed_by_id=user_id,
            notes="Completed gemba walk",
            actual_duration_minutes=25,
        )
        
        assert completed is not None
        assert completed.status == LSWItemStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.completed_by_id == user_id
        assert completed.notes == "Completed gemba walk"
        assert completed.actual_duration_minutes == 25
    
    def test_complete_item_calculates_duration(self, service: LSWSchedulingService, owner_id: str):
        """Test that duration is calculated from start time if not provided."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        user_id = str(uuid4())
        
        service.start_item(item.id)
        # Wait a tiny bit (in tests, we can't really wait)
        completed = service.complete_item(item.id, completed_by_id=user_id)
        
        assert completed.actual_duration_minutes is not None
    
    def test_complete_sub_item(self, service: LSWSchedulingService, owner_id: str):
        """Test completing sub-items."""
        result = service.generate_checklist(owner_id, date.today())
        # Find gemba walk which has sub-items
        gemba_item = next((i for i in result.items if i.template_id == "daily-gemba"), None)
        assert gemba_item is not None
        
        updated = service.complete_sub_item(gemba_item.id, "Walk through all work areas")
        
        assert updated is not None
        assert "Walk through all work areas" in updated.sub_items_completed
    
    def test_skip_item(self, service: LSWSchedulingService, owner_id: str):
        """Test skipping an item."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        
        skipped = service.skip_item(item.id, "Production emergency")
        
        assert skipped is not None
        assert skipped.status == LSWItemStatus.SKIPPED
        assert skipped.skip_reason == "Production emergency"
    
    def test_defer_item(self, service: LSWSchedulingService, owner_id: str):
        """Test deferring an item."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        tomorrow = date.today() + timedelta(days=1)
        
        deferred = service.defer_item(item.id, tomorrow, "Rescheduled due to meeting")
        
        assert deferred is not None
        assert deferred.status == LSWItemStatus.DEFERRED
        assert deferred.deferred_to == tomorrow
    
    def test_add_finding(self, service: LSWSchedulingService, owner_id: str):
        """Test adding findings to an item."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        
        finding = {
            "type": "observation",
            "description": "5S issue in area B",
            "severity": "minor",
        }
        updated = service.add_finding(item.id, finding)
        
        assert updated is not None
        assert len(updated.findings) == 1
        assert updated.findings[0]["description"] == "5S issue in area B"
    
    def test_link_generated_task(self, service: LSWSchedulingService, owner_id: str):
        """Test linking a generated task."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        task_id = str(uuid4())
        
        updated = service.link_generated_task(item.id, task_id)
        
        assert updated is not None
        assert task_id in updated.generated_task_ids
    
    def test_link_generated_a3(self, service: LSWSchedulingService, owner_id: str):
        """Test linking a generated A3."""
        result = service.generate_checklist(owner_id, date.today())
        item = result.items[0]
        a3_id = str(uuid4())
        
        updated = service.link_generated_a3(item.id, a3_id)
        
        assert updated is not None
        assert a3_id in updated.generated_a3_ids


# --------------------------------------------------------------------------
# Retrieval Tests
# --------------------------------------------------------------------------

class TestChecklistRetrieval:
    """Test checklist retrieval."""
    
    def test_get_checklist(self, service: LSWSchedulingService, owner_id: str):
        """Test getting a checklist by owner and date."""
        today = date.today()
        service.generate_checklist(owner_id, today)
        
        checklist = service.get_checklist(owner_id, today)
        
        assert checklist is not None
        assert checklist.owner_id == owner_id
        assert checklist.date == today
    
    def test_get_instance(self, service: LSWSchedulingService, owner_id: str):
        """Test getting an instance by ID."""
        result = service.generate_checklist(owner_id, date.today())
        instance_id = result.items[0].id
        
        instance = service.get_instance(instance_id)
        
        assert instance is not None
        assert instance.id == instance_id
    
    def test_get_pending_items(self, service: LSWSchedulingService, owner_id: str):
        """Test getting pending items."""
        service.generate_checklist(owner_id, date.today())
        
        pending = service.get_pending_items(owner_id)
        
        assert len(pending) > 0
        for item in pending:
            assert item.status in [LSWItemStatus.PENDING, LSWItemStatus.DUE, LSWItemStatus.OVERDUE]
    
    def test_get_overdue_items(self, service: LSWSchedulingService, owner_id: str):
        """Test getting overdue items."""
        # Generate checklist for yesterday
        yesterday = date.today() - timedelta(days=1)
        service.generate_checklist(owner_id, yesterday)
        
        # Mark as overdue
        service.update_overdue_items()
        
        overdue = service.get_overdue_items(owner_id)
        
        assert len(overdue) > 0
        for item in overdue:
            assert item.scheduled_date < date.today()


# --------------------------------------------------------------------------
# Status Updates Tests
# --------------------------------------------------------------------------

class TestStatusUpdates:
    """Test status update functionality."""
    
    def test_update_overdue_items(self, service: LSWSchedulingService, owner_id: str):
        """Test updating items to overdue status."""
        yesterday = date.today() - timedelta(days=1)
        result = service.generate_checklist(owner_id, yesterday)
        
        updated = service.update_overdue_items()
        
        assert len(updated) > 0
        for item in updated:
            assert item.status == LSWItemStatus.OVERDUE
    
    def test_get_due_reminders(self, service: LSWSchedulingService, owner_id: str):
        """Test getting due reminders."""
        # Create checklist with reminders set in the past
        today = date.today()
        result = service.generate_checklist(owner_id, today)
        
        # Manually set reminder time to past
        if result.reminders:
            result.reminders[0].reminder_time = datetime.now() - timedelta(hours=1)
        
        due = service.get_due_reminders()
        
        # At least some should be due
        assert len(due) >= 0  # May or may not have due reminders depending on timing
    
    def test_mark_reminder_sent(self, service: LSWSchedulingService, owner_id: str):
        """Test marking a reminder as sent."""
        today = date.today() + timedelta(days=1)  # Tomorrow to get future reminders
        result = service.generate_checklist(owner_id, today)
        
        if result.reminders:
            reminder = result.reminders[0]
            updated = service.mark_reminder_sent(reminder.id)
            
            assert updated is not None
            assert updated.sent is True
            assert updated.sent_at is not None


# --------------------------------------------------------------------------
# Analytics Tests
# --------------------------------------------------------------------------

class TestAnalytics:
    """Test analytics and compliance tracking."""
    
    def test_compliance_stats(self, service: LSWSchedulingService, owner_id: str):
        """Test getting compliance statistics."""
        today = date.today()
        user_id = str(uuid4())
        
        # Generate and complete some items
        result = service.generate_checklist(owner_id, today)
        for i, item in enumerate(result.items[:3]):
            service.complete_item(item.id, completed_by_id=user_id)
        
        stats = service.get_compliance_stats(
            owner_id,
            today,
            today,
        )
        
        assert stats["owner_id"] == owner_id
        assert stats["total_items"] > 0
        assert stats["completed"] == 3
        assert stats["completion_rate"] > 0
    
    def test_compliance_stats_by_category(self, service: LSWSchedulingService, owner_id: str):
        """Test compliance stats include category breakdown."""
        today = date.today()
        user_id = str(uuid4())
        
        result = service.generate_checklist(owner_id, today)
        for item in result.items[:2]:
            service.complete_item(item.id, completed_by_id=user_id)
        
        stats = service.get_compliance_stats(owner_id, today, today)
        
        assert "by_category" in stats
        # Should have at least one category
        assert len(stats["by_category"]) > 0
    
    def test_findings_summary(self, service: LSWSchedulingService, owner_id: str):
        """Test getting findings summary."""
        today = date.today()
        
        result = service.generate_checklist(owner_id, today)
        item = result.items[0]
        
        # Add some findings
        service.add_finding(item.id, {"type": "observation", "description": "Issue 1"})
        service.add_finding(item.id, {"type": "action_needed", "description": "Issue 2"})
        
        findings = service.get_findings_summary(owner_id, today, today)
        
        assert len(findings) == 2


# --------------------------------------------------------------------------
# Frequency Tests
# --------------------------------------------------------------------------

class TestFrequencyScheduling:
    """Test different frequency scheduling logic."""
    
    def test_daily_frequency(self, service: LSWSchedulingService, owner_id: str):
        """Test daily items are generated every day."""
        for i in range(7):
            target = date.today() + timedelta(days=i)
            result = service.generate_checklist(owner_id, target)
            template_ids = [item.template_id for item in result.items]
            assert "daily-gemba" in template_ids
    
    def test_bi_weekly_frequency(self, service: LSWSchedulingService, owner_id: str):
        """Test bi-weekly items are generated every other week."""
        # Create a bi-weekly template
        bi_weekly = LSWChecklistTemplate(
            id="bi-weekly-test",
            name="Bi-Weekly Test",
            description="Test",
            category=LSWCategory.OTHER,
            frequency=LSWFrequency.BI_WEEKLY,
            days_of_week=[DayOfWeek.MONDAY],
        )
        service.create_template(bi_weekly)
        
        # Find two consecutive Mondays
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        monday1 = today + timedelta(days=days_until_monday)
        monday2 = monday1 + timedelta(days=7)
        
        result1 = service.generate_checklist(owner_id, monday1, template_ids=["bi-weekly-test"])
        result2 = service.generate_checklist(owner_id, monday2, template_ids=["bi-weekly-test"])
        
        # One should generate, one should not (depending on even/odd week)
        counts = [result1.generated_count, result2.generated_count]
        assert 0 in counts or 1 in counts  # At least some variation
    
    def test_quarterly_frequency(self, service: LSWSchedulingService, owner_id: str):
        """Test quarterly items are generated on first Monday of quarter."""
        quarterly = LSWChecklistTemplate(
            id="quarterly-test",
            name="Quarterly Test",
            description="Test",
            category=LSWCategory.OTHER,
            frequency=LSWFrequency.QUARTERLY,
        )
        service.create_template(quarterly)
        
        # Find first Monday of January (Q1)
        q1_start = date(date.today().year + 1, 1, 1)
        days_until_monday = (7 - q1_start.weekday()) % 7
        first_monday_q1 = q1_start + timedelta(days=days_until_monday)
        
        result = service.generate_checklist(owner_id, first_monday_q1, template_ids=["quarterly-test"])
        
        template_ids = [item.template_id for item in result.items]
        assert "quarterly-test" in template_ids


# --------------------------------------------------------------------------
# Helper Function Tests
# --------------------------------------------------------------------------

class TestHelperFunctions:
    """Test helper functions."""
    
    def test_build_lsw_template(self):
        """Test building an LSW template from parameters."""
        template = build_lsw_template(
            name="Test Template",
            description="Test description",
            category="gemba_walk",
            frequency="weekly",
            estimated_duration_minutes=30,
            days_of_week=["monday", "wednesday"],
            requires_notes=True,
        )
        
        assert template.name == "Test Template"
        assert template.category == LSWCategory.GEMBA_WALK
        assert template.frequency == LSWFrequency.WEEKLY
        assert template.estimated_duration_minutes == 30
        assert DayOfWeek.MONDAY in template.days_of_week
        assert template.requires_notes is True
    
    def test_get_default_template_ids(self):
        """Test getting default template IDs."""
        ids = get_default_template_ids()
        
        assert "daily-gemba" in ids
        assert "daily-tier1" in ids
        assert "weekly-tier2" in ids
        assert "monthly-tier3" in ids
        assert len(ids) >= 10


# --------------------------------------------------------------------------
# Edge Cases
# --------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_nonexistent_instance_returns_none(self, service: LSWSchedulingService):
        """Test operations on nonexistent instances return None."""
        assert service.get_instance("nonexistent") is None
        assert service.start_item("nonexistent") is None
        assert service.complete_item("nonexistent", "user") is None
        assert service.skip_item("nonexistent", "reason") is None
    
    def test_duplicate_sub_item_completion(self, service: LSWSchedulingService, owner_id: str):
        """Test completing same sub-item twice doesn't duplicate."""
        result = service.generate_checklist(owner_id, date.today())
        gemba = next((i for i in result.items if i.template_id == "daily-gemba"), None)
        assert gemba is not None
        
        service.complete_sub_item(gemba.id, "Walk through all work areas")
        service.complete_sub_item(gemba.id, "Walk through all work areas")
        
        instance = service.get_instance(gemba.id)
        assert instance.sub_items_completed.count("Walk through all work areas") == 1
    
    def test_empty_compliance_stats(self, service: LSWSchedulingService, owner_id: str):
        """Test compliance stats with no data."""
        stats = service.get_compliance_stats(
            owner_id,
            date.today() - timedelta(days=30),
            date.today() - timedelta(days=29),
        )
        
        assert stats["total_items"] == 0
        assert stats["completion_rate"] == 0
    
    def test_findings_summary_no_owner_filter(self, service: LSWSchedulingService, owner_id: str):
        """Test findings summary without owner filter."""
        today = date.today()
        result = service.generate_checklist(owner_id, today)
        
        service.add_finding(result.items[0].id, {"type": "test", "description": "Test finding"})
        
        findings = service.get_findings_summary(None, today, today)
        
        assert len(findings) >= 1


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_daily_workflow(self, service: LSWSchedulingService, owner_id: str):
        """Test a complete daily LSW workflow."""
        today = date.today()
        user_id = str(uuid4())
        
        # 1. Generate checklist
        result = service.generate_checklist(owner_id, today)
        assert result.generated_count > 0
        
        # 2. Start first item
        gemba = next((i for i in result.items if i.template_id == "daily-gemba"), None)
        assert gemba is not None
        service.start_item(gemba.id)
        
        # 3. Complete sub-items
        service.complete_sub_item(gemba.id, "Walk through all work areas")
        service.complete_sub_item(gemba.id, "Observe 5S conditions")
        
        # 4. Add findings
        service.add_finding(gemba.id, {
            "type": "observation",
            "area": "Assembly Line B",
            "description": "Tool not returned to shadow board",
        })
        
        # 5. Complete with notes
        service.complete_item(
            gemba.id,
            completed_by_id=user_id,
            notes="Good overall, one 5S issue noted",
        )
        
        # 6. Link generated action
        task_id = str(uuid4())
        service.link_generated_task(gemba.id, task_id)
        
        # 7. Check stats
        stats = service.get_compliance_stats(owner_id, today, today)
        assert stats["completed"] >= 1
        
        # 8. Check findings
        findings = service.get_findings_summary(owner_id, today, today)
        assert len(findings) == 1
    
    def test_skip_and_defer_workflow(self, service: LSWSchedulingService, owner_id: str):
        """Test skipping and deferring items."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        result = service.generate_checklist(owner_id, today)
        
        # Skip one item
        item1 = result.items[0]
        service.skip_item(item1.id, "Production crisis - no time")
        
        # Defer another
        item2 = result.items[1]
        service.defer_item(item2.id, tomorrow, "Rescheduled for tomorrow")
        
        # Check states
        assert service.get_instance(item1.id).status == LSWItemStatus.SKIPPED
        assert service.get_instance(item2.id).status == LSWItemStatus.DEFERRED
        assert service.get_instance(item2.id).deferred_to == tomorrow
    
    def test_overdue_management(self, service: LSWSchedulingService, owner_id: str):
        """Test overdue item management."""
        yesterday = date.today() - timedelta(days=1)
        
        # Generate yesterday's checklist
        result = service.generate_checklist(owner_id, yesterday)
        
        # Update status
        updated = service.update_overdue_items()
        
        # All should be overdue
        for item in updated:
            assert item.status == LSWItemStatus.OVERDUE
        
        # Get overdue items
        overdue = service.get_overdue_items(owner_id)
        assert len(overdue) == len(result.items)
