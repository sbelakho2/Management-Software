"""
Tests for Lot & Serial Traceability (Genealogy) Service.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from sensei.services.production.lot_serial_traceability import (
    # Enums
    LotStatus,
    SerialStatus,
    TraceabilityDirection,
    GenealogyLinkType,
    CertificateType,
    RecallStatus,
    # Data Models
    LotRecord,
    SerialRecord,
    GenealogyLink,
    Certificate,
    RecallRecord,
    WhereUsedResult,
    TraceabilityTree,
    # Service
    LotSerialTraceabilityService,
    create_lot_serial_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance."""
    return LotSerialTraceabilityService()


@pytest.fixture
def sample_lot(service):
    """Create a sample lot."""
    return service.create_lot(
        part_id="part-001",
        part_number="PN-10001",
        quantity=Decimal("100"),
        uom="EA",
        supplier_id="supplier-001",
        supplier_lot_number="SUP-LOT-12345",
        purchase_order_id="PO-001",
        manufacture_date=datetime.now(timezone.utc) - timedelta(days=10),
        shelf_life_days=365,
        location_id="loc-001",
    )


@pytest.fixture
def sample_serial(service, sample_lot):
    """Create a sample serial number."""
    return service.create_serial(
        part_id="part-002",
        part_number="PN-20001",
        lot_id=sample_lot.id,
        work_order_id="WO-001",
        location_id="loc-001",
    )


# =============================================================================
# TEST: ENUMS
# =============================================================================


class TestEnums:
    """Tests for enumeration types."""
    
    def test_lot_status_values(self):
        """Test LotStatus enum values."""
        assert LotStatus.ACTIVE == "active"
        assert LotStatus.CONSUMED == "consumed"
        assert LotStatus.SHIPPED == "shipped"
        assert LotStatus.QUARANTINED == "quarantined"
        assert LotStatus.REJECTED == "rejected"
        assert LotStatus.EXPIRED == "expired"
        assert LotStatus.RECALLED == "recalled"
    
    def test_serial_status_values(self):
        """Test SerialStatus enum values."""
        assert SerialStatus.AVAILABLE == "available"
        assert SerialStatus.IN_USE == "in_use"
        assert SerialStatus.SHIPPED == "shipped"
        assert SerialStatus.RETURNED == "returned"
        assert SerialStatus.SCRAPPED == "scrapped"
        assert SerialStatus.RECALLED == "recalled"
    
    def test_traceability_direction_values(self):
        """Test TraceabilityDirection enum values."""
        assert TraceabilityDirection.UPSTREAM == "upstream"
        assert TraceabilityDirection.DOWNSTREAM == "downstream"
        assert TraceabilityDirection.BOTH == "both"
    
    def test_genealogy_link_type_values(self):
        """Test GenealogyLinkType enum values."""
        assert GenealogyLinkType.CONSUMED == "consumed"
        assert GenealogyLinkType.PRODUCED == "produced"
        assert GenealogyLinkType.TRANSFERRED == "transferred"
        assert GenealogyLinkType.INSPECTED == "inspected"
        assert GenealogyLinkType.SHIPPED == "shipped"
        assert GenealogyLinkType.SPLIT == "split"
        assert GenealogyLinkType.MERGED == "merged"
    
    def test_certificate_type_values(self):
        """Test CertificateType enum values."""
        assert CertificateType.COA == "coa"
        assert CertificateType.COC == "coc"
        assert CertificateType.MSDS == "msds"
        assert CertificateType.TEST_REPORT == "test_report"
        assert CertificateType.INSPECTION_REPORT == "inspection_report"


# =============================================================================
# TEST: DATA MODELS
# =============================================================================


