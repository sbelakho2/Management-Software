"""
Activity Feed Service.

Provides a real-time activity feed showing recent actions across
the system. Supports filtering by entity type, user, and time range.

Features:
- Activity event creation and storage
- Multiple entity type support
- User-specific activity tracking
- Activity aggregation (e.g., "5 items updated")
- Read/unread tracking
- Feed pagination
- Filtering by type, entity, user, time
- Activity digest generation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class ActivityType(str, Enum):
    """Types of activities that can be tracked."""
    
    # Entity lifecycle
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ARCHIVED = "archived"
    RESTORED = "restored"
    
    # Status changes
    STATUS_CHANGED = "status_changed"
    STAGE_CHANGED = "stage_changed"
    PRIORITY_CHANGED = "priority_changed"
    
    # Assignment
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    REASSIGNED = "reassigned"
    
    # Comments and communication
    COMMENTED = "commented"
    MENTIONED = "mentioned"
    REPLIED = "replied"
    
    # Attachments
    ATTACHMENT_ADDED = "attachment_added"
    ATTACHMENT_REMOVED = "attachment_removed"
    
    # Approvals
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAIVED = "waived"
    
    # Reviews
    REVIEWED = "reviewed"
    ESCALATED = "escalated"
    
    # Links and relations
    LINKED = "linked"
    UNLINKED = "unlinked"
    
    # Custom
    CUSTOM = "custom"


class EntityType(str, Enum):
    """Types of entities that can have activities."""
    
    RFQ = "rfq"
    QUOTE = "quote"
    WORK_ORDER = "work_order"
    TASK = "task"
    PRODUCT = "product"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    USER = "user"
    RISK = "risk"
    QUALITY_ISSUE = "quality_issue"
    CAPA = "capa"
    A3 = "a3"
    NPI_PROJECT = "npi_project"
    CHECKLIST = "checklist"
    TRAINING = "training"
    DOCUMENT = "document"
    COMMENT = "comment"
    ATTACHMENT = "attachment"


class ActivityPriority(str, Enum):
    """Priority levels for activities."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ActivityActor:
    """The user or system that performed the activity."""
    
    id: UUID
    name: str
    email: str | None = None
    avatar_url: str | None = None
    is_system: bool = False


@dataclass
class ActivityTarget:
    """The entity affected by the activity."""
    
    id: UUID
    entity_type: EntityType
    name: str
    url: str | None = None
    parent_id: UUID | None = None
    parent_type: EntityType | None = None


@dataclass
class ActivityMetadata:
    """Additional metadata about the activity."""
    
    # Field changes
    field_name: str | None = None
    old_value: Any = None
    new_value: Any = None
    
    # Related entities
    related_entity_id: UUID | None = None
    related_entity_type: EntityType | None = None
    related_entity_name: str | None = None
    
    # Attachment info
    file_name: str | None = None
    file_size: int | None = None
    
    # Comment/mention info
    comment_preview: str | None = None
    mentioned_user_ids: list[UUID] = field(default_factory=list)
    
    # Custom data
    custom_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Activity:
    """An activity event in the feed."""
    
    id: UUID = field(default_factory=uuid4)
    
    # Activity details
    activity_type: ActivityType = ActivityType.UPDATED
    priority: ActivityPriority = ActivityPriority.NORMAL
    
    # Actor (who did it)
    actor: ActivityActor | None = None
    
    # Target (what was affected)
    target: ActivityTarget | None = None
    
    # Description
    title: str = ""  # Human-readable title
    description: str | None = None  # Optional detailed description
    
    # Metadata
    metadata: ActivityMetadata | None = None
    
    # Grouping
    group_key: str | None = None  # For aggregating similar activities
    
    # Visibility
    is_public: bool = True  # Visible to all with access to target
    notify_users: list[UUID] = field(default_factory=list)  # Users to notify
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Read status (per user)
    read_by: dict[UUID, datetime] = field(default_factory=dict)
    
    def is_read_by(self, user_id: UUID) -> bool:
        """Check if user has read this activity."""
        return user_id in self.read_by
    
    def mark_read(self, user_id: UUID) -> None:
        """Mark activity as read by user."""
        if user_id not in self.read_by:
            self.read_by[user_id] = datetime.now(timezone.utc)


