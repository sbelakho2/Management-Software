"""
Lot & Serial Traceability (Genealogy) Service.

Provides end-to-end traceability with:
- Supplier Lot → Incoming Inspection → WO Consumption → Finished Good Lot
- Full 1-Up/1-Down genealogy
- "Where-Used" Intelligence for recall readiness
- Evidence Binding (COA/COC attachments)
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


class LotStatus(str, Enum):
    """Lot status states."""
    ACTIVE = "active"
    CONSUMED = "consumed"
    SHIPPED = "shipped"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    EXPIRED = "expired"
    RECALLED = "recalled"


class SerialStatus(str, Enum):
    """Serial number status states."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    SHIPPED = "shipped"
    RETURNED = "returned"
    SCRAPPED = "scrapped"
    RECALLED = "recalled"


class TraceabilityDirection(str, Enum):
    """Direction for traceability queries."""
    UPSTREAM = "upstream"  # 1-Down: Where did this come from?
    DOWNSTREAM = "downstream"  # 1-Up: Where did this go?
    BOTH = "both"


class GenealogyLinkType(str, Enum):
    """Types of genealogy links."""
    CONSUMED = "consumed"  # Component consumed into assembly
    PRODUCED = "produced"  # Output from work order
    TRANSFERRED = "transferred"  # Moved between locations
    INSPECTED = "inspected"  # Inspection relationship
    SHIPPED = "shipped"  # Shipped to customer
    RETURNED = "returned"  # Returned from customer
    SPLIT = "split"  # Lot was split
    MERGED = "merged"  # Lots were merged


class CertificateType(str, Enum):
    """Types of certificates/evidence."""
    COA = "coa"  # Certificate of Analysis
    COC = "coc"  # Certificate of Conformance
    MSDS = "msds"  # Material Safety Data Sheet
    TEST_REPORT = "test_report"
    INSPECTION_REPORT = "inspection_report"
    CALIBRATION_CERT = "calibration_cert"
    SUPPLIER_CERT = "supplier_cert"


class RecallStatus(str, Enum):
    """Recall status states."""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class LotRecord:
    """A lot record for batch tracking."""
    id: str
    lot_number: str
    part_id: str
    part_number: str
    quantity: Decimal
    uom: str
    status: LotStatus = LotStatus.ACTIVE
    supplier_id: str | None = None
    supplier_lot_number: str | None = None
    purchase_order_id: str | None = None
    work_order_id: str | None = None
    manufacture_date: datetime | None = None
    expiry_date: datetime | None = None
    shelf_life_days: int | None = None
    received_date: datetime | None = None
    inspection_lot_id: str | None = None
    inspection_status: str | None = None  # pending, passed, failed
    location_id: str | None = None
    parent_lot_id: str | None = None  # For lot splitting
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerialRecord:
    """A serial number record for unit tracking."""
    id: str
    serial_number: str
    part_id: str
    part_number: str
    lot_id: str | None = None
    lot_number: str | None = None
    status: SerialStatus = SerialStatus.AVAILABLE
    work_order_id: str | None = None
    manufacture_date: datetime | None = None
    ship_date: datetime | None = None
    customer_id: str | None = None
    sales_order_id: str | None = None
    warranty_start: datetime | None = None
    warranty_end: datetime | None = None
    location_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenealogyLink:
    """A link in the genealogy chain."""
    id: str
    link_type: GenealogyLinkType
    source_lot_id: str | None = None
    source_serial_id: str | None = None
    target_lot_id: str | None = None
    target_serial_id: str | None = None
    quantity: Decimal = Decimal("0")
    work_order_id: str | None = None
    work_order_operation: str | None = None
    transaction_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    performed_by: str | None = None
    notes: str | None = None


