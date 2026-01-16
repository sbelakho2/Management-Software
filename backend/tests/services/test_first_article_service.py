from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sensei.models.user import User
from sensei.services.quality.first_article_service import FirstArticleService


@pytest.mark.asyncio
async def test_fai_inspection_workflow(async_session):
    user = User(
        email="fai@example.com",
        username="fai_user",
        password_hash="hashed",
        first_name="First",
        last_name="Article",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = FirstArticleService(async_session)
    inspection = await svc.create_inspection(
        inspection_number="FAI-2026-001",
        part_number="PN-100",
        revision="A",
        drawing_number="DWG-100",
        status="in_progress",
        inspector_id=user.id,
        started_at=datetime.now(timezone.utc),
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    characteristic = await svc.add_characteristic(
        inspection_id=inspection.id,
        characteristic_number=1,
        requirement="Diameter 10.00 ±0.05",
        actual=10.01,
        result="pass",
    )

    assert characteristic.requirement.startswith("Diameter")

    closed = await svc.close_inspection(inspection)
    assert closed.status == "completed"
    assert closed.completed_at is not None
