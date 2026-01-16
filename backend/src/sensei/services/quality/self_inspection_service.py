from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import SelfInspection, SelfInspectionCheck


class SelfInspectionService:
    """Persistent operator self-inspection service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_inspections(self) -> list[SelfInspection]:
        result = await self.db.execute(
            select(SelfInspection).options(selectinload(SelfInspection.checks))
        )
        return list(result.scalars().all())

    async def get_inspection(self, inspection_id: UUID) -> Optional[SelfInspection]:
        result = await self.db.execute(
            select(SelfInspection)
            .where(SelfInspection.id == inspection_id)
            .options(selectinload(SelfInspection.checks))
        )
        return result.scalar_one_or_none()

    async def create_inspection(self, **kwargs) -> SelfInspection:
        inspection = SelfInspection(**kwargs)
        self.db.add(inspection)
        await self.db.flush()
        return inspection

    async def add_check(
        self,
        *,
        inspection_id: UUID,
        characteristic: str,
        specification: Optional[str] = None,
        actual_value: Optional[str] = None,
        result: str = "pending",
        notes: Optional[str] = None,
    ) -> SelfInspectionCheck:
        check = SelfInspectionCheck(
            inspection_id=inspection_id,
            characteristic=characteristic,
            specification=specification,
            actual_value=actual_value,
            result=result,
            notes=notes,
        )
        self.db.add(check)
        await self.db.flush()
        return check

    async def update_inspection(self, inspection: SelfInspection, **kwargs) -> SelfInspection:
        for key, value in kwargs.items():
            setattr(inspection, key, value)
        await self.db.flush()
        return inspection

    async def close_inspection(self, inspection: SelfInspection) -> SelfInspection:
        inspection.status = "completed"
        inspection.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return inspection
