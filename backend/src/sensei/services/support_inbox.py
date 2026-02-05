"""Support Inbox Service.

Routes user issues and feedback into A3-lite or Task creation.
Manages support tickets, feedback collection, and issue routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TicketPriority(Enum):
    """Priority levels for support tickets."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(Enum):
    """Status states for support tickets."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_USER = "waiting_on_user"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketCategory(Enum):
    """Categories for classifying tickets."""

    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    QUESTION = "question"
    FEEDBACK = "feedback"
    DATA_ISSUE = "data_issue"
    ACCESS_REQUEST = "access_request"
    TRAINING = "training"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    OTHER = "other"


class FeedbackType(Enum):
    """Types of user feedback."""

    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    BUG_REPORT = "bug_report"
    USABILITY = "usability"
    MISSING_FEATURE = "missing_feature"


class RoutingTarget(Enum):
    """Targets for routing tickets."""

    A3_LITE = "a3_lite"
    TASK = "task"
    MANUAL_REVIEW = "manual_review"
    AUTO_RESPONSE = "auto_response"
    ESCALATION = "escalation"


@dataclass
class TicketComment:
    """Comment on a support ticket."""

    id: UUID = field(default_factory=uuid4)
    ticket_id: UUID = field(default_factory=uuid4)
    author_id: UUID = field(default_factory=uuid4)
    author_name: str = ""
    content: str = ""
    is_internal: bool = False
    is_from_user: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attachments: list[str] = field(default_factory=list)


@dataclass
class TicketAttachment:
    """Attachment on a support ticket."""

    id: UUID = field(default_factory=uuid4)
    ticket_id: UUID = field(default_factory=uuid4)
    filename: str = ""
    file_type: str = ""
    file_size: int = 0
    storage_path: str = ""
    uploaded_by: UUID = field(default_factory=uuid4)
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RoutingDecision:
    """Decision for how to route a ticket."""

    id: UUID = field(default_factory=uuid4)
    ticket_id: UUID = field(default_factory=uuid4)
    target: RoutingTarget = RoutingTarget.MANUAL_REVIEW
    target_id: Optional[UUID] = None
    reason: str = ""
    confidence_score: float = 0.0
    applied_at: Optional[datetime] = None
    applied_by: Optional[UUID] = None
    auto_applied: bool = False


@dataclass
class SupportTicket:
    """Support ticket from a user."""

    id: UUID = field(default_factory=uuid4)
    subject: str = ""
    description: str = ""
    category: TicketCategory = TicketCategory.OTHER
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    submitted_by: UUID = field(default_factory=uuid4)
    submitter_name: str = ""
    submitter_email: str = ""
    assigned_to: Optional[UUID] = None
    assignee_name: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    sla_due_at: Optional[datetime] = None
    routing_decision: Optional[RoutingDecision] = None
    comments: list[TicketComment] = field(default_factory=list)
    attachments: list[TicketAttachment] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class UserFeedback:
    """Feedback submitted by a user."""

    id: UUID = field(default_factory=uuid4)
    feedback_type: FeedbackType = FeedbackType.SUGGESTION
    content: str = ""
    rating: Optional[int] = None
    submitted_by: UUID = field(default_factory=uuid4)
    submitter_name: str = ""
    page_url: str = ""
    browser_info: str = ""
    feature_area: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed: bool = False
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    converted_to_ticket: bool = False
    ticket_id: Optional[UUID] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class RoutingRule:
    """Rule for automatic ticket routing."""

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    is_active: bool = True
    priority: int = 0
    conditions: dict = field(default_factory=dict)
    target: RoutingTarget = RoutingTarget.MANUAL_REVIEW
    target_config: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID = field(default_factory=uuid4)


@dataclass
class A3LiteRecord:
    """Lightweight A3 problem record created from a ticket."""

    id: UUID = field(default_factory=uuid4)
    source_ticket_id: UUID = field(default_factory=uuid4)
    title: str = ""
    problem_statement: str = ""
    current_state: str = ""
    root_cause: str = ""
    countermeasures: str = ""
    target_state: str = ""
    owner_id: UUID = field(default_factory=uuid4)
    status: str = "open"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


@dataclass
class InboxStats:
    """Statistics for the support inbox."""

    total_open: int = 0
    total_in_progress: int = 0
    total_resolved_today: int = 0
    total_escalated: int = 0
    avg_response_time_hours: float = 0.0
    avg_resolution_time_hours: float = 0.0
    by_category: dict = field(default_factory=dict)
    by_priority: dict = field(default_factory=dict)


class SupportInboxService:
    """Service for managing support inbox and user feedback.

    Routes user issues into A3-lite records or Task creation.
    Provides ticket management, feedback collection, and routing.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize the support inbox service.
        
        Args:
            session: Optional database session for persistence. If not provided,
                     tickets will be stored in memory only (useful for testing).
        """
        self._session = session
        self._tickets: dict[UUID, SupportTicket] = {}
        self._feedback: dict[UUID, UserFeedback] = {}
        self._routing_rules: dict[UUID, RoutingRule] = {}
        self._a3_lite_records: dict[UUID, A3LiteRecord] = {}
        self._max_tickets: int = 5000
        self._ticket_ttl: timedelta = timedelta(days=90)
        self._default_sla_hours: dict[TicketPriority, int] = {
            TicketPriority.CRITICAL: 2,
            TicketPriority.HIGH: 8,
            TicketPriority.MEDIUM: 24,
            TicketPriority.LOW: 72,
        }
        self._setup_default_rules()

    def _prune_tickets(self) -> None:
        """Prune old tickets to prevent unbounded memory growth."""
        cutoff = datetime.now(timezone.utc) - self._ticket_ttl
        resolved_statuses = {TicketStatus.RESOLVED, TicketStatus.CLOSED}

        stale_ids = [
            tid for tid, ticket in self._tickets.items()
            if ticket.status in resolved_statuses and ticket.updated_at < cutoff
        ]
        for tid in stale_ids:
            del self._tickets[tid]

        excess = len(self._tickets) - self._max_tickets
        if excess > 0:
            # Prefer pruning resolved/closed tickets first
            resolved = [
                (tid, t) for tid, t in self._tickets.items()
                if t.status in resolved_statuses
            ]
            resolved_sorted = sorted(resolved, key=lambda item: item[1].updated_at)
            for tid, _ in resolved_sorted[:excess]:
                del self._tickets[tid]

            excess = len(self._tickets) - self._max_tickets
            if excess > 0:
                oldest = sorted(self._tickets.items(), key=lambda item: item[1].updated_at)
                for tid, _ in oldest[:excess]:
                    del self._tickets[tid]

    def _setup_default_rules(self) -> None:
        """Set up default routing rules."""
        rules = [
            RoutingRule(
                name="Critical Bugs to A3",
                description="Route critical bugs to A3-lite for root cause analysis",
                priority=100,
                conditions={"category": "bug", "priority": "critical"},
                target=RoutingTarget.A3_LITE,
            ),
            RoutingRule(
                name="High Priority to Escalation",
                description="Escalate high priority tickets",
                priority=90,
                conditions={"priority": "high"},
                target=RoutingTarget.ESCALATION,
            ),
            RoutingRule(
                name="Feature Requests to Task",
                description="Create tasks for feature requests",
                priority=80,
                conditions={"category": "feature_request"},
                target=RoutingTarget.TASK,
            ),
            RoutingRule(
                name="Data Issues to A3",
                description="Route data issues to A3-lite",
                priority=70,
                conditions={"category": "data_issue"},
                target=RoutingTarget.A3_LITE,
            ),
            RoutingRule(
                name="Questions Auto-Response",
                description="Send auto-response for simple questions",
                priority=60,
                conditions={"category": "question"},
                target=RoutingTarget.AUTO_RESPONSE,
            ),
        ]

        for rule in rules:
            self._routing_rules[rule.id] = rule

    # --- Ticket Management ---

    def create_ticket(
        self,
        subject: str,
        description: str,
        submitted_by: UUID,
        submitter_name: str = "",
        submitter_email: str = "",
        category: TicketCategory = TicketCategory.OTHER,
        priority: TicketPriority = TicketPriority.MEDIUM,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[UUID] = None,
        tags: Optional[list[str]] = None,
        auto_route: bool = True,
    ) -> SupportTicket:
        """Create a new support ticket.

        Args:
            subject: Ticket subject line
            description: Detailed description
            submitted_by: User ID of submitter
            submitter_name: Name of submitter
            submitter_email: Email of submitter
            category: Ticket category
            priority: Ticket priority
            related_entity_type: Type of related entity (e.g., 'rfq', 'quote')
            related_entity_id: ID of related entity
            tags: Optional tags
            auto_route: Whether to auto-route the ticket

        Returns:
            Created ticket
        """
        from datetime import timedelta

        sla_hours = self._default_sla_hours.get(priority, 24)

        ticket = SupportTicket(
            subject=subject,
            description=description,
            submitted_by=submitted_by,
            submitter_name=submitter_name,
            submitter_email=submitter_email,
            category=category,
            priority=priority,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            tags=tags or [],
            sla_due_at=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
        )

        self._tickets[ticket.id] = ticket
        self._prune_tickets()

        if auto_route:
            self._apply_routing(ticket)

        return ticket

    def get_ticket(self, ticket_id: UUID) -> Optional[SupportTicket]:
        """Get a ticket by ID."""
        return self._tickets.get(ticket_id)

    def get_tickets(
        self,
        status: Optional[TicketStatus] = None,
        category: Optional[TicketCategory] = None,
        priority: Optional[TicketPriority] = None,
        assigned_to: Optional[UUID] = None,
        submitted_by: Optional[UUID] = None,
    ) -> list[SupportTicket]:
        """Get tickets with optional filters."""
        self._prune_tickets()
        tickets = list(self._tickets.values())

        if status:
            tickets = [t for t in tickets if t.status == status]
        if category:
            tickets = [t for t in tickets if t.category == category]
        if priority:
            tickets = [t for t in tickets if t.priority == priority]
        if assigned_to:
            tickets = [t for t in tickets if t.assigned_to == assigned_to]
        if submitted_by:
            tickets = [t for t in tickets if t.submitted_by == submitted_by]

        return sorted(tickets, key=lambda x: x.created_at, reverse=True)

    def update_ticket(
        self,
        ticket_id: UUID,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[TicketCategory] = None,
        priority: Optional[TicketPriority] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[SupportTicket]:
        """Update a ticket's details."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        if subject is not None:
            ticket.subject = subject
        if description is not None:
            ticket.description = description
        if category is not None:
            ticket.category = category
        if priority is not None:
            ticket.priority = priority
            # Update SLA based on new priority
            from datetime import timedelta

            sla_hours = self._default_sla_hours.get(priority, 24)
            ticket.sla_due_at = ticket.created_at + timedelta(hours=sla_hours)
        if tags is not None:
            ticket.tags = tags

        ticket.updated_at = datetime.now(timezone.utc)
        return ticket

    def assign_ticket(
        self,
        ticket_id: UUID,
        assignee_id: UUID,
        assignee_name: str = "",
    ) -> Optional[SupportTicket]:
        """Assign a ticket to a user."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        ticket.assigned_to = assignee_id
        ticket.assignee_name = assignee_name
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = datetime.now(timezone.utc)

        return ticket

    def add_comment(
        self,
        ticket_id: UUID,
        author_id: UUID,
        author_name: str,
        content: str,
        is_internal: bool = False,
        is_from_user: bool = True,
        attachments: Optional[list[str]] = None,
    ) -> Optional[TicketComment]:
        """Add a comment to a ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        comment = TicketComment(
            ticket_id=ticket_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            is_internal=is_internal,
            is_from_user=is_from_user,
            attachments=attachments or [],
        )

        ticket.comments.append(comment)
        ticket.updated_at = datetime.now(timezone.utc)

        # Track first response time if this is from support
        if not is_from_user and not ticket.first_response_at:
            ticket.first_response_at = datetime.now(timezone.utc)

        return comment

    def change_status(
        self,
        ticket_id: UUID,
        new_status: TicketStatus,
        actor_id: Optional[UUID] = None,
    ) -> Optional[SupportTicket]:
        """Change a ticket's status."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        now = datetime.now(timezone.utc)

        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = now
        elif new_status == TicketStatus.CLOSED:
            ticket.closed_at = now

        ticket.status = new_status
        ticket.updated_at = now

        return ticket

    def escalate_ticket(
        self,
        ticket_id: UUID,
        reason: str,
        escalate_to: Optional[UUID] = None,
    ) -> Optional[SupportTicket]:
        """Escalate a ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        ticket.status = TicketStatus.ESCALATED
        ticket.priority = TicketPriority.HIGH
        ticket.updated_at = datetime.now(timezone.utc)

        if escalate_to:
            ticket.assigned_to = escalate_to

        # Add escalation note
        ticket.metadata["escalation_reason"] = reason
        ticket.metadata["escalated_at"] = datetime.now(timezone.utc).isoformat()

        return ticket

    # --- Routing ---

    def _apply_routing(self, ticket: SupportTicket) -> Optional[RoutingDecision]:
        """Apply routing rules to a ticket."""
        sorted_rules = sorted(
            [r for r in self._routing_rules.values() if r.is_active],
            key=lambda x: x.priority,
            reverse=True,
        )

        for rule in sorted_rules:
            if self._matches_rule(ticket, rule):
                decision = RoutingDecision(
                    ticket_id=ticket.id,
                    target=rule.target,
                    reason=rule.description,
                    confidence_score=0.9,
                    applied_at=datetime.now(timezone.utc),
                    auto_applied=True,
                )

                ticket.routing_decision = decision

                # Apply the routing
                if rule.target == RoutingTarget.A3_LITE:
                    a3 = self._create_a3_lite_from_ticket(ticket)
                    decision.target_id = a3.id

                return decision

        # Default to manual review
        decision = RoutingDecision(
            ticket_id=ticket.id,
            target=RoutingTarget.MANUAL_REVIEW,
            reason="No matching routing rule",
            confidence_score=0.0,
            auto_applied=True,
        )
        ticket.routing_decision = decision
        return decision

    def _matches_rule(self, ticket: SupportTicket, rule: RoutingRule) -> bool:
        """Check if a ticket matches a routing rule."""
        conditions = rule.conditions

        if "category" in conditions:
            if ticket.category.value != conditions["category"]:
                return False

        if "priority" in conditions:
            if ticket.priority.value != conditions["priority"]:
                return False

        if "tags" in conditions:
            required_tags = conditions["tags"]
            if not all(tag in ticket.tags for tag in required_tags):
                return False

        if "keywords" in conditions:
            keywords = conditions["keywords"]
            text = f"{ticket.subject} {ticket.description}".lower()
            if not any(kw.lower() in text for kw in keywords):
                return False

        return True

    def route_ticket(
        self,
        ticket_id: UUID,
        target: RoutingTarget,
        actor_id: UUID,
        reason: str = "",
    ) -> Optional[RoutingDecision]:
        """Manually route a ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        decision = RoutingDecision(
            ticket_id=ticket_id,
            target=target,
            reason=reason,
            confidence_score=1.0,
            applied_at=datetime.now(timezone.utc),
            applied_by=actor_id,
            auto_applied=False,
        )

        if target == RoutingTarget.A3_LITE:
            a3 = self._create_a3_lite_from_ticket(ticket)
            decision.target_id = a3.id

        ticket.routing_decision = decision
        ticket.updated_at = datetime.now(timezone.utc)

        return decision

    def _create_a3_lite_from_ticket(self, ticket: SupportTicket) -> A3LiteRecord:
        """Create an A3-lite record from a ticket."""
        a3 = A3LiteRecord(
            source_ticket_id=ticket.id,
            title=ticket.subject,
            problem_statement=ticket.description,
            current_state=f"Issue reported: {ticket.category.value}",
            owner_id=ticket.assigned_to or ticket.submitted_by,
        )

        self._a3_lite_records[a3.id] = a3
        return a3

    # --- Routing Rules ---

    def create_routing_rule(
        self,
        name: str,
        description: str,
        conditions: dict,
        target: RoutingTarget,
        priority: int = 50,
        target_config: Optional[dict] = None,
        created_by: UUID = uuid4(),
    ) -> RoutingRule:
        """Create a new routing rule."""
        rule = RoutingRule(
            name=name,
            description=description,
            conditions=conditions,
            target=target,
            priority=priority,
            target_config=target_config or {},
            created_by=created_by,
        )

        self._routing_rules[rule.id] = rule
        return rule

    def get_routing_rules(
        self,
        active_only: bool = False,
    ) -> list[RoutingRule]:
        """Get all routing rules."""
        rules = list(self._routing_rules.values())

        if active_only:
            rules = [r for r in rules if r.is_active]

        return sorted(rules, key=lambda x: x.priority, reverse=True)

    def update_routing_rule(
        self,
        rule_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        conditions: Optional[dict] = None,
        target: Optional[RoutingTarget] = None,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[RoutingRule]:
        """Update a routing rule."""
        rule = self._routing_rules.get(rule_id)
        if not rule:
            return None

        if name is not None:
            rule.name = name
        if description is not None:
            rule.description = description
        if conditions is not None:
            rule.conditions = conditions
        if target is not None:
            rule.target = target
        if priority is not None:
            rule.priority = priority
        if is_active is not None:
            rule.is_active = is_active

        return rule

    def delete_routing_rule(self, rule_id: UUID) -> bool:
        """Delete a routing rule."""
        if rule_id in self._routing_rules:
            del self._routing_rules[rule_id]
            return True
        return False

    # --- Feedback ---

    def submit_feedback(
        self,
        content: str,
        feedback_type: FeedbackType,
        submitted_by: UUID,
        submitter_name: str = "",
        rating: Optional[int] = None,
        page_url: str = "",
        browser_info: str = "",
        feature_area: str = "",
        tags: Optional[list[str]] = None,
    ) -> UserFeedback:
        """Submit user feedback."""
        feedback = UserFeedback(
            content=content,
            feedback_type=feedback_type,
            submitted_by=submitted_by,
            submitter_name=submitter_name,
            rating=rating,
            page_url=page_url,
            browser_info=browser_info,
            feature_area=feature_area,
            tags=tags or [],
        )

        self._feedback[feedback.id] = feedback
        return feedback

    def get_feedback(
        self,
        feedback_type: Optional[FeedbackType] = None,
        reviewed: Optional[bool] = None,
        feature_area: Optional[str] = None,
    ) -> list[UserFeedback]:
        """Get feedback with optional filters."""
        feedback_list = list(self._feedback.values())

        if feedback_type:
            feedback_list = [f for f in feedback_list if f.feedback_type == feedback_type]
        if reviewed is not None:
            feedback_list = [f for f in feedback_list if f.reviewed == reviewed]
        if feature_area:
            feedback_list = [f for f in feedback_list if f.feature_area == feature_area]

        return sorted(feedback_list, key=lambda x: x.created_at, reverse=True)

    def review_feedback(
        self,
        feedback_id: UUID,
        reviewer_id: UUID,
    ) -> Optional[UserFeedback]:
        """Mark feedback as reviewed."""
        feedback = self._feedback.get(feedback_id)
        if not feedback:
            return None

        feedback.reviewed = True
        feedback.reviewed_by = reviewer_id
        feedback.reviewed_at = datetime.now(timezone.utc)

        return feedback

    def convert_feedback_to_ticket(
        self,
        feedback_id: UUID,
        priority: TicketPriority = TicketPriority.MEDIUM,
    ) -> Optional[SupportTicket]:
        """Convert feedback to a support ticket."""
        feedback = self._feedback.get(feedback_id)
        if not feedback:
            return None

        if feedback.converted_to_ticket:
            return self._tickets.get(feedback.ticket_id) if feedback.ticket_id else None

        # Map feedback type to ticket category
        category_map: dict[FeedbackType, TicketCategory] = {
            FeedbackType.SUGGESTION: TicketCategory.FEATURE_REQUEST,
            FeedbackType.COMPLAINT: TicketCategory.OTHER,
            FeedbackType.BUG_REPORT: TicketCategory.BUG,
            FeedbackType.USABILITY: TicketCategory.FEEDBACK,
            FeedbackType.MISSING_FEATURE: TicketCategory.FEATURE_REQUEST,
            FeedbackType.PRAISE: TicketCategory.FEEDBACK,
        }

        ticket = self.create_ticket(
            subject=f"Feedback: {feedback.feedback_type.value.replace('_', ' ').title()}",
            description=feedback.content,
            submitted_by=feedback.submitted_by,
            submitter_name=feedback.submitter_name,
            category=category_map.get(feedback.feedback_type, TicketCategory.FEEDBACK),
            priority=priority,
            tags=feedback.tags + ["converted_from_feedback"],
        )

        feedback.converted_to_ticket = True
        feedback.ticket_id = ticket.id

        return ticket

    # --- A3-Lite ---

    def get_a3_lite(self, a3_id: UUID) -> Optional[A3LiteRecord]:
        """Get an A3-lite record by ID."""
        return self._a3_lite_records.get(a3_id)

    def get_a3_lite_for_ticket(self, ticket_id: UUID) -> Optional[A3LiteRecord]:
        """Get A3-lite record created from a ticket."""
        for a3 in self._a3_lite_records.values():
            if a3.source_ticket_id == ticket_id:
                return a3
        return None

    def update_a3_lite(
        self,
        a3_id: UUID,
        root_cause: Optional[str] = None,
        countermeasures: Optional[str] = None,
        target_state: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[A3LiteRecord]:
        """Update an A3-lite record."""
        a3 = self._a3_lite_records.get(a3_id)
        if not a3:
            return None

        if root_cause is not None:
            a3.root_cause = root_cause
        if countermeasures is not None:
            a3.countermeasures = countermeasures
        if target_state is not None:
            a3.target_state = target_state
        if status is not None:
            a3.status = status
            if status == "completed":
                a3.completed_at = datetime.now(timezone.utc)

        return a3

    # --- Statistics ---

    def get_inbox_stats(self) -> InboxStats:
        """Get statistics for the support inbox."""
        tickets = list(self._tickets.values())

        today = datetime.now(timezone.utc).date()

        open_tickets = [t for t in tickets if t.status == TicketStatus.OPEN]
        in_progress = [t for t in tickets if t.status == TicketStatus.IN_PROGRESS]
        resolved_today = [
            t for t in tickets
            if t.status == TicketStatus.RESOLVED
            and t.resolved_at
            and t.resolved_at.date() == today
        ]
        escalated = [t for t in tickets if t.status == TicketStatus.ESCALATED]

        # Calculate average response time
        response_times: list[float] = []
        for ticket in tickets:
            if ticket.first_response_at:
                delta = ticket.first_response_at - ticket.created_at
                response_times.append(delta.total_seconds() / 3600)

        avg_response = sum(response_times) / len(response_times) if response_times else 0

        # Calculate average resolution time
        resolution_times: list[float] = []
        for ticket in tickets:
            if ticket.resolved_at:
                delta = ticket.resolved_at - ticket.created_at
                resolution_times.append(delta.total_seconds() / 3600)

        avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0

        # Count by category
        by_category: dict[str, int] = {}
        for ticket in tickets:
            cat = ticket.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by priority
        by_priority: dict[str, int] = {}
        for ticket in tickets:
            pri = ticket.priority.value
            by_priority[pri] = by_priority.get(pri, 0) + 1

        return InboxStats(
            total_open=len(open_tickets),
            total_in_progress=len(in_progress),
            total_resolved_today=len(resolved_today),
            total_escalated=len(escalated),
            avg_response_time_hours=round(avg_response, 2),
            avg_resolution_time_hours=round(avg_resolution, 2),
            by_category=by_category,
            by_priority=by_priority,
        )

    def get_overdue_tickets(self) -> list[SupportTicket]:
        """Get tickets that have exceeded their SLA."""
        now = datetime.now(timezone.utc)

        overdue = [
            t for t in self._tickets.values()
            if t.status in [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]
            and t.sla_due_at
            and t.sla_due_at < now
        ]

        return sorted(overdue, key=lambda x: x.sla_due_at or x.created_at)

    def get_unassigned_tickets(self) -> list[SupportTicket]:
        """Get open tickets that are not assigned."""
        unassigned = [
            t for t in self._tickets.values()
            if t.status == TicketStatus.OPEN
            and t.assigned_to is None
        ]

        return sorted(unassigned, key=lambda x: x.created_at)

    def get_ticket_summary(self, ticket_id: UUID) -> Optional[dict]:
        """Get a summary of a ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        a3_lite = self.get_a3_lite_for_ticket(ticket_id)

        return {
            "id": str(ticket.id),
            "subject": ticket.subject,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "category": ticket.category.value,
            "submitter": ticket.submitter_name or str(ticket.submitted_by),
            "assignee": ticket.assignee_name,
            "created_at": ticket.created_at.isoformat(),
            "sla_due_at": ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
            "comment_count": len(ticket.comments),
            "has_a3_lite": a3_lite is not None,
            "a3_lite_id": str(a3_lite.id) if a3_lite else None,
            "routing_target": ticket.routing_decision.target.value if ticket.routing_decision else None,
        }

    # --- SLA Management ---

    def update_sla_hours(
        self,
        priority: TicketPriority,
        hours: int,
    ) -> None:
        """Update SLA hours for a priority level."""
        if hours > 0:
            self._default_sla_hours[priority] = hours

    def get_sla_config(self) -> dict[str, int]:
        """Get current SLA configuration."""
        return {p.value: h for p, h in self._default_sla_hours.items()}

    # --- Search ---

    def search_tickets(
        self,
        query: str,
        limit: int = 50,
    ) -> list[SupportTicket]:
        """Search tickets by subject or description."""
        query_lower = query.lower()

        matches = [
            t for t in self._tickets.values()
            if query_lower in t.subject.lower()
            or query_lower in t.description.lower()
            or any(query_lower in tag.lower() for tag in t.tags)
        ]

        return sorted(matches, key=lambda x: x.created_at, reverse=True)[:limit]
