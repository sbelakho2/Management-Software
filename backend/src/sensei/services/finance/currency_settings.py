from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.finance import CurrencySetting, FXRate


class CurrencySettingsService:
    """Service for managing multi-currency configuration and FX rates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_settings(self) -> CurrencySetting:
        result = await self.db.execute(select(CurrencySetting))
        settings = result.scalar_one_or_none()
        if settings:
            return settings
        settings = CurrencySetting(base_currency="USD", auto_update_rates=False)
        self.db.add(settings)
        await self.db.flush()
        return settings

    async def update_settings(self, settings: CurrencySetting, **kwargs) -> CurrencySetting:
        for key, value in kwargs.items():
            setattr(settings, key, value)
        await self.db.flush()
        return settings

    async def list_fx_rates(self, as_of: Optional[date] = None) -> list[FXRate]:
        stmt = select(FXRate)
        if as_of:
            stmt = stmt.where(FXRate.as_of == as_of)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert_fx_rate(
        self,
        as_of: date,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
    ) -> FXRate:
        result = await self.db.execute(
            select(FXRate).where(
                FXRate.as_of == as_of,
                FXRate.from_currency == from_currency,
                FXRate.to_currency == to_currency,
            )
        )
        fx_rate = result.scalar_one_or_none()
        if fx_rate:
            fx_rate.rate = rate
        else:
            fx_rate = FXRate(
                as_of=as_of,
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
            )
            self.db.add(fx_rate)
        await self.db.flush()
        return fx_rate
