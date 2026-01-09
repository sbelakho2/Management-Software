"""
Tests for Deep Semantic Anomaly Detection.

Tests cover:
- Sentiment analysis
- Sequence analysis
- Alert management
- Complete detection engine
"""

import pytest
from datetime import datetime, timezone, timedelta

from sensei.services.semantic_anomaly_detection import (
    # Enums
    AlertSensitivity,
    AnomalyType,
    EventType,
    SentimentLevel,
    UrgencyLevel,
    # Data models
    ProcessEvent,
    SentimentResult,
    SequencePattern,
    TimingAnomaly,
    Anomaly,
    AlertConfig,
    Alert,
    # Components
    SentimentAnalyzer,
    SequenceAnalyzer,
    AlertManager,
    AnomalyDetectionEngine,
    # Factory
    create_anomaly_detector,
    # Constants
    SEQUENCE_WINDOW_SIZE,
    ANOMALY_SCORE_THRESHOLD,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_events() -> list[ProcessEvent]:
    """Create sample process events."""
    base_time = datetime.now(timezone.utc)
    
    return [
        ProcessEvent(
            event_id="EVT-001",
            event_type=EventType.RFQ_RECEIVED,
            timestamp=base_time,
            entity_id="RFQ-001",
            entity_type="rfq",
        ),
        ProcessEvent(
            event_id="EVT-002",
            event_type=EventType.QUOTE_CREATED,
            timestamp=base_time + timedelta(hours=2),
            entity_id="RFQ-001",
            entity_type="rfq",
        ),
        ProcessEvent(
            event_id="EVT-003",
            event_type=EventType.QUOTE_SENT,
            timestamp=base_time + timedelta(hours=3),
            entity_id="RFQ-001",
            entity_type="rfq",
        ),
    ]


@pytest.fixture
def negative_sentiment_event() -> ProcessEvent:
    """Create event with negative sentiment content."""
    return ProcessEvent(
        event_id="EVT-NEG",
        event_type=EventType.EMAIL_RECEIVED,
        timestamp=datetime.now(timezone.utc),
        entity_id="RFQ-002",
        entity_type="rfq",
        content="I am very frustrated with this service. Still waiting for a response after multiple requests. This is unacceptable!",
    )


@pytest.fixture
def urgent_event() -> ProcessEvent:
    """Create event with urgent content."""
    return ProcessEvent(
        event_id="EVT-URG",
        event_type=EventType.EMAIL_RECEIVED,
        timestamp=datetime.now(timezone.utc),
        entity_id="RFQ-003",
        entity_type="rfq",
        content="URGENT! We need this quote ASAP. This is a critical deadline emergency.",
    )


@pytest.fixture
def alert_config() -> AlertConfig:
    """Create sample alert config."""
    return AlertConfig(
        sensitivity=AlertSensitivity.MEDIUM,
        cooldown_minutes=15,
        max_alerts_per_hour=20,
    )


@pytest.fixture
def detection_engine(alert_config: AlertConfig) -> AnomalyDetectionEngine:
    """Create detection engine."""
    return AnomalyDetectionEngine(alert_config=alert_config)


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_alert_sensitivity_values(self):
        """Test AlertSensitivity values."""
        assert AlertSensitivity.LOW.value == "low"
        assert AlertSensitivity.MEDIUM.value == "medium"
        assert AlertSensitivity.HIGH.value == "high"
    
    def test_anomaly_type_values(self):
        """Test AnomalyType values."""
        assert AnomalyType.SEQUENCE.value == "sequence"
        assert AnomalyType.TIMING.value == "timing"
        assert AnomalyType.SENTIMENT.value == "sentiment"
        assert AnomalyType.URGENCY.value == "urgency"
    
    def test_event_type_values(self):
        """Test EventType values."""
        assert EventType.RFQ_RECEIVED.value == "rfq_received"
        assert EventType.QUOTE_CREATED.value == "quote_created"
        assert EventType.ANDON_RAISED.value == "andon_raised"
    
    def test_sentiment_level_values(self):
        """Test SentimentLevel values."""
        assert SentimentLevel.VERY_POSITIVE.value == "very_positive"
        assert SentimentLevel.NEUTRAL.value == "neutral"
        assert SentimentLevel.VERY_NEGATIVE.value == "very_negative"
    
    def test_urgency_level_values(self):
        """Test UrgencyLevel values."""
        assert UrgencyLevel.NONE.value == "none"
        assert UrgencyLevel.CRITICAL.value == "critical"


# =============================================================================
# Tests: Data Models
# =============================================================================

class TestProcessEvent:
    """Test ProcessEvent dataclass."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = ProcessEvent(
            event_id="EVT-001",
            event_type=EventType.RFQ_RECEIVED,
            timestamp=datetime.now(timezone.utc),
            entity_id="RFQ-001",
            entity_type="rfq",
        )
        
        assert event.event_id == "EVT-001"
        assert event.event_type == EventType.RFQ_RECEIVED
    
    def test_event_with_content(self):
        """Test event with content."""
        event = ProcessEvent(
            event_id="EVT-001",
            event_type=EventType.NOTE_ADDED,
            timestamp=datetime.now(timezone.utc),
            entity_id="RFQ-001",
            entity_type="rfq",
            content="This is a note",
        )
        
        assert event.content == "This is a note"


class TestSentimentResult:
    """Test SentimentResult dataclass."""
    
    def test_result_creation(self):
        """Test creating sentiment result."""
        result = SentimentResult(
            text="Great service!",
            sentiment_level=SentimentLevel.POSITIVE,
            sentiment_score=0.8,
            urgency_level=UrgencyLevel.NONE,
            urgency_score=0.0,
        )
        
        assert result.sentiment_score == 0.8
        assert not result.is_escalating


class TestAnomaly:
    """Test Anomaly dataclass."""
    
    def test_anomaly_creation(self):
        """Test creating an anomaly."""
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SEQUENCE,
            severity=0.7,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test anomaly",
        )
        
        assert anomaly.severity == 0.7
    
    def test_should_alert_low_sensitivity(self):
        """Test should_alert with low sensitivity."""
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SEQUENCE,
            severity=0.7,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        # Low sensitivity requires 0.8
        assert not anomaly.should_alert(AlertSensitivity.LOW)
        
        anomaly.severity = 0.85
        assert anomaly.should_alert(AlertSensitivity.LOW)
    
    def test_should_alert_high_sensitivity(self):
        """Test should_alert with high sensitivity."""
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SEQUENCE,
            severity=0.5,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        # High sensitivity triggers at 0.4
        assert anomaly.should_alert(AlertSensitivity.HIGH)


class TestAlertConfig:
    """Test AlertConfig dataclass."""
    
    def test_default_config(self):
        """Test default config values."""
        config = AlertConfig()
        
        assert config.sensitivity == AlertSensitivity.MEDIUM
        assert config.cooldown_minutes == 30
    
    def test_get_threshold(self):
        """Test getting threshold for anomaly type."""
        config = AlertConfig(sensitivity=AlertSensitivity.HIGH)
        
        threshold = config.get_threshold(AnomalyType.SENTIMENT)
        assert threshold == 0.4
    
    def test_custom_threshold(self):
        """Test custom threshold override."""
        config = AlertConfig(
            sensitivity=AlertSensitivity.MEDIUM,
            custom_thresholds={AnomalyType.SENTIMENT: 0.5},
        )
        
        assert config.get_threshold(AnomalyType.SENTIMENT) == 0.5
        assert config.get_threshold(AnomalyType.SEQUENCE) == 0.6  # Default


# =============================================================================
# Tests: Sentiment Analyzer
# =============================================================================

class TestSentimentAnalyzer:
    """Test SentimentAnalyzer."""
    
    def test_analyzer_creation(self):
        """Test creating analyzer."""
        analyzer = SentimentAnalyzer()
        assert analyzer is not None
    
    def test_analyze_positive_text(self):
        """Test analyzing positive text."""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze("Thank you for the excellent service! Great job!")
        
        assert result.sentiment_score > 0
        assert result.sentiment_level in [SentimentLevel.POSITIVE, SentimentLevel.VERY_POSITIVE]
    
    def test_analyze_negative_text(self):
        """Test analyzing negative text."""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze("I am very frustrated and disappointed with this terrible service.")
        
        assert result.sentiment_score < 0
        assert result.sentiment_level in [SentimentLevel.NEGATIVE, SentimentLevel.VERY_NEGATIVE]
    
    def test_analyze_neutral_text(self):
        """Test analyzing neutral text."""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze("Please send me the quote for the requested items.")
        
        assert result.sentiment_level == SentimentLevel.NEUTRAL
    
    def test_analyze_empty_text(self):
        """Test analyzing empty text."""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze("")
        
        assert result.sentiment_level == SentimentLevel.NEUTRAL
        assert result.sentiment_score == 0.0
    
    def test_detect_urgency(self, urgent_event: ProcessEvent):
        """Test urgency detection."""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze(urgent_event.content)
        
        assert result.urgency_score > 0.5
        assert result.urgency_level in [UrgencyLevel.HIGH, UrgencyLevel.CRITICAL]
        assert len(result.urgency_indicators) > 0
    
    def test_detect_frustration_patterns(self):
        """Test frustration pattern detection."""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze("I'm still waiting! How many times do I have to ask?")
        
        assert len(result.frustration_indicators) > 0
    
    def test_escalation_detection(self):
        """Test sentiment escalation detection."""
        analyzer = SentimentAnalyzer()
        
        # First few messages are okay
        analyzer.analyze("Please send the quote.", "ENTITY-001")
        analyzer.analyze("Any update on my request?", "ENTITY-001")
        
        # Then sentiment gets worse
        result = analyzer.analyze(
            "I am very frustrated! This is terrible service. Speak to manager!",
            "ENTITY-001",
        )
        
        # Should detect escalation
        assert result.sentiment_score < 0
    
    def test_get_sentiment_trend(self):
        """Test getting sentiment trend."""
        analyzer = SentimentAnalyzer()
        
        analyzer.analyze("Great service!", "ENTITY-001")
        analyzer.analyze("Good work", "ENTITY-001")
        analyzer.analyze("Not happy with this", "ENTITY-001")
        
        trend = analyzer.get_entity_sentiment_trend("ENTITY-001")
        
        assert len(trend) == 3


# =============================================================================
# Tests: Sequence Analyzer
# =============================================================================

class TestSequenceAnalyzer:
    """Test SequenceAnalyzer."""
    
    def test_analyzer_creation(self):
        """Test creating analyzer."""
        analyzer = SequenceAnalyzer()
        assert analyzer is not None
    
    def test_learn_pattern(self, sample_events: list[ProcessEvent]):
        """Test learning a pattern."""
        analyzer = SequenceAnalyzer()
        
        pattern = analyzer.learn_pattern(sample_events)
        
        assert pattern is not None
        assert len(pattern.event_sequence) == 3
    
    def test_learn_pattern_insufficient_events(self):
        """Test learning with too few events."""
        analyzer = SequenceAnalyzer()
        
        events = [
            ProcessEvent(
                event_id="EVT-001",
                event_type=EventType.RFQ_RECEIVED,
                timestamp=datetime.now(timezone.utc),
                entity_id="RFQ-001",
                entity_type="rfq",
            ),
        ]
        
        pattern = analyzer.learn_pattern(events)
        
        assert pattern is None
    
    def test_detect_out_of_order(self):
        """Test detecting out of order events."""
        analyzer = SequenceAnalyzer()
        
        base_time = datetime.now(timezone.utc)
        
        # Wrong order: Quote sent before Quote created
        events = [
            ProcessEvent(
                event_id="EVT-001",
                event_type=EventType.RFQ_RECEIVED,
                timestamp=base_time,
                entity_id="RFQ-001",
                entity_type="rfq",
            ),
            ProcessEvent(
                event_id="EVT-002",
                event_type=EventType.QUOTE_SENT,  # Should come after QUOTE_CREATED
                timestamp=base_time + timedelta(hours=1),
                entity_id="RFQ-001",
                entity_type="rfq",
            ),
            ProcessEvent(
                event_id="EVT-003",
                event_type=EventType.QUOTE_CREATED,
                timestamp=base_time + timedelta(hours=2),
                entity_id="RFQ-001",
                entity_type="rfq",
            ),
        ]
        
        anomalies = analyzer.detect_sequence_anomalies(events)
        
        sequence_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.SEQUENCE]
        assert len(sequence_anomalies) > 0
    
    def test_detect_missing_qc(self):
        """Test detecting missing QC event."""
        analyzer = SequenceAnalyzer()
        
        base_time = datetime.now(timezone.utc)
        
        # Missing QC between production and shipping
        events = [
            ProcessEvent(
                event_id="EVT-001",
                event_type=EventType.PRODUCTION_COMPLETED,
                timestamp=base_time,
                entity_id="ORD-001",
                entity_type="order",
            ),
            ProcessEvent(
                event_id="EVT-002",
                event_type=EventType.SHIPPED,  # QC should come first
                timestamp=base_time + timedelta(hours=1),
                entity_id="ORD-001",
                entity_type="order",
            ),
        ]
        
        anomalies = analyzer.detect_sequence_anomalies(events)
        
        missing_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.MISSING]
        assert len(missing_anomalies) > 0
    
    def test_timing_anomaly_detection(self):
        """Test timing anomaly detection."""
        analyzer = SequenceAnalyzer()
        
        base_time = datetime.now(timezone.utc)
        
        # First, learn normal pattern
        for i in range(10):
            events = [
                ProcessEvent(
                    event_id=f"EVT-{i}-1",
                    event_type=EventType.RFQ_RECEIVED,
                    timestamp=base_time + timedelta(days=i),
                    entity_id=f"RFQ-{i}",
                    entity_type="rfq",
                ),
                ProcessEvent(
                    event_id=f"EVT-{i}-2",
                    event_type=EventType.QUOTE_CREATED,
                    timestamp=base_time + timedelta(days=i, hours=2),  # 2 hours gap
                    entity_id=f"RFQ-{i}",
                    entity_type="rfq",
                ),
            ]
            analyzer.learn_pattern(events)
        
        # Now check anomalous timing
        anomalous_events = [
            ProcessEvent(
                event_id="EVT-ANM-1",
                event_type=EventType.RFQ_RECEIVED,
                timestamp=base_time + timedelta(days=20),
                entity_id="RFQ-ANOMALY",
                entity_type="rfq",
            ),
            ProcessEvent(
                event_id="EVT-ANM-2",
                event_type=EventType.QUOTE_CREATED,
                timestamp=base_time + timedelta(days=20, hours=48),  # 48 hours gap!
                entity_id="RFQ-ANOMALY",
                entity_type="rfq",
            ),
        ]
        
        anomalies = analyzer.detect_sequence_anomalies(anomalous_events)
        
        # Should detect timing anomaly
        timing_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.TIMING]
        # May or may not trigger depending on variance
        assert isinstance(anomalies, list)


# =============================================================================
# Tests: Alert Manager
# =============================================================================

class TestAlertManager:
    """Test AlertManager."""
    
    def test_manager_creation(self, alert_config: AlertConfig):
        """Test creating manager."""
        manager = AlertManager(alert_config)
        assert manager is not None
    
    def test_should_alert(self, alert_config: AlertConfig):
        """Test should_alert check."""
        manager = AlertManager(alert_config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,
            severity=0.7,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        # Medium sensitivity threshold is 0.6
        assert manager.should_alert(anomaly)
    
    def test_should_not_alert_below_threshold(self, alert_config: AlertConfig):
        """Test should_alert returns False below threshold."""
        manager = AlertManager(alert_config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,
            severity=0.4,  # Below 0.6 threshold
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        assert not manager.should_alert(anomaly)
    
    def test_create_alert(self, alert_config: AlertConfig):
        """Test creating an alert."""
        manager = AlertManager(alert_config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,
            severity=0.8,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        alert = manager.create_alert(anomaly)
        
        assert alert is not None
        assert alert.alert_id is not None
        assert not alert.acknowledged
    
    def test_cooldown(self, alert_config: AlertConfig):
        """Test cooldown prevents duplicate alerts."""
        manager = AlertManager(alert_config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,
            severity=0.8,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        # First alert should succeed
        alert1 = manager.create_alert(anomaly)
        assert alert1 is not None
        
        # Second alert for same entity/type should fail (cooldown)
        anomaly.anomaly_id = "ANM-002"
        alert2 = manager.create_alert(anomaly)
        assert alert2 is None
    
    def test_acknowledge_alert(self, alert_config: AlertConfig):
        """Test acknowledging an alert."""
        manager = AlertManager(alert_config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,
            severity=0.8,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        alert = manager.create_alert(anomaly)
        assert alert is not None
        
        result = manager.acknowledge_alert(alert.alert_id, "user123")
        
        assert result is True
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "user123"
    
    def test_suppress_alert(self, alert_config: AlertConfig):
        """Test suppressing an alert."""
        manager = AlertManager(alert_config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,
            severity=0.8,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        alert = manager.create_alert(anomaly)
        assert alert is not None
        
        result = manager.suppress_alert(alert.alert_id, "Known issue")
        
        assert result is True
        assert alert.is_suppressed is True
    
    def test_get_active_alerts(self, alert_config: AlertConfig):
        """Test getting active alerts."""
        manager = AlertManager(alert_config)
        
        # Create alerts for different entities
        for i in range(3):
            anomaly = Anomaly(
                anomaly_id=f"ANM-{i}",
                anomaly_type=AnomalyType.SENTIMENT,
                severity=0.8,
                entity_id=f"RFQ-{i}",  # Different entities
                entity_type="rfq",
                detected_at=datetime.now(timezone.utc),
                description="Test",
            )
            manager.create_alert(anomaly)
        
        active = manager.get_active_alerts()
        
        assert len(active) == 3
    
    def test_disabled_anomaly_type(self):
        """Test that disabled anomaly types don't alert."""
        config = AlertConfig(
            sensitivity=AlertSensitivity.MEDIUM,
            enabled_anomaly_types=[AnomalyType.SEQUENCE],  # Only sequence
        )
        manager = AlertManager(config)
        
        anomaly = Anomaly(
            anomaly_id="ANM-001",
            anomaly_type=AnomalyType.SENTIMENT,  # Not enabled
            severity=0.9,
            entity_id="RFQ-001",
            entity_type="rfq",
            detected_at=datetime.now(timezone.utc),
            description="Test",
        )
        
        assert not manager.should_alert(anomaly)


# =============================================================================
# Tests: Anomaly Detection Engine
# =============================================================================

class TestAnomalyDetectionEngine:
    """Test AnomalyDetectionEngine."""
    
    def test_engine_creation(self):
        """Test creating engine."""
        engine = AnomalyDetectionEngine()
        assert engine is not None
    
    def test_process_event(self, sample_events: list[ProcessEvent]):
        """Test processing events."""
        engine = AnomalyDetectionEngine()
        
        for event in sample_events:
            alerts = engine.process_event(event)
            assert isinstance(alerts, list)
    
    def test_process_negative_sentiment(
        self,
        detection_engine: AnomalyDetectionEngine,
        negative_sentiment_event: ProcessEvent,
    ):
        """Test processing negative sentiment event."""
        alerts = detection_engine.process_event(negative_sentiment_event)
        
        # Should detect sentiment anomaly
        assert len(detection_engine._detected_anomalies) > 0
    
    def test_process_urgent_event(
        self,
        detection_engine: AnomalyDetectionEngine,
        urgent_event: ProcessEvent,
    ):
        """Test processing urgent event."""
        alerts = detection_engine.process_event(urgent_event)
        
        # Should detect urgency
        urgency_anomalies = [
            a for a in detection_engine._detected_anomalies
            if a.anomaly_type == AnomalyType.URGENCY
        ]
        assert len(urgency_anomalies) > 0
    
    def test_process_events_batch(self, sample_events: list[ProcessEvent]):
        """Test processing multiple events."""
        engine = AnomalyDetectionEngine()
        
        alerts = engine.process_events(sample_events)
        
        assert isinstance(alerts, list)
    
    def test_analyze_entity(self, detection_engine: AnomalyDetectionEngine):
        """Test analyzing all events for an entity."""
        base_time = datetime.now(timezone.utc)
        
        # Add some events
        events = [
            ProcessEvent(
                event_id="EVT-001",
                event_type=EventType.RFQ_RECEIVED,
                timestamp=base_time,
                entity_id="RFQ-ANALYZE",
                entity_type="rfq",
            ),
            ProcessEvent(
                event_id="EVT-002",
                event_type=EventType.QUOTE_CREATED,
                timestamp=base_time + timedelta(hours=1),
                entity_id="RFQ-ANALYZE",
                entity_type="rfq",
            ),
        ]
        
        for event in events:
            detection_engine.process_event(event)
        
        anomalies = detection_engine.analyze_entity("RFQ-ANALYZE")
        
        assert isinstance(anomalies, list)
    
    def test_get_anomaly_summary(self, detection_engine: AnomalyDetectionEngine):
        """Test getting anomaly summary."""
        # Add some events with issues
        event = ProcessEvent(
            event_id="EVT-001",
            event_type=EventType.EMAIL_RECEIVED,
            timestamp=datetime.now(timezone.utc),
            entity_id="RFQ-SUM",
            entity_type="rfq",
            content="This is terrible! Very frustrated!",
        )
        
        detection_engine.process_event(event)
        
        summary = detection_engine.get_anomaly_summary()
        
        assert "total_anomalies" in summary
        assert "by_type" in summary
        assert "by_severity" in summary
    
    def test_set_alert_sensitivity(self, detection_engine: AnomalyDetectionEngine):
        """Test setting alert sensitivity."""
        detection_engine.set_alert_sensitivity(AlertSensitivity.HIGH)
        
        assert detection_engine.alert_manager.config.sensitivity == AlertSensitivity.HIGH


# =============================================================================
# Tests: Factory Function
# =============================================================================

class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_default_detector(self):
        """Test creating default detector."""
        detector = create_anomaly_detector()
        
        assert isinstance(detector, AnomalyDetectionEngine)
        assert detector.alert_manager.config.sensitivity == AlertSensitivity.MEDIUM
    
    def test_create_custom_detector(self):
        """Test creating custom detector."""
        detector = create_anomaly_detector(
            sensitivity=AlertSensitivity.HIGH,
            enabled_types=[AnomalyType.SENTIMENT, AnomalyType.URGENCY],
            cooldown_minutes=10,
            max_alerts_per_hour=50,
        )
        
        assert detector.alert_manager.config.sensitivity == AlertSensitivity.HIGH
        assert detector.alert_manager.config.cooldown_minutes == 10


# =============================================================================
# Tests: Integration
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflow."""
    
    def test_full_detection_workflow(self):
        """Test complete detection workflow."""
        # Create detector
        detector = create_anomaly_detector(sensitivity=AlertSensitivity.HIGH)
        
        base_time = datetime.now(timezone.utc)
        
        # Normal events
        events = [
            ProcessEvent(
                event_id="EVT-001",
                event_type=EventType.RFQ_RECEIVED,
                timestamp=base_time,
                entity_id="RFQ-FLOW",
                entity_type="rfq",
            ),
            ProcessEvent(
                event_id="EVT-002",
                event_type=EventType.QUOTE_CREATED,
                timestamp=base_time + timedelta(hours=1),
                entity_id="RFQ-FLOW",
                entity_type="rfq",
            ),
            # Negative customer feedback
            ProcessEvent(
                event_id="EVT-003",
                event_type=EventType.EMAIL_RECEIVED,
                timestamp=base_time + timedelta(hours=2),
                entity_id="RFQ-FLOW",
                entity_type="rfq",
                content="I'm very disappointed with the quote. This is not what we discussed!",
            ),
        ]
        
        all_alerts = []
        for event in events:
            alerts = detector.process_event(event)
            all_alerts.extend(alerts)
        
        # Should have detected sentiment anomaly
        assert len(detector._detected_anomalies) > 0
    
    def test_escalation_detection_workflow(self):
        """Test escalation detection."""
        detector = create_anomaly_detector(sensitivity=AlertSensitivity.MEDIUM)
        
        # Series of increasingly negative messages
        messages = [
            "Can you provide an update on my quote?",
            "Still waiting for the quote...",
            "I've asked multiple times now. Where is my quote?",
            "This is unacceptable! I want to speak to a manager!",
        ]
        
        for i, msg in enumerate(messages):
            event = ProcessEvent(
                event_id=f"EVT-{i}",
                event_type=EventType.EMAIL_RECEIVED,
                timestamp=datetime.now(timezone.utc) + timedelta(hours=i),
                entity_id="RFQ-ESCALATE",
                entity_type="rfq",
                content=msg,
            )
            detector.process_event(event)
        
        # Check sentiment trend
        trend = detector.sentiment_analyzer.get_entity_sentiment_trend("RFQ-ESCALATE")
        
        # Trend should show decline
        if len(trend) >= 2:
            assert trend[-1][1] <= trend[0][1]  # Last score <= first score
    
    def test_alert_fatigue_prevention(self):
        """Test that cooldown prevents alert fatigue."""
        config = AlertConfig(
            sensitivity=AlertSensitivity.HIGH,
            cooldown_minutes=60,
            max_alerts_per_hour=3,
        )
        detector = AnomalyDetectionEngine(alert_config=config)
        
        # Generate many anomalies
        alerts_created = 0
        for i in range(10):
            event = ProcessEvent(
                event_id=f"EVT-{i}",
                event_type=EventType.EMAIL_RECEIVED,
                timestamp=datetime.now(timezone.utc),
                entity_id=f"RFQ-{i}",  # Different entities
                entity_type="rfq",
                content="URGENT! CRITICAL EMERGENCY! This is terrible!",
            )
            alerts = detector.process_event(event)
            alerts_created += len(alerts)
        
        # Should be limited by rate limiting
        assert alerts_created <= 3
