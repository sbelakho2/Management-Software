"""
Quality Traceability Service.

Provides end-to-end traceability linking inspections,
NCRs, CAPAs, and audit findings to source materials,
processes, and customer complaints.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.quality_qms import TraceabilityMatrix, TraceabilityLink


class TraceabilityService:
    """Service for managing traceability matrices and links."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_matrices(self) -> list[TraceabilityMatrix]:
        result = await self.db.execute(select(TraceabilityMatrix))
        return list(result.scalars().all())

    async def get_matrix(self, matrix_id: UUID) -> Optional[TraceabilityMatrix]:
        result = await self.db.execute(select(TraceabilityMatrix).where(TraceabilityMatrix.id == matrix_id))
        return result.scalar_one_or_none()

    async def create_matrix(self, **kwargs) -> TraceabilityMatrix:
        matrix = TraceabilityMatrix(**kwargs)
        self.db.add(matrix)
        await self.db.flush()
        return matrix

    async def list_links(self, matrix_id: Optional[UUID] = None) -> list[TraceabilityLink]:
        stmt = select(TraceabilityLink)
        if matrix_id:
            stmt = stmt.where(TraceabilityLink.matrix_id == matrix_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add_link(self, **kwargs) -> TraceabilityLink:
        link = TraceabilityLink(**kwargs)
        self.db.add(link)
        await self.db.flush()
        return link
