"""
Tests for Activity Feed Service.

Tests cover:
- Activity creation
- Feed retrieval and filtering
- Read/unread tracking
- Activity aggregation
- Feed subscriptions
- Digest generation
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.core.activity_feed import (
    Activity,
    ActivityFeedService,
    ActivityPriority,
    ActivityType,
    AggregatedActivity,
    EntityType,
    FeedSubscription,
)


@pytest.fixture
def service() -> ActivityFeedService:
    """Create a fresh service instance."""
    return ActivityFeedService()


@pytest.fixture
def user_id() -> uuid4:
    """Create a consistent user ID."""
    return uuid4()


@pytest.fixture
def target_id() -> uuid4:
    """Create a consistent target ID."""
    return uuid4()


class TestActivityCreation:
    """Tests for activity creation."""
    
    def test_create_basic_activity(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test creating a basic activity."""
        activity = service.create_activity(
            activity_type=ActivityType.CREATED,
            actor_id=uuid4(),
            actor_name="John Doe",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            title="John Doe created RFQ 'RFQ-001'",
        )
        
        assert activity.id is not None
        assert activity.activity_type == ActivityType.CREATED
        assert activity.title == "John Doe created RFQ 'RFQ-001'"
        assert activity.actor is not None
        assert activity.actor.name == "John Doe"
        assert activity.target is not None
        assert activity.target.name == "RFQ-001"
    
    def test_create_activity_with_metadata(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test creating activity with metadata."""
        activity = service.create_activity(
            activity_type=ActivityType.UPDATED,
            actor_id=uuid4(),
            actor_name="Jane Doe",
            target_id=uuid4(),
            target_type=EntityType.TASK,
            target_name="Task-001",
            title="Jane Doe updated Task-001",
            metadata={
                "field_name": "status",
                "old_value": "pending",
                "new_value": "in_progress",
            },
        )
        
        assert activity.metadata is not None
        assert activity.metadata.field_name == "status"
        assert activity.metadata.old_value == "pending"
        assert activity.metadata.new_value == "in_progress"
    
    def test_create_activity_with_mentions(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test creating activity with user mentions."""
        mentioned_user = uuid4()
        
        activity = service.create_activity(
            activity_type=ActivityType.COMMENTED,
            actor_id=uuid4(),
            actor_name="John Doe",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            title="John Doe commented on RFQ-001",
            metadata={
                "comment_preview": "Hey @Jane, can you review this?",
                "mentioned_user_ids": [mentioned_user],
            },
        )
        
        assert activity.metadata is not None
        assert mentioned_user in activity.metadata.mentioned_user_ids
    
    def test_log_created(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_created helper."""
        activity = service.log_created(
            actor_id=uuid4(),
            actor_name="John Doe",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        assert activity.activity_type == ActivityType.CREATED
        assert "created" in activity.title.lower()
    
    def test_log_updated(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_updated helper with field tracking."""
        activity = service.log_updated(
            actor_id=uuid4(),
            actor_name="Jane Doe",
            target_id=uuid4(),
            target_type=EntityType.WORK_ORDER,
            target_name="WO-001",
            field_name="quantity",
            old_value=100,
            new_value=150,
        )
        
        assert activity.activity_type == ActivityType.UPDATED
        assert activity.metadata.field_name == "quantity"
        assert activity.metadata.old_value == 100
        assert activity.metadata.new_value == 150
    
    def test_log_status_changed(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_status_changed helper."""
        activity = service.log_status_changed(
            actor_id=uuid4(),
            actor_name="John Doe",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            old_status="draft",
            new_status="submitted",
        )
        
        assert activity.activity_type == ActivityType.STATUS_CHANGED
        assert activity.priority == ActivityPriority.HIGH
        assert "submitted" in activity.title
    
    def test_log_assigned(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_assigned helper."""
        assignee_id = uuid4()
        
        activity = service.log_assigned(
            actor_id=uuid4(),
            actor_name="Manager",
            target_id=uuid4(),
            target_type=EntityType.TASK,
            target_name="Task-001",
            assignee_id=assignee_id,
            assignee_name="John Doe",
        )
        
        assert activity.activity_type == ActivityType.ASSIGNED
        assert assignee_id in activity.notify_users
        assert "John Doe" in activity.title
    
    def test_log_commented(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_commented helper."""
        mentioned = uuid4()
        
        activity = service.log_commented(
            actor_id=uuid4(),
            actor_name="John Doe",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            comment_preview="This looks good to me",
            mentioned_user_ids=[mentioned],
        )
        
        assert activity.activity_type == ActivityType.COMMENTED
        assert mentioned in activity.notify_users
    
    def test_log_attachment_added(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_attachment_added helper."""
        activity = service.log_attachment_added(
            actor_id=uuid4(),
            actor_name="John Doe",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            file_name="drawing.pdf",
            file_size=1024000,
        )
        
        assert activity.activity_type == ActivityType.ATTACHMENT_ADDED
        assert activity.metadata.file_name == "drawing.pdf"
        assert activity.metadata.file_size == 1024000
    
    def test_log_approved(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_approved helper."""
        activity = service.log_approved(
            actor_id=uuid4(),
            actor_name="Manager",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        assert activity.activity_type == ActivityType.APPROVED
        assert activity.priority == ActivityPriority.HIGH
    
    def test_log_rejected(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test log_rejected helper."""
        activity = service.log_rejected(
            actor_id=uuid4(),
            actor_name="Manager",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
            reason="Price too high",
        )
        
        assert activity.activity_type == ActivityType.REJECTED
        assert activity.description == "Price too high"


class TestFeedRetrieval:
    """Tests for feed retrieval."""
    
    def test_get_activity_by_id(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test retrieving activity by ID."""
        activity = service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        
        retrieved = service.get_activity(activity.id)
        
        assert retrieved is not None
        assert retrieved.id == activity.id
    
    def test_get_nonexistent_activity(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test retrieving non-existent activity."""
        result = service.get_activity(uuid4())
        assert result is None
    
    def test_get_feed_all(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test getting all activities."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        feed = service.get_feed()
        
        assert len(feed) == 2
    
    def test_get_feed_by_entity(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test filtering feed by entity."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_updated(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Bob",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        feed = service.get_feed(entity_id=target_id)
        
        assert len(feed) == 2
    
    def test_get_feed_by_entity_type(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test filtering feed by entity type."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Bob",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        rfq_feed = service.get_feed(entity_type=EntityType.RFQ)
        
        assert len(rfq_feed) == 2
    
    def test_get_feed_by_activity_type(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test filtering feed by activity type."""
        target = uuid4()
        
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_updated(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=target,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_commented(
            actor_id=uuid4(),
            actor_name="Bob",
            target_id=target,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            comment_preview="Looks good",
        )
        
        comments = service.get_feed(activity_types=[ActivityType.COMMENTED])
        
        assert len(comments) == 1
        assert comments[0].activity_type == ActivityType.COMMENTED
    
    def test_get_feed_by_time_range(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test filtering feed by time range."""
        now = datetime.now(timezone.utc)
        
        a1 = service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        a1.created_at = now - timedelta(hours=2)
        
        a2 = service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
        )
        
        recent = service.get_feed(since=now - timedelta(hours=1))
        
        assert len(recent) == 1
        assert recent[0].id == a2.id
    
    def test_get_feed_pagination(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test feed pagination."""
        for i in range(10):
            service.log_created(
                actor_id=uuid4(),
                actor_name="User",
                target_id=uuid4(),
                target_type=EntityType.RFQ,
                target_name=f"RFQ-{i:03d}",
            )
        
        page1 = service.get_feed(limit=5, offset=0)
        page2 = service.get_feed(limit=5, offset=5)
        
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id
    
    def test_get_entity_feed(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test getting feed for specific entity."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        
        feed = service.get_entity_feed(target_id)
        
        assert len(feed) == 1
    
    def test_get_actor_activities(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test getting activities by actor."""
        actor_id = uuid4()
        
        service.log_created(
            actor_id=actor_id,
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=actor_id,
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
        )
        
        activities = service.get_actor_activities(actor_id)
        
        assert len(activities) == 2
    
    def test_get_mentions(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test getting activities with mentions."""
        service.log_commented(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            comment_preview="Hey @user",
            mentioned_user_ids=[user_id],
        )
        service.log_commented(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
            comment_preview="No mentions here",
        )
        
        mentions = service.get_mentions(user_id)
        
        assert len(mentions) == 1


class TestReadStatus:
    """Tests for read/unread tracking."""
    
    def test_mark_read(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test marking activity as read."""
        activity = service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        
        assert not activity.is_read_by(user_id)
        
        result = service.mark_read(activity.id, user_id)
        
        assert result is True
        assert activity.is_read_by(user_id)
    
    def test_mark_read_nonexistent(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test marking non-existent activity as read."""
        result = service.mark_read(uuid4(), user_id)
        assert result is False
    
    def test_mark_all_read(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test marking all activities as read."""
        for i in range(5):
            service.log_created(
                actor_id=uuid4(),
                actor_name="User",
                target_id=uuid4(),
                target_type=EntityType.RFQ,
                target_name=f"RFQ-{i}",
            )
        
        count = service.mark_all_read(user_id)
        
        assert count == 5
    
    def test_mark_all_read_for_entity(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
        target_id: uuid4,
    ) -> None:
        """Test marking all activities for entity as read."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_updated(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Bob",
            target_id=uuid4(),
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        count = service.mark_all_read(user_id, entity_id=target_id)
        
        assert count == 2
    
    def test_get_unread_count(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test getting unread count."""
        a1 = service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
        )
        
        service.mark_read(a1.id, user_id)
        
        unread = service.get_unread_count(user_id)
        
        assert unread == 1
    
    def test_get_feed_unread_only(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test filtering feed by unread only."""
        a1 = service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
        )
        
        service.mark_read(a1.id, user_id)
        
        unread_feed = service.get_feed(user_id=user_id, unread_only=True)
        
        assert len(unread_feed) == 1


class TestAggregation:
    """Tests for activity aggregation."""
    
    def test_aggregate_similar_activities(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test aggregating similar activities."""
        for i in range(5):
            service.log_updated(
                actor_id=uuid4(),
                actor_name=f"User {i}",
                target_id=target_id,
                target_type=EntityType.RFQ,
                target_name="RFQ-001",
            )
        
        aggregated = service.get_aggregated_feed(entity_id=target_id)
        
        # Should be aggregated into one
        assert len(aggregated) == 1
        assert isinstance(aggregated[0], AggregatedActivity)
        assert aggregated[0].count == 5
    
    def test_aggregated_activity_title(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test aggregated activity title generation."""
        # Same actor
        actor_id = uuid4()
        for _ in range(3):
            service.log_updated(
                actor_id=actor_id,
                actor_name="John Doe",
                target_id=target_id,
                target_type=EntityType.RFQ,
                target_name="RFQ-001",
            )
        
        aggregated = service.get_aggregated_feed(entity_id=target_id)
        
        assert len(aggregated) == 1
        assert isinstance(aggregated[0], AggregatedActivity)
        assert "John Doe" in aggregated[0].title
        assert "3 changes" in aggregated[0].title
    
    def test_no_aggregation_single_activity(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test that single activities are not aggregated."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        
        aggregated = service.get_aggregated_feed(entity_id=target_id)
        
        assert len(aggregated) == 1
        assert isinstance(aggregated[0], Activity)
    
    def test_different_activity_types_not_aggregated(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test that different activity types are not aggregated."""
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_updated(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_commented(
            actor_id=uuid4(),
            actor_name="Bob",
            target_id=target_id,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            comment_preview="Nice",
        )
        
        aggregated = service.get_aggregated_feed(entity_id=target_id)
        
        # Each type should be separate
        assert len(aggregated) == 3


class TestSubscriptions:
    """Tests for feed subscriptions."""
    
    def test_subscribe_to_entity(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
        target_id: uuid4,
    ) -> None:
        """Test subscribing to an entity."""
        subscription = service.subscribe(
            user_id=user_id,
            entity_id=target_id,
            entity_type=EntityType.RFQ,
        )
        
        assert subscription.id is not None
        assert subscription.user_id == user_id
        assert subscription.entity_id == target_id
    
    def test_subscribe_with_settings(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
        target_id: uuid4,
    ) -> None:
        """Test subscribing with notification settings."""
        subscription = service.subscribe(
            user_id=user_id,
            entity_id=target_id,
            entity_type=EntityType.RFQ,
            notify_on_update=True,
            notify_on_comment=True,
            notify_on_status_change=True,
            notify_on_assignment=False,
            email_digest=True,
            digest_frequency="weekly",
        )
        
        assert subscription.notify_on_update is True
        assert subscription.notify_on_assignment is False
        assert subscription.email_digest is True
        assert subscription.digest_frequency == "weekly"
    
    def test_update_existing_subscription(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
        target_id: uuid4,
    ) -> None:
        """Test updating existing subscription."""
        sub1 = service.subscribe(
            user_id=user_id,
            entity_id=target_id,
            entity_type=EntityType.RFQ,
            email_digest=False,
        )
        
        sub2 = service.subscribe(
            user_id=user_id,
            entity_id=target_id,
            entity_type=EntityType.RFQ,
            email_digest=True,
        )
        
        assert sub1.id == sub2.id
        assert sub2.email_digest is True
    
    def test_unsubscribe(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
        target_id: uuid4,
    ) -> None:
        """Test unsubscribing from an entity."""
        service.subscribe(
            user_id=user_id,
            entity_id=target_id,
            entity_type=EntityType.RFQ,
        )
        
        assert service.is_subscribed(user_id, target_id)
        
        result = service.unsubscribe(user_id, target_id)
        
        assert result is True
        assert not service.is_subscribed(user_id, target_id)
    
    def test_unsubscribe_nonexistent(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test unsubscribing from non-subscribed entity."""
        result = service.unsubscribe(user_id, uuid4())
        assert result is False
    
    def test_get_subscription(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
        target_id: uuid4,
    ) -> None:
        """Test getting subscription."""
        service.subscribe(
            user_id=user_id,
            entity_id=target_id,
            entity_type=EntityType.RFQ,
        )
        
        subscription = service.get_subscription(user_id, target_id)
        
        assert subscription is not None
        assert subscription.user_id == user_id
    
    def test_get_user_subscriptions(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test getting all user subscriptions."""
        service.subscribe(user_id=user_id, entity_id=uuid4(), entity_type=EntityType.RFQ)
        service.subscribe(user_id=user_id, entity_id=uuid4(), entity_type=EntityType.QUOTE)
        service.subscribe(user_id=user_id, entity_id=uuid4(), entity_type=EntityType.TASK)
        
        subscriptions = service.get_user_subscriptions(user_id)
        
        assert len(subscriptions) == 3
    
    def test_get_entity_subscribers(
        self,
        service: ActivityFeedService,
        target_id: uuid4,
    ) -> None:
        """Test getting all entity subscribers."""
        service.subscribe(user_id=uuid4(), entity_id=target_id, entity_type=EntityType.RFQ)
        service.subscribe(user_id=uuid4(), entity_id=target_id, entity_type=EntityType.RFQ)
        service.subscribe(user_id=uuid4(), entity_id=target_id, entity_type=EntityType.RFQ)
        
        subscribers = service.get_entity_subscribers(target_id)
        
        assert len(subscribers) == 3
    
    def test_get_user_feed_with_subscriptions(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test getting personalized feed based on subscriptions."""
        target1 = uuid4()
        target2 = uuid4()
        
        service.subscribe(user_id=user_id, entity_id=target1, entity_type=EntityType.RFQ)
        
        # Activity on subscribed entity
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target1,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        
        # Activity on unsubscribed entity
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=target2,
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        feed = service.get_user_feed(user_id)
        
        assert len(feed) == 1
        assert feed[0].target.id == target1


class TestDigest:
    """Tests for digest generation."""
    
    def test_generate_daily_digest(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test generating daily digest."""
        target = uuid4()
        
        service.subscribe(
            user_id=user_id,
            entity_id=target,
            entity_type=EntityType.RFQ,
            email_digest=True,
            digest_frequency="daily",
        )
        
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_updated(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=target,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        
        digest = service.generate_digest(user_id, period="daily")
        
        assert digest["user_id"] == user_id
        assert digest["period"] == "daily"
        assert digest["summary"]["total_activities"] == 2
        assert len(digest["top_activities"]) == 2
    
    def test_digest_excludes_non_subscribed(
        self,
        service: ActivityFeedService,
        user_id: uuid4,
    ) -> None:
        """Test that digest excludes non-subscribed entities."""
        target = uuid4()
        other = uuid4()
        
        service.subscribe(
            user_id=user_id,
            entity_id=target,
            entity_type=EntityType.RFQ,
            email_digest=True,
            digest_frequency="daily",
        )
        
        service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=target,
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=other,
            target_type=EntityType.QUOTE,
            target_name="Quote-001",
        )
        
        digest = service.generate_digest(user_id, period="daily")
        
        assert digest["summary"]["total_activities"] == 1


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_activity_without_group_key(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test activity without explicit group key."""
        activity = service.create_activity(
            activity_type=ActivityType.CREATED,
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
            title="Created RFQ",
        )
        
        # Should auto-generate group key
        assert activity.group_key is not None
        assert "rfq" in activity.group_key.lower()
    
    def test_is_read_by_method(self) -> None:
        """Test Activity.is_read_by method."""
        activity = Activity(
            activity_type=ActivityType.CREATED,
            title="Test",
        )
        user = uuid4()
        
        assert activity.is_read_by(user) is False
        
        activity.mark_read(user)
        
        assert activity.is_read_by(user) is True
    
    def test_feed_sorted_by_created_at(
        self,
        service: ActivityFeedService,
    ) -> None:
        """Test that feed is sorted by created_at descending."""
        a1 = service.log_created(
            actor_id=uuid4(),
            actor_name="John",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-001",
        )
        a1.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        a2 = service.log_created(
            actor_id=uuid4(),
            actor_name="Jane",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-002",
        )
        a2.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        a3 = service.log_created(
            actor_id=uuid4(),
            actor_name="Bob",
            target_id=uuid4(),
            target_type=EntityType.RFQ,
            target_name="RFQ-003",
        )
        
        feed = service.get_feed()
        
        assert feed[0].id == a3.id  # Most recent first
        assert feed[1].id == a2.id
        assert feed[2].id == a1.id
