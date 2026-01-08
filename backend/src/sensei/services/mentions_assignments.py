"""
Mentions and Assignments Service

This service provides functionality for:
- Parsing @mentions from text/comments
- Converting comments to tasks with one click
- Assigning owners to entities
- Managing due dates and assignments
- Notification triggers for mentions
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


# =============================================================================
# Enums
# =============================================================================

class MentionType(str, Enum):
    """Types of mentions that can occur in text."""
    USER = "user"
    TEAM = "team"
    ROLE = "role"
    ENTITY = "entity"


class AssignmentStatus(str, Enum):
    """Status of an assignment."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    REASSIGNED = "reassigned"


class NotificationType(str, Enum):
    """Types of notifications for mentions and assignments."""
    MENTION = "mention"
    ASSIGNMENT = "assignment"
    DUE_DATE_SET = "due_date_set"
    DUE_DATE_REMINDER = "due_date_reminder"
    DUE_DATE_OVERDUE = "due_date_overdue"
    TASK_CREATED_FROM_COMMENT = "task_created_from_comment"
    REASSIGNMENT = "reassignment"


class EntityType(str, Enum):
    """Types of entities that can be mentioned or assigned."""
    TASK = "task"
    COMMENT = "comment"
    RFQ = "rfq"
    QUOTE = "quote"
    OPPORTUNITY = "opportunity"
    A3 = "a3"
    OBEYA = "obeya"
    ANDON = "andon"


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Mention:
    """Represents a mention in text."""
    id: str = field(default_factory=lambda: str(uuid4()))
    mention_type: MentionType = MentionType.USER
    target_id: str = ""
    target_name: str = ""
    display_text: str = ""
    start_index: int = 0
    end_index: int = 0
    source_entity_type: EntityType = EntityType.COMMENT
    source_entity_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    notified: bool = False


@dataclass
class Assignment:
    """Represents an assignment of an entity to a user."""
    id: str = field(default_factory=lambda: str(uuid4()))
    entity_type: EntityType = EntityType.TASK
    entity_id: str = ""
    entity_name: str = ""
    assignee_id: str = ""
    assignee_name: str = ""
    assigned_by: str = ""
    assigned_by_name: str = ""
    status: AssignmentStatus = AssignmentStatus.PENDING
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class TaskFromComment:
    """Represents a task created from a comment."""
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    source_comment_id: str = ""
    source_comment_text: str = ""
    source_entity_type: EntityType = EntityType.COMMENT
    source_entity_id: str = ""
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    created_by_name: str = ""
    linked_entity_type: Optional[EntityType] = None
    linked_entity_id: Optional[str] = None


@dataclass
class MentionNotification:
    """Represents a notification for a mention or assignment."""
    id: str = field(default_factory=lambda: str(uuid4()))
    notification_type: NotificationType = NotificationType.MENTION
    recipient_id: str = ""
    recipient_name: str = ""
    sender_id: str = ""
    sender_name: str = ""
    entity_type: EntityType = EntityType.COMMENT
    entity_id: str = ""
    entity_name: str = ""
    message: str = ""
    link: str = ""
    read: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    read_at: Optional[datetime] = None


@dataclass
class UserSummary:
    """Summary information for a user."""
    id: str = ""
    name: str = ""
    email: str = ""
    role: str = ""
    avatar_url: Optional[str] = None


@dataclass
class TeamSummary:
    """Summary information for a team."""
    id: str = ""
    name: str = ""
    member_ids: list[str] = field(default_factory=list)


@dataclass
class DueDateInfo:
    """Information about a due date."""
    due_date: datetime
    is_overdue: bool = False
    days_remaining: int = 0
    hours_remaining: int = 0
    reminder_sent: bool = False


# =============================================================================
# Request/Response Models
# =============================================================================

@dataclass
class ParseMentionsRequest:
    """Request to parse mentions from text."""
    text: str = ""
    source_entity_type: EntityType = EntityType.COMMENT
    source_entity_id: str = ""
    created_by: str = ""


