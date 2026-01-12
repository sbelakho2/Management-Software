"""
Tests for AI CTQ Summarization Service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sensei.services.ai.ai_ctq_summarization import (
    # Enums
    SummaryType,
    AnalysisPeriod,
    RiskLevel,
    TrendDirection,
    CapabilityStatus,
    RecommendationType,
    OutputFormat,
    # Data Classes
    MeasurementData,
    CTQSpec,
    StatisticalSummary,
    TrendAnalysis,
    RiskAssessment,
    Recommendation,
    CTQSummary,
    MultiCTQSummary,
    # Service
    AICTQSummarizationService,
)


# ============================================================================
# Enum Tests
# ============================================================================

class TestSummaryType:
    """Tests for SummaryType enum."""
    
    def test_summary_type_values(self):
        """Test all summary type values."""
        assert SummaryType.OVERVIEW.value == "overview"
        assert SummaryType.DETAILED.value == "detailed"
        assert SummaryType.EXECUTIVE.value == "executive"
        assert SummaryType.TECHNICAL.value == "technical"
        assert SummaryType.AUDIT.value == "audit"
        assert SummaryType.TREND.value == "trend"
    
    def test_summary_type_count(self):
        """Test number of summary types."""
        assert len(SummaryType) == 6


class TestAnalysisPeriod:
    """Tests for AnalysisPeriod enum."""
    
    def test_analysis_period_values(self):
        """Test all analysis period values."""
        assert AnalysisPeriod.LAST_24_HOURS.value == "24h"
        assert AnalysisPeriod.LAST_7_DAYS.value == "7d"
        assert AnalysisPeriod.LAST_30_DAYS.value == "30d"
        assert AnalysisPeriod.LAST_90_DAYS.value == "90d"
        assert AnalysisPeriod.LAST_YEAR.value == "1y"
        assert AnalysisPeriod.ALL_TIME.value == "all"
        assert AnalysisPeriod.CUSTOM.value == "custom"
    
    def test_analysis_period_count(self):
        """Test number of periods."""
        assert len(AnalysisPeriod) == 7


class TestRiskLevel:
    """Tests for RiskLevel enum."""
    
    def test_risk_level_values(self):
        """Test all risk level values."""
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.NONE.value == "none"
    
    def test_risk_level_ordering(self):
        """Test risk levels are defined in severity order."""
        levels = list(RiskLevel)
        assert levels[0] == RiskLevel.CRITICAL
        # UNKNOWN is last as it's for cases where risk can't be determined
        assert RiskLevel.NONE in levels


class TestTrendDirection:
    """Tests for TrendDirection enum."""
    
    def test_trend_direction_values(self):
        """Test all trend direction values."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DEGRADING.value == "degrading"
        assert TrendDirection.VOLATILE.value == "volatile"
        assert TrendDirection.INSUFFICIENT_DATA.value == "insufficient_data"


class TestCapabilityStatus:
    """Tests for CapabilityStatus enum."""
    
    def test_capability_status_values(self):
        """Test all capability status values."""
        assert CapabilityStatus.EXCELLENT.value == "excellent"
        assert CapabilityStatus.CAPABLE.value == "capable"
        assert CapabilityStatus.MARGINALLY_CAPABLE.value == "marginally_capable"
        assert CapabilityStatus.NOT_CAPABLE.value == "not_capable"
        assert CapabilityStatus.UNKNOWN.value == "unknown"


class TestRecommendationType:
    """Tests for RecommendationType enum."""
    
    def test_recommendation_type_values(self):
        """Test all recommendation types."""
        assert RecommendationType.PROCESS_ADJUSTMENT.value == "process_adjustment"
        assert RecommendationType.EQUIPMENT_CALIBRATION.value == "equipment_calibration"
        assert RecommendationType.OPERATOR_TRAINING.value == "operator_training"
        assert RecommendationType.ROOT_CAUSE_ANALYSIS.value == "root_cause_analysis"
        assert RecommendationType.IMMEDIATE_ACTION.value == "immediate_action"
    
    def test_recommendation_type_count(self):
        """Test number of recommendation types."""
        assert len(RecommendationType) == 10


class TestOutputFormat:
    """Tests for OutputFormat enum."""
    
    def test_output_format_values(self):
        """Test all output formats."""
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.HTML.value == "html"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.JSON.value == "json"


# ============================================================================
# Data Class Tests
# ============================================================================

