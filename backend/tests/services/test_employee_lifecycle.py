"""Tests for Employee Lifecycle & Records Service (Development Plan 21.7)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.services.hr.employee_lifecycle import (
    EmployeeLifecycleService,
    ChecklistType,
    ChecklistStatus,
    PersonnelDocumentType,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 1, 9, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def service() -> EmployeeLifecycleService:
    return EmployeeLifecycleService()


def test_employee_profile_pii_masked_for_non_privileged(service: EmployeeLifecycleService, now: datetime) -> None:
    employee_id = uuid4()
    hr_user_id = uuid4()
    viewer_id = uuid4()

    profile = service.upsert_employee_profile(
        employee_id=employee_id,
        actor_id=hr_user_id,
        actor_roles=["hr"],
        created_at=now,
        first_name="Amina",
        last_name="El Fassi",
        email="amina.elfassi@example.com",
        phone="+212 600 000 000",
        department="Production",
        job_title="Operator",
        site_id="SM1",
    )
    assert profile.email == "amina.elfassi@example.com"

    masked = service.get_employee_profile(
        employee_id,
        actor_id=viewer_id,
        actor_roles=["operator"],
        purpose="view",
    )
    assert masked is not None
    assert masked.email is not None
    assert masked.email != "amina.elfassi@example.com"
    assert masked.phone is not None
    assert masked.phone != "+212 600 000 000"

    full = service.get_employee_profile(
        employee_id,
        actor_id=viewer_id,
        actor_roles=["gm"],
        purpose="view",
    )
    assert full is not None
    assert full.email == "amina.elfassi@example.com"


def test_onboarding_checklist_status_transitions(service: EmployeeLifecycleService, now: datetime) -> None:
    employee_id = uuid4()
    creator_id = uuid4()

    checklist = service.create_checklist(
        employee_id=employee_id,
        checklist_type=ChecklistType.ONBOARDING,
        created_by=creator_id,
        created_at=now,
    )
    assert checklist.status == ChecklistStatus.NOT_STARTED
    assert len(checklist.items) >= 3

    first_item = checklist.items[0]
    updated = service.complete_checklist_item(
        checklist.id,
        first_item.id,
        actor_id=creator_id,
        completed_at=now,
        notes="Done",
    )
    assert updated.status == ChecklistStatus.IN_PROGRESS

    # Complete remaining
    current = updated
    for item in current.items:
        if item.completed:
            continue
        current = service.complete_checklist_item(
            current.id,
            item.id,
            actor_id=creator_id,
            completed_at=now,
        )

    assert current.status == ChecklistStatus.COMPLETED
    assert all(i.completed for i in current.items)


def test_offboarding_checklist_contains_exit_interview(service: EmployeeLifecycleService, now: datetime) -> None:
    employee_id = uuid4()
    creator_id = uuid4()

    checklist = service.create_checklist(
        employee_id=employee_id,
        checklist_type=ChecklistType.OFFBOARDING,
        created_by=creator_id,
        created_at=now,
    )

    titles = {i.title.lower() for i in checklist.items}
    assert "exit interview" in titles


def test_personnel_file_redacts_for_non_privileged(service: EmployeeLifecycleService, now: datetime) -> None:
    employee_id = uuid4()
    hr_user_id = uuid4()
    viewer_id = uuid4()

    doc = service.add_personnel_document(
        employee_id=employee_id,
        document_type=PersonnelDocumentType.CONTRACT,
        filename="Contract_Amina_2026.pdf",
        storage_key="s3://bucket/contract.pdf",
        uploaded_by=hr_user_id,
        actor_roles=["hr"],
        uploaded_at=now,
        notes="Signed original on file",
    )
    assert doc.storage_key

    hr_docs = service.list_personnel_documents(
        employee_id=employee_id,
        actor_id=viewer_id,
        actor_roles=["hr"],
        purpose="view",
    )
    assert len(hr_docs) == 1
    assert hr_docs[0].storage_key == "s3://bucket/contract.pdf"

    viewer_docs = service.list_personnel_documents(
        employee_id=employee_id,
        actor_id=viewer_id,
        actor_roles=["operator"],
        purpose="view",
    )
    assert len(viewer_docs) == 1
    assert viewer_docs[0].storage_key == ""
    assert viewer_docs[0].filename != "Contract_Amina_2026.pdf"

    logs = service.get_pii_access_logs_for_employee(employee_id=employee_id)
    assert len(logs) >= 1


def test_personnel_file_requires_hr_write(service: EmployeeLifecycleService, now: datetime) -> None:
    employee_id = uuid4()

    with pytest.raises(PermissionError):
        service.add_personnel_document(
            employee_id=employee_id,
            document_type=PersonnelDocumentType.GOVERNMENT_ID,
            filename="ID.pdf",
            storage_key="s3://bucket/id.pdf",
            uploaded_by=uuid4(),
            actor_roles=["operator"],
            uploaded_at=now,
        )
