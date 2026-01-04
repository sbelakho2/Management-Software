"""
Base model with common functionality for all SQLAlchemy models.

Provides:
- TimestampMixin: created_at, updated_at fields with auto-update
- AuditMixin: created_by, updated_by, owner fields for tracking ownership
- Base: declarative base with common configurations
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, event, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
)


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Provides:
    - UUID primary key
    - Async attribute access
    - Common type annotations
    """
    
    type_annotation_map = {
        UUID: PGUUID(as_uuid=True),
    }
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    
    def __repr__(self) -> str:
        """Generate a string representation of the model."""
        class_name = self.__class__.__name__
        attrs = []
        for col in self.__table__.columns:
            value = getattr(self, col.name, None)
            if col.name == "id":
                attrs.insert(0, f"id={value}")
            elif col.primary_key or col.name in ("name", "title", "email", "username"):
                attrs.append(f"{col.name}={value!r}")
        return f"<{class_name}({', '.join(attrs)})>"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        for col in self.__table__.columns:
            value = getattr(self, col.name, None)
            if isinstance(value, UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[col.name] = value
        return result


class TimestampMixin:
    """
    Mixin providing created_at and updated_at timestamp fields.
    
    - created_at: Set automatically on insert
    - updated_at: Updated automatically on every update
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin:
    """
    Mixin providing ownership and audit trail fields.
    
    - created_by_id: User who created the record
    - updated_by_id: User who last updated the record
    - owner_id: User who owns/is responsible for the record
    """
    
    @declared_attr
    def created_by_id(cls) -> Mapped[UUID | None]:
        return mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )
    
    @declared_attr
    def updated_by_id(cls) -> Mapped[UUID | None]:
        return mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )
    
    @declared_attr
    def owner_id(cls) -> Mapped[UUID | None]:
        return mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )


class SoftDeleteMixin:
    """
    Mixin providing soft delete functionality.
    
    - deleted_at: Timestamp when record was soft-deleted
    - deleted_by_id: User who deleted the record
    - is_deleted: Computed property to check if record is deleted
    """
    
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    
    @declared_attr
    def deleted_by_id(cls) -> Mapped[UUID | None]:
        return mapped_column(
            PGUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record has been soft-deleted."""
        return self.deleted_at is not None


class StatusMixin:
    """
    Mixin providing status field with common workflow states.
    """
    
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="draft",
        index=True,
    )


def generate_ulid() -> str:
    """
    Generate a ULID-style identifier.
    
    ULIDs are lexicographically sortable unique identifiers.
    Format: timestamp (10 chars) + randomness (16 chars)
    """
    import time
    import secrets
    
    # Crockford's Base32 alphabet
    ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    
    # Timestamp component (48 bits = 10 chars)
    timestamp_ms = int(time.time() * 1000)
    timestamp_chars = ""
    for _ in range(10):
        timestamp_chars = ENCODING[timestamp_ms & 0x1F] + timestamp_chars
        timestamp_ms >>= 5
    
    # Randomness component (80 bits = 16 chars)
    random_bytes = secrets.token_bytes(10)
    random_int = int.from_bytes(random_bytes, "big")
    random_chars = ""
    for _ in range(16):
        random_chars = ENCODING[random_int & 0x1F] + random_chars
        random_int >>= 5
    
    return timestamp_chars + random_chars
