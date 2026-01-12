"""
Notification Triggers Engine.

A service for generating notifications based on system events and conditions.

Key features:
- Trigger types: overdue tasks, stalled RFQs, missing CTQs, low-margin quotes, 
  aging approvals, recurring abnormalities
- Recipients by role and ownership
- Snooze/acknowledge to prevent fatigue
- Channels: in-app first, email later
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class TriggerType(str, Enum):
    """Type of notification trigger."""
    
    # Task triggers
    TASK_OVERDUE = "task_overdue"
    TASK_DUE_SOON = "task_due_soon"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    
    # RFQ triggers
    RFQ_STALLED = "rfq_stalled"
    RFQ_DUE_SOON = "rfq_due_soon"
    RFQ_OVERDUE = "rfq_overdue"
    RFQ_ASSIGNED = "rfq_assigned"
    RFQ_INCOMPLETE = "rfq_incomplete"
    
    # Quote triggers
    QUOTE_LOW_MARGIN = "quote_low_margin"
    QUOTE_APPROVAL_NEEDED = "quote_approval_needed"
    QUOTE_APPROVAL_AGING = "quote_approval_aging"
    QUOTE_APPROVED = "quote_approved"
    QUOTE_REJECTED = "quote_rejected"
    
    # CTQ triggers
    CTQ_MISSING = "ctq_missing"
    CTQ_OUT_OF_SPEC = "ctq_out_of_spec"
    
    # A3/Andon triggers
    RECURRING_ABNORMALITY = "recurring_abnormality"
    A3_CREATED = "a3_created"
    A3_ACTION_OVERDUE = "a3_action_overdue"
    
    # Training triggers
    CERTIFICATION_EXPIRING = "certification_expiring"
    SKILL_GAP = "skill_gap"
    
    # System triggers
    ESCALATION = "escalation"
    MENTION = "mention"
    REMINDER = "reminder"


class RecipientRole(str, Enum):
    """Role-based recipient targeting."""
    
    OWNER = "owner"  # Object owner
    ASSIGNEE = "assignee"  # Assigned user
    MANAGER = "manager"  # Direct manager
    GM = "gm"  # General manager
    APPROVER = "approver"  # Approval role
    EXEC_SPONSOR = "exec_sponsor"  # Executive sponsor
    TEAM_MEMBERS = "team_members"  # All team members
    WATCHERS = "watchers"  # Subscribed users
    DEPARTMENT_HEAD = "department_head"
    QUALITY = "quality"  # Quality team
    OPERATIONS = "operations"  # Operations team
    FINANCE = "finance"  # Finance team


class NotificationChannel(str, Enum):
    """Delivery channel for notifications."""
    
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationPriority(str, Enum):
    """Priority level for notifications."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SnoozeStatus(str, Enum):
    """Snooze/acknowledge status."""
    
    ACTIVE = "active"
    SNOOZED = "snoozed"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


@dataclass
class TriggerCondition:
    """
    A condition that can trigger a notification.
    
    Defines when to trigger, who to notify, and what to say.
    """
    
    trigger_type: TriggerType
    name: str
    description: str
    
    # Target recipients by role
    recipients: list[RecipientRole] = field(default_factory=list)
    
    # Delivery channels
    channels: list[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.IN_APP])
    
    # Priority
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Timing
    check_interval_minutes: int = 60  # How often to check
    cooldown_minutes: int = 1440  # Min time between repeat notifications (24h default)
    
    # Threshold values
    days_before_due: int | None = None  # For "due soon" triggers
    days_overdue: int | None = None  # For overdue triggers
    margin_threshold: float | None = None  # For low-margin triggers
    occurrence_count: int | None = None  # For recurring triggers
    
    # Message templates
    title_template: str = "{trigger_type}: {entity_type} {entity_id}"
    message_template: str = "{description}"
    
    # Enabled
    is_enabled: bool = True


@dataclass
class NotificationTarget:
    """Target recipient for a notification."""
    
    user_id: UUID
    role: RecipientRole
    email: str | None = None
    name: str | None = None


