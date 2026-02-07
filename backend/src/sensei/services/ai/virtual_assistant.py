"""
Sensei Virtual Assistant - Proactive assistance for manufacturing operations.

Includes:
- SLA Watchdog: Background worker for critical path monitoring
- Meeting Preparation AI: Automated briefing notes and entity extraction
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional
import re
import json
import asyncio
from collections import defaultdict, deque
import hashlib


# =============================================================================
# Constants
# =============================================================================

DEFAULT_SLA_CHECK_INTERVAL = 300  # 5 minutes
CRITICAL_THRESHOLD_HOURS = 24
WARNING_THRESHOLD_HOURS = 48
BRIEFING_MAX_ITEMS = 10


# =============================================================================
# Enums
# =============================================================================

class SLAStatus(Enum):
    """SLA status levels."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    BREACHED = "breached"


class ItemType(Enum):
    """Types of monitored items."""
    RFQ = "rfq"
    QUOTE = "quote"
    ORDER = "order"
    TASK = "task"
    APPROVAL = "approval"
    SHIPMENT = "shipment"


class NotificationType(Enum):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class EntityCategory(Enum):
    """Calendar entity categories."""
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PROJECT = "project"
    RFQ = "rfq"
    ORDER = "order"
    PERSON = "person"
    LOCATION = "location"
    TOPIC = "topic"


class BriefingSection(Enum):
    """Briefing note sections."""
    EXECUTIVE_SUMMARY = "executive_summary"
    KEY_METRICS = "key_metrics"
    ACTION_ITEMS = "action_items"
    RISK_ALERTS = "risk_alerts"
    RECENT_UPDATES = "recent_updates"
    BACKGROUND = "background"
    AGENDA_ITEMS = "agenda_items"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SLADeadline:
    """SLA deadline for a monitored item."""
    item_id: str
    item_type: ItemType
    deadline: datetime
    description: str
    owner_id: str
    priority: int = 1
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeToFailure:
    """Time to failure calculation result."""
    item_id: str
    item_type: ItemType
    deadline: datetime
    time_remaining: timedelta
    status: SLAStatus
    risk_score: float  # 0.0 to 1.0
    blocking_factors: list[str] = field(default_factory=list)
    estimated_completion: Optional[datetime] = None
    confidence: float = 0.8
    
    @property
    def hours_remaining(self) -> float:
        """Get hours remaining."""
        return self.time_remaining.total_seconds() / 3600
    
    @property
    def is_on_track(self) -> bool:
        """Check if item is on track."""
        if self.estimated_completion is None:
            return self.status in [SLAStatus.OK, SLAStatus.WARNING]
        return self.estimated_completion <= self.deadline


@dataclass
class Notification:
    """Notification to send."""
    notification_id: str
    recipient_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    item_id: Optional[str] = None
    item_type: Optional[ItemType] = None
    action_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationRule:
    """Rule for sending notifications."""
    rule_id: str
    item_type: ItemType
    status: SLAStatus
    notification_types: list[NotificationType]
    recipient_roles: list[str]
    priority: NotificationPriority
    cooldown_minutes: int = 60
    template: str = ""
    enabled: bool = True


@dataclass
class CalendarEvent:
    """Calendar event representation."""
    event_id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    organizer: Optional[str] = None
    attendees: list[str] = field(default_factory=list)
    is_recurring: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedEntity:
    """Entity extracted from calendar invite."""
    entity_type: EntityCategory
    value: str
    normalized_value: str
    confidence: float
    linked_record_id: Optional[str] = None
    linked_record_type: Optional[str] = None
    context: str = ""


@dataclass
class BriefingItem:
    """Item in a briefing note."""
    section: BriefingSection
    title: str
    content: str
    priority: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    source_records: list[str] = field(default_factory=list)


@dataclass
class BriefingNote:
    """Generated briefing note."""
    briefing_id: str
    meeting_id: str
    title: str
    generated_at: datetime
    items: list[BriefingItem] = field(default_factory=list)
    extracted_entities: list[ExtractedEntity] = field(default_factory=list)
    linked_records: dict[str, list[str]] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        lines = [
            f"# {self.title}",
            "",
            f"*Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]
        
        # Group by section
        sections: dict[BriefingSection, list[BriefingItem]] = defaultdict(list)
        for item in self.items:
            sections[item.section].append(item)
        
        section_order = [
            BriefingSection.EXECUTIVE_SUMMARY,
            BriefingSection.KEY_METRICS,
            BriefingSection.ACTION_ITEMS,
            BriefingSection.RISK_ALERTS,
            BriefingSection.AGENDA_ITEMS,
            BriefingSection.RECENT_UPDATES,
            BriefingSection.BACKGROUND,
        ]
        
        for section in section_order:
            if section not in sections:
                continue
            
            section_title = section.value.replace("_", " ").title()
            lines.append(f"## {section_title}")
            lines.append("")
            
            for item in sorted(sections[section], key=lambda x: -x.priority):
                if item.title:
                    lines.append(f"### {item.title}")
                lines.append(item.content)
                lines.append("")
        
        if self.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "briefing_id": self.briefing_id,
            "meeting_id": self.meeting_id,
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "items": [
                {
                    "section": item.section.value,
                    "title": item.title,
                    "content": item.content,
                    "priority": item.priority,
                }
                for item in self.items
            ],
            "extracted_entities": [
                {
                    "entity_type": e.entity_type.value,
                    "value": e.value,
                    "linked_record_id": e.linked_record_id,
                }
                for e in self.extracted_entities
            ],
            "recommendations": self.recommendations,
        }


