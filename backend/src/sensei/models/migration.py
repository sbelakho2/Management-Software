"""
Data migration and import models.
"""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    Boolean,
    Integer,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from sensei.models.base import Base, TimestampMixin


class ImportBatch(Base, TimestampMixin):
    """
    A batch of imported data.
    """
    __tablename__ = "import_batches"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    imported_by: Mapped[str] = mapped_column(String(255), nullable=False)
    error_log: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
