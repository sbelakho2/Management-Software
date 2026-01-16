from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.finance import StandardCostRecord, WorkOrderCostRollup


class CostRollupService:
    """Service for costing rollups and variance persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_standard_costs(self, sku: Optional[str] = None) -> list[StandardCostRecord]:
        stmt = select(StandardCostRecord)
        if sku:
            stmt = stmt.where(StandardCostRecord.sku == sku)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert_standard_cost(
        self,
        sku: str,
        currency: str,
        effective_date,
        material_unit_cost: Decimal,
        labor_unit_cost: Decimal,
        overhead_unit_cost: Decimal,
    ) -> StandardCostRecord:
        result = await self.db.execute(
            select(StandardCostRecord).where(
                StandardCostRecord.sku == sku,
                StandardCostRecord.effective_date == effective_date,
            )
        )
        record = result.scalar_one_or_none()
        total_unit_cost = material_unit_cost + labor_unit_cost + overhead_unit_cost
        if record:
            record.currency = currency
            record.material_unit_cost = material_unit_cost
            record.labor_unit_cost = labor_unit_cost
            record.overhead_unit_cost = overhead_unit_cost
            record.total_unit_cost = total_unit_cost
        else:
            record = StandardCostRecord(
                sku=sku,
                currency=currency,
                effective_date=effective_date,
                material_unit_cost=material_unit_cost,
                labor_unit_cost=labor_unit_cost,
                overhead_unit_cost=overhead_unit_cost,
                total_unit_cost=total_unit_cost,
            )
            self.db.add(record)
        await self.db.flush()
        return record

    async def list_rollups(self, work_order_id: Optional[str] = None) -> list[WorkOrderCostRollup]:
        stmt = select(WorkOrderCostRollup)
        if work_order_id:
            stmt = stmt.where(WorkOrderCostRollup.work_order_id == work_order_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rollup(self, **kwargs) -> WorkOrderCostRollup:
        if "calculated_at" not in kwargs:
            kwargs["calculated_at"] = datetime.now(timezone.utc)
        rollup = WorkOrderCostRollup(**kwargs)
        self.db.add(rollup)
        await self.db.flush()
        return rollup
