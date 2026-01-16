from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sensei.models.base import Base, TimestampMixin, AuditMixin


class Site(Base, TimestampMixin, AuditMixin):
    """
    Manufacturing site registry.
    """
    __tablename__ = "sites"

    site_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
