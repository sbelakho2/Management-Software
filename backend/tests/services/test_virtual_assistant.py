"""
Tests for Sensei Virtual Assistant.

Covers:
- SLA Watchdog
- Meeting Preparation AI
- Combined Virtual Assistant
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
import time
import asyncio

from sensei.services.virtual_assistant import (
    # Enums
    SLAStatus,
    ItemType,
    NotificationType,
    NotificationPriority,
    EntityCategory,
    BriefingSection,
    # Data models
    SLADeadline,
    TimeToFailure,
    Notification,
    NotificationRule,
    CalendarEvent,
    ExtractedEntity,
    BriefingItem,
    BriefingNote,
    # Classes
    CriticalPathCalculator,
    SLAWatchdog,
    CalendarEntityExtractor,
    BriefingNoteGenerator,
    MeetingPreparationAI,
    SenseiVirtualAssistant,
    # Factory
    create_virtual_assistant,
    # Constants
    DEFAULT_SLA_CHECK_INTERVAL,
    CRITICAL_THRESHOLD_HOURS,
    WARNING_THRESHOLD_HOURS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def now():
    """Current time fixture."""
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_deadline(now):
    """Sample SLA deadline."""
    return SLADeadline(
        item_id="RFQ-001",
        item_type=ItemType.RFQ,
        deadline=now + timedelta(hours=12),
        description="RFQ deadline",
        owner_id="user_001",
        priority=1,
    )


@pytest.fixture
def sample_event(now):
    """Sample calendar event."""
    return CalendarEvent(
        event_id="evt_001",
        title="Customer Review: Acme Corp RFQ#123",
        description="Discuss RFQ status and pricing for Acme Corp order.",
        start_time=now + timedelta(hours=2),
        end_time=now + timedelta(hours=3),
        location="Conference Room A",
        organizer="sales@example.com",
        attendees=["john@acme.com", "sales@example.com"],
    )


@pytest.fixture
def sla_watchdog():
    """SLA Watchdog instance."""
    return SLAWatchdog(check_interval=60)


@pytest.fixture
def entity_extractor():
    """Entity extractor instance."""
    return CalendarEntityExtractor()


@pytest.fixture
def meeting_prep():
    """Meeting preparation AI instance."""
    return MeetingPreparationAI()


@pytest.fixture
def virtual_assistant():
    """Virtual assistant instance."""
    return SenseiVirtualAssistant(sla_check_interval=60)


# =============================================================================
# CriticalPathCalculator Tests
# =============================================================================

class TestCriticalPathCalculator:
    """Tests for CriticalPathCalculator."""
    
    def test_simple_path(self):
        """Test simple critical path calculation."""
        calc = CriticalPathCalculator()
        calc.add_item("A", 2, [])
        calc.add_item("B", 3, ["A"])
        calc.add_item("C", 1, ["B"])
        
        path = calc.calculate_critical_path()
        
        assert path == ["A", "B", "C"]
    
    def test_parallel_paths(self):
        """Test with parallel paths."""
        calc = CriticalPathCalculator()
        calc.add_item("A", 2, [])
        calc.add_item("B", 5, ["A"])  # Longer path
        calc.add_item("C", 2, ["A"])  # Shorter path
        calc.add_item("D", 1, ["B", "C"])
        
        path = calc.calculate_critical_path()
        
        # Critical path goes through B (longer)
        assert "B" in path
        assert "D" in path
    
    def test_empty_graph(self):
        """Test empty dependency graph."""
        calc = CriticalPathCalculator()
        
        path = calc.calculate_critical_path()
        
        assert path == []
    
    def test_slack_times(self):
        """Test slack time calculation."""
        calc = CriticalPathCalculator()
        calc.add_item("A", 2, [])
        calc.add_item("B", 3, ["A"])
        calc.add_item("C", 1, ["A"])
        calc.add_item("D", 1, ["B", "C"])
        
        slack = calc.get_slack_times()
        
        # Items on critical path have zero slack
        assert slack["A"] == 0.0 or slack["B"] == 0.0
    
    def test_single_item(self):
        """Test single item graph."""
        calc = CriticalPathCalculator()
        calc.add_item("A", 5, [])
        
        path = calc.calculate_critical_path()
        
        assert path == ["A"]


# =============================================================================
# SLAWatchdog Tests
# =============================================================================

class TestSLAWatchdog:
    """Tests for SLAWatchdog."""
    
    def test_add_deadline(self, sla_watchdog, sample_deadline):
        """Test adding a deadline."""
        sla_watchdog.add_deadline(sample_deadline)
        
        assert len(sla_watchdog._deadlines) == 1
        assert "RFQ-001" in sla_watchdog._deadlines
    
    def test_remove_deadline(self, sla_watchdog, sample_deadline):
        """Test removing a deadline."""
        sla_watchdog.add_deadline(sample_deadline)
        
        result = sla_watchdog.remove_deadline("RFQ-001")
        
        assert result is True
        assert len(sla_watchdog._deadlines) == 0
    
    def test_remove_nonexistent(self, sla_watchdog):
        """Test removing non-existent deadline."""
        result = sla_watchdog.remove_deadline("FAKE")
        
        assert result is False
    
    def test_calculate_ttf_ok_status(self, sla_watchdog, now):
        """Test TTF calculation for OK status."""
        deadline = SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=72),  # Far in future
            description="Test",
            owner_id="user",
        )
        sla_watchdog.add_deadline(deadline)
        
        ttf = sla_watchdog.calculate_time_to_failure("RFQ-001", now)
        
        assert ttf is not None
        assert ttf.status == SLAStatus.OK
        assert ttf.risk_score < 0.5
    
    def test_calculate_ttf_warning_status(self, sla_watchdog, now):
        """Test TTF calculation for WARNING status."""
        deadline = SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=36),  # Within warning threshold
            description="Test",
            owner_id="user",
        )
        sla_watchdog.add_deadline(deadline)
        
        ttf = sla_watchdog.calculate_time_to_failure("RFQ-001", now)
        
        assert ttf is not None
        assert ttf.status == SLAStatus.WARNING
    
    def test_calculate_ttf_critical_status(self, sla_watchdog, now):
        """Test TTF calculation for CRITICAL status."""
        deadline = SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=12),  # Within critical threshold
            description="Test",
            owner_id="user",
        )
        sla_watchdog.add_deadline(deadline)
        
        ttf = sla_watchdog.calculate_time_to_failure("RFQ-001", now)
        
        assert ttf is not None
        assert ttf.status == SLAStatus.CRITICAL
        assert ttf.risk_score > 0.8
    
    def test_calculate_ttf_breached_status(self, sla_watchdog, now):
        """Test TTF calculation for BREACHED status."""
        deadline = SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now - timedelta(hours=1),  # Past deadline
            description="Test",
            owner_id="user",
        )
        sla_watchdog.add_deadline(deadline)
        
        ttf = sla_watchdog.calculate_time_to_failure("RFQ-001", now)
        
        assert ttf is not None
        assert ttf.status == SLAStatus.BREACHED
        assert ttf.risk_score == 1.0
    
    def test_calculate_ttf_nonexistent(self, sla_watchdog):
        """Test TTF for non-existent item."""
        ttf = sla_watchdog.calculate_time_to_failure("FAKE")
        
        assert ttf is None
    
    def test_check_all_deadlines(self, sla_watchdog, now):
        """Test checking all deadlines."""
        # Add multiple deadlines with different statuses
        for i, hours in enumerate([5, 30, 60]):
            deadline = SLADeadline(
                item_id=f"RFQ-{i}",
                item_type=ItemType.RFQ,
                deadline=now + timedelta(hours=hours),
                description="Test",
                owner_id="user",
            )
            sla_watchdog.add_deadline(deadline)
        
        results = sla_watchdog.check_all_deadlines(now)
        
        assert len(results) == 3
        # Should be sorted by risk score descending
        assert results[0].risk_score >= results[1].risk_score
    
    def test_get_critical_items(self, sla_watchdog, now):
        """Test getting critical items."""
        # Add one critical and one OK
        sla_watchdog.add_deadline(SLADeadline(
            item_id="CRITICAL",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=5),
            description="Test",
            owner_id="user",
        ))
        sla_watchdog.add_deadline(SLADeadline(
            item_id="OK",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=100),
            description="Test",
            owner_id="user",
        ))
        
        critical = sla_watchdog.get_critical_items(now)
        
        assert len(critical) == 1
        assert critical[0].item_id == "CRITICAL"
    
    def test_blocking_factors(self, sla_watchdog, now):
        """Test blocking factor detection."""
        # Add dependent items with bad ordering
        sla_watchdog.add_deadline(SLADeadline(
            item_id="PARENT",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=30),  # Due after child
            description="Parent",
            owner_id="user",
        ))
        sla_watchdog.add_deadline(SLADeadline(
            item_id="CHILD",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=20),
            description="Child",
            owner_id="user",
            dependencies=["PARENT"],
        ))
        
        ttf = sla_watchdog.calculate_time_to_failure("CHILD", now)
        
        assert ttf is not None
        assert len(ttf.blocking_factors) > 0
    
    def test_add_rule(self, sla_watchdog):
        """Test adding notification rule."""
        rule = NotificationRule(
            rule_id="test_rule",
            item_type=ItemType.QUOTE,
            status=SLAStatus.WARNING,
            notification_types=[NotificationType.EMAIL],
            recipient_roles=["manager"],
            priority=NotificationPriority.HIGH,
        )
        
        sla_watchdog.add_rule(rule)
        
        assert "test_rule" in sla_watchdog._rules
    
    def test_generate_notifications(self, sla_watchdog, now):
        """Test notification generation."""
        # Add a critical item
        sla_watchdog.add_deadline(SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=5),
            description="Test",
            owner_id="user",
        ))
        
        ttf = sla_watchdog.calculate_time_to_failure("RFQ-001", now)
        
        recipient_ids = {
            "gm": ["gm_001"],
            "sales_manager": ["sm_001"],
        }
        
        notifications = sla_watchdog.generate_notifications(ttf, recipient_ids)
        
        # Should generate notifications based on default rules
        assert len(notifications) > 0
    
    def test_notification_cooldown(self, sla_watchdog, now):
        """Test notification cooldown prevents spam."""
        sla_watchdog.add_deadline(SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=5),
            description="Test",
            owner_id="user",
        ))
        
        ttf = sla_watchdog.calculate_time_to_failure("RFQ-001", now)
        recipient_ids = {"gm": ["gm_001"]}
        
        # First call - should generate
        notifications1 = sla_watchdog.generate_notifications(ttf, recipient_ids)
        
        # Second call immediately - should be blocked by cooldown
        notifications2 = sla_watchdog.generate_notifications(ttf, recipient_ids)
        
        # First should have notifications, second should be empty
        assert len(notifications1) > 0
        assert len(notifications2) == 0
    
    def test_send_notification(self, sla_watchdog):
        """Test sending notification."""
        callback_called = []
        
        def callback(n):
            callback_called.append(n)
        
        sla_watchdog.notification_callback = callback
        
        notification = Notification(
            notification_id="test",
            recipient_id="user",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        result = sla_watchdog.send_notification(notification)
        
        assert result is True
        assert len(callback_called) == 1
    
    def test_get_stats(self, sla_watchdog, sample_deadline):
        """Test getting statistics."""
        sla_watchdog.add_deadline(sample_deadline)
        
        stats = sla_watchdog.get_stats()
        
        assert stats["total_monitored"] == 1
        assert "status_counts" in stats
    
    @pytest.mark.asyncio
    async def test_run_check_cycle(self, sla_watchdog, now):
        """Test running a check cycle."""
        sla_watchdog.add_deadline(SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=5),
            description="Test",
            owner_id="user",
        ))
        
        recipient_ids = {"gm": ["gm_001"]}
        
        notifications = await sla_watchdog.run_check_cycle(recipient_ids)
        
        assert isinstance(notifications, list)
    
    def test_stop_watchdog(self, sla_watchdog):
        """Test stopping watchdog."""
        sla_watchdog._is_running = True
        
        sla_watchdog.stop()
        
        assert sla_watchdog._is_running is False


# =============================================================================
# CalendarEntityExtractor Tests
# =============================================================================

class TestCalendarEntityExtractor:
    """Tests for CalendarEntityExtractor."""
    
    def test_extract_rfq_from_title(self, entity_extractor, sample_event):
        """Test extracting RFQ from title."""
        entities = entity_extractor.extract_from_event(sample_event)
        
        rfq_entities = [e for e in entities if e.entity_type == EntityCategory.RFQ]
        assert len(rfq_entities) >= 1
        assert rfq_entities[0].normalized_value == "123"
    
    def test_extract_customer_from_attendee(self, entity_extractor, now):
        """Test extracting customer from attendee email."""
        event = CalendarEvent(
            event_id="evt",
            title="Meeting",
            description="",
            start_time=now,
            end_time=now + timedelta(hours=1),
            attendees=["contact@acmecorp.com"],
        )
        
        entities = entity_extractor.extract_from_event(event)
        
        customer_entities = [e for e in entities if e.entity_type == EntityCategory.CUSTOMER]
        assert len(customer_entities) >= 1
    
    def test_extract_order_po(self, entity_extractor, now):
        """Test extracting PO number."""
        event = CalendarEvent(
            event_id="evt",
            title="Review PO#456",
            description="Discuss purchase order",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        
        entities = entity_extractor.extract_from_event(event)
        
        order_entities = [e for e in entities if e.entity_type == EntityCategory.ORDER]
        assert len(order_entities) >= 1
    
    def test_register_known_entity(self, entity_extractor):
        """Test registering known entity for linking."""
        entity_extractor.register_known_entity(
            EntityCategory.CUSTOMER,
            "Acme Corp",
            "cust_001",
        )
        
        assert "acme corp" in entity_extractor._known_entities[EntityCategory.CUSTOMER]
    
    def test_extract_with_linking(self, entity_extractor, now):
        """Test extraction with known entity linking."""
        entity_extractor.register_known_entity(
            EntityCategory.RFQ,
            "123",
            "rfq_123",
        )
        
        event = CalendarEvent(
            event_id="evt",
            title="Review RFQ 123",
            description="",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        
        entities = entity_extractor.extract_from_event(event)
        
        rfq_entity = next((e for e in entities if e.entity_type == EntityCategory.RFQ), None)
        assert rfq_entity is not None
        assert rfq_entity.linked_record_id == "rfq_123"
        assert rfq_entity.confidence > 0.8
    
    def test_deduplication(self, entity_extractor, now):
        """Test that duplicate entities are removed."""
        event = CalendarEvent(
            event_id="evt",
            title="RFQ 123 meeting",
            description="Discuss RFQ#123 progress",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )
        
        entities = entity_extractor.extract_from_event(event)
        
        # Should deduplicate RFQ 123 mentions
        rfq_entities = [e for e in entities if e.entity_type == EntityCategory.RFQ]
        assert len(rfq_entities) == 1
    
    def test_batch_register(self, entity_extractor):
        """Test batch registration of entities."""
        entity_extractor.register_known_entities_batch(
            EntityCategory.CUSTOMER,
            [("Acme Corp", "cust_001"), ("TechCo", "cust_002")],
        )
        
        assert len(entity_extractor._known_entities[EntityCategory.CUSTOMER]) == 2


# =============================================================================
# BriefingNoteGenerator Tests
# =============================================================================

class TestBriefingNoteGenerator:
    """Tests for BriefingNoteGenerator."""
    
    @pytest.fixture
    def generator(self, entity_extractor):
        return BriefingNoteGenerator(entity_extractor)
    
    def test_generate_briefing(self, generator, sample_event):
        """Test generating a briefing."""
        briefing = generator.generate_briefing(sample_event)
        
        assert briefing.meeting_id == sample_event.event_id
        assert len(briefing.items) > 0
    
    def test_executive_summary_included(self, generator, sample_event):
        """Test executive summary is included."""
        briefing = generator.generate_briefing(sample_event)
        
        summary_items = [i for i in briefing.items if i.section == BriefingSection.EXECUTIVE_SUMMARY]
        assert len(summary_items) == 1
    
    def test_to_markdown(self, generator, sample_event):
        """Test Markdown generation."""
        briefing = generator.generate_briefing(sample_event)
        markdown = briefing.to_markdown()
        
        assert "# " in markdown  # Has heading
        assert sample_event.title in markdown or "Briefing" in markdown
    
    def test_to_dict(self, generator, sample_event):
        """Test dictionary conversion."""
        briefing = generator.generate_briefing(sample_event)
        data = briefing.to_dict()
        
        assert "briefing_id" in data
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_register_data_provider(self, generator):
        """Test registering a data provider."""
        mock_provider = Mock(return_value={"total_value": 1000})
        
        generator.register_data_provider("rfq_provider", mock_provider)
        
        assert "rfq_provider" in generator._data_providers
    
    def test_generate_with_data_provider(self, generator, sample_event, entity_extractor):
        """Test generation with data provider."""
        entity_extractor.register_known_entity(EntityCategory.RFQ, "123", "rfq_123")
        
        mock_provider = Mock(return_value={
            "total_value": 50000,
            "pending_count": 3,
        })
        generator.register_data_provider("rfq_provider", mock_provider)
        
        briefing = generator.generate_briefing(sample_event)
        
        # Provider should have been called
        mock_provider.assert_called()
    
    def test_generate_pdf_content(self, generator, sample_event):
        """Test PDF content generation."""
        briefing = generator.generate_briefing(sample_event)
        html = generator.generate_pdf_content(briefing)
        
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert briefing.title in html


# =============================================================================
# MeetingPreparationAI Tests
# =============================================================================

class TestMeetingPreparationAI:
    """Tests for MeetingPreparationAI."""
    
    def test_extract_entities(self, meeting_prep, sample_event):
        """Test entity extraction."""
        entities = meeting_prep.extract_entities(sample_event)
        
        assert isinstance(entities, list)
    
    def test_generate_briefing(self, meeting_prep, sample_event):
        """Test briefing generation."""
        briefing = meeting_prep.generate_briefing(sample_event)
        
        assert isinstance(briefing, BriefingNote)
        assert briefing.meeting_id == sample_event.event_id
    
    def test_get_briefing(self, meeting_prep, sample_event):
        """Test retrieving generated briefing."""
        briefing = meeting_prep.generate_briefing(sample_event)
        
        retrieved = meeting_prep.get_briefing(briefing.briefing_id)
        
        assert retrieved is briefing
    
    def test_generate_markdown(self, meeting_prep, sample_event):
        """Test Markdown generation."""
        markdown = meeting_prep.generate_briefing_markdown(sample_event)
        
        assert isinstance(markdown, str)
        assert "# " in markdown
    
    def test_generate_pdf(self, meeting_prep, sample_event):
        """Test PDF generation."""
        html = meeting_prep.generate_briefing_pdf(sample_event)
        
        assert "<html>" in html
    
    def test_register_known_entities(self, meeting_prep):
        """Test registering known entities."""
        meeting_prep.register_known_entities(
            EntityCategory.CUSTOMER,
            [("Acme Corp", "cust_001")],
        )
        
        assert "acme corp" in meeting_prep.entity_extractor._known_entities[EntityCategory.CUSTOMER]
    
    def test_get_stats(self, meeting_prep, sample_event):
        """Test getting stats."""
        meeting_prep.generate_briefing(sample_event)
        
        stats = meeting_prep.get_stats()
        
        assert stats["total_briefings_generated"] == 1


# =============================================================================
# SenseiVirtualAssistant Tests
# =============================================================================

class TestSenseiVirtualAssistant:
    """Tests for SenseiVirtualAssistant."""
    
    def test_setup_sla_monitoring(self, virtual_assistant, sample_deadline):
        """Test setting up SLA monitoring."""
        virtual_assistant.setup_sla_monitoring([sample_deadline])
        
        assert len(virtual_assistant.sla_watchdog._deadlines) == 1
    
    def test_get_critical_alerts(self, virtual_assistant, now):
        """Test getting critical alerts."""
        deadline = SLADeadline(
            item_id="CRITICAL",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=5),
            description="Test",
            owner_id="user",
        )
        virtual_assistant.setup_sla_monitoring([deadline])
        
        alerts = virtual_assistant.get_critical_alerts()
        
        assert len(alerts) == 1
    
    def test_prepare_for_meeting(self, virtual_assistant, sample_event):
        """Test preparing for meeting."""
        briefing = virtual_assistant.prepare_for_meeting(sample_event)
        
        assert isinstance(briefing, BriefingNote)
    
    def test_stop_monitoring(self, virtual_assistant):
        """Test stopping monitoring."""
        virtual_assistant.sla_watchdog._is_running = True
        
        virtual_assistant.stop_monitoring()
        
        assert virtual_assistant.sla_watchdog._is_running is False
    
    def test_get_stats(self, virtual_assistant, sample_deadline, sample_event):
        """Test getting combined stats."""
        virtual_assistant.setup_sla_monitoring([sample_deadline])
        virtual_assistant.prepare_for_meeting(sample_event)
        
        stats = virtual_assistant.get_stats()
        
        assert "sla_watchdog" in stats
        assert "meeting_prep" in stats


# =============================================================================
# Data Model Tests
# =============================================================================

class TestDataModels:
    """Tests for data models."""
    
    def test_time_to_failure_hours_remaining(self):
        """Test TimeToFailure hours_remaining property."""
        ttf = TimeToFailure(
            item_id="test",
            item_type=ItemType.RFQ,
            deadline=datetime.now(timezone.utc) + timedelta(hours=5),
            time_remaining=timedelta(hours=5),
            status=SLAStatus.CRITICAL,
            risk_score=0.9,
        )
        
        assert ttf.hours_remaining == 5.0
    
    def test_time_to_failure_on_track(self):
        """Test TimeToFailure is_on_track property."""
        now = datetime.now(timezone.utc)
        
        ttf = TimeToFailure(
            item_id="test",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=10),
            time_remaining=timedelta(hours=10),
            status=SLAStatus.OK,
            risk_score=0.3,
            estimated_completion=now + timedelta(hours=5),  # Before deadline
        )
        
        assert ttf.is_on_track is True
    
    def test_notification_creation(self):
        """Test Notification creation."""
        notification = Notification(
            notification_id="test",
            recipient_id="user_001",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        assert notification.sent_at is None
        assert notification.created_at is not None
    
    def test_briefing_note_to_markdown(self):
        """Test BriefingNote to_markdown."""
        briefing = BriefingNote(
            briefing_id="test",
            meeting_id="evt",
            title="Test Briefing",
            generated_at=datetime.now(timezone.utc),
            items=[
                BriefingItem(
                    section=BriefingSection.EXECUTIVE_SUMMARY,
                    title="",
                    content="Test summary",
                    priority=100,
                ),
            ],
        )
        
        markdown = briefing.to_markdown()
        
        assert "# Test Briefing" in markdown
        assert "Test summary" in markdown


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enums."""
    
    def test_sla_status_values(self):
        """Test SLAStatus enum values."""
        assert SLAStatus.OK.value == "ok"
        assert SLAStatus.BREACHED.value == "breached"
    
    def test_item_type_values(self):
        """Test ItemType enum values."""
        assert ItemType.RFQ.value == "rfq"
        assert ItemType.ORDER.value == "order"
    
    def test_notification_type_values(self):
        """Test NotificationType enum values."""
        assert NotificationType.EMAIL.value == "email"
        assert NotificationType.PUSH.value == "push"
    
    def test_entity_category_values(self):
        """Test EntityCategory enum values."""
        assert EntityCategory.CUSTOMER.value == "customer"
        assert EntityCategory.RFQ.value == "rfq"


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_virtual_assistant(self):
        """Test creating virtual assistant."""
        assistant = create_virtual_assistant(sla_check_interval=120)
        
        assert isinstance(assistant, SenseiVirtualAssistant)
        assert assistant.sla_watchdog.check_interval == 120
    
    def test_create_with_callback(self):
        """Test creating with notification callback."""
        callback = Mock()
        
        assistant = create_virtual_assistant(notification_callback=callback)
        
        assert assistant.sla_watchdog.notification_callback is callback


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(self, now):
        """Test full workflow from deadline to notification."""
        notifications_sent = []
        
        def callback(n):
            notifications_sent.append(n)
        
        assistant = create_virtual_assistant(notification_callback=callback)
        
        # Set up monitoring
        deadline = SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=5),
            description="Urgent RFQ",
            owner_id="user_001",
        )
        assistant.setup_sla_monitoring([deadline])
        
        # Check for critical items
        alerts = assistant.get_critical_alerts()
        
        assert len(alerts) == 1
        assert alerts[0].status == SLAStatus.CRITICAL
    
    def test_meeting_prep_workflow(self, now):
        """Test meeting preparation workflow."""
        assistant = create_virtual_assistant()
        
        # Register known entities
        assistant.meeting_prep.register_known_entities(
            EntityCategory.CUSTOMER,
            [("Acme Corp", "cust_001")],
        )
        
        # Create event
        event = CalendarEvent(
            event_id="evt",
            title="Meeting with Acme Corp about RFQ#999",
            description="Quarterly review",
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
            attendees=["john@acme.com"],
        )
        
        # Generate briefing
        briefing = assistant.prepare_for_meeting(event)
        
        assert briefing is not None
        assert len(briefing.extracted_entities) > 0
    
    @pytest.mark.asyncio
    async def test_check_cycle_with_notifications(self, now):
        """Test check cycle generates notifications."""
        notifications = []
        
        def callback(n):
            notifications.append(n)
        
        assistant = create_virtual_assistant(notification_callback=callback)
        
        # Add critical deadline
        deadline = SLADeadline(
            item_id="RFQ-001",
            item_type=ItemType.RFQ,
            deadline=now + timedelta(hours=3),
            description="Critical",
            owner_id="user",
        )
        assistant.setup_sla_monitoring([deadline])
        
        # Run check cycle
        recipient_ids = {
            "gm": ["gm_001"],
            "sales_manager": ["sm_001"],
        }
        
        sent = await assistant.sla_watchdog.run_check_cycle(recipient_ids)
        
        assert len(sent) > 0
        assert len(notifications) > 0
