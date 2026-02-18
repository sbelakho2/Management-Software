"""
First Article Inspection (FAI) Service.

Manages AS9102 First Article Inspection Reports.
Tracks Form 1 (Part Number Accountability), Form 2
(Product Accountability), and Form 3 (Characteristic
Accountability).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import FirstArticleInspection, FAICharacteristic
from sensei.services.event_bus import event_bus
from sensei.services.domain_events import InspectionCompletedEvent


class FirstArticleService:
    """Persistent First Article Inspection (FAI) service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_inspections(self) -> list[FirstArticleInspection]:
        result = await self.db.execute(
            select(FirstArticleInspection)
            .options(selectinload(FirstArticleInspection.characteristics))
        )
        return list(result.scalars().all())

    async def get_inspection(self, inspection_id: UUID) -> Optional[FirstArticleInspection]:
        result = await self.db.execute(
            select(FirstArticleInspection)
            .where(FirstArticleInspection.id == inspection_id)
            .options(selectinload(FirstArticleInspection.characteristics))
        )
        return result.scalar_one_or_none()

    async def create_inspection(self, **kwargs) -> FirstArticleInspection:
        inspection = FirstArticleInspection(**kwargs)
        self.db.add(inspection)
        await self.db.flush()
        return inspection

    async def add_characteristic(
        self,
        *,
        inspection_id: UUID,
        characteristic_number: int,
        requirement: str,
        nominal: Optional[Decimal] = None,
        tolerance: Optional[str] = None,
        actual: Optional[Decimal] = None,
        result: str = "pending",
        method: Optional[str] = None,
        tool_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> FAICharacteristic:
        characteristic = FAICharacteristic(
            inspection_id=inspection_id,
            characteristic_number=characteristic_number,
            requirement=requirement,
            nominal=nominal,
            tolerance=tolerance,
            actual=actual,
            result=result,
            method=method,
            tool_id=tool_id,
            notes=notes,
        )
        self.db.add(characteristic)
        await self.db.flush()
        return characteristic

    async def update_inspection(self, inspection: FirstArticleInspection, **kwargs) -> FirstArticleInspection:
        for key, value in kwargs.items():
            setattr(inspection, key, value)
        await self.db.flush()
        return inspection

    async def close_inspection(self, inspection: FirstArticleInspection) -> FirstArticleInspection:
        inspection.status = "completed"
        inspection.completed_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Publish domain event — feeds single data thread
        await event_bus.publish(InspectionCompletedEvent(
            inspection_id=str(inspection.id),
            result="completed",
            product_id=str(getattr(inspection, "product_id", "") or ""),
            inspector_id=str(getattr(inspection, "inspector_id", "") or ""),
        ))

        return inspection
