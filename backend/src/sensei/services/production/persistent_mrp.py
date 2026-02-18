"""
Persistent MRP Service.

Database-backed Material Requirements Planning.
Persists BOMs, inventory records, demand forecasts,
supply orders, and MRP run results to PostgreSQL.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from sensei.models.mrp import BOMComponent, MRPDemand, MRPSuggestion, MRPRun
from sensei.models.product import Product
from sensei.models.inventory import InventoryLevel
from sensei.services.event_bus import event_bus
from sensei.services.domain_events import MRPRunCompleted


class PersistentMRPService:
    """Database-backed MRP service with real BOM explosion + net requirements."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_bom(self) -> List[BOMComponent]:
        result = await self.db.execute(select(BOMComponent).options(selectinload(BOMComponent.parent_product), selectinload(BOMComponent.component_product)))
        return list(result.scalars().all())

    async def add_bom_component(self, **kwargs) -> BOMComponent:
        comp = BOMComponent(**kwargs)
        self.db.add(comp)
        await self.db.flush()
        return comp

    async def list_demands(self) -> List[MRPDemand]:
        result = await self.db.execute(select(MRPDemand).options(selectinload(MRPDemand.product)))
        return list(result.scalars().all())

    async def list_suggestions(self) -> List[MRPSuggestion]:
        result = await self.db.execute(select(MRPSuggestion).options(selectinload(MRPSuggestion.product)))
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Core MRP logic
    # ------------------------------------------------------------------

    async def _get_on_hand(self, product_id: UUID) -> Decimal:
        """Sum all inventory levels for a product across all locations."""
        total = await self.db.scalar(
            select(func.coalesce(func.sum(InventoryLevel.quantity_on_hand), 0))
            .where(InventoryLevel.product_id == product_id)
        )
        return Decimal(str(total))

    async def _get_bom_children(self, parent_product_id: UUID) -> List[BOMComponent]:
        """Get direct BOM children for a product."""
        result = await self.db.execute(
            select(BOMComponent)
            .options(selectinload(BOMComponent.component_product))
            .where(BOMComponent.parent_product_id == parent_product_id)
        )
        return list(result.scalars().all())

    async def _has_bom(self, product_id: UUID) -> bool:
        """Check if a product has BOM children (i.e., it is manufactured)."""
        count = await self.db.scalar(
            select(func.count(BOMComponent.id))
            .where(BOMComponent.parent_product_id == product_id)
        )
        return (count or 0) > 0

    async def run_mrp(
        self,
        planning_horizon_days: int = 30,
        user_id: UUID | None = None,
    ) -> MRPRun:
        """
        Execute MRP calculation:

        1. Load all active demands within the planning horizon.
        2. For each demand, compute gross requirement.
        3. Subtract on-hand inventory => net requirement.
        4. If net > 0 and product has BOM children => requirement_type='build',
           then recursively explode BOM for component demands.
        5. If net > 0 and product has NO BOM => requirement_type='buy'.
        6. Persist MRPSuggestion rows and an MRPRun history record.
        """
        horizon_end = date.today() + timedelta(days=planning_horizon_days)

        # 1. Gather active demands within horizon
        result = await self.db.execute(
            select(MRPDemand)
            .where(and_(
                MRPDemand.is_active == True,  # noqa: E712
                MRPDemand.required_date <= horizon_end,
            ))
            .order_by(MRPDemand.required_date)
        )
        demands = list(result.scalars().all())

        # Aggregate demand by product
        demand_map: dict[UUID, list[MRPDemand]] = {}
        for d in demands:
            demand_map.setdefault(d.product_id, []).append(d)

        suggestions_created = 0
        shortages_detected = 0

        # Track products already processed to avoid duplicate suggestions within a single run
        processed: set[UUID] = set()

        async def _process_product(
            product_id: UUID,
            gross_qty: Decimal,
            needed_date: date,
            source_demand_ids: list[str],
            depth: int = 0,
        ) -> None:
            nonlocal suggestions_created, shortages_detected

            if depth > 20:
                return  # guard against circular BOMs

            on_hand = await self._get_on_hand(product_id)
            net_qty = gross_qty - on_hand
            if net_qty <= Decimal("0"):
                return  # on-hand covers requirement

            shortages_detected += 1
            has_bom = await self._has_bom(product_id)
            req_type = "build" if has_bom else "buy"

            # Get product lead time
            prod = await self.db.get(Product, product_id)
            lead_time = prod.lead_time_days if prod else 0

            suggestion = MRPSuggestion(
                product_id=product_id,
                requirement_type=req_type,
                quantity=net_qty,
                needed_date=needed_date,
                status="pending",
                lead_time_days=lead_time,
                source_demands=source_demand_ids,
                created_by_id=user_id,
                updated_by_id=user_id,
                owner_id=user_id,
            )
            self.db.add(suggestion)
            suggestions_created += 1

            # Explode BOM for manufactured items
            if has_bom:
                bom_children = await self._get_bom_children(product_id)
                for comp in bom_children:
                    comp_qty = net_qty * comp.quantity_per * (1 + comp.scrap_factor)
                    component_needed = needed_date - timedelta(days=comp.lead_time_days)
                    await _process_product(
                        comp.component_product_id,
                        comp_qty,
                        component_needed,
                        source_demand_ids,
                        depth + 1,
                    )

        # 2. Process each product's aggregated demand
        for product_id, product_demands in demand_map.items():
            total_qty = sum(d.quantity for d in product_demands)
            earliest_date = min(d.required_date for d in product_demands)
            source_ids = [d.source_id or str(d.id) for d in product_demands]

            await _process_product(
                product_id, total_qty, earliest_date, source_ids
            )

        await self.db.flush()

        # 3. Create MRP run history record
        run = MRPRun(
            run_at=datetime.now(timezone.utc),
            planning_horizon_days=planning_horizon_days,
            executed_by_id=user_id,
            suggestions_count=suggestions_created,
            shortages_count=shortages_detected,
        )
        self.db.add(run)
        await self.db.flush()

        # Publish domain event — feeds single data thread
        await event_bus.publish(MRPRunCompleted(
            run_id=str(run.id),
            planned_orders=suggestions_created,
            shortage_count=shortages_detected,
        ))

        return run
