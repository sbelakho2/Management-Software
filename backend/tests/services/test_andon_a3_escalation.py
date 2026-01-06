"""
Tests for Andon A3 Auto-Escalation Service.

Tests recurrence detection, threshold evaluation, and A3 generation.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sensei.services.andon_a3_escalation import (
    AndonA3EscalationService,
    AndonA3EscalationJobRunner,
    RecurrencePattern,
    RecurrenceThresholds,
    A3Template,
    RecurrencePatternType,
    A3EscalationReason,
    A3EscalationStatus,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def service() -> AndonA3EscalationService:
    """Create a fresh service instance."""
    return AndonA3EscalationService()


@pytest.fixture
def base_datetime() -> datetime:
    """Base datetime for tests."""
    return datetime(2025, 1, 15, 12, 0, 0)


@pytest.fixture
def sample_events(base_datetime: datetime) -> list[dict]:
    """Create sample Andon events for testing."""
    return [
        # Pattern A: Station 1, QUALITY, "Surface defect" - 3 occurrences (should escalate)
        {
            "id": 1,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Surface defect",
            "status": "resolved",
            "reported_at": base_datetime - timedelta(days=6),
            "downtime_minutes": 30,
            "estimated_cost_impact": 500.0,
        },
        {
            "id": 2,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Surface defect",
            "status": "resolved",
            "reported_at": base_datetime - timedelta(days=4),
            "downtime_minutes": 45,
            "estimated_cost_impact": 750.0,
        },
        {
            "id": 3,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Surface defect",
            "status": "open",
            "reported_at": base_datetime - timedelta(days=1),
            "downtime_minutes": 60,
            "estimated_cost_impact": 1000.0,
        },
        # Pattern B: Station 2, EQUIPMENT, "Motor overheating" - 2 occurrences (should not escalate)
        {
            "id": 4,
            "station_id": 2,
            "andon_type": "equipment",
            "symptom": "Motor overheating",
            "status": "resolved",
            "reported_at": base_datetime - timedelta(days=3),
            "downtime_minutes": 120,
            "estimated_cost_impact": 2000.0,
        },
        {
            "id": 5,
            "station_id": 2,
            "andon_type": "equipment",
            "symptom": "Motor overheating",
            "status": "open",
            "reported_at": base_datetime - timedelta(days=1),
            "downtime_minutes": 90,
            "estimated_cost_impact": 1500.0,
        },
        # Pattern C: Station 3, SAFETY, "Guard missing" - 1 occurrence
        {
            "id": 6,
            "station_id": 3,
            "andon_type": "safety",
            "symptom": "Guard missing",
            "status": "resolved",
            "reported_at": base_datetime - timedelta(days=2),
            "downtime_minutes": 15,
            "estimated_cost_impact": 200.0,
        },
    ]


@pytest.fixture
def high_downtime_events(base_datetime: datetime) -> list[dict]:
    """Events with high downtime that should trigger escalation."""
    return [
        {
            "id": 10,
            "station_id": 5,
            "andon_type": "equipment",
            "symptom": "Major breakdown",
            "status": "resolved",
            "reported_at": base_datetime - timedelta(days=2),
            "downtime_minutes": 300,  # 5 hours
            "estimated_cost_impact": 3000.0,
        },
        {
            "id": 11,
            "station_id": 5,
            "andon_type": "equipment",
            "symptom": "Major breakdown",
            "status": "open",
            "reported_at": base_datetime - timedelta(days=1),
            "downtime_minutes": 240,  # 4 hours
            "estimated_cost_impact": 2000.0,
        },
    ]


@pytest.fixture
def high_cost_events(base_datetime: datetime) -> list[dict]:
    """Events with high cost impact that should trigger escalation."""
    return [
        {
            "id": 20,
            "station_id": 6,
            "andon_type": "quality",
            "symptom": "Batch rejection",
            "status": "resolved",
            "reported_at": base_datetime - timedelta(days=2),
            "downtime_minutes": 30,
            "estimated_cost_impact": 6000.0,
        },
        {
            "id": 21,
            "station_id": 6,
            "andon_type": "quality",
            "symptom": "Batch rejection",
            "status": "open",
            "reported_at": base_datetime - timedelta(days=1),
            "downtime_minutes": 30,
            "estimated_cost_impact": 5000.0,
        },
    ]


@pytest.fixture
def stations() -> list[dict]:
    """Sample station data."""
    return [
        {"id": 1, "name": "CNC Machine 1"},
        {"id": 2, "name": "Assembly Station A"},
        {"id": 3, "name": "Inspection Bay 1"},
        {"id": 5, "name": "Stamping Press"},
        {"id": 6, "name": "Paint Booth"},
    ]


@pytest.fixture
def products() -> list[dict]:
    """Sample product data."""
    return [
        {"id": 100, "name": "Widget A"},
        {"id": 101, "name": "Widget B"},
    ]


# =============================================================================
# Threshold Configuration Tests
# =============================================================================


class TestThresholdConfiguration:
    """Tests for threshold configuration."""
    
    def test_default_thresholds(self, service: AndonA3EscalationService):
        """Test default threshold values."""
        thresholds = service.get_thresholds()
        
        assert thresholds.occurrence_count == 3
        assert thresholds.time_window_days == 7
        assert thresholds.downtime_threshold_minutes == 480
        assert thresholds.cost_threshold == 10000.0
    
    def test_update_occurrence_count(self, service: AndonA3EscalationService):
        """Test updating occurrence count threshold."""
        result = service.set_thresholds(occurrence_count=5)
        
        assert result.occurrence_count == 5
        assert result.time_window_days == 7  # Unchanged
    
    def test_update_time_window(self, service: AndonA3EscalationService):
        """Test updating time window."""
        result = service.set_thresholds(time_window_days=14)
        
        assert result.time_window_days == 14
    
    def test_update_downtime_threshold(self, service: AndonA3EscalationService):
        """Test updating downtime threshold."""
        result = service.set_thresholds(downtime_threshold_minutes=240)
        
        assert result.downtime_threshold_minutes == 240
    
    def test_update_cost_threshold(self, service: AndonA3EscalationService):
        """Test updating cost threshold."""
        result = service.set_thresholds(cost_threshold=5000.0)
        
        assert result.cost_threshold == 5000.0
    
    def test_update_multiple_thresholds(self, service: AndonA3EscalationService):
        """Test updating multiple thresholds at once."""
        result = service.set_thresholds(
            occurrence_count=4,
            time_window_days=10,
            downtime_threshold_minutes=360,
            cost_threshold=8000.0,
        )
        
        assert result.occurrence_count == 4
        assert result.time_window_days == 10
        assert result.downtime_threshold_minutes == 360
        assert result.cost_threshold == 8000.0


# =============================================================================
# Recurrence Pattern Detection Tests
# =============================================================================


class TestRecurrencePatternDetection:
    """Tests for recurrence pattern detection."""
    
    def test_detect_station_type_symptom_pattern(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test detection of station + type + symptom pattern."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=base_datetime,
        )
        
        # Should detect 3 patterns
        assert len(patterns) == 3
        
        # Find the pattern that should escalate (3 occurrences)
        escalating = [p for p in patterns if p.should_escalate]
        assert len(escalating) == 1
        assert escalating[0].station_id == 1
        assert escalating[0].andon_type == "quality"
        assert escalating[0].symptom == "Surface defect"
        assert escalating[0].event_count == 3
    
    def test_detect_station_type_pattern(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test detection of station + type pattern (ignoring symptom)."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE,
            reference_date=base_datetime,
        )
        
        # Should detect 3 patterns (grouped by station + type)
        assert len(patterns) == 3
    
    def test_pattern_aggregates_downtime(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that patterns aggregate downtime correctly."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=base_datetime,
        )
        
        # Pattern A: 30 + 45 + 60 = 135 minutes
        pattern_a = next(p for p in patterns if p.station_id == 1)
        assert pattern_a.total_downtime_minutes == 135
    
    def test_pattern_aggregates_cost(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that patterns aggregate cost correctly."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=base_datetime,
        )
        
        # Pattern A: 500 + 750 + 1000 = 2250
        pattern_a = next(p for p in patterns if p.station_id == 1)
        assert pattern_a.total_cost_impact == 2250.0
    
    def test_pattern_tracks_first_last_occurrence(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that patterns track first and last occurrence."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=base_datetime,
        )
        
        pattern_a = next(p for p in patterns if p.station_id == 1)
        assert pattern_a.first_occurrence == base_datetime - timedelta(days=6)
        assert pattern_a.last_occurrence == base_datetime - timedelta(days=1)
    
    def test_pattern_collects_event_ids(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that patterns collect all event IDs."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=base_datetime,
        )
        
        pattern_a = next(p for p in patterns if p.station_id == 1)
        assert set(pattern_a.event_ids) == {1, 2, 3}
    
    def test_exclude_resolved_events(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test excluding resolved events from pattern detection."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=base_datetime,
            include_resolved=False,
        )
        
        # Pattern A should only have 1 open event now
        pattern_a = next((p for p in patterns if p.station_id == 1), None)
        assert pattern_a is not None
        assert pattern_a.event_count == 1
        assert pattern_a.should_escalate is False
    
    def test_time_window_filtering(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that events outside time window are excluded."""
        # Set a shorter time window
        service.set_thresholds(time_window_days=5)
        
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        # With 5-day window from base_datetime:
        # - Day 1: included (within 5 days)
        # - Day 4: included (within 5 days)
        # - Day 6: excluded (outside 5 days)
        pattern_a = next(p for p in patterns if p.station_id == 1)
        assert pattern_a.event_count == 2


# =============================================================================
# Escalation Evaluation Tests
# =============================================================================


class TestEscalationEvaluation:
    """Tests for escalation threshold evaluation."""
    
    def test_escalate_on_occurrence_count(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test escalation triggered by occurrence count."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        pattern_a = next(p for p in patterns if p.station_id == 1)
        assert pattern_a.should_escalate is True
        assert pattern_a.escalation_reason == A3EscalationReason.RECURRENCE_THRESHOLD
    
    def test_no_escalate_below_threshold(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test no escalation when below occurrence threshold."""
        patterns = service.detect_recurrence_patterns(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        # Pattern B has only 2 occurrences
        pattern_b = next(p for p in patterns if p.station_id == 2)
        assert pattern_b.event_count == 2
        assert pattern_b.should_escalate is False
    
    def test_escalate_on_downtime_threshold(
        self,
        service: AndonA3EscalationService,
        high_downtime_events: list[dict],
        base_datetime: datetime,
    ):
        """Test escalation triggered by cumulative downtime."""
        patterns = service.detect_recurrence_patterns(
            andon_events=high_downtime_events,
            reference_date=base_datetime,
        )
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.total_downtime_minutes == 540  # 300 + 240
        assert pattern.should_escalate is True
        assert pattern.escalation_reason == A3EscalationReason.DOWNTIME_THRESHOLD
    
    def test_escalate_on_cost_threshold(
        self,
        service: AndonA3EscalationService,
        high_cost_events: list[dict],
        base_datetime: datetime,
    ):
        """Test escalation triggered by cumulative cost."""
        patterns = service.detect_recurrence_patterns(
            andon_events=high_cost_events,
            reference_date=base_datetime,
        )
        
        assert len(patterns) == 1
        pattern = patterns[0]
        assert pattern.total_cost_impact == 11000.0  # 6000 + 5000
        assert pattern.should_escalate is True
        assert pattern.escalation_reason == A3EscalationReason.COST_THRESHOLD
    
    def test_occurrence_priority_over_downtime(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test that occurrence count is evaluated before downtime."""
        events = [
            {
                "id": i + 1,
                "station_id": 10,
                "andon_type": "quality",
                "symptom": "Test symptom",
                "status": "open",
                "reported_at": base_datetime - timedelta(hours=i * 8),  # Spread within same day window
                "downtime_minutes": 100,  # Each 100 mins (300 total < 480 threshold)
            }
            for i in range(3)
        ]
        
        patterns = service.detect_recurrence_patterns(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        pattern = patterns[0]
        assert pattern.event_count == 3
        # Occurrence count threshold (3) is evaluated first, triggers before downtime
        assert pattern.escalation_reason == A3EscalationReason.RECURRENCE_THRESHOLD
    
    def test_skip_already_escalated(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test that patterns with existing A3 don't escalate again."""
        a3_id = uuid4()
        events = [
            {
                "id": 1,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                "reported_at": base_datetime - timedelta(days=1),
                "escalated_to_a3_id": str(a3_id),
            },
            {
                "id": 2,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                "reported_at": base_datetime - timedelta(days=2),
            },
            {
                "id": 3,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                "reported_at": base_datetime - timedelta(days=3),
            },
        ]
        
        patterns = service.detect_recurrence_patterns(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        pattern = patterns[0]
        assert pattern.event_count == 3
        assert pattern.existing_a3_id == a3_id
        assert pattern.should_escalate is False  # Already has A3


# =============================================================================
# Check for Escalations (Full Workflow) Tests
# =============================================================================


class TestCheckForEscalations:
    """Tests for the full escalation check workflow."""
    
    def test_check_returns_result(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test that check returns an EscalationResult."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        assert result.total_patterns == 3
        assert result.escalation_count == 1
        assert len(result.patterns_to_escalate) == 1
    
    def test_enriches_station_names(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test that station names are enriched in patterns."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        pattern_a = next(
            p for p in result.patterns_detected 
            if p.station_id == 1
        )
        assert pattern_a.station_name == "CNC Machine 1"
    
    def test_generates_a3_templates(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test that A3 templates are generated for escalating patterns."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        assert len(result.a3s_to_create) == 1
        template = result.a3s_to_create[0]
        assert "Surface defect" in template.title
        assert "CNC Machine 1" in template.problem_statement
    
    def test_no_duplicate_a3_for_existing(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
        stations: list[dict],
    ):
        """Test that no A3 is generated if pattern already has A3."""
        a3_id = uuid4()
        events = [
            {
                "id": i,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                "reported_at": base_datetime - timedelta(days=i),
                "escalated_to_a3_id": str(a3_id) if i == 0 else None,
            }
            for i in range(3)
        ]
        
        result = service.check_for_escalations(
            andon_events=events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        # Pattern exists and should escalate but A3 already exists
        assert result.escalation_count == 0  # Already escalated, no new escalation
        assert len(result.a3s_to_create) == 0
    
    def test_analysis_window(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that analysis window is set correctly."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        assert result.analysis_window_end == base_datetime
        assert result.analysis_window_start == base_datetime - timedelta(days=7)


# =============================================================================
# A3 Template Generation Tests
# =============================================================================


class TestA3TemplateGeneration:
    """Tests for A3 template generation."""
    
    def test_template_title(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template title format."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert "Recurring Quality Issue" in template.title
        assert "Surface defect" in template.title
    
    def test_template_problem_statement(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template problem statement content."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert "CNC Machine 1" in template.problem_statement
        assert "3 times" in template.problem_statement
        assert "quality" in template.problem_statement
    
    def test_template_background(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template background content."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert "automatically generated" in template.background
        assert "135 minutes" in template.background  # Total downtime
        assert "$2,250.00" in template.background  # Total cost
    
    def test_template_current_condition(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template current condition content."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert "Related Andon Event IDs" in template.current_condition
        assert "1" in template.current_condition
        assert "2" in template.current_condition
        assert "3" in template.current_condition
    
    def test_template_goal(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template goal content."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert "Eliminate root cause" in template.goal
        assert "Zero recurrences" in template.goal
    
    def test_template_priority_medium_for_threshold_match(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template priority is medium for exactly 3 occurrences (threshold match)."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        # With 3 occurrences (exactly at threshold) and low impact, priority is medium
        assert template.priority == "medium"
    
    def test_template_priority_critical_for_high_impact(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test A3 template priority is critical for high-impact patterns."""
        events = [
            {
                "id": i + 1,
                "station_id": 1,
                "andon_type": "equipment",
                "symptom": "Major failure",
                "reported_at": base_datetime - timedelta(hours=i * 12),  # Within time window
                "downtime_minutes": 100,  # 300 total
                "estimated_cost_impact": 2000.0,  # 6000 total > 5000 threshold
            }
            for i in range(3)
        ]
        
        result = service.check_for_escalations(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        assert len(result.a3s_to_create) == 1
        template = result.a3s_to_create[0]
        assert template.priority == "critical"
    
    def test_template_tags(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template includes proper tags."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert "auto-escalated" in template.tags
        assert "andon-quality" in template.tags
        assert "recurring-issue" in template.tags
        assert "station-1" in template.tags
    
    def test_template_related_andon_ids(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test A3 template includes related Andon event IDs."""
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        template = result.a3s_to_create[0]
        assert set(template.related_andon_ids) == {1, 2, 3}
    
    def test_generate_a3_for_pattern_with_author(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test generating A3 template with specific author."""
        author_id = uuid4()
        
        result = service.check_for_escalations(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        pattern = result.patterns_to_escalate[0]
        template = service.generate_a3_for_pattern(pattern, author_id=author_id)
        
        assert template.author_id == author_id


# =============================================================================
# Link Events to A3 Tests
# =============================================================================


class TestLinkEventsToA3:
    """Tests for linking Andon events to A3."""
    
    def test_link_events_returns_updated(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
    ):
        """Test that linking returns updated events."""
        a3_id = uuid4()
        event_ids = [1, 2, 3]
        
        updated = service.link_events_to_a3(
            event_ids=event_ids,
            a3_id=a3_id,
            andon_events=sample_events,
        )
        
        assert len(updated) == 3
    
    def test_link_sets_a3_id(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
    ):
        """Test that linking sets escalated_to_a3_id."""
        a3_id = uuid4()
        event_ids = [1, 2]
        
        updated = service.link_events_to_a3(
            event_ids=event_ids,
            a3_id=a3_id,
            andon_events=sample_events,
        )
        
        for event in updated:
            assert event["escalated_to_a3_id"] == str(a3_id)
    
    def test_link_sets_status_escalated(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
    ):
        """Test that linking sets status to escalated."""
        a3_id = uuid4()
        event_ids = [1]
        
        updated = service.link_events_to_a3(
            event_ids=event_ids,
            a3_id=a3_id,
            andon_events=sample_events,
        )
        
        assert updated[0]["status"] == "escalated"
    
    def test_link_sets_recurrence_flag(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
    ):
        """Test that linking sets is_recurrence flag."""
        a3_id = uuid4()
        event_ids = [1, 2, 3]
        
        updated = service.link_events_to_a3(
            event_ids=event_ids,
            a3_id=a3_id,
            andon_events=sample_events,
        )
        
        for event in updated:
            assert event["is_recurrence"] is True
            assert event["recurrence_count"] == 3
    
    def test_link_only_specified_events(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
    ):
        """Test that only specified events are updated."""
        a3_id = uuid4()
        event_ids = [1, 2]  # Not event 3
        
        updated = service.link_events_to_a3(
            event_ids=event_ids,
            a3_id=a3_id,
            andon_events=sample_events,
        )
        
        updated_ids = [e["id"] for e in updated]
        assert 3 not in updated_ids


# =============================================================================
# Pattern Summary Tests
# =============================================================================


class TestPatternSummary:
    """Tests for pattern summary generation."""
    
    def test_summary_counts(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test summary provides correct counts."""
        summary = service.get_pattern_summary(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        assert summary["total_patterns"] == 3
        assert summary["requiring_escalation"] == 1
    
    def test_summary_by_reason(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test summary groups by escalation reason."""
        summary = service.get_pattern_summary(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        assert "recurrence_threshold" in summary["by_reason"]
        assert summary["by_reason"]["recurrence_threshold"] == 1
    
    def test_summary_top_recurring(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test summary includes top recurring patterns."""
        summary = service.get_pattern_summary(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        assert len(summary["top_recurring"]) > 0
        top = summary["top_recurring"][0]
        assert top["event_count"] == 3  # Highest count first
        assert top["station_id"] == 1
    
    def test_summary_includes_thresholds(
        self,
        service: AndonA3EscalationService,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test summary includes current thresholds."""
        summary = service.get_pattern_summary(
            andon_events=sample_events,
            reference_date=base_datetime,
        )
        
        assert "thresholds" in summary
        assert summary["thresholds"]["occurrence_count"] == 3
        assert summary["thresholds"]["time_window_days"] == 7


# =============================================================================
# Job Runner Tests
# =============================================================================


class TestAndonA3EscalationJobRunner:
    """Tests for the background job runner."""
    
    @pytest.mark.asyncio
    async def test_run_returns_result(
        self,
        sample_events: list[dict],
        stations: list[dict],
        base_datetime: datetime,
    ):
        """Test that job run returns escalation result."""
        runner = AndonA3EscalationJobRunner()
        
        result = await runner.run(
            andon_events=sample_events,
            stations=stations,
            reference_date=base_datetime,
        )
        
        assert result.total_patterns == 3
        assert result.escalation_count == 1
    
    @pytest.mark.asyncio
    async def test_run_tracks_last_run(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that job tracks last run time."""
        runner = AndonA3EscalationJobRunner()
        
        assert runner.last_run is None
        
        await runner.run(andon_events=sample_events, reference_date=base_datetime)
        
        assert runner.last_run is not None
    
    @pytest.mark.asyncio
    async def test_run_with_callback(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that job invokes callback for A3 creation."""
        created_a3s = []
        
        def on_a3_create(template: A3Template):
            created_a3s.append(template)
        
        runner = AndonA3EscalationJobRunner(on_a3_create=on_a3_create)
        
        await runner.run(
            andon_events=sample_events,
            auto_create=True,
            reference_date=base_datetime,
        )
        
        assert len(created_a3s) == 1
        assert "Surface defect" in created_a3s[0].title
    
    @pytest.mark.asyncio
    async def test_run_no_callback_without_auto_create(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that callbacks are not invoked without auto_create."""
        created_a3s = []
        
        def on_a3_create(template: A3Template):
            created_a3s.append(template)
        
        runner = AndonA3EscalationJobRunner(on_a3_create=on_a3_create)
        
        await runner.run(
            andon_events=sample_events,
            auto_create=False,
            reference_date=base_datetime,
        )
        
        assert len(created_a3s) == 0
    
    @pytest.mark.asyncio
    async def test_runner_uses_custom_service(
        self,
        sample_events: list[dict],
        base_datetime: datetime,
    ):
        """Test that runner can use custom service instance."""
        custom_service = AndonA3EscalationService()
        custom_service.set_thresholds(occurrence_count=5)  # Higher threshold
        
        runner = AndonA3EscalationJobRunner(service=custom_service)
        
        result = await runner.run(andon_events=sample_events, reference_date=base_datetime)
        
        # With threshold of 5, no patterns should escalate
        assert result.escalation_count == 0


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_events_list(self, service: AndonA3EscalationService):
        """Test with empty events list."""
        result = service.check_for_escalations(andon_events=[])
        
        assert result.total_patterns == 0
        assert result.escalation_count == 0
        assert len(result.a3s_to_create) == 0
    
    def test_single_event(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test with single event."""
        events = [{
            "id": 1,
            "station_id": 1,
            "andon_type": "quality",
            "symptom": "Test",
            "reported_at": base_datetime,
        }]
        
        result = service.check_for_escalations(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        assert result.total_patterns == 1
        assert result.escalation_count == 0
    
    def test_missing_optional_fields(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test with events missing optional fields."""
        events = [
            {
                "id": i + 1,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                "reported_at": base_datetime - timedelta(hours=i * 12),
                # No downtime_minutes or estimated_cost_impact
            }
            for i in range(3)
        ]
        
        result = service.check_for_escalations(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        assert result.escalation_count == 1
        pattern = result.patterns_to_escalate[0]
        assert pattern.total_downtime_minutes == 0
        assert pattern.total_cost_impact == 0.0
    
    def test_null_symptom(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test with null symptom."""
        events = [
            {
                "id": i + 1,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": None,
                "reported_at": base_datetime - timedelta(hours=i * 12),
            }
            for i in range(3)
        ]
        
        result = service.check_for_escalations(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        assert result.total_patterns == 1
        template = result.a3s_to_create[0]
        assert "Unknown issue" in template.problem_statement
    
    def test_iso_string_datetime(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test with ISO string datetime format."""
        events = [
            {
                "id": i + 1,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                # Use naive datetime format (no Z or timezone)
                "reported_at": (base_datetime - timedelta(hours=i * 12)).isoformat(),
            }
            for i in range(3)
        ]
        
        result = service.check_for_escalations(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        assert result.total_patterns == 1
        assert result.escalation_count == 1
    
    def test_uuid_as_string_a3_id(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test with UUID as string for escalated_to_a3_id."""
        a3_id = uuid4()
        events = [
            {
                "id": 1,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Test",
                "reported_at": base_datetime,
                "escalated_to_a3_id": str(a3_id),
            },
        ]
        
        patterns = service.detect_recurrence_patterns(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        assert patterns[0].existing_a3_id == a3_id
    
    def test_case_insensitive_symptom_matching(
        self,
        service: AndonA3EscalationService,
        base_datetime: datetime,
    ):
        """Test that symptom matching is case-insensitive."""
        events = [
            {
                "id": 1,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "Surface Defect",
                "reported_at": base_datetime - timedelta(hours=12),
            },
            {
                "id": 2,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "surface defect",
                "reported_at": base_datetime - timedelta(hours=24),
            },
            {
                "id": 3,
                "station_id": 1,
                "andon_type": "quality",
                "symptom": "SURFACE DEFECT",
                "reported_at": base_datetime - timedelta(hours=36),
            },
        ]
        
        patterns = service.detect_recurrence_patterns(
            andon_events=events,
            reference_date=base_datetime,
        )
        
        # All should match to same pattern
        assert len(patterns) == 1
        assert patterns[0].event_count == 3
