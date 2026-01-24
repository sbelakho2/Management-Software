"""
Inline Comments and Mentions Service.

Provides inline commenting capabilities with @mention functionality
for team collaboration on quotes, line items, and other objects.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class CommentableType(str, Enum):
    """Types of objects that can have comments."""
    
    QUOTE = "quote"
    QUOTE_LINE_ITEM = "quote_line_item"
    QUOTE_VERSION = "quote_version"
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    ACCOUNT = "account"
    CONTACT = "contact"
    PRODUCT = "product"
    WORK_ORDER = "work_order"
    TASK = "task"
    A3 = "a3"
    OBEYA = "obeya"


class CommentStatus(str, Enum):
    """Status of a comment."""
    
    ACTIVE = "active"
    RESOLVED = "resolved"
    DELETED = "deleted"


class MentionType(str, Enum):
    """Types of mentions."""
    
    USER = "user"           # @john.doe
    TEAM = "team"           # @sales-team
    ROLE = "role"           # @approvers
    ALL = "all"             # @all (notify everyone on thread)
    ASSIGNEE = "assignee"   # @assignee (notify current assignee)


class NotificationPriority(str, Enum):
    """Priority level for mention notifications."""
    
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Mention:
    """A mention within a comment."""
    
    id: UUID
    mention_type: MentionType
    target_id: UUID | None  # User ID, Team ID, Role ID (None for @all/@assignee)
    target_identifier: str  # e.g., "john.doe", "sales-team", "approvers"
    start_position: int     # Position in comment text where mention starts
    end_position: int       # Position in comment text where mention ends
    notified: bool = False
    notified_at: datetime | None = None


@dataclass
class CommentReaction:
    """A reaction to a comment (e.g., thumbs up, heart)."""
    
    id: UUID
    comment_id: UUID
    user_id: UUID
    reaction_type: str  # e.g., "👍", "❤️", "✅", "👀"
    created_at: datetime


@dataclass
class Comment:
    """An inline comment on an object."""
    
    id: UUID
    parent_type: CommentableType
    parent_id: UUID
    content: str
    html_content: str | None  # Rendered content with mention links
    created_by: UUID
    created_at: datetime
    updated_at: datetime | None = None
    status: CommentStatus = CommentStatus.ACTIVE
    mentions: list[Mention] = field(default_factory=list)
    reactions: list[CommentReaction] = field(default_factory=list)
    reply_to_id: UUID | None = None  # For threaded comments
    is_pinned: bool = False
    resolved_by: UUID | None = None
    resolved_at: datetime | None = None
    # For line item specific comments
    line_number: int | None = None
    field_name: str | None = None  # e.g., "unit_price", "quantity"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommentThread:
    """A thread of comments."""
    
    root_comment: Comment
    replies: list[Comment] = field(default_factory=list)
    participant_ids: set[UUID] = field(default_factory=set)
    is_resolved: bool = False
    total_replies: int = 0
    last_activity_at: datetime | None = None


@dataclass
class MentionNotification:
    """A notification for a mention."""
    
    id: UUID
    comment_id: UUID
    mention_id: UUID
    recipient_id: UUID
    priority: NotificationPriority
    read: bool = False
    read_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class UserRef:
    """Reference to a user for mention resolution."""
    
    id: UUID
    username: str
    display_name: str
    email: str
    is_active: bool = True


@dataclass
class TeamRef:
    """Reference to a team for mention resolution."""
    
    id: UUID
    name: str
    identifier: str  # e.g., "sales-team"
    member_ids: list[UUID] = field(default_factory=list)


@dataclass
class RoleRef:
    """Reference to a role for mention resolution."""
    
    id: UUID
    name: str
    identifier: str  # e.g., "approvers"
    user_ids: list[UUID] = field(default_factory=list)


class InlineCommentsService:
    """Service for managing inline comments and mentions."""
    
    # Regex pattern to match @mentions
    MENTION_PATTERN = re.compile(r'@([\w.-]+)', re.UNICODE)
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._comments: dict[UUID, Comment] = {}
        self._notifications: dict[UUID, MentionNotification] = {}
        self._users: dict[UUID, UserRef] = {}
        self._users_by_username: dict[str, UserRef] = {}
        self._teams: dict[UUID, TeamRef] = {}
        self._teams_by_identifier: dict[str, TeamRef] = {}
        self._roles: dict[UUID, RoleRef] = {}
        self._roles_by_identifier: dict[str, RoleRef] = {}
        self._object_assignees: dict[tuple[CommentableType, UUID], UUID] = {}
        self._object_watchers: dict[tuple[CommentableType, UUID], set[UUID]] = {}
    
    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._comments.clear()
        self._notifications.clear()
        self._users.clear()
        self._users_by_username.clear()
        self._teams.clear()
        self._teams_by_identifier.clear()
        self._roles.clear()
        self._roles_by_identifier.clear()
        self._object_assignees.clear()
        self._object_watchers.clear()
    
    # =========================================================================
    # User/Team/Role Reference Management
    # =========================================================================
    
    def register_user(self, user: UserRef) -> None:
        """Register a user for mention resolution."""
        self._users[user.id] = user
        self._users_by_username[user.username.lower()] = user
    
    def register_team(self, team: TeamRef) -> None:
        """Register a team for mention resolution."""
        self._teams[team.id] = team
        self._teams_by_identifier[team.identifier.lower()] = team
    
    def register_role(self, role: RoleRef) -> None:
        """Register a role for mention resolution."""
        self._roles[role.id] = role
        self._roles_by_identifier[role.identifier.lower()] = role
    
    def set_assignee(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        assignee_id: UUID,
    ) -> None:
        """Set the assignee for an object (for @assignee mentions)."""
        self._object_assignees[(parent_type, parent_id)] = assignee_id
    
    def add_watcher(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        watcher_id: UUID,
    ) -> None:
        """Add a watcher to an object (for @all mentions)."""
        key = (parent_type, parent_id)
        if key not in self._object_watchers:
            self._object_watchers[key] = set()
        self._object_watchers[key].add(watcher_id)
    
    def remove_watcher(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        watcher_id: UUID,
    ) -> bool:
        """Remove a watcher from an object."""
        key = (parent_type, parent_id)
        if key in self._object_watchers:
            self._object_watchers[key].discard(watcher_id)
            return True
        return False
    
    def get_watchers(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
    ) -> set[UUID]:
        """Get all watchers for an object."""
        key = (parent_type, parent_id)
        return self._object_watchers.get(key, set()).copy()
    
    # =========================================================================
    # Comment Creation
    # =========================================================================
    
    def create_comment(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        content: str,
        created_by: UUID,
        reply_to_id: UUID | None = None,
        line_number: int | None = None,
        field_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Comment:
        """
        Create a new comment with automatic mention parsing.
        
        Args:
            parent_type: Type of object being commented on
            parent_id: ID of the object being commented on
            content: Comment text with @mentions
            created_by: User creating the comment
            reply_to_id: ID of comment being replied to (for threading)
            line_number: Line number for line item comments
            field_name: Field name for field-specific comments
            metadata: Additional metadata
            
        Returns:
            The created comment
        """
        comment_id = uuid4()
        now = datetime.now(timezone.utc)
        
        # Parse mentions from content
        mentions = self._parse_mentions(content)
        
        # Render HTML content with mention links
        html_content = self._render_html_content(content, mentions)
        
        comment = Comment(
            id=comment_id,
            parent_type=parent_type,
            parent_id=parent_id,
            content=content,
            html_content=html_content,
            created_by=created_by,
            created_at=now,
            mentions=mentions,
            reply_to_id=reply_to_id,
            line_number=line_number,
            field_name=field_name,
            metadata=metadata or {},
        )
        
        self._comments[comment_id] = comment
        
        # Create notifications for mentions
        self._create_mention_notifications(comment)
        
        # Auto-add commenter as watcher
        self.add_watcher(parent_type, parent_id, created_by)
        
        return comment
    
    def update_comment(
        self,
        comment_id: UUID,
        content: str,
        updated_by: UUID,
    ) -> Comment | None:
        """
        Update a comment's content.
        
        Only the original author can update. Re-parses mentions.
        """
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        if comment.created_by != updated_by:
            return None  # Only author can edit
        
        if comment.status != CommentStatus.ACTIVE:
            return None  # Can't edit deleted/resolved comments
        
        # Re-parse mentions
        new_mentions = self._parse_mentions(content)
        
        # Find new mentions that weren't in original
        original_targets = {(m.mention_type, m.target_id) for m in comment.mentions}
        new_mention_targets = {(m.mention_type, m.target_id) for m in new_mentions}
        
        comment.content = content
        comment.html_content = self._render_html_content(content, new_mentions)
        comment.mentions = new_mentions
        comment.updated_at = datetime.now(timezone.utc)
        
        # Notify newly mentioned users
        for mention in new_mentions:
            if (mention.mention_type, mention.target_id) not in original_targets:
                self._notify_mention(comment, mention)
        
        return comment
    
    def delete_comment(
        self,
        comment_id: UUID,
        deleted_by: UUID,
        hard_delete: bool = False,
    ) -> bool:
        """
        Delete a comment.
        
        Soft delete by default (marks as deleted).
        Hard delete removes from storage.
        """
        comment = self._comments.get(comment_id)
        if comment is None:
            return False
        
        if hard_delete:
            del self._comments[comment_id]
        else:
            comment.status = CommentStatus.DELETED
        
        return True
    
    def resolve_comment(
        self,
        comment_id: UUID,
        resolved_by: UUID,
    ) -> Comment | None:
        """Mark a comment as resolved."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        comment.status = CommentStatus.RESOLVED
        comment.resolved_by = resolved_by
        comment.resolved_at = datetime.now(timezone.utc)
        
        return comment
    
    def reopen_comment(
        self,
        comment_id: UUID,
    ) -> Comment | None:
        """Reopen a resolved comment."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        if comment.status != CommentStatus.RESOLVED:
            return None
        
        comment.status = CommentStatus.ACTIVE
        comment.resolved_by = None
        comment.resolved_at = None
        
        return comment
    
    def pin_comment(
        self,
        comment_id: UUID,
    ) -> Comment | None:
        """Pin a comment to the top."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        comment.is_pinned = True
        return comment
    
    def unpin_comment(
        self,
        comment_id: UUID,
    ) -> Comment | None:
        """Unpin a comment."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        comment.is_pinned = False
        return comment
    
    # =========================================================================
    # Comment Retrieval
    # =========================================================================
    
    def get_comment(self, comment_id: UUID) -> Comment | None:
        """Get a comment by ID."""
        return self._comments.get(comment_id)
    
    def get_comments_for_object(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        include_resolved: bool = True,
        include_deleted: bool = False,
    ) -> list[Comment]:
        """Get all comments for an object."""
        comments = []
        for comment in self._comments.values():
            if comment.parent_type != parent_type:
                continue
            if comment.parent_id != parent_id:
                continue
            if comment.status == CommentStatus.DELETED and not include_deleted:
                continue
            if comment.status == CommentStatus.RESOLVED and not include_resolved:
                continue
            comments.append(comment)
        
        # Sort: pinned first, then by created_at
        return sorted(
            comments,
            key=lambda c: (not c.is_pinned, c.created_at),
        )
    
    def get_comments_for_line_item(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        line_number: int,
        field_name: str | None = None,
    ) -> list[Comment]:
        """Get comments for a specific line item or field."""
        comments = self.get_comments_for_object(parent_type, parent_id)
        
        filtered = []
        for comment in comments:
            if comment.line_number != line_number:
                continue
            if field_name is not None and comment.field_name != field_name:
                continue
            filtered.append(comment)
        
        return filtered
    
    def get_thread(self, root_comment_id: UUID) -> CommentThread | None:
        """Get a comment thread with all replies."""
        root = self._comments.get(root_comment_id)
        if root is None:
            return None
        
        # Don't return deleted threads
        if root.status == CommentStatus.DELETED:
            return None
        
        # Find all replies
        replies = []
        participants = {root.created_by}
        
        for comment in self._comments.values():
            if comment.reply_to_id == root_comment_id:
                if comment.status != CommentStatus.DELETED:
                    replies.append(comment)
                    participants.add(comment.created_by)
        
        # Sort replies by created_at
        replies.sort(key=lambda c: c.created_at)
        
        last_activity = root.created_at
        if replies:
            last_activity = max(r.created_at for r in replies)
        
        return CommentThread(
            root_comment=root,
            replies=replies,
            participant_ids=participants,
            is_resolved=root.status == CommentStatus.RESOLVED,
            total_replies=len(replies),
            last_activity_at=last_activity,
        )
    
    def get_user_mentions(
        self,
        user_id: UUID,
        unread_only: bool = False,
    ) -> list[tuple[Comment, Mention]]:
        """Get all comments where a user is mentioned."""
        results = []
        
        for comment in self._comments.values():
            if comment.status == CommentStatus.DELETED:
                continue
            
            for mention in comment.mentions:
                is_user_mentioned = False
                
                if mention.mention_type == MentionType.USER:
                    is_user_mentioned = mention.target_id == user_id
                elif mention.mention_type == MentionType.TEAM:
                    team = self._teams.get(mention.target_id) if mention.target_id else None
                    if team and user_id in team.member_ids:
                        is_user_mentioned = True
                elif mention.mention_type == MentionType.ROLE:
                    role = self._roles.get(mention.target_id) if mention.target_id else None
                    if role and user_id in role.user_ids:
                        is_user_mentioned = True
                elif mention.mention_type == MentionType.ALL:
                    key = (comment.parent_type, comment.parent_id)
                    if user_id in self._object_watchers.get(key, set()):
                        is_user_mentioned = True
                elif mention.mention_type == MentionType.ASSIGNEE:
                    key = (comment.parent_type, comment.parent_id)
                    if self._object_assignees.get(key) == user_id:
                        is_user_mentioned = True
                
                if is_user_mentioned:
                    if unread_only:
                        # Check if there's an unread notification
                        has_unread = any(
                            n.recipient_id == user_id and n.comment_id == comment.id and not n.read
                            for n in self._notifications.values()
                        )
                        if has_unread:
                            results.append((comment, mention))
                    else:
                        results.append((comment, mention))
        
        return results
    
    def get_comment_count(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
    ) -> dict[str, int]:
        """Get comment statistics for an object."""
        comments = self.get_comments_for_object(
            parent_type,
            parent_id,
            include_resolved=True,
            include_deleted=False,
        )
        
        active = sum(1 for c in comments if c.status == CommentStatus.ACTIVE)
        resolved = sum(1 for c in comments if c.status == CommentStatus.RESOLVED)
        
        return {
            "total": len(comments),
            "active": active,
            "resolved": resolved,
            "unresolved": active,  # Same as active
        }
    
    # =========================================================================
    # Reactions
    # =========================================================================
    
    def add_reaction(
        self,
        comment_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> CommentReaction | None:
        """Add a reaction to a comment."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        if comment.status == CommentStatus.DELETED:
            return None
        
        # Check if user already has this reaction
        for existing in comment.reactions:
            if existing.user_id == user_id and existing.reaction_type == reaction_type:
                return existing  # Already exists
        
        reaction = CommentReaction(
            id=uuid4(),
            comment_id=comment_id,
            user_id=user_id,
            reaction_type=reaction_type,
            created_at=datetime.now(timezone.utc),
        )
        
        comment.reactions.append(reaction)
        return reaction
    
    def remove_reaction(
        self,
        comment_id: UUID,
        user_id: UUID,
        reaction_type: str,
    ) -> bool:
        """Remove a reaction from a comment."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return False
        
        for i, reaction in enumerate(comment.reactions):
            if reaction.user_id == user_id and reaction.reaction_type == reaction_type:
                comment.reactions.pop(i)
                return True
        
        return False
    
    def get_reaction_summary(
        self,
        comment_id: UUID,
    ) -> dict[str, list[UUID]]:
        """Get summary of reactions grouped by type."""
        comment = self._comments.get(comment_id)
        if comment is None:
            return {}
        
        summary: dict[str, list[UUID]] = {}
        for reaction in comment.reactions:
            if reaction.reaction_type not in summary:
                summary[reaction.reaction_type] = []
            summary[reaction.reaction_type].append(reaction.user_id)
        
        return summary
    
    # =========================================================================
    # Notifications
    # =========================================================================
    
    def get_notifications(
        self,
        user_id: UUID,
        unread_only: bool = True,
    ) -> list[MentionNotification]:
        """Get notifications for a user."""
        notifications = []
        for notification in self._notifications.values():
            if notification.recipient_id != user_id:
                continue
            if unread_only and notification.read:
                continue
            notifications.append(notification)
        
        # Sort by created_at descending
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)
    
    def mark_notification_read(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Mark a notification as read."""
        notification = self._notifications.get(notification_id)
        if notification is None:
            return False
        
        if notification.recipient_id != user_id:
            return False
        
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)
        return True
    
    def mark_all_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for a user."""
        count = 0
        now = datetime.now(timezone.utc)
        for notification in self._notifications.values():
            if notification.recipient_id == user_id and not notification.read:
                notification.read = True
                notification.read_at = now
                count += 1
        return count
    
    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user."""
        return sum(
            1 for n in self._notifications.values()
            if n.recipient_id == user_id and not n.read
        )
    
    # =========================================================================
    # Task Conversion
    # =========================================================================
    
    def convert_to_task(
        self,
        comment_id: UUID,
        assigned_to: UUID,
        due_date: datetime | None = None,
        priority: str = "medium",
    ) -> dict[str, Any] | None:
        """
        Convert a comment to a task.
        
        Returns task data that can be used to create a task.
        Does not actually create the task (that's for the task service).
        """
        comment = self._comments.get(comment_id)
        if comment is None:
            return None
        
        return {
            "title": f"From comment: {comment.content[:50]}...",
            "description": comment.content,
            "assigned_to": assigned_to,
            "due_date": due_date,
            "priority": priority,
            "source_type": "comment",
            "source_id": comment_id,
            "parent_type": comment.parent_type.value,
            "parent_id": comment.parent_id,
            "metadata": {
                "original_author": str(comment.created_by),
                "original_comment_at": comment.created_at.isoformat(),
                "line_number": comment.line_number,
                "field_name": comment.field_name,
            },
        }
    
    # =========================================================================
    # Mention Parsing and Resolution
    # =========================================================================
    
    def _parse_mentions(self, content: str) -> list[Mention]:
        """Parse @mentions from comment content."""
        mentions = []
        
        for match in self.MENTION_PATTERN.finditer(content):
            identifier = match.group(1).lower()
            start = match.start()
            end = match.end()
            
            mention = self._resolve_mention(identifier, start, end)
            if mention:
                mentions.append(mention)
        
        return mentions
    
    def _resolve_mention(
        self,
        identifier: str,
        start: int,
        end: int,
    ) -> Mention | None:
        """Resolve a mention identifier to a Mention object."""
        mention_id = uuid4()
        
        # Check for special mentions
        if identifier == "all":
            return Mention(
                id=mention_id,
                mention_type=MentionType.ALL,
                target_id=None,
                target_identifier=identifier,
                start_position=start,
                end_position=end,
            )
        
        if identifier == "assignee":
            return Mention(
                id=mention_id,
                mention_type=MentionType.ASSIGNEE,
                target_id=None,
                target_identifier=identifier,
                start_position=start,
                end_position=end,
            )
        
        # Check if it's a user
        user = self._users_by_username.get(identifier)
        if user:
            return Mention(
                id=mention_id,
                mention_type=MentionType.USER,
                target_id=user.id,
                target_identifier=identifier,
                start_position=start,
                end_position=end,
            )
        
        # Check if it's a team
        team = self._teams_by_identifier.get(identifier)
        if team:
            return Mention(
                id=mention_id,
                mention_type=MentionType.TEAM,
                target_id=team.id,
                target_identifier=identifier,
                start_position=start,
                end_position=end,
            )
        
        # Check if it's a role
        role = self._roles_by_identifier.get(identifier)
        if role:
            return Mention(
                id=mention_id,
                mention_type=MentionType.ROLE,
                target_id=role.id,
                target_identifier=identifier,
                start_position=start,
                end_position=end,
            )
        
        # Unknown mention - still create but with no target
        return Mention(
            id=mention_id,
            mention_type=MentionType.USER,
            target_id=None,
            target_identifier=identifier,
            start_position=start,
            end_position=end,
        )
    
    def _render_html_content(
        self,
        content: str,
        mentions: list[Mention],
    ) -> str:
        """Render content with HTML mention links."""
        if not mentions:
            return content
        
        # Sort mentions by position (reverse order for replacement)
        sorted_mentions = sorted(mentions, key=lambda m: m.start_position, reverse=True)
        
        result = content
        for mention in sorted_mentions:
            original = result[mention.start_position:mention.end_position]
            
            if mention.target_id:
                link = f'<span class="mention" data-type="{mention.mention_type.value}" data-id="{mention.target_id}">{original}</span>'
            else:
                link = f'<span class="mention mention-unresolved">{original}</span>'
            
            result = result[:mention.start_position] + link + result[mention.end_position:]
        
        return result
    
    def _create_mention_notifications(self, comment: Comment) -> None:
        """Create notifications for all mentions in a comment."""
        for mention in comment.mentions:
            self._notify_mention(comment, mention)
    
    def _notify_mention(self, comment: Comment, mention: Mention) -> None:
        """Create notification(s) for a single mention."""
        recipients: list[UUID] = []
        priority = NotificationPriority.NORMAL
        
        if mention.mention_type == MentionType.USER:
            if mention.target_id:
                recipients.append(mention.target_id)
        
        elif mention.mention_type == MentionType.TEAM:
            if mention.target_id:
                team = self._teams.get(mention.target_id)
                if team:
                    recipients.extend(team.member_ids)
        
        elif mention.mention_type == MentionType.ROLE:
            if mention.target_id:
                role = self._roles.get(mention.target_id)
                if role:
                    recipients.extend(role.user_ids)
        
        elif mention.mention_type == MentionType.ALL:
            key = (comment.parent_type, comment.parent_id)
            recipients.extend(self._object_watchers.get(key, set()))
            priority = NotificationPriority.HIGH
        
        elif mention.mention_type == MentionType.ASSIGNEE:
            key = (comment.parent_type, comment.parent_id)
            assignee = self._object_assignees.get(key)
            if assignee:
                recipients.append(assignee)
                priority = NotificationPriority.HIGH
        
        # Don't notify the comment author
        recipients = [r for r in recipients if r != comment.created_by]
        
        # Create notifications
        for recipient_id in recipients:
            notification = MentionNotification(
                id=uuid4(),
                comment_id=comment.id,
                mention_id=mention.id,
                recipient_id=recipient_id,
                priority=priority,
            )
            self._notifications[notification.id] = notification
        
        # Mark mention as notified
        mention.notified = True
        mention.notified_at = datetime.now(timezone.utc)
    
    # =========================================================================
    # Search
    # =========================================================================
    
    def search_comments(
        self,
        query: str,
        parent_type: CommentableType | None = None,
        created_by: UUID | None = None,
        limit: int = 50,
    ) -> list[Comment]:
        """Search comments by text content."""
        query_lower = query.lower()
        results = []
        
        for comment in self._comments.values():
            if comment.status == CommentStatus.DELETED:
                continue
            
            if parent_type and comment.parent_type != parent_type:
                continue
            
            if created_by and comment.created_by != created_by:
                continue
            
            if query_lower in comment.content.lower():
                results.append(comment)
            
            if len(results) >= limit:
                break
        
        # Sort by created_at descending
        return sorted(results, key=lambda c: c.created_at, reverse=True)[:limit]
    
    # =========================================================================
    # Activity Feed
    # =========================================================================
    
    def get_activity_feed(
        self,
        parent_type: CommentableType,
        parent_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get activity feed for an object including comments."""
        activities = []
        
        comments = self.get_comments_for_object(
            parent_type,
            parent_id,
            include_resolved=True,
            include_deleted=False,
        )
        
        for comment in comments:
            activity = {
                "type": "comment",
                "timestamp": comment.created_at,
                "user_id": comment.created_by,
                "data": {
                    "comment_id": comment.id,
                    "content_preview": comment.content[:100],
                    "is_reply": comment.reply_to_id is not None,
                    "mention_count": len(comment.mentions),
                    "reaction_count": len(comment.reactions),
                },
            }
            activities.append(activity)
            
            # Add resolution as separate activity
            if comment.status == CommentStatus.RESOLVED and comment.resolved_at:
                resolution = {
                    "type": "comment_resolved",
                    "timestamp": comment.resolved_at,
                    "user_id": comment.resolved_by,
                    "data": {
                        "comment_id": comment.id,
                    },
                }
                activities.append(resolution)
        
        # Sort by timestamp descending
        activities.sort(key=lambda a: str(a.get("timestamp", "")), reverse=True)
        return activities[:limit]