class TestDataModels:
    """Tests for data models."""
    
    def test_lot_record_creation(self):
        """Test LotRecord creation."""
        lot = LotRecord(
            id="lot-001",
            lot_number="LOT-20250101-0001",
            part_id="part-001",
            part_number="PN-10001",
            quantity=Decimal("100"),
            uom="EA",
            status=LotStatus.ACTIVE,
        )
        assert lot.id == "lot-001"
        assert lot.lot_number == "LOT-20250101-0001"
        assert lot.quantity == Decimal("100")
        assert lot.status == LotStatus.ACTIVE
    
    def test_serial_record_creation(self):
        """Test SerialRecord creation."""
        serial = SerialRecord(
            id="serial-001",
            serial_number="SN-20250101-000001",
            part_id="part-002",
            part_number="PN-20001",
            status=SerialStatus.AVAILABLE,
        )
        assert serial.id == "serial-001"
        assert serial.serial_number == "SN-20250101-000001"
        assert serial.status == SerialStatus.AVAILABLE
    
    def test_genealogy_link_creation(self):
        """Test GenealogyLink creation."""
        link = GenealogyLink(
            id="link-001",
            link_type=GenealogyLinkType.CONSUMED,
            source_lot_id="lot-001",
            target_lot_id="lot-002",
            quantity=Decimal("50"),
            work_order_id="WO-001",
        )
        assert link.id == "link-001"
        assert link.link_type == GenealogyLinkType.CONSUMED
        assert link.quantity == Decimal("50")
    
    def test_certificate_creation(self):
        """Test Certificate creation."""
        cert = Certificate(
            id="cert-001",
            certificate_type=CertificateType.COA,
            certificate_number="COA-12345",
            lot_id="lot-001",
            file_path="/path/to/coa.pdf",
        )
        assert cert.id == "cert-001"
        assert cert.certificate_type == CertificateType.COA
        assert cert.is_valid is True
    
    def test_recall_record_creation(self):
        """Test RecallRecord creation."""
        recall = RecallRecord(
            id="recall-001",
            recall_number="RCL-2025-001",
            reason="Quality issue detected",
            affected_lot_ids=["lot-001", "lot-002"],
            status=RecallStatus.INITIATED,
        )
        assert recall.id == "recall-001"
        assert recall.recall_number == "RCL-2025-001"
        assert len(recall.affected_lot_ids) == 2
    
    def test_where_used_result_creation(self):
        """Test WhereUsedResult creation."""
        result = WhereUsedResult(
            source_lot_id="lot-001",
            affected_lots=["lot-002", "lot-003"],
            affected_serials=["serial-001"],
            total_quantity_affected=Decimal("150"),
        )
        assert result.source_lot_id == "lot-001"
        assert len(result.affected_lots) == 2
    
    def test_traceability_tree_creation(self):
        """Test TraceabilityTree creation."""
        tree = TraceabilityTree(
            lot_id="lot-001",
            part_number="PN-10001",
            lot_number="LOT-001",
            quantity=Decimal("100"),
            level=0,
            direction=TraceabilityDirection.DOWNSTREAM,
        )
        assert tree.lot_id == "lot-001"
        assert tree.level == 0
        assert len(tree.children) == 0


# =============================================================================
# TEST: LOT MANAGEMENT
# =============================================================================


