"""Autonomous Standard Work Evolution.

Analyzes effectiveness of A3 countermeasures against KPI time series, and when
success patterns are detected, drafts proposed StandardWork revisions.

Design goals:
- Deterministic + testable (no LLM calls)
- Cross-module: A3 -> KPI -> StandardWork
- Transport-agnostic: usable from API endpoints, schedulers, workers

Assumptions:
- KPI time series is provided via KPIService (currently in-memory)
- A3.custom_fields carries links/criteria needed for automation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.a3 import A3, A3SectionType
from sensei.models.standard_work import StandardWork, StandardWorkStatus
from sensei.core.time import utcnow_naive
from sensei.services.ops.kpi_metrics import KPIService


SYSTEM_ACTOR_ID = UUID("00000000-0000-0000-0000-000000000001")


@dataclass(frozen=True)
class KPIImpact:
    kpi_id: str
    before_avg: float | None
    after_avg: float | None
    delta: float | None
    delta_pct: float | None
    improved: bool
    window_days_pre: int
    window_days_post: int


@dataclass(frozen=True)
class EvolutionDecision:
    a3_id: UUID
    a3_number: str
    success: bool
    impacts: list[KPIImpact]
    drafted_standard_work_ids: list[int]


class AutonomousStandardWorkEvolutionService:
    """Evaluates A3 KPI impact and drafts StandardWork revisions on success."""

    def __init__(self, *, kpi_service: KPIService) -> None:
        self.kpi_service = kpi_service

    async def evaluate_and_draft(
        self,
        db: AsyncSession,
        *,
        a3_id: UUID,
        actor_user_id: UUID = SYSTEM_ACTOR_ID,
        min_improvement_pct: float = 2.0,
        window_days_pre: int = 7,
        window_days_post: int = 7,
        default_kpis: list[str] | None = None,
    ) -> EvolutionDecision:
        """Evaluate one A3 and draft StandardWork revisions if successful.

        Criteria and linkages are sourced from A3.custom_fields when present:
        - `linked_standard_work_ids`: list[int]
        - `success_kpis`: list[str]
        - `kpi_dimensions`: dict[str, str]
        - `min_improvement_pct`, `window_days_pre`, `window_days_post`: overrides
        """

        a3 = await self._load_a3(db, a3_id)

        criteria = a3.custom_fields or {}
        linked_sw_ids = self._as_int_list(criteria.get("linked_standard_work_ids"))
        kpis = self._as_str_list(
            criteria.get("success_kpis")
            or default_kpis
            or ["first-pass-yield", "takt-adherence"]
        )

        dims = criteria.get("kpi_dimensions")
        if not isinstance(dims, dict):
            dims = None

        min_pct = float(criteria.get("min_improvement_pct", min_improvement_pct))
        pre_days = int(criteria.get("window_days_pre", window_days_pre))
        post_days = int(criteria.get("window_days_post", window_days_post))

        impacts = self._evaluate_kpis(
            a3=a3,
            kpi_ids=kpis,
            min_improvement_pct=min_pct,
            window_days_pre=pre_days,
            window_days_post=post_days,
            dimensions=dims,
        )

        success = any(i.improved for i in impacts)
        drafted: list[int] = []

        if success and linked_sw_ids:
            drafted = await self._draft_revisions(
                db,
                a3=a3,
                standard_work_ids=linked_sw_ids,
                actor_user_id=actor_user_id,
            )

        # Persist decision back onto A3 for auditability.
        a3.custom_fields = {
            **(a3.custom_fields or {}),
            "kpi_effectiveness": {
                "evaluated_at": utcnow_naive().isoformat(),
                "success": success,
                "impacts": [
                    {
                        "kpi_id": i.kpi_id,
                        "before_avg": i.before_avg,
                        "after_avg": i.after_avg,
                        "delta": i.delta,
                        "delta_pct": i.delta_pct,
                        "improved": i.improved,
                        "window_days_pre": i.window_days_pre,
                        "window_days_post": i.window_days_post,
                    }
                    for i in impacts
                ],
            },
            "drafted_standard_work_ids": drafted,
        }

        await db.flush()

        return EvolutionDecision(
            a3_id=a3.id,
            a3_number=a3.a3_number,
            success=success,
            impacts=impacts,
            drafted_standard_work_ids=drafted,
        )

    async def evaluate_recent_a3s(
        self,
        db: AsyncSession,
        *,
        since_days: int = 90,
        actor_user_id: UUID = SYSTEM_ACTOR_ID,
    ) -> list[EvolutionDecision]:
        """Evaluate recently completed A3s and draft standard work updates."""

        cutoff = utcnow_naive() - timedelta(days=since_days)
        stmt = select(A3).where(
            and_(
                A3.deleted_at.is_(None),
                A3.actual_completion_date.is_not(None),
                A3.actual_completion_date >= cutoff,
                A3.status.in_(["implemented", "closed"]),
            )
        )
        result = await db.execute(stmt)
        a3s = list(result.scalars().all())

        decisions: list[EvolutionDecision] = []
        for a3 in a3s:
            decisions.append(
                await self.evaluate_and_draft(
                    db,
                    a3_id=a3.id,
                    actor_user_id=actor_user_id,
                )
            )

        return decisions

    # -----------------
    # Internal helpers
    # -----------------

    async def _load_a3(self, db: AsyncSession, a3_id: UUID) -> A3:
        stmt = select(A3).where(and_(A3.id == a3_id, A3.deleted_at.is_(None)))
        result = await db.execute(stmt)
        a3 = result.scalar_one_or_none()
        if not a3:
            raise ValueError(f"A3 {a3_id} not found")
        return a3

    def _evaluate_kpis(
        self,
        *,
        a3: A3,
        kpi_ids: list[str],
        min_improvement_pct: float,
        window_days_pre: int,
        window_days_post: int,
        dimensions: dict[str, str] | None,
    ) -> list[KPIImpact]:
        completed_at = a3.actual_completion_date or a3.updated_at
        if completed_at is None:
            completed_at = utcnow_naive()

        pre_start = completed_at - timedelta(days=window_days_pre)
        pre_end = completed_at
        post_start = completed_at
        post_end = completed_at + timedelta(days=window_days_post)

        impacts: list[KPIImpact] = []
        for kpi_id in kpi_ids:
            before_values = self._values_in_window(kpi_id, pre_start, pre_end, dimensions)
            after_values = self._values_in_window(kpi_id, post_start, post_end, dimensions)

            before_avg = self._avg(before_values)
            after_avg = self._avg(after_values)

            delta = None
            delta_pct = None
            improved = False

            if before_avg is not None and after_avg is not None:
                delta = after_avg - before_avg
                if before_avg != 0:
                    delta_pct = (delta / before_avg) * 100.0

                definition = self.kpi_service.get_definition(kpi_id)
                direction = getattr(definition, "direction", None)
                direction_str = str(direction)

                if direction_str in {
                    "higher_is_better",
                    "KPIDirection.HIGHER_IS_BETTER",
                    "KPIDirection.higher_is_better",
                }:
                    improved = (delta_pct or 0.0) >= min_improvement_pct
                elif direction_str in {
                    "target_is_best",
                    "KPIDirection.TARGET_IS_BEST",
                    "KPIDirection.target_is_best",
                }:
                    threshold = getattr(definition, "threshold", None)
                    target = getattr(threshold, "target", None)
                    if isinstance(target, (int, float)):
                        before_err = abs(before_avg - float(target))
                        after_err = abs(after_avg - float(target))
                        if before_err == 0:
                            improved = after_err == 0
                        else:
                            err_reduction_pct = ((before_err - after_err) / before_err) * 100.0
                            improved = err_reduction_pct >= min_improvement_pct
                    else:
                        # No explicit target configured; fall back to treating higher as better.
                        improved = (delta_pct or 0.0) >= min_improvement_pct
                else:
                    # If lower is better (or unknown), treat a decrease as improvement.
                    improved = (delta_pct or 0.0) <= -min_improvement_pct

            impacts.append(
                KPIImpact(
                    kpi_id=kpi_id,
                    before_avg=before_avg,
                    after_avg=after_avg,
                    delta=delta,
                    delta_pct=delta_pct,
                    improved=improved,
                    window_days_pre=window_days_pre,
                    window_days_post=window_days_post,
                )
            )

        return impacts

    def _values_in_window(
        self,
        kpi_id: str,
        start: datetime,
        end: datetime,
        dimensions: dict[str, str] | None,
    ) -> list[float]:
        # KPIService doesn't currently expose a datetime-range query.
        # Keep this deterministic by filtering the stored values.
        values = self.kpi_service.get_values(
            kpi_id,
            start_date=start.date(),
            end_date=end.date(),
            dimensions=dimensions,
        )
        return [
            v.value
            for v in values
            if v.timestamp >= start and v.timestamp <= end
        ]

    async def _draft_revisions(
        self,
        db: AsyncSession,
        *,
        a3: A3,
        standard_work_ids: list[int],
        actor_user_id: UUID,
    ) -> list[int]:
        drafted: list[int] = []
        countermeasures = self._extract_countermeasures(a3)
        countermeasure_summary = (countermeasures or "").strip()
        if len(countermeasure_summary) > 240:
            countermeasure_summary = countermeasure_summary[:240].rstrip() + "…"

        for sw_id in standard_work_ids:
            sw = await self._load_standard_work(db, sw_id)
            if sw.status != StandardWorkStatus.APPROVED:
                continue

            # Avoid duplicate draft revisions for same document.
            draft_stmt = select(StandardWork).where(
                and_(
                    StandardWork.document_number == sw.document_number,
                    StandardWork.status == StandardWorkStatus.DRAFT,
                    StandardWork.deleted_at.is_(None),
                )
            )
            draft_result = await db.execute(draft_stmt)
            if draft_result.scalar_one_or_none():
                continue

            new_work = sw.create_new_version()
            new_work.created_by_id = actor_user_id
            new_work.change_summary = (
                f"Auto-draft from A3 {a3.a3_number}: {countermeasure_summary}"
                if countermeasure_summary
                else f"Auto-draft from A3 {a3.a3_number}"
            )

            if new_work.content_json and isinstance(new_work.content_json, dict):
                existing_notes = new_work.content_json.get("revision_notes")
                if not existing_notes:
                    new_work.content_json["revision_notes"] = new_work.change_summary

            db.add(new_work)
            await db.flush()
            drafted.append(int(new_work.id))

        return drafted

    async def _load_standard_work(self, db: AsyncSession, standard_work_id: int) -> StandardWork:
        stmt = select(StandardWork).where(
            and_(
                StandardWork.id == standard_work_id,
                StandardWork.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        sw = result.scalar_one_or_none()
        if not sw:
            raise ValueError(f"StandardWork {standard_work_id} not found")
        return sw

    def _extract_countermeasures(self, a3: A3) -> str:
        # Prefer structured content if present; fall back to free text.
        for section in a3.sections or []:
            if section.section_type != A3SectionType.COUNTERMEASURES.value:
                continue

            if section.structured_content and isinstance(section.structured_content, dict):
                sc = section.structured_content
                for key in ("actions", "action_items", "countermeasures"):
                    items = sc.get(key)
                    if isinstance(items, list) and items:
                        lines: list[str] = []
                        for item in items:
                            if isinstance(item, str):
                                lines.append(item)
                            elif isinstance(item, dict):
                                text = item.get("text") or item.get("description") or item.get("action")
                                if isinstance(text, str) and text.strip():
                                    lines.append(text.strip())
                        if lines:
                            return "\n".join(lines)

            if section.content and section.content.strip():
                return section.content.strip()

        return ""

    def _avg(self, values: Iterable[float]) -> float | None:
        vals = list(values)
        if not vals:
            return None
        return sum(vals) / len(vals)

    def _as_int_list(self, value: Any) -> list[int]:
        if isinstance(value, list):
            out: list[int] = []
            for v in value:
                if isinstance(v, int):
                    out.append(v)
                elif isinstance(v, str) and v.isdigit():
                    out.append(int(v))
            return out
        return []

    def _as_str_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v) for v in value if isinstance(v, (str, int, float))]
        if isinstance(value, str):
            return [value]
        return []
