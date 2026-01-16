from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sensei.models.maintenance import Asset
from sensei.models.user import User
from sensei.services.maintenance.warranty_tracking import WarrantyTrackingService


@pytest.mark.asyncio
async def test_warranty_and_claim(async_session):
    user = User(
        email="warranty@example.com",
        username="warranty_user",
        password_hash="hashed",
        first_name="Warranty",
        last_name="User",
        status="active",
    )
    async_session.add(user)

    asset = Asset(
        asset_number="AST-100",
        name="Hydraulic Press",
        asset_type="press",
    )
    async_session.add(asset)
    await async_session.flush()

    svc = WarrantyTrackingService(async_session)
    warranty = await svc.create_warranty(
        asset_id=asset.id,
        warranty_type="manufacturer",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=365),
        coverage_type="parts_labor",
        status="active",
        created_by_id=user.id,
        updated_by_id=user.id,
        owner_id=user.id,
    )

    claim = await svc.file_claim(
        warranty_id=warranty.id,
        asset_id=asset.id,
        claim_number="WC-0001",
        submitted_by_id=user.id,
        notes="Motor failure",
    )

    await async_session.commit()

    fetched = await svc.get_warranty(warranty.id)
    assert fetched is not None
    assert fetched.warranty_type == "manufacturer"

    resolved = await svc.resolve_claim(
        claim_id=claim.id,
        status="approved",
        resolved_by_id=user.id,
        approved_amount=2500,
    )
    assert resolved is not None
    assert resolved.status == "approved"
    assert resolved.resolved_at is not None
