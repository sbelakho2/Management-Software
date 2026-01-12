"""App-wide service singletons for KPI + muda nudging.

These are process-local singletons intended to be shared between:
- REST endpoints (e.g. KPI API)
- Background/scheduled workers (e.g. muda nudging)

Note: KPIService is currently in-memory; persistence/aggregation is handled elsewhere.
"""

from __future__ import annotations

from sensei.services.ops.jit_lean_learning import KnowledgeRetrievalEngine, MicroLessonEngine
from sensei.services.ops.kpi_metrics import KPIService
from sensei.services.ai.knowledge_enrichment import KnowledgeEnrichmentService
from sensei.services.ops.muda_contextual_nudging import MudaAwareContextualNudgingService


# Global KPI service instance
kpi_service = KPIService()

# Muda-aware micro-lesson nudging (shares KPI in-memory store)
muda_lesson_engine = MicroLessonEngine()
muda_knowledge_engine = KnowledgeRetrievalEngine()
muda_knowledge_enrichment = KnowledgeEnrichmentService()
muda_nudging_service = MudaAwareContextualNudgingService(
    kpi_service=kpi_service,
    lesson_engine=muda_lesson_engine,
    knowledge_engine=muda_knowledge_engine,
    knowledge_enrichment=muda_knowledge_enrichment,
    knowledge_actor_roles={"ops"},
)
