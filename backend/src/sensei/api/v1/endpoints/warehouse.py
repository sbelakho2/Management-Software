"""
Warehouse/Inventory API Endpoints.

Provides endpoints for warehouse dashboard, inventory stats, stock movements, and low stock alerts.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.api.deps import DBSession, CurrentUser
from sensei.api.schemas import APIResponse
from sensei.api.utils import build_response
from sensei.core.database import get_db_session
from sensei.core.external_db import get_starz_erp_session
from sensei.models.inventory import Warehouse, Location, InventoryLevel, StockMove
from sensei.models.product import Product
from sensei.services.external.starz_ingestion import StarzErpIngestionService

router = APIRouter()
logger = logging.getLogger(__name__)

# =============================================================================
# Schemas
# =============================================================================

class WarehouseStatsResponse(BaseModel):
    total_items: int
    low_stock: int
    out_of_stock: int
    pending_receipts: int
    pending_shipments: int
    inventory_value: float


class StockMovementResponse(BaseModel):
    id: str
    type: str  # 'in' or 'out'
    item: str
    quantity: float
    location: str
    time: str


class LowStockItemResponse(BaseModel):
    id: str
    name: str
    current: float
    reorder: float
    unit: str


class WarehouseResponse(BaseModel):
    id: str
    name: str
    code: str
    address: Optional[str]
    location_count: int


class LocationResponse(BaseModel):
    id: str
    warehouse_id: str
    name: str
    location_type: str
    parent_id: Optional[str]


class InventoryLevelResponse(BaseModel):
    id: str
    product_id: int
    product_name: str
    location_id: str
    location_name: str
    quantity_on_hand: float
    quantity_reserved: float
    quantity_available: float


# =============================================================================
# Helper Functions
# =============================================================================

def format_time_ago(dt: datetime) -> str:
    """Convert datetime to human-readable 'X ago' format."""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} min ago"
    
    return "just now"


# =============================================================================
# Endpoints - Dashboard Stats
# =============================================================================

@router.get("/stats", response_model=WarehouseStatsResponse)
async def get_warehouse_stats(db: DBSession, current_user: CurrentUser) -> Any:
    """Get warehouse dashboard statistics."""
    # Total unique items (SKUs) in inventory
    total_items = await db.scalar(
        select(func.count(func.distinct(InventoryLevel.product_id)))
    ) or 0
    
    # Low stock items (where on_hand < 20% of typical reorder level, simplified)
    # In real scenario, you'd compare against product.reorder_point
    low_stock = await db.scalar(
        select(func.count(InventoryLevel.id)).where(
            and_(
                InventoryLevel.quantity_on_hand > 0,
                InventoryLevel.quantity_on_hand < 50  # Threshold
            )
        )
    ) or 0
    
    # Out of stock items
    out_of_stock = await db.scalar(
        select(func.count(InventoryLevel.id)).where(InventoryLevel.quantity_on_hand <= 0)
    ) or 0
    
    # Pending receipts (inbound moves not yet done)
    pending_receipts = await db.scalar(
        select(func.count(StockMove.id)).where(
            and_(
                StockMove.status.in_(['draft', 'waiting', 'confirmed']),
                # Source is external/supplier location
            )
        )
    ) or 0
    
    # Pending shipments (outbound moves not yet done)
    pending_shipments = await db.scalar(
        select(func.count(StockMove.id)).where(
            StockMove.status.in_(['draft', 'waiting', 'confirmed'])
        )
    ) or 0
    
    # Simple inventory value calculation (would normally use valuation layers)
    # For now, sum quantity * estimated unit cost
    inventory_value = await db.scalar(
        select(func.sum(InventoryLevel.quantity_on_hand * 100))  # Placeholder unit cost
    ) or 0.0
    
    return WarehouseStatsResponse(
        total_items=total_items,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        pending_receipts=pending_receipts,
        pending_shipments=pending_shipments,
        inventory_value=float(inventory_value)
    )


@router.get("/movements", response_model=List[StockMovementResponse])
async def get_recent_movements(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=100)
) -> Any:
    """Get recent stock movements."""
    result = await db.execute(
        select(StockMove, Product, Location)
        .join(Product, StockMove.product_id == Product.id)
        .join(Location, StockMove.destination_location_id == Location.id)
        .where(StockMove.status == 'done')
        .order_by(StockMove.created_at.desc())
        .limit(limit)
    )
    moves = result.all()
    
    movements = []
    for move, product, location in moves:
        # Determine if it's inbound or outbound based on location type
        move_type = 'in' if location.location_type in ['internal', 'inventory'] else 'out'
        movements.append(StockMovementResponse(
            id=str(move.id),
            type=move_type,
            item=product.name if product else 'Unknown',
            quantity=float(move.quantity),
            location=f"{location.name}" if location else 'Unknown',
            time=format_time_ago(move.created_at) if move.created_at else 'Unknown'
        ))
    
    return movements


@router.get("/low-stock", response_model=List[LowStockItemResponse])
async def get_low_stock_items(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=100)
) -> Any:
    """Get items with low stock levels."""
    result = await db.execute(
        select(InventoryLevel, Product)
        .join(Product, InventoryLevel.product_id == Product.id)
        .where(
            and_(
                InventoryLevel.quantity_on_hand > 0,
                InventoryLevel.quantity_on_hand < 50  # Simple threshold
            )
        )
        .order_by(InventoryLevel.quantity_on_hand.asc())
        .limit(limit)
    )
    items = result.all()
    
    low_stock_items = []
    for level, product in items:
        low_stock_items.append(LowStockItemResponse(
            id=str(level.id),
            name=product.name if product else 'Unknown',
            current=float(level.quantity_on_hand),
            reorder=50.0,  # Default reorder point
            unit=product.unit_of_measure if hasattr(product, 'unit_of_measure') and product.unit_of_measure else 'pcs'
        ))
    
    return low_stock_items


# =============================================================================
# Endpoints - Warehouses CRUD
# =============================================================================

@router.get("/warehouses", response_model=APIResponse[dict])
async def get_warehouses(db: DBSession, current_user: CurrentUser) -> Any:
    """Get all warehouses."""
    result = await db.execute(select(Warehouse))
    warehouses = result.scalars().all()
    
    items = []
    for w in warehouses:
        # Count locations
        loc_count = await db.scalar(
            select(func.count(Location.id)).where(Location.warehouse_id == w.id)
        ) or 0
        
        items.append({
            "id": str(w.id),
            "name": w.name,
            "code": w.code,
            "address": w.address,
            "location_count": loc_count
        })
    
    return build_response(data={"items": items})


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(warehouse_id: UUID, db: DBSession, current_user: CurrentUser) -> Any:
    """Get a specific warehouse."""
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    loc_count = await db.scalar(
        select(func.count(Location.id)).where(Location.warehouse_id == warehouse.id)
    ) or 0
    
    return WarehouseResponse(
        id=str(warehouse.id),
        name=warehouse.name,
        code=warehouse.code,
        address=warehouse.address,
        location_count=loc_count
    )


# =============================================================================
# Endpoints - Locations
# =============================================================================

@router.get("/locations", response_model=APIResponse[dict])
async def get_locations(
    db: DBSession,
    current_user: CurrentUser,
    warehouse_id: Optional[UUID] = None
) -> Any:
    """Get all locations, optionally filtered by warehouse."""
    query = select(Location)
    if warehouse_id:
        query = query.where(Location.warehouse_id == warehouse_id)
    
    result = await db.execute(query)
    locations = result.scalars().all()
    
    items = [
        {
            "id": str(loc.id),
            "warehouse_id": str(loc.warehouse_id),
            "name": loc.name,
            "location_type": loc.location_type,
            "parent_id": str(loc.parent_id) if loc.parent_id else None
        }
        for loc in locations
    ]
    
    return build_response(data={"items": items})


# =============================================================================
# Endpoints - Inventory Levels
# =============================================================================

@router.get("/levels", response_model=APIResponse[dict])
async def get_inventory_levels(
    db: DBSession,
    current_user: CurrentUser,
    location_id: Optional[UUID] = None,
    product_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500)
) -> Any:
    """Get inventory levels with optional filters."""
    query = select(InventoryLevel, Product, Location).join(
        Product, InventoryLevel.product_id == Product.id
    ).join(
        Location, InventoryLevel.location_id == Location.id
    )
    
    if location_id:
        query = query.where(InventoryLevel.location_id == location_id)
    if product_id:
        query = query.where(InventoryLevel.product_id == product_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for level, product, location in rows:
        items.append({
            "id": str(level.id),
            "product_id": level.product_id,
            "product_name": product.name if product else 'Unknown',
            "location_id": str(level.location_id),
            "location_name": location.name if location else 'Unknown',
            "quantity_on_hand": float(level.quantity_on_hand),
            "quantity_reserved": float(level.quantity_reserved),
            "quantity_available": float(level.quantity_available)
        })
    
    return build_response(data={"items": items})


@router.post("/sync", response_model=dict)
async def sync_inventory(
    db: DBSession, 
    current_user: CurrentUser,
    starz_db: AsyncSession = Depends(get_starz_erp_session)
) -> Any:
    """Trigger inventory synchronization from starzERP."""
    service = StarzErpIngestionService()
    try:
        stats = await service.run_full_ingestion(starz_db, db)
        return {
            "success": True,
            "message": "Inventory synchronization completed",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}")
