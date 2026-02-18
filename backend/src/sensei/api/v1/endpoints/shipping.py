"""
Shipping & WMS (Pick List) API Endpoints.

Provides CRUD endpoints for shipments, shipment lines, pick lists, and pick list lines.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api import deps
from sensei.api.deps import DBSession, CurrentUser, RoleChecker
from sensei.api.utils import build_response, build_paginated_response, APIResponse
from sensei.models.accounts_receivable import Shipment, ShipmentLine
from sensei.models.inventory import PickList, PickListLine


# ──────────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────────

shipping_router = APIRouter(
    prefix="/shipping",
    tags=["Shipping"],
    dependencies=[Depends(RoleChecker([
        "warehouse", "ops", "logistics", "supply_chain",
        "purchasing", "gm", "supervisor",
    ]))],
)

wms_router = APIRouter(
    prefix="/wms",
    tags=["WMS"],
    dependencies=[Depends(RoleChecker([
        "warehouse", "ops", "logistics", "supply_chain",
        "purchasing", "gm", "supervisor",
    ]))],
)


# ──────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────

class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    shipment_number: str
    sales_order_id: Optional[UUID] = None
    account_id: UUID
    ship_from_warehouse_id: Optional[UUID] = None
    ship_date: Optional[datetime] = None
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    service_level: Optional[str] = None
    ship_to_name: str
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    ship_to_postal: Optional[str] = None
    ship_to_country: Optional[str] = None
    weight: Optional[Decimal] = None
    weight_uom: Optional[str] = None
    status: Optional[str] = "pending"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ShipmentLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    shipment_id: UUID
    sales_order_line_id: Optional[UUID] = None
    sku: str
    description: Optional[str] = None
    quantity_shipped: Decimal
    uom: Optional[str] = "EA"
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ShipmentCreateRequest(BaseModel):
    sales_order_id: Optional[UUID] = None
    account_id: UUID
    ship_from_warehouse_id: Optional[UUID] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    service_level: Optional[str] = None
    ship_date: Optional[datetime] = None
    ship_to_name: str
    ship_to_address: str
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    ship_to_postal: Optional[str] = None
    ship_to_country: Optional[str] = "Tunisia"
    notes: Optional[str] = None


class ShipmentUpdateRequest(BaseModel):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    service_level: Optional[str] = None
    ship_date: Optional[datetime] = None
    expected_delivery: Optional[datetime] = None
    ship_to_name: Optional[str] = None
    ship_to_address: Optional[str] = None
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    ship_to_postal: Optional[str] = None
    ship_to_country: Optional[str] = None
    weight: Optional[Decimal] = None
    weight_uom: Optional[str] = None
    notes: Optional[str] = None


class ShipmentLineCreateRequest(BaseModel):
    sales_order_line_id: Optional[UUID] = None
    sku: str
    description: Optional[str] = None
    quantity_shipped: Decimal
    uom: Optional[str] = "EA"
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str


class ShippingStatsResponse(BaseModel):
    pending_shipments: int = 0
    in_transit: int = 0
    delivered_today: int = 0
    pending_picks: int = 0
    picks_in_progress: int = 0
    completed_picks: int = 0


class PickListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    pick_number: str
    warehouse_id: UUID
    source_type: str
    source_id: UUID
    assigned_to_id: Optional[UUID] = None
    device_id: Optional[UUID] = None
    priority: int = 50
    pick_strategy: Optional[str] = "FIFO"
    status: Optional[str] = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PickListLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    pick_list_id: UUID
    sku: str
    description: Optional[str] = None
    quantity_requested: Decimal
    quantity_picked: Optional[Decimal] = Decimal(0)
    uom: Optional[str] = "EA"
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = "pending"
    picked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PickListCreateRequest(BaseModel):
    warehouse_id: UUID
    source_type: str
    source_id: UUID
    assigned_to_id: Optional[UUID] = None
    priority: int = 50
    pick_strategy: Optional[str] = "FIFO"
    notes: Optional[str] = None


class PickListUpdateRequest(BaseModel):
    assigned_to_id: Optional[UUID] = None
    priority: Optional[int] = None
    pick_strategy: Optional[str] = None
    notes: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────
# Shipping Endpoints
# ──────────────────────────────────────────────────────────────────────

@shipping_router.get("/shipments", response_model=APIResponse)
async def list_shipments(
    db: DBSession,
    current_user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    account_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """List shipments with optional filtering."""
    query = select(Shipment).order_by(Shipment.created_at.desc())
    if status_filter:
        query = query.where(Shipment.status == status_filter)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    shipments = result.scalars().all()
    return build_response(
        data={"items": [ShipmentResponse.model_validate(s).model_dump() for s in shipments]},
    )


@shipping_router.get("/shipments/{shipment_id}", response_model=APIResponse)
async def get_shipment(
    shipment_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Get a single shipment by ID."""
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return build_response(data=ShipmentResponse.model_validate(shipment).model_dump())


