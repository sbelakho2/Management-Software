"""
Database models for persisting service state.

These models replace in-memory storage in various services with database persistence,
ensuring data survives restarts and scales across multiple instances.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin, AuditMixin


# =============================================================================
# Saved Views Persistence
# =============================================================================

class SavedViewVisibility(str, Enum):
    """Visibility level for saved views."""
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


class SavedViewDB(Base, TimestampMixin, AuditMixin):
    """
    Persisted saved view / filter configuration.
    
    Stores user-created custom views for filtering and sorting entities.
    """
    
    __tablename__ = "saved_views"
    
    # View identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Entity type this view applies to
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Owner and visibility
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SavedViewVisibility.PRIVATE.value,
    )
    team_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    
    # View configuration (stored as JSON)
    conditions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # List of filter conditions, each with: field, operator, value, etc.
    
    sort_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # List of sort specifications: field, direction
    
    columns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Visible columns configuration
    
    # UI metadata
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Favorites
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        Index("ix_saved_views_owner_entity", owner_id, entity_type),
        Index("ix_saved_views_visibility", visibility),
    )


# =============================================================================
# Autosave Drafts Persistence
# =============================================================================

class DraftTypeDB(str, Enum):
    """Types of drafts."""
    FORM = "form"
    ENTITY_EDIT = "entity_edit"
    NEW_ENTITY = "new_entity"
    COMMENT = "comment"
    RICH_TEXT = "rich_text"


class DraftStatusDB(str, Enum):
    """Draft status."""
    ACTIVE = "active"
    SUBMITTED = "submitted"
    DISCARDED = "discarded"
    EXPIRED = "expired"
    RECOVERED = "recovered"


class DraftDB(Base, TimestampMixin):
    """
    Persisted autosave draft.
    
    Stores work-in-progress data to prevent data loss.
    """
    
    __tablename__ = "autosave_drafts"
    
    # Draft type and status
    draft_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DraftStatusDB.ACTIVE.value,
        index=True,
    )
    
    # Owner
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Related entity (if editing existing)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    
    # Session/form context
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    form_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    route: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Content
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Versioning
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    base_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Expiry
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Recovery
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    __table_args__ = (
        Index("ix_drafts_user_entity", user_id, entity_type, entity_id),
        Index("ix_drafts_user_active", user_id, status),
        Index("ix_drafts_expires", expires_at, postgresql_where=(status == DraftStatusDB.ACTIVE.value)),
    )


class DraftVersionDB(Base, TimestampMixin):
    """
    Draft version history.
    
    Tracks all versions of a draft for recovery.
    """
    
    __tablename__ = "autosave_draft_versions"
    
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("autosave_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # How this version was saved
    auto_saved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    save_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Field changes
    changed_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("draft_id", "version_number", name="uq_draft_version"),
    )


# =============================================================================
# Support Inbox Persistence
# =============================================================================

class TicketPriorityDB(str, Enum):
    """Support ticket priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketStatusDB(str, Enum):
    """Support ticket status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_USER = "waiting_on_user"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicketDB(Base, TimestampMixin, AuditMixin):
    """
    Support ticket for user issues.
    """
    
    __tablename__ = "support_tickets"
    
    # Ticket info
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Status and priority
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=TicketStatusDB.OPEN.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TicketPriorityDB.MEDIUM.value,
        index=True,
    )
    
    # Reporter
    reporter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Assignment
    assignee_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    
    # SLA tracking
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Response tracking
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Escalation
    escalation_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Context
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # app, email, chat
    
    # Metadata
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    __table_args__ = (
        Index("ix_tickets_status_priority", status, priority),
        Index("ix_tickets_sla", sla_due_at, sla_breached),
    )


class TicketCommentDB(Base, TimestampMixin):
    """
    Comment on a support ticket.
    """
    
    __tablename__ = "support_ticket_comments"
    
    ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    author_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_resolution: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UserFeedbackDB(Base, TimestampMixin):
    """
    User feedback submission.
    """
    
    __tablename__ = "user_feedback"
    
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)  # bug, feature, improvement
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context
    page_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    feature_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Processing
    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False)
    linked_ticket_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="SET NULL"),
        nullable=True,
    )


class RoutingRuleDB(Base, TimestampMixin):
    """
    Ticket routing rule configuration.
    """
    
    __tablename__ = "support_routing_rules"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Conditions and target (JSON for flexibility)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    target: Mapped[str] = mapped_column(String(50), nullable=False)  # a3_lite, task, escalation, auto_response
    target_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class A3LiteRecordDB(Base, TimestampMixin, AuditMixin):
    """
    Lightweight A3 problem record created from a support ticket.
    """
    
    __tablename__ = "a3_lite_records"
    
    source_ticket_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    problem_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    countermeasures: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    owner_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# =============================================================================
# Escalation Policy Persistence
# =============================================================================

class EscalationPolicyDB(Base, TimestampMixin, AuditMixin):
    """
    Custom escalation policy configuration.
    """
    
    __tablename__ = "escalation_policies"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # quote_approval, risk, andon, task, etc.
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Conditions to trigger this policy (JSON)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # Escalation levels configuration (JSON array)
    escalation_levels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Each level: { level: "L1", wait_hours: 24, escalate_to_role: "team_lead", notifications: [...] }
    
    # Options
    auto_create_task: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_channels: Mapped[list | None] = mapped_column(JSONB, nullable=True)


class EscalationThresholdDB(Base, TimestampMixin):
    """
    Custom escalation thresholds per entity type.
    """
    
    __tablename__ = "escalation_thresholds"
    
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_key: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Threshold values
    value_numeric: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    value_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("entity_type", "threshold_key", name="uq_escalation_threshold"),
    )


# =============================================================================
# Mentions & Assignments Persistence
# =============================================================================

class MentionDB(Base, TimestampMixin):
    """
    @mention in a comment or description.
    """
    
    __tablename__ = "mentions"
    
    # Who was mentioned
    mentioned_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Who created the mention
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Context
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # comment, task, a3, etc.
    source_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Related entity
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("ix_mentions_user_unread", mentioned_user_id, is_read),
        Index("ix_mentions_source", source_type, source_id),
    )


class AssignmentDB(Base, TimestampMixin, AuditMixin):
    """
    Entity assignment tracking.
    """
    
    __tablename__ = "entity_assignments"
    
    # What is assigned
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Who is assigned
    assignee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # user, team
    
    # Assignment details
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)  # owner, reviewer, collaborator
    
    # Status
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Due date
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index("ix_assignments_entity", entity_type, entity_id),
        Index("ix_assignments_assignee_active", assignee_id, status),
    )


class TaskFromCommentDB(Base, TimestampMixin):
    """
    Task created from a comment mention.
    """
    
    __tablename__ = "tasks_from_comments"
    
    # Link to actual task
    task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Source comment
    source_comment_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Extracted info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    assignee_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)


# =============================================================================
# Smart Ingestion Persistence
# =============================================================================

class IngestionJobDB(Base, TimestampMixin):
    """
    Smart ingestion job tracking.
    """
    
    __tablename__ = "smart_ingestion_jobs"
    
    # Job identity
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # email, document, file
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    
    # Source info
    source_id: Mapped[str | None] = mapped_column(String(500), nullable=True)  # email ID, file path, etc.
    source_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Processing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Results
    extracted_entities: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_entity_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # User context
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class IngestionDocumentDB(Base, TimestampMixin):
    """
    Document metadata for smart ingestion.
    """
    
    __tablename__ = "smart_ingestion_documents"
    
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("smart_ingestion_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Document info
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Storage location (path or S3 key)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # Processing status
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Extracted data
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