@dataclass
class Certificate:
    """A certificate or evidence document attached to a lot/serial."""
    id: str
    certificate_type: CertificateType
    certificate_number: str | None = None
    lot_id: str | None = None
    serial_id: str | None = None
    supplier_id: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_hash: str | None = None
    issue_date: datetime | None = None
    expiry_date: datetime | None = None
    issuing_authority: str | None = None
    is_valid: bool = True
    verified_by: str | None = None
    verified_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecallRecord:
    """A recall record for affected lots/serials."""
    id: str
    recall_number: str
    reason: str
    affected_part_ids: list[str] = field(default_factory=list)
    affected_lot_ids: list[str] = field(default_factory=list)
    affected_serial_ids: list[str] = field(default_factory=list)
    status: RecallStatus = RecallStatus.INITIATED
    initiated_by: str | None = None
    initiated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    affected_shipments: list[str] = field(default_factory=list)
    affected_customers: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass
class WhereUsedResult:
    """Result of a where-used query."""
    source_lot_id: str | None = None
    source_serial_id: str | None = None
    affected_lots: list[str] = field(default_factory=list)
    affected_serials: list[str] = field(default_factory=list)
    affected_shipments: list[dict[str, Any]] = field(default_factory=list)
    affected_customers: list[str] = field(default_factory=list)
    affected_work_orders: list[str] = field(default_factory=list)
    total_quantity_affected: Decimal = Decimal("0")


@dataclass
class TraceabilityTree:
    """A node in the traceability tree."""
    lot_id: str | None = None
    serial_id: str | None = None
    part_number: str | None = None
    lot_number: str | None = None
    serial_number: str | None = None
    quantity: Decimal = Decimal("0")
    level: int = 0
    direction: TraceabilityDirection = TraceabilityDirection.DOWNSTREAM
    children: list["TraceabilityTree"] = field(default_factory=list)


# =============================================================================
# LOT & SERIAL TRACEABILITY SERVICE
# =============================================================================


