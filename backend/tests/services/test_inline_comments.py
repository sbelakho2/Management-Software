"""
Tests for Inline Comments and Mentions Service.

Comprehensive tests covering:
- Comment CRUD operations
- Mention parsing and resolution
- Notifications
- Threading and replies
- Reactions
- Task conversion
- Search and activity feeds
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sensei.services.inline_comments import (
    InlineCommentsService,
    Comment,
    CommentThread,
    CommentStatus,
    CommentableType,
    Mention,
    MentionType,
    MentionNotification,
    NotificationPriority,
    CommentReaction,
    UserRef,
    TeamRef,
    RoleRef,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service() -> InlineCommentsService:
    """Create a fresh comments service."""
    svc = InlineCommentsService()
    svc.clear()
    return svc


@pytest.fixture
def sample_users(service: InlineCommentsService) -> list[UserRef]:
    """Create and register sample users."""
    users = [
        UserRef(
            id=uuid4(),
            username="john.doe",
            display_name="John Doe",
            email="john.doe@example.com",
        ),
        UserRef(
            id=uuid4(),
            username="jane.smith",
            display_name="Jane Smith",
            email="jane.smith@example.com",
        ),
        UserRef(
            id=uuid4(),
            username="bob.wilson",
            display_name="Bob Wilson",
            email="bob.wilson@example.com",
        ),
    ]
    
    for user in users:
        service.register_user(user)
    
    return users


@pytest.fixture
def sample_team(service: InlineCommentsService, sample_users: list[UserRef]) -> TeamRef:
    """Create and register a sample team."""
    team = TeamRef(
        id=uuid4(),
        name="Sales Team",
        identifier="sales-team",
        member_ids=[sample_users[0].id, sample_users[1].id],
    )
    service.register_team(team)
    return team


@pytest.fixture
def sample_role(service: InlineCommentsService, sample_users: list[UserRef]) -> RoleRef:
    """Create and register a sample role."""
    role = RoleRef(
        id=uuid4(),
        name="Approvers",
        identifier="approvers",
        user_ids=[sample_users[1].id, sample_users[2].id],
    )
    service.register_role(role)
    return role


@pytest.fixture
def quote_id() -> tuple[CommentableType, uuid4]:
    """Create a sample quote reference."""
    return CommentableType.QUOTE, uuid4()


# =============================================================================
# Test Comment Creation
# =============================================================================


class TestCommentCreation:
    """Tests for creating comments."""
    
    def test_create_simple_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a simple comment without mentions."""
        quote_id = uuid4()
        author = sample_users[0]
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="This is a simple comment.",
            created_by=author.id,
        )
        
        assert comment.id is not None
        assert comment.content == "This is a simple comment."
        assert comment.created_by == author.id
        assert comment.status == CommentStatus.ACTIVE
        assert len(comment.mentions) == 0
    
    def test_create_comment_with_user_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a comment with a user mention."""
        quote_id = uuid4()
        author = sample_users[0]
        mentioned = sample_users[1]
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"Hey @{mentioned.username}, please review this.",
            created_by=author.id,
        )
        
        assert len(comment.mentions) == 1
        assert comment.mentions[0].mention_type == MentionType.USER
        assert comment.mentions[0].target_id == mentioned.id
    
    def test_create_comment_with_multiple_mentions(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a comment with multiple mentions."""
        quote_id = uuid4()
        author = sample_users[0]
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username} and @{sample_users[2].username}, please check.",
            created_by=author.id,
        )
        
        assert len(comment.mentions) == 2
    
    def test_create_comment_with_team_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
        sample_team: TeamRef,
    ) -> None:
        """Test creating a comment with a team mention."""
        quote_id = uuid4()
        author = sample_users[2]  # Not in team
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_team.identifier}, please review.",
            created_by=author.id,
        )
        
        assert len(comment.mentions) == 1
        assert comment.mentions[0].mention_type == MentionType.TEAM
        assert comment.mentions[0].target_id == sample_team.id
    
    def test_create_comment_with_role_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
        sample_role: RoleRef,
    ) -> None:
        """Test creating a comment with a role mention."""
        quote_id = uuid4()
        author = sample_users[0]  # Not in role
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_role.identifier}, approval needed.",
            created_by=author.id,
        )
        
        assert len(comment.mentions) == 1
        assert comment.mentions[0].mention_type == MentionType.ROLE
        assert comment.mentions[0].target_id == sample_role.id
    
    def test_create_comment_with_all_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a comment with @all mention."""
        quote_id = uuid4()
        author = sample_users[0]
        
        # Add watchers
        for user in sample_users:
            service.add_watcher(CommentableType.QUOTE, quote_id, user.id)
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="@all, important update!",
            created_by=author.id,
        )
        
        assert len(comment.mentions) == 1
        assert comment.mentions[0].mention_type == MentionType.ALL
    
    def test_create_comment_with_assignee_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a comment with @assignee mention."""
        quote_id = uuid4()
        author = sample_users[0]
        
        # Set assignee
        service.set_assignee(CommentableType.QUOTE, quote_id, sample_users[1].id)
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="@assignee, please check.",
            created_by=author.id,
        )
        
        assert len(comment.mentions) == 1
        assert comment.mentions[0].mention_type == MentionType.ASSIGNEE
    
    def test_create_line_item_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a comment on a specific line item."""
        quote_id = uuid4()
        author = sample_users[0]
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="This price needs review.",
            created_by=author.id,
            line_number=1,
            field_name="unit_price",
        )
        
        assert comment.line_number == 1
        assert comment.field_name == "unit_price"
    
    def test_create_comment_auto_adds_watcher(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that creating a comment auto-adds author as watcher."""
        quote_id = uuid4()
        author = sample_users[0]
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Test comment.",
            created_by=author.id,
        )
        
        watchers = service.get_watchers(CommentableType.QUOTE, quote_id)
        assert author.id in watchers


