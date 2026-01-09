"""
Tests for Predictive Utility & Resource Forecasting.

Tests cover:
- Time series decomposition
- Demand forecasting
- Resource forecasting
- Capacity planning
- What-if simulations
"""

import pytest
from datetime import datetime, timezone, timedelta
import math

from sensei.services.predictive_utility_forecasting import (
    # Enums
    ResourceType,
    ForecastHorizon,
    TrendDirection,
    SeasonalityType,
    CapacityStatus,
    # Data models
    ResourceData,
    TimeSeriesPoint,
    SeasonalComponent,
    TrendComponent,
    ForecastPoint,
    ResourceForecast,
    CapacityPlan,
    DemandForecast,
    # Components
    TimeSeriesDecomposer,
    DemandForecaster,
    ResourceForecaster,
    CapacityPlanner,
    WhatIfSimulator,
    PredictiveUtilityEngine,
    # Factory
    create_utility_forecaster,
    # Constants
    UTILIZATION_THRESHOLDS,
    MINIMUM_HISTORY_POINTS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_resource_data() -> list[ResourceData]:
    """Create sample resource data."""
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    data = []
    
    for i in range(30):
        # Simulate utilization with slight upward trend
        utilization = 0.6 + (i * 0.005) + (0.05 * math.sin(i * 0.5))
        utilization = max(0.0, min(1.0, utilization))
        
        data.append(ResourceData(
            timestamp=base_time + timedelta(days=i),
            resource_id="MACHINE-001",
            resource_type=ResourceType.MACHINE,
            utilization=utilization,
            capacity=100.0,
            actual_usage=utilization * 100.0,
        ))
    
    return data


@pytest.fixture
def sample_time_series() -> list[TimeSeriesPoint]:
    """Create sample time series."""
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    points = []
    
    for i in range(30):
        value = 0.5 + (i * 0.01) + (0.1 * math.sin(i / 7 * 2 * math.pi))
        points.append(TimeSeriesPoint(
            timestamp=base_time + timedelta(days=i),
            value=value,
        ))
    
    return points


@pytest.fixture
def sample_demand_data() -> list[tuple[datetime, float]]:
    """Create sample demand data."""
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    data = []
    
    for i in range(30):
        demand = 100 + (i * 2) + (20 * math.sin(i / 7 * 2 * math.pi))
        data.append((base_time + timedelta(days=i), demand))
    
    return data


@pytest.fixture
def utility_engine(sample_resource_data: list[ResourceData]) -> PredictiveUtilityEngine:
    """Create engine with sample data."""
    engine = create_utility_forecaster()
    engine.add_data_batch(sample_resource_data)
    return engine


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_resource_type_values(self):
        """Test ResourceType values."""
        assert ResourceType.MACHINE.value == "machine"
        assert ResourceType.LABOR.value == "labor"
        assert ResourceType.ENERGY.value == "energy"
    
    def test_forecast_horizon_values(self):
        """Test ForecastHorizon values."""
        assert ForecastHorizon.SHORT_TERM.value == "short_term"
        assert ForecastHorizon.LONG_TERM.value == "long_term"
    
    def test_trend_direction_values(self):
        """Test TrendDirection values."""
        assert TrendDirection.INCREASING.value == "increasing"
        assert TrendDirection.STABLE.value == "stable"
    
    def test_seasonality_type_values(self):
        """Test SeasonalityType values."""
        assert SeasonalityType.WEEKLY.value == "weekly"
        assert SeasonalityType.MONTHLY.value == "monthly"
    
    def test_capacity_status_values(self):
        """Test CapacityStatus values."""
        assert CapacityStatus.OPTIMAL.value == "optimal"
        assert CapacityStatus.OVERCAPACITY.value == "overcapacity"


# =============================================================================
# Tests: Data Models
# =============================================================================

class TestResourceData:
    """Test ResourceData dataclass."""
    
    def test_creation(self):
        """Test creating resource data."""
        data = ResourceData(
            timestamp=datetime.now(timezone.utc),
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            utilization=0.75,
            capacity=100.0,
            actual_usage=75.0,
        )
        
        assert data.resource_id == "RES-001"
        assert data.utilization == 0.75


class TestTimeSeriesPoint:
    """Test TimeSeriesPoint dataclass."""
    
    def test_creation(self):
        """Test creating time series point."""
        point = TimeSeriesPoint(
            timestamp=datetime.now(timezone.utc),
            value=0.5,
        )
        
        assert point.value == 0.5
    
    def test_comparison(self):
        """Test point comparison."""
        now = datetime.now(timezone.utc)
        p1 = TimeSeriesPoint(timestamp=now, value=1.0)
        p2 = TimeSeriesPoint(timestamp=now + timedelta(days=1), value=2.0)
        
        assert p1 < p2


class TestSeasonalComponent:
    """Test SeasonalComponent dataclass."""
    
    def test_get_seasonal_factor_no_pattern(self):
        """Test seasonal factor with no pattern."""
        component = SeasonalComponent(
            seasonality_type=SeasonalityType.NONE,
            period_days=0,
            strength=0.0,
        )
        
        assert component.get_seasonal_factor(0) == 1.0
    
    def test_get_seasonal_factor_with_pattern(self):
        """Test seasonal factor with pattern."""
        component = SeasonalComponent(
            seasonality_type=SeasonalityType.WEEKLY,
            period_days=7,
            strength=0.5,
            pattern=[0.1, -0.1, 0.2, -0.2, 0.1, 0.0, -0.1],
        )
        
        factor = component.get_seasonal_factor(0)
        assert factor != 1.0


class TestTrendComponent:
    """Test TrendComponent dataclass."""
    
    def test_predict(self):
        """Test trend prediction."""
        trend = TrendComponent(
            direction=TrendDirection.INCREASING,
            slope=0.01,
            intercept=0.5,
        )
        
        assert trend.predict(0) == 0.5
        assert trend.predict(10) == 0.6


class TestForecastPoint:
    """Test ForecastPoint dataclass."""
    
    def test_uncertainty(self):
        """Test uncertainty calculation."""
        point = ForecastPoint(
            timestamp=datetime.now(timezone.utc),
            predicted_value=0.7,
            lower_bound=0.6,
            upper_bound=0.8,
        )
        
        assert abs(point.uncertainty - 0.2) < 1e-10


class TestResourceForecast:
    """Test ResourceForecast dataclass."""
    
    def test_average_predicted_utilization(self):
        """Test average utilization calculation."""
        now = datetime.now(timezone.utc)
        
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.SHORT_TERM,
            forecasts=[
                ForecastPoint(now, 0.6, 0.5, 0.7),
                ForecastPoint(now + timedelta(days=1), 0.8, 0.7, 0.9),
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.7),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        assert forecast.average_predicted_utilization == 0.7
    
    def test_peak_utilization(self):
        """Test peak utilization."""
        now = datetime.now(timezone.utc)
        
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.SHORT_TERM,
            forecasts=[
                ForecastPoint(now, 0.6, 0.5, 0.7),
                ForecastPoint(now + timedelta(days=1), 0.9, 0.8, 1.0),
                ForecastPoint(now + timedelta(days=2), 0.7, 0.6, 0.8),
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.7),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        _, peak = forecast.peak_utilization
        assert peak == 0.9
    
    def test_get_capacity_status(self):
        """Test capacity status calculation."""
        now = datetime.now(timezone.utc)
        
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.SHORT_TERM,
            forecasts=[
                ForecastPoint(now, 0.7, 0.6, 0.8),
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.7),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        assert forecast.get_capacity_status() == CapacityStatus.OPTIMAL


# =============================================================================
# Tests: Time Series Decomposer
# =============================================================================

class TestTimeSeriesDecomposer:
    """Test TimeSeriesDecomposer."""
    
    def test_decomposer_creation(self):
        """Test creating decomposer."""
        decomposer = TimeSeriesDecomposer()
        assert decomposer is not None
    
    def test_decompose_insufficient_data(self):
        """Test decomposition with insufficient data."""
        decomposer = TimeSeriesDecomposer()
        
        data = [
            TimeSeriesPoint(datetime.now(timezone.utc), 0.5),
        ]
        
        trend, seasonality, residuals = decomposer.decompose(data)
        
        assert trend.direction == TrendDirection.STABLE
        assert seasonality.seasonality_type == SeasonalityType.NONE
    
    def test_decompose_with_trend(self, sample_time_series: list[TimeSeriesPoint]):
        """Test decomposition extracts trend."""
        decomposer = TimeSeriesDecomposer()
        
        trend, seasonality, residuals = decomposer.decompose(sample_time_series)
        
        # Should detect increasing trend
        assert trend.slope > 0 or trend.direction == TrendDirection.STABLE
    
    def test_moving_average(self):
        """Test moving average calculation."""
        decomposer = TimeSeriesDecomposer()
        
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        ma = decomposer._calculate_moving_average(values, 3)
        
        assert len(ma) == len(values)
        assert ma[3] == pytest.approx(4.0, rel=0.1)
    
    def test_fit_linear_trend(self):
        """Test linear trend fitting."""
        decomposer = TimeSeriesDecomposer()
        
        # Clear upward trend
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        trend = decomposer._fit_linear_trend(values)
        
        assert trend.slope > 0
        assert trend.direction == TrendDirection.INCREASING


# =============================================================================
# Tests: Demand Forecaster
# =============================================================================

class TestDemandForecaster:
    """Test DemandForecaster."""
    
    def test_forecaster_creation(self):
        """Test creating forecaster."""
        forecaster = DemandForecaster()
        assert forecaster is not None
    
    def test_forecast_empty_data(self):
        """Test forecasting with empty data."""
        forecaster = DemandForecaster()
        
        result = forecaster.forecast([], horizon_days=7)
        
        assert result.total_demand_units == 0.0
    
    def test_forecast_basic(self, sample_demand_data: list[tuple[datetime, float]]):
        """Test basic forecasting."""
        forecaster = DemandForecaster()
        
        result = forecaster.forecast(sample_demand_data, horizon_days=7)
        
        assert len(result.daily_forecasts) == 7
        assert result.total_demand_units > 0
    
    def test_forecast_peak_detection(self, sample_demand_data: list[tuple[datetime, float]]):
        """Test peak detection in forecast."""
        forecaster = DemandForecaster()
        
        result = forecaster.forecast(sample_demand_data, horizon_days=14)
        
        assert result.peak_demand_units >= 0
        assert result.peak_date is not None
    
    def test_double_exponential_smoothing(self):
        """Test exponential smoothing."""
        forecaster = DemandForecaster()
        
        values = [100, 110, 120, 130, 140]
        forecasts = forecaster._double_exponential_smoothing(values, 3)
        
        assert len(forecasts) == 3
        # With upward trend, forecasts should continue increasing
        assert forecasts[0] > values[-1] * 0.9


# =============================================================================
# Tests: Resource Forecaster
# =============================================================================

class TestResourceForecaster:
    """Test ResourceForecaster."""
    
    def test_forecaster_creation(self):
        """Test creating forecaster."""
        forecaster = ResourceForecaster()
        assert forecaster is not None
    
    def test_forecast_empty_data(self):
        """Test forecasting with empty data."""
        forecaster = ResourceForecaster()
        
        result = forecaster.forecast([])
        
        assert len(result.forecasts) == 0
    
    def test_forecast_basic(self, sample_resource_data: list[ResourceData]):
        """Test basic forecasting."""
        forecaster = ResourceForecaster()
        
        result = forecaster.forecast(sample_resource_data)
        
        assert len(result.forecasts) > 0
        assert result.resource_id == "MACHINE-001"
    
    def test_forecast_horizons(self, sample_resource_data: list[ResourceData]):
        """Test different forecast horizons."""
        forecaster = ResourceForecaster()
        
        short = forecaster.forecast(sample_resource_data, ForecastHorizon.SHORT_TERM)
        medium = forecaster.forecast(sample_resource_data, ForecastHorizon.MEDIUM_TERM)
        long = forecaster.forecast(sample_resource_data, ForecastHorizon.LONG_TERM)
        
        assert len(short.forecasts) < len(medium.forecasts) < len(long.forecasts)
    
    def test_confidence_intervals(self, sample_resource_data: list[ResourceData]):
        """Test confidence intervals are generated."""
        forecaster = ResourceForecaster()
        
        result = forecaster.forecast(sample_resource_data)
        
        for point in result.forecasts:
            assert point.lower_bound <= point.predicted_value <= point.upper_bound


# =============================================================================
# Tests: Capacity Planner
# =============================================================================

class TestCapacityPlanner:
    """Test CapacityPlanner."""
    
    def test_planner_creation(self):
        """Test creating planner."""
        planner = CapacityPlanner()
        assert planner is not None
    
    def test_plan_empty_forecast(self):
        """Test planning with empty forecast."""
        planner = CapacityPlanner()
        
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.5),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        plan = planner.plan(forecast, current_capacity=100.0)
        
        assert plan.recommended_capacity == 100.0
    
    def test_plan_increase_capacity(self):
        """Test planning recommends capacity increase."""
        planner = CapacityPlanner(target_utilization=0.75)
        now = datetime.now(timezone.utc)
        
        # High utilization forecast
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[
                ForecastPoint(now + timedelta(days=i), 0.9, 0.85, 0.95)
                for i in range(7)
            ],
            trend=TrendComponent(TrendDirection.INCREASING, 0.01, 0.9),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        plan = planner.plan(forecast, current_capacity=100.0)
        
        assert plan.capacity_change > 0
    
    def test_plan_decrease_capacity(self):
        """Test planning recommends capacity decrease."""
        planner = CapacityPlanner(target_utilization=0.75)
        now = datetime.now(timezone.utc)
        
        # Low utilization forecast
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[
                ForecastPoint(now + timedelta(days=i), 0.3, 0.25, 0.35)
                for i in range(7)
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.3),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        plan = planner.plan(forecast, current_capacity=100.0)
        
        assert plan.capacity_change < 0
    
    def test_plan_cost_impact(self):
        """Test cost impact calculation."""
        planner = CapacityPlanner()
        now = datetime.now(timezone.utc)
        
        forecast = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[
                ForecastPoint(now, 0.9, 0.85, 0.95),
            ],
            trend=TrendComponent(TrendDirection.INCREASING, 0.01, 0.9),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        plan = planner.plan(forecast, current_capacity=100.0, cost_per_unit=50.0)
        
        # Cost impact should reflect capacity change
        expected_cost = (plan.recommended_capacity - 100.0) * 50.0
        assert abs(plan.cost_impact - expected_cost) < 1.0


