"""
Predictive Utility & Resource Forecasting Service.

ML-based forecasting for resource utilization using time series analysis
and demand prediction to optimize capacity planning.

Features:
- Time series decomposition
- Demand forecasting
- Capacity planning
- Resource optimization
- What-if simulations
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
import math
import uuid
import statistics


# =============================================================================
# Enums
# =============================================================================

class ResourceType(Enum):
    """Types of resources."""
    
    MACHINE = "machine"
    LABOR = "labor"
    MATERIAL = "material"
    FLOOR_SPACE = "floor_space"
    TOOLING = "tooling"
    ENERGY = "energy"


class ForecastHorizon(Enum):
    """Forecast time horizons."""
    
    SHORT_TERM = "short_term"  # 1-7 days
    MEDIUM_TERM = "medium_term"  # 1-4 weeks
    LONG_TERM = "long_term"  # 1-6 months


class TrendDirection(Enum):
    """Trend direction."""
    
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class SeasonalityType(Enum):
    """Type of seasonality."""
    
    NONE = "none"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class CapacityStatus(Enum):
    """Capacity status."""
    
    UNDERUTILIZED = "underutilized"
    OPTIMAL = "optimal"
    NEAR_CAPACITY = "near_capacity"
    OVERCAPACITY = "overcapacity"


# =============================================================================
# Constants
# =============================================================================

UTILIZATION_THRESHOLDS = {
    CapacityStatus.UNDERUTILIZED: (0.0, 0.5),
    CapacityStatus.OPTIMAL: (0.5, 0.8),
    CapacityStatus.NEAR_CAPACITY: (0.8, 0.95),
    CapacityStatus.OVERCAPACITY: (0.95, float('inf')),
}

DEFAULT_FORECAST_DAYS = 30
MINIMUM_HISTORY_POINTS = 10


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ResourceData:
    """Historical resource usage data point."""
    
    timestamp: datetime
    resource_id: str
    resource_type: ResourceType
    utilization: float  # 0-1
    capacity: float
    actual_usage: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeSeriesPoint:
    """Single point in time series."""
    
    timestamp: datetime
    value: float
    
    def __lt__(self, other: "TimeSeriesPoint") -> bool:
        """Compare by timestamp."""
        return self.timestamp < other.timestamp


@dataclass
class SeasonalComponent:
    """Seasonal component of time series."""
    
    seasonality_type: SeasonalityType
    period_days: int
    strength: float  # 0-1, how strong the seasonality is
    pattern: list[float] = field(default_factory=list)  # Pattern values
    
    def get_seasonal_factor(self, day_offset: int) -> float:
        """Get seasonal factor for given day offset."""
        if not self.pattern or self.strength == 0:
            return 1.0
        
        pattern_idx = day_offset % len(self.pattern)
        return 1.0 + (self.pattern[pattern_idx] * self.strength)


@dataclass
class TrendComponent:
    """Trend component of time series."""
    
    direction: TrendDirection
    slope: float  # Change per day
    intercept: float
    r_squared: float = 0.0  # Fit quality
    
    def predict(self, days_from_start: int) -> float:
        """Predict value at given day offset."""
        return self.intercept + self.slope * days_from_start


@dataclass
class ForecastPoint:
    """Single forecast point."""
    
    timestamp: datetime
    predicted_value: float
    lower_bound: float
    upper_bound: float
    confidence: float = 0.95
    
    @property
    def uncertainty(self) -> float:
        """Calculate uncertainty range."""
        return self.upper_bound - self.lower_bound


@dataclass
class ResourceForecast:
    """Complete forecast for a resource."""
    
    forecast_id: str
    resource_id: str
    resource_type: ResourceType
    horizon: ForecastHorizon
    forecasts: list[ForecastPoint]
    trend: TrendComponent
    seasonality: SeasonalComponent
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def average_predicted_utilization(self) -> float:
        """Get average predicted utilization."""
        if not self.forecasts:
            return 0.0
        return sum(f.predicted_value for f in self.forecasts) / len(self.forecasts)
    
    @property
    def peak_utilization(self) -> tuple[datetime, float]:
        """Get peak predicted utilization."""
        if not self.forecasts:
            return datetime.now(timezone.utc), 0.0
        
        peak = max(self.forecasts, key=lambda f: f.predicted_value)
        return peak.timestamp, peak.predicted_value
    
    def get_capacity_status(self) -> CapacityStatus:
        """Get overall capacity status based on forecast."""
        avg = self.average_predicted_utilization
        
        for status, (low, high) in UTILIZATION_THRESHOLDS.items():
            if low <= avg < high:
                return status
        
        return CapacityStatus.OPTIMAL


@dataclass
class CapacityPlan:
    """Capacity planning recommendation."""
    
    plan_id: str
    resource_id: str
    resource_type: ResourceType
    current_capacity: float
    recommended_capacity: float
    capacity_change: float
    justification: str
    cost_impact: float = 0.0
    implementation_days: int = 0
    risk_level: str = "low"


@dataclass
class DemandForecast:
    """Aggregate demand forecast."""
    
    forecast_id: str
    start_date: datetime
    end_date: datetime
    total_demand_units: float
    peak_demand_units: float
    peak_date: datetime
    daily_forecasts: list[tuple[datetime, float]] = field(default_factory=list)
    confidence_level: float = 0.95


# =============================================================================
# Time Series Decomposition
# =============================================================================

class TimeSeriesDecomposer:
    """
    Decompose time series into trend, seasonal, and residual components.
    
    Uses additive decomposition: Y = Trend + Seasonal + Residual
    """
    
    def __init__(self, min_points: int = MINIMUM_HISTORY_POINTS):
        """Initialize decomposer."""
        self._min_points = min_points
    
    def _calculate_moving_average(
        self,
        values: list[float],
        window: int,
    ) -> list[float]:
        """Calculate centered moving average."""
        if len(values) < window:
            return values.copy()
        
        result = []
        half_window = window // 2
        
        for i in range(len(values)):
            start = max(0, i - half_window)
            end = min(len(values), i + half_window + 1)
            result.append(sum(values[start:end]) / (end - start))
        
        return result
    
    def _fit_linear_trend(
        self,
        values: list[float],
    ) -> TrendComponent:
        """Fit linear trend to values."""
        n = len(values)
        if n < 2:
            return TrendComponent(
                direction=TrendDirection.STABLE,
                slope=0.0,
                intercept=values[0] if values else 0.0,
            )
        
        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = 0.0
        denominator = 0.0
        
        for i, y in enumerate(values):
            numerator += (i - x_mean) * (y - y_mean)
            denominator += (i - x_mean) ** 2
        
        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator
        
        intercept = y_mean - slope * x_mean
        
        # Calculate R-squared
        ss_tot = sum((y - y_mean) ** 2 for y in values)
        ss_res = sum((y - (intercept + slope * i)) ** 2 for i, y in enumerate(values))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Determine direction
        # Low R² with meaningful slope → data is volatile (noisy, no clear trend)
        if r_squared < 0.15 and abs(slope) >= 0.001:
            direction = TrendDirection.VOLATILE
        elif abs(slope) < 0.001:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
        
        return TrendComponent(
            direction=direction,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
        )
    
    def _detect_seasonality(
        self,
        detrended: list[float],
    ) -> SeasonalComponent:
        """Detect seasonality in detrended data."""
        n = len(detrended)
        
        if n < 14:  # Need at least 2 weeks
            return SeasonalComponent(
                seasonality_type=SeasonalityType.NONE,
                period_days=0,
                strength=0.0,
            )
        
        # Try weekly pattern (7 days)
        weekly_pattern = self._extract_pattern(detrended, 7)
        weekly_strength = self._pattern_strength(weekly_pattern, detrended, 7)
        
        # Try monthly pattern (~30 days)
        monthly_strength = 0.0
        monthly_pattern: list[float] = []
        
        if n >= 60:
            monthly_pattern = self._extract_pattern(detrended, 30)
            monthly_strength = self._pattern_strength(monthly_pattern, detrended, 30)
        
        # Choose strongest
        if weekly_strength > 0.3 and weekly_strength >= monthly_strength:
            return SeasonalComponent(
                seasonality_type=SeasonalityType.WEEKLY,
                period_days=7,
                strength=weekly_strength,
                pattern=weekly_pattern,
            )
        elif monthly_strength > 0.3:
            return SeasonalComponent(
                seasonality_type=SeasonalityType.MONTHLY,
                period_days=30,
                strength=monthly_strength,
                pattern=monthly_pattern,
            )
        
        return SeasonalComponent(
            seasonality_type=SeasonalityType.NONE,
            period_days=0,
            strength=0.0,
        )
    
    def _extract_pattern(self, values: list[float], period: int) -> list[float]:
        """Extract repeating pattern from values."""
        if period <= 0:
            return []
        
        # Average values at each position in the period
        pattern = [0.0] * period
        counts = [0] * period
        
        for i, v in enumerate(values):
            pos = i % period
            pattern[pos] += v
            counts[pos] += 1
        
        for i in range(period):
            if counts[i] > 0:
                pattern[i] /= counts[i]
        
        # Normalize to zero mean
        mean = sum(pattern) / len(pattern) if pattern else 0
        return [p - mean for p in pattern]
    
    def _pattern_strength(
        self,
        pattern: list[float],
        values: list[float],
        period: int,
    ) -> float:
        """Calculate how well pattern explains variance."""
        if not pattern or period <= 0:
            return 0.0
        
        # Calculate variance explained
        total_variance = statistics.variance(values) if len(values) > 1 else 0
        
        if total_variance == 0:
            return 0.0
        
        pattern_variance = statistics.variance(pattern) if len(pattern) > 1 else 0
        
        return min(1.0, pattern_variance / total_variance)
    
    def decompose(
        self,
        data: list[TimeSeriesPoint],
    ) -> tuple[TrendComponent, SeasonalComponent, list[float]]:
        """
        Decompose time series into components.
        
        Returns:
            Tuple of (trend, seasonality, residuals)
        """
        if len(data) < self._min_points:
            # Return defaults for insufficient data
            return (
                TrendComponent(
                    direction=TrendDirection.STABLE,
                    slope=0.0,
                    intercept=data[0].value if data else 0.0,
                ),
                SeasonalComponent(
                    seasonality_type=SeasonalityType.NONE,
                    period_days=0,
                    strength=0.0,
                ),
                [],
            )
        
        # Sort by timestamp
        sorted_data = sorted(data)
        values = [d.value for d in sorted_data]
        
        # 1. Calculate trend using moving average
        ma_values = self._calculate_moving_average(values, 7)
        trend = self._fit_linear_trend(ma_values)
        
        # 2. Remove trend to get detrended
        detrended = [
            values[i] - trend.predict(i)
            for i in range(len(values))
        ]
        
        # 3. Detect seasonality
        seasonality = self._detect_seasonality(detrended)
        
        # 4. Calculate residuals
        residuals = []
        for i, v in enumerate(values):
            trend_val = trend.predict(i)
            seasonal_val = seasonality.get_seasonal_factor(i) - 1
            residuals.append(v - trend_val - seasonal_val)
        
        return trend, seasonality, residuals


# =============================================================================
# Demand Forecaster
# =============================================================================

class DemandForecaster:
    """
    Forecast demand using exponential smoothing and trend analysis.
    """
    
    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        """
        Initialize forecaster.
        
        Args:
            alpha: Level smoothing parameter (0-1)
            beta: Trend smoothing parameter (0-1)
        """
        self._alpha = alpha
        self._beta = beta
    
    def _double_exponential_smoothing(
        self,
        values: list[float],
        forecast_periods: int,
    ) -> list[float]:
        """Apply double exponential smoothing (Holt's method)."""
        if not values:
            return [0.0] * forecast_periods
        
        n = len(values)
        
        # Initialize
        level = values[0]
        trend = (values[1] - values[0]) if n > 1 else 0.0
        
        # Fit to historical data
        for i in range(1, n):
            new_level = self._alpha * values[i] + (1 - self._alpha) * (level + trend)
            new_trend = self._beta * (new_level - level) + (1 - self._beta) * trend
            level = new_level
            trend = new_trend
        
        # Forecast
        forecasts = []
        for h in range(1, forecast_periods + 1):
            forecasts.append(level + h * trend)
        
        return forecasts
    
    def forecast(
        self,
        historical_data: list[tuple[datetime, float]],
        horizon_days: int = DEFAULT_FORECAST_DAYS,
    ) -> DemandForecast:
        """Generate demand forecast."""
        if not historical_data:
            now = datetime.now(timezone.utc)
            return DemandForecast(
                forecast_id=str(uuid.uuid4()),
                start_date=now,
                end_date=now + timedelta(days=horizon_days),
                total_demand_units=0.0,
                peak_demand_units=0.0,
                peak_date=now,
            )
        
        # Sort by date
        sorted_data = sorted(historical_data, key=lambda x: x[0])
        values = [v for _, v in sorted_data]
        last_date = sorted_data[-1][0]
        
        # Apply smoothing
        forecasted_values = self._double_exponential_smoothing(values, horizon_days)
        
        # Ensure non-negative
        forecasted_values = [max(0, v) for v in forecasted_values]
        
        # Build daily forecasts
        daily_forecasts = []
        for i, val in enumerate(forecasted_values):
            date = last_date + timedelta(days=i + 1)
            daily_forecasts.append((date, val))
        
        # Find peak
        peak_val = max(forecasted_values)
        peak_idx = forecasted_values.index(peak_val)
        peak_date = last_date + timedelta(days=peak_idx + 1)
        
        return DemandForecast(
            forecast_id=str(uuid.uuid4()),
            start_date=last_date + timedelta(days=1),
            end_date=last_date + timedelta(days=horizon_days),
            total_demand_units=sum(forecasted_values),
            peak_demand_units=peak_val,
            peak_date=peak_date,
            daily_forecasts=daily_forecasts,
        )


# =============================================================================
# Resource Forecaster
# =============================================================================

class ResourceForecaster:
    """
    Forecast resource utilization combining trend, seasonality, and demand.
    """
    
    def __init__(self):
        """Initialize forecaster."""
        self._decomposer = TimeSeriesDecomposer()
        self._demand_forecaster = DemandForecaster()
    
    def _calculate_confidence_interval(
        self,
        value: float,
        residuals: list[float],
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Calculate confidence interval."""
        if not residuals or len(residuals) < 3:
            margin = abs(value) * 0.1
            return max(0, value - margin), min(1, value + margin)
        
        std_dev = statistics.stdev(residuals)
        
        # Z-score for confidence level
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }
        z = z_scores.get(confidence, 1.96)
        
        margin = z * std_dev
        
        # For utilization, clamp to 0-1
        return max(0.0, value - margin), min(1.0, value + margin)
    
    def forecast(
        self,
        historical_data: list[ResourceData],
        horizon: ForecastHorizon = ForecastHorizon.MEDIUM_TERM,
    ) -> ResourceForecast:
        """Generate resource utilization forecast."""
        if not historical_data:
            return ResourceForecast(
                forecast_id=str(uuid.uuid4()),
                resource_id="unknown",
                resource_type=ResourceType.MACHINE,
                horizon=horizon,
                forecasts=[],
                trend=TrendComponent(
                    direction=TrendDirection.STABLE,
                    slope=0.0,
                    intercept=0.5,
                ),
                seasonality=SeasonalComponent(
                    seasonality_type=SeasonalityType.NONE,
                    period_days=0,
                    strength=0.0,
                ),
            )
        
        # Get resource info
        resource_id = historical_data[0].resource_id
        resource_type = historical_data[0].resource_type
        
        # Convert to time series
        ts_data = [
            TimeSeriesPoint(timestamp=d.timestamp, value=d.utilization)
            for d in historical_data
        ]
        
        # Decompose
        trend, seasonality, residuals = self._decomposer.decompose(ts_data)
        
        # Determine forecast days
        horizon_days = {
            ForecastHorizon.SHORT_TERM: 7,
            ForecastHorizon.MEDIUM_TERM: 28,
            ForecastHorizon.LONG_TERM: 90,
        }
        days = horizon_days.get(horizon, 28)
        
        # Get last timestamp
        sorted_data = sorted(historical_data, key=lambda x: x.timestamp)
        last_ts = sorted_data[-1].timestamp
        n_historical = len(sorted_data)
        
        # Generate forecasts
        forecasts = []
        for i in range(1, days + 1):
            forecast_date = last_ts + timedelta(days=i)
            
            # Predict using trend
            trend_value = trend.predict(n_historical + i)
            
            # Apply seasonality
            seasonal_factor = seasonality.get_seasonal_factor(n_historical + i)
            predicted = trend_value * seasonal_factor
            
            # Clamp to valid range
            predicted = max(0.0, min(1.0, predicted))
            
            # Confidence interval
            lower, upper = self._calculate_confidence_interval(predicted, residuals)
            
            forecasts.append(ForecastPoint(
                timestamp=forecast_date,
                predicted_value=predicted,
                lower_bound=lower,
                upper_bound=upper,
            ))
        
        return ResourceForecast(
            forecast_id=str(uuid.uuid4()),
            resource_id=resource_id,
            resource_type=resource_type,
            horizon=horizon,
            forecasts=forecasts,
            trend=trend,
            seasonality=seasonality,
        )


# =============================================================================
# Capacity Planner
# =============================================================================

class CapacityPlanner:
    """
    Plan capacity based on forecasts and business rules.
    """
    
    def __init__(
        self,
        target_utilization: float = 0.75,
        buffer_percentage: float = 0.15,
    ):
        """
        Initialize planner.
        
        Args:
            target_utilization: Target utilization rate
            buffer_percentage: Safety buffer for capacity
        """
        self._target_utilization = target_utilization
        self._buffer = buffer_percentage
    
    def _determine_risk_level(
        self,
        forecast: ResourceForecast,
        capacity_change: float,
    ) -> str:
        """Determine risk level of capacity change."""
        if abs(capacity_change) < 0.1:
            return "low"
        elif abs(capacity_change) < 0.3:
            return "medium"
        else:
            return "high"
    
    def plan(
        self,
        forecast: ResourceForecast,
        current_capacity: float,
        cost_per_unit: float = 0.0,
    ) -> CapacityPlan:
        """Generate capacity plan based on forecast."""
        if not forecast.forecasts:
            return CapacityPlan(
                plan_id=str(uuid.uuid4()),
                resource_id=forecast.resource_id,
                resource_type=forecast.resource_type,
                current_capacity=current_capacity,
                recommended_capacity=current_capacity,
                capacity_change=0.0,
                justification="Insufficient forecast data",
            )
        
        # Get peak utilization
        _, peak_util = forecast.peak_utilization
        avg_util = forecast.average_predicted_utilization
        
        # Calculate required capacity
        # If at 90% util with 100 capacity, need ~100/0.75=133 for 75% target
        effective_demand = avg_util * current_capacity
        required_for_target = effective_demand / self._target_utilization
        
        # Add buffer
        recommended = required_for_target * (1 + self._buffer)
        
        # Consider peak
        peak_demand = peak_util * current_capacity
        peak_capacity = peak_demand / 0.9  # Allow 90% at peak
        
        recommended = max(recommended, peak_capacity)
        
        # Round to reasonable increment
        recommended = round(recommended, -1)  # Round to nearest 10
        
        capacity_change = (recommended - current_capacity) / current_capacity if current_capacity > 0 else 0
        
        # Determine justification
        if capacity_change > 0.1:
            justification = f"Forecast indicates {peak_util:.0%} peak utilization. Increase capacity to maintain {self._target_utilization:.0%} target."
        elif capacity_change < -0.1:
            justification = f"Forecast indicates {avg_util:.0%} average utilization. Reduce capacity to optimize costs."
        else:
            justification = f"Current capacity appropriate for forecasted {avg_util:.0%} utilization."
        
        risk = self._determine_risk_level(forecast, capacity_change)
        cost_impact = (recommended - current_capacity) * cost_per_unit
        
        return CapacityPlan(
            plan_id=str(uuid.uuid4()),
            resource_id=forecast.resource_id,
            resource_type=forecast.resource_type,
            current_capacity=current_capacity,
            recommended_capacity=recommended,
            capacity_change=capacity_change,
            justification=justification,
            cost_impact=cost_impact,
            implementation_days=14 if abs(capacity_change) > 0.2 else 7,
            risk_level=risk,
        )


# =============================================================================
# What-If Simulator
# =============================================================================

class WhatIfSimulator:
    """
    Simulate what-if scenarios for capacity planning.
    """
    
    def __init__(self, forecaster: ResourceForecaster):
        """Initialize with forecaster."""
        self._forecaster = forecaster
    
    def simulate_demand_change(
        self,
        forecast: ResourceForecast,
        demand_multiplier: float,
    ) -> ResourceForecast:
        """Simulate effect of demand change."""
        adjusted_forecasts = []
        
        for f in forecast.forecasts:
            new_value = min(1.0, f.predicted_value * demand_multiplier)
            new_lower = min(1.0, f.lower_bound * demand_multiplier)
            new_upper = min(1.0, f.upper_bound * demand_multiplier)
            
            adjusted_forecasts.append(ForecastPoint(
                timestamp=f.timestamp,
                predicted_value=new_value,
                lower_bound=new_lower,
                upper_bound=new_upper,
                confidence=f.confidence,
            ))
        
        # Adjust trend
        adjusted_trend = TrendComponent(
            direction=forecast.trend.direction,
            slope=forecast.trend.slope * demand_multiplier,
            intercept=forecast.trend.intercept * demand_multiplier,
            r_squared=forecast.trend.r_squared,
        )
        
        return ResourceForecast(
            forecast_id=str(uuid.uuid4()),
            resource_id=forecast.resource_id,
            resource_type=forecast.resource_type,
            horizon=forecast.horizon,
            forecasts=adjusted_forecasts,
            trend=adjusted_trend,
            seasonality=forecast.seasonality,
        )
    
    def simulate_capacity_change(
        self,
        forecast: ResourceForecast,
        capacity_multiplier: float,
    ) -> ResourceForecast:
        """Simulate effect of capacity change (utilization goes down as capacity goes up)."""
        adjusted_forecasts = []
        
        for f in forecast.forecasts:
            new_value = f.predicted_value / capacity_multiplier if capacity_multiplier > 0 else 1.0
            new_value = min(1.0, new_value)
            
            new_lower = f.lower_bound / capacity_multiplier if capacity_multiplier > 0 else 0.0
            new_upper = f.upper_bound / capacity_multiplier if capacity_multiplier > 0 else 1.0
            
            adjusted_forecasts.append(ForecastPoint(
                timestamp=f.timestamp,
                predicted_value=new_value,
                lower_bound=min(1.0, max(0.0, new_lower)),
                upper_bound=min(1.0, max(0.0, new_upper)),
                confidence=f.confidence,
            ))
        
        return ResourceForecast(
            forecast_id=str(uuid.uuid4()),
            resource_id=forecast.resource_id,
            resource_type=forecast.resource_type,
            horizon=forecast.horizon,
            forecasts=adjusted_forecasts,
            trend=forecast.trend,
            seasonality=forecast.seasonality,
        )
    
    def compare_scenarios(
        self,
        baseline: ResourceForecast,
        scenarios: list[tuple[str, ResourceForecast]],
    ) -> dict[str, Any]:
        """Compare multiple scenarios."""
        scenario_results: dict[str, dict[str, Any]] = {}
        results: dict[str, Any] = {
            "baseline": {
                "average_utilization": baseline.average_predicted_utilization,
                "peak_utilization": baseline.peak_utilization[1],
                "status": baseline.get_capacity_status().value,
            },
            "scenarios": scenario_results,
        }
        
        for name, scenario in scenarios:
            scenario_results[name] = {
                "average_utilization": scenario.average_predicted_utilization,
                "peak_utilization": scenario.peak_utilization[1],
                "status": scenario.get_capacity_status().value,
                "delta_from_baseline": (
                    scenario.average_predicted_utilization -
                    baseline.average_predicted_utilization
                ),
            }
        
        return results


# =============================================================================
# Predictive Utility Engine
# =============================================================================

class PredictiveUtilityEngine:
    """
    Main engine for predictive utility and resource forecasting.
    """
    
    def __init__(
        self,
        target_utilization: float = 0.75,
        buffer_percentage: float = 0.15,
        max_history_per_resource: int = 10_000,
    ):
        """Initialize engine."""
        self._forecaster = ResourceForecaster()
        self._demand_forecaster = DemandForecaster()
        self._planner = CapacityPlanner(target_utilization, buffer_percentage)
        self._simulator = WhatIfSimulator(self._forecaster)
        self._max_history = max_history_per_resource
        
        # Store historical data (bounded per resource)
        self._resource_history: dict[str, list[ResourceData]] = {}
        self._forecasts: dict[str, ResourceForecast] = {}
    
    def add_data(self, data: ResourceData):
        """Add historical data point (evicts oldest when limit reached)."""
        if data.resource_id not in self._resource_history:
            self._resource_history[data.resource_id] = []
        
        hist = self._resource_history[data.resource_id]
        hist.append(data)
        # Evict oldest entries when exceeding limit
        if len(hist) > self._max_history:
            self._resource_history[data.resource_id] = hist[-self._max_history:]
    
    def add_data_batch(self, data: list[ResourceData]):
        """Add multiple data points."""
        for d in data:
            self.add_data(d)
    
    def get_resource_ids(self) -> list[str]:
        """Get list of tracked resource IDs."""
        return list(self._resource_history.keys())
    
    def forecast_resource(
        self,
        resource_id: str,
        horizon: ForecastHorizon = ForecastHorizon.MEDIUM_TERM,
    ) -> ResourceForecast:
        """Generate forecast for a resource."""
        history = self._resource_history.get(resource_id, [])
        
        forecast = self._forecaster.forecast(history, horizon)
        self._forecasts[resource_id] = forecast
        
        return forecast
    
    def forecast_all_resources(
        self,
        horizon: ForecastHorizon = ForecastHorizon.MEDIUM_TERM,
    ) -> dict[str, ResourceForecast]:
        """Forecast all tracked resources."""
        forecasts = {}
        
        for resource_id in self._resource_history:
            forecasts[resource_id] = self.forecast_resource(resource_id, horizon)
        
        return forecasts
    
    def plan_capacity(
        self,
        resource_id: str,
        current_capacity: float,
        cost_per_unit: float = 0.0,
    ) -> CapacityPlan:
        """Generate capacity plan for resource."""
        # Ensure we have a forecast
        if resource_id not in self._forecasts:
            self.forecast_resource(resource_id)
        
        forecast = self._forecasts.get(resource_id)
        
        if not forecast:
            # Create dummy forecast
            forecast = ResourceForecast(
                forecast_id=str(uuid.uuid4()),
                resource_id=resource_id,
                resource_type=ResourceType.MACHINE,
                horizon=ForecastHorizon.MEDIUM_TERM,
                forecasts=[],
                trend=TrendComponent(
                    direction=TrendDirection.STABLE,
                    slope=0.0,
                    intercept=0.5,
                ),
                seasonality=SeasonalComponent(
                    seasonality_type=SeasonalityType.NONE,
                    period_days=0,
                    strength=0.0,
                ),
            )
        
        return self._planner.plan(forecast, current_capacity, cost_per_unit)
    
    def simulate_demand_change(
        self,
        resource_id: str,
        demand_change_percent: float,
    ) -> ResourceForecast:
        """Simulate demand change for resource."""
        if resource_id not in self._forecasts:
            self.forecast_resource(resource_id)
        
        forecast = self._forecasts.get(resource_id)
        if not forecast:
            return ResourceForecast(
                forecast_id=str(uuid.uuid4()),
                resource_id=resource_id,
                resource_type=ResourceType.MACHINE,
                horizon=ForecastHorizon.MEDIUM_TERM,
                forecasts=[],
                trend=TrendComponent(
                    direction=TrendDirection.STABLE,
                    slope=0.0,
                    intercept=0.5,
                ),
                seasonality=SeasonalComponent(
                    seasonality_type=SeasonalityType.NONE,
                    period_days=0,
                    strength=0.0,
                ),
            )
        
        multiplier = 1 + (demand_change_percent / 100)
        return self._simulator.simulate_demand_change(forecast, multiplier)
    
    def simulate_capacity_change(
        self,
        resource_id: str,
        capacity_change_percent: float,
    ) -> ResourceForecast:
        """Simulate capacity change for resource."""
        if resource_id not in self._forecasts:
            self.forecast_resource(resource_id)
        
        forecast = self._forecasts.get(resource_id)
        if not forecast:
            return ResourceForecast(
                forecast_id=str(uuid.uuid4()),
                resource_id=resource_id,
                resource_type=ResourceType.MACHINE,
                horizon=ForecastHorizon.MEDIUM_TERM,
                forecasts=[],
                trend=TrendComponent(
                    direction=TrendDirection.STABLE,
                    slope=0.0,
                    intercept=0.5,
                ),
                seasonality=SeasonalComponent(
                    seasonality_type=SeasonalityType.NONE,
                    period_days=0,
                    strength=0.0,
                ),
            )
        
        multiplier = 1 + (capacity_change_percent / 100)
        return self._simulator.simulate_capacity_change(forecast, multiplier)
    
    def get_utilization_summary(self) -> dict[str, Any]:
        """Get summary of all resource utilization."""
        resources: dict[str, dict[str, Any]] = {}
        summary: dict[str, Any] = {
            "total_resources": len(self._resource_history),
            "resources": resources,
            "overall_status": {},
        }
        
        status_counts = {s.value: 0 for s in CapacityStatus}
        
        for resource_id in self._resource_history:
            if resource_id not in self._forecasts:
                self.forecast_resource(resource_id)
            
            forecast = self._forecasts.get(resource_id)
            
            if forecast:
                status = forecast.get_capacity_status()
                status_counts[status.value] += 1
                
                resources[resource_id] = {
                    "type": forecast.resource_type.value,
                    "average_utilization": forecast.average_predicted_utilization,
                    "peak_utilization": forecast.peak_utilization[1],
                    "trend": forecast.trend.direction.value,
                    "status": status.value,
                }
        
        summary["overall_status"] = status_counts
        
        return summary
    
    def forecast_demand(
        self,
        historical_demand: list[tuple[datetime, float]],
        horizon_days: int = DEFAULT_FORECAST_DAYS,
    ) -> DemandForecast:
        """Forecast aggregate demand."""
        return self._demand_forecaster.forecast(historical_demand, horizon_days)


# =============================================================================
# Factory Function
# =============================================================================

def create_utility_forecaster(
    target_utilization: float = 0.75,
    buffer_percentage: float = 0.15,
) -> PredictiveUtilityEngine:
    """Create and initialize utility forecaster."""
    return PredictiveUtilityEngine(
        target_utilization=target_utilization,
        buffer_percentage=buffer_percentage,
    )