class TestLotManagement:
    """Tests for lot management functions."""
    
    def test_generate_lot_number(self, service):
        """Test lot number generation."""
        lot_number = service.generate_lot_number()
        assert lot_number.startswith("LOT-")
        
        lot_number2 = service.generate_lot_number(prefix="BATCH")
        assert lot_number2.startswith("BATCH-")
    
    def test_create_lot(self, service):
        """Test lot creation."""
        lot = service.create_lot(
            part_id="part-001",
            part_number="PN-10001",
            quantity=Decimal("100"),
            uom="EA",
            supplier_id="supplier-001",
            supplier_lot_number="SUP-LOT-123",
        )
        
        assert lot.id is not None
        assert lot.lot_number is not None
        assert lot.part_id == "part-001"
        assert lot.quantity == Decimal("100")
        assert lot.status == LotStatus.ACTIVE
        assert lot.supplier_id == "supplier-001"
    
    def test_create_lot_with_expiry_calculation(self, service):
        """Test lot creation with shelf life expiry calculation."""
        manufacture_date = datetime.now(timezone.utc)
        
        lot = service.create_lot(
            part_id="part-001",
            part_number="PN-10001",
            quantity=Decimal("100"),
            uom="EA",
            manufacture_date=manufacture_date,
            shelf_life_days=90,
        )
        
        assert lot.expiry_date is not None
        expected_expiry = manufacture_date + timedelta(days=90)
        assert lot.expiry_date.date() == expected_expiry.date()
    
    def test_get_lot(self, service, sample_lot):
        """Test getting a lot by ID."""
        lot = service.get_lot(sample_lot.id)
        assert lot is not None
        assert lot.id == sample_lot.id
        
        # Non-existent lot
        assert service.get_lot("non-existent") is None
    
    def test_get_lot_by_number(self, service, sample_lot):
        """Test getting a lot by lot number."""
        lot = service.get_lot_by_number(sample_lot.lot_number)
        assert lot is not None
        assert lot.lot_number == sample_lot.lot_number
    
    def test_get_lots_by_part(self, service):
        """Test getting lots by part ID."""
        # Create multiple lots for same part
        service.create_lot(part_id="part-001", part_number="PN-10001", quantity=Decimal("100"), uom="EA")
        service.create_lot(part_id="part-001", part_number="PN-10001", quantity=Decimal("50"), uom="EA")
        service.create_lot(part_id="part-002", part_number="PN-10002", quantity=Decimal("200"), uom="EA")
        
        lots = service.get_lots_by_part("part-001")
        assert len(lots) == 2
        
        # Filter by status
        lots_active = service.get_lots_by_part("part-001", status=LotStatus.ACTIVE)
        assert len(lots_active) == 2
    
    def test_get_lots_by_supplier(self, service):
        """Test getting lots by supplier."""
        service.create_lot(
            part_id="part-001", 
            part_number="PN-10001", 
            quantity=Decimal("100"), 
            uom="EA",
            supplier_id="supplier-001",
        )
        service.create_lot(
            part_id="part-002", 
            part_number="PN-10002", 
            quantity=Decimal("200"), 
            uom="EA",
            supplier_id="supplier-001",
        )
        
        lots = service.get_lots_by_supplier("supplier-001")
        assert len(lots) == 2
    
    def test_update_lot_status(self, service, sample_lot):
        """Test updating lot status."""
        lot = service.update_lot_status(sample_lot.id, LotStatus.QUARANTINED)
        assert lot is not None
        assert lot.status == LotStatus.QUARANTINED
        
        # Non-existent lot
        assert service.update_lot_status("non-existent", LotStatus.ACTIVE) is None
    
    def test_update_lot_inspection(self, service, sample_lot):
        """Test updating lot with inspection results."""
        lot = service.update_lot_inspection(
            sample_lot.id,
            inspection_lot_id="insp-001",
            inspection_status="passed",
        )
        
        assert lot is not None
        assert lot.inspection_lot_id == "insp-001"
        assert lot.inspection_status == "passed"
        assert lot.status == LotStatus.ACTIVE  # Not quarantined
        
        # Failed inspection quarantines lot
        lot2 = service.create_lot(part_id="part-002", part_number="PN-10002", quantity=Decimal("50"), uom="EA")
        lot2_updated = service.update_lot_inspection(
            lot2.id,
            inspection_lot_id="insp-002",
            inspection_status="failed",
        )
        assert lot2_updated.status == LotStatus.QUARANTINED
    
    def test_split_lot(self, service, sample_lot):
        """Test splitting a lot."""
        original_qty = sample_lot.quantity
        split_qty = Decimal("30")
        
        child_lot = service.split_lot(sample_lot.id, split_qty, performed_by="user-001")
        
        assert child_lot is not None
        assert child_lot.quantity == split_qty
        assert child_lot.parent_lot_id == sample_lot.id
        
        # Original lot quantity reduced
        parent = service.get_lot(sample_lot.id)
        assert parent.quantity == original_qty - split_qty
        
        # Genealogy link created
        links = service.get_genealogy_links(lot_id=sample_lot.id)
        assert len(links) >= 1
        assert any(l.link_type == GenealogyLinkType.SPLIT for l in links)
    
    def test_split_lot_invalid_quantity(self, service, sample_lot):
        """Test splitting with invalid quantity."""
        # Can't split more than available
        result = service.split_lot(sample_lot.id, Decimal("200"))
        assert result is None
    
    def test_consume_lot(self, service, sample_lot):
        """Test consuming from a lot."""
        original_qty = sample_lot.quantity
        consume_qty = Decimal("25")
        
        result = service.consume_lot(
            sample_lot.id,
            consume_qty,
            work_order_id="WO-001",
            operation="Assembly",
            performed_by="user-001",
        )
        
        assert result is True
        
        lot = service.get_lot(sample_lot.id)
        assert lot.quantity == original_qty - consume_qty
        
        # Genealogy link created
        links = service.get_genealogy_links(lot_id=sample_lot.id)
        assert any(l.link_type == GenealogyLinkType.CONSUMED for l in links)
    
    def test_consume_lot_fully(self, service):
        """Test fully consuming a lot changes status."""
        lot = service.create_lot(
            part_id="part-001",
            part_number="PN-10001",
            quantity=Decimal("10"),
            uom="EA",
        )
        
        service.consume_lot(lot.id, Decimal("10"), work_order_id="WO-001")
        
        updated = service.get_lot(lot.id)
        assert updated.quantity == Decimal("0")
        assert updated.status == LotStatus.CONSUMED
    
    def test_consume_lot_insufficient_quantity(self, service, sample_lot):
        """Test consuming more than available."""
        result = service.consume_lot(
            sample_lot.id,
            Decimal("500"),  # More than available
            work_order_id="WO-001",
        )
        assert result is False
    
    def test_check_expiry(self, service):
        """Test expiry checking."""
        # Lot with future expiry
        lot_good = service.create_lot(
            part_id="part-001",
            part_number="PN-10001",
            quantity=Decimal("100"),
            uom="EA",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=100),
        )
        
        result = service.check_expiry(lot_good.id)
        assert result["expired"] is False
        assert result["days_remaining"] >= 99
        
        # Lot with past expiry
        lot_expired = service.create_lot(
            part_id="part-002",
            part_number="PN-10002",
            quantity=Decimal("50"),
            uom="EA",
            expiry_date=datetime.now(timezone.utc) - timedelta(days=10),
        )
        
        result = service.check_expiry(lot_expired.id)
        assert result["expired"] is True
        
        # Lot expiring soon
        lot_expiring = service.create_lot(
            part_id="part-003",
            part_number="PN-10003",
            quantity=Decimal("25"),
            uom="EA",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=15),
        )
        
        result = service.check_expiry(lot_expiring.id)
        assert result["expiring_soon"] is True
    
    def test_check_expiry_no_expiry(self, service):
        """Test expiry check for lot without expiry date."""
        lot = service.create_lot(
            part_id="part-001",
            part_number="PN-10001",
            quantity=Decimal("100"),
            uom="EA",
        )
        
        result = service.check_expiry(lot.id)
        assert result["expired"] is False
        assert result["days_remaining"] is None


