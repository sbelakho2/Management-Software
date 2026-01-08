"""
Tests for Mentions and Assignments Service
"""
from datetime import datetime, timedelta

import pytest

from sensei.services.mentions_assignments import (
    # Enums
    MentionType,
    AssignmentStatus,
    NotificationType,
    EntityType,
    Priority,
    # Data Models
    Mention,
    Assignment,
    TaskFromComment,
    MentionNotification,
    UserSummary,
    TeamSummary,
    DueDateInfo,
    # Request/Response Models
    ParseMentionsRequest,
    CreateAssignmentRequest,
    CreateTaskFromCommentRequest,
    UpdateDueDateRequest,
    ReassignRequest,
    # Utility Functions
    extract_mentions_from_text,
    clean_mention_text,
    generate_task_title_from_comment,
    calculate_due_date_info,
    generate_due_date_from_text,
    format_mention_notification_message,
    generate_entity_link,
    # Service
    MentionsAssignmentsService,
)


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enum values."""
    
    def test_mention_type_values(self):
        """Test MentionType enum values."""
        assert MentionType.USER.value == "user"
        assert MentionType.TEAM.value == "team"
        assert MentionType.ROLE.value == "role"
        assert MentionType.ENTITY.value == "entity"
    
    def test_assignment_status_values(self):
        """Test AssignmentStatus enum values."""
        assert AssignmentStatus.PENDING.value == "pending"
        assert AssignmentStatus.ACCEPTED.value == "accepted"
        assert AssignmentStatus.DECLINED.value == "declined"
        assert AssignmentStatus.COMPLETED.value == "completed"
        assert AssignmentStatus.REASSIGNED.value == "reassigned"
    
    def test_notification_type_values(self):
        """Test NotificationType enum values."""
        assert NotificationType.MENTION.value == "mention"
        assert NotificationType.ASSIGNMENT.value == "assignment"
        assert NotificationType.DUE_DATE_SET.value == "due_date_set"
        assert NotificationType.DUE_DATE_REMINDER.value == "due_date_reminder"
        assert NotificationType.DUE_DATE_OVERDUE.value == "due_date_overdue"
        assert NotificationType.TASK_CREATED_FROM_COMMENT.value == "task_created_from_comment"
        assert NotificationType.REASSIGNMENT.value == "reassignment"
    
    def test_entity_type_values(self):
        """Test EntityType enum values."""
        assert EntityType.TASK.value == "task"
        assert EntityType.COMMENT.value == "comment"
        assert EntityType.RFQ.value == "rfq"
        assert EntityType.QUOTE.value == "quote"
        assert EntityType.OPPORTUNITY.value == "opportunity"
        assert EntityType.A3.value == "a3"
        assert EntityType.OBEYA.value == "obeya"
        assert EntityType.ANDON.value == "andon"
    
    def test_priority_values(self):
        """Test Priority enum values."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.URGENT.value == "urgent"


# =============================================================================
# Data Model Tests
# =============================================================================

