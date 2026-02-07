"""Jidoka (AI Error-Proofing) suggestions.

Goal (Development Plan 23.1):
- Integrate Quality NCR/NC data with deterministic reasoning to suggest
  Poka-Yoke (mistake-proofing) opportunities during Work Order release.

This module is intentionally deterministic and testable (no LLM calls).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.quality import NonConformance, NCStatus, NCType, NCSource, RootCauseCategory
from sensei.models.work_order import WorkOrder

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JidokaSuggestion:
    title: str
    rationale: str
    actions: list[str]
    related_non_conformance_ids: list[int]
    confidence: float


class JidokaErrorProofingService:
    """Generates poka-yoke suggestions based on recent non-conformances."""

    async def suggest_for_work_order_release(
        self,
        db: AsyncSession,
        *,
        work_order_id: int,
        lookback_days: int = 180,
        max_non_conformances: int = 25,
        max_suggestions: int = 5,
    ) -> list[JidokaSuggestion]:
        wo = await self._load_work_order(db, work_order_id)

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=lookback_days)
        ncs = await self._load_recent_open_non_conformances(
            db,
            work_order_id=wo.id,
            product_id=wo.product_id,
            station_id=wo.current_station_id,
            cutoff=cutoff,
            limit=max_non_conformances,
        )

        if not ncs:
            return []

        buckets: dict[str, list[NonConformance]] = {
            "measurement": [],
            "mixup": [],
            "handling": [],
            "supplier": [],
            "process": [],
        }

        for nc in ncs:
            combined = self._combine_text(nc)

            if nc.root_cause_category == RootCauseCategory.MEASUREMENT or self._contains_any(
                combined,
                (
                    "out of spec",
                    "out-of-spec",
                    "dimension",
                    "tolerance",
                    "spec",
                    "gauge",
                    "calibration",
                    "measurement",
                ),
            ):
                buckets["measurement"].append(nc)

            if self._contains_any(
                combined,
                (
                    "wrong part",
                    "incorrect",
                    "swapped",
                    "mixed",
                    "mix-up",
                    "mix up",
                    "reversed",
                    "wrong orientation",
                ),
            ):
                buckets["mixup"].append(nc)

            if nc.nc_type in {NCType.HANDLING, NCType.PACKAGING} or self._contains_any(
                combined,
                (
                    "scratch",
                    "dent",
                    "damage",
                    "bent",
                    "cracked",
                    "scuff",
                    "handling",
                    "packaging",
                ),
            ):
                buckets["handling"].append(nc)

            if nc.nc_type == NCType.SUPPLIER or nc.source == NCSource.INCOMING_INSPECTION:
                buckets["supplier"].append(nc)

            if nc.nc_type == NCType.PROCESS or self._contains_any(
                combined,
                (
                    "setup",
                    "fixture",
                    "program",
                    "parameter",
                    "cycle",
                    "process",
                    "tool",
                ),
            ):
                buckets["process"].append(nc)

        suggestions: list[JidokaSuggestion] = []
        total = len(ncs)

        def conf(items: list[NonConformance]) -> float:
            return round(len(items) / total, 2) if total else 0.0

        if buckets["measurement"]:
            ids = [nc.id for nc in buckets["measurement"]]
            suggestions.append(
                JidokaSuggestion(
                    title="Add go/no-go or automated measurement checks",
                    rationale="Recent non-conformances indicate spec/measurement escapes.",
                    actions=[
                        "Add a go/no-go gauge or fixture-based check at the operation",
                        "Require first-article verification at start of shift/setup",
                        "Add gauge calibration check before use (Jidoka stop condition)",
                    ],
                    related_non_conformance_ids=ids,
                    confidence=conf(buckets["measurement"]),
                )
            )

        if buckets["mixup"]:
            ids = [nc.id for nc in buckets["mixup"]]
            suggestions.append(
                JidokaSuggestion(
                    title="Prevent part/assembly mix-ups with verification",
                    rationale="Recent non-conformances suggest wrong-part or orientation errors.",
                    actions=[
                        "Require barcode/QR scan of part + work order before operation",
                        "Add keyed fixtures or asymmetric locating pins to prevent reversal",
                        "Add a digital checklist interlock before proceeding",
                    ],
                    related_non_conformance_ids=ids,
                    confidence=conf(buckets["mixup"]),
                )
            )

        if buckets["handling"]:
            ids = [nc.id for nc in buckets["handling"]]
            suggestions.append(
                JidokaSuggestion(
                    title="Error-proof handling/packaging to prevent damage",
                    rationale="Recent non-conformances indicate damage during handling/packaging.",
                    actions=[
                        "Add protective dunnage/standard pack to prevent contact damage",
                        "Define visual standard for acceptable handling and staging",
                        "Add a damage check point with stop-the-line trigger",
                    ],
                    related_non_conformance_ids=ids,
                    confidence=conf(buckets["handling"]),
                )
            )

        if buckets["supplier"]:
            ids = [nc.id for nc in buckets["supplier"]]
            suggestions.append(
                JidokaSuggestion(
                    title="Strengthen incoming quality gates for suppliers",
                    rationale="Supplier/incoming non-conformances indicate upstream variation.",
                    actions=[
                        "Add incoming sampling plan or 100% check for critical features",
                        "Require supplier CoC/inspection record attachment",
                        "Trigger supplier corrective action workflow for repeat defects",
                    ],
                    related_non_conformance_ids=ids,
                    confidence=conf(buckets["supplier"]),
                )
            )

        if buckets["process"]:
            ids = [nc.id for nc in buckets["process"]]
            suggestions.append(
                JidokaSuggestion(
                    title="Add process interlocks and setup verification",
                    rationale="Process-related non-conformances suggest setup/parameter drift.",
                    actions=[
                        "Add setup parameter verification (digital sign-off) before run",
                        "Add tooling/fixture presence sensors where feasible",
                        "Trigger Andon when critical parameters are out of range",
                    ],
                    related_non_conformance_ids=ids,
                    confidence=conf(buckets["process"]),
                )
            )

        # Stable ordering: highest confidence first, then title.
        suggestions.sort(key=lambda s: (-s.confidence, s.title))
        return suggestions[:max_suggestions]

    async def _load_work_order(self, db: AsyncSession, work_order_id: int) -> WorkOrder:
        stmt = select(WorkOrder).where(and_(WorkOrder.id == work_order_id, WorkOrder.deleted_at.is_(None)))
        result = await db.execute(stmt)
        wo = result.scalar_one_or_none()
        if not wo:
            logger.warning("Work order %d not found for Jidoka analysis", work_order_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Work order {work_order_id} not found",
            )
        return wo

    async def _load_recent_open_non_conformances(
        self,
        db: AsyncSession,
        *,
        work_order_id: int,
        product_id: int,
        station_id: int | None,
        cutoff: datetime,
        limit: int,
    ) -> list[NonConformance]:
        filters = [
            NonConformance.deleted_at.is_(None),
            NonConformance.detected_at >= cutoff,
            NonConformance.status.notin_([NCStatus.CLOSED, NCStatus.ESCALATED_TO_CAPA]),
            or_(
                NonConformance.work_order_id == work_order_id,
                NonConformance.product_id == product_id,
                *( [NonConformance.station_id == station_id] if station_id is not None else [] ),
            ),
        ]

        stmt = (
            select(NonConformance)
            .where(and_(*filters))
            .order_by(NonConformance.detected_at.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _combine_text(self, nc: NonConformance) -> str:
        parts = [
            nc.title or "",
            nc.description or "",
            nc.specification_requirement or "",
            nc.actual_condition or "",
            nc.root_cause_description or "",
        ]
        return " ".join(p.strip() for p in parts if p).lower()

    def _contains_any(self, text: str, needles: tuple[str, ...]) -> bool:
        return any(n in text for n in needles)
