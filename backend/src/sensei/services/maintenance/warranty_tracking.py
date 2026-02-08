"""
Warranty Tracking Service.

Manages warranty registrations, claim submissions,
coverage verification, and warranty cost analysis.
Tracks warranty periods and exclusions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.maintenance import AssetWarranty, WarrantyClaim


class WarrantyTrackingService:
    """Persistent warranty tracking service using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_warranties(self) -> list[AssetWarranty]:
        result = await self.db.execute(
            select(AssetWarranty).options(selectinload(AssetWarranty.claims))
        )
        return list(result.scalars().all())

    async def get_warranty(self, warranty_id: UUID) -> Optional[AssetWarranty]:
        result = await self.db.execute(
            select(AssetWarranty)
            .where(AssetWarranty.id == warranty_id)
            .options(selectinload(AssetWarranty.claims))
        )
        return result.scalar_one_or_none()

    async def create_warranty(self, **kwargs) -> AssetWarranty:
        warranty = AssetWarranty(**kwargs)
        self.db.add(warranty)
        await self.db.flush()
        return warranty

    async def file_claim(
        self,
        *,
        warranty_id: UUID,
        asset_id: UUID,
        claim_number: str,
        submitted_by_id: UUID,
        work_order_id: Optional[UUID] = None,
        claim_amount: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> WarrantyClaim:
        claim = WarrantyClaim(
            warranty_id=warranty_id,
            asset_id=asset_id,
            work_order_id=work_order_id,
            claim_number=claim_number,
            status="submitted",
            claim_amount=claim_amount,
            submitted_at=datetime.now(timezone.utc),
            notes=notes,
            created_by_id=submitted_by_id,
            updated_by_id=submitted_by_id,
            owner_id=submitted_by_id,
        )
        self.db.add(claim)
        await self.db.flush()
        return claim

    async def resolve_claim(
        self,
        *,
        claim_id: UUID,
        status: str,
        resolved_by_id: UUID,
        approved_amount: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> Optional[WarrantyClaim]:
        result = await self.db.execute(select(WarrantyClaim).where(WarrantyClaim.id == claim_id))
        claim = result.scalar_one_or_none()
        if not claim:
            return None

        claim.status = status
        claim.approved_amount = approved_amount
        claim.resolved_at = datetime.now(timezone.utc)
        claim.notes = notes or claim.notes
        claim.updated_by_id = resolved_by_id
        return claim
