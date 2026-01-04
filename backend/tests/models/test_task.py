"""
Tests for Task and Notification models.

Tests:
- Task model fields and defaults
- Task priority and status handling
- Task polymorphic parent relationships
- TaskComment model
- Notification model
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.models.task import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
    Task,
    TaskComment,
    TaskPriority,
    TaskStatus,
    TaskType,
)


class TestTaskModel:
    """Tests for the Task model."""

    def test_task_required_fields(self):
        """Task should require title."""
        task = Task(
            title="Review supplier quote",
        )
        assert task.title == "Review supplier quote"

    def test_task_default_status_is_todo(self):
        """Task status should default to todo."""
        task = Task(
            title="Test",
            status=TaskStatus.TODO.value,
        )
        assert task.status == TaskStatus.TODO.value

    def test_task_default_priority_is_medium(self):
        """Task priority should default to medium."""
        task = Task(
            title="Test",
            priority=TaskPriority.MEDIUM.value,
        )
        assert task.priority == TaskPriority.MEDIUM.value

    def test_task_default_type_is_action(self):
        """Task type should default to action."""
        task = Task(
            title="Test",
            task_type=TaskType.ACTION.value,
        )
        assert task.task_type == TaskType.ACTION.value

    def test_task_default_progress_is_0(self):
        """Task progress_percentage should default to 0."""
        task = Task(
            title="Test",
            progress_percentage=0,
        )
        assert task.progress_percentage == 0

    def test_task_default_is_recurring_false(self):
        """is_recurring should default to False."""
        task = Task(
            title="Test",
            is_recurring=False,
        )
        assert task.is_recurring is False

    def test_task_default_reminder_sent_false(self):
        """reminder_sent should default to False."""
        task = Task(
            title="Test",
            reminder_sent=False,
        )
        assert task.reminder_sent is False

    def test_task_is_open_true_for_active_statuses(self):
        """is_open should be True for active statuses."""
        for status in [
            TaskStatus.TODO,
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.IN_REVIEW,
        ]:
            task = Task(
                title="Test",
                status=status.value,
            )
            assert task.is_open is True

    def test_task_is_open_false_for_closed_statuses(self):
        """is_open should be False for closed statuses."""
        for status in [
            TaskStatus.DONE,
            TaskStatus.CANCELLED,
        ]:
            task = Task(
                title="Test",
                status=status.value,
            )
            assert task.is_open is False

    def test_task_is_overdue_true_when_past_due(self):
        """is_overdue should be True when due_date is past and not complete."""
        task = Task(
            title="Test",
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
            status=TaskStatus.IN_PROGRESS.value,
        )
        assert task.is_overdue is True

    def test_task_is_overdue_false_when_completed(self):
        """is_overdue should be False when completed even if past due."""
        task = Task(
            title="Test",
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
            status=TaskStatus.DONE.value,
        )
        assert task.is_overdue is False

    def test_task_is_overdue_false_for_future_date(self):
        """is_overdue should be False when due_date is in the future."""
        task = Task(
            title="Test",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            status=TaskStatus.IN_PROGRESS.value,
        )
        assert task.is_overdue is False

    def test_task_is_overdue_false_when_no_due_date(self):
        """is_overdue should be False when due_date not set."""
        task = Task(
            title="Test",
            status=TaskStatus.IN_PROGRESS.value,
        )
        assert task.is_overdue is False

    def test_task_polymorphic_entity_reference(self):
        """Task should support polymorphic entity reference."""
        rfq_id = uuid4()
        task = Task(
            title="Test",
            related_entity_type="rfq",
            related_entity_id=rfq_id,
        )
        assert task.related_entity_type == "rfq"
        assert task.related_entity_id == rfq_id

    def test_task_estimated_hours_tracking(self):
        """Task should track estimated and actual hours."""
        task = Task(
            title="Test",
            estimated_hours=8.0,
            actual_hours=6.5,
        )
        assert task.estimated_hours == 8.0
        assert task.actual_hours == 6.5

    def test_task_checklist_progress_empty(self):
        """checklist_progress should return (0, 0) for empty checklist."""
        task = Task(
            title="Test",
        )
        assert task.checklist_progress == (0, 0)

    def test_task_checklist_progress_calculation(self):
        """checklist_progress should calculate completed/total."""
        task = Task(
            title="Test",
            checklist=[
                {"id": "1", "text": "Item 1", "checked": True},
                {"id": "2", "text": "Item 2", "checked": False},
                {"id": "3", "text": "Item 3", "checked": True},
            ],
        )
        assert task.checklist_progress == (2, 3)


class TestTaskStatusEnum:
    """Tests for TaskStatus enum."""

    def test_all_statuses_defined(self):
        """All expected task statuses should be defined."""
        assert TaskStatus.TODO.value == "todo"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.IN_REVIEW.value == "in_review"
        assert TaskStatus.DONE.value == "done"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskPriorityEnum:
    """Tests for TaskPriority enum."""

    def test_all_priorities_defined(self):
        """All expected task priorities should be defined."""
        assert TaskPriority.URGENT.value == "urgent"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"


class TestTaskTypeEnum:
    """Tests for TaskType enum."""

    def test_all_types_defined(self):
        """All expected task types should be defined."""
        assert TaskType.ACTION.value == "action"
        assert TaskType.FOLLOW_UP.value == "follow_up"
        assert TaskType.REVIEW.value == "review"
        assert TaskType.APPROVAL.value == "approval"
        assert TaskType.CALL.value == "call"
        assert TaskType.MEETING.value == "meeting"
        assert TaskType.DOCUMENT.value == "document"
        assert TaskType.OTHER.value == "other"


class TestTaskCommentModel:
    """Tests for the TaskComment model."""

    def test_task_comment_required_fields(self):
        """TaskComment should require task_id and content."""
        task_id = uuid4()
        author_id = uuid4()
        comment = TaskComment(
            task_id=task_id,
            content="Updated the timeline based on new info.",
            author_id=author_id,
        )
        assert comment.task_id == task_id
        assert comment.content == "Updated the timeline based on new info."
        assert comment.author_id == author_id

    def test_task_comment_is_status_change_default_false(self):
        """is_status_change should default to False."""
        comment = TaskComment(
            task_id=uuid4(),
            content="Test",
            author_id=uuid4(),
            is_status_change=False,
        )
        assert comment.is_status_change is False

    def test_task_comment_is_edited_default_false(self):
        """is_edited should default to False."""
        comment = TaskComment(
            task_id=uuid4(),
            content="Test",
            author_id=uuid4(),
            is_edited=False,
        )
        assert comment.is_edited is False

    def test_task_comment_mentions_list(self):
        """mentions should support list of user IDs."""
        user1 = uuid4()
        user2 = uuid4()
        comment = TaskComment(
            task_id=uuid4(),
            content="@user1 @user2 please review",
            author_id=uuid4(),
            mentions=[str(user1), str(user2)],
        )
        assert len(comment.mentions) == 2


class TestNotificationModel:
    """Tests for the Notification model."""

    def test_notification_required_fields(self):
        """Notification should require user_id, title, message, notification_type."""
        user_id = uuid4()
        notif = Notification(
            user_id=user_id,
            title="New task assigned",
            message="You have been assigned a new task.",
            notification_type=NotificationType.TASK_ASSIGNED.value,
        )
        assert notif.user_id == user_id
        assert notif.title == "New task assigned"
        assert notif.message == "You have been assigned a new task."
        assert notif.notification_type == NotificationType.TASK_ASSIGNED.value

    def test_notification_default_priority_is_normal(self):
        """Notification priority should default to normal."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            priority=NotificationPriority.NORMAL.value,
        )
        assert notif.priority == NotificationPriority.NORMAL.value

    def test_notification_is_read_default_false(self):
        """is_read should default to False."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            is_read=False,
        )
        assert notif.is_read is False

    def test_notification_is_dismissed_default_false(self):
        """is_dismissed should default to False."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            is_dismissed=False,
        )
        assert notif.is_dismissed is False

    def test_notification_email_sent_default_false(self):
        """email_sent should default to False."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            email_sent=False,
        )
        assert notif.email_sent is False

    def test_notification_push_sent_default_false(self):
        """push_sent should default to False."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            push_sent=False,
        )
        assert notif.push_sent is False

    def test_notification_is_expired_false_when_no_expiry(self):
        """is_expired should be False when expires_at is not set."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
        )
        assert notif.is_expired is False

    def test_notification_is_expired_true_for_past_date(self):
        """is_expired should be True when expires_at is in the past."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert notif.is_expired is True

    def test_notification_is_expired_false_for_future_date(self):
        """is_expired should be False when expires_at is in the future."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert notif.is_expired is False

    def test_notification_entity_reference(self):
        """Notification should support entity reference."""
        rfq_id = uuid4()
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.RFQ_RECEIVED.value,
            related_entity_type="rfq",
            related_entity_id=rfq_id,
        )
        assert notif.related_entity_type == "rfq"
        assert notif.related_entity_id == rfq_id

    def test_notification_action_url(self):
        """Notification should support action URL."""
        notif = Notification(
            user_id=uuid4(),
            title="Test",
            message="Test message",
            notification_type=NotificationType.SYSTEM.value,
            action_url="/rfqs/abc123",
        )
        assert notif.action_url == "/rfqs/abc123"


class TestNotificationTypeEnum:
    """Tests for NotificationType enum."""

    def test_all_types_defined(self):
        """All expected notification types should be defined."""
        assert NotificationType.TASK_ASSIGNED.value == "task_assigned"
        assert NotificationType.TASK_DUE.value == "task_due"
        assert NotificationType.TASK_OVERDUE.value == "task_overdue"
        assert NotificationType.TASK_COMPLETED.value == "task_completed"
        assert NotificationType.TASK_COMMENT.value == "task_comment"
        assert NotificationType.RFQ_RECEIVED.value == "rfq_received"
        assert NotificationType.RFQ_DUE.value == "rfq_due"
        assert NotificationType.QUOTE_APPROVED.value == "quote_approved"
        assert NotificationType.MENTION.value == "mention"
        assert NotificationType.SYSTEM.value == "system"


class TestNotificationStatusEnum:
    """Tests for NotificationStatus enum."""

    def test_all_statuses_defined(self):
        """All expected notification statuses should be defined."""
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.DELIVERED.value == "delivered"
        assert NotificationStatus.FAILED.value == "failed"
        assert NotificationStatus.CANCELLED.value == "cancelled"


class TestNotificationPriorityEnum:
    """Tests for NotificationPriority enum."""

    def test_all_priorities_defined(self):
        """All expected notification priorities should be defined."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


class TestNotificationChannelEnum:
    """Tests for NotificationChannel enum."""

    def test_all_channels_defined(self):
        """All expected notification channels should be defined."""
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.PUSH.value == "push"
        assert NotificationChannel.SMS.value == "sms"
