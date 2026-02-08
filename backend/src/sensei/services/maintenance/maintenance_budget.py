"""
Maintenance Budget Service.

Manages maintenance cost budgets, tracks actual spending
against budget, and provides variance analysis by asset
category, cost type, and time period.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.maintenance import MaintenanceBudget


class MaintenanceBudgetService:
    """Persistent maintenance budgeting service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_budgets(self) -> list[MaintenanceBudget]:
        result = await self.db.execute(select(MaintenanceBudget))
        return list(result.scalars().all())

    async def create_budget(self, **kwargs) -> MaintenanceBudget:
        budget = MaintenanceBudget(**kwargs)
        self.db.add(budget)
        await self.db.flush()
        return budget

    async def get_budget(self, budget_id: UUID) -> Optional[MaintenanceBudget]:
        result = await self.db.execute(select(MaintenanceBudget).where(MaintenanceBudget.id == budget_id))
        return result.scalar_one_or_none()

    async def update_actuals(self, budget_id: UUID, actual_amount: Decimal, updated_by_id: UUID) -> Optional[MaintenanceBudget]:
        budget = await self.get_budget(budget_id)
        if not budget:
            return None
        budget.actual_amount = actual_amount
        budget.variance_amount = budget.actual_amount - budget.budget_amount
        budget.updated_by_id = updated_by_id
        return budget