@dataclass
class ParseMentionsResponse:
    """Response from parsing mentions."""
    mentions: list[Mention] = field(default_factory=list)
    cleaned_text: str = ""
    mention_count: int = 0
    user_mentions: list[Mention] = field(default_factory=list)
    team_mentions: list[Mention] = field(default_factory=list)
    role_mentions: list[Mention] = field(default_factory=list)
    entity_mentions: list[Mention] = field(default_factory=list)


@dataclass
class CreateAssignmentRequest:
    """Request to create an assignment."""
    entity_type: EntityType = EntityType.TASK
    entity_id: str = ""
    entity_name: str = ""
    assignee_id: str = ""
    assignee_name: str = ""
    assigned_by: str = ""
    assigned_by_name: str = ""
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    notes: str = ""


@dataclass
class CreateAssignmentResponse:
    """Response from creating an assignment."""
    assignment: Assignment | None = None
    notification: MentionNotification | None = None
    success: bool = False
    error: str = ""


@dataclass
class CreateTaskFromCommentRequest:
    """Request to create a task from a comment."""
    comment_id: str = ""
    comment_text: str = ""
    source_entity_type: EntityType = EntityType.COMMENT
    source_entity_id: str = ""
    title: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    created_by: str = ""
    created_by_name: str = ""


@dataclass
class CreateTaskFromCommentResponse:
    """Response from creating a task from a comment."""
    task: TaskFromComment | None = None
    assignment: Assignment | None = None
    notifications: list[MentionNotification] = field(default_factory=list)
    success: bool = False
    error: str = ""


@dataclass
class UpdateDueDateRequest:
    """Request to update a due date."""
    entity_type: EntityType = EntityType.TASK
    entity_id: str = ""
    new_due_date: Optional[datetime] = None
    updated_by: str = ""
    updated_by_name: str = ""
    notify_assignee: bool = True


@dataclass
class UpdateDueDateResponse:
    """Response from updating a due date."""
    success: bool = False
    previous_due_date: Optional[datetime] = None
    new_due_date: Optional[datetime] = None
    notification: MentionNotification | None = None
    error: str = ""


@dataclass
class ReassignRequest:
    """Request to reassign an entity."""
    entity_type: EntityType = EntityType.TASK
    entity_id: str = ""
    new_assignee_id: str = ""
    new_assignee_name: str = ""
    reassigned_by: str = ""
    reassigned_by_name: str = ""
    reason: str = ""
    notify_both: bool = True


@dataclass
class ReassignResponse:
    """Response from reassigning an entity."""
    success: bool = False
    previous_assignee_id: Optional[str] = None
    previous_assignee_name: Optional[str] = None
    new_assignment: Assignment | None = None
    notifications: list[MentionNotification] = field(default_factory=list)
    error: str = ""


# =============================================================================
# Mention Patterns
# =============================================================================

# Pattern for @username mentions (excludes team: and role: prefixed mentions)
USER_MENTION_PATTERN = re.compile(r"@(?!team:|role:)(\w+(?:\.\w+)*)")

# Pattern for @team:teamname mentions
TEAM_MENTION_PATTERN = re.compile(r"@team:(\w+)")

# Pattern for @role:rolename mentions
ROLE_MENTION_PATTERN = re.compile(r"@role:(\w+)")

# Pattern for entity mentions like #RFQ-123 or #QUOTE-456
ENTITY_MENTION_PATTERN = re.compile(r"#(RFQ|QUOTE|OPP|TASK|A3|OBEYA|ANDON)-(\d+)", re.IGNORECASE)


# =============================================================================
# Utility Functions
# =============================================================================