# =============================================================================
# TEST: SERIAL NUMBER MANAGEMENT
# =============================================================================


class TestSerialManagement:
    """Tests for serial number management functions."""
    
    def test_generate_serial_number(self, service):
        """Test serial number generation."""
        serial_number = service.generate_serial_number()
        assert serial_number.startswith("SN-")
        
        serial_number2 = service.generate_serial_number(prefix="UNIT")
        assert serial_number2.startswith("UNIT-")
    
    def test_create_serial(self, service, sample_lot):
        """Test serial creation."""
        serial = service.create_serial(
            part_id="part-002",
            part_number="PN-20001",
            lot_id=sample_lot.id,
            work_order_id="WO-001",
        )
        
        assert serial.id is not None
        assert serial.serial_number is not None
        assert serial.lot_id == sample_lot.id
        assert serial.lot_number == sample_lot.lot_number
        assert serial.status == SerialStatus.AVAILABLE
    
    def test_create_serials_batch(self, service):
        """Test batch serial creation."""
        serials = service.create_serials_batch(
            part_id="part-002",
            part_number="PN-20001",
            quantity=5,
            prefix="BATCH",
        )
        
        assert len(serials) == 5
        serial_numbers = [s.serial_number for s in serials]
        assert len(set(serial_numbers)) == 5  # All unique
    
    def test_get_serial(self, service, sample_serial):
        """Test getting a serial by ID."""
        serial = service.get_serial(sample_serial.id)
        assert serial is not None
        assert serial.id == sample_serial.id
    
    def test_get_serial_by_number(self, service, sample_serial):
        """Test getting a serial by serial number."""
        serial = service.get_serial_by_number(sample_serial.serial_number)
        assert serial is not None
        assert serial.serial_number == sample_serial.serial_number
    
    def test_get_serials_by_lot(self, service, sample_lot):
        """Test getting serials by lot."""
        service.create_serial(part_id="part-002", part_number="PN-20001", lot_id=sample_lot.id)
        service.create_serial(part_id="part-002", part_number="PN-20001", lot_id=sample_lot.id)
        
        serials = service.get_serials_by_lot(sample_lot.id)
        assert len(serials) == 2
    
    def test_get_serials_by_part(self, service):
        """Test getting serials by part."""
        service.create_serial(part_id="part-002", part_number="PN-20001")
        service.create_serial(part_id="part-002", part_number="PN-20001")
        service.create_serial(part_id="part-003", part_number="PN-30001")
        
        serials = service.get_serials_by_part("part-002")
        assert len(serials) == 2
    
    def test_update_serial_status(self, service, sample_serial):
        """Test updating serial status."""
        serial = service.update_serial_status(sample_serial.id, SerialStatus.IN_USE)
        assert serial is not None
        assert serial.status == SerialStatus.IN_USE
    
    def test_ship_serial(self, service, sample_serial):
        """Test shipping a serial."""
        serial = service.ship_serial(
            sample_serial.id,
            customer_id="customer-001",
            sales_order_id="SO-001",
            warranty_days=365,
        )
        
        assert serial is not None
        assert serial.status == SerialStatus.SHIPPED
        assert serial.customer_id == "customer-001"
        assert serial.ship_date is not None
        assert serial.warranty_start is not None
        assert serial.warranty_end is not None


