"""
AI CTQ Summarization Service.

Provides AI-powered summarization and analysis for CTQ (Critical to Quality)
characteristics and their measurement data:
- CTQ Summary Generation
- Trend Analysis
- Capability Analysis (Cpk/Ppk)
- Risk Identification
- Improvement Recommendations
- Compliance Report Generation

Key Features:
- Statistical analysis of measurement data
- Visual trend detection
- Out-of-spec pattern identification
- Root cause hypothesis generation
- Actionable improvement suggestions
- Multi-format summary output
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4
import math
import statistics


# ============================================================================
# Enums
# ============================================================================

class SummaryType(str, Enum):
    """Type of CTQ summary."""
    
    OVERVIEW = "overview"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    AUDIT = "audit"
    TREND = "trend"


class AnalysisPeriod(str, Enum):
    """Time period for analysis."""
    
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    LAST_YEAR = "1y"
    ALL_TIME = "all"
    CUSTOM = "custom"


class RiskLevel(str, Enum):
    """Risk level classification."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
    UNKNOWN = "unknown"


class TrendDirection(str, Enum):
    """Direction of trend."""
    
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"


class CapabilityStatus(str, Enum):
    """Process capability status."""
    
    EXCELLENT = "excellent"  # Cpk >= 2.0
    CAPABLE = "capable"  # 1.33 <= Cpk < 2.0
    MARGINALLY_CAPABLE = "marginally_capable"  # 1.0 <= Cpk < 1.33
    NOT_CAPABLE = "not_capable"  # Cpk < 1.0
    UNKNOWN = "unknown"


class RecommendationType(str, Enum):
    """Type of improvement recommendation."""
    
    PROCESS_ADJUSTMENT = "process_adjustment"
    EQUIPMENT_CALIBRATION = "equipment_calibration"
    OPERATOR_TRAINING = "operator_training"
    MATERIAL_REVIEW = "material_review"
    DESIGN_REVIEW = "design_review"
    CONTROL_PLAN_UPDATE = "control_plan_update"
    SAMPLE_SIZE_INCREASE = "sample_size_increase"
    MONITORING_FREQUENCY = "monitoring_frequency"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    IMMEDIATE_ACTION = "immediate_action"


class OutputFormat(str, Enum):
    """Output format for summaries."""
    
    TEXT = "text"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MeasurementData:
    """Measurement data point."""
    
    id: UUID
    value: Decimal
    measured_at: datetime
    result: str  # pass, fail, marginal
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    operator_id: Optional[UUID] = None
    deviation: Optional[Decimal] = None
    notes: Optional[str] = None


@dataclass
class CTQSpec:
    """CTQ specification data."""
    
    id: UUID
    ctq_number: str
    name: str
    category: str
    priority: str  # critical, major, minor
    nominal_value: Optional[Decimal] = None
    upper_spec_limit: Optional[Decimal] = None
    lower_spec_limit: Optional[Decimal] = None
    unit_of_measure: str = "mm"
    target_cpk: Optional[Decimal] = None
    target_ppk: Optional[Decimal] = None
    part_number: Optional[str] = None
    description: Optional[str] = None


@dataclass
class StatisticalSummary:
    """Statistical summary of measurement data."""
    
    count: int = 0
    mean: Optional[Decimal] = None
    std_dev: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    median: Optional[Decimal] = None
    range: Optional[Decimal] = None
    pass_count: int = 0
    fail_count: int = 0
    marginal_count: int = 0
    pass_rate: Decimal = Decimal("0")
    cpk: Optional[Decimal] = None
    ppk: Optional[Decimal] = None
    capability_status: CapabilityStatus = CapabilityStatus.UNKNOWN


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    
    direction: TrendDirection = TrendDirection.INSUFFICIENT_DATA
    slope: Optional[Decimal] = None
    r_squared: Optional[Decimal] = None
    period_mean: Optional[Decimal] = None
    prior_period_mean: Optional[Decimal] = None
    mean_shift: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    data_points: int = 0
    description: str = ""


@dataclass
class RiskAssessment:
    """Risk assessment for a CTQ."""
    
    level: RiskLevel = RiskLevel.UNKNOWN
    score: Decimal = Decimal("0")
    factors: list[str] = field(default_factory=list)
    description: str = ""
    immediate_action_required: bool = False


@dataclass
class Recommendation:
    """Improvement recommendation."""
    
    id: UUID = field(default_factory=uuid4)
    type: RecommendationType = RecommendationType.PROCESS_ADJUSTMENT
    priority: str = "medium"  # critical, high, medium, low
    title: str = ""
    description: str = ""
    expected_impact: str = ""
    effort_level: str = "medium"  # low, medium, high
    confidence: Decimal = Decimal("0.8")


@dataclass
class CTQSummary:
    """Complete CTQ summary."""
    
    id: UUID = field(default_factory=uuid4)
    ctq_id: UUID = field(default_factory=uuid4)
    ctq_number: str = ""
    ctq_name: str = ""
    summary_type: SummaryType = SummaryType.OVERVIEW
    period: AnalysisPeriod = AnalysisPeriod.LAST_30_DAYS
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Statistical Summary
    statistics: StatisticalSummary = field(default_factory=StatisticalSummary)
    
    # Trend Analysis
    trend: TrendAnalysis = field(default_factory=TrendAnalysis)
    
    # Risk Assessment
    risk: RiskAssessment = field(default_factory=RiskAssessment)
    
    # Recommendations
    recommendations: list[Recommendation] = field(default_factory=list)
    
    # Generated Content
    executive_summary: str = ""
    detailed_analysis: str = ""
    key_findings: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)
    generation_time_ms: int = 0
    format: OutputFormat = OutputFormat.TEXT