def extract_mentions_from_text(text: str) -> list[dict[str, Any]]:
    """Extract all mentions from text."""
    mentions = []
    
    # Extract team mentions first (so they don't conflict with user mentions)
    for match in TEAM_MENTION_PATTERN.finditer(text):
        mentions.append({
            "type": MentionType.TEAM,
            "value": match.group(1),
            "display": match.group(0),
            "start": match.start(),
            "end": match.end(),
        })
    
    # Extract role mentions
    for match in ROLE_MENTION_PATTERN.finditer(text):
        mentions.append({
            "type": MentionType.ROLE,
            "value": match.group(1),
            "display": match.group(0),
            "start": match.start(),
            "end": match.end(),
        })
    
    # Extract user mentions (excludes team: and role: patterns)
    for match in USER_MENTION_PATTERN.finditer(text):
        mentions.append({
            "type": MentionType.USER,
            "value": match.group(1),
            "display": match.group(0),
            "start": match.start(),
            "end": match.end(),
        })
    
    # Extract entity mentions
    for match in ENTITY_MENTION_PATTERN.finditer(text):
        entity_type = match.group(1).upper()
        entity_id = match.group(2)
        mentions.append({
            "type": MentionType.ENTITY,
            "value": f"{entity_type}-{entity_id}",
            "display": match.group(0),
            "start": match.start(),
            "end": match.end(),
        })
    
    return sorted(mentions, key=lambda m: m["start"])


def clean_mention_text(text: str) -> str:
    """Remove mention syntax from text, keeping readable names."""
    # Replace @team:name with just "name team"
    text = TEAM_MENTION_PATTERN.sub(r"\1 team", text)
    
    # Replace @role:name with just "name role"
    text = ROLE_MENTION_PATTERN.sub(r"\1 role", text)
    
    # Replace @username with just "username"
    text = USER_MENTION_PATTERN.sub(r"\1", text)
    
    return text


def generate_task_title_from_comment(comment_text: str, max_length: int = 100) -> str:
    """Generate a task title from comment text."""
    # Clean up the text
    cleaned = clean_mention_text(comment_text)
    
    # Remove excess whitespace
    cleaned = " ".join(cleaned.split())
    
    # Truncate if necessary
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length - 3].rsplit(" ", 1)[0] + "..."
    
    return cleaned


def calculate_due_date_info(due_date: Optional[datetime]) -> Optional[DueDateInfo]:
    """Calculate information about a due date."""
    if not due_date:
        return None
    
    now = datetime.now()
    diff = due_date - now
    
    is_overdue = diff.total_seconds() < 0
    total_seconds = abs(diff.total_seconds())
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    
    if is_overdue:
        days = -days
        hours = -hours
    
    return DueDateInfo(
        due_date=due_date,
        is_overdue=is_overdue,
        days_remaining=days,
        hours_remaining=hours,
    )


def generate_due_date_from_text(text: str) -> Optional[datetime]:
    """Parse a due date from natural language text."""
    text_lower = text.lower()
    now = datetime.now()
    
    # Common patterns
    if "today" in text_lower:
        return now.replace(hour=23, minute=59, second=59)
    if "tomorrow" in text_lower:
        return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
    if "next week" in text_lower:
        return (now + timedelta(weeks=1)).replace(hour=23, minute=59, second=59)
    if "next month" in text_lower:
        return (now + timedelta(days=30)).replace(hour=23, minute=59, second=59)
    
    # Pattern: in X days
    days_match = re.search(r"in\s+(\d+)\s+days?", text_lower)
    if days_match:
        days = int(days_match.group(1))
        return (now + timedelta(days=days)).replace(hour=23, minute=59, second=59)
    
    # Pattern: in X hours
    hours_match = re.search(r"in\s+(\d+)\s+hours?", text_lower)
    if hours_match:
        hours = int(hours_match.group(1))
        return now + timedelta(hours=hours)
    
    # Pattern: in X weeks
    weeks_match = re.search(r"in\s+(\d+)\s+weeks?", text_lower)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return (now + timedelta(weeks=weeks)).replace(hour=23, minute=59, second=59)
    
    return None


