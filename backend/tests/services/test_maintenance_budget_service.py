from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sensei.models.user import User
from sensei.services.maintenance.maintenance_budget import MaintenanceBudgetService


@pytest.mark.asyncio
async def test_maintenance_budget_update(async_session):
    user = User(
        email="budget@example.com",
        username="budget_user",
        password_hash="hashed",
        first_name="Budget",
        last_name="User",
        status="active",
    )
    async_session.add(user)
    await async_session.flush()

    svc = MaintenanceBudgetService(async_session)
    budget = await svc.create_budget(
        name="Q1 2026 Maintenance",
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc) + timedelta(days=90),
        budget_amount=50000,
        actual_amount=0,
        variance_amount=0,
        currency="MAD",
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    updated = await svc.update_actuals(budget.id, 15000, user.id)
    assert updated is not None
    assert float(updated.actual_amount) == 15000.0
    assert float(updated.variance_amount) == 15000.0 - 50000.0