class TestDataModels:
    """Tests for data models."""
    
    def test_mention_defaults(self):
        """Test Mention model defaults."""
        mention = Mention()
        assert mention.id is not None
        assert mention.mention_type == MentionType.USER
        assert mention.target_id == ""
        assert mention.notified is False
    
    def test_mention_custom_values(self):
        """Test Mention model with custom values."""
        mention = Mention(
            mention_type=MentionType.TEAM,
            target_id="team-1",
            target_name="Engineering",
            display_text="@team:engineering",
        )
        assert mention.mention_type == MentionType.TEAM
        assert mention.target_id == "team-1"
        assert mention.target_name == "Engineering"
    
    def test_assignment_defaults(self):
        """Test Assignment model defaults."""
        assignment = Assignment()
        assert assignment.id is not None
        assert assignment.status == AssignmentStatus.PENDING
        assert assignment.priority == Priority.MEDIUM
        assert assignment.due_date is None
    
    def test_task_from_comment_defaults(self):
        """Test TaskFromComment model defaults."""
        task = TaskFromComment()
        assert task.id is not None
        assert task.title == ""
        assert task.priority == Priority.MEDIUM
    
    def test_mention_notification_defaults(self):
        """Test MentionNotification model defaults."""
        notification = MentionNotification()
        assert notification.id is not None
        assert notification.read is False
        assert notification.read_at is None
    
    def test_user_summary_model(self):
        """Test UserSummary model."""
        user = UserSummary(
            id="user-1",
            name="John Doe",
            email="john@example.com",
            role="engineer",
        )
        assert user.id == "user-1"
        assert user.name == "John Doe"
    
    def test_team_summary_model(self):
        """Test TeamSummary model."""
        team = TeamSummary(
            id="team-1",
            name="Engineering",
            member_ids=["user-1", "user-2"],
        )
        assert team.id == "team-1"
        assert len(team.member_ids) == 2
    
    def test_due_date_info_model(self):
        """Test DueDateInfo model."""
        due = datetime.now() + timedelta(days=5)
        info = DueDateInfo(
            due_date=due,
            is_overdue=False,
            days_remaining=5,
        )
        assert info.due_date == due
        assert info.is_overdue is False


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_extract_user_mentions(self):
        """Test extracting user mentions from text."""
        text = "Hey @john.doe and @jane, please review this."
        mentions = extract_mentions_from_text(text)
        
        assert len(mentions) == 2
        assert mentions[0]["type"] == MentionType.USER
        assert mentions[0]["value"] == "john.doe"
        assert mentions[1]["value"] == "jane"
    
    def test_extract_team_mentions(self):
        """Test extracting team mentions from text."""
        text = "Assigning this to @team:engineering for review."
        mentions = extract_mentions_from_text(text)
        
        assert len(mentions) == 1
        assert mentions[0]["type"] == MentionType.TEAM
        assert mentions[0]["value"] == "engineering"
    
    def test_extract_role_mentions(self):
        """Test extracting role mentions from text."""
        text = "Need approval from @role:manager"
        mentions = extract_mentions_from_text(text)
        
        assert len(mentions) == 1
        assert mentions[0]["type"] == MentionType.ROLE
        assert mentions[0]["value"] == "manager"
    
    def test_extract_entity_mentions(self):
        """Test extracting entity mentions from text."""
        text = "Related to #RFQ-123 and #QUOTE-456"
        mentions = extract_mentions_from_text(text)
        
        assert len(mentions) == 2
        assert mentions[0]["type"] == MentionType.ENTITY
        assert mentions[0]["value"] == "RFQ-123"
        assert mentions[1]["value"] == "QUOTE-456"
    
    def test_extract_mixed_mentions(self):
        """Test extracting mixed mentions from text."""
        text = "@john please check #RFQ-123 with @team:sales"
        mentions = extract_mentions_from_text(text)
        
        assert len(mentions) == 3
        # Should be sorted by position
        assert mentions[0]["value"] == "john"
        assert mentions[1]["value"] == "RFQ-123"
        assert mentions[2]["value"] == "sales"
    
    def test_extract_no_mentions(self):
        """Test text with no mentions."""
        text = "Just a regular comment with no mentions."
        mentions = extract_mentions_from_text(text)
        assert len(mentions) == 0
    
    def test_clean_mention_text_users(self):
        """Test cleaning user mentions from text."""
        text = "Hey @john.doe, please review."
        cleaned = clean_mention_text(text)
        assert cleaned == "Hey john.doe, please review."
    
    def test_clean_mention_text_teams(self):
        """Test cleaning team mentions from text."""
        text = "Assigned to @team:engineering"
        cleaned = clean_mention_text(text)
        assert cleaned == "Assigned to engineering team"
    
    def test_clean_mention_text_roles(self):
        """Test cleaning role mentions from text."""
        text = "Need approval from @role:manager"
        cleaned = clean_mention_text(text)
        assert cleaned == "Need approval from manager role"
    
    def test_generate_task_title_short(self):
        """Test generating task title from short comment."""
        comment = "@john please review this RFQ"
        title = generate_task_title_from_comment(comment)
        assert title == "john please review this RFQ"
    
    def test_generate_task_title_long(self):
        """Test generating task title from long comment."""
        comment = "This is a very long comment that needs to be truncated " * 5
        title = generate_task_title_from_comment(comment, max_length=50)
        assert len(title) <= 50
        assert title.endswith("...")
    
    def test_calculate_due_date_info_future(self):
        """Test calculating due date info for future date."""
        due_date = datetime.now() + timedelta(days=5, hours=12)
        info = calculate_due_date_info(due_date)
        
        assert info is not None
        assert info.is_overdue is False
        assert info.days_remaining == 5
    
    def test_calculate_due_date_info_past(self):
        """Test calculating due date info for past date."""
        due_date = datetime.now() - timedelta(days=2)
        info = calculate_due_date_info(due_date)
        
        assert info is not None
        assert info.is_overdue is True
        assert info.days_remaining == -2
    
    def test_calculate_due_date_info_none(self):
        """Test calculating due date info for None."""
        info = calculate_due_date_info(None)
        assert info is None
    
    def test_generate_due_date_today(self):
        """Test generating due date from 'today'."""
        due = generate_due_date_from_text("Complete this today")
        assert due is not None
        assert due.date() == datetime.now().date()
    
    def test_generate_due_date_tomorrow(self):
        """Test generating due date from 'tomorrow'."""
        due = generate_due_date_from_text("Complete this tomorrow")
        assert due is not None
        assert due.date() == (datetime.now() + timedelta(days=1)).date()
    
    def test_generate_due_date_in_days(self):
        """Test generating due date from 'in X days'."""
        due = generate_due_date_from_text("Complete this in 3 days")
        assert due is not None
        expected = (datetime.now() + timedelta(days=3)).date()
        assert due.date() == expected
    
    def test_generate_due_date_in_weeks(self):
        """Test generating due date from 'in X weeks'."""
        due = generate_due_date_from_text("Complete this in 2 weeks")
        assert due is not None
        expected = (datetime.now() + timedelta(weeks=2)).date()
        assert due.date() == expected
    
    def test_generate_due_date_next_week(self):
        """Test generating due date from 'next week'."""
        due = generate_due_date_from_text("Complete this next week")
        assert due is not None
    
    def test_generate_due_date_no_match(self):
        """Test generating due date from text with no date."""
        due = generate_due_date_from_text("Complete this soon")
        assert due is None
    
    def test_format_mention_notification_message(self):
        """Test formatting notification messages."""
        message = format_mention_notification_message(
            NotificationType.MENTION,
            "John Doe",
            EntityType.COMMENT,
            "RFQ Discussion",
        )
        assert "John Doe" in message
        assert "mentioned" in message
        assert "comment" in message
    
    def test_format_assignment_notification_message(self):
        """Test formatting assignment notification messages."""
        message = format_mention_notification_message(
            NotificationType.ASSIGNMENT,
            "Jane Smith",
            EntityType.TASK,
            "Review Quote",
        )
        assert "Jane Smith" in message
        assert "assigned" in message
    
    def test_generate_entity_link(self):
        """Test generating entity links."""
        link = generate_entity_link(EntityType.TASK, "task-123")
        assert link == "/tasks/task-123"
        
        link = generate_entity_link(EntityType.RFQ, "rfq-456")
        assert link == "/rfqs/rfq-456"
        
        link = generate_entity_link(EntityType.QUOTE, "quote-789")
        assert link == "/quotes/quote-789"


