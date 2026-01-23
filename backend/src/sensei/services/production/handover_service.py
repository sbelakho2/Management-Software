from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, List
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.production import ShiftHandoverNote, HandoverSeverity
from sensei.models.user import User


class HandoverService:
    """Service for managing digital shift handovers with database persistence."""

    async def create_handover_note(
        self,
        db: AsyncSession,
        *,
        station_id: int,
        created_by_id: UUID,
        work_order_id: Optional[int] = None,
        severity: HandoverSeverity = HandoverSeverity.INFO,
        safety: str = "",
        quality: str = "",
        delivery: str = "",
        cost: str = "",
        people: str = "",
        notes: str = "",
    ) -> ShiftHandoverNote:
        note = ShiftHandoverNote(
            station_id=station_id,
            created_by_id=created_by_id,
            work_order_id=work_order_id,
            severity=severity,
            safety=safety,
            quality=quality,
            delivery=delivery,
            cost=cost,
            people=people,
            notes=notes,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    async def list_handover_notes(
        self,
        db: AsyncSession,
        *,
        station_id: Optional[int] = None,
        include_acknowledged: bool = True,
        limit: int = 50,
    ) -> List[ShiftHandoverNote]:
        query = select(ShiftHandoverNote).order_by(desc(ShiftHandoverNote.created_at))

        if station_id is not None:
            query = query.where(ShiftHandoverNote.station_id == station_id)
        
        if not include_acknowledged:
            query = query.where(ShiftHandoverNote.acknowledged == False)

        query = query.limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def acknowledge_handover_note(
        self,
        db: AsyncSession,
        note_id: int,
        acknowledged_by_id: UUID,
    ) -> Optional[ShiftHandoverNote]:
        result = await db.execute(
            select(ShiftHandoverNote).where(ShiftHandoverNote.id == note_id)
        )
        note = result.scalar_one_or_none()
        
        if not note:
            return None
        
        note.acknowledged = True
        note.acknowledged_by_id = acknowledged_by_id
        note.acknowledged_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(note)
        return note

    async def get_active_handovers_for_stations(
        self,
        db: AsyncSession,
        station_ids: List[int],
    ) -> List[ShiftHandoverNote]:
        """Get unacknowledged handover notes for specific stations."""
        if not station_ids:
            return []
            
        result = await db.execute(
            select(ShiftHandoverNote)
            .where(ShiftHandoverNote.station_id.in_(station_ids))
            .where(ShiftHandoverNote.acknowledged == False)
            .order_by(desc(ShiftHandoverNote.created_at))
        )
        return list(result.scalars().all())


_service_instance: Optional[HandoverService] = None


def get_handover_service() -> HandoverService:
    global _service_instance
    if _service_instance is None:
        _service_instance = HandoverService()
    return _service_instance
