"""
User, Role, and Permission models for authentication and authorization.

Implements RBAC with:
- User: Core user entity with authentication fields
- Role: Named roles (GM, Sales Engineer, Estimator, Quality, Supply Chain, Ops, Exec)
- Permission: Fine-grained permissions for resources and actions
- UserRole: Many-to-many relationship between users and roles
- RolePermission: Many-to-many relationship between roles and permissions
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from sensei.models.task import Notification, Task


class UserStatus(str, Enum):
    """User account status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    LOCKED = "locked"


class RoleType(str, Enum):
    """Predefined role types."""
    
    ADMIN = "admin"
    GM = "gm"
    SALES_ENGINEER = "sales_engineer"
    ESTIMATOR = "estimator"
    QUALITY = "quality"
    SUPPLY_CHAIN = "supply_chain"
    OPS = "ops"
    EXEC = "exec"
    VIEWER = "viewer"


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User account model.
    
    Stores authentication credentials, profile information, and preferences.
    Supports soft delete for data retention requirements.
    """
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Status & Security
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserStatus.PENDING.value,
        index=True,
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 2FA
    totp_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    backup_codes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    
    # Session tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Password management
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Preferences
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    locale: Mapped[str] = mapped_column(String(10), default="fr", nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="Africa/Casablanca",
        nullable=False,
    )
    
    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    tasks_assigned: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="Task.assignee_id",
        back_populates="assignee",
        lazy="dynamic",
    )
    
    tasks_created: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="Task.created_by_id",
        back_populates="creator",
        lazy="dynamic",
    )
    
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email)),
        Index("ix_users_full_name", first_name, last_name),
        Index("ix_users_status_active", status, postgresql_where=(status == "active")),
    )
    
    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        if self.display_name:
            return self.display_name
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        """Check if the user account is active."""
        return self.status == UserStatus.ACTIVE.value and not self.is_deleted
    
    @property
    def is_locked(self) -> bool:
        """Check if the account is locked."""
        if self.locked_until is None:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) < self.locked_until
    
    def get_role_names(self) -> list[str]:
        """Get list of role names for this user."""
        return [ur.role.name for ur in self.roles if ur.role]


class Role(Base, TimestampMixin):
    """
    Role definition for RBAC.
    
    Roles group permissions and are assigned to users.
    """
    
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Role type for predefined roles
    role_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    
    # Is this a system role that cannot be deleted?
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Is this role active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Role hierarchy level (lower = more privileged)
    hierarchy_level: Mapped[int] = mapped_column(default=100, nullable=False)
    
    # Relationships
    users: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    def get_permission_names(self) -> list[str]:
        """Get list of permission names for this role."""
        return [rp.permission.name for rp in self.permissions if rp.permission]


class Permission(Base, TimestampMixin):
    """
    Fine-grained permission definition.
    
    Permissions define what actions can be performed on which resources.
    Format: resource:action (e.g., "quotes:create", "rfq:approve")
    """
    
    __tablename__ = "permissions"
    
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Resource and action components
    resource: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Is this a system permission that cannot be deleted?
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    roles: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    
    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
        Index("ix_permissions_resource_action", resource, action),
    )


class UserRole(Base, TimestampMixin):
    """
    Many-to-many relationship between users and roles.
    
    Allows additional metadata like assignment date and expiration.
    """
    
    __tablename__ = "user_roles"
    
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # When was this role assigned?
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Who assigned this role?
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Optional expiration for temporary role assignments
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Is this assignment active?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    assigned_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_by_id],
    )
    
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("ix_user_roles_user_id", user_id),
        Index("ix_user_roles_role_id", role_id),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if the role assignment has expired."""
        if self.expires_at is None:
            return False
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.expires_at


class RolePermission(Base, TimestampMixin):
    """
    Many-to-many relationship between roles and permissions.
    """
    
    __tablename__ = "role_permissions"
    
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Optional conditions for this permission (e.g., field-level restrictions)
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="roles")
    
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        Index("ix_role_permissions_role_id", role_id),
        Index("ix_role_permissions_permission_id", permission_id),
    )


class RefreshToken(Base, TimestampMixin):
    """
    Refresh token storage for JWT authentication.
    
    Stores refresh tokens with device information for session management.
    """
    
    __tablename__ = "refresh_tokens"
    
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    
    # Token metadata
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Device/session information
    device_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Revocation
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    # Relationship
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("ix_refresh_tokens_user_id_expires", user_id, expires_at),
        Index(
            "ix_refresh_tokens_valid",
            user_id,
            postgresql_where=(is_revoked == False),  # noqa: E712
        ),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        from datetime import timezone as tz
        return datetime.now(tz.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked
