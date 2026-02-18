"""
RFQ Time Tracking Service.

Implements time-on-task tracking for RFQ intake and quote approval workflows.
Measures user task completion times against targets (RFQ intake < 10 mins,
Quote Approval < 60s) as specified in the Development Plan usability testing.

Features:
- Task session management (start, pause, resume, complete)
- Time targets with warning thresholds
- Real-time elapsed time calculation
- Performance analytics and trends
- User efficiency metrics
- Alert generation for approaching/exceeding limits
- Historical analysis and reporting
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Callable
from uuid import UUID, uuid4
from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Types of timed tasks."""
    
    RFQ_INTAKE = "rfq_intake"
    QUOTE_APPROVAL = "quote_approval"
    RFQ_REVIEW = "rfq_review"
    QUOTE_CREATION = "quote_creation"
    QUALIFICATION = "qualification"
    CUSTOMER_RESPONSE = "customer_response"


class TaskSessionStatus(str, Enum):
    """Status of a task session."""
    
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class PerformanceLevel(str, Enum):
    """Performance level based on time spent."""
    
    EXCELLENT = "excellent"  # Under 50% of target
    GOOD = "good"            # 50-80% of target
    ON_TRACK = "on_track"    # 80-100% of target
    WARNING = "warning"      # 100-120% of target
    CRITICAL = "critical"    # Over 120% of target


@dataclass
class TaskTarget:
    """Time target for a task type."""
    
    task_type: TaskType
    target_seconds: int
    warning_threshold_pct: float = 0.8  # 80% of target
    critical_threshold_pct: float = 1.0  # 100% of target
    max_threshold_pct: float = 1.2  # 120% of target - exceeded
    
    @property
    def warning_seconds(self) -> int:
        """Get warning threshold in seconds."""
        return int(self.target_seconds * self.warning_threshold_pct)
    
    @property
    def critical_seconds(self) -> int:
        """Get critical threshold in seconds."""
        return int(self.target_seconds * self.critical_threshold_pct)
    
    @property
    def max_seconds(self) -> int:
        """Get max threshold in seconds."""
        return int(self.target_seconds * self.max_threshold_pct)
    
    def get_performance_level(self, elapsed_seconds: int) -> PerformanceLevel:
        """Get performance level based on elapsed time."""
        pct = elapsed_seconds / self.target_seconds if self.target_seconds > 0 else 0
        
        if pct < 0.5:
            return PerformanceLevel.EXCELLENT
        elif pct < 0.8:
            return PerformanceLevel.GOOD
        elif pct < 1.0:
            return PerformanceLevel.ON_TRACK
        elif pct < 1.2:
            return PerformanceLevel.WARNING
        else:
            return PerformanceLevel.CRITICAL
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_type": self.task_type.value,
            "target_seconds": self.target_seconds,
            "warning_seconds": self.warning_seconds,
            "critical_seconds": self.critical_seconds,
            "max_seconds": self.max_seconds,
        }


@dataclass
class PauseRecord:
    """Record of a pause in a task session."""
    
    paused_at: datetime
    resumed_at: datetime | None = None
    reason: str | None = None
    
    @property
    def pause_duration_seconds(self) -> int:
        """Get duration of pause in seconds."""
        if self.resumed_at:
            return int((self.resumed_at - self.paused_at).total_seconds())
        return int((datetime.now(timezone.utc) - self.paused_at).total_seconds())
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "paused_at": self.paused_at.isoformat(),
            "resumed_at": self.resumed_at.isoformat() if self.resumed_at else None,
            "reason": self.reason,
            "pause_duration_seconds": self.pause_duration_seconds,
        }


