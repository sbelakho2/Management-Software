import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

        # PCBA specific checks (mocked)
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
        # Fallback for non-postgresql environments (sqlite during tests)
        if self.session.bind.dialect.name != "postgresql":
            stmt = (
                select(RFQ)
                .where(RFQ.id != rfq_id)
                .where(RFQ.status.in_(["won", "lost"]))
                .limit(5)
            )
            result = await self.session.execute(stmt)
            similar_rfqs = [(r, 0.1) for r in result.scalars().all()] # Mock distance
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
        # Mock generative narrative
        return "This quote is based on the provided BOM version 1.2 and assumes standard lead times for all materials. Turnkey assembly includes AOI and final functional test."

def get_quoting_assist_service(session: AsyncSession) -> QuotingAssistService:
    return QuotingAssistService(session)
