"""
AI-Driven Supply Chain Simulation.

Enables stress-testing RFQs against simulated global disruptions
and predictive impact analysis on quote delivery dates.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import math
import random
import hashlib
from collections import defaultdict


# =============================================================================
# Constants
# =============================================================================

DEFAULT_SIMULATION_RUNS = 1000
MIN_CONFIDENCE_SAMPLES = 100
BASE_LEAD_TIME_DAYS = 14


# =============================================================================
# Enums
# =============================================================================

class DisruptionType(Enum):
    """Types of supply chain disruptions."""
    LOGISTICS_DELAY = "logistics_delay"
    SUPPLIER_OUTAGE = "supplier_outage"
    RAW_MATERIAL_SHORTAGE = "raw_material_shortage"
    LABOR_STRIKE = "labor_strike"
    NATURAL_DISASTER = "natural_disaster"
    GEOPOLITICAL = "geopolitical"
    DEMAND_SURGE = "demand_surge"
    QUALITY_ISSUE = "quality_issue"
    CUSTOMS_DELAY = "customs_delay"
    CAPACITY_CONSTRAINT = "capacity_constraint"


class ImpactSeverity(Enum):
    """Severity levels for disruption impact."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MitigationStrategy(Enum):
    """Mitigation strategies for disruptions."""
    SAFETY_STOCK = "safety_stock"
    ALTERNATE_SUPPLIER = "alternate_supplier"
    EXPEDITED_SHIPPING = "expedited_shipping"
    PRODUCTION_RESEQUENCE = "production_resequence"
    CUSTOMER_COMMUNICATION = "customer_communication"
    PARTIAL_SHIPMENT = "partial_shipment"
    OVERTIME_PRODUCTION = "overtime_production"
    NONE = "none"


class SimulationStatus(Enum):
    """Status of a simulation run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class DisruptionScenario:
    """A disruption scenario to simulate."""
    scenario_id: str
    name: str
    disruption_type: DisruptionType
    severity: ImpactSeverity
    
    # Impact parameters
    delay_percentage: float  # e.g., 0.20 = 20% logistics delay
    cost_increase_percentage: float  # e.g., 0.15 = 15% cost increase
    availability_impact: float  # 0.0-1.0, 1.0 = fully available
    duration_days: int  # Expected duration of disruption
    
    # Probability
    probability: float = 0.1  # Likelihood of occurring
    
    description: str = ""
    affected_regions: list[str] = field(default_factory=list)
    affected_suppliers: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate parameters."""
        if not 0 <= self.delay_percentage <= 5.0:
            self.delay_percentage = max(0.0, min(5.0, self.delay_percentage))
        if not 0 <= self.availability_impact <= 1.0:
            self.availability_impact = max(0.0, min(1.0, self.availability_impact))


@dataclass
class SupplyChainNode:
    """A node in the supply chain."""
    node_id: str
    name: str
    node_type: str  # supplier, warehouse, factory, customer
    location: str
    region: str
    
    # Lead times
    base_lead_time_days: float = 7.0
    lead_time_variance: float = 0.2  # Coefficient of variation
    
    # Capacity
    max_capacity: float = 1000.0
    current_utilization: float = 0.7
    
    # Reliability
    reliability_score: float = 0.95
    quality_score: float = 0.98
    
    # Connections
    upstream_nodes: list[str] = field(default_factory=list)
    downstream_nodes: list[str] = field(default_factory=list)