# =============================================================================
# Tests: What-If Simulator
# =============================================================================

class TestWhatIfSimulator:
    """Test WhatIfSimulator."""
    
    def test_simulator_creation(self):
        """Test creating simulator."""
        forecaster = ResourceForecaster()
        simulator = WhatIfSimulator(forecaster)
        assert simulator is not None
    
    def test_simulate_demand_increase(self):
        """Test simulating demand increase."""
        forecaster = ResourceForecaster()
        simulator = WhatIfSimulator(forecaster)
        now = datetime.now(timezone.utc)
        
        baseline = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[
                ForecastPoint(now, 0.5, 0.4, 0.6),
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.5),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        increased = simulator.simulate_demand_change(baseline, 1.5)
        
        assert increased.forecasts[0].predicted_value > baseline.forecasts[0].predicted_value
    
    def test_simulate_capacity_increase(self):
        """Test simulating capacity increase."""
        forecaster = ResourceForecaster()
        simulator = WhatIfSimulator(forecaster)
        now = datetime.now(timezone.utc)
        
        baseline = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[
                ForecastPoint(now, 0.8, 0.7, 0.9),
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.8),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        # Increase capacity by 50%
        increased = simulator.simulate_capacity_change(baseline, 1.5)
        
        # Utilization should decrease
        assert increased.forecasts[0].predicted_value < baseline.forecasts[0].predicted_value
    
    def test_compare_scenarios(self):
        """Test comparing scenarios."""
        forecaster = ResourceForecaster()
        simulator = WhatIfSimulator(forecaster)
        now = datetime.now(timezone.utc)
        
        baseline = ResourceForecast(
            forecast_id="FC-001",
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            horizon=ForecastHorizon.MEDIUM_TERM,
            forecasts=[
                ForecastPoint(now, 0.7, 0.6, 0.8),
            ],
            trend=TrendComponent(TrendDirection.STABLE, 0.0, 0.7),
            seasonality=SeasonalComponent(SeasonalityType.NONE, 0, 0.0),
        )
        
        scenario1 = simulator.simulate_demand_change(baseline, 1.2)
        scenario2 = simulator.simulate_capacity_change(baseline, 1.2)
        
        comparison = simulator.compare_scenarios(
            baseline,
            [("demand_up_20", scenario1), ("capacity_up_20", scenario2)],
        )
        
        assert "baseline" in comparison
        assert "scenarios" in comparison
        assert len(comparison["scenarios"]) == 2