class TestMeasurementData:
    """Tests for MeasurementData dataclass."""
    
    def test_measurement_creation(self):
        """Test measurement data creation."""
        measurement = MeasurementData(
            id=uuid4(),
            value=Decimal("10.05"),
            measured_at=datetime.now(timezone.utc),
            result="pass",
        )
        
        assert measurement.value == Decimal("10.05")
        assert measurement.result == "pass"
    
    def test_measurement_optional_fields(self):
        """Test optional fields have defaults."""
        measurement = MeasurementData(
            id=uuid4(),
            value=Decimal("10.0"),
            measured_at=datetime.now(timezone.utc),
            result="pass",
        )
        
        assert measurement.batch_number is None
        assert measurement.serial_number is None
        assert measurement.operator_id is None
        assert measurement.deviation is None
        assert measurement.notes is None
    
    def test_measurement_with_all_fields(self):
        """Test measurement with all fields populated."""
        measurement = MeasurementData(
            id=uuid4(),
            value=Decimal("10.05"),
            measured_at=datetime.now(timezone.utc),
            result="fail",
            batch_number="BATCH-001",
            serial_number="SN-123",
            operator_id=uuid4(),
            deviation=Decimal("0.05"),
            notes="Slightly over spec",
        )
        
        assert measurement.batch_number == "BATCH-001"
        assert measurement.serial_number == "SN-123"
        assert measurement.deviation == Decimal("0.05")


class TestCTQSpec:
    """Tests for CTQSpec dataclass."""
    
    def test_ctq_spec_creation(self):
        """Test CTQ spec creation."""
        spec = CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Surface Roughness",
            category="surface",
            priority="critical",
        )
        
        assert spec.ctq_number == "CTQ-001"
        assert spec.name == "Surface Roughness"
        assert spec.priority == "critical"
    
    def test_ctq_spec_with_tolerances(self):
        """Test CTQ spec with tolerances."""
        spec = CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-002",
            name="Dimension A",
            category="dimensional",
            priority="major",
            nominal_value=Decimal("25.0"),
            upper_spec_limit=Decimal("25.1"),
            lower_spec_limit=Decimal("24.9"),
            unit_of_measure="mm",
        )
        
        assert spec.nominal_value == Decimal("25.0")
        assert spec.upper_spec_limit == Decimal("25.1")
        assert spec.lower_spec_limit == Decimal("24.9")
        assert spec.unit_of_measure == "mm"


class TestStatisticalSummary:
    """Tests for StatisticalSummary dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        summary = StatisticalSummary()
        
        assert summary.count == 0
        assert summary.mean is None
        assert summary.std_dev is None
        assert summary.pass_count == 0
        assert summary.fail_count == 0
        assert summary.pass_rate == Decimal("0")
        assert summary.capability_status == CapabilityStatus.UNKNOWN
    
    def test_with_data(self):
        """Test with populated data."""
        summary = StatisticalSummary(
            count=100,
            mean=Decimal("25.0"),
            std_dev=Decimal("0.02"),
            pass_count=98,
            fail_count=2,
            pass_rate=Decimal("98.0"),
            cpk=Decimal("1.67"),
            capability_status=CapabilityStatus.CAPABLE,
        )
        
        assert summary.count == 100
        assert summary.cpk == Decimal("1.67")
        assert summary.capability_status == CapabilityStatus.CAPABLE


class TestTrendAnalysis:
    """Tests for TrendAnalysis dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        analysis = TrendAnalysis()
        
        assert analysis.direction == TrendDirection.INSUFFICIENT_DATA
        assert analysis.slope is None
        assert analysis.data_points == 0
        assert analysis.description == ""
    
    def test_with_trend_data(self):
        """Test with trend data."""
        analysis = TrendAnalysis(
            direction=TrendDirection.STABLE,
            slope=Decimal("0.001"),
            r_squared=Decimal("0.85"),
            period_mean=Decimal("25.0"),
            volatility=Decimal("5.5"),
            data_points=50,
            description="Process is stable",
        )
        
        assert analysis.direction == TrendDirection.STABLE
        assert analysis.volatility == Decimal("5.5")


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        risk = RiskAssessment()
        
        assert risk.level == RiskLevel.UNKNOWN
        assert risk.score == Decimal("0")
        assert risk.factors == []
        assert risk.immediate_action_required is False
    
    def test_high_risk(self):
        """Test high risk assessment."""
        risk = RiskAssessment(
            level=RiskLevel.HIGH,
            score=Decimal("65"),
            factors=["Low pass rate", "Degrading trend"],
            immediate_action_required=True,
        )
        
        assert risk.level == RiskLevel.HIGH
        assert risk.immediate_action_required is True