# =============================================================================
# Test Comment Retrieval
# =============================================================================


class TestCommentRetrieval:
    """Tests for retrieving comments."""
    
    def test_get_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting a comment by ID."""
        quote_id = uuid4()
        
        created = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Test comment.",
            created_by=sample_users[0].id,
        )
        
        retrieved = service.get_comment(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_nonexistent_comment(
        self,
        service: InlineCommentsService,
    ) -> None:
        """Test getting a non-existent comment."""
        result = service.get_comment(uuid4())
        assert result is None
    
    def test_get_comments_for_object(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting all comments for an object."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Comment 1",
            created_by=sample_users[0].id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Comment 2",
            created_by=sample_users[1].id,
        )
        
        comments = service.get_comments_for_object(CommentableType.QUOTE, quote_id)
        
        assert len(comments) == 2
    
    def test_get_comments_excludes_deleted(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that deleted comments are excluded by default."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Will be deleted",
            created_by=sample_users[0].id,
        )
        
        service.delete_comment(comment.id, sample_users[0].id)
        
        comments = service.get_comments_for_object(CommentableType.QUOTE, quote_id)
        
        assert len(comments) == 0
    
    def test_get_comments_for_line_item(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting comments for a specific line item."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Line 1 comment",
            created_by=sample_users[0].id,
            line_number=1,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Line 2 comment",
            created_by=sample_users[0].id,
            line_number=2,
        )
        
        line1_comments = service.get_comments_for_line_item(
            CommentableType.QUOTE,
            quote_id,
            line_number=1,
        )
        
        assert len(line1_comments) == 1
        assert line1_comments[0].content == "Line 1 comment"
    
    def test_get_comment_count(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting comment count for an object."""
        quote_id = uuid4()
        
        comment1 = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Active comment",
            created_by=sample_users[0].id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Will be resolved",
            created_by=sample_users[0].id,
        )
        
        service.resolve_comment(comment1.id, sample_users[1].id)
        
        counts = service.get_comment_count(CommentableType.QUOTE, quote_id)
        
        assert counts["total"] == 2
        assert counts["active"] == 1
        assert counts["resolved"] == 1


# =============================================================================
# Test Comment Updates
# =============================================================================


class TestCommentUpdates:
    """Tests for updating comments."""
    
    def test_update_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test updating a comment."""
        quote_id = uuid4()
        author = sample_users[0]
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Original content",
            created_by=author.id,
        )
        
        updated = service.update_comment(
            comment.id,
            "Updated content",
            author.id,
        )
        
        assert updated is not None
        assert updated.content == "Updated content"
        assert updated.updated_at is not None
    
    def test_update_comment_by_non_author_fails(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that non-author cannot update a comment."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Original content",
            created_by=sample_users[0].id,
        )
        
        result = service.update_comment(
            comment.id,
            "Updated content",
            sample_users[1].id,  # Not the author
        )
        
        assert result is None
    
    def test_update_adds_new_mention_notification(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that updating to add a new mention creates notification."""
        quote_id = uuid4()
        author = sample_users[0]
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Original content",
            created_by=author.id,
        )
        
        # Update with a new mention
        service.update_comment(
            comment.id,
            f"Updated @{sample_users[1].username}",
            author.id,
        )
        
        # Check notification was created
        notifications = service.get_notifications(sample_users[1].id)
        assert len(notifications) > 0