class LotSerialTraceabilityService:
    """
    Lot & Serial Traceability (Genealogy) Service.
    
    Provides:
    - Full lot lifecycle management
    - Serial number tracking
    - Genealogy chain building
    - Where-used intelligence
    - Certificate/evidence binding
    - Recall management
    """
    
    def __init__(self):
        # Storage
        self._lots: dict[str, LotRecord] = {}
        self._serials: dict[str, SerialRecord] = {}
        self._genealogy_links: list[GenealogyLink] = []
        self._certificates: dict[str, Certificate] = {}
        self._recalls: dict[str, RecallRecord] = {}
        
        # Lot number sequence
        self._lot_sequence: int = 1
        self._serial_sequence: int = 1
    
    # =========================================================================
    # LOT MANAGEMENT
    # =========================================================================
    
    def generate_lot_number(self, prefix: str = "LOT") -> str:
        """Generate a unique lot number."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = str(self._lot_sequence).zfill(4)
        self._lot_sequence += 1
        return f"{prefix}-{date_part}-{seq}"
    
    def create_lot(
        self,
        part_id: str,
        part_number: str,
        quantity: Decimal,
        uom: str,
        lot_number: str | None = None,
        supplier_id: str | None = None,
        supplier_lot_number: str | None = None,
        purchase_order_id: str | None = None,
        work_order_id: str | None = None,
        manufacture_date: datetime | None = None,
        expiry_date: datetime | None = None,
        shelf_life_days: int | None = None,
        location_id: str | None = None,
    ) -> LotRecord:
        """Create a new lot record."""
        lot_id = str(uuid4())
        lot_number = lot_number or self.generate_lot_number()
        
        # Calculate expiry if shelf life provided
        if shelf_life_days and manufacture_date and not expiry_date:
            expiry_date = manufacture_date + timedelta(days=shelf_life_days)
        
        lot = LotRecord(
            id=lot_id,
            lot_number=lot_number,
            part_id=part_id,
            part_number=part_number,
            quantity=quantity,
            uom=uom,
            supplier_id=supplier_id,
            supplier_lot_number=supplier_lot_number,
            purchase_order_id=purchase_order_id,
            work_order_id=work_order_id,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            shelf_life_days=shelf_life_days,
            received_date=datetime.now(timezone.utc),
            location_id=location_id,
        )
        
        self._lots[lot_id] = lot
        logger.info(f"Created lot: {lot_number} for {part_number}")
        return lot
    
    def get_lot(self, lot_id: str) -> LotRecord | None:
        """Get a lot by ID."""
        return self._lots.get(lot_id)
    
    def get_lot_by_number(self, lot_number: str) -> LotRecord | None:
        """Get a lot by lot number."""
        for lot in self._lots.values():
            if lot.lot_number == lot_number:
                return lot
        return None
    
    def get_lots_by_part(self, part_id: str, status: LotStatus | None = None) -> list[LotRecord]:
        """Get all lots for a part."""
        lots = [l for l in self._lots.values() if l.part_id == part_id]
        if status:
            lots = [l for l in lots if l.status == status]
        return lots
    
    def get_lots_by_supplier(self, supplier_id: str) -> list[LotRecord]:
        """Get all lots from a supplier."""
        return [l for l in self._lots.values() if l.supplier_id == supplier_id]
    
    def update_lot_status(
        self,
        lot_id: str,
        new_status: LotStatus,
        reason: str | None = None,
    ) -> LotRecord | None:
        """Update lot status."""
        lot = self._lots.get(lot_id)
        if not lot:
            return None
        
        lot.status = new_status
        lot.updated_at = datetime.now(timezone.utc)
        return lot
    
    def update_lot_inspection(
        self,
        lot_id: str,
        inspection_lot_id: str,
        inspection_status: str,
    ) -> LotRecord | None:
        """Update lot with inspection results."""
        lot = self._lots.get(lot_id)
        if not lot:
            return None
        
        lot.inspection_lot_id = inspection_lot_id
        lot.inspection_status = inspection_status
        lot.updated_at = datetime.now(timezone.utc)
        
        # Quarantine if failed
        if inspection_status == "failed":
            lot.status = LotStatus.QUARANTINED
        
        return lot
    
    def split_lot(
        self,
        lot_id: str,
        split_quantity: Decimal,
        new_location_id: str | None = None,
        performed_by: str | None = None,
    ) -> LotRecord | None:
        """Split a lot into a new lot."""
        parent_lot = self._lots.get(lot_id)
        if not parent_lot:
            return None
        
        if split_quantity >= parent_lot.quantity:
            return None
        
        # Reduce parent quantity
        parent_lot.quantity -= split_quantity
        parent_lot.updated_at = datetime.now(timezone.utc)
        
        # Create child lot
        child_lot = self.create_lot(
            part_id=parent_lot.part_id,
            part_number=parent_lot.part_number,
            quantity=split_quantity,
            uom=parent_lot.uom,
            supplier_id=parent_lot.supplier_id,
            supplier_lot_number=parent_lot.supplier_lot_number,
            manufacture_date=parent_lot.manufacture_date,
            expiry_date=parent_lot.expiry_date,
            location_id=new_location_id or parent_lot.location_id,
        )
        child_lot.parent_lot_id = lot_id
        
        # Create genealogy link
        self._create_genealogy_link(
            link_type=GenealogyLinkType.SPLIT,
            source_lot_id=lot_id,
            target_lot_id=child_lot.id,
            quantity=split_quantity,
            performed_by=performed_by,
        )
        
        return child_lot
    
    def consume_lot(
        self,
        lot_id: str,
        quantity: Decimal,
        work_order_id: str,
        operation: str | None = None,
        target_lot_id: str | None = None,
        performed_by: str | None = None,
    ) -> bool:
        """Consume quantity from a lot into a work order."""
        lot = self._lots.get(lot_id)
        if not lot:
            return False
        
        if quantity > lot.quantity:
            return False
        
        lot.quantity -= quantity
        lot.updated_at = datetime.now(timezone.utc)
        
        if lot.quantity == Decimal("0"):
            lot.status = LotStatus.CONSUMED
        
        # Create genealogy link
        self._create_genealogy_link(
            link_type=GenealogyLinkType.CONSUMED,
            source_lot_id=lot_id,
            target_lot_id=target_lot_id,
            quantity=quantity,
            work_order_id=work_order_id,
            work_order_operation=operation,
            performed_by=performed_by,
        )
        
        return True
    
    def check_expiry(self, lot_id: str) -> dict[str, Any]:
        """Check if a lot is expired or expiring soon."""
        lot = self._lots.get(lot_id)
        if not lot:
            return {"error": "Lot not found"}
        
        now = datetime.now(timezone.utc)
        
        if not lot.expiry_date:
            return {"expired": False, "days_remaining": None}
        
        if lot.expiry_date < now:
            lot.status = LotStatus.EXPIRED
            return {"expired": True, "days_remaining": 0}
        
        days_remaining = (lot.expiry_date - now).days
        expiring_soon = days_remaining <= 30
        
        return {
            "expired": False,
            "expiring_soon": expiring_soon,
            "days_remaining": days_remaining,
            "expiry_date": lot.expiry_date.isoformat(),
        }
    
    # =========================================================================
    # SERIAL NUMBER MANAGEMENT
    # =========================================================================
    
    def generate_serial_number(self, prefix: str = "SN") -> str:
        """Generate a unique serial number."""
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = str(self._serial_sequence).zfill(6)
        self._serial_sequence += 1
        return f"{prefix}-{date_part}-{seq}"
    
    def create_serial(
        self,
        part_id: str,
        part_number: str,
        serial_number: str | None = None,
        lot_id: str | None = None,
        work_order_id: str | None = None,
        manufacture_date: datetime | None = None,
        location_id: str | None = None,
    ) -> SerialRecord:
        """Create a serial number record."""
        serial_id = str(uuid4())
        serial_number = serial_number or self.generate_serial_number()
        
        # Get lot number if lot provided
        lot_number = None
        if lot_id:
            lot = self._lots.get(lot_id)
            if lot:
                lot_number = lot.lot_number
        
        serial = SerialRecord(
            id=serial_id,
            serial_number=serial_number,
            part_id=part_id,
            part_number=part_number,
            lot_id=lot_id,
            lot_number=lot_number,
            work_order_id=work_order_id,
            manufacture_date=manufacture_date or datetime.now(timezone.utc),
            location_id=location_id,
        )
        
        self._serials[serial_id] = serial
        logger.info(f"Created serial: {serial_number} for {part_number}")
        return serial
    
    def create_serials_batch(
        self,
        part_id: str,
        part_number: str,
        quantity: int,
        prefix: str = "SN",
        lot_id: str | None = None,
        work_order_id: str | None = None,
    ) -> list[SerialRecord]:
        """Create multiple serial numbers."""
        serials = []
        for _ in range(quantity):
            serial = self.create_serial(
                part_id=part_id,
                part_number=part_number,
                lot_id=lot_id,
                work_order_id=work_order_id,
            )
            serials.append(serial)
        return serials
    
    def get_serial(self, serial_id: str) -> SerialRecord | None:
        """Get a serial by ID."""
        return self._serials.get(serial_id)
    
    def get_serial_by_number(self, serial_number: str) -> SerialRecord | None:
        """Get a serial by serial number."""
        for serial in self._serials.values():
            if serial.serial_number == serial_number:
                return serial
        return None
    
    def get_serials_by_lot(self, lot_id: str) -> list[SerialRecord]:
        """Get all serials for a lot."""
        return [s for s in self._serials.values() if s.lot_id == lot_id]
    
    def get_serials_by_part(self, part_id: str, status: SerialStatus | None = None) -> list[SerialRecord]:
        """Get all serials for a part."""
        serials = [s for s in self._serials.values() if s.part_id == part_id]
        if status:
            serials = [s for s in serials if s.status == status]
        return serials
    
    def update_serial_status(
        self,
        serial_id: str,
        new_status: SerialStatus,
    ) -> SerialRecord | None:
        """Update serial status."""
        serial = self._serials.get(serial_id)
        if not serial:
            return None
        
        serial.status = new_status
        serial.updated_at = datetime.now(timezone.utc)
        return serial
    
    def ship_serial(
        self,
        serial_id: str,
        customer_id: str,
        sales_order_id: str,
        warranty_days: int | None = None,
    ) -> SerialRecord | None:
        """Record serial shipment to customer."""
        serial = self._serials.get(serial_id)
        if not serial:
            return None
        
        now = datetime.now(timezone.utc)
        serial.status = SerialStatus.SHIPPED
        serial.ship_date = now
        serial.customer_id = customer_id
        serial.sales_order_id = sales_order_id
        serial.warranty_start = now
        
        if warranty_days:
            serial.warranty_end = now + timedelta(days=warranty_days)
        
        serial.updated_at = now
        
        # Create genealogy link
        self._create_genealogy_link(
            link_type=GenealogyLinkType.SHIPPED,
            source_serial_id=serial_id,
            notes=f"Shipped to customer {customer_id}",
        )
        
        return serial
    
    # =========================================================================
    # GENEALOGY MANAGEMENT
    # =========================================================================
    
    def _create_genealogy_link(
        self,
        link_type: GenealogyLinkType,
        source_lot_id: str | None = None,
        source_serial_id: str | None = None,
        target_lot_id: str | None = None,
        target_serial_id: str | None = None,
        quantity: Decimal = Decimal("0"),
        work_order_id: str | None = None,
        work_order_operation: str | None = None,
        performed_by: str | None = None,
        notes: str | None = None,
    ) -> GenealogyLink:
        """Create a genealogy link."""
        link = GenealogyLink(
            id=str(uuid4()),
            link_type=link_type,
            source_lot_id=source_lot_id,
            source_serial_id=source_serial_id,
            target_lot_id=target_lot_id,
            target_serial_id=target_serial_id,
            quantity=quantity,
            work_order_id=work_order_id,
            work_order_operation=work_order_operation,
            performed_by=performed_by,
            notes=notes,
        )
        self._genealogy_links.append(link)
        return link
    
    def record_production(
        self,
        work_order_id: str,
        output_lot_id: str,
        component_lots: list[dict[str, Any]],
        performed_by: str | None = None,
    ) -> list[GenealogyLink]:
        """Record production genealogy (components consumed → output produced)."""
        links = []
        
        for component in component_lots:
            link = self._create_genealogy_link(
                link_type=GenealogyLinkType.CONSUMED,
                source_lot_id=component["lot_id"],
                target_lot_id=output_lot_id,
                quantity=Decimal(str(component.get("quantity", 0))),
                work_order_id=work_order_id,
                work_order_operation=component.get("operation"),
                performed_by=performed_by,
            )
            links.append(link)
        
        # Create production link
        output_link = self._create_genealogy_link(
            link_type=GenealogyLinkType.PRODUCED,
            target_lot_id=output_lot_id,
            work_order_id=work_order_id,
            performed_by=performed_by,
        )
        links.append(output_link)
        
        return links
    
    def get_genealogy_links(
        self,
        lot_id: str | None = None,
        serial_id: str | None = None,
        link_type: GenealogyLinkType | None = None,
    ) -> list[GenealogyLink]:
        """Get genealogy links."""
        links = self._genealogy_links
        
        if lot_id:
            links = [
                l for l in links 
                if l.source_lot_id == lot_id or l.target_lot_id == lot_id
            ]
        
        if serial_id:
            links = [
                l for l in links 
                if l.source_serial_id == serial_id or l.target_serial_id == serial_id
            ]
        
        if link_type:
            links = [l for l in links if l.link_type == link_type]
        
        return links
    
    def trace_upstream(
        self,
        lot_id: str | None = None,
        serial_id: str | None = None,
        max_levels: int = 10,
    ) -> TraceabilityTree:
        """Trace upstream (1-Down): Where did this come from?"""
        root = TraceabilityTree(
            lot_id=lot_id,
            serial_id=serial_id,
            level=0,
            direction=TraceabilityDirection.UPSTREAM,
        )
        
        if lot_id:
            lot = self._lots.get(lot_id)
            if lot:
                root.part_number = lot.part_number
                root.lot_number = lot.lot_number
                root.quantity = lot.quantity
        elif serial_id:
            serial = self._serials.get(serial_id)
            if serial:
                root.part_number = serial.part_number
                root.serial_number = serial.serial_number
                root.quantity = Decimal("1")
        
        self._build_upstream_tree(root, max_levels)
        return root
    
    def _build_upstream_tree(self, node: TraceabilityTree, max_levels: int) -> None:
        """Recursively build upstream tree."""
        if node.level >= max_levels:
            return
        
        # Find links where this is the target
        links = [
            l for l in self._genealogy_links
            if (node.lot_id and l.target_lot_id == node.lot_id) or
               (node.serial_id and l.target_serial_id == node.serial_id)
        ]
        
        for link in links:
            if link.source_lot_id:
                lot = self._lots.get(link.source_lot_id)
                if lot:
                    child = TraceabilityTree(
                        lot_id=link.source_lot_id,
                        part_number=lot.part_number,
                        lot_number=lot.lot_number,
                        quantity=link.quantity,
                        level=node.level + 1,
                        direction=TraceabilityDirection.UPSTREAM,
                    )
                    node.children.append(child)
                    self._build_upstream_tree(child, max_levels)
            
            if link.source_serial_id:
                serial = self._serials.get(link.source_serial_id)
                if serial:
                    child = TraceabilityTree(
                        serial_id=link.source_serial_id,
                        part_number=serial.part_number,
                        serial_number=serial.serial_number,
                        quantity=Decimal("1"),
                        level=node.level + 1,
                        direction=TraceabilityDirection.UPSTREAM,
                    )
                    node.children.append(child)
                    self._build_upstream_tree(child, max_levels)
    
    def trace_downstream(
        self,
        lot_id: str | None = None,
        serial_id: str | None = None,
        max_levels: int = 10,
    ) -> TraceabilityTree:
        """Trace downstream (1-Up): Where did this go?"""
        root = TraceabilityTree(
            lot_id=lot_id,
            serial_id=serial_id,
            level=0,
            direction=TraceabilityDirection.DOWNSTREAM,
        )
        
        if lot_id:
            lot = self._lots.get(lot_id)
            if lot:
                root.part_number = lot.part_number
                root.lot_number = lot.lot_number
                root.quantity = lot.quantity
        elif serial_id:
            serial = self._serials.get(serial_id)
            if serial:
                root.part_number = serial.part_number
                root.serial_number = serial.serial_number
                root.quantity = Decimal("1")
        
        self._build_downstream_tree(root, max_levels)
        return root
    
    def _build_downstream_tree(self, node: TraceabilityTree, max_levels: int) -> None:
        """Recursively build downstream tree."""
        if node.level >= max_levels:
            return
        
        # Find links where this is the source
        links = [
            l for l in self._genealogy_links
            if (node.lot_id and l.source_lot_id == node.lot_id) or
               (node.serial_id and l.source_serial_id == node.serial_id)
        ]
        
        for link in links:
            if link.target_lot_id:
                lot = self._lots.get(link.target_lot_id)
                if lot:
                    child = TraceabilityTree(
                        lot_id=link.target_lot_id,
                        part_number=lot.part_number,
                        lot_number=lot.lot_number,
                        quantity=link.quantity,
                        level=node.level + 1,
                        direction=TraceabilityDirection.DOWNSTREAM,
                    )
                    node.children.append(child)
                    self._build_downstream_tree(child, max_levels)
            
            if link.target_serial_id:
                serial = self._serials.get(link.target_serial_id)
                if serial:
                    child = TraceabilityTree(
                        serial_id=link.target_serial_id,
                        part_number=serial.part_number,
                        serial_number=serial.serial_number,
                        quantity=Decimal("1"),
                        level=node.level + 1,
                        direction=TraceabilityDirection.DOWNSTREAM,
                    )
                    node.children.append(child)
                    self._build_downstream_tree(child, max_levels)
    
    # =========================================================================
    # WHERE-USED INTELLIGENCE
    # =========================================================================
    
    def where_used(
        self,
        lot_id: str | None = None,
        serial_id: str | None = None,
    ) -> WhereUsedResult:
        """
        Find all affected items if a lot/serial is found defective.
        Supports recall readiness.
        """
        result = WhereUsedResult(
            source_lot_id=lot_id,
            source_serial_id=serial_id,
        )
        
        # Trace downstream to find all affected items
        tree = self.trace_downstream(lot_id=lot_id, serial_id=serial_id, max_levels=20)
        
        # Collect affected items
        self._collect_affected_items(tree, result)
        
        # Find affected shipments
        for serial_id_affected in result.affected_serials:
            serial = self._serials.get(serial_id_affected)
            if serial and serial.status == SerialStatus.SHIPPED:
                result.affected_shipments.append({
                    "serial_number": serial.serial_number,
                    "customer_id": serial.customer_id,
                    "sales_order_id": serial.sales_order_id,
                    "ship_date": serial.ship_date.isoformat() if serial.ship_date else None,
                })
                if serial.customer_id and serial.customer_id not in result.affected_customers:
                    result.affected_customers.append(serial.customer_id)
        
        # Find affected lots that were shipped
        for lot_id_affected in result.affected_lots:
            lot = self._lots.get(lot_id_affected)
            if lot and lot.status == LotStatus.SHIPPED:
                # Would query shipment data in real implementation
                pass
        
        return result
    
    def _collect_affected_items(self, node: TraceabilityTree, result: WhereUsedResult) -> None:
        """Recursively collect affected items from tree."""
        if node.lot_id and node.lot_id not in result.affected_lots:
            result.affected_lots.append(node.lot_id)
            result.total_quantity_affected += node.quantity
        
        if node.serial_id and node.serial_id not in result.affected_serials:
            result.affected_serials.append(node.serial_id)
            result.total_quantity_affected += Decimal("1")
        
        for child in node.children:
            self._collect_affected_items(child, result)
    
    # =========================================================================
    # CERTIFICATE / EVIDENCE BINDING
    # =========================================================================
    
    def attach_certificate(
        self,
        certificate_type: CertificateType,
        lot_id: str | None = None,
        serial_id: str | None = None,
        supplier_id: str | None = None,
        certificate_number: str | None = None,
        file_path: str | None = None,
        file_name: str | None = None,
        file_hash: str | None = None,
        issue_date: datetime | None = None,
        expiry_date: datetime | None = None,
        issuing_authority: str | None = None,
    ) -> Certificate:
        """Attach a certificate/evidence to a lot or serial."""
        cert_id = str(uuid4())
        
        cert = Certificate(
            id=cert_id,
            certificate_type=certificate_type,
            certificate_number=certificate_number,
            lot_id=lot_id,
            serial_id=serial_id,
            supplier_id=supplier_id,
            file_path=file_path,
            file_name=file_name,
            file_hash=file_hash,
            issue_date=issue_date,
            expiry_date=expiry_date,
            issuing_authority=issuing_authority,
        )
        
        self._certificates[cert_id] = cert
        logger.info(f"Attached {certificate_type.value} to lot/serial")
        return cert
    
    def get_certificates(
        self,
        lot_id: str | None = None,
        serial_id: str | None = None,
        certificate_type: CertificateType | None = None,
    ) -> list[Certificate]:
        """Get certificates for a lot or serial."""
        certs = list(self._certificates.values())
        
        if lot_id:
            certs = [c for c in certs if c.lot_id == lot_id]
        
        if serial_id:
            certs = [c for c in certs if c.serial_id == serial_id]
        
        if certificate_type:
            certs = [c for c in certs if c.certificate_type == certificate_type]
        
        return certs
    
    def verify_certificate(
        self,
        certificate_id: str,
        verified_by: str,
    ) -> Certificate | None:
        """Mark a certificate as verified."""
        cert = self._certificates.get(certificate_id)
        if not cert:
            return None
        
        cert.verified_by = verified_by
        cert.verified_at = datetime.now(timezone.utc)
        return cert
    
    def check_certificate_validity(self, certificate_id: str) -> dict[str, Any]:
        """Check if a certificate is valid (not expired)."""
        cert = self._certificates.get(certificate_id)
        if not cert:
            return {"error": "Certificate not found"}
        
        now = datetime.now(timezone.utc)
        
        if not cert.expiry_date:
            return {"valid": cert.is_valid, "expired": False}
        
        if cert.expiry_date < now:
            cert.is_valid = False
            return {"valid": False, "expired": True}
        
        days_remaining = (cert.expiry_date - now).days
        return {
            "valid": cert.is_valid,
            "expired": False,
            "days_remaining": days_remaining,
        }
    
    # =========================================================================
    # RECALL MANAGEMENT
    # =========================================================================
    
    def initiate_recall(
        self,
        recall_number: str,
        reason: str,
        affected_lot_ids: list[str] | None = None,
        affected_serial_ids: list[str] | None = None,
        initiated_by: str | None = None,
    ) -> RecallRecord:
        """Initiate a recall for affected lots/serials."""
        recall_id = str(uuid4())
        
        recall = RecallRecord(
            id=recall_id,
            recall_number=recall_number,
            reason=reason,
            affected_lot_ids=affected_lot_ids or [],
            affected_serial_ids=affected_serial_ids or [],
            initiated_by=initiated_by,
        )
        
        # Use where-used to find all downstream affected items
        for lot_id in recall.affected_lot_ids:
            result = self.where_used(lot_id=lot_id)
            for affected_lot in result.affected_lots:
                if affected_lot not in recall.affected_lot_ids:
                    recall.affected_lot_ids.append(affected_lot)
            for affected_serial in result.affected_serials:
                if affected_serial not in recall.affected_serial_ids:
                    recall.affected_serial_ids.append(affected_serial)
            recall.affected_shipments.extend(
                [s["serial_number"] for s in result.affected_shipments]
            )
            for customer in result.affected_customers:
                if customer not in recall.affected_customers:
                    recall.affected_customers.append(customer)
        
        # Update status of affected lots/serials
        for lot_id in recall.affected_lot_ids:
            self.update_lot_status(lot_id, LotStatus.RECALLED)
        
        for serial_id in recall.affected_serial_ids:
            self.update_serial_status(serial_id, SerialStatus.RECALLED)
        
        # Collect affected parts
        affected_parts = set()
        for lot_id in recall.affected_lot_ids:
            lot = self._lots.get(lot_id)
            if lot:
                affected_parts.add(lot.part_id)
        recall.affected_part_ids = list(affected_parts)
        
        self._recalls[recall_id] = recall
        logger.info(f"Initiated recall: {recall_number}")
        return recall
    
    def get_recall(self, recall_id: str) -> RecallRecord | None:
        """Get a recall by ID."""
        return self._recalls.get(recall_id)
    
    def get_recalls(self, status: RecallStatus | None = None) -> list[RecallRecord]:
        """Get all recalls, optionally filtered by status."""
        recalls = list(self._recalls.values())
        if status:
            recalls = [r for r in recalls if r.status == status]
        return recalls
    
    def complete_recall(
        self,
        recall_id: str,
        notes: str | None = None,
    ) -> RecallRecord | None:
        """Mark a recall as completed."""
        recall = self._recalls.get(recall_id)
        if not recall:
            return None
        
        recall.status = RecallStatus.COMPLETED
        recall.completed_at = datetime.now(timezone.utc)
        recall.notes = notes
        return recall
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> dict[str, Any]:
        """Get traceability statistics."""
        lots = list(self._lots.values())
        serials = list(self._serials.values())
        
        return {
            "total_lots": len(lots),
            "total_serials": len(serials),
            "total_genealogy_links": len(self._genealogy_links),
            "total_certificates": len(self._certificates),
            "active_recalls": len([r for r in self._recalls.values() if r.status != RecallStatus.COMPLETED]),
            "lots_by_status": {
                status.value: len([l for l in lots if l.status == status])
                for status in LotStatus
            },
            "serials_by_status": {
                status.value: len([s for s in serials if s.status == status])
                for status in SerialStatus
            },
            "certificates_by_type": {
                cert_type.value: len([c for c in self._certificates.values() if c.certificate_type == cert_type])
                for cert_type in CertificateType
            },
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_lot_serial_service() -> LotSerialTraceabilityService:
    """Factory function to create a Lot/Serial Traceability service."""
    return LotSerialTraceabilityService()
