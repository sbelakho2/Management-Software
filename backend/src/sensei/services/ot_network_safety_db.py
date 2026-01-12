"""OT Network Safety Service (Development Plan 21.8 — OT/IT Hardening).

Database-backed implementation for production use.

Implements:
- Network Zoning: detect connections/routes between IT/OT segments.
- Edge Certificate Rotation: track & rotate TLS certs for edge controllers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
from typing import Iterable, Sequence
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.ot_network import (
    NetworkZone,
    ZoneViolation,
    EdgeCertificate,
    ZoneType,
    CertificateStatus,
    ZoneViolationSeverity,
)


_OT_ADMIN_ROLES: set[str] = {"admin", "secops", "it", "ops", "gm"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    """Normalize role names to lowercase set."""
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class OTNetworkSafetyService:
    """Database-backed OT network safety service.
    
    Provides network zoning, violation detection, and certificate
    management for IT/OT security boundary enforcement.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        self._session = session

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        """Check if actor has administrative privileges.
        
        Args:
            actor_roles: Roles assigned to the current user
            
        Returns:
            True if user can administer OT network settings
        """
        return len(_norm_roles(actor_roles).intersection(_OT_ADMIN_ROLES)) > 0

    # ---- Network Zones ----

    async def create_zone(
        self,
        *,
        name: str,
        zone_type: ZoneType,
        cidrs: list[str],
        description: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> NetworkZone:
        """Create a new network zone.
        
        Args:
            name: Human-readable zone name
            zone_type: IT, OT, or DMZ classification
            cidrs: List of CIDR ranges in this zone
            description: Zone description
            actor_user_id: ID of user creating the zone
            actor_roles: Roles of the creating user
            
        Returns:
            Created NetworkZone instance
            
        Raises:
            PermissionError: If user lacks admin privileges
            ValueError: If CIDR validation fails
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage network zones")

        # Validate CIDRs
        for cidr in cidrs:
            try:
                ip_network(cidr, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid CIDR '{cidr}': {e}")

        zone = NetworkZone(
            name=name.strip(),
            zone_type=zone_type.value,
            cidrs=list(cidrs),
            description=description,
            created_by_id=actor_user_id,
        )
        self._session.add(zone)
        await self._session.flush()
        await self._session.refresh(zone)
        return zone

    async def get_zone(self, zone_id: UUID) -> NetworkZone | None:
        """Get a network zone by ID.
        
        Args:
            zone_id: UUID of the zone
            
        Returns:
            NetworkZone if found, None otherwise
        """
        result = await self._session.execute(
            select(NetworkZone).where(NetworkZone.id == zone_id)
        )
        return result.scalar_one_or_none()

    async def list_zones(
        self,
        *,
        actor_roles: Iterable[str],
        include_inactive: bool = False,
    ) -> Sequence[NetworkZone]:
        """List all network zones.
        
        Args:
            actor_roles: Roles of the requesting user
            include_inactive: Whether to include inactive zones
            
        Returns:
            List of NetworkZone instances
            
        Raises:
            PermissionError: If user lacks admin privileges
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view network zones")

        query = select(NetworkZone).order_by(NetworkZone.name)
        if not include_inactive:
            query = query.where(NetworkZone.is_active == True)
        
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update_zone(
        self,
        zone_id: UUID,
        *,
        actor_roles: Iterable[str],
        name: str | None = None,
        zone_type: ZoneType | None = None,
        cidrs: list[str] | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> NetworkZone:
        """Update an existing network zone.
        
        Args:
            zone_id: ID of zone to update
            actor_roles: Roles of the updating user
            name: New zone name (optional)
            zone_type: New zone type (optional)
            cidrs: New CIDR list (optional)
            description: New description (optional)
            is_active: Active status (optional)
            
        Returns:
            Updated NetworkZone instance
            
        Raises:
            PermissionError: If user lacks admin privileges
            KeyError: If zone not found
            ValueError: If CIDR validation fails
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage network zones")

        zone = await self.get_zone(zone_id)
        if not zone:
            raise KeyError("Network zone not found")

        if name is not None:
            zone.name = name.strip()
        if zone_type is not None:
            zone.zone_type = zone_type.value
        if cidrs is not None:
            for cidr in cidrs:
                try:
                    ip_network(cidr, strict=False)
                except ValueError as e:
                    raise ValueError(f"Invalid CIDR '{cidr}': {e}")
            zone.cidrs = list(cidrs)
        if description is not None:
            zone.description = description
        if is_active is not None:
            zone.is_active = is_active

        await self._session.flush()
        await self._session.refresh(zone)
        return zone

    async def delete_zone(
        self,
        zone_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> None:
        """Delete a network zone.
        
        Args:
            zone_id: ID of zone to delete
            actor_roles: Roles of the deleting user
            
        Raises:
            PermissionError: If user lacks admin privileges
            KeyError: If zone not found
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage network zones")

        zone = await self.get_zone(zone_id)
        if not zone:
            raise KeyError("Network zone not found")

        await self._session.delete(zone)
        await self._session.flush()

    async def _lookup_zone_for_ip(self, ip_str: str) -> NetworkZone | None:
        """Find the network zone containing an IP address.
        
        Args:
            ip_str: IP address string to look up
            
        Returns:
            NetworkZone containing the IP, or None
        """
        try:
            addr = ip_address(ip_str)
        except ValueError:
            return None

        # Get all active zones
        result = await self._session.execute(
            select(NetworkZone).where(NetworkZone.is_active == True)
        )
        zones = result.scalars().all()

        for zone in zones:
            for cidr in zone.cidrs:
                if addr in ip_network(cidr, strict=False):
                    return zone
        return None

    # ---- Zone Violations ----

    async def detect_violation(
        self,
        *,
        source_ip: str,
        dest_ip: str,
    ) -> ZoneViolation | None:
        """Detect if traffic between IPs crosses IT/OT boundary illegally.
        
        Creates a violation record if traffic crosses directly between
        IT and OT zones without going through DMZ.
        
        Args:
            source_ip: Source IP address
            dest_ip: Destination IP address
            
        Returns:
            Created ZoneViolation if violation detected, None otherwise
        """
        src_zone = await self._lookup_zone_for_ip(source_ip)
        dst_zone = await self._lookup_zone_for_ip(dest_ip)

        if not src_zone or not dst_zone:
            return None

        # IT → OT or OT → IT direct is violation; DMZ bridges are OK
        if src_zone.zone_type == ZoneType.IT.value and dst_zone.zone_type == ZoneType.OT.value:
            severity = ZoneViolationSeverity.CRITICAL.value
        elif src_zone.zone_type == ZoneType.OT.value and dst_zone.zone_type == ZoneType.IT.value:
            severity = ZoneViolationSeverity.HIGH.value
        else:
            return None

        violation = ZoneViolation(
            source_zone_id=src_zone.id,
            dest_zone_id=dst_zone.id,
            source_ip=source_ip,
            dest_ip=dest_ip,
            severity=severity,
            detected_at=_utcnow(),
            acknowledged=False,
        )
        self._session.add(violation)
        await self._session.flush()
        await self._session.refresh(violation)
        return violation

    async def get_violation(self, violation_id: UUID) -> ZoneViolation | None:
        """Get a zone violation by ID.
        
        Args:
            violation_id: UUID of the violation
            
        Returns:
            ZoneViolation if found, None otherwise
        """
        result = await self._session.execute(
            select(ZoneViolation).where(ZoneViolation.id == violation_id)
        )
        return result.scalar_one_or_none()

    async def list_violations(
        self,
        *,
        actor_roles: Iterable[str],
        only_unacknowledged: bool = False,
        severity: ZoneViolationSeverity | None = None,
        limit: int = 100,
    ) -> Sequence[ZoneViolation]:
        """List zone violations.
        
        Args:
            actor_roles: Roles of the requesting user
            only_unacknowledged: Filter to unacknowledged only
            severity: Filter by severity level
            limit: Maximum results to return
            
        Returns:
            List of ZoneViolation instances
            
        Raises:
            PermissionError: If user lacks admin privileges
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view zone violations")

        query = select(ZoneViolation).order_by(ZoneViolation.detected_at.desc())
        
        if only_unacknowledged:
            query = query.where(ZoneViolation.acknowledged == False)
        if severity:
            query = query.where(ZoneViolation.severity == severity.value)
        
        query = query.limit(limit)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def acknowledge_violation(
        self,
        violation_id: UUID,
        *,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        notes: str | None = None,
    ) -> ZoneViolation:
        """Acknowledge a zone violation.
        
        Args:
            violation_id: ID of violation to acknowledge
            actor_user_id: ID of acknowledging user
            actor_roles: Roles of the acknowledging user
            notes: Optional notes about the acknowledgment
            
        Returns:
            Updated ZoneViolation instance
            
        Raises:
            PermissionError: If user lacks admin privileges
            KeyError: If violation not found
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to acknowledge violations")

        violation = await self.get_violation(violation_id)
        if not violation:
            raise KeyError("Violation not found")

        violation.acknowledged = True
        violation.acknowledged_by_id = actor_user_id
        violation.acknowledged_at = _utcnow()
        if notes:
            violation.notes = notes

        await self._session.flush()
        await self._session.refresh(violation)
        return violation

    async def get_violation_stats(
        self,
        *,
        actor_roles: Iterable[str],
        days: int = 30,
    ) -> dict:
        """Get violation statistics.
        
        Args:
            actor_roles: Roles of the requesting user
            days: Number of days to analyze
            
        Returns:
            Dictionary with violation statistics
            
        Raises:
            PermissionError: If user lacks admin privileges
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view zone violations")

        since = _utcnow() - timedelta(days=days)
        
        result = await self._session.execute(
            select(ZoneViolation).where(ZoneViolation.detected_at >= since)
        )
        violations = result.scalars().all()

        stats = {
            "total": len(violations),
            "unacknowledged": sum(1 for v in violations if not v.acknowledged),
            "by_severity": {},
            "by_zone_pair": {},
        }

        for v in violations:
            sev = v.severity
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
            
            pair_key = f"{v.source_zone_id}:{v.dest_zone_id}"
            stats["by_zone_pair"][pair_key] = stats["by_zone_pair"].get(pair_key, 0) + 1

        return stats

    # ---- Edge Certificate Rotation ----

    async def register_certificate(
        self,
        *,
        controller_id: str,
        subject_cn: str,
        issuer: str,
        not_before: datetime,
        not_after: datetime,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        serial_number: str | None = None,
        fingerprint_sha256: str | None = None,
    ) -> EdgeCertificate:
        """Register a new edge certificate.
        
        Args:
            controller_id: Unique edge controller identifier
            subject_cn: Certificate subject common name
            issuer: Certificate issuer
            not_before: Certificate validity start
            not_after: Certificate validity end
            actor_user_id: ID of registering user
            actor_roles: Roles of the registering user
            serial_number: Certificate serial number (optional)
            fingerprint_sha256: SHA256 fingerprint (optional)
            
        Returns:
            Created EdgeCertificate instance
            
        Raises:
            PermissionError: If user lacks admin privileges
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage edge certificates")

        status = CertificateStatus.ACTIVE.value
        if _utcnow() > not_after:
            status = CertificateStatus.EXPIRED.value

        cert = EdgeCertificate(
            controller_id=controller_id.strip(),
            subject_cn=subject_cn,
            issuer=issuer,
            not_before=not_before,
            not_after=not_after,
            status=status,
            serial_number=serial_number,
            fingerprint_sha256=fingerprint_sha256,
            created_by_id=actor_user_id,
        )
        self._session.add(cert)
        await self._session.flush()
        await self._session.refresh(cert)
        return cert

    async def get_certificate(self, cert_id: UUID) -> EdgeCertificate | None:
        """Get an edge certificate by ID.
        
        Args:
            cert_id: UUID of the certificate
            
        Returns:
            EdgeCertificate if found, None otherwise
        """
        result = await self._session.execute(
            select(EdgeCertificate).where(EdgeCertificate.id == cert_id)
        )
        return result.scalar_one_or_none()

    async def list_certificates(
        self,
        *,
        actor_roles: Iterable[str],
        controller_id: str | None = None,
        status: CertificateStatus | None = None,
    ) -> Sequence[EdgeCertificate]:
        """List edge certificates.
        
        Args:
            actor_roles: Roles of the requesting user
            controller_id: Filter by controller ID (optional)
            status: Filter by certificate status (optional)
            
        Returns:
            List of EdgeCertificate instances
            
        Raises:
            PermissionError: If user lacks admin privileges
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view edge certificates")

        query = select(EdgeCertificate).order_by(EdgeCertificate.not_after)
        
        if controller_id:
            query = query.where(EdgeCertificate.controller_id == controller_id)
        if status:
            query = query.where(EdgeCertificate.status == status.value)
        
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_expiring_certificates(
        self,
        *,
        actor_roles: Iterable[str],
        days_ahead: int = 30,
    ) -> Sequence[EdgeCertificate]:
        """Get certificates expiring within a time window.
        
        Args:
            actor_roles: Roles of the requesting user
            days_ahead: Days ahead to check for expiration
            
        Returns:
            List of EdgeCertificate instances expiring soon
            
        Raises:
            PermissionError: If user lacks admin privileges
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view edge certificates")

        threshold = _utcnow() + timedelta(days=days_ahead)
        
        result = await self._session.execute(
            select(EdgeCertificate)
            .where(
                and_(
                    EdgeCertificate.status == CertificateStatus.ACTIVE.value,
                    EdgeCertificate.not_after <= threshold,
                )
            )
            .order_by(EdgeCertificate.not_after)
        )
        return result.scalars().all()

    async def rotate_certificate(
        self,
        cert_id: UUID,
        *,
        new_not_after: datetime,
        new_subject_cn: str | None = None,
        new_issuer: str | None = None,
        new_serial_number: str | None = None,
        new_fingerprint_sha256: str | None = None,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> EdgeCertificate:
        """Rotate an edge certificate.
        
        Revokes the old certificate and creates a new one for
        the same controller.
        
        Args:
            cert_id: ID of certificate to rotate
            new_not_after: New certificate expiration date
            new_subject_cn: New subject CN (defaults to old)
            new_issuer: New issuer (defaults to old)
            new_serial_number: New serial number (optional)
            new_fingerprint_sha256: New fingerprint (optional)
            actor_user_id: ID of rotating user
            actor_roles: Roles of the rotating user
            
        Returns:
            New EdgeCertificate instance
            
        Raises:
            PermissionError: If user lacks admin privileges
            KeyError: If certificate not found
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to rotate certificates")

        old_cert = await self.get_certificate(cert_id)
        if not old_cert:
            raise KeyError("Certificate not found")

        # Mark old as revoked
        old_cert.status = CertificateStatus.REVOKED.value
        await self._session.flush()

        # Create new certificate for same controller
        new_cert = EdgeCertificate(
            controller_id=old_cert.controller_id,
            subject_cn=new_subject_cn or old_cert.subject_cn,
            issuer=new_issuer or old_cert.issuer,
            not_before=_utcnow(),
            not_after=new_not_after,
            status=CertificateStatus.ACTIVE.value,
            serial_number=new_serial_number,
            fingerprint_sha256=new_fingerprint_sha256,
            rotated_at=_utcnow(),
            created_by_id=actor_user_id,
        )
        self._session.add(new_cert)
        await self._session.flush()
        await self._session.refresh(new_cert)
        return new_cert

    async def revoke_certificate(
        self,
        cert_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> EdgeCertificate:
        """Revoke an edge certificate.
        
        Args:
            cert_id: ID of certificate to revoke
            actor_roles: Roles of the revoking user
            
        Returns:
            Updated EdgeCertificate instance
            
        Raises:
            PermissionError: If user lacks admin privileges
            KeyError: If certificate not found
        """
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to revoke certificates")

        cert = await self.get_certificate(cert_id)
        if not cert:
            raise KeyError("Certificate not found")

        cert.status = CertificateStatus.REVOKED.value
        await self._session.flush()
        await self._session.refresh(cert)
        return cert


# Factory function for dependency injection
def get_ot_network_safety_service(session: AsyncSession) -> OTNetworkSafetyService:
    """Get OT network safety service instance.
    
    Args:
        session: Database session
        
    Returns:
        OTNetworkSafetyService instance
    """
    return OTNetworkSafetyService(session)
