"""Tests for OT Network Safety service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.ot_network_safety import (
    CertificateStatus,
    EdgeCertificate,
    NetworkZone,
    OTNetworkSafetyService,
    ZoneType,
    ZoneViolationSeverity,
)


@pytest.fixture
def svc() -> OTNetworkSafetyService:
    return OTNetworkSafetyService()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ADMIN_ROLES = ("admin",)
OPS_ROLES = ("ops",)
VIEWER_ROLES = ("viewer",)


class TestNetworkZoning:
    def test_create_zone_requires_role(self, svc: OTNetworkSafetyService) -> None:
        with pytest.raises(PermissionError):
            svc.create_zone(
                name="IT Zone",
                zone_type=ZoneType.IT,
                cidrs=["192.168.1.0/24"],
                description="Corporate IT",
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

        zone = svc.create_zone(
            name="OT Zone",
            zone_type=ZoneType.OT,
            cidrs=["10.100.0.0/16"],
            description="Manufacturing OT",
            actor_user_id=uuid4(),
            actor_roles=OPS_ROLES,
        )
        assert isinstance(zone, NetworkZone)
        assert zone.zone_type == ZoneType.OT

    def test_detect_it_ot_violation(self, svc: OTNetworkSafetyService) -> None:
        svc.create_zone(
            name="IT",
            zone_type=ZoneType.IT,
            cidrs=["192.168.0.0/16"],
            description="IT",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.create_zone(
            name="OT",
            zone_type=ZoneType.OT,
            cidrs=["10.0.0.0/8"],
            description="OT",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        # IT → OT is CRITICAL.
        violation = svc.detect_violation(source_ip="192.168.1.50", dest_ip="10.0.1.1")
        assert violation is not None
        assert violation.severity == ZoneViolationSeverity.CRITICAL

        # OT → IT is HIGH.
        violation2 = svc.detect_violation(source_ip="10.0.5.5", dest_ip="192.168.100.1")
        assert violation2 is not None
        assert violation2.severity == ZoneViolationSeverity.HIGH

    def test_no_violation_within_same_zone(self, svc: OTNetworkSafetyService) -> None:
        svc.create_zone(
            name="OT",
            zone_type=ZoneType.OT,
            cidrs=["10.0.0.0/8"],
            description="OT",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        violation = svc.detect_violation(source_ip="10.0.1.1", dest_ip="10.0.1.2")
        assert violation is None

    def test_acknowledge_violation(self, svc: OTNetworkSafetyService) -> None:
        svc.create_zone(
            name="IT",
            zone_type=ZoneType.IT,
            cidrs=["192.168.0.0/16"],
            description="IT",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        svc.create_zone(
            name="OT",
            zone_type=ZoneType.OT,
            cidrs=["10.0.0.0/8"],
            description="OT",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        violation = svc.detect_violation(source_ip="192.168.1.1", dest_ip="10.0.0.1")
        assert violation is not None

        unack = svc.list_violations(actor_roles=ADMIN_ROLES, only_unacknowledged=True)
        assert len(unack) == 1

        svc.acknowledge_violation(violation.id, actor_roles=ADMIN_ROLES)
        unack2 = svc.list_violations(actor_roles=ADMIN_ROLES, only_unacknowledged=True)
        assert len(unack2) == 0


class TestEdgeCertificates:
    def test_register_and_list_certificates(self, svc: OTNetworkSafetyService) -> None:
        cert = svc.register_certificate(
            controller_id="EDGE-001",
            subject_cn="edge-001.local",
            issuer="Internal CA",
            not_before=_utcnow() - timedelta(days=30),
            not_after=_utcnow() + timedelta(days=365),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(cert, EdgeCertificate)
        assert cert.status == CertificateStatus.ACTIVE

        certs = svc.list_certificates(actor_roles=ADMIN_ROLES)
        assert len(certs) == 1

    def test_expiring_certificates(self, svc: OTNetworkSafetyService) -> None:
        # Cert expiring in 10 days.
        svc.register_certificate(
            controller_id="EDGE-002",
            subject_cn="edge-002.local",
            issuer="Internal CA",
            not_before=_utcnow() - timedelta(days=355),
            not_after=_utcnow() + timedelta(days=10),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        # Cert expiring in 60 days.
        svc.register_certificate(
            controller_id="EDGE-003",
            subject_cn="edge-003.local",
            issuer="Internal CA",
            not_before=_utcnow() - timedelta(days=305),
            not_after=_utcnow() + timedelta(days=60),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        expiring = svc.get_expiring_certificates(actor_roles=ADMIN_ROLES, days_ahead=30)
        assert len(expiring) == 1
        assert expiring[0].controller_id == "EDGE-002"

    def test_rotate_certificate(self, svc: OTNetworkSafetyService) -> None:
        cert = svc.register_certificate(
            controller_id="EDGE-004",
            subject_cn="edge-004.local",
            issuer="Internal CA",
            not_before=_utcnow() - timedelta(days=365),
            not_after=_utcnow() + timedelta(days=5),
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        new_cert = svc.rotate_certificate(
            cert.id,
            new_not_after=_utcnow() + timedelta(days=365),
            actor_roles=ADMIN_ROLES,
        )

        assert new_cert.status == CertificateStatus.ACTIVE
        assert new_cert.rotated_at is not None

        # Old cert should be revoked.
        assert svc._certificates[cert.id].status == CertificateStatus.REVOKED

    def test_admin_role_required(self, svc: OTNetworkSafetyService) -> None:
        with pytest.raises(PermissionError):
            svc.register_certificate(
                controller_id="EDGE-X",
                subject_cn="x.local",
                issuer="CA",
                not_before=_utcnow(),
                not_after=_utcnow() + timedelta(days=30),
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )
