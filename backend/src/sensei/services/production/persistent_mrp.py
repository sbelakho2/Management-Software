from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from sensei.models.mrp import BOMComponent, MRPDemand, MRPSuggestion, MRPRun
from sensei.models.product import Product

class PersistentMRPService:
    """Persistent MRP-lite service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_bom(self) -> List[BOMComponent]:
        result = await self.db.execute(select(BOMComponent).options(selectinload(BOMComponent.parent_product), selectinload(BOMComponent.component_product)))
        return list(result.scalars().all())

    async def add_bom_component(self, **kwargs) -> BOMComponent:
        comp = BOMComponent(**kwargs)
        self.db.add(comp)
        await self.db.flush()
        return comp

    async def list_demands(self) -> List[MRPDemand]:
        result = await self.db.execute(select(MRPDemand).options(selectinload(MRPDemand.product)))
        return list(result.scalars().all())

    async def list_suggestions(self) -> List[MRPSuggestion]:
        result = await self.db.execute(select(MRPSuggestion).options(selectinload(MRPSuggestion.product)))
        return list(result.scalars().all())

    async def run_mrp(self, planning_horizon_days: int = 30, user_id: UUID | None = None) -> MRPRun:
        """
        Execute MRP calculation.
        This is a placeholder for the actual logic that calculates net requirements.
        """
        # Actual logic would involve walking the BOM tree, checking inventory and demands
        run = MRPRun(
            run_at=datetime.now(timezone.utc),
            planning_horizon_days=planning_horizon_days,
            executed_by_id=user_id,
            suggestions_count=0
        )
        self.db.add(run)
        await self.db.flush()
        return run
