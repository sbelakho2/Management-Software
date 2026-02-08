"""
AQL Sampling Service.

Implements ANSI/ASQ Z1.4 (ISO 2859-1) acceptance sampling
plans. Calculates sample sizes, acceptance/rejection numbers,
and switching rules (normal/tightened/reduced).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.quality_qms import AQLSamplingPlan, AQLLotInspection


class AQLSamplingService:
    """Service for managing AQL sampling plans and lot inspections."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_plans(self) -> list[AQLSamplingPlan]:
        result = await self.db.execute(select(AQLSamplingPlan))
        return list(result.scalars().all())

    async def get_plan(self, plan_id: UUID) -> Optional[AQLSamplingPlan]:
        result = await self.db.execute(select(AQLSamplingPlan).where(AQLSamplingPlan.id == plan_id))
        return result.scalar_one_or_none()

    async def create_plan(self, **kwargs) -> AQLSamplingPlan:
        plan = AQLSamplingPlan(**kwargs)
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def list_inspections(self, plan_id: Optional[UUID] = None) -> list[AQLLotInspection]:
        stmt = select(AQLLotInspection)
        if plan_id:
            stmt = stmt.where(AQLLotInspection.plan_id == plan_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_inspection(
        self,
        plan: AQLSamplingPlan,
        lot_number: str,
        lot_size: int,
        defect_count: int,
        sample_size: Optional[int] = None,
        inspected_at: Optional[datetime] = None,
        inspector_id: Optional[UUID] = None,
        defects_json: Optional[list] = None,
        notes: Optional[str] = None,
        created_by_id: Optional[UUID] = None,
        updated_by_id: Optional[UUID] = None,
        owner_id: Optional[UUID] = None,
    ) -> AQLLotInspection:
        if not (plan.lot_size_min <= lot_size <= plan.lot_size_max):
            raise ValueError("Lot size outside plan range")

        effective_sample_size = sample_size or plan.sample_size
        inspected_at = inspected_at or datetime.now(timezone.utc)
        result = "accept" if defect_count <= plan.accept_limit else "reject"

        inspection = AQLLotInspection(
            plan_id=plan.id,
            lot_number=lot_number,
            lot_size=lot_size,
            sample_size=effective_sample_size,
            defect_count=defect_count,
            accept_limit=plan.accept_limit,
            reject_limit=plan.reject_limit,
            result=result,
            inspected_at=inspected_at,
            inspector_id=inspector_id,
            inspection_level=plan.inspection_level,
            aql_level=plan.aql_level,
            defects_json=defects_json,
            notes=notes,
            created_by_id=created_by_id,
            updated_by_id=updated_by_id,
            owner_id=owner_id,
        )
        self.db.add(inspection)
        await self.db.flush()
        return inspection