class TestRecommendation:
    """Tests for Recommendation dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        rec = Recommendation()
        
        assert rec.type == RecommendationType.PROCESS_ADJUSTMENT
        assert rec.priority == "medium"
        assert rec.confidence == Decimal("0.8")
    
    def test_custom_recommendation(self):
        """Test custom recommendation."""
        rec = Recommendation(
            type=RecommendationType.ROOT_CAUSE_ANALYSIS,
            priority="critical",
            title="Investigate Process Drift",
            description="Root cause analysis required",
            expected_impact="High",
            effort_level="high",
            confidence=Decimal("0.9"),
        )
        
        assert rec.priority == "critical"
        assert rec.effort_level == "high"


# ============================================================================
# Service Tests - Statistical Analysis
# ============================================================================

class TestStatisticalAnalysis:
    """Tests for statistical analysis functionality."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test CTQ spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
            nominal_value=Decimal("10.0"),
            upper_spec_limit=Decimal("10.1"),
            lower_spec_limit=Decimal("9.9"),
            unit_of_measure="mm",
        )
    
    def test_empty_measurements(self, service, spec):
        """Test with no measurements."""
        stats = service.calculate_statistics([], spec)
        
        assert stats.count == 0
        assert stats.mean is None
        assert stats.capability_status == CapabilityStatus.UNKNOWN
    
    def test_single_measurement(self, service, spec):
        """Test with single measurement."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc),
                result="pass",
            )
        ]
        
        stats = service.calculate_statistics(measurements, spec)
        
        assert stats.count == 1
        assert stats.pass_count == 1
        assert stats.pass_rate == Decimal("100.00")
    
    def test_multiple_measurements(self, service, spec):
        """Test with multiple measurements."""
        measurements = [
            MeasurementData(id=uuid4(), value=Decimal("10.0"), measured_at=datetime.now(timezone.utc), result="pass"),
            MeasurementData(id=uuid4(), value=Decimal("10.02"), measured_at=datetime.now(timezone.utc), result="pass"),
            MeasurementData(id=uuid4(), value=Decimal("9.98"), measured_at=datetime.now(timezone.utc), result="pass"),
            MeasurementData(id=uuid4(), value=Decimal("10.01"), measured_at=datetime.now(timezone.utc), result="pass"),
            MeasurementData(id=uuid4(), value=Decimal("9.99"), measured_at=datetime.now(timezone.utc), result="pass"),
        ]
        
        stats = service.calculate_statistics(measurements, spec)
        
        assert stats.count == 5
        assert stats.mean is not None
        assert stats.std_dev is not None
        assert stats.min_value == Decimal("9.980000")
        assert stats.max_value == Decimal("10.020000")
    
    def test_pass_fail_counting(self, service, spec):
        """Test pass/fail counting."""
        measurements = [
            MeasurementData(id=uuid4(), value=Decimal("10.0"), measured_at=datetime.now(timezone.utc), result="pass"),
            MeasurementData(id=uuid4(), value=Decimal("10.2"), measured_at=datetime.now(timezone.utc), result="fail"),
            MeasurementData(id=uuid4(), value=Decimal("10.05"), measured_at=datetime.now(timezone.utc), result="marginal"),
            MeasurementData(id=uuid4(), value=Decimal("10.01"), measured_at=datetime.now(timezone.utc), result="pass"),
        ]
        
        stats = service.calculate_statistics(measurements, spec)
        
        assert stats.pass_count == 2
        assert stats.fail_count == 1
        assert stats.marginal_count == 1
        assert stats.pass_rate == Decimal("50.00")
    
    def test_capability_calculation(self, service, spec):
        """Test Cpk calculation with good data."""
        # Create tight distribution around nominal
        measurements = []
        for i in range(50):
            value = Decimal("10.0") + Decimal(str(i * 0.001 - 0.025))
            measurements.append(MeasurementData(
                id=uuid4(),
                value=value,
                measured_at=datetime.now(timezone.utc),
                result="pass",
            ))
        
        stats = service.calculate_statistics(measurements, spec)
        
        assert stats.cpk is not None
        assert stats.capability_status != CapabilityStatus.UNKNOWN


class TestCapabilityStatusDetermination:
    """Tests for capability status determination."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    def test_excellent_capability(self, service):
        """Test excellent capability (Cpk >= 2.0)."""
        status = service._determine_capability_status(Decimal("2.5"))
        assert status == CapabilityStatus.EXCELLENT
    
    def test_capable(self, service):
        """Test capable (1.33 <= Cpk < 2.0)."""
        status = service._determine_capability_status(Decimal("1.5"))
        assert status == CapabilityStatus.CAPABLE
    
    def test_marginally_capable(self, service):
        """Test marginally capable (1.0 <= Cpk < 1.33)."""
        status = service._determine_capability_status(Decimal("1.1"))
        assert status == CapabilityStatus.MARGINALLY_CAPABLE
    
    def test_not_capable(self, service):
        """Test not capable (Cpk < 1.0)."""
        status = service._determine_capability_status(Decimal("0.8"))
        assert status == CapabilityStatus.NOT_CAPABLE
    
    def test_unknown_capability(self, service):
        """Test unknown capability (None)."""
        status = service._determine_capability_status(None)
        assert status == CapabilityStatus.UNKNOWN


# ============================================================================
# Service Tests - Trend Analysis
# ============================================================================

