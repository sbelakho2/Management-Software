"""
Tests for Insight Audit Logging.

Tests cover:
- Logging insight requests
- Logging batch filter operations
- Rate limit exceeded logging
- Anomaly detection
- Stats computation
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sensei.services.core.insight_audit_logger import (
    InsightAuditLogger,
    InsightAuditEntry,
    InsightAccessStats,
    AuditEventType,
    AuditSeverity,
    get_insight_audit_logger,
)


class TestInsightAuditLoggerBasics:
    """Test basic audit logger functionality."""
    
    @pytest.fixture
    def logger(self):
        return InsightAuditLogger()
    
    def test_logger_initialization(self, logger):
        """Test logger initializes correctly."""
        assert logger is not None
        assert logger.secret_key is not None
        assert logger.rate_limit_max > 0
    
    def test_log_insight_request_granted(self, logger):
        """Test logging a granted insight request."""
        entry = logger.log_insight_request(
            user_id="user-123",
            user_roles=["admin", "finance"],
            insight_category="revenue",
            access_granted=True,
        )
        
        assert entry is not None
        assert entry.user_id == "user-123"
        assert entry.access_granted is True
        assert entry.event_type == AuditEventType.INSIGHT_GRANTED
        assert entry.severity == AuditSeverity.INFO
    
    def test_log_insight_request_denied(self, logger):
        """Test logging a denied insight request."""
        entry = logger.log_insight_request(
            user_id="user-456",
            user_roles=["operator"],
            insight_category="hr_compensation",
            access_granted=False,
            denial_reason="Role not authorized for HR compensation insights",
        )
        
        assert entry is not None
        assert entry.access_granted is False
        assert entry.event_type == AuditEventType.INSIGHT_DENIED
        assert entry.severity == AuditSeverity.WARNING
        assert entry.denial_reason is not None
    
    def test_log_batch_filter(self, logger):
        """Test logging a batch filter operation."""
        entry = logger.log_batch_filter(
            user_id="user-789",
            user_roles=["quality"],
            total_insights=50,
            filtered_count=35,
            removed_categories=["hr_salary", "finance_pii"],
            endpoint="/api/v1/analytics/insights",
        )
        
        assert entry is not None
        assert entry.event_type == AuditEventType.INSIGHTS_BATCH_FILTERED
        assert entry.metadata["total_insights"] == 50
        assert entry.metadata["filtered_count"] == 35
        assert entry.metadata["removed_count"] == 15
    
    def test_log_rate_limit_exceeded(self, logger):
        """Test logging rate limit exceeded."""
        entry = logger.log_rate_limit_exceeded(
            user_id="user-spam",
            user_roles=["viewer"],
            request_count=150,
            window_seconds=60,
            ip_address="192.168.1.100",
        )
        
        assert entry is not None
        assert entry.event_type == AuditEventType.RATE_LIMIT_EXCEEDED
        assert entry.access_granted is False
        assert "Rate limit exceeded" in entry.denial_reason


class TestInsightAuditEntry:
    """Test InsightAuditEntry dataclass."""
    
    def test_entry_is_immutable(self):
        """Test that entries are frozen (immutable)."""
        entry = InsightAuditEntry(
            id=uuid4(),
            correlation_id="corr-123",
            timestamp=datetime.now(timezone.utc),
            user_id="user-1",
            user_roles=("admin",),
            session_id=None,
            ip_address=None,
            user_agent=None,
            event_type=AuditEventType.INSIGHT_GRANTED,
            severity=AuditSeverity.INFO,
            insight_category="quality",
            insight_id=None,
            access_granted=True,
            denial_reason=None,
            endpoint="/api/test",
        )
        
        # Frozen dataclass should raise error on modification
        with pytest.raises(AttributeError):
            entry.user_id = "modified"  # type: ignore
    
    def test_compute_signature(self):
        """Test signature computation."""
        entry = InsightAuditEntry(
            id=uuid4(),
            correlation_id="corr-456",
            timestamp=datetime.now(timezone.utc),
            user_id="user-2",
            user_roles=("finance",),
            session_id=None,
            ip_address=None,
            user_agent=None,
            event_type=AuditEventType.INSIGHT_GRANTED,
            severity=AuditSeverity.INFO,
            insight_category="finance",
            insight_id=None,
            access_granted=True,
            denial_reason=None,
            endpoint="/api/test",
        )
        
        sig1 = entry.compute_signature("secret-key-1")
        sig2 = entry.compute_signature("secret-key-2")
        
        # Different keys should produce different signatures
        assert sig1 != sig2
        
        # Same key should produce same signature
        sig3 = entry.compute_signature("secret-key-1")
        assert sig1 == sig3


class TestInsightAccessStats:
    """Test InsightAccessStats dataclass."""
    
    def test_denial_rate_calculation(self):
        """Test denial rate percentage calculation."""
        stats = InsightAccessStats(
            role="operator",
            period_start=datetime.now(timezone.utc) - timedelta(hours=1),
            period_end=datetime.now(timezone.utc),
            total_requests=100,
            granted_requests=80,
            denied_requests=20,
        )
        
        assert stats.denial_rate == 20.0
    
    def test_denial_rate_zero_requests(self):
        """Test denial rate with zero requests."""
        stats = InsightAccessStats(
            role="viewer",
            period_start=datetime.now(timezone.utc) - timedelta(hours=1),
            period_end=datetime.now(timezone.utc),
            total_requests=0,
            granted_requests=0,
            denied_requests=0,
        )
        
        assert stats.denial_rate == 0.0


class TestAuditLoggerSingleton:
    """Test audit logger singleton behavior."""
    
    def test_get_insight_audit_logger_returns_same_instance(self):
        """Test that get_insight_audit_logger returns singleton."""
        logger1 = get_insight_audit_logger()
        logger2 = get_insight_audit_logger()
        
        assert logger1 is logger2


class TestAuditEventTypes:
    """Test audit event type enumeration."""
    
    def test_access_event_types(self):
        """Test access-related event types."""
        assert AuditEventType.INSIGHT_REQUESTED.value == "insight_requested"
        assert AuditEventType.INSIGHT_GRANTED.value == "insight_granted"
        assert AuditEventType.INSIGHT_DENIED.value == "insight_denied"
    
    def test_batch_event_types(self):
        """Test batch operation event types."""
        assert AuditEventType.INSIGHTS_BATCH_REQUESTED.value == "insights_batch_requested"
        assert AuditEventType.INSIGHTS_BATCH_FILTERED.value == "insights_batch_filtered"
    
    def test_anomaly_event_types(self):
        """Test anomaly-related event types."""
        assert AuditEventType.UNUSUAL_ACCESS_PATTERN.value == "unusual_access_pattern"
        assert AuditEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert AuditEventType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"


class TestAuditSeverityLevels:
    """Test audit severity enumeration."""
    
    def test_severity_levels(self):
        """Test all severity levels exist."""
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditLoggerWithMetadata:
    """Test audit logger with full metadata."""
    
    @pytest.fixture
    def logger(self):
        return InsightAuditLogger()
    
    def test_log_with_full_context(self, logger):
        """Test logging with all optional context fields."""
        entry = logger.log_insight_request(
            user_id="user-full",
            user_roles=["admin", "finance", "hr"],
            insight_category="employee_performance",
            access_granted=True,
            correlation_id="req-12345",
            session_id="sess-67890",
            ip_address="10.0.0.50",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            endpoint="/api/v1/executive-intel/ceo-dashboard",
            request_params={"include_trends": True, "period": "30d"},
            metadata={"source": "dashboard", "version": "2.0"},
        )
        
        assert entry.correlation_id == "req-12345"
        assert entry.session_id == "sess-67890"
        assert entry.ip_address == "10.0.0.50"
        assert entry.user_agent is not None
        assert entry.endpoint == "/api/v1/executive-intel/ceo-dashboard"
        assert "include_trends" in entry.request_params
        assert "source" in entry.metadata


class TestAuditLoggerIntegration:
    """Test audit logger integration scenarios."""
    
    def test_analytics_endpoint_flow(self):
        """Test the flow that happens in analytics endpoint."""
        logger = InsightAuditLogger()
        
        # Simulate: user requests insights
        user_id = str(uuid4())
        user_roles = ["quality", "ops"]
        
        # Generate insights (mocked)
        all_insights = [
            {"id": "1", "category": "quality"},
            {"id": "2", "category": "hr_salary"},  # Should be filtered
            {"id": "3", "category": "production"},
            {"id": "4", "category": "finance_pii"},  # Should be filtered
        ]
        
        # Filter insights
        filtered_insights = [
            i for i in all_insights 
            if i["category"] not in ["hr_salary", "finance_pii"]
        ]
        
        # Determine removed categories
        removed_categories = list(set(
            i["category"] for i in all_insights
        ) - set(
            i["category"] for i in filtered_insights
        ))
        
        # Log the batch filter
        entry = logger.log_batch_filter(
            user_id=user_id,
            user_roles=user_roles,
            total_insights=len(all_insights),
            filtered_count=len(filtered_insights),
            removed_categories=removed_categories,
            endpoint="/api/v1/analytics/insights",
        )
        
        assert entry.metadata["total_insights"] == 4
        assert entry.metadata["filtered_count"] == 2
        assert entry.metadata["removed_count"] == 2
        assert set(entry.metadata["removed_categories"]) == {"hr_salary", "finance_pii"}
