from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from sensei.services.certification_tracking import (
    CertificationTrackingService,
    CertificationStandard,
    CertificationStatus,
)


def test_registry_requires_write_role() -> None:
    svc = CertificationTrackingService()
    employee_id = uuid4()
    actor_user_id = uuid4()

    with pytest.raises(PermissionError):
        svc.add_certification(
            employee_id=employee_id,
            standard=CertificationStandard.ISO_9001,
            name="ISO 9001 Internal Auditor",
            issuer="TUV",
            issued_on=date.today(),
            expires_on=date.today() + timedelta(days=365),
            actor_user_id=actor_user_id,
            actor_roles={"viewer"},
        )


def test_registry_self_view_and_privileged_view() -> None:
    svc = CertificationTrackingService()
    employee_id = uuid4()
    other_employee_id = uuid4()
    hr_user_id = uuid4()

    cert = svc.add_certification(
        employee_id=employee_id,
        standard=CertificationStandard.IATF_16949,
        name="IATF 16949 Awareness",
        issuer="Internal",
        issued_on=date.today(),
        expires_on=date.today() + timedelta(days=120),
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
    )

    # Self view allowed.
    rows = svc.list_certifications(
        employee_id=employee_id,
        actor_roles={"viewer"},
        actor_employee_id=employee_id,
        include_inactive=True,
    )
    assert [r.id for r in rows] == [cert.id]

    # Privileged view allowed.
    rows2 = svc.list_certifications(
        employee_id=employee_id,
        actor_roles={"quality"},
        actor_employee_id=other_employee_id,
        include_inactive=True,
    )
    assert [r.id for r in rows2] == [cert.id]

    # Unrelated non-privileged view denied.
    with pytest.raises(PermissionError):
        svc.list_certifications(
            employee_id=employee_id,
            actor_roles={"viewer"},
            actor_employee_id=other_employee_id,
            include_inactive=True,
        )


def test_evidence_masking_for_non_privileged() -> None:
    svc = CertificationTrackingService()
    employee_id = uuid4()
    hr_user_id = uuid4()

    cert = svc.add_certification(
        employee_id=employee_id,
        standard=CertificationStandard.AS9100,
        name="AS9100 Lead Auditor",
        issuer="External",
        issued_on=date.today(),
        expires_on=date.today() + timedelta(days=200),
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
    )

    svc.add_evidence(
        certification_id=cert.id,
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
        filename="john_doe_as9100_certificate.pdf",
        storage_key="s3://bucket/certs/employee/john_doe_as9100_certificate.pdf",
        notes="Passed with distinction",
        sha256="deadbeef",
        mime_type="application/pdf",
    )

    # Self should see full storage key.
    self_view = svc.list_evidence(
        certification_id=cert.id,
        actor_roles={"viewer"},
        actor_employee_id=employee_id,
        actor_user_id=uuid4(),
    )
    assert self_view[0]["storage_key"].startswith("s3://")

    # Non-privileged non-self should not be able to view evidence at all.
    with pytest.raises(PermissionError):
        svc.list_evidence(
            certification_id=cert.id,
            actor_roles={"viewer"},
            actor_employee_id=uuid4(),
            actor_user_id=uuid4(),
        )


def test_recertification_nudges_60_day_lead_and_idempotent() -> None:
    svc = CertificationTrackingService()
    employee_id = uuid4()
    hr_user_id = uuid4()

    as_of = date(2026, 1, 9)

    cert_due = svc.add_certification(
        employee_id=employee_id,
        standard=CertificationStandard.ISO_45001,
        name="ISO 45001 Safety Training",
        issuer="Internal",
        issued_on=as_of,
        expires_on=as_of + timedelta(days=59),
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
    )

    cert_not_due = svc.add_certification(
        employee_id=employee_id,
        standard=CertificationStandard.ISO_14001,
        name="ISO 14001 Awareness",
        issuer="Internal",
        issued_on=as_of,
        expires_on=as_of + timedelta(days=61),
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
    )

    nudges = svc.generate_recertification_nudges(
        as_of=as_of,
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
        lead_days=60,
    )
    assert [n.certification_id for n in nudges] == [cert_due.id]

    # Idempotent: no new nudges if generated again.
    nudges2 = svc.generate_recertification_nudges(
        as_of=as_of,
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
        lead_days=60,
    )
    assert nudges2 == []

    assert cert_not_due.id not in [n.certification_id for n in svc.list_recertification_nudges(
        employee_id=employee_id,
        actor_roles={"hr"},
        actor_employee_id=uuid4(),
    )]


def test_expire_and_renew_emits_events() -> None:
    svc = CertificationTrackingService()
    employee_id = uuid4()
    hr_user_id = uuid4()

    cert = svc.add_certification(
        employee_id=employee_id,
        standard=CertificationStandard.CUSTOMER_SPECIFIC,
        name="Customer X Special Process",
        issuer="Customer X",
        issued_on=date(2025, 1, 1),
        expires_on=date(2026, 1, 1),
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
    )

    expired = svc.expire_due_certifications(as_of=date(2026, 1, 9))
    assert cert.id in expired
    assert any(e["event_name"] == "certification.expired" for e in svc.events)

    renewed = svc.renew_certification(
        cert.id,
        new_expires_on=date(2027, 1, 1),
        actor_user_id=hr_user_id,
        actor_roles={"hr"},
    )
    assert renewed.status == CertificationStatus.ACTIVE
    assert any(e["event_name"] == "certification.renewed" for e in svc.events)