class TestTrendAnalysis:
    """Tests for trend analysis functionality."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test CTQ spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
            nominal_value=Decimal("10.0"),
            upper_spec_limit=Decimal("10.1"),
            lower_spec_limit=Decimal("9.9"),
        )
    
    def test_insufficient_data(self, service, spec):
        """Test with insufficient data for trend."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc),
                result="pass",
            )
        ]
        
        trend = service.analyze_trend(measurements, spec)
        
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA
        assert "insufficient" in trend.description.lower()
    
    def test_stable_trend(self, service, spec):
        """Test detection of stable trend."""
        base_time = datetime.now(timezone.utc)
        measurements = []
        
        # Create stable data
        for i in range(20):
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.0") + Decimal(str((i % 3 - 1) * 0.01)),
                measured_at=base_time - timedelta(days=i),
                result="pass",
            ))
        
        trend = service.analyze_trend(measurements, spec)
        
        assert trend.data_points == 20
        assert trend.period_mean is not None
    
    def test_volatility_calculation(self, service, spec):
        """Test volatility calculation."""
        base_time = datetime.now(timezone.utc)
        measurements = []
        
        # Create volatile data
        for i in range(15):
            value = Decimal("10.0") + Decimal(str((i % 2 - 0.5) * 0.1))
            measurements.append(MeasurementData(
                id=uuid4(),
                value=value,
                measured_at=base_time - timedelta(days=i),
                result="pass",
            ))
        
        trend = service.analyze_trend(measurements, spec)
        
        assert trend.volatility is not None
    
    def test_mean_shift_calculation(self, service, spec):
        """Test mean shift calculation."""
        base_time = datetime.now(timezone.utc)
        measurements = []
        
        # First half at 10.0, second half at 10.05
        for i in range(10):
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=base_time - timedelta(days=20-i),
                result="pass",
            ))
        
        for i in range(10):
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.05"),
                measured_at=base_time - timedelta(days=10-i),
                result="pass",
            ))
        
        trend = service.analyze_trend(measurements, spec)
        
        assert trend.mean_shift is not None
        assert trend.prior_period_mean is not None


# ============================================================================
# Service Tests - Risk Assessment
# ============================================================================