# =============================================================================
# SLA Watchdog
# =============================================================================

class CriticalPathCalculator:
    """Calculates critical path for SLA items."""
    
    def __init__(self):
        """Initialize calculator."""
        self._dependency_graph: dict[str, list[str]] = {}
        self._durations: dict[str, float] = {}
    
    def add_item(
        self,
        item_id: str,
        duration_hours: float,
        dependencies: list[str] | None = None
    ) -> None:
        """Add item to graph."""
        self._durations[item_id] = duration_hours
        self._dependency_graph[item_id] = dependencies or []
    
    def calculate_critical_path(self) -> list[str]:
        """Calculate critical path through dependency graph."""
        if not self._dependency_graph:
            return []
        
        # Topological sort with longest path
        earliest_start: dict[str, float] = {}
        earliest_finish: dict[str, float] = {}
        
        # Find items with no dependencies (start nodes)
        start_nodes = [
            item_id for item_id, deps in self._dependency_graph.items()
            if not deps
        ]
        
        # Initialize start nodes
        for item_id in start_nodes:
            earliest_start[item_id] = 0
            earliest_finish[item_id] = self._durations.get(item_id, 0)
        
        # Forward pass
        visited = set(start_nodes)
        queue = deque(start_nodes)
        
        while queue:
            current = queue.popleft()
            
            for item_id, deps in self._dependency_graph.items():
                if current in deps and item_id not in visited:
                    # Check if all dependencies are visited
                    if all(d in visited for d in deps):
                        es = max(earliest_finish.get(d, 0) for d in deps)
                        earliest_start[item_id] = es
                        earliest_finish[item_id] = es + self._durations.get(item_id, 0)
                        visited.add(item_id)
                        queue.append(item_id)
        
        # Find critical path (longest path)
        if not earliest_finish:
            return []
        
        end_item = max(earliest_finish.items(), key=lambda x: x[1])[0]
        
        # Trace back critical path
        critical_path = [end_item]
        current = end_item
        
        while current and self._dependency_graph.get(current):
            deps = self._dependency_graph[current]
            if deps:
                # Find dependency with latest finish (on critical path)
                max_finish: float = -1.0
                next_item: str | None = None
                for dep in deps:
                    if earliest_finish.get(dep, 0) > max_finish:
                        max_finish = earliest_finish[dep]
                        next_item = dep
                if next_item:
                    critical_path.insert(0, next_item)
                    current = next_item
                else:
                    break
            else:
                break
        
        return critical_path
    
    def get_slack_times(self) -> dict[str, float]:
        """Calculate slack times for all items using forward/backward pass."""
        # Forward pass – earliest start / earliest finish
        earliest_start: dict[str, float] = {}
        earliest_finish: dict[str, float] = {}
        topo_order: list[str] = []
        visited: set[str] = set()

        def _forward(node: str) -> float:
            if node in earliest_finish:
                return earliest_finish[node]
            if node in visited:
                return 0.0  # cycle guard
            visited.add(node)
            es = 0.0
            for pred in self._dependencies.get(node, []):
                pred_ef = _forward(pred)
                if pred_ef > es:
                    es = pred_ef
            earliest_start[node] = es
            ef = es + self._durations.get(node, 0.0)
            earliest_finish[node] = ef
            topo_order.append(node)
            return ef

        for item_id in self._durations:
            _forward(item_id)

        if not earliest_finish:
            return {}

        project_end = max(earliest_finish.values())

        # Backward pass – latest start / latest finish
        latest_finish: dict[str, float] = {}
        latest_start: dict[str, float] = {}

        # Build successors map
        successors: dict[str, list[str]] = {k: [] for k in self._durations}
        for item_id, deps in self._dependencies.items():
            for dep in deps:
                if dep in successors:
                    successors[dep].append(item_id)

        for item_id in reversed(topo_order):
            if not successors.get(item_id):
                latest_finish[item_id] = project_end
            else:
                latest_finish[item_id] = min(
                    latest_start.get(s, project_end) for s in successors[item_id]
                )
            latest_start[item_id] = latest_finish[item_id] - self._durations.get(item_id, 0.0)

        # Slack = LS - ES
        slack_times: dict[str, float] = {}
        for item_id in self._durations:
            slack = latest_start.get(item_id, 0.0) - earliest_start.get(item_id, 0.0)
            slack_times[item_id] = max(0.0, round(slack, 4))

        return slack_times