def format_mention_notification_message(
    notification_type: NotificationType,
    sender_name: str,
    entity_type: EntityType,
    entity_name: str,
    assignee_name: Optional[str] = None,
) -> str:
    """Format a notification message."""
    messages = {
        NotificationType.MENTION: f"{sender_name} mentioned you in a {entity_type.value}: {entity_name}",
        NotificationType.ASSIGNMENT: f"{sender_name} assigned you to {entity_type.value}: {entity_name}",
        NotificationType.DUE_DATE_SET: f"{sender_name} set a due date for {entity_type.value}: {entity_name}",
        NotificationType.DUE_DATE_REMINDER: f"Reminder: {entity_type.value} '{entity_name}' is due soon",
        NotificationType.DUE_DATE_OVERDUE: f"Overdue: {entity_type.value} '{entity_name}' is past due",
        NotificationType.TASK_CREATED_FROM_COMMENT: f"{sender_name} created a task from a comment: {entity_name}",
        NotificationType.REASSIGNMENT: f"{sender_name} reassigned {entity_type.value}: {entity_name}",
    }
    
    return messages.get(notification_type, f"Notification for {entity_type.value}: {entity_name}")


def generate_entity_link(entity_type: EntityType, entity_id: str) -> str:
    """Generate a link to an entity."""
    type_paths = {
        EntityType.TASK: "tasks",
        EntityType.COMMENT: "comments",
        EntityType.RFQ: "rfqs",
        EntityType.QUOTE: "quotes",
        EntityType.OPPORTUNITY: "pipeline",
        EntityType.A3: "a3s",
        EntityType.OBEYA: "obeya",
        EntityType.ANDON: "andon",
    }
    
    path = type_paths.get(entity_type, "entities")
    return f"/{path}/{entity_id}"


# =============================================================================
# Service Class
# =============================================================================