@dataclass
class MultiCTQSummary:
    """Summary across multiple CTQs."""
    
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    period: AnalysisPeriod = AnalysisPeriod.LAST_30_DAYS
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Aggregate Statistics
    total_ctqs: int = 0
    total_measurements: int = 0
    overall_pass_rate: Decimal = Decimal("0")
    ctqs_at_risk: int = 0
    ctqs_not_capable: int = 0
    
    # Individual Summaries
    ctq_summaries: list[CTQSummary] = field(default_factory=list)
    
    # Top Issues
    top_issues: list[str] = field(default_factory=list)
    top_recommendations: list[Recommendation] = field(default_factory=list)
    
    # Generated Content
    executive_summary: str = ""
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Templates
# ============================================================================

EXECUTIVE_SUMMARY_TEMPLATES = {
    "good_performance": """
CTQ Summary for {ctq_name} ({ctq_number})

The {ctq_name} characteristic is performing well within specifications. Over the analysis period, we recorded {count} measurements with a pass rate of {pass_rate}%. The process capability index (Cpk) of {cpk} indicates {capability_description}. No immediate action is required, though continued monitoring is recommended.
""",
    
    "marginal_performance": """
CTQ Summary for {ctq_name} ({ctq_number})

The {ctq_name} characteristic requires attention. Over the analysis period, we recorded {count} measurements with a pass rate of {pass_rate}%. The current Cpk of {cpk} indicates {capability_description}. The trend analysis shows {trend_description}. Recommended actions include {top_recommendation}.
""",
    
    "poor_performance": """
CTQ Summary for {ctq_name} ({ctq_number})

ATTENTION REQUIRED: The {ctq_name} characteristic is not meeting quality targets. Over the analysis period, we recorded {count} measurements with a pass rate of {pass_rate}%, which is below acceptable levels. The Cpk of {cpk} indicates the process is {capability_description}. Immediate action is recommended to address {risk_factors}.
""",
    
    "insufficient_data": """
CTQ Summary for {ctq_name} ({ctq_number})

Insufficient measurement data is available for comprehensive analysis. Only {count} measurements have been recorded in the analysis period. To enable meaningful statistical analysis and trend detection, a minimum of 30 measurements is recommended. Current observations show a pass rate of {pass_rate}%.
""",
}

DETAILED_ANALYSIS_TEMPLATES = {
    "statistical": """
## Statistical Analysis

### Measurement Summary
- **Total Measurements:** {count}
- **Mean Value:** {mean} {unit}
- **Standard Deviation:** {std_dev} {unit}
- **Min / Max:** {min_value} / {max_value} {unit}
- **Range:** {range} {unit}

### Specification Performance
- **Nominal:** {nominal} {unit}
- **USL / LSL:** {usl} / {lsl} {unit}
- **Pass Rate:** {pass_rate}%
- **Pass/Fail/Marginal:** {pass_count} / {fail_count} / {marginal_count}

### Process Capability
- **Cpk:** {cpk} ({cpk_status})
- **Ppk:** {ppk}
- **Target Cpk:** {target_cpk}
""",
    
    "trend": """
## Trend Analysis

### Direction
{trend_direction}

### Statistical Trend
- **Period Mean:** {period_mean} {unit}
- **Prior Period Mean:** {prior_mean} {unit}
- **Mean Shift:** {mean_shift}%
- **Volatility (CV):** {volatility}%

### Observations
{trend_observations}
""",
    
    "risk": """
## Risk Assessment

### Risk Level: {risk_level}
**Score:** {risk_score}/100

### Contributing Factors
{risk_factors}

### Recommended Actions
{action_items}
""",
}

CAPABILITY_DESCRIPTIONS = {
    CapabilityStatus.EXCELLENT: "excellent process capability that exceeds requirements",
    CapabilityStatus.CAPABLE: "acceptable process capability meeting requirements",
    CapabilityStatus.MARGINALLY_CAPABLE: "marginally acceptable process capability requiring monitoring",
    CapabilityStatus.NOT_CAPABLE: "process capability below requirements requiring immediate attention",
    CapabilityStatus.UNKNOWN: "unknown process capability due to insufficient data",
}

TREND_DESCRIPTIONS = {
    TrendDirection.IMPROVING: "an improving trend with measurements moving toward target",
    TrendDirection.STABLE: "a stable trend with consistent measurement values",
    TrendDirection.DEGRADING: "a concerning degrading trend requiring attention",
    TrendDirection.VOLATILE: "high volatility in measurements indicating process instability",
    TrendDirection.INSUFFICIENT_DATA: "insufficient data for reliable trend analysis",
}


# ============================================================================
# Service Class
# ============================================================================

