"""
Warehouse Management System (WMS) Integration Service.

Provides WMS-Lite functionality with:
- Location mapping (Aisle/Bin/Rack hierarchy, zones)
- Inventory status management
- Core transactions (Putaway, Picking, Issue to WO)
- Smart cycle counting
- ERP synchronization
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class LocationType(str, Enum):
    """Types of warehouse locations."""
    RECEIVING = "receiving"
    STORAGE = "storage"
    PICKING = "picking"
    SHIPPING = "shipping"
    QUARANTINE = "quarantine"
    MRB = "mrb"  # Material Review Board
    WIP_SUPERMARKET = "wip_supermarket"
    STAGING = "staging"
    PRODUCTION = "production"
    FINISHED_GOODS = "finished_goods"


class InventoryStatus(str, Enum):
    """Inventory status states."""
    AVAILABLE = "available"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    RESERVED = "reserved"
    IN_TRANSIT = "in_transit"
    ALLOCATED = "allocated"
    ON_HOLD = "on_hold"
    BLOCKED = "blocked"


class TransactionType(str, Enum):
    """Types of inventory transactions."""
    RECEIPT = "receipt"
    PUTAWAY = "putaway"
    PICK = "pick"
    ISSUE = "issue"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    CYCLE_COUNT = "cycle_count"
    RETURN = "return"
    SCRAP = "scrap"
    SHIP = "ship"


class PickStrategy(str, Enum):
    """Picking strategies."""
    FIFO = "fifo"  # First In First Out
    FEFO = "fefo"  # First Expired First Out
    LIFO = "lifo"  # Last In First Out
    MIN_MOVES = "min_moves"  # Minimize movements
    CLOSEST = "closest"  # Closest to pick point


class CycleCountPriority(str, Enum):
    """Cycle count priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


class ShipmentStatus(str, Enum):
    """Shipment status states."""
    PENDING = "pending"
    PICKING = "picking"
    PACKED = "packed"
    STAGED = "staged"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class WarehouseLocation:
    """A warehouse location (bin/rack/aisle)."""
    id: str
    code: str
    name: str
    location_type: LocationType
    warehouse_id: str | None = None
    zone_id: str | None = None
    aisle: str | None = None
    rack: str | None = None
    level: str | None = None
    bin: str | None = None
    is_active: bool = True
    capacity: Decimal = Decimal("0")
    current_usage: Decimal = Decimal("0")
    pick_sequence: int = 0
    is_bulk: bool = False
    temperature_controlled: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WarehouseZone:
    """A warehouse zone grouping locations."""
    id: str
    code: str
    name: str
    warehouse_id: str | None = None
    zone_type: LocationType = LocationType.STORAGE
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InventoryRecord:
    """An inventory record for a part at a location."""
    id: str
    part_id: str
    part_number: str
    location_id: str
    quantity: Decimal
    uom: str
    status: InventoryStatus = InventoryStatus.AVAILABLE
    lot_number: str | None = None
    serial_number: str | None = None
    expiry_date: datetime | None = None
    receipt_date: datetime | None = None
    supplier_id: str | None = None
    purchase_order_id: str | None = None
    work_order_id: str | None = None
    reserved_quantity: Decimal = Decimal("0")
    allocated_quantity: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InventoryTransaction:
    """A record of an inventory movement."""
    id: str
    transaction_type: TransactionType
    part_id: str
    part_number: str
    quantity: Decimal
    uom: str
    from_location_id: str | None = None
    to_location_id: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    reference_type: str | None = None  # work_order, purchase_order, sales_order
    reference_id: str | None = None
    reason_code: str | None = None
    performed_by: str | None = None
    performed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    erp_synced: bool = False
    erp_sync_at: datetime | None = None
    notes: str | None = None


@dataclass
class PickTask:
    """A pick task for order fulfillment."""
    id: str
    order_id: str
    order_type: str  # sales_order, work_order, transfer
    part_id: str
    part_number: str
    required_quantity: Decimal
    picked_quantity: Decimal = Decimal("0")
    uom: str = ""
    from_location_id: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    pick_sequence: int = 0
    status: str = "pending"  # pending, in_progress, completed, cancelled
    assigned_to: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PutawayTask:
    """A putaway task for received goods."""
    id: str
    receipt_id: str
    part_id: str
    part_number: str
    quantity: Decimal
    uom: str
    from_location_id: str  # Receiving dock
    suggested_location_id: str | None = None
    actual_location_id: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    status: str = "pending"  # pending, in_progress, completed
    assigned_to: str | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CycleCount:
    """A cycle count request."""
    id: str
    location_id: str
    part_id: str | None = None
    scheduled_date: datetime | None = None
    priority: CycleCountPriority = CycleCountPriority.MEDIUM
    system_quantity: Decimal = Decimal("0")
    counted_quantity: Decimal | None = None
    variance: Decimal | None = None
    variance_percentage: Decimal | None = None
    status: str = "pending"  # pending, in_progress, counted, verified, adjusted
    counted_by: str | None = None
    counted_at: datetime | None = None
    verified_by: str | None = None
    verified_at: datetime | None = None
    adjustment_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GoodsReceipt:
    """A goods receipt record."""
    id: str
    receipt_number: str
    supplier_id: str | None = None
    purchase_order_id: str | None = None
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    received_by: str | None = None
    status: str = "pending"  # pending, inspecting, completed, rejected
    dock_location_id: str | None = None
    notes: str | None = None
    erp_synced: bool = False
    erp_gr_number: str | None = None


@dataclass
class GoodsReceiptLine:
    """A line item in a goods receipt."""
    id: str
    receipt_id: str
    part_id: str
    part_number: str
    expected_quantity: Decimal
    received_quantity: Decimal
    uom: str
    lot_number: str | None = None
    serial_numbers: list[str] = field(default_factory=list)
    inspection_required: bool = False
    inspection_lot_id: str | None = None
    status: str = "pending"  # pending, received, inspected, putaway


