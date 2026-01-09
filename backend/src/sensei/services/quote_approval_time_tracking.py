"""
Quote Approval Time Tracking Service.

Implements time-on-task tracking specifically for quote approval workflows.
Measures approval times against the < 60 second target from the Development Plan.

Features:
- Approval session tracking (start, review, decide)
- Approval criteria verification
- Real-time countdown during approval
- Approval history and audit trail
- Performance analytics for approvers
- Approval delegation and escalation
- Mobile-optimized quick approval flow
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class ApprovalDecision(str, Enum):
    """Quote approval decisions."""
    
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED_FOR_REVISION = "returned_for_revision"
    ESCALATED = "escalated"
    DELEGATED = "delegated"


class ApprovalReason(str, Enum):
    """Pre-defined reasons for approval decisions."""
    
    # Approval reasons
    WITHIN_AUTHORITY = "within_authority"
    MARGIN_ACCEPTABLE = "margin_acceptable"
    STANDARD_TERMS = "standard_terms"
    CUSTOMER_RELATIONSHIP = "customer_relationship"
    STRATEGIC_IMPORTANCE = "strategic_importance"
    
    # Rejection reasons
    MARGIN_TOO_LOW = "margin_too_low"
    EXCEEDS_AUTHORITY = "exceeds_authority"
    MISSING_INFORMATION = "missing_information"
    PRICING_ERROR = "pricing_error"
    NON_STANDARD_TERMS = "non_standard_terms"
    CAPACITY_CONSTRAINTS = "capacity_constraints"
    
    # Revision reasons
    CLARIFICATION_NEEDED = "clarification_needed"
    CALCULATION_REVIEW = "calculation_review"
    DOCUMENTATION_INCOMPLETE = "documentation_incomplete"
    
    # Escalation reasons
    ABOVE_THRESHOLD = "above_threshold"
    SPECIAL_TERMS = "special_terms"
    NEW_CUSTOMER = "new_customer"


class ApprovalSessionStatus(str, Enum):
    """Status of an approval session."""
    
    STARTED = "started"
    REVIEWING = "reviewing"
    DECIDED = "decided"
    TIMEOUT = "timeout"
    ABANDONED = "abandoned"


class ApprovalCriterionStatus(str, Enum):
    """Status of an approval criterion check."""
    
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ApprovalCriterion:
    """A criterion that must be checked during approval."""
    
    id: str
    name: str
    description: str
    category: str
    status: ApprovalCriterionStatus = ApprovalCriterionStatus.SKIPPED
    value: Any = None
    threshold: Any = None
    message: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


@dataclass
class QuoteApprovalContext:
    """Context information for quote approval."""
    
    quote_id: UUID
    quote_number: str
    version: int
    customer_name: str
    total_value: float
    margin_percent: float
    line_item_count: int
    currency: str = "USD"
    requested_by: UUID | None = None
    requested_at: datetime | None = None
    urgency: str = "normal"  # low, normal, high, urgent
    notes: str | None = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "quote_id": str(self.quote_id),
            "quote_number": self.quote_number,
            "version": self.version,
            "customer_name": self.customer_name,
            "total_value": self.total_value,
            "margin_percent": self.margin_percent,
            "line_item_count": self.line_item_count,
            "currency": self.currency,
            "requested_by": str(self.requested_by) if self.requested_by else None,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "urgency": self.urgency,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class ApprovalSession:
    """A tracked approval session for a quote."""
    
    id: UUID
    quote_id: UUID
    approver_id: UUID
    context: QuoteApprovalContext
    status: ApprovalSessionStatus
    started_at: datetime
    criteria: list[ApprovalCriterion] = field(default_factory=list)
    completed_at: datetime | None = None
    decision: ApprovalDecision | None = None
    reason: ApprovalReason | None = None
    custom_reason: str | None = None
    comments: str | None = None
    escalated_to: UUID | None = None
    delegated_to: UUID | None = None
    
    @property
    def elapsed_seconds(self) -> int:
        """Get elapsed time in seconds."""
        end = self.completed_at or datetime.now(timezone.utc)
        return int((end - self.started_at).total_seconds())
    
    @property
    def is_within_target(self) -> bool:
        """Check if approval was within 60 second target."""
        return self.elapsed_seconds <= 60
    
    @property
    def criteria_summary(self) -> dict:
        """Get summary of criteria checks."""
        summary = {
            "total": len(self.criteria),
            "passed": 0,
            "failed": 0,
            "warning": 0,
            "skipped": 0,
        }
        for c in self.criteria:
            if c.status == ApprovalCriterionStatus.PASSED:
                summary["passed"] += 1
            elif c.status == ApprovalCriterionStatus.FAILED:
                summary["failed"] += 1
            elif c.status == ApprovalCriterionStatus.WARNING:
                summary["warning"] += 1
            else:
                summary["skipped"] += 1
        return summary
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "quote_id": str(self.quote_id),
            "approver_id": str(self.approver_id),
            "context": self.context.to_dict(),
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_seconds": self.elapsed_seconds,
            "is_within_target": self.is_within_target,
            "criteria": [c.to_dict() for c in self.criteria],
            "criteria_summary": self.criteria_summary,
            "decision": self.decision.value if self.decision else None,
            "reason": self.reason.value if self.reason else None,
            "custom_reason": self.custom_reason,
            "comments": self.comments,
            "escalated_to": str(self.escalated_to) if self.escalated_to else None,
            "delegated_to": str(self.delegated_to) if self.delegated_to else None,
        }


@dataclass
class ApprovalAlert:
    """Alert for approval time threshold."""
    
    id: UUID
    session_id: UUID
    alert_type: str  # "warning", "critical", "timeout"
    elapsed_seconds: int
    created_at: datetime
    message: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "alert_type": self.alert_type,
            "elapsed_seconds": self.elapsed_seconds,
            "created_at": self.created_at.isoformat(),
            "message": self.message,
        }


@dataclass
class ApproverPerformance:
    """Performance metrics for an approver."""
    
    approver_id: UUID
    period_start: datetime
    period_end: datetime
    total_approvals: int
    approvals_within_target: int
    approvals_over_target: int
    average_time_seconds: float
    median_time_seconds: float
    min_time_seconds: int
    max_time_seconds: int
    approval_rate: float  # % approved vs rejected
    delegation_rate: float  # % delegated
    escalation_rate: float  # % escalated
    
    @property
    def target_compliance_rate(self) -> float:
        """Get rate of approvals within 60s target."""
        if self.total_approvals == 0:
            return 0.0
        return (self.approvals_within_target / self.total_approvals) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "approver_id": str(self.approver_id),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_approvals": self.total_approvals,
            "approvals_within_target": self.approvals_within_target,
            "approvals_over_target": self.approvals_over_target,
            "average_time_seconds": round(self.average_time_seconds, 2),
            "median_time_seconds": round(self.median_time_seconds, 2),
            "min_time_seconds": self.min_time_seconds,
            "max_time_seconds": self.max_time_seconds,
            "target_compliance_rate": round(self.target_compliance_rate, 2),
            "approval_rate": round(self.approval_rate, 2),
            "delegation_rate": round(self.delegation_rate, 2),
            "escalation_rate": round(self.escalation_rate, 2),
        }


@dataclass
class QuickApprovalOption:
    """Pre-configured quick approval option for mobile."""
    
    id: str
    label: str
    decision: ApprovalDecision
    reason: ApprovalReason
    icon: str
    color: str
    requires_comment: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "label": self.label,
            "decision": self.decision.value,
            "reason": self.reason.value,
            "icon": self.icon,
            "color": self.color,
            "requires_comment": self.requires_comment,
        }


# Default quick approval options for mobile
DEFAULT_QUICK_OPTIONS: list[QuickApprovalOption] = [
    QuickApprovalOption(
        id="quick_approve",
        label="Approve",
        decision=ApprovalDecision.APPROVED,
        reason=ApprovalReason.WITHIN_AUTHORITY,
        icon="check",
        color="green",
    ),
    QuickApprovalOption(
        id="approve_strategic",
        label="Approve (Strategic)",
        decision=ApprovalDecision.APPROVED,
        reason=ApprovalReason.STRATEGIC_IMPORTANCE,
        icon="star",
        color="green",
    ),
    QuickApprovalOption(
        id="return_revision",
        label="Return for Revision",
        decision=ApprovalDecision.RETURNED_FOR_REVISION,
        reason=ApprovalReason.CLARIFICATION_NEEDED,
        icon="edit",
        color="yellow",
        requires_comment=True,
    ),
    QuickApprovalOption(
        id="reject_margin",
        label="Reject (Margin)",
        decision=ApprovalDecision.REJECTED,
        reason=ApprovalReason.MARGIN_TOO_LOW,
        icon="x",
        color="red",
        requires_comment=True,
    ),
    QuickApprovalOption(
        id="escalate",
        label="Escalate",
        decision=ApprovalDecision.ESCALATED,
        reason=ApprovalReason.ABOVE_THRESHOLD,
        icon="arrow-up",
        color="orange",
    ),
]


# Default approval criteria
DEFAULT_APPROVAL_CRITERIA: list[dict] = [
    {
        "id": "margin_check",
        "name": "Margin Threshold",
        "description": "Gross margin meets minimum requirements",
        "category": "financial",
    },
    {
        "id": "discount_limit",
        "name": "Discount Limit",
        "description": "Applied discounts within authorized limits",
        "category": "financial",
    },
    {
        "id": "payment_terms",
        "name": "Payment Terms",
        "description": "Payment terms within standard policy",
        "category": "terms",
    },
    {
        "id": "authority_level",
        "name": "Authority Level",
        "description": "Quote value within approver's authority",
        "category": "authority",
    },
    {
        "id": "customer_credit",
        "name": "Customer Credit",
        "description": "Customer credit status is acceptable",
        "category": "customer",
    },
    {
        "id": "completeness",
        "name": "Quote Completeness",
        "description": "All required fields are populated",
        "category": "documentation",
    },
]


class QuoteApprovalTimeTrackingService:
    """
    Service for tracking quote approval time with < 60 second target.
    
    Provides optimized approval workflows for both desktop and mobile,
    with real-time countdown, criteria verification, and quick actions.
    """
    
    def __init__(self) -> None:
        """Initialize the quote approval service."""
        self._sessions: dict[UUID, ApprovalSession] = {}
        self._sessions_by_quote: dict[UUID, list[UUID]] = {}
        self._sessions_by_approver: dict[UUID, list[UUID]] = {}
        self._alerts: dict[UUID, ApprovalAlert] = {}
        self._completed_history: list[ApprovalSession] = []
        self._max_history = 10000
        self._target_seconds = 60
        self._warning_seconds = 45
        self._critical_seconds = 55
        self._listeners: list[Callable[[ApprovalAlert], None]] = []
        self._quick_options = DEFAULT_QUICK_OPTIONS.copy()
    
    # ===== Session Management =====
    
    def start_approval_session(
        self,
        quote_id: UUID,
        approver_id: UUID,
        context: QuoteApprovalContext,
    ) -> ApprovalSession:
        """
        Start a quote approval session.
        
        Args:
            quote_id: ID of the quote to approve
            approver_id: ID of the approver
            context: Approval context with quote details
            
        Returns:
            The created ApprovalSession
        """
        # Check for existing active session
        existing = self.get_active_session(quote_id, approver_id)
        if existing:
            return existing
        
        # Generate criteria
        criteria = self._generate_criteria(context)
        
        session = ApprovalSession(
            id=uuid4(),
            quote_id=quote_id,
            approver_id=approver_id,
            context=context,
            status=ApprovalSessionStatus.STARTED,
            started_at=datetime.now(timezone.utc),
            criteria=criteria,
        )
        
        self._sessions[session.id] = session
        
        # Index by quote
        if quote_id not in self._sessions_by_quote:
            self._sessions_by_quote[quote_id] = []
        self._sessions_by_quote[quote_id].append(session.id)
        
        # Index by approver
        if approver_id not in self._sessions_by_approver:
            self._sessions_by_approver[approver_id] = []
        self._sessions_by_approver[approver_id].append(session.id)
        
        return session
    
    def _generate_criteria(self, context: QuoteApprovalContext) -> list[ApprovalCriterion]:
        """Generate approval criteria for a quote."""
        criteria = []
        
        for c in DEFAULT_APPROVAL_CRITERIA:
            criterion = ApprovalCriterion(
                id=c["id"],
                name=c["name"],
                description=c["description"],
                category=c["category"],
            )
            
            # Auto-check some criteria based on context
            if c["id"] == "margin_check":
                min_margin = 15.0  # Example threshold
                criterion.threshold = min_margin
                criterion.value = context.margin_percent
                if context.margin_percent >= min_margin:
                    criterion.status = ApprovalCriterionStatus.PASSED
                    criterion.message = f"Margin {context.margin_percent:.1f}% meets minimum {min_margin}%"
                else:
                    criterion.status = ApprovalCriterionStatus.FAILED
                    criterion.message = f"Margin {context.margin_percent:.1f}% below minimum {min_margin}%"
            
            elif c["id"] == "completeness":
                # Basic completeness check
                complete = (
                    context.customer_name and 
                    context.total_value > 0 and 
                    context.line_item_count > 0
                )
                if complete:
                    criterion.status = ApprovalCriterionStatus.PASSED
                    criterion.message = "Quote is complete"
                else:
                    criterion.status = ApprovalCriterionStatus.WARNING
                    criterion.message = "Some fields may be incomplete"
            
            criteria.append(criterion)
        
        return criteria
    
    def update_criterion(
        self,
        session_id: UUID,
        criterion_id: str,
        status: ApprovalCriterionStatus,
        message: str | None = None,
    ) -> ApprovalSession | None:
        """
        Update a criterion status in an approval session.
        
        Args:
            session_id: ID of the session
            criterion_id: ID of the criterion
            status: New status
            message: Optional message
            
        Returns:
            Updated session or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        for criterion in session.criteria:
            if criterion.id == criterion_id:
                criterion.status = status
                if message:
                    criterion.message = message
                break
        
        session.status = ApprovalSessionStatus.REVIEWING
        
        return session
    
    def make_decision(
        self,
        session_id: UUID,
        decision: ApprovalDecision,
        reason: ApprovalReason | None = None,
        custom_reason: str | None = None,
        comments: str | None = None,
        escalated_to: UUID | None = None,
        delegated_to: UUID | None = None,
    ) -> ApprovalSession | None:
        """
        Make a decision on a quote approval.
        
        Args:
            session_id: ID of the session
            decision: The approval decision
            reason: Pre-defined reason
            custom_reason: Custom reason text
            comments: Additional comments
            escalated_to: User to escalate to (if escalating)
            delegated_to: User to delegate to (if delegating)
            
        Returns:
            Updated session or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.status == ApprovalSessionStatus.DECIDED:
            return session
        
        session.completed_at = datetime.now(timezone.utc)
        session.status = ApprovalSessionStatus.DECIDED
        session.decision = decision
        session.reason = reason
        session.custom_reason = custom_reason
        session.comments = comments
        session.escalated_to = escalated_to
        session.delegated_to = delegated_to
        
        # Archive to history
        self._archive_session(session)
        
        return session
    
    def quick_approve(
        self,
        session_id: UUID,
        option_id: str,
        comments: str | None = None,
    ) -> ApprovalSession | None:
        """
        Quick approval using pre-configured option.
        
        Args:
            session_id: ID of the session
            option_id: ID of the quick option
            comments: Optional comments (required for some options)
            
        Returns:
            Updated session or None if not found/invalid
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        option = next((o for o in self._quick_options if o.id == option_id), None)
        if not option:
            return None
        
        if option.requires_comment and not comments:
            return None
        
        return self.make_decision(
            session_id=session_id,
            decision=option.decision,
            reason=option.reason,
            comments=comments,
        )
    
    def abandon_session(
        self,
        session_id: UUID,
        reason: str | None = None,
    ) -> ApprovalSession | None:
        """
        Abandon an approval session.
        
        Args:
            session_id: ID of the session
            reason: Optional reason
            
        Returns:
            Updated session or None if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        if session.status == ApprovalSessionStatus.DECIDED:
            return session
        
        session.completed_at = datetime.now(timezone.utc)
        session.status = ApprovalSessionStatus.ABANDONED
        session.custom_reason = reason
        
        self._archive_session(session)
        
        return session
    
    def _archive_session(self, session: ApprovalSession) -> None:
        """Archive a completed session to history."""
        self._completed_history.append(session)
        if len(self._completed_history) > self._max_history:
            self._completed_history = self._completed_history[-self._max_history:]
    
    def get_session(self, session_id: UUID) -> ApprovalSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_active_session(
        self,
        quote_id: UUID,
        approver_id: UUID,
    ) -> ApprovalSession | None:
        """Get active session for a quote and approver."""
        session_ids = self._sessions_by_quote.get(quote_id, [])
        for sid in session_ids:
            session = self._sessions.get(sid)
            if session and session.approver_id == approver_id and session.status in (
                ApprovalSessionStatus.STARTED,
                ApprovalSessionStatus.REVIEWING,
            ):
                return session
        return None
    
    def get_quote_sessions(self, quote_id: UUID) -> list[ApprovalSession]:
        """Get all sessions for a quote."""
        session_ids = self._sessions_by_quote.get(quote_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    def get_approver_pending(self, approver_id: UUID) -> list[ApprovalSession]:
        """Get pending sessions for an approver."""
        session_ids = self._sessions_by_approver.get(approver_id, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions and self._sessions[sid].status in (
                ApprovalSessionStatus.STARTED,
                ApprovalSessionStatus.REVIEWING,
            )
        ]
    
    # ===== Real-time Monitoring =====
    
    def check_session_countdown(self, session_id: UUID) -> dict:
        """
        Get real-time countdown status for an approval session.
        
        Returns:
            Dict with elapsed time, remaining time, and status
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        elapsed = session.elapsed_seconds
        remaining = max(0, self._target_seconds - elapsed)
        
        status = "on_track"
        if elapsed >= self._target_seconds:
            status = "exceeded"
        elif elapsed >= self._critical_seconds:
            status = "critical"
        elif elapsed >= self._warning_seconds:
            status = "warning"
        
        # Generate alerts
        self._check_alerts(session, elapsed)
        
        return {
            "session_id": str(session.id),
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "target_seconds": self._target_seconds,
            "percentage": min(100, round((elapsed / self._target_seconds) * 100, 1)),
            "status": status,
            "is_within_target": elapsed <= self._target_seconds,
            "decision_status": session.status.value,
        }
    
    def _check_alerts(self, session: ApprovalSession, elapsed: int) -> None:
        """Check and generate alerts for a session."""
        existing = {
            a.alert_type
            for a in self._alerts.values()
            if a.session_id == session.id
        }
        
        if elapsed >= self._target_seconds and "timeout" not in existing:
            self._create_alert(session, "timeout", elapsed, 
                "Approval time exceeded 60 second target")
        elif elapsed >= self._critical_seconds and "critical" not in existing:
            self._create_alert(session, "critical", elapsed,
                "5 seconds remaining - decide now")
        elif elapsed >= self._warning_seconds and "warning" not in existing:
            self._create_alert(session, "warning", elapsed,
                "15 seconds remaining - review quickly")
    
    def _create_alert(
        self,
        session: ApprovalSession,
        alert_type: str,
        elapsed: int,
        message: str,
    ) -> ApprovalAlert:
        """Create an alert."""
        alert = ApprovalAlert(
            id=uuid4(),
            session_id=session.id,
            alert_type=alert_type,
            elapsed_seconds=elapsed,
            created_at=datetime.now(timezone.utc),
            message=message,
        )
        
        self._alerts[alert.id] = alert
        
        for listener in self._listeners:
            try:
                listener(alert)
            except Exception:
                pass
        
        return alert
    
    def add_alert_listener(self, callback: Callable[[ApprovalAlert], None]) -> None:
        """Add an alert listener."""
        self._listeners.append(callback)
    
    def remove_alert_listener(self, callback: Callable[[ApprovalAlert], None]) -> None:
        """Remove an alert listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    # ===== Quick Approval Options =====
    
    def get_quick_options(self) -> list[QuickApprovalOption]:
        """Get available quick approval options."""
        return self._quick_options.copy()
    
    def add_quick_option(self, option: QuickApprovalOption) -> None:
        """Add a custom quick option."""
        self._quick_options.append(option)
    
    # ===== Analytics =====
    
    def get_approver_performance(
        self,
        approver_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ApproverPerformance | None:
        """
        Get performance metrics for an approver.
        
        Args:
            approver_id: ID of the approver
            start_date: Start of period
            end_date: End of period
            
        Returns:
            ApproverPerformance or None if no data
        """
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now
        
        # Collect completed sessions
        sessions = [
            s for s in self._completed_history
            if s.approver_id == approver_id
            and s.status == ApprovalSessionStatus.DECIDED
            and start <= s.started_at <= end
        ]
        
        # Also check active sessions
        for s in self._sessions.values():
            if (s.approver_id == approver_id 
                and s.status == ApprovalSessionStatus.DECIDED
                and start <= s.started_at <= end
                and s not in sessions):
                sessions.append(s)
        
        if not sessions:
            return None
        
        times = [s.elapsed_seconds for s in sessions]
        sorted_times = sorted(times)
        
        approved = sum(1 for s in sessions if s.decision == ApprovalDecision.APPROVED)
        delegated = sum(1 for s in sessions if s.decision == ApprovalDecision.DELEGATED)
        escalated = sum(1 for s in sessions if s.decision == ApprovalDecision.ESCALATED)
        
        return ApproverPerformance(
            approver_id=approver_id,
            period_start=start,
            period_end=end,
            total_approvals=len(sessions),
            approvals_within_target=sum(1 for t in times if t <= self._target_seconds),
            approvals_over_target=sum(1 for t in times if t > self._target_seconds),
            average_time_seconds=sum(times) / len(times),
            median_time_seconds=sorted_times[len(sorted_times) // 2],
            min_time_seconds=min(times),
            max_time_seconds=max(times),
            approval_rate=(approved / len(sessions)) * 100 if sessions else 0,
            delegation_rate=(delegated / len(sessions)) * 100 if sessions else 0,
            escalation_rate=(escalated / len(sessions)) * 100 if sessions else 0,
        )
    
    def get_quote_approval_summary(self, quote_id: UUID) -> dict:
        """
        Get approval summary for a quote.
        
        Returns:
            Summary of all approval sessions for the quote
        """
        sessions = self.get_quote_sessions(quote_id)
        
        decided = [s for s in sessions if s.status == ApprovalSessionStatus.DECIDED]
        pending = [s for s in sessions if s.status in (
            ApprovalSessionStatus.STARTED, ApprovalSessionStatus.REVIEWING
        )]
        
        final_decision = None
        final_session = None
        if decided:
            final_session = max(decided, key=lambda s: s.completed_at or s.started_at)
            final_decision = final_session.decision.value if final_session.decision else None
        
        return {
            "quote_id": str(quote_id),
            "total_sessions": len(sessions),
            "decided_sessions": len(decided),
            "pending_sessions": len(pending),
            "final_decision": final_decision,
            "final_decision_time_seconds": final_session.elapsed_seconds if final_session else None,
            "within_target": final_session.is_within_target if final_session else None,
            "sessions": [s.to_dict() for s in sessions],
        }
    
    def get_approval_leaderboard(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get leaderboard of approvers by speed and compliance.
        
        Args:
            start_date: Start of period
            end_date: End of period
            limit: Max entries to return
            
        Returns:
            List of approver performance summaries
        """
        now = datetime.now(timezone.utc)
        start = start_date or (now - timedelta(days=30))
        end = end_date or now
        
        # Get unique approvers
        approver_ids: set[UUID] = set()
        
        for s in self._completed_history:
            if start <= s.started_at <= end and s.status == ApprovalSessionStatus.DECIDED:
                approver_ids.add(s.approver_id)
        
        for s in self._sessions.values():
            if start <= s.started_at <= end and s.status == ApprovalSessionStatus.DECIDED:
                approver_ids.add(s.approver_id)
        
        # Get performance for each
        performances = []
        for aid in approver_ids:
            perf = self.get_approver_performance(aid, start, end)
            if perf:
                performances.append(perf)
        
        # Sort by target compliance rate, then average time
        performances.sort(
            key=lambda p: (p.target_compliance_rate, -p.average_time_seconds),
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                **p.to_dict()
            }
            for i, p in enumerate(performances[:limit])
        ]
    
    # ===== Configuration =====
    
    def set_target(self, target_seconds: int, warning_seconds: int, critical_seconds: int) -> None:
        """Set time targets."""
        self._target_seconds = target_seconds
        self._warning_seconds = warning_seconds
        self._critical_seconds = critical_seconds
    
    def get_target(self) -> dict:
        """Get current time targets."""
        return {
            "target_seconds": self._target_seconds,
            "warning_seconds": self._warning_seconds,
            "critical_seconds": self._critical_seconds,
        }
    
    def reset(self) -> None:
        """Reset all data (for testing)."""
        self._sessions.clear()
        self._sessions_by_quote.clear()
        self._sessions_by_approver.clear()
        self._alerts.clear()
        self._completed_history.clear()
        self._listeners.clear()
        self._quick_options = DEFAULT_QUICK_OPTIONS.copy()
        self._target_seconds = 60
        self._warning_seconds = 45
        self._critical_seconds = 55


# Singleton instance
_service_instance: QuoteApprovalTimeTrackingService | None = None


def get_quote_approval_service() -> QuoteApprovalTimeTrackingService:
    """Get the singleton quote approval service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = QuoteApprovalTimeTrackingService()
    return _service_instance


def reset_quote_approval_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _service_instance
    if _service_instance:
        _service_instance.reset()
    _service_instance = None
