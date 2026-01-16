from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.quality_qms import ChangePointStudy, ChangePointObservation, ChangePointEvent


class ChangePointService:
    """Service for change point control studies."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_studies(self) -> list[ChangePointStudy]:
        result = await self.db.execute(select(ChangePointStudy))
        return list(result.scalars().all())

    async def get_study(self, study_id: UUID) -> Optional[ChangePointStudy]:
        result = await self.db.execute(select(ChangePointStudy).where(ChangePointStudy.id == study_id))
        return result.scalar_one_or_none()

    async def create_study(self, **kwargs) -> ChangePointStudy:
        study = ChangePointStudy(**kwargs)
        self.db.add(study)
        await self.db.flush()
        return study

    async def add_observation(self, **kwargs) -> ChangePointObservation:
        observation = ChangePointObservation(**kwargs)
        self.db.add(observation)
        await self.db.flush()
        return observation

    async def list_observations(self, study_id: UUID) -> list[ChangePointObservation]:
        result = await self.db.execute(
            select(ChangePointObservation).where(ChangePointObservation.study_id == study_id)
        )
        return list(result.scalars().all())

    async def list_events(self, study_id: UUID) -> list[ChangePointEvent]:
        result = await self.db.execute(
            select(ChangePointEvent).where(ChangePointEvent.study_id == study_id)
        )
        return list(result.scalars().all())

    async def detect_change_points(self, study: ChangePointStudy) -> Optional[ChangePointEvent]:
        observations = await self.list_observations(study.id)
        if len(observations) < 4:
            return None

        values = [obs.value for obs in observations]
        mid = len(values) // 2
        first_mean = sum(values[:mid]) / Decimal(mid)
        second_mean = sum(values[mid:]) / Decimal(len(values) - mid)
        magnitude = second_mean - first_mean

        threshold = study.sensitivity if study.sensitivity is not None else Decimal("0.5")
        if abs(magnitude) < threshold:
            return None

        event = ChangePointEvent(
            study_id=study.id,
            detected_at=datetime.now(timezone.utc),
            index_position=mid,
            change_magnitude=magnitude,
            confidence=Decimal("0.75"),
            notes=f"Mean shift detected ({first_mean:.3f} -> {second_mean:.3f})",
        )
        self.db.add(event)
        await self.db.flush()
        return event
