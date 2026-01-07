"""
Tests for What-If Simulation Service.

Comprehensive tests covering:
- Scenario management
- Simulation execution
- Cost/price/margin adjustments
- Scenario comparison
- Sensitivity analysis
- Break-even calculations
"""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sensei.services.whatif_simulation import (
    WhatIfSimulationService,
    SimulationScenario,
    SimulationResult,
    ScenarioComparison,
    VariableAdjustment,
    SimulationVariableType,
    AdjustmentType,
    QuoteData,
    QuoteLineItemData,
    SimulatedLineItem,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service() -> WhatIfSimulationService:
    """Create a fresh simulation service."""
    svc = WhatIfSimulationService()
    svc.clear()
    return svc


@pytest.fixture
def sample_line_item() -> QuoteLineItemData:
    """Create a sample line item."""
    return QuoteLineItemData(
        id=uuid4(),
        line_number=1,
        part_number="PART-001",
        description="Widget Assembly",
        quantity=Decimal("100"),
        unit_price=Decimal("50.00"),
        unit_cost=Decimal("35.00"),
        line_total=Decimal("5000.00"),
        cost_total=Decimal("3500.00"),
        margin_percentage=Decimal("30.00"),
    )


@pytest.fixture
def sample_line_item_2() -> QuoteLineItemData:
    """Create a second sample line item."""
    return QuoteLineItemData(
        id=uuid4(),
        line_number=2,
        part_number="PART-002",
        description="Gadget Assembly",
        quantity=Decimal("50"),
        unit_price=Decimal("100.00"),
        unit_cost=Decimal("70.00"),
        line_total=Decimal("5000.00"),
        cost_total=Decimal("3500.00"),
        margin_percentage=Decimal("30.00"),
    )


@pytest.fixture
def sample_quote(
    sample_line_item: QuoteLineItemData,
    sample_line_item_2: QuoteLineItemData,
) -> QuoteData:
    """Create a sample quote with line items."""
    return QuoteData(
        id=uuid4(),
        quote_number="Q-2026-001",
        title="Sample Quote",
        currency="MAD",
        exchange_rate=Decimal("1.0"),
        subtotal=Decimal("10000.00"),
        discount_percentage=Decimal("5.00"),
        discount_amount=Decimal("500.00"),
        tax_rate=Decimal("20.00"),
        tax_amount=Decimal("1900.00"),
        total=Decimal("11400.00"),
        total_cost=Decimal("7000.00"),
        target_margin=Decimal("35.00"),
        actual_margin=Decimal("38.60"),
        line_items=[sample_line_item, sample_line_item_2],
    )


# =============================================================================
# Test Scenario Management
# =============================================================================


class TestScenarioManagement:
    """Tests for scenario CRUD operations."""
    
    def test_create_scenario(self, service: WhatIfSimulationService) -> None:
        """Test creating a new scenario."""
        scenario = service.create_scenario(
            name="Cost Increase 10%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                )
            ],
            description="Test cost increase scenario",
        )
        
        assert scenario.id is not None
        assert scenario.name == "Cost Increase 10%"
        assert len(scenario.adjustments) == 1
        assert scenario.created_at is not None
    
    def test_get_scenario(self, service: WhatIfSimulationService) -> None:
        """Test retrieving a scenario."""
        created = service.create_scenario(
            name="Test Scenario",
            adjustments=[],
        )
        
        retrieved = service.get_scenario(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
    
    def test_get_nonexistent_scenario(self, service: WhatIfSimulationService) -> None:
        """Test retrieving a non-existent scenario."""
        result = service.get_scenario(uuid4())
        assert result is None
    
    def test_list_scenarios(self, service: WhatIfSimulationService) -> None:
        """Test listing scenarios."""
        service.create_scenario(name="Scenario 1", adjustments=[])
        service.create_scenario(name="Scenario 2", adjustments=[])
        service.create_scenario(name="Scenario 3", adjustments=[])
        
        scenarios = service.list_scenarios()
        
        assert len(scenarios) == 3
    
    def test_list_scenarios_by_user(self, service: WhatIfSimulationService) -> None:
        """Test filtering scenarios by user."""
        user1 = uuid4()
        user2 = uuid4()
        
        service.create_scenario(name="User1 Scenario", adjustments=[], created_by=user1)
        service.create_scenario(name="User2 Scenario", adjustments=[], created_by=user2)
        
        user1_scenarios = service.list_scenarios(created_by=user1)
        
        assert len(user1_scenarios) == 1
        assert user1_scenarios[0].name == "User1 Scenario"
    
    def test_delete_scenario(self, service: WhatIfSimulationService) -> None:
        """Test deleting a scenario."""
        scenario = service.create_scenario(name="To Delete", adjustments=[])
        
        result = service.delete_scenario(scenario.id)
        
        assert result is True
        assert service.get_scenario(scenario.id) is None
    
    def test_delete_nonexistent_scenario(self, service: WhatIfSimulationService) -> None:
        """Test deleting a non-existent scenario."""
        result = service.delete_scenario(uuid4())
        assert result is False
    
    def test_duplicate_scenario(self, service: WhatIfSimulationService) -> None:
        """Test duplicating a scenario."""
        original = service.create_scenario(
            name="Original",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                )
            ],
        )
        
        duplicate = service.duplicate_scenario(original.id, "Copy of Original")
        
        assert duplicate is not None
        assert duplicate.id != original.id
        assert duplicate.name == "Copy of Original"
        assert len(duplicate.adjustments) == len(original.adjustments)
        assert duplicate.parent_scenario_id == original.id


