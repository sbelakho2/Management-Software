"""
Tests for Andon System models.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from sensei.models.andon import (
    AndonEvent,
    AndonType,
    AndonSeverity,
    AndonStatus,
    EscalationLevel,
    ResponseStatus,
    AndonEscalation,
    AndonRecurrencePattern,
)


class TestAndonEventModel:
    """Test cases for AndonEvent model."""

    def test_andon_event_creation_basic(self):
        """Test basic Andon event creation."""
        event = AndonEvent(
            event_number="AND-001",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Dimension out of spec",
            reported_by_id=1,
            status=AndonStatus.OPEN,
            escalation_level=EscalationLevel.NONE,
        )

        assert event.event_number == "AND-001"
        assert event.andon_type == AndonType.QUALITY
        assert event.severity == AndonSeverity.YELLOW
        assert event.status == AndonStatus.OPEN
        assert event.escalation_level == EscalationLevel.NONE

    def test_andon_event_creation_full(self):
        """Test Andon event creation with all fields."""
        event = AndonEvent(
            event_number="AND-002",
            andon_type=AndonType.EQUIPMENT,
            severity=AndonSeverity.RED,
            station_id=1,
            product_id=5,
            work_order_id=10,
            symptom="Machine stopped",
            description="CNC spindle overheating",
            affected_quantity=50,
            status=AndonStatus.ACKNOWLEDGED,
            reported_by_id=1,
            downtime_minutes=30,
            estimated_cost_impact=Decimal("500.00"),
            is_recurrence=True,
            recurrence_count=3,
        )

        assert event.andon_type == AndonType.EQUIPMENT
        assert event.severity == AndonSeverity.RED
        assert event.symptom == "Machine stopped"
        assert event.affected_quantity == 50
        assert event.downtime_minutes == 30
        assert event.is_recurrence is True
        assert event.recurrence_count == 3

    def test_andon_type_values(self):
        """Test all valid Andon type values."""
        for atype in AndonType:
            event = AndonEvent(
                event_number=f"AND-{atype.value}",
                andon_type=atype,
                severity=AndonSeverity.YELLOW,
                station_id=1,
                symptom=f"Test {atype.value}",
                reported_by_id=1,
            )
            assert event.andon_type == atype

    def test_andon_severity_values(self):
        """Test all valid severity values."""
        for severity in AndonSeverity:
            event = AndonEvent(
                event_number=f"AND-{severity.value}",
                andon_type=AndonType.QUALITY,
                severity=severity,
                station_id=1,
                symptom=f"Test {severity.value}",
                reported_by_id=1,
            )
            assert event.severity == severity

    def test_andon_status_values(self):
        """Test all valid status values."""
        for status in AndonStatus:
            event = AndonEvent(
                event_number=f"AND-{status.value}",
                andon_type=AndonType.QUALITY,
                severity=AndonSeverity.YELLOW,
                station_id=1,
                symptom=f"Test {status.value}",
                reported_by_id=1,
                status=status,
            )
            assert event.status == status

    def test_andon_is_open(self):
        """Test is_open property."""
        event_open = AndonEvent(
            event_number="AND-OPEN",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Open event",
            reported_by_id=1,
            status=AndonStatus.OPEN,
        )

        event_resolved = AndonEvent(
            event_number="AND-RESOLVED",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Resolved event",
            reported_by_id=1,
            status=AndonStatus.RESOLVED,
        )

        assert event_open.is_open is True
        assert event_resolved.is_open is False

    def test_andon_is_critical(self):
        """Test is_critical property."""
        event_red = AndonEvent(
            event_number="AND-RED",
            andon_type=AndonType.SAFETY,
            severity=AndonSeverity.RED,
            station_id=1,
            symptom="Critical event",
            reported_by_id=1,
        )

        event_yellow = AndonEvent(
            event_number="AND-YELLOW",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Warning event",
            reported_by_id=1,
        )

        assert event_red.is_critical is True
        assert event_yellow.is_critical is False

    def test_andon_response_time(self):
        """Test response time calculation."""
        reported = datetime.utcnow() - timedelta(minutes=10)
        acknowledged = datetime.utcnow()

        event = AndonEvent(
            event_number="AND-RESP",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test response time",
            reported_by_id=1,
            reported_at=reported,
            acknowledged_at=acknowledged,
        )

        response_time = event.response_time_minutes
        assert response_time is not None
        assert 9 <= response_time <= 11

    def test_andon_response_time_no_ack(self):
        """Test response time when not acknowledged."""
        event = AndonEvent(
            event_number="AND-NOACK",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Not acknowledged",
            reported_by_id=1,
            acknowledged_at=None,
        )

        assert event.response_time_minutes is None

    def test_andon_resolution_time(self):
        """Test resolution time calculation."""
        reported = datetime.utcnow() - timedelta(hours=2)
        resolved = datetime.utcnow()

        event = AndonEvent(
            event_number="AND-RES",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test resolution time",
            reported_by_id=1,
            status=AndonStatus.RESOLVED,
            reported_at=reported,
            resolved_at=resolved,
        )

        resolution_time = event.resolution_time_minutes
        assert resolution_time is not None
        assert 115 <= resolution_time <= 125

    def test_andon_elapsed_time(self):
        """Test elapsed time calculation."""
        reported = datetime.utcnow() - timedelta(minutes=30)

        event = AndonEvent(
            event_number="AND-ELAPSED",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test elapsed time",
            reported_by_id=1,
            reported_at=reported,
        )

        elapsed = event.elapsed_time_minutes
        assert 29 <= elapsed <= 31

    def test_andon_repr(self):
        """Test string representation."""
        event = AndonEvent(
            event_number="AND-TEST",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test",
            reported_by_id=1,
        )
        event.id = 1

        assert "AndonEvent" in repr(event)
        assert "AND-TEST" in repr(event)


class TestAndonEscalationModel:
    """Test cases for AndonEscalation model."""

    def test_escalation_creation_basic(self):
        """Test basic escalation creation."""
        escalation = AndonEscalation(
            andon_event_id=1,
            escalation_level=EscalationLevel.LEVEL_1,
            escalated_to_user_id=5,
            response_status=ResponseStatus.PENDING,
        )

        assert escalation.andon_event_id == 1
        assert escalation.escalation_level == EscalationLevel.LEVEL_1
        assert escalation.response_status == ResponseStatus.PENDING

    def test_escalation_level_values(self):
        """Test all escalation level values."""
        for level in EscalationLevel:
            escalation = AndonEscalation(
                andon_event_id=1,
                escalation_level=level,
                escalated_to_user_id=1,
            )
            assert escalation.escalation_level == level

    def test_escalation_response_status_values(self):
        """Test all response status values."""
        for status in ResponseStatus:
            escalation = AndonEscalation(
                andon_event_id=1,
                escalation_level=EscalationLevel.LEVEL_1,
                escalated_to_user_id=1,
                response_status=status,
            )
            assert escalation.response_status == status

    def test_escalation_response_time(self):
        """Test response time calculation."""
        escalated = datetime.utcnow() - timedelta(minutes=15)
        responded = datetime.utcnow()

        escalation = AndonEscalation(
            andon_event_id=1,
            escalation_level=EscalationLevel.LEVEL_1,
            escalated_to_user_id=1,
            escalated_at=escalated,
            responded_at=responded,
            response_status=ResponseStatus.ACKNOWLEDGED,
        )

        response_time = escalation.response_time_minutes
        assert response_time is not None
        assert 14 <= response_time <= 16

    def test_escalation_response_time_pending(self):
        """Test response time when still pending."""
        escalation = AndonEscalation(
            andon_event_id=1,
            escalation_level=EscalationLevel.LEVEL_1,
            escalated_to_user_id=1,
            response_status=ResponseStatus.PENDING,
            responded_at=None,
        )

        assert escalation.response_time_minutes is None

    def test_escalation_delegation(self):
        """Test escalation with delegation."""
        escalation = AndonEscalation(
            andon_event_id=1,
            escalation_level=EscalationLevel.LEVEL_2,
            escalated_to_user_id=5,
            response_status=ResponseStatus.DELEGATED,
            delegated_to_user_id=10,
        )

        assert escalation.response_status == ResponseStatus.DELEGATED
        assert escalation.delegated_to_user_id == 10

    def test_escalation_repr(self):
        """Test string representation."""
        escalation = AndonEscalation(
            andon_event_id=1,
            escalation_level=EscalationLevel.LEVEL_1,
            escalated_to_user_id=1,
        )

        assert "AndonEscalation" in repr(escalation)


class TestAndonRecurrencePatternModel:
    """Test cases for AndonRecurrencePattern model."""

    def test_recurrence_pattern_creation(self):
        """Test recurrence pattern creation."""
        now = datetime.utcnow()

        pattern = AndonRecurrencePattern(
            station_id=1,
            andon_type=AndonType.QUALITY,
            symptom_pattern="Dimension out of spec",
            occurrence_count=3,
            first_occurrence_at=now - timedelta(days=5),
            last_occurrence_at=now,
            window_days=7,
            escalation_threshold=3,
        )

        assert pattern.station_id == 1
        assert pattern.andon_type == AndonType.QUALITY
        assert pattern.occurrence_count == 3
        assert pattern.escalation_threshold == 3

    def test_recurrence_should_escalate(self):
        """Test should_escalate property."""
        now = datetime.utcnow()

        # At threshold, not yet escalated
        pattern_escalate = AndonRecurrencePattern(
            station_id=1,
            andon_type=AndonType.QUALITY,
            symptom_pattern="Test pattern",
            occurrence_count=3,
            first_occurrence_at=now - timedelta(days=5),
            last_occurrence_at=now,
            escalation_threshold=3,
            escalated_to_a3=False,
        )

        # Below threshold
        pattern_below = AndonRecurrencePattern(
            station_id=1,
            andon_type=AndonType.QUALITY,
            symptom_pattern="Test pattern 2",
            occurrence_count=2,
            first_occurrence_at=now - timedelta(days=5),
            last_occurrence_at=now,
            escalation_threshold=3,
            escalated_to_a3=False,
        )

        # Already escalated
        pattern_already = AndonRecurrencePattern(
            station_id=1,
            andon_type=AndonType.QUALITY,
            symptom_pattern="Test pattern 3",
            occurrence_count=5,
            first_occurrence_at=now - timedelta(days=5),
            last_occurrence_at=now,
            escalation_threshold=3,
            escalated_to_a3=True,
        )

        assert pattern_escalate.should_escalate is True
        assert pattern_below.should_escalate is False
        assert pattern_already.should_escalate is False

    def test_recurrence_pattern_repr(self):
        """Test string representation."""
        now = datetime.utcnow()

        pattern = AndonRecurrencePattern(
            station_id=1,
            andon_type=AndonType.QUALITY,
            symptom_pattern="Test",
            occurrence_count=1,
            first_occurrence_at=now,
            last_occurrence_at=now,
        )

        assert "AndonRecurrencePattern" in repr(pattern)


class TestAndonEventRelationships:
    """Test Andon Event relationships."""

    def test_andon_has_escalations_list(self):
        """Test that Andon event has escalations list."""
        event = AndonEvent(
            event_number="AND-001",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test",
            reported_by_id=1,
        )
        assert hasattr(event, 'escalations')

    def test_escalation_references_andon(self):
        """Test that escalation references Andon event."""
        escalation = AndonEscalation(
            andon_event_id=1,
            escalation_level=EscalationLevel.LEVEL_1,
            escalated_to_user_id=1,
        )
        assert escalation.andon_event_id == 1
        assert hasattr(escalation, 'andon_event')


class TestAndonValidation:
    """Test Andon validation constraints."""

    def test_andon_explicit_recurrence_count(self):
        """Test explicit recurrence count is zero."""
        event = AndonEvent(
            event_number="AND-001",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test",
            reported_by_id=1,
            recurrence_count=0,
        )
        assert event.recurrence_count == 0

    def test_andon_explicit_is_recurrence(self):
        """Test explicit is_recurrence is False."""
        event = AndonEvent(
            event_number="AND-001",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Test",
            reported_by_id=1,
            is_recurrence=False,
        )
        assert event.is_recurrence is False


class TestAndonEdgeCases:
    """Test edge cases for Andon model."""

    def test_andon_with_all_null_optionals(self):
        """Test Andon with minimal required fields."""
        event = AndonEvent(
            event_number="AND-MIN",
            andon_type=AndonType.QUALITY,
            severity=AndonSeverity.YELLOW,
            station_id=1,
            symptom="Minimal event",
            reported_by_id=1,
        )

        assert event.product_id is None
        assert event.work_order_id is None
        assert event.description is None
        assert event.photo_attachment_id is None
        assert event.acknowledged_by_id is None
        assert event.resolved_by_id is None

    def test_andon_blue_severity(self):
        """Test blue (material call) severity."""
        event = AndonEvent(
            event_number="AND-BLUE",
            andon_type=AndonType.MATERIAL,
            severity=AndonSeverity.BLUE,
            station_id=1,
            symptom="Material needed",
            reported_by_id=1,
        )

        assert event.severity == AndonSeverity.BLUE
        assert event.is_critical is False

    def test_andon_full_lifecycle(self):
        """Test Andon through full lifecycle."""
        reported = datetime.utcnow() - timedelta(hours=1)
        acknowledged = reported + timedelta(minutes=5)
        resolved = datetime.utcnow()

        event = AndonEvent(
            event_number="AND-LIFECYCLE",
            andon_type=AndonType.EQUIPMENT,
            severity=AndonSeverity.RED,
            station_id=1,
            symptom="Machine breakdown",
            description="Motor failure on spindle",
            reported_by_id=1,
            reported_at=reported,
            acknowledged_by_id=2,
            acknowledged_at=acknowledged,
            resolved_by_id=3,
            resolved_at=resolved,
            resolution_notes="Replaced motor",
            status=AndonStatus.RESOLVED,
            downtime_minutes=55,
        )

        assert event.response_time_minutes == 5
        assert event.resolution_time_minutes == 60
        assert event.is_open is False