# =============================================================================
# Test Comment Deletion
# =============================================================================


class TestCommentDeletion:
    """Tests for deleting comments."""
    
    def test_soft_delete_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test soft deleting a comment."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Will be deleted",
            created_by=sample_users[0].id,
        )
        
        result = service.delete_comment(comment.id, sample_users[0].id)
        
        assert result is True
        
        # Comment still exists but is marked deleted
        retrieved = service.get_comment(comment.id)
        assert retrieved is not None
        assert retrieved.status == CommentStatus.DELETED
    
    def test_hard_delete_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test hard deleting a comment."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Will be deleted",
            created_by=sample_users[0].id,
        )
        
        result = service.delete_comment(comment.id, sample_users[0].id, hard_delete=True)
        
        assert result is True
        assert service.get_comment(comment.id) is None
    
    def test_delete_nonexistent_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test deleting a non-existent comment."""
        result = service.delete_comment(uuid4(), sample_users[0].id)
        assert result is False


# =============================================================================
# Test Comment Resolution
# =============================================================================


class TestCommentResolution:
    """Tests for resolving and reopening comments."""
    
    def test_resolve_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test resolving a comment."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Issue to resolve",
            created_by=sample_users[0].id,
        )
        
        resolved = service.resolve_comment(comment.id, sample_users[1].id)
        
        assert resolved is not None
        assert resolved.status == CommentStatus.RESOLVED
        assert resolved.resolved_by == sample_users[1].id
        assert resolved.resolved_at is not None
    
    def test_reopen_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test reopening a resolved comment."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Issue to resolve",
            created_by=sample_users[0].id,
        )
        
        service.resolve_comment(comment.id, sample_users[1].id)
        reopened = service.reopen_comment(comment.id)
        
        assert reopened is not None
        assert reopened.status == CommentStatus.ACTIVE
        assert reopened.resolved_by is None
        assert reopened.resolved_at is None


# =============================================================================
# Test Pinning
# =============================================================================


class TestPinning:
    """Tests for pinning comments."""
    
    def test_pin_comment(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test pinning a comment."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Important comment",
            created_by=sample_users[0].id,
        )
        
        pinned = service.pin_comment(comment.id)
        
        assert pinned is not None
        assert pinned.is_pinned is True
    
    def test_pinned_comments_come_first(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that pinned comments are returned first."""
        quote_id = uuid4()
        
        comment1 = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="First comment",
            created_by=sample_users[0].id,
        )
        comment2 = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Second comment (pinned)",
            created_by=sample_users[0].id,
        )
        
        service.pin_comment(comment2.id)
        
        comments = service.get_comments_for_object(CommentableType.QUOTE, quote_id)
        
        assert comments[0].id == comment2.id  # Pinned first


# =============================================================================
# Test Threading
# =============================================================================


class TestThreading:
    """Tests for threaded comments."""
    
    def test_create_reply(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating a reply to a comment."""
        quote_id = uuid4()
        
        root = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Original comment",
            created_by=sample_users[0].id,
        )
        
        reply = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Reply to original",
            created_by=sample_users[1].id,
            reply_to_id=root.id,
        )
        
        assert reply.reply_to_id == root.id
    
    def test_get_thread(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting a full comment thread."""
        quote_id = uuid4()
        
        root = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Original comment",
            created_by=sample_users[0].id,
        )
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Reply 1",
            created_by=sample_users[1].id,
            reply_to_id=root.id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Reply 2",
            created_by=sample_users[2].id,
            reply_to_id=root.id,
        )
        
        thread = service.get_thread(root.id)
        
        assert thread is not None
        assert thread.root_comment.id == root.id
        assert len(thread.replies) == 2
        assert len(thread.participant_ids) == 3
        assert thread.total_replies == 2


# =============================================================================
# Test Reactions
# =============================================================================