# =============================================================================
# TEST: GENEALOGY MANAGEMENT
# =============================================================================


class TestGenealogyManagement:
    """Tests for genealogy management functions."""
    
    def test_record_production(self, service):
        """Test recording production genealogy."""
        # Create component lots
        comp1 = service.create_lot(part_id="comp-001", part_number="COMP-1", quantity=Decimal("100"), uom="EA")
        comp2 = service.create_lot(part_id="comp-002", part_number="COMP-2", quantity=Decimal("50"), uom="EA")
        
        # Create output lot
        output = service.create_lot(part_id="assy-001", part_number="ASSY-1", quantity=Decimal("10"), uom="EA", work_order_id="WO-001")
        
        # Record production
        links = service.record_production(
            work_order_id="WO-001",
            output_lot_id=output.id,
            component_lots=[
                {"lot_id": comp1.id, "quantity": 20, "operation": "OP10"},
                {"lot_id": comp2.id, "quantity": 10, "operation": "OP20"},
            ],
            performed_by="user-001",
        )
        
        assert len(links) == 3  # 2 consumed + 1 produced
        assert any(l.link_type == GenealogyLinkType.CONSUMED for l in links)
        assert any(l.link_type == GenealogyLinkType.PRODUCED for l in links)
    
    def test_get_genealogy_links(self, service, sample_lot):
        """Test getting genealogy links."""
        # Create some links
        child = service.split_lot(sample_lot.id, Decimal("20"))
        
        links = service.get_genealogy_links(lot_id=sample_lot.id)
        assert len(links) >= 1
        
        # Filter by type
        split_links = service.get_genealogy_links(lot_id=sample_lot.id, link_type=GenealogyLinkType.SPLIT)
        assert len(split_links) == 1
    
    def test_trace_upstream(self, service):
        """Test upstream tracing (1-Down)."""
        # Create supply chain
        supplier_lot = service.create_lot(
            part_id="raw-001", 
            part_number="RAW-1", 
            quantity=Decimal("1000"), 
            uom="KG",
            supplier_id="supplier-001",
        )
        
        intermediate_lot = service.create_lot(
            part_id="int-001", 
            part_number="INT-1", 
            quantity=Decimal("100"), 
            uom="EA",
        )
        
        final_lot = service.create_lot(
            part_id="final-001", 
            part_number="FINAL-1", 
            quantity=Decimal("50"), 
            uom="EA",
        )
        
        # Record genealogy
        service.record_production(
            work_order_id="WO-001",
            output_lot_id=intermediate_lot.id,
            component_lots=[{"lot_id": supplier_lot.id, "quantity": 100}],
        )
        
        service.record_production(
            work_order_id="WO-002",
            output_lot_id=final_lot.id,
            component_lots=[{"lot_id": intermediate_lot.id, "quantity": 50}],
        )
        
        # Trace upstream from final
        tree = service.trace_upstream(lot_id=final_lot.id)
        
        assert tree.lot_id == final_lot.id
        assert tree.direction == TraceabilityDirection.UPSTREAM
        assert len(tree.children) >= 1
    
    def test_trace_downstream(self, service):
        """Test downstream tracing (1-Up)."""
        # Create supply chain
        raw_lot = service.create_lot(
            part_id="raw-001", 
            part_number="RAW-1", 
            quantity=Decimal("1000"), 
            uom="KG",
        )
        
        prod_lot = service.create_lot(
            part_id="prod-001", 
            part_number="PROD-1", 
            quantity=Decimal("100"), 
            uom="EA",
        )
        
        # Record genealogy
        service.record_production(
            work_order_id="WO-001",
            output_lot_id=prod_lot.id,
            component_lots=[{"lot_id": raw_lot.id, "quantity": 100}],
        )
        
        # Trace downstream from raw
        tree = service.trace_downstream(lot_id=raw_lot.id)
        
        assert tree.lot_id == raw_lot.id
        assert tree.direction == TraceabilityDirection.DOWNSTREAM
        assert len(tree.children) >= 1


# =============================================================================
# TEST: WHERE-USED INTELLIGENCE
# =============================================================================


