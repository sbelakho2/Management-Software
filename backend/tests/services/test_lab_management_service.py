from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from sensei.models.user import User
from sensei.services.quality.lab_management_service import LabManagementService


@pytest.mark.asyncio
async def test_lab_management_flow(async_session):
    user = User(
        email="lab@example.com",
        username="lab_user",
        password_hash="hashed",
        first_name="Lab",
        last_name="User",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = LabManagementService(async_session)
    method = await svc.create_method(
        name="Tensile Strength",
        standard="ASTM E8",
        unit="MPa",
        lower_spec=Decimal("350"),
        upper_spec=Decimal("550"),
        target_value=Decimal("450"),
        status="active",
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    sample = await svc.create_sample(
        sample_number="LAB-2026-001",
        lot_number="LOT-100",
        collected_at=datetime.now(timezone.utc),
        collected_by_id=user.id,
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    test_run = await svc.add_test_run(
        sample_id=sample.id,
        method_id=method.id,
        result_value=Decimal("460"),
        result_status="pass",
        tester_id=user.id,
    )

    assert test_run.result_status == "pass"