class SLAWatchdog:
    """
    Background worker for monitoring SLA deadlines.
    
    Calculates "Time to Failure" for critical path items and
    sends proactive notifications.
    """
    
    def __init__(
        self,
        check_interval: int = DEFAULT_SLA_CHECK_INTERVAL,
        notification_callback: Callable[[Notification], None] | None = None,
    ):
        """Initialize SLA Watchdog."""
        self.check_interval = check_interval
        self.notification_callback = notification_callback
        
        self._deadlines: dict[str, SLADeadline] = {}
        self._rules: dict[str, NotificationRule] = {}
        self._notification_history: dict[str, datetime] = {}
        self._critical_path_calculator = CriticalPathCalculator()
        
        self._is_running = False
        self._last_check: datetime | None = None
        
        # Register default rules
        self._register_default_rules()
    
    def _register_default_rules(self) -> None:
        """Register default notification rules."""
        default_rules = [
            NotificationRule(
                rule_id="critical_rfq",
                item_type=ItemType.RFQ,
                status=SLAStatus.CRITICAL,
                notification_types=[NotificationType.EMAIL, NotificationType.PUSH],
                recipient_roles=["gm", "sales_manager"],
                priority=NotificationPriority.URGENT,
                template="RFQ {item_id} is critical: {hours} hours remaining",
                cooldown_minutes=30,
            ),
            NotificationRule(
                rule_id="warning_quote",
                item_type=ItemType.QUOTE,
                status=SLAStatus.WARNING,
                notification_types=[NotificationType.IN_APP],
                recipient_roles=["estimator", "sales_rep"],
                priority=NotificationPriority.HIGH,
                template="Quote deadline approaching: {hours} hours remaining",
                cooldown_minutes=120,
            ),
            NotificationRule(
                rule_id="critical_approval",
                item_type=ItemType.APPROVAL,
                status=SLAStatus.CRITICAL,
                notification_types=[NotificationType.EMAIL, NotificationType.SMS],
                recipient_roles=["manager", "gm"],
                priority=NotificationPriority.URGENT,
                template="Approval required urgently for {item_id}",
                cooldown_minutes=15,
            ),
            NotificationRule(
                rule_id="breached_order",
                item_type=ItemType.ORDER,
                status=SLAStatus.BREACHED,
                notification_types=[NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH],
                recipient_roles=["gm", "production_manager", "customer_service"],
                priority=NotificationPriority.URGENT,
                template="SLA BREACHED: Order {item_id} past deadline",
                cooldown_minutes=60,
            ),
        ]
        
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def add_deadline(self, deadline: SLADeadline) -> None:
        """Add or update an SLA deadline."""
        self._deadlines[deadline.item_id] = deadline
        
        # Add to critical path calculator
        self._critical_path_calculator.add_item(
            deadline.item_id,
            duration_hours=24.0,  # Default estimate
            dependencies=deadline.dependencies,
        )
    
    def remove_deadline(self, item_id: str) -> bool:
        """Remove a deadline."""
        if item_id in self._deadlines:
            del self._deadlines[item_id]
            return True
        return False
    
    def add_rule(self, rule: NotificationRule) -> None:
        """Add a notification rule."""
        self._rules[rule.rule_id] = rule
    
    def calculate_time_to_failure(
        self,
        item_id: str,
        now: datetime | None = None
    ) -> TimeToFailure | None:
        """Calculate time to failure for a specific item."""
        deadline = self._deadlines.get(item_id)
        if not deadline:
            return None
        
        now = now or datetime.now(timezone.utc)
        
        # Ensure deadline is timezone-aware
        dl = deadline.deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        
        time_remaining = dl - now
        hours_remaining = time_remaining.total_seconds() / 3600
        
        # Determine status based on time remaining
        if hours_remaining < 0:
            status = SLAStatus.BREACHED
            risk_score = 1.0
        elif hours_remaining < CRITICAL_THRESHOLD_HOURS:
            status = SLAStatus.CRITICAL
            risk_score = 0.8 + (0.2 * (1 - hours_remaining / CRITICAL_THRESHOLD_HOURS))
        elif hours_remaining < WARNING_THRESHOLD_HOURS:
            status = SLAStatus.WARNING
            risk_score = 0.5 + (0.3 * (1 - hours_remaining / WARNING_THRESHOLD_HOURS))
        else:
            status = SLAStatus.OK
            risk_score = max(0.1, 0.5 * (1 - hours_remaining / (WARNING_THRESHOLD_HOURS * 2)))
        
        # Check dependencies for blocking factors
        blocking_factors = []
        for dep_id in deadline.dependencies:
            dep_deadline = self._deadlines.get(dep_id)
            if dep_deadline:
                dep_dl = dep_deadline.deadline
                if dep_dl.tzinfo is None:
                    dep_dl = dep_dl.replace(tzinfo=timezone.utc)
                if dep_dl >= dl:
                    blocking_factors.append(f"Dependency {dep_id} due after this item")
        
        # Estimate completion
        estimated_completion = now + timedelta(hours=hours_remaining * 0.8)
        
        return TimeToFailure(
            item_id=item_id,
            item_type=deadline.item_type,
            deadline=dl,
            time_remaining=time_remaining if time_remaining.total_seconds() > 0 else timedelta(0),
            status=status,
            risk_score=min(1.0, risk_score),
            blocking_factors=blocking_factors,
            estimated_completion=estimated_completion,
            confidence=0.75 if blocking_factors else 0.85,
        )
    
    def check_all_deadlines(
        self,
        now: datetime | None = None
    ) -> list[TimeToFailure]:
        """Check all deadlines and return status."""
        now = now or datetime.now(timezone.utc)
        self._last_check = now
        
        results = []
        for item_id in self._deadlines:
            ttf = self.calculate_time_to_failure(item_id, now)
            if ttf:
                results.append(ttf)
        
        # Sort by risk score descending
        results.sort(key=lambda x: -x.risk_score)
        
        return results
    
    def get_critical_items(
        self,
        now: datetime | None = None
    ) -> list[TimeToFailure]:
        """Get items in critical or breached status."""
        all_items = self.check_all_deadlines(now)
        return [
            item for item in all_items
            if item.status in [SLAStatus.CRITICAL, SLAStatus.BREACHED]
        ]
    
    def get_critical_path_items(self) -> list[str]:
        """Get items on the critical path."""
        return self._critical_path_calculator.calculate_critical_path()
    
    def generate_notifications(
        self,
        ttf: TimeToFailure,
        recipient_ids: dict[str, list[str]]
    ) -> list[Notification]:
        """Generate notifications for a time-to-failure result."""
        notifications = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.item_type != ttf.item_type:
                continue
            if rule.status != ttf.status:
                continue
            
            # Check cooldown
            cooldown_key = f"{rule.rule_id}:{ttf.item_id}"
            last_sent = self._notification_history.get(cooldown_key)
            if last_sent:
                cooldown_delta = datetime.now(timezone.utc) - last_sent
                if cooldown_delta.total_seconds() < rule.cooldown_minutes * 60:
                    continue
            
            # Get recipients
            recipients = []
            for role in rule.recipient_roles:
                recipients.extend(recipient_ids.get(role, []))
            
            if not recipients:
                continue
            
            # Generate message
            message = rule.template.format(
                item_id=ttf.item_id,
                hours=f"{ttf.hours_remaining:.1f}",
                status=ttf.status.value,
            )
            
            for recipient_id in set(recipients):
                for notif_type in rule.notification_types:
                    notification = Notification(
                        notification_id=hashlib.md5(
                            f"{ttf.item_id}:{recipient_id}:{notif_type.value}:{datetime.now(timezone.utc)}".encode()
                        ).hexdigest()[:16],
                        recipient_id=recipient_id,
                        notification_type=notif_type,
                        priority=rule.priority,
                        title=f"SLA Alert: {ttf.item_type.value.upper()} {ttf.item_id}",
                        message=message,
                        item_id=ttf.item_id,
                        item_type=ttf.item_type,
                        action_url=f"/items/{ttf.item_type.value}/{ttf.item_id}",
                    )
                    notifications.append(notification)
            
            # Record notification
            self._notification_history[cooldown_key] = datetime.now(timezone.utc)
        
        return notifications
    
    def send_notification(self, notification: Notification) -> bool:
        """Send a notification."""
        notification.sent_at = datetime.now(timezone.utc)
        
        if self.notification_callback:
            try:
                self.notification_callback(notification)
                return True
            except Exception as exc:
                import structlog
                structlog.get_logger(__name__).warning(
                    "notification_callback_failed",
                    notification_type=notification.notification_type,
                    entity_id=notification.entity_id,
                    error=str(exc),
                    exc_info=True,
                )
                return False
        
        return True
    
    async def run_check_cycle(
        self,
        recipient_ids: dict[str, list[str]]
    ) -> list[Notification]:
        """Run a single check cycle."""
        all_notifications = []
        
        for ttf in self.check_all_deadlines():
            if ttf.status in [SLAStatus.WARNING, SLAStatus.CRITICAL, SLAStatus.BREACHED]:
                notifications = self.generate_notifications(ttf, recipient_ids)
                for notification in notifications:
                    self.send_notification(notification)
                    all_notifications.append(notification)
        
        return all_notifications
    
    async def start(
        self,
        recipient_ids: dict[str, list[str]]
    ) -> None:
        """Start the watchdog background loop."""
        import structlog
        _logger = structlog.get_logger(__name__)
        self._is_running = True
        
        while self._is_running:
            try:
                await self.run_check_cycle(recipient_ids)
            except Exception as exc:
                _logger.error(
                    "sla_watchdog_cycle_failed",
                    error=str(exc),
                    exc_info=True,
                )
            await asyncio.sleep(self.check_interval)
    
    def stop(self) -> None:
        """Stop the watchdog."""
        self._is_running = False
    
    def get_stats(self) -> dict[str, Any]:
        """Get watchdog statistics."""
        items = self.check_all_deadlines()
        
        return {
            "total_monitored": len(self._deadlines),
            "status_counts": {
                status.value: len([i for i in items if i.status == status])
                for status in SLAStatus
            },
            "notifications_sent": len(self._notification_history),
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "is_running": self._is_running,
        }


