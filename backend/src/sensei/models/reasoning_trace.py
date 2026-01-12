"""Reasoning trace model.

Stores "Reasoning IDs" for entities without requiring schema changes in every
module table.

A Reasoning ID represents the AI suggestion / rationale thread that influenced
an entity's creation or update.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sensei.models.base import AuditMixin, Base, TimestampMixin


class ReasoningTrace(Base, TimestampMixin, AuditMixin):
    """Maps an entity (type,id) to one or more reasoning IDs."""

    __tablename__ = "reasoning_traces"

    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    reasoning_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    source: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "reasoning_id",
            name="uq_reasoning_trace_entity_reasoning",
        ),
        Index("ix_reasoning_trace_entity", "entity_type", "entity_id"),
        Index("ix_reasoning_trace_reasoning", "reasoning_id"),
    )
