"""
Tests for Kanban System models.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from sensei.models.kanban import (
    KanbanBoard,
    BoardType,
    KanbanCard,
    CardType,
    CardStatus,
    CardPriority,
    KanbanCardHistory,
)


class TestKanbanBoardModel:
    """Test cases for KanbanBoard model."""

    def test_kanban_board_creation_basic(self):
        """Test basic board creation with required fields."""
        board = KanbanBoard(
            name="Production Board",
            board_type=BoardType.PRODUCTION,
            is_active=True,
        )

        assert board.name == "Production Board"
        assert board.board_type == BoardType.PRODUCTION
        assert board.is_active is True

    def test_kanban_board_creation_full(self):
        """Test board with all fields."""
        columns = [
            {"name": "To Do", "order": 0, "wip_limit": None},
            {"name": "Doing", "order": 1, "wip_limit": 5},
            {"name": "Done", "order": 2, "wip_limit": None},
        ]

        board = KanbanBoard(
            name="Engineering Board",
            code="KB-ENG-001",
            description="Engineering change requests",
            board_type=BoardType.ENGINEERING,
            work_center_id=5,
            wip_limit_global=20,
            columns_config_json=columns,
            is_active=True,
        )

        assert board.code == "KB-ENG-001"
        assert board.board_type == BoardType.ENGINEERING
        assert board.wip_limit_global == 20
        assert len(board.columns_config_json) == 3

    def test_board_type_values(self):
        """Test all board type values."""
        for board_type in BoardType:
            board = KanbanBoard(
                name=f"Test {board_type.value}",
                board_type=board_type,
            )
            assert board.board_type == board_type

    def test_board_column_names(self):
        """Test column_names property."""
        columns = [
            {"name": "Done", "order": 3},
            {"name": "Backlog", "order": 0},
            {"name": "In Progress", "order": 2},
            {"name": "Ready", "order": 1},
        ]

        board = KanbanBoard(
            name="Test",
            columns_config_json=columns,
        )

        names = board.column_names
        assert names == ["Backlog", "Ready", "In Progress", "Done"]

    def test_board_first_column(self):
        """Test first_column property."""
        columns = [
            {"name": "Backlog", "order": 0},
            {"name": "Done", "order": 1},
        ]

        board = KanbanBoard(
            name="Test",
            columns_config_json=columns,
        )

        assert board.first_column == "Backlog"

    def test_board_last_column(self):
        """Test last_column property."""
        columns = [
            {"name": "Backlog", "order": 0},
            {"name": "Done", "order": 1},
        ]

        board = KanbanBoard(
            name="Test",
            columns_config_json=columns,
        )

        assert board.last_column == "Done"

    def test_board_get_column_wip_limit(self):
        """Test get_column_wip_limit method."""
        columns = [
            {"name": "Backlog", "order": 0, "wip_limit": None},
            {"name": "In Progress", "order": 1, "wip_limit": 5},
            {"name": "Done", "order": 2, "wip_limit": None},
        ]

        board = KanbanBoard(
            name="Test",
            columns_config_json=columns,
        )

        assert board.get_column_wip_limit("Backlog") is None
        assert board.get_column_wip_limit("In Progress") == 5
        assert board.get_column_wip_limit("Unknown") is None

    def test_board_repr(self):
        """Test string representation."""
        board = KanbanBoard(
            name="Test Board",
            board_type=BoardType.PRODUCTION,
        )
        board.id = 1

        assert "KanbanBoard" in repr(board)
        assert "Test Board" in repr(board)


class TestKanbanCardModel:
    """Test cases for KanbanCard model."""

    def test_kanban_card_creation_basic(self):
        """Test basic card creation."""
        card = KanbanCard(
            card_number="CARD-001",
            title="Task 1",
            board_id=1,
            column_name="Backlog",
            card_type=CardType.TASK,
            priority=CardPriority.NORMAL,
            status=CardStatus.ACTIVE,
        )

        assert card.card_number == "CARD-001"
        assert card.title == "Task 1"
        assert card.column_name == "Backlog"
        assert card.card_type == CardType.TASK
        assert card.priority == CardPriority.NORMAL
        assert card.status == CardStatus.ACTIVE

    def test_kanban_card_creation_full(self):
        """Test card with all fields."""
        card = KanbanCard(
            card_number="CARD-002",
            title="Production Task",
            description="Complete assembly",
            board_id=1,
            column_name="In Progress",
            swimlane_name="Expedite",
            position=1,
            card_type=CardType.WORK_ORDER,
            priority=CardPriority.HIGH,
            status=CardStatus.ACTIVE,
            work_order_id=100,
            product_id=50,
            quantity=Decimal("10.0"),
            assigned_to_id=5,
            due_date=date.today() + timedelta(days=3),
            story_points=5,
            estimated_hours=Decimal("8.0"),
            tags=["urgent", "assembly"],
        )

        assert card.card_type == CardType.WORK_ORDER
        assert card.priority == CardPriority.HIGH
        assert card.quantity == Decimal("10.0")
        assert card.story_points == 5
        assert "urgent" in card.tags

    def test_card_type_values(self):
        """Test all card type values."""
        for card_type in CardType:
            card = KanbanCard(
                card_number=f"CARD-{card_type.value}",
                title=f"Test {card_type.value}",
                board_id=1,
                column_name="Backlog",
                card_type=card_type,
            )
            assert card.card_type == card_type

    def test_card_status_values(self):
        """Test all status values."""
        for status in CardStatus:
            card = KanbanCard(
                card_number=f"CARD-{status.value}",
                title=f"Test {status.value}",
                board_id=1,
                column_name="Backlog",
                status=status,
            )
            assert card.status == status

    def test_card_priority_values(self):
        """Test all priority values."""
        for priority in CardPriority:
            card = KanbanCard(
                card_number=f"CARD-{priority.value}",
                title=f"Test {priority.value}",
                board_id=1,
                column_name="Backlog",
                priority=priority,
            )
            assert card.priority == priority

    def test_card_is_active(self):
        """Test is_active property."""
        active = KanbanCard(
            card_number="CARD-ACTIVE",
            title="Active",
            board_id=1,
            column_name="Backlog",
            status=CardStatus.ACTIVE,
        )

        blocked = KanbanCard(
            card_number="CARD-BLOCKED",
            title="Blocked",
            board_id=1,
            column_name="Backlog",
            status=CardStatus.BLOCKED,
        )

        assert active.is_active is True
        assert blocked.is_active is False

    def test_card_is_blocked(self):
        """Test is_blocked property."""
        blocked = KanbanCard(
            card_number="CARD-BLOCKED",
            title="Blocked",
            board_id=1,
            column_name="Backlog",
            status=CardStatus.BLOCKED,
            blocked_reason="Waiting for materials",
        )

        assert blocked.is_blocked is True
        assert blocked.blocked_reason == "Waiting for materials"

    def test_card_is_completed(self):
        """Test is_completed property."""
        completed = KanbanCard(
            card_number="CARD-COMPLETE",
            title="Completed",
            board_id=1,
            column_name="Done",
            status=CardStatus.COMPLETED,
            completed_at=datetime.utcnow(),
        )

        active = KanbanCard(
            card_number="CARD-ACTIVE",
            title="Active",
            board_id=1,
            column_name="In Progress",
            status=CardStatus.ACTIVE,
        )

        assert completed.is_completed is True
        assert active.is_completed is False

    def test_card_is_overdue(self):
        """Test is_overdue property."""
        overdue = KanbanCard(
            card_number="CARD-OVERDUE",
            title="Overdue",
            board_id=1,
            column_name="Backlog",
            status=CardStatus.ACTIVE,
            due_date=date.today() - timedelta(days=5),
        )

        on_time = KanbanCard(
            card_number="CARD-ONTIME",
            title="On time",
            board_id=1,
            column_name="Backlog",
            status=CardStatus.ACTIVE,
            due_date=date.today() + timedelta(days=5),
        )

        completed_overdue = KanbanCard(
            card_number="CARD-COMP",
            title="Completed",
            board_id=1,
            column_name="Done",
            status=CardStatus.COMPLETED,
            due_date=date.today() - timedelta(days=5),
        )

        assert overdue.is_overdue is True
        assert on_time.is_overdue is False
        assert completed_overdue.is_overdue is False

    def test_card_lead_time_days(self):
        """Test lead_time_days property."""
        now = datetime.utcnow()
        card = KanbanCard(
            card_number="CARD-LEAD",
            title="Lead time",
            board_id=1,
            column_name="Done",
            status=CardStatus.COMPLETED,
        )
        card.created_at = now - timedelta(days=5)
        card.completed_at = now

        assert card.lead_time_days == 5

    def test_card_lead_time_not_completed(self):
        """Test lead_time_days when not completed."""
        card = KanbanCard(
            card_number="CARD-ACTIVE",
            title="Active",
            board_id=1,
            column_name="In Progress",
            status=CardStatus.ACTIVE,
        )

        assert card.lead_time_days is None

    def test_card_cycle_time_days(self):
        """Test cycle_time_days property."""
        now = datetime.utcnow()
        card = KanbanCard(
            card_number="CARD-CYCLE",
            title="Cycle time",
            board_id=1,
            column_name="Done",
            cycle_started_at=now - timedelta(days=3),
            cycle_completed_at=now,
        )

        cycle_time = card.cycle_time_days
        assert cycle_time is not None
        assert 2.9 <= cycle_time <= 3.1

    def test_card_age_days(self):
        """Test age_days property."""
        now = datetime.utcnow()
        card = KanbanCard(
            card_number="CARD-AGE",
            title="Age test",
            board_id=1,
            column_name="In Progress",
        )
        card.created_at = now - timedelta(days=10)

        assert card.age_days == 10

    def test_card_repr(self):
        """Test string representation."""
        card = KanbanCard(
            card_number="CARD-TEST",
            title="Test",
            board_id=1,
            column_name="Backlog",
        )
        card.id = 1

        assert "KanbanCard" in repr(card)
        assert "CARD-TEST" in repr(card)


class TestKanbanCardHistoryModel:
    """Test cases for KanbanCardHistory model."""

    def test_history_creation(self):
        """Test history record creation."""
        history = KanbanCardHistory(
            card_id=1,
            changed_by_id=5,
            field_name="column_name",
            old_value="Backlog",
            new_value="In Progress",
        )

        assert history.card_id == 1
        assert history.field_name == "column_name"
        assert history.old_value == "Backlog"
        assert history.new_value == "In Progress"

    def test_history_with_all_fields(self):
        """Test history with all fields."""
        history = KanbanCardHistory(
            card_id=1,
            changed_by_id=5,
            field_name="priority",
            old_value=CardPriority.NORMAL.value,
            new_value=CardPriority.HIGH.value,
        )

        assert history.old_value == "normal"
        assert history.new_value == "high"

    def test_history_repr(self):
        """Test string representation."""
        history = KanbanCardHistory(
            card_id=1,
            changed_by_id=5,
            field_name="column_name",
            old_value="Backlog",
            new_value="In Progress",
        )

        assert "KanbanCardHistory" in repr(history)


class TestKanbanRelationships:
    """Test Kanban model relationships."""

    def test_board_has_cards_list(self):
        """Test that board has cards list."""
        board = KanbanBoard(
            name="Test Board",
        )
        assert hasattr(board, 'cards')

    def test_card_has_history_list(self):
        """Test that card has history list."""
        card = KanbanCard(
            card_number="CARD-001",
            title="Test",
            board_id=1,
            column_name="Backlog",
        )
        assert hasattr(card, 'history')

    def test_card_has_board_relationship(self):
        """Test that card has board relationship."""
        card = KanbanCard(
            card_number="CARD-001",
            title="Test",
            board_id=1,
            column_name="Backlog",
        )
        assert hasattr(card, 'board')


class TestKanbanValidation:
    """Test validation constraints."""

    def test_board_explicit_is_active(self):
        """Test explicit is_active is True."""
        board = KanbanBoard(
            name="Test",
            is_active=True,
        )
        assert board.is_active is True

    def test_card_explicit_status(self):
        """Test explicit card status is ACTIVE."""
        card = KanbanCard(
            card_number="CARD-001",
            title="Test",
            board_id=1,
            column_name="Backlog",
            status=CardStatus.ACTIVE,
        )
        assert card.status == CardStatus.ACTIVE

    def test_card_explicit_priority(self):
        """Test explicit card priority is NORMAL."""
        card = KanbanCard(
            card_number="CARD-001",
            title="Test",
            board_id=1,
            column_name="Backlog",
            priority=CardPriority.NORMAL,
        )
        assert card.priority == CardPriority.NORMAL


class TestKanbanEdgeCases:
    """Test edge cases for Kanban models."""

    def test_board_with_swimlanes(self):
        """Test board with swimlane configuration."""
        swimlanes = [
            {"name": "Expedite", "order": 0, "wip_limit": 1},
            {"name": "Standard", "order": 1, "wip_limit": None},
            {"name": "Low Priority", "order": 2, "wip_limit": None},
        ]

        board = KanbanBoard(
            name="Swimlane Board",
            swimlanes_config_json=swimlanes,
        )

        assert len(board.swimlanes_config_json) == 3
        assert board.swimlanes_config_json[0]["name"] == "Expedite"

    def test_card_with_wip_override(self):
        """Test card with WIP limit override."""
        card = KanbanCard(
            card_number="CARD-WIP",
            title="WIP Override",
            board_id=1,
            column_name="In Progress",
            wip_limit_override=True,
            wip_limit_override_by_id=100,
            wip_limit_override_reason="GM approved for urgent delivery",
        )

        assert card.wip_limit_override is True
        assert card.wip_limit_override_reason == "GM approved for urgent delivery"

    def test_card_with_tags(self):
        """Test card with tags."""
        card = KanbanCard(
            card_number="CARD-TAGS",
            title="Tagged card",
            board_id=1,
            column_name="Backlog",
            tags=["urgent", "customer-request", "assembly"],
        )

        assert len(card.tags) == 3
        assert "urgent" in card.tags
