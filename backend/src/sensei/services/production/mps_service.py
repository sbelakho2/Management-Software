"""
Master Production Schedule (MPS) Service.

Manages the master production schedule including demand
planning, capacity allocation, and schedule leveling.
Feeds MRP and shop floor scheduling.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.mrp import MPSPlan, MPSPlanLine


class MPSService:
    """Service for master production scheduling."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_plans(self) -> list[MPSPlan]:
        result = await self.db.execute(select(MPSPlan))
        return list(result.scalars().all())

    async def get_plan(self, plan_id: UUID) -> Optional[MPSPlan]:
        result = await self.db.execute(select(MPSPlan).where(MPSPlan.id == plan_id))
        return result.scalar_one_or_none()

    async def create_plan(self, **kwargs) -> MPSPlan:
        plan = MPSPlan(**kwargs)
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def list_lines(self, plan_id: UUID) -> list[MPSPlanLine]:
        result = await self.db.execute(select(MPSPlanLine).where(MPSPlanLine.plan_id == plan_id))
        return list(result.scalars().all())

    async def add_line(self, **kwargs) -> MPSPlanLine:
        line = MPSPlanLine(**kwargs)
        self.db.add(line)
        await self.db.flush()
        return line
