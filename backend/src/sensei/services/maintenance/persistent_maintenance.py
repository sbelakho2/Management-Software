from __future__ import annotations
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from sensei.models.maintenance import Asset, PMSchedule, MaintenanceWorkOrder, SparePart, DowntimeEvent
from sensei.models.user import User

class PersistentMaintenanceService:
    """Persistent Maintenance & Asset Reliability service using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_assets(self) -> List[Asset]:
        result = await self.db.execute(select(Asset))
        return list(result.scalars().all())

    async def create_asset(self, **kwargs) -> Asset:
        asset = Asset(**kwargs)
        self.db.add(asset)
        await self.db.flush()
        return asset

    async def get_asset(self, asset_id: UUID) -> Optional[Asset]:
        result = await self.db.execute(select(Asset).where(Asset.id == asset_id))
        return result.scalar_one_or_none()

    async def create_work_order(self, **kwargs) -> MaintenanceWorkOrder:
        wo = MaintenanceWorkOrder(**kwargs)
        self.db.add(wo)
        await self.db.flush()
        return wo

    async def list_pm_schedules(self) -> List[PMSchedule]:
        result = await self.db.execute(select(PMSchedule))
        return list(result.scalars().all())

    async def get_pm_route(self, days_ahead: int = 7) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days_ahead)

        result = await self.db.execute(
            select(PMSchedule).where(
                PMSchedule.is_active.is_(True),
                PMSchedule.next_due.is_not(None),
                PMSchedule.next_due <= horizon,
            )
        )
        schedules = list(result.scalars().all())

        # Simple heuristic: sort by location/work center then due date
        def sort_key(item: PMSchedule) -> tuple[str, datetime]:
            return (str(item.asset_id), item.next_due or now)

        schedules.sort(key=sort_key)

        return [
            {
                "pm_id": str(s.id),
                "asset_id": str(s.asset_id),
                "name": s.name,
                "frequency": f"{s.frequency_value} {s.frequency_unit}",
                "next_due": s.next_due.isoformat() if s.next_due else None,
            }
            for s in schedules
        ]

    async def list_work_orders(self) -> List[MaintenanceWorkOrder]:
        result = await self.db.execute(select(MaintenanceWorkOrder).options(selectinload(MaintenanceWorkOrder.asset)))
        return list(result.scalars().all())

    async def get_work_order(self, wo_id: UUID) -> Optional[MaintenanceWorkOrder]:
        result = await self.db.execute(select(MaintenanceWorkOrder).where(MaintenanceWorkOrder.id == wo_id))
        return result.scalar_one_or_none()

    async def request_work_order_approval(self, wo_id: UUID, requested_by_id: UUID) -> Optional[MaintenanceWorkOrder]:
        wo = await self.get_work_order(wo_id)
        if not wo:
            return None
        wo.approval_status = "pending"
        wo.approval_requested_at = datetime.now(timezone.utc)
        wo.updated_by_id = requested_by_id
        return wo

    async def approve_work_order(self, wo_id: UUID, approved_by_id: UUID, notes: Optional[str] = None) -> Optional[MaintenanceWorkOrder]:
        wo = await self.get_work_order(wo_id)
        if not wo:
            return None
        wo.approval_status = "approved"
        wo.approved_by_id = approved_by_id
        wo.approved_at = datetime.now(timezone.utc)
        wo.approval_notes = notes
        wo.updated_by_id = approved_by_id
        return wo

    async def reject_work_order(self, wo_id: UUID, rejected_by_id: UUID, notes: Optional[str] = None) -> Optional[MaintenanceWorkOrder]:
        wo = await self.get_work_order(wo_id)
        if not wo:
            return None
        wo.approval_status = "rejected"
        wo.approved_by_id = rejected_by_id
        wo.approved_at = datetime.now(timezone.utc)
        wo.approval_notes = notes
        wo.updated_by_id = rejected_by_id
        return wo

    async def get_statistics(self) -> dict[str, Any]:
        total_assets = await self.db.scalar(select(func.count(Asset.id)))
        down_assets = await self.db.scalar(select(func.count(Asset.id)).where(Asset.status == "down"))
        total_wo = await self.db.scalar(select(func.count(MaintenanceWorkOrder.id)))
        
        # Calculate overdue PMs: active schedules with next_due in the past
        now = datetime.now(timezone.utc)
        overdue_pms = await self.db.scalar(
            select(func.count(PMSchedule.id)).where(
                PMSchedule.is_active.is_(True),
                PMSchedule.next_due.is_not(None),
                PMSchedule.next_due < now,
            )
        )
        
        return {
            "total_assets": total_assets or 0,
            "assets_by_status": {
                "down": down_assets or 0,
                "operational": (total_assets or 0) - (down_assets or 0)
            },
            "total_work_orders": total_wo or 0,
            "overdue_pms": overdue_pms or 0
        }

    async def list_overdue_pms(self) -> List[PMSchedule]:
        """List all overdue preventive maintenance schedules."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(PMSchedule).where(
                PMSchedule.is_active.is_(True),
                PMSchedule.next_due.is_not(None),
                PMSchedule.next_due < now,
            ).order_by(PMSchedule.next_due)
        )
        return list(result.scalars().all())
