"""
Tests for Product, BOM, and Routing models.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from sensei.models.product import (
    Product,
    ProductStatus,
    UnitOfMeasure,
    BOMItem,
    Routing,
)


class TestProductModel:
    """Test cases for Product model."""

    def test_product_creation_basic(self):
        """Test basic product creation."""
        product = Product(
            name="Widget Assembly",
            part_number="WDG-001",
            revision="A",
            status=ProductStatus.ACTIVE,
            unit_of_measure=UnitOfMeasure.EACH,
        )

        assert product.name == "Widget Assembly"
        assert product.part_number == "WDG-001"
        assert product.revision == "A"
        assert product.status == ProductStatus.ACTIVE
        assert product.unit_of_measure == UnitOfMeasure.EACH

    def test_product_creation_full(self):
        """Test product creation with all fields."""
        product = Product(
            name="Precision Gear",
            part_number="PG-1000",
            revision="B",
            description="High-precision gear assembly",
            product_family="Gears",
            product_category="Mechanical",
            unit_of_measure=UnitOfMeasure.EACH,
            weight_kg=Decimal("0.5000"),
            dimensions="50x50x10",
            standard_cost=Decimal("25.5000"),
            standard_labor_hours=Decimal("0.5000"),
            lead_time_days=5,
            setup_time_hours=Decimal("0.25"),
            status=ProductStatus.ACTIVE,
        )

        assert product.part_number == "PG-1000"
        assert product.revision == "B"
        assert product.product_family == "Gears"
        assert product.weight_kg == Decimal("0.5000")
        assert product.lead_time_days == 5
        assert product.setup_time_hours == Decimal("0.25")

    def test_product_status_values(self):
        """Test all valid product status values."""
        for status in ProductStatus:
            product = Product(
                name=f"Product {status.value}",
                part_number=f"PRD-{status.value[:3].upper()}",
                status=status,
            )
            assert product.status == status

    def test_product_unit_of_measure_values(self):
        """Test all valid unit of measure values."""
        for uom in UnitOfMeasure:
            product = Product(
                name=f"Product {uom.value}",
                part_number=f"PRD-{uom.value[:3].upper()}",
                unit_of_measure=uom,
            )
            assert product.unit_of_measure == uom

    def test_product_full_part_number(self):
        """Test full part number property."""
        product = Product(
            name="Test Product",
            part_number="TST-001",
            revision="C",
        )
        assert product.full_part_number == "TST-001-C"

    def test_product_is_active(self):
        """Test is_active property."""
        product_active = Product(
            name="Active Product",
            part_number="ACT-001",
            status=ProductStatus.ACTIVE,
        )
        product_obsolete = Product(
            name="Obsolete Product",
            part_number="OBS-001",
            status=ProductStatus.OBSOLETE,
        )

        assert product_active.is_active is True
        assert product_obsolete.is_active is False

    def test_product_repr(self):
        """Test string representation."""
        product = Product(
            name="Test Product",
            part_number="TST-001",
            revision="A",
        )
        product.id = 1

        assert "Product" in repr(product)
        assert "TST-001" in repr(product)


class TestBOMItemModel:
    """Test cases for BOMItem model."""

    def test_bom_item_creation_basic(self):
        """Test basic BOM item creation."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("2.0"),
            unit_of_measure=UnitOfMeasure.EACH,
            is_critical=False,
        )

        assert bom_item.product_id == 1
        assert bom_item.component_part_number == "CMP-001"
        assert bom_item.quantity == Decimal("2.0")
        assert bom_item.unit_of_measure == UnitOfMeasure.EACH
        assert bom_item.is_critical is False

    def test_bom_item_creation_full(self):
        """Test BOM item creation with all fields."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="BOLT-M6-20",
            component_description="M6x20 Hex Bolt",
            quantity=Decimal("4.000000"),
            unit_of_measure=UnitOfMeasure.EACH,
            position=10,
            find_number="1A",
            is_critical=True,
            is_phantom=False,
            is_alternate=False,
            scrap_factor=Decimal("0.0200"),
        )

        assert bom_item.component_part_number == "BOLT-M6-20"
        assert bom_item.quantity == Decimal("4.000000")
        assert bom_item.position == 10
        assert bom_item.find_number == "1A"
        assert bom_item.is_critical is True
        assert bom_item.scrap_factor == Decimal("0.0200")

    def test_bom_item_extended_quantity(self):
        """Test extended quantity with scrap factor."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("10.000000"),
            scrap_factor=Decimal("0.0500"),  # 5% scrap
        )

        expected = Decimal("10.000000") * (1 + Decimal("0.0500"))
        assert bom_item.extended_quantity == expected

    def test_bom_item_extended_quantity_no_scrap(self):
        """Test extended quantity without scrap."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("5.000000"),
            scrap_factor=Decimal("0.0000"),
        )

        assert bom_item.extended_quantity == Decimal("5.000000")

    def test_bom_item_phantom_flag(self):
        """Test phantom/subassembly flag."""
        phantom = BOMItem(
            product_id=1,
            component_part_number="SUB-001",
            quantity=Decimal("1.0"),
            is_phantom=True,
        )
        assert phantom.is_phantom is True

    def test_bom_item_alternate_flag(self):
        """Test alternate part flag."""
        alternate = BOMItem(
            product_id=1,
            component_part_number="ALT-001",
            quantity=Decimal("1.0"),
            is_alternate=True,
        )
        assert alternate.is_alternate is True

    def test_bom_item_repr(self):
        """Test string representation."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("2.0"),
        )

        assert "BOMItem" in repr(bom_item)
        assert "CMP-001" in repr(bom_item)