@shipping_router.post("/shipments", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    payload: ShipmentCreateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Create a new shipment."""
    shipment = Shipment(
        sales_order_id=payload.sales_order_id,
        account_id=payload.account_id,
        ship_from_warehouse_id=payload.ship_from_warehouse_id,
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
        service_level=payload.service_level,
        ship_date=payload.ship_date,
        ship_to_name=payload.ship_to_name,
        ship_to_address=payload.ship_to_address,
        ship_to_city=payload.ship_to_city,
        ship_to_state=payload.ship_to_state,
        ship_to_postal=payload.ship_to_postal,
        ship_to_country=payload.ship_to_country,
        notes=payload.notes,
        status="pending",
    )
    db.add(shipment)
    await db.commit()
    await db.refresh(shipment)
    return build_response(data=ShipmentResponse.model_validate(shipment).model_dump())


@shipping_router.patch("/shipments/{shipment_id}", response_model=APIResponse)
async def update_shipment(
    shipment_id: UUID,
    payload: ShipmentUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Update a shipment."""
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shipment, field, value)
    await db.commit()
    await db.refresh(shipment)
    return build_response(data=ShipmentResponse.model_validate(shipment).model_dump())


@shipping_router.post("/shipments/{shipment_id}/status", response_model=APIResponse)
async def update_shipment_status(
    shipment_id: UUID,
    payload: StatusUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Update shipment status."""
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment.status = payload.status
    if payload.status == "delivered":
        shipment.actual_delivery = datetime.now(timezone.utc)
    await db.commit()
    return build_response(data={"id": str(shipment_id), "status": payload.status})


@shipping_router.post("/shipments/{shipment_id}/lines", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_shipment_line(
    shipment_id: UUID,
    payload: ShipmentLineCreateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Add a line to a shipment."""
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")
    line = ShipmentLine(
        shipment_id=shipment_id,
        sales_order_line_id=payload.sales_order_line_id,
        sku=payload.sku,
        description=payload.description,
        quantity_shipped=payload.quantity_shipped,
        uom=payload.uom or "EA",
        lot_number=payload.lot_number,
        serial_number=payload.serial_number,
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return build_response(data=ShipmentLineResponse.model_validate(line).model_dump())


@shipping_router.get("/stats", response_model=ShippingStatsResponse)
async def get_shipping_stats(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Get shipping and pick list stats."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # Shipment counts
    pending_q = await db.execute(
        select(func.count()).select_from(Shipment).where(Shipment.status == "pending")
    )
    in_transit_q = await db.execute(
        select(func.count()).select_from(Shipment).where(Shipment.status == "in_transit")
    )
    delivered_q = await db.execute(
        select(func.count()).select_from(Shipment).where(
            and_(Shipment.status == "delivered", Shipment.actual_delivery >= today)
        )
    )

    # Pick list counts
    pick_pending_q = await db.execute(
        select(func.count()).select_from(PickList).where(PickList.status == "pending")
    )
    pick_progress_q = await db.execute(
        select(func.count()).select_from(PickList).where(PickList.status == "in_progress")
    )
    pick_complete_q = await db.execute(
        select(func.count()).select_from(PickList).where(PickList.status == "completed")
    )

    return ShippingStatsResponse(
        pending_shipments=pending_q.scalar() or 0,
        in_transit=in_transit_q.scalar() or 0,
        delivered_today=delivered_q.scalar() or 0,
        pending_picks=pick_pending_q.scalar() or 0,
        picks_in_progress=pick_progress_q.scalar() or 0,
        completed_picks=pick_complete_q.scalar() or 0,
    )


# ──────────────────────────────────────────────────────────────────────
# WMS / Pick List Endpoints
# ──────────────────────────────────────────────────────────────────────

@wms_router.get("/pick-lists", response_model=APIResponse)
async def list_pick_lists(
    db: DBSession,
    current_user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    warehouse_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """List pick lists with optional filtering."""
    query = select(PickList).order_by(PickList.created_at.desc())
    if status_filter:
        query = query.where(PickList.status == status_filter)
    if warehouse_id:
        query = query.where(PickList.warehouse_id == warehouse_id)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    pick_lists = result.scalars().all()
    return build_response(
        data={"items": [PickListResponse.model_validate(p).model_dump() for p in pick_lists]},
    )


@wms_router.get("/pick-lists/{pick_list_id}", response_model=APIResponse)
async def get_pick_list(
    pick_list_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Get a single pick list by ID."""
    result = await db.execute(select(PickList).where(PickList.id == pick_list_id))
    pick_list = result.scalar_one_or_none()
    if not pick_list:
        raise HTTPException(status_code=404, detail="Pick list not found")
    return build_response(data=PickListResponse.model_validate(pick_list).model_dump())


@wms_router.post("/pick-lists", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_pick_list(
    payload: PickListCreateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Create a new pick list."""
    pick_list = PickList(
        warehouse_id=payload.warehouse_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        assigned_to_id=payload.assigned_to_id,
        priority=payload.priority,
        pick_strategy=payload.pick_strategy,
        notes=payload.notes,
        status="pending",
    )
    db.add(pick_list)
    await db.commit()
    await db.refresh(pick_list)
    return build_response(data=PickListResponse.model_validate(pick_list).model_dump())


@wms_router.patch("/pick-lists/{pick_list_id}", response_model=APIResponse)
async def update_pick_list(
    pick_list_id: UUID,
    payload: PickListUpdateRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Update a pick list."""
    result = await db.execute(select(PickList).where(PickList.id == pick_list_id))
    pick_list = result.scalar_one_or_none()
    if not pick_list:
        raise HTTPException(status_code=404, detail="Pick list not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pick_list, field, value)
    await db.commit()
    await db.refresh(pick_list)
    return build_response(data=PickListResponse.model_validate(pick_list).model_dump())


@wms_router.post("/pick-lists/{pick_list_id}/start", response_model=APIResponse)
async def start_picking(
    pick_list_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Start picking on a pick list."""
    result = await db.execute(select(PickList).where(PickList.id == pick_list_id))
    pick_list = result.scalar_one_or_none()
    if not pick_list:
        raise HTTPException(status_code=404, detail="Pick list not found")
    pick_list.status = "in_progress"
    pick_list.started_at = datetime.now(timezone.utc)
    await db.commit()
    return build_response(data={"id": str(pick_list_id), "status": "in_progress"})


@wms_router.post("/pick-lists/{pick_list_id}/complete", response_model=APIResponse)
async def complete_picking(
    pick_list_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """Complete picking on a pick list."""
    result = await db.execute(select(PickList).where(PickList.id == pick_list_id))
    pick_list = result.scalar_one_or_none()
    if not pick_list:
        raise HTTPException(status_code=404, detail="Pick list not found")
    pick_list.status = "completed"
    pick_list.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return build_response(data={"id": str(pick_list_id), "status": "completed"})


@wms_router.patch("/pick-lists/{pick_list_id}/lines/{line_id}", response_model=APIResponse)
async def update_pick_line(
    pick_list_id: UUID,
    line_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    quantity_picked: Decimal = Query(...),
) -> Any:
    """Update the picked quantity on a pick list line."""
    result = await db.execute(
        select(PickListLine).where(
            and_(PickListLine.id == line_id, PickListLine.pick_list_id == pick_list_id)
        )
    )
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Pick list line not found")
    line.quantity_picked = quantity_picked
    await db.commit()
    await db.refresh(line)
    return build_response(data=PickListLineResponse.model_validate(line).model_dump())