@dataclass
class GeneratedNotification:
    """A notification ready to be sent."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    trigger_type: TriggerType = TriggerType.TASK_OVERDUE
    
    # Content
    title: str = ""
    message: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Recipient
    recipient_id: UUID | None = None
    recipient_role: RecipientRole = RecipientRole.OWNER
    
    # Related entity
    entity_type: str | None = None
    entity_id: str | None = None
    action_url: str | None = None
    
    # Channels
    channels: list[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.IN_APP])
    
    # Timing
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at: datetime | None = None
    
    # Status
    snooze_status: SnoozeStatus = SnoozeStatus.ACTIVE
    snooze_until: datetime | None = None
    
    # Extra data
    extra_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerEvaluationResult:
    """Result of evaluating triggers."""
    
    notifications: list[GeneratedNotification]
    triggers_checked: int = 0
    triggers_fired: int = 0
    entities_scanned: int = 0
    evaluation_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class UserSnoozeSettings:
    """User's snooze and acknowledge settings."""
    
    user_id: UUID
    
    # Global snooze
    global_snooze_until: datetime | None = None
    
    # Per-trigger snooze
    trigger_snoozes: dict[str, datetime] = field(default_factory=dict)
    
    # Per-entity snooze (entity_type::entity_id -> snooze_until)
    entity_snoozes: dict[str, datetime] = field(default_factory=dict)
    
    # Acknowledged (won't notify again)
    acknowledged_entities: set[str] = field(default_factory=set)


