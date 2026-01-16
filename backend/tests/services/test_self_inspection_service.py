from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sensei.models.user import User
from sensei.services.quality.self_inspection_service import SelfInspectionService


@pytest.mark.asyncio
async def test_self_inspection_workflow(async_session):
    user = User(
        email="selfinsp@example.com",
        username="selfinsp_user",
        password_hash="hashed",
        first_name="Self",
        last_name="Inspector",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = SelfInspectionService(async_session)
    inspection = await svc.create_inspection(
        inspection_number="SI-2026-001",
        operator_id=user.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    check = await svc.add_check(
        inspection_id=inspection.id,
        characteristic="Diameter",
        specification="10.00 ±0.05",
        actual_value="10.01",
        result="pass",
    )
    assert check.characteristic == "Diameter"

    closed = await svc.close_inspection(inspection)
    assert closed.status == "completed"
    assert closed.completed_at is not None
