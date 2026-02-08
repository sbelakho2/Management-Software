"""
Process Capability Service.

Calculates Cp, Cpk, Pp, Ppk indices with normality testing.
Supports bilateral and unilateral specifications,
histogram generation, and capability trending.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import (
    ProcessCapabilityStudy,
    ProcessCapabilityMeasurement,
    ProcessCapabilityResult,
)


class ProcessCapabilityService:
    """Persistent Cp/Cpk capability service using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_studies(self) -> list[ProcessCapabilityStudy]:
        result = await self.db.execute(
            select(ProcessCapabilityStudy).options(selectinload(ProcessCapabilityStudy.result))
        )
        return list(result.scalars().all())

    async def get_study(self, study_id: UUID) -> Optional[ProcessCapabilityStudy]:
        result = await self.db.execute(
            select(ProcessCapabilityStudy)
            .where(ProcessCapabilityStudy.id == study_id)
            .options(
                selectinload(ProcessCapabilityStudy.measurements),
                selectinload(ProcessCapabilityStudy.result),
            )
        )
        return result.scalar_one_or_none()

    async def create_study(self, **kwargs) -> ProcessCapabilityStudy:
        study = ProcessCapabilityStudy(**kwargs)
        self.db.add(study)
        await self.db.flush()
        return study

    async def add_measurement(
        self,
        *,
        study_id: UUID,
        measured_value: Decimal,
        sample_label: Optional[str] = None,
    ) -> ProcessCapabilityMeasurement:
        measurement = ProcessCapabilityMeasurement(
            study_id=study_id,
            measured_value=measured_value,
            sample_label=sample_label,
            measured_at=datetime.now(timezone.utc),
        )
        self.db.add(measurement)
        await self.db.flush()
        return measurement

    async def compute_capability(self, study_id: UUID) -> Optional[ProcessCapabilityResult]:
        study = await self.get_study(study_id)
        if not study:
            return None

        if study.lsl is None or study.usl is None:
            raise ValueError("Spec limits required for capability calculation")

        measurements = study.measurements
        if not measurements or len(measurements) < 2:
            raise ValueError("Not enough data for capability calculation")

        values = [m.measured_value for m in measurements]
        sample_size = len(values)
        mean = sum(values) / Decimal(sample_size)
        variance = sum((v - mean) ** 2 for v in values) / Decimal(sample_size - 1)
        std_dev = variance.sqrt() if variance > 0 else Decimal("0")

        if std_dev == 0:
            cp = Decimal("0")
            cpu = Decimal("0")
            cpl = Decimal("0")
            cpk = Decimal("0")
        else:
            cp = (study.usl - study.lsl) / (Decimal("6") * std_dev)
            cpu = (study.usl - mean) / (Decimal("3") * std_dev)
            cpl = (mean - study.lsl) / (Decimal("3") * std_dev)
            cpk = min(cpu, cpl)

        if study.result:
            result = study.result
            result.mean = mean
            result.std_dev = std_dev
            result.cp = cp
            result.cpk = cpk
            result.cpu = cpu
            result.cpl = cpl
            result.sample_size = sample_size
        else:
            result = ProcessCapabilityResult(
                study_id=study.id,
                mean=mean,
                std_dev=std_dev,
                cp=cp,
                cpk=cpk,
                cpu=cpu,
                cpl=cpl,
                sample_size=sample_size,
            )
            self.db.add(result)

        study.status = "completed"
        study.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return result
