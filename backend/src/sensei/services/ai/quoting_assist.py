"""
AI Quoting Assistant.

Provides AI-powered quote generation, cost estimation,
and pricing recommendations using historical RFQ data
and machine learning models.
"""

import logging
import math
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sensei.api.deps import DBSession

from sensei.models.rfq import RFQ
from sensei.models.quote import Quote
from sensei.models.quoting_helper import WorkPacket
from sensei.services.ai.onnx_text_embeddings import get_onnx_embedder

logger = logging.getLogger(__name__)


class QuotingAssistService:
    """
    AI assistance for the Quoting Helper.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def suggest_clarifications(self, rfq_id: UUID) -> List[Dict[str, Any]]:
        """
        Stage 0 - Generate minimal clarification questions based on RFQ completeness.
        """
        rfq = await self.session.get(RFQ, rfq_id)
        if not rfq:
            return []

        # Logic to identify missing info
        questions = []
        if not rfq.due_date:
            questions.append({
                "question": "Could you please confirm the target delivery date?",
                "gate": "Sales",
                "risk_level": "medium"
            })
        
        if not rfq.quantity:
            questions.append({
                "question": "What are the required quantities for the quantity ladder?",
                "gate": "Sourcing",
                "risk_level": "high"
            })

        # PCBA specific checks
        if rfq.part_name and "PCBA" in rfq.part_name.upper():
            questions.append({
                "question": "Is the PCB finish specified (ENIG, HASL)?",
                "gate": "PCB Fab",
                "risk_level": "medium"
            })

        # Technical checks
        if not rfq.material_spec:
            questions.append({
                "question": "Could you please specify the material grade/specification?",
                "gate": "Hardware/ME",
                "risk_level": "medium"
            })

        if not rfq.finish_requirements:
            questions.append({
                "question": "What is the required surface finish or coating?",
                "gate": "Manufacturing",
                "risk_level": "low"
            })

        return questions[:8] # Max 8 as per requirement

    async def retrieve_quote_memory(self, rfq_id: UUID) -> List[Dict[str, Any]]:
        """
        Retrieve similar historical jobs and extract proven assumptions using semantic search.
        """
        rfq = await self.session.get(RFQ, rfq_id)
        if not rfq:
            return []

        # If RFQ doesn't have an embedding yet, generate it
        if not rfq.embedding:
            embedder = get_onnx_embedder()
            text_to_embed = f"{rfq.title} {rfq.description or ''}"
            rfq.embedding = embedder.embed_text(text_to_embed)
            await self.session.commit()

        # Perform vector similarity search
        # Using cosine distance (<=> operator in pgvector)
        # Fallback for non-postgresql environments computes cosine similarity in Python
        if self.session.bind.dialect.name != "postgresql":
            stmt = (
                select(RFQ)
                .where(RFQ.id != rfq_id)
                .where(RFQ.status.in_(["won", "lost"]))
            )
            result = await self.session.execute(stmt)
            candidates = [r for r in result.scalars().all() if r.embedding]

            def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
                if not vec_a or not vec_b:
                    return 0.0
                dot = sum(a * b for a, b in zip(vec_a, vec_b))
                norm_a = math.sqrt(sum(a * a for a in vec_a))
                norm_b = math.sqrt(sum(b * b for b in vec_b))
                if norm_a == 0.0 or norm_b == 0.0:
                    return 0.0
                return dot / (norm_a * norm_b)

            ranked = []
            for candidate in candidates:
                similarity = _cosine_similarity(rfq.embedding, candidate.embedding)
                ranked.append((candidate, 1 - similarity))

            ranked.sort(key=lambda item: item[1])
            similar_rfqs = ranked[:5]
        else:
            stmt = (
                select(
                    RFQ,
                    RFQ.embedding.cosine_distance(rfq.embedding).label("distance")
                )
                .where(RFQ.id != rfq_id)
                .where(RFQ.status.in_(["won", "lost"]))
                .order_by("distance")
                .limit(5)
            )
            result = await self.session.execute(stmt)
            similar_rfqs = result.all()

        memory = []
        for s_rfq, dist in similar_rfqs:
            similarity = 1 - float(dist)
            if similarity < 0.7: # Threshold
                continue
                
            memory.append({
                "rfq_id": str(s_rfq.id),
                "rfq_number": s_rfq.rfq_number,
                "title": s_rfq.title,
                "similarity": round(similarity, 4),
                "reason": f"Semantic similarity match ({round(similarity*100)}%)",
                "past_assumptions": s_rfq.internal_notes.split("\n") if s_rfq.internal_notes else [],
                "outcome": s_rfq.status.capitalize()
            })

        return memory

    async def suggest_quote_narrative(self, quote_id: UUID) -> str:
        """
        Generate a draft quote narrative / assumptions.
        """
        quote = await self.session.get(Quote, quote_id)
        if not quote:
            return ""

        line_items = list(quote.line_items) if hasattr(quote, "line_items") and quote.line_items else []
        total_items = len(line_items)
        currency = quote.currency or ""
        lead_time = None
        if total_items > 0:
            lead_times = [item.lead_time_days for item in line_items if item.lead_time_days]
            lead_time = max(lead_times) if lead_times else None

        assumptions = []
        if quote.custom_fields and isinstance(quote.custom_fields, dict):
            for key in ("assumptions", "notes", "constraints"):
                value = quote.custom_fields.get(key)
                if isinstance(value, str) and value.strip():
                    assumptions.append(value.strip())

        if quote.notes:
            assumptions.append(quote.notes.strip())

        summary = [f"Quote {quote.quote_number} for {quote.title or 'customer request'}.".strip()]
        if total_items:
            summary.append(f"Includes {total_items} line item(s).")
        if quote.total:
            summary.append(f"Total estimated value: {quote.total} {currency}.".strip())
        if lead_time is not None:
            summary.append(f"Estimated lead time: {lead_time} day(s).")

        if assumptions:
            summary.append("Assumptions:")
            summary.extend(f"- {item}" for item in assumptions if item)

        return " ".join(summary)

def get_quoting_assist_service(session: DBSession) -> QuotingAssistService:
    return QuotingAssistService(session)
