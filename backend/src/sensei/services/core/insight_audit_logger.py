"""
Audit Logging for AI Insight Access.

This module provides comprehensive audit logging for:
- Insight access requests and responses
- Role-based access decisions
- Failed access attempts
- Usage analytics by role

All audit entries are immutable and cryptographically signed for compliance.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Enums
# =============================================================================


class AuditEventType(str, Enum):
    """Types of audit events for insight access."""
    
    # Access events
    INSIGHT_REQUESTED = "insight_requested"
    INSIGHT_GRANTED = "insight_granted"
    INSIGHT_DENIED = "insight_denied"
    INSIGHT_FILTERED = "insight_filtered"
    
    # Batch operations
    INSIGHTS_BATCH_REQUESTED = "insights_batch_requested"
    INSIGHTS_BATCH_FILTERED = "insights_batch_filtered"
    
    # Configuration changes
    ROLE_INSIGHT_CONFIG_CHANGED = "role_insight_config_changed"
    INSIGHT_CATEGORY_ADDED = "insight_category_added"
    INSIGHT_CATEGORY_REMOVED = "insight_category_removed"
    
    # Admin actions
    ADMIN_OVERRIDE = "admin_override"
    EMERGENCY_ACCESS = "emergency_access"
    
    # Anomalies
    UNUSUAL_ACCESS_PATTERN = "unusual_access_pattern"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Data Models
# =============================================================================


@dataclass(frozen=True)
class InsightAuditEntry:
    """
    Immutable audit entry for insight access.
    
    All fields are frozen to prevent tampering after creation.
    """
    
    # Identity
    id: UUID
    correlation_id: str
    timestamp: datetime
    
    # Actor information
    user_id: str
    user_roles: tuple[str, ...]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    
    # Event details
    event_type: AuditEventType
    severity: AuditSeverity
    
    # Insight details
    insight_category: Optional[str]
    insight_id: Optional[str]
    
    # Access decision
    access_granted: bool
    denial_reason: Optional[str]
    
    # Context
    endpoint: Optional[str]
    request_params: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Integrity
    signature: str = ""
    
    def compute_signature(self, secret_key: str) -> str:
        """Compute HMAC signature for tamper detection."""
        data = f"{self.id}:{self.timestamp.isoformat()}:{self.user_id}:{self.event_type}:{self.access_granted}"
        return hashlib.sha256(f"{data}:{secret_key}".encode()).hexdigest()[:32]


@dataclass
class InsightAccessStats:
    """Statistics for insight access by role."""
    
    role: str
    period_start: datetime
    period_end: datetime
    
    # Counts
    total_requests: int = 0
    granted_requests: int = 0
    denied_requests: int = 0
    filtered_insights: int = 0
    
    # By category
    category_counts: dict[str, int] = field(default_factory=dict)
    
    # Timing
    avg_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    
    @property
    def denial_rate(self) -> float:
        """Calculate denial rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.denied_requests / self.total_requests) * 100


@dataclass
class AnomalyAlert:
    """Alert for anomalous insight access patterns."""
    
    id: UUID
    timestamp: datetime
    user_id: str
    user_roles: tuple[str, ...]
    
    anomaly_type: str
    description: str
    severity: AuditSeverity
    
    # Evidence
    recent_access_count: int
    baseline_access_count: int
    deviation_factor: float
    
    # Response
    action_taken: Optional[str] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


# =============================================================================
# Audit Logger Service
# =============================================================================