# =============================================================================
# Tests: Predictive Utility Engine
# =============================================================================

class TestPredictiveUtilityEngine:
    """Test PredictiveUtilityEngine."""
    
    def test_engine_creation(self):
        """Test creating engine."""
        engine = PredictiveUtilityEngine()
        assert engine is not None
    
    def test_add_data(self):
        """Test adding data."""
        engine = PredictiveUtilityEngine()
        
        data = ResourceData(
            timestamp=datetime.now(timezone.utc),
            resource_id="RES-001",
            resource_type=ResourceType.MACHINE,
            utilization=0.7,
            capacity=100.0,
            actual_usage=70.0,
        )
        
        engine.add_data(data)
        
        assert "RES-001" in engine.get_resource_ids()
    
    def test_add_data_batch(self, sample_resource_data: list[ResourceData]):
        """Test adding batch data."""
        engine = PredictiveUtilityEngine()
        
        engine.add_data_batch(sample_resource_data)
        
        assert len(engine._resource_history["MACHINE-001"]) == 30
    
    def test_forecast_resource(self, utility_engine: PredictiveUtilityEngine):
        """Test forecasting resource."""
        forecast = utility_engine.forecast_resource("MACHINE-001")
        
        assert forecast.resource_id == "MACHINE-001"
        assert len(forecast.forecasts) > 0
    
    def test_forecast_all_resources(self, sample_resource_data: list[ResourceData]):
        """Test forecasting all resources."""
        engine = PredictiveUtilityEngine()
        
        # Add data for multiple resources
        for data in sample_resource_data:
            engine.add_data(data)
        
        # Add another resource
        for i in range(15):
            engine.add_data(ResourceData(
                timestamp=datetime.now(timezone.utc) - timedelta(days=15-i),
                resource_id="MACHINE-002",
                resource_type=ResourceType.MACHINE,
                utilization=0.5 + (i * 0.02),
                capacity=50.0,
                actual_usage=25.0,
            ))
        
        forecasts = engine.forecast_all_resources()
        
        assert len(forecasts) == 2
    
    def test_plan_capacity(self, utility_engine: PredictiveUtilityEngine):
        """Test capacity planning."""
        plan = utility_engine.plan_capacity("MACHINE-001", current_capacity=100.0)
        
        assert plan.resource_id == "MACHINE-001"
        assert plan.current_capacity == 100.0
    
    def test_simulate_demand_change(self, utility_engine: PredictiveUtilityEngine):
        """Test demand simulation."""
        # First generate forecast
        utility_engine.forecast_resource("MACHINE-001")
        
        # Then simulate
        result = utility_engine.simulate_demand_change("MACHINE-001", 20.0)
        
        assert result.resource_id == "MACHINE-001"
    
    def test_simulate_capacity_change(self, utility_engine: PredictiveUtilityEngine):
        """Test capacity simulation."""
        utility_engine.forecast_resource("MACHINE-001")
        
        result = utility_engine.simulate_capacity_change("MACHINE-001", 50.0)
        
        assert result.resource_id == "MACHINE-001"
    
    def test_get_utilization_summary(self, utility_engine: PredictiveUtilityEngine):
        """Test utilization summary."""
        summary = utility_engine.get_utilization_summary()
        
        assert summary["total_resources"] == 1
        assert "MACHINE-001" in summary["resources"]
    
    def test_forecast_demand(self, sample_demand_data: list[tuple[datetime, float]]):
        """Test demand forecasting."""
        engine = PredictiveUtilityEngine()
        
        forecast = engine.forecast_demand(sample_demand_data, horizon_days=14)
        
        assert len(forecast.daily_forecasts) == 14


