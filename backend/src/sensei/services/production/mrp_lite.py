"""MRP-lite Service (Development Plan 22.7).

Implements Material Requirements Planning (MRP) in a lightweight form:
- Net requirements calculation from BOM + demand + inventory.
- Suggested buys (purchase requisitions) and builds (work orders).
- Approval workflow for generated suggestions.

This module is in-memory and pure-Python to match other services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.core.config import settings
from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class RequirementType(str, Enum):
    BUY = "buy"
    BUILD = "build"


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RELEASED = "released"
    CANCELLED = "cancelled"


class DemandType(str, Enum):
    SALES_ORDER = "sales_order"
    FORECAST = "forecast"
    SAFETY_STOCK = "safety_stock"
    WORK_ORDER = "work_order"


# RBAC
_MRP_WRITE_ROLES: set[str] = {"admin", "ops", "planner", "ceo", "gm"}
_MRP_READ_ROLES: set[str] = {"admin", "ops", "planner", "ceo", "gm", "finance", "purchasing", "auditor"}
_MRP_APPROVE_ROLES: set[str] = {"admin", "ops", "planner", "ceo", "gm", "purchasing"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BOMComponent:
    """Bill of Materials component."""

    parent_item_id: str
    component_item_id: str
    quantity_per: Decimal
    scrap_factor: Decimal = Decimal("0")  # Percent scrap (0.05 = 5%)
    lead_time_days: int = 0


@dataclass(frozen=True)
class InventoryLevel:
    """Current inventory level for an item."""

    item_id: str
    on_hand: Decimal
    on_order: Decimal  # PO qty not yet received
    reserved: Decimal  # Allocated to existing orders
    safety_stock: Decimal = Decimal("0")


@dataclass(frozen=True)
class DemandEntry:
    """A demand entry for MRP calculation."""

    id: UUID
    item_id: str
    quantity: Decimal
    required_date: date
    demand_type: DemandType
    source_id: str = ""  # e.g., sales order ID, work order ID


@dataclass(frozen=True)
class MRPSuggestion:
    """A suggested buy or build action from MRP."""

    id: UUID
    item_id: str
    requirement_type: RequirementType
    quantity: Decimal
    needed_date: date
    status: SuggestionStatus
    source_demands: tuple[str, ...] = ()  # Demand IDs that drove this
    lead_time_days: int = 0
    notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    created_by: str = ""
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class MRPRunResult:
    """Result of an MRP run."""

    run_id: UUID
    run_at: datetime
    planning_horizon_days: int
    suggestions: tuple[MRPSuggestion, ...]
    shortage_items: tuple[str, ...]


class MRPService(PersistentServiceMixin):
    """In-memory MRP-lite service."""

    SERVICE_NAME = "mrp_lite"
    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")

    def __init__(self) -> None:
        # Master data
        self._bom: dict[str, list[BOMComponent]] = {}  # parent_item_id -> components
        self._inventory: dict[str, InventoryLevel] = {}  # item_id -> level
        self._lead_times: dict[str, int] = {}  # item_id -> lead time in days
        self._item_types: dict[str, RequirementType] = {}  # item_id -> buy or build

        # Transactional data
        self._demands: dict[UUID, DemandEntry] = {}
        self._suggestions: dict[UUID, MRPSuggestion] = {}
        self._runs: list[MRPRunResult] = []
        self._audit: list[AuditEvent] = []
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        bom_data = await self.load_state(self._DEFAULT_TENANT_ID, "bom") or {}
        inventory_data = await self.load_state(self._DEFAULT_TENANT_ID, "inventory") or {}
        lead_times_data = await self.load_state(self._DEFAULT_TENANT_ID, "lead_times") or {}
        item_types_data = await self.load_state(self._DEFAULT_TENANT_ID, "item_types") or {}
        demands_data = await self.load_state(self._DEFAULT_TENANT_ID, "demands") or {}
        suggestions_data = await self.load_state(self._DEFAULT_TENANT_ID, "suggestions") or {}
        runs_data = await self.load_state(self._DEFAULT_TENANT_ID, "runs") or []
        audit_data = await self.load_state(self._DEFAULT_TENANT_ID, "audit") or []

        self._bom = {
            parent_id: [decode_dataclass(comp, BOMComponent) for comp in comps]
            for parent_id, comps in bom_data.items()
        }
        self._inventory = {
            item_id: decode_dataclass(level, InventoryLevel)
            for item_id, level in inventory_data.items()
        }
        self._lead_times = {item_id: int(days) for item_id, days in lead_times_data.items()}
        self._item_types = {
            item_id: RequirementType(value) for item_id, value in item_types_data.items()
        }
        self._demands = {
            UUID(demand_id): decode_dataclass(entry, DemandEntry)
            for demand_id, entry in demands_data.items()
        }
        self._suggestions = {
            UUID(suggestion_id): decode_dataclass(entry, MRPSuggestion)
            for suggestion_id, entry in suggestions_data.items()
        }
        self._runs = [decode_dataclass(run, MRPRunResult) for run in runs_data]
        self._audit = [decode_dataclass(ev, AuditEvent) for ev in audit_data]
        self._state_loaded = True

    async def persist_all(self) -> None:
        bom_data = {
            parent_id: [encode_dataclass(comp) for comp in comps]
            for parent_id, comps in self._bom.items()
        }
        inventory_data = {
            item_id: encode_dataclass(level) for item_id, level in self._inventory.items()
        }
        lead_times_data = dict(self._lead_times)
        item_types_data = {item_id: item_type.value for item_id, item_type in self._item_types.items()}
        demands_data = {
            str(demand_id): encode_dataclass(entry) for demand_id, entry in self._demands.items()
        }
        suggestions_data = {
            str(suggestion_id): encode_dataclass(entry)
            for suggestion_id, entry in self._suggestions.items()
        }
        runs_data = [encode_dataclass(run) for run in self._runs]
        audit_data = [encode_dataclass(ev) for ev in self._audit]

        await self.save_state(self._DEFAULT_TENANT_ID, "bom", bom_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "inventory", inventory_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "lead_times", lead_times_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "item_types", item_types_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "demands", demands_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "suggestions", suggestions_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "runs", runs_data)
        await self.save_state(self._DEFAULT_TENANT_ID, "audit", audit_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ev = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(ev)

    # ----------------------------------------------------------------
    # Audit API
    # ----------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_READ_ROLES, "MRP read role required")
        return list(self._audit)

    async def list_audit_events_async(self, **kwargs: Any) -> list[AuditEvent]:
        await self._ensure_loaded()
        return self.list_audit_events(**kwargs)

    # ----------------------------------------------------------------
    # Master Data Management
    # ----------------------------------------------------------------

    def register_bom(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        parent_item_id: str,
        components: list[tuple[str, Decimal, Decimal]],  # (component_id, qty_per, scrap_factor)
    ) -> list[BOMComponent]:
        """Register or replace BOM for a parent item."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_WRITE_ROLES, "MRP write role required")

        if not parent_item_id or not parent_item_id.strip():
            raise ValueError("parent_item_id required")

        bom_components = []
        for comp_id, qty_per, scrap in components:
            if qty_per <= 0:
                raise ValueError(f"quantity_per must be positive for {comp_id}")
            bom_components.append(BOMComponent(
                parent_item_id=parent_item_id.strip(),
                component_item_id=comp_id.strip(),
                quantity_per=qty_per,
                scrap_factor=scrap,
            ))

        self._bom[parent_item_id.strip()] = bom_components

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.bom.register",
            entity_type="bom",
            entity_id=parent_item_id,
            correlation_id=correlation_id,
            metadata={"component_count": len(components)},
        )

        return bom_components

    async def register_bom_async(self, **kwargs: Any) -> list[BOMComponent]:
        await self._ensure_loaded()
        result = self.register_bom(**kwargs)
        await self.persist_all()
        return result

    async def run_mrp_async(self, **kwargs: Any) -> MRPRunResult:
        await self._ensure_loaded()
        result = self.run_mrp(**kwargs)
        await self.persist_all()
        return result

    def set_inventory_level(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: str,
        on_hand: Decimal,
        on_order: Decimal = Decimal("0"),
        reserved: Decimal = Decimal("0"),
        safety_stock: Decimal = Decimal("0"),
    ) -> InventoryLevel:
        """Set current inventory level for an item."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_WRITE_ROLES, "MRP write role required")

        if not item_id or not item_id.strip():
            raise ValueError("item_id required")

        level = InventoryLevel(
            item_id=item_id.strip(),
            on_hand=on_hand,
            on_order=on_order,
            reserved=reserved,
            safety_stock=safety_stock,
        )
        self._inventory[item_id.strip()] = level

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.inventory.set",
            entity_type="inventory",
            entity_id=item_id,
            correlation_id=correlation_id,
        )

        return level

    async def set_inventory_level_async(self, **kwargs: Any) -> InventoryLevel:
        await self._ensure_loaded()
        level = self.set_inventory_level(**kwargs)
        await self.persist_all()
        return level

    def set_item_type(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: str,
        requirement_type: RequirementType,
        lead_time_days: int = 0,
    ) -> None:
        """Set whether an item is a buy or build item."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_WRITE_ROLES, "MRP write role required")

        if not item_id or not item_id.strip():
            raise ValueError("item_id required")
        if lead_time_days < 0:
            raise ValueError("lead_time_days must be non-negative")

        self._item_types[item_id.strip()] = requirement_type
        self._lead_times[item_id.strip()] = lead_time_days

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.item_type.set",
            entity_type="item",
            entity_id=item_id,
            correlation_id=correlation_id,
            metadata={"type": requirement_type.value, "lead_time": lead_time_days},
        )

    async def set_item_type_async(self, **kwargs: Any) -> None:
        await self._ensure_loaded()
        self.set_item_type(**kwargs)
        await self.persist_all()

    # ----------------------------------------------------------------
    # Demand Management
    # ----------------------------------------------------------------

    def add_demand(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        item_id: str,
        quantity: Decimal,
        required_date: date,
        demand_type: DemandType,
        source_id: str = "",
    ) -> DemandEntry:
        """Add a demand entry."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_WRITE_ROLES, "MRP write role required")

        if not item_id or not item_id.strip():
            raise ValueError("item_id required")
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        demand = DemandEntry(
            id=uuid4(),
            item_id=item_id.strip(),
            quantity=quantity,
            required_date=required_date,
            demand_type=demand_type,
            source_id=source_id,
        )
        self._demands[demand.id] = demand

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.demand.add",
            entity_type="demand",
            entity_id=str(demand.id),
            correlation_id=correlation_id,
            metadata={"item_id": item_id, "quantity": str(quantity)},
        )

        return demand

    async def add_demand_async(self, **kwargs: Any) -> DemandEntry:
        await self._ensure_loaded()
        demand = self.add_demand(**kwargs)
        await self.persist_all()
        return demand

    def remove_demand(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        demand_id: UUID,
    ) -> None:
        """Remove a demand entry."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_WRITE_ROLES, "MRP write role required")

        if demand_id not in self._demands:
            raise ValueError("demand_id not found")

        del self._demands[demand_id]

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.demand.remove",
            entity_type="demand",
            entity_id=str(demand_id),
            correlation_id=correlation_id,
        )

    async def remove_demand_async(self, **kwargs: Any) -> None:
        await self._ensure_loaded()
        self.remove_demand(**kwargs)
        await self.persist_all()

    def list_demands(
        self,
        *,
        actor_roles: Iterable[str],
        item_id: str | None = None,
    ) -> list[DemandEntry]:
        """List demand entries."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_READ_ROLES, "MRP read role required")

        result = []
        for d in self._demands.values():
            if item_id and d.item_id != item_id:
                continue
            result.append(d)

        return sorted(result, key=lambda d: d.required_date)

    async def list_demands_async(self, **kwargs: Any) -> list[DemandEntry]:
        await self._ensure_loaded()
        return self.list_demands(**kwargs)

    # ----------------------------------------------------------------
    # MRP Calculation
    # ----------------------------------------------------------------

    def run_mrp(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        planning_horizon_days: int = settings.MRP_PLANNING_HORIZON_DAYS,
        as_of_date: date | None = None,
    ) -> MRPRunResult:
        """Run MRP calculation and generate suggestions."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_WRITE_ROLES, "MRP write role required")

        if planning_horizon_days < 1:
            raise ValueError("planning_horizon_days must be >= 1")

        run_date = as_of_date or date.today()
        horizon_end = run_date + timedelta(days=planning_horizon_days)

        # Collect demands within horizon
        demands_in_scope = [
            d for d in self._demands.values()
            if d.required_date <= horizon_end
        ]

        # Group demands by item
        item_demands: dict[str, list[DemandEntry]] = {}
        for d in demands_in_scope:
            item_demands.setdefault(d.item_id, []).append(d)

        suggestions: list[MRPSuggestion] = []
        shortage_items: list[str] = []

        # Process each item with demands
        for item_id, demands in item_demands.items():
            total_demand = sum(d.quantity for d in demands)

            # Get inventory
            inv = self._inventory.get(item_id)
            available = Decimal("0")
            if inv:
                available = inv.on_hand + inv.on_order - inv.reserved - inv.safety_stock

            # Calculate net requirement
            net_requirement = total_demand - available

            if net_requirement > 0:
                shortage_items.append(item_id)

                # Determine if buy or build
                req_type = self._item_types.get(item_id, RequirementType.BUY)
                lead_time = self._lead_times.get(item_id, 0)

                # Find earliest need date
                earliest_need = min(d.required_date for d in demands)

                # Create suggestion
                suggestion = MRPSuggestion(
                    id=uuid4(),
                    item_id=item_id,
                    requirement_type=req_type,
                    quantity=net_requirement,
                    needed_date=earliest_need,
                    status=SuggestionStatus.PENDING,
                    source_demands=tuple(str(d.id) for d in demands),
                    lead_time_days=lead_time,
                    created_at=_utcnow(),
                    created_by=actor_id,
                )
                suggestions.append(suggestion)
                self._suggestions[suggestion.id] = suggestion

        # Explode BOM for build items
        additional_suggestions = self._explode_bom(
            actor_id=actor_id,
            suggestions=suggestions,
            run_date=run_date,
        )
        for s in additional_suggestions:
            suggestions.append(s)
            self._suggestions[s.id] = s
            if s.item_id not in shortage_items:
                shortage_items.append(s.item_id)

        result = MRPRunResult(
            run_id=uuid4(),
            run_at=_utcnow(),
            planning_horizon_days=planning_horizon_days,
            suggestions=tuple(suggestions),
            shortage_items=tuple(sorted(set(shortage_items))),
        )
        self._runs.append(result)

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.run",
            entity_type="mrp_run",
            entity_id=str(result.run_id),
            correlation_id=correlation_id,
            metadata={
                "horizon_days": planning_horizon_days,
                "suggestions_count": len(suggestions),
                "shortage_count": len(shortage_items),
            },
        )

        return result

    def _explode_bom(
        self,
        *,
        actor_id: str,
        suggestions: list[MRPSuggestion],
        run_date: date,
    ) -> list[MRPSuggestion]:
        """Explode BOM for build suggestions to create component requirements."""
        additional: list[MRPSuggestion] = []

        for suggestion in suggestions:
            if suggestion.requirement_type != RequirementType.BUILD:
                continue

            components = self._bom.get(suggestion.item_id, [])
            for comp in components:
                # Calculate component requirement including scrap
                scrap_multiplier = Decimal("1") + comp.scrap_factor
                comp_qty = suggestion.quantity * comp.quantity_per * scrap_multiplier

                # Check component inventory
                inv = self._inventory.get(comp.component_item_id)
                available = Decimal("0")
                if inv:
                    available = inv.on_hand + inv.on_order - inv.reserved - inv.safety_stock

                net_req = comp_qty - available

                if net_req > 0:
                    comp_type = self._item_types.get(comp.component_item_id, RequirementType.BUY)
                    comp_lead = self._lead_times.get(comp.component_item_id, 0)

                    # Component needed before parent build starts
                    comp_needed = suggestion.needed_date

                    comp_suggestion = MRPSuggestion(
                        id=uuid4(),
                        item_id=comp.component_item_id,
                        requirement_type=comp_type,
                        quantity=net_req,
                        needed_date=comp_needed,
                        status=SuggestionStatus.PENDING,
                        source_demands=(str(suggestion.id),),  # Parent suggestion
                        lead_time_days=comp_lead,
                        notes=f"Component for {suggestion.item_id}",
                        created_at=_utcnow(),
                        created_by=actor_id,
                    )
                    additional.append(comp_suggestion)

        return additional

    # ----------------------------------------------------------------
    # Suggestion Approval
    # ----------------------------------------------------------------

    def list_suggestions(
        self,
        *,
        actor_roles: Iterable[str],
        status: SuggestionStatus | None = None,
        item_id: str | None = None,
    ) -> list[MRPSuggestion]:
        """List MRP suggestions."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_READ_ROLES, "MRP read role required")

        result = []
        for s in self._suggestions.values():
            if status and s.status != status:
                continue
            if item_id and s.item_id != item_id:
                continue
            result.append(s)

        return sorted(result, key=lambda s: s.needed_date)

    async def list_suggestions_async(self, **kwargs: Any) -> list[MRPSuggestion]:
        await self._ensure_loaded()
        return self.list_suggestions(**kwargs)

    def approve_suggestion(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        suggestion_id: UUID,
    ) -> MRPSuggestion:
        """Approve an MRP suggestion."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_APPROVE_ROLES, "MRP approve role required")

        suggestion = self._suggestions.get(suggestion_id)
        if not suggestion:
            raise ValueError("suggestion_id not found")
        if suggestion.status != SuggestionStatus.PENDING:
            raise ValueError("Only pending suggestions can be approved")

        # SoD check: creator cannot approve
        if suggestion.created_by == actor_id:
            raise PermissionError("Suggestion creator cannot approve their own suggestion")

        updated = MRPSuggestion(
            id=suggestion.id,
            item_id=suggestion.item_id,
            requirement_type=suggestion.requirement_type,
            quantity=suggestion.quantity,
            needed_date=suggestion.needed_date,
            status=SuggestionStatus.APPROVED,
            source_demands=suggestion.source_demands,
            lead_time_days=suggestion.lead_time_days,
            notes=suggestion.notes,
            created_at=suggestion.created_at,
            created_by=suggestion.created_by,
            approved_at=_utcnow(),
            approved_by=actor_id,
        )
        self._suggestions[suggestion.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.suggestion.approve",
            entity_type="suggestion",
            entity_id=str(suggestion_id),
            correlation_id=correlation_id,
        )

        return updated

    async def reject_suggestion_async(self, **kwargs: Any) -> MRPSuggestion:
        await self._ensure_loaded()
        suggestion = self.reject_suggestion(**kwargs)
        await self.persist_all()
        return suggestion

    async def approve_suggestion_async(self, **kwargs: Any) -> MRPSuggestion:
        await self._ensure_loaded()
        suggestion = self.approve_suggestion(**kwargs)
        await self.persist_all()
        return suggestion

    def reject_suggestion(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        suggestion_id: UUID,
        reason: str,
    ) -> MRPSuggestion:
        """Reject an MRP suggestion."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_APPROVE_ROLES, "MRP approve role required")

        suggestion = self._suggestions.get(suggestion_id)
        if not suggestion:
            raise ValueError("suggestion_id not found")
        if suggestion.status != SuggestionStatus.PENDING:
            raise ValueError("Only pending suggestions can be rejected")
        if not reason or not reason.strip():
            raise ValueError("rejection reason required")

        updated = MRPSuggestion(
            id=suggestion.id,
            item_id=suggestion.item_id,
            requirement_type=suggestion.requirement_type,
            quantity=suggestion.quantity,
            needed_date=suggestion.needed_date,
            status=SuggestionStatus.REJECTED,
            source_demands=suggestion.source_demands,
            lead_time_days=suggestion.lead_time_days,
            notes=suggestion.notes,
            created_at=suggestion.created_at,
            created_by=suggestion.created_by,
            rejection_reason=reason.strip(),
        )
        self._suggestions[suggestion.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.suggestion.reject",
            entity_type="suggestion",
            entity_id=str(suggestion_id),
            correlation_id=correlation_id,
            metadata={"reason": reason},
        )

        return updated

    async def release_suggestion_async(self, **kwargs: Any) -> MRPSuggestion:
        await self._ensure_loaded()
        suggestion = self.release_suggestion(**kwargs)
        await self.persist_all()
        return suggestion

    def release_suggestion(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        suggestion_id: UUID,
    ) -> MRPSuggestion:
        """Release an approved suggestion (creates PO/WO)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_APPROVE_ROLES, "MRP approve role required")

        suggestion = self._suggestions.get(suggestion_id)
        if not suggestion:
            raise ValueError("suggestion_id not found")
        if suggestion.status != SuggestionStatus.APPROVED:
            raise ValueError("Only approved suggestions can be released")

        updated = MRPSuggestion(
            id=suggestion.id,
            item_id=suggestion.item_id,
            requirement_type=suggestion.requirement_type,
            quantity=suggestion.quantity,
            needed_date=suggestion.needed_date,
            status=SuggestionStatus.RELEASED,
            source_demands=suggestion.source_demands,
            lead_time_days=suggestion.lead_time_days,
            notes=suggestion.notes,
            created_at=suggestion.created_at,
            created_by=suggestion.created_by,
            approved_at=suggestion.approved_at,
            approved_by=suggestion.approved_by,
        )
        self._suggestions[suggestion.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="mrp.suggestion.release",
            entity_type="suggestion",
            entity_id=str(suggestion_id),
            correlation_id=correlation_id,
            metadata={"type": suggestion.requirement_type.value},
        )

        return updated

    # ----------------------------------------------------------------
    # Reporting
    # ----------------------------------------------------------------

    def get_item_requirements(
        self,
        *,
        actor_roles: Iterable[str],
        item_id: str,
    ) -> dict[str, Any]:
        """Get net requirements summary for an item."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_READ_ROLES, "MRP read role required")

        demands = [d for d in self._demands.values() if d.item_id == item_id]
        total_demand = sum(d.quantity for d in demands)

        inv = self._inventory.get(item_id)
        on_hand = inv.on_hand if inv else Decimal("0")
        on_order = inv.on_order if inv else Decimal("0")
        reserved = inv.reserved if inv else Decimal("0")
        safety = inv.safety_stock if inv else Decimal("0")

        available = on_hand + on_order - reserved - safety
        net_requirement = max(Decimal("0"), total_demand - available)

        return {
            "item_id": item_id,
            "total_demand": total_demand,
            "on_hand": on_hand,
            "on_order": on_order,
            "reserved": reserved,
            "safety_stock": safety,
            "available": available,
            "net_requirement": net_requirement,
        }

    async def get_item_requirements_async(self, **kwargs: Any) -> dict[str, Any]:
        await self._ensure_loaded()
        return self.get_item_requirements(**kwargs)

    def list_runs(
        self,
        *,
        actor_roles: Iterable[str],
    ) -> list[MRPRunResult]:
        """List MRP run history."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _MRP_READ_ROLES, "MRP read role required")
        return list(self._runs)

    async def list_runs_async(self, **kwargs: Any) -> list[MRPRunResult]:
        await self._ensure_loaded()
        return self.list_runs(**kwargs)
