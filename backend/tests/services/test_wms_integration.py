"""
Tests for WMS Integration Service.

Tests:
- Zone and location management
- Inventory tracking and status
- Transactions (transfer, issue, pick, putaway)
- Cycle counting
- Goods receipt and shipping
- ERP synchronization
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sensei.services.wms_integration import (
    # Enums
    LocationType,
    InventoryStatus,
    TransactionType,
    PickStrategy,
    CycleCountPriority,
    ShipmentStatus,
    # Data models
    WarehouseLocation,
    WarehouseZone,
    InventoryRecord,
    InventoryTransaction,
    PickTask,
    PutawayTask,
    CycleCount,
    GoodsReceipt,
    GoodsReceiptLine,
    Shipment,
    PackingListLine,
    StockLevel,
    # Service
    WMSIntegrationService,
    create_wms_service,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def service():
    """Create a WMS Integration service."""
    return create_wms_service()


@pytest.fixture
def sample_zone(service):
    """Create a sample zone."""
    return service.create_zone(
        code="ZONE-A",
        name="Storage Zone A",
        zone_type=LocationType.STORAGE,
    )


@pytest.fixture
def sample_location(service, sample_zone):
    """Create a sample location."""
    return service.create_location(
        code="A-01-01-01",
        name="Aisle A, Rack 1, Level 1, Bin 1",
        location_type=LocationType.STORAGE,
        zone_id=sample_zone.id,
        aisle="A",
        rack="01",
        level="01",
        bin="01",
        capacity=Decimal("100"),
    )


@pytest.fixture
def sample_inventory(service, sample_location):
    """Create a sample inventory record."""
    return service.create_inventory_record(
        part_id="PART-001",
        part_number="PN-001",
        location_id=sample_location.id,
        quantity=Decimal("50"),
        uom="EA",
        lot_number="LOT-2026-001",
    )


# =============================================================================
# TEST ENUMS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_location_type_values(self):
        """Test location type enum values."""
        assert LocationType.RECEIVING.value == "receiving"
        assert LocationType.STORAGE.value == "storage"
        assert LocationType.QUARANTINE.value == "quarantine"
        assert LocationType.MRB.value == "mrb"
        assert LocationType.WIP_SUPERMARKET.value == "wip_supermarket"
    
    def test_inventory_status_values(self):
        """Test inventory status enum values."""
        assert InventoryStatus.AVAILABLE.value == "available"
        assert InventoryStatus.QUARANTINED.value == "quarantined"
        assert InventoryStatus.RESERVED.value == "reserved"
        assert InventoryStatus.IN_TRANSIT.value == "in_transit"
    
    def test_transaction_type_values(self):
        """Test transaction type enum values."""
        assert TransactionType.RECEIPT.value == "receipt"
        assert TransactionType.PUTAWAY.value == "putaway"
        assert TransactionType.PICK.value == "pick"
        assert TransactionType.ISSUE.value == "issue"
        assert TransactionType.TRANSFER.value == "transfer"
    
    def test_pick_strategy_values(self):
        """Test pick strategy enum values."""
        assert PickStrategy.FIFO.value == "fifo"
        assert PickStrategy.FEFO.value == "fefo"
        assert PickStrategy.LIFO.value == "lifo"
    
    def test_shipment_status_values(self):
        """Test shipment status enum values."""
        assert ShipmentStatus.PENDING.value == "pending"
        assert ShipmentStatus.SHIPPED.value == "shipped"
        assert ShipmentStatus.DELIVERED.value == "delivered"


# =============================================================================
# TEST DATA MODELS
# =============================================================================


class TestDataModels:
    """Test data model classes."""
    
    def test_warehouse_location_creation(self):
        """Test WarehouseLocation creation."""
        location = WarehouseLocation(
            id="loc-001",
            code="A-01-01",
            name="Test Location",
            location_type=LocationType.STORAGE,
        )
        
        assert location.id == "loc-001"
        assert location.code == "A-01-01"
        assert location.is_active is True
    
    def test_inventory_record_creation(self):
        """Test InventoryRecord creation."""
        record = InventoryRecord(
            id="inv-001",
            part_id="PART-001",
            part_number="PN-001",
            location_id="loc-001",
            quantity=Decimal("100"),
            uom="EA",
        )
        
        assert record.id == "inv-001"
        assert record.quantity == Decimal("100")
        assert record.status == InventoryStatus.AVAILABLE
    
    def test_inventory_transaction_creation(self):
        """Test InventoryTransaction creation."""
        transaction = InventoryTransaction(
            id="txn-001",
            transaction_type=TransactionType.TRANSFER,
            part_id="PART-001",
            part_number="PN-001",
            quantity=Decimal("10"),
            uom="EA",
        )
        
        assert transaction.id == "txn-001"
        assert transaction.erp_synced is False
    
    def test_pick_task_creation(self):
        """Test PickTask creation."""
        task = PickTask(
            id="pick-001",
            order_id="SO-001",
            order_type="sales_order",
            part_id="PART-001",
            part_number="PN-001",
            required_quantity=Decimal("10"),
        )
        
        assert task.id == "pick-001"
        assert task.status == "pending"
        assert task.picked_quantity == Decimal("0")
    
    def test_cycle_count_creation(self):
        """Test CycleCount creation."""
        count = CycleCount(
            id="cc-001",
            location_id="loc-001",
            system_quantity=Decimal("50"),
        )
        
        assert count.id == "cc-001"
        assert count.status == "pending"
        assert count.priority == CycleCountPriority.MEDIUM


# =============================================================================
# TEST ZONE MANAGEMENT
# =============================================================================


class TestZoneManagement:
    """Test zone management operations."""
    
    def test_create_zone(self, service):
        """Test creating a zone."""
        zone = service.create_zone(
            code="ZONE-A",
            name="Storage Zone A",
            zone_type=LocationType.STORAGE,
        )
        
        assert zone is not None
        assert zone.code == "ZONE-A"
        assert zone.zone_type == LocationType.STORAGE
    
    def test_get_zone(self, service, sample_zone):
        """Test getting a zone by ID."""
        retrieved = service.get_zone(sample_zone.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_zone.id
    
    def test_get_zones(self, service):
        """Test getting all zones."""
        service.create_zone("ZONE-A", "Zone A", LocationType.STORAGE)
        service.create_zone("ZONE-B", "Zone B", LocationType.STORAGE)
        service.create_zone("ZONE-Q", "Quarantine", LocationType.QUARANTINE)
        
        all_zones = service.get_zones()
        storage_zones = service.get_zones(zone_type=LocationType.STORAGE)
        
        assert len(all_zones) == 3
        assert len(storage_zones) == 2


# =============================================================================
# TEST LOCATION MANAGEMENT
# =============================================================================


class TestLocationManagement:
    """Test location management operations."""
    
    def test_create_location(self, service):
        """Test creating a location."""
        location = service.create_location(
            code="A-01-01-01",
            name="Test Location",
            location_type=LocationType.STORAGE,
            aisle="A",
            rack="01",
            level="01",
            bin="01",
        )
        
        assert location is not None
        assert location.code == "A-01-01-01"
        assert location.aisle == "A"
    
    def test_get_location(self, service, sample_location):
        """Test getting a location by ID."""
        retrieved = service.get_location(sample_location.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_location.id
    
    def test_get_location_by_code(self, service, sample_location):
        """Test getting a location by code."""
        retrieved = service.get_location_by_code("A-01-01-01")
        
        assert retrieved is not None
        assert retrieved.id == sample_location.id
    
    def test_get_locations_by_zone(self, service, sample_zone):
        """Test getting locations by zone."""
        service.create_location("LOC-1", "Location 1", LocationType.STORAGE, zone_id=sample_zone.id)
        service.create_location("LOC-2", "Location 2", LocationType.STORAGE, zone_id=sample_zone.id)
        
        locations = service.get_locations(zone_id=sample_zone.id)
        
        assert len(locations) == 2
    
    def test_get_locations_by_type(self, service):
        """Test getting locations by type."""
        service.create_location("STORAGE-1", "Storage 1", LocationType.STORAGE)
        service.create_location("QUARANTINE-1", "Quarantine 1", LocationType.QUARANTINE)
        
        storage = service.get_locations(location_type=LocationType.STORAGE)
        quarantine = service.get_locations(location_type=LocationType.QUARANTINE)
        
        assert len(storage) == 1
        assert len(quarantine) == 1
    
    def test_update_location(self, service, sample_location):
        """Test updating a location."""
        updated = service.update_location(
            sample_location.id,
            capacity=Decimal("200"),
            is_active=False,
        )
        
        assert updated is not None
        assert updated.capacity == Decimal("200")
        assert updated.is_active is False


# =============================================================================
# TEST INVENTORY MANAGEMENT
# =============================================================================


class TestInventoryManagement:
    """Test inventory management operations."""
    
    def test_create_inventory_record(self, service, sample_location):
        """Test creating an inventory record."""
        record = service.create_inventory_record(
            part_id="PART-001",
            part_number="PN-001",
            location_id=sample_location.id,
            quantity=Decimal("100"),
            uom="EA",
            lot_number="LOT-001",
        )
        
        assert record is not None
        assert record.quantity == Decimal("100")
        assert record.lot_number == "LOT-001"
    
    def test_get_inventory_record(self, service, sample_inventory):
        """Test getting an inventory record by ID."""
        retrieved = service.get_inventory_record(sample_inventory.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_inventory.id
    
    def test_get_inventory_by_part(self, service, sample_inventory):
        """Test getting inventory by part ID."""
        records = service.get_inventory_by_part("PART-001")
        
        assert len(records) == 1
        assert records[0].id == sample_inventory.id
    
    def test_get_inventory_by_location(self, service, sample_inventory, sample_location):
        """Test getting inventory by location."""
        records = service.get_inventory_by_location(sample_location.id)
        
        assert len(records) == 1
    
    def test_get_inventory_by_lot(self, service, sample_inventory):
        """Test getting inventory by lot number."""
        records = service.get_inventory_by_lot("LOT-2026-001")
        
        assert len(records) == 1
    
    def test_get_stock_level(self, service, sample_location):
        """Test getting aggregated stock level."""
        service.create_inventory_record("PART-001", "PN-001", sample_location.id, Decimal("50"), "EA")
        service.create_inventory_record("PART-001", "PN-001", sample_location.id, Decimal("30"), "EA")
        
        stock = service.get_stock_level("PART-001")
        
        assert stock is not None
        assert stock.total_quantity == Decimal("80")
    
    def test_update_inventory_status(self, service, sample_inventory):
        """Test updating inventory status."""
        updated = service.update_inventory_status(
            sample_inventory.id,
            InventoryStatus.QUARANTINED,
            reason="Quality hold",
            performed_by="qa_user",
        )
        
        assert updated is not None
        assert updated.status == InventoryStatus.QUARANTINED
    
    def test_reserve_inventory(self, service, sample_inventory):
        """Test reserving inventory."""
        result = service.reserve_inventory(
            sample_inventory.id,
            Decimal("20"),
            "sales_order",
            "SO-001",
        )
        
        assert result is True
        assert sample_inventory.reserved_quantity == Decimal("20")
    
    def test_reserve_inventory_insufficient(self, service, sample_inventory):
        """Test reserving more than available."""
        result = service.reserve_inventory(
            sample_inventory.id,
            Decimal("100"),  # More than 50 available
            "sales_order",
            "SO-001",
        )
        
        assert result is False
    
    def test_release_reservation(self, service, sample_inventory):
        """Test releasing a reservation."""
        service.reserve_inventory(sample_inventory.id, Decimal("20"), "so", "SO-001")
        
        result = service.release_reservation(sample_inventory.id, Decimal("20"))
        
        assert result is True
        assert sample_inventory.reserved_quantity == Decimal("0")


# =============================================================================
# TEST TRANSACTIONS
# =============================================================================


class TestTransactions:
    """Test inventory transaction operations."""
    
    def test_transfer_inventory(self, service, sample_location, sample_inventory):
        """Test transferring inventory between locations."""
        # Create destination location
        dest = service.create_location(
            "DEST-01", "Destination", LocationType.STORAGE
        )
        
        transaction = service.transfer_inventory(
            from_location_id=sample_location.id,
            to_location_id=dest.id,
            part_id="PART-001",
            quantity=Decimal("10"),
            performed_by="operator",
        )
        
        assert transaction is not None
        assert transaction.transaction_type == TransactionType.TRANSFER
        assert transaction.quantity == Decimal("10")
    
    def test_transfer_inventory_insufficient(self, service, sample_location, sample_inventory):
        """Test transfer with insufficient quantity."""
        dest = service.create_location("DEST-01", "Destination", LocationType.STORAGE)
        
        transaction = service.transfer_inventory(
            from_location_id=sample_location.id,
            to_location_id=dest.id,
            part_id="PART-001",
            quantity=Decimal("100"),  # More than 50 available
            performed_by="operator",
        )
        
        assert transaction is None
    
    def test_issue_to_work_order(self, service, sample_location, sample_inventory):
        """Test issuing inventory to a work order."""
        transaction = service.issue_to_work_order(
            work_order_id="WO-001",
            part_id="PART-001",
            quantity=Decimal("10"),
            performed_by="operator",
        )
        
        assert transaction is not None
        assert transaction.transaction_type == TransactionType.ISSUE
        assert transaction.reference_type == "work_order"
        assert transaction.reference_id == "WO-001"
    
    def test_receive_from_production(self, service, sample_location):
        """Test receiving finished goods from production."""
        record = service.receive_from_production(
            work_order_id="WO-001",
            part_id="FG-001",
            part_number="FG-PN-001",
            quantity=Decimal("100"),
            uom="EA",
            to_location_id=sample_location.id,
            lot_number="FG-LOT-001",
            performed_by="operator",
        )
        
        assert record is not None
        assert record.quantity == Decimal("100")
        assert record.lot_number == "FG-LOT-001"
    
    def test_adjust_inventory(self, service, sample_inventory):
        """Test adjusting inventory quantity."""
        transaction = service.adjust_inventory(
            record_id=sample_inventory.id,
            new_quantity=Decimal("45"),
            reason_code="damage",
            performed_by="supervisor",
            notes="5 units damaged",
        )
        
        assert transaction is not None
        assert transaction.quantity == Decimal("-5")  # Adjustment delta
        assert sample_inventory.quantity == Decimal("45")
    
    def test_scrap_inventory(self, service, sample_inventory):
        """Test scrapping inventory."""
        transaction = service.scrap_inventory(
            record_id=sample_inventory.id,
            quantity=Decimal("5"),
            reason_code="defective",
            performed_by="qa",
            notes="Failed inspection",
        )
        
        assert transaction is not None
        assert transaction.transaction_type == TransactionType.SCRAP
        assert sample_inventory.quantity == Decimal("45")
    
    def test_get_transactions(self, service, sample_location, sample_inventory):
        """Test getting transaction history."""
        dest = service.create_location("DEST-01", "Destination", LocationType.STORAGE)
        service.transfer_inventory(sample_location.id, dest.id, "PART-001", Decimal("10"), performed_by="op")
        service.transfer_inventory(sample_location.id, dest.id, "PART-001", Decimal("5"), performed_by="op")
        
        transactions = service.get_transactions(part_id="PART-001")
        
        assert len(transactions) == 2
    
    def test_get_transactions_by_type(self, service, sample_inventory):
        """Test getting transactions by type."""
        service.adjust_inventory(sample_inventory.id, Decimal("45"), "count", "user")
        service.scrap_inventory(sample_inventory.id, Decimal("5"), "damage", "user")
        
        adjustments = service.get_transactions(transaction_type=TransactionType.ADJUSTMENT)
        scraps = service.get_transactions(transaction_type=TransactionType.SCRAP)
        
        assert len(adjustments) == 1
        assert len(scraps) == 1


# =============================================================================
# TEST PICKING
# =============================================================================


class TestPicking:
    """Test picking operations."""
    
    def test_create_pick_task(self, service, sample_inventory):
        """Test creating a pick task."""
        task = service.create_pick_task(
            order_id="SO-001",
            order_type="sales_order",
            part_id="PART-001",
            part_number="PN-001",
            required_quantity=Decimal("10"),
            uom="EA",
        )
        
        assert task is not None
        assert task.order_id == "SO-001"
        assert task.required_quantity == Decimal("10")
        assert task.status == "pending"
    
    def test_create_pick_task_no_inventory(self, service):
        """Test creating a pick task with no inventory."""
        task = service.create_pick_task(
            order_id="SO-001",
            order_type="sales_order",
            part_id="NONEXISTENT",
            part_number="PN-XXX",
            required_quantity=Decimal("10"),
            uom="EA",
        )
        
        assert task is None
    
    def test_complete_pick_task(self, service, sample_inventory):
        """Test completing a pick task."""
        task = service.create_pick_task(
            order_id="SO-001",
            order_type="sales_order",
            part_id="PART-001",
            part_number="PN-001",
            required_quantity=Decimal("10"),
            uom="EA",
        )
        
        completed = service.complete_pick_task(
            task_id=task.id,
            picked_quantity=Decimal("10"),
            performed_by="picker",
        )
        
        assert completed is not None
        assert completed.status == "completed"
        assert completed.picked_quantity == Decimal("10")
    
    def test_get_pick_tasks(self, service, sample_inventory):
        """Test getting pick tasks."""
        service.create_pick_task("SO-001", "sales_order", "PART-001", "PN-001", Decimal("10"), "EA")
        service.create_pick_task("SO-002", "sales_order", "PART-001", "PN-001", Decimal("5"), "EA")
        
        tasks = service.get_pick_tasks()
        pending = service.get_pick_tasks(status="pending")
        
        assert len(tasks) == 2
        assert len(pending) == 2
    
    def test_fifo_picking(self, service, sample_location):
        """Test FIFO picking strategy."""
        # Create older inventory first
        old_inv = service.create_inventory_record(
            "PART-001", "PN-001", sample_location.id, Decimal("20"), "EA", lot_number="LOT-OLD"
        )
        old_inv.receipt_date = datetime.now(timezone.utc) - timedelta(days=10)
        
        # Create newer inventory
        new_inv = service.create_inventory_record(
            "PART-001", "PN-001", sample_location.id, Decimal("20"), "EA", lot_number="LOT-NEW"
        )
        new_inv.receipt_date = datetime.now(timezone.utc)
        
        # Pick should select older lot
        task = service.create_pick_task(
            "SO-001", "sales_order", "PART-001", "PN-001", Decimal("10"), "EA",
            strategy=PickStrategy.FIFO
        )
        
        assert task is not None
        assert task.lot_number == "LOT-OLD"


# =============================================================================
# TEST PUTAWAY
# =============================================================================


class TestPutaway:
    """Test putaway operations."""
    
    def test_suggest_putaway_location(self, service, sample_location, sample_inventory):
        """Test putaway location suggestion."""
        suggested = service.suggest_putaway_location(
            part_id="PART-001",
            quantity=Decimal("10"),
        )
        
        # Should suggest existing location with same part
        assert suggested is not None
        assert suggested.id == sample_location.id
    
    def test_suggest_putaway_new_part(self, service, sample_location):
        """Test putaway location for new part."""
        suggested = service.suggest_putaway_location(
            part_id="NEW-PART",
            quantity=Decimal("10"),
        )
        
        assert suggested is not None
    
    def test_create_putaway_task(self, service, sample_location):
        """Test creating a putaway task."""
        receiving = service.create_location("RECV-01", "Receiving Dock", LocationType.RECEIVING)
        
        task = service.create_putaway_task(
            receipt_id="GR-001",
            part_id="PART-001",
            part_number="PN-001",
            quantity=Decimal("50"),
            uom="EA",
            from_location_id=receiving.id,
        )
        
        assert task is not None
        assert task.status == "pending"
    
    def test_complete_putaway_task(self, service, sample_location):
        """Test completing a putaway task."""
        receiving = service.create_location("RECV-01", "Receiving Dock", LocationType.RECEIVING)
        
        task = service.create_putaway_task(
            receipt_id="GR-001",
            part_id="PART-001",
            part_number="PN-001",
            quantity=Decimal("50"),
            uom="EA",
            from_location_id=receiving.id,
        )
        
        completed = service.complete_putaway_task(
            task_id=task.id,
            actual_location_id=sample_location.id,
            performed_by="operator",
        )
        
        assert completed is not None
        assert completed.status == "completed"
        assert completed.actual_location_id == sample_location.id


# =============================================================================
# TEST CYCLE COUNTING
# =============================================================================


class TestCycleCounting:
    """Test cycle counting operations."""
    
    def test_create_cycle_count(self, service, sample_location, sample_inventory):
        """Test creating a cycle count."""
        count = service.create_cycle_count(
            location_id=sample_location.id,
            priority=CycleCountPriority.HIGH,
        )
        
        assert count is not None
        assert count.status == "pending"
        assert count.system_quantity == Decimal("50")
    
    def test_record_cycle_count(self, service, sample_location, sample_inventory):
        """Test recording a cycle count result."""
        count = service.create_cycle_count(sample_location.id)
        
        recorded = service.record_cycle_count(
            count_id=count.id,
            counted_quantity=Decimal("48"),
            counted_by="counter",
        )
        
        assert recorded is not None
        assert recorded.status == "counted"
        assert recorded.variance == Decimal("-2")
    
    def test_verify_cycle_count(self, service, sample_location, sample_inventory):
        """Test verifying a cycle count."""
        count = service.create_cycle_count(sample_location.id)
        service.record_cycle_count(count.id, Decimal("50"), "counter")
        
        verified = service.verify_cycle_count(
            count_id=count.id,
            verified_by="supervisor",
        )
        
        assert verified is not None
        assert verified.status == "verified"
    
    def test_verify_cycle_count_with_adjustment(self, service, sample_location, sample_inventory):
        """Test verifying a cycle count with adjustment."""
        count = service.create_cycle_count(sample_location.id, part_id="PART-001")
        service.record_cycle_count(count.id, Decimal("45"), "counter")
        
        verified = service.verify_cycle_count(
            count_id=count.id,
            verified_by="supervisor",
            apply_adjustment=True,
            adjustment_reason="Discrepancy resolved",
        )
        
        assert verified is not None
        assert verified.status == "adjusted"
        
        # Check inventory was adjusted
        assert sample_inventory.quantity == Decimal("45")
    
    def test_get_cycle_counts(self, service, sample_location, sample_inventory):
        """Test getting cycle counts."""
        service.create_cycle_count(sample_location.id, priority=CycleCountPriority.HIGH)
        service.create_cycle_count(sample_location.id, priority=CycleCountPriority.LOW)
        
        all_counts = service.get_cycle_counts()
        high_priority = service.get_cycle_counts(priority=CycleCountPriority.HIGH)
        
        assert len(all_counts) == 2
        assert len(high_priority) == 1
    
    def test_generate_smart_cycle_counts(self, service, sample_location, sample_inventory):
        """Test generating smart cycle count suggestions."""
        # Create some transactions to build activity history
        dest = service.create_location("DEST-01", "Destination", LocationType.STORAGE)
        for _ in range(5):
            service.transfer_inventory(
                sample_location.id, dest.id, "PART-001", Decimal("1"), performed_by="op"
            )
        
        counts = service.generate_smart_cycle_counts(max_counts=5)
        
        assert len(counts) >= 1


# =============================================================================
# TEST GOODS RECEIPT
# =============================================================================


class TestGoodsReceipt:
    """Test goods receipt operations."""
    
    def test_create_goods_receipt(self, service):
        """Test creating a goods receipt."""
        receipt = service.create_goods_receipt(
            receipt_number="GR-001",
            supplier_id="SUPP-001",
            purchase_order_id="PO-001",
            received_by="receiver",
        )
        
        assert receipt is not None
        assert receipt.receipt_number == "GR-001"
        assert receipt.status == "pending"
    
    def test_add_goods_receipt_line(self, service):
        """Test adding a line to a goods receipt."""
        receipt = service.create_goods_receipt("GR-001")
        
        line = service.add_goods_receipt_line(
            receipt_id=receipt.id,
            part_id="PART-001",
            part_number="PN-001",
            expected_quantity=Decimal("100"),
            received_quantity=Decimal("100"),
            uom="EA",
            lot_number="LOT-001",
        )
        
        assert line is not None
        assert line.received_quantity == Decimal("100")
    
    def test_complete_goods_receipt(self, service):
        """Test completing a goods receipt."""
        receipt = service.create_goods_receipt("GR-001")
        service.add_goods_receipt_line(
            receipt.id, "PART-001", "PN-001", Decimal("100"), Decimal("100"), "EA"
        )
        
        completed = service.complete_goods_receipt(receipt.id)
        
        assert completed is not None
        assert completed.status == "completed"
    
    def test_get_goods_receipt(self, service):
        """Test getting a goods receipt."""
        receipt = service.create_goods_receipt("GR-001")
        
        retrieved = service.get_goods_receipt(receipt.id)
        
        assert retrieved is not None
        assert retrieved.id == receipt.id
    
    def test_get_goods_receipt_lines(self, service):
        """Test getting goods receipt lines."""
        receipt = service.create_goods_receipt("GR-001")
        service.add_goods_receipt_line(receipt.id, "PART-001", "PN-001", Decimal("50"), Decimal("50"), "EA")
        service.add_goods_receipt_line(receipt.id, "PART-002", "PN-002", Decimal("30"), Decimal("30"), "EA")
        
        lines = service.get_goods_receipt_lines(receipt.id)
        
        assert len(lines) == 2


# =============================================================================
# TEST SHIPPING
# =============================================================================


class TestShipping:
    """Test shipping operations."""
    
    def test_create_shipment(self, service):
        """Test creating a shipment."""
        shipment = service.create_shipment(
            shipment_number="SHIP-001",
            order_id="SO-001",
            order_type="sales_order",
            customer_id="CUST-001",
            ship_to_address="123 Main St",
        )
        
        assert shipment is not None
        assert shipment.shipment_number == "SHIP-001"
        assert shipment.status == ShipmentStatus.PENDING
    
    def test_add_packing_list_line(self, service):
        """Test adding a packing list line."""
        shipment = service.create_shipment("SHIP-001", "SO-001", "sales_order")
        
        line = service.add_packing_list_line(
            shipment_id=shipment.id,
            part_id="PART-001",
            part_number="PN-001",
            description="Widget",
            quantity=Decimal("10"),
            uom="EA",
            package_number=1,
            weight=Decimal("5.5"),
        )
        
        assert line is not None
        assert line.quantity == Decimal("10")
    
    def test_generate_packing_list(self, service):
        """Test generating a packing list."""
        shipment = service.create_shipment("SHIP-001", "SO-001", "sales_order")
        service.add_packing_list_line(shipment.id, "PART-001", "PN-001", "Widget", Decimal("10"), "EA")
        service.add_packing_list_line(shipment.id, "PART-002", "PN-002", "Gadget", Decimal("5"), "EA")
        
        packing_list = service.generate_packing_list(shipment.id)
        
        assert "lines" in packing_list
        assert len(packing_list["lines"]) == 2
        assert shipment.packing_list_generated is True
    
    def test_confirm_shipment(self, service):
        """Test confirming a shipment."""
        shipment = service.create_shipment("SHIP-001", "SO-001", "sales_order")
        service.add_packing_list_line(shipment.id, "PART-001", "PN-001", "Widget", Decimal("10"), "EA")
        
        confirmed = service.confirm_shipment(
            shipment_id=shipment.id,
            carrier="FedEx",
            tracking_number="1234567890",
        )
        
        assert confirmed is not None
        assert confirmed.status == ShipmentStatus.SHIPPED
        assert confirmed.tracking_number == "1234567890"
    
    def test_get_shipment(self, service):
        """Test getting a shipment."""
        shipment = service.create_shipment("SHIP-001", "SO-001", "sales_order")
        
        retrieved = service.get_shipment(shipment.id)
        
        assert retrieved is not None
        assert retrieved.id == shipment.id
    
    def test_get_shipments(self, service):
        """Test getting shipments with filters."""
        service.create_shipment("SHIP-001", "SO-001", "sales_order")
        ship2 = service.create_shipment("SHIP-002", "SO-002", "sales_order")
        service.confirm_shipment(ship2.id)
        
        all_shipments = service.get_shipments()
        shipped = service.get_shipments(status=ShipmentStatus.SHIPPED)
        
        assert len(all_shipments) == 2
        assert len(shipped) == 1


# =============================================================================
# TEST ERP SYNC
# =============================================================================


class TestERPSync:
    """Test ERP synchronization operations."""
    
    def test_get_pending_erp_sync(self, service, sample_inventory):
        """Test getting pending ERP sync items."""
        service.adjust_inventory(sample_inventory.id, Decimal("45"), "count", "user")
        
        pending = service.get_pending_erp_sync()
        
        assert len(pending) >= 1
    
    def test_mark_erp_synced(self, service, sample_inventory):
        """Test marking an item as ERP synced."""
        service.adjust_inventory(sample_inventory.id, Decimal("45"), "count", "user")
        
        pending = service.get_pending_erp_sync()
        if pending:
            result = service.mark_erp_synced(pending[0]["id"])
            assert result is True
            
            # Should be removed from queue
            new_pending = service.get_pending_erp_sync()
            assert len(new_pending) < len(pending)


# =============================================================================
# TEST STATISTICS
# =============================================================================


class TestStatistics:
    """Test statistics operations."""
    
    def test_get_statistics(self, service, sample_zone, sample_location, sample_inventory):
        """Test getting WMS statistics."""
        stats = service.get_statistics()
        
        assert stats["total_zones"] == 1
        assert stats["total_locations"] == 1
        assert stats["total_inventory_records"] == 1
        assert "inventory_by_status" in stats


# =============================================================================
# TEST FACTORY FUNCTION
# =============================================================================


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_service_default(self):
        """Test creating service with defaults."""
        service = create_wms_service()
        
        assert service is not None
        assert service.default_pick_strategy == PickStrategy.FIFO
    
    def test_create_service_with_strategy(self):
        """Test creating service with custom pick strategy."""
        service = create_wms_service(default_pick_strategy=PickStrategy.FEFO)
        
        assert service.default_pick_strategy == PickStrategy.FEFO