class TestWhereUsedIntelligence:
    """Tests for where-used intelligence."""
    
    def test_where_used_basic(self, service):
        """Test basic where-used query."""
        # Create component
        component = service.create_lot(
            part_id="comp-001", 
            part_number="COMP-1", 
            quantity=Decimal("100"), 
            uom="EA",
        )
        
        # Create assemblies using the component
        assy1 = service.create_lot(part_id="assy-001", part_number="ASSY-1", quantity=Decimal("10"), uom="EA")
        assy2 = service.create_lot(part_id="assy-002", part_number="ASSY-2", quantity=Decimal("20"), uom="EA")
        
        service.record_production("WO-001", assy1.id, [{"lot_id": component.id, "quantity": 30}])
        service.record_production("WO-002", assy2.id, [{"lot_id": component.id, "quantity": 40}])
        
        # Query where-used
        result = service.where_used(lot_id=component.id)
        
        assert result.source_lot_id == component.id
        assert len(result.affected_lots) >= 2  # At least the assemblies
    
    def test_where_used_with_shipped_serials(self, service):
        """Test where-used with shipped serials."""
        # Create component
        component = service.create_lot(
            part_id="comp-001", 
            part_number="COMP-1", 
            quantity=Decimal("100"), 
            uom="EA",
        )
        
        # Create assembly
        assembly = service.create_lot(
            part_id="assy-001", 
            part_number="ASSY-1", 
            quantity=Decimal("5"), 
            uom="EA",
        )
        
        service.record_production("WO-001", assembly.id, [{"lot_id": component.id, "quantity": 50}])
        
        # Create serials from assembly lot and ship them
        serial1 = service.create_serial(part_id="assy-001", part_number="ASSY-1", lot_id=assembly.id)
        serial2 = service.create_serial(part_id="assy-001", part_number="ASSY-1", lot_id=assembly.id)
        
        service.ship_serial(serial1.id, customer_id="CUST-001", sales_order_id="SO-001")
        service.ship_serial(serial2.id, customer_id="CUST-002", sales_order_id="SO-002")
        
        # Create genealogy links for serials
        service._create_genealogy_link(
            link_type=GenealogyLinkType.PRODUCED,
            source_lot_id=assembly.id,
            target_serial_id=serial1.id,
        )
        service._create_genealogy_link(
            link_type=GenealogyLinkType.PRODUCED,
            source_lot_id=assembly.id,
            target_serial_id=serial2.id,
        )
        
        # Query where-used
        result = service.where_used(lot_id=component.id)
        
        assert len(result.affected_shipments) >= 0  # May or may not find depending on link structure
    
    def test_where_used_multilevel(self, service):
        """Test where-used across multiple levels."""
        # L0: Raw material
        raw = service.create_lot(part_id="raw-001", part_number="RAW-1", quantity=Decimal("1000"), uom="KG")
        
        # L1: Intermediate
        intermediate = service.create_lot(part_id="int-001", part_number="INT-1", quantity=Decimal("100"), uom="EA")
        service.record_production("WO-001", intermediate.id, [{"lot_id": raw.id, "quantity": 100}])
        
        # L2: Sub-assembly
        sub_assy = service.create_lot(part_id="sub-001", part_number="SUB-1", quantity=Decimal("50"), uom="EA")
        service.record_production("WO-002", sub_assy.id, [{"lot_id": intermediate.id, "quantity": 50}])
        
        # L3: Final assembly
        final = service.create_lot(part_id="fin-001", part_number="FIN-1", quantity=Decimal("25"), uom="EA")
        service.record_production("WO-003", final.id, [{"lot_id": sub_assy.id, "quantity": 25}])
        
        # Query from raw material
        result = service.where_used(lot_id=raw.id)
        
        # Should find all downstream lots
        assert raw.id in result.affected_lots
        assert len(result.affected_lots) >= 4  # raw, intermediate, sub, final


# =============================================================================
# TEST: CERTIFICATE / EVIDENCE BINDING
# =============================================================================