# =============================================================================
# Service Tests
# =============================================================================

class TestMentionsAssignmentsService:
    """Tests for MentionsAssignmentsService."""
    
    @pytest.fixture
    def service(self) -> MentionsAssignmentsService:
        """Create a fresh service instance."""
        return MentionsAssignmentsService()
    
    @pytest.fixture
    def users(self, service: MentionsAssignmentsService) -> list[UserSummary]:
        """Register test users."""
        users = [
            UserSummary(id="user-1", name="john.doe", email="john@example.com", role="engineer"),
            UserSummary(id="user-2", name="jane.smith", email="jane@example.com", role="manager"),
            UserSummary(id="user-3", name="bob.wilson", email="bob@example.com", role="engineer"),
        ]
        for user in users:
            service.register_user(user)
        return users
    
    @pytest.fixture
    def team(self, service: MentionsAssignmentsService, users: list[UserSummary]) -> TeamSummary:
        """Register a test team."""
        team = TeamSummary(
            id="team-1",
            name="engineering",
            member_ids=["user-1", "user-3"],
        )
        service.register_team(team)
        return team


class TestUserTeamManagement(TestMentionsAssignmentsService):
    """Tests for user and team management."""
    
    def test_register_user(self, service: MentionsAssignmentsService):
        """Test registering a user."""
        user = UserSummary(id="user-1", name="john.doe", email="john@example.com", role="engineer")
        service.register_user(user)
        
        resolved = service.resolve_user("user-1")
        assert resolved is not None
        assert resolved.name == "john.doe"
    
    def test_resolve_user_by_name(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test resolving a user by name."""
        resolved = service.resolve_user("john.doe")
        assert resolved is not None
        assert resolved.id == "user-1"
    
    def test_resolve_user_case_insensitive(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test resolving a user with different case."""
        resolved = service.resolve_user("JOHN.DOE")
        assert resolved is not None
        assert resolved.id == "user-1"
    
    def test_resolve_unknown_user(self, service: MentionsAssignmentsService):
        """Test resolving an unknown user."""
        resolved = service.resolve_user("unknown")
        assert resolved is None
    
    def test_register_team(self, service: MentionsAssignmentsService, team: TeamSummary):
        """Test registering a team."""
        resolved = service.resolve_team("team-1")
        assert resolved is not None
        assert resolved.name == "engineering"
    
    def test_resolve_team_by_name(self, service: MentionsAssignmentsService, team: TeamSummary):
        """Test resolving a team by name."""
        resolved = service.resolve_team("engineering")
        assert resolved is not None
        assert resolved.id == "team-1"


class TestMentionParsing(TestMentionsAssignmentsService):
    """Tests for mention parsing."""
    
    def test_parse_user_mentions(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test parsing user mentions."""
        request = ParseMentionsRequest(
            text="Hey @john.doe, can you help with this?",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        )
        
        response = service.parse_mentions(request)
        
        assert len(response.mentions) == 1
        assert len(response.user_mentions) == 1
        assert response.user_mentions[0].target_id == "user-1"
        assert response.mention_count == 1
    
    def test_parse_team_mentions(self, service: MentionsAssignmentsService, team: TeamSummary):
        """Test parsing team mentions."""
        request = ParseMentionsRequest(
            text="Assigning to @team:engineering",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        )
        
        response = service.parse_mentions(request)
        
        assert len(response.team_mentions) == 1
        assert response.team_mentions[0].target_id == "team-1"
    
    def test_parse_multiple_mentions(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test parsing multiple mentions."""
        request = ParseMentionsRequest(
            text="@john.doe and @jane.smith please review",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-3",
        )
        
        response = service.parse_mentions(request)
        
        assert len(response.mentions) == 2
        assert response.mention_count == 2
    
    def test_parse_cleaned_text(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test that parsed response includes cleaned text."""
        request = ParseMentionsRequest(
            text="Hey @john.doe, can you help?",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        )
        
        response = service.parse_mentions(request)
        
        assert response.cleaned_text == "Hey john.doe, can you help?"
    
    def test_get_mention_by_id(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting a mention by ID."""
        request = ParseMentionsRequest(
            text="@john.doe please review",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        )
        
        response = service.parse_mentions(request)
        mention_id = response.mentions[0].id
        
        retrieved = service.get_mention(mention_id)
        assert retrieved is not None
        assert retrieved.target_id == "user-1"
    
    def test_get_mentions_for_entity(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting mentions for an entity."""
        service.parse_mentions(ParseMentionsRequest(
            text="@john.doe please review",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        ))
        
        mentions = service.get_mentions_for_entity(EntityType.COMMENT, "comment-1")
        assert len(mentions) == 1
    
    def test_get_mentions_for_user(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting mentions for a user."""
        service.parse_mentions(ParseMentionsRequest(
            text="@john.doe please review",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        ))
        
        mentions = service.get_mentions_for_user("user-1")
        assert len(mentions) == 1


class TestAssignmentManagement(TestMentionsAssignmentsService):
    """Tests for assignment management."""
    
    def test_create_assignment(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test creating an assignment."""
        request = CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Review RFQ",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            priority=Priority.HIGH,
        )
        
        response = service.create_assignment(request)
        
        assert response.success is True
        assert response.assignment is not None
        assert response.assignment.assignee_id == "user-1"
        assert response.assignment.status == AssignmentStatus.PENDING
    
    def test_create_assignment_with_due_date(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test creating an assignment with due date."""
        due_date = datetime.now() + timedelta(days=7)
        
        request = CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Review RFQ",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            due_date=due_date,
        )
        
        response = service.create_assignment(request)
        
        assert response.success is True
        assert response.assignment.due_date == due_date
    
    def test_create_assignment_creates_notification(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test that creating an assignment creates a notification."""
        request = CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Review RFQ",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        )
        
        response = service.create_assignment(request)
        
        assert response.notification is not None
        assert response.notification.recipient_id == "user-1"
        assert response.notification.notification_type == NotificationType.ASSIGNMENT
    
    def test_create_assignment_missing_entity_id(self, service: MentionsAssignmentsService):
        """Test creating assignment without entity ID fails."""
        request = CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            assignee_id="user-1",
        )
        
        response = service.create_assignment(request)
        
        assert response.success is False
        assert "Entity ID" in response.error
    
    def test_create_assignment_missing_assignee(self, service: MentionsAssignmentsService):
        """Test creating assignment without assignee fails."""
        request = CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
        )
        
        response = service.create_assignment(request)
        
        assert response.success is False
        assert "Assignee" in response.error
    
    def test_get_assignment_by_id(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting an assignment by ID."""
        request = CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Review RFQ",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        )
        
        response = service.create_assignment(request)
        assignment_id = response.assignment.id
        
        retrieved = service.get_assignment(assignment_id)
        assert retrieved is not None
        assert retrieved.entity_id == "task-1"
    
    def test_get_assignments_for_user(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting assignments for a user."""
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-2",
            entity_name="Task 2",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        assignments = service.get_assignments_for_user("user-1")
        assert len(assignments) == 2
    
    def test_accept_assignment(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test accepting an assignment."""
        response = service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        result = service.accept_assignment(response.assignment.id)
        
        assert result is True
        assignment = service.get_assignment(response.assignment.id)
        assert assignment.status == AssignmentStatus.ACCEPTED
        assert assignment.accepted_at is not None
    
    def test_decline_assignment(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test declining an assignment."""
        response = service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        result = service.decline_assignment(response.assignment.id, "Too busy")
        
        assert result is True
        assignment = service.get_assignment(response.assignment.id)
        assert assignment.status == AssignmentStatus.DECLINED
        assert assignment.notes == "Too busy"
    
    def test_complete_assignment(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test completing an assignment."""
        response = service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        result = service.complete_assignment(response.assignment.id)
        
        assert result is True
        assignment = service.get_assignment(response.assignment.id)
        assert assignment.status == AssignmentStatus.COMPLETED
        assert assignment.completed_at is not None
    
    def test_complete_unknown_assignment(self, service: MentionsAssignmentsService):
        """Test completing an unknown assignment."""
        result = service.complete_assignment("unknown-id")
        assert result is False


class TestTaskFromComment(TestMentionsAssignmentsService):
    """Tests for creating tasks from comments."""
    
    def test_create_task_from_comment(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test creating a task from a comment."""
        request = CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="Need to review the pricing for this quote",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        )
        
        response = service.create_task_from_comment(request)
        
        assert response.success is True
        assert response.task is not None
        assert response.task.source_comment_id == "comment-1"
        assert "pricing" in response.task.title.lower()
    
    def test_create_task_with_custom_title(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test creating a task with custom title."""
        request = CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="Need to review the pricing",
            title="Custom Task Title",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        )
        
        response = service.create_task_from_comment(request)
        
        assert response.task.title == "Custom Task Title"
    
    def test_create_task_with_assignee(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test creating a task with an assignee."""
        request = CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="Need to review the pricing",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            assignee_id="user-1",
            assignee_name="john.doe",
            created_by="user-2",
            created_by_name="jane.smith",
        )
        
        response = service.create_task_from_comment(request)
        
        assert response.success is True
        assert response.task.assignee_id == "user-1"
        assert response.assignment is not None
        assert response.assignment.assignee_id == "user-1"
    
    def test_create_task_with_mentions(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test creating a task with mentions creates notifications."""
        request = CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="@john.doe please check this pricing issue",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        )
        
        response = service.create_task_from_comment(request)
        
        assert response.success is True
        # Should have notification for mentioned user
        assert len(response.notifications) >= 1
    
    def test_create_task_empty_comment(self, service: MentionsAssignmentsService):
        """Test creating task from empty comment fails."""
        request = CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        )
        
        response = service.create_task_from_comment(request)
        
        assert response.success is False
        assert "required" in response.error.lower()
    
    def test_get_task_by_id(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting a task by ID."""
        response = service.create_task_from_comment(CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="Review pricing",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        ))
        
        task = service.get_task(response.task.id)
        assert task is not None
        assert task.source_comment_id == "comment-1"
    
    def test_get_tasks_for_entity(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting tasks for an entity."""
        service.create_task_from_comment(CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text="Task 1",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        ))
        
        service.create_task_from_comment(CreateTaskFromCommentRequest(
            comment_id="comment-2",
            comment_text="Task 2",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
            created_by_name="jane.smith",
        ))
        
        tasks = service.get_tasks_for_entity(EntityType.QUOTE, "quote-123")
        assert len(tasks) == 2


class TestDueDateManagement(TestMentionsAssignmentsService):
    """Tests for due date management."""
    
    def test_update_due_date(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test updating a due date."""
        # First create an assignment
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        new_due = datetime.now() + timedelta(days=5)
        request = UpdateDueDateRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            new_due_date=new_due,
            updated_by="user-2",
            updated_by_name="jane.smith",
        )
        
        response = service.update_due_date(request)
        
        assert response.success is True
        assert response.new_due_date == new_due
    
    def test_update_due_date_creates_notification(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test that updating due date creates notification."""
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        response = service.update_due_date(UpdateDueDateRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            new_due_date=datetime.now() + timedelta(days=5),
            updated_by="user-2",
            updated_by_name="jane.smith",
            notify_assignee=True,
        ))
        
        assert response.notification is not None
        assert response.notification.notification_type == NotificationType.DUE_DATE_SET
    
    def test_update_due_date_no_assignment(self, service: MentionsAssignmentsService):
        """Test updating due date for non-existent assignment."""
        response = service.update_due_date(UpdateDueDateRequest(
            entity_type=EntityType.TASK,
            entity_id="nonexistent",
            new_due_date=datetime.now(),
            updated_by="user-1",
            updated_by_name="john.doe",
        ))
        
        assert response.success is False
        assert "No assignment" in response.error
    
    def test_get_overdue_assignments(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting overdue assignments."""
        # Create overdue assignment
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Overdue Task",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            due_date=datetime.now() - timedelta(days=1),
        ))
        
        # Create future assignment
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-2",
            entity_name="Future Task",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            due_date=datetime.now() + timedelta(days=7),
        ))
        
        overdue = service.get_overdue_assignments()
        assert len(overdue) == 1
        assert overdue[0].entity_name == "Overdue Task"
    
    def test_get_upcoming_assignments(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting upcoming assignments."""
        # Create assignment due in 3 days
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Soon Task",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            due_date=datetime.now() + timedelta(days=3),
        ))
        
        # Create assignment due in 14 days
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-2",
            entity_name="Later Task",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            due_date=datetime.now() + timedelta(days=14),
        ))
        
        upcoming = service.get_upcoming_assignments(days=7)
        assert len(upcoming) == 1
        assert upcoming[0].entity_name == "Soon Task"


class TestReassignment(TestMentionsAssignmentsService):
    """Tests for reassignment functionality."""
    
    def test_reassign_entity(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test reassigning an entity."""
        # Create initial assignment
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-3",
            assigned_by_name="bob.wilson",
        ))
        
        response = service.reassign(ReassignRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            new_assignee_id="user-2",
            new_assignee_name="jane.smith",
            reassigned_by="user-3",
            reassigned_by_name="bob.wilson",
            reason="Better suited for this task",
        ))
        
        assert response.success is True
        assert response.previous_assignee_id == "user-1"
        assert response.new_assignment.assignee_id == "user-2"
    
    def test_reassign_notifies_both(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test that reassignment notifies both parties."""
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-3",
            assigned_by_name="bob.wilson",
        ))
        
        response = service.reassign(ReassignRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            new_assignee_id="user-2",
            new_assignee_name="jane.smith",
            reassigned_by="user-3",
            reassigned_by_name="bob.wilson",
            notify_both=True,
        ))
        
        # Should have notification for new assignee and previous assignee
        assert len(response.notifications) == 2
    
    def test_reassign_no_assignment(self, service: MentionsAssignmentsService):
        """Test reassigning when no assignment exists."""
        response = service.reassign(ReassignRequest(
            entity_type=EntityType.TASK,
            entity_id="nonexistent",
            new_assignee_id="user-2",
            new_assignee_name="jane.smith",
            reassigned_by="user-1",
            reassigned_by_name="john.doe",
        ))
        
        assert response.success is False
        assert "No assignment" in response.error


class TestNotifications(TestMentionsAssignmentsService):
    """Tests for notification functionality."""
    
    def test_get_notifications_for_user(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting notifications for a user."""
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        notifications = service.get_notifications_for_user("user-1")
        assert len(notifications) == 1
    
    def test_get_unread_notifications(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting unread notifications."""
        response = service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        # Mark first notification as read
        service.mark_notification_read(response.notification.id)
        
        # Create another notification
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-2",
            entity_name="Task 2",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        unread = service.get_notifications_for_user("user-1", unread_only=True)
        assert len(unread) == 1
    
    def test_mark_notification_read(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test marking a notification as read."""
        response = service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        result = service.mark_notification_read(response.notification.id)
        
        assert result is True
        notification = service.get_notification(response.notification.id)
        assert notification.read is True
        assert notification.read_at is not None
    
    def test_mark_all_notifications_read(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test marking all notifications as read."""
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-2",
            entity_name="Task 2",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        count = service.mark_all_notifications_read("user-1")
        
        assert count == 2
        assert service.get_unread_notification_count("user-1") == 0
    
    def test_get_unread_count(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test getting unread notification count."""
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-2",
            entity_name="Task 2",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        count = service.get_unread_notification_count("user-1")
        assert count == 2


class TestMentionNotificationProcessing(TestMentionsAssignmentsService):
    """Tests for mention-to-notification processing."""
    
    def test_process_user_mention_notifications(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test processing notifications for user mentions."""
        # Parse mentions first
        response = service.parse_mentions(ParseMentionsRequest(
            text="@john.doe please review this",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        ))
        
        notifications = service.process_mention_notifications(
            mentions=response.mentions,
            sender_id="user-2",
            sender_name="jane.smith",
            entity_type=EntityType.COMMENT,
            entity_id="comment-1",
            entity_name="Discussion Thread",
        )
        
        assert len(notifications) == 1
        assert notifications[0].recipient_id == "user-1"
        assert notifications[0].notification_type == NotificationType.MENTION
    
    def test_process_team_mention_notifications(self, service: MentionsAssignmentsService, users: list[UserSummary], team: TeamSummary):
        """Test processing notifications for team mentions."""
        response = service.parse_mentions(ParseMentionsRequest(
            text="@team:engineering please review",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        ))
        
        notifications = service.process_mention_notifications(
            mentions=response.mentions,
            sender_id="user-2",
            sender_name="jane.smith",
            entity_type=EntityType.COMMENT,
            entity_id="comment-1",
            entity_name="Discussion",
        )
        
        # Should have notifications for all team members
        assert len(notifications) == 2  # user-1 and user-3


class TestServiceCleanup(TestMentionsAssignmentsService):
    """Tests for service cleanup."""
    
    def test_clear_all(self, service: MentionsAssignmentsService, users: list[UserSummary]):
        """Test clearing all data."""
        # Create some data
        service.parse_mentions(ParseMentionsRequest(
            text="@john.doe test",
            source_entity_type=EntityType.COMMENT,
            source_entity_id="comment-1",
            created_by="user-2",
        ))
        
        service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Task 1",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
        ))
        
        service.clear_all()
        
        assert service.get_mentions_for_user("user-1") == []
        assert service.get_assignments_for_user("user-1") == []
        assert service.get_notifications_for_user("user-1") == []


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_comment_to_task_workflow(self):
        """Test complete workflow: comment with mention → task → assignment → completion."""
        service = MentionsAssignmentsService()
        
        # Register users
        john = UserSummary(id="user-1", name="john.doe", email="john@example.com", role="engineer")
        jane = UserSummary(id="user-2", name="jane.smith", email="jane@example.com", role="manager")
        service.register_user(john)
        service.register_user(jane)
        
        # Jane creates a comment with a mention
        parse_response = service.parse_mentions(ParseMentionsRequest(
            text="@john.doe we need to review the pricing for this quote by tomorrow",
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            created_by="user-2",
        ))
        
        assert len(parse_response.user_mentions) == 1
        
        # Jane creates a task from the comment
        due_date = generate_due_date_from_text("by tomorrow")
        task_response = service.create_task_from_comment(CreateTaskFromCommentRequest(
            comment_id="comment-1",
            comment_text=parse_response.cleaned_text,
            source_entity_type=EntityType.QUOTE,
            source_entity_id="quote-123",
            assignee_id="user-1",
            assignee_name="john.doe",
            due_date=due_date,
            priority=Priority.HIGH,
            created_by="user-2",
            created_by_name="jane.smith",
        ))
        
        assert task_response.success is True
        assert task_response.task is not None
        assert task_response.assignment is not None
        
        # John gets notifications
        john_notifications = service.get_notifications_for_user("user-1")
        assert len(john_notifications) >= 1
        
        # John accepts the assignment
        service.accept_assignment(task_response.assignment.id)
        
        # Verify status
        assignment = service.get_assignment(task_response.assignment.id)
        assert assignment.status == AssignmentStatus.ACCEPTED
        
        # John completes the task
        service.complete_assignment(task_response.assignment.id)
        
        # Verify completion
        assignment = service.get_assignment(task_response.assignment.id)
        assert assignment.status == AssignmentStatus.COMPLETED
        assert assignment.completed_at is not None
    
    def test_reassignment_workflow(self):
        """Test complete reassignment workflow."""
        service = MentionsAssignmentsService()
        
        # Register users
        service.register_user(UserSummary(id="user-1", name="john.doe", email="john@example.com", role="engineer"))
        service.register_user(UserSummary(id="user-2", name="jane.smith", email="jane@example.com", role="manager"))
        service.register_user(UserSummary(id="user-3", name="bob.wilson", email="bob@example.com", role="engineer"))
        
        # Create initial assignment to John
        initial = service.create_assignment(CreateAssignmentRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            entity_name="Review Quote",
            assignee_id="user-1",
            assignee_name="john.doe",
            assigned_by="user-2",
            assigned_by_name="jane.smith",
            due_date=datetime.now() + timedelta(days=3),
            priority=Priority.HIGH,
        ))
        
        assert initial.success is True
        
        # John declines
        service.decline_assignment(initial.assignment.id, "On vacation")
        
        # Jane reassigns to Bob
        reassign_response = service.reassign(ReassignRequest(
            entity_type=EntityType.TASK,
            entity_id="task-1",
            new_assignee_id="user-3",
            new_assignee_name="bob.wilson",
            reassigned_by="user-2",
            reassigned_by_name="jane.smith",
            reason="John unavailable",
            notify_both=True,
        ))
        
        assert reassign_response.success is True
        assert reassign_response.new_assignment.assignee_id == "user-3"
        
        # Verify old assignment is marked as reassigned
        old_assignment = service.get_assignment(initial.assignment.id)
        assert old_assignment.status == AssignmentStatus.REASSIGNED
        
        # Bob gets notification
        bob_notifications = service.get_notifications_for_user("user-3")
        assert len(bob_notifications) >= 1