@dataclass
class AggregatedActivity:
    """Multiple similar activities grouped together."""
    
    group_key: str
    activity_type: ActivityType
    target_type: EntityType
    count: int
    activities: list[Activity]
    first_at: datetime
    last_at: datetime
    actors: list[ActivityActor]
    
    @property
    def title(self) -> str:
        """Generate aggregated title."""
        if self.count == 1:
            return self.activities[0].title
        
        actor_names = list({a.name for a in self.actors})
        if len(actor_names) == 1:
            return f"{actor_names[0]} made {self.count} changes"
        elif len(actor_names) == 2:
            return f"{actor_names[0]} and {actor_names[1]} made {self.count} changes"
        else:
            return f"{actor_names[0]} and {len(actor_names) - 1} others made {self.count} changes"


@dataclass
class FeedSubscription:
    """A user's subscription to an entity's activity feed."""
    
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    entity_id: UUID = field(default_factory=uuid4)
    entity_type: EntityType = EntityType.RFQ
    
    # Notification settings
    notify_on_update: bool = True
    notify_on_comment: bool = True
    notify_on_status_change: bool = True
    notify_on_assignment: bool = True
    
    # Email digest
    email_digest: bool = False
    digest_frequency: str = "daily"  # daily, weekly
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ActivityFeedService:
    """
    Service for managing activity feeds.
    
    Provides creation, retrieval, aggregation, and subscription
    management for activity events.
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._activities: dict[UUID, Activity] = {}
        self._subscriptions: dict[UUID, FeedSubscription] = {}
        # Index for quick lookups
        self._by_target: dict[UUID, list[UUID]] = {}
        self._by_actor: dict[UUID, list[UUID]] = {}
        self._by_user_mentions: dict[UUID, list[UUID]] = {}
    
    # ---------------------
    # Activity Creation
    # ---------------------
    
    def create_activity(
        self,
        activity_type: ActivityType,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        title: str,
        description: str | None = None,
        priority: ActivityPriority = ActivityPriority.NORMAL,
        actor_email: str | None = None,
        target_url: str | None = None,
        parent_id: UUID | None = None,
        parent_type: EntityType | None = None,
        metadata: dict[str, Any] | None = None,
        group_key: str | None = None,
        is_public: bool = True,
        notify_users: list[UUID] | None = None,
        is_system: bool = False,
    ) -> Activity:
        """Create a new activity event."""
        actor = ActivityActor(
            id=actor_id,
            name=actor_name,
            email=actor_email,
            is_system=is_system,
        )
        
        target = ActivityTarget(
            id=target_id,
            entity_type=target_type,
            name=target_name,
            url=target_url,
            parent_id=parent_id,
            parent_type=parent_type,
        )
        
        activity_metadata = None
        mentioned_users: list[UUID] = []
        
        if metadata:
            mentioned_users = metadata.get("mentioned_user_ids", [])
            activity_metadata = ActivityMetadata(
                field_name=metadata.get("field_name"),
                old_value=metadata.get("old_value"),
                new_value=metadata.get("new_value"),
                related_entity_id=metadata.get("related_entity_id"),
                related_entity_type=metadata.get("related_entity_type"),
                related_entity_name=metadata.get("related_entity_name"),
                file_name=metadata.get("file_name"),
                file_size=metadata.get("file_size"),
                comment_preview=metadata.get("comment_preview"),
                mentioned_user_ids=mentioned_users,
                custom_data=metadata.get("custom_data", {}),
            )
        
        activity = Activity(
            activity_type=activity_type,
            priority=priority,
            actor=actor,
            target=target,
            title=title,
            description=description,
            metadata=activity_metadata,
            group_key=group_key or f"{target_type.value}:{target_id}",
            is_public=is_public,
            notify_users=notify_users or [],
        )
        
        self._activities[activity.id] = activity
        
        # Update indexes
        if target_id not in self._by_target:
            self._by_target[target_id] = []
        self._by_target[target_id].append(activity.id)
        
        if actor_id not in self._by_actor:
            self._by_actor[actor_id] = []
        self._by_actor[actor_id].append(activity.id)
        
        for user_id in mentioned_users:
            if user_id not in self._by_user_mentions:
                self._by_user_mentions[user_id] = []
            self._by_user_mentions[user_id].append(activity.id)
        
        return activity
    
    def log_created(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        **kwargs: Any,
    ) -> Activity:
        """Log entity creation."""
        return self.create_activity(
            activity_type=ActivityType.CREATED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} created {target_type.value} '{target_name}'",
            **kwargs,
        )
    
    def log_updated(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        field_name: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        **kwargs: Any,
    ) -> Activity:
        """Log entity update."""
        metadata = kwargs.pop("metadata", {}) or {}
        if field_name:
            metadata["field_name"] = field_name
            metadata["old_value"] = old_value
            metadata["new_value"] = new_value
        
        title = f"{actor_name} updated {target_type.value} '{target_name}'"
        if field_name:
            title = f"{actor_name} changed {field_name} on '{target_name}'"
        
        return self.create_activity(
            activity_type=ActivityType.UPDATED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=title,
            metadata=metadata,
            **kwargs,
        )
    
    def log_status_changed(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        old_status: str,
        new_status: str,
        **kwargs: Any,
    ) -> Activity:
        """Log status change."""
        return self.create_activity(
            activity_type=ActivityType.STATUS_CHANGED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} changed status to '{new_status}'",
            priority=ActivityPriority.HIGH,
            metadata={
                "field_name": "status",
                "old_value": old_status,
                "new_value": new_status,
            },
            **kwargs,
        )
    
    def log_assigned(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        assignee_id: UUID,
        assignee_name: str,
        **kwargs: Any,
    ) -> Activity:
        """Log assignment."""
        return self.create_activity(
            activity_type=ActivityType.ASSIGNED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} assigned '{target_name}' to {assignee_name}",
            notify_users=[assignee_id],
            metadata={
                "related_entity_id": assignee_id,
                "related_entity_type": EntityType.USER,
                "related_entity_name": assignee_name,
            },
            **kwargs,
        )
    
    def log_commented(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        comment_preview: str,
        mentioned_user_ids: list[UUID] | None = None,
        **kwargs: Any,
    ) -> Activity:
        """Log comment."""
        return self.create_activity(
            activity_type=ActivityType.COMMENTED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} commented on '{target_name}'",
            notify_users=mentioned_user_ids or [],
            metadata={
                "comment_preview": comment_preview[:200] if comment_preview else None,
                "mentioned_user_ids": mentioned_user_ids or [],
            },
            **kwargs,
        )
    
    def log_attachment_added(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        file_name: str,
        file_size: int | None = None,
        **kwargs: Any,
    ) -> Activity:
        """Log attachment added."""
        return self.create_activity(
            activity_type=ActivityType.ATTACHMENT_ADDED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} added '{file_name}' to '{target_name}'",
            metadata={
                "file_name": file_name,
                "file_size": file_size,
            },
            **kwargs,
        )
    
    def log_approved(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        **kwargs: Any,
    ) -> Activity:
        """Log approval."""
        return self.create_activity(
            activity_type=ActivityType.APPROVED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} approved '{target_name}'",
            priority=ActivityPriority.HIGH,
            **kwargs,
        )
    
    def log_rejected(
        self,
        actor_id: UUID,
        actor_name: str,
        target_id: UUID,
        target_type: EntityType,
        target_name: str,
        reason: str | None = None,
        **kwargs: Any,
    ) -> Activity:
        """Log rejection."""
        return self.create_activity(
            activity_type=ActivityType.REJECTED,
            actor_id=actor_id,
            actor_name=actor_name,
            target_id=target_id,
            target_type=target_type,
            target_name=target_name,
            title=f"{actor_name} rejected '{target_name}'",
            description=reason,
            priority=ActivityPriority.HIGH,
            **kwargs,
        )
    
    # ---------------------
    # Activity Retrieval
    # ---------------------
    
    def get_activity(self, activity_id: UUID) -> Activity | None:
        """Get an activity by ID."""
        return self._activities.get(activity_id)
    
    def get_feed(
        self,
        user_id: UUID | None = None,
        entity_id: UUID | None = None,
        entity_type: EntityType | None = None,
        activity_types: list[ActivityType] | None = None,
        priority: ActivityPriority | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
    ) -> list[Activity]:
        """Get activity feed with filters."""
        activities = list(self._activities.values())
        
        # Filter by entity
        if entity_id:
            activity_ids = self._by_target.get(entity_id, [])
            activities = [
                a for a in activities if a.id in activity_ids
            ]
        
        # Filter by entity type
        if entity_type:
            activities = [
                a for a in activities
                if a.target and a.target.entity_type == entity_type
            ]
        
        # Filter by activity types
        if activity_types:
            activities = [
                a for a in activities
                if a.activity_type in activity_types
            ]
        
        # Filter by priority
        if priority:
            activities = [
                a for a in activities
                if a.priority == priority
            ]
        
        # Filter by time
        if since:
            activities = [a for a in activities if a.created_at >= since]
        
        if until:
            activities = [a for a in activities if a.created_at <= until]
        
        # Filter by unread (requires user_id)
        if unread_only and user_id:
            activities = [
                a for a in activities
                if not a.is_read_by(user_id)
            ]
        
        # Sort by created_at descending (newest first)
        activities.sort(key=lambda a: a.created_at, reverse=True)
        
        # Paginate
        return activities[offset : offset + limit]
    
    def get_entity_feed(
        self,
        entity_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Activity]:
        """Get activity feed for a specific entity."""
        return self.get_feed(
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )
    
    def get_user_feed(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        include_mentions: bool = True,
    ) -> list[Activity]:
        """Get personalized feed for a user."""
        # Get user's subscriptions
        subscriptions = self.get_user_subscriptions(user_id)
        subscribed_entities = {s.entity_id for s in subscriptions}
        
        # Get activities for subscribed entities
        activities = []
        for entity_id in subscribed_entities:
            entity_activities = self.get_entity_feed(entity_id, limit=limit)
            activities.extend(entity_activities)
        
        # Add mentions
        if include_mentions:
            mention_ids = self._by_user_mentions.get(user_id, [])
            for activity_id in mention_ids:
                activity = self._activities.get(activity_id)
                if activity and activity not in activities:
                    activities.append(activity)
        
        # Sort and paginate
        activities.sort(key=lambda a: a.created_at, reverse=True)
        return activities[offset : offset + limit]
    
    def get_actor_activities(
        self,
        actor_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Activity]:
        """Get activities by a specific actor."""
        activity_ids = self._by_actor.get(actor_id, [])
        activities = [
            self._activities[aid]
            for aid in activity_ids
            if aid in self._activities
        ]
        activities.sort(key=lambda a: a.created_at, reverse=True)
        return activities[offset : offset + limit]
    
    def get_mentions(
        self,
        user_id: UUID,
        unread_only: bool = False,
    ) -> list[Activity]:
        """Get activities where user was mentioned."""
        activity_ids = self._by_user_mentions.get(user_id, [])
        activities = [
            self._activities[aid]
            for aid in activity_ids
            if aid in self._activities
        ]
        
        if unread_only:
            activities = [a for a in activities if not a.is_read_by(user_id)]
        
        activities.sort(key=lambda a: a.created_at, reverse=True)
        return activities
    
    # ---------------------
    # Read Status
    # ---------------------
    
    def mark_read(
        self,
        activity_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Mark an activity as read by a user."""
        activity = self._activities.get(activity_id)
        if not activity:
            return False
        
        activity.mark_read(user_id)
        return True
    
    def mark_all_read(
        self,
        user_id: UUID,
        entity_id: UUID | None = None,
    ) -> int:
        """Mark all activities as read for a user."""
        count = 0
        
        if entity_id:
            activity_ids = self._by_target.get(entity_id, [])
            activities = [
                self._activities[aid]
                for aid in activity_ids
                if aid in self._activities
            ]
        else:
            activities = list(self._activities.values())
        
        for activity in activities:
            if not activity.is_read_by(user_id):
                activity.mark_read(user_id)
                count += 1
        
        return count
    
    def get_unread_count(
        self,
        user_id: UUID,
        entity_id: UUID | None = None,
    ) -> int:
        """Get count of unread activities for a user."""
        if entity_id:
            activity_ids = self._by_target.get(entity_id, [])
            activities = [
                self._activities[aid]
                for aid in activity_ids
                if aid in self._activities
            ]
        else:
            activities = list(self._activities.values())
        
        return sum(1 for a in activities if not a.is_read_by(user_id))
    
    # ---------------------
    # Aggregation
    # ---------------------
    
    def get_aggregated_feed(
        self,
        entity_id: UUID | None = None,
        time_window_minutes: int = 60,
        limit: int = 20,
    ) -> list[AggregatedActivity | Activity]:
        """Get activity feed with similar activities aggregated."""
        activities = self.get_feed(entity_id=entity_id, limit=200)
        
        if not activities:
            return []
        
        # Group by group_key and activity_type within time window
        groups: dict[str, list[Activity]] = {}
        result: list[AggregatedActivity | Activity] = []
        
        for activity in activities:
            if not activity.group_key:
                result.append(activity)
                continue
            
            key = f"{activity.group_key}:{activity.activity_type.value}"
            
            if key not in groups:
                groups[key] = []
            
            # Check if within time window of first activity in group
            if groups[key]:
                first = groups[key][0]
                delta = abs((activity.created_at - first.created_at).total_seconds())
                if delta > time_window_minutes * 60:
                    # Start new group, finalize old one
                    if len(groups[key]) > 1:
                        result.append(self._create_aggregated(key, groups[key]))
                    else:
                        result.append(groups[key][0])
                    groups[key] = []
            
            groups[key].append(activity)
        
        # Finalize remaining groups
        for key, group_activities in groups.items():
            if len(group_activities) > 1:
                result.append(self._create_aggregated(key, group_activities))
            elif group_activities:
                result.append(group_activities[0])
        
        # Sort by most recent
        result.sort(
            key=lambda x: (
                x.last_at if isinstance(x, AggregatedActivity) else x.created_at
            ),
            reverse=True,
        )
        
        return result[:limit]
    
    def _create_aggregated(
        self,
        group_key: str,
        activities: list[Activity],
    ) -> AggregatedActivity:
        """Create an aggregated activity from a list of activities."""
        activities.sort(key=lambda a: a.created_at)
        
        actors = []
        seen_actors: set[UUID] = set()
        for a in activities:
            if a.actor and a.actor.id not in seen_actors:
                actors.append(a.actor)
                seen_actors.add(a.actor.id)
        
        return AggregatedActivity(
            group_key=group_key,
            activity_type=activities[0].activity_type,
            target_type=activities[0].target.entity_type if activities[0].target else EntityType.RFQ,
            count=len(activities),
            activities=activities,
            first_at=activities[0].created_at,
            last_at=activities[-1].created_at,
            actors=actors,
        )
    
    # ---------------------
    # Subscriptions
    # ---------------------
    
    def subscribe(
        self,
        user_id: UUID,
        entity_id: UUID,
        entity_type: EntityType,
        notify_on_update: bool = True,
        notify_on_comment: bool = True,
        notify_on_status_change: bool = True,
        notify_on_assignment: bool = True,
        email_digest: bool = False,
        digest_frequency: str = "daily",
    ) -> FeedSubscription:
        """Subscribe a user to an entity's activity feed."""
        # Check for existing subscription
        for sub in self._subscriptions.values():
            if sub.user_id == user_id and sub.entity_id == entity_id:
                # Update existing
                sub.notify_on_update = notify_on_update
                sub.notify_on_comment = notify_on_comment
                sub.notify_on_status_change = notify_on_status_change
                sub.notify_on_assignment = notify_on_assignment
                sub.email_digest = email_digest
                sub.digest_frequency = digest_frequency
                return sub
        
        subscription = FeedSubscription(
            user_id=user_id,
            entity_id=entity_id,
            entity_type=entity_type,
            notify_on_update=notify_on_update,
            notify_on_comment=notify_on_comment,
            notify_on_status_change=notify_on_status_change,
            notify_on_assignment=notify_on_assignment,
            email_digest=email_digest,
            digest_frequency=digest_frequency,
        )
        
        self._subscriptions[subscription.id] = subscription
        return subscription
    
    def unsubscribe(
        self,
        user_id: UUID,
        entity_id: UUID,
    ) -> bool:
        """Unsubscribe a user from an entity's activity feed."""
        for sub_id, sub in list(self._subscriptions.items()):
            if sub.user_id == user_id and sub.entity_id == entity_id:
                del self._subscriptions[sub_id]
                return True
        return False
    
    def get_subscription(
        self,
        user_id: UUID,
        entity_id: UUID,
    ) -> FeedSubscription | None:
        """Get a user's subscription to an entity."""
        for sub in self._subscriptions.values():
            if sub.user_id == user_id and sub.entity_id == entity_id:
                return sub
        return None
    
    def is_subscribed(
        self,
        user_id: UUID,
        entity_id: UUID,
    ) -> bool:
        """Check if user is subscribed to an entity."""
        return self.get_subscription(user_id, entity_id) is not None
    
    def get_user_subscriptions(
        self,
        user_id: UUID,
    ) -> list[FeedSubscription]:
        """Get all subscriptions for a user."""
        return [s for s in self._subscriptions.values() if s.user_id == user_id]
    
    def get_entity_subscribers(
        self,
        entity_id: UUID,
    ) -> list[FeedSubscription]:
        """Get all subscribers to an entity."""
        return [s for s in self._subscriptions.values() if s.entity_id == entity_id]
    
    # ---------------------
    # Digest Generation
    # ---------------------
    
    def generate_digest(
        self,
        user_id: UUID,
        since: datetime | None = None,
        period: str = "daily",
    ) -> dict[str, Any]:
        """Generate an activity digest for a user."""
        if since is None:
            if period == "daily":
                since = datetime.now(timezone.utc) - timedelta(days=1)
            else:  # weekly
                since = datetime.now(timezone.utc) - timedelta(weeks=1)
        
        # Get subscriptions with digest enabled
        subscriptions = [
            s for s in self.get_user_subscriptions(user_id)
            if s.email_digest and s.digest_frequency == period
        ]
        
        entity_ids = {s.entity_id for s in subscriptions}
        
        # Get activities for subscribed entities
        all_activities: list[Activity] = []
        for entity_id in entity_ids:
            activities = self.get_feed(
                entity_id=entity_id,
                since=since,
            )
            all_activities.extend(activities)
        
        # Add mentions
        mentions = self.get_mentions(user_id, unread_only=True)
        for mention in mentions:
            if mention.created_at >= since and mention not in all_activities:
                all_activities.append(mention)
        
        # Sort and group by entity
        all_activities.sort(key=lambda a: a.created_at, reverse=True)
        
        by_entity: dict[UUID, list[Activity]] = {}
        for activity in all_activities:
            if activity.target:
                entity_id = activity.target.id
                if entity_id not in by_entity:
                    by_entity[entity_id] = []
                by_entity[entity_id].append(activity)
        
        # Build digest summary
        summary = {
            "total_activities": len(all_activities),
            "high_priority_count": sum(
                1 for a in all_activities
                if a.priority in (ActivityPriority.HIGH, ActivityPriority.URGENT)
            ),
            "mentions_count": len(mentions),
            "entities_updated": len(by_entity),
        }
        
        return {
            "user_id": user_id,
            "period": period,
            "since": since,
            "until": datetime.now(timezone.utc),
            "summary": summary,
            "activities_by_entity": {
                str(k): [
                    {
                        "id": a.id,
                        "type": a.activity_type.value,
                        "title": a.title,
                        "actor": a.actor.name if a.actor else "System",
                        "created_at": a.created_at,
                    }
                    for a in v
                ]
                for k, v in by_entity.items()
            },
            "top_activities": [
                {
                    "id": a.id,
                    "type": a.activity_type.value,
                    "title": a.title,
                    "target": a.target.name if a.target else None,
                    "created_at": a.created_at,
                }
                for a in all_activities[:10]
            ],
        }