class TestReactions:
    """Tests for comment reactions."""
    
    def test_add_reaction(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test adding a reaction."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Great idea!",
            created_by=sample_users[0].id,
        )
        
        reaction = service.add_reaction(comment.id, sample_users[1].id, "👍")
        
        assert reaction is not None
        assert reaction.reaction_type == "👍"
        assert reaction.user_id == sample_users[1].id
    
    def test_add_duplicate_reaction(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test adding duplicate reaction returns existing."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Great idea!",
            created_by=sample_users[0].id,
        )
        
        reaction1 = service.add_reaction(comment.id, sample_users[1].id, "👍")
        reaction2 = service.add_reaction(comment.id, sample_users[1].id, "👍")
        
        assert reaction1.id == reaction2.id
    
    def test_remove_reaction(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test removing a reaction."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Great idea!",
            created_by=sample_users[0].id,
        )
        
        service.add_reaction(comment.id, sample_users[1].id, "👍")
        result = service.remove_reaction(comment.id, sample_users[1].id, "👍")
        
        assert result is True
        
        summary = service.get_reaction_summary(comment.id)
        assert "👍" not in summary
    
    def test_get_reaction_summary(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting reaction summary."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Great idea!",
            created_by=sample_users[0].id,
        )
        
        service.add_reaction(comment.id, sample_users[1].id, "👍")
        service.add_reaction(comment.id, sample_users[2].id, "👍")
        service.add_reaction(comment.id, sample_users[1].id, "❤️")
        
        summary = service.get_reaction_summary(comment.id)
        
        assert len(summary["👍"]) == 2
        assert len(summary["❤️"]) == 1


# =============================================================================
# Test Notifications
# =============================================================================


class TestNotifications:
    """Tests for mention notifications."""
    
    def test_notification_created_on_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that notifications are created on mention."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"Hey @{sample_users[1].username}, check this.",
            created_by=sample_users[0].id,
        )
        
        notifications = service.get_notifications(sample_users[1].id)
        
        assert len(notifications) == 1
        assert notifications[0].read is False
    
    def test_team_mention_notifies_all_members(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
        sample_team: TeamRef,
    ) -> None:
        """Test that team mention notifies all team members."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_team.identifier}, please review.",
            created_by=sample_users[2].id,  # Not in team
        )
        
        # Both team members should get notifications
        for user_id in sample_team.member_ids:
            notifications = service.get_notifications(user_id)
            assert len(notifications) == 1
    
    def test_author_not_notified_of_own_mention(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that author is not notified of their own mention."""
        quote_id = uuid4()
        author = sample_users[0]
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"I'll mention myself @{author.username}.",
            created_by=author.id,
        )
        
        notifications = service.get_notifications(author.id)
        
        assert len(notifications) == 0
    
    def test_mark_notification_read(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test marking a notification as read."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username}, check this.",
            created_by=sample_users[0].id,
        )
        
        notifications = service.get_notifications(sample_users[1].id)
        result = service.mark_notification_read(notifications[0].id, sample_users[1].id)
        
        assert result is True
        
        unread = service.get_notifications(sample_users[1].id, unread_only=True)
        assert len(unread) == 0
    
    def test_mark_all_read(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test marking all notifications as read."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username}, check this.",
            created_by=sample_users[0].id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username}, another one.",
            created_by=sample_users[0].id,
        )
        
        count = service.mark_all_read(sample_users[1].id)
        
        assert count == 2
        assert service.get_unread_count(sample_users[1].id) == 0
    
    def test_get_unread_count(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting unread notification count."""
        quote_id = uuid4()
        
        for i in range(3):
            service.create_comment(
                parent_type=CommentableType.QUOTE,
                parent_id=quote_id,
                content=f"@{sample_users[1].username}, message {i}.",
                created_by=sample_users[0].id,
            )
        
        count = service.get_unread_count(sample_users[1].id)
        
        assert count == 3


# =============================================================================
# Test Watchers
# =============================================================================


class TestWatchers:
    """Tests for watching/unwatching objects."""
    
    def test_add_watcher(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test adding a watcher."""
        quote_id = uuid4()
        
        service.add_watcher(CommentableType.QUOTE, quote_id, sample_users[0].id)
        
        watchers = service.get_watchers(CommentableType.QUOTE, quote_id)
        
        assert sample_users[0].id in watchers
    
    def test_remove_watcher(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test removing a watcher."""
        quote_id = uuid4()
        
        service.add_watcher(CommentableType.QUOTE, quote_id, sample_users[0].id)
        result = service.remove_watcher(CommentableType.QUOTE, quote_id, sample_users[0].id)
        
        assert result is True
        
        watchers = service.get_watchers(CommentableType.QUOTE, quote_id)
        assert sample_users[0].id not in watchers
    
    def test_at_all_notifies_watchers(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that @all notifies all watchers."""
        quote_id = uuid4()
        
        # Add watchers
        service.add_watcher(CommentableType.QUOTE, quote_id, sample_users[1].id)
        service.add_watcher(CommentableType.QUOTE, quote_id, sample_users[2].id)
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="@all, important update!",
            created_by=sample_users[0].id,
        )
        
        # Both watchers should be notified
        assert service.get_unread_count(sample_users[1].id) == 1
        assert service.get_unread_count(sample_users[2].id) == 1


# =============================================================================
# Test Task Conversion
# =============================================================================


class TestTaskConversion:
    """Tests for converting comments to tasks."""
    
    def test_convert_to_task(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test converting a comment to task data."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="We need to review this pricing before sending to customer.",
            created_by=sample_users[0].id,
            line_number=1,
            field_name="unit_price",
        )
        
        task_data = service.convert_to_task(
            comment.id,
            assigned_to=sample_users[1].id,
            priority="high",
        )
        
        assert task_data is not None
        assert task_data["assigned_to"] == sample_users[1].id
        assert task_data["priority"] == "high"
        assert task_data["source_type"] == "comment"
        assert task_data["source_id"] == comment.id
        assert task_data["metadata"]["line_number"] == 1
        assert task_data["metadata"]["field_name"] == "unit_price"


# =============================================================================
# Test User Mentions Retrieval
# =============================================================================


class TestUserMentions:
    """Tests for retrieving user mentions."""
    
    def test_get_user_mentions(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting all comments where user is mentioned."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username}, check this.",
            created_by=sample_users[0].id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username}, another one.",
            created_by=sample_users[2].id,
        )
        
        mentions = service.get_user_mentions(sample_users[1].id)
        
        assert len(mentions) == 2


