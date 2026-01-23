from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.production import GlobalPulse, HandoverSeverity


class PulseService:
    """Service for managing site-wide real-time announcements (The Sensei Pulse)."""

    async def create_pulse(
        self,
        db: AsyncSession,
        *,
        message: str,
        severity: HandoverSeverity = HandoverSeverity.INFO,
        expires_at: Optional[datetime] = None,
        highlight_metric_name: Optional[str] = None,
        highlight_metric_value: Optional[str] = None,
    ) -> GlobalPulse:
        # Deactivate previous active pulses of same severity or lower if needed? 
        # Actually, let's just allow multiple active pulses.
        
        pulse = GlobalPulse(
            message=message,
            severity=severity,
            expires_at=expires_at,
            highlight_metric_name=highlight_metric_name,
            highlight_metric_value=highlight_metric_value,
            is_active=True
        )
        db.add(pulse)
        await db.commit()
        await db.refresh(pulse)
        return pulse

    async def get_active_pulses(
        self,
        db: AsyncSession,
    ) -> List[GlobalPulse]:
        now = datetime.now(timezone.utc)
        query = select(GlobalPulse).where(
            and_(
                GlobalPulse.is_active.is_(True),
                (GlobalPulse.expires_at == None) | (GlobalPulse.expires_at > now)
            )
        ).order_by(desc(GlobalPulse.severity), desc(GlobalPulse.created_at))
        
        result = await db.execute(query)
        return list(result.scalars().all())

    async def deactivate_pulse(
        self,
        db: AsyncSession,
        pulse_id: int,
    ) -> Optional[GlobalPulse]:
        result = await db.execute(
            select(GlobalPulse).where(GlobalPulse.id == pulse_id)
        )
        pulse = result.scalar_one_or_none()
        
        if not pulse:
            return None
            
        pulse.is_active = False
        await db.commit()
        await db.refresh(pulse)
        return pulse


_service_instance: Optional[PulseService] = None


def get_pulse_service() -> PulseService:
    global _service_instance
    if _service_instance is None:
        _service_instance = PulseService()
    return _service_instance
