"""Quality certification gating.

Development Plan 23.2: ensure the Quality system is comprehensive and integrated
with training/certification requirements.

This service enforces that inspection records can only be created by users who
meet mandatory skill requirements for the relevant station/product.

It is deterministic and DB-backed via the existing training models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.exceptions import ConflictError
from sensei.models.training import CertificationStatus, SkillRequirement, UserSkill


@dataclass(frozen=True)
class CertificationCheckResult:
    required_skill_ids: list[int]
    missing_skill_ids: list[int]


class QualityCertificationGate:
    """Validates that users meet mandatory certification requirements."""

    async def assert_user_can_record_inspection(
        self,
        db: AsyncSession,
        *,
        user_id: object | None,
        station_id: int | None,
        product_id: int | None,
    ) -> CertificationCheckResult:
        if user_id is None:
            raise ConflictError("Inspector identity is required")

        if station_id is None and product_id is None:
            return CertificationCheckResult(required_skill_ids=[], missing_skill_ids=[])

        conditions = []
        if station_id is not None:
            conditions.append(SkillRequirement.station_id == station_id)
        if product_id is not None:
            conditions.append(SkillRequirement.product_id == product_id)

        if not conditions:
            return CertificationCheckResult(required_skill_ids=[], missing_skill_ids=[])

        req_result = await db.execute(
            select(SkillRequirement).where(
                SkillRequirement.is_mandatory.is_(True),
                or_(*conditions),
            )
        )
        requirements = req_result.scalars().all()
        if not requirements:
            return CertificationCheckResult(required_skill_ids=[], missing_skill_ids=[])

        # Merge by skill_id taking the strictest (max) minimum level.
        required_min_level: dict[int, int] = {}
        for req in requirements:
            required_min_level[req.skill_id] = max(
                required_min_level.get(req.skill_id, 0),
                req.minimum_proficiency_level,
            )

        required_skill_ids = sorted(required_min_level.keys())

        skills_result = await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id.in_(required_skill_ids),
            )
        )
        user_skills = {us.skill_id: us for us in skills_result.scalars().all()}

        today = date.today()
        missing: list[int] = []

        for skill_id, min_level in required_min_level.items():
            us = user_skills.get(skill_id)
            if us is None:
                missing.append(skill_id)
                continue
            if us.certification_status != CertificationStatus.CERTIFIED:
                missing.append(skill_id)
                continue
            if us.proficiency_level < min_level:
                missing.append(skill_id)
                continue
            if us.expiration_date is not None and us.expiration_date < today:
                missing.append(skill_id)
                continue

        if missing:
            raise ConflictError(
                "Inspector is not certified for required skills",
                details={
                    "required_skill_ids": required_skill_ids,
                    "missing_skill_ids": sorted(set(missing)),
                },
            )

        return CertificationCheckResult(required_skill_ids=required_skill_ids, missing_skill_ids=[])


_service: Optional[QualityCertificationGate] = None


def get_quality_certification_gate() -> QualityCertificationGate:
    global _service
    if _service is None:
        _service = QualityCertificationGate()
    return _service