class NotificationTriggersService:
    """
    Service for evaluating notification triggers and generating notifications.
    
    Key responsibilities:
    - Define and manage trigger conditions
    - Evaluate conditions against system data
    - Generate notifications with proper targeting
    - Respect snooze and acknowledge settings
    """
    
    def __init__(self):
        """Initialize with default triggers."""
        self._triggers: dict[TriggerType, TriggerCondition] = {}
        self._snooze_settings: dict[UUID, UserSnoozeSettings] = {}
        self._last_sent: dict[str, datetime] = {}  # trigger_key -> last_sent_at
        self._register_default_triggers()
    
    def _register_default_triggers(self) -> None:
        """Register default notification triggers."""
        defaults = [
            TriggerCondition(
                trigger_type=TriggerType.TASK_OVERDUE,
                name="Task Overdue",
                description="Task has passed its due date",
                recipients=[RecipientRole.ASSIGNEE, RecipientRole.OWNER],
                priority=NotificationPriority.HIGH,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                title_template="Overdue Task: {entity_name}",
                message_template="Task '{entity_name}' was due on {due_date} and is now {days_overdue} day(s) overdue.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.TASK_DUE_SOON,
                name="Task Due Soon",
                description="Task is due within the threshold",
                recipients=[RecipientRole.ASSIGNEE],
                priority=NotificationPriority.NORMAL,
                days_before_due=1,
                title_template="Task Due Tomorrow: {entity_name}",
                message_template="Task '{entity_name}' is due on {due_date}.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.RFQ_STALLED,
                name="Stalled RFQ",
                description="RFQ has had no activity for extended period",
                recipients=[RecipientRole.OWNER, RecipientRole.MANAGER],
                priority=NotificationPriority.HIGH,
                days_overdue=7,
                title_template="Stalled RFQ: {entity_name}",
                message_template="RFQ '{entity_name}' has had no activity for {days_stalled} days.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.RFQ_INCOMPLETE,
                name="Incomplete RFQ",
                description="RFQ is missing required information",
                recipients=[RecipientRole.OWNER],
                priority=NotificationPriority.NORMAL,
                title_template="Incomplete RFQ: {entity_name}",
                message_template="RFQ '{entity_name}' is {completeness}% complete. Missing: {missing_fields}.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.QUOTE_LOW_MARGIN,
                name="Low Margin Quote",
                description="Quote margin is below threshold",
                recipients=[RecipientRole.OWNER, RecipientRole.MANAGER, RecipientRole.FINANCE],
                priority=NotificationPriority.HIGH,
                margin_threshold=15.0,
                title_template="Low Margin Quote: {entity_name}",
                message_template="Quote '{entity_name}' has a margin of {margin}%, which is below the {threshold}% threshold.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.QUOTE_APPROVAL_NEEDED,
                name="Quote Needs Approval",
                description="Quote is waiting for approval",
                recipients=[RecipientRole.APPROVER],
                priority=NotificationPriority.HIGH,
                title_template="Quote Awaiting Approval: {entity_name}",
                message_template="Quote '{entity_name}' requires your approval. Value: ${value}.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.QUOTE_APPROVAL_AGING,
                name="Quote Approval Aging",
                description="Quote approval has been pending too long",
                recipients=[RecipientRole.APPROVER, RecipientRole.MANAGER],
                priority=NotificationPriority.URGENT,
                days_overdue=3,
                title_template="Aging Quote Approval: {entity_name}",
                message_template="Quote '{entity_name}' has been awaiting approval for {days_pending} days.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.CTQ_MISSING,
                name="Missing CTQ",
                description="Product is missing CTQ definitions",
                recipients=[RecipientRole.QUALITY, RecipientRole.OWNER],
                priority=NotificationPriority.NORMAL,
                title_template="Missing CTQ: {entity_name}",
                message_template="Product '{entity_name}' has no CTQ definitions.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.RECURRING_ABNORMALITY,
                name="Recurring Abnormality",
                description="Same issue has occurred multiple times",
                recipients=[RecipientRole.OWNER, RecipientRole.MANAGER, RecipientRole.QUALITY],
                priority=NotificationPriority.HIGH,
                occurrence_count=3,
                title_template="Recurring Issue: {symptom}",
                message_template="Issue '{symptom}' has occurred {count} times at {station}.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.CERTIFICATION_EXPIRING,
                name="Certification Expiring",
                description="User certification is about to expire",
                recipients=[RecipientRole.OWNER, RecipientRole.MANAGER],
                priority=NotificationPriority.NORMAL,
                days_before_due=30,
                title_template="Certification Expiring: {skill_name}",
                message_template="Your certification for '{skill_name}' expires on {expiration_date}.",
            ),
            TriggerCondition(
                trigger_type=TriggerType.ESCALATION,
                name="Escalation",
                description="Issue has been escalated",
                recipients=[RecipientRole.MANAGER, RecipientRole.GM],
                priority=NotificationPriority.URGENT,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
                title_template="Escalation: {entity_type} {entity_id}",
                message_template="Issue has been escalated: {reason}.",
            ),
        ]
        
        for trigger in defaults:
            self._triggers[trigger.trigger_type] = trigger
    
    def get_trigger(self, trigger_type: TriggerType) -> TriggerCondition | None:
        """Get a trigger condition by type."""
        return self._triggers.get(trigger_type)
    
    def get_all_triggers(self) -> list[TriggerCondition]:
        """Get all registered triggers."""
        return list(self._triggers.values())
    
    def register_trigger(self, trigger: TriggerCondition) -> None:
        """Register or update a trigger condition."""
        self._triggers[trigger.trigger_type] = trigger
    
    def enable_trigger(self, trigger_type: TriggerType) -> bool:
        """Enable a trigger."""
        if trigger_type in self._triggers:
            self._triggers[trigger_type].is_enabled = True
            return True
        return False
    
    def disable_trigger(self, trigger_type: TriggerType) -> bool:
        """Disable a trigger."""
        if trigger_type in self._triggers:
            self._triggers[trigger_type].is_enabled = False
            return True
        return False
    
    def evaluate_tasks(
        self,
        tasks: list[dict[str, Any]],
        users: dict[UUID, NotificationTarget],
        reference_date: datetime | None = None,
    ) -> list[GeneratedNotification]:
        """
        Evaluate task-related triggers.
        
        Args:
            tasks: List of task dicts with id, title, due_date, status, assignee_id, owner_id
            users: User lookup map
            reference_date: Reference date (defaults to now)
            
        Returns:
            List of generated notifications
        """
        ref_date = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)
        notifications = []
        
        overdue_trigger = self._triggers.get(TriggerType.TASK_OVERDUE)
        due_soon_trigger = self._triggers.get(TriggerType.TASK_DUE_SOON)
        
        for task in tasks:
            due_date = self._parse_datetime(task.get("due_date"))
            if not due_date:
                continue
            
            status = task.get("status", "")
            if status in ("completed", "cancelled"):
                continue
            
            entity_key = f"task::{task.get('id')}"
            
            # Check overdue
            if overdue_trigger and overdue_trigger.is_enabled:
                if due_date < ref_date:
                    days_overdue = (ref_date - due_date).days
                    
                    for role in overdue_trigger.recipients:
                        recipient = self._get_recipient(task, role, users)
                        if recipient and not self._is_snoozed(recipient.user_id, TriggerType.TASK_OVERDUE, entity_key):
                            notifications.append(GeneratedNotification(
                                trigger_type=TriggerType.TASK_OVERDUE,
                                title=overdue_trigger.title_template.format(
                                    entity_name=task.get("title", "Untitled"),
                                ),
                                message=overdue_trigger.message_template.format(
                                    entity_name=task.get("title", "Untitled"),
                                    due_date=due_date.strftime("%Y-%m-%d"),
                                    days_overdue=days_overdue,
                                ),
                                priority=overdue_trigger.priority,
                                recipient_id=recipient.user_id,
                                recipient_role=role,
                                entity_type="task",
                                entity_id=str(task.get("id")),
                                channels=overdue_trigger.channels,
                                extra_data={"days_overdue": days_overdue},
                            ))
            
            # Check due soon
            if due_soon_trigger and due_soon_trigger.is_enabled:
                days_until = (due_date - ref_date).days
                threshold = due_soon_trigger.days_before_due or 1
                
                if 0 <= days_until <= threshold:
                    for role in due_soon_trigger.recipients:
                        recipient = self._get_recipient(task, role, users)
                        if recipient and not self._is_snoozed(recipient.user_id, TriggerType.TASK_DUE_SOON, entity_key):
                            notifications.append(GeneratedNotification(
                                trigger_type=TriggerType.TASK_DUE_SOON,
                                title=due_soon_trigger.title_template.format(
                                    entity_name=task.get("title", "Untitled"),
                                ),
                                message=due_soon_trigger.message_template.format(
                                    entity_name=task.get("title", "Untitled"),
                                    due_date=due_date.strftime("%Y-%m-%d"),
                                ),
                                priority=due_soon_trigger.priority,
                                recipient_id=recipient.user_id,
                                recipient_role=role,
                                entity_type="task",
                                entity_id=str(task.get("id")),
                                channels=due_soon_trigger.channels,
                                extra_data={"days_until_due": days_until},
                            ))
        
        return notifications
    
    def evaluate_rfqs(
        self,
        rfqs: list[dict[str, Any]],
        users: dict[UUID, NotificationTarget],
        reference_date: datetime | None = None,
    ) -> list[GeneratedNotification]:
        """
        Evaluate RFQ-related triggers.
        
        Args:
            rfqs: List of RFQ dicts
            users: User lookup map
            reference_date: Reference date
            
        Returns:
            List of generated notifications
        """
        ref_date = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)
        notifications = []
        
        stalled_trigger = self._triggers.get(TriggerType.RFQ_STALLED)
        incomplete_trigger = self._triggers.get(TriggerType.RFQ_INCOMPLETE)
        
        for rfq in rfqs:
            status = rfq.get("status", "")
            if status in ("closed", "cancelled", "won", "lost"):
                continue
            
            entity_key = f"rfq::{rfq.get('id')}"
            
            # Check stalled
            if stalled_trigger and stalled_trigger.is_enabled:
                last_activity = self._parse_datetime(rfq.get("updated_at") or rfq.get("last_activity_at"))
                if last_activity:
                    days_stalled = (ref_date - last_activity).days
                    threshold = stalled_trigger.days_overdue or 7
                    
                    if days_stalled >= threshold:
                        for role in stalled_trigger.recipients:
                            recipient = self._get_recipient(rfq, role, users)
                            if recipient and not self._is_snoozed(recipient.user_id, TriggerType.RFQ_STALLED, entity_key):
                                notifications.append(GeneratedNotification(
                                    trigger_type=TriggerType.RFQ_STALLED,
                                    title=stalled_trigger.title_template.format(
                                        entity_name=rfq.get("title") or rfq.get("rfq_number", "Untitled"),
                                    ),
                                    message=stalled_trigger.message_template.format(
                                        entity_name=rfq.get("title") or rfq.get("rfq_number", "Untitled"),
                                        days_stalled=days_stalled,
                                    ),
                                    priority=stalled_trigger.priority,
                                    recipient_id=recipient.user_id,
                                    recipient_role=role,
                                    entity_type="rfq",
                                    entity_id=str(rfq.get("id")),
                                    channels=stalled_trigger.channels,
                                    extra_data={"days_stalled": days_stalled},
                                ))
            
            # Check incomplete
            if incomplete_trigger and incomplete_trigger.is_enabled:
                completeness = rfq.get("completeness_score")
                missing_fields = rfq.get("missing_fields", [])
                
                if completeness is not None and completeness < 100 and missing_fields:
                    for role in incomplete_trigger.recipients:
                        recipient = self._get_recipient(rfq, role, users)
                        if recipient and not self._is_snoozed(recipient.user_id, TriggerType.RFQ_INCOMPLETE, entity_key):
                            notifications.append(GeneratedNotification(
                                trigger_type=TriggerType.RFQ_INCOMPLETE,
                                title=incomplete_trigger.title_template.format(
                                    entity_name=rfq.get("title") or rfq.get("rfq_number", "Untitled"),
                                ),
                                message=incomplete_trigger.message_template.format(
                                    entity_name=rfq.get("title") or rfq.get("rfq_number", "Untitled"),
                                    completeness=completeness,
                                    missing_fields=", ".join(missing_fields[:3]),
                                ),
                                priority=incomplete_trigger.priority,
                                recipient_id=recipient.user_id,
                                recipient_role=role,
                                entity_type="rfq",
                                entity_id=str(rfq.get("id")),
                                channels=incomplete_trigger.channels,
                                extra_data={
                                    "completeness": completeness,
                                    "missing_fields": missing_fields,
                                },
                            ))
        
        return notifications
    
    def evaluate_quotes(
        self,
        quotes: list[dict[str, Any]],
        users: dict[UUID, NotificationTarget],
        reference_date: datetime | None = None,
    ) -> list[GeneratedNotification]:
        """
        Evaluate quote-related triggers.
        
        Args:
            quotes: List of quote dicts
            users: User lookup map
            reference_date: Reference date
            
        Returns:
            List of generated notifications
        """
        ref_date = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)
        notifications = []
        
        low_margin_trigger = self._triggers.get(TriggerType.QUOTE_LOW_MARGIN)
        approval_trigger = self._triggers.get(TriggerType.QUOTE_APPROVAL_NEEDED)
        aging_trigger = self._triggers.get(TriggerType.QUOTE_APPROVAL_AGING)
        
        for quote in quotes:
            status = quote.get("status", "")
            entity_key = f"quote::{quote.get('id')}"
            
            # Check low margin
            if low_margin_trigger and low_margin_trigger.is_enabled:
                margin = quote.get("margin_percent") or quote.get("gross_margin")
                threshold = low_margin_trigger.margin_threshold or 15.0
                
                if margin is not None and margin < threshold:
                    for role in low_margin_trigger.recipients:
                        recipient = self._get_recipient(quote, role, users)
                        if recipient and not self._is_snoozed(recipient.user_id, TriggerType.QUOTE_LOW_MARGIN, entity_key):
                            notifications.append(GeneratedNotification(
                                trigger_type=TriggerType.QUOTE_LOW_MARGIN,
                                title=low_margin_trigger.title_template.format(
                                    entity_name=quote.get("quote_number", "Untitled"),
                                ),
                                message=low_margin_trigger.message_template.format(
                                    entity_name=quote.get("quote_number", "Untitled"),
                                    margin=f"{margin:.1f}",
                                    threshold=threshold,
                                ),
                                priority=low_margin_trigger.priority,
                                recipient_id=recipient.user_id,
                                recipient_role=role,
                                entity_type="quote",
                                entity_id=str(quote.get("id")),
                                channels=low_margin_trigger.channels,
                                extra_data={"margin": margin, "threshold": threshold},
                            ))
            
            # Check approval needed
            if approval_trigger and approval_trigger.is_enabled:
                if status in ("pending_approval", "awaiting_approval"):
                    for role in approval_trigger.recipients:
                        recipient = self._get_recipient(quote, role, users)
                        if recipient and not self._is_snoozed(recipient.user_id, TriggerType.QUOTE_APPROVAL_NEEDED, entity_key):
                            notifications.append(GeneratedNotification(
                                trigger_type=TriggerType.QUOTE_APPROVAL_NEEDED,
                                title=approval_trigger.title_template.format(
                                    entity_name=quote.get("quote_number", "Untitled"),
                                ),
                                message=approval_trigger.message_template.format(
                                    entity_name=quote.get("quote_number", "Untitled"),
                                    value=f"{quote.get('total_value', 0):,.2f}",
                                ),
                                priority=approval_trigger.priority,
                                recipient_id=recipient.user_id,
                                recipient_role=role,
                                entity_type="quote",
                                entity_id=str(quote.get("id")),
                                channels=approval_trigger.channels,
                            ))
            
            # Check aging approval
            if aging_trigger and aging_trigger.is_enabled:
                if status in ("pending_approval", "awaiting_approval"):
                    submitted_at = self._parse_datetime(quote.get("submitted_for_approval_at") or quote.get("updated_at"))
                    if submitted_at:
                        days_pending = (ref_date - submitted_at).days
                        threshold = aging_trigger.days_overdue or 3
                        
                        if days_pending >= threshold:
                            for role in aging_trigger.recipients:
                                recipient = self._get_recipient(quote, role, users)
                                if recipient and not self._is_snoozed(recipient.user_id, TriggerType.QUOTE_APPROVAL_AGING, entity_key):
                                    notifications.append(GeneratedNotification(
                                        trigger_type=TriggerType.QUOTE_APPROVAL_AGING,
                                        title=aging_trigger.title_template.format(
                                            entity_name=quote.get("quote_number", "Untitled"),
                                        ),
                                        message=aging_trigger.message_template.format(
                                            entity_name=quote.get("quote_number", "Untitled"),
                                            days_pending=days_pending,
                                        ),
                                        priority=aging_trigger.priority,
                                        recipient_id=recipient.user_id,
                                        recipient_role=role,
                                        entity_type="quote",
                                        entity_id=str(quote.get("id")),
                                        channels=aging_trigger.channels,
                                        extra_data={"days_pending": days_pending},
                                    ))
        
        return notifications
    
    def evaluate_certifications(
        self,
        certifications: list[dict[str, Any]],
        users: dict[UUID, NotificationTarget],
        reference_date: datetime | None = None,
    ) -> list[GeneratedNotification]:
        """
        Evaluate certification expiration triggers.
        
        Args:
            certifications: List of certification/skill dicts
            users: User lookup map
            reference_date: Reference date
            
        Returns:
            List of generated notifications
        """
        ref_date = reference_date or datetime.now(timezone.utc).replace(tzinfo=None)
        notifications = []
        
        expiring_trigger = self._triggers.get(TriggerType.CERTIFICATION_EXPIRING)
        
        if not expiring_trigger or not expiring_trigger.is_enabled:
            return notifications
        
        for cert in certifications:
            expires_at = self._parse_datetime(cert.get("expires_at") or cert.get("expiration_date"))
            if not expires_at:
                continue
            
            days_until = (expires_at - ref_date).days
            threshold = expiring_trigger.days_before_due or 30
            
            if 0 <= days_until <= threshold:
                entity_key = f"certification::{cert.get('id')}"
                user_id = cert.get("user_id")
                
                if user_id:
                    if isinstance(user_id, str):
                        user_id = UUID(user_id)
                    
                    if not self._is_snoozed(user_id, TriggerType.CERTIFICATION_EXPIRING, entity_key):
                        notifications.append(GeneratedNotification(
                            trigger_type=TriggerType.CERTIFICATION_EXPIRING,
                            title=expiring_trigger.title_template.format(
                                skill_name=cert.get("skill_name", "Certification"),
                            ),
                            message=expiring_trigger.message_template.format(
                                skill_name=cert.get("skill_name", "Certification"),
                                expiration_date=expires_at.strftime("%Y-%m-%d"),
                            ),
                            priority=expiring_trigger.priority,
                            recipient_id=user_id,
                            recipient_role=RecipientRole.OWNER,
                            entity_type="certification",
                            entity_id=str(cert.get("id")),
                            channels=expiring_trigger.channels,
                            extra_data={
                                "days_until_expiration": days_until,
                                "skill_name": cert.get("skill_name"),
                            },
                        ))
        
        return notifications
    
    def snooze_for_user(
        self,
        user_id: UUID,
        trigger_type: TriggerType | None = None,
        entity_key: str | None = None,
        snooze_hours: int = 24,
    ) -> None:
        """
        Snooze notifications for a user.
        
        Args:
            user_id: User to snooze for
            trigger_type: Specific trigger to snooze (None = all)
            entity_key: Specific entity to snooze (format: "type::id")
            snooze_hours: Duration of snooze in hours
        """
        if user_id not in self._snooze_settings:
            self._snooze_settings[user_id] = UserSnoozeSettings(user_id=user_id)
        
        settings = self._snooze_settings[user_id]
        snooze_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=snooze_hours)
        
        if trigger_type is None and entity_key is None:
            settings.global_snooze_until = snooze_until
        elif trigger_type and entity_key is None:
            settings.trigger_snoozes[trigger_type.value] = snooze_until
        elif entity_key:
            settings.entity_snoozes[entity_key] = snooze_until
    
    def acknowledge_entity(
        self,
        user_id: UUID,
        entity_key: str,
    ) -> None:
        """
        Acknowledge an entity to stop notifications permanently.
        
        Args:
            user_id: User acknowledging
            entity_key: Entity key (format: "type::id")
        """
        if user_id not in self._snooze_settings:
            self._snooze_settings[user_id] = UserSnoozeSettings(user_id=user_id)
        
        self._snooze_settings[user_id].acknowledged_entities.add(entity_key)
    
    def clear_snooze(
        self,
        user_id: UUID,
        trigger_type: TriggerType | None = None,
        entity_key: str | None = None,
    ) -> None:
        """Clear snooze settings."""
        if user_id not in self._snooze_settings:
            return
        
        settings = self._snooze_settings[user_id]
        
        if trigger_type is None and entity_key is None:
            settings.global_snooze_until = None
        elif trigger_type:
            settings.trigger_snoozes.pop(trigger_type.value, None)
        elif entity_key:
            settings.entity_snoozes.pop(entity_key, None)
            settings.acknowledged_entities.discard(entity_key)
    
    def get_user_snooze_settings(self, user_id: UUID) -> UserSnoozeSettings:
        """Get snooze settings for a user."""
        if user_id not in self._snooze_settings:
            self._snooze_settings[user_id] = UserSnoozeSettings(user_id=user_id)
        return self._snooze_settings[user_id]
    
    # --------------------------------------------------------------------------
    # Private Methods
    # --------------------------------------------------------------------------
    
    def _parse_datetime(self, value: Any) -> datetime | None:
        """Parse a datetime value."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except (ValueError, AttributeError):
                return None
        return None
    
    def _get_recipient(
        self,
        entity: dict[str, Any],
        role: RecipientRole,
        users: dict[UUID, NotificationTarget],
    ) -> NotificationTarget | None:
        """Get a recipient based on role and entity."""
        user_id = None
        
        if role == RecipientRole.OWNER:
            user_id = entity.get("owner_id") or entity.get("created_by_id")
        elif role == RecipientRole.ASSIGNEE:
            user_id = entity.get("assignee_id") or entity.get("assigned_to_id")
        elif role == RecipientRole.MANAGER:
            user_id = entity.get("manager_id")
        elif role == RecipientRole.APPROVER:
            user_id = entity.get("approver_id") or entity.get("approved_by_id")
        
        if user_id:
            if isinstance(user_id, str):
                user_id = UUID(user_id)
            return users.get(user_id)
        
        return None
    
    def _is_snoozed(
        self,
        user_id: UUID,
        trigger_type: TriggerType,
        entity_key: str,
    ) -> bool:
        """Check if notifications are snoozed for this user/trigger/entity."""
        if user_id not in self._snooze_settings:
            return False
        
        settings = self._snooze_settings[user_id]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Check acknowledged
        if entity_key in settings.acknowledged_entities:
            return True
        
        # Check global snooze
        if settings.global_snooze_until and settings.global_snooze_until > now:
            return True
        
        # Check trigger snooze
        if trigger_type.value in settings.trigger_snoozes:
            if settings.trigger_snoozes[trigger_type.value] > now:
                return True
        
        # Check entity snooze
        if entity_key in settings.entity_snoozes:
            if settings.entity_snoozes[entity_key] > now:
                return True
        
        return False


class NotificationTriggersJobRunner:
    """
    Background job runner for periodic trigger evaluation.
    """
    
    def __init__(
        self,
        service: NotificationTriggersService | None = None,
        on_notification: Callable[[GeneratedNotification], None] | None = None,
    ):
        """
        Initialize the job runner.
        
        Args:
            service: Notification triggers service
            on_notification: Callback for each generated notification
        """
        self.service = service or NotificationTriggersService()
        self.on_notification = on_notification
        self._last_run: datetime | None = None
    
    async def run(
        self,
        tasks: list[dict[str, Any]] | None = None,
        rfqs: list[dict[str, Any]] | None = None,
        quotes: list[dict[str, Any]] | None = None,
        certifications: list[dict[str, Any]] | None = None,
        users: dict[UUID, NotificationTarget] | None = None,
        reference_date: datetime | None = None,
        deliver: bool = False,
    ) -> TriggerEvaluationResult:
        """
        Run trigger evaluation.
        
        Args:
            tasks: Task data
            rfqs: RFQ data
            quotes: Quote data
            certifications: Certification data
            users: User lookup map
            reference_date: Reference date
            deliver: Whether to call on_notification callback
            
        Returns:
            Evaluation result
        """
        import time
        start = time.time()
        
        self._last_run = datetime.now(timezone.utc).replace(tzinfo=None)
        ref_date = reference_date or self._last_run
        users = users or {}
        
        all_notifications = []
        triggers_checked = 0
        entities_scanned = 0
        errors = []
        
        # Evaluate tasks
        if tasks:
            try:
                entities_scanned += len(tasks)
                triggers_checked += 2
                notifications = self.service.evaluate_tasks(tasks, users, ref_date)
                all_notifications.extend(notifications)
            except Exception as e:
                errors.append(f"Task evaluation error: {str(e)}")
        
        # Evaluate RFQs
        if rfqs:
            try:
                entities_scanned += len(rfqs)
                triggers_checked += 2
                notifications = self.service.evaluate_rfqs(rfqs, users, ref_date)
                all_notifications.extend(notifications)
            except Exception as e:
                errors.append(f"RFQ evaluation error: {str(e)}")
        
        # Evaluate quotes
        if quotes:
            try:
                entities_scanned += len(quotes)
                triggers_checked += 3
                notifications = self.service.evaluate_quotes(quotes, users, ref_date)
                all_notifications.extend(notifications)
            except Exception as e:
                errors.append(f"Quote evaluation error: {str(e)}")
        
        # Evaluate certifications
        if certifications:
            try:
                entities_scanned += len(certifications)
                triggers_checked += 1
                notifications = self.service.evaluate_certifications(certifications, users, ref_date)
                all_notifications.extend(notifications)
            except Exception as e:
                errors.append(f"Certification evaluation error: {str(e)}")
        
        # Deliver
        if deliver and self.on_notification:
            for notification in all_notifications:
                try:
                    self.on_notification(notification)
                except Exception as e:
                    errors.append(f"Notification delivery error: {str(e)}")
        
        elapsed_ms = (time.time() - start) * 1000
        
        return TriggerEvaluationResult(
            notifications=all_notifications,
            triggers_checked=triggers_checked,
            triggers_fired=len(all_notifications),
            entities_scanned=entities_scanned,
            evaluation_time_ms=elapsed_ms,
            errors=errors,
        )
    
    @property
    def last_run(self) -> datetime | None:
        """Get the last run timestamp."""
        return self._last_run
