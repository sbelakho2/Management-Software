"""
Stale Detection Service for Sensei OS.

Implements background job logic to detect and flag stale entities:
- Opportunities with no activity for X days
- RFQs stuck in a status too long
- Tasks past their due date

Designed to be called periodically (e.g., daily) via a job scheduler.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID


class EntityType(str, Enum):
    """Entity types that support stale detection."""
    
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    TASK = "task"


class StaleReason(str, Enum):
    """Reason why an entity is considered stale."""
    
    NO_ACTIVITY = "no_activity"
    STUCK_IN_STATUS = "stuck_in_status"
    OVERDUE = "overdue"
    NO_NEXT_STEP = "no_next_step"
    NEXT_STEP_OVERDUE = "next_step_overdue"
    WAITING_TOO_LONG = "waiting_too_long"


class StaleSeverity(str, Enum):
    """Severity level of staleness."""
    
    LOW = "low"          # Just became stale (warning)
    MEDIUM = "medium"    # Been stale for a while
    HIGH = "high"        # Critical - needs immediate attention
    CRITICAL = "critical"  # Escalation needed


@dataclass
class StaleThreshold:
    """
    Configuration for stale detection thresholds.
    
    Attributes:
        days_until_stale: Days of inactivity before marking as stale
        severity_escalation_days: Additional days for each severity level increase
        applies_to_statuses: List of statuses this threshold applies to (None = all)
        excluded_statuses: List of statuses to exclude from stale detection
    """
    days_until_stale: int
    severity_escalation_days: int = 7  # Days between severity escalations
    applies_to_statuses: list[str] | None = None
    excluded_statuses: list[str] = field(default_factory=list)
    reason: StaleReason = StaleReason.NO_ACTIVITY


@dataclass
class StaleEntity:
    """
    Represents a detected stale entity.
    
    Attributes:
        entity_id: UUID of the stale entity
        entity_type: Type of entity
        entity_name: Human-readable name/identifier
        reason: Why it's considered stale
        severity: Current severity level
        days_stale: Number of days entity has been stale
        last_activity_at: When the entity was last updated
        status: Current status of the entity
        owner_id: UUID of the entity owner (if applicable)
        owner_name: Name of the owner
        account_name: Associated account name (if applicable)
        suggested_action: Recommended action to take
        metadata: Additional context-specific data
    """
    entity_id: UUID
    entity_type: EntityType
    entity_name: str
    reason: StaleReason
    severity: StaleSeverity
    days_stale: int
    last_activity_at: datetime
    status: str
    owner_id: UUID | None = None
    owner_name: str | None = None
    account_name: str | None = None
    suggested_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StaleDetectionResult:
    """
    Result of a stale detection scan.
    
    Attributes:
        scanned_at: When the scan was performed
        entity_type: Type of entities scanned
        total_scanned: Total number of entities examined
        stale_count: Number of stale entities found
        stale_entities: List of detected stale entities
        thresholds_used: Thresholds configuration used for detection
        scan_duration_ms: How long the scan took in milliseconds
    """
    scanned_at: datetime
    entity_type: EntityType
    total_scanned: int
    stale_count: int
    stale_entities: list[StaleEntity]
    thresholds_used: dict[str, Any]
    scan_duration_ms: float = 0.0
    
    @property
    def by_severity(self) -> dict[StaleSeverity, list[StaleEntity]]:
        """Group stale entities by severity level."""
        result: dict[StaleSeverity, list[StaleEntity]] = {
            severity: [] for severity in StaleSeverity
        }
        for entity in self.stale_entities:
            result[entity.severity].append(entity)
        return result
    
    @property
    def critical_count(self) -> int:
        """Count of critical severity stale entities."""
        return sum(1 for e in self.stale_entities if e.severity == StaleSeverity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        """Count of high severity stale entities."""
        return sum(1 for e in self.stale_entities if e.severity == StaleSeverity.HIGH)


class StaleDetectionService:
    """
    Service for detecting stale entities across the system.
    
    Provides configurable thresholds per entity type and status,
    with severity escalation based on how long an entity has been stale.
    
    Example usage:
        service = StaleDetectionService()
        
        # Check specific opportunities
        result = service.detect_stale_opportunities(opportunities, reference_time)
        
        # Get only critical/high severity
        urgent = [e for e in result.stale_entities 
                  if e.severity in (StaleSeverity.CRITICAL, StaleSeverity.HIGH)]
    """
    
    # Default thresholds - can be overridden via constructor
    DEFAULT_OPPORTUNITY_THRESHOLDS: dict[str, StaleThreshold] = {
        "default": StaleThreshold(
            days_until_stale=7,
            severity_escalation_days=7,
            excluded_statuses=["closed_won", "closed_lost"],
            reason=StaleReason.NO_ACTIVITY,
        ),
        "prospecting": StaleThreshold(
            days_until_stale=5,
            severity_escalation_days=5,
            reason=StaleReason.NO_ACTIVITY,
        ),
        "qualification": StaleThreshold(
            days_until_stale=3,
            severity_escalation_days=3,
            reason=StaleReason.NO_ACTIVITY,
        ),
        "proposal": StaleThreshold(
            days_until_stale=5,
            severity_escalation_days=5,
            reason=StaleReason.STUCK_IN_STATUS,
        ),
        "negotiation": StaleThreshold(
            days_until_stale=7,
            severity_escalation_days=7,
            reason=StaleReason.STUCK_IN_STATUS,
        ),
    }
    
    DEFAULT_RFQ_THRESHOLDS: dict[str, StaleThreshold] = {
        "default": StaleThreshold(
            days_until_stale=5,
            severity_escalation_days=5,
            excluded_statuses=["won", "lost", "no_bid", "cancelled", "expired"],
            reason=StaleReason.NO_ACTIVITY,
        ),
        "received": StaleThreshold(
            days_until_stale=2,
            severity_escalation_days=2,
            reason=StaleReason.NO_ACTIVITY,
        ),
        "under_review": StaleThreshold(
            days_until_stale=3,
            severity_escalation_days=3,
            reason=StaleReason.STUCK_IN_STATUS,
        ),
        "questions_pending": StaleThreshold(
            days_until_stale=3,
            severity_escalation_days=5,
            reason=StaleReason.WAITING_TOO_LONG,
        ),
        "qualifying": StaleThreshold(
            days_until_stale=5,
            severity_escalation_days=3,
            reason=StaleReason.STUCK_IN_STATUS,
        ),
        "quoting": StaleThreshold(
            days_until_stale=7,
            severity_escalation_days=5,
            reason=StaleReason.STUCK_IN_STATUS,
        ),
    }
    
    DEFAULT_TASK_THRESHOLDS: dict[str, StaleThreshold] = {
        "default": StaleThreshold(
            days_until_stale=3,
            severity_escalation_days=3,
            excluded_statuses=["done", "cancelled"],
            reason=StaleReason.NO_ACTIVITY,
        ),
        "todo": StaleThreshold(
            days_until_stale=7,
            severity_escalation_days=7,
            reason=StaleReason.NO_ACTIVITY,
        ),
        "in_progress": StaleThreshold(
            days_until_stale=3,
            severity_escalation_days=3,
            reason=StaleReason.NO_ACTIVITY,
        ),
        "blocked": StaleThreshold(
            days_until_stale=2,
            severity_escalation_days=2,
            reason=StaleReason.STUCK_IN_STATUS,
        ),
        "in_review": StaleThreshold(
            days_until_stale=2,
            severity_escalation_days=2,
            reason=StaleReason.WAITING_TOO_LONG,
        ),
    }
    
    def __init__(
        self,
        opportunity_thresholds: dict[str, StaleThreshold] | None = None,
        rfq_thresholds: dict[str, StaleThreshold] | None = None,
        task_thresholds: dict[str, StaleThreshold] | None = None,
    ):
        """
        Initialize the stale detection service.
        
        Args:
            opportunity_thresholds: Custom thresholds for opportunities
            rfq_thresholds: Custom thresholds for RFQs
            task_thresholds: Custom thresholds for tasks
        """
        self.opportunity_thresholds = opportunity_thresholds or self.DEFAULT_OPPORTUNITY_THRESHOLDS.copy()
        self.rfq_thresholds = rfq_thresholds or self.DEFAULT_RFQ_THRESHOLDS.copy()
        self.task_thresholds = task_thresholds or self.DEFAULT_TASK_THRESHOLDS.copy()
    
    def _get_threshold(
        self,
        thresholds: dict[str, StaleThreshold],
        status: str,
    ) -> StaleThreshold | None:
        """
        Get the appropriate threshold for a given status.
        
        Returns:
            The status-specific threshold, default threshold, or None if excluded.
        """
        # Check for status-specific threshold
        if status in thresholds:
            return thresholds[status]
        
        # Fall back to default
        default = thresholds.get("default")
        if default:
            # Check if status is excluded from default
            if status in default.excluded_statuses:
                return None
            return default
        
        return None
    
    def _calculate_severity(
        self,
        days_stale: int,
        threshold: StaleThreshold,
    ) -> StaleSeverity:
        """
        Calculate severity based on how long the entity has been stale.
        
        Severity escalates based on severity_escalation_days intervals.
        """
        if days_stale < threshold.days_until_stale:
            # Not yet stale - shouldn't happen but handle gracefully
            return StaleSeverity.LOW
        
        # Days beyond the initial stale threshold
        extra_days = days_stale - threshold.days_until_stale
        escalation_level = extra_days // threshold.severity_escalation_days
        
        if escalation_level == 0:
            return StaleSeverity.LOW
        elif escalation_level == 1:
            return StaleSeverity.MEDIUM
        elif escalation_level == 2:
            return StaleSeverity.HIGH
        else:
            return StaleSeverity.CRITICAL
    
    def _get_suggested_action(
        self,
        entity_type: EntityType,
        reason: StaleReason,
        status: str,
        severity: StaleSeverity,
    ) -> str:
        """Generate a suggested action based on the stale entity context."""
        if severity == StaleSeverity.CRITICAL:
            prefix = "URGENT: "
        elif severity == StaleSeverity.HIGH:
            prefix = "Priority: "
        else:
            prefix = ""
        
        if entity_type == EntityType.OPPORTUNITY:
            if reason == StaleReason.NO_NEXT_STEP:
                return f"{prefix}Define next step and date for this opportunity"
            elif reason == StaleReason.NEXT_STEP_OVERDUE:
                return f"{prefix}Complete or reschedule the overdue next step"
            elif status == "prospecting":
                return f"{prefix}Qualify or disqualify this prospect"
            elif status == "proposal":
                return f"{prefix}Follow up on proposal status"
            elif status == "negotiation":
                return f"{prefix}Advance negotiations or update status"
            else:
                return f"{prefix}Review and update opportunity status"
        
        elif entity_type == EntityType.RFQ:
            if status == "received":
                return f"{prefix}Begin RFQ review and assign to team"
            elif status == "questions_pending":
                return f"{prefix}Follow up on pending customer questions"
            elif status == "qualifying":
                return f"{prefix}Complete qualification process"
            elif status == "quoting":
                return f"{prefix}Complete quote preparation"
            else:
                return f"{prefix}Review and update RFQ status"
        
        elif entity_type == EntityType.TASK:
            if reason == StaleReason.OVERDUE:
                return f"{prefix}Complete overdue task or update due date"
            elif status == "blocked":
                return f"{prefix}Resolve blocker and resume task"
            elif status == "in_review":
                return f"{prefix}Complete task review"
            else:
                return f"{prefix}Update task progress or status"
        
        return f"{prefix}Review and take action"
    
    def detect_stale_opportunities(
        self,
        opportunities: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> StaleDetectionResult:
        """
        Detect stale opportunities from a list of opportunity data.
        
        Args:
            opportunities: List of opportunity dicts with at minimum:
                - id: UUID
                - name: str
                - status/stage: str
                - updated_at: datetime
                Optional fields:
                - owner_id, owner_name, account_name
                - next_step, next_step_date
            reference_time: Point in time to compare against (default: now)
        
        Returns:
            StaleDetectionResult with all stale opportunities
        """
        import time
        start_time = time.time()
        
        if reference_time is None:
            reference_time = datetime.now()
        
        stale_entities: list[StaleEntity] = []
        
        for opp in opportunities:
            opp_id = opp.get("id")
            if not opp_id:
                continue
            
            # Get status - try both "status" and "stage" fields
            status = opp.get("status") or opp.get("stage") or "unknown"
            
            # Get appropriate threshold
            threshold = self._get_threshold(self.opportunity_thresholds, status)
            if threshold is None:
                continue  # Status is excluded
            
            # Get last activity time
            last_activity = opp.get("updated_at")
            if not last_activity:
                continue
            
            # Ensure datetime comparison works
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            
            # Make reference_time offset-naive if last_activity is offset-naive
            ref_time = reference_time
            if last_activity.tzinfo is None and reference_time.tzinfo is not None:
                ref_time = reference_time.replace(tzinfo=None)
            elif last_activity.tzinfo is not None and reference_time.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=None)
            
            # Calculate days since last activity
            days_inactive = (ref_time - last_activity).days
            
            # Check for next_step issues (additional stale reasons)
            reason = threshold.reason
            next_step = opp.get("next_step")
            next_step_date = opp.get("next_step_date")
            
            if not next_step and status not in ["closed_won", "closed_lost"]:
                reason = StaleReason.NO_NEXT_STEP
                # Use shorter threshold for no next step
                effective_threshold = StaleThreshold(
                    days_until_stale=3,
                    severity_escalation_days=3,
                    reason=reason,
                )
            elif next_step_date:
                if isinstance(next_step_date, str):
                    next_step_date = datetime.fromisoformat(next_step_date.replace("Z", "+00:00"))
                if next_step_date.tzinfo is not None:
                    next_step_date = next_step_date.replace(tzinfo=None)
                # Compare against timezone-naive reference time
                ref_time_naive = ref_time.replace(tzinfo=None) if ref_time.tzinfo else ref_time
                if next_step_date < ref_time_naive:
                    reason = StaleReason.NEXT_STEP_OVERDUE
                    days_overdue = (ref_time_naive - next_step_date).days
                    effective_threshold = StaleThreshold(
                        days_until_stale=0,  # Immediately stale when next step is overdue
                        severity_escalation_days=2,
                        reason=reason,
                    )
                    days_inactive = max(days_inactive, days_overdue)
                else:
                    effective_threshold = threshold
            else:
                effective_threshold = threshold
            
            # Check if stale
            if days_inactive >= effective_threshold.days_until_stale:
                severity = self._calculate_severity(days_inactive, effective_threshold)
                
                stale_entity = StaleEntity(
                    entity_id=opp_id if isinstance(opp_id, UUID) else UUID(str(opp_id)),
                    entity_type=EntityType.OPPORTUNITY,
                    entity_name=opp.get("name", f"Opportunity {opp_id}"),
                    reason=reason,
                    severity=severity,
                    days_stale=days_inactive - effective_threshold.days_until_stale,
                    last_activity_at=last_activity,
                    status=status,
                    owner_id=opp.get("owner_id"),
                    owner_name=opp.get("owner_name"),
                    account_name=opp.get("account_name"),
                    suggested_action=self._get_suggested_action(
                        EntityType.OPPORTUNITY, reason, status, severity
                    ),
                    metadata={
                        "opportunity_number": opp.get("opportunity_number"),
                        "amount": opp.get("amount"),
                        "probability": opp.get("probability"),
                        "next_step": next_step,
                        "next_step_date": str(next_step_date) if next_step_date else None,
                    },
                )
                stale_entities.append(stale_entity)
        
        end_time = time.time()
        
        return StaleDetectionResult(
            scanned_at=reference_time,
            entity_type=EntityType.OPPORTUNITY,
            total_scanned=len(opportunities),
            stale_count=len(stale_entities),
            stale_entities=stale_entities,
            thresholds_used={k: {"days": v.days_until_stale, "reason": v.reason.value} 
                            for k, v in self.opportunity_thresholds.items()},
            scan_duration_ms=(end_time - start_time) * 1000,
        )
    
    def detect_stale_rfqs(
        self,
        rfqs: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> StaleDetectionResult:
        """
        Detect stale RFQs from a list of RFQ data.
        
        Args:
            rfqs: List of RFQ dicts with at minimum:
                - id: UUID
                - rfq_number: str
                - status: str
                - updated_at: datetime
                Optional fields:
                - owner_id, owner_name, account_name
                - due_date, quote_due_date
            reference_time: Point in time to compare against (default: now)
        
        Returns:
            StaleDetectionResult with all stale RFQs
        """
        import time
        start_time = time.time()
        
        if reference_time is None:
            reference_time = datetime.now()
        
        stale_entities: list[StaleEntity] = []
        
        for rfq in rfqs:
            rfq_id = rfq.get("id")
            if not rfq_id:
                continue
            
            status = rfq.get("status") or "unknown"
            
            # Get appropriate threshold
            threshold = self._get_threshold(self.rfq_thresholds, status)
            if threshold is None:
                continue  # Status is excluded
            
            # Get last activity time
            last_activity = rfq.get("updated_at")
            if not last_activity:
                continue
            
            # Ensure datetime comparison works
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            
            # Handle timezone
            ref_time = reference_time
            if last_activity.tzinfo is None and reference_time.tzinfo is not None:
                ref_time = reference_time.replace(tzinfo=None)
            elif last_activity.tzinfo is not None and reference_time.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=None)
            
            days_inactive = (ref_time - last_activity).days
            
            # Check if stale
            if days_inactive >= threshold.days_until_stale:
                severity = self._calculate_severity(days_inactive, threshold)
                
                stale_entity = StaleEntity(
                    entity_id=rfq_id if isinstance(rfq_id, UUID) else UUID(str(rfq_id)),
                    entity_type=EntityType.RFQ,
                    entity_name=rfq.get("rfq_number", f"RFQ {rfq_id}"),
                    reason=threshold.reason,
                    severity=severity,
                    days_stale=days_inactive - threshold.days_until_stale,
                    last_activity_at=last_activity,
                    status=status,
                    owner_id=rfq.get("owner_id"),
                    owner_name=rfq.get("owner_name"),
                    account_name=rfq.get("account_name"),
                    suggested_action=self._get_suggested_action(
                        EntityType.RFQ, threshold.reason, status, severity
                    ),
                    metadata={
                        "rfq_number": rfq.get("rfq_number"),
                        "customer_rfq_number": rfq.get("customer_rfq_number"),
                        "due_date": str(rfq.get("due_date")) if rfq.get("due_date") else None,
                        "quote_due_date": str(rfq.get("quote_due_date")) if rfq.get("quote_due_date") else None,
                        "priority": rfq.get("priority"),
                    },
                )
                stale_entities.append(stale_entity)
        
        end_time = time.time()
        
        return StaleDetectionResult(
            scanned_at=reference_time,
            entity_type=EntityType.RFQ,
            total_scanned=len(rfqs),
            stale_count=len(stale_entities),
            stale_entities=stale_entities,
            thresholds_used={k: {"days": v.days_until_stale, "reason": v.reason.value} 
                            for k, v in self.rfq_thresholds.items()},
            scan_duration_ms=(end_time - start_time) * 1000,
        )
    
    def detect_stale_tasks(
        self,
        tasks: list[dict[str, Any]],
        reference_time: datetime | None = None,
    ) -> StaleDetectionResult:
        """
        Detect stale tasks from a list of task data.
        
        Args:
            tasks: List of task dicts with at minimum:
                - id: UUID
                - title: str
                - status: str
                - updated_at: datetime
                Optional fields:
                - assignee_id, assignee_name
                - due_date
            reference_time: Point in time to compare against (default: now)
        
        Returns:
            StaleDetectionResult with all stale tasks
        """
        import time
        start_time = time.time()
        
        if reference_time is None:
            reference_time = datetime.now()
        
        stale_entities: list[StaleEntity] = []
        
        for task in tasks:
            task_id = task.get("id")
            if not task_id:
                continue
            
            status = task.get("status") or "unknown"
            
            # Get appropriate threshold
            threshold = self._get_threshold(self.task_thresholds, status)
            if threshold is None:
                continue  # Status is excluded
            
            # Get last activity time
            last_activity = task.get("updated_at")
            if not last_activity:
                continue
            
            # Ensure datetime comparison works
            if isinstance(last_activity, str):
                last_activity = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            
            # Handle timezone
            ref_time = reference_time
            if last_activity.tzinfo is None and reference_time.tzinfo is not None:
                ref_time = reference_time.replace(tzinfo=None)
            elif last_activity.tzinfo is not None and reference_time.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=None)
            
            days_inactive = (ref_time - last_activity).days
            
            # Check for overdue tasks
            reason = threshold.reason
            effective_threshold = threshold
            due_date = task.get("due_date")
            
            if due_date:
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                if due_date.tzinfo is not None:
                    due_date = due_date.replace(tzinfo=None)
                
                ref_naive = ref_time.replace(tzinfo=None) if ref_time.tzinfo else ref_time
                if due_date < ref_naive:
                    reason = StaleReason.OVERDUE
                    days_overdue = (ref_naive - due_date).days
                    effective_threshold = StaleThreshold(
                        days_until_stale=0,  # Immediately stale when overdue
                        severity_escalation_days=2,
                        reason=reason,
                    )
                    days_inactive = days_overdue
            
            # Check if stale
            if days_inactive >= effective_threshold.days_until_stale:
                severity = self._calculate_severity(days_inactive, effective_threshold)
                
                stale_entity = StaleEntity(
                    entity_id=task_id if isinstance(task_id, UUID) else UUID(str(task_id)),
                    entity_type=EntityType.TASK,
                    entity_name=task.get("title", f"Task {task_id}"),
                    reason=reason,
                    severity=severity,
                    days_stale=days_inactive - effective_threshold.days_until_stale,
                    last_activity_at=last_activity,
                    status=status,
                    owner_id=task.get("assignee_id"),
                    owner_name=task.get("assignee_name"),
                    suggested_action=self._get_suggested_action(
                        EntityType.TASK, reason, status, severity
                    ),
                    metadata={
                        "task_type": task.get("task_type"),
                        "priority": task.get("priority"),
                        "due_date": str(due_date) if due_date else None,
                        "entity_type": task.get("entity_type"),
                        "entity_id": str(task.get("entity_id")) if task.get("entity_id") else None,
                    },
                )
                stale_entities.append(stale_entity)
        
        end_time = time.time()
        
        return StaleDetectionResult(
            scanned_at=reference_time,
            entity_type=EntityType.TASK,
            total_scanned=len(tasks),
            stale_count=len(stale_entities),
            stale_entities=stale_entities,
            thresholds_used={k: {"days": v.days_until_stale, "reason": v.reason.value} 
                            for k, v in self.task_thresholds.items()},
            scan_duration_ms=(end_time - start_time) * 1000,
        )
    
    def get_thresholds(self, entity_type: EntityType) -> dict[str, StaleThreshold]:
        """Get the configured thresholds for an entity type."""
        if entity_type == EntityType.OPPORTUNITY:
            return self.opportunity_thresholds
        elif entity_type == EntityType.RFQ:
            return self.rfq_thresholds
        elif entity_type == EntityType.TASK:
            return self.task_thresholds
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
    
    def update_threshold(
        self,
        entity_type: EntityType,
        status: str,
        threshold: StaleThreshold,
    ) -> None:
        """Update the threshold for a specific entity type and status."""
        thresholds = self.get_thresholds(entity_type)
        thresholds[status] = threshold


class StaleDetectionJobRunner:
    """
    Job runner for scheduled stale detection.
    
    Coordinates running stale detection across all entity types
    and handling the results (creating tasks, sending notifications, etc.).
    
    Designed to be called by a scheduler (e.g., Celery, APScheduler).
    """
    
    def __init__(
        self,
        service: StaleDetectionService | None = None,
        create_task_callback: Any = None,
        create_notification_callback: Any = None,
    ):
        """
        Initialize the job runner.
        
        Args:
            service: StaleDetectionService instance (creates default if not provided)
            create_task_callback: Async callback to create follow-up tasks
            create_notification_callback: Async callback to create notifications
        """
        self.service = service or StaleDetectionService()
        self.create_task_callback = create_task_callback
        self.create_notification_callback = create_notification_callback
    
    async def run_full_scan(
        self,
        opportunities: list[dict[str, Any]],
        rfqs: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        reference_time: datetime | None = None,
        create_follow_up_tasks: bool = True,
        send_notifications: bool = True,
        min_severity_for_task: StaleSeverity = StaleSeverity.MEDIUM,
        min_severity_for_notification: StaleSeverity = StaleSeverity.HIGH,
    ) -> dict[EntityType, StaleDetectionResult]:
        """
        Run stale detection across all entity types.
        
        Args:
            opportunities: List of opportunity data
            rfqs: List of RFQ data
            tasks: List of task data
            reference_time: Point in time to compare against
            create_follow_up_tasks: Whether to create tasks for stale items
            send_notifications: Whether to send notifications
            min_severity_for_task: Minimum severity to create follow-up task
            min_severity_for_notification: Minimum severity to send notification
        
        Returns:
            Dict mapping entity type to detection results
        """
        results = {}
        
        # Run detection for each entity type
        results[EntityType.OPPORTUNITY] = self.service.detect_stale_opportunities(
            opportunities, reference_time
        )
        results[EntityType.RFQ] = self.service.detect_stale_rfqs(rfqs, reference_time)
        results[EntityType.TASK] = self.service.detect_stale_tasks(tasks, reference_time)
        
        # Handle follow-up actions
        if create_follow_up_tasks and self.create_task_callback:
            await self._create_follow_up_tasks(results, min_severity_for_task)
        
        if send_notifications and self.create_notification_callback:
            await self._send_notifications(results, min_severity_for_notification)
        
        return results
    
    async def _create_follow_up_tasks(
        self,
        results: dict[EntityType, StaleDetectionResult],
        min_severity: StaleSeverity,
    ) -> list[dict[str, Any]]:
        """Create follow-up tasks for stale entities above minimum severity."""
        severity_order = [StaleSeverity.LOW, StaleSeverity.MEDIUM, StaleSeverity.HIGH, StaleSeverity.CRITICAL]
        min_index = severity_order.index(min_severity)
        
        created_tasks = []
        
        for entity_type, result in results.items():
            for stale_entity in result.stale_entities:
                if severity_order.index(stale_entity.severity) >= min_index:
                    task_data = {
                        "title": f"[STALE] {stale_entity.entity_name}",
                        "description": (
                            f"This {entity_type.value} has been stale for {stale_entity.days_stale} days.\n\n"
                            f"Reason: {stale_entity.reason.value}\n"
                            f"Suggested action: {stale_entity.suggested_action}"
                        ),
                        "entity_type": entity_type.value,
                        "entity_id": str(stale_entity.entity_id),
                        "priority": "high" if stale_entity.severity in (StaleSeverity.HIGH, StaleSeverity.CRITICAL) else "medium",
                        "assignee_id": str(stale_entity.owner_id) if stale_entity.owner_id else None,
                    }
                    
                    if self.create_task_callback:
                        result_task = await self.create_task_callback(task_data)
                        created_tasks.append(result_task)
        
        return created_tasks
    
    async def _send_notifications(
        self,
        results: dict[EntityType, StaleDetectionResult],
        min_severity: StaleSeverity,
    ) -> list[dict[str, Any]]:
        """Send notifications for stale entities above minimum severity."""
        severity_order = [StaleSeverity.LOW, StaleSeverity.MEDIUM, StaleSeverity.HIGH, StaleSeverity.CRITICAL]
        min_index = severity_order.index(min_severity)
        
        sent_notifications = []
        
        for entity_type, result in results.items():
            for stale_entity in result.stale_entities:
                if severity_order.index(stale_entity.severity) >= min_index:
                    notification_data = {
                        "type": "stale_alert",
                        "title": f"Stale {entity_type.value.title()}: {stale_entity.entity_name}",
                        "message": (
                            f"Has been stale for {stale_entity.days_stale} days. "
                            f"{stale_entity.suggested_action}"
                        ),
                        "severity": stale_entity.severity.value,
                        "entity_type": entity_type.value,
                        "entity_id": str(stale_entity.entity_id),
                        "user_id": str(stale_entity.owner_id) if stale_entity.owner_id else None,
                    }
                    
                    if self.create_notification_callback:
                        result_notification = await self.create_notification_callback(notification_data)
                        sent_notifications.append(result_notification)
        
        return sent_notifications
    
    def get_summary(
        self,
        results: dict[EntityType, StaleDetectionResult],
    ) -> dict[str, Any]:
        """
        Generate a summary of stale detection results.
        
        Returns:
            Summary dict with counts and aggregations
        """
        total_scanned = sum(r.total_scanned for r in results.values())
        total_stale = sum(r.stale_count for r in results.values())
        total_critical = sum(r.critical_count for r in results.values())
        total_high = sum(r.high_count for r in results.values())
        
        return {
            "scanned_at": results[EntityType.OPPORTUNITY].scanned_at.isoformat() if EntityType.OPPORTUNITY in results else None,
            "total_scanned": total_scanned,
            "total_stale": total_stale,
            "total_critical": total_critical,
            "total_high": total_high,
            "by_entity_type": {
                entity_type.value: {
                    "scanned": result.total_scanned,
                    "stale": result.stale_count,
                    "critical": result.critical_count,
                    "high": result.high_count,
                    "scan_duration_ms": result.scan_duration_ms,
                }
                for entity_type, result in results.items()
            },
            "requires_immediate_attention": total_critical + total_high,
        }
