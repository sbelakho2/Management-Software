"""
Tax Service.

Manages tax rates, tax rules, jurisdiction mappings, and
tax calculations for sales tax, VAT, and withholding tax.
Supports multi-jurisdiction tax compliance.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.finance import TaxJurisdiction, TaxRate, TaxTransaction


class TaxService:
    """Service for tax compliance configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_jurisdictions(self) -> list[TaxJurisdiction]:
        result = await self.db.execute(select(TaxJurisdiction))
        return list(result.scalars().all())

    async def create_jurisdiction(self, **kwargs) -> TaxJurisdiction:
        jurisdiction = TaxJurisdiction(**kwargs)
        self.db.add(jurisdiction)
        await self.db.flush()
        return jurisdiction

    async def list_rates(self, jurisdiction_id: Optional[UUID] = None) -> list[TaxRate]:
        stmt = select(TaxRate)
        if jurisdiction_id:
            stmt = stmt.where(TaxRate.jurisdiction_id == jurisdiction_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rate(self, **kwargs) -> TaxRate:
        rate = TaxRate(**kwargs)
        self.db.add(rate)
        await self.db.flush()
        return rate

    async def list_transactions(self, reference_id: Optional[str] = None) -> list[TaxTransaction]:
        stmt = select(TaxTransaction)
        if reference_id:
            stmt = stmt.where(TaxTransaction.reference_id == reference_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_transaction(self, **kwargs) -> TaxTransaction:
        transaction = TaxTransaction(**kwargs)
        self.db.add(transaction)
        await self.db.flush()
        return transaction