class TestRiskAssessment:
    """Tests for risk assessment functionality."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def good_stats(self):
        """Create good statistics."""
        return StatisticalSummary(
            count=100,
            pass_rate=Decimal("99"),
            cpk=Decimal("2.0"),
            capability_status=CapabilityStatus.EXCELLENT,
        )
    
    @pytest.fixture
    def poor_stats(self):
        """Create poor statistics."""
        return StatisticalSummary(
            count=100,
            pass_rate=Decimal("80"),
            cpk=Decimal("0.8"),
            capability_status=CapabilityStatus.NOT_CAPABLE,
        )
    
    @pytest.fixture
    def stable_trend(self):
        """Create stable trend."""
        return TrendAnalysis(direction=TrendDirection.STABLE)
    
    @pytest.fixture
    def degrading_trend(self):
        """Create degrading trend."""
        return TrendAnalysis(direction=TrendDirection.DEGRADING)
    
    @pytest.fixture
    def critical_spec(self):
        """Create critical priority spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Critical CTQ",
            category="dimensional",
            priority="critical",
        )
    
    @pytest.fixture
    def minor_spec(self):
        """Create minor priority spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-002",
            name="Minor CTQ",
            category="dimensional",
            priority="minor",
        )
    
    def test_low_risk_assessment(self, service, good_stats, stable_trend, minor_spec):
        """Test low risk assessment."""
        risk = service.assess_risk(good_stats, stable_trend, minor_spec)
        
        assert risk.level in [RiskLevel.NONE, RiskLevel.LOW]
        assert risk.immediate_action_required is False
    
    def test_high_risk_assessment(self, service, poor_stats, degrading_trend, critical_spec):
        """Test high risk assessment."""
        risk = service.assess_risk(poor_stats, degrading_trend, critical_spec)
        
        assert risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        assert risk.immediate_action_required is True
        assert len(risk.factors) > 0
    
    def test_risk_factors_included(self, service, poor_stats, stable_trend, minor_spec):
        """Test risk factors are included."""
        risk = service.assess_risk(poor_stats, stable_trend, minor_spec)
        
        # Should have factors for low pass rate and not capable
        assert any("pass rate" in f.lower() for f in risk.factors)
        assert any("capable" in f.lower() for f in risk.factors)
    
    def test_risk_score_calculation(self, service, poor_stats, degrading_trend, critical_spec):
        """Test risk score is calculated."""
        risk = service.assess_risk(poor_stats, degrading_trend, critical_spec)
        
        assert risk.score > Decimal("0")
        assert risk.score <= Decimal("100")
    
    def test_risk_description_generated(self, service, good_stats, stable_trend, minor_spec):
        """Test risk description is generated."""
        risk = service.assess_risk(good_stats, stable_trend, minor_spec)
        
        assert risk.description != ""


# ============================================================================
# Service Tests - Recommendations
# ============================================================================

class TestRecommendations:
    """Tests for recommendation generation."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
        )
    
    def test_not_capable_recommendations(self, service, spec):
        """Test recommendations for not capable process."""
        stats = StatisticalSummary(
            count=50,
            cpk=Decimal("0.7"),
            capability_status=CapabilityStatus.NOT_CAPABLE,
            pass_rate=Decimal("85"),
        )
        trend = TrendAnalysis(direction=TrendDirection.STABLE)
        risk = RiskAssessment(level=RiskLevel.HIGH)
        
        recs = service.generate_recommendations(stats, trend, risk, spec)
        
        assert len(recs) > 0
        assert any(r.type == RecommendationType.ROOT_CAUSE_ANALYSIS for r in recs)
    
    def test_degrading_trend_recommendations(self, service, spec):
        """Test recommendations for degrading trend."""
        stats = StatisticalSummary(
            count=50,
            cpk=Decimal("1.2"),
            capability_status=CapabilityStatus.MARGINALLY_CAPABLE,
            pass_rate=Decimal("92"),
        )
        trend = TrendAnalysis(direction=TrendDirection.DEGRADING)
        risk = RiskAssessment(level=RiskLevel.MEDIUM)
        
        recs = service.generate_recommendations(stats, trend, risk, spec)
        
        assert any(r.type == RecommendationType.EQUIPMENT_CALIBRATION for r in recs)
    
    def test_volatile_trend_recommendations(self, service, spec):
        """Test recommendations for volatile trend."""
        stats = StatisticalSummary(
            count=50,
            cpk=Decimal("1.1"),
            capability_status=CapabilityStatus.MARGINALLY_CAPABLE,
            pass_rate=Decimal("90"),
        )
        trend = TrendAnalysis(direction=TrendDirection.VOLATILE)
        risk = RiskAssessment(level=RiskLevel.MEDIUM)
        
        recs = service.generate_recommendations(stats, trend, risk, spec)
        
        assert any(r.type == RecommendationType.MATERIAL_REVIEW for r in recs)
        assert any(r.type == RecommendationType.OPERATOR_TRAINING for r in recs)
    
    def test_insufficient_data_recommendations(self, service, spec):
        """Test recommendations for insufficient data."""
        stats = StatisticalSummary(
            count=10,
            pass_rate=Decimal("100"),
        )
        trend = TrendAnalysis(direction=TrendDirection.INSUFFICIENT_DATA)
        risk = RiskAssessment(level=RiskLevel.LOW)
        
        recs = service.generate_recommendations(stats, trend, risk, spec)
        
        assert any(r.type == RecommendationType.SAMPLE_SIZE_INCREASE for r in recs)
    
    def test_critical_ctq_recommendations(self, service):
        """Test recommendations for critical CTQ at risk."""
        spec = CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Critical CTQ",
            category="dimensional",
            priority="critical",
        )
        stats = StatisticalSummary(
            count=50,
            cpk=Decimal("0.9"),
            capability_status=CapabilityStatus.NOT_CAPABLE,
            pass_rate=Decimal("88"),
        )
        trend = TrendAnalysis(direction=TrendDirection.DEGRADING)
        risk = RiskAssessment(level=RiskLevel.CRITICAL)
        
        recs = service.generate_recommendations(stats, trend, risk, spec)
        
        # Should have immediate action recommendation first
        assert recs[0].type == RecommendationType.IMMEDIATE_ACTION
        assert recs[0].priority == "critical"
    
    def test_recommendations_sorted_by_priority(self, service, spec):
        """Test recommendations are sorted by priority."""
        stats = StatisticalSummary(
            count=50,
            cpk=Decimal("0.8"),
            capability_status=CapabilityStatus.NOT_CAPABLE,
            pass_rate=Decimal("85"),
        )
        trend = TrendAnalysis(direction=TrendDirection.DEGRADING)
        risk = RiskAssessment(level=RiskLevel.HIGH)
        
        recs = service.generate_recommendations(stats, trend, risk, spec)
        
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        priorities = [priority_order.get(r.priority, 4) for r in recs]
        assert priorities == sorted(priorities)


# ============================================================================
# Service Tests - Summary Generation
# ============================================================================