@dataclass
class TaskSession:
    """A tracked work session on a task."""
    
    id: UUID
    task_type: TaskType
    entity_id: UUID  # RFQ ID, Quote ID, etc.
    user_id: UUID
    status: TaskSessionStatus
    started_at: datetime
    pauses: list[PauseRecord] = field(default_factory=list)
    completed_at: datetime | None = None
    notes: str | None = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def total_pause_seconds(self) -> int:
        """Get total pause time in seconds."""
        return sum(p.pause_duration_seconds for p in self.pauses if p.resumed_at)
    
    @property
    def active_elapsed_seconds(self) -> int:
        """Get active working time in seconds (excluding pauses)."""
        end_time = self.completed_at or datetime.now(timezone.utc)
        total = int((end_time - self.started_at).total_seconds())
        return max(0, total - self.total_pause_seconds)
    
    @property
    def is_currently_paused(self) -> bool:
        """Check if session is currently paused."""
        if not self.pauses:
            return False
        return self.pauses[-1].resumed_at is None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "task_type": self.task_type.value,
            "entity_id": str(self.entity_id),
            "user_id": str(self.user_id),
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "pauses": [p.to_dict() for p in self.pauses],
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_pause_seconds": self.total_pause_seconds,
            "active_elapsed_seconds": self.active_elapsed_seconds,
            "is_currently_paused": self.is_currently_paused,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class TimeAlert:
    """Alert for time threshold crossing."""
    
    id: UUID
    session_id: UUID
    task_type: TaskType
    alert_type: str  # "warning", "critical", "exceeded"
    threshold_seconds: int
    elapsed_seconds: int
    created_at: datetime
    message: str
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "task_type": self.task_type.value,
            "alert_type": self.alert_type,
            "threshold_seconds": self.threshold_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "created_at": self.created_at.isoformat(),
            "message": self.message,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": str(self.acknowledged_by) if self.acknowledged_by else None,
        }


@dataclass
class TaskPerformanceStats:
    """Performance statistics for a task type."""
    
    task_type: TaskType
    period_start: datetime
    period_end: datetime
    total_sessions: int
    completed_sessions: int
    abandoned_sessions: int
    average_duration_seconds: float
    median_duration_seconds: float
    min_duration_seconds: int
    max_duration_seconds: int
    p90_duration_seconds: int  # 90th percentile
    target_seconds: int
    sessions_under_target: int
    sessions_over_target: int
    target_compliance_rate: float  # % of sessions under target
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_type": self.task_type.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_sessions": self.total_sessions,
            "completed_sessions": self.completed_sessions,
            "abandoned_sessions": self.abandoned_sessions,
            "average_duration_seconds": round(self.average_duration_seconds, 2),
            "median_duration_seconds": round(self.median_duration_seconds, 2),
            "min_duration_seconds": self.min_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "p90_duration_seconds": self.p90_duration_seconds,
            "target_seconds": self.target_seconds,
            "sessions_under_target": self.sessions_under_target,
            "sessions_over_target": self.sessions_over_target,
            "target_compliance_rate": round(self.target_compliance_rate, 2),
        }


@dataclass
class UserEfficiencyMetrics:
    """Efficiency metrics for a specific user."""
    
    user_id: UUID
    period_start: datetime
    period_end: datetime
    metrics_by_task: dict[TaskType, TaskPerformanceStats]
    total_active_time_seconds: int
    total_sessions: int
    efficiency_score: float  # 0-100 based on target compliance
    trend: str  # "improving", "stable", "declining"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "metrics_by_task": {
                k.value: v.to_dict() for k, v in self.metrics_by_task.items()
            },
            "total_active_time_seconds": self.total_active_time_seconds,
            "total_sessions": self.total_sessions,
            "efficiency_score": round(self.efficiency_score, 2),
            "trend": self.trend,
        }


@dataclass
class DailyTimeBreakdown:
    """Daily breakdown of time spent on tasks."""
    
    date: datetime
    task_type: TaskType
    total_sessions: int
    completed_sessions: int
    total_active_seconds: int
    average_duration_seconds: float
    under_target_count: int
    over_target_count: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "date": self.date.date().isoformat(),
            "task_type": self.task_type.value,
            "total_sessions": self.total_sessions,
            "completed_sessions": self.completed_sessions,
            "total_active_seconds": self.total_active_seconds,
            "average_duration_seconds": round(self.average_duration_seconds, 2),
            "under_target_count": self.under_target_count,
            "over_target_count": self.over_target_count,
        }


# Default task targets
DEFAULT_TASK_TARGETS: dict[TaskType, TaskTarget] = {
    TaskType.RFQ_INTAKE: TaskTarget(
        task_type=TaskType.RFQ_INTAKE,
        target_seconds=600,  # 10 minutes
        warning_threshold_pct=0.8,
        critical_threshold_pct=1.0,
        max_threshold_pct=1.2,
    ),
    TaskType.QUOTE_APPROVAL: TaskTarget(
        task_type=TaskType.QUOTE_APPROVAL,
        target_seconds=60,  # 60 seconds
        warning_threshold_pct=0.7,
        critical_threshold_pct=1.0,
        max_threshold_pct=1.5,
    ),
    TaskType.RFQ_REVIEW: TaskTarget(
        task_type=TaskType.RFQ_REVIEW,
        target_seconds=300,  # 5 minutes
        warning_threshold_pct=0.8,
        critical_threshold_pct=1.0,
        max_threshold_pct=1.3,
    ),
    TaskType.QUOTE_CREATION: TaskTarget(
        task_type=TaskType.QUOTE_CREATION,
        target_seconds=1800,  # 30 minutes
        warning_threshold_pct=0.8,
        critical_threshold_pct=1.0,
        max_threshold_pct=1.2,
    ),
    TaskType.QUALIFICATION: TaskTarget(
        task_type=TaskType.QUALIFICATION,
        target_seconds=900,  # 15 minutes
        warning_threshold_pct=0.8,
        critical_threshold_pct=1.0,
        max_threshold_pct=1.2,
    ),
    TaskType.CUSTOMER_RESPONSE: TaskTarget(
        task_type=TaskType.CUSTOMER_RESPONSE,
        target_seconds=300,  # 5 minutes
        warning_threshold_pct=0.8,
        critical_threshold_pct=1.0,
        max_threshold_pct=1.3,
    ),
}


