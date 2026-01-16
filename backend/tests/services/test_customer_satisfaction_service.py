from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sensei.models.user import User
from sensei.services.quality.customer_satisfaction_service import CustomerSatisfactionService


@pytest.mark.asyncio
async def test_customer_complaint_workflow(async_session):
    user = User(
        email="complaints@example.com",
        username="complaints_user",
        password_hash="hashed",
        first_name="Complaint",
        last_name="Owner",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = CustomerSatisfactionService(async_session)
    complaint = await svc.create_complaint(
        customer_id=None,
        title="Surface scratch",
        description="Scratch on finished part",
        received_at=datetime.now(timezone.utc),
        status="received",
        rma_number="RMA-2026-01",
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    updated = await svc.update_complaint(
        complaint,
        root_cause="Handling damage",
        containment_actions=["Quarantine lot"],
        corrective_actions=["Improve packaging"],
    )

    assert updated.root_cause == "Handling damage"
    assert updated.containment_actions == ["Quarantine lot"]

    closed = await svc.close_complaint(updated)
    assert closed.status == "closed"
    assert closed.closed_at is not None


@pytest.mark.asyncio
async def test_customer_survey_nps_stats(async_session):
    user = User(
        email="survey@example.com",
        username="survey_user",
        password_hash="hashed",
        first_name="Survey",
        last_name="Owner",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = CustomerSatisfactionService(async_session)
    survey = await svc.create_survey(
        title="Q1 NPS",
        description="Quarterly NPS survey",
        status="active",
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    await svc.add_response(survey_id=survey.id, nps_score=10, respondent_name="A")
    await svc.add_response(survey_id=survey.id, nps_score=8, respondent_name="B")
    await svc.add_response(survey_id=survey.id, nps_score=5, respondent_name="C")

    stats = await svc.compute_nps_stats(survey.id)
    assert stats["total_responses"] == 3
    assert stats["promoters"] == 1
    assert stats["passives"] == 1
    assert stats["detractors"] == 1