# =============================================================================
# Meeting Preparation AI
# =============================================================================

class CalendarEntityExtractor:
    """Extract entities from calendar invites."""
    
    # Patterns for entity extraction
    PATTERNS = {
        EntityCategory.RFQ: [
            r"RFQ[#\-\s]*(\d+)",
            r"request\s+for\s+quote[#\-\s]*(\d+)",
            r"rfq\s*#?\s*(\d+)",
        ],
        EntityCategory.ORDER: [
            r"(?:PO|order)[#\-\s]*(\d+)",
            r"purchase\s+order[#\-\s]*(\d+)",
            r"SO[#\-\s]*(\d+)",
        ],
        EntityCategory.PROJECT: [
            r"project[:\s]+([A-Za-z0-9\-_]+)",
            r"(?:PRJ|PROJ)[#\-\s]*(\d+)",
        ],
        EntityCategory.CUSTOMER: [
            r"(?:customer|client)[:\s]+([A-Za-z0-9\s]+?)(?:\s*[-,\.\n]|$)",
            r"(?:re|regarding)[:\s]+([A-Za-z0-9\s]+?)(?:\s+meeting|$)",
        ],
        EntityCategory.TOPIC: [
            r"(?:discuss|review|about)[:\s]+([A-Za-z0-9\s]+?)(?:\s*[-,\.\n]|$)",
            r"(?:agenda|topic)[:\s]+([A-Za-z0-9\s]+?)(?:\s*[-,\.\n]|$)",
        ],
    }
    
    def __init__(self):
        """Initialize extractor."""
        self._known_entities: dict[EntityCategory, dict[str, str]] = defaultdict(dict)
    
    def register_known_entity(
        self,
        category: EntityCategory,
        value: str,
        record_id: str
    ) -> None:
        """Register a known entity for linking."""
        self._known_entities[category][value.lower()] = record_id
    
    def register_known_entities_batch(
        self,
        category: EntityCategory,
        entities: list[tuple[str, str]]
    ) -> None:
        """Register multiple known entities."""
        for value, record_id in entities:
            self.register_known_entity(category, value, record_id)
    
    def extract_from_event(self, event: CalendarEvent) -> list[ExtractedEntity]:
        """Extract entities from a calendar event."""
        entities = []
        
        # Combine text sources
        text_sources = [
            ("title", event.title),
            ("description", event.description),
            ("location", event.location or ""),
        ]
        
        for source_name, text in text_sources:
            if not text:
                continue
            
            text_lower = text.lower()
            
            for category, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text_lower)  # text already lowercased (#239)
                    for match in matches:
                        value = match.group(1).strip() if match.lastindex else match.group(0)
                        
                        # Try to link to known entity
                        linked_id = self._known_entities.get(category, {}).get(value.lower())
                        
                        # Compute confidence based on match quality
                        match_len = len(value)
                        base_confidence = min(0.6 + match_len * 0.02, 0.80)
                        if linked_id:
                            base_confidence = min(base_confidence + 0.15, 0.98)
                        if match.lastindex and match.lastindex >= 1:
                            base_confidence = min(base_confidence + 0.05, 0.98)  # capture-group boost

                        entity = ExtractedEntity(
                            entity_type=category,
                            value=value,
                            normalized_value=value.upper() if category in [EntityCategory.RFQ, EntityCategory.ORDER] else value.title(),
                            confidence=round(base_confidence, 2),
                            linked_record_id=linked_id,
                            linked_record_type=category.value if linked_id else None,
                            context=f"from {source_name}",
                        )
                        entities.append(entity)
        
        # Extract attendee-based entities
        for attendee in event.attendees:
            email_parts = attendee.split("@")
            if len(email_parts) == 2:
                domain = email_parts[1]
                if domain not in ["gmail.com", "yahoo.com", "outlook.com"]:
                    company_name = domain.split(".")[0].title()
                    linked_id = self._known_entities.get(EntityCategory.CUSTOMER, {}).get(company_name.lower())
                    
                    entity = ExtractedEntity(
                        entity_type=EntityCategory.CUSTOMER,
                        value=company_name,
                        normalized_value=company_name,
                        confidence=0.5,
                        linked_record_id=linked_id,
                        context=f"from attendee {attendee}",
                    )
                    entities.append(entity)
        
        # Deduplicate
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity.entity_type, entity.normalized_value)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities


class BriefingNoteGenerator:
    """Generate briefing notes for meetings."""
    
    def __init__(self, entity_extractor: CalendarEntityExtractor):
        """Initialize generator."""
        self.entity_extractor = entity_extractor
        self._data_providers: dict[str, Callable[[list[str]], dict[str, Any]]] = {}
    
    def register_data_provider(
        self,
        provider_name: str,
        provider: Callable[[list[str]], dict[str, Any]]
    ) -> None:
        """Register a data provider for fetching related data."""
        self._data_providers[provider_name] = provider
    
    def _generate_id(self, event: CalendarEvent) -> str:
        """Generate briefing ID."""
        return hashlib.md5(
            f"{event.event_id}:{datetime.now(timezone.utc)}".encode()
        ).hexdigest()[:16]
    
    def _fetch_related_data(
        self,
        entities: list[ExtractedEntity]
    ) -> dict[str, Any]:
        """Fetch related data for entities."""
        related_data = {}
        
        for provider_name, provider in self._data_providers.items():
            record_ids = [
                e.linked_record_id for e in entities
                if e.linked_record_id
            ]
            if record_ids:
                try:
                    related_data[provider_name] = provider(record_ids)
                except Exception:
                    related_data[provider_name] = {}
        
        return related_data
    
    def _generate_executive_summary(
        self,
        event: CalendarEvent,
        entities: list[ExtractedEntity],
        related_data: dict[str, Any],
    ) -> BriefingItem:
        """Generate executive summary section."""
        # Build summary
        summary_parts = []
        
        if event.title:
            summary_parts.append(f"Meeting: {event.title}")
        
        summary_parts.append(
            f"Scheduled: {event.start_time.strftime('%A, %B %d at %I:%M %p')}"
        )
        
        if event.attendees:
            summary_parts.append(f"Attendees: {len(event.attendees)} participants")
        
        # Add entity context
        customers = [e for e in entities if e.entity_type == EntityCategory.CUSTOMER]
        if customers:
            summary_parts.append(f"Related customers: {', '.join(e.normalized_value for e in customers[:3])}")
        
        rfqs = [e for e in entities if e.entity_type == EntityCategory.RFQ]
        if rfqs:
            summary_parts.append(f"Related RFQs: {', '.join(e.normalized_value for e in rfqs[:3])}")
        
        return BriefingItem(
            section=BriefingSection.EXECUTIVE_SUMMARY,
            title="",
            content="\n".join(summary_parts),
            priority=100,
        )
    
    def _generate_key_metrics(
        self,
        entities: list[ExtractedEntity],
        related_data: dict[str, Any],
    ) -> BriefingItem | None:
        """Generate key metrics section."""
        metrics = []
        
        # Pull metrics from related data
        rfq_data = related_data.get("rfq_provider", {})
        if rfq_data:
            if "total_value" in rfq_data:
                metrics.append(f"Total RFQ Value: ${rfq_data['total_value']:,.2f}")
            if "pending_count" in rfq_data:
                metrics.append(f"Pending Items: {rfq_data['pending_count']}")
        
        order_data = related_data.get("order_provider", {})
        if order_data:
            if "open_orders" in order_data:
                metrics.append(f"Open Orders: {order_data['open_orders']}")
        
        if not metrics:
            return None
        
        return BriefingItem(
            section=BriefingSection.KEY_METRICS,
            title="",
            content="\n".join(f"- {m}" for m in metrics),
            priority=90,
        )
    
    def _generate_action_items(
        self,
        entities: list[ExtractedEntity],
        related_data: dict[str, Any],
    ) -> BriefingItem | None:
        """Generate action items section."""
        actions = []
        
        # Add actions based on entity types
        for entity in entities:
            if entity.entity_type == EntityCategory.RFQ and entity.linked_record_id:
                actions.append(f"Review RFQ {entity.normalized_value} status")
            elif entity.entity_type == EntityCategory.ORDER and entity.linked_record_id:
                actions.append(f"Check Order {entity.normalized_value} delivery timeline")
        
        # Get pending tasks from data
        task_data = related_data.get("task_provider", {})
        if task_data and "pending_tasks" in task_data:
            for task in task_data["pending_tasks"][:5]:
                actions.append(f"[Task] {task}")
        
        if not actions:
            return None
        
        return BriefingItem(
            section=BriefingSection.ACTION_ITEMS,
            title="",
            content="\n".join(f"- [ ] {a}" for a in actions[:BRIEFING_MAX_ITEMS]),
            priority=85,
        )
    
    def _generate_risk_alerts(
        self,
        entities: list[ExtractedEntity],
        related_data: dict[str, Any],
    ) -> BriefingItem | None:
        """Generate risk alerts section."""
        alerts = []
        
        risk_data = related_data.get("risk_provider", {})
        if risk_data and "alerts" in risk_data:
            for alert in risk_data["alerts"][:5]:
                alerts.append(f"⚠️ {alert}")
        
        if not alerts:
            return None
        
        return BriefingItem(
            section=BriefingSection.RISK_ALERTS,
            title="",
            content="\n".join(alerts),
            priority=95,
        )
    
    def _generate_background(
        self,
        event: CalendarEvent,
        entities: list[ExtractedEntity],
    ) -> BriefingItem | None:
        """Generate background section."""
        background_parts = []
        
        for entity in entities:
            if entity.entity_type == EntityCategory.CUSTOMER:
                background_parts.append(
                    f"**{entity.normalized_value}**: "
                    f"{'Existing customer record' if entity.linked_record_id else 'No linked record'}"
                )
        
        if not background_parts:
            return None
        
        return BriefingItem(
            section=BriefingSection.BACKGROUND,
            title="",
            content="\n".join(background_parts),
            priority=50,
        )
    
    def _generate_recommendations(
        self,
        entities: list[ExtractedEntity],
        related_data: dict[str, Any],
    ) -> list[str]:
        """Generate recommendations."""
        recommendations = []
        
        # Unlinked entities
        unlinked = [e for e in entities if not e.linked_record_id and e.confidence > 0.5]
        if unlinked:
            recommendations.append(
                f"Consider linking {len(unlinked)} detected entities to system records"
            )
        
        # RFQ follow-ups
        rfqs = [e for e in entities if e.entity_type == EntityCategory.RFQ]
        if rfqs:
            recommendations.append(
                "Prepare latest pricing and status for mentioned RFQs"
            )
        
        return recommendations
    
    def generate_briefing(self, event: CalendarEvent) -> BriefingNote:
        """Generate a complete briefing note for a meeting."""
        # Extract entities
        entities = self.entity_extractor.extract_from_event(event)
        
        # Fetch related data
        related_data = self._fetch_related_data(entities)
        
        # Generate sections
        items: list[BriefingItem] = []
        
        # Executive summary
        items.append(self._generate_executive_summary(event, entities, related_data))
        
        # Key metrics
        key_metrics = self._generate_key_metrics(entities, related_data)
        if key_metrics:
            items.append(key_metrics)
        
        # Action items
        action_items = self._generate_action_items(entities, related_data)
        if action_items:
            items.append(action_items)
        
        # Risk alerts
        risk_alerts = self._generate_risk_alerts(entities, related_data)
        if risk_alerts:
            items.append(risk_alerts)
        
        # Background
        background = self._generate_background(event, entities)
        if background:
            items.append(background)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(entities, related_data)
        
        # Build linked records map
        linked_records: dict[str, list[str]] = defaultdict(list)
        for entity in entities:
            if entity.linked_record_id:
                linked_records[entity.entity_type.value].append(entity.linked_record_id)
        
        return BriefingNote(
            briefing_id=self._generate_id(event),
            meeting_id=event.event_id,
            title=f"Briefing: {event.title}",
            generated_at=datetime.now(timezone.utc),
            items=items,
            extracted_entities=entities,
            linked_records=dict(linked_records),
            recommendations=recommendations,
        )
    
    def generate_pdf_content(self, briefing: BriefingNote) -> str:
        """Generate PDF-ready content (simplified HTML for PDF conversion)."""
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            '<meta charset="UTF-8">',
            f"<title>{briefing.title}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            "h1 { color: #333; border-bottom: 2px solid #333; }",
            "h2 { color: #666; margin-top: 30px; }",
            ".meta { color: #999; font-size: 12px; }",
            ".alert { background: #fff3cd; padding: 10px; border-radius: 4px; }",
            ".action { margin: 5px 0; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>{briefing.title}</h1>",
            f'<p class="meta">Generated: {briefing.generated_at.strftime("%Y-%m-%d %H:%M UTC")}</p>',
        ]
        
        # Add sections
        section_order = [
            BriefingSection.EXECUTIVE_SUMMARY,
            BriefingSection.KEY_METRICS,
            BriefingSection.ACTION_ITEMS,
            BriefingSection.RISK_ALERTS,
            BriefingSection.BACKGROUND,
        ]
        
        items_by_section: dict[BriefingSection, list[BriefingItem]] = defaultdict(list)
        for item in briefing.items:
            items_by_section[item.section].append(item)
        
        for section in section_order:
            if section not in items_by_section:
                continue
            
            section_title = section.value.replace("_", " ").title()
            html_parts.append(f"<h2>{section_title}</h2>")
            
            for item in items_by_section[section]:
                if item.title:
                    html_parts.append(f"<h3>{item.title}</h3>")
                
                # Convert markdown-ish content to HTML
                content = item.content.replace("\n", "<br>")
                html_parts.append(f"<p>{content}</p>")
        
        if briefing.recommendations:
            html_parts.append("<h2>Recommendations</h2>")
            html_parts.append("<ul>")
            for rec in briefing.recommendations:
                html_parts.append(f"<li>{rec}</li>")
            html_parts.append("</ul>")
        
        html_parts.extend([
            "</body>",
            "</html>",
        ])
        
        return "\n".join(html_parts)


