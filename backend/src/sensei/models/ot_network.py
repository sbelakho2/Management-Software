"""OT Network Safety SQLAlchemy models.

Models for OT/IT network zone management and security:
- NetworkZone: Network segments (IT, OT, DMZ)
- ZoneViolation: Cross-zone policy violations
- EdgeCertificate: TLS certificates for edge controllers
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, AuditMixin

if TYPE_CHECKING:
    from .user import User


class ZoneType(str, Enum):
    """Network zone types."""
    IT = "it"
    OT = "ot"
    DMZ = "dmz"


class CertificateStatus(str, Enum):
    """Edge certificate status values."""
    ACTIVE = "active"
    PENDING_ROTATION = "pending_rotation"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ZoneViolationSeverity(str, Enum):
    """Security violation severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NetworkZone(Base, TimestampMixin, AuditMixin):
    """Network zone model for IT/OT segmentation.
    
    Represents a network segment with CIDR ranges and security policies.
    Zones are classified as IT, OT, or DMZ for policy enforcement.
    """
    
    __tablename__ = "network_zones"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(10), nullable=False)
    cidrs: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    source_violations: Mapped[list["ZoneViolation"]] = relationship(
        "ZoneViolation",
        foreign_keys="ZoneViolation.source_zone_id",
        back_populates="source_zone",
        cascade="all, delete-orphan",
    )
    dest_violations: Mapped[list["ZoneViolation"]] = relationship(
        "ZoneViolation",
        foreign_keys="ZoneViolation.dest_zone_id",
        back_populates="dest_zone",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<NetworkZone(id={self.id}, name={self.name!r}, type={self.zone_type})>"


class ZoneViolation(Base, TimestampMixin):
    """Security violation for cross-zone communication.
    
    Records detected policy violations when traffic crosses
    between zones that shouldn't communicate directly.
    """
    
    __tablename__ = "zone_violations"
    
    source_zone_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("network_zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    dest_zone_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("network_zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv6 max length
    dest_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    source_zone: Mapped["NetworkZone"] = relationship(
        "NetworkZone",
        foreign_keys=[source_zone_id],
        back_populates="source_violations",
    )
    dest_zone: Mapped["NetworkZone"] = relationship(
        "NetworkZone",
        foreign_keys=[dest_zone_id],
        back_populates="dest_violations",
    )
    acknowledged_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[acknowledged_by_id],
    )
    
    def __repr__(self) -> str:
        return f"<ZoneViolation(id={self.id}, {self.source_ip} -> {self.dest_ip}, severity={self.severity})>"


class EdgeCertificate(Base, TimestampMixin, AuditMixin):
    """TLS certificate for edge controllers.
    
    Tracks certificate lifecycle for edge/IoT devices that
    communicate between IT and OT networks.
    """
    
    __tablename__ = "edge_certificates"
    
    controller_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    subject_cn: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    not_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    fingerprint_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    def __repr__(self) -> str:
        return f"<EdgeCertificate(id={self.id}, controller={self.controller_id!r}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        from datetime import timezone
        return datetime.now(timezone.utc) > self.not_after
    
    @property
    def days_until_expiry(self) -> int:
        """Days until certificate expires (negative if already expired)."""
        from datetime import timezone
        delta = self.not_after - datetime.now(timezone.utc)
        return delta.days