class TestRoutingModel:
    """Test cases for Routing model."""

    def test_routing_creation_basic(self):
        """Test basic routing creation."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Assembly",
            station_id=1,
            standard_time_seconds=60,
            setup_time_seconds=0,
        )

        assert routing.product_id == 1
        assert routing.sequence == 10
        assert routing.operation_name == "Assembly"
        assert routing.station_id == 1
        assert routing.standard_time_seconds == 60
        assert routing.setup_time_seconds == 0

    def test_routing_creation_full(self):
        """Test routing creation with all fields."""
        routing = Routing(
            product_id=1,
            sequence=20,
            operation_name="CNC Machining",
            operation_code="OP-020",
            description="Machine outer diameter",
            station_id=2,
            standard_time_seconds=180,
            setup_time_seconds=300,
            move_time_seconds=30,
            queue_time_seconds=600,
            labor_hours=Decimal("0.0500"),
            crew_size=1,
            is_subcontracted=False,
            is_inspection=False,
        )

        assert routing.operation_name == "CNC Machining"
        assert routing.operation_code == "OP-020"
        assert routing.standard_time_seconds == 180
        assert routing.setup_time_seconds == 300
        assert routing.move_time_seconds == 30
        assert routing.queue_time_seconds == 600
        assert routing.crew_size == 1

    def test_routing_total_time(self):
        """Test total time calculation."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            standard_time_seconds=60,
            setup_time_seconds=120,
            move_time_seconds=10,
            queue_time_seconds=30,
        )

        expected = 60 + 120 + 10 + 30
        assert routing.total_time_seconds == expected

    def test_routing_time_per_unit(self):
        """Test time per unit (excludes setup)."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            standard_time_seconds=45,
            setup_time_seconds=600,  # Long setup
        )

        assert routing.time_per_unit_seconds == 45

    def test_routing_subcontracted_flag(self):
        """Test subcontracted operation flag."""
        subcontracted = Routing(
            product_id=1,
            sequence=30,
            operation_name="Heat Treatment",
            station_id=1,
            is_subcontracted=True,
        )
        assert subcontracted.is_subcontracted is True

    def test_routing_inspection_flag(self):
        """Test inspection operation flag."""
        inspection = Routing(
            product_id=1,
            sequence=40,
            operation_name="Final Inspection",
            station_id=1,
            is_inspection=True,
        )
        assert inspection.is_inspection is True

    def test_routing_repr(self):
        """Test string representation."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Assembly",
            station_id=1,
        )

        assert "Routing" in repr(routing)
        assert "10" in repr(routing)
        assert "Assembly" in repr(routing)


