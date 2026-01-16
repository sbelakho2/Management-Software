from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sensei.models.maintenance import LOTOProcedure, LOTOEnergySource, LOTOLock


class LockoutTagoutService:
    """Persistent LOTO management service using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_procedures(self) -> list[LOTOProcedure]:
        result = await self.db.execute(
            select(LOTOProcedure).options(selectinload(LOTOProcedure.energy_sources))
        )
        return list(result.scalars().all())

    async def get_procedure(self, procedure_id: UUID) -> Optional[LOTOProcedure]:
        result = await self.db.execute(
            select(LOTOProcedure)
            .where(LOTOProcedure.id == procedure_id)
            .options(selectinload(LOTOProcedure.energy_sources))
        )
        return result.scalar_one_or_none()

    async def create_procedure(
        self,
        *,
        asset_id: UUID,
        title: str,
        description: Optional[str] = None,
        status: str = "active",
        requires_verification: bool = True,
        version: str = "v1",
        energy_sources: Optional[list[dict[str, Any]]] = None,
        created_by_id: Optional[UUID] = None,
    ) -> LOTOProcedure:
        procedure = LOTOProcedure(
            asset_id=asset_id,
            title=title,
            description=description,
            status=status,
            requires_verification=requires_verification,
            version=version,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
            owner_id=created_by_id,
        )
        self.db.add(procedure)
        await self.db.flush()

        for src in energy_sources or []:
            energy = LOTOEnergySource(
                procedure_id=procedure.id,
                source_type=src.get("source_type", "other"),
                isolation_point=src.get("isolation_point", ""),
                lock_required=bool(src.get("lock_required", True)),
                verification_steps=src.get("verification_steps"),
                notes=src.get("notes"),
            )
            self.db.add(energy)

        await self.db.flush()
        return procedure

    async def list_active_locks(self) -> list[LOTOLock]:
        result = await self.db.execute(
            select(LOTOLock).where(LOTOLock.status == "active")
        )
        return list(result.scalars().all())

    async def create_lock(
        self,
        *,
        procedure_id: UUID,
        asset_id: UUID,
        lock_number: str,
        applied_by_id: UUID,
        work_order_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        verification_required: bool = True,
    ) -> LOTOLock:
        lock = LOTOLock(
            procedure_id=procedure_id,
            asset_id=asset_id,
            work_order_id=work_order_id,
            lock_number=lock_number,
            status="active",
            reason=reason,
            applied_by_id=applied_by_id,
            applied_at=datetime.now(timezone.utc),
            verification_required=verification_required,
            created_by_id=applied_by_id,
            updated_by_id=applied_by_id,
            owner_id=applied_by_id,
        )
        self.db.add(lock)
        await self.db.flush()
        return lock

    async def release_lock(
        self,
        *,
        lock_id: UUID,
        released_by_id: UUID,
        verification_notes: Optional[str] = None,
    ) -> Optional[LOTOLock]:
        result = await self.db.execute(select(LOTOLock).where(LOTOLock.id == lock_id))
        lock = result.scalar_one_or_none()
        if not lock:
            return None

        lock.status = "released"
        lock.released_by_id = released_by_id
        lock.released_at = datetime.now(timezone.utc)
        lock.verification_notes = verification_notes
        lock.updated_by_id = released_by_id
        return lock

    async def verify_lock(
        self,
        *,
        lock_id: UUID,
        verified_by_id: UUID,
        verification_notes: Optional[str] = None,
    ) -> Optional[LOTOLock]:
        result = await self.db.execute(select(LOTOLock).where(LOTOLock.id == lock_id))
        lock = result.scalar_one_or_none()
        if not lock:
            return None

        lock.verified_by_id = verified_by_id
        lock.verified_at = datetime.now(timezone.utc)
        lock.verification_notes = verification_notes
        lock.updated_by_id = verified_by_id
        return lock
