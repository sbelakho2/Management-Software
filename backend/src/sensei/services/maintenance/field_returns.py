"""
Field Returns / RMA Service.

Manages Return Merchandise Authorization (RMA) workflows,
field failure analysis, root cause tracking, and
replacement part logistics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.maintenance import FieldReturn


class FieldReturnService:
    """Persistent field return service for warranty analysis."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_returns(self) -> list[FieldReturn]:
        result = await self.db.execute(select(FieldReturn))
        return list(result.scalars().all())

    async def get_return(self, return_id: UUID) -> Optional[FieldReturn]:
        result = await self.db.execute(select(FieldReturn).where(FieldReturn.id == return_id))
        return result.scalar_one_or_none()

    async def create_return(self, **kwargs) -> FieldReturn:
        field_return = FieldReturn(**kwargs)
        self.db.add(field_return)
        await self.db.flush()
        return field_return

    async def update_return(self, field_return: FieldReturn, **kwargs) -> FieldReturn:
        for key, value in kwargs.items():
            setattr(field_return, key, value)
        await self.db.flush()
        return field_return

    async def close_return(self, field_return: FieldReturn) -> FieldReturn:
        field_return.status = "closed"
        field_return.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return field_return
