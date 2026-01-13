"""OT Network Safety (Development Plan 21.8 — OT/IT Hardening).

Implements:
- Network Zoning: detect connections/routes between IT/OT segments.
- Edge Certificate Rotation: track & rotate TLS certs for edge controllers.

This module provides:
- In-memory OTNetworkSafetyService for testing/development
- Re-exports of database-backed DBOTNetworkSafetyService for production
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Sequence
from uuid import UUID, uuid4

if TYPE_CHECKING:
    pass


class ZoneType(str, Enum):
    """Network zone type."""
    IT = "IT"
    OT = "OT"
    DMZ = "DMZ"


class ZoneViolationSeverity(str, Enum):
    """Severity of zone violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CertificateStatus(str, Enum):
    """Certificate status."""
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class NetworkZone:
    """Network zone definition."""
    id: UUID
    name: str
    zone_type: ZoneType
    cidrs: list[str]
    mac_addresses: list[str] = field(default_factory=list)
    allowed_protocols: list[str] = field(default_factory=list)
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = None


@dataclass
class ZoneViolation:
    """Record of a zone violation."""
    id: UUID
    source_ip: str
    dest_ip: str
    source_zone_id: UUID
    dest_zone_id: UUID
    severity: ZoneViolationSeverity
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    acknowledged_by: UUID | None = None


@dataclass
class EdgeCertificate:
    """Certificate for edge controllers."""
    id: UUID
    controller_id: str
    subject_cn: str
    issuer: str
    not_before: datetime
    not_after: datetime
    status: CertificateStatus = CertificateStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID | None = None
    rotated_at: datetime | None = None
    rotated_by: UUID | None = None


