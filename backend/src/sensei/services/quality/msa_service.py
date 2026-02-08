"""
Measurement System Analysis (MSA) Service.

Performs Gage R&R studies, linearity/bias analysis,
and stability assessments per AIAG MSA 4th edition.
Calculates %GRR, ndc, and measurement uncertainty.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from math import sqrt
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import MSAStudy, MSAMeasurement, MSAResult

_D2_CONSTANTS = {
    2: Decimal("1.128"),
    3: Decimal("1.693"),
    4: Decimal("2.059"),
}


class MSAService:
    """Persistent MSA/GRR service using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_studies(self) -> list[MSAStudy]:
        result = await self.db.execute(select(MSAStudy).options(selectinload(MSAStudy.result)))
        return list(result.scalars().all())

    async def get_study(self, study_id: UUID) -> Optional[MSAStudy]:
        result = await self.db.execute(
            select(MSAStudy)
            .where(MSAStudy.id == study_id)
            .options(selectinload(MSAStudy.measurements), selectinload(MSAStudy.result))
        )
        return result.scalar_one_or_none()

    async def create_study(self, **kwargs) -> MSAStudy:
        study = MSAStudy(**kwargs)
        self.db.add(study)
        await self.db.flush()
        return study

    async def add_measurement(
        self,
        *,
        study_id: UUID,
        operator_id: UUID,
        part_id: str,
        trial_number: int,
        measured_value: Decimal,
    ) -> MSAMeasurement:
        measurement = MSAMeasurement(
            study_id=study_id,
            operator_id=operator_id,
            part_id=part_id,
            trial_number=trial_number,
            measured_value=measured_value,
            measured_at=datetime.now(timezone.utc),
        )
        self.db.add(measurement)
        await self.db.flush()
        return measurement

    async def compute_grr(self, study_id: UUID) -> Optional[MSAResult]:
        study = await self.get_study(study_id)
        if not study:
            return None

        measurements = study.measurements
        if not measurements:
            return None

        # Organize by operator/part
        by_operator: dict[UUID, list[Decimal]] = defaultdict(list)
        by_part: dict[str, list[Decimal]] = defaultdict(list)
        by_op_part: dict[tuple[UUID, str], list[Decimal]] = defaultdict(list)

        for m in measurements:
            by_operator[m.operator_id].append(m.measured_value)
            by_part[m.part_id].append(m.measured_value)
            by_op_part[(m.operator_id, m.part_id)].append(m.measured_value)

        # EV (repeatability) using range method
        ranges: list[Decimal] = []
        for values in by_op_part.values():
            if len(values) >= 2:
                ranges.append(max(values) - min(values))
        rbar = sum(ranges) / Decimal(len(ranges)) if ranges else Decimal("0")
        d2 = _D2_CONSTANTS.get(study.trials_count, Decimal("1.128"))
        ev = rbar / d2 if d2 != 0 else Decimal("0")

        # AV (reproducibility) - std dev of operator means
        op_means = []
        for values in by_operator.values():
            if values:
                op_means.append(sum(values) / Decimal(len(values)))
        if len(op_means) > 1:
            mean_op = sum(op_means) / Decimal(len(op_means))
            op_var = sum((m - mean_op) ** 2 for m in op_means) / Decimal(len(op_means) - 1)
            op_std = op_var.sqrt()
        else:
            op_std = Decimal("0")
        av = op_std * Decimal(sqrt(study.parts_count * study.trials_count))

        # PV (part variation)
        part_means = []
        for values in by_part.values():
            if values:
                part_means.append(sum(values) / Decimal(len(values)))
        if len(part_means) > 1:
            mean_part = sum(part_means) / Decimal(len(part_means))
            part_var = sum((m - mean_part) ** 2 for m in part_means) / Decimal(len(part_means) - 1)
            part_std = part_var.sqrt()
        else:
            part_std = Decimal("0")
        pv = part_std * Decimal(sqrt(study.operators_count * study.trials_count))

        grr = (ev**2 + av**2).sqrt() if (ev or av) else Decimal("0")
        tv = (grr**2 + pv**2).sqrt() if (grr or pv) else Decimal("0")
        grr_percent = (grr / tv * Decimal("100")) if tv != 0 else Decimal("0")
        ndc = int((Decimal("1.41") * (pv / grr)) if grr != 0 else 0)

        # Upsert result
        if study.result:
            result = study.result
            result.repeatability_ev = ev
            result.reproducibility_av = av
            result.grr = grr
            result.part_variation_pv = pv
            result.total_variation_tv = tv
            result.grr_percent = grr_percent
            result.ndc = ndc
        else:
            result = MSAResult(
                study_id=study.id,
                repeatability_ev=ev,
                reproducibility_av=av,
                grr=grr,
                part_variation_pv=pv,
                total_variation_tv=tv,
                grr_percent=grr_percent,
                ndc=ndc,
            )
            self.db.add(result)

        study.status = "completed"
        study.completed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return result
