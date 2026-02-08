"""
Deep Semantic Anomaly Detection.

Detects anomalies in business processes using:
- Sequence Modeling: Analyze order of events for unusual patterns
- Sentiment/Urgency Analysis: Detect escalating frustration before Andon events
- Configurable Alert Thresholds: Avoid alarm fatigue
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional, Callable
import math
import re
import hashlib
import uuid
from collections import defaultdict


# =============================================================================
# Constants
# =============================================================================

SEQUENCE_WINDOW_SIZE = 10
SENTIMENT_HISTORY_SIZE = 100  # #233: Increased from 20 for better escalation tracking
MIN_SEQUENCE_LENGTH = 3
ANOMALY_SCORE_THRESHOLD = 0.7
SENTIMENT_ESCALATION_THRESHOLD = 0.3


# =============================================================================
# Enums
# =============================================================================

class AlertSensitivity(Enum):
    """Configurable alert sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnomalyType(Enum):
    """Types of detected anomalies."""
    SEQUENCE = "sequence"  # Unusual event ordering
    TIMING = "timing"  # Unusual delays
    SENTIMENT = "sentiment"  # Negative sentiment escalation
    URGENCY = "urgency"  # Urgency pattern detection
    FREQUENCY = "frequency"  # Unusual event frequency
    MISSING = "missing"  # Expected event missing


class EventType(Enum):
    """Types of process events."""
    RFQ_RECEIVED = "rfq_received"
    QUOTE_CREATED = "quote_created"
    QUOTE_SENT = "quote_sent"
    ORDER_RECEIVED = "order_received"
    PRODUCTION_STARTED = "production_started"
    PRODUCTION_COMPLETED = "production_completed"
    QC_PASSED = "qc_passed"
    QC_FAILED = "qc_failed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CUSTOMER_FEEDBACK = "customer_feedback"
    ANDON_RAISED = "andon_raised"
    ESCALATION = "escalation"
    NOTE_ADDED = "note_added"
    EMAIL_RECEIVED = "email_received"
    EMAIL_SENT = "email_sent"


