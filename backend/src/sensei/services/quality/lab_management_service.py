from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import LabTestMethod, LabSample, LabTestRun


class LabManagementService:
    """Persistent lab management service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_methods(self) -> list[LabTestMethod]:
        result = await self.db.execute(select(LabTestMethod))
        return list(result.scalars().all())

    async def create_method(self, **kwargs) -> LabTestMethod:
        method = LabTestMethod(**kwargs)
        self.db.add(method)
        await self.db.flush()
        return method

    async def list_samples(self) -> list[LabSample]:
        result = await self.db.execute(
            select(LabSample).options(selectinload(LabSample.tests))
        )
        return list(result.scalars().all())

    async def get_sample(self, sample_id: UUID) -> Optional[LabSample]:
        result = await self.db.execute(
            select(LabSample)
            .where(LabSample.id == sample_id)
            .options(selectinload(LabSample.tests))
        )
        return result.scalar_one_or_none()

    async def create_sample(self, **kwargs) -> LabSample:
        sample = LabSample(**kwargs)
        self.db.add(sample)
        await self.db.flush()
        return sample

    async def add_test_run(
        self,
        *,
        sample_id: UUID,
        method_id: UUID,
        result_value: Optional[Decimal] = None,
        result_text: Optional[str] = None,
        result_status: str = "pending",
        tester_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> LabTestRun:
        test_run = LabTestRun(
            sample_id=sample_id,
            method_id=method_id,
            result_value=result_value,
            result_text=result_text,
            result_status=result_status,
            tested_at=datetime.now(timezone.utc),
            tester_id=tester_id,
            notes=notes,
        )
        self.db.add(test_run)
        await self.db.flush()
        return test_run
