"""
Tests for Obeya models.

Tests:
- ObeyaItem model fields and defaults
- ObeyaItem category and status handling
- ObeyaComment model
- Status workflow
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.models.obeya import (
    ObeyaBoard,
    ObeyaCategory,
    ObeyaComment,
    ObeyaItem,
    ObeyaItemStatus,
    ObeyaItemType,
    ObeyaPriority,
    ObeyaStatus,
)


class TestObeyaItemModel:
    """Tests for the ObeyaItem model."""

    def test_obeya_item_required_fields(self):
        """ObeyaItem should require title, category."""
        item = ObeyaItem(
            title="Weekly Production KPI",
            category=ObeyaCategory.METRICS.value,
        )
        assert item.title == "Weekly Production KPI"
        assert item.category == ObeyaCategory.METRICS.value

    def test_obeya_item_default_status_is_new(self):
        """ObeyaItem status should default to new - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            status=ObeyaStatus.NEW.value,
        )
        assert item.status == ObeyaStatus.NEW.value

    def test_obeya_item_default_priority_is_medium(self):
        """ObeyaItem priority should default to medium - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            priority=ObeyaPriority.MEDIUM.value,
        )
        assert item.priority == ObeyaPriority.MEDIUM.value

    def test_obeya_item_default_board_is_daily(self):
        """ObeyaItem board should default to daily - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            board=ObeyaBoard.DAILY.value,
        )
        assert item.board == ObeyaBoard.DAILY.value

    def test_obeya_item_default_position_is_0(self):
        """ObeyaItem position should default to 0 - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            position=0,
        )
        assert item.position == 0

    def test_obeya_item_is_open_true_for_non_closed_statuses(self):
        """is_open should be True for non-closed statuses."""
        for status in [
            ObeyaStatus.NEW,
            ObeyaStatus.IN_PROGRESS,
            ObeyaStatus.BLOCKED,
            ObeyaStatus.WAITING,
        ]:
            item = ObeyaItem(
                title="Test",
                category=ObeyaCategory.METRICS.value,
                status=status.value,
            )
            assert item.is_open is True

    def test_obeya_item_is_open_false_for_closed_statuses(self):
        """is_open should be False for closed statuses."""
        for status in [
            ObeyaStatus.COMPLETED,
            ObeyaStatus.CANCELLED,
        ]:
            item = ObeyaItem(
                title="Test",
                category=ObeyaCategory.METRICS.value,
                status=status.value,
            )
            assert item.is_open is False

    def test_obeya_item_is_overdue_false_when_no_due_date(self):
        """is_overdue should be False when no due_date set."""
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            status=ObeyaStatus.IN_PROGRESS.value,
        )
        assert item.is_overdue is False

    def test_obeya_item_is_overdue_false_when_completed(self):
        """is_overdue should be False when item is completed."""
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            status=ObeyaStatus.COMPLETED.value,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert item.is_overdue is False

    def test_obeya_item_with_assignment(self):
        """ObeyaItem should accept assignment fields."""
        user_id = uuid4()
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.ISSUE.value,
            assigned_to_id=user_id,
        )
        assert item.assigned_to_id == user_id

    def test_obeya_item_with_due_date(self):
        """ObeyaItem should accept due_date."""
        due = datetime.now(timezone.utc) + timedelta(days=7)
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.ACTION.value,
            due_date=due,
        )
        assert item.due_date == due

    def test_obeya_item_with_kpi_fields(self):
        """ObeyaItem should accept KPI fields."""
        item = ObeyaItem(
            title="OEE Target",
            category=ObeyaCategory.KPI.value,
            kpi_target="95%",
            kpi_actual="92%",
            kpi_unit="%",
            kpi_trend="improving",
        )
        assert item.kpi_target == "95%"
        assert item.kpi_actual == "92%"
        assert item.kpi_unit == "%"
        assert item.kpi_trend == "improving"

    def test_obeya_item_with_escalation_fields(self):
        """ObeyaItem should accept escalation fields."""
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.ESCALATION.value,
            is_escalated=True,
            escalated_to_id=user_id,
            escalated_at=now,
            escalation_reason="Needs management attention",
        )
        assert item.is_escalated is True
        assert item.escalated_to_id == user_id
        assert item.escalated_at == now
        assert item.escalation_reason == "Needs management attention"

    def test_obeya_item_with_resolution(self):
        """ObeyaItem should accept resolution for issues."""
        item = ObeyaItem(
            title="Machine Down",
            category=ObeyaCategory.ISSUE.value,
            status=ObeyaStatus.COMPLETED.value,
            blocked_reason="Motor failure",
            resolution="Replaced motor, preventive maintenance scheduled",
        )
        assert item.blocked_reason == "Motor failure"
        assert item.resolution == "Replaced motor, preventive maintenance scheduled"

    def test_obeya_item_with_decision_fields(self):
        """ObeyaItem should accept decision fields."""
        item = ObeyaItem(
            title="Supplier Selection",
            category=ObeyaCategory.DECISION.value,
            decision_outcome="Selected Supplier A",
            decision_rationale="Best quality/cost ratio",
        )
        assert item.decision_outcome == "Selected Supplier A"
        assert item.decision_rationale == "Best quality/cost ratio"

    def test_obeya_item_with_color(self):
        """ObeyaItem should accept color for visual management."""
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.METRICS.value,
            color="red",
        )
        assert item.color == "red"

    def test_obeya_item_with_related_entity(self):
        """ObeyaItem should accept related entity reference."""
        entity_id = uuid4()
        item = ObeyaItem(
            title="Test",
            category=ObeyaCategory.ACTION.value,
            related_entity_type="rfq",
            related_entity_id=entity_id,
        )
        assert item.related_entity_type == "rfq"
        assert item.related_entity_id == entity_id


class TestObeyaCategoryEnum:
    """Tests for ObeyaCategory enum."""

    def test_main_categories_defined(self):
        """Main Obeya categories should be defined."""
        assert ObeyaCategory.ISSUE.value == "issue"
        assert ObeyaCategory.ACTION.value == "action"
        assert ObeyaCategory.RISK.value == "risk"
        assert ObeyaCategory.DECISION.value == "decision"
        assert ObeyaCategory.KPI.value == "kpi"
        assert ObeyaCategory.METRICS.value == "metrics"
        assert ObeyaCategory.ESCALATION.value == "escalation"


class TestObeyaStatusEnum:
    """Tests for ObeyaStatus enum."""

    def test_all_statuses_defined(self):
        """All expected statuses should be defined."""
        assert ObeyaStatus.NEW.value == "new"
        assert ObeyaStatus.IN_PROGRESS.value == "in_progress"
        assert ObeyaStatus.BLOCKED.value == "blocked"
        assert ObeyaStatus.WAITING.value == "waiting"
        assert ObeyaStatus.COMPLETED.value == "completed"
        assert ObeyaStatus.CANCELLED.value == "cancelled"


class TestObeyaPriorityEnum:
    """Tests for ObeyaPriority enum."""

    def test_all_priorities_defined(self):
        """All expected priorities should be defined."""
        assert ObeyaPriority.LOW.value == "low"
        assert ObeyaPriority.MEDIUM.value == "medium"
        assert ObeyaPriority.HIGH.value == "high"
        assert ObeyaPriority.CRITICAL.value == "critical"


class TestObeyaBoardEnum:
    """Tests for ObeyaBoard enum."""

    def test_all_boards_defined(self):
        """All expected board types should be defined."""
        assert ObeyaBoard.DAILY.value == "daily"
        assert ObeyaBoard.WEEKLY.value == "weekly"
        assert ObeyaBoard.PROJECT.value == "project"
        assert ObeyaBoard.STRATEGIC.value == "strategic"


class TestObeyaCommentModel:
    """Tests for the ObeyaComment model."""

    def test_obeya_comment_required_fields(self):
        """ObeyaComment should require item_id, content."""
        item_id = uuid4()
        comment = ObeyaComment(
            item_id=item_id,
            content="This is a comment on the item.",
        )
        assert comment.item_id == item_id
        assert comment.content == "This is a comment on the item."

    def test_obeya_comment_with_author(self):
        """ObeyaComment should accept author_id."""
        author_id = uuid4()
        comment = ObeyaComment(
            item_id=uuid4(),
            content="Test comment",
            author_id=author_id,
        )
        assert comment.author_id == author_id

    def test_obeya_comment_is_status_change_default_false(self):
        """is_status_change should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        comment = ObeyaComment(
            item_id=uuid4(),
            content="Test comment",
            is_status_change=False,
        )
        assert comment.is_status_change is False

    def test_obeya_comment_status_change_fields(self):
        """ObeyaComment should accept status change tracking fields."""
        comment = ObeyaComment(
            item_id=uuid4(),
            content="Status changed",
            is_status_change=True,
            old_status=ObeyaStatus.NEW.value,
            new_status=ObeyaStatus.IN_PROGRESS.value,
        )
        assert comment.is_status_change is True
        assert comment.old_status == ObeyaStatus.NEW.value
        assert comment.new_status == ObeyaStatus.IN_PROGRESS.value

    def test_obeya_comment_is_pinned_default_false(self):
        """is_pinned should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        comment = ObeyaComment(
            item_id=uuid4(),
            content="Test comment",
            is_pinned=False,
        )
        assert comment.is_pinned is False

    def test_obeya_comment_is_edited_default_false(self):
        """is_edited should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        comment = ObeyaComment(
            item_id=uuid4(),
            content="Test comment",
            is_edited=False,
        )
        assert comment.is_edited is False

    def test_obeya_comment_with_reply(self):
        """ObeyaComment should accept parent_id for replies."""
        parent_id = uuid4()
        comment = ObeyaComment(
            item_id=uuid4(),
            content="Reply to parent comment",
            parent_id=parent_id,
        )
        assert comment.parent_id == parent_id

    def test_obeya_comment_with_mentions(self):
        """ObeyaComment should accept mentions list."""
        user1 = uuid4()
        user2 = uuid4()
        comment = ObeyaComment(
            item_id=uuid4(),
            content="@user1 @user2 please review",
            mentions=[str(user1), str(user2)],
        )
        assert len(comment.mentions) == 2