@dataclass
class RFQSimulationInput:
    """Input data for RFQ simulation."""
    rfq_id: str
    customer_id: str
    
    # Timeline
    requested_delivery_date: datetime
    quote_date: datetime
    
    # Items
    line_items: list[dict[str, Any]] = field(default_factory=list)
    total_value: float = 0.0
    
    # Supply chain
    primary_supplier_id: str = ""
    alternate_supplier_ids: list[str] = field(default_factory=list)
    
    # Requirements
    critical_materials: list[str] = field(default_factory=list)
    required_certifications: list[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Result of a single simulation run."""
    run_id: int
    scenario_id: str
    
    # Delivery impact
    original_delivery_date: datetime
    simulated_delivery_date: datetime
    delay_days: float
    
    # Cost impact
    original_cost: float
    simulated_cost: float
    cost_delta: float
    
    # Success metrics
    on_time_delivery: bool
    within_budget: bool
    quality_maintained: bool
    
    # Applied disruptions
    disruptions_applied: list[str] = field(default_factory=list)
    mitigation_used: list[MitigationStrategy] = field(default_factory=list)


@dataclass
class ImpactAnalysis:
    """Analysis of simulation impact."""
    rfq_id: str
    scenario_id: str
    
    # Delivery statistics
    mean_delay_days: float
    median_delay_days: float
    p95_delay_days: float  # 95th percentile
    max_delay_days: float
    delay_std_dev: float
    
    # Probability metrics
    on_time_probability: float
    probability_of_delay: float
    probability_of_major_delay: float  # >7 days
    
    # Cost statistics
    mean_cost_increase: float
    max_cost_increase: float
    expected_additional_cost: float
    
    # Recommendations
    recommended_buffer_days: int
    risk_rating: ImpactSeverity
    
    confidence_level: float = 0.95


@dataclass
class MitigationRecommendation:
    """A recommended mitigation action."""
    strategy: MitigationStrategy
    description: str
    effectiveness: float  # 0.0-1.0
    estimated_cost: float
    implementation_time_days: int
    risk_reduction: float  # How much it reduces delay probability
    priority: int  # 1 = highest


@dataclass
class SimulationReport:
    """Complete simulation report for an RFQ."""
    report_id: str
    rfq_id: str
    generated_at: datetime
    
    # Input summary
    scenarios_tested: list[str]
    simulation_runs: int
    
    # Results
    impact_analyses: list[ImpactAnalysis] = field(default_factory=list)
    individual_results: list[SimulationResult] = field(default_factory=list)
    
    # Aggregated metrics
    overall_risk_rating: ImpactSeverity = ImpactSeverity.LOW
    recommended_delivery_buffer_days: int = 0
    expected_delivery_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Mitigations
    mitigation_recommendations: list[MitigationRecommendation] = field(default_factory=list)
    
    # Confidence
    confidence_level: float = 0.95
    
    def get_summary(self) -> dict[str, Any]:
        """Get report summary."""
        return {
            "rfq_id": self.rfq_id,
            "scenarios_tested": len(self.scenarios_tested),
            "simulation_runs": self.simulation_runs,
            "overall_risk": self.overall_risk_rating.value,
            "recommended_buffer_days": self.recommended_delivery_buffer_days,
            "top_mitigations": [
                m.strategy.value for m in self.mitigation_recommendations[:3]
            ],
        }


# =============================================================================
# Disruption Scenario Library
# =============================================================================

class DisruptionLibrary:
    """Library of predefined disruption scenarios."""
    
    STANDARD_SCENARIOS: list[DisruptionScenario] = [
        DisruptionScenario(
            scenario_id="logistics_20",
            name="20% Logistics Delay",
            disruption_type=DisruptionType.LOGISTICS_DELAY,
            severity=ImpactSeverity.MODERATE,
            delay_percentage=0.20,
            cost_increase_percentage=0.10,
            availability_impact=1.0,
            duration_days=14,
            probability=0.15,
            description="General logistics congestion causing 20% delays",
        ),
        DisruptionScenario(
            scenario_id="logistics_50",
            name="50% Logistics Delay",
            disruption_type=DisruptionType.LOGISTICS_DELAY,
            severity=ImpactSeverity.HIGH,
            delay_percentage=0.50,
            cost_increase_percentage=0.25,
            availability_impact=0.9,
            duration_days=30,
            probability=0.05,
            description="Major logistics disruption with 50% delays",
        ),
        DisruptionScenario(
            scenario_id="supplier_partial",
            name="Partial Supplier Outage",
            disruption_type=DisruptionType.SUPPLIER_OUTAGE,
            severity=ImpactSeverity.MODERATE,
            delay_percentage=0.30,
            cost_increase_percentage=0.15,
            availability_impact=0.6,
            duration_days=21,
            probability=0.08,
            description="Primary supplier operating at 60% capacity",
        ),
        DisruptionScenario(
            scenario_id="supplier_full",
            name="Full Supplier Outage",
            disruption_type=DisruptionType.SUPPLIER_OUTAGE,
            severity=ImpactSeverity.CRITICAL,
            delay_percentage=1.0,
            cost_increase_percentage=0.50,
            availability_impact=0.0,
            duration_days=45,
            probability=0.02,
            description="Primary supplier completely unavailable",
        ),
        DisruptionScenario(
            scenario_id="material_shortage",
            name="Raw Material Shortage",
            disruption_type=DisruptionType.RAW_MATERIAL_SHORTAGE,
            severity=ImpactSeverity.HIGH,
            delay_percentage=0.40,
            cost_increase_percentage=0.30,
            availability_impact=0.7,
            duration_days=28,
            probability=0.06,
            description="Critical material shortage affecting production",
        ),
        DisruptionScenario(
            scenario_id="demand_surge",
            name="Market Demand Surge",
            disruption_type=DisruptionType.DEMAND_SURGE,
            severity=ImpactSeverity.MODERATE,
            delay_percentage=0.25,
            cost_increase_percentage=0.20,
            availability_impact=0.8,
            duration_days=21,
            probability=0.10,
            description="Unexpected market demand surge",
        ),
        DisruptionScenario(
            scenario_id="customs_delay",
            name="Customs Processing Delay",
            disruption_type=DisruptionType.CUSTOMS_DELAY,
            severity=ImpactSeverity.LOW,
            delay_percentage=0.15,
            cost_increase_percentage=0.05,
            availability_impact=1.0,
            duration_days=7,
            probability=0.12,
            description="Extended customs processing times",
        ),
        DisruptionScenario(
            scenario_id="capacity_constraint",
            name="Production Capacity Constraint",
            disruption_type=DisruptionType.CAPACITY_CONSTRAINT,
            severity=ImpactSeverity.MODERATE,
            delay_percentage=0.20,
            cost_increase_percentage=0.15,
            availability_impact=0.85,
            duration_days=14,
            probability=0.10,
            description="Internal production capacity limitations",
        ),
    ]
    
    @classmethod
    def get_all_scenarios(cls) -> list[DisruptionScenario]:
        """Get all standard scenarios."""
        return cls.STANDARD_SCENARIOS.copy()
    
    @classmethod
    def get_scenario_by_id(cls, scenario_id: str) -> DisruptionScenario | None:
        """Get a specific scenario by ID."""
        for scenario in cls.STANDARD_SCENARIOS:
            if scenario.scenario_id == scenario_id:
                return scenario
        return None
    
    @classmethod
    def get_scenarios_by_type(
        cls,
        disruption_type: DisruptionType,
    ) -> list[DisruptionScenario]:
        """Get scenarios by disruption type."""
        return [
            s for s in cls.STANDARD_SCENARIOS
            if s.disruption_type == disruption_type
        ]
    
    @classmethod
    def get_scenarios_by_severity(
        cls,
        min_severity: ImpactSeverity,
    ) -> list[DisruptionScenario]:
        """Get scenarios at or above a severity level."""
        severity_order = [
            ImpactSeverity.MINIMAL,
            ImpactSeverity.LOW,
            ImpactSeverity.MODERATE,
            ImpactSeverity.HIGH,
            ImpactSeverity.CRITICAL,
        ]
        min_idx = severity_order.index(min_severity)
        
        return [
            s for s in cls.STANDARD_SCENARIOS
            if severity_order.index(s.severity) >= min_idx
        ]


# =============================================================================
# Monte Carlo Simulator
# =============================================================================

class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for supply chain.
    
    Runs multiple simulations with stochastic disruption occurrence.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize simulator."""
        self.random = random.Random(seed)
        self._disruption_correlations: dict[tuple[str, str], float] = {}
    
    def set_disruption_correlation(
        self,
        scenario1_id: str,
        scenario2_id: str,
        correlation: float,
    ) -> None:
        """Set correlation between two disruptions."""
        key = tuple(sorted([scenario1_id, scenario2_id]))
        self._disruption_correlations[key] = max(-1.0, min(1.0, correlation))
    
    def simulate_run(
        self,
        rfq: RFQSimulationInput,
        scenarios: list[DisruptionScenario],
        supply_chain: list[SupplyChainNode],
        run_id: int,
    ) -> SimulationResult:
        """Run a single simulation."""
        # Determine which disruptions occur
        active_disruptions = self._determine_active_disruptions(scenarios)
        
        # Calculate base lead time
        base_delivery = self._calculate_base_delivery(rfq, supply_chain)
        
        # Apply disruption impacts
        total_delay_factor = 1.0
        total_cost_factor = 1.0
        availability = 1.0
        
        for scenario in active_disruptions:
            total_delay_factor *= (1 + scenario.delay_percentage)
            total_cost_factor *= (1 + scenario.cost_increase_percentage)
            availability *= scenario.availability_impact
        
        # Add stochastic variation
        delay_noise = self.random.gauss(0, 0.1) * total_delay_factor
        total_delay_factor = max(1.0, total_delay_factor + delay_noise)
        
        # Calculate final values
        lead_time_days = self._calculate_lead_time(rfq, supply_chain)
        delay_days = lead_time_days * (total_delay_factor - 1)
        
        simulated_delivery = base_delivery + timedelta(days=delay_days)
        
        original_cost = rfq.total_value if rfq.total_value > 0 else 10000.0
        simulated_cost = original_cost * total_cost_factor
        
        # Determine mitigation
        mitigations = self._select_mitigations(
            delay_days, active_disruptions, rfq
        )
        
        return SimulationResult(
            run_id=run_id,
            scenario_id=",".join(s.scenario_id for s in active_disruptions) or "none",
            original_delivery_date=base_delivery,
            simulated_delivery_date=simulated_delivery,
            delay_days=delay_days,
            original_cost=original_cost,
            simulated_cost=simulated_cost,
            cost_delta=simulated_cost - original_cost,
            on_time_delivery=simulated_delivery <= rfq.requested_delivery_date,
            within_budget=simulated_cost <= original_cost * 1.10,
            quality_maintained=availability > 0.8,
            disruptions_applied=[s.scenario_id for s in active_disruptions],
            mitigation_used=mitigations,
        )
    
    def _determine_active_disruptions(
        self,
        scenarios: list[DisruptionScenario],
    ) -> list[DisruptionScenario]:
        """Determine which disruptions occur in this run."""
        active: list[DisruptionScenario] = []
        
        for scenario in scenarios:
            # Check if this disruption occurs
            if self.random.random() < scenario.probability:
                # Check correlations with already active disruptions
                correlation_boost = 0.0
                for active_scenario in active:
                    key = tuple(sorted([scenario.scenario_id, active_scenario.scenario_id]))
                    correlation = self._disruption_correlations.get(key, 0.0)
                    correlation_boost += correlation * 0.1
                
                # Correlated disruptions are more likely
                if self.random.random() < scenario.probability + correlation_boost:
                    active.append(scenario)
        
        return active
    
    def _calculate_base_delivery(
        self,
        rfq: RFQSimulationInput,
        supply_chain: list[SupplyChainNode],
    ) -> datetime:
        """Calculate base delivery date."""
        lead_time = self._calculate_lead_time(rfq, supply_chain)
        return rfq.quote_date + timedelta(days=lead_time)
    
    def _calculate_lead_time(
        self,
        rfq: RFQSimulationInput,
        supply_chain: list[SupplyChainNode],
    ) -> float:
        """Calculate total lead time through supply chain."""
        if not supply_chain:
            return BASE_LEAD_TIME_DAYS
        
        # Sum lead times along critical path
        total_lead_time = 0.0
        for node in supply_chain:
            # Add node lead time with variance
            variance = node.lead_time_variance * node.base_lead_time_days
            node_lead_time = self.random.gauss(
                node.base_lead_time_days,
                variance,
            )
            total_lead_time += max(0, node_lead_time)
        
        return total_lead_time
    
    def _select_mitigations(
        self,
        delay_days: float,
        disruptions: list[DisruptionScenario],
        rfq: RFQSimulationInput,
    ) -> list[MitigationStrategy]:
        """Select appropriate mitigation strategies."""
        mitigations = []
        
        if delay_days > 7:
            mitigations.append(MitigationStrategy.CUSTOMER_COMMUNICATION)
        
        if delay_days > 14:
            if rfq.alternate_supplier_ids:
                mitigations.append(MitigationStrategy.ALTERNATE_SUPPLIER)
            mitigations.append(MitigationStrategy.EXPEDITED_SHIPPING)
        
        if delay_days > 21:
            mitigations.append(MitigationStrategy.PRODUCTION_RESEQUENCE)
            mitigations.append(MitigationStrategy.OVERTIME_PRODUCTION)
        
        if any(d.disruption_type == DisruptionType.SUPPLIER_OUTAGE for d in disruptions):
            if MitigationStrategy.ALTERNATE_SUPPLIER not in mitigations:
                mitigations.append(MitigationStrategy.ALTERNATE_SUPPLIER)
        
        return mitigations if mitigations else [MitigationStrategy.NONE]


# =============================================================================
# Impact Analyzer
# =============================================================================

class ImpactAnalyzer:
    """Analyzes simulation results to produce impact metrics."""
    
    def __init__(self, confidence_level: float = 0.95):
        """Initialize analyzer."""
        self.confidence_level = confidence_level
    
    def analyze(
        self,
        rfq_id: str,
        scenario_id: str,
        results: list[SimulationResult],
    ) -> ImpactAnalysis:
        """Analyze simulation results."""
        if not results:
            return self._empty_analysis(rfq_id, scenario_id)
        
        # Extract delay data
        delays = [r.delay_days for r in results]
        costs = [r.cost_delta for r in results]
        
        # Calculate statistics
        mean_delay = sum(delays) / len(delays)
        sorted_delays = sorted(delays)
        median_delay = sorted_delays[len(sorted_delays) // 2]
        
        # Percentiles
        p95_idx = int(len(sorted_delays) * 0.95)
        p95_delay = sorted_delays[min(p95_idx, len(sorted_delays) - 1)]
        max_delay = max(delays)
        
        # Standard deviation
        if len(delays) > 1:
            variance = sum((d - mean_delay) ** 2 for d in delays) / (len(delays) - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0
        
        # Probability metrics
        on_time_count = sum(1 for r in results if r.on_time_delivery)
        on_time_prob = on_time_count / len(results)
        
        delayed_count = sum(1 for d in delays if d > 0)
        delay_prob = delayed_count / len(results)
        
        major_delay_count = sum(1 for d in delays if d > 7)
        major_delay_prob = major_delay_count / len(results)
        
        # Cost statistics
        mean_cost = sum(costs) / len(costs) if costs else 0.0
        max_cost = max(costs) if costs else 0.0
        
        # Recommendations
        recommended_buffer = self._calculate_buffer(p95_delay, std_dev)
        risk_rating = self._determine_risk_rating(mean_delay, delay_prob, major_delay_prob)
        
        return ImpactAnalysis(
            rfq_id=rfq_id,
            scenario_id=scenario_id,
            mean_delay_days=mean_delay,
            median_delay_days=median_delay,
            p95_delay_days=p95_delay,
            max_delay_days=max_delay,
            delay_std_dev=std_dev,
            on_time_probability=on_time_prob,
            probability_of_delay=delay_prob,
            probability_of_major_delay=major_delay_prob,
            mean_cost_increase=mean_cost,
            max_cost_increase=max_cost,
            expected_additional_cost=mean_cost * delay_prob,
            recommended_buffer_days=recommended_buffer,
            risk_rating=risk_rating,
            confidence_level=self.confidence_level,
        )
    
    def _empty_analysis(
        self,
        rfq_id: str,
        scenario_id: str,
    ) -> ImpactAnalysis:
        """Return empty analysis when no results."""
        return ImpactAnalysis(
            rfq_id=rfq_id,
            scenario_id=scenario_id,
            mean_delay_days=0.0,
            median_delay_days=0.0,
            p95_delay_days=0.0,
            max_delay_days=0.0,
            delay_std_dev=0.0,
            on_time_probability=1.0,
            probability_of_delay=0.0,
            probability_of_major_delay=0.0,
            mean_cost_increase=0.0,
            max_cost_increase=0.0,
            expected_additional_cost=0.0,
            recommended_buffer_days=0,
            risk_rating=ImpactSeverity.MINIMAL,
            confidence_level=self.confidence_level,
        )
    
    def _calculate_buffer(self, p95_delay: float, std_dev: float) -> int:
        """Calculate recommended buffer days."""
        # Use P95 plus one standard deviation
        buffer = p95_delay + std_dev
        return max(0, int(math.ceil(buffer)))
    
    def _determine_risk_rating(
        self,
        mean_delay: float,
        delay_prob: float,
        major_delay_prob: float,
    ) -> ImpactSeverity:
        """Determine overall risk rating."""
        if major_delay_prob > 0.3 or mean_delay > 14:
            return ImpactSeverity.CRITICAL
        elif major_delay_prob > 0.15 or mean_delay > 7:
            return ImpactSeverity.HIGH
        elif delay_prob > 0.3 or mean_delay > 3:
            return ImpactSeverity.MODERATE
        elif delay_prob > 0.1:
            return ImpactSeverity.LOW
        else:
            return ImpactSeverity.MINIMAL


# =============================================================================
# Mitigation Advisor
# =============================================================================

class MitigationAdvisor:
    """Recommends mitigation strategies based on simulation results."""
    
    STRATEGY_INFO: dict[MitigationStrategy, dict[str, Any]] = {
        MitigationStrategy.SAFETY_STOCK: {
            "description": "Maintain safety stock of critical materials",
            "effectiveness": 0.75,
            "cost_factor": 0.08,  # 8% of material cost
            "implementation_days": 14,
        },
        MitigationStrategy.ALTERNATE_SUPPLIER: {
            "description": "Qualify and engage alternate supplier",
            "effectiveness": 0.85,
            "cost_factor": 0.12,
            "implementation_days": 30,
        },
        MitigationStrategy.EXPEDITED_SHIPPING: {
            "description": "Use expedited shipping methods",
            "effectiveness": 0.60,
            "cost_factor": 0.25,
            "implementation_days": 1,
        },
        MitigationStrategy.PRODUCTION_RESEQUENCE: {
            "description": "Resequence production schedule to prioritize order",
            "effectiveness": 0.50,
            "cost_factor": 0.05,
            "implementation_days": 3,
        },
        MitigationStrategy.CUSTOMER_COMMUNICATION: {
            "description": "Proactive customer communication about potential delays",
            "effectiveness": 0.20,
            "cost_factor": 0.01,
            "implementation_days": 0,
        },
        MitigationStrategy.PARTIAL_SHIPMENT: {
            "description": "Ship available items first, remainder later",
            "effectiveness": 0.40,
            "cost_factor": 0.10,
            "implementation_days": 0,
        },
        MitigationStrategy.OVERTIME_PRODUCTION: {
            "description": "Authorize overtime for production acceleration",
            "effectiveness": 0.55,
            "cost_factor": 0.20,
            "implementation_days": 0,
        },
    }
    
    def __init__(self, base_order_value: float = 10000.0):
        """Initialize advisor."""
        self.base_order_value = base_order_value
    
    def recommend(
        self,
        impact_analysis: ImpactAnalysis,
        available_strategies: Optional[list[MitigationStrategy]] = None,
    ) -> list[MitigationRecommendation]:
        """Generate mitigation recommendations."""
        if available_strategies is None:
            available_strategies = list(MitigationStrategy)
            available_strategies.remove(MitigationStrategy.NONE)
        
        recommendations = []
        
        for strategy in available_strategies:
            info = self.STRATEGY_INFO.get(strategy)
            if not info:
                continue
            
            # Calculate risk reduction
            risk_reduction = self._calculate_risk_reduction(
                strategy, info, impact_analysis
            )
            
            if risk_reduction > 0.05:  # At least 5% reduction
                recommendations.append(MitigationRecommendation(
                    strategy=strategy,
                    description=info["description"],
                    effectiveness=info["effectiveness"],
                    estimated_cost=self.base_order_value * info["cost_factor"],
                    implementation_time_days=info["implementation_days"],
                    risk_reduction=risk_reduction,
                    priority=0,  # Will be set below
                ))
        
        # Sort by effectiveness and assign priorities
        recommendations.sort(
            key=lambda r: r.effectiveness * r.risk_reduction,
            reverse=True,
        )
        
        for i, rec in enumerate(recommendations):
            rec.priority = i + 1
        
        return recommendations
    
    def _calculate_risk_reduction(
        self,
        strategy: MitigationStrategy,
        info: dict,
        analysis: ImpactAnalysis,
    ) -> float:
        """Calculate expected risk reduction from a strategy."""
        base_effectiveness = info["effectiveness"]
        
        # Adjust based on specific scenario
        if strategy == MitigationStrategy.SAFETY_STOCK:
            # More effective for material-related issues
            if analysis.probability_of_major_delay > 0.2:
                return base_effectiveness * 1.2
        
        elif strategy == MitigationStrategy.EXPEDITED_SHIPPING:
            # More effective for logistics delays
            if analysis.mean_delay_days < 7:
                return base_effectiveness * 1.3
        
        elif strategy == MitigationStrategy.ALTERNATE_SUPPLIER:
            # More effective when primary supplier is risky
            if analysis.probability_of_delay > 0.3:
                return base_effectiveness * 1.4
        
        return base_effectiveness * analysis.probability_of_delay


# =============================================================================
# Supply Chain Simulation Engine
# =============================================================================

class SupplyChainSimulator:
    """
    Main supply chain simulation engine.
    
    Combines Monte Carlo simulation with impact analysis.
    """
    
    def __init__(
        self,
        simulation_runs: int = DEFAULT_SIMULATION_RUNS,
        confidence_level: float = 0.95,
        seed: Optional[int] = None,
    ):
        """Initialize simulator."""
        self.simulation_runs = simulation_runs
        self.confidence_level = confidence_level
        
        self.mc_simulator = MonteCarloSimulator(seed)
        self.impact_analyzer = ImpactAnalyzer(confidence_level)
        self.mitigation_advisor = MitigationAdvisor()
        
        # Supply chain model
        self._supply_chain_nodes: list[SupplyChainNode] = []
        self._custom_scenarios: list[DisruptionScenario] = []
    
    def add_supply_chain_node(self, node: SupplyChainNode) -> None:
        """Add a node to the supply chain model."""
        self._supply_chain_nodes.append(node)
    
    def add_custom_scenario(self, scenario: DisruptionScenario) -> None:
        """Add a custom disruption scenario."""
        self._custom_scenarios.append(scenario)
    
    def simulate_rfq(
        self,
        rfq: RFQSimulationInput,
        scenarios: Optional[list[DisruptionScenario]] = None,
    ) -> SimulationReport:
        """Run complete simulation for an RFQ."""
        report_id = hashlib.md5(
            f"{rfq.rfq_id}:{datetime.now(timezone.utc)}".encode()
        ).hexdigest()[:16]
        
        # Get scenarios
        if scenarios is None:
            scenarios = DisruptionLibrary.get_all_scenarios() + self._custom_scenarios
        
        # Run simulations
        all_results: list[SimulationResult] = []
        
        for run_id in range(self.simulation_runs):
            result = self.mc_simulator.simulate_run(
                rfq, scenarios, self._supply_chain_nodes, run_id
            )
            all_results.append(result)
        
        # Analyze results by scenario combination
        scenario_results: dict[str, list[SimulationResult]] = defaultdict(list)
        for result in all_results:
            scenario_results[result.scenario_id].append(result)
        
        # Generate impact analyses
        impact_analyses = []
        for scenario_id, results in scenario_results.items():
            if scenario_id:  # Skip empty scenario
                analysis = self.impact_analyzer.analyze(
                    rfq.rfq_id, scenario_id, results
                )
                impact_analyses.append(analysis)
        
        # Also analyze all results together
        overall_analysis = self.impact_analyzer.analyze(
            rfq.rfq_id, "overall", all_results
        )
        impact_analyses.insert(0, overall_analysis)
        
        # Generate mitigations
        self.mitigation_advisor.base_order_value = rfq.total_value or 10000.0
        mitigation_recommendations = self.mitigation_advisor.recommend(overall_analysis)
        
        # Calculate expected delivery
        expected_delivery = rfq.quote_date + timedelta(
            days=overall_analysis.mean_delay_days + self._get_base_lead_time()
        )
        
        return SimulationReport(
            report_id=report_id,
            rfq_id=rfq.rfq_id,
            generated_at=datetime.now(timezone.utc),
            scenarios_tested=[s.scenario_id for s in scenarios],
            simulation_runs=self.simulation_runs,
            impact_analyses=impact_analyses,
            individual_results=all_results,
            overall_risk_rating=overall_analysis.risk_rating,
            recommended_delivery_buffer_days=overall_analysis.recommended_buffer_days,
            expected_delivery_date=expected_delivery,
            mitigation_recommendations=mitigation_recommendations,
            confidence_level=self.confidence_level,
        )
    
    def stress_test(
        self,
        rfq: RFQSimulationInput,
        disruption_type: DisruptionType,
        severity_level: float,  # 0.0-1.0
    ) -> SimulationReport:
        """Stress test an RFQ with a specific disruption type."""
        # Create stress test scenario
        stress_scenario = DisruptionScenario(
            scenario_id=f"stress_{disruption_type.value}",
            name=f"Stress Test: {disruption_type.value}",
            disruption_type=disruption_type,
            severity=ImpactSeverity.HIGH,
            delay_percentage=severity_level,
            cost_increase_percentage=severity_level * 0.5,
            availability_impact=1.0 - (severity_level * 0.5),
            duration_days=int(14 * (1 + severity_level)),
            probability=1.0,  # Always apply in stress test
        )
        
        return self.simulate_rfq(rfq, [stress_scenario])
    
    def compare_scenarios(
        self,
        rfq: RFQSimulationInput,
        scenario_ids: list[str],
    ) -> dict[str, ImpactAnalysis]:
        """Compare impact of specific scenarios."""
        scenarios = []
        for sid in scenario_ids:
            scenario = DisruptionLibrary.get_scenario_by_id(sid)
            if scenario:
                # Force probability to 1 for comparison
                comparison_scenario = DisruptionScenario(
                    scenario_id=scenario.scenario_id,
                    name=scenario.name,
                    disruption_type=scenario.disruption_type,
                    severity=scenario.severity,
                    delay_percentage=scenario.delay_percentage,
                    cost_increase_percentage=scenario.cost_increase_percentage,
                    availability_impact=scenario.availability_impact,
                    duration_days=scenario.duration_days,
                    probability=1.0,  # Always apply
                    description=scenario.description,
                )
                scenarios.append(comparison_scenario)
        
        results = {}
        for scenario in scenarios:
            report = self.simulate_rfq(rfq, [scenario])
            if report.impact_analyses:
                results[scenario.scenario_id] = report.impact_analyses[0]
        
        return results
    
    def _get_base_lead_time(self) -> float:
        """Get base lead time from supply chain."""
        if not self._supply_chain_nodes:
            return BASE_LEAD_TIME_DAYS
        return sum(n.base_lead_time_days for n in self._supply_chain_nodes)
    
    def get_statistics(self) -> dict[str, Any]:
        """Get simulator statistics."""
        return {
            "simulation_runs": self.simulation_runs,
            "confidence_level": self.confidence_level,
            "supply_chain_nodes": len(self._supply_chain_nodes),
            "custom_scenarios": len(self._custom_scenarios),
            "standard_scenarios": len(DisruptionLibrary.STANDARD_SCENARIOS),
        }


# =============================================================================
# Singleton
# =============================================================================

_supply_chain_simulator: SupplyChainSimulator | None = None


def get_supply_chain_simulator() -> SupplyChainSimulator:
    """Get the supply chain simulator singleton."""
    global _supply_chain_simulator
    if _supply_chain_simulator is None:
        _supply_chain_simulator = SupplyChainSimulator()
    return _supply_chain_simulator


def create_supply_chain_simulator(
    simulation_runs: int = DEFAULT_SIMULATION_RUNS,
    confidence_level: float = 0.95,
    seed: Optional[int] = None,
) -> SupplyChainSimulator:
    """Create a configured supply chain simulator (for testing)."""
    return SupplyChainSimulator(
        simulation_runs=simulation_runs,
        confidence_level=confidence_level,
        seed=seed,
    )