class TestSummaryGeneration:
    """Tests for summary generation."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Surface Roughness",
            category="surface",
            priority="major",
            nominal_value=Decimal("3.2"),
            upper_spec_limit=Decimal("3.5"),
            lower_spec_limit=Decimal("2.9"),
            unit_of_measure="μm",
        )
    
    @pytest.fixture
    def measurements(self):
        """Create test measurements."""
        base_time = datetime.now(timezone.utc)
        measurements = []
        
        for i in range(50):
            value = Decimal("3.2") + Decimal(str((i % 5 - 2) * 0.05))
            measurements.append(MeasurementData(
                id=uuid4(),
                value=value,
                measured_at=base_time - timedelta(days=i),
                result="pass" if Decimal("2.9") <= value <= Decimal("3.5") else "fail",
            ))
        
        return measurements
    
    def test_generate_summary(self, service, spec, measurements):
        """Test summary generation."""
        summary = service.generate_summary(
            spec=spec,
            measurements=measurements,
            summary_type=SummaryType.OVERVIEW,
            period=AnalysisPeriod.LAST_90_DAYS,
        )
        
        assert summary.ctq_number == "CTQ-001"
        assert summary.ctq_name == "Surface Roughness"
        assert summary.statistics.count == 50
    
    def test_summary_contains_all_components(self, service, spec, measurements):
        """Test summary contains all components."""
        summary = service.generate_summary(spec, measurements)
        
        assert summary.statistics is not None
        assert summary.trend is not None
        assert summary.risk is not None
        assert summary.recommendations is not None
        assert summary.executive_summary != ""
        assert summary.detailed_analysis != ""
        assert len(summary.key_findings) > 0
        assert len(summary.action_items) >= 0
    
    def test_summary_stored(self, service, spec, measurements):
        """Test summary is stored for retrieval."""
        summary = service.generate_summary(spec, measurements)
        
        retrieved = service.get_summary(summary.id)
        assert retrieved is not None
        assert retrieved.id == summary.id
    
    def test_generation_time_recorded(self, service, spec, measurements):
        """Test generation time is recorded."""
        summary = service.generate_summary(spec, measurements)
        
        assert summary.generation_time_ms >= 0
        assert summary.generated_at is not None
    
    def test_period_filtering(self, service, spec):
        """Test measurements are filtered by period."""
        base_time = datetime.now(timezone.utc)
        
        # Create measurements over 60 days
        measurements = []
        for i in range(60):
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("3.2"),
                measured_at=base_time - timedelta(days=i),
                result="pass",
            ))
        
        summary = service.generate_summary(
            spec=spec,
            measurements=measurements,
            period=AnalysisPeriod.LAST_30_DAYS,
        )
        
        assert summary.statistics.count == 30
    
    def test_custom_period(self, service, spec, measurements):
        """Test custom period."""
        custom_start = datetime.now(timezone.utc) - timedelta(days=20)
        custom_end = datetime.now(timezone.utc) - timedelta(days=10)
        
        summary = service.generate_summary(
            spec=spec,
            measurements=measurements,
            period=AnalysisPeriod.CUSTOM,
            custom_start=custom_start,
            custom_end=custom_end,
        )
        
        assert summary.period_start == custom_start
        assert summary.period_end == custom_end
    
    def test_html_output_format(self, service, spec, measurements):
        """Test HTML output format."""
        summary = service.generate_summary(
            spec=spec,
            measurements=measurements,
            output_format=OutputFormat.HTML,
        )
        
        assert "<h" in summary.detailed_analysis or "<p>" in summary.detailed_analysis
    
    def test_json_output_format(self, service, spec, measurements):
        """Test JSON output format."""
        summary = service.generate_summary(
            spec=spec,
            measurements=measurements,
            output_format=OutputFormat.JSON,
        )
        
        # Should be valid JSON
        import json
        data = json.loads(summary.detailed_analysis)
        assert "statistics" in data
        assert "trend" in data
        assert "risk" in data


class TestExecutiveSummary:
    """Tests for executive summary generation."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
            nominal_value=Decimal("10.0"),
            upper_spec_limit=Decimal("10.1"),
            lower_spec_limit=Decimal("9.9"),
        )
    
    def test_good_performance_summary(self, service, spec):
        """Test executive summary for good performance."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="pass",
            )
            for i in range(50)
        ]
        
        summary = service.generate_summary(spec, measurements)
        
        assert "Test CTQ" in summary.executive_summary
        assert "CTQ-001" in summary.executive_summary
    
    def test_insufficient_data_summary(self, service, spec):
        """Test executive summary for insufficient data."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc),
                result="pass",
            )
        ]
        
        summary = service.generate_summary(spec, measurements)
        
        assert "insufficient" in summary.executive_summary.lower()


# ============================================================================
# Service Tests - Multi-CTQ Summary
# ============================================================================