class SentimentLevel(Enum):
    """Sentiment classification levels."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class UrgencyLevel(Enum):
    """Urgency classification levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ProcessEvent:
    """A single process event."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    entity_id: str  # RFQ, Order, etc.
    entity_type: str
    
    # Optional content for sentiment analysis
    content: str = ""
    
    # Actor info
    actor_id: str = ""
    actor_type: str = ""  # user, system, customer
    
    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    text: str
    sentiment_level: SentimentLevel
    sentiment_score: float  # -1.0 to 1.0
    urgency_level: UrgencyLevel
    urgency_score: float  # 0.0 to 1.0
    
    # Detected patterns
    frustration_indicators: list[str] = field(default_factory=list)
    urgency_indicators: list[str] = field(default_factory=list)
    
    # Flags
    is_escalating: bool = False


@dataclass
class SequencePattern:
    """A learned sequence pattern."""
    pattern_id: str
    event_sequence: list[EventType]
    frequency: int
    avg_duration_seconds: float
    std_duration_seconds: float
    
    # Expected timing between each event
    expected_gaps: list[float] = field(default_factory=list)
    gap_tolerances: list[float] = field(default_factory=list)


@dataclass
class TimingAnomaly:
    """A timing anomaly detection."""
    event1_type: EventType
    event2_type: EventType
    expected_gap_seconds: float
    actual_gap_seconds: float
    deviation_factor: float  # How many std devs from mean


@dataclass
class Anomaly:
    """A detected anomaly."""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: float  # 0.0 to 1.0
    
    # Context
    entity_id: str
    entity_type: str
    detected_at: datetime
    
    # Details
    description: str
    events_involved: list[str] = field(default_factory=list)
    
    # For sentiment anomalies
    sentiment_result: Optional[SentimentResult] = None
    
    # For sequence anomalies
    expected_pattern: Optional[str] = None
    actual_pattern: Optional[str] = None
    
    # For timing anomalies
    timing_details: Optional[TimingAnomaly] = None
    
    # Recommendations
    recommended_actions: list[str] = field(default_factory=list)
    
    def should_alert(self, sensitivity: AlertSensitivity) -> bool:
        """Determine if anomaly should trigger alert based on sensitivity."""
        thresholds = {
            AlertSensitivity.LOW: 0.8,
            AlertSensitivity.MEDIUM: 0.6,
            AlertSensitivity.HIGH: 0.4,
        }
        return self.severity >= thresholds[sensitivity]


@dataclass
class AlertConfig:
    """Alert configuration."""
    sensitivity: AlertSensitivity = AlertSensitivity.MEDIUM
    enabled_anomaly_types: list[AnomalyType] = field(
        default_factory=lambda: list(AnomalyType)
    )
    
    # Cooldown to avoid alarm fatigue
    cooldown_minutes: int = 30
    max_alerts_per_hour: int = 10
    
    # Custom thresholds
    custom_thresholds: dict[AnomalyType, float] = field(default_factory=dict)
    
    def get_threshold(self, anomaly_type: AnomalyType) -> float:
        """Get threshold for anomaly type."""
        if anomaly_type in self.custom_thresholds:
            return self.custom_thresholds[anomaly_type]
        
        base_thresholds = {
            AlertSensitivity.LOW: 0.8,
            AlertSensitivity.MEDIUM: 0.6,
            AlertSensitivity.HIGH: 0.4,
        }
        return base_thresholds[self.sensitivity]


@dataclass
class Alert:
    """An alert triggered by anomaly."""
    alert_id: str
    anomaly: Anomaly
    triggered_at: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    # Suppression info
    is_suppressed: bool = False
    suppression_reason: Optional[str] = None


# =============================================================================
# Sentiment Analyzer
# =============================================================================

class SentimentAnalyzer:
    """
    Analyzes text for sentiment and urgency.
    
    Detects escalating frustration before it becomes an Andon event.
    """
    
    # Sentiment keywords
    POSITIVE_KEYWORDS = [
        "thank", "great", "excellent", "good", "appreciate",
        "pleased", "happy", "satisfied", "wonderful", "perfect",
    ]
    
    NEGATIVE_KEYWORDS = [
        "frustrated", "disappointed", "angry", "upset", "unacceptable",
        "terrible", "awful", "poor", "bad", "worst", "hate",
        "incompetent", "ridiculous", "absurd", "outrageous",
    ]
    
    FRUSTRATION_PATTERNS = [
        r"still waiting",
        r"no response",
        r"again\?",
        r"how many times",
        r"third time",
        r"fourth time",
        r"not acceptable",
        r"not good enough",
        r"complete failure",
        r"waste of time",
        r"escalate",
        r"speak to (a )?manager",
        r"legal action",
        r"cancel",
        r"competitor",
    ]
    
    URGENCY_KEYWORDS = [
        ("urgent", 0.8),
        ("asap", 0.9),
        ("immediately", 0.9),
        ("critical", 0.85),
        ("emergency", 0.95),
        ("rush", 0.7),
        ("expedite", 0.75),
        ("priority", 0.6),
        ("deadline", 0.7),
        ("overdue", 0.8),
        ("late", 0.6),
    ]
    
    def __init__(self):
        """Initialize analyzer."""
        self._history: dict[str, list[SentimentResult]] = defaultdict(list)
    
    def analyze(self, text: str, entity_id: str = "") -> SentimentResult:
        """Analyze text for sentiment and urgency."""
        if not text:
            return SentimentResult(
                text="",
                sentiment_level=SentimentLevel.NEUTRAL,
                sentiment_score=0.0,
                urgency_level=UrgencyLevel.NONE,
                urgency_score=0.0,
            )
        
        text_lower = text.lower()
        
        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment_score(text_lower)
        sentiment_level = self._score_to_sentiment_level(sentiment_score)
        
        # Calculate urgency score — pass original text for CAPS detection
        urgency_score = self._calculate_urgency_score(text_lower, original_text=text)
        urgency_level = self._score_to_urgency_level(urgency_score)
        
        # Detect frustration patterns
        frustration_indicators = self._detect_frustration_patterns(text_lower)
        
        # Detect urgency indicators
        urgency_indicators = [
            kw for kw, _ in self.URGENCY_KEYWORDS
            if kw in text_lower
        ]
        
        # Check for escalation
        is_escalating = self._check_escalation(entity_id, sentiment_score)
        
        result = SentimentResult(
            text=text[:200],  # Truncate for storage
            sentiment_level=sentiment_level,
            sentiment_score=sentiment_score,
            urgency_level=urgency_level,
            urgency_score=urgency_score,
            frustration_indicators=frustration_indicators,
            urgency_indicators=urgency_indicators,
            is_escalating=is_escalating,
        )
        
        # Store in history for escalation tracking
        if entity_id:
            self._history[entity_id].append(result)
            # Keep only recent history
            if len(self._history[entity_id]) > SENTIMENT_HISTORY_SIZE:
                self._history[entity_id] = self._history[entity_id][-SENTIMENT_HISTORY_SIZE:]
        
        return result
    
    _NEGATION_RE = re.compile(
        r"\b(?:not|no|never|don't|doesn't|didn't|won't|wouldn't|can't|cannot|isn't|aren't|wasn't|weren't|hardly|barely|scarcely)\b"
    )

    def _is_negated(self, text: str, keyword: str) -> bool:
        """Check if a keyword is preceded by a negation word within a 4-word window."""
        match = re.search(rf'\b{re.escape(keyword)}\b', text)
        if not match:
            return False
        # Grab up to 40 chars before the keyword as context window
        prefix = text[max(0, match.start() - 40):match.start()]
        return bool(self._NEGATION_RE.search(prefix))

    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score from -1 to 1."""
        positive_count = 0
        negative_count = 0

        for kw in self.POSITIVE_KEYWORDS:
            if re.search(rf'\b{re.escape(kw)}\b', text):
                if self._is_negated(text, kw):
                    negative_count += 1  # Negated positive → negative
                else:
                    positive_count += 1

        for kw in self.NEGATIVE_KEYWORDS:
            if re.search(rf'\b{re.escape(kw)}\b', text):
                if self._is_negated(text, kw):
                    positive_count += 1  # Negated negative → positive
                else:
                    negative_count += 1

        # Count frustration patterns (weighted higher)
        frustration_count = len(self._detect_frustration_patterns(text))
        negative_count += frustration_count * 2

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        score = (positive_count - negative_count) / total
        return max(-1.0, min(1.0, score))
    
    def _calculate_urgency_score(self, text: str, *, original_text: str = "") -> float:
        """Calculate urgency score from 0 to 1.

        Args:
            text: Lowercased text for keyword matching.
            original_text: Original (un-lowered) text for ALL-CAPS detection.
        """
        max_urgency = 0.0
        
        for keyword, weight in self.URGENCY_KEYWORDS:
            if keyword in text:
                max_urgency = max(max_urgency, weight)
        
        # Check for exclamation marks (adds urgency) — use original text
        source = original_text or text
        exclamation_count = source.count("!")
        if exclamation_count > 0:
            max_urgency = max(max_urgency, min(0.5 + exclamation_count * 0.1, 0.8))
        
        # Check for ALL CAPS words — must use original (un-lowered) text
        caps_words = len(re.findall(r"\b[A-Z]{3,}\b", source))
        if caps_words > 0:
            max_urgency = max(max_urgency, min(0.4 + caps_words * 0.1, 0.7))
        
        return max_urgency
    
    def _detect_frustration_patterns(self, text: str) -> list[str]:
        """Detect frustration patterns in text."""
        detected = []
        for pattern in self.FRUSTRATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                detected.append(pattern)
        return detected
    
    def _score_to_sentiment_level(self, score: float) -> SentimentLevel:
        """Convert sentiment score to level."""
        if score >= 0.6:
            return SentimentLevel.VERY_POSITIVE
        elif score >= 0.2:
            return SentimentLevel.POSITIVE
        elif score <= -0.6:
            return SentimentLevel.VERY_NEGATIVE
        elif score <= -0.2:
            return SentimentLevel.NEGATIVE
        else:
            return SentimentLevel.NEUTRAL
    
    def _score_to_urgency_level(self, score: float) -> UrgencyLevel:
        """Convert urgency score to level."""
        if score >= 0.9:
            return UrgencyLevel.CRITICAL
        elif score >= 0.7:
            return UrgencyLevel.HIGH
        elif score >= 0.5:
            return UrgencyLevel.MEDIUM
        elif score >= 0.3:
            return UrgencyLevel.LOW
        else:
            return UrgencyLevel.NONE
    
    def _check_escalation(self, entity_id: str, current_score: float) -> bool:
        """Check if sentiment is escalating."""
        if not entity_id or entity_id not in self._history:
            return False
        
        history = self._history[entity_id]
        if len(history) < 2:
            return False
        
        # Check if sentiment is getting more negative
        recent_scores = [r.sentiment_score for r in history[-5:]]
        if len(recent_scores) >= 2:
            trend = recent_scores[-1] - recent_scores[0]
            if trend < -SENTIMENT_ESCALATION_THRESHOLD:
                return True
        
        # Check if current is significantly more negative than average
        avg_score = sum(recent_scores) / len(recent_scores)
        if current_score < avg_score - 0.3:
            return True
        
        return False
    
    def get_entity_sentiment_trend(
        self,
        entity_id: str,
    ) -> list[tuple[int, float]]:
        """Get sentiment trend for an entity."""
        history = self._history.get(entity_id, [])
        return [(i, r.sentiment_score) for i, r in enumerate(history)]


