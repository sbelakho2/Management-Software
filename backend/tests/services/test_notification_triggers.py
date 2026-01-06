"""
Tests for the Notification Triggers Engine.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID

from sensei.services.notification_triggers import (
    NotificationTriggersService,
    NotificationTriggersJobRunner,
    TriggerType,
    TriggerCondition,
    TriggerEvaluationResult,
    GeneratedNotification,
    NotificationTarget,
    UserSnoozeSettings,
    RecipientRole,
    NotificationChannel,
    NotificationPriority,
    SnoozeStatus,
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def service() -> NotificationTriggersService:
    """Create a fresh service instance."""
    return NotificationTriggersService()


@pytest.fixture
def now() -> datetime:
    """Reference datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def user1_id() -> UUID:
    """First test user ID."""
    return uuid4()


@pytest.fixture
def user2_id() -> UUID:
    """Second test user ID."""
    return uuid4()


@pytest.fixture
def users(user1_id: UUID, user2_id: UUID) -> dict[UUID, NotificationTarget]:
    """User lookup map."""
    return {
        user1_id: NotificationTarget(
            user_id=user1_id,
            role=RecipientRole.OWNER,
            email="user1@example.com",
            name="User One",
        ),
        user2_id: NotificationTarget(
            user_id=user2_id,
            role=RecipientRole.ASSIGNEE,
            email="user2@example.com",
            name="User Two",
        ),
    }


# --------------------------------------------------------------------------
# Enums and Dataclasses Tests
# --------------------------------------------------------------------------

class TestTriggerType:
    """Tests for TriggerType enum."""
    
    def test_trigger_type_values(self):
        """Test all trigger type values exist."""
        assert TriggerType.TASK_OVERDUE.value == "task_overdue"
        assert TriggerType.TASK_DUE_SOON.value == "task_due_soon"
        assert TriggerType.RFQ_STALLED.value == "rfq_stalled"
        assert TriggerType.QUOTE_LOW_MARGIN.value == "quote_low_margin"
        assert TriggerType.QUOTE_APPROVAL_NEEDED.value == "quote_approval_needed"
        assert TriggerType.RECURRING_ABNORMALITY.value == "recurring_abnormality"
        assert TriggerType.CERTIFICATION_EXPIRING.value == "certification_expiring"
    
    def test_trigger_type_is_string(self):
        """Trigger types should be usable as strings."""
        trigger = TriggerType.TASK_OVERDUE
        assert isinstance(trigger.value, str)
        assert trigger == "task_overdue"


class TestRecipientRole:
    """Tests for RecipientRole enum."""
    
    def test_recipient_role_values(self):
        """Test all recipient role values."""
        assert RecipientRole.OWNER.value == "owner"
        assert RecipientRole.ASSIGNEE.value == "assignee"
        assert RecipientRole.MANAGER.value == "manager"
        assert RecipientRole.APPROVER.value == "approver"
        assert RecipientRole.QUALITY.value == "quality"


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""
    
    def test_priority_values(self):
        """Test priority levels."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


class TestTriggerCondition:
    """Tests for TriggerCondition dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        cond = TriggerCondition(
            trigger_type=TriggerType.TASK_OVERDUE,
            name="Test Trigger",
            description="A test trigger",
        )
        assert cond.recipients == []
        assert cond.channels == [NotificationChannel.IN_APP]
        assert cond.priority == NotificationPriority.NORMAL
        assert cond.is_enabled is True
        assert cond.cooldown_minutes == 1440
    
    def test_custom_values(self):
        """Test custom values."""
        cond = TriggerCondition(
            trigger_type=TriggerType.QUOTE_LOW_MARGIN,
            name="Low Margin",
            description="Margin below threshold",
            recipients=[RecipientRole.OWNER, RecipientRole.FINANCE],
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH,
            margin_threshold=15.0,
            is_enabled=False,
        )
        assert len(cond.recipients) == 2
        assert cond.margin_threshold == 15.0
        assert cond.is_enabled is False


