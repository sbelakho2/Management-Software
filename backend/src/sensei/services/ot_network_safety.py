"""OT Network Safety (Development Plan 21.8 — OT/IT Hardening).

Implements:
- Network Zoning: detect connections/routes between IT/OT segments.
- Edge Certificate Rotation: track & rotate TLS certs for edge controllers.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from ipaddress import ip_network, IPv4Network, IPv6Network
from typing import Any, Iterable
from uuid import UUID, uuid4


class ZoneType(str, Enum):
    IT = "it"
    OT = "ot"
    DMZ = "dmz"


class CertificateStatus(str, Enum):
    ACTIVE = "active"
    PENDING_ROTATION = "pending_rotation"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ZoneViolationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_OT_ADMIN_ROLES: set[str] = {"admin", "secops", "it", "ops", "gm"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class NetworkZone:
    id: UUID
    name: str
    zone_type: ZoneType
    cidrs: list[str]
    description: str
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True)
class ZoneViolation:
    id: UUID
    source_zone_id: UUID
    dest_zone_id: UUID
    source_ip: str
    dest_ip: str
    severity: ZoneViolationSeverity
    detected_at: datetime
    acknowledged: bool


@dataclass
class EdgeCertificate:
    id: UUID
    controller_id: str  # Unique controller / edge node identifier.
    subject_cn: str
    issuer: str
    not_before: datetime
    not_after: datetime
    status: CertificateStatus
    created_at: datetime
    created_by: UUID
    rotated_at: datetime | None = None


class OTNetworkSafetyService:
    """In-memory OT network safety service."""

    def __init__(self) -> None:
        self._zones: dict[UUID, NetworkZone] = {}
        self._violations: dict[UUID, ZoneViolation] = {}
        self._certificates: dict[UUID, EdgeCertificate] = {}

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_OT_ADMIN_ROLES)) > 0

    # ---- Network Zones ----

    def create_zone(
        self,
        *,
        name: str,
        zone_type: ZoneType,
        cidrs: list[str],
        description: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> NetworkZone:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage network zones")

        # Validate CIDRs.
        for cidr in cidrs:
            ip_network(cidr, strict=False)

        zone = NetworkZone(
            id=uuid4(),
            name=name.strip(),
            zone_type=zone_type,
            cidrs=list(cidrs),
            description=description,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._zones[zone.id] = zone
        return zone

    def list_zones(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[NetworkZone]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view network zones")

        result = list(self._zones.values())
        result.sort(key=lambda z: z.name.lower())
        return result

    def _lookup_zone_for_ip(self, ip_str: str) -> NetworkZone | None:
        from ipaddress import ip_address
        try:
            addr = ip_address(ip_str)
        except ValueError:
            return None

        for zone in self._zones.values():
            for cidr in zone.cidrs:
                if addr in ip_network(cidr, strict=False):
                    return zone
        return None

    def detect_violation(
        self,
        *,
        source_ip: str,
        dest_ip: str,
    ) -> ZoneViolation | None:
        """Detect if traffic between IPs crosses IT/OT boundary illegally."""
        src_zone = self._lookup_zone_for_ip(source_ip)
        dst_zone = self._lookup_zone_for_ip(dest_ip)

        if not src_zone or not dst_zone:
            return None

        # IT → OT or OT → IT direct is violation; DMZ bridges are OK.
        if src_zone.zone_type == ZoneType.IT and dst_zone.zone_type == ZoneType.OT:
            severity = ZoneViolationSeverity.CRITICAL
        elif src_zone.zone_type == ZoneType.OT and dst_zone.zone_type == ZoneType.IT:
            severity = ZoneViolationSeverity.HIGH
        else:
            return None

        violation = ZoneViolation(
            id=uuid4(),
            source_zone_id=src_zone.id,
            dest_zone_id=dst_zone.id,
            source_ip=source_ip,
            dest_ip=dest_ip,
            severity=severity,
            detected_at=_utcnow(),
            acknowledged=False,
        )
        self._violations[violation.id] = violation
        return violation

    def list_violations(
        self,
        *,
        actor_roles: Iterable[str],
        only_unacknowledged: bool = False,
    ) -> list[ZoneViolation]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view zone violations")

        result = list(self._violations.values())
        if only_unacknowledged:
            result = [v for v in result if not v.acknowledged]
        result.sort(key=lambda v: v.detected_at, reverse=True)
        return result

    def acknowledge_violation(
        self,
        violation_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> ZoneViolation:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to acknowledge violations")
        if violation_id not in self._violations:
            raise KeyError("Violation not found")

        old = self._violations[violation_id]
        updated = ZoneViolation(
            id=old.id,
            source_zone_id=old.source_zone_id,
            dest_zone_id=old.dest_zone_id,
            source_ip=old.source_ip,
            dest_ip=old.dest_ip,
            severity=old.severity,
            detected_at=old.detected_at,
            acknowledged=True,
        )
        self._violations[violation_id] = updated
        return updated

    # ---- Edge Certificate Rotation ----

    def register_certificate(
        self,
        *,
        controller_id: str,
        subject_cn: str,
        issuer: str,
        not_before: datetime,
        not_after: datetime,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> EdgeCertificate:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage edge certificates")

        status = CertificateStatus.ACTIVE
        if _utcnow() > not_after:
            status = CertificateStatus.EXPIRED

        cert = EdgeCertificate(
            id=uuid4(),
            controller_id=controller_id.strip(),
            subject_cn=subject_cn,
            issuer=issuer,
            not_before=not_before,
            not_after=not_after,
            status=status,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._certificates[cert.id] = cert
        return cert

    def list_certificates(
        self,
        *,
        actor_roles: Iterable[str],
        controller_id: str | None = None,
    ) -> list[EdgeCertificate]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view edge certificates")

        result = list(self._certificates.values())
        if controller_id:
            result = [c for c in result if c.controller_id == controller_id]
        result.sort(key=lambda c: c.not_after)
        return result

    def get_expiring_certificates(
        self,
        *,
        actor_roles: Iterable[str],
        days_ahead: int = 30,
    ) -> list[EdgeCertificate]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view edge certificates")

        threshold = _utcnow() + timedelta(days=days_ahead)
        result: list[EdgeCertificate] = []
        for cert in self._certificates.values():
            if cert.status == CertificateStatus.ACTIVE and cert.not_after <= threshold:
                result.append(cert)
        result.sort(key=lambda c: c.not_after)
        return result

    def rotate_certificate(
        self,
        cert_id: UUID,
        *,
        new_not_after: datetime,
        actor_roles: Iterable[str],
    ) -> EdgeCertificate:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to rotate certificates")
        if cert_id not in self._certificates:
            raise KeyError("Certificate not found")

        old = self._certificates[cert_id]

        # Mark old as revoked.
        old.status = CertificateStatus.REVOKED

        # Create new certificate entry for same controller.
        new_cert = EdgeCertificate(
            id=uuid4(),
            controller_id=old.controller_id,
            subject_cn=old.subject_cn,
            issuer=old.issuer,
            not_before=_utcnow(),
            not_after=new_not_after,
            status=CertificateStatus.ACTIVE,
            created_at=_utcnow(),
            created_by=old.created_by,
            rotated_at=_utcnow(),
        )
        self._certificates[new_cert.id] = new_cert
        return new_cert