@dataclass
class Shipment:
    """A shipment record."""
    id: str
    shipment_number: str
    order_id: str
    order_type: str
    customer_id: str | None = None
    ship_to_address: str | None = None
    status: ShipmentStatus = ShipmentStatus.PENDING
    carrier: str | None = None
    tracking_number: str | None = None
    shipped_at: datetime | None = None
    estimated_delivery: datetime | None = None
    packing_list_generated: bool = False
    erp_synced: bool = False
    erp_obd_number: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PackingListLine:
    """A line in a packing list."""
    id: str
    shipment_id: str
    part_id: str
    part_number: str
    description: str
    quantity: Decimal
    uom: str
    lot_number: str | None = None
    serial_numbers: list[str] = field(default_factory=list)
    package_number: int = 1
    weight: Decimal = Decimal("0")


@dataclass
class StockLevel:
    """Aggregated stock level for a part."""
    part_id: str
    part_number: str
    total_quantity: Decimal
    available_quantity: Decimal
    reserved_quantity: Decimal
    quarantined_quantity: Decimal
    in_transit_quantity: Decimal
    uom: str
    locations: list[str] = field(default_factory=list)


# =============================================================================
# WMS INTEGRATION SERVICE
# =============================================================================


class WMSIntegrationService:
    """
    Warehouse Management System (WMS-Lite) Service.
    
    Provides:
    - Location management
    - Inventory tracking
    - Transactions (putaway, pick, transfer)
    - Cycle counting
    - ERP synchronization
    """
    
    def __init__(self, default_pick_strategy: PickStrategy = PickStrategy.FIFO):
        self.default_pick_strategy = default_pick_strategy
        
        # Storage
        self._zones: dict[str, WarehouseZone] = {}
        self._locations: dict[str, WarehouseLocation] = {}
        self._inventory: dict[str, InventoryRecord] = {}
        self._transactions: list[InventoryTransaction] = []
        self._pick_tasks: dict[str, PickTask] = {}
        self._putaway_tasks: dict[str, PutawayTask] = {}
        self._cycle_counts: dict[str, CycleCount] = {}
        self._goods_receipts: dict[str, GoodsReceipt] = {}
        self._goods_receipt_lines: list[GoodsReceiptLine] = []
        self._shipments: dict[str, Shipment] = {}
        self._packing_list_lines: list[PackingListLine] = []
        
        # ERP sync queue
        self._erp_sync_queue: list[dict[str, Any]] = []
    
    # =========================================================================
    # ZONE MANAGEMENT
    # =========================================================================
    
    def create_zone(
        self,
        code: str,
        name: str,
        zone_type: LocationType = LocationType.STORAGE,
        warehouse_id: str | None = None,
    ) -> WarehouseZone:
        """Create a warehouse zone."""
        zone_id = str(uuid4())
        zone = WarehouseZone(
            id=zone_id,
            code=code,
            name=name,
            warehouse_id=warehouse_id,
            zone_type=zone_type,
        )
        self._zones[zone_id] = zone
        logger.info(f"Created zone: {code} ({zone_type.value})")
        return zone
    
    def get_zone(self, zone_id: str) -> WarehouseZone | None:
        """Get a zone by ID."""
        return self._zones.get(zone_id)
    
    def get_zones(self, zone_type: LocationType | None = None) -> list[WarehouseZone]:
        """Get all zones, optionally filtered by type."""
        zones = list(self._zones.values())
        if zone_type:
            zones = [z for z in zones if z.zone_type == zone_type]
        return zones
    
    # =========================================================================
    # LOCATION MANAGEMENT
    # =========================================================================
    
    def create_location(
        self,
        code: str,
        name: str,
        location_type: LocationType,
        zone_id: str | None = None,
        aisle: str | None = None,
        rack: str | None = None,
        level: str | None = None,
        bin: str | None = None,
        capacity: Decimal = Decimal("0"),
        pick_sequence: int = 0,
    ) -> WarehouseLocation:
        """Create a warehouse location."""
        location_id = str(uuid4())
        location = WarehouseLocation(
            id=location_id,
            code=code,
            name=name,
            location_type=location_type,
            zone_id=zone_id,
            aisle=aisle,
            rack=rack,
            level=level,
            bin=bin,
            capacity=capacity,
            pick_sequence=pick_sequence,
        )
        self._locations[location_id] = location
        logger.info(f"Created location: {code} ({location_type.value})")
        return location
    
    def get_location(self, location_id: str) -> WarehouseLocation | None:
        """Get a location by ID."""
        return self._locations.get(location_id)
    
    def get_location_by_code(self, code: str) -> WarehouseLocation | None:
        """Get a location by code."""
        for loc in self._locations.values():
            if loc.code == code:
                return loc
        return None
    
    def get_locations(
        self,
        zone_id: str | None = None,
        location_type: LocationType | None = None,
        active_only: bool = True,
    ) -> list[WarehouseLocation]:
        """Get locations with optional filters."""
        locations = list(self._locations.values())
        
        if zone_id:
            locations = [l for l in locations if l.zone_id == zone_id]
        
        if location_type:
            locations = [l for l in locations if l.location_type == location_type]
        
        if active_only:
            locations = [l for l in locations if l.is_active]
        
        return sorted(locations, key=lambda l: l.pick_sequence)
    
    def update_location(self, location_id: str, **kwargs) -> WarehouseLocation | None:
        """Update a location."""
        location = self._locations.get(location_id)
        if not location:
            return None
        
        for key, value in kwargs.items():
            if hasattr(location, key):
                setattr(location, key, value)
        
        return location
    
    # =========================================================================
    # INVENTORY MANAGEMENT
    # =========================================================================
    
    def create_inventory_record(
        self,
        part_id: str,
        part_number: str,
        location_id: str,
        quantity: Decimal,
        uom: str,
        status: InventoryStatus = InventoryStatus.AVAILABLE,
        lot_number: str | None = None,
        serial_number: str | None = None,
        expiry_date: datetime | None = None,
        supplier_id: str | None = None,
        unit_cost: Decimal = Decimal("0"),
    ) -> InventoryRecord:
        """Create an inventory record."""
        record_id = str(uuid4())
        record = InventoryRecord(
            id=record_id,
            part_id=part_id,
            part_number=part_number,
            location_id=location_id,
            quantity=quantity,
            uom=uom,
            status=status,
            lot_number=lot_number,
            serial_number=serial_number,
            expiry_date=expiry_date,
            supplier_id=supplier_id,
            unit_cost=unit_cost,
            receipt_date=datetime.now(timezone.utc),
        )
        self._inventory[record_id] = record
        
        # Update location usage
        location = self._locations.get(location_id)
        if location:
            location.current_usage += quantity
        
        logger.info(f"Created inventory: {part_number} x {quantity} at {location_id}")
        return record
    
    def get_inventory_record(self, record_id: str) -> InventoryRecord | None:
        """Get an inventory record by ID."""
        return self._inventory.get(record_id)
    
    def get_inventory_by_part(
        self,
        part_id: str,
        status: InventoryStatus | None = None,
        location_id: str | None = None,
    ) -> list[InventoryRecord]:
        """Get inventory records for a part."""
        records = [r for r in self._inventory.values() if r.part_id == part_id]
        
        if status:
            records = [r for r in records if r.status == status]
        
        if location_id:
            records = [r for r in records if r.location_id == location_id]
        
        return records
    
    def get_inventory_by_location(
        self,
        location_id: str,
        status: InventoryStatus | None = None,
    ) -> list[InventoryRecord]:
        """Get inventory records at a location."""
        records = [r for r in self._inventory.values() if r.location_id == location_id]
        
        if status:
            records = [r for r in records if r.status == status]
        
        return records
    
    def get_inventory_by_lot(self, lot_number: str) -> list[InventoryRecord]:
        """Get inventory records for a lot number."""
        return [r for r in self._inventory.values() if r.lot_number == lot_number]
    
    def get_stock_level(self, part_id: str) -> StockLevel | None:
        """Get aggregated stock level for a part."""
        records = self.get_inventory_by_part(part_id)
        if not records:
            return None
        
        total = Decimal("0")
        available = Decimal("0")
        reserved = Decimal("0")
        quarantined = Decimal("0")
        in_transit = Decimal("0")
        locations = set()
        
        for r in records:
            total += r.quantity
            locations.add(r.location_id)
            
            if r.status == InventoryStatus.AVAILABLE:
                available += r.quantity - r.reserved_quantity - r.allocated_quantity
            elif r.status == InventoryStatus.QUARANTINED:
                quarantined += r.quantity
            elif r.status == InventoryStatus.IN_TRANSIT:
                in_transit += r.quantity
            elif r.status == InventoryStatus.RESERVED:
                reserved += r.quantity
        
        return StockLevel(
            part_id=part_id,
            part_number=records[0].part_number,
            total_quantity=total,
            available_quantity=available,
            reserved_quantity=reserved,
            quarantined_quantity=quarantined,
            in_transit_quantity=in_transit,
            uom=records[0].uom,
            locations=list(locations),
        )
    
    def update_inventory_status(
        self,
        record_id: str,
        new_status: InventoryStatus,
        reason: str | None = None,
        performed_by: str | None = None,
    ) -> InventoryRecord | None:
        """Update inventory status."""
        record = self._inventory.get(record_id)
        if not record:
            return None
        
        old_status = record.status
        record.status = new_status
        record.updated_at = datetime.now(timezone.utc)
        
        # Log transaction
        self._record_transaction(
            transaction_type=TransactionType.ADJUSTMENT,
            part_id=record.part_id,
            part_number=record.part_number,
            quantity=record.quantity,
            uom=record.uom,
            from_location_id=record.location_id,
            to_location_id=record.location_id,
            lot_number=record.lot_number,
            reason_code=f"status_change:{old_status.value}>{new_status.value}",
            performed_by=performed_by,
            notes=reason,
        )
        
        return record
    
    def reserve_inventory(
        self,
        record_id: str,
        quantity: Decimal,
        reference_type: str,
        reference_id: str,
    ) -> bool:
        """Reserve inventory for an order."""
        record = self._inventory.get(record_id)
        if not record:
            return False
        
        available = record.quantity - record.reserved_quantity - record.allocated_quantity
        if quantity > available:
            return False
        
        record.reserved_quantity += quantity
        record.updated_at = datetime.now(timezone.utc)
        return True
    
    def release_reservation(
        self,
        record_id: str,
        quantity: Decimal,
    ) -> bool:
        """Release a reservation."""
        record = self._inventory.get(record_id)
        if not record:
            return False
        
        if quantity > record.reserved_quantity:
            return False
        
        record.reserved_quantity -= quantity
        record.updated_at = datetime.now(timezone.utc)
        return True
    
    # =========================================================================
    # TRANSACTIONS
    # =========================================================================
    
    def _record_transaction(
        self,
        transaction_type: TransactionType,
        part_id: str,
        part_number: str,
        quantity: Decimal,
        uom: str,
        from_location_id: str | None = None,
        to_location_id: str | None = None,
        lot_number: str | None = None,
        serial_number: str | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        reason_code: str | None = None,
        performed_by: str | None = None,
        notes: str | None = None,
    ) -> InventoryTransaction:
        """Record an inventory transaction."""
        transaction = InventoryTransaction(
            id=str(uuid4()),
            transaction_type=transaction_type,
            part_id=part_id,
            part_number=part_number,
            quantity=quantity,
            uom=uom,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            lot_number=lot_number,
            serial_number=serial_number,
            reference_type=reference_type,
            reference_id=reference_id,
            reason_code=reason_code,
            performed_by=performed_by,
            notes=notes,
        )
        self._transactions.append(transaction)
        
        # Queue for ERP sync
        self._erp_sync_queue.append({
            "type": "transaction",
            "id": transaction.id,
            "data": transaction,
        })
        
        return transaction
    
    def transfer_inventory(
        self,
        from_location_id: str,
        to_location_id: str,
        part_id: str,
        quantity: Decimal,
        lot_number: str | None = None,
        performed_by: str | None = None,
        reason: str | None = None,
    ) -> InventoryTransaction | None:
        """Transfer inventory between locations."""
        # Find source inventory
        source_records = self.get_inventory_by_part(
            part_id, 
            status=InventoryStatus.AVAILABLE,
            location_id=from_location_id
        )
        
        if lot_number:
            source_records = [r for r in source_records if r.lot_number == lot_number]
        
        if not source_records:
            logger.error(f"No available inventory for transfer: {part_id}")
            return None
        
        source = source_records[0]
        available = source.quantity - source.reserved_quantity - source.allocated_quantity
        
        if quantity > available:
            logger.error(f"Insufficient quantity for transfer: {available} < {quantity}")
            return None
        
        # Reduce source
        source.quantity -= quantity
        source.updated_at = datetime.now(timezone.utc)
        
        # Update source location usage
        from_loc = self._locations.get(from_location_id)
        if from_loc:
            from_loc.current_usage -= quantity
        
        # Add to destination (or create new record)
        dest_records = [
            r for r in self._inventory.values()
            if r.part_id == part_id 
            and r.location_id == to_location_id
            and r.lot_number == source.lot_number
            and r.status == InventoryStatus.AVAILABLE
        ]
        
        if dest_records:
            dest = dest_records[0]
            dest.quantity += quantity
            dest.updated_at = datetime.now(timezone.utc)
        else:
            self.create_inventory_record(
                part_id=source.part_id,
                part_number=source.part_number,
                location_id=to_location_id,
                quantity=quantity,
                uom=source.uom,
                lot_number=source.lot_number,
                serial_number=source.serial_number,
                expiry_date=source.expiry_date,
                supplier_id=source.supplier_id,
                unit_cost=source.unit_cost,
            )
        
        # Record transaction
        transaction = self._record_transaction(
            transaction_type=TransactionType.TRANSFER,
            part_id=part_id,
            part_number=source.part_number,
            quantity=quantity,
            uom=source.uom,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            lot_number=source.lot_number,
            performed_by=performed_by,
            notes=reason,
        )
        
        logger.info(f"Transferred {quantity} of {part_id} from {from_location_id} to {to_location_id}")
        return transaction
    
    def issue_to_work_order(
        self,
        work_order_id: str,
        part_id: str,
        quantity: Decimal,
        from_location_id: str | None = None,
        lot_number: str | None = None,
        performed_by: str | None = None,
    ) -> InventoryTransaction | None:
        """Issue inventory to a work order."""
        # Find available inventory using pick strategy
        candidates = self._get_pick_candidates(
            part_id=part_id,
            quantity=quantity,
            location_id=from_location_id,
            lot_number=lot_number,
        )
        
        if not candidates:
            logger.error(f"No available inventory for WO issue: {part_id}")
            return None
        
        source = candidates[0]
        actual_location = source.location_id
        
        # Reduce inventory
        source.quantity -= quantity
        source.updated_at = datetime.now(timezone.utc)
        
        # Update location usage
        loc = self._locations.get(actual_location)
        if loc:
            loc.current_usage -= quantity
        
        # Record transaction
        transaction = self._record_transaction(
            transaction_type=TransactionType.ISSUE,
            part_id=part_id,
            part_number=source.part_number,
            quantity=quantity,
            uom=source.uom,
            from_location_id=actual_location,
            lot_number=source.lot_number,
            reference_type="work_order",
            reference_id=work_order_id,
            performed_by=performed_by,
        )
        
        logger.info(f"Issued {quantity} of {part_id} to WO {work_order_id}")
        return transaction
    
    def receive_from_production(
        self,
        work_order_id: str,
        part_id: str,
        part_number: str,
        quantity: Decimal,
        uom: str,
        to_location_id: str,
        lot_number: str | None = None,
        performed_by: str | None = None,
    ) -> InventoryRecord:
        """Receive finished goods from production."""
        record = self.create_inventory_record(
            part_id=part_id,
            part_number=part_number,
            location_id=to_location_id,
            quantity=quantity,
            uom=uom,
            lot_number=lot_number,
        )
        
        # Record transaction
        self._record_transaction(
            transaction_type=TransactionType.RECEIPT,
            part_id=part_id,
            part_number=part_number,
            quantity=quantity,
            uom=uom,
            to_location_id=to_location_id,
            lot_number=lot_number,
            reference_type="work_order",
            reference_id=work_order_id,
            performed_by=performed_by,
        )
        
        logger.info(f"Received {quantity} of {part_id} from WO {work_order_id}")
        return record
    
    def adjust_inventory(
        self,
        record_id: str,
        new_quantity: Decimal,
        reason_code: str,
        performed_by: str,
        notes: str | None = None,
    ) -> InventoryTransaction | None:
        """Adjust inventory quantity."""
        record = self._inventory.get(record_id)
        if not record:
            return None
        
        old_quantity = record.quantity
        adjustment = new_quantity - old_quantity
        
        record.quantity = new_quantity
        record.updated_at = datetime.now(timezone.utc)
        
        # Update location usage
        loc = self._locations.get(record.location_id)
        if loc:
            loc.current_usage += adjustment
        
        transaction = self._record_transaction(
            transaction_type=TransactionType.ADJUSTMENT,
            part_id=record.part_id,
            part_number=record.part_number,
            quantity=adjustment,
            uom=record.uom,
            from_location_id=record.location_id if adjustment < 0 else None,
            to_location_id=record.location_id if adjustment > 0 else None,
            lot_number=record.lot_number,
            reason_code=reason_code,
            performed_by=performed_by,
            notes=notes,
        )
        
        logger.info(f"Adjusted inventory {record_id}: {old_quantity} -> {new_quantity}")
        return transaction
    
    def scrap_inventory(
        self,
        record_id: str,
        quantity: Decimal,
        reason_code: str,
        performed_by: str,
        notes: str | None = None,
    ) -> InventoryTransaction | None:
        """Scrap inventory."""
        record = self._inventory.get(record_id)
        if not record:
            return None
        
        if quantity > record.quantity:
            return None
        
        record.quantity -= quantity
        record.updated_at = datetime.now(timezone.utc)
        
        # Update location usage
        loc = self._locations.get(record.location_id)
        if loc:
            loc.current_usage -= quantity
        
        transaction = self._record_transaction(
            transaction_type=TransactionType.SCRAP,
            part_id=record.part_id,
            part_number=record.part_number,
            quantity=quantity,
            uom=record.uom,
            from_location_id=record.location_id,
            lot_number=record.lot_number,
            reason_code=reason_code,
            performed_by=performed_by,
            notes=notes,
        )
        
        logger.info(f"Scrapped {quantity} of {record.part_number}")
        return transaction
    
    def get_transactions(
        self,
        part_id: str | None = None,
        transaction_type: TransactionType | None = None,
        since: datetime | None = None,
        reference_id: str | None = None,
    ) -> list[InventoryTransaction]:
        """Get inventory transactions."""
        transactions = self._transactions
        
        if part_id:
            transactions = [t for t in transactions if t.part_id == part_id]
        
        if transaction_type:
            transactions = [t for t in transactions if t.transaction_type == transaction_type]
        
        if since:
            transactions = [t for t in transactions if t.performed_at >= since]
        
        if reference_id:
            transactions = [t for t in transactions if t.reference_id == reference_id]
        
        return sorted(transactions, key=lambda t: t.performed_at, reverse=True)
    
    # =========================================================================
    # PICKING
    # =========================================================================
    
    def _get_pick_candidates(
        self,
        part_id: str,
        quantity: Decimal,
        location_id: str | None = None,
        lot_number: str | None = None,
        strategy: PickStrategy | None = None,
    ) -> list[InventoryRecord]:
        """Get pick candidates based on strategy."""
        strategy = strategy or self.default_pick_strategy
        
        candidates = self.get_inventory_by_part(
            part_id, 
            status=InventoryStatus.AVAILABLE,
            location_id=location_id
        )
        
        if lot_number:
            candidates = [c for c in candidates if c.lot_number == lot_number]
        
        # Filter by available quantity
        candidates = [
            c for c in candidates 
            if (c.quantity - c.reserved_quantity - c.allocated_quantity) > 0
        ]
        
        # Sort based on strategy
        if strategy == PickStrategy.FIFO:
            candidates.sort(key=lambda c: c.receipt_date or datetime.min.replace(tzinfo=timezone.utc))
        elif strategy == PickStrategy.FEFO:
            candidates.sort(key=lambda c: c.expiry_date or datetime.max.replace(tzinfo=timezone.utc))
        elif strategy == PickStrategy.LIFO:
            candidates.sort(key=lambda c: c.receipt_date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        elif strategy == PickStrategy.MIN_MOVES:
            # Prefer locations with exact or closest quantity
            candidates.sort(key=lambda c: abs(c.quantity - quantity))
        
        return candidates
    
    def create_pick_task(
        self,
        order_id: str,
        order_type: str,
        part_id: str,
        part_number: str,
        required_quantity: Decimal,
        uom: str,
        strategy: PickStrategy | None = None,
    ) -> PickTask | None:
        """Create a pick task for an order."""
        candidates = self._get_pick_candidates(
            part_id=part_id,
            quantity=required_quantity,
            strategy=strategy,
        )
        
        if not candidates:
            logger.warning(f"No pick candidates for {part_id}")
            return None
        
        source = candidates[0]
        
        task = PickTask(
            id=str(uuid4()),
            order_id=order_id,
            order_type=order_type,
            part_id=part_id,
            part_number=part_number,
            required_quantity=required_quantity,
            uom=uom,
            from_location_id=source.location_id,
            lot_number=source.lot_number,
            pick_sequence=self._locations.get(source.location_id, WarehouseLocation(
                id="", code="", name="", location_type=LocationType.STORAGE
            )).pick_sequence,
        )
        
        self._pick_tasks[task.id] = task
        
        # Allocate inventory
        source.allocated_quantity += required_quantity
        
        logger.info(f"Created pick task for {part_number} x {required_quantity}")
        return task
    
    def complete_pick_task(
        self,
        task_id: str,
        picked_quantity: Decimal,
        performed_by: str,
        lot_number: str | None = None,
    ) -> PickTask | None:
        """Complete a pick task."""
        task = self._pick_tasks.get(task_id)
        if not task:
            return None
        
        task.picked_quantity = picked_quantity
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        
        # Find and reduce inventory
        records = self.get_inventory_by_part(
            task.part_id,
            location_id=task.from_location_id,
        )
        
        if lot_number:
            records = [r for r in records if r.lot_number == lot_number]
        
        if records:
            record = records[0]
            record.quantity -= picked_quantity
            record.allocated_quantity = max(Decimal("0"), record.allocated_quantity - task.required_quantity)
            record.updated_at = datetime.now(timezone.utc)
            
            # Update location usage
            loc = self._locations.get(task.from_location_id)
            if loc:
                loc.current_usage -= picked_quantity
        
        # Record transaction
        self._record_transaction(
            transaction_type=TransactionType.PICK,
            part_id=task.part_id,
            part_number=task.part_number,
            quantity=picked_quantity,
            uom=task.uom,
            from_location_id=task.from_location_id,
            lot_number=lot_number or task.lot_number,
            reference_type=task.order_type,
            reference_id=task.order_id,
            performed_by=performed_by,
        )
        
        return task
    
    def get_pick_tasks(
        self,
        order_id: str | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
    ) -> list[PickTask]:
        """Get pick tasks."""
        tasks = list(self._pick_tasks.values())
        
        if order_id:
            tasks = [t for t in tasks if t.order_id == order_id]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        return sorted(tasks, key=lambda t: t.pick_sequence)
    
    # =========================================================================
    # PUTAWAY
    # =========================================================================
    
    def suggest_putaway_location(
        self,
        part_id: str,
        quantity: Decimal,
        zone_type: LocationType = LocationType.STORAGE,
    ) -> WarehouseLocation | None:
        """Suggest a putaway location for a part."""
        # Find existing locations with same part
        existing = self.get_inventory_by_part(part_id)
        if existing:
            location = self._locations.get(existing[0].location_id)
            if location and location.is_active:
                available_capacity = location.capacity - location.current_usage
                if available_capacity >= quantity or location.capacity == Decimal("0"):
                    return location
        
        # Find empty locations in zone
        locations = self.get_locations(location_type=zone_type)
        for loc in locations:
            if loc.capacity == Decimal("0"):  # No capacity limit
                return loc
            if loc.capacity - loc.current_usage >= quantity:
                return loc
        
        return None
    
    def create_putaway_task(
        self,
        receipt_id: str,
        part_id: str,
        part_number: str,
        quantity: Decimal,
        uom: str,
        from_location_id: str,
        lot_number: str | None = None,
    ) -> PutawayTask:
        """Create a putaway task."""
        suggested = self.suggest_putaway_location(part_id, quantity)
        
        task = PutawayTask(
            id=str(uuid4()),
            receipt_id=receipt_id,
            part_id=part_id,
            part_number=part_number,
            quantity=quantity,
            uom=uom,
            from_location_id=from_location_id,
            suggested_location_id=suggested.id if suggested else None,
            lot_number=lot_number,
        )
        
        self._putaway_tasks[task.id] = task
        return task
    
    def complete_putaway_task(
        self,
        task_id: str,
        actual_location_id: str,
        performed_by: str,
    ) -> PutawayTask | None:
        """Complete a putaway task."""
        task = self._putaway_tasks.get(task_id)
        if not task:
            return None
        
        task.actual_location_id = actual_location_id
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        
        # Create inventory record
        self.create_inventory_record(
            part_id=task.part_id,
            part_number=task.part_number,
            location_id=actual_location_id,
            quantity=task.quantity,
            uom=task.uom,
            lot_number=task.lot_number,
        )
        
        # Record transaction
        self._record_transaction(
            transaction_type=TransactionType.PUTAWAY,
            part_id=task.part_id,
            part_number=task.part_number,
            quantity=task.quantity,
            uom=task.uom,
            from_location_id=task.from_location_id,
            to_location_id=actual_location_id,
            lot_number=task.lot_number,
            reference_type="receipt",
            reference_id=task.receipt_id,
            performed_by=performed_by,
        )
        
        return task
    
    # =========================================================================
    # CYCLE COUNTING
    # =========================================================================
    
    def create_cycle_count(
        self,
        location_id: str,
        part_id: str | None = None,
        priority: CycleCountPriority = CycleCountPriority.MEDIUM,
        scheduled_date: datetime | None = None,
    ) -> CycleCount:
        """Create a cycle count request."""
        # Calculate system quantity
        if part_id:
            records = self.get_inventory_by_part(part_id, location_id=location_id)
        else:
            records = self.get_inventory_by_location(location_id)
        
        system_qty = sum(r.quantity for r in records)
        
        count = CycleCount(
            id=str(uuid4()),
            location_id=location_id,
            part_id=part_id,
            scheduled_date=scheduled_date or datetime.now(timezone.utc),
            priority=priority,
            system_quantity=system_qty,
        )
        
        self._cycle_counts[count.id] = count
        return count
    
    def record_cycle_count(
        self,
        count_id: str,
        counted_quantity: Decimal,
        counted_by: str,
    ) -> CycleCount | None:
        """Record a cycle count result."""
        count = self._cycle_counts.get(count_id)
        if not count:
            return None
        
        count.counted_quantity = counted_quantity
        count.counted_by = counted_by
        count.counted_at = datetime.now(timezone.utc)
        count.variance = counted_quantity - count.system_quantity
        
        if count.system_quantity != Decimal("0"):
            count.variance_percentage = (count.variance / count.system_quantity) * 100
        else:
            count.variance_percentage = Decimal("100") if counted_quantity > 0 else Decimal("0")
        
        count.status = "counted"
        return count
    
    def verify_cycle_count(
        self,
        count_id: str,
        verified_by: str,
        apply_adjustment: bool = False,
        adjustment_reason: str | None = None,
    ) -> CycleCount | None:
        """Verify a cycle count and optionally apply adjustment."""
        count = self._cycle_counts.get(count_id)
        if not count or count.status != "counted":
            return None
        
        count.verified_by = verified_by
        count.verified_at = datetime.now(timezone.utc)
        
        if apply_adjustment and count.variance and count.variance != Decimal("0"):
            count.status = "adjusted"
            count.adjustment_reason = adjustment_reason
            
            # Find and adjust inventory
            if count.part_id:
                records = self.get_inventory_by_part(
                    count.part_id, 
                    location_id=count.location_id
                )
                if records:
                    self.adjust_inventory(
                        record_id=records[0].id,
                        new_quantity=count.counted_quantity,
                        reason_code="cycle_count",
                        performed_by=verified_by,
                        notes=adjustment_reason,
                    )
            
            # Record transaction
            self._record_transaction(
                transaction_type=TransactionType.CYCLE_COUNT,
                part_id=count.part_id or "",
                part_number="",
                quantity=count.variance,
                uom="",
                from_location_id=count.location_id if count.variance < 0 else None,
                to_location_id=count.location_id if count.variance > 0 else None,
                reason_code="cycle_count_adjustment",
                performed_by=verified_by,
                notes=adjustment_reason,
            )
        else:
            count.status = "verified"
        
        return count
    
    def get_cycle_counts(
        self,
        status: str | None = None,
        priority: CycleCountPriority | None = None,
        location_id: str | None = None,
    ) -> list[CycleCount]:
        """Get cycle counts."""
        counts = list(self._cycle_counts.values())
        
        if status:
            counts = [c for c in counts if c.status == status]
        
        if priority:
            counts = [c for c in counts if c.priority == priority]
        
        if location_id:
            counts = [c for c in counts if c.location_id == location_id]
        
        return counts
    
    def generate_smart_cycle_counts(
        self,
        max_counts: int = 10,
    ) -> list[CycleCount]:
        """Generate smart cycle count suggestions based on discrepancy risk."""
        # Calculate transaction volume per location
        location_activity: dict[str, int] = {}
        for t in self._transactions[-1000:]:  # Last 1000 transactions
            loc_id = t.from_location_id or t.to_location_id
            if loc_id:
                location_activity[loc_id] = location_activity.get(loc_id, 0) + 1
        
        # Sort by activity (high activity = high risk)
        high_risk_locations = sorted(
            location_activity.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_counts]
        
        counts = []
        for loc_id, activity in high_risk_locations:
            priority = CycleCountPriority.CRITICAL if activity > 50 else (
                CycleCountPriority.HIGH if activity > 20 else CycleCountPriority.MEDIUM
            )
            count = self.create_cycle_count(
                location_id=loc_id,
                priority=priority,
            )
            counts.append(count)
        
        return counts
    
    # =========================================================================
    # GOODS RECEIPT
    # =========================================================================
    
    def create_goods_receipt(
        self,
        receipt_number: str,
        supplier_id: str | None = None,
        purchase_order_id: str | None = None,
        dock_location_id: str | None = None,
        received_by: str | None = None,
    ) -> GoodsReceipt:
        """Create a goods receipt."""
        receipt = GoodsReceipt(
            id=str(uuid4()),
            receipt_number=receipt_number,
            supplier_id=supplier_id,
            purchase_order_id=purchase_order_id,
            dock_location_id=dock_location_id,
            received_by=received_by,
        )
        self._goods_receipts[receipt.id] = receipt
        return receipt
    
    def add_goods_receipt_line(
        self,
        receipt_id: str,
        part_id: str,
        part_number: str,
        expected_quantity: Decimal,
        received_quantity: Decimal,
        uom: str,
        lot_number: str | None = None,
        inspection_required: bool = False,
    ) -> GoodsReceiptLine:
        """Add a line to a goods receipt."""
        line = GoodsReceiptLine(
            id=str(uuid4()),
            receipt_id=receipt_id,
            part_id=part_id,
            part_number=part_number,
            expected_quantity=expected_quantity,
            received_quantity=received_quantity,
            uom=uom,
            lot_number=lot_number,
            inspection_required=inspection_required,
            status="received",
        )
        self._goods_receipt_lines.append(line)
        
        # Record transaction
        self._record_transaction(
            transaction_type=TransactionType.RECEIPT,
            part_id=part_id,
            part_number=part_number,
            quantity=received_quantity,
            uom=uom,
            lot_number=lot_number,
            reference_type="purchase_order",
            reference_id=self._goods_receipts.get(receipt_id, GoodsReceipt(
                id="", receipt_number=""
            )).purchase_order_id,
        )
        
        return line
    
    def complete_goods_receipt(
        self,
        receipt_id: str,
    ) -> GoodsReceipt | None:
        """Complete a goods receipt and trigger ERP sync."""
        receipt = self._goods_receipts.get(receipt_id)
        if not receipt:
            return None
        
        receipt.status = "completed"
        
        # Queue for ERP sync
        self._erp_sync_queue.append({
            "type": "goods_receipt",
            "id": receipt.id,
            "data": receipt,
        })
        
        return receipt
    
    def get_goods_receipt(self, receipt_id: str) -> GoodsReceipt | None:
        """Get a goods receipt by ID."""
        return self._goods_receipts.get(receipt_id)
    
    def get_goods_receipt_lines(self, receipt_id: str) -> list[GoodsReceiptLine]:
        """Get lines for a goods receipt."""
        return [l for l in self._goods_receipt_lines if l.receipt_id == receipt_id]
    
    # =========================================================================
    # SHIPPING
    # =========================================================================
    
    def create_shipment(
        self,
        shipment_number: str,
        order_id: str,
        order_type: str,
        customer_id: str | None = None,
        ship_to_address: str | None = None,
    ) -> Shipment:
        """Create a shipment."""
        shipment = Shipment(
            id=str(uuid4()),
            shipment_number=shipment_number,
            order_id=order_id,
            order_type=order_type,
            customer_id=customer_id,
            ship_to_address=ship_to_address,
        )
        self._shipments[shipment.id] = shipment
        return shipment
    
    def add_packing_list_line(
        self,
        shipment_id: str,
        part_id: str,
        part_number: str,
        description: str,
        quantity: Decimal,
        uom: str,
        lot_number: str | None = None,
        package_number: int = 1,
        weight: Decimal = Decimal("0"),
    ) -> PackingListLine:
        """Add a line to a packing list."""
        line = PackingListLine(
            id=str(uuid4()),
            shipment_id=shipment_id,
            part_id=part_id,
            part_number=part_number,
            description=description,
            quantity=quantity,
            uom=uom,
            lot_number=lot_number,
            package_number=package_number,
            weight=weight,
        )
        self._packing_list_lines.append(line)
        return line
    
    def generate_packing_list(self, shipment_id: str) -> dict[str, Any]:
        """Generate a packing list for a shipment."""
        shipment = self._shipments.get(shipment_id)
        if not shipment:
            return {"error": "Shipment not found"}
        
        lines = [l for l in self._packing_list_lines if l.shipment_id == shipment_id]
        
        shipment.packing_list_generated = True
        
        return {
            "shipment_number": shipment.shipment_number,
            "customer_id": shipment.customer_id,
            "ship_to_address": shipment.ship_to_address,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "lines": [
                {
                    "part_number": l.part_number,
                    "description": l.description,
                    "quantity": str(l.quantity),
                    "uom": l.uom,
                    "lot_number": l.lot_number,
                    "package": l.package_number,
                    "weight": str(l.weight),
                }
                for l in lines
            ],
            "total_packages": max([l.package_number for l in lines], default=0),
            "total_weight": str(sum(l.weight for l in lines)),
        }
    
    def confirm_shipment(
        self,
        shipment_id: str,
        carrier: str | None = None,
        tracking_number: str | None = None,
    ) -> Shipment | None:
        """Confirm a shipment and trigger ERP sync."""
        shipment = self._shipments.get(shipment_id)
        if not shipment:
            return None
        
        shipment.status = ShipmentStatus.SHIPPED
        shipment.carrier = carrier
        shipment.tracking_number = tracking_number
        shipment.shipped_at = datetime.now(timezone.utc)
        
        # Record ship transactions for all lines
        lines = [l for l in self._packing_list_lines if l.shipment_id == shipment_id]
        for line in lines:
            self._record_transaction(
                transaction_type=TransactionType.SHIP,
                part_id=line.part_id,
                part_number=line.part_number,
                quantity=line.quantity,
                uom=line.uom,
                lot_number=line.lot_number,
                reference_type=shipment.order_type,
                reference_id=shipment.order_id,
            )
        
        # Queue for ERP sync (OBD)
        self._erp_sync_queue.append({
            "type": "shipment",
            "id": shipment.id,
            "data": shipment,
        })
        
        return shipment
    
    def get_shipment(self, shipment_id: str) -> Shipment | None:
        """Get a shipment by ID."""
        return self._shipments.get(shipment_id)
    
    def get_shipments(
        self,
        status: ShipmentStatus | None = None,
        order_id: str | None = None,
    ) -> list[Shipment]:
        """Get shipments with optional filters."""
        shipments = list(self._shipments.values())
        
        if status:
            shipments = [s for s in shipments if s.status == status]
        
        if order_id:
            shipments = [s for s in shipments if s.order_id == order_id]
        
        return shipments
    
    # =========================================================================
    # ERP SYNC
    # =========================================================================
    
    def get_pending_erp_sync(self) -> list[dict[str, Any]]:
        """Get items pending ERP synchronization."""
        return self._erp_sync_queue.copy()
    
    def mark_erp_synced(self, sync_item_id: str) -> bool:
        """Mark an item as synced to ERP."""
        for item in self._erp_sync_queue:
            if item["id"] == sync_item_id:
                self._erp_sync_queue.remove(item)
                
                # Update the record
                if item["type"] == "transaction":
                    for t in self._transactions:
                        if t.id == sync_item_id:
                            t.erp_synced = True
                            t.erp_sync_at = datetime.now(timezone.utc)
                            break
                elif item["type"] == "goods_receipt":
                    receipt = self._goods_receipts.get(sync_item_id)
                    if receipt:
                        receipt.erp_synced = True
                elif item["type"] == "shipment":
                    shipment = self._shipments.get(sync_item_id)
                    if shipment:
                        shipment.erp_synced = True
                
                return True
        return False
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> dict[str, Any]:
        """Get WMS statistics."""
        return {
            "total_zones": len(self._zones),
            "total_locations": len(self._locations),
            "active_locations": len([l for l in self._locations.values() if l.is_active]),
            "total_inventory_records": len(self._inventory),
            "total_transactions": len(self._transactions),
            "pending_pick_tasks": len([t for t in self._pick_tasks.values() if t.status == "pending"]),
            "pending_putaway_tasks": len([t for t in self._putaway_tasks.values() if t.status == "pending"]),
            "pending_cycle_counts": len([c for c in self._cycle_counts.values() if c.status == "pending"]),
            "pending_erp_sync": len(self._erp_sync_queue),
            "inventory_by_status": {
                status.value: len([r for r in self._inventory.values() if r.status == status])
                for status in InventoryStatus
            },
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_wms_service(
    default_pick_strategy: PickStrategy = PickStrategy.FIFO,
) -> WMSIntegrationService:
    """Factory function to create a WMS Integration service."""
    return WMSIntegrationService(default_pick_strategy=default_pick_strategy)