class RFQTimeTrackingService(PersistentServiceMixin):
    """
    Service for tracking time spent on RFQ-related tasks.
    
    Provides session-based time tracking with pause/resume capability,
    real-time performance monitoring, and analytics.
    """

    SERVICE_NAME = "rfq_time_tracking"

    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
    
    def __init__(self) -> None:
        """Initialize the time tracking service."""
        self._sessions: dict[UUID, TaskSession] = {}
        self._sessions_by_entity: dict[UUID, list[UUID]] = {}
        self._sessions_by_user: dict[UUID, list[UUID]] = {}
        self._alerts: dict[UUID, TimeAlert] = {}
        self._alerts_by_session: dict[UUID, list[UUID]] = {}
        self._task_targets: dict[TaskType, TaskTarget] = DEFAULT_TASK_TARGETS.copy()
        self._listeners: list[Callable[[TimeAlert], None]] = []
        self._completed_sessions_history: list[TaskSession] = []
        self._max_history_size = 10000
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        state = await self.load_state(self._DEFAULT_TENANT_ID, "state")
        if not state:
            self._state_loaded = True
            return

        self._sessions = {
            UUID(session_id): decode_dataclass(session, TaskSession)
            for session_id, session in state.get("sessions", {}).items()
        }
        self._alerts = {
            UUID(alert_id): decode_dataclass(alert, TimeAlert)
            for alert_id, alert in state.get("alerts", {}).items()
        }
        self._task_targets = {
            TaskType(task_type): decode_dataclass(target, TaskTarget)
            for task_type, target in state.get("task_targets", {}).items()
        }
        self._completed_sessions_history = [
            decode_dataclass(session, TaskSession)
            for session in state.get("completed_sessions", [])
        ]
        self._max_history_size = int(state.get("max_history_size", self._max_history_size))

        self._sessions_by_entity = {}
        self._sessions_by_user = {}
        for session in self._sessions.values():
            self._sessions_by_entity.setdefault(session.entity_id, []).append(session.id)
            self._sessions_by_user.setdefault(session.user_id, []).append(session.id)

        self._alerts_by_session = {}
        for alert_id, alert in self._alerts.items():
            self._alerts_by_session.setdefault(alert.session_id, []).append(alert_id)

        self._state_loaded = True

    async def persist_all(self) -> None:
        state = {
            "sessions": {str(session_id): encode_dataclass(session) for session_id, session in self._sessions.items()},
            "alerts": {str(alert_id): encode_dataclass(alert) for alert_id, alert in self._alerts.items()},
            "task_targets": {task_type.value: encode_dataclass(target) for task_type, target in self._task_targets.items()},
            "completed_sessions": [encode_dataclass(session) for session in self._completed_sessions_history],
            "max_history_size": self._max_history_size,
        }
        await self.save_state(self._DEFAULT_TENANT_ID, "state", state)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()
    
    # ===== Session Management =====
    
    def start_session(
        self,
        task_type: TaskType,
        entity_id: UUID,
        user_id: UUID,
        notes: str | None = None,
        metadata: dict | None = None,
    ) -> TaskSession:
        """
        Start a new task session.
        
        Args:
            task_type: Type of task being tracked
            entity_id: ID of the entity (RFQ, Quote, etc.)
            user_id: ID of the user performing the task
            notes: Optional notes
            metadata: Optional metadata
            
        Returns:
            The created TaskSession
        """
        # Check if there's already an active session for this entity/user
        existing = self.get_active_session(entity_id, user_id)
        if existing:
            # Return existing session instead of creating duplicate
            return existing
        
        session = TaskSession(
            id=uuid4(),
            task_type=task_type,
            entity_id=entity_id,
            user_id=user_id,
            status=TaskSessionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
            notes=notes,
            metadata=metadata or {},
        )
        
        self._sessions[session.id] = session
        
        # Index by entity
        if entity_id not in self._sessions_by_entity:
            self._sessions_by_entity[entity_id] = []
        self._sessions_by_entity[entity_id].append(session.id)
        
        # Index by user
        if user_id not in self._sessions_by_user:
            self._sessions_by_user[user_id] = []
        self._sessions_by_user[user_id].append(session.id)
        
        return session

    async def start_session_async(self, *args: Any, **kwargs: Any) -> TaskSession:
        await self._ensure_loaded()
        session = self.start_session(*args, **kwargs)
        await self.persist_all()
        return session
    
    def pause_session(
        self,
        session_id: UUID,
        reason: str | None = None,
    ) -> TaskSession | None:
        """
        Pause an active session.
        
        Args:
            session_id: ID of the session to pause
            reason: Optional reason for pausing
            
        Returns:
            Updated TaskSession or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.status != TaskSessionStatus.ACTIVE:
            return session
        
        if session.is_currently_paused:
            return session
        
        pause = PauseRecord(
            paused_at=datetime.now(timezone.utc),
            reason=reason,
        )
        session.pauses.append(pause)
        session.status = TaskSessionStatus.PAUSED
        
        return session

    async def pause_session_async(self, *args: Any, **kwargs: Any) -> TaskSession | None:
        await self._ensure_loaded()
        session = self.pause_session(*args, **kwargs)
        await self.persist_all()
        return session
    
    def resume_session(self, session_id: UUID) -> TaskSession | None:
        """
        Resume a paused session.
        
        Args:
            session_id: ID of the session to resume
            
        Returns:
            Updated TaskSession or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.status != TaskSessionStatus.PAUSED:
            return session
        
        if not session.is_currently_paused:
            return session
        
        # Resume the last pause
        session.pauses[-1].resumed_at = datetime.now(timezone.utc)
        session.status = TaskSessionStatus.ACTIVE
        
        return session

    async def resume_session_async(self, session_id: UUID) -> TaskSession | None:
        await self._ensure_loaded()
        session = self.resume_session(session_id)
        await self.persist_all()
        return session
    
    def complete_session(
        self,
        session_id: UUID,
        notes: str | None = None,
    ) -> TaskSession | None:
        """
        Complete a session.
        
        Args:
            session_id: ID of the session to complete
            notes: Optional completion notes
            
        Returns:
            Updated TaskSession or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.status in (TaskSessionStatus.COMPLETED, TaskSessionStatus.ABANDONED):
            return session
        
        # If paused, resume first to close the pause record
        if session.is_currently_paused:
            session.pauses[-1].resumed_at = datetime.now(timezone.utc)
        
        session.completed_at = datetime.now(timezone.utc)
        session.status = TaskSessionStatus.COMPLETED
        
        if notes:
            session.notes = notes
        
        # Archive to history
        self._archive_session(session)
        
        return session

    async def complete_session_async(self, *args: Any, **kwargs: Any) -> TaskSession | None:
        await self._ensure_loaded()
        session = self.complete_session(*args, **kwargs)
        await self.persist_all()
        return session
    
    def abandon_session(
        self,
        session_id: UUID,
        reason: str | None = None,
    ) -> TaskSession | None:
        """
        Abandon a session.
        
        Args:
            session_id: ID of the session to abandon
            reason: Optional reason for abandoning
            
        Returns:
            Updated TaskSession or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.status in (TaskSessionStatus.COMPLETED, TaskSessionStatus.ABANDONED):
            return session
        
        # Close any open pause
        if session.is_currently_paused:
            session.pauses[-1].resumed_at = datetime.now(timezone.utc)
        
        session.completed_at = datetime.now(timezone.utc)
        session.status = TaskSessionStatus.ABANDONED
        
        if reason:
            session.metadata["abandon_reason"] = reason
        
        # Archive to history
        self._archive_session(session)
        
        return session

    async def abandon_session_async(self, *args: Any, **kwargs: Any) -> TaskSession | None:
        await self._ensure_loaded()
        session = self.abandon_session(*args, **kwargs)
        await self.persist_all()
        return session
    
    def _archive_session(self, session: TaskSession) -> None:
        """Archive a completed/abandoned session to history."""
        self._completed_sessions_history.append(session)
        
        # Trim history if needed
        if len(self._completed_sessions_history) > self._max_history_size:
            self._completed_sessions_history = self._completed_sessions_history[-self._max_history_size:]
    
    def get_session(self, session_id: UUID) -> TaskSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_active_session(
        self,
        entity_id: UUID,
        user_id: UUID,
    ) -> TaskSession | None:
        """Get active session for an entity and user."""
        session_ids = self._sessions_by_entity.get(entity_id, [])
        for sid in session_ids:
            session = self._sessions.get(sid)
            if session and session.user_id == user_id and session.status in (
                TaskSessionStatus.ACTIVE,
                TaskSessionStatus.PAUSED,
            ):
                return session
        return None
    
    def get_user_active_sessions(self, user_id: UUID) -> list[TaskSession]:
        """Get all active sessions for a user."""
        session_ids = self._sessions_by_user.get(user_id, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions and self._sessions[sid].status in (
                TaskSessionStatus.ACTIVE,
                TaskSessionStatus.PAUSED,
            )
        ]
    
    def get_entity_sessions(self, entity_id: UUID) -> list[TaskSession]:
        """Get all sessions for an entity."""
        session_ids = self._sessions_by_entity.get(entity_id, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions
        ]
    
    # ===== Real-time Monitoring =====
    
    def check_session_status(self, session_id: UUID) -> dict:
        """
        Check current status of a session with real-time metrics.
        
        Returns:
            Dict with elapsed time, performance level, and alerts
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        elapsed = session.active_elapsed_seconds
        target = self._task_targets.get(session.task_type)
        
        result: dict[str, Any] = {
            "session_id": str(session.id),
            "task_type": session.task_type.value,
            "status": session.status.value,
            "elapsed_seconds": elapsed,
            "elapsed_formatted": self._format_duration(elapsed),
            "is_paused": session.is_currently_paused,
            "pause_count": len(session.pauses),
            "total_pause_seconds": session.total_pause_seconds,
        }
        
        if target:
            result.update({
                "target_seconds": target.target_seconds,
                "target_formatted": self._format_duration(target.target_seconds),
                "remaining_seconds": max(0, target.target_seconds - elapsed),
                "remaining_formatted": self._format_duration(max(0, target.target_seconds - elapsed)),
                "percentage_used": round((elapsed / target.target_seconds) * 100, 1) if target.target_seconds > 0 else 0,
                "performance_level": target.get_performance_level(elapsed).value,
            })
            
            # Check for alerts
            self._check_and_generate_alerts(session, target, elapsed)
        
        return result
    
    def _check_and_generate_alerts(
        self,
        session: TaskSession,
        target: TaskTarget,
        elapsed: int,
    ) -> None:
        """Check thresholds and generate alerts if needed."""
        existing_alerts = self._alerts_by_session.get(session.id, [])
        existing_types = {self._alerts[aid].alert_type for aid in existing_alerts if aid in self._alerts}
        
        alerts_to_create = []
        
        if elapsed >= target.max_seconds and "exceeded" not in existing_types:
            alerts_to_create.append(("exceeded", target.max_seconds, 
                f"Task exceeded maximum time ({self._format_duration(target.max_seconds)})"))
        elif elapsed >= target.critical_seconds and "critical" not in existing_types:
            alerts_to_create.append(("critical", target.critical_seconds,
                f"Task at target time ({self._format_duration(target.critical_seconds)}) - action needed"))
        elif elapsed >= target.warning_seconds and "warning" not in existing_types:
            alerts_to_create.append(("warning", target.warning_seconds,
                f"Task approaching target ({self._format_duration(target.warning_seconds)})"))
        
        for alert_type, threshold, message in alerts_to_create:
            self._create_alert(session, alert_type, threshold, elapsed, message)
    
    def _create_alert(
        self,
        session: TaskSession,
        alert_type: str,
        threshold: int,
        elapsed: int,
        message: str,
    ) -> TimeAlert:
        """Create and store a time alert."""
        alert = TimeAlert(
            id=uuid4(),
            session_id=session.id,
            task_type=session.task_type,
            alert_type=alert_type,
            threshold_seconds=threshold,
            elapsed_seconds=elapsed,
            created_at=datetime.now(timezone.utc),
            message=message,
        )
        
        self._alerts[alert.id] = alert
        
        if session.id not in self._alerts_by_session:
            self._alerts_by_session[session.id] = []
        self._alerts_by_session[session.id].append(alert.id)
        
        # Notify listeners
        for listener in self._listeners:
            try:
                listener(alert)
            except Exception:
                logger.exception("RFQ time tracking listener failed for alert %s", alert.id)
        
        return alert
    
    def get_session_alerts(self, session_id: UUID) -> list[TimeAlert]:
        """Get all alerts for a session."""
        alert_ids = self._alerts_by_session.get(session_id, [])
        return [self._alerts[aid] for aid in alert_ids if aid in self._alerts]
    
    def acknowledge_alert(
        self,
        alert_id: UUID,
        user_id: UUID,
    ) -> TimeAlert | None:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id
        
        return alert

    async def acknowledge_alert_async(self, alert_id: UUID, user_id: UUID) -> TimeAlert | None:
        await self._ensure_loaded()
        alert = self.acknowledge_alert(alert_id, user_id)
        await self.persist_all()
        return alert
    
    def get_pending_alerts(self, user_id: UUID | None = None) -> list[TimeAlert]:
        """Get all pending (unacknowledged) alerts, optionally filtered by user."""
        result = []
        
        for alert in self._alerts.values():
            if alert.acknowledged:
                continue
            
            if user_id:
                session = self._sessions.get(alert.session_id)
                if session and session.user_id != user_id:
                    continue
            
            result.append(alert)
        
        return sorted(result, key=lambda a: a.created_at, reverse=True)
    
    def add_alert_listener(self, callback: Callable[[TimeAlert], None]) -> None:
        """Add a listener for alert events."""
        self._listeners.append(callback)
    
    def remove_alert_listener(self, callback: Callable[[TimeAlert], None]) -> None:
        """Remove an alert listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    # ===== Target Management =====
    
    def get_target(self, task_type: TaskType) -> TaskTarget | None:
        """Get target for a task type."""
        return self._task_targets.get(task_type)
    
    def set_target(self, target: TaskTarget) -> None:
        """Set or update a task target."""
        self._task_targets[target.task_type] = target

    async def set_target_async(self, target: TaskTarget) -> None:
        await self._ensure_loaded()
        self.set_target(target)
        await self.persist_all()
    
    def get_all_targets(self) -> dict[TaskType, TaskTarget]:
        """Get all task targets."""
        return self._task_targets.copy()
    
    # ===== Analytics =====
    
    def get_performance_stats(
        self,
        task_type: TaskType,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_id: UUID | None = None,
    ) -> TaskPerformanceStats | None:
        """
        Get performance statistics for a task type.
        
        Args:
            task_type: Type of task
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: now)
            user_id: Filter by user (optional)
            
        Returns:
            TaskPerformanceStats or None if no data
        """
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now
        
        # Collect sessions
        sessions = []
        
        # From history
        for session in self._completed_sessions_history:
            if session.task_type != task_type:
                continue
            if session.started_at < start or session.started_at > end:
                continue
            if user_id and session.user_id != user_id:
                continue
            sessions.append(session)
        
        # From active sessions (completed ones)
        for session in self._sessions.values():
            if session.task_type != task_type:
                continue
            if session.status not in (TaskSessionStatus.COMPLETED, TaskSessionStatus.ABANDONED):
                continue
            if session.started_at < start or session.started_at > end:
                continue
            if user_id and session.user_id != user_id:
                continue
            if session not in sessions:
                sessions.append(session)
        
        if not sessions:
            return None
        
        # Calculate statistics
        completed = [s for s in sessions if s.status == TaskSessionStatus.COMPLETED]
        abandoned = [s for s in sessions if s.status == TaskSessionStatus.ABANDONED]
        
        durations = [s.active_elapsed_seconds for s in completed]
        target = self._task_targets.get(task_type)
        target_seconds = target.target_seconds if target else 600
        
        if not durations:
            return TaskPerformanceStats(
                task_type=task_type,
                period_start=start,
                period_end=end,
                total_sessions=len(sessions),
                completed_sessions=0,
                abandoned_sessions=len(abandoned),
                average_duration_seconds=0,
                median_duration_seconds=0,
                min_duration_seconds=0,
                max_duration_seconds=0,
                p90_duration_seconds=0,
                target_seconds=target_seconds,
                sessions_under_target=0,
                sessions_over_target=0,
                target_compliance_rate=0,
            )
        
        sorted_durations = sorted(durations)
        
        return TaskPerformanceStats(
            task_type=task_type,
            period_start=start,
            period_end=end,
            total_sessions=len(sessions),
            completed_sessions=len(completed),
            abandoned_sessions=len(abandoned),
            average_duration_seconds=sum(durations) / len(durations),
            median_duration_seconds=sorted_durations[len(sorted_durations) // 2],
            min_duration_seconds=min(durations),
            max_duration_seconds=max(durations),
            p90_duration_seconds=sorted_durations[int(len(sorted_durations) * 0.9)] if len(sorted_durations) > 0 else 0,
            target_seconds=target_seconds,
            sessions_under_target=sum(1 for d in durations if d <= target_seconds),
            sessions_over_target=sum(1 for d in durations if d > target_seconds),
            target_compliance_rate=(sum(1 for d in durations if d <= target_seconds) / len(durations)) * 100,
        )
    
    def get_user_efficiency(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> UserEfficiencyMetrics | None:
        """
        Get efficiency metrics for a user.
        
        Args:
            user_id: User ID
            start_date: Start of period
            end_date: End of period
            
        Returns:
            UserEfficiencyMetrics or None if no data
        """
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now
        
        metrics_by_task: dict[TaskType, TaskPerformanceStats] = {}
        
        for task_type in TaskType:
            stats = self.get_performance_stats(task_type, start, end, user_id)
            if stats and stats.total_sessions > 0:
                metrics_by_task[task_type] = stats
        
        if not metrics_by_task:
            return None
        
        # Calculate overall metrics
        total_sessions = sum(s.total_sessions for s in metrics_by_task.values())
        total_active_time = sum(
            s.average_duration_seconds * s.completed_sessions
            for s in metrics_by_task.values()
        )
        
        # Efficiency score based on compliance rates
        weighted_compliance = sum(
            s.target_compliance_rate * s.completed_sessions
            for s in metrics_by_task.values()
        )
        total_completed = sum(s.completed_sessions for s in metrics_by_task.values())
        efficiency_score = weighted_compliance / total_completed if total_completed > 0 else 0
        
        # Trend calculation (compare first half vs second half)
        mid = start + (end - start) / 2
        
        first_half_compliance: float = 0.0
        second_half_compliance: float = 0.0
        first_half_count = 0
        second_half_count = 0
        
        for task_type in metrics_by_task:
            first_stats = self.get_performance_stats(task_type, start, mid, user_id)
            second_stats = self.get_performance_stats(task_type, mid, end, user_id)
            
            if first_stats and first_stats.completed_sessions > 0:
                first_half_compliance += first_stats.target_compliance_rate
                first_half_count += 1
            if second_stats and second_stats.completed_sessions > 0:
                second_half_compliance += second_stats.target_compliance_rate
                second_half_count += 1
        
        if first_half_count > 0 and second_half_count > 0:
            first_avg = first_half_compliance / first_half_count
            second_avg = second_half_compliance / second_half_count
            diff = second_avg - first_avg
            if diff > 5:
                trend = "improving"
            elif diff < -5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return UserEfficiencyMetrics(
            user_id=user_id,
            period_start=start,
            period_end=end,
            metrics_by_task=metrics_by_task,
            total_active_time_seconds=int(total_active_time),
            total_sessions=total_sessions,
            efficiency_score=efficiency_score,
            trend=trend,
        )
    
    def get_daily_breakdown(
        self,
        task_type: TaskType,
        start_date: datetime,
        end_date: datetime,
    ) -> list[DailyTimeBreakdown]:
        """
        Get daily breakdown of task performance.
        
        Args:
            task_type: Type of task
            start_date: Start date
            end_date: End date
            
        Returns:
            List of DailyTimeBreakdown for each day
        """
        result = []
        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        target = self._task_targets.get(task_type)
        target_seconds = target.target_seconds if target else 600
        
        while current <= end_date:
            day_end = current + timedelta(days=1)
            
            # Get sessions for this day
            day_sessions = []
            
            for session in self._completed_sessions_history:
                if session.task_type != task_type:
                    continue
                if session.started_at < current or session.started_at >= day_end:
                    continue
                day_sessions.append(session)
            
            for session in self._sessions.values():
                if session.task_type != task_type:
                    continue
                if session.started_at < current or session.started_at >= day_end:
                    continue
                day_sessions.append(session)
            
            completed = [s for s in day_sessions if s.status == TaskSessionStatus.COMPLETED]
            durations = [s.active_elapsed_seconds for s in completed]
            
            result.append(DailyTimeBreakdown(
                date=current,
                task_type=task_type,
                total_sessions=len(day_sessions),
                completed_sessions=len(completed),
                total_active_seconds=sum(durations),
                average_duration_seconds=sum(durations) / len(durations) if durations else 0,
                under_target_count=sum(1 for d in durations if d <= target_seconds),
                over_target_count=sum(1 for d in durations if d > target_seconds),
            ))
            
            current = day_end
        
        return result
    
    def get_leaderboard(
        self,
        task_type: TaskType,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get leaderboard of users by task completion efficiency.
        
        Args:
            task_type: Type of task
            start_date: Start of period
            end_date: End of period
            limit: Maximum number of users to return
            
        Returns:
            List of user efficiency data, sorted by efficiency score
        """
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now
        
        # Collect all users who have sessions
        user_ids: set[UUID] = set()
        
        for session in self._completed_sessions_history:
            if session.task_type == task_type and start <= session.started_at <= end:
                user_ids.add(session.user_id)
        
        for session in self._sessions.values():
            if session.task_type == task_type and start <= session.started_at <= end:
                user_ids.add(session.user_id)
        
        # Get stats for each user
        user_stats: list[dict[str, Any]] = []
        
        for uid in user_ids:
            stats = self.get_performance_stats(task_type, start, end, uid)
            if stats and stats.completed_sessions > 0:
                user_stats.append({
                    "user_id": str(uid),
                    "completed_sessions": stats.completed_sessions,
                    "average_duration_seconds": stats.average_duration_seconds,
                    "target_compliance_rate": stats.target_compliance_rate,
                    "efficiency_rank": 0,  # Will be set below
                })
        
        # Sort by compliance rate (higher is better)
        user_stats.sort(key=lambda x: x["target_compliance_rate"], reverse=True)
        
        # Set ranks
        for i, user_stat in enumerate(user_stats[:limit]):
            user_stat["efficiency_rank"] = i + 1
        
        return user_stats[:limit]
    
    # ===== Utility Methods =====
    
    def _format_duration(self, seconds: int) -> str:
        """Format seconds as human-readable duration."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
    
    def get_rfq_intake_summary(
        self,
        rfq_id: UUID,
    ) -> dict:
        """
        Get summary of all time tracking for an RFQ.
        
        Args:
            rfq_id: RFQ ID
            
        Returns:
            Summary dict with all session data
        """
        sessions = self.get_entity_sessions(rfq_id)
        
        completed = [s for s in sessions if s.status == TaskSessionStatus.COMPLETED]
        active = [s for s in sessions if s.status in (TaskSessionStatus.ACTIVE, TaskSessionStatus.PAUSED)]
        abandoned = [s for s in sessions if s.status == TaskSessionStatus.ABANDONED]
        
        total_time = sum(s.active_elapsed_seconds for s in completed)
        target = self._task_targets.get(TaskType.RFQ_INTAKE)
        
        return {
            "rfq_id": str(rfq_id),
            "total_sessions": len(sessions),
            "completed_sessions": len(completed),
            "active_sessions": len(active),
            "abandoned_sessions": len(abandoned),
            "total_active_time_seconds": total_time,
            "total_active_time_formatted": self._format_duration(total_time),
            "target_seconds": target.target_seconds if target else 600,
            "target_formatted": self._format_duration(target.target_seconds if target else 600),
            "within_target": total_time <= (target.target_seconds if target else 600),
            "sessions": [s.to_dict() for s in sessions],
        }
    
    def cleanup_expired_sessions(
        self,
        max_age_hours: int = 24,
    ) -> int:
        """
        Clean up abandoned/expired sessions older than max_age.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_age_hours)
        
        to_expire = []
        
        for session in self._sessions.values():
            if session.status in (TaskSessionStatus.ACTIVE, TaskSessionStatus.PAUSED):
                if session.started_at < cutoff:
                    to_expire.append(session.id)
        
        for sid in to_expire:
            expiring_session = self._sessions.get(sid)
            if expiring_session:
                expiring_session.status = TaskSessionStatus.EXPIRED
                expiring_session.completed_at = now
                self._archive_session(expiring_session)
        
        return len(to_expire)
    
    def reset(self) -> None:
        """Reset all tracking data (for testing)."""
        self._sessions.clear()
        self._sessions_by_entity.clear()
        self._sessions_by_user.clear()
        self._alerts.clear()
        self._alerts_by_session.clear()
        self._completed_sessions_history.clear()
        self._task_targets = DEFAULT_TASK_TARGETS.copy()
        self._listeners.clear()


# Singleton instance
_service_instance: RFQTimeTrackingService | None = None


def get_rfq_time_tracking_service() -> RFQTimeTrackingService:
    """Get the singleton RFQ time tracking service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RFQTimeTrackingService()
    return _service_instance


def reset_rfq_time_tracking_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _service_instance
    if _service_instance:
        _service_instance.reset()
    _service_instance = None