# =============================================================================
# Tests: Factory Function
# =============================================================================

class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_default_forecaster(self):
        """Test creating default forecaster."""
        engine = create_utility_forecaster()
        
        assert isinstance(engine, PredictiveUtilityEngine)
    
    def test_create_custom_forecaster(self):
        """Test creating custom forecaster."""
        engine = create_utility_forecaster(
            target_utilization=0.8,
            buffer_percentage=0.2,
        )
        
        assert engine._planner._target_utilization == 0.8
        assert engine._planner._buffer == 0.2


# =============================================================================
# Tests: Integration
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_complete_forecasting_workflow(self):
        """Test complete forecasting workflow."""
        engine = create_utility_forecaster()
        
        # Generate synthetic data
        base_time = datetime.now(timezone.utc) - timedelta(days=60)
        
        for i in range(60):
            # Simulate utilization with trend and weekly seasonality
            day_of_week = i % 7
            weekly_factor = 1.0 + 0.1 * math.sin(day_of_week / 7 * 2 * math.pi)
            utilization = 0.5 + (i * 0.005) * weekly_factor
            utilization = max(0.0, min(1.0, utilization))
            
            engine.add_data(ResourceData(
                timestamp=base_time + timedelta(days=i),
                resource_id="CNC-001",
                resource_type=ResourceType.MACHINE,
                utilization=utilization,
                capacity=100.0,
                actual_usage=utilization * 100.0,
            ))
        
        # Forecast
        forecast = engine.forecast_resource("CNC-001", ForecastHorizon.MEDIUM_TERM)
        
        assert len(forecast.forecasts) > 0
        
        # Plan capacity
        plan = engine.plan_capacity("CNC-001", current_capacity=100.0, cost_per_unit=1000.0)
        
        assert plan.justification != ""
        
        # Get summary
        summary = engine.get_utilization_summary()
        
        assert summary["total_resources"] == 1
    
    def test_what_if_analysis_workflow(self):
        """Test what-if analysis workflow."""
        engine = create_utility_forecaster()
        
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        
        for i in range(30):
            engine.add_data(ResourceData(
                timestamp=base_time + timedelta(days=i),
                resource_id="LASER-001",
                resource_type=ResourceType.MACHINE,
                utilization=0.75 + (0.1 * math.sin(i * 0.5)),
                capacity=50.0,
                actual_usage=37.5,
            ))
        
        # Baseline forecast
        baseline = engine.forecast_resource("LASER-001")
        
        # What if demand increases 30%?
        high_demand = engine.simulate_demand_change("LASER-001", 30.0)
        
        # What if we add 25% more capacity?
        more_capacity = engine.simulate_capacity_change("LASER-001", 25.0)
        
        # Compare
        assert high_demand.average_predicted_utilization > baseline.average_predicted_utilization
        assert more_capacity.average_predicted_utilization < baseline.average_predicted_utilization
    
    def test_multi_resource_planning(self):
        """Test planning for multiple resources."""
        engine = create_utility_forecaster()
        
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Add different resource types
        resources = [
            ("CNC-001", ResourceType.MACHINE, 0.7),
            ("CNC-002", ResourceType.MACHINE, 0.9),
            ("LABOR-001", ResourceType.LABOR, 0.6),
        ]
        
        for res_id, res_type, base_util in resources:
            for i in range(30):
                engine.add_data(ResourceData(
                    timestamp=base_time + timedelta(days=i),
                    resource_id=res_id,
                    resource_type=res_type,
                    utilization=base_util + (0.05 * math.sin(i * 0.3)),
                    capacity=100.0,
                    actual_usage=base_util * 100.0,
                ))
        
        # Forecast all
        forecasts = engine.forecast_all_resources()
        
        assert len(forecasts) == 3
        
        # Summary
        summary = engine.get_utilization_summary()
        
        assert summary["total_resources"] == 3
        assert len(summary["resources"]) == 3