class TestMultiCTQSummary:
    """Tests for multi-CTQ summary generation."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def specs(self):
        """Create multiple CTQ specs."""
        return [
            CTQSpec(
                id=uuid4(),
                ctq_number=f"CTQ-00{i}",
                name=f"Test CTQ {i}",
                category="dimensional",
                priority="major" if i % 2 == 0 else "minor",
                nominal_value=Decimal("10.0"),
                upper_spec_limit=Decimal("10.1"),
                lower_spec_limit=Decimal("9.9"),
            )
            for i in range(1, 6)
        ]
    
    @pytest.fixture
    def measurements_by_ctq(self, specs):
        """Create measurements for each CTQ."""
        measurements = {}
        base_time = datetime.now(timezone.utc)
        
        for i, spec in enumerate(specs):
            measurements[spec.id] = [
                MeasurementData(
                    id=uuid4(),
                    value=Decimal("10.0") + Decimal(str((j % 3 - 1) * 0.02)),
                    measured_at=base_time - timedelta(days=j),
                    result="pass",
                )
                for j in range(30)
            ]
        
        return measurements
    
    def test_multi_summary_generation(self, service, specs, measurements_by_ctq):
        """Test multi-CTQ summary generation."""
        summary = service.generate_multi_ctq_summary(
            specs=specs,
            measurements_by_ctq=measurements_by_ctq,
            title="Quality Report",
        )
        
        assert summary.title == "Quality Report"
        assert summary.total_ctqs == 5
        assert summary.total_measurements == 150  # 5 * 30
    
    def test_multi_summary_aggregates(self, service, specs, measurements_by_ctq):
        """Test multi-CTQ summary aggregates."""
        summary = service.generate_multi_ctq_summary(
            specs=specs,
            measurements_by_ctq=measurements_by_ctq,
        )
        
        assert summary.overall_pass_rate is not None
        assert summary.ctqs_at_risk >= 0
        assert summary.ctqs_not_capable >= 0
    
    def test_multi_summary_contains_individual(self, service, specs, measurements_by_ctq):
        """Test multi-CTQ summary contains individual summaries."""
        summary = service.generate_multi_ctq_summary(
            specs=specs,
            measurements_by_ctq=measurements_by_ctq,
        )
        
        assert len(summary.ctq_summaries) == 5
        for ctq_summary in summary.ctq_summaries:
            assert ctq_summary.statistics.count == 30
    
    def test_multi_summary_executive(self, service, specs, measurements_by_ctq):
        """Test multi-CTQ summary has executive summary."""
        summary = service.generate_multi_ctq_summary(
            specs=specs,
            measurements_by_ctq=measurements_by_ctq,
            title="Monthly Quality Report",
        )
        
        assert "Monthly Quality Report" in summary.executive_summary
        assert "Total CTQs Analyzed" in summary.executive_summary
    
    def test_multi_summary_stored(self, service, specs, measurements_by_ctq):
        """Test multi-CTQ summary is stored."""
        summary = service.generate_multi_ctq_summary(
            specs=specs,
            measurements_by_ctq=measurements_by_ctq,
        )
        
        retrieved = service.get_multi_summary(summary.id)
        assert retrieved is not None
        assert retrieved.id == summary.id


# ============================================================================
# Service Tests - Retrieval and Comparison
# ============================================================================

class TestRetrieval:
    """Tests for summary retrieval."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
        )
    
    def test_list_summaries(self, service, spec):
        """Test listing summaries."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="pass",
            )
            for i in range(20)
        ]
        
        # Generate multiple summaries
        service.generate_summary(spec, measurements, SummaryType.OVERVIEW)
        service.generate_summary(spec, measurements, SummaryType.DETAILED)
        
        summaries = service.list_summaries(limit=10)
        assert len(summaries) == 2
    
    def test_list_summaries_by_ctq(self, service, spec):
        """Test filtering summaries by CTQ."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc),
                result="pass",
            )
        ]
        
        service.generate_summary(spec, measurements)
        
        summaries = service.list_summaries(ctq_id=spec.id)
        assert all(s.ctq_id == spec.id for s in summaries)
    
    def test_list_summaries_by_type(self, service, spec):
        """Test filtering summaries by type."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc),
                result="pass",
            )
        ]
        
        service.generate_summary(spec, measurements, SummaryType.OVERVIEW)
        service.generate_summary(spec, measurements, SummaryType.DETAILED)
        
        summaries = service.list_summaries(summary_type=SummaryType.OVERVIEW)
        assert all(s.summary_type == SummaryType.OVERVIEW for s in summaries)


class TestPeriodComparison:
    """Tests for period comparison."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
            nominal_value=Decimal("10.0"),
            upper_spec_limit=Decimal("10.1"),
            lower_spec_limit=Decimal("9.9"),
        )
    
    def test_compare_periods(self, service, spec):
        """Test period comparison."""
        now = datetime.now(timezone.utc)
        
        # Create measurements for two periods
        measurements = []
        
        # Period 1: 60-31 days ago (all pass) - exclusive boundaries
        for i in range(30):
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=now - timedelta(days=59-i),  # days 59 to 30
                result="pass",
            ))
        
        # Period 2: 29-0 days ago (mostly pass)
        for i in range(30):
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=now - timedelta(days=29-i),  # days 29 to 0
                result="pass",
            ))
        
        period1 = (now - timedelta(days=60), now - timedelta(days=30))
        period2 = (now - timedelta(days=29), now)
        
        comparison = service.compare_periods(spec, measurements, period1, period2)
        
        # Both periods should have measurements
        assert comparison["period1"]["count"] >= 1
        assert comparison["period2"]["count"] >= 1
        assert "assessment" in comparison
    
    def test_comparison_assessment(self, service, spec):
        """Test comparison assessment."""
        now = datetime.now(timezone.utc)
        
        measurements = []
        
        # Period 1: 80% pass rate
        for i in range(100):
            result = "pass" if i < 80 else "fail"
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.0") if result == "pass" else Decimal("10.2"),
                measured_at=now - timedelta(days=60) + timedelta(hours=i),
                result=result,
            ))
        
        # Period 2: 95% pass rate
        for i in range(100):
            result = "pass" if i < 95 else "fail"
            measurements.append(MeasurementData(
                id=uuid4(),
                value=Decimal("10.0") if result == "pass" else Decimal("10.2"),
                measured_at=now - timedelta(days=30) + timedelta(hours=i),
                result=result,
            ))
        
        period1 = (now - timedelta(days=60), now - timedelta(days=30))
        period2 = (now - timedelta(days=30), now)
        
        comparison = service.compare_periods(spec, measurements, period1, period2)
        
        assert comparison["changes"]["pass_rate_change"] > 0
        assert comparison["assessment"] == "improved"


