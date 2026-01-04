"""
Audit log model for tracking all changes.

Implements:
- AuditLog: Comprehensive audit trail for all entity changes
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base


class AuditAction(str, Enum):
    """Type of audit action."""
    
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    LOGIN = "login"
    LOGOUT = "logout"
    FAILED_LOGIN = "failed_login"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    STATUS_CHANGE = "status_change"
    APPROVAL = "approval"
    REJECTION = "rejection"


class AuditLog(Base):
    """
    Audit log entry.
    
    Tracks all significant changes to entities in the system.
    Designed for compliance, debugging, and data recovery.
    """
    
    __tablename__ = "audit_logs"
    
    # Timestamp (not using TimestampMixin as we don't need updated_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # What was changed
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    # Action performed
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Who performed the action
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Stored separately in case user is deleted
    
    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    # Change details
    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changed_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Additional context
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # For status changes
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Relationship to user
    user: Mapped["User | None"] = relationship("User")
    
    __table_args__ = (
        Index("ix_audit_logs_entity", entity_type, entity_id),
        Index("ix_audit_logs_user_created", user_id, created_at.desc()),
        Index("ix_audit_logs_entity_created", entity_type, entity_id, created_at.desc()),
        Index("ix_audit_logs_action_created", action, created_at.desc()),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, entity={self.entity_type}:{self.entity_id}, "
            f"action={self.action}, user={self.user_email})>"
        )
    
    @classmethod
    def create_log(
        cls,
        entity_type: str,
        entity_id: UUID,
        action: str,
        user_id: UUID | None = None,
        user_email: str | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> "AuditLog":
        """
        Factory method to create an audit log entry.
        
        Automatically calculates changed_fields from old_values and new_values.
        """
        changed_fields = None
        if old_values and new_values:
            changed_fields = [
                key
                for key in set(old_values.keys()) | set(new_values.keys())
                if old_values.get(key) != new_values.get(key)
            ]
        
        old_status = None
        new_status = None
        if old_values and "status" in old_values:
            old_status = old_values["status"]
        if new_values and "status" in new_values:
            new_status = new_values["status"]
        
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            user_email=user_email,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            old_status=old_status,
            new_status=new_status,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            description=description,
            metadata=metadata,
        )


# Import User here to avoid circular import issues
from sensei.models.user import User  # noqa: E402, F401
