"""
SQLAlchemy models for PII (Personally Identifiable Information) management.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sensei.models.base import Base, TimestampMixin


class PIIField(Base, TimestampMixin):
    """Definition of a PII field."""
    __tablename__ = "pii_fields"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # PIICategory
    sensitivity: Mapped[str] = mapped_column(String(50), nullable=False)  # SensitivityLevel
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection_pattern: Mapped[str | None] = mapped_column(String(500), nullable=True)
    masking_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MaskingType
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_types: Mapped[list] = mapped_column(JSONB, default=list)  # list[ConsentType]
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_exportable: Mapped[bool] = mapped_column(Boolean, default=True)


class DataSubject(Base, TimestampMixin):
    """A data subject (person whose PII is stored)."""
    __tablename__ = "pii_data_subjects"

    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, customer, etc.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deletion_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    consents: Mapped[list["Consent"]] = relationship("Consent", back_populates="subject", cascade="all, delete-orphan")
    access_logs: Mapped[list["PIIAccessLog"]] = relationship("PIIAccessLog", back_populates="subject", cascade="all, delete-orphan")


class Consent(Base, TimestampMixin):
    """Consent record for a data subject."""
    __tablename__ = "pii_consents"

    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pii_data_subjects.id", ondelete="CASCADE"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ConsentType
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # ConsentStatus
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(200), nullable=False)  # How consent was obtained
    version: Mapped[str] = mapped_column(String(50), nullable=False)  # Version of privacy policy
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    subject: Mapped["DataSubject"] = relationship("DataSubject", back_populates="consents")


class PIIAccessLog(Base):
    """Log of PII data access."""
    __tablename__ = "pii_access_logs"

    # Not using TimestampMixin, using accessed_at instead
    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pii_data_subjects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    field_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pii_fields.id", ondelete="CASCADE"), nullable=False)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # PIIAccessType
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    data_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # Masked snapshot

    subject: Mapped["DataSubject"] = relationship("DataSubject", back_populates="access_logs")


class DeletionRequest(Base, TimestampMixin):
    """Request to delete PII data."""
    __tablename__ = "pii_deletion_requests"

    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pii_data_subjects.id", ondelete="CASCADE"), nullable=False)
    requested_by_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    affected_tables: Mapped[list] = mapped_column(JSONB, default=list)
    deleted_records: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