# ============================================================================
# Service Tests - Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return AICTQSummarizationService()
    
    @pytest.fixture
    def spec(self):
        """Create test spec."""
        return CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
            nominal_value=Decimal("10.0"),
            upper_spec_limit=Decimal("10.1"),
            lower_spec_limit=Decimal("9.9"),
        )
    
    def test_all_pass_measurements(self, service, spec):
        """Test with all passing measurements."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="pass",
            )
            for i in range(50)
        ]
        
        summary = service.generate_summary(spec, measurements)
        
        assert summary.statistics.pass_rate == Decimal("100.00")
        assert summary.statistics.fail_count == 0
    
    def test_all_fail_measurements(self, service, spec):
        """Test with all failing measurements."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.5"),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="fail",
            )
            for i in range(50)
        ]
        
        summary = service.generate_summary(spec, measurements)
        
        assert summary.statistics.pass_rate == Decimal("0.00")
        assert summary.statistics.pass_count == 0
        # Risk should be elevated due to 0% pass rate
        assert summary.risk.level != RiskLevel.NONE
        assert summary.risk.score > Decimal("0")
    
    def test_identical_values(self, service, spec):
        """Test with all identical values (zero variance)."""
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="pass",
            )
            for i in range(50)
        ]
        
        stats = service.calculate_statistics(measurements, spec)
        
        assert stats.mean == Decimal("10.000000")
        assert stats.std_dev == Decimal("0")
    
    def test_spec_without_limits(self, service):
        """Test with spec without limits."""
        spec = CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Test CTQ",
            category="dimensional",
            priority="major",
            # No limits defined
        )
        
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("10.0"),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="pass",
            )
            for i in range(20)
        ]
        
        stats = service.calculate_statistics(measurements, spec)
        
        # Cpk cannot be calculated without limits
        assert stats.cpk is None
        assert stats.capability_status == CapabilityStatus.UNKNOWN
    
    def test_negative_values(self, service):
        """Test with negative measurement values."""
        spec = CTQSpec(
            id=uuid4(),
            ctq_number="CTQ-001",
            name="Temperature Delta",
            category="environmental",
            priority="major",
            nominal_value=Decimal("-5.0"),
            upper_spec_limit=Decimal("-2.0"),
            lower_spec_limit=Decimal("-8.0"),
        )
        
        measurements = [
            MeasurementData(
                id=uuid4(),
                value=Decimal("-5.0") + Decimal(str((i % 5 - 2) * 0.5)),
                measured_at=datetime.now(timezone.utc) - timedelta(days=i),
                result="pass",
            )
            for i in range(30)
        ]
        
        stats = service.calculate_statistics(measurements, spec)
        
        assert stats.mean is not None
        assert stats.mean < 0


# ============================================================================
# Service Tests - Configuration
# ============================================================================

class TestServiceConfiguration:
    """Tests for service configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        service = AICTQSummarizationService()
        
        assert service.min_samples_for_stats == 2
        assert service.min_samples_for_trend == 10
        assert service.min_samples_for_capability == 30
        assert service.cpk_excellent_threshold == Decimal("2.0")
    
    def test_custom_configuration(self):
        """Test custom configuration."""
        service = AICTQSummarizationService(
            min_samples_for_stats=5,
            min_samples_for_trend=20,
            min_samples_for_capability=50,
            cpk_excellent_threshold=Decimal("2.5"),
        )
        
        assert service.min_samples_for_stats == 5
        assert service.min_samples_for_trend == 20
        assert service.min_samples_for_capability == 50
        assert service.cpk_excellent_threshold == Decimal("2.5")
    
    def test_custom_cpk_thresholds(self):
        """Test custom Cpk thresholds affect capability status."""
        service = AICTQSummarizationService(
            cpk_excellent_threshold=Decimal("3.0"),
            cpk_capable_threshold=Decimal("2.0"),
            cpk_marginal_threshold=Decimal("1.5"),
        )
        
        # 2.5 would be EXCELLENT with defaults, but CAPABLE with custom
        status = service._determine_capability_status(Decimal("2.5"))
        assert status == CapabilityStatus.CAPABLE