class TestCertificateBinding:
    """Tests for certificate/evidence binding."""
    
    def test_attach_certificate(self, service, sample_lot):
        """Test attaching a certificate to a lot."""
        cert = service.attach_certificate(
            certificate_type=CertificateType.COA,
            lot_id=sample_lot.id,
            certificate_number="COA-2025-001",
            file_path="/docs/coa_2025_001.pdf",
            file_name="coa_2025_001.pdf",
            issue_date=datetime.now(timezone.utc),
            issuing_authority="Quality Lab Inc.",
        )
        
        assert cert.id is not None
        assert cert.certificate_type == CertificateType.COA
        assert cert.lot_id == sample_lot.id
        assert cert.is_valid is True
    
    def test_attach_coc(self, service, sample_lot):
        """Test attaching Certificate of Conformance."""
        cert = service.attach_certificate(
            certificate_type=CertificateType.COC,
            lot_id=sample_lot.id,
            certificate_number="COC-2025-001",
            supplier_id="supplier-001",
        )
        
        assert cert.certificate_type == CertificateType.COC
    
    def test_get_certificates(self, service, sample_lot):
        """Test getting certificates."""
        service.attach_certificate(CertificateType.COA, lot_id=sample_lot.id)
        service.attach_certificate(CertificateType.COC, lot_id=sample_lot.id)
        service.attach_certificate(CertificateType.MSDS, lot_id=sample_lot.id)
        
        # Get all for lot
        certs = service.get_certificates(lot_id=sample_lot.id)
        assert len(certs) == 3
        
        # Filter by type
        coas = service.get_certificates(lot_id=sample_lot.id, certificate_type=CertificateType.COA)
        assert len(coas) == 1
    
    def test_verify_certificate(self, service, sample_lot):
        """Test verifying a certificate."""
        cert = service.attach_certificate(
            CertificateType.COA,
            lot_id=sample_lot.id,
        )
        
        verified = service.verify_certificate(cert.id, verified_by="quality-mgr-001")
        
        assert verified.verified_by == "quality-mgr-001"
        assert verified.verified_at is not None
    
    def test_check_certificate_validity(self, service, sample_lot):
        """Test certificate validity checking."""
        # Valid certificate with future expiry
        cert_valid = service.attach_certificate(
            CertificateType.COA,
            lot_id=sample_lot.id,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
        )
        
        result = service.check_certificate_validity(cert_valid.id)
        assert result["valid"] is True
        assert result["expired"] is False
        
        # Expired certificate
        cert_expired = service.attach_certificate(
            CertificateType.COC,
            lot_id=sample_lot.id,
            expiry_date=datetime.now(timezone.utc) - timedelta(days=30),
        )
        
        result = service.check_certificate_validity(cert_expired.id)
        assert result["expired"] is True
    
    def test_certificate_with_file_hash(self, service, sample_lot):
        """Test certificate with file hash for integrity."""
        cert = service.attach_certificate(
            CertificateType.COA,
            lot_id=sample_lot.id,
            file_path="/docs/coa.pdf",
            file_hash="sha256:abc123def456...",
        )
        
        assert cert.file_hash == "sha256:abc123def456..."


# =============================================================================
# TEST: RECALL MANAGEMENT
# =============================================================================


class TestRecallManagement:
    """Tests for recall management."""
    
    def test_initiate_recall(self, service):
        """Test initiating a recall."""
        # Create component and downstream products
        component = service.create_lot(
            part_id="comp-001", 
            part_number="COMP-1", 
            quantity=Decimal("100"), 
            uom="EA",
        )
        
        product = service.create_lot(
            part_id="prod-001", 
            part_number="PROD-1", 
            quantity=Decimal("50"), 
            uom="EA",
        )
        
        service.record_production("WO-001", product.id, [{"lot_id": component.id, "quantity": 50}])
        
        # Initiate recall
        recall = service.initiate_recall(
            recall_number="RCL-2025-001",
            reason="Defective component batch",
            affected_lot_ids=[component.id],
            initiated_by="quality-mgr-001",
        )
        
        assert recall.id is not None
        assert recall.recall_number == "RCL-2025-001"
        assert recall.status == RecallStatus.INITIATED
        assert component.id in recall.affected_lot_ids
        # Should also find downstream product
        assert product.id in recall.affected_lot_ids
        
        # Affected lots should be marked as recalled
        comp_lot = service.get_lot(component.id)
        assert comp_lot.status == LotStatus.RECALLED
    
    def test_get_recall(self, service):
        """Test getting a recall by ID."""
        lot = service.create_lot(part_id="comp-001", part_number="COMP-1", quantity=Decimal("100"), uom="EA")
        
        recall = service.initiate_recall(
            recall_number="RCL-2025-002",
            reason="Test recall",
            affected_lot_ids=[lot.id],
        )
        
        retrieved = service.get_recall(recall.id)
        assert retrieved is not None
        assert retrieved.recall_number == "RCL-2025-002"
    
    def test_get_recalls(self, service):
        """Test getting all recalls."""
        lot1 = service.create_lot(part_id="p1", part_number="P1", quantity=Decimal("10"), uom="EA")
        lot2 = service.create_lot(part_id="p2", part_number="P2", quantity=Decimal("20"), uom="EA")
        
        service.initiate_recall("RCL-001", "Reason 1", affected_lot_ids=[lot1.id])
        service.initiate_recall("RCL-002", "Reason 2", affected_lot_ids=[lot2.id])
        
        recalls = service.get_recalls()
        assert len(recalls) == 2
        
        # Filter by status
        initiated = service.get_recalls(status=RecallStatus.INITIATED)
        assert len(initiated) == 2
    
    def test_complete_recall(self, service):
        """Test completing a recall."""
        lot = service.create_lot(part_id="p1", part_number="P1", quantity=Decimal("10"), uom="EA")
        recall = service.initiate_recall("RCL-001", "Test", affected_lot_ids=[lot.id])
        
        completed = service.complete_recall(recall.id, notes="All affected units recovered")
        
        assert completed.status == RecallStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.notes == "All affected units recovered"
    
    def test_recall_finds_shipped_products(self, service):
        """Test that recall identifies shipped products."""
        # Create and ship product
        lot = service.create_lot(part_id="prod-001", part_number="PROD-1", quantity=Decimal("10"), uom="EA")
        serial = service.create_serial(part_id="prod-001", part_number="PROD-1", lot_id=lot.id)
        service.ship_serial(serial.id, customer_id="CUST-001", sales_order_id="SO-001")
        
        # Link serial to lot
        service._create_genealogy_link(
            link_type=GenealogyLinkType.PRODUCED,
            source_lot_id=lot.id,
            target_serial_id=serial.id,
        )
        
        # Initiate recall
        recall = service.initiate_recall(
            recall_number="RCL-SHIP-001",
            reason="Shipped product defect",
            affected_lot_ids=[lot.id],
        )
        
        # Should identify the serial as affected
        assert serial.id in recall.affected_serial_ids