class OTNetworkSafetyService:
    """In-memory OT Network Safety service for testing/development."""
    
    # Roles that can manage zones
    ZONE_ADMIN_ROLES = ("admin", "ops", "security")
    # Roles that can view data
    VIEW_ROLES = ("admin", "ops", "security", "viewer")
    
    def __init__(self) -> None:
        self._zones: dict[UUID, NetworkZone] = {}
        self._violations: dict[UUID, ZoneViolation] = {}
        self._certificates: dict[UUID, EdgeCertificate] = {}
    
    def _check_zone_admin(self, actor_roles: Sequence[str]) -> None:
        """Check if actor has zone admin role."""
        if not any(r in self.ZONE_ADMIN_ROLES for r in actor_roles):
            raise PermissionError("Zone admin role required")
    
    def _check_viewer(self, actor_roles: Sequence[str]) -> None:
        """Check if actor has viewer role."""
        if not any(r in self.VIEW_ROLES for r in actor_roles):
            raise PermissionError("Viewer role required")
    
    def _ip_in_zone(self, ip: str, zone: NetworkZone) -> bool:
        """Check if IP is within zone CIDRs."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for cidr in zone.cidrs:
                if ip_obj in ipaddress.ip_network(cidr, strict=False):
                    return True
        except ValueError:
            pass
        return False
    
    def _find_zone_for_ip(self, ip: str) -> NetworkZone | None:
        """Find which zone an IP belongs to."""
        for zone in self._zones.values():
            if self._ip_in_zone(ip, zone):
                return zone
        return None
    
    # --------------------------------------------------------------------------
    # Zone Management
    # --------------------------------------------------------------------------
    
    def create_zone(
        self,
        name: str,
        zone_type: ZoneType,
        cidrs: list[str],
        description: str,
        actor_user_id: UUID,
        actor_roles: Sequence[str],
    ) -> NetworkZone:
        """Create a network zone."""
        self._check_zone_admin(actor_roles)
        
        zone = NetworkZone(
            id=uuid4(),
            name=name,
            zone_type=zone_type,
            cidrs=cidrs,
            description=description,
            created_by=actor_user_id,
        )
        self._zones[zone.id] = zone
        return zone
    
    def list_zones(self, actor_roles: Sequence[str]) -> list[NetworkZone]:
        """List all network zones."""
        self._check_viewer(actor_roles)
        return list(self._zones.values())
    
    def get_zone(self, zone_id: UUID, actor_roles: Sequence[str]) -> NetworkZone | None:
        """Get a zone by ID."""
        self._check_viewer(actor_roles)
        return self._zones.get(zone_id)
    
    def delete_zone(
        self,
        zone_id: UUID,
        actor_roles: Sequence[str],
    ) -> bool:
        """Delete a zone."""
        self._check_zone_admin(actor_roles)
        if zone_id in self._zones:
            del self._zones[zone_id]
            return True
        return False
    
    # --------------------------------------------------------------------------
    # Violation Detection
    # --------------------------------------------------------------------------
    
    def detect_violation(
        self,
        source_ip: str,
        dest_ip: str,
        source_mac: str | None = None,
        dest_mac: str | None = None,
        protocol: str | None = None,
    ) -> ZoneViolation | None:
        """Detect and record a zone violation with multi-factor identification."""
        source_zone = self._find_zone_for_ip(source_ip)
        if not source_zone and source_mac:
            source_zone = self._find_zone_for_mac(source_mac)

        dest_zone = self._find_zone_for_ip(dest_ip)
        if not dest_zone and dest_mac:
            dest_zone = self._find_zone_for_mac(dest_mac)

        if not source_zone or not dest_zone:
            return None

        # Same zone is always allowed.
        if source_zone.id == dest_zone.id:
            return None

        # Cross-zone rules.
        violation_severity: ZoneViolationSeverity | None = None

        # IT to OT is critical.
        if source_zone.zone_type == ZoneType.IT and dest_zone.zone_type == ZoneType.OT:
            violation_severity = ZoneViolationSeverity.CRITICAL
            # Allow specific OT protocols even if zones differ (e.g., jump host)
            if protocol and protocol.upper() in [p.upper() for p in dest_zone.allowed_protocols]:
                violation_severity = None

        # OT to IT is highly suspicious (exfiltration risk).
        elif source_zone.zone_type == ZoneType.OT and dest_zone.zone_type == ZoneType.IT:
            violation_severity = ZoneViolationSeverity.HIGH

        # Any cross-zone without DMZ.
        elif dest_zone.zone_type == ZoneType.DMZ or source_zone.zone_type == ZoneType.DMZ:
            violation_severity = ZoneViolationSeverity.MEDIUM
        else:
            violation_severity = ZoneViolationSeverity.LOW

        if not violation_severity:
            return None

        violation = ZoneViolation(
            id=uuid4(),
            source_ip=source_ip,
            dest_ip=dest_ip,
            source_zone_id=source_zone.id,
            dest_zone_id=dest_zone.id,
            severity=violation_severity,
        )

        self._violations[violation.id] = violation
        return violation

    def _find_zone_for_mac(self, mac: str) -> NetworkZone | None:
        """Find zone containing a MAC address."""
        for zone in self._zones.values():
            if mac.upper() in [m.upper() for m in zone.mac_addresses]:
                return zone
        return None
    
    def list_violations(
        self,
        actor_roles: Sequence[str],
        only_unacknowledged: bool = False,
    ) -> list[ZoneViolation]:
        """List violations."""
        self._check_viewer(actor_roles)
        violations = list(self._violations.values())
        if only_unacknowledged:
            violations = [v for v in violations if not v.acknowledged]
        return violations
    
    def acknowledge_violation(
        self,
        violation_id: UUID,
        actor_roles: Sequence[str],
        actor_user_id: UUID | None = None,
    ) -> bool:
        """Acknowledge a violation."""
        self._check_zone_admin(actor_roles)
        if violation_id in self._violations:
            v = self._violations[violation_id]
            v.acknowledged = True
            v.acknowledged_at = datetime.now(timezone.utc)
            v.acknowledged_by = actor_user_id
            return True
        return False
    
    # --------------------------------------------------------------------------
    # Certificate Management
    # --------------------------------------------------------------------------
    
    def register_certificate(
        self,
        controller_id: str,
        subject_cn: str,
        issuer: str,
        not_before: datetime,
        not_after: datetime,
        actor_user_id: UUID,
        actor_roles: Sequence[str],
    ) -> EdgeCertificate:
        """Register an edge controller certificate."""
        self._check_zone_admin(actor_roles)
        
        cert = EdgeCertificate(
            id=uuid4(),
            controller_id=controller_id,
            subject_cn=subject_cn,
            issuer=issuer,
            not_before=not_before,
            not_after=not_after,
            created_by=actor_user_id,
        )
        self._certificates[cert.id] = cert
        return cert
    
    def list_certificates(
        self,
        actor_roles: Sequence[str],
    ) -> list[EdgeCertificate]:
        """List all certificates."""
        self._check_viewer(actor_roles)
        return list(self._certificates.values())
    
    def get_expiring_certificates(
        self,
        actor_roles: Sequence[str],
        days_ahead: int = 30,
    ) -> list[EdgeCertificate]:
        """Get certificates expiring soon."""
        self._check_viewer(actor_roles)
        threshold = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        return [
            c for c in self._certificates.values()
            if c.status == CertificateStatus.ACTIVE and c.not_after <= threshold
        ]
    
    def rotate_certificate(
        self,
        cert_id: UUID,
        new_not_after: datetime,
        actor_roles: Sequence[str],
        actor_user_id: UUID | None = None,
    ) -> EdgeCertificate:
        """Rotate a certificate."""
        self._check_zone_admin(actor_roles)
        
        old_cert = self._certificates.get(cert_id)
        if not old_cert:
            raise ValueError(f"Certificate {cert_id} not found")
        
        # Revoke old cert
        old_cert.status = CertificateStatus.REVOKED
        
        # Create new cert
        new_cert = EdgeCertificate(
            id=uuid4(),
            controller_id=old_cert.controller_id,
            subject_cn=old_cert.subject_cn,
            issuer=old_cert.issuer,
            not_before=datetime.now(timezone.utc),
            not_after=new_not_after,
            created_by=actor_user_id,
            rotated_at=datetime.now(timezone.utc),
            rotated_by=actor_user_id,
        )
        self._certificates[new_cert.id] = new_cert
        return new_cert


# Re-export database-backed service for production use
from sensei.services.ot_network_safety_db import (
    OTNetworkSafetyService as DBOTNetworkSafetyService,
    get_ot_network_safety_service,
)

__all__ = [
    # In-memory service (for testing)
    "OTNetworkSafetyService",
    # Database-backed service (for production)
    "DBOTNetworkSafetyService",
    "get_ot_network_safety_service",
    # Data classes
    "NetworkZone",
    "ZoneViolation",
    "EdgeCertificate",
    # Enums
    "ZoneType",
    "CertificateStatus",
    "ZoneViolationSeverity",
]
