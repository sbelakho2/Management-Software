from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.models.maintenance import Asset
from sensei.models.user import User
from sensei.services.maintenance.lockout_tagout import LockoutTagoutService


@pytest.mark.asyncio
async def test_loto_procedure_and_lock(async_session):
    user = User(
        email="loto@example.com",
        username="loto_user",
        password_hash="hashed",
        first_name="Loto",
        last_name="Tester",
        status="active",
    )
    async_session.add(user)

    asset = Asset(
        asset_number="AST-00001",
        name="CNC Mill 1",
        asset_type="cnc",
    )
    async_session.add(asset)
    await async_session.flush()

    svc = LockoutTagoutService(async_session)
    procedure = await svc.create_procedure(
        asset_id=asset.id,
        title="CNC Mill Lockout",
        description="Isolate power and pneumatic lines",
        energy_sources=[
            {
                "source_type": "electric",
                "isolation_point": "Panel P1",
                "lock_required": True,
                "verification_steps": ["Test start button", "Check voltage"],
            }
        ],
        created_by_id=user.id,
    )

    lock = await svc.create_lock(
        procedure_id=procedure.id,
        asset_id=asset.id,
        lock_number="LOTO-0001",
        applied_by_id=user.id,
        reason="Planned maintenance",
        verification_required=True,
    )

    await async_session.commit()

    fetched = await svc.get_procedure(procedure.id)
    assert fetched is not None
    assert fetched.title == "CNC Mill Lockout"
    assert len(fetched.energy_sources) == 1

    active_locks = await svc.list_active_locks()
    assert any(l.id == lock.id for l in active_locks)

    verified = await svc.verify_lock(
        lock_id=lock.id,
        verified_by_id=user.id,
        verification_notes="Isolation verified",
    )
    assert verified is not None
    assert verified.verified_at is not None

    released = await svc.release_lock(
        lock_id=lock.id,
        released_by_id=user.id,
        verification_notes="Work completed",
    )
    assert released is not None
    assert released.status == "released"
    assert released.released_at is not None