class AICTQSummarizationService:
    """
    AI-powered CTQ summarization and analysis service.
    
    Provides comprehensive analysis of CTQ measurement data including:
    - Statistical analysis
    - Trend detection
    - Risk assessment
    - Improvement recommendations
    """
    
    def __init__(
        self,
        min_samples_for_stats: int = 2,
        min_samples_for_trend: int = 10,
        min_samples_for_capability: int = 30,
        cpk_excellent_threshold: Decimal = Decimal("2.0"),
        cpk_capable_threshold: Decimal = Decimal("1.33"),
        cpk_marginal_threshold: Decimal = Decimal("1.0"),
    ):
        """
        Initialize the service.
        
        Args:
            min_samples_for_stats: Minimum samples needed for basic statistics
            min_samples_for_trend: Minimum samples needed for trend analysis
            min_samples_for_capability: Minimum samples for reliable capability analysis
            cpk_excellent_threshold: Cpk threshold for excellent rating
            cpk_capable_threshold: Cpk threshold for capable rating
            cpk_marginal_threshold: Cpk threshold for marginal rating
        """
        self.min_samples_for_stats = min_samples_for_stats
        self.min_samples_for_trend = min_samples_for_trend
        self.min_samples_for_capability = min_samples_for_capability
        self.cpk_excellent_threshold = cpk_excellent_threshold
        self.cpk_capable_threshold = cpk_capable_threshold
        self.cpk_marginal_threshold = cpk_marginal_threshold
        
        self._summaries: dict[UUID, CTQSummary] = {}
        self._multi_summaries: dict[UUID, MultiCTQSummary] = {}
    
    # ========================================================================
    # Statistical Analysis
    # ========================================================================
    
    def calculate_statistics(
        self,
        measurements: list[MeasurementData],
        spec: CTQSpec,
    ) -> StatisticalSummary:
        """
        Calculate statistical summary from measurement data.
        
        Args:
            measurements: List of measurement data points
            spec: CTQ specification
            
        Returns:
            StatisticalSummary object with calculated statistics
        """
        summary = StatisticalSummary()
        
        if not measurements:
            return summary
        
        # Extract values
        values = [float(m.value) for m in measurements]
        summary.count = len(values)
        
        # Count results
        for m in measurements:
            if m.result == "pass":
                summary.pass_count += 1
            elif m.result == "fail":
                summary.fail_count += 1
            elif m.result == "marginal":
                summary.marginal_count += 1
        
        # Calculate pass rate
        if summary.count > 0:
            summary.pass_rate = Decimal(str(
                (summary.pass_count / summary.count) * 100
            )).quantize(Decimal("0.01"))
        
        # Basic statistics
        if len(values) >= self.min_samples_for_stats:
            summary.mean = Decimal(str(statistics.mean(values))).quantize(Decimal("0.000001"))
            summary.min_value = Decimal(str(min(values))).quantize(Decimal("0.000001"))
            summary.max_value = Decimal(str(max(values))).quantize(Decimal("0.000001"))
            summary.range = summary.max_value - summary.min_value
            summary.median = Decimal(str(statistics.median(values))).quantize(Decimal("0.000001"))
            
            if len(values) >= self.min_samples_for_stats:
                try:
                    summary.std_dev = Decimal(str(
                        statistics.stdev(values)
                    )).quantize(Decimal("0.000001"))
                except statistics.StatisticsError:
                    summary.std_dev = Decimal("0")
        
        # Process capability (Cpk)
        if (
            summary.std_dev is not None
            and summary.std_dev > 0
            and spec.upper_spec_limit is not None
            and spec.lower_spec_limit is not None
            and summary.mean is not None
        ):
            usl = float(spec.upper_spec_limit)
            lsl = float(spec.lower_spec_limit)
            mean = float(summary.mean)
            std = float(summary.std_dev)
            
            if std > 0:
                cpu = (usl - mean) / (3 * std)
                cpl = (mean - lsl) / (3 * std)
                cpk = min(cpu, cpl)
                summary.cpk = Decimal(str(cpk)).quantize(Decimal("0.01"))
                
                # Ppk (using sample standard deviation)
                summary.ppk = summary.cpk  # Simplified; in practice Ppk uses overall variation
        
        # Determine capability status
        summary.capability_status = self._determine_capability_status(summary.cpk)
        
        return summary
    
    def _determine_capability_status(
        self,
        cpk: Optional[Decimal],
    ) -> CapabilityStatus:
        """Determine capability status from Cpk value."""
        if cpk is None:
            return CapabilityStatus.UNKNOWN
        
        if cpk >= self.cpk_excellent_threshold:
            return CapabilityStatus.EXCELLENT
        elif cpk >= self.cpk_capable_threshold:
            return CapabilityStatus.CAPABLE
        elif cpk >= self.cpk_marginal_threshold:
            return CapabilityStatus.MARGINALLY_CAPABLE
        else:
            return CapabilityStatus.NOT_CAPABLE
    
    # ========================================================================
    # Trend Analysis
    # ========================================================================
    
    def analyze_trend(
        self,
        measurements: list[MeasurementData],
        spec: CTQSpec,
    ) -> TrendAnalysis:
        """
        Analyze trend in measurement data.
        
        Args:
            measurements: List of measurement data points (sorted by date)
            spec: CTQ specification
            
        Returns:
            TrendAnalysis object with trend information
        """
        analysis = TrendAnalysis()
        analysis.data_points = len(measurements)
        
        if len(measurements) < self.min_samples_for_trend:
            analysis.direction = TrendDirection.INSUFFICIENT_DATA
            analysis.description = f"Insufficient data for trend analysis (need at least {self.min_samples_for_trend} measurements)"
            return analysis
        
        # Sort by date
        sorted_measurements = sorted(measurements, key=lambda m: m.measured_at)
        values = [float(m.value) for m in sorted_measurements]
        
        # Calculate overall statistics
        mean_val = statistics.mean(values)
        analysis.period_mean = Decimal(str(mean_val)).quantize(Decimal("0.000001"))
        
        # Split into two periods for comparison
        mid_point = len(values) // 2
        first_half = values[:mid_point]
        second_half = values[mid_point:]
        
        if first_half and second_half:
            first_mean = statistics.mean(first_half)
            second_mean = statistics.mean(second_half)
            
            analysis.prior_period_mean = Decimal(str(first_mean)).quantize(Decimal("0.000001"))
            
            # Calculate mean shift percentage
            if first_mean != 0:
                shift = ((second_mean - first_mean) / abs(first_mean)) * 100
                analysis.mean_shift = Decimal(str(shift)).quantize(Decimal("0.01"))
        
        # Calculate volatility (coefficient of variation)
        if len(values) >= 2:
            try:
                std = statistics.stdev(values)
                if mean_val != 0:
                    cv = (std / abs(mean_val)) * 100
                    analysis.volatility = Decimal(str(cv)).quantize(Decimal("0.01"))
            except statistics.StatisticsError:
                pass
        
        # Simple linear regression for trend
        n = len(values)
        x_vals = list(range(n))
        x_mean = statistics.mean(x_vals)
        y_mean = mean_val
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, values))
        denominator = sum((x - x_mean) ** 2 for x in x_vals)
        
        if denominator != 0:
            slope = numerator / denominator
            analysis.slope = Decimal(str(slope)).quantize(Decimal("0.000001"))
            
            # Calculate R-squared
            y_pred = [y_mean + slope * (x - x_mean) for x in x_vals]
            ss_res = sum((y - yp) ** 2 for y, yp in zip(values, y_pred))
            ss_tot = sum((y - y_mean) ** 2 for y in values)
            
            if ss_tot > 0:
                r_squared = 1 - (ss_res / ss_tot)
                analysis.r_squared = Decimal(str(r_squared)).quantize(Decimal("0.01"))
        
        # Determine trend direction
        analysis.direction = self._determine_trend_direction(
            analysis.slope,
            analysis.volatility,
            analysis.mean_shift,
            spec,
        )
        
        analysis.description = self._generate_trend_description(analysis, spec)
        
        return analysis
    
    def _determine_trend_direction(
        self,
        slope: Optional[Decimal],
        volatility: Optional[Decimal],
        mean_shift: Optional[Decimal],
        spec: CTQSpec,
    ) -> TrendDirection:
        """Determine trend direction based on analysis."""
        # High volatility indicates unstable process
        if volatility is not None and volatility > Decimal("20"):
            return TrendDirection.VOLATILE
        
        if slope is None:
            return TrendDirection.INSUFFICIENT_DATA
        
        # Determine if moving toward or away from nominal
        if spec.nominal_value is not None:
            # If slope moves values toward nominal, it's improving
            if mean_shift is not None:
                if abs(mean_shift) < Decimal("2"):
                    return TrendDirection.STABLE
        
        slope_magnitude = abs(float(slope))
        if slope_magnitude < 0.001:
            return TrendDirection.STABLE
        elif slope > 0:
            # Positive slope - could be improving or degrading depending on limits
            if spec.upper_spec_limit and spec.nominal_value:
                if spec.nominal_value < spec.upper_spec_limit:
                    return TrendDirection.DEGRADING  # Moving toward upper limit
            return TrendDirection.STABLE
        else:
            # Negative slope
            if spec.lower_spec_limit and spec.nominal_value:
                if spec.nominal_value > spec.lower_spec_limit:
                    return TrendDirection.DEGRADING  # Moving toward lower limit
            return TrendDirection.STABLE
    
    def _generate_trend_description(
        self,
        analysis: TrendAnalysis,
        spec: CTQSpec,
    ) -> str:
        """Generate human-readable trend description."""
        direction_desc = TREND_DESCRIPTIONS.get(
            analysis.direction,
            "unknown trend pattern"
        )
        
        parts = [f"The data shows {direction_desc}."]
        
        if analysis.mean_shift is not None:
            if abs(analysis.mean_shift) > Decimal("1"):
                direction = "increased" if analysis.mean_shift > 0 else "decreased"
                parts.append(
                    f"The mean has {direction} by {abs(analysis.mean_shift)}% compared to the prior period."
                )
        
        if analysis.volatility is not None:
            if analysis.volatility > Decimal("15"):
                parts.append(
                    f"Process volatility is elevated at {analysis.volatility}% CV."
                )
            elif analysis.volatility < Decimal("5"):
                parts.append(
                    f"Process is very consistent with only {analysis.volatility}% CV."
                )
        
        return " ".join(parts)
    
    # ========================================================================
    # Risk Assessment
    # ========================================================================
    
    def assess_risk(
        self,
        statistics: StatisticalSummary,
        trend: TrendAnalysis,
        spec: CTQSpec,
    ) -> RiskAssessment:
        """
        Assess risk level for a CTQ based on statistics and trend.
        
        Args:
            statistics: Statistical summary
            trend: Trend analysis
            spec: CTQ specification
            
        Returns:
            RiskAssessment object
        """
        assessment = RiskAssessment()
        risk_score = Decimal("0")
        factors = []
        
        # Factor 1: Pass rate (0-30 points)
        if statistics.pass_rate < Decimal("85"):
            factor_score = (Decimal("100") - statistics.pass_rate) * Decimal("0.3")
            risk_score += factor_score
            factors.append(f"Low pass rate: {statistics.pass_rate}%")
        
        # Factor 2: Capability (0-30 points)
        if statistics.capability_status == CapabilityStatus.NOT_CAPABLE:
            risk_score += Decimal("30")
            factors.append(f"Process not capable (Cpk: {statistics.cpk})")
        elif statistics.capability_status == CapabilityStatus.MARGINALLY_CAPABLE:
            risk_score += Decimal("15")
            factors.append(f"Marginally capable (Cpk: {statistics.cpk})")
        
        # Factor 3: Trend (0-20 points)
        if trend.direction == TrendDirection.DEGRADING:
            risk_score += Decimal("20")
            factors.append("Degrading trend detected")
        elif trend.direction == TrendDirection.VOLATILE:
            risk_score += Decimal("15")
            factors.append("High process volatility")
        
        # Factor 4: Priority (0-20 points)
        if spec.priority == "critical":
            risk_score += Decimal("20")
            factors.append("Critical priority CTQ")
        elif spec.priority == "major":
            risk_score += Decimal("10")
            factors.append("Major priority CTQ")
        
        # Determine risk level
        assessment.score = min(risk_score, Decimal("100"))
        assessment.factors = factors
        
        if assessment.score >= Decimal("70"):
            assessment.level = RiskLevel.CRITICAL
            assessment.immediate_action_required = True
        elif assessment.score >= Decimal("50"):
            assessment.level = RiskLevel.HIGH
            assessment.immediate_action_required = True
        elif assessment.score >= Decimal("30"):
            assessment.level = RiskLevel.MEDIUM
        elif assessment.score >= Decimal("10"):
            assessment.level = RiskLevel.LOW
        else:
            assessment.level = RiskLevel.NONE
        
        # Generate description
        assessment.description = self._generate_risk_description(assessment)
        
        return assessment
    
    def _generate_risk_description(self, assessment: RiskAssessment) -> str:
        """Generate human-readable risk description."""
        level_descriptions = {
            RiskLevel.CRITICAL: "This CTQ requires immediate attention. Multiple risk factors indicate a high likelihood of quality issues.",
            RiskLevel.HIGH: "This CTQ has elevated risk and should be prioritized for improvement actions.",
            RiskLevel.MEDIUM: "This CTQ has moderate risk and should be monitored closely.",
            RiskLevel.LOW: "This CTQ has low risk but routine monitoring should continue.",
            RiskLevel.NONE: "This CTQ is performing well with minimal risk identified.",
        }
        
        base_desc = level_descriptions.get(assessment.level, "Unknown risk level.")
        
        if assessment.factors:
            factor_list = "; ".join(assessment.factors[:3])
            return f"{base_desc} Key factors: {factor_list}."
        
        return base_desc
    
    # ========================================================================
    # Recommendations
    # ========================================================================
    
    def generate_recommendations(
        self,
        statistics: StatisticalSummary,
        trend: TrendAnalysis,
        risk: RiskAssessment,
        spec: CTQSpec,
    ) -> list[Recommendation]:
        """
        Generate improvement recommendations.
        
        Args:
            statistics: Statistical summary
            trend: Trend analysis
            risk: Risk assessment
            spec: CTQ specification
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Capability-based recommendations
        if statistics.capability_status == CapabilityStatus.NOT_CAPABLE:
            recommendations.append(Recommendation(
                type=RecommendationType.ROOT_CAUSE_ANALYSIS,
                priority="critical",
                title="Conduct Root Cause Analysis",
                description=f"The process capability (Cpk: {statistics.cpk}) is below requirements. Perform a thorough root cause analysis to identify sources of variation.",
                expected_impact="Identification of key variation sources for targeted improvement",
                effort_level="medium",
                confidence=Decimal("0.95"),
            ))
            
            recommendations.append(Recommendation(
                type=RecommendationType.PROCESS_ADJUSTMENT,
                priority="high",
                title="Adjust Process Parameters",
                description="Based on the analysis, adjust process parameters to center the distribution and reduce variation.",
                expected_impact="Potential Cpk improvement of 0.3-0.5",
                effort_level="medium",
                confidence=Decimal("0.75"),
            ))
        
        elif statistics.capability_status == CapabilityStatus.MARGINALLY_CAPABLE:
            recommendations.append(Recommendation(
                type=RecommendationType.MONITORING_FREQUENCY,
                priority="medium",
                title="Increase Monitoring Frequency",
                description="The process is marginally capable. Increase measurement frequency to detect shifts early.",
                expected_impact="Earlier detection of process drift",
                effort_level="low",
                confidence=Decimal("0.85"),
            ))
        
        # Trend-based recommendations
        if trend.direction == TrendDirection.DEGRADING:
            recommendations.append(Recommendation(
                type=RecommendationType.EQUIPMENT_CALIBRATION,
                priority="high",
                title="Verify Equipment Calibration",
                description="A degrading trend may indicate equipment drift. Verify calibration of measurement equipment and process machinery.",
                expected_impact="Correction of systematic drift",
                effort_level="low",
                confidence=Decimal("0.70"),
            ))
        
        if trend.direction == TrendDirection.VOLATILE:
            recommendations.append(Recommendation(
                type=RecommendationType.MATERIAL_REVIEW,
                priority="medium",
                title="Review Material Consistency",
                description="High volatility may be caused by incoming material variation. Review supplier quality data.",
                expected_impact="Reduced variation from material sources",
                effort_level="medium",
                confidence=Decimal("0.65"),
            ))
            
            recommendations.append(Recommendation(
                type=RecommendationType.OPERATOR_TRAINING,
                priority="medium",
                title="Standardize Operator Methods",
                description="Volatility can result from operator technique variation. Review and standardize work instructions.",
                expected_impact="Reduced human-induced variation",
                effort_level="medium",
                confidence=Decimal("0.70"),
            ))
        
        # Pass rate recommendations
        if statistics.pass_rate < Decimal("90"):
            recommendations.append(Recommendation(
                type=RecommendationType.CONTROL_PLAN_UPDATE,
                priority="high",
                title="Update Control Plan",
                description=f"With a {statistics.pass_rate}% pass rate, the current control plan may need strengthening. Add additional inspection points or tighten controls.",
                expected_impact="Reduced defect escape rate",
                effort_level="medium",
                confidence=Decimal("0.80"),
            ))
        
        # Insufficient data recommendations
        if statistics.count < self.min_samples_for_capability:
            recommendations.append(Recommendation(
                type=RecommendationType.SAMPLE_SIZE_INCREASE,
                priority="medium",
                title="Increase Sample Size",
                description=f"Only {statistics.count} measurements available. Increase to at least {self.min_samples_for_capability} for reliable capability analysis.",
                expected_impact="More reliable statistical analysis",
                effort_level="low",
                confidence=Decimal("0.95"),
            ))
        
        # Critical priority recommendations
        if spec.priority == "critical" and risk.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.insert(0, Recommendation(
                type=RecommendationType.IMMEDIATE_ACTION,
                priority="critical",
                title="Immediate Containment Required",
                description="This is a critical CTQ with elevated risk. Implement immediate containment actions while addressing root cause.",
                expected_impact="Prevention of quality escapes",
                effort_level="high",
                confidence=Decimal("0.90"),
            ))
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))
        
        return recommendations
    
    # ========================================================================
    # Summary Generation
    # ========================================================================
    
    def generate_summary(
        self,
        spec: CTQSpec,
        measurements: list[MeasurementData],
        summary_type: SummaryType = SummaryType.OVERVIEW,
        period: AnalysisPeriod = AnalysisPeriod.LAST_30_DAYS,
        output_format: OutputFormat = OutputFormat.TEXT,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> CTQSummary:
        """
        Generate a complete CTQ summary.
        
        Args:
            spec: CTQ specification
            measurements: List of measurement data
            summary_type: Type of summary to generate
            period: Analysis time period
            output_format: Output format
            custom_start: Custom period start (for CUSTOM period)
            custom_end: Custom period end (for CUSTOM period)
            
        Returns:
            Complete CTQSummary object
        """
        start_time = datetime.utcnow()
        
        # Filter measurements by period
        period_start, period_end = self._calculate_period(period, custom_start, custom_end)
        filtered_measurements = [
            m for m in measurements
            if period_start <= m.measured_at <= period_end
        ]
        
        # Calculate statistics
        statistics = self.calculate_statistics(filtered_measurements, spec)
        
        # Analyze trend
        trend = self.analyze_trend(filtered_measurements, spec)
        
        # Assess risk
        risk = self.assess_risk(statistics, trend, spec)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(statistics, trend, risk, spec)
        
        # Generate content
        executive_summary = self._generate_executive_summary(
            spec, statistics, trend, risk, recommendations
        )
        detailed_analysis = self._generate_detailed_analysis(
            spec, statistics, trend, risk, output_format
        )
        key_findings = self._extract_key_findings(statistics, trend, risk)
        action_items = self._extract_action_items(recommendations)
        
        # Calculate generation time
        generation_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Create summary
        summary = CTQSummary(
            ctq_id=spec.id,
            ctq_number=spec.ctq_number,
            ctq_name=spec.name,
            summary_type=summary_type,
            period=period,
            period_start=period_start,
            period_end=period_end,
            statistics=statistics,
            trend=trend,
            risk=risk,
            recommendations=recommendations,
            executive_summary=executive_summary,
            detailed_analysis=detailed_analysis,
            key_findings=key_findings,
            action_items=action_items,
            generated_at=datetime.utcnow(),
            generation_time_ms=generation_time,
            format=output_format,
        )
        
        # Store summary
        self._summaries[summary.id] = summary
        
        return summary
    
    def _calculate_period(
        self,
        period: AnalysisPeriod,
        custom_start: Optional[datetime],
        custom_end: Optional[datetime],
    ) -> tuple[datetime, datetime]:
        """Calculate period start and end dates."""
        now = datetime.utcnow()
        end = now
        
        if period == AnalysisPeriod.CUSTOM and custom_start and custom_end:
            return custom_start, custom_end
        
        period_days = {
            AnalysisPeriod.LAST_24_HOURS: 1,
            AnalysisPeriod.LAST_7_DAYS: 7,
            AnalysisPeriod.LAST_30_DAYS: 30,
            AnalysisPeriod.LAST_90_DAYS: 90,
            AnalysisPeriod.LAST_YEAR: 365,
            AnalysisPeriod.ALL_TIME: 365 * 10,  # 10 years
        }
        
        days = period_days.get(period, 30)
        start = now - timedelta(days=days)
        
        return start, end
    
    def _generate_executive_summary(
        self,
        spec: CTQSpec,
        statistics: StatisticalSummary,
        trend: TrendAnalysis,
        risk: RiskAssessment,
        recommendations: list[Recommendation],
    ) -> str:
        """Generate executive summary text."""
        # Select template based on performance
        if statistics.count < self.min_samples_for_trend:
            template_key = "insufficient_data"
        elif risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            template_key = "poor_performance"
        elif statistics.capability_status in [CapabilityStatus.MARGINALLY_CAPABLE, CapabilityStatus.NOT_CAPABLE]:
            template_key = "marginal_performance"
        else:
            template_key = "good_performance"
        
        template = EXECUTIVE_SUMMARY_TEMPLATES.get(template_key, "")
        
        # Get top recommendation
        top_recommendation = recommendations[0].title if recommendations else "continued monitoring"
        
        # Format template
        summary = template.format(
            ctq_name=spec.name,
            ctq_number=spec.ctq_number,
            count=statistics.count,
            pass_rate=statistics.pass_rate,
            cpk=statistics.cpk if statistics.cpk else "N/A",
            capability_description=CAPABILITY_DESCRIPTIONS.get(
                statistics.capability_status, "unknown"
            ),
            trend_description=trend.description,
            top_recommendation=top_recommendation,
            risk_factors="; ".join(risk.factors[:2]) if risk.factors else "elevated risk levels",
        )
        
        return summary.strip()
    
    def _generate_detailed_analysis(
        self,
        spec: CTQSpec,
        statistics: StatisticalSummary,
        trend: TrendAnalysis,
        risk: RiskAssessment,
        output_format: OutputFormat,
    ) -> str:
        """Generate detailed analysis text."""
        parts = []
        
        # Statistical section
        stats_section = DETAILED_ANALYSIS_TEMPLATES["statistical"].format(
            count=statistics.count,
            mean=statistics.mean if statistics.mean else "N/A",
            unit=spec.unit_of_measure,
            std_dev=statistics.std_dev if statistics.std_dev else "N/A",
            min_value=statistics.min_value if statistics.min_value else "N/A",
            max_value=statistics.max_value if statistics.max_value else "N/A",
            range=statistics.range if statistics.range else "N/A",
            nominal=spec.nominal_value if spec.nominal_value else "N/A",
            usl=spec.upper_spec_limit if spec.upper_spec_limit else "N/A",
            lsl=spec.lower_spec_limit if spec.lower_spec_limit else "N/A",
            pass_rate=statistics.pass_rate,
            pass_count=statistics.pass_count,
            fail_count=statistics.fail_count,
            marginal_count=statistics.marginal_count,
            cpk=statistics.cpk if statistics.cpk else "N/A",
            cpk_status=statistics.capability_status.value,
            ppk=statistics.ppk if statistics.ppk else "N/A",
            target_cpk=spec.target_cpk if spec.target_cpk else "1.33",
        )
        parts.append(stats_section)
        
        # Trend section
        trend_section = DETAILED_ANALYSIS_TEMPLATES["trend"].format(
            trend_direction=TREND_DESCRIPTIONS.get(trend.direction, "Unknown"),
            period_mean=trend.period_mean if trend.period_mean else "N/A",
            unit=spec.unit_of_measure,
            prior_mean=trend.prior_period_mean if trend.prior_period_mean else "N/A",
            mean_shift=trend.mean_shift if trend.mean_shift else "N/A",
            volatility=trend.volatility if trend.volatility else "N/A",
            trend_observations=trend.description,
        )
        parts.append(trend_section)
        
        # Risk section
        risk_factors_list = "\n".join(f"- {f}" for f in risk.factors) if risk.factors else "- None identified"
        risk_section = DETAILED_ANALYSIS_TEMPLATES["risk"].format(
            risk_level=risk.level.value.upper(),
            risk_score=risk.score,
            risk_factors=risk_factors_list,
            action_items=risk.description,
        )
        parts.append(risk_section)
        
        full_analysis = "\n".join(parts)
        
        # Convert format if needed
        if output_format == OutputFormat.HTML:
            full_analysis = self._markdown_to_html(full_analysis)
        elif output_format == OutputFormat.JSON:
            full_analysis = self._to_json(statistics, trend, risk)
        
        return full_analysis
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML."""
        import re
        html = markdown
        
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Paragraphs
        html = html.replace('\n\n', '</p><p>')
        html = f'<p>{html}</p>'
        
        return html
    
    def _to_json(
        self,
        statistics: StatisticalSummary,
        trend: TrendAnalysis,
        risk: RiskAssessment,
    ) -> str:
        """Convert analysis to JSON."""
        import json
        
        data = {
            "statistics": {
                "count": statistics.count,
                "mean": str(statistics.mean) if statistics.mean else None,
                "std_dev": str(statistics.std_dev) if statistics.std_dev else None,
                "pass_rate": str(statistics.pass_rate),
                "cpk": str(statistics.cpk) if statistics.cpk else None,
                "capability_status": statistics.capability_status.value,
            },
            "trend": {
                "direction": trend.direction.value,
                "mean_shift": str(trend.mean_shift) if trend.mean_shift else None,
                "volatility": str(trend.volatility) if trend.volatility else None,
            },
            "risk": {
                "level": risk.level.value,
                "score": str(risk.score),
                "factors": risk.factors,
            },
        }
        
        return json.dumps(data, indent=2)
    
    def _extract_key_findings(
        self,
        statistics: StatisticalSummary,
        trend: TrendAnalysis,
        risk: RiskAssessment,
    ) -> list[str]:
        """Extract key findings as bullet points."""
        findings = []
        
        # Pass rate finding
        if statistics.pass_rate >= Decimal("98"):
            findings.append(f"Excellent pass rate of {statistics.pass_rate}%")
        elif statistics.pass_rate >= Decimal("95"):
            findings.append(f"Good pass rate of {statistics.pass_rate}%")
        elif statistics.pass_rate >= Decimal("90"):
            findings.append(f"Pass rate of {statistics.pass_rate}% is below target")
        else:
            findings.append(f"Pass rate of {statistics.pass_rate}% requires immediate attention")
        
        # Capability finding
        if statistics.cpk is not None:
            if statistics.capability_status == CapabilityStatus.EXCELLENT:
                findings.append(f"Process capability is excellent (Cpk = {statistics.cpk})")
            elif statistics.capability_status == CapabilityStatus.CAPABLE:
                findings.append(f"Process is capable (Cpk = {statistics.cpk})")
            elif statistics.capability_status == CapabilityStatus.MARGINALLY_CAPABLE:
                findings.append(f"Process capability is marginal (Cpk = {statistics.cpk})")
            else:
                findings.append(f"Process is not capable (Cpk = {statistics.cpk})")
        
        # Trend finding
        if trend.direction != TrendDirection.INSUFFICIENT_DATA:
            findings.append(f"Trend analysis shows {trend.direction.value} pattern")
        
        # Risk finding
        if risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            findings.append(f"Risk level is {risk.level.value} - action required")
        
        return findings
    
    def _extract_action_items(self, recommendations: list[Recommendation]) -> list[str]:
        """Extract action items from recommendations."""
        return [
            f"[{r.priority.upper()}] {r.title}"
            for r in recommendations[:5]
        ]
    
    # ========================================================================
    # Multi-CTQ Summarization
    # ========================================================================
    
    def generate_multi_ctq_summary(
        self,
        specs: list[CTQSpec],
        measurements_by_ctq: dict[UUID, list[MeasurementData]],
        title: str = "Multi-CTQ Quality Summary",
        period: AnalysisPeriod = AnalysisPeriod.LAST_30_DAYS,
    ) -> MultiCTQSummary:
        """
        Generate summary across multiple CTQs.
        
        Args:
            specs: List of CTQ specifications
            measurements_by_ctq: Mapping of CTQ ID to measurements
            title: Summary title
            period: Analysis period
            
        Returns:
            MultiCTQSummary object
        """
        # Generate individual summaries
        ctq_summaries = []
        for spec in specs:
            measurements = measurements_by_ctq.get(spec.id, [])
            summary = self.generate_summary(
                spec=spec,
                measurements=measurements,
                summary_type=SummaryType.OVERVIEW,
                period=period,
            )
            ctq_summaries.append(summary)
        
        # Calculate aggregates
        total_measurements = sum(s.statistics.count for s in ctq_summaries)
        total_pass = sum(s.statistics.pass_count for s in ctq_summaries)
        
        overall_pass_rate = Decimal("0")
        if total_measurements > 0:
            overall_pass_rate = Decimal(str(
                (total_pass / total_measurements) * 100
            )).quantize(Decimal("0.01"))
        
        ctqs_at_risk = sum(
            1 for s in ctq_summaries
            if s.risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        )
        
        ctqs_not_capable = sum(
            1 for s in ctq_summaries
            if s.statistics.capability_status == CapabilityStatus.NOT_CAPABLE
        )
        
        # Collect top issues
        top_issues = []
        for s in ctq_summaries:
            if s.risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                top_issues.append(f"{s.ctq_name}: {s.risk.description[:100]}...")
        
        # Collect top recommendations (prioritized)
        all_recommendations = []
        for s in ctq_summaries:
            for r in s.recommendations:
                all_recommendations.append((s.ctq_name, r))
        
        # Sort and take top 5
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_recommendations.sort(key=lambda x: priority_order.get(x[1].priority, 4))
        top_recommendations = [r for _, r in all_recommendations[:5]]
        
        # Generate executive summary
        period_start, period_end = self._calculate_period(period, None, None)
        
        exec_summary = f"""
Multi-CTQ Quality Summary: {title}

Analysis Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}

Overview:
- Total CTQs Analyzed: {len(specs)}
- Total Measurements: {total_measurements}
- Overall Pass Rate: {overall_pass_rate}%
- CTQs at Risk: {ctqs_at_risk}
- CTQs Not Capable: {ctqs_not_capable}

{"⚠️ ATTENTION REQUIRED: " + str(ctqs_at_risk) + " CTQ(s) require immediate attention." if ctqs_at_risk > 0 else "✓ All CTQs are within acceptable risk levels."}
""".strip()
        
        # Create multi-summary
        multi_summary = MultiCTQSummary(
            title=title,
            period=period,
            period_start=period_start,
            period_end=period_end,
            total_ctqs=len(specs),
            total_measurements=total_measurements,
            overall_pass_rate=overall_pass_rate,
            ctqs_at_risk=ctqs_at_risk,
            ctqs_not_capable=ctqs_not_capable,
            ctq_summaries=ctq_summaries,
            top_issues=top_issues[:5],
            top_recommendations=top_recommendations,
            executive_summary=exec_summary,
            generated_at=datetime.utcnow(),
        )
        
        self._multi_summaries[multi_summary.id] = multi_summary
        
        return multi_summary
    
    # ========================================================================
    # Retrieval Methods
    # ========================================================================
    
    def get_summary(self, summary_id: UUID) -> Optional[CTQSummary]:
        """Get a stored summary by ID."""
        return self._summaries.get(summary_id)
    
    def get_multi_summary(self, summary_id: UUID) -> Optional[MultiCTQSummary]:
        """Get a stored multi-CTQ summary by ID."""
        return self._multi_summaries.get(summary_id)
    
    def list_summaries(
        self,
        ctq_id: Optional[UUID] = None,
        summary_type: Optional[SummaryType] = None,
        limit: int = 10,
    ) -> list[CTQSummary]:
        """List stored summaries with optional filtering."""
        summaries = list(self._summaries.values())
        
        if ctq_id:
            summaries = [s for s in summaries if s.ctq_id == ctq_id]
        
        if summary_type:
            summaries = [s for s in summaries if s.summary_type == summary_type]
        
        # Sort by generation time (newest first)
        summaries.sort(key=lambda s: s.generated_at, reverse=True)
        
        return summaries[:limit]
    
    def compare_periods(
        self,
        spec: CTQSpec,
        measurements: list[MeasurementData],
        period1: tuple[datetime, datetime],
        period2: tuple[datetime, datetime],
    ) -> dict[str, Any]:
        """
        Compare CTQ performance between two time periods.
        
        Args:
            spec: CTQ specification
            measurements: All available measurements
            period1: First period (start, end)
            period2: Second period (start, end)
            
        Returns:
            Comparison dictionary
        """
        # Filter measurements for each period
        period1_measurements = [
            m for m in measurements
            if period1[0] <= m.measured_at <= period1[1]
        ]
        period2_measurements = [
            m for m in measurements
            if period2[0] <= m.measured_at <= period2[1]
        ]
        
        # Calculate statistics for each period
        stats1 = self.calculate_statistics(period1_measurements, spec)
        stats2 = self.calculate_statistics(period2_measurements, spec)
        
        # Calculate changes
        pass_rate_change = Decimal("0")
        if stats1.pass_rate and stats2.pass_rate:
            pass_rate_change = stats2.pass_rate - stats1.pass_rate
        
        cpk_change = None
        if stats1.cpk is not None and stats2.cpk is not None:
            cpk_change = stats2.cpk - stats1.cpk
        
        # Determine overall assessment
        if pass_rate_change > Decimal("5") or (cpk_change and cpk_change > Decimal("0.2")):
            assessment = "improved"
        elif pass_rate_change < Decimal("-5") or (cpk_change and cpk_change < Decimal("-0.2")):
            assessment = "degraded"
        else:
            assessment = "stable"
        
        return {
            "period1": {
                "start": period1[0],
                "end": period1[1],
                "count": stats1.count,
                "pass_rate": stats1.pass_rate,
                "cpk": stats1.cpk,
                "capability": stats1.capability_status.value,
            },
            "period2": {
                "start": period2[0],
                "end": period2[1],
                "count": stats2.count,
                "pass_rate": stats2.pass_rate,
                "cpk": stats2.cpk,
                "capability": stats2.capability_status.value,
            },
            "changes": {
                "pass_rate_change": pass_rate_change,
                "cpk_change": cpk_change,
                "measurement_count_change": stats2.count - stats1.count,
            },
            "assessment": assessment,
        }