class MentionsAssignmentsService:
    """Service for handling mentions and assignments."""
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._mentions: dict[str, Mention] = {}
        self._assignments: dict[str, Assignment] = {}
        self._tasks: dict[str, TaskFromComment] = {}
        self._notifications: dict[str, MentionNotification] = {}
        self._users: dict[str, UserSummary] = {}
        self._teams: dict[str, TeamSummary] = {}
    
    # =========================================================================
    # User/Team Management
    # =========================================================================
    
    def register_user(self, user: UserSummary) -> None:
        """Register a user for mention resolution."""
        self._users[user.id] = user
        # Also index by name for @mention lookup
        self._users[user.name.lower()] = user
    
    def register_team(self, team: TeamSummary) -> None:
        """Register a team for mention resolution."""
        self._teams[team.id] = team
        self._teams[team.name.lower()] = team
    
    def resolve_user(self, identifier: str) -> Optional[UserSummary]:
        """Resolve a user by ID or name."""
        return self._users.get(identifier) or self._users.get(identifier.lower())
    
    def resolve_team(self, identifier: str) -> Optional[TeamSummary]:
        """Resolve a team by ID or name."""
        return self._teams.get(identifier) or self._teams.get(identifier.lower())
    
    # =========================================================================
    # Mention Parsing
    # =========================================================================
    
    def parse_mentions(self, request: ParseMentionsRequest) -> ParseMentionsResponse:
        """Parse mentions from text."""
        raw_mentions = extract_mentions_from_text(request.text)
        
        mentions: list[Mention] = []
        user_mentions: list[Mention] = []
        team_mentions: list[Mention] = []
        role_mentions: list[Mention] = []
        entity_mentions: list[Mention] = []
        
        for raw in raw_mentions:
            mention = Mention(
                mention_type=raw["type"],
                target_name=raw["value"],
                display_text=raw["display"],
                start_index=raw["start"],
                end_index=raw["end"],
                source_entity_type=request.source_entity_type,
                source_entity_id=request.source_entity_id,
                created_by=request.created_by,
            )
            
            # Try to resolve the target
            if raw["type"] == MentionType.USER:
                user = self.resolve_user(raw["value"])
                if user:
                    mention.target_id = user.id
                    mention.target_name = user.name
            elif raw["type"] == MentionType.TEAM:
                team = self.resolve_team(raw["value"])
                if team:
                    mention.target_id = team.id
                    mention.target_name = team.name
            
            mentions.append(mention)
            self._mentions[mention.id] = mention
            
            # Categorize
            if mention.mention_type == MentionType.USER:
                user_mentions.append(mention)
            elif mention.mention_type == MentionType.TEAM:
                team_mentions.append(mention)
            elif mention.mention_type == MentionType.ROLE:
                role_mentions.append(mention)
            elif mention.mention_type == MentionType.ENTITY:
                entity_mentions.append(mention)
        
        return ParseMentionsResponse(
            mentions=mentions,
            cleaned_text=clean_mention_text(request.text),
            mention_count=len(mentions),
            user_mentions=user_mentions,
            team_mentions=team_mentions,
            role_mentions=role_mentions,
            entity_mentions=entity_mentions,
        )
    
    def get_mention(self, mention_id: str) -> Optional[Mention]:
        """Get a mention by ID."""
        return self._mentions.get(mention_id)
    
    def get_mentions_for_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> list[Mention]:
        """Get all mentions for a specific entity."""
        return [
            m for m in self._mentions.values()
            if m.source_entity_type == entity_type and m.source_entity_id == entity_id
        ]
    
    def get_mentions_for_user(self, user_id: str) -> list[Mention]:
        """Get all mentions targeting a specific user."""
        return [
            m for m in self._mentions.values()
            if m.mention_type == MentionType.USER and m.target_id == user_id
        ]
    
    # =========================================================================
    # Assignment Management
    # =========================================================================
    
    def create_assignment(self, request: CreateAssignmentRequest) -> CreateAssignmentResponse:
        """Create a new assignment."""
        if not request.entity_id:
            return CreateAssignmentResponse(
                success=False,
                error="Entity ID is required",
            )
        
        if not request.assignee_id:
            return CreateAssignmentResponse(
                success=False,
                error="Assignee ID is required",
            )
        
        assignment = Assignment(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_name=request.entity_name,
            assignee_id=request.assignee_id,
            assignee_name=request.assignee_name,
            assigned_by=request.assigned_by,
            assigned_by_name=request.assigned_by_name,
            due_date=request.due_date,
            priority=request.priority,
            notes=request.notes,
        )
        
        self._assignments[assignment.id] = assignment
        
        # Create notification
        notification = MentionNotification(
            notification_type=NotificationType.ASSIGNMENT,
            recipient_id=request.assignee_id,
            recipient_name=request.assignee_name,
            sender_id=request.assigned_by,
            sender_name=request.assigned_by_name,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_name=request.entity_name,
            message=format_mention_notification_message(
                NotificationType.ASSIGNMENT,
                request.assigned_by_name,
                request.entity_type,
                request.entity_name,
            ),
            link=generate_entity_link(request.entity_type, request.entity_id),
        )
        
        self._notifications[notification.id] = notification
        
        return CreateAssignmentResponse(
            assignment=assignment,
            notification=notification,
            success=True,
        )
    
    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Get an assignment by ID."""
        return self._assignments.get(assignment_id)
    
    def get_assignments_for_user(self, user_id: str) -> list[Assignment]:
        """Get all assignments for a user."""
        return [a for a in self._assignments.values() if a.assignee_id == user_id]
    
    def get_assignments_for_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> list[Assignment]:
        """Get all assignments for an entity."""
        return [
            a for a in self._assignments.values()
            if a.entity_type == entity_type and a.entity_id == entity_id
        ]
    
    def accept_assignment(self, assignment_id: str) -> bool:
        """Accept an assignment."""
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            return False
        
        assignment.status = AssignmentStatus.ACCEPTED
        assignment.accepted_at = datetime.now()
        assignment.updated_at = datetime.now()
        return True
    
    def decline_assignment(self, assignment_id: str, reason: str = "") -> bool:
        """Decline an assignment."""
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            return False
        
        assignment.status = AssignmentStatus.DECLINED
        assignment.notes = reason if reason else assignment.notes
        assignment.updated_at = datetime.now()
        return True
    
    def complete_assignment(self, assignment_id: str) -> bool:
        """Mark an assignment as completed."""
        assignment = self._assignments.get(assignment_id)
        if not assignment:
            return False
        
        assignment.status = AssignmentStatus.COMPLETED
        assignment.completed_at = datetime.now()
        assignment.updated_at = datetime.now()
        return True
    
    # =========================================================================
    # Task from Comment
    # =========================================================================
    
    def create_task_from_comment(
        self,
        request: CreateTaskFromCommentRequest,
    ) -> CreateTaskFromCommentResponse:
        """Create a task from a comment."""
        if not request.comment_text:
            return CreateTaskFromCommentResponse(
                success=False,
                error="Comment text is required",
            )
        
        # Generate title if not provided
        title = request.title or generate_task_title_from_comment(request.comment_text)
        
        task = TaskFromComment(
            title=title,
            description=request.comment_text,
            source_comment_id=request.comment_id,
            source_comment_text=request.comment_text,
            source_entity_type=request.source_entity_type,
            source_entity_id=request.source_entity_id,
            assignee_id=request.assignee_id,
            assignee_name=request.assignee_name,
            due_date=request.due_date,
            priority=request.priority,
            created_by=request.created_by,
            created_by_name=request.created_by_name,
            linked_entity_type=request.source_entity_type,
            linked_entity_id=request.source_entity_id,
        )
        
        self._tasks[task.id] = task
        
        notifications: list[MentionNotification] = []
        assignment: Optional[Assignment] = None
        
        # Create assignment if assignee specified
        if request.assignee_id:
            assignment_response = self.create_assignment(CreateAssignmentRequest(
                entity_type=EntityType.TASK,
                entity_id=task.id,
                entity_name=title,
                assignee_id=request.assignee_id,
                assignee_name=request.assignee_name or "",
                assigned_by=request.created_by,
                assigned_by_name=request.created_by_name,
                due_date=request.due_date,
                priority=request.priority,
            ))
            
            if assignment_response.success:
                assignment = assignment_response.assignment
                if assignment_response.notification:
                    notifications.append(assignment_response.notification)
        
        # Parse mentions in the comment and create notifications
        parse_response = self.parse_mentions(ParseMentionsRequest(
            text=request.comment_text,
            source_entity_type=EntityType.TASK,
            source_entity_id=task.id,
            created_by=request.created_by,
        ))
        
        for mention in parse_response.user_mentions:
            if mention.target_id and mention.target_id != request.assignee_id:
                notification = MentionNotification(
                    notification_type=NotificationType.TASK_CREATED_FROM_COMMENT,
                    recipient_id=mention.target_id,
                    recipient_name=mention.target_name,
                    sender_id=request.created_by,
                    sender_name=request.created_by_name,
                    entity_type=EntityType.TASK,
                    entity_id=task.id,
                    entity_name=title,
                    message=format_mention_notification_message(
                        NotificationType.TASK_CREATED_FROM_COMMENT,
                        request.created_by_name,
                        EntityType.TASK,
                        title,
                    ),
                    link=generate_entity_link(EntityType.TASK, task.id),
                )
                self._notifications[notification.id] = notification
                notifications.append(notification)
        
        return CreateTaskFromCommentResponse(
            task=task,
            assignment=assignment,
            notifications=notifications,
            success=True,
        )
    
    def get_task(self, task_id: str) -> Optional[TaskFromComment]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_tasks_for_entity(
        self,
        entity_type: EntityType,
        entity_id: str,
    ) -> list[TaskFromComment]:
        """Get all tasks created from comments on an entity."""
        return [
            t for t in self._tasks.values()
            if t.source_entity_type == entity_type and t.source_entity_id == entity_id
        ]
    
    # =========================================================================
    # Due Date Management
    # =========================================================================
    
    def update_due_date(self, request: UpdateDueDateRequest) -> UpdateDueDateResponse:
        """Update a due date for an entity."""
        # Find the assignment for this entity
        assignments = self.get_assignments_for_entity(
            request.entity_type,
            request.entity_id,
        )
        
        if not assignments:
            return UpdateDueDateResponse(
                success=False,
                error="No assignment found for this entity",
            )
        
        # Update the most recent assignment
        assignment = assignments[-1]
        previous_due_date = assignment.due_date
        assignment.due_date = request.new_due_date
        assignment.updated_at = datetime.now()
        
        notification = None
        if request.notify_assignee and assignment.assignee_id:
            notification = MentionNotification(
                notification_type=NotificationType.DUE_DATE_SET,
                recipient_id=assignment.assignee_id,
                recipient_name=assignment.assignee_name,
                sender_id=request.updated_by,
                sender_name=request.updated_by_name,
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                entity_name=assignment.entity_name,
                message=format_mention_notification_message(
                    NotificationType.DUE_DATE_SET,
                    request.updated_by_name,
                    request.entity_type,
                    assignment.entity_name,
                ),
                link=generate_entity_link(request.entity_type, request.entity_id),
            )
            self._notifications[notification.id] = notification
        
        return UpdateDueDateResponse(
            success=True,
            previous_due_date=previous_due_date,
            new_due_date=request.new_due_date,
            notification=notification,
        )
    
    def get_overdue_assignments(self) -> list[Assignment]:
        """Get all overdue assignments."""
        now = datetime.now()
        return [
            a for a in self._assignments.values()
            if a.due_date and a.due_date < now and a.status not in [
                AssignmentStatus.COMPLETED,
                AssignmentStatus.DECLINED,
                AssignmentStatus.REASSIGNED,
            ]
        ]
    
    def get_upcoming_assignments(self, days: int = 7) -> list[Assignment]:
        """Get assignments due within the specified number of days."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        
        return [
            a for a in self._assignments.values()
            if a.due_date and now <= a.due_date <= cutoff and a.status not in [
                AssignmentStatus.COMPLETED,
                AssignmentStatus.DECLINED,
                AssignmentStatus.REASSIGNED,
            ]
        ]
    
    # =========================================================================
    # Reassignment
    # =========================================================================
    
    def reassign(self, request: ReassignRequest) -> ReassignResponse:
        """Reassign an entity to a new user."""
        # Find the current assignment
        assignments = self.get_assignments_for_entity(
            request.entity_type,
            request.entity_id,
        )
        
        if not assignments:
            return ReassignResponse(
                success=False,
                error="No assignment found for this entity",
            )
        
        current_assignment = assignments[-1]
        previous_assignee_id = current_assignment.assignee_id
        previous_assignee_name = current_assignment.assignee_name
        
        # Mark old assignment as reassigned
        current_assignment.status = AssignmentStatus.REASSIGNED
        current_assignment.updated_at = datetime.now()
        
        # Create new assignment
        assignment_response = self.create_assignment(CreateAssignmentRequest(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_name=current_assignment.entity_name,
            assignee_id=request.new_assignee_id,
            assignee_name=request.new_assignee_name,
            assigned_by=request.reassigned_by,
            assigned_by_name=request.reassigned_by_name,
            due_date=current_assignment.due_date,
            priority=current_assignment.priority,
            notes=request.reason,
        ))
        
        if not assignment_response.success:
            return ReassignResponse(
                success=False,
                error=assignment_response.error,
            )
        
        notifications: list[MentionNotification] = []
        if assignment_response.notification:
            notifications.append(assignment_response.notification)
        
        # Notify previous assignee if requested
        if request.notify_both and previous_assignee_id:
            notification = MentionNotification(
                notification_type=NotificationType.REASSIGNMENT,
                recipient_id=previous_assignee_id,
                recipient_name=previous_assignee_name,
                sender_id=request.reassigned_by,
                sender_name=request.reassigned_by_name,
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                entity_name=current_assignment.entity_name,
                message=f"{request.reassigned_by_name} reassigned {request.entity_type.value} '{current_assignment.entity_name}' to {request.new_assignee_name}",
                link=generate_entity_link(request.entity_type, request.entity_id),
            )
            self._notifications[notification.id] = notification
            notifications.append(notification)
        
        return ReassignResponse(
            success=True,
            previous_assignee_id=previous_assignee_id,
            previous_assignee_name=previous_assignee_name,
            new_assignment=assignment_response.assignment,
            notifications=notifications,
        )
    
    # =========================================================================
    # Notifications
    # =========================================================================
    
    def get_notification(self, notification_id: str) -> Optional[MentionNotification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)
    
    def get_notifications_for_user(
        self,
        user_id: str,
        unread_only: bool = False,
    ) -> list[MentionNotification]:
        """Get notifications for a user."""
        notifications = [
            n for n in self._notifications.values()
            if n.recipient_id == user_id
        ]
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        return sorted(notifications, key=lambda n: n.created_at, reverse=True)
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notification = self._notifications.get(notification_id)
        if not notification:
            return False
        
        notification.read = True
        notification.read_at = datetime.now()
        return True
    
    def mark_all_notifications_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        count = 0
        for notification in self._notifications.values():
            if notification.recipient_id == user_id and not notification.read:
                notification.read = True
                notification.read_at = datetime.now()
                count += 1
        return count
    
    def get_unread_notification_count(self, user_id: str) -> int:
        """Get the count of unread notifications for a user."""
        return len([
            n for n in self._notifications.values()
            if n.recipient_id == user_id and not n.read
        ])
    
    # =========================================================================
    # Mention-to-Notification Processing
    # =========================================================================
    
    def process_mention_notifications(
        self,
        mentions: list[Mention],
        sender_id: str,
        sender_name: str,
        entity_type: EntityType,
        entity_id: str,
        entity_name: str,
    ) -> list[MentionNotification]:
        """Create notifications for a list of mentions."""
        notifications: list[MentionNotification] = []
        
        for mention in mentions:
            if mention.mention_type == MentionType.USER and mention.target_id:
                notification = MentionNotification(
                    notification_type=NotificationType.MENTION,
                    recipient_id=mention.target_id,
                    recipient_name=mention.target_name,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    message=format_mention_notification_message(
                        NotificationType.MENTION,
                        sender_name,
                        entity_type,
                        entity_name,
                    ),
                    link=generate_entity_link(entity_type, entity_id),
                )
                
                self._notifications[notification.id] = notification
                notifications.append(notification)
                
                # Mark mention as notified
                mention.notified = True
            
            elif mention.mention_type == MentionType.TEAM and mention.target_id:
                # For team mentions, notify all team members
                team = self.resolve_team(mention.target_id)
                if team:
                    for member_id in team.member_ids:
                        member = self.resolve_user(member_id)
                        if member:
                            notification = MentionNotification(
                                notification_type=NotificationType.MENTION,
                                recipient_id=member.id,
                                recipient_name=member.name,
                                sender_id=sender_id,
                                sender_name=sender_name,
                                entity_type=entity_type,
                                entity_id=entity_id,
                                entity_name=entity_name,
                                message=f"{sender_name} mentioned {team.name} team in {entity_type.value}: {entity_name}",
                                link=generate_entity_link(entity_type, entity_id),
                            )
                            
                            self._notifications[notification.id] = notification
                            notifications.append(notification)
                    
                    mention.notified = True
        
        return notifications
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def clear_all(self) -> None:
        """Clear all data (for testing)."""
        self._mentions.clear()
        self._assignments.clear()
        self._tasks.clear()
        self._notifications.clear()
        self._users.clear()
        self._teams.clear()
