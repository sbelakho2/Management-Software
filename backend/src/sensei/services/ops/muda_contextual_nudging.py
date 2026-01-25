"""Muda-aware contextual nudging.

Maps operational variance (via KPI snapshots and optional overrides) to Lean micro-lessons.

This is intentionally deterministic and dependency-injected:
- Uses KPIService latest values when present
- Allows callers to pass additional operational signals (inventory days, changeover time, etc.)
- Produces micro-lesson deliveries with trigger context
- Optionally recommends TPS knowledge-pack documents
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from sensei.core.config import settings
from sensei.services.ops.jit_lean_learning import (
    KnowledgeRetrievalEngine,
    MicroLessonEngine,
    TriggerType,
)
from sensei.services.ops.kpi_metrics import KPIService, KPIValue
from sensei.services.ai.knowledge_enrichment import KnowledgeEnrichmentService


@dataclass(frozen=True)
class MudaNudge:
    """A generated muda-aware micro-lesson nudge."""

    trigger: TriggerType
    recipient_id: str
    trigger_context: dict[str, Any]

    delivery_id: str | None
    lesson_id: str | None
    lesson_title: str | None
    lesson_summary: str | None
    lesson_category: str | None

    recommended_documents: list[dict[str, Any]]
    generated_at: datetime


class MudaAwareContextualNudgingService:
    """Detects muda-related anomalies and generates contextual micro-lessons."""

    def __init__(
        self,
        kpi_service: KPIService,
        lesson_engine: MicroLessonEngine | None = None,
        knowledge_engine: KnowledgeRetrievalEngine | None = None,
        knowledge_enrichment: KnowledgeEnrichmentService | None = None,
        knowledge_actor_roles: set[str] | None = None,
    ) -> None:
        self.kpi_service = kpi_service
        self.lesson_engine = lesson_engine or MicroLessonEngine()
        self.knowledge_engine = knowledge_engine or KnowledgeRetrievalEngine()
        self.knowledge_enrichment = knowledge_enrichment
        self.knowledge_actor_roles = knowledge_actor_roles or {"ops"}

    def build_operational_snapshot(
        self,
        *,
        dimensions: dict[str, str] | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build an operational snapshot from KPIs and optional overrides.

        Snapshot keys intentionally align with MicroLessonEngine.detect_trigger().
        """

        snapshot: dict[str, Any] = {}

        fpy = self._get_latest_value("first-pass-yield", dimensions)
        if fpy is not None:
            # MicroLessonEngine expects defect_rate_pct; convert FPY to defect rate.
            snapshot["defect_rate_pct"] = max(0.0, min(100.0, 100.0 - fpy))

        oee = self._get_latest_value("oee", dimensions)
        if oee is not None:
            snapshot["oee_pct"] = oee

        takt_adherence = self._get_latest_value("takt-adherence", dimensions)
        if takt_adherence is not None:
            # If takt adherence drops, downstream experiences waiting. Use deviation as a proxy.
            snapshot["idle_time_pct"] = max(0.0, min(100.0, 100.0 - takt_adherence))

        if overrides:
            snapshot.update(overrides)

        return snapshot

    def evaluate_triggers(self, snapshot: dict[str, Any]) -> list[TriggerType]:
        """Evaluate triggers in priority order.

        MicroLessonEngine.detect_trigger() returns only the first match;
        muda nudging should surface multiple relevant micro-lessons.
        """

        triggers: list[TriggerType] = []

        # Explicit abnormal events first.
        if snapshot.get("equipment_down"):
            triggers.append(TriggerType.EQUIPMENT_FAILURE)
        if snapshot.get("quality_hold"):
            triggers.append(TriggerType.QUALITY_ISSUE)

        # Rate/threshold based anomalies.
        if snapshot.get("defect_rate_pct", 0) > settings.MUDA_THRESHOLD_DEFECT_RATE_PCT:
            triggers.append(TriggerType.HIGH_DEFECT_RATE)
        if snapshot.get("oee_pct", 100) < settings.MUDA_THRESHOLD_OEE_PCT:
            triggers.append(TriggerType.LOW_OEE)
        if snapshot.get("changeover_time_minutes", 0) > settings.MUDA_THRESHOLD_CHANGEOVER_MINUTES:
            triggers.append(TriggerType.HIGH_CHANGEOVER_TIME)
        if snapshot.get("inventory_days", 0) > settings.MUDA_THRESHOLD_INVENTORY_DAYS:
            triggers.append(TriggerType.HIGH_INVENTORY)
        if snapshot.get("idle_time_pct", 0) > settings.MUDA_THRESHOLD_IDLE_TIME_PCT:
            triggers.append(TriggerType.WAITING_WASTE)

        # Deduplicate while preserving order.
        seen: set[TriggerType] = set()
        ordered: list[TriggerType] = []
        for trigger in triggers:
            if trigger not in seen:
                ordered.append(trigger)
                seen.add(trigger)
        return ordered

    async def generate_nudges(
        self,
        db: AsyncSession | None,
        *,
        recipient_id: UUID | str,
        dimensions: dict[str, str] | None = None,
        overrides: dict[str, Any] | None = None,
        include_knowledge: bool = True,
    ) -> list[MudaNudge]:
        snapshot = self.build_operational_snapshot(dimensions=dimensions, overrides=overrides)
        triggers = self.evaluate_triggers(snapshot)

        nudges: list[MudaNudge] = []
        now = datetime.now(timezone.utc)

        for trigger in triggers:
            nudges.append(
                await self.generate_nudge_for_trigger(
                    db=db,
                    trigger=trigger,
                    recipient_id=recipient_id,
                    trigger_context=snapshot,
                    include_knowledge=include_knowledge,
                    generated_at=now,
                )
            )

        return nudges

    async def generate_nudge_for_trigger(
        self,
        db: AsyncSession | None = None,
        *,
        trigger: TriggerType,
        recipient_id: UUID | str,
        trigger_context: dict[str, Any],
        include_knowledge: bool = True,
        generated_at: datetime | None = None,
    ) -> MudaNudge:
        """Generate a single nudge for a specific trigger."""

        if db is None or not isinstance(recipient_id, UUID):
            delivery = self.lesson_engine.get_lesson_for_trigger(
                trigger,
                str(recipient_id),
                trigger_context,
            )
            lesson = self.lesson_engine.get_lesson_content(delivery.lesson_id) if delivery else None
        else:
            delivery = await self.lesson_engine.get_lesson_for_trigger_async(
                db,
                trigger,
                recipient_id,
                context=trigger_context,
            )
            lesson = self.lesson_engine.get_lesson_content(delivery.lesson_id) if delivery else None

        recommended_documents: list[dict[str, Any]] = []
        if include_knowledge:
            query = self._knowledge_query_for_trigger(trigger, trigger_context)
            recommended_documents = self._recommend_knowledge(query)

        now = generated_at or datetime.now(timezone.utc)
        return MudaNudge(
            trigger=trigger,
            recipient_id=str(recipient_id),
            trigger_context=trigger_context,
            delivery_id=(str(delivery.id) if hasattr(delivery, "id") else delivery.delivery_id) if delivery else None,
            lesson_id=delivery.lesson_id if delivery else None,
            lesson_title=lesson.title if lesson else None,
            lesson_summary=lesson.summary if lesson else None,
            lesson_category=lesson.category.value if lesson else None,
            recommended_documents=recommended_documents,
            generated_at=now,
        )

    def _get_latest_value(self, kpi_id: str, dimensions: dict[str, str] | None) -> float | None:
        latest: KPIValue | None = self.kpi_service.get_latest_value(kpi_id, dimensions=dimensions)
        if not latest:
            return None
        return float(latest.value)

    def _knowledge_query_for_trigger(self, trigger: TriggerType, snapshot: dict[str, Any]) -> str:
        if trigger in (TriggerType.HIGH_DEFECT_RATE, TriggerType.QUALITY_ISSUE):
            return "defect prevention poka-yoke jidoka root cause"
        if trigger == TriggerType.LOW_OEE:
            return "oee availability performance quality tpm"
        if trigger == TriggerType.HIGH_CHANGEOVER_TIME:
            return "changeover setup reduction smed"
        if trigger == TriggerType.HIGH_INVENTORY:
            return "inventory wip kanban sizing pull system"
        if trigger == TriggerType.WAITING_WASTE:
            return "waiting waste flow value stream mapping kanban"
        if trigger == TriggerType.EQUIPMENT_FAILURE:
            return "equipment downtime maintenance tpm"

        # Fallback: keywords from snapshot.
        return " ".join(str(v) for v in snapshot.values() if isinstance(v, (str, int, float)))

    def _recommend_knowledge(self, query: str) -> list[dict[str, Any]]:
        """Recommend knowledge from the ingested TPS pack when available.

        Prefers KnowledgeEnrichmentService (Section 22.13) because it reflects the
        ingested corpus; falls back to the lightweight KnowledgeRetrievalEngine.
        """

        if self.knowledge_enrichment is not None:
            chunks = self.knowledge_enrichment.search_chunks_by_keyword(
                actor_roles=self.knowledge_actor_roles,
                keyword=query,
                limit=5,
            )
            return [
                {
                    "chunk_id": str(c.id),
                    "source_id": str(c.source_id),
                    "chunk_type": c.chunk_type.value,
                    "taxonomy_categories": [cat.value for cat in c.taxonomy_categories],
                    "citation": c.citation,
                    "content": c.content,
                }
                for c in chunks
            ]

        results = self.knowledge_engine.search_documents(query, a3_field=None, max_results=5)
        return [
            {
                "document_id": doc.document_id,
                "title": doc.title,
                "category": doc.category.value,
                "summary": doc.summary,
                "relevance_score": score,
            }
            for doc, score in results
        ]
