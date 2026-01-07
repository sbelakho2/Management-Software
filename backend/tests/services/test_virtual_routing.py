"""
Tests for Virtual Routing Service.

Comprehensive tests covering:
- Virtual routing CRUD operations
- Operation management
- Cost calculations
- Template management
- Routing comparison
- Quick builders
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sensei.services.virtual_routing import (
    VirtualRoutingService,
    VirtualRouting,
    VirtualOperation,
    RoutingTemplate,
    OperationType,
    CostBasis,
    RoutingSource,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service() -> VirtualRoutingService:
    """Create a fresh virtual routing service."""
    svc = VirtualRoutingService()
    svc.clear()
    return svc


@pytest.fixture
def sample_routing(service: VirtualRoutingService) -> VirtualRouting:
    """Create a sample virtual routing with operations."""
    routing = service.create_routing(
        name="Test Machining Routing",
        description="Test routing for machining part",
        quote_id=uuid4(),
    )
    
    routing.add_operation(
        operation_type=OperationType.SETUP,
        operation_name="Setup",
        setup_time_minutes=Decimal("30"),
        run_time_minutes=Decimal("0"),
    )
    
    routing.add_operation(
        operation_type=OperationType.MACHINING,
        operation_name="CNC Machining",
        setup_time_minutes=Decimal("0"),
        run_time_minutes=Decimal("5"),
        machine_rate_per_hour=Decimal("50"),
    )
    
    routing.add_operation(
        operation_type=OperationType.INSPECTION,
        operation_name="Inspection",
        setup_time_minutes=Decimal("0"),
        run_time_minutes=Decimal("2"),
    )
    
    return routing


# =============================================================================
# Test Routing CRUD
# =============================================================================


class TestRoutingCRUD:
    """Tests for routing CRUD operations."""
    
    def test_create_routing(self, service: VirtualRoutingService) -> None:
        """Test creating a new virtual routing."""
        routing = service.create_routing(
            name="New Routing",
            description="Test routing",
        )
        
        assert routing.id is not None
        assert routing.name == "New Routing"
        assert routing.source == RoutingSource.MANUAL
        assert routing.created_at is not None
    
    def test_create_routing_with_quote_reference(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test creating routing with quote reference."""
        quote_id = uuid4()
        line_item_id = uuid4()
        
        routing = service.create_routing(
            name="Quote Routing",
            quote_id=quote_id,
            quote_line_item_id=line_item_id,
        )
        
        assert routing.quote_id == quote_id
        assert routing.quote_line_item_id == line_item_id
    
    def test_get_routing(self, service: VirtualRoutingService) -> None:
        """Test getting a routing by ID."""
        created = service.create_routing(name="Test Routing")
        
        retrieved = service.get_routing(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_nonexistent_routing(self, service: VirtualRoutingService) -> None:
        """Test getting a non-existent routing."""
        result = service.get_routing(uuid4())
        assert result is None
    
    def test_list_routings(self, service: VirtualRoutingService) -> None:
        """Test listing routings."""
        service.create_routing(name="Routing 1")
        service.create_routing(name="Routing 2")
        service.create_routing(name="Routing 3")
        
        routings = service.list_routings()
        
        assert len(routings) == 3
    
    def test_list_routings_by_quote(self, service: VirtualRoutingService) -> None:
        """Test filtering routings by quote."""
        quote_id = uuid4()
        
        service.create_routing(name="Quote Routing", quote_id=quote_id)
        service.create_routing(name="Other Routing")
        
        routings = service.list_routings(quote_id=quote_id)
        
        assert len(routings) == 1
        assert routings[0].quote_id == quote_id
    
    def test_delete_routing(self, service: VirtualRoutingService) -> None:
        """Test deleting a routing."""
        routing = service.create_routing(name="To Delete")
        
        result = service.delete_routing(routing.id)
        
        assert result is True
        assert service.get_routing(routing.id) is None
    
    def test_delete_nonexistent_routing(self, service: VirtualRoutingService) -> None:
        """Test deleting a non-existent routing."""
        result = service.delete_routing(uuid4())
        assert result is False
    
    def test_clone_routing(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test cloning a routing."""
        cloned = service.clone_routing(sample_routing.id, "Cloned Routing")
        
        assert cloned is not None
        assert cloned.id != sample_routing.id
        assert cloned.name == "Cloned Routing"
        assert cloned.source == RoutingSource.CLONED
        assert len(cloned.operations) == len(sample_routing.operations)


# =============================================================================
# Test Operation Management
# =============================================================================


class TestOperationManagement:
    """Tests for managing operations in routings."""
    
    def test_add_operation(self, service: VirtualRoutingService) -> None:
        """Test adding an operation to a routing."""
        routing = service.create_routing(name="Test Routing")
        
        operation = routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="CNC Mill",
            setup_time_minutes=Decimal("15"),
            run_time_minutes=Decimal("5"),
        )
        
        assert operation.id is not None
        assert operation.operation_type == OperationType.MACHINING
        assert operation.setup_time_minutes == Decimal("15")
        assert len(routing.operations) == 1
    
    def test_add_multiple_operations(self, service: VirtualRoutingService) -> None:
        """Test adding multiple operations."""
        routing = service.create_routing(name="Test Routing")
        
        routing.add_operation(
            operation_type=OperationType.SETUP,
            operation_name="Setup",
        )
        routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
        )
        routing.add_operation(
            operation_type=OperationType.INSPECTION,
            operation_name="Inspection",
        )
        
        assert len(routing.operations) == 3
    
    def test_operations_have_default_rates(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that operations inherit default rates from routing."""
        routing = service.create_routing(
            name="Test Routing",
            default_labor_rate=Decimal("30.00"),
        )
        
        operation = routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
        )
        
        assert operation.labor_rate_per_hour == Decimal("30.00")
    
    def test_remove_operation(self, service: VirtualRoutingService) -> None:
        """Test removing an operation."""
        routing = service.create_routing(name="Test Routing")
        
        op = routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
        )
        
        result = routing.remove_operation(op.id)
        
        assert result is True
        assert len(routing.operations) == 0
    
    def test_get_operation(self, service: VirtualRoutingService) -> None:
        """Test getting an operation by ID."""
        routing = service.create_routing(name="Test Routing")
        
        op = routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
        )
        
        retrieved = routing.get_operation(op.id)
        
        assert retrieved is not None
        assert retrieved.id == op.id
    
    def test_operations_renumbered_on_add(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that operation sequences are renumbered."""
        routing = service.create_routing(name="Test Routing")
        
        routing.add_operation(
            operation_type=OperationType.SETUP,
            operation_name="Setup",
        )
        routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
        )
        
        sequences = [op.sequence for op in routing.operations]
        
        assert sequences == [10, 20]


# =============================================================================
# Test Time Calculations
# =============================================================================


class TestTimeCalculations:
    """Tests for time calculations."""
    
    def test_operation_time_per_unit(self) -> None:
        """Test calculating operation time per unit."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("30"),
            run_time_minutes=Decimal("5"),
            move_time_minutes=Decimal("2"),
            queue_time_minutes=Decimal("1"),
        )
        
        # With batch size of 10
        time_per_unit = operation.calculate_time_per_unit(batch_size=10)
        
        # Setup (30/10=3) + run (5) + move (2) + queue (1) = 11
        assert time_per_unit == Decimal("11")
    
    def test_routing_total_time(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test calculating total routing time."""
        # sample_routing has:
        # - Setup: 30 min setup, 0 run
        # - Machining: 0 setup, 5 run
        # - Inspection: 0 setup, 2 run
        
        total_time = sample_routing.calculate_total_time_minutes(quantity=1)
        
        # With batch_size=1: 30 + 5 + 2 = 37
        assert total_time == Decimal("37")
    
    def test_routing_time_for_multiple_units(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test calculating time for multiple units."""
        total_time = sample_routing.calculate_total_time_minutes(quantity=10)
        
        # Setup amortized: 30/1 = 30 per unit (batch_size=1)
        # Run time: (5 + 2) * 10 = 70
        # Total: (30 + 5 + 2) * 10 = 370
        assert total_time == Decimal("370")
    
    def test_lead_time_calculation(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test calculating lead time in days."""
        lead_time = sample_routing.calculate_lead_time_days(
            quantity=100,
            hours_per_day=Decimal("8"),
        )
        
        # Total time for 100 units = 3700 minutes = ~61.67 hours = ~8 days
        assert lead_time >= 7


# =============================================================================
# Test Cost Calculations
# =============================================================================


class TestCostCalculations:
    """Tests for cost calculations."""
    
    def test_operation_labor_cost(self) -> None:
        """Test calculating operation labor cost."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=Decimal("60"),  # 1 hour
            labor_rate_per_hour=Decimal("25"),
            crew_size=1,
        )
        
        labor_cost = operation.calculate_labor_cost(quantity=1)
        
        assert labor_cost == Decimal("25.00")
    
    def test_operation_overhead_cost(self) -> None:
        """Test calculating operation overhead cost."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=Decimal("60"),  # 1 hour
            overhead_rate_per_hour=Decimal("35"),
            machine_rate_per_hour=Decimal("15"),
        )
        
        overhead_cost = operation.calculate_overhead_cost(quantity=1)
        
        # 1 hour * (35 + 15) = 50
        assert overhead_cost == Decimal("50.00")
    
    def test_operation_total_cost(self) -> None:
        """Test calculating total operation cost."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=Decimal("60"),
            labor_rate_per_hour=Decimal("25"),
            overhead_rate_per_hour=Decimal("35"),
            machine_rate_per_hour=Decimal("15"),
            crew_size=1,
        )
        
        total_cost = operation.calculate_total_cost(quantity=1)
        
        # Labor: 25, Overhead: 50, Total: 75
        assert total_cost == Decimal("75.00")
    
    def test_subcontract_operation_cost(self) -> None:
        """Test calculating subcontract operation cost."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.SUBCONTRACT,
            operation_name="Heat Treatment",
            is_subcontracted=True,
            subcontract_cost=Decimal("10.00"),
        )
        
        total_cost = operation.calculate_total_cost(quantity=100)
        
        assert total_cost == Decimal("1000.00")
    
    def test_routing_cost_breakdown(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test getting routing cost breakdown."""
        costs = sample_routing.calculate_costs(quantity=100)
        
        assert "labor_cost" in costs
        assert "overhead_cost" in costs
        assert "subcontract_cost" in costs
        assert "total_manufacturing_cost" in costs
        assert "cost_per_unit" in costs
        
        assert costs["total_manufacturing_cost"] > 0
    
    def test_routing_costs_with_material(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test cost estimation including material."""
        estimate = service.estimate_costs(
            routing_id=sample_routing.id,
            quantity=100,
            material_cost=Decimal("500.00"),
        )
        
        assert estimate is not None
        assert estimate["material_cost"] == Decimal("500.00")
        assert estimate["total_cost"] > estimate["total_manufacturing_cost"]
    
    def test_fixed_cost_operation(self) -> None:
        """Test operation with fixed cost basis."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.SETUP,
            operation_name="One-time Setup",
            cost_basis=CostBasis.FIXED,
            fixed_cost=Decimal("100.00"),
        )
        
        # Fixed cost regardless of quantity
        cost_1 = operation.calculate_labor_cost(quantity=1)
        cost_100 = operation.calculate_labor_cost(quantity=100)
        
        assert cost_1 == Decimal("100.00")
        assert cost_100 == Decimal("100.00")
    
    def test_per_batch_cost_operation(self) -> None:
        """Test operation with per-batch cost basis."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.SETUP,
            operation_name="Batch Setup",
            cost_basis=CostBasis.PER_BATCH,
            fixed_cost=Decimal("50.00"),
        )
        
        # 100 units with batch size 25 = 4 batches
        cost = operation.calculate_labor_cost(quantity=100, batch_size=25)
        
        assert cost == Decimal("200.00")
    
    def test_scrap_rate_increases_cost(self) -> None:
        """Test that scrap rate increases operation cost."""
        operation = VirtualOperation(
            id=uuid4(),
            sequence=10,
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("0"),
            run_time_minutes=Decimal("60"),
            labor_rate_per_hour=Decimal("25"),
            overhead_rate_per_hour=Decimal("0"),
            machine_rate_per_hour=Decimal("0"),
            scrap_rate=Decimal("0.10"),  # 10% scrap
        )
        
        cost = operation.calculate_total_cost(quantity=1)
        
        # Base cost: 25, with 10% scrap: 27.50
        assert cost == Decimal("27.50")


# =============================================================================
# Test Template Management
# =============================================================================


class TestTemplateManagement:
    """Tests for routing template management."""
    
    def test_default_templates_exist(self, service: VirtualRoutingService) -> None:
        """Test that default templates are initialized."""
        templates = service.list_templates()
        
        assert len(templates) >= 2  # Simple Machining and Assembly
    
    def test_create_template(self, service: VirtualRoutingService) -> None:
        """Test creating a new template."""
        template = service.create_template(
            name="Custom Template",
            description="Test template",
            category="custom",
            operations=[
                {
                    "operation_type": OperationType.CUSTOM,
                    "operation_name": "Custom Op",
                    "run_time_minutes": Decimal("10"),
                },
            ],
        )
        
        assert template.id is not None
        assert template.name == "Custom Template"
        assert len(template.operations) == 1
    
    def test_create_routing_from_template(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test creating a routing from a template."""
        # Get first template
        templates = service.list_templates()
        template = templates[0]
        
        routing = service.create_from_template(
            template_id=template.id,
            name="From Template",
        )
        
        assert routing is not None
        assert routing.source == RoutingSource.TEMPLATE
        assert routing.template_id == template.id
        assert len(routing.operations) > 0
    
    def test_template_time_multiplier(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test applying time multiplier when creating from template."""
        template = service.create_template(
            name="Test Template",
            operations=[
                {
                    "operation_type": OperationType.MACHINING,
                    "operation_name": "Machining",
                    "setup_time_minutes": Decimal("10"),
                    "run_time_minutes": Decimal("5"),
                },
            ],
        )
        
        routing = service.create_from_template(
            template_id=template.id,
            name="Multiplied",
            time_multiplier=Decimal("2.0"),
        )
        
        assert routing is not None
        assert routing.operations[0].setup_time_minutes == Decimal("20")
        assert routing.operations[0].run_time_minutes == Decimal("10")
    
    def test_template_usage_count_incremented(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that template usage count is incremented."""
        template = service.create_template(
            name="Track Usage",
            operations=[],
        )
        
        initial_count = template.usage_count
        
        service.create_from_template(template.id, "Usage 1")
        service.create_from_template(template.id, "Usage 2")
        
        assert template.usage_count == initial_count + 2
    
    def test_create_template_from_routing(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test creating a template from an existing routing."""
        template = service.create_template_from_routing(
            routing_id=sample_routing.id,
            template_name="From Routing",
            category="machining",
        )
        
        assert template is not None
        assert len(template.operations) == len(sample_routing.operations)
    
    def test_list_templates_by_category(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test filtering templates by category."""
        service.create_template(
            name="Category A",
            category="category_a",
            operations=[],
        )
        service.create_template(
            name="Category B",
            category="category_b",
            operations=[],
        )
        
        templates = service.list_templates(category="category_a")
        
        assert len(templates) == 1
        assert templates[0].name == "Category A"
    
    def test_delete_template_soft_delete(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that deleting a template is a soft delete."""
        template = service.create_template(name="To Delete", operations=[])
        
        result = service.delete_template(template.id)
        
        assert result is True
        assert template.is_active is False
        
        # Should not appear in active list
        templates = service.list_templates(active_only=True)
        assert template.id not in [t.id for t in templates]


# =============================================================================
# Test Routing Comparison
# =============================================================================


class TestRoutingComparison:
    """Tests for comparing routing options."""
    
    def test_compare_routings(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test comparing multiple routings."""
        # Create two routings with different costs
        routing1 = service.create_routing(name="Fast Expensive")
        routing1.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            run_time_minutes=Decimal("5"),
            labor_rate_per_hour=Decimal("50"),
        )
        
        routing2 = service.create_routing(name="Slow Cheap")
        routing2.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            run_time_minutes=Decimal("10"),
            labor_rate_per_hour=Decimal("20"),
        )
        
        comparison = service.compare_routings(
            routing_ids=[routing1.id, routing2.id],
            quantity=100,
        )
        
        assert comparison is not None
        assert len(comparison["routings"]) == 2
        assert comparison["best_cost_routing"] is not None
        assert comparison["best_time_routing"] is not None
    
    def test_compare_identifies_best_cost(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that comparison identifies lowest cost routing."""
        cheap = service.create_routing(name="Cheap")
        cheap.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            run_time_minutes=Decimal("10"),
            labor_rate_per_hour=Decimal("10"),
        )
        
        expensive = service.create_routing(name="Expensive")
        expensive.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            run_time_minutes=Decimal("10"),
            labor_rate_per_hour=Decimal("50"),
        )
        
        comparison = service.compare_routings(
            routing_ids=[cheap.id, expensive.id],
            quantity=100,
        )
        
        assert comparison["best_cost_routing"] == cheap.id
    
    def test_break_even_quantity(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test calculating break-even quantity."""
        routing = service.create_routing(
            name="Test",
            default_overhead_rate=Decimal("0"),
            default_machine_rate=Decimal("0"),
        )
        # Single operation with setup amortized over batch
        routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Machining",
            setup_time_minutes=Decimal("60"),  # 1 hour setup
            run_time_minutes=Decimal("6"),  # 0.1 hour per unit
            labor_rate_per_hour=Decimal("25"),
            overhead_rate_per_hour=Decimal("0"),
            machine_rate_per_hour=Decimal("0"),
        )
        
        # With batch_size=1, setup is amortized per unit
        # At 10 units: time per unit = 60/1 + 6 = 66 min = 1.1 hr
        # Labor = 1.1 * 25 * 10 = $275 total = $27.50/unit
        # Target $30/unit should be achievable at low quantities
        
        break_even = service.calculate_break_even_quantity(
            routing_id=routing.id,
            target_unit_cost=Decimal("30.00"),
        )
        
        assert break_even is not None
        assert break_even >= 1  # Should find some quantity


# =============================================================================
# Test Quick Builders
# =============================================================================


class TestQuickBuilders:
    """Tests for quick builder methods."""
    
    def test_create_simple_machining_routing(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test quick machining routing builder."""
        routing = service.create_simple_machining_routing(
            name="Quick Machining",
            setup_minutes=Decimal("15"),
            cycle_time_minutes=Decimal("5"),
        )
        
        assert routing is not None
        assert len(routing.operations) == 3  # Setup, Machining, Inspection
        
        # Find machining operation
        machining_op = next(
            op for op in routing.operations
            if op.operation_type == OperationType.MACHINING
        )
        assert machining_op.run_time_minutes == Decimal("5")
    
    def test_create_assembly_routing(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test quick assembly routing builder."""
        routing = service.create_assembly_routing(
            name="Quick Assembly",
            assembly_time_minutes=Decimal("10"),
            test_time_minutes=Decimal("5"),
        )
        
        assert routing is not None
        # Prep, Assembly, Test, Packaging = 4
        assert len(routing.operations) == 4
    
    def test_create_assembly_routing_without_test(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test assembly routing without test step."""
        routing = service.create_assembly_routing(
            name="Quick Assembly",
            assembly_time_minutes=Decimal("10"),
            test_time_minutes=Decimal("0"),
        )
        
        # Prep, Assembly, Packaging = 3 (no test)
        assert len(routing.operations) == 3
    
    def test_create_subcontract_routing(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test quick subcontract routing builder."""
        vendor_id = uuid4()
        
        routing = service.create_subcontract_routing(
            name="Heat Treatment",
            subcontract_cost_per_unit=Decimal("5.00"),
            lead_time_days=3,
            vendor_id=vendor_id,
        )
        
        assert routing is not None
        assert len(routing.operations) == 1
        
        op = routing.operations[0]
        assert op.is_subcontracted is True
        assert op.subcontract_cost == Decimal("5.00")
        assert op.subcontract_lead_days == 3


# =============================================================================
# Test Work Center Rates
# =============================================================================


class TestWorkCenterRates:
    """Tests for work center rate management."""
    
    def test_set_work_center_rates(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test setting work center rates."""
        wc_id = uuid4()
        
        service.set_work_center_rates(
            work_center_id=wc_id,
            labor_rate=Decimal("30.00"),
            overhead_rate=Decimal("40.00"),
            machine_rate=Decimal("20.00"),
        )
        
        rates = service.get_work_center_rates(wc_id)
        
        assert rates is not None
        assert rates["labor_rate"] == Decimal("30.00")
        assert rates["overhead_rate"] == Decimal("40.00")
        assert rates["machine_rate"] == Decimal("20.00")
    
    def test_get_nonexistent_work_center_rates(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test getting rates for unknown work center."""
        result = service.get_work_center_rates(uuid4())
        assert result is None


# =============================================================================
# Test Learning Curve
# =============================================================================


class TestLearningCurve:
    """Tests for learning curve factor."""
    
    def test_learning_curve_reduces_cost(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that learning curve factor reduces labor cost."""
        routing = service.create_routing(
            name="With Learning Curve",
            learning_curve_factor=Decimal("0.8"),  # 20% improvement
        )
        
        routing.add_operation(
            operation_type=OperationType.ASSEMBLY,
            operation_name="Assembly",
            run_time_minutes=Decimal("60"),
            labor_rate_per_hour=Decimal("25"),
        )
        
        costs = routing.calculate_costs(quantity=100)
        
        # Base labor cost: (60/60) * 25 * 100 = 2500
        # With 0.8 learning curve: 2500 * 0.8 = 2000
        assert costs["labor_cost"] == Decimal("2000.00")


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_routing_with_no_operations(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test calculations for routing with no operations."""
        routing = service.create_routing(name="Empty Routing")
        
        time = routing.calculate_total_time_minutes(quantity=100)
        costs = routing.calculate_costs(quantity=100)
        
        assert time == Decimal("0")
        assert costs["total_manufacturing_cost"] == Decimal("0")
    
    def test_zero_quantity(
        self,
        service: VirtualRoutingService,
        sample_routing: VirtualRouting,
    ) -> None:
        """Test calculations with zero quantity."""
        costs = sample_routing.calculate_costs(quantity=0)
        
        assert costs["cost_per_unit"] == Decimal("0")
    
    def test_optional_operations_excluded(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test that optional operations are excluded from totals."""
        routing = service.create_routing(name="With Optional")
        
        routing.add_operation(
            operation_type=OperationType.MACHINING,
            operation_name="Required",
            run_time_minutes=Decimal("10"),
        )
        routing.add_operation(
            operation_type=OperationType.FINISHING,
            operation_name="Optional Finishing",
            run_time_minutes=Decimal("10"),
            is_optional=True,
        )
        
        time = routing.calculate_total_time_minutes(quantity=1)
        
        # Only required operation counted
        assert time == Decimal("10")
    
    def test_estimate_costs_missing_routing(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test cost estimation for non-existent routing."""
        result = service.estimate_costs(uuid4(), quantity=100)
        assert result is None
    
    def test_create_from_nonexistent_template(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test creating from non-existent template."""
        result = service.create_from_template(uuid4(), "Test")
        assert result is None
    
    def test_clone_nonexistent_routing(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test cloning non-existent routing."""
        result = service.clone_routing(uuid4(), "Clone")
        assert result is None


# =============================================================================
# Test Full Integration
# =============================================================================


class TestFullIntegration:
    """Full integration tests."""
    
    def test_complete_quoting_workflow(
        self,
        service: VirtualRoutingService,
    ) -> None:
        """Test complete workflow for creating routing for quote."""
        quote_id = uuid4()
        line_item_id = uuid4()
        
        # 1. Create routing from template
        templates = service.list_templates()
        routing = service.create_from_template(
            template_id=templates[0].id,
            name="Quote Routing",
            quote_id=quote_id,
            quote_line_item_id=line_item_id,
        )
        
        assert routing is not None
        
        # 2. Add custom operation
        routing.add_operation(
            operation_type=OperationType.SUBCONTRACT,
            operation_name="Heat Treatment",
            is_subcontracted=True,
            subcontract_cost=Decimal("5.00"),
        )
        
        # 3. Estimate costs for different quantities
        estimates = []
        for qty in [100, 500, 1000]:
            estimate = service.estimate_costs(
                routing_id=routing.id,
                quantity=qty,
                material_cost=Decimal("1000.00"),
            )
            estimates.append(estimate)
        
        # Unit cost should decrease with quantity
        assert estimates[0]["unit_total_cost"] > estimates[1]["unit_total_cost"]
        assert estimates[1]["unit_total_cost"] > estimates[2]["unit_total_cost"]
        
        # 4. Save as template for future use
        template = service.create_template_from_routing(
            routing_id=routing.id,
            template_name="Quote Template",
            category="custom",
        )
        
        assert template is not None
        
        # 5. Compare with alternative routing
        alternative = service.create_assembly_routing(
            name="Alternative Process",
            assembly_time_minutes=Decimal("15"),
            quote_id=quote_id,
        )
        
        comparison = service.compare_routings(
            routing_ids=[routing.id, alternative.id],
            quantity=500,
            material_cost=Decimal("1000.00"),
        )
        
        assert comparison["best_cost_routing"] is not None
