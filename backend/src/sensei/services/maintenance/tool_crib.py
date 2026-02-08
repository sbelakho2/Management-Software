"""
Tool Crib Management Service.

Manages tool inventory, check-out/check-in workflows,
calibration tracking, tool life monitoring, and
replacement ordering for shop floor tooling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.maintenance import ToolItem, ToolCheckout


class ToolCribService:
    """Persistent tool crib service using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tools(self) -> list[ToolItem]:
        result = await self.db.execute(select(ToolItem))
        return list(result.scalars().all())

    async def create_tool(self, **kwargs) -> ToolItem:
        tool = ToolItem(**kwargs)
        self.db.add(tool)
        await self.db.flush()
        return tool

    async def get_tool(self, tool_id: UUID) -> Optional[ToolItem]:
        result = await self.db.execute(select(ToolItem).where(ToolItem.id == tool_id))
        return result.scalar_one_or_none()

    async def list_active_checkouts(self) -> list[ToolCheckout]:
        result = await self.db.execute(
            select(ToolCheckout)
            .where(ToolCheckout.returned_at.is_(None))
            .options(selectinload(ToolCheckout.tool))
        )
        return list(result.scalars().all())

    async def checkout_tool(
        self,
        *,
        tool_id: UUID,
        checked_out_by_id: UUID,
        work_order_id: Optional[UUID] = None,
        due_back_at: Optional[datetime] = None,
        condition_out: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ToolCheckout]:
        tool = await self.get_tool(tool_id)
        if not tool or tool.quantity_on_hand <= 0:
            return None

        tool.status = "checked_out"
        tool.quantity_on_hand -= 1

        checkout = ToolCheckout(
            tool_id=tool_id,
            work_order_id=work_order_id,
            checked_out_by_id=checked_out_by_id,
            checked_out_at=datetime.now(timezone.utc),
            due_back_at=due_back_at,
            condition_out=condition_out,
            notes=notes,
            created_by_id=checked_out_by_id,
            updated_by_id=checked_out_by_id,
            owner_id=checked_out_by_id,
        )
        self.db.add(checkout)
        await self.db.flush()
        return checkout

    async def return_tool(
        self,
        *,
        checkout_id: UUID,
        returned_by_id: UUID,
        condition_in: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ToolCheckout]:
        result = await self.db.execute(select(ToolCheckout).where(ToolCheckout.id == checkout_id))
        checkout = result.scalar_one_or_none()
        if not checkout or checkout.returned_at is not None:
            return None

        tool = await self.get_tool(checkout.tool_id)
        if not tool:
            return None

        checkout.returned_by_id = returned_by_id
        checkout.returned_at = datetime.now(timezone.utc)
        checkout.condition_in = condition_in
        checkout.notes = notes or checkout.notes
        checkout.updated_by_id = returned_by_id

        tool.quantity_on_hand += 1
        tool.status = "available" if tool.quantity_on_hand > 0 else "checked_out"

        return checkout