class InsightAuditLogger:
    """
    Service for logging and analyzing insight access.
    
    Features:
    - Immutable audit trail
    - Cryptographic signing
    - Anomaly detection
    - Usage analytics
    """
    
    def __init__(
        self,
        secret_key: str = "default-audit-secret-change-in-production",
        anomaly_threshold: float = 3.0,  # 3x baseline = anomaly
        rate_limit_window_seconds: int = 60,
        rate_limit_max_requests: int = 100,
    ):
        self.secret_key = secret_key
        self.anomaly_threshold = anomaly_threshold
        self.rate_limit_window = rate_limit_window_seconds
        self.rate_limit_max = rate_limit_max_requests
        
        # In-memory storage (replace with database in production)
        self._audit_entries: list[InsightAuditEntry] = []
        self._access_counts: dict[str, list[datetime]] = {}  # user_id -> timestamps
        self._anomaly_alerts: list[AnomalyAlert] = []
        
        # Baseline stats (would be computed from historical data)
        self._baseline_access_rates: dict[str, float] = {}  # role -> requests/hour
    
    def log_insight_request(
        self,
        user_id: str,
        user_roles: list[str],
        insight_category: str,
        access_granted: bool,
        denial_reason: Optional[str] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        request_params: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> InsightAuditEntry:
        """
        Log an insight access request.
        
        Args:
            user_id: ID of the requesting user
            user_roles: User's roles
            insight_category: Category of insight requested
            access_granted: Whether access was granted
            denial_reason: Reason for denial if applicable
            correlation_id: Request correlation ID
            session_id: User's session ID
            ip_address: Client IP address
            user_agent: Client user agent
            endpoint: API endpoint accessed
            request_params: Request parameters
            metadata: Additional metadata
            
        Returns:
            Created audit entry
        """
        entry_id = uuid4()
        timestamp = _utcnow()
        
        event_type = (
            AuditEventType.INSIGHT_GRANTED if access_granted
            else AuditEventType.INSIGHT_DENIED
        )
        
        severity = AuditSeverity.INFO if access_granted else AuditSeverity.WARNING
        
        entry = InsightAuditEntry(
            id=entry_id,
            correlation_id=correlation_id or str(uuid4()),
            timestamp=timestamp,
            user_id=user_id,
            user_roles=tuple(user_roles),
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            event_type=event_type,
            severity=severity,
            insight_category=insight_category,
            insight_id=None,
            access_granted=access_granted,
            denial_reason=denial_reason,
            endpoint=endpoint,
            request_params=request_params or {},
            metadata=metadata or {},
            signature=self._compute_signature(entry_id, timestamp, user_id, event_type, access_granted),
        )
        
        self._audit_entries.append(entry)
        self._track_access(user_id, timestamp)
        
        # Check for anomalies
        self._check_anomalies(user_id, user_roles, timestamp)
        
        logger.info(
            f"Insight audit: {event_type.value} for user {user_id} "
            f"category={insight_category} granted={access_granted}"
        )
        
        return entry
    
    def log_batch_filter(
        self,
        user_id: str,
        user_roles: list[str],
        total_insights: int,
        filtered_count: int,
        removed_categories: list[str],
        correlation_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> InsightAuditEntry:
        """
        Log a batch insight filter operation.
        
        Args:
            user_id: ID of the requesting user
            user_roles: User's roles
            total_insights: Total insights before filtering
            filtered_count: Number of insights after filtering
            removed_categories: Categories that were filtered out
            correlation_id: Request correlation ID
            endpoint: API endpoint accessed
            
        Returns:
            Created audit entry
        """
        entry_id = uuid4()
        timestamp = _utcnow()
        
        entry = InsightAuditEntry(
            id=entry_id,
            correlation_id=correlation_id or str(uuid4()),
            timestamp=timestamp,
            user_id=user_id,
            user_roles=tuple(user_roles),
            session_id=None,
            ip_address=None,
            user_agent=None,
            event_type=AuditEventType.INSIGHTS_BATCH_FILTERED,
            severity=AuditSeverity.INFO,
            insight_category=None,
            insight_id=None,
            access_granted=True,
            denial_reason=None,
            endpoint=endpoint,
            request_params={},
            metadata={
                "total_insights": total_insights,
                "filtered_count": filtered_count,
                "removed_count": total_insights - filtered_count,
                "removed_categories": removed_categories,
            },
            signature=self._compute_signature(
                entry_id, timestamp, user_id,
                AuditEventType.INSIGHTS_BATCH_FILTERED, True
            ),
        )
        
        self._audit_entries.append(entry)
        
        logger.info(
            f"Batch filter audit: user {user_id} "
            f"total={total_insights} filtered={filtered_count} "
            f"removed={total_insights - filtered_count}"
        )
        
        return entry
    
    def log_rate_limit_exceeded(
        self,
        user_id: str,
        user_roles: list[str],
        request_count: int,
        window_seconds: int,
        ip_address: Optional[str] = None,
    ) -> InsightAuditEntry:
        """Log a rate limit exceeded event."""
        entry_id = uuid4()
        timestamp = _utcnow()
        
        entry = InsightAuditEntry(
            id=entry_id,
            correlation_id=str(uuid4()),
            timestamp=timestamp,
            user_id=user_id,
            user_roles=tuple(user_roles),
            session_id=None,
            ip_address=ip_address,
            user_agent=None,
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.WARNING,
            insight_category=None,
            insight_id=None,
            access_granted=False,
            denial_reason=f"Rate limit exceeded: {request_count} requests in {window_seconds}s",
            endpoint=None,
            request_params={},
            metadata={
                "request_count": request_count,
                "window_seconds": window_seconds,
                "limit": self.rate_limit_max,
            },
            signature=self._compute_signature(
                entry_id, timestamp, user_id,
                AuditEventType.RATE_LIMIT_EXCEEDED, False
            ),
        )
        
        self._audit_entries.append(entry)
        
        logger.warning(
            f"Rate limit exceeded: user {user_id} "
            f"count={request_count} window={window_seconds}s"
        )
        
        return entry
    
    def get_user_stats(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> InsightAccessStats:
        """
        Get access statistics for a specific user.
        
        Args:
            user_id: User ID to get stats for
            start_time: Start of period (default: 24 hours ago)
            end_time: End of period (default: now)
            
        Returns:
            Access statistics for the user
        """
        end_time = end_time or _utcnow()
        start_time = start_time or datetime(
            end_time.year, end_time.month, end_time.day,
            tzinfo=None
        )
        
        relevant_entries = [
            e for e in self._audit_entries
            if e.user_id == user_id
            and start_time <= e.timestamp <= end_time
        ]
        
        stats = InsightAccessStats(
            role=",".join(relevant_entries[0].user_roles) if relevant_entries else "",
            period_start=start_time,
            period_end=end_time,
            total_requests=len(relevant_entries),
            granted_requests=sum(1 for e in relevant_entries if e.access_granted),
            denied_requests=sum(1 for e in relevant_entries if not e.access_granted),
        )
        
        # Count by category
        for entry in relevant_entries:
            if entry.insight_category:
                stats.category_counts[entry.insight_category] = \
                    stats.category_counts.get(entry.insight_category, 0) + 1
        
        return stats
    
    def get_role_stats(
        self,
        role: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> InsightAccessStats:
        """
        Get aggregated access statistics for a role.
        
        Args:
            role: Role to get stats for
            start_time: Start of period
            end_time: End of period
            
        Returns:
            Aggregated access statistics for the role
        """
        end_time = end_time or _utcnow()
        start_time = start_time or datetime(
            end_time.year, end_time.month, end_time.day,
            tzinfo=None
        )
        
        relevant_entries = [
            e for e in self._audit_entries
            if role in e.user_roles
            and start_time <= e.timestamp <= end_time
        ]
        
        stats = InsightAccessStats(
            role=role,
            period_start=start_time,
            period_end=end_time,
            total_requests=len(relevant_entries),
            granted_requests=sum(1 for e in relevant_entries if e.access_granted),
            denied_requests=sum(1 for e in relevant_entries if not e.access_granted),
        )
        
        # Count by category
        for entry in relevant_entries:
            if entry.insight_category:
                stats.category_counts[entry.insight_category] = \
                    stats.category_counts.get(entry.insight_category, 0) + 1
        
        # Count filtered insights from batch operations
        batch_entries = [
            e for e in relevant_entries
            if e.event_type == AuditEventType.INSIGHTS_BATCH_FILTERED
        ]
        stats.filtered_insights = sum(
            e.metadata.get("removed_count", 0) for e in batch_entries
        )
        
        return stats
    
    def get_anomaly_alerts(
        self,
        acknowledged: Optional[bool] = None,
        severity: Optional[AuditSeverity] = None,
    ) -> list[AnomalyAlert]:
        """
        Get anomaly alerts.
        
        Args:
            acknowledged: Filter by acknowledgement status
            severity: Filter by severity
            
        Returns:
            List of matching anomaly alerts
        """
        alerts = self._anomaly_alerts
        
        if acknowledged is not None:
            alerts = [
                a for a in alerts
                if (a.acknowledged_at is not None) == acknowledged
            ]
        
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    def acknowledge_alert(
        self,
        alert_id: UUID,
        acknowledged_by: str,
        action_taken: Optional[str] = None,
    ) -> bool:
        """
        Acknowledge an anomaly alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            acknowledged_by: User acknowledging the alert
            action_taken: Description of action taken
            
        Returns:
            True if alert was found and acknowledged
        """
        for alert in self._anomaly_alerts:
            if alert.id == alert_id:
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = _utcnow()
                alert.action_taken = action_taken
                return True
        return False
    
    def check_rate_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Tuple of (is_allowed, current_count)
        """
        now = _utcnow()
        window_start = datetime(
            now.year, now.month, now.day, now.hour, now.minute,
            now.second - self.rate_limit_window if now.second >= self.rate_limit_window else 0,
            tzinfo=None
        )
        
        if user_id not in self._access_counts:
            return True, 0
        
        # Count requests in window
        recent = [
            ts for ts in self._access_counts[user_id]
            if ts >= window_start
        ]
        
        count = len(recent)
        is_allowed = count < self.rate_limit_max
        
        return is_allowed, count
    
    def _compute_signature(
        self,
        entry_id: UUID,
        timestamp: datetime,
        user_id: str,
        event_type: AuditEventType,
        access_granted: bool,
    ) -> str:
        """Compute signature for audit entry."""
        data = f"{entry_id}:{timestamp.isoformat()}:{user_id}:{event_type.value}:{access_granted}"
        return hashlib.sha256(f"{data}:{self.secret_key}".encode()).hexdigest()[:32]
    
    def _track_access(self, user_id: str, timestamp: datetime) -> None:
        """Track access for rate limiting and anomaly detection."""
        if user_id not in self._access_counts:
            self._access_counts[user_id] = []
        
        self._access_counts[user_id].append(timestamp)
        
        # Keep only last hour of access times
        cutoff = datetime(
            timestamp.year, timestamp.month, timestamp.day,
            timestamp.hour - 1 if timestamp.hour > 0 else 23,
            tzinfo=None
        )
        self._access_counts[user_id] = [
            ts for ts in self._access_counts[user_id]
            if ts >= cutoff
        ]
    
    def _check_anomalies(
        self,
        user_id: str,
        user_roles: list[str],
        timestamp: datetime,
    ) -> None:
        """Check for anomalous access patterns."""
        # Get recent access count
        recent_count = len(self._access_counts.get(user_id, []))
        
        # Get baseline for primary role
        primary_role = user_roles[0] if user_roles else "viewer"
        baseline = self._baseline_access_rates.get(primary_role, 50.0)  # Default baseline
        
        # Check if access rate is anomalous
        if recent_count > baseline * self.anomaly_threshold:
            alert = AnomalyAlert(
                id=uuid4(),
                timestamp=timestamp,
                user_id=user_id,
                user_roles=tuple(user_roles),
                anomaly_type="high_access_rate",
                description=f"User {user_id} has unusually high insight access rate",
                severity=AuditSeverity.WARNING,
                recent_access_count=recent_count,
                baseline_access_count=int(baseline),
                deviation_factor=recent_count / baseline if baseline > 0 else float('inf'),
            )
            
            self._anomaly_alerts.append(alert)
            
            logger.warning(
                f"Anomaly detected: user {user_id} "
                f"count={recent_count} baseline={baseline}"
            )


# =============================================================================
# Singleton Instance
# =============================================================================


_audit_logger: Optional[InsightAuditLogger] = None


def get_insight_audit_logger() -> InsightAuditLogger:
    """Get the singleton audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = InsightAuditLogger()
    return _audit_logger


def configure_insight_audit_logger(
    secret_key: str,
    anomaly_threshold: float = 3.0,
    rate_limit_window_seconds: int = 60,
    rate_limit_max_requests: int = 100,
) -> InsightAuditLogger:
    """
    Configure and return the audit logger.
    
    Should be called during application startup.
    """
    global _audit_logger
    _audit_logger = InsightAuditLogger(
        secret_key=secret_key,
        anomaly_threshold=anomaly_threshold,
        rate_limit_window_seconds=rate_limit_window_seconds,
        rate_limit_max_requests=rate_limit_max_requests,
    )
    return _audit_logger