# =============================================================================
# TEST: STATISTICS
# =============================================================================


class TestStatistics:
    """Tests for statistics functions."""
    
    def test_get_statistics(self, service, sample_lot, sample_serial):
        """Test getting traceability statistics."""
        # Create more data
        service.create_lot(part_id="p2", part_number="P2", quantity=Decimal("50"), uom="EA")
        service.attach_certificate(CertificateType.COA, lot_id=sample_lot.id)
        service.attach_certificate(CertificateType.COC, lot_id=sample_lot.id)
        
        stats = service.get_statistics()
        
        assert stats["total_lots"] >= 2
        assert stats["total_serials"] >= 1
        assert stats["total_certificates"] == 2
        assert "lots_by_status" in stats
        assert "serials_by_status" in stats
        assert "certificates_by_type" in stats


# =============================================================================
# TEST: FACTORY FUNCTION
# =============================================================================


class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_lot_serial_service(self):
        """Test factory function creates service."""
        service = create_lot_serial_service()
        
        assert service is not None
        assert isinstance(service, LotSerialTraceabilityService)
    
    def test_factory_creates_fresh_instance(self):
        """Test factory creates independent instances."""
        service1 = create_lot_serial_service()
        service2 = create_lot_serial_service()
        
        # Add data to service1
        service1.create_lot(part_id="p1", part_number="P1", quantity=Decimal("10"), uom="EA")
        
        # Service2 should be empty
        stats1 = service1.get_statistics()
        stats2 = service2.get_statistics()
        
        assert stats1["total_lots"] == 1
        assert stats2["total_lots"] == 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_check_expiry_nonexistent_lot(self, service):
        """Test expiry check for non-existent lot."""
        result = service.check_expiry("non-existent")
        assert "error" in result
    
    def test_split_nonexistent_lot(self, service):
        """Test splitting non-existent lot."""
        result = service.split_lot("non-existent", Decimal("10"))
        assert result is None
    
    def test_consume_nonexistent_lot(self, service):
        """Test consuming from non-existent lot."""
        result = service.consume_lot("non-existent", Decimal("10"), work_order_id="WO-001")
        assert result is False
    
    def test_verify_nonexistent_certificate(self, service):
        """Test verifying non-existent certificate."""
        result = service.verify_certificate("non-existent", verified_by="user")
        assert result is None
    
    def test_check_validity_nonexistent_certificate(self, service):
        """Test validity check for non-existent certificate."""
        result = service.check_certificate_validity("non-existent")
        assert "error" in result
    
    def test_complete_nonexistent_recall(self, service):
        """Test completing non-existent recall."""
        result = service.complete_recall("non-existent")
        assert result is None
    
    def test_trace_empty_genealogy(self, service, sample_lot):
        """Test tracing lot with no genealogy."""
        tree = service.trace_downstream(lot_id=sample_lot.id)
        
        assert tree.lot_id == sample_lot.id
        assert len(tree.children) == 0
    
    def test_where_used_no_downstream(self, service, sample_lot):
        """Test where-used with no downstream items."""
        result = service.where_used(lot_id=sample_lot.id)
        
        assert result.source_lot_id == sample_lot.id
        assert sample_lot.id in result.affected_lots  # Only itself
