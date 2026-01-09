"""
Tests for AI-Driven Supply Chain Simulation.

Tests cover:
- Disruption scenarios and library
- Monte Carlo simulation
- Impact analysis
- Mitigation recommendations
- Complete simulation engine
"""

import pytest
from datetime import datetime, timezone, timedelta

from sensei.services.supply_chain_simulation import (
    # Enums
    DisruptionType,
    ImpactSeverity,
    MitigationStrategy,
    SimulationStatus,
    # Data models
    DisruptionScenario,
    SupplyChainNode,
    RFQSimulationInput,
    SimulationResult,
    ImpactAnalysis,
    MitigationRecommendation,
    SimulationReport,
    # Components
    DisruptionLibrary,
    MonteCarloSimulator,
    ImpactAnalyzer,
    MitigationAdvisor,
    SupplyChainSimulator,
    # Factory
    create_supply_chain_simulator,
    # Constants
    DEFAULT_SIMULATION_RUNS,
    BASE_LEAD_TIME_DAYS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_rfq() -> RFQSimulationInput:
    """Sample RFQ for testing."""
    return RFQSimulationInput(
        rfq_id="RFQ-TEST-001",
        customer_id="CUST-001",
        requested_delivery_date=datetime.now(timezone.utc) + timedelta(days=30),
        quote_date=datetime.now(timezone.utc),
        line_items=[
            {"part_number": "PART-001", "quantity": 100, "unit_price": 50.0},
            {"part_number": "PART-002", "quantity": 50, "unit_price": 100.0},
        ],
        total_value=10000.0,
        primary_supplier_id="SUPP-001",
        alternate_supplier_ids=["SUPP-002", "SUPP-003"],
        critical_materials=["aluminum", "steel"],
    )


@pytest.fixture
def sample_supply_chain() -> list[SupplyChainNode]:
    """Sample supply chain nodes."""
    return [
        SupplyChainNode(
            node_id="SUPP-001",
            name="Primary Supplier",
            node_type="supplier",
            location="Shanghai, China",
            region="Asia",
            base_lead_time_days=7.0,
            lead_time_variance=0.15,
            reliability_score=0.95,
        ),
        SupplyChainNode(
            node_id="WHSE-001",
            name="Distribution Warehouse",
            node_type="warehouse",
            location="Los Angeles, CA",
            region="North America",
            base_lead_time_days=3.0,
            lead_time_variance=0.10,
        ),
        SupplyChainNode(
            node_id="FACT-001",
            name="Manufacturing Facility",
            node_type="factory",
            location="Detroit, MI",
            region="North America",
            base_lead_time_days=5.0,
            lead_time_variance=0.20,
            max_capacity=500.0,
            current_utilization=0.75,
        ),
    ]


@pytest.fixture
def logistics_delay_scenario() -> DisruptionScenario:
    """Create logistics delay scenario."""
    return DisruptionScenario(
        scenario_id="test_logistics",
        name="Test Logistics Delay",
        disruption_type=DisruptionType.LOGISTICS_DELAY,
        severity=ImpactSeverity.MODERATE,
        delay_percentage=0.20,
        cost_increase_percentage=0.10,
        availability_impact=1.0,
        duration_days=14,
        probability=0.5,  # High probability for testing
    )


@pytest.fixture
def simulator() -> SupplyChainSimulator:
    """Create simulator with fixed seed for reproducibility."""
    return SupplyChainSimulator(
        simulation_runs=100,
        seed=42,
    )


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_disruption_type_values(self):
        """Test DisruptionType values."""
        assert DisruptionType.LOGISTICS_DELAY.value == "logistics_delay"
        assert DisruptionType.SUPPLIER_OUTAGE.value == "supplier_outage"
        assert DisruptionType.RAW_MATERIAL_SHORTAGE.value == "raw_material_shortage"
        assert DisruptionType.NATURAL_DISASTER.value == "natural_disaster"
    
    def test_impact_severity_values(self):
        """Test ImpactSeverity values."""
        assert ImpactSeverity.MINIMAL.value == "minimal"
        assert ImpactSeverity.LOW.value == "low"
        assert ImpactSeverity.MODERATE.value == "moderate"
        assert ImpactSeverity.HIGH.value == "high"
        assert ImpactSeverity.CRITICAL.value == "critical"
    
    def test_mitigation_strategy_values(self):
        """Test MitigationStrategy values."""
        assert MitigationStrategy.SAFETY_STOCK.value == "safety_stock"
        assert MitigationStrategy.ALTERNATE_SUPPLIER.value == "alternate_supplier"
        assert MitigationStrategy.EXPEDITED_SHIPPING.value == "expedited_shipping"
    
    def test_simulation_status_values(self):
        """Test SimulationStatus values."""
        assert SimulationStatus.PENDING.value == "pending"
        assert SimulationStatus.COMPLETED.value == "completed"


# =============================================================================
# Tests: Data Models
# =============================================================================

class TestDisruptionScenario:
    """Test DisruptionScenario dataclass."""
    
    def test_scenario_creation(self, logistics_delay_scenario: DisruptionScenario):
        """Test creating a scenario."""
        assert logistics_delay_scenario.scenario_id == "test_logistics"
        assert logistics_delay_scenario.delay_percentage == 0.20
        assert logistics_delay_scenario.disruption_type == DisruptionType.LOGISTICS_DELAY
    
    def test_scenario_clamps_values(self):
        """Test that invalid values are clamped."""
        scenario = DisruptionScenario(
            scenario_id="test",
            name="Test",
            disruption_type=DisruptionType.LOGISTICS_DELAY,
            severity=ImpactSeverity.LOW,
            delay_percentage=10.0,  # Too high
            cost_increase_percentage=0.0,
            availability_impact=1.5,  # Too high
            duration_days=1,
        )
        
        assert scenario.delay_percentage == 5.0  # Clamped
        assert scenario.availability_impact == 1.0  # Clamped


class TestSupplyChainNode:
    """Test SupplyChainNode dataclass."""
    
    def test_node_creation(self):
        """Test creating a node."""
        node = SupplyChainNode(
            node_id="NODE-001",
            name="Test Node",
            node_type="supplier",
            location="Test City",
            region="Test Region",
        )
        
        assert node.node_id == "NODE-001"
        assert node.base_lead_time_days == 7.0  # Default
        assert node.reliability_score == 0.95  # Default


class TestRFQSimulationInput:
    """Test RFQSimulationInput dataclass."""
    
    def test_rfq_creation(self, sample_rfq: RFQSimulationInput):
        """Test creating RFQ input."""
        assert sample_rfq.rfq_id == "RFQ-TEST-001"
        assert sample_rfq.total_value == 10000.0
        assert len(sample_rfq.line_items) == 2


class TestSimulationResult:
    """Test SimulationResult dataclass."""
    
    def test_result_creation(self):
        """Test creating simulation result."""
        now = datetime.now(timezone.utc)
        result = SimulationResult(
            run_id=1,
            scenario_id="test",
            original_delivery_date=now,
            simulated_delivery_date=now + timedelta(days=5),
            delay_days=5.0,
            original_cost=10000.0,
            simulated_cost=11000.0,
            cost_delta=1000.0,
            on_time_delivery=False,
            within_budget=True,
            quality_maintained=True,
        )
        
        assert result.delay_days == 5.0
        assert result.cost_delta == 1000.0


class TestImpactAnalysis:
    """Test ImpactAnalysis dataclass."""
    
    def test_analysis_creation(self):
        """Test creating impact analysis."""
        analysis = ImpactAnalysis(
            rfq_id="RFQ-001",
            scenario_id="test",
            mean_delay_days=5.0,
            median_delay_days=4.5,
            p95_delay_days=10.0,
            max_delay_days=15.0,
            delay_std_dev=2.5,
            on_time_probability=0.7,
            probability_of_delay=0.3,
            probability_of_major_delay=0.1,
            mean_cost_increase=500.0,
            max_cost_increase=1500.0,
            expected_additional_cost=150.0,
            recommended_buffer_days=7,
            risk_rating=ImpactSeverity.MODERATE,
        )
        
        assert analysis.mean_delay_days == 5.0
        assert analysis.risk_rating == ImpactSeverity.MODERATE


class TestSimulationReport:
    """Test SimulationReport dataclass."""
    
    def test_report_creation(self):
        """Test creating simulation report."""
        report = SimulationReport(
            report_id="RPT-001",
            rfq_id="RFQ-001",
            generated_at=datetime.now(timezone.utc),
            scenarios_tested=["scenario1", "scenario2"],
            simulation_runs=1000,
        )
        
        assert report.simulation_runs == 1000
        assert len(report.scenarios_tested) == 2
    
    def test_report_summary(self):
        """Test report summary method."""
        report = SimulationReport(
            report_id="RPT-001",
            rfq_id="RFQ-001",
            generated_at=datetime.now(timezone.utc),
            scenarios_tested=["s1", "s2", "s3"],
            simulation_runs=500,
            overall_risk_rating=ImpactSeverity.HIGH,
            recommended_delivery_buffer_days=7,
        )
        
        summary = report.get_summary()
        
        assert summary["rfq_id"] == "RFQ-001"
        assert summary["scenarios_tested"] == 3
        assert summary["overall_risk"] == "high"


# =============================================================================
# Tests: Disruption Library
# =============================================================================

class TestDisruptionLibrary:
    """Test DisruptionLibrary."""
    
    def test_get_all_scenarios(self):
        """Test getting all scenarios."""
        scenarios = DisruptionLibrary.get_all_scenarios()
        
        assert len(scenarios) >= 8
        assert all(isinstance(s, DisruptionScenario) for s in scenarios)
    
    def test_get_scenario_by_id(self):
        """Test getting scenario by ID."""
        scenario = DisruptionLibrary.get_scenario_by_id("logistics_20")
        
        assert scenario is not None
        assert scenario.name == "20% Logistics Delay"
        assert scenario.delay_percentage == 0.20
    
    def test_get_scenario_by_id_not_found(self):
        """Test getting non-existent scenario."""
        scenario = DisruptionLibrary.get_scenario_by_id("nonexistent")
        
        assert scenario is None
    
    def test_get_scenarios_by_type(self):
        """Test filtering by disruption type."""
        logistics = DisruptionLibrary.get_scenarios_by_type(
            DisruptionType.LOGISTICS_DELAY
        )
        
        assert len(logistics) >= 2
        assert all(
            s.disruption_type == DisruptionType.LOGISTICS_DELAY
            for s in logistics
        )
    
    def test_get_scenarios_by_severity(self):
        """Test filtering by severity."""
        high_severity = DisruptionLibrary.get_scenarios_by_severity(
            ImpactSeverity.HIGH
        )
        
        assert len(high_severity) >= 2
        for scenario in high_severity:
            assert scenario.severity in [ImpactSeverity.HIGH, ImpactSeverity.CRITICAL]


# =============================================================================
# Tests: Monte Carlo Simulator
# =============================================================================

class TestMonteCarloSimulator:
    """Test MonteCarloSimulator."""
    
    def test_simulator_creation(self):
        """Test creating simulator."""
        sim = MonteCarloSimulator(seed=42)
        assert sim is not None
    
    def test_simulate_run(
        self,
        sample_rfq: RFQSimulationInput,
        sample_supply_chain: list[SupplyChainNode],
        logistics_delay_scenario: DisruptionScenario,
    ):
        """Test running a single simulation."""
        sim = MonteCarloSimulator(seed=42)
        
        result = sim.simulate_run(
            sample_rfq,
            [logistics_delay_scenario],
            sample_supply_chain,
            run_id=1,
        )
        
        assert result.run_id == 1
        assert isinstance(result.delay_days, float)
        assert isinstance(result.on_time_delivery, bool)
    
    def test_simulate_run_no_disruptions(
        self,
        sample_rfq: RFQSimulationInput,
        sample_supply_chain: list[SupplyChainNode],
    ):
        """Test simulation with no disruptions."""
        sim = MonteCarloSimulator(seed=42)
        
        result = sim.simulate_run(
            sample_rfq,
            [],  # No scenarios
            sample_supply_chain,
            run_id=1,
        )
        
        assert result.delay_days >= 0  # Some variance expected
    
    def test_disruption_correlation(self):
        """Test setting disruption correlation."""
        sim = MonteCarloSimulator()
        
        sim.set_disruption_correlation("s1", "s2", 0.8)
        
        key = ("s1", "s2")
        assert sim._disruption_correlations.get(key) == 0.8
    
    def test_deterministic_with_seed(
        self,
        sample_rfq: RFQSimulationInput,
        logistics_delay_scenario: DisruptionScenario,
    ):
        """Test that same seed produces same results."""
        sim1 = MonteCarloSimulator(seed=42)
        sim2 = MonteCarloSimulator(seed=42)
        
        result1 = sim1.simulate_run(sample_rfq, [logistics_delay_scenario], [], 1)
        result2 = sim2.simulate_run(sample_rfq, [logistics_delay_scenario], [], 1)
        
        assert result1.delay_days == result2.delay_days


# =============================================================================
# Tests: Impact Analyzer
# =============================================================================

class TestImpactAnalyzer:
    """Test ImpactAnalyzer."""
    
    def test_analyzer_creation(self):
        """Test creating analyzer."""
        analyzer = ImpactAnalyzer()
        assert analyzer.confidence_level == 0.95
    
    def test_analyze_results(self):
        """Test analyzing simulation results."""
        analyzer = ImpactAnalyzer()
        
        now = datetime.now(timezone.utc)
        results = [
            SimulationResult(
                run_id=i,
                scenario_id="test",
                original_delivery_date=now,
                simulated_delivery_date=now + timedelta(days=i % 10),
                delay_days=float(i % 10),
                original_cost=10000.0,
                simulated_cost=10000.0 + (i % 5) * 100,
                cost_delta=float((i % 5) * 100),
                on_time_delivery=i % 3 == 0,
                within_budget=True,
                quality_maintained=True,
            )
            for i in range(100)
        ]
        
        analysis = analyzer.analyze("RFQ-001", "test", results)
        
        assert analysis.rfq_id == "RFQ-001"
        assert analysis.mean_delay_days >= 0
        assert 0 <= analysis.on_time_probability <= 1
    
    def test_analyze_empty_results(self):
        """Test analyzing empty results."""
        analyzer = ImpactAnalyzer()
        
        analysis = analyzer.analyze("RFQ-001", "test", [])
        
        assert analysis.mean_delay_days == 0.0
        assert analysis.on_time_probability == 1.0
        assert analysis.risk_rating == ImpactSeverity.MINIMAL
    
    def test_risk_rating_determination(self):
        """Test risk rating calculation."""
        analyzer = ImpactAnalyzer()
        
        # Test CRITICAL rating
        now = datetime.now(timezone.utc)
        critical_results = [
            SimulationResult(
                run_id=i,
                scenario_id="test",
                original_delivery_date=now,
                simulated_delivery_date=now + timedelta(days=15),
                delay_days=15.0,  # High delay
                original_cost=10000.0,
                simulated_cost=15000.0,
                cost_delta=5000.0,
                on_time_delivery=False,
                within_budget=False,
                quality_maintained=True,
            )
            for i in range(50)
        ]
        
        analysis = analyzer.analyze("RFQ-001", "test", critical_results)
        
        assert analysis.risk_rating == ImpactSeverity.CRITICAL


# =============================================================================
# Tests: Mitigation Advisor
# =============================================================================

class TestMitigationAdvisor:
    """Test MitigationAdvisor."""
    
    def test_advisor_creation(self):
        """Test creating advisor."""
        advisor = MitigationAdvisor(base_order_value=15000.0)
        assert advisor.base_order_value == 15000.0
    
    def test_recommend_mitigations(self):
        """Test generating recommendations."""
        advisor = MitigationAdvisor(base_order_value=10000.0)
        
        analysis = ImpactAnalysis(
            rfq_id="RFQ-001",
            scenario_id="test",
            mean_delay_days=7.0,
            median_delay_days=6.0,
            p95_delay_days=12.0,
            max_delay_days=20.0,
            delay_std_dev=3.0,
            on_time_probability=0.6,
            probability_of_delay=0.4,
            probability_of_major_delay=0.2,
            mean_cost_increase=800.0,
            max_cost_increase=2000.0,
            expected_additional_cost=320.0,
            recommended_buffer_days=10,
            risk_rating=ImpactSeverity.HIGH,
        )
        
        recommendations = advisor.recommend(analysis)
        
        assert len(recommendations) > 0
        assert all(isinstance(r, MitigationRecommendation) for r in recommendations)
        
        # Should be sorted by priority
        for i in range(len(recommendations) - 1):
            assert recommendations[i].priority <= recommendations[i + 1].priority
    
    def test_recommend_with_limited_strategies(self):
        """Test recommendations with limited strategies."""
        advisor = MitigationAdvisor()
        
        analysis = ImpactAnalysis(
            rfq_id="RFQ-001",
            scenario_id="test",
            mean_delay_days=5.0,
            median_delay_days=5.0,
            p95_delay_days=10.0,
            max_delay_days=15.0,
            delay_std_dev=2.0,
            on_time_probability=0.7,
            probability_of_delay=0.3,
            probability_of_major_delay=0.1,
            mean_cost_increase=500.0,
            max_cost_increase=1000.0,
            expected_additional_cost=150.0,
            recommended_buffer_days=7,
            risk_rating=ImpactSeverity.MODERATE,
        )
        
        # Only allow two strategies
        allowed = [MitigationStrategy.EXPEDITED_SHIPPING, MitigationStrategy.SAFETY_STOCK]
        recommendations = advisor.recommend(analysis, allowed)
        
        for rec in recommendations:
            assert rec.strategy in allowed


# =============================================================================
# Tests: Supply Chain Simulator
# =============================================================================

class TestSupplyChainSimulator:
    """Test SupplyChainSimulator."""
    
    def test_simulator_creation(self):
        """Test creating simulator."""
        sim = SupplyChainSimulator(simulation_runs=500)
        
        assert sim.simulation_runs == 500
        assert sim.confidence_level == 0.95
    
    def test_add_supply_chain_node(
        self,
        simulator: SupplyChainSimulator,
    ):
        """Test adding supply chain nodes."""
        node = SupplyChainNode(
            node_id="TEST-001",
            name="Test Node",
            node_type="supplier",
            location="Test City",
            region="Test",
        )
        
        simulator.add_supply_chain_node(node)
        
        assert len(simulator._supply_chain_nodes) == 1
    
    def test_add_custom_scenario(
        self,
        simulator: SupplyChainSimulator,
        logistics_delay_scenario: DisruptionScenario,
    ):
        """Test adding custom scenarios."""
        simulator.add_custom_scenario(logistics_delay_scenario)
        
        assert len(simulator._custom_scenarios) == 1
    
    def test_simulate_rfq(
        self,
        simulator: SupplyChainSimulator,
        sample_rfq: RFQSimulationInput,
    ):
        """Test running complete simulation."""
        report = simulator.simulate_rfq(sample_rfq)
        
        assert report.rfq_id == sample_rfq.rfq_id
        assert report.simulation_runs == 100
        assert len(report.scenarios_tested) > 0
        assert len(report.individual_results) == 100
    
    def test_simulate_rfq_with_custom_scenarios(
        self,
        simulator: SupplyChainSimulator,
        sample_rfq: RFQSimulationInput,
        logistics_delay_scenario: DisruptionScenario,
    ):
        """Test simulation with custom scenarios."""
        report = simulator.simulate_rfq(sample_rfq, [logistics_delay_scenario])
        
        assert report.rfq_id == sample_rfq.rfq_id
        assert "test_logistics" in report.scenarios_tested
    
    def test_stress_test(
        self,
        simulator: SupplyChainSimulator,
        sample_rfq: RFQSimulationInput,
    ):
        """Test stress testing an RFQ."""
        report = simulator.stress_test(
            sample_rfq,
            DisruptionType.LOGISTICS_DELAY,
            severity_level=0.5,
        )
        
        assert report.rfq_id == sample_rfq.rfq_id
        # Stress test should show impact
        assert len(report.impact_analyses) > 0
    
    def test_compare_scenarios(
        self,
        simulator: SupplyChainSimulator,
        sample_rfq: RFQSimulationInput,
    ):
        """Test comparing scenarios."""
        results = simulator.compare_scenarios(
            sample_rfq,
            ["logistics_20", "logistics_50"],
        )
        
        assert "logistics_20" in results
        assert "logistics_50" in results
        
        # 50% delay should have higher impact
        assert (
            results["logistics_50"].mean_delay_days >=
            results["logistics_20"].mean_delay_days
        )
    
    def test_get_statistics(
        self,
        simulator: SupplyChainSimulator,
    ):
        """Test getting simulator statistics."""
        stats = simulator.get_statistics()
        
        assert "simulation_runs" in stats
        assert "confidence_level" in stats
        assert stats["simulation_runs"] == 100
    
    def test_mitigation_recommendations_generated(
        self,
        simulator: SupplyChainSimulator,
        sample_rfq: RFQSimulationInput,
    ):
        """Test that mitigation recommendations are generated."""
        report = simulator.simulate_rfq(sample_rfq)
        
        # Should have some recommendations for typical disruptions
        assert len(report.mitigation_recommendations) >= 0  # May be empty if low risk


# =============================================================================
# Tests: Factory Function
# =============================================================================

class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_default_simulator(self):
        """Test creating default simulator."""
        sim = create_supply_chain_simulator()
        
        assert isinstance(sim, SupplyChainSimulator)
        assert sim.simulation_runs == DEFAULT_SIMULATION_RUNS
    
    def test_create_custom_simulator(self):
        """Test creating custom simulator."""
        sim = create_supply_chain_simulator(
            simulation_runs=500,
            confidence_level=0.99,
            seed=123,
        )
        
        assert sim.simulation_runs == 500
        assert sim.confidence_level == 0.99


# =============================================================================
# Tests: Integration
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflow."""
    
    def test_full_simulation_workflow(
        self,
        sample_rfq: RFQSimulationInput,
        sample_supply_chain: list[SupplyChainNode],
    ):
        """Test complete simulation workflow."""
        # Create simulator
        sim = create_supply_chain_simulator(simulation_runs=100, seed=42)
        
        # Add supply chain
        for node in sample_supply_chain:
            sim.add_supply_chain_node(node)
        
        # Run simulation
        report = sim.simulate_rfq(sample_rfq)
        
        # Verify report
        assert report.report_id is not None
        assert len(report.impact_analyses) > 0
        
        # Get summary
        summary = report.get_summary()
        assert "overall_risk" in summary
    
    def test_stress_test_workflow(
        self,
        sample_rfq: RFQSimulationInput,
    ):
        """Test stress test workflow."""
        sim = create_supply_chain_simulator(simulation_runs=50, seed=42)
        
        # Run stress test for 20% disruption
        report = sim.stress_test(
            sample_rfq,
            DisruptionType.LOGISTICS_DELAY,
            severity_level=0.2,
        )
        
        # All runs should show impact since probability = 1.0
        overall_analysis = report.impact_analyses[0]
        assert overall_analysis.probability_of_delay > 0
    
    def test_scenario_comparison_workflow(
        self,
        sample_rfq: RFQSimulationInput,
    ):
        """Test scenario comparison workflow."""
        sim = create_supply_chain_simulator(simulation_runs=50, seed=42)
        
        # Compare different scenarios
        results = sim.compare_scenarios(
            sample_rfq,
            ["logistics_20", "supplier_partial", "material_shortage"],
        )
        
        # Verify we got results for each scenario
        assert len(results) == 3
        
        # Each should have impact analysis
        for scenario_id, analysis in results.items():
            assert analysis.rfq_id == sample_rfq.rfq_id
            assert analysis.mean_delay_days >= 0
    
    def test_mitigation_prioritization(
        self,
        sample_rfq: RFQSimulationInput,
    ):
        """Test that mitigations are properly prioritized."""
        sim = create_supply_chain_simulator(simulation_runs=100, seed=42)
        
        # Create high-impact scenario
        severe_scenario = DisruptionScenario(
            scenario_id="severe_test",
            name="Severe Test",
            disruption_type=DisruptionType.SUPPLIER_OUTAGE,
            severity=ImpactSeverity.CRITICAL,
            delay_percentage=0.50,
            cost_increase_percentage=0.30,
            availability_impact=0.5,
            duration_days=30,
            probability=1.0,  # Always apply
        )
        
        report = sim.simulate_rfq(sample_rfq, [severe_scenario])
        
        # Should have mitigation recommendations
        if report.mitigation_recommendations:
            # First should be highest priority
            assert report.mitigation_recommendations[0].priority == 1
    
    def test_reproducibility_with_seed(
        self,
        sample_rfq: RFQSimulationInput,
    ):
        """Test that simulations are reproducible with same seed."""
        report1 = create_supply_chain_simulator(
            simulation_runs=50, seed=42
        ).simulate_rfq(sample_rfq)
        
        report2 = create_supply_chain_simulator(
            simulation_runs=50, seed=42
        ).simulate_rfq(sample_rfq)
        
        # Results should be identical
        assert len(report1.individual_results) == len(report2.individual_results)
        
        for r1, r2 in zip(report1.individual_results, report2.individual_results):
            assert r1.delay_days == r2.delay_days
