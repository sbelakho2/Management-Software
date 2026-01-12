"""Data lineage models.

Provides a minimal, generic representation of cross-module entity relationships.

The goal is to support lineage graphs like:
RFQ -> Quote -> Work Order -> Non-Conformance

We store entity IDs as strings to support heterogeneous primary key types
(UUIDs, ints, etc.) across modules.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sensei.models.base import AuditMixin, Base, TimestampMixin


class DataLineageLink(Base, TimestampMixin, AuditMixin):
    """Directed relationship between two entities."""

    __tablename__ = "data_lineage_links"

    source_entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_entity_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    target_entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    reasoning_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    # "metadata" is reserved by SQLAlchemy's declarative API; keep column name but use a different attribute.
    link_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_entity_type",
            "source_entity_id",
            "relationship_type",
            "target_entity_type",
            "target_entity_id",
            name="uq_data_lineage_link",
        ),
        Index(
            "ix_data_lineage_link_source",
            "source_entity_type",
            "source_entity_id",
            "created_at",
        ),
        Index(
            "ix_data_lineage_link_target",
            "target_entity_type",
            "target_entity_id",
            "created_at",
        ),
    )
