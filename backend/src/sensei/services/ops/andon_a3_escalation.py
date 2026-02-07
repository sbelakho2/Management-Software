"""
Andon A3 Auto-Escalation Service.

Automatically escalates recurring Andon events to A3 problem-solving documents.

Key features:
- Track recurrence: Same station_id + andon_type + symptom pattern
- Threshold: 3 occurrences within 7 days triggers A3 creation
- A3 auto-populated with: problem statement from symptom, affected station/product, occurrence dates
- Link all related Andon events to A3
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Callable
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class RecurrencePatternType(str, Enum):
    """Type of recurrence pattern to match."""
    
    STATION_TYPE_SYMPTOM = "station_type_symptom"  # station_id + andon_type + symptom
    STATION_TYPE = "station_type"  # station_id + andon_type
    SYMPTOM_ONLY = "symptom"  # Just symptom matching
    PRODUCT_TYPE = "product_type"  # product_id + andon_type


class A3EscalationReason(str, Enum):
    """Reason for escalating to A3."""
    
    RECURRENCE_THRESHOLD = "recurrence_threshold"  # Exceeded occurrence threshold
    SEVERITY_CRITICAL = "severity_critical"  # Critical severity triggered
    MANUAL_ESCALATION = "manual_escalation"  # User manually escalated
    DOWNTIME_THRESHOLD = "downtime_threshold"  # Cumulative downtime exceeded
    COST_THRESHOLD = "cost_threshold"  # Cumulative cost impact exceeded


class A3EscalationStatus(str, Enum):
    """Status of an A3 escalation."""
    
    PENDING = "pending"  # A3 should be created
    A3_CREATED = "a3_created"  # A3 was created
    A3_LINKED = "a3_linked"  # Andon events linked to existing A3
    SKIPPED = "skipped"  # Pattern skipped (e.g., already has A3)


@dataclass
class RecurrencePattern:
    """
    Represents a recurrence pattern for Andon events.
    
    Used to detect recurring issues that should escalate to A3.
    """
    
    pattern_type: RecurrencePatternType
    station_id: int | None = None
    station_name: str | None = None
    andon_type: str | None = None
    symptom: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    
    # Matching events
    event_ids: list[int] = field(default_factory=list)
    event_count: int = 0
    first_occurrence: datetime | None = None
    last_occurrence: datetime | None = None
    
    # Impact aggregates
    total_downtime_minutes: int = 0
    total_cost_impact: float = 0.0
    
    # Escalation
    should_escalate: bool = False
    escalation_reason: A3EscalationReason | None = None
    existing_a3_id: UUID | None = None


@dataclass
class RecurrenceThresholds:
    """Configurable thresholds for recurrence detection."""
    
    # Number of occurrences to trigger escalation
    occurrence_count: int = 3
    
    # Time window for counting occurrences (days)
    time_window_days: int = 7
    
    # Downtime threshold (minutes) for immediate escalation
    downtime_threshold_minutes: int = 480  # 8 hours
    
    # Cost threshold for immediate escalation
    cost_threshold: float = 10000.0


@dataclass
class A3Template:
    """Template for auto-creating A3 from recurring Andon events."""
    
    title: str
    problem_statement: str
    background: str
    current_condition: str
    goal: str
    author_id: UUID | None = None
    department: str | None = None
    area: str | None = None
    priority: str = "high"
    related_andon_ids: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class EscalationResult:
    """Result of auto-escalation check."""
    
    patterns_detected: list[RecurrencePattern]
    patterns_to_escalate: list[RecurrencePattern]
    a3s_to_create: list[A3Template]
    total_patterns: int = 0
    escalation_count: int = 0
    analysis_window_start: datetime | None = None
    analysis_window_end: datetime | None = None


class AndonA3EscalationService:
    """
    Service for auto-escalating recurring Andon events to A3.
    
    Key responsibilities:
    - Detect recurring Andon patterns
    - Apply threshold rules
    - Generate A3 templates
    - Track escalation history
    """
    
    def __init__(self):
        """Initialize the service with default thresholds."""
        self._thresholds = RecurrenceThresholds()
    
    def get_thresholds(self) -> RecurrenceThresholds:
        """Get current threshold configuration."""
        return self._thresholds
    
    def set_thresholds(
        self,
        occurrence_count: int | None = None,
        time_window_days: int | None = None,
        downtime_threshold_minutes: int | None = None,
        cost_threshold: float | None = None,
    ) -> RecurrenceThresholds:
        """
        Update threshold configuration.
        
        Args:
            occurrence_count: Number of occurrences to trigger escalation
            time_window_days: Time window for counting occurrences
            downtime_threshold_minutes: Downtime threshold for immediate escalation
            cost_threshold: Cost threshold for immediate escalation
            
        Returns:
            Updated thresholds
        """
        if occurrence_count is not None:
            self._thresholds.occurrence_count = occurrence_count
        if time_window_days is not None:
            self._thresholds.time_window_days = time_window_days
        if downtime_threshold_minutes is not None:
            self._thresholds.downtime_threshold_minutes = downtime_threshold_minutes
        if cost_threshold is not None:
            self._thresholds.cost_threshold = cost_threshold
        return self._thresholds
    
    def detect_recurrence_patterns(
        self,
        andon_events: list[dict[str, Any]],
        pattern_type: RecurrencePatternType = RecurrencePatternType.STATION_TYPE_SYMPTOM,
        reference_date: datetime | None = None,
        include_resolved: bool = True,
    ) -> list[RecurrencePattern]:
        """
        Detect recurrence patterns in Andon events.
        
        Groups events by pattern type and identifies recurring issues.
        
        Args:
            andon_events: List of Andon event dicts
            pattern_type: Type of pattern to match
            reference_date: Reference date for time window calculation
            include_resolved: Include resolved events in pattern detection
            
        Returns:
            List of detected patterns
        """
        ref_date = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)
        window_start = ref_date - timedelta(days=self._thresholds.time_window_days)
        
        # Filter events within time window
        filtered_events = [
            e for e in andon_events
            if self._get_event_datetime(e) >= window_start
        ]
        
        if not include_resolved:
            filtered_events = [
                e for e in filtered_events
                if e.get("status") != "resolved"
            ]
        
        # Group by pattern
        pattern_map: dict[str, RecurrencePattern] = {}
        
        for event in filtered_events:
            pattern_key = self._generate_pattern_key(event, pattern_type)
            
            if pattern_key not in pattern_map:
                pattern_map[pattern_key] = self._create_pattern(event, pattern_type)
            
            pattern = pattern_map[pattern_key]
            self._add_event_to_pattern(event, pattern)
        
        patterns = list(pattern_map.values())
        
        # Mark patterns for escalation
        for pattern in patterns:
            self._evaluate_escalation(pattern)
        
        return patterns
    
    def check_for_escalations(
        self,
        andon_events: list[dict[str, Any]],
        stations: list[dict[str, Any]] | None = None,
        products: list[dict[str, Any]] | None = None,
        existing_a3s: list[dict[str, Any]] | None = None,
        reference_date: datetime | None = None,
    ) -> EscalationResult:
        """
        Check Andon events for patterns requiring A3 escalation.
        
        This is the main entry point for the auto-escalation workflow.
        
        Args:
            andon_events: List of Andon event dicts
            stations: Station lookup data
            products: Product lookup data
            existing_a3s: Existing A3s to check for duplicates
            reference_date: Reference date for analysis
            
        Returns:
            EscalationResult with patterns and A3 templates
        """
        ref_date = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)
        window_start = ref_date - timedelta(days=self._thresholds.time_window_days)
        
        # Build lookup maps
        station_map = {s["id"]: s for s in (stations or [])}
        product_map = {p["id"]: p for p in (products or [])}
        
        # Detect patterns using the default pattern type
        patterns = self.detect_recurrence_patterns(
            andon_events=andon_events,
            pattern_type=RecurrencePatternType.STATION_TYPE_SYMPTOM,
            reference_date=ref_date,
        )
        
        # Enrich patterns with names
        for pattern in patterns:
            if pattern.station_id and pattern.station_id in station_map:
                pattern.station_name = station_map[pattern.station_id].get("name")
            if pattern.product_id and pattern.product_id in product_map:
                pattern.product_name = product_map[pattern.product_id].get("name")
        
        # Check for existing A3s
        if existing_a3s:
            self._check_existing_a3s(patterns, existing_a3s, andon_events)
        
        # Filter to patterns requiring escalation
        patterns_to_escalate = [p for p in patterns if p.should_escalate]
        
        # Generate A3 templates
        a3_templates = [
            self._generate_a3_template(pattern)
            for pattern in patterns_to_escalate
            if pattern.existing_a3_id is None  # Only create if no existing A3
        ]
        
        return EscalationResult(
            patterns_detected=patterns,
            patterns_to_escalate=patterns_to_escalate,
            a3s_to_create=a3_templates,
            total_patterns=len(patterns),
            escalation_count=len(patterns_to_escalate),
            analysis_window_start=window_start,
            analysis_window_end=ref_date,
        )
    
    def generate_a3_for_pattern(
        self,
        pattern: RecurrencePattern,
        author_id: UUID | None = None,
    ) -> A3Template:
        """
        Generate an A3 template for a recurrence pattern.
        
        Args:
            pattern: The pattern to generate A3 for
            author_id: Optional author ID for the A3
            
        Returns:
            A3Template ready for creation
        """
        template = self._generate_a3_template(pattern)
        if author_id:
            template.author_id = author_id
        return template
    
    def link_events_to_a3(
        self,
        event_ids: list[int],
        a3_id: UUID,
        andon_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Link Andon events to an A3 document.
        
        Returns updated event dicts with escalated_to_a3_id set.
        
        Args:
            event_ids: IDs of events to link
            a3_id: A3 document ID to link to
            andon_events: Full list of Andon events
            
        Returns:
            List of updated event dicts
        """
        updated_events = []
        for event in andon_events:
            if event.get("id") in event_ids:
                updated = dict(event)
                updated["escalated_to_a3_id"] = str(a3_id)
                updated["status"] = "escalated"
                updated["is_recurrence"] = True
                updated["recurrence_count"] = len(event_ids)
                updated_events.append(updated)
        return updated_events
    
    def get_pattern_summary(
        self,
        andon_events: list[dict[str, Any]],
        reference_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get a summary of recurrence patterns for dashboard display.
        
        Args:
            andon_events: List of Andon events
            reference_date: Reference date for analysis
            
        Returns:
            Summary dict with pattern statistics
        """
        patterns = self.detect_recurrence_patterns(
            andon_events=andon_events,
            reference_date=reference_date,
        )
        
        total = len(patterns)
        requiring_escalation = sum(1 for p in patterns if p.should_escalate)
        already_escalated = sum(1 for p in patterns if p.existing_a3_id is not None)
        
        # Group by reason
        by_reason: dict[str, int] = {}
        for pattern in patterns:
            if pattern.escalation_reason:
                reason = pattern.escalation_reason.value
                by_reason[reason] = by_reason.get(reason, 0) + 1
        
        # Most recurring patterns
        top_patterns = sorted(patterns, key=lambda p: p.event_count, reverse=True)[:5]
        
        return {
            "total_patterns": total,
            "requiring_escalation": requiring_escalation,
            "already_escalated": already_escalated,
            "pending_escalation": requiring_escalation - already_escalated,
            "by_reason": by_reason,
            "top_recurring": [
                {
                    "station_id": p.station_id,
                    "station_name": p.station_name,
                    "andon_type": p.andon_type,
                    "symptom": p.symptom,
                    "event_count": p.event_count,
                    "should_escalate": p.should_escalate,
                }
                for p in top_patterns
            ],
            "thresholds": {
                "occurrence_count": self._thresholds.occurrence_count,
                "time_window_days": self._thresholds.time_window_days,
                "downtime_threshold_minutes": self._thresholds.downtime_threshold_minutes,
                "cost_threshold": self._thresholds.cost_threshold,
            },
        }
    
    # --------------------------------------------------------------------------
    # Private Methods
    # --------------------------------------------------------------------------
    
    def _get_event_datetime(self, event: dict[str, Any]) -> datetime:
        """Extract datetime from event."""
        dt = event.get("reported_at") or event.get("created_at")
        if isinstance(dt, str):
            # Try to parse ISO format
            try:
                return datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning("Invalid event datetime: %s", dt)
                return datetime.min
        if isinstance(dt, datetime):
            return dt
        return datetime.min
    
    def _generate_pattern_key(
        self,
        event: dict[str, Any],
        pattern_type: RecurrencePatternType,
    ) -> str:
        """Generate a unique key for a pattern."""
        parts = []
        
        if pattern_type == RecurrencePatternType.STATION_TYPE_SYMPTOM:
            parts = [
                str(event.get("station_id", "")),
                str(event.get("andon_type", "")),
                str(event.get("symptom", "")).lower().strip(),
            ]
        elif pattern_type == RecurrencePatternType.STATION_TYPE:
            parts = [
                str(event.get("station_id", "")),
                str(event.get("andon_type", "")),
            ]
        elif pattern_type == RecurrencePatternType.SYMPTOM_ONLY:
            parts = [str(event.get("symptom", "")).lower().strip()]
        elif pattern_type == RecurrencePatternType.PRODUCT_TYPE:
            parts = [
                str(event.get("product_id", "")),
                str(event.get("andon_type", "")),
            ]
        
        return "::".join(parts)
    
    def _create_pattern(
        self,
        event: dict[str, Any],
        pattern_type: RecurrencePatternType,
    ) -> RecurrencePattern:
        """Create a new pattern from an event."""
        return RecurrencePattern(
            pattern_type=pattern_type,
            station_id=event.get("station_id"),
            andon_type=event.get("andon_type"),
            symptom=event.get("symptom"),
            product_id=event.get("product_id"),
        )
    
    def _add_event_to_pattern(
        self,
        event: dict[str, Any],
        pattern: RecurrencePattern,
    ) -> None:
        """Add an event to a pattern, updating aggregates."""
        event_id = event.get("id")
        if event_id and event_id not in pattern.event_ids:
            pattern.event_ids.append(event_id)
        pattern.event_count = len(pattern.event_ids)
        
        event_dt = self._get_event_datetime(event)
        if pattern.first_occurrence is None or event_dt < pattern.first_occurrence:
            pattern.first_occurrence = event_dt
        if pattern.last_occurrence is None or event_dt > pattern.last_occurrence:
            pattern.last_occurrence = event_dt
        
        # Aggregate impact
        downtime = event.get("downtime_minutes")
        if downtime:
            pattern.total_downtime_minutes += int(downtime)
        
        cost = event.get("estimated_cost_impact")
        if cost:
            pattern.total_cost_impact += float(cost)
        
        # Check if already linked to A3
        a3_id = event.get("escalated_to_a3_id")
        if a3_id and not pattern.existing_a3_id:
            if isinstance(a3_id, str):
                pattern.existing_a3_id = UUID(a3_id)
            elif isinstance(a3_id, UUID):
                pattern.existing_a3_id = a3_id
    
    def _evaluate_escalation(self, pattern: RecurrencePattern) -> None:
        """Evaluate if a pattern should escalate to A3."""
        # Already escalated
        if pattern.existing_a3_id:
            pattern.should_escalate = False
            return
        
        # Check occurrence threshold
        if pattern.event_count >= self._thresholds.occurrence_count:
            pattern.should_escalate = True
            pattern.escalation_reason = A3EscalationReason.RECURRENCE_THRESHOLD
            return
        
        # Check downtime threshold
        if pattern.total_downtime_minutes >= self._thresholds.downtime_threshold_minutes:
            pattern.should_escalate = True
            pattern.escalation_reason = A3EscalationReason.DOWNTIME_THRESHOLD
            return
        
        # Check cost threshold
        if pattern.total_cost_impact >= self._thresholds.cost_threshold:
            pattern.should_escalate = True
            pattern.escalation_reason = A3EscalationReason.COST_THRESHOLD
            return
        
        pattern.should_escalate = False
    
    def _check_existing_a3s(
        self,
        patterns: list[RecurrencePattern],
        existing_a3s: list[dict[str, Any]],
        andon_events: list[dict[str, Any]],
    ) -> None:
        """Check if patterns are already linked to existing A3s."""
        # Build map of event_id -> a3_id from events
        event_a3_map: dict[int, UUID] = {}
        for event in andon_events:
            a3_id = event.get("escalated_to_a3_id")
            if a3_id:
                event_id = event.get("id")
                if event_id:
                    if isinstance(a3_id, str):
                        event_a3_map[event_id] = UUID(a3_id)
                    elif isinstance(a3_id, UUID):
                        event_a3_map[event_id] = a3_id
        
        # Check each pattern
        for pattern in patterns:
            for event_id in pattern.event_ids:
                if event_id in event_a3_map:
                    pattern.existing_a3_id = event_a3_map[event_id]
                    break
    
    def _generate_a3_template(self, pattern: RecurrencePattern) -> A3Template:
        """Generate an A3 template from a pattern."""
        symptom = pattern.symptom or "Unknown issue"
        andon_type = pattern.andon_type or "Unknown type"
        station_name = pattern.station_name or f"Station {pattern.station_id}"
        
        title = f"Recurring {andon_type.title()} Issue: {symptom[:50]}"
        
        # Generate problem statement
        problem_statement = (
            f"A recurring {andon_type} issue has been identified at {station_name}. "
            f"The symptom '{symptom}' has occurred {pattern.event_count} times "
            f"between {pattern.first_occurrence.strftime('%Y-%m-%d') if pattern.first_occurrence else 'N/A'} "
            f"and {pattern.last_occurrence.strftime('%Y-%m-%d') if pattern.last_occurrence else 'N/A'}."
        )
        
        # Generate background
        background = (
            f"This A3 was automatically generated due to recurring Andon events. "
            f"Pattern: {pattern.pattern_type.value}\n"
            f"Station: {station_name}\n"
            f"Type: {andon_type}\n"
            f"Symptom: {symptom}\n"
            f"Total occurrences: {pattern.event_count}\n"
            f"Total downtime: {pattern.total_downtime_minutes} minutes\n"
            f"Estimated cost impact: ${pattern.total_cost_impact:,.2f}"
        )
        
        # Generate current condition
        current_condition = (
            f"The issue has been occurring repeatedly, causing:\n"
            f"- {pattern.total_downtime_minutes} minutes of cumulative downtime\n"
            f"- ${pattern.total_cost_impact:,.2f} estimated cost impact\n"
            f"- Worker frustration and potential quality risks\n\n"
            f"Related Andon Event IDs: {', '.join(str(id) for id in pattern.event_ids)}"
        )
        
        # Generate goal
        goal = (
            f"Eliminate root cause of recurring {andon_type} issue at {station_name}. "
            f"Target: Zero recurrences within 30 days of countermeasure implementation."
        )
        
        # Determine priority
        priority = "high"
        if pattern.total_downtime_minutes >= 240 or pattern.total_cost_impact >= 5000:
            priority = "critical"
        elif pattern.event_count <= 3:
            priority = "medium"
        
        # Tags
        tags = [
            "auto-escalated",
            f"andon-{andon_type}",
            "recurring-issue",
        ]
        if pattern.station_id:
            tags.append(f"station-{pattern.station_id}")
        
        return A3Template(
            title=title,
            problem_statement=problem_statement,
            background=background,
            current_condition=current_condition,
            goal=goal,
            priority=priority,
            related_andon_ids=pattern.event_ids.copy(),
            tags=tags,
        )


class AndonA3EscalationJobRunner:
    """
    Background job runner for periodic escalation checks.
    
    Integrates with scheduler to run escalation detection.
    """
    
    def __init__(
        self,
        service: AndonA3EscalationService | None = None,
        on_a3_create: Callable[[A3Template], None] | None = None,
        on_events_link: Callable[[list[int], UUID], None] | None = None,
    ):
        """
        Initialize the job runner.
        
        Args:
            service: Escalation service instance
            on_a3_create: Callback when A3 should be created
            on_events_link: Callback when events should be linked to A3
        """
        self.service = service or AndonA3EscalationService()
        self.on_a3_create = on_a3_create
        self.on_events_link = on_events_link
        self._last_run: datetime | None = None
    
    async def run(
        self,
        andon_events: list[dict[str, Any]],
        stations: list[dict[str, Any]] | None = None,
        products: list[dict[str, Any]] | None = None,
        existing_a3s: list[dict[str, Any]] | None = None,
        auto_create: bool = False,
        reference_date: datetime | None = None,
    ) -> EscalationResult:
        """
        Run the escalation check job.
        
        Args:
            andon_events: Current Andon events
            stations: Station lookup data
            products: Product lookup data
            existing_a3s: Existing A3 documents
            auto_create: If True, automatically trigger callbacks
            reference_date: Reference date for analysis (defaults to now)
            
        Returns:
            EscalationResult from analysis
        """
        self._last_run = datetime.now(timezone.utc).replace(tzinfo=None)
        
        result = self.service.check_for_escalations(
            andon_events=andon_events,
            stations=stations,
            products=products,
            existing_a3s=existing_a3s,
            reference_date=reference_date,
        )
        
        if auto_create and self.on_a3_create:
            for template in result.a3s_to_create:
                self.on_a3_create(template)
        
        return result
    
    @property
    def last_run(self) -> datetime | None:
        """Get the last run timestamp."""
        return self._last_run