# =============================================================================
# Sequence Analyzer
# =============================================================================

class SequenceAnalyzer:
    """
    Analyzes event sequences for anomalies.
    
    Uses pattern learning to detect unusual orderings or missing events.
    """
    
    # Expected event order for common workflows
    EXPECTED_WORKFLOWS = {
        "quote_flow": [
            EventType.RFQ_RECEIVED,
            EventType.QUOTE_CREATED,
            EventType.QUOTE_SENT,
        ],
        "order_flow": [
            EventType.ORDER_RECEIVED,
            EventType.PRODUCTION_STARTED,
            EventType.PRODUCTION_COMPLETED,
            EventType.QC_PASSED,
            EventType.SHIPPED,
            EventType.DELIVERED,
        ],
        "full_flow": [
            EventType.RFQ_RECEIVED,
            EventType.QUOTE_CREATED,
            EventType.QUOTE_SENT,
            EventType.ORDER_RECEIVED,
            EventType.PRODUCTION_STARTED,
            EventType.PRODUCTION_COMPLETED,
            EventType.QC_PASSED,
            EventType.SHIPPED,
            EventType.DELIVERED,
        ],
    }
    
    def __init__(self):
        """Initialize analyzer."""
        self._learned_patterns: list[SequencePattern] = []
        self._transition_stats: dict[tuple[EventType, EventType], list[float]] = defaultdict(list)
    
    def learn_pattern(self, events: list[ProcessEvent]) -> Optional[SequencePattern]:
        """Learn a pattern from event sequence."""
        if len(events) < MIN_SEQUENCE_LENGTH:
            return None
        
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        # Extract sequence
        event_sequence = [e.event_type for e in sorted_events]
        
        # Calculate gaps
        gaps = []
        for i in range(len(sorted_events) - 1):
            gap = (sorted_events[i + 1].timestamp - sorted_events[i].timestamp).total_seconds()
            gaps.append(gap)
        
        # Record transition stats
        for i in range(len(sorted_events) - 1):
            key = (sorted_events[i].event_type, sorted_events[i + 1].event_type)
            self._transition_stats[key].append(gaps[i])
        
        # Create pattern
        pattern_id = hashlib.md5(
            str(event_sequence).encode()
        ).hexdigest()[:12]
        
        pattern = SequencePattern(
            pattern_id=pattern_id,
            event_sequence=event_sequence,
            frequency=1,
            avg_duration_seconds=sum(gaps) if gaps else 0.0,
            std_duration_seconds=self._std_dev(gaps) if gaps else 0.0,
            expected_gaps=gaps,
            gap_tolerances=[g * 0.5 for g in gaps],  # 50% tolerance
        )
        
        # Check if pattern exists
        for existing in self._learned_patterns:
            if existing.event_sequence == event_sequence:
                existing.frequency += 1
                return existing
        
        self._learned_patterns.append(pattern)
        return pattern
    
    def detect_sequence_anomalies(
        self,
        events: list[ProcessEvent],
    ) -> list[Anomaly]:
        """Detect sequence-based anomalies."""
        if len(events) < 2:
            return []
        
        anomalies = []
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        entity_id = sorted_events[0].entity_id if sorted_events else ""
        
        # Check event ordering
        ordering_anomalies = self._check_ordering(sorted_events)
        anomalies.extend(ordering_anomalies)
        
        # Check for missing events
        missing_anomalies = self._check_missing_events(sorted_events)
        anomalies.extend(missing_anomalies)
        
        # Check timing
        timing_anomalies = self._check_timing(sorted_events)
        anomalies.extend(timing_anomalies)
        
        return anomalies
    
    def _check_ordering(self, events: list[ProcessEvent]) -> list[Anomaly]:
        """Check for ordering anomalies."""
        anomalies = []
        event_types = [e.event_type for e in events]

        # Build type→sorted-indices map for O(1) lookup per type (#93)
        from collections import defaultdict
        type_indices: dict[str, list[int]] = defaultdict(list)
        for i, et in enumerate(event_types):
            type_indices[et].append(i)
        # Each list is already in ascending order since we iterate i in order.

        # Check against expected workflows
        for workflow_name, expected in self.EXPECTED_WORKFLOWS.items():
            # Find first available index per expected type
            matched_indices: list[int] = []
            used: set[int] = set()
            for expected_type in expected:
                for idx in type_indices.get(expected_type, []):
                    if idx not in used:
                        matched_indices.append(idx)
                        used.add(idx)
                        break
            
            # Check if matched events are in order
            if len(matched_indices) >= 2:
                for i in range(len(matched_indices) - 1):
                    if matched_indices[i] > matched_indices[i + 1]:
                        # Out of order
                        anomaly = Anomaly(
                            anomaly_id=self._generate_id(),
                            anomaly_type=AnomalyType.SEQUENCE,
                            severity=0.7,
                            entity_id=events[0].entity_id,
                            entity_type=events[0].entity_type,
                            detected_at=datetime.now(timezone.utc),
                            description=f"Events out of expected order in {workflow_name}",
                            events_involved=[events[matched_indices[i]].event_id],
                            expected_pattern=str(expected),
                            actual_pattern=str(event_types),
                            recommended_actions=[
                                "Review process flow for this entity",
                                "Check if steps were recorded incorrectly",
                            ],
                        )
                        anomalies.append(anomaly)
                        break
        
        return anomalies
    
    def _check_missing_events(self, events: list[ProcessEvent]) -> list[Anomaly]:
        """Check for missing expected events."""
        anomalies = []
        event_types = set(e.event_type for e in events)
        entity_id = events[0].entity_id if events else ""
        entity_type = events[0].entity_type if events else ""
        
        # Check quote flow
        if EventType.RFQ_RECEIVED in event_types:
            if EventType.ORDER_RECEIVED in event_types:
                # Full flow expected
                if EventType.QUOTE_CREATED not in event_types:
                    anomalies.append(Anomaly(
                        anomaly_id=self._generate_id(),
                        anomaly_type=AnomalyType.MISSING,
                        severity=0.6,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        detected_at=datetime.now(timezone.utc),
                        description="Quote creation event missing between RFQ and Order",
                        recommended_actions=["Verify quote was created properly"],
                    ))
        
        # Check order flow
        if EventType.PRODUCTION_COMPLETED in event_types:
            if EventType.SHIPPED in event_types:
                if EventType.QC_PASSED not in event_types and EventType.QC_FAILED not in event_types:
                    anomalies.append(Anomaly(
                        anomaly_id=self._generate_id(),
                        anomaly_type=AnomalyType.MISSING,
                        severity=0.8,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        detected_at=datetime.now(timezone.utc),
                        description="QC check missing between production and shipping",
                        recommended_actions=[
                            "Verify QC was performed",
                            "Update records if QC was done",
                        ],
                    ))
        
        return anomalies
    
    def _check_timing(self, events: list[ProcessEvent]) -> list[Anomaly]:
        """Check for timing anomalies."""
        anomalies = []
        
        for i in range(len(events) - 1):
            key = (events[i].event_type, events[i + 1].event_type)
            gaps = self._transition_stats.get(key, [])
            
            if len(gaps) < 5:
                continue  # Not enough data
            
            actual_gap = (events[i + 1].timestamp - events[i].timestamp).total_seconds()
            mean_gap = sum(gaps) / len(gaps)
            std_gap = self._std_dev(gaps)
            
            if std_gap > 0:
                deviation = abs(actual_gap - mean_gap) / std_gap
                
                if deviation > 3:  # More than 3 std devs
                    timing_detail = TimingAnomaly(
                        event1_type=events[i].event_type,
                        event2_type=events[i + 1].event_type,
                        expected_gap_seconds=mean_gap,
                        actual_gap_seconds=actual_gap,
                        deviation_factor=deviation,
                    )
                    
                    severity = min(0.5 + (deviation - 3) * 0.1, 1.0)
                    
                    anomalies.append(Anomaly(
                        anomaly_id=self._generate_id(),
                        anomaly_type=AnomalyType.TIMING,
                        severity=severity,
                        entity_id=events[i].entity_id,
                        entity_type=events[i].entity_type,
                        detected_at=datetime.now(timezone.utc),
                        description=f"Unusual delay between {events[i].event_type.value} and {events[i + 1].event_type.value}",
                        events_involved=[events[i].event_id, events[i + 1].event_id],
                        timing_details=timing_detail,
                        recommended_actions=[
                            f"Investigate delay of {actual_gap / 3600:.1f} hours (expected {mean_gap / 3600:.1f} hours)",
                        ],
                    ))
        
        return anomalies
    
    def _std_dev(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def _generate_id(self) -> str:
        """Generate unique anomaly ID."""
        return uuid.uuid4().hex[:12]


# =============================================================================
# Alert Manager
# =============================================================================

class AlertManager:
    """
    Manages alerts with configurable thresholds.
    
    Implements cooldown and rate limiting to avoid alarm fatigue.
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """Initialize alert manager."""
        self.config = config or AlertConfig()
        
        self._alerts: list[Alert] = []
        self._alert_history: dict[str, list[datetime]] = defaultdict(list)
        self._cooldowns: dict[str, datetime] = {}
    
    def should_alert(self, anomaly: Anomaly) -> bool:
        """Determine if anomaly should trigger an alert."""
        # Check if type is enabled
        if anomaly.anomaly_type not in self.config.enabled_anomaly_types:
            return False
        
        # Check threshold
        threshold = self.config.get_threshold(anomaly.anomaly_type)
        if anomaly.severity < threshold:
            return False
        
        # Check cooldown
        cooldown_key = f"{anomaly.entity_id}:{anomaly.anomaly_type.value}"
        if cooldown_key in self._cooldowns:
            cooldown_end = self._cooldowns[cooldown_key]
            if datetime.now(timezone.utc) < cooldown_end:
                return False
        
        # Check rate limit
        if not self._check_rate_limit():
            return False
        
        return True
    
    def create_alert(self, anomaly: Anomaly) -> Alert | None:
        """Create alert from anomaly if conditions are met."""
        if not self.should_alert(anomaly):
            return None
        
        alert_id = hashlib.md5(
            f"{anomaly.anomaly_id}:{datetime.now(timezone.utc)}".encode()
        ).hexdigest()[:12]
        
        alert = Alert(
            alert_id=alert_id,
            anomaly=anomaly,
            triggered_at=datetime.now(timezone.utc),
        )
        
        self._alerts.append(alert)
        
        # Set cooldown
        cooldown_key = f"{anomaly.entity_id}:{anomaly.anomaly_type.value}"
        cooldown_end = datetime.now(timezone.utc) + timedelta(
            minutes=self.config.cooldown_minutes
        )
        self._cooldowns[cooldown_key] = cooldown_end
        
        # Record for rate limiting
        self._alert_history["global"].append(datetime.now(timezone.utc))
        
        return alert
    
    def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str,
    ) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user_id
                alert.acknowledged_at = datetime.now(timezone.utc)
                return True
        return False
    
    def suppress_alert(
        self,
        alert_id: str,
        reason: str,
    ) -> bool:
        """Suppress an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.is_suppressed = True
                alert.suppression_reason = reason
                return True
        return False
    
    def get_active_alerts(self) -> list[Alert]:
        """Get unacknowledged, non-suppressed alerts."""
        return [
            a for a in self._alerts
            if not a.acknowledged and not a.is_suppressed
        ]
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows new alert."""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        self._alert_history["global"] = [
            t for t in self._alert_history["global"]
            if t > hour_ago
        ]
        
        return len(self._alert_history["global"]) < self.config.max_alerts_per_hour
    
    def update_config(self, config: AlertConfig) -> None:
        """Update alert configuration."""
        self.config = config


# =============================================================================
# Anomaly Detection Engine
# =============================================================================

class AnomalyDetectionEngine:
    """
    Main engine for deep semantic anomaly detection.
    
    Combines sequence, timing, and sentiment analysis.
    """
    
    def __init__(
        self,
        alert_config: Optional[AlertConfig] = None,
    ):
        """Initialize engine."""
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sequence_analyzer = SequenceAnalyzer()
        self.alert_manager = AlertManager(alert_config)
        
        self._event_buffer: dict[str, list[ProcessEvent]] = defaultdict(list)
        self._detected_anomalies: list[Anomaly] = []
        # Track event ids already analysed to avoid duplicates
        self._analyzed_event_ids: set[str] = set()
    
    def process_event(self, event: ProcessEvent) -> list[Alert]:
        """Process a single event and return any triggered alerts."""
        # Skip if already processed
        if event.event_id in self._analyzed_event_ids:
            return []
        self._analyzed_event_ids.add(event.event_id)

        alerts = []

        # Add to buffer
        self._event_buffer[event.entity_id].append(event)

        # Limit buffer size
        if len(self._event_buffer[event.entity_id]) > SEQUENCE_WINDOW_SIZE:
            self._event_buffer[event.entity_id] = (
                self._event_buffer[event.entity_id][-SEQUENCE_WINDOW_SIZE:]
            )

        # Analyze sentiment if content exists
        if event.content:
            sentiment_anomalies = self._analyze_sentiment_anomaly(event)
            for anomaly in sentiment_anomalies:
                self._detected_anomalies.append(anomaly)
                alert = self.alert_manager.create_alert(anomaly)
                if alert:
                    alerts.append(alert)

        # Learn patterns
        self.sequence_analyzer.learn_pattern(self._event_buffer[event.entity_id])

        # Detect sequence anomalies on the full buffer (cheap with small window)
        sequence_anomalies = self.sequence_analyzer.detect_sequence_anomalies(
            self._event_buffer[event.entity_id]
        )

        for anomaly in sequence_anomalies:
            self._detected_anomalies.append(anomaly)
            alert = self.alert_manager.create_alert(anomaly)
            if alert:
                alerts.append(alert)

        return alerts
    
    def process_events(self, events: list[ProcessEvent]) -> list[Alert]:
        """Process multiple events."""
        all_alerts = []
        for event in events:
            alerts = self.process_event(event)
            all_alerts.extend(alerts)
        return all_alerts
    
    def analyze_entity(self, entity_id: str) -> list[Anomaly]:
        """Analyze all events for an entity, skipping already-analyzed events."""
        events = self._event_buffer.get(entity_id, [])
        if not events:
            return []

        anomalies = []

        # Sequence anomalies (operates on full buffer, lightweight)
        sequence_anomalies = self.sequence_analyzer.detect_sequence_anomalies(events)
        anomalies.extend(sequence_anomalies)

        # Sentiment analysis only on events not yet processed
        for event in events:
            if event.content and event.event_id not in self._analyzed_event_ids:
                sentiment_anomalies = self._analyze_sentiment_anomaly(event)
                anomalies.extend(sentiment_anomalies)
                self._analyzed_event_ids.add(event.event_id)

        return anomalies
    
    def _analyze_sentiment_anomaly(self, event: ProcessEvent) -> list[Anomaly]:
        """Analyze event content for sentiment anomalies."""
        anomalies = []
        
        result = self.sentiment_analyzer.analyze(event.content, event.entity_id)
        
        # Check for negative sentiment
        if result.sentiment_level in [SentimentLevel.NEGATIVE, SentimentLevel.VERY_NEGATIVE]:
            severity = 0.5 + abs(result.sentiment_score) * 0.5
            
            anomaly = Anomaly(
                anomaly_id=self._generate_id(),
                anomaly_type=AnomalyType.SENTIMENT,
                severity=severity,
                entity_id=event.entity_id,
                entity_type=event.entity_type,
                detected_at=datetime.now(timezone.utc),
                description=f"Negative sentiment detected: {result.sentiment_level.value}",
                events_involved=[event.event_id],
                sentiment_result=result,
                recommended_actions=[
                    "Review recent communications",
                    "Consider proactive customer outreach",
                ],
            )
            anomalies.append(anomaly)
        
        # Check for escalation
        if result.is_escalating:
            anomaly = Anomaly(
                anomaly_id=self._generate_id(),
                anomaly_type=AnomalyType.SENTIMENT,
                severity=0.85,
                entity_id=event.entity_id,
                entity_type=event.entity_type,
                detected_at=datetime.now(timezone.utc),
                description="Sentiment is escalating negatively - potential Andon event",
                events_involved=[event.event_id],
                sentiment_result=result,
                recommended_actions=[
                    "Immediate attention required",
                    "Escalate to supervisor",
                    "Document issue and resolution plan",
                ],
            )
            anomalies.append(anomaly)
        
        # Check for high urgency
        if result.urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]:
            severity = 0.6 + result.urgency_score * 0.4
            
            anomaly = Anomaly(
                anomaly_id=self._generate_id(),
                anomaly_type=AnomalyType.URGENCY,
                severity=severity,
                entity_id=event.entity_id,
                entity_type=event.entity_type,
                detected_at=datetime.now(timezone.utc),
                description=f"High urgency detected: {result.urgency_level.value}",
                events_involved=[event.event_id],
                sentiment_result=result,
                recommended_actions=[
                    "Prioritize this request",
                    "Acknowledge receipt immediately",
                ],
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def get_anomaly_summary(self) -> dict[str, Any]:
        """Get summary of detected anomalies."""
        by_type: dict[AnomalyType, int] = defaultdict(int)
        by_severity: dict[str, int] = defaultdict(int)
        
        for anomaly in self._detected_anomalies:
            by_type[anomaly.anomaly_type] += 1
            
            if anomaly.severity >= 0.8:
                by_severity["critical"] += 1
            elif anomaly.severity >= 0.6:
                by_severity["high"] += 1
            elif anomaly.severity >= 0.4:
                by_severity["medium"] += 1
            else:
                by_severity["low"] += 1
        
        return {
            "total_anomalies": len(self._detected_anomalies),
            "by_type": {k.value: v for k, v in by_type.items()},
            "by_severity": dict(by_severity),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
        }
    
    def set_alert_sensitivity(self, sensitivity: AlertSensitivity) -> None:
        """Set alert sensitivity level."""
        self.alert_manager.config.sensitivity = sensitivity
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return uuid.uuid4().hex[:12]


# =============================================================================
# Factory Function
# =============================================================================

def create_anomaly_detector(
    sensitivity: AlertSensitivity = AlertSensitivity.MEDIUM,
    enabled_types: Optional[list[AnomalyType]] = None,
    cooldown_minutes: int = 30,
    max_alerts_per_hour: int = 10,
) -> AnomalyDetectionEngine:
    """Create a configured anomaly detection engine."""
    config = AlertConfig(
        sensitivity=sensitivity,
        enabled_anomaly_types=enabled_types or list(AnomalyType),
        cooldown_minutes=cooldown_minutes,
        max_alerts_per_hour=max_alerts_per_hour,
    )
    
    return AnomalyDetectionEngine(alert_config=config)