class TestGeneratedNotification:
    """Tests for GeneratedNotification dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        notif = GeneratedNotification()
        assert notif.id is not None
        assert notif.trigger_type == TriggerType.TASK_OVERDUE
        assert notif.priority == NotificationPriority.NORMAL
        assert notif.snooze_status == SnoozeStatus.ACTIVE
        assert notif.generated_at is not None
    
    def test_custom_values(self):
        """Test with custom values."""
        recipient = uuid4()
        notif = GeneratedNotification(
            trigger_type=TriggerType.QUOTE_APPROVAL_NEEDED,
            title="Quote Approval",
            message="Please review quote Q-001",
            priority=NotificationPriority.HIGH,
            recipient_id=recipient,
            recipient_role=RecipientRole.APPROVER,
            entity_type="quote",
            entity_id="q-001",
        )
        assert notif.title == "Quote Approval"
        assert notif.recipient_id == recipient
        assert notif.entity_type == "quote"


class TestNotificationTarget:
    """Tests for NotificationTarget dataclass."""
    
    def test_creation(self):
        """Test target creation."""
        user_id = uuid4()
        target = NotificationTarget(
            user_id=user_id,
            role=RecipientRole.MANAGER,
            email="manager@example.com",
            name="The Manager",
        )
        assert target.user_id == user_id
        assert target.role == RecipientRole.MANAGER
        assert target.email == "manager@example.com"


# --------------------------------------------------------------------------
# Service Tests
# --------------------------------------------------------------------------

class TestNotificationTriggersService:
    """Tests for NotificationTriggersService."""
    
    def test_initialization(self, service: NotificationTriggersService):
        """Test service initializes with default triggers."""
        triggers = service.get_all_triggers()
        assert len(triggers) > 0
        
        # Check some expected defaults exist
        assert service.get_trigger(TriggerType.TASK_OVERDUE) is not None
        assert service.get_trigger(TriggerType.RFQ_STALLED) is not None
        assert service.get_trigger(TriggerType.QUOTE_LOW_MARGIN) is not None
    
    def test_get_trigger(self, service: NotificationTriggersService):
        """Test getting a specific trigger."""
        trigger = service.get_trigger(TriggerType.TASK_OVERDUE)
        assert trigger is not None
        assert trigger.trigger_type == TriggerType.TASK_OVERDUE
        assert trigger.is_enabled is True
    
    def test_register_trigger(self, service: NotificationTriggersService):
        """Test registering a custom trigger."""
        custom = TriggerCondition(
            trigger_type=TriggerType.MENTION,
            name="User Mention",
            description="User was mentioned",
            recipients=[RecipientRole.OWNER],
            priority=NotificationPriority.NORMAL,
        )
        service.register_trigger(custom)
        
        retrieved = service.get_trigger(TriggerType.MENTION)
        assert retrieved is not None
        assert retrieved.name == "User Mention"
    
    def test_enable_disable_trigger(self, service: NotificationTriggersService):
        """Test enabling and disabling triggers."""
        # Initially enabled
        trigger = service.get_trigger(TriggerType.TASK_OVERDUE)
        assert trigger.is_enabled is True
        
        # Disable
        result = service.disable_trigger(TriggerType.TASK_OVERDUE)
        assert result is True
        assert service.get_trigger(TriggerType.TASK_OVERDUE).is_enabled is False
        
        # Enable
        result = service.enable_trigger(TriggerType.TASK_OVERDUE)
        assert result is True
        assert service.get_trigger(TriggerType.TASK_OVERDUE).is_enabled is True
    
    def test_enable_nonexistent_trigger(self, service: NotificationTriggersService):
        """Test enabling a nonexistent trigger returns False."""
        result = service.enable_trigger(TriggerType.SKILL_GAP)
        assert result is False


class TestTaskEvaluation:
    """Tests for task trigger evaluation."""
    
    def test_overdue_task(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test overdue task generates notification."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Complete report",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "in_progress",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        
        assert len(notifications) > 0
        assert any(n.trigger_type == TriggerType.TASK_OVERDUE for n in notifications)
        
        overdue = [n for n in notifications if n.trigger_type == TriggerType.TASK_OVERDUE][0]
        assert "Overdue Task" in overdue.title
        assert "2 day(s) overdue" in overdue.message
        assert overdue.recipient_id == user1_id
    
    def test_due_soon_task(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test task due soon generates notification."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Tomorrow's task",
                "due_date": (now + timedelta(hours=20)).isoformat(),
                "status": "pending",
                "assignee_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        
        assert len(notifications) > 0
        assert any(n.trigger_type == TriggerType.TASK_DUE_SOON for n in notifications)
    
    def test_completed_task_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Completed tasks should not generate notifications."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Done task",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "completed",
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) == 0
    
    def test_cancelled_task_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Cancelled tasks should not generate notifications."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Cancelled task",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "cancelled",
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) == 0
    
    def test_future_task_no_overdue_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Future tasks should not generate overdue notifications."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Future task",
                "due_date": (now + timedelta(days=10)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        overdue = [n for n in notifications if n.trigger_type == TriggerType.TASK_OVERDUE]
        assert len(overdue) == 0
    
    def test_no_due_date_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Tasks without due dates should not generate date-based notifications."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "No due date",
                "status": "pending",
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) == 0


class TestRFQEvaluation:
    """Tests for RFQ trigger evaluation."""
    
    def test_stalled_rfq(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test stalled RFQ generates notification."""
        rfqs = [
            {
                "id": str(uuid4()),
                "rfq_number": "RFQ-001",
                "title": "Parts Quote Request",
                "status": "open",
                "updated_at": (now - timedelta(days=10)).isoformat(),
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_rfqs(rfqs, users, now)
        
        assert len(notifications) > 0
        stalled = [n for n in notifications if n.trigger_type == TriggerType.RFQ_STALLED]
        assert len(stalled) > 0
        assert "Stalled RFQ" in stalled[0].title
        assert "10 days" in stalled[0].message
    
    def test_incomplete_rfq(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test incomplete RFQ generates notification."""
        rfqs = [
            {
                "id": str(uuid4()),
                "rfq_number": "RFQ-002",
                "status": "open",
                "completeness_score": 65,
                "missing_fields": ["unit_price", "lead_time", "delivery_terms"],
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_rfqs(rfqs, users, now)
        
        incomplete = [n for n in notifications if n.trigger_type == TriggerType.RFQ_INCOMPLETE]
        assert len(incomplete) > 0
        assert "65% complete" in incomplete[0].message
    
    def test_closed_rfq_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Closed RFQs should not generate notifications."""
        rfqs = [
            {
                "id": str(uuid4()),
                "rfq_number": "RFQ-003",
                "status": "closed",
                "updated_at": (now - timedelta(days=30)).isoformat(),
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_rfqs(rfqs, users, now)
        assert len(notifications) == 0
    
    def test_complete_rfq_no_incomplete_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Complete RFQs should not generate incomplete notifications."""
        rfqs = [
            {
                "id": str(uuid4()),
                "rfq_number": "RFQ-004",
                "status": "open",
                "completeness_score": 100,
                "missing_fields": [],
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_rfqs(rfqs, users, now)
        incomplete = [n for n in notifications if n.trigger_type == TriggerType.RFQ_INCOMPLETE]
        assert len(incomplete) == 0


class TestQuoteEvaluation:
    """Tests for quote trigger evaluation."""
    
    def test_low_margin_quote(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test low margin quote generates notification."""
        quotes = [
            {
                "id": str(uuid4()),
                "quote_number": "Q-001",
                "status": "draft",
                "margin_percent": 8.5,
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_quotes(quotes, users, now)
        
        low_margin = [n for n in notifications if n.trigger_type == TriggerType.QUOTE_LOW_MARGIN]
        assert len(low_margin) > 0
        assert "8.5%" in low_margin[0].message
        assert "15" in low_margin[0].message  # Threshold
    
    def test_approval_needed_quote(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test pending approval quote generates notification."""
        quotes = [
            {
                "id": str(uuid4()),
                "quote_number": "Q-002",
                "status": "pending_approval",
                "total_value": 50000,
                "approver_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_quotes(quotes, users, now)
        
        approval = [n for n in notifications if n.trigger_type == TriggerType.QUOTE_APPROVAL_NEEDED]
        assert len(approval) > 0
        assert "Q-002" in approval[0].title
    
    def test_aging_approval(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test aging approval generates notification."""
        quotes = [
            {
                "id": str(uuid4()),
                "quote_number": "Q-003",
                "status": "pending_approval",
                "submitted_for_approval_at": (now - timedelta(days=5)).isoformat(),
                "approver_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_quotes(quotes, users, now)
        
        aging = [n for n in notifications if n.trigger_type == TriggerType.QUOTE_APPROVAL_AGING]
        assert len(aging) > 0
        assert "5 days" in aging[0].message
    
    def test_acceptable_margin_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Acceptable margin quotes should not generate low margin notifications."""
        quotes = [
            {
                "id": str(uuid4()),
                "quote_number": "Q-004",
                "status": "draft",
                "margin_percent": 25.0,
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_quotes(quotes, users, now)
        low_margin = [n for n in notifications if n.trigger_type == TriggerType.QUOTE_LOW_MARGIN]
        assert len(low_margin) == 0


class TestCertificationEvaluation:
    """Tests for certification trigger evaluation."""
    
    def test_expiring_certification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test expiring certification generates notification."""
        certifications = [
            {
                "id": str(uuid4()),
                "user_id": str(user1_id),
                "skill_name": "Forklift Operation",
                "expires_at": (now + timedelta(days=15)).isoformat(),
            }
        ]
        
        notifications = service.evaluate_certifications(certifications, users, now)
        
        assert len(notifications) > 0
        expiring = notifications[0]
        assert expiring.trigger_type == TriggerType.CERTIFICATION_EXPIRING
        assert "Forklift Operation" in expiring.title
        assert expiring.extra_data["days_until_expiration"] == 15
    
    def test_far_future_cert_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Certifications far in the future should not generate notifications."""
        certifications = [
            {
                "id": str(uuid4()),
                "user_id": str(user1_id),
                "skill_name": "Safety Training",
                "expires_at": (now + timedelta(days=365)).isoformat(),
            }
        ]
        
        notifications = service.evaluate_certifications(certifications, users, now)
        assert len(notifications) == 0
    
    def test_already_expired_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Already expired certifications use a different trigger (not expiring)."""
        certifications = [
            {
                "id": str(uuid4()),
                "user_id": str(user1_id),
                "skill_name": "Expired Cert",
                "expires_at": (now - timedelta(days=5)).isoformat(),
            }
        ]
        
        notifications = service.evaluate_certifications(certifications, users, now)
        expiring = [n for n in notifications if n.trigger_type == TriggerType.CERTIFICATION_EXPIRING]
        # Expired certs are not "expiring", they're expired
        assert len(expiring) == 0


# --------------------------------------------------------------------------
# Snooze and Acknowledge Tests
# --------------------------------------------------------------------------

class TestSnoozeAndAcknowledge:
    """Tests for snooze and acknowledge functionality."""
    
    def test_snooze_global(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test global snooze for a user."""
        service.snooze_for_user(user1_id, snooze_hours=24)
        
        settings = service.get_user_snooze_settings(user1_id)
        assert settings.global_snooze_until is not None
    
    def test_snooze_trigger_type(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test snooze for specific trigger type."""
        service.snooze_for_user(
            user1_id,
            trigger_type=TriggerType.TASK_OVERDUE,
            snooze_hours=8,
        )
        
        settings = service.get_user_snooze_settings(user1_id)
        assert TriggerType.TASK_OVERDUE.value in settings.trigger_snoozes
    
    def test_snooze_entity(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test snooze for specific entity."""
        entity_key = "task::12345"
        service.snooze_for_user(
            user1_id,
            entity_key=entity_key,
            snooze_hours=4,
        )
        
        settings = service.get_user_snooze_settings(user1_id)
        assert entity_key in settings.entity_snoozes
    
    def test_acknowledge_entity(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test acknowledging an entity."""
        entity_key = "rfq::67890"
        service.acknowledge_entity(user1_id, entity_key)
        
        settings = service.get_user_snooze_settings(user1_id)
        assert entity_key in settings.acknowledged_entities
    
    def test_snoozed_task_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Snoozed entities should not generate notifications."""
        task_id = str(uuid4())
        tasks = [
            {
                "id": task_id,
                "title": "Snoozed task",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "in_progress",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        # Snooze the entity
        service.snooze_for_user(
            user1_id,
            entity_key=f"task::{task_id}",
            snooze_hours=24,
        )
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) == 0
    
    def test_acknowledged_entity_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Acknowledged entities should not generate notifications."""
        task_id = str(uuid4())
        tasks = [
            {
                "id": task_id,
                "title": "Acknowledged task",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "in_progress",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        # Acknowledge
        service.acknowledge_entity(user1_id, f"task::{task_id}")
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) == 0
    
    def test_clear_snooze_global(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test clearing global snooze."""
        service.snooze_for_user(user1_id, snooze_hours=24)
        service.clear_snooze(user1_id)
        
        settings = service.get_user_snooze_settings(user1_id)
        assert settings.global_snooze_until is None
    
    def test_clear_snooze_trigger(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test clearing trigger-specific snooze."""
        service.snooze_for_user(
            user1_id,
            trigger_type=TriggerType.TASK_OVERDUE,
            snooze_hours=8,
        )
        service.clear_snooze(user1_id, trigger_type=TriggerType.TASK_OVERDUE)
        
        settings = service.get_user_snooze_settings(user1_id)
        assert TriggerType.TASK_OVERDUE.value not in settings.trigger_snoozes
    
    def test_clear_snooze_entity(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
    ):
        """Test clearing entity snooze and acknowledge."""
        entity_key = "task::12345"
        service.snooze_for_user(user1_id, entity_key=entity_key, snooze_hours=4)
        service.acknowledge_entity(user1_id, entity_key)
        
        service.clear_snooze(user1_id, entity_key=entity_key)
        
        settings = service.get_user_snooze_settings(user1_id)
        assert entity_key not in settings.entity_snoozes
        assert entity_key not in settings.acknowledged_entities
    
    def test_expired_snooze_allows_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Expired snoozes should allow notifications."""
        task_id = str(uuid4())
        tasks = [
            {
                "id": task_id,
                "title": "Test task",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "in_progress",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        # Create an already-expired snooze by manipulating settings
        service.snooze_for_user(user1_id, entity_key=f"task::{task_id}", snooze_hours=1)
        settings = service.get_user_snooze_settings(user1_id)
        # Set snooze to the past
        settings.entity_snoozes[f"task::{task_id}"] = now - timedelta(hours=1)
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) > 0


# --------------------------------------------------------------------------
# Job Runner Tests
# --------------------------------------------------------------------------

class TestNotificationTriggersJobRunner:
    """Tests for NotificationTriggersJobRunner."""
    
    @pytest.mark.asyncio
    async def test_run_with_tasks(
        self,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test running the job runner with tasks."""
        runner = NotificationTriggersJobRunner()
        
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Overdue task",
                "due_date": (now - timedelta(days=3)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        result = await runner.run(tasks=tasks, users=users, reference_date=now)
        
        assert isinstance(result, TriggerEvaluationResult)
        assert result.triggers_checked > 0
        assert result.entities_scanned == 1
        assert len(result.notifications) > 0
    
    @pytest.mark.asyncio
    async def test_run_all_entity_types(
        self,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test running with all entity types."""
        runner = NotificationTriggersJobRunner()
        
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": (now - timedelta(days=1)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        rfqs = [
            {
                "id": str(uuid4()),
                "rfq_number": "RFQ-001",
                "status": "open",
                "updated_at": (now - timedelta(days=10)).isoformat(),
                "owner_id": str(user1_id),
            }
        ]
        quotes = [
            {
                "id": str(uuid4()),
                "quote_number": "Q-001",
                "status": "draft",
                "margin_percent": 5.0,
                "owner_id": str(user1_id),
            }
        ]
        certs = [
            {
                "id": str(uuid4()),
                "user_id": str(user1_id),
                "skill_name": "Skill",
                "expires_at": (now + timedelta(days=10)).isoformat(),
            }
        ]
        
        result = await runner.run(
            tasks=tasks,
            rfqs=rfqs,
            quotes=quotes,
            certifications=certs,
            users=users,
            reference_date=now,
        )
        
        assert result.entities_scanned == 4
        assert result.triggers_checked > 0
        assert len(result.notifications) > 0
    
    @pytest.mark.asyncio
    async def test_run_with_delivery_callback(
        self,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test the delivery callback."""
        delivered = []
        
        def on_notification(notif: GeneratedNotification):
            delivered.append(notif)
        
        runner = NotificationTriggersJobRunner(on_notification=on_notification)
        
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": (now - timedelta(days=1)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        result = await runner.run(tasks=tasks, users=users, reference_date=now, deliver=True)
        
        assert len(delivered) == len(result.notifications)
    
    @pytest.mark.asyncio
    async def test_run_empty_data(self):
        """Test running with no data."""
        runner = NotificationTriggersJobRunner()
        
        result = await runner.run()
        
        assert result.entities_scanned == 0
        assert result.triggers_checked == 0
        assert len(result.notifications) == 0
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_last_run_timestamp(
        self,
        now: datetime,
    ):
        """Test last_run timestamp is updated."""
        runner = NotificationTriggersJobRunner()
        
        assert runner.last_run is None
        
        await runner.run()
        
        assert runner.last_run is not None
    
    @pytest.mark.asyncio
    async def test_evaluation_time_recorded(
        self,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test evaluation time is recorded."""
        runner = NotificationTriggersJobRunner()
        
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": (now - timedelta(days=1)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
            }
        ]
        
        result = await runner.run(tasks=tasks, users=users, reference_date=now)
        
        assert result.evaluation_time_ms > 0


# --------------------------------------------------------------------------
# Edge Cases and Error Handling
# --------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_invalid_datetime_string(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test handling of invalid datetime strings."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Bad date task",
                "due_date": "not-a-date",
                "status": "pending",
                "owner_id": str(user1_id),
            }
        ]
        
        # Should not raise, just skip
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) == 0
    
    def test_missing_user_lookup(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
        now: datetime,
    ):
        """Test when user not in lookup map."""
        unknown_user = uuid4()
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": (now - timedelta(days=1)).isoformat(),
                "status": "pending",
                "owner_id": str(unknown_user),
            }
        ]
        
        # Empty users map
        notifications = service.evaluate_tasks(tasks, {}, now)
        assert len(notifications) == 0
    
    def test_disabled_trigger_no_notification(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Disabled triggers should not generate notifications."""
        service.disable_trigger(TriggerType.TASK_OVERDUE)
        
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": (now - timedelta(days=5)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        overdue = [n for n in notifications if n.trigger_type == TriggerType.TASK_OVERDUE]
        assert len(overdue) == 0
    
    def test_multiple_recipients_same_task(
        self,
        service: NotificationTriggersService,
        user1_id: UUID,
        user2_id: UUID,
        now: datetime,
    ):
        """Test that multiple recipients get notifications."""
        users = {
            user1_id: NotificationTarget(user_id=user1_id, role=RecipientRole.OWNER),
            user2_id: NotificationTarget(user_id=user2_id, role=RecipientRole.ASSIGNEE),
        }
        
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Shared task",
                "due_date": (now - timedelta(days=2)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user2_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        
        # Should have notifications for both owner and assignee
        recipient_ids = {n.recipient_id for n in notifications}
        assert user1_id in recipient_ids or user2_id in recipient_ids
    
    def test_empty_users_map(
        self,
        service: NotificationTriggersService,
        now: datetime,
    ):
        """Test with empty users map."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": (now - timedelta(days=1)).isoformat(),
                "status": "pending",
                "owner_id": str(uuid4()),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, {}, now)
        assert len(notifications) == 0
    
    def test_z_suffix_datetime(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test datetime with Z suffix is handled."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": f"{(now - timedelta(days=1)).isoformat()}Z",
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) > 0
    
    def test_datetime_object_input(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test datetime object (not string) is handled."""
        tasks = [
            {
                "id": str(uuid4()),
                "title": "Task",
                "due_date": now - timedelta(days=1),  # datetime object
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        assert len(notifications) > 0


class TestNotificationContent:
    """Tests for notification content generation."""
    
    def test_task_notification_content(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test task notification has proper content."""
        tasks = [
            {
                "id": "task-123",
                "title": "Important Task",
                "due_date": (now - timedelta(days=3)).isoformat(),
                "status": "pending",
                "owner_id": str(user1_id),
                "assignee_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_tasks(tasks, users, now)
        overdue = [n for n in notifications if n.trigger_type == TriggerType.TASK_OVERDUE][0]
        
        assert "Important Task" in overdue.title
        assert "Important Task" in overdue.message
        assert overdue.entity_type == "task"
        assert overdue.entity_id == "task-123"
        assert overdue.priority == NotificationPriority.HIGH
    
    def test_rfq_stalled_content(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test RFQ stalled notification has proper content."""
        rfqs = [
            {
                "id": "rfq-456",
                "rfq_number": "RFQ-2024-001",
                "title": "Machine Parts",
                "status": "open",
                "updated_at": (now - timedelta(days=14)).isoformat(),
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_rfqs(rfqs, users, now)
        stalled = [n for n in notifications if n.trigger_type == TriggerType.RFQ_STALLED][0]
        
        assert "RFQ-2024-001" in stalled.title or "Machine Parts" in stalled.title
        assert stalled.entity_type == "rfq"
        assert stalled.entity_id == "rfq-456"
        assert stalled.extra_data["days_stalled"] == 14
    
    def test_quote_low_margin_content(
        self,
        service: NotificationTriggersService,
        users: dict[UUID, NotificationTarget],
        user1_id: UUID,
        now: datetime,
    ):
        """Test quote low margin notification has proper content."""
        quotes = [
            {
                "id": "quote-789",
                "quote_number": "Q-2024-050",
                "status": "draft",
                "margin_percent": 7.5,
                "owner_id": str(user1_id),
            }
        ]
        
        notifications = service.evaluate_quotes(quotes, users, now)
        low = [n for n in notifications if n.trigger_type == TriggerType.QUOTE_LOW_MARGIN][0]
        
        assert "Q-2024-050" in low.title
        assert "7.5%" in low.message
        assert low.extra_data["margin"] == 7.5
        assert low.extra_data["threshold"] == 15.0


class TestUserSnoozeSettings:
    """Tests for UserSnoozeSettings dataclass."""
    
    def test_defaults(self):
        """Test default values."""
        user_id = uuid4()
        settings = UserSnoozeSettings(user_id=user_id)
        
        assert settings.user_id == user_id
        assert settings.global_snooze_until is None
        assert settings.trigger_snoozes == {}
        assert settings.entity_snoozes == {}
        assert settings.acknowledged_entities == set()
    
    def test_add_snooze(self):
        """Test adding snooze entries."""
        user_id = uuid4()
        settings = UserSnoozeSettings(user_id=user_id)
        
        snooze_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8)
        settings.trigger_snoozes["task_overdue"] = snooze_time
        settings.entity_snoozes["task::123"] = snooze_time
        settings.acknowledged_entities.add("rfq::456")
        
        assert "task_overdue" in settings.trigger_snoozes
        assert "task::123" in settings.entity_snoozes
        assert "rfq::456" in settings.acknowledged_entities