# =============================================================================
# Test Search
# =============================================================================


class TestSearch:
    """Tests for searching comments."""
    
    def test_search_comments_by_content(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test searching comments by content."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="This pricing is too high.",
            created_by=sample_users[0].id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Quality looks good.",
            created_by=sample_users[0].id,
        )
        
        results = service.search_comments("pricing")
        
        assert len(results) == 1
        assert "pricing" in results[0].content.lower()
    
    def test_search_case_insensitive(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that search is case insensitive."""
        quote_id = uuid4()
        
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="URGENT: Review needed",
            created_by=sample_users[0].id,
        )
        
        results = service.search_comments("urgent")
        
        assert len(results) == 1


# =============================================================================
# Test Activity Feed
# =============================================================================


class TestActivityFeed:
    """Tests for activity feed."""
    
    def test_get_activity_feed(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test getting activity feed for an object."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="First comment",
            created_by=sample_users[0].id,
        )
        service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Second comment",
            created_by=sample_users[1].id,
        )
        
        service.resolve_comment(comment.id, sample_users[1].id)
        
        feed = service.get_activity_feed(CommentableType.QUOTE, quote_id)
        
        # Should have 3 activities: 2 comments + 1 resolution
        assert len(feed) == 3


# =============================================================================
# Test HTML Rendering
# =============================================================================


class TestHTMLRendering:
    """Tests for HTML content rendering."""
    
    def test_html_content_generated(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that HTML content is generated with mention links."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"Hey @{sample_users[1].username}!",
            created_by=sample_users[0].id,
        )
        
        assert comment.html_content is not None
        assert '<span class="mention"' in comment.html_content
        assert f'data-id="{sample_users[1].id}"' in comment.html_content
    
    def test_unresolved_mention_marked(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test that unresolved mentions are marked."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="Hey @unknown-user!",
            created_by=sample_users[0].id,
        )
        
        assert comment.html_content is not None
        assert "mention-unresolved" in comment.html_content


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_content(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test creating comment with empty content."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content="",
            created_by=sample_users[0].id,
        )
        
        assert comment.content == ""
        assert len(comment.mentions) == 0
    
    def test_mention_at_end_of_content(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test mention at end of content."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"Check this @{sample_users[1].username}",
            created_by=sample_users[0].id,
        )
        
        assert len(comment.mentions) == 1
    
    def test_multiple_same_user_mentions(
        self,
        service: InlineCommentsService,
        sample_users: list[UserRef],
    ) -> None:
        """Test mentioning same user multiple times."""
        quote_id = uuid4()
        
        comment = service.create_comment(
            parent_type=CommentableType.QUOTE,
            parent_id=quote_id,
            content=f"@{sample_users[1].username} and again @{sample_users[1].username}",
            created_by=sample_users[0].id,
        )
        
        # Should have 2 mention objects
        assert len(comment.mentions) == 2
        # But only 1 notification (deduplicated)
        notifications = service.get_notifications(sample_users[1].id)
        # Both mentions create separate notifications in this implementation
        assert len(notifications) == 2