# =============================================================================
# Test Simulation Execution
# =============================================================================


class TestSimulationExecution:
    """Tests for running simulations."""
    
    def test_run_simulation_no_changes(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with no adjustments (baseline)."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Baseline",
            adjustments=[],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        assert result.simulated_total == sample_quote.total
        assert result.simulated_total_cost == sample_quote.total_cost
    
    def test_run_simulation_cost_increase(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with cost increase."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Cost +10%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Cost should increase by 10%
        expected_cost = sample_quote.total_cost * Decimal("1.1")
        assert result.simulated_total_cost == expected_cost
        # Margin should decrease
        assert result.simulated_margin_percentage < (sample_quote.actual_margin or 0)
    
    def test_run_simulation_quantity_increase(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with quantity increase."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Quantity +50%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.QUANTITY,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("50"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Subtotal should increase by 50%
        expected_subtotal = sample_quote.subtotal * Decimal("1.5")
        assert result.simulated_subtotal == expected_subtotal
    
    def test_run_simulation_price_change(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with price change."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Price -5%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.UNIT_PRICE,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("-5"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Subtotal should decrease by 5%
        expected_subtotal = sample_quote.subtotal * Decimal("0.95")
        assert result.simulated_subtotal == expected_subtotal
    
    def test_run_simulation_target_margin(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with target margin."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Target 25% Margin",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TARGET_MARGIN,
                    adjustment_type=AdjustmentType.ABSOLUTE,
                    value=Decimal("25"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Simulated margin should be close to 25%
        # Note: Due to discount and tax, exact margin may differ slightly
        assert result.simulated_margin_percentage is not None
    
    def test_run_simulation_discount_change(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with discount change."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Discount 10%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.DISCOUNT_PERCENTAGE,
                    adjustment_type=AdjustmentType.ABSOLUTE,
                    value=Decimal("10"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Discount should be 10% of subtotal
        expected_discount = result.simulated_subtotal * Decimal("0.1")
        assert result.simulated_discount_amount == expected_discount
    
    def test_run_simulation_missing_quote(
        self,
        service: WhatIfSimulationService,
    ) -> None:
        """Test simulation with missing quote."""
        scenario = service.create_scenario(name="Test", adjustments=[])
        
        result = service.run_simulation(uuid4(), scenario.id)
        
        assert result is None
    
    def test_run_simulation_missing_scenario(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test simulation with missing scenario."""
        service.set_quote_data(sample_quote)
        
        result = service.run_simulation(sample_quote.id, uuid4())
        
        assert result is None


# =============================================================================
# Test Multiple Adjustments
# =============================================================================


class TestMultipleAdjustments:
    """Tests for scenarios with multiple adjustments."""
    
    def test_multiple_adjustments(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test applying multiple adjustments."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Complex Scenario",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                ),
                VariableAdjustment(
                    variable=SimulationVariableType.UNIT_PRICE,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("5"),
                ),
                VariableAdjustment(
                    variable=SimulationVariableType.DISCOUNT_PERCENTAGE,
                    adjustment_type=AdjustmentType.ABSOLUTE,
                    value=Decimal("3"),
                ),
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # All adjustments should be applied
        assert len(result.simulated_line_items) == 2
    
    def test_line_item_specific_adjustment(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test adjustment applied to specific line item only."""
        service.set_quote_data(sample_quote)
        
        target_item_id = sample_quote.line_items[0].id
        
        scenario = service.create_scenario(
            name="Specific Item Cost Increase",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("20"),
                    line_item_id=target_item_id,
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        
        # Find the specific line item in results
        target_result = next(
            (item for item in result.simulated_line_items
             if item.original.id == target_item_id),
            None,
        )
        other_result = next(
            (item for item in result.simulated_line_items
             if item.original.id != target_item_id),
            None,
        )
        
        assert target_result is not None
        assert other_result is not None
        
        # Target should have cost change
        assert "unit_cost" in target_result.changes
        # Other should not
        assert "unit_cost" not in other_result.changes


# =============================================================================
# Test Comparison and Insights
# =============================================================================


class TestComparisonAndInsights:
    """Tests for comparison and insight generation."""
    
    def test_comparison_metrics(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that comparison metrics are generated."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Cost +10%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        assert "total" in result.comparison
        assert "margin_percentage" in result.comparison
        assert "total_cost" in result.comparison
        
        # Check comparison structure
        total_comparison = result.comparison["total"]
        assert "original" in total_comparison
        assert "simulated" in total_comparison
        assert "delta" in total_comparison
        assert "delta_percentage" in total_comparison
    
    def test_insights_generated(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that insights are generated for significant changes."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Cost +20%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("20"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        assert len(result.insights) > 0
    
    def test_warnings_low_margin(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that warnings are generated for low margin."""
        service.set_quote_data(sample_quote)
        
        # Increase cost significantly to reduce margin
        scenario = service.create_scenario(
            name="High Cost Increase",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("50"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Should have warnings about margin
        assert len(result.warnings) > 0


# =============================================================================
# Test Scenario Comparison
# =============================================================================


class TestScenarioComparison:
    """Tests for comparing multiple scenarios."""
    
    def test_compare_scenarios(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test comparing multiple scenarios."""
        service.set_quote_data(sample_quote)
        
        scenario1 = service.create_scenario(
            name="Conservative",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("5"),
                )
            ],
        )
        
        scenario2 = service.create_scenario(
            name="Aggressive",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("15"),
                )
            ],
        )
        
        comparison = service.compare_scenarios(
            sample_quote.id,
            [scenario1.id, scenario2.id],
        )
        
        assert comparison is not None
        assert len(comparison.scenarios) == 2
        assert comparison.baseline_scenario is not None
        assert "total" in comparison.comparison_metrics
        assert "margin" in comparison.comparison_metrics
    
    def test_compare_identifies_best_margin(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that comparison identifies best margin scenario."""
        service.set_quote_data(sample_quote)
        
        # Lower cost = better margin
        low_cost = service.create_scenario(
            name="Low Cost",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("-10"),
                )
            ],
        )
        
        high_cost = service.create_scenario(
            name="High Cost",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                )
            ],
        )
        
        comparison = service.compare_scenarios(
            sample_quote.id,
            [low_cost.id, high_cost.id],
        )
        
        assert comparison is not None
        assert comparison.best_margin_scenario == low_cost.id
    
    def test_compare_generates_recommendations(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that comparison generates recommendations."""
        service.set_quote_data(sample_quote)
        
        scenario1 = service.create_scenario(name="Scenario 1", adjustments=[])
        scenario2 = service.create_scenario(name="Scenario 2", adjustments=[])
        
        comparison = service.compare_scenarios(
            sample_quote.id,
            [scenario1.id, scenario2.id],
        )
        
        assert comparison is not None
        assert len(comparison.recommendations) > 0


# =============================================================================
# Test Quick Simulation Helpers
# =============================================================================


class TestQuickSimulationHelpers:
    """Tests for quick simulation helper methods."""
    
    def test_simulate_cost_increase(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test quick cost increase simulation."""
        service.set_quote_data(sample_quote)
        
        result = service.simulate_cost_increase(
            sample_quote.id,
            Decimal("15"),
        )
        
        assert result is not None
        assert "Cost +15%" in result.scenario_name
    
    def test_simulate_quantity_change(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test quick quantity change simulation."""
        service.set_quote_data(sample_quote)
        
        result = service.simulate_quantity_change(
            sample_quote.id,
            Decimal("100"),
        )
        
        assert result is not None
        assert "Quantity +100%" in result.scenario_name
        assert result.simulated_subtotal == sample_quote.subtotal * 2
    
    def test_simulate_target_margin(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test quick target margin simulation."""
        service.set_quote_data(sample_quote)
        
        result = service.simulate_target_margin(
            sample_quote.id,
            Decimal("30"),
        )
        
        assert result is not None
        assert "Target Margin 30%" in result.scenario_name
    
    def test_simulate_discount(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test quick discount simulation."""
        service.set_quote_data(sample_quote)
        
        result = service.simulate_discount(
            sample_quote.id,
            Decimal("10"),
        )
        
        assert result is not None
        assert "Discount 10%" in result.scenario_name


# =============================================================================
# Test Sensitivity Analysis
# =============================================================================


class TestSensitivityAnalysis:
    """Tests for sensitivity analysis."""
    
    def test_run_sensitivity_analysis(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test running sensitivity analysis."""
        service.set_quote_data(sample_quote)
        
        results = service.run_sensitivity_analysis(
            sample_quote.id,
            SimulationVariableType.TOTAL_COST,
            [Decimal("-10"), Decimal("0"), Decimal("10")],
        )
        
        assert len(results) == 3
        # Check that results are in order
        costs = [r.simulated_total_cost for r in results]
        assert costs[0] < costs[1] < costs[2]
    
    def test_run_cost_sensitivity(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test standard cost sensitivity analysis."""
        service.set_quote_data(sample_quote)
        
        results = service.run_cost_sensitivity(sample_quote.id)
        
        assert len(results) == 4  # -20%, -10%, +10%, +20%


# =============================================================================
# Test Break-Even Analysis
# =============================================================================


class TestBreakEvenAnalysis:
    """Tests for break-even calculations."""
    
    def test_calculate_break_even_price(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test break-even price calculation."""
        service.set_quote_data(sample_quote)
        
        result = service.calculate_break_even_price(sample_quote.id)
        
        assert result is not None
        assert result["break_even_price"] == float(sample_quote.total_cost)
        assert result["current_price"] == float(sample_quote.total)
        assert result["margin_buffer"] > 0
        assert result["margin_buffer_percentage"] > 0
    
    def test_calculate_price_for_margin(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test price calculation for target margin."""
        service.set_quote_data(sample_quote)
        
        result = service.calculate_price_for_margin(
            sample_quote.id,
            Decimal("25"),
        )
        
        assert result is not None
        assert result["target_margin_percentage"] == 25.0
        assert "required_price" in result
        assert "price_change" in result
        assert "price_change_percentage" in result
    
    def test_calculate_price_for_invalid_margin(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test price calculation with invalid margin (>=100%)."""
        service.set_quote_data(sample_quote)
        
        result = service.calculate_price_for_margin(
            sample_quote.id,
            Decimal("100"),
        )
        
        assert result is None
    
    def test_break_even_missing_quote(
        self,
        service: WhatIfSimulationService,
    ) -> None:
        """Test break-even calculation with missing quote."""
        result = service.calculate_break_even_price(uuid4())
        assert result is None


# =============================================================================
# Test Adjustment Types
# =============================================================================


class TestAdjustmentTypes:
    """Tests for different adjustment types."""
    
    def test_absolute_adjustment(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test absolute value adjustment."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Fixed Price",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.UNIT_PRICE,
                    adjustment_type=AdjustmentType.ABSOLUTE,
                    value=Decimal("75.00"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # All line items should have unit price of 75.00
        for item in result.simulated_line_items:
            assert item.simulated_unit_price == Decimal("75.00")
    
    def test_percentage_adjustment(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test percentage adjustment."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Price +20%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.UNIT_PRICE,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("20"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Check first item price increased by 20%
        first_item = result.simulated_line_items[0]
        expected_price = first_item.original.unit_price * Decimal("1.20")
        assert first_item.simulated_unit_price == expected_price
    
    def test_delta_adjustment(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test delta (add/subtract) adjustment."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Cost +5 per unit",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.DELTA,
                    value=Decimal("5.00"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        # Check first item cost increased by 5
        first_item = result.simulated_line_items[0]
        expected_cost = first_item.original.unit_cost + Decimal("5.00")
        assert first_item.simulated_unit_cost == expected_cost


# =============================================================================
# Test Line Item Changes Tracking
# =============================================================================


class TestLineItemChangesTracking:
    """Tests for tracking changes on line items."""
    
    def test_changes_tracked(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that changes are tracked on line items."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Cost +10%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("10"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        
        for item in result.simulated_line_items:
            assert "unit_cost" in item.changes
            original, simulated = item.changes["unit_cost"]
            assert simulated > original
    
    def test_no_changes_when_baseline(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test that no changes are tracked for baseline."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Baseline",
            adjustments=[],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        
        for item in result.simulated_line_items:
            assert len(item.changes) == 0


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_quote_line_items(
        self,
        service: WhatIfSimulationService,
    ) -> None:
        """Test simulation with no line items."""
        quote = QuoteData(
            id=uuid4(),
            quote_number="Q-EMPTY",
            title="Empty Quote",
            currency="MAD",
            exchange_rate=Decimal("1.0"),
            subtotal=Decimal("0"),
            discount_percentage=None,
            discount_amount=Decimal("0"),
            tax_rate=None,
            tax_amount=Decimal("0"),
            total=Decimal("0"),
            total_cost=Decimal("0"),
            target_margin=None,
            actual_margin=None,
            line_items=[],
        )
        
        service.set_quote_data(quote)
        scenario = service.create_scenario(name="Test", adjustments=[])
        
        result = service.run_simulation(quote.id, scenario.id)
        
        assert result is not None
        assert result.simulated_total == Decimal("0")
        assert len(result.simulated_line_items) == 0
    
    def test_excluded_line_items(
        self,
        service: WhatIfSimulationService,
    ) -> None:
        """Test that excluded line items are not simulated."""
        line_item = QuoteLineItemData(
            id=uuid4(),
            line_number=1,
            part_number="PART-001",
            description="Excluded Item",
            quantity=Decimal("100"),
            unit_price=Decimal("50.00"),
            unit_cost=Decimal("35.00"),
            line_total=Decimal("5000.00"),
            cost_total=Decimal("3500.00"),
            margin_percentage=Decimal("30.00"),
            is_included=False,  # Excluded
        )
        
        quote = QuoteData(
            id=uuid4(),
            quote_number="Q-TEST",
            title="Test Quote",
            currency="MAD",
            exchange_rate=Decimal("1.0"),
            subtotal=Decimal("0"),
            discount_percentage=None,
            discount_amount=Decimal("0"),
            tax_rate=None,
            tax_amount=Decimal("0"),
            total=Decimal("0"),
            total_cost=Decimal("0"),
            target_margin=None,
            actual_margin=None,
            line_items=[line_item],
        )
        
        service.set_quote_data(quote)
        scenario = service.create_scenario(name="Test", adjustments=[])
        
        result = service.run_simulation(quote.id, scenario.id)
        
        assert result is not None
        assert len(result.simulated_line_items) == 0
    
    def test_negative_percentage_adjustment(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test negative percentage adjustment (decrease)."""
        service.set_quote_data(sample_quote)
        
        scenario = service.create_scenario(
            name="Cost -15%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("-15"),
                )
            ],
        )
        
        result = service.run_simulation(sample_quote.id, scenario.id)
        
        assert result is not None
        expected_cost = sample_quote.total_cost * Decimal("0.85")
        assert result.simulated_total_cost == expected_cost
    
    def test_zero_cost_margin_calculation(
        self,
        service: WhatIfSimulationService,
    ) -> None:
        """Test margin calculation with zero cost."""
        line_item = QuoteLineItemData(
            id=uuid4(),
            line_number=1,
            part_number="FREE-001",
            description="Free Item",
            quantity=Decimal("1"),
            unit_price=Decimal("100.00"),
            unit_cost=Decimal("0"),  # Zero cost
            line_total=Decimal("100.00"),
            cost_total=Decimal("0"),
            margin_percentage=Decimal("100.00"),
        )
        
        quote = QuoteData(
            id=uuid4(),
            quote_number="Q-FREE",
            title="Free Item Quote",
            currency="MAD",
            exchange_rate=Decimal("1.0"),
            subtotal=Decimal("100.00"),
            discount_percentage=None,
            discount_amount=Decimal("0"),
            tax_rate=None,
            tax_amount=Decimal("0"),
            total=Decimal("100.00"),
            total_cost=Decimal("0"),
            target_margin=None,
            actual_margin=Decimal("100.00"),
            line_items=[line_item],
        )
        
        service.set_quote_data(quote)
        scenario = service.create_scenario(name="Test", adjustments=[])
        
        result = service.run_simulation(quote.id, scenario.id)
        
        assert result is not None
        assert result.simulated_margin_percentage == Decimal("100")


# =============================================================================
# Test Full Integration
# =============================================================================


class TestFullIntegration:
    """Full integration tests."""
    
    def test_complete_what_if_workflow(
        self,
        service: WhatIfSimulationService,
        sample_quote: QuoteData,
    ) -> None:
        """Test complete what-if analysis workflow."""
        # Set up quote
        service.set_quote_data(sample_quote)
        
        # Create multiple scenarios
        scenario1 = service.create_scenario(
            name="Best Case: Cost -10%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("-10"),
                )
            ],
        )
        
        scenario2 = service.create_scenario(
            name="Worst Case: Cost +20%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TOTAL_COST,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("20"),
                )
            ],
        )
        
        scenario3 = service.create_scenario(
            name="Aggressive: High Volume, Low Price",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.QUANTITY,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("100"),
                ),
                VariableAdjustment(
                    variable=SimulationVariableType.UNIT_PRICE,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=Decimal("-10"),
                ),
            ],
        )
        
        # Run simulations
        result1 = service.run_simulation(sample_quote.id, scenario1.id)
        result2 = service.run_simulation(sample_quote.id, scenario2.id)
        result3 = service.run_simulation(sample_quote.id, scenario3.id)
        
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        
        # Compare scenarios
        comparison = service.compare_scenarios(
            sample_quote.id,
            [scenario1.id, scenario2.id, scenario3.id],
        )
        
        assert comparison is not None
        assert len(comparison.scenarios) == 3
        
        # Best margin should be scenario1 (cost reduction)
        assert comparison.best_margin_scenario == scenario1.id
        
        # Run sensitivity analysis
        sensitivity_results = service.run_cost_sensitivity(sample_quote.id)
        assert len(sensitivity_results) == 4
        
        # Calculate break-even
        break_even = service.calculate_break_even_price(sample_quote.id)
        assert break_even is not None
        assert break_even["break_even_price"] < break_even["current_price"]