class TestProductBOMRelationship:
    """Test Product - BOM relationships."""

    def test_product_has_bom_items_list(self):
        """Test that product has bom_items list attribute."""
        product = Product(
            name="Test Product",
            part_number="TST-001",
        )
        assert hasattr(product, 'bom_items')

    def test_bom_item_references_product(self):
        """Test that BOM item references product."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("1.0"),
        )
        assert bom_item.product_id == 1
        assert hasattr(bom_item, 'product')


class TestProductRoutingRelationship:
    """Test Product - Routing relationships."""

    def test_product_has_routings_list(self):
        """Test that product has routings list attribute."""
        product = Product(
            name="Test Product",
            part_number="TST-001",
        )
        assert hasattr(product, 'routings')

    def test_routing_references_product_and_station(self):
        """Test that routing references product and station."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=2,
        )
        assert routing.product_id == 1
        assert routing.station_id == 2
        assert hasattr(routing, 'product')
        assert hasattr(routing, 'station')


class TestProductValidation:
    """Test Product validation constraints."""

    def test_product_explicit_revision(self):
        """Test explicit revision is A."""
        product = Product(
            name="Test Product",
            part_number="TST-001",
            revision="A",
        )
        assert product.revision == "A"

    def test_product_explicit_lead_time(self):
        """Test explicit lead time is zero."""
        product = Product(
            name="Test Product",
            part_number="TST-001",
            lead_time_days=0,
        )
        assert product.lead_time_days == 0


class TestBOMItemValidation:
    """Test BOM Item validation constraints."""

    def test_bom_item_explicit_scrap_factor(self):
        """Test explicit scrap factor is zero."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("1.0"),
            scrap_factor=Decimal("0.0"),
        )
        assert bom_item.scrap_factor == Decimal("0.0")

    def test_bom_item_explicit_position(self):
        """Test explicit position is zero."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="CMP-001",
            quantity=Decimal("1.0"),
            position=0,
        )
        assert bom_item.position == 0


class TestRoutingValidation:
    """Test Routing validation constraints."""

    def test_routing_explicit_crew_size(self):
        """Test explicit crew size is 1."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            crew_size=1,
        )
        assert routing.crew_size == 1

    def test_routing_explicit_move_time(self):
        """Test explicit move time is zero."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            move_time_seconds=0,
        )
        assert routing.move_time_seconds == 0

    def test_routing_explicit_queue_time(self):
        """Test explicit queue time is zero."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Test Op",
            station_id=1,
            queue_time_seconds=0,
        )
        assert routing.queue_time_seconds == 0


class TestProductEdgeCases:
    """Test edge cases for Product model."""

    def test_product_very_long_part_number(self):
        """Test product with long part number."""
        product = Product(
            name="Long PN Product",
            part_number="A" * 100,  # Max 100 chars
        )
        assert len(product.part_number) == 100

    def test_product_with_decimal_weight(self):
        """Test product with precise weight."""
        product = Product(
            name="Precise Weight",
            part_number="PW-001",
            weight_kg=Decimal("0.0001"),
        )
        assert product.weight_kg == Decimal("0.0001")


class TestBOMItemEdgeCases:
    """Test edge cases for BOM Item model."""

    def test_bom_item_fractional_quantity(self):
        """Test BOM item with fractional quantity."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="LIQUID-001",
            quantity=Decimal("0.250000"),
            unit_of_measure=UnitOfMeasure.LITER,
        )
        assert bom_item.quantity == Decimal("0.250000")

    def test_bom_item_high_scrap_factor(self):
        """Test BOM item with high scrap factor."""
        bom_item = BOMItem(
            product_id=1,
            component_part_number="HIGH-SCRAP-001",
            quantity=Decimal("100.0"),
            scrap_factor=Decimal("0.5000"),  # 50% scrap
        )
        expected = Decimal("100.0") * Decimal("1.5000")
        assert bom_item.extended_quantity == expected


class TestRoutingEdgeCases:
    """Test edge cases for Routing model."""

    def test_routing_very_long_operation(self):
        """Test routing with very long operation time."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Long Operation",
            station_id=1,
            standard_time_seconds=86400,  # 24 hours
        )
        assert routing.standard_time_seconds == 86400

    def test_routing_large_crew_size(self):
        """Test routing with large crew size."""
        routing = Routing(
            product_id=1,
            sequence=10,
            operation_name="Team Operation",
            station_id=1,
            crew_size=10,
        )
        assert routing.crew_size == 10
