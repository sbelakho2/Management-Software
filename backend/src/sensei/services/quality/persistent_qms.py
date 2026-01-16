from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from sensei.models.quality_qms import QMSDocument, QualityAudit, AuditFinding, Gauge, CalibrationEvent, SCAR
from sensei.models.user import User

class PersistentQMSService:
    """Persistent Advanced Quality System (QMS) service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_documents(self) -> List[QMSDocument]:
        result = await self.db.execute(select(QMSDocument).options(selectinload(QMSDocument.current_revision)))
        return list(result.scalars().all())

    async def create_document(self, **kwargs) -> QMSDocument:
        doc = QMSDocument(**kwargs)
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def list_audits(self) -> List[QualityAudit]:
        result = await self.db.execute(select(QualityAudit).options(selectinload(QualityAudit.findings)))
        return list(result.scalars().all())

    async def list_gauges(self) -> List[Gauge]:
        result = await self.db.execute(select(Gauge))
        return list(result.scalars().all())

    async def get_qms_stats(self) -> dict[str, Any]:
        total_docs = await self.db.scalar(select(func.count(QMSDocument.id)))
        open_audits = await self.db.scalar(select(func.count(QualityAudit.id)).where(QualityAudit.status != "completed"))
        overdue_gauges = await self.db.scalar(select(func.count(Gauge.id)).where(Gauge.next_due_at < datetime.now(timezone.utc)))
        
        return {
            "total_documents": total_docs or 0,
            "open_audits": open_audits or 0,
            "overdue_calibrations": overdue_gauges or 0
        }