# =============================================================================
# Meeting Preparation AI - Main Class
# =============================================================================

class MeetingPreparationAI:
    """
    AI-powered meeting preparation assistant.
    
    Generates briefing notes and extracts entities from calendar invites.
    """
    
    def __init__(self):
        """Initialize meeting preparation AI."""
        self.entity_extractor = CalendarEntityExtractor()
        self.briefing_generator = BriefingNoteGenerator(self.entity_extractor)
        self._generated_briefings: dict[str, BriefingNote] = {}
    
    def register_known_entities(
        self,
        category: EntityCategory,
        entities: list[tuple[str, str]]
    ) -> None:
        """Register known entities for linking."""
        self.entity_extractor.register_known_entities_batch(category, entities)
    
    def register_data_provider(
        self,
        provider_name: str,
        provider: Callable[[list[str]], dict[str, Any]]
    ) -> None:
        """Register a data provider."""
        self.briefing_generator.register_data_provider(provider_name, provider)
    
    def extract_entities(self, event: CalendarEvent) -> list[ExtractedEntity]:
        """Extract entities from a calendar event."""
        return self.entity_extractor.extract_from_event(event)
    
    def generate_briefing(self, event: CalendarEvent) -> BriefingNote:
        """Generate a briefing note for a meeting."""
        briefing = self.briefing_generator.generate_briefing(event)
        self._generated_briefings[briefing.briefing_id] = briefing
        return briefing
    
    def get_briefing(self, briefing_id: str) -> BriefingNote | None:
        """Get a previously generated briefing."""
        return self._generated_briefings.get(briefing_id)
    
    def generate_briefing_markdown(self, event: CalendarEvent) -> str:
        """Generate briefing as Markdown."""
        briefing = self.generate_briefing(event)
        return briefing.to_markdown()
    
    def generate_briefing_pdf(self, event: CalendarEvent) -> str:
        """Generate briefing as PDF-ready HTML."""
        briefing = self.generate_briefing(event)
        return self.briefing_generator.generate_pdf_content(briefing)
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics."""
        return {
            "total_briefings_generated": len(self._generated_briefings),
            "known_entities": {
                category.value: len(entities)
                for category, entities in self.entity_extractor._known_entities.items()
            },
        }


# =============================================================================
# Virtual Assistant - Combined Interface
# =============================================================================

class SenseiVirtualAssistant:
    """
    Sensei Virtual Assistant - Proactive AI assistant.
    
    Combines SLA Watchdog and Meeting Preparation AI capabilities.
    """
    
    def __init__(
        self,
        sla_check_interval: int = DEFAULT_SLA_CHECK_INTERVAL,
        notification_callback: Callable[[Notification], None] | None = None,
    ):
        """Initialize virtual assistant."""
        self.sla_watchdog = SLAWatchdog(
            check_interval=sla_check_interval,
            notification_callback=notification_callback,
        )
        self.meeting_prep = MeetingPreparationAI()
    
    def setup_sla_monitoring(
        self,
        deadlines: list[SLADeadline],
        notification_rules: list[NotificationRule] | None = None,
    ) -> None:
        """Set up SLA monitoring."""
        for deadline in deadlines:
            self.sla_watchdog.add_deadline(deadline)
        
        if notification_rules:
            for rule in notification_rules:
                self.sla_watchdog.add_rule(rule)
    
    def get_critical_alerts(self) -> list[TimeToFailure]:
        """Get current critical alerts."""
        return self.sla_watchdog.get_critical_items()
    
    def prepare_for_meeting(self, event: CalendarEvent) -> BriefingNote:
        """Prepare briefing for a meeting."""
        return self.meeting_prep.generate_briefing(event)
    
    async def start_monitoring(
        self,
        recipient_ids: dict[str, list[str]]
    ) -> None:
        """Start background monitoring."""
        await self.sla_watchdog.start(recipient_ids)
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self.sla_watchdog.stop()
    
    def get_stats(self) -> dict[str, Any]:
        """Get combined statistics."""
        return {
            "sla_watchdog": self.sla_watchdog.get_stats(),
            "meeting_prep": self.meeting_prep.get_stats(),
        }


# =============================================================================
# Factory Function
# =============================================================================

def create_virtual_assistant(
    sla_check_interval: int = DEFAULT_SLA_CHECK_INTERVAL,
    notification_callback: Callable[[Notification], None] | None = None,
) -> SenseiVirtualAssistant:
    """Create a configured virtual assistant instance."""
    return SenseiVirtualAssistant(
        sla_check_interval=sla_check_interval,
        notification_callback=notification_callback,
    )
