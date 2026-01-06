"""
KPI Definitions & Metrics API.

Provides a comprehensive system for defining, calculating, and tracking
Key Performance Indicators (KPIs) across all business domains.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class KPICategory(str, Enum):
    """Categories of KPIs."""
    
    # Quote-to-Cash
    SALES = "sales"
    QUOTING = "quoting"
    RFQ = "rfq"
    
    # Production
    PRODUCTION = "production"
    OEE = "oee"
    
    # Quality
    QUALITY = "quality"
    INSPECTION = "inspection"
    
    # Training & People
    TRAINING = "training"
    SKILLS = "skills"
    
    # Operations
    ANDON = "andon"
    PROBLEM_SOLVING = "problem_solving"
    
    # LSW & Discipline
    LSW = "lsw"
    CADENCE = "cadence"
    
    # Custom
    CUSTOM = "custom"


class KPIUnit(str, Enum):
    """Units for KPI values."""
    
    # Ratios and percentages
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    
    # Time
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    
    # Counts
    COUNT = "count"
    UNITS = "units"
    PPM = "ppm"  # Parts per million
    
    # Currency
    CURRENCY = "currency"
    
    # Rate
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    PER_WEEK = "per_week"
    PER_MONTH = "per_month"
    
    # Other
    INDEX = "index"
    SCORE = "score"


class KPIDirection(str, Enum):
    """Direction indicating what is 'good' for this KPI."""
    
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    TARGET_IS_BEST = "target_is_best"  # Being close to target is best


class KPIStatus(str, Enum):
    """Status of a KPI relative to its targets."""
    
    ON_TARGET = "on_target"
    WITHIN_TOLERANCE = "within_tolerance"
    OFF_TARGET = "off_target"
    CRITICAL = "critical"
    NO_DATA = "no_data"


class AggregationType(str, Enum):
    """How to aggregate KPI values over time."""
    
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LATEST = "latest"
    WEIGHTED_AVERAGE = "weighted_average"


class TrendDirection(str, Enum):
    """Direction of a trend."""
    
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"


# --------------------------------------------------------------------------
# Data Classes
# --------------------------------------------------------------------------

@dataclass
class KPIThreshold:
    """Threshold configuration for a KPI."""
    
    # Target value
    target: float
    
    # Warning threshold (percentage from target)
    warning_threshold: float = 10.0
    
    # Critical threshold (percentage from target)
    critical_threshold: float = 20.0
    
    # Min/Max bounds
    min_value: float | None = None
    max_value: float | None = None


@dataclass
class KPIDataSource:
    """Definition of data source for a KPI."""
    
    # Entity type (e.g., "rfq", "quote", "work_order")
    entity_type: str
    
    # Field(s) used for calculation
    fields: list[str] = field(default_factory=list)
    
    # Filter conditions (as dict for flexibility)
    filters: dict[str, Any] = field(default_factory=dict)
    
    # How to aggregate the data
    aggregation: AggregationType = AggregationType.AVERAGE
    
    # Optional timestamp field for time-based filtering
    timestamp_field: str = "created_at"
    
    # Optional grouping fields
    group_by: list[str] = field(default_factory=list)


@dataclass
class KPIDefinition:
    """Complete KPI definition."""
    
    id: str
    name: str
    description: str
    category: KPICategory
    unit: KPIUnit
    direction: KPIDirection
    
    # Data source configuration
    data_source: KPIDataSource | None = None
    
    # Calculation formula (for derived/composite KPIs)
    formula: str = ""
    component_kpis: list[str] = field(default_factory=list)
    
    # Target configuration
    threshold: KPIThreshold | None = None
    
    # Display configuration
    decimal_places: int = 2
    display_format: str = ""  # e.g., "{value}%", "${value}"
    
    # Metadata
    owner_role: str = ""
    frequency: str = "daily"  # How often this KPI should be calculated
    is_active: bool = True
    tags: list[str] = field(default_factory=list)
    
    # Custom calculation function name (for complex KPIs)
    custom_calculator: str = ""


@dataclass
class KPIValue:
    """A single KPI value at a point in time."""
    
    id: str
    kpi_id: str
    value: float
    timestamp: datetime
    
    # Context
    period_start: date | None = None
    period_end: date | None = None
    
    # Status
    status: KPIStatus = KPIStatus.NO_DATA
    
    # Breakdown by dimension (e.g., {"customer_segment": "automotive"})
    dimensions: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    sample_size: int = 0
    confidence: float = 1.0


@dataclass
class KPITrend:
    """Trend analysis for a KPI."""
    
    kpi_id: str
    direction: TrendDirection
    
    # Values
    current_value: float
    previous_value: float
    change_absolute: float
    change_percentage: float
    
    # Period
    current_period: tuple[date, date] | None = None
    previous_period: tuple[date, date] | None = None
    
    # Statistical info
    moving_average: float | None = None
    standard_deviation: float | None = None
    
    # Forecast
    forecast_next_period: float | None = None


@dataclass
class KPIDashboard:
    """Collection of KPIs for a dashboard view."""
    
    id: str
    name: str
    description: str
    
    # KPIs included
    kpi_ids: list[str] = field(default_factory=list)
    
    # Layout configuration (grid positions)
    layout: dict[str, dict[str, Any]] = field(default_factory=dict)
    
    # Filters
    default_time_range: str = "last_30_days"
    dimension_filters: dict[str, list[str]] = field(default_factory=dict)
    
    # Metadata
    owner_id: str = ""
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class KPICalculationResult:
    """Result of a KPI calculation."""
    
    kpi_id: str
    success: bool
    value: KPIValue | None = None
    error: str = ""
    calculation_time_ms: float = 0.0


# --------------------------------------------------------------------------
# KPI Service
# --------------------------------------------------------------------------

class KPIService:
    """
    Service for managing KPI definitions and calculations.
    
    Provides:
    - KPI definition CRUD
    - Value calculation and storage
    - Trend analysis
    - Dashboard management
    """
    
    def __init__(self) -> None:
        """Initialize the KPI service."""
        self._definitions: dict[str, KPIDefinition] = {}
        self._values: dict[str, list[KPIValue]] = {}  # kpi_id -> values
        self._dashboards: dict[str, KPIDashboard] = {}
        
        # Register default Phase 1 KPIs
        self._register_default_kpis()
    
    # --------------------------------------------------------------------------
    # KPI Definition Management
    # --------------------------------------------------------------------------
    
    def create_definition(self, definition: KPIDefinition) -> KPIDefinition:
        """Create a new KPI definition."""
        if not definition.id:
            definition.id = str(uuid4())
        
        self._definitions[definition.id] = definition
        self._values[definition.id] = []
        
        return definition
    
    def get_definition(self, kpi_id: str) -> KPIDefinition | None:
        """Get a KPI definition by ID."""
        return self._definitions.get(kpi_id)
    
    def update_definition(
        self,
        kpi_id: str,
        updates: dict[str, Any],
    ) -> KPIDefinition | None:
        """Update a KPI definition."""
        definition = self._definitions.get(kpi_id)
        if not definition:
            return None
        
        for key, value in updates.items():
            if hasattr(definition, key):
                setattr(definition, key, value)
        
        return definition
    
    def delete_definition(self, kpi_id: str) -> bool:
        """Delete a KPI definition and its values."""
        if kpi_id not in self._definitions:
            return False
        
        del self._definitions[kpi_id]
        if kpi_id in self._values:
            del self._values[kpi_id]
        
        return True
    
    def list_definitions(
        self,
        category: KPICategory | None = None,
        active_only: bool = True,
        tags: list[str] | None = None,
    ) -> list[KPIDefinition]:
        """List KPI definitions with optional filters."""
        definitions = list(self._definitions.values())
        
        if category:
            definitions = [d for d in definitions if d.category == category]
        
        if active_only:
            definitions = [d for d in definitions if d.is_active]
        
        if tags:
            definitions = [
                d for d in definitions
                if any(t in d.tags for t in tags)
            ]
        
        return definitions
    
    # --------------------------------------------------------------------------
    # Value Management
    # --------------------------------------------------------------------------
    
    def record_value(self, value: KPIValue) -> KPIValue:
        """Record a KPI value."""
        if value.kpi_id not in self._values:
            self._values[value.kpi_id] = []
        
        # Determine status based on threshold
        definition = self._definitions.get(value.kpi_id)
        if definition and definition.threshold:
            value.status = self._calculate_status(value.value, definition)
        
        self._values[value.kpi_id].append(value)
        return value
    
    def get_latest_value(
        self,
        kpi_id: str,
        dimensions: dict[str, str] | None = None,
    ) -> KPIValue | None:
        """Get the most recent value for a KPI."""
        values = self._values.get(kpi_id, [])
        
        if dimensions:
            values = [
                v for v in values
                if all(v.dimensions.get(k) == val for k, val in dimensions.items())
            ]
        
        if not values:
            return None
        
        return max(values, key=lambda v: v.timestamp)
    
    def get_values(
        self,
        kpi_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        dimensions: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[KPIValue]:
        """Get KPI values with optional filters."""
        values = self._values.get(kpi_id, [])
        
        if start_date:
            values = [v for v in values if v.timestamp.date() >= start_date]
        
        if end_date:
            values = [v for v in values if v.timestamp.date() <= end_date]
        
        if dimensions:
            values = [
                v for v in values
                if all(v.dimensions.get(k) == val for k, val in dimensions.items())
            ]
        
        # Sort by timestamp descending
        values = sorted(values, key=lambda v: v.timestamp, reverse=True)
        
        if limit:
            values = values[:limit]
        
        return values
    
    def _calculate_status(
        self,
        value: float,
        definition: KPIDefinition,
    ) -> KPIStatus:
        """Calculate KPI status based on thresholds."""
        threshold = definition.threshold
        if not threshold:
            return KPIStatus.NO_DATA
        
        target = threshold.target
        warning_pct = threshold.warning_threshold / 100
        critical_pct = threshold.critical_threshold / 100
        
        if definition.direction == KPIDirection.HIGHER_IS_BETTER:
            if value >= target:
                return KPIStatus.ON_TARGET
            elif value >= target * (1 - warning_pct):
                return KPIStatus.WITHIN_TOLERANCE
            elif value >= target * (1 - critical_pct):
                return KPIStatus.OFF_TARGET
            else:
                return KPIStatus.CRITICAL
        
        elif definition.direction == KPIDirection.LOWER_IS_BETTER:
            if value <= target:
                return KPIStatus.ON_TARGET
            elif value <= target * (1 + warning_pct):
                return KPIStatus.WITHIN_TOLERANCE
            elif value <= target * (1 + critical_pct):
                return KPIStatus.OFF_TARGET
            else:
                return KPIStatus.CRITICAL
        
        else:  # TARGET_IS_BEST
            deviation = abs(value - target) / target if target != 0 else abs(value)
            if deviation <= warning_pct:
                return KPIStatus.ON_TARGET
            elif deviation <= critical_pct:
                return KPIStatus.WITHIN_TOLERANCE
            elif deviation <= critical_pct * 1.5:
                return KPIStatus.OFF_TARGET
            else:
                return KPIStatus.CRITICAL
    
    # --------------------------------------------------------------------------
    # Calculations
    # --------------------------------------------------------------------------
    
    def calculate_kpi(
        self,
        kpi_id: str,
        start_date: date,
        end_date: date,
        data_provider: Callable[[KPIDataSource, date, date], list[dict]] | None = None,
        dimensions: dict[str, str] | None = None,
    ) -> KPICalculationResult:
        """
        Calculate a KPI value for a given period.
        
        Args:
            kpi_id: The KPI to calculate
            start_date: Start of the calculation period
            end_date: End of the calculation period
            data_provider: Optional function to fetch data for calculation
            dimensions: Optional dimension filters
        
        Returns:
            Calculation result with value or error
        """
        start_time = datetime.now()
        
        definition = self._definitions.get(kpi_id)
        if not definition:
            return KPICalculationResult(
                kpi_id=kpi_id,
                success=False,
                error=f"KPI {kpi_id} not found",
            )
        
        try:
            # Use custom calculator if specified
            if definition.custom_calculator:
                value = self._run_custom_calculator(
                    definition,
                    start_date,
                    end_date,
                    dimensions,
                )
            # Use formula for composite KPIs
            elif definition.formula and definition.component_kpis:
                value = self._calculate_composite(
                    definition,
                    start_date,
                    end_date,
                    dimensions,
                )
            # Use data source for direct calculation
            elif definition.data_source and data_provider:
                value = self._calculate_from_data(
                    definition,
                    start_date,
                    end_date,
                    data_provider,
                    dimensions,
                )
            else:
                # No calculation method available, return simulated value
                value = self._simulate_value(definition)
            
            kpi_value = KPIValue(
                id=str(uuid4()),
                kpi_id=kpi_id,
                value=value,
                timestamp=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                dimensions=dimensions or {},
                status=self._calculate_status(value, definition),
            )
            
            # Record the value
            self.record_value(kpi_value)
            
            calc_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return KPICalculationResult(
                kpi_id=kpi_id,
                success=True,
                value=kpi_value,
                calculation_time_ms=calc_time,
            )
        
        except Exception as e:
            calc_time = (datetime.now() - start_time).total_seconds() * 1000
            return KPICalculationResult(
                kpi_id=kpi_id,
                success=False,
                error=str(e),
                calculation_time_ms=calc_time,
            )
    
    def _calculate_composite(
        self,
        definition: KPIDefinition,
        start_date: date,
        end_date: date,
        dimensions: dict[str, str] | None,
    ) -> float:
        """Calculate a composite KPI from its components."""
        # Get component values
        component_values: dict[str, float] = {}
        for comp_id in definition.component_kpis:
            value = self.get_latest_value(comp_id, dimensions)
            if value:
                component_values[comp_id] = value.value
            else:
                # Try to calculate it
                result = self.calculate_kpi(comp_id, start_date, end_date, None, dimensions)
                if result.success and result.value:
                    component_values[comp_id] = result.value.value
                else:
                    component_values[comp_id] = 0.0
        
        # Evaluate formula
        # Simple formula evaluation (production would use a proper expression evaluator)
        formula = definition.formula
        for comp_id, val in component_values.items():
            formula = formula.replace(f"{{{comp_id}}}", str(val))
        
        try:
            return eval(formula)  # noqa: S307 - In production, use safe eval
        except Exception:
            return 0.0
    
    def _calculate_from_data(
        self,
        definition: KPIDefinition,
        start_date: date,
        end_date: date,
        data_provider: Callable[[KPIDataSource, date, date], list[dict]],
        dimensions: dict[str, str] | None,
    ) -> float:
        """Calculate KPI from raw data."""
        data_source = definition.data_source
        if not data_source:
            return 0.0
        
        # Fetch data
        data = data_provider(data_source, start_date, end_date)
        
        # Apply dimension filters
        if dimensions:
            data = [
                d for d in data
                if all(d.get(k) == v for k, v in dimensions.items())
            ]
        
        if not data:
            return 0.0
        
        # Extract field values
        values = []
        for record in data:
            for field_name in data_source.fields:
                if field_name in record and record[field_name] is not None:
                    values.append(float(record[field_name]))
        
        if not values:
            return 0.0
        
        # Aggregate
        agg = data_source.aggregation
        if agg == AggregationType.SUM:
            return sum(values)
        elif agg == AggregationType.AVERAGE:
            return sum(values) / len(values)
        elif agg == AggregationType.MIN:
            return min(values)
        elif agg == AggregationType.MAX:
            return max(values)
        elif agg == AggregationType.COUNT:
            return float(len(values))
        elif agg == AggregationType.LATEST:
            return values[-1] if values else 0.0
        else:
            return sum(values) / len(values)
    
    def _run_custom_calculator(
        self,
        definition: KPIDefinition,
        start_date: date,
        end_date: date,
        dimensions: dict[str, str] | None,
    ) -> float:
        """Run a custom calculator for complex KPIs."""
        calc_name = definition.custom_calculator
        
        # Map of custom calculators
        calculators = {
            "oee_calculator": self._calculate_oee,
            "quote_cycle_time": self._calculate_quote_cycle_time,
            "training_compliance": self._calculate_training_compliance,
        }
        
        calculator = calculators.get(calc_name)
        if calculator:
            return calculator(start_date, end_date, dimensions)
        
        return self._simulate_value(definition)
    
    def _simulate_value(self, definition: KPIDefinition) -> float:
        """Generate a simulated value for demonstration."""
        import random
        
        threshold = definition.threshold
        if threshold:
            # Generate value around target
            target = threshold.target
            variance = target * 0.15  # 15% variance
            return max(0, target + random.uniform(-variance, variance))
        
        # Default random values based on unit
        if definition.unit == KPIUnit.PERCENTAGE:
            return random.uniform(70, 98)
        elif definition.unit in [KPIUnit.DAYS, KPIUnit.HOURS]:
            return random.uniform(1, 30)
        elif definition.unit == KPIUnit.PPM:
            return random.uniform(100, 5000)
        else:
            return random.uniform(50, 150)
    
    def _calculate_oee(
        self,
        start_date: date,
        end_date: date,
        dimensions: dict[str, str] | None,
    ) -> float:
        """Calculate OEE (Overall Equipment Effectiveness)."""
        # OEE = Availability × Performance × Quality
        # Simulated for now
        availability = 0.92
        performance = 0.88
        quality = 0.99
        return availability * performance * quality * 100
    
    def _calculate_quote_cycle_time(
        self,
        start_date: date,
        end_date: date,
        dimensions: dict[str, str] | None,
    ) -> float:
        """Calculate average quote cycle time in days."""
        # Simulated - would query quote data in production
        return 4.5
    
    def _calculate_training_compliance(
        self,
        start_date: date,
        end_date: date,
        dimensions: dict[str, str] | None,
    ) -> float:
        """Calculate training compliance percentage."""
        # Simulated - would query training records in production
        return 94.5
    
    # --------------------------------------------------------------------------
    # Trend Analysis
    # --------------------------------------------------------------------------
    
    def analyze_trend(
        self,
        kpi_id: str,
        current_start: date,
        current_end: date,
        comparison_periods: int = 1,
    ) -> KPITrend | None:
        """Analyze trend for a KPI by comparing periods."""
        definition = self._definitions.get(kpi_id)
        if not definition:
            return None
        
        # Get current period values
        current_values = self.get_values(kpi_id, current_start, current_end)
        if not current_values:
            return KPITrend(
                kpi_id=kpi_id,
                direction=TrendDirection.INSUFFICIENT_DATA,
                current_value=0,
                previous_value=0,
                change_absolute=0,
                change_percentage=0,
            )
        
        # Calculate current average
        current_avg = sum(v.value for v in current_values) / len(current_values)
        
        # Calculate previous period
        period_days = (current_end - current_start).days + 1
        prev_end = current_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days - 1)
        
        prev_values = self.get_values(kpi_id, prev_start, prev_end)
        
        if not prev_values:
            return KPITrend(
                kpi_id=kpi_id,
                direction=TrendDirection.INSUFFICIENT_DATA,
                current_value=current_avg,
                previous_value=0,
                change_absolute=0,
                change_percentage=0,
                current_period=(current_start, current_end),
            )
        
        # Calculate previous average
        prev_avg = sum(v.value for v in prev_values) / len(prev_values)
        
        # Calculate changes
        change_abs = current_avg - prev_avg
        change_pct = (change_abs / prev_avg * 100) if prev_avg != 0 else 0
        
        # Determine trend direction
        threshold = 5  # 5% change threshold
        if definition.direction == KPIDirection.HIGHER_IS_BETTER:
            if change_pct >= threshold:
                direction = TrendDirection.IMPROVING
            elif change_pct <= -threshold:
                direction = TrendDirection.DECLINING
            else:
                direction = TrendDirection.STABLE
        elif definition.direction == KPIDirection.LOWER_IS_BETTER:
            if change_pct <= -threshold:
                direction = TrendDirection.IMPROVING
            elif change_pct >= threshold:
                direction = TrendDirection.DECLINING
            else:
                direction = TrendDirection.STABLE
        else:
            direction = TrendDirection.STABLE
        
        # Calculate statistics
        all_values = [v.value for v in current_values + prev_values]
        moving_avg = sum(all_values) / len(all_values)
        
        variance = sum((v - moving_avg) ** 2 for v in all_values) / len(all_values)
        std_dev = variance ** 0.5
        
        return KPITrend(
            kpi_id=kpi_id,
            direction=direction,
            current_value=current_avg,
            previous_value=prev_avg,
            change_absolute=change_abs,
            change_percentage=change_pct,
            current_period=(current_start, current_end),
            previous_period=(prev_start, prev_end),
            moving_average=moving_avg,
            standard_deviation=std_dev,
        )
    
    # --------------------------------------------------------------------------
    # Dashboard Management
    # --------------------------------------------------------------------------
    
    def create_dashboard(self, dashboard: KPIDashboard) -> KPIDashboard:
        """Create a new KPI dashboard."""
        if not dashboard.id:
            dashboard.id = str(uuid4())
        
        self._dashboards[dashboard.id] = dashboard
        return dashboard
    
    def get_dashboard(self, dashboard_id: str) -> KPIDashboard | None:
        """Get a dashboard by ID."""
        return self._dashboards.get(dashboard_id)
    
    def update_dashboard(
        self,
        dashboard_id: str,
        updates: dict[str, Any],
    ) -> KPIDashboard | None:
        """Update a dashboard."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        
        for key, value in updates.items():
            if hasattr(dashboard, key):
                setattr(dashboard, key, value)
        
        return dashboard
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        if dashboard_id not in self._dashboards:
            return False
        
        del self._dashboards[dashboard_id]
        return True
    
    def list_dashboards(
        self,
        owner_id: str | None = None,
        include_public: bool = True,
    ) -> list[KPIDashboard]:
        """List dashboards."""
        dashboards = list(self._dashboards.values())
        
        if owner_id:
            dashboards = [
                d for d in dashboards
                if d.owner_id == owner_id or (include_public and d.is_public)
            ]
        
        return dashboards
    
    def get_dashboard_data(
        self,
        dashboard_id: str,
        start_date: date,
        end_date: date,
        dimensions: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Get all KPI data for a dashboard."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return {}
        
        result = {
            "dashboard": {
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "kpis": {},
        }
        
        for kpi_id in dashboard.kpi_ids:
            # Calculate current value
            calc_result = self.calculate_kpi(kpi_id, start_date, end_date, None, dimensions)
            
            # Get trend
            trend = self.analyze_trend(kpi_id, start_date, end_date)
            
            definition = self._definitions.get(kpi_id)
            
            result["kpis"][kpi_id] = {
                "definition": {
                    "name": definition.name if definition else kpi_id,
                    "unit": definition.unit.value if definition else "unknown",
                    "direction": definition.direction.value if definition else "unknown",
                },
                "current_value": calc_result.value.value if calc_result.value else None,
                "status": calc_result.value.status.value if calc_result.value else "no_data",
                "target": definition.threshold.target if definition and definition.threshold else None,
                "trend": {
                    "direction": trend.direction.value if trend else "insufficient_data",
                    "change_percentage": trend.change_percentage if trend else 0,
                } if trend else None,
            }
        
        return result
    
    # --------------------------------------------------------------------------
    # Default KPIs
    # --------------------------------------------------------------------------
    
    def _register_default_kpis(self) -> None:
        """Register Phase 1 KPIs."""
        default_kpis = [
            # Quote-to-Cash KPIs
            KPIDefinition(
                id="rfq-completeness",
                name="RFQ Completeness Score",
                description="Average completeness score of RFQs at qualification gate",
                category=KPICategory.RFQ,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=85, warning_threshold=10, critical_threshold=20),
                data_source=KPIDataSource(
                    entity_type="rfq",
                    fields=["completeness_score"],
                    aggregation=AggregationType.AVERAGE,
                ),
                tags=["phase1", "quote-to-cash"],
            ),
            KPIDefinition(
                id="qualification-discipline",
                name="Qualification Discipline",
                description="Percentage of RFQs with completed qualification checklist",
                category=KPICategory.RFQ,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=95, warning_threshold=5, critical_threshold=15),
                tags=["phase1", "quote-to-cash"],
            ),
            KPIDefinition(
                id="quote-cycle-time",
                name="Quote Cycle Time",
                description="Average days from RFQ received to quote released",
                category=KPICategory.QUOTING,
                unit=KPIUnit.DAYS,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=5, warning_threshold=20, critical_threshold=40),
                custom_calculator="quote_cycle_time",
                tags=["phase1", "quote-to-cash"],
            ),
            KPIDefinition(
                id="quote-revision-rate",
                name="Quote Revision Rate",
                description="Percentage of quotes requiring revisions after initial release",
                category=KPICategory.QUOTING,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=10, warning_threshold=30, critical_threshold=50),
                tags=["phase1", "quote-to-cash"],
            ),
            KPIDefinition(
                id="margin-protection",
                name="Margin Protection",
                description="Percentage of quotes meeting minimum margin threshold",
                category=KPICategory.QUOTING,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=90, warning_threshold=10, critical_threshold=20),
                tags=["phase1", "quote-to-cash"],
            ),
            KPIDefinition(
                id="win-rate",
                name="Win Rate",
                description="Percentage of quotes won vs total quotes sent",
                category=KPICategory.SALES,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=35, warning_threshold=15, critical_threshold=30),
                tags=["phase1", "quote-to-cash"],
            ),
            KPIDefinition(
                id="bad-win-rate",
                name="Bad Win Rate",
                description="Percentage of won quotes with margin < target after production",
                category=KPICategory.SALES,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=5, warning_threshold=50, critical_threshold=100),
                tags=["phase1", "quote-to-cash"],
            ),
            
            # Cadence & LSW KPIs
            KPIDefinition(
                id="cadence-adherence",
                name="Cadence Adherence",
                description="Percentage of scheduled reviews/meetings completed on time",
                category=KPICategory.CADENCE,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=90, warning_threshold=10, critical_threshold=20),
                tags=["phase1", "cadence"],
            ),
            KPIDefinition(
                id="lsw-compliance",
                name="LSW Compliance",
                description="Percentage of LSW items completed on schedule",
                category=KPICategory.LSW,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=95, warning_threshold=5, critical_threshold=15),
                tags=["phase1", "lsw"],
            ),
            KPIDefinition(
                id="knowledge-capture",
                name="Knowledge Capture Rate",
                description="Lessons learned documented per month",
                category=KPICategory.PROBLEM_SOLVING,
                unit=KPIUnit.COUNT,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=10, warning_threshold=30, critical_threshold=50),
                tags=["phase1", "learning"],
            ),
            
            # Production KPIs
            KPIDefinition(
                id="oee",
                name="Overall Equipment Effectiveness",
                description="OEE = Availability × Performance × Quality",
                category=KPICategory.OEE,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=85, warning_threshold=10, critical_threshold=20),
                custom_calculator="oee_calculator",
                tags=["production", "oee"],
            ),
            KPIDefinition(
                id="first-pass-yield",
                name="First Pass Yield",
                description="Units passing first inspection vs total units",
                category=KPICategory.QUALITY,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=98, warning_threshold=2, critical_threshold=5),
                tags=["production", "quality"],
            ),
            KPIDefinition(
                id="takt-adherence",
                name="Takt Time Adherence",
                description="Actual cycle time vs takt time",
                category=KPICategory.PRODUCTION,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.TARGET_IS_BEST,
                threshold=KPIThreshold(target=100, warning_threshold=5, critical_threshold=10),
                tags=["production"],
            ),
            KPIDefinition(
                id="work-order-on-time",
                name="Work Order On-Time Completion",
                description="Percentage of work orders completed by scheduled date",
                category=KPICategory.PRODUCTION,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=95, warning_threshold=5, critical_threshold=15),
                tags=["production"],
            ),
            
            # Quality KPIs
            KPIDefinition(
                id="nc-rate-ppm",
                name="NC Rate (PPM)",
                description="Non-conformances per million units",
                category=KPICategory.QUALITY,
                unit=KPIUnit.PPM,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=500, warning_threshold=50, critical_threshold=100),
                tags=["quality"],
            ),
            KPIDefinition(
                id="capa-closure-rate",
                name="CAPA Closure Rate",
                description="CAPAs closed on time vs total CAPAs due",
                category=KPICategory.QUALITY,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=90, warning_threshold=10, critical_threshold=20),
                tags=["quality"],
            ),
            KPIDefinition(
                id="escape-rate",
                name="Escape Rate",
                description="Customer-detected defects vs total shipped",
                category=KPICategory.QUALITY,
                unit=KPIUnit.PPM,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=100, warning_threshold=50, critical_threshold=100),
                tags=["quality"],
            ),
            
            # Training KPIs
            KPIDefinition(
                id="training-compliance",
                name="Training Compliance",
                description="Percentage of required certifications current",
                category=KPICategory.TRAINING,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=100, warning_threshold=5, critical_threshold=10),
                custom_calculator="training_compliance",
                tags=["training"],
            ),
            KPIDefinition(
                id="skill-gap-index",
                name="Skill Gap Index",
                description="Required skills minus available skills per station",
                category=KPICategory.SKILLS,
                unit=KPIUnit.INDEX,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=0, warning_threshold=100, critical_threshold=200),
                tags=["training", "skills"],
            ),
            KPIDefinition(
                id="cert-expiration-rate",
                name="Certification Expiration Rate",
                description="Certifications expiring within 30 days",
                category=KPICategory.TRAINING,
                unit=KPIUnit.COUNT,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=0, warning_threshold=100, critical_threshold=200),
                tags=["training"],
            ),
            
            # Andon KPIs
            KPIDefinition(
                id="andon-mttr",
                name="Andon MTTR",
                description="Mean time to resolution for Andon events (minutes)",
                category=KPICategory.ANDON,
                unit=KPIUnit.MINUTES,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=15, warning_threshold=33, critical_threshold=67),
                tags=["andon"],
            ),
            KPIDefinition(
                id="andon-frequency",
                name="Andon Frequency",
                description="Andon events per day",
                category=KPICategory.ANDON,
                unit=KPIUnit.PER_DAY,
                direction=KPIDirection.LOWER_IS_BETTER,
                threshold=KPIThreshold(target=5, warning_threshold=40, critical_threshold=80),
                tags=["andon"],
            ),
            KPIDefinition(
                id="andon-ack-sla",
                name="Andon Acknowledgement SLA",
                description="Percentage of Andons acknowledged within SLA",
                category=KPICategory.ANDON,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.HIGHER_IS_BETTER,
                threshold=KPIThreshold(target=95, warning_threshold=5, critical_threshold=15),
                tags=["andon"],
            ),
            KPIDefinition(
                id="a3-escalation-rate",
                name="A3 Escalation Rate",
                description="Percentage of Andon events escalated to A3",
                category=KPICategory.PROBLEM_SOLVING,
                unit=KPIUnit.PERCENTAGE,
                direction=KPIDirection.TARGET_IS_BEST,
                threshold=KPIThreshold(target=10, warning_threshold=50, critical_threshold=100),
                tags=["andon", "problem-solving"],
            ),
        ]
        
        for kpi in default_kpis:
            self.create_definition(kpi)
        
        # Create default dashboards
        self._register_default_dashboards()
    
    def _register_default_dashboards(self) -> None:
        """Register default dashboards."""
        # Quote-to-Cash Dashboard
        self.create_dashboard(KPIDashboard(
            id="quote-to-cash",
            name="Quote-to-Cash Performance",
            description="Key metrics for RFQ processing and quoting performance",
            kpi_ids=[
                "rfq-completeness",
                "qualification-discipline",
                "quote-cycle-time",
                "quote-revision-rate",
                "margin-protection",
                "win-rate",
                "bad-win-rate",
            ],
            is_public=True,
        ))
        
        # Production Dashboard
        self.create_dashboard(KPIDashboard(
            id="production",
            name="Production Performance",
            description="Shop floor performance metrics",
            kpi_ids=[
                "oee",
                "first-pass-yield",
                "takt-adherence",
                "work-order-on-time",
            ],
            is_public=True,
        ))
        
        # Quality Dashboard
        self.create_dashboard(KPIDashboard(
            id="quality",
            name="Quality Performance",
            description="Quality and non-conformance metrics",
            kpi_ids=[
                "nc-rate-ppm",
                "first-pass-yield",
                "capa-closure-rate",
                "escape-rate",
            ],
            is_public=True,
        ))
        
        # Training Dashboard
        self.create_dashboard(KPIDashboard(
            id="training",
            name="Training & Skills",
            description="Training compliance and skill gap metrics",
            kpi_ids=[
                "training-compliance",
                "skill-gap-index",
                "cert-expiration-rate",
            ],
            is_public=True,
        ))
        
        # Andon Dashboard
        self.create_dashboard(KPIDashboard(
            id="andon",
            name="Andon Performance",
            description="Andon response and resolution metrics",
            kpi_ids=[
                "andon-mttr",
                "andon-frequency",
                "andon-ack-sla",
                "a3-escalation-rate",
            ],
            is_public=True,
        ))
        
        # Executive Dashboard (all Phase 1 KPIs)
        self.create_dashboard(KPIDashboard(
            id="executive",
            name="Executive Overview",
            description="High-level KPIs across all domains",
            kpi_ids=[
                "rfq-completeness",
                "quote-cycle-time",
                "win-rate",
                "oee",
                "first-pass-yield",
                "training-compliance",
                "andon-mttr",
                "lsw-compliance",
            ],
            is_public=True,
        ))


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def build_kpi_definition(
    name: str,
    description: str,
    category: str,
    unit: str,
    direction: str,
    id: str | None = None,
    target: float | None = None,
    warning_threshold: float = 10.0,
    critical_threshold: float = 20.0,
    **kwargs: Any,
) -> KPIDefinition:
    """Helper to build a KPI definition."""
    threshold = None
    if target is not None:
        threshold = KPIThreshold(
            target=target,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )
    
    return KPIDefinition(
        id=id or str(uuid4()),
        name=name,
        description=description,
        category=KPICategory(category),
        unit=KPIUnit(unit),
        direction=KPIDirection(direction),
        threshold=threshold,
        **kwargs,
    )


def get_default_kpi_ids() -> list[str]:
    """Get list of default KPI IDs."""
    return [
        # Phase 1
        "rfq-completeness",
        "qualification-discipline",
        "quote-cycle-time",
        "quote-revision-rate",
        "margin-protection",
        "win-rate",
        "bad-win-rate",
        "cadence-adherence",
        "lsw-compliance",
        "knowledge-capture",
        # Production
        "oee",
        "first-pass-yield",
        "takt-adherence",
        "work-order-on-time",
        # Quality
        "nc-rate-ppm",
        "capa-closure-rate",
        "escape-rate",
        # Training
        "training-compliance",
        "skill-gap-index",
        "cert-expiration-rate",
        # Andon
        "andon-mttr",
        "andon-frequency",
        "andon-ack-sla",
        "a3-escalation-rate",
    ]


def get_default_dashboard_ids() -> list[str]:
    """Get list of default dashboard IDs."""
    return [
        "quote-to-cash",
        "production",
        "quality",
        "training",
        "andon",
        "executive",
    ]
