"""
What-If Simulation Service.

Provides scenario planning capabilities for quotes without altering the draft.
Allows users to explore "what-if" scenarios like:
- "If material cost +10%, margin = ?"
- "If quantity doubles, unit price = ?"
- "If we reduce margin to X%, price = ?"
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class SimulationVariableType(str, Enum):
    """Types of variables that can be adjusted in simulations."""
    
    # Cost adjustments
    MATERIAL_COST = "material_cost"
    LABOR_COST = "labor_cost"
    OVERHEAD_COST = "overhead_cost"
    TOOLING_COST = "tooling_cost"
    FREIGHT_COST = "freight_cost"
    TOTAL_COST = "total_cost"
    
    # Pricing adjustments
    UNIT_PRICE = "unit_price"
    DISCOUNT_PERCENTAGE = "discount_percentage"
    DISCOUNT_AMOUNT = "discount_amount"
    
    # Margin adjustments
    TARGET_MARGIN = "target_margin"
    MARGIN_PERCENTAGE = "margin_percentage"
    
    # Volume adjustments
    QUANTITY = "quantity"
    
    # Other adjustments
    TAX_RATE = "tax_rate"
    EXCHANGE_RATE = "exchange_rate"
    LEAD_TIME = "lead_time"
    SCRAP_RATE = "scrap_rate"
    YIELD_RATE = "yield_rate"


class AdjustmentType(str, Enum):
    """How the adjustment is applied."""
    
    ABSOLUTE = "absolute"  # Set to exact value
    PERCENTAGE = "percentage"  # Adjust by percentage
    DELTA = "delta"  # Add/subtract amount


class ComparisonType(str, Enum):
    """What to compare scenarios against."""
    
    BASELINE = "baseline"
    PREVIOUS_SCENARIO = "previous_scenario"
    SPECIFIC_SCENARIO = "specific_scenario"


@dataclass
class VariableAdjustment:
    """An adjustment to a simulation variable."""
    
    variable: SimulationVariableType
    adjustment_type: AdjustmentType
    value: Decimal
    line_item_id: UUID | None = None  # If None, applies to all line items
    description: str | None = None


@dataclass
class QuoteLineItemData:
    """Quote line item data for simulation."""
    
    id: UUID
    line_number: int
    part_number: str | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    unit_cost: Decimal
    line_total: Decimal
    cost_total: Decimal
    margin_percentage: Decimal
    discount_percentage: Decimal = field(default_factory=lambda: Decimal("0"))
    discount_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    nre_cost: Decimal | None = None
    tooling_cost: Decimal | None = None
    lead_time_days: int | None = None
    is_included: bool = True
    is_optional: bool = False


@dataclass
class QuoteData:
    """Quote data for simulation."""
    
    id: UUID
    quote_number: str
    title: str
    currency: str
    exchange_rate: Decimal
    subtotal: Decimal
    discount_percentage: Decimal | None
    discount_amount: Decimal
    tax_rate: Decimal | None
    tax_amount: Decimal
    total: Decimal
    total_cost: Decimal
    target_margin: Decimal | None
    actual_margin: Decimal | None
    line_items: list[QuoteLineItemData] = field(default_factory=list)


@dataclass
class SimulationScenario:
    """A single simulation scenario."""
    
    id: UUID
    name: str
    description: str | None
    adjustments: list[VariableAdjustment]
    created_at: datetime
    created_by: UUID | None = None
    is_baseline: bool = False
    parent_scenario_id: UUID | None = None


@dataclass
class SimulatedLineItem:
    """Simulated line item with calculated values."""
    
    original: QuoteLineItemData
    simulated_quantity: Decimal
    simulated_unit_price: Decimal
    simulated_unit_cost: Decimal
    simulated_line_total: Decimal
    simulated_cost_total: Decimal
    simulated_margin_percentage: Decimal
    simulated_discount_amount: Decimal
    changes: dict[str, tuple[Decimal, Decimal]] = field(default_factory=dict)
    # e.g., {"unit_cost": (10.00, 11.00)} = original -> simulated


@dataclass
class SimulationResult:
    """Result of running a simulation."""
    
    scenario_id: UUID
    scenario_name: str
    baseline: QuoteData
    simulated_subtotal: Decimal
    simulated_discount_amount: Decimal
    simulated_tax_amount: Decimal
    simulated_total: Decimal
    simulated_total_cost: Decimal
    simulated_margin_percentage: Decimal
    simulated_line_items: list[SimulatedLineItem]
    comparison: dict[str, dict[str, Any]] = field(default_factory=dict)
    # e.g., {"total": {"original": 100, "simulated": 110, "delta": 10, "delta_pct": 10}}
    insights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScenarioComparison:
    """Comparison between multiple scenarios."""
    
    baseline_scenario: SimulationResult
    scenarios: list[SimulationResult]
    comparison_metrics: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    best_margin_scenario: UUID | None = None
    lowest_price_scenario: UUID | None = None
    recommendations: list[str] = field(default_factory=list)


class WhatIfSimulationService:
    """Service for what-if scenario planning on quotes."""
    
    def __init__(self) -> None:
        """Initialize the simulation service."""
        self._scenarios: dict[UUID, SimulationScenario] = {}
        self._results: dict[UUID, SimulationResult] = {}
        self._quotes: dict[UUID, QuoteData] = {}
        self._max_results: int = 1000
        self._result_ttl: timedelta = timedelta(days=30)
        self._max_scenarios: int = 1000
        self._scenario_ttl: timedelta = timedelta(days=90)

    def _prune_results(self) -> None:
        """Prune old simulation results to avoid unbounded growth."""
        cutoff = datetime.now(timezone.utc) - self._result_ttl
        stale_ids = [
            sid for sid, result in self._results.items()
            if result.calculated_at < cutoff
        ]
        for sid in stale_ids:
            del self._results[sid]

        excess = len(self._results) - self._max_results
        if excess > 0:
            oldest = sorted(self._results.items(), key=lambda item: item[1].calculated_at)
            for sid, _ in oldest[:excess]:
                del self._results[sid]

    def _prune_scenarios(self) -> None:
        """Prune old scenarios to avoid unbounded growth."""
        cutoff = datetime.now(timezone.utc) - self._scenario_ttl
        stale_ids = [
            sid for sid, scenario in self._scenarios.items()
            if scenario.created_at < cutoff
        ]
        for sid in stale_ids:
            del self._scenarios[sid]
    
    # =========================================================================
    # Scenario Management
    # =========================================================================
    
    def create_scenario(
        self,
        name: str,
        adjustments: list[VariableAdjustment],
        description: str | None = None,
        created_by: UUID | None = None,
        parent_scenario_id: UUID | None = None,
    ) -> SimulationScenario:
        """Create a new simulation scenario."""
        scenario_id = uuid4()
        scenario = SimulationScenario(
            id=scenario_id,
            name=name,
            description=description,
            adjustments=adjustments,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            is_baseline=False,
            parent_scenario_id=parent_scenario_id,
        )
        self._scenarios[scenario_id] = scenario
        self._prune_scenarios()
        return scenario
    
    def get_scenario(self, scenario_id: UUID) -> SimulationScenario | None:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)
    
    def list_scenarios(
        self,
        created_by: UUID | None = None,
        limit: int = 50,
    ) -> list[SimulationScenario]:
        """List scenarios with optional filtering."""
        scenarios = list(self._scenarios.values())
        
        if created_by:
            scenarios = [s for s in scenarios if s.created_by == created_by]
        
        scenarios.sort(key=lambda s: s.created_at, reverse=True)
        return scenarios[:limit]
    
    def delete_scenario(self, scenario_id: UUID) -> bool:
        """Delete a scenario."""
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            if scenario_id in self._results:
                del self._results[scenario_id]
            return True
        return False
    
    def duplicate_scenario(
        self,
        scenario_id: UUID,
        new_name: str,
    ) -> SimulationScenario | None:
        """Duplicate an existing scenario."""
        original = self._scenarios.get(scenario_id)
        if not original:
            return None
        
        return self.create_scenario(
            name=new_name,
            adjustments=original.adjustments.copy(),
            description=f"Copy of {original.name}",
            created_by=original.created_by,
            parent_scenario_id=original.id,
        )
    
    # =========================================================================
    # Quote Data Management
    # =========================================================================
    
    def set_quote_data(self, quote: QuoteData) -> None:
        """Set quote data for simulation."""
        self._quotes[quote.id] = quote
    
    def get_quote_data(self, quote_id: UUID) -> QuoteData | None:
        """Get quote data."""
        return self._quotes.get(quote_id)
    
    # =========================================================================
    # Simulation Execution
    # =========================================================================
    
    def run_simulation(
        self,
        quote_id: UUID,
        scenario_id: UUID,
    ) -> SimulationResult | None:
        """
        Run a simulation scenario on a quote.
        
        Returns the simulated quote data without modifying the original.
        """
        quote = self._quotes.get(quote_id)
        scenario = self._scenarios.get(scenario_id)
        
        if not quote or not scenario:
            return None
        
        # Start with baseline values
        simulated_line_items: list[SimulatedLineItem] = []
        
        for line_item in quote.line_items:
            if not line_item.is_included:
                continue
            
            simulated = self._simulate_line_item(line_item, scenario.adjustments)
            simulated_line_items.append(simulated)
        
        # Calculate totals
        simulated_subtotal = sum(
            (item.simulated_line_total for item in simulated_line_items),
            Decimal(0),
        )
        simulated_total_cost = sum(
            (item.simulated_cost_total for item in simulated_line_items),
            Decimal(0),
        )
        
        # Apply discount adjustments
        simulated_discount_amount = self._calculate_simulated_discount(
            simulated_subtotal,
            quote,
            scenario.adjustments,
        )
        
        after_discount = simulated_subtotal - simulated_discount_amount
        
        # Apply tax adjustments
        simulated_tax_amount = self._calculate_simulated_tax(
            after_discount,
            quote,
            scenario.adjustments,
        )
        
        simulated_total = after_discount + simulated_tax_amount
        
        # Calculate margin
        if simulated_total > 0:
            simulated_margin = (
                (simulated_total - simulated_total_cost) / simulated_total
            ) * 100
        else:
            simulated_margin = Decimal("0")
        
        # Build comparison
        comparison = self._build_comparison(
            quote,
            simulated_subtotal,
            simulated_discount_amount,
            simulated_tax_amount,
            simulated_total,
            simulated_total_cost,
            simulated_margin,
        )
        
        # Generate insights
        insights = self._generate_insights(quote, comparison)
        warnings = self._generate_warnings(quote, simulated_margin, comparison)
        
        result = SimulationResult(
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            baseline=quote,
            simulated_subtotal=simulated_subtotal,
            simulated_discount_amount=simulated_discount_amount,
            simulated_tax_amount=simulated_tax_amount,
            simulated_total=simulated_total,
            simulated_total_cost=simulated_total_cost,
            simulated_margin_percentage=simulated_margin,
            simulated_line_items=simulated_line_items,
            comparison=comparison,
            insights=insights,
            warnings=warnings,
        )
        
        self._results[scenario_id] = result
        self._prune_results()
        return result
    
    def _simulate_line_item(
        self,
        line_item: QuoteLineItemData,
        adjustments: list[VariableAdjustment],
    ) -> SimulatedLineItem:
        """Simulate adjustments on a single line item."""
        simulated_quantity = line_item.quantity
        simulated_unit_price = line_item.unit_price
        simulated_unit_cost = line_item.unit_cost
        simulated_discount = line_item.discount_amount
        
        changes: dict[str, tuple[Decimal, Decimal]] = {}
        
        for adjustment in adjustments:
            # Check if adjustment applies to this line item
            if adjustment.line_item_id and adjustment.line_item_id != line_item.id:
                continue
            
            if adjustment.variable == SimulationVariableType.QUANTITY:
                new_value = self._apply_adjustment(
                    simulated_quantity,
                    adjustment,
                )
                if new_value != simulated_quantity:
                    changes["quantity"] = (simulated_quantity, new_value)
                    simulated_quantity = new_value
            
            elif adjustment.variable == SimulationVariableType.UNIT_PRICE:
                new_value = self._apply_adjustment(
                    simulated_unit_price,
                    adjustment,
                )
                if new_value != simulated_unit_price:
                    changes["unit_price"] = (simulated_unit_price, new_value)
                    simulated_unit_price = new_value
            
            elif adjustment.variable in (
                SimulationVariableType.MATERIAL_COST,
                SimulationVariableType.LABOR_COST,
                SimulationVariableType.TOTAL_COST,
            ):
                new_value = self._apply_adjustment(
                    simulated_unit_cost,
                    adjustment,
                )
                if new_value != simulated_unit_cost:
                    changes["unit_cost"] = (simulated_unit_cost, new_value)
                    simulated_unit_cost = new_value
            
            elif adjustment.variable == SimulationVariableType.DISCOUNT_AMOUNT:
                new_value = self._apply_adjustment(
                    simulated_discount,
                    adjustment,
                )
                if new_value != simulated_discount:
                    changes["discount_amount"] = (simulated_discount, new_value)
                    simulated_discount = new_value
            
            elif adjustment.variable == SimulationVariableType.TARGET_MARGIN:
                # Calculate price from target margin
                if simulated_unit_cost > 0:
                    target_margin_pct = adjustment.value / 100
                    # price = cost / (1 - margin)
                    new_price = simulated_unit_cost / (1 - target_margin_pct)
                    if new_price != simulated_unit_price:
                        changes["unit_price"] = (simulated_unit_price, new_price)
                        simulated_unit_price = new_price
        
        # Calculate line totals
        simulated_line_total = (
            simulated_quantity * simulated_unit_price - simulated_discount
        )
        simulated_cost_total = simulated_quantity * simulated_unit_cost
        
        # Calculate margin
        if simulated_line_total > 0:
            simulated_margin = (
                (simulated_line_total - simulated_cost_total) / simulated_line_total
            ) * 100
        else:
            simulated_margin = Decimal("0")
        
        return SimulatedLineItem(
            original=line_item,
            simulated_quantity=simulated_quantity,
            simulated_unit_price=simulated_unit_price,
            simulated_unit_cost=simulated_unit_cost,
            simulated_line_total=simulated_line_total,
            simulated_cost_total=simulated_cost_total,
            simulated_margin_percentage=simulated_margin,
            simulated_discount_amount=simulated_discount,
            changes=changes,
        )
    
    def _apply_adjustment(
        self,
        original_value: Decimal,
        adjustment: VariableAdjustment,
    ) -> Decimal:
        """Apply an adjustment to a value."""
        if adjustment.adjustment_type == AdjustmentType.ABSOLUTE:
            return adjustment.value
        
        elif adjustment.adjustment_type == AdjustmentType.PERCENTAGE:
            # +10 means increase by 10%
            multiplier = (100 + adjustment.value) / 100
            return original_value * multiplier
        
        elif adjustment.adjustment_type == AdjustmentType.DELTA:
            return original_value + adjustment.value
        
        return original_value
    
    def _calculate_simulated_discount(
        self,
        subtotal: Decimal,
        quote: QuoteData,
        adjustments: list[VariableAdjustment],
    ) -> Decimal:
        """Calculate simulated discount amount."""
        discount_pct = quote.discount_percentage or Decimal("0")
        discount_amount = quote.discount_amount
        
        for adjustment in adjustments:
            if adjustment.variable == SimulationVariableType.DISCOUNT_PERCENTAGE:
                discount_pct = self._apply_adjustment(discount_pct, adjustment)
            elif adjustment.variable == SimulationVariableType.DISCOUNT_AMOUNT:
                discount_amount = self._apply_adjustment(discount_amount, adjustment)
        
        if discount_pct > 0:
            return subtotal * discount_pct / 100
        
        return discount_amount
    
    def _calculate_simulated_tax(
        self,
        after_discount: Decimal,
        quote: QuoteData,
        adjustments: list[VariableAdjustment],
    ) -> Decimal:
        """Calculate simulated tax amount."""
        tax_rate = quote.tax_rate or Decimal("0")
        
        for adjustment in adjustments:
            if adjustment.variable == SimulationVariableType.TAX_RATE:
                tax_rate = self._apply_adjustment(tax_rate, adjustment)
        
        if tax_rate > 0:
            return after_discount * tax_rate / 100
        
        return Decimal("0")
    
    def _build_comparison(
        self,
        quote: QuoteData,
        simulated_subtotal: Decimal,
        simulated_discount: Decimal,
        simulated_tax: Decimal,
        simulated_total: Decimal,
        simulated_cost: Decimal,
        simulated_margin: Decimal,
    ) -> dict[str, dict[str, Any]]:
        """Build comparison dictionary between original and simulated values."""
        comparison = {}
        
        def make_comparison(name: str, original: Decimal, simulated: Decimal) -> None:
            delta = simulated - original
            delta_pct = (delta / original * 100) if original != 0 else Decimal("0")
            comparison[name] = {
                "original": float(original),
                "simulated": float(simulated),
                "delta": float(delta),
                "delta_percentage": float(delta_pct),
            }
        
        make_comparison("subtotal", quote.subtotal, simulated_subtotal)
        make_comparison("discount_amount", quote.discount_amount, simulated_discount)
        make_comparison("tax_amount", quote.tax_amount, simulated_tax)
        make_comparison("total", quote.total, simulated_total)
        make_comparison("total_cost", quote.total_cost, simulated_cost)
        make_comparison(
            "margin_percentage",
            quote.actual_margin or Decimal("0"),
            simulated_margin,
        )
        
        return comparison
    
    def _generate_insights(
        self,
        quote: QuoteData,
        comparison: dict[str, dict[str, Any]],
    ) -> list[str]:
        """Generate insights from the simulation."""
        insights = []
        
        # Total change
        total_delta = comparison["total"]["delta_percentage"]
        if abs(total_delta) > 0.1:
            direction = "increases" if total_delta > 0 else "decreases"
            insights.append(
                f"Quote total {direction} by {abs(total_delta):.1f}%"
            )
        
        # Margin change
        margin_delta = comparison["margin_percentage"]["delta"]
        if abs(margin_delta) > 0.5:
            direction = "increases" if margin_delta > 0 else "decreases"
            insights.append(
                f"Margin {direction} by {abs(margin_delta):.1f} percentage points"
            )
        
        # Cost change
        cost_delta = comparison["total_cost"]["delta_percentage"]
        if abs(cost_delta) > 0.1:
            direction = "increase" if cost_delta > 0 else "decrease"
            insights.append(
                f"Total costs {direction} by {abs(cost_delta):.1f}%"
            )
        
        return insights
    
    def _generate_warnings(
        self,
        quote: QuoteData,
        simulated_margin: Decimal,
        comparison: dict[str, dict[str, Any]],
    ) -> list[str]:
        """Generate warnings for the simulation."""
        warnings = []
        
        # Low margin warning
        if simulated_margin < 10:
            warnings.append(
                f"Warning: Simulated margin ({simulated_margin:.1f}%) is below 10%"
            )
        
        # Negative margin warning
        if simulated_margin < 0:
            warnings.append("Critical: Simulated margin is negative (loss scenario)")
        
        # Large price increase
        total_delta = comparison["total"]["delta_percentage"]
        if total_delta > 15:
            warnings.append(
                f"Warning: Price increase of {total_delta:.1f}% may impact competitiveness"
            )
        
        return warnings
    
    # =========================================================================
    # Scenario Comparison
    # =========================================================================
    
    def compare_scenarios(
        self,
        quote_id: UUID,
        scenario_ids: list[UUID],
    ) -> ScenarioComparison | None:
        """
        Compare multiple simulation scenarios.
        
        Returns a comparison showing metrics across all scenarios.
        """
        quote = self._quotes.get(quote_id)
        if not quote:
            return None
        
        # Run simulations
        results: list[SimulationResult] = []
        for scenario_id in scenario_ids:
            result = self.run_simulation(quote_id, scenario_id)
            if result:
                results.append(result)
        
        if not results:
            return None
        
        # Create baseline result (no changes)
        baseline_scenario = self.create_scenario(
            name="Baseline (Current)",
            adjustments=[],
        )
        baseline_result = self.run_simulation(quote_id, baseline_scenario.id)
        
        if not baseline_result:
            return None
        
        # Build comparison metrics
        comparison_metrics: dict[str, list[dict[str, Any]]] = {
            "total": [],
            "margin": [],
            "cost": [],
        }
        
        best_margin_id = None
        best_margin = Decimal("-999")
        lowest_price_id = None
        lowest_price = Decimal("999999999")
        
        for result in results:
            comparison_metrics["total"].append({
                "scenario_id": str(result.scenario_id),
                "scenario_name": result.scenario_name,
                "value": float(result.simulated_total),
            })
            comparison_metrics["margin"].append({
                "scenario_id": str(result.scenario_id),
                "scenario_name": result.scenario_name,
                "value": float(result.simulated_margin_percentage),
            })
            comparison_metrics["cost"].append({
                "scenario_id": str(result.scenario_id),
                "scenario_name": result.scenario_name,
                "value": float(result.simulated_total_cost),
            })
            
            if result.simulated_margin_percentage > best_margin:
                best_margin = result.simulated_margin_percentage
                best_margin_id = result.scenario_id
            
            if result.simulated_total < lowest_price:
                lowest_price = result.simulated_total
                lowest_price_id = result.scenario_id
        
        # Generate recommendations
        recommendations = []
        if best_margin_id:
            best_margin_scenario = next(
                (r for r in results if r.scenario_id == best_margin_id),
                None,
            )
            if best_margin_scenario:
                recommendations.append(
                    f"Best margin scenario: {best_margin_scenario.scenario_name} "
                    f"({best_margin:.1f}%)"
                )
        
        if lowest_price_id and lowest_price_id != best_margin_id:
            lowest_price_scenario = next(
                (r for r in results if r.scenario_id == lowest_price_id),
                None,
            )
            if lowest_price_scenario:
                recommendations.append(
                    f"Lowest price scenario: {lowest_price_scenario.scenario_name} "
                    f"({lowest_price:,.2f})"
                )
        
        return ScenarioComparison(
            baseline_scenario=baseline_result,
            scenarios=results,
            comparison_metrics=comparison_metrics,
            best_margin_scenario=best_margin_id,
            lowest_price_scenario=lowest_price_id,
            recommendations=recommendations,
        )
    
    # =========================================================================
    # Quick Simulation Helpers
    # =========================================================================
    
    def simulate_cost_increase(
        self,
        quote_id: UUID,
        percentage: Decimal,
        cost_type: SimulationVariableType = SimulationVariableType.TOTAL_COST,
    ) -> SimulationResult | None:
        """Quick simulation for cost increase scenario."""
        scenario = self.create_scenario(
            name=f"Cost +{percentage}%",
            adjustments=[
                VariableAdjustment(
                    variable=cost_type,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=percentage,
                )
            ],
        )
        return self.run_simulation(quote_id, scenario.id)
    
    def simulate_quantity_change(
        self,
        quote_id: UUID,
        percentage: Decimal,
    ) -> SimulationResult | None:
        """Quick simulation for quantity change scenario."""
        scenario = self.create_scenario(
            name=f"Quantity {'+' if percentage > 0 else ''}{percentage}%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.QUANTITY,
                    adjustment_type=AdjustmentType.PERCENTAGE,
                    value=percentage,
                )
            ],
        )
        return self.run_simulation(quote_id, scenario.id)
    
    def simulate_target_margin(
        self,
        quote_id: UUID,
        target_margin_percentage: Decimal,
    ) -> SimulationResult | None:
        """Quick simulation for target margin scenario."""
        scenario = self.create_scenario(
            name=f"Target Margin {target_margin_percentage}%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.TARGET_MARGIN,
                    adjustment_type=AdjustmentType.ABSOLUTE,
                    value=target_margin_percentage,
                )
            ],
        )
        return self.run_simulation(quote_id, scenario.id)
    
    def simulate_discount(
        self,
        quote_id: UUID,
        discount_percentage: Decimal,
    ) -> SimulationResult | None:
        """Quick simulation for discount scenario."""
        scenario = self.create_scenario(
            name=f"Discount {discount_percentage}%",
            adjustments=[
                VariableAdjustment(
                    variable=SimulationVariableType.DISCOUNT_PERCENTAGE,
                    adjustment_type=AdjustmentType.ABSOLUTE,
                    value=discount_percentage,
                )
            ],
        )
        return self.run_simulation(quote_id, scenario.id)
    
    # =========================================================================
    # Sensitivity Analysis
    # =========================================================================
    
    def run_sensitivity_analysis(
        self,
        quote_id: UUID,
        variable: SimulationVariableType,
        range_values: list[Decimal],
    ) -> list[SimulationResult]:
        """
        Run sensitivity analysis on a variable.
        
        Creates and runs multiple scenarios with different values of the variable.
        """
        results = []
        
        for value in range_values:
            scenario = self.create_scenario(
                name=f"{variable.value} @ {value}",
                adjustments=[
                    VariableAdjustment(
                        variable=variable,
                        adjustment_type=AdjustmentType.PERCENTAGE,
                        value=value,
                    )
                ],
            )
            result = self.run_simulation(quote_id, scenario.id)
            if result:
                results.append(result)
        
        return results
    
    def run_cost_sensitivity(
        self,
        quote_id: UUID,
    ) -> list[SimulationResult]:
        """Run standard cost sensitivity analysis (-20%, -10%, +10%, +20%)."""
        return self.run_sensitivity_analysis(
            quote_id,
            SimulationVariableType.TOTAL_COST,
            [Decimal("-20"), Decimal("-10"), Decimal("10"), Decimal("20")],
        )
    
    # =========================================================================
    # Break-Even Analysis
    # =========================================================================
    
    def calculate_break_even_price(
        self,
        quote_id: UUID,
    ) -> dict[str, Any] | None:
        """Calculate break-even price (margin = 0%)."""
        quote = self._quotes.get(quote_id)
        if not quote:
            return None
        
        total_cost = quote.total_cost
        
        # At break-even, price = cost
        return {
            "break_even_price": float(total_cost),
            "current_price": float(quote.total),
            "margin_buffer": float(quote.total - total_cost),
            "margin_buffer_percentage": float(
                (quote.total - total_cost) / quote.total * 100
                if quote.total > 0 else 0
            ),
        }
    
    def calculate_price_for_margin(
        self,
        quote_id: UUID,
        target_margin: Decimal,
    ) -> dict[str, Any] | None:
        """Calculate the price needed to achieve a target margin."""
        quote = self._quotes.get(quote_id)
        if not quote:
            return None
        
        total_cost = quote.total_cost
        
        # price = cost / (1 - margin_pct)
        target_margin_decimal = target_margin / 100
        if target_margin_decimal >= 1:
            return None  # Invalid margin (>=100%)
        
        required_price = total_cost / (1 - target_margin_decimal)
        
        return {
            "target_margin_percentage": float(target_margin),
            "required_price": float(required_price),
            "current_price": float(quote.total),
            "price_change": float(required_price - quote.total),
            "price_change_percentage": float(
                (required_price - quote.total) / quote.total * 100
                if quote.total > 0 else 0
            ),
        }
    
    # =========================================================================
    # Testing Helpers
    # =========================================================================
    
    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._scenarios.clear()
        self._results.clear()
        self._quotes.clear()
