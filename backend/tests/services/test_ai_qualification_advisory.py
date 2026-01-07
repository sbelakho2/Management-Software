"""
Tests for AI Qualification Advisory Service.

Comprehensive tests covering:
- All enums and data classes
- Scoring recommendations
- Risk assessment
- Gap analysis
- Decision support
- Benchmark comparison
- Full advisory generation
- Edge cases and configuration
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.ai_qualification_advisory import (
    # Enums
    AdvisoryType,
    DecisionRecommendation,
    ConfidenceLevel,
    RiskCategory,
    RiskSeverity,
    GapSeverity,
    ActionPriority,
    ScoringRationale,
    # Data Classes
    CriterionData,
    ScoreData,
    QualificationData,
    ScoringRecommendation,
    IdentifiedRisk,
    Gap,
    RecommendedAction,
    DecisionSupport,
    BenchmarkResult,
    QualificationAdvisory,
    # Service
    AIQualificationAdvisoryService,
    # Constants
    CATEGORY_BENCHMARKS,
    RISK_FACTORS,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def service():
    """Create advisory service instance."""
    return AIQualificationAdvisoryService()


@pytest.fixture
def sample_criteria():
    """Create sample criteria."""
    return [
        CriterionData(
            id=uuid4(),
            code="TECH-001",
            name="Technical Capability",
            category="technical",
            max_score=Decimal("10.0"),
            weight=Decimal("1.5"),
            is_blocker=True,
            blocker_threshold=Decimal("3.0"),
        ),
        CriterionData(
            id=uuid4(),
            code="COMM-001",
            name="Commercial Viability",
            category="commercial",
            max_score=Decimal("10.0"),
            weight=Decimal("1.0"),
            is_blocker=False,
        ),
        CriterionData(
            id=uuid4(),
            code="CAP-001",
            name="Capacity Availability",
            category="capacity",
            max_score=Decimal("10.0"),
            weight=Decimal("1.2"),
            is_blocker=True,
            blocker_threshold=Decimal("4.0"),
        ),
        CriterionData(
            id=uuid4(),
            code="QUAL-001",
            name="Quality Systems",
            category="quality",
            max_score=Decimal("10.0"),
            weight=Decimal("1.3"),
            is_blocker=True,
            blocker_threshold=Decimal("5.0"),
        ),
        CriterionData(
            id=uuid4(),
            code="STRAT-001",
            name="Strategic Fit",
            category="strategic",
            max_score=Decimal("10.0"),
            weight=Decimal("0.8"),
            is_blocker=False,
        ),
    ]


@pytest.fixture
def sample_scores(sample_criteria):
    """Create sample scores."""
    return [
        ScoreData(
            criterion_id=sample_criteria[0].id,
            criterion_code="TECH-001",
            score=Decimal("8.0"),
            max_score=Decimal("10.0"),
            weight=Decimal("1.5"),
        ),
        ScoreData(
            criterion_id=sample_criteria[1].id,
            criterion_code="COMM-001",
            score=Decimal("7.0"),
            max_score=Decimal("10.0"),
            weight=Decimal("1.0"),
        ),
        ScoreData(
            criterion_id=sample_criteria[2].id,
            criterion_code="CAP-001",
            score=Decimal("6.5"),
            max_score=Decimal("10.0"),
            weight=Decimal("1.2"),
        ),
        ScoreData(
            criterion_id=sample_criteria[3].id,
            criterion_code="QUAL-001",
            score=Decimal("9.0"),
            max_score=Decimal("10.0"),
            weight=Decimal("1.3"),
        ),
        ScoreData(
            criterion_id=sample_criteria[4].id,
            criterion_code="STRAT-001",
            score=Decimal("7.5"),
            max_score=Decimal("10.0"),
            weight=Decimal("0.8"),
        ),
    ]


@pytest.fixture
def sample_qualification(sample_scores):
    """Create sample qualification."""
    return QualificationData(
        id=uuid4(),
        rfq_id=uuid4(),
        scores=sample_scores,
        total_score=Decimal("76.5"),
        percentage_score=Decimal("76.5"),
        result="pending",
        has_blockers=False,
        customer_name="Acme Corp",
        part_description="Precision Widget Assembly",
        estimated_value=Decimal("250000"),
        process_types=["machining", "assembly"],
    )


@pytest.fixture
def sample_rfq_context():
    """Create sample RFQ context."""
    return {
        "existing_customer": True,
        "part_complexity": "medium",
        "annual_volume": 5000,
        "familiar_process": True,
        "new_process_required": False,
        "aggressive_timeline": False,
        "estimated_margin_percent": 22,
    }


# ============================================================================
# Enum Tests
# ============================================================================

class TestAdvisoryType:
    """Tests for AdvisoryType enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert AdvisoryType.SCORING_SUGGESTION.value == "scoring_suggestion"
        assert AdvisoryType.RISK_ASSESSMENT.value == "risk_assessment"
        assert AdvisoryType.DECISION_SUPPORT.value == "decision_support"
        assert AdvisoryType.GAP_ANALYSIS.value == "gap_analysis"
        assert AdvisoryType.BENCHMARK_COMPARISON.value == "benchmark_comparison"
        assert AdvisoryType.IMPROVEMENT_PLAN.value == "improvement_plan"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(AdvisoryType) == 6


class TestDecisionRecommendation:
    """Tests for DecisionRecommendation enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert DecisionRecommendation.GO.value == "go"
        assert DecisionRecommendation.CONDITIONAL_GO.value == "conditional_go"
        assert DecisionRecommendation.NO_GO.value == "no_go"
        assert DecisionRecommendation.NEEDS_MORE_INFO.value == "needs_more_info"
        assert DecisionRecommendation.ESCALATE.value == "escalate"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(DecisionRecommendation) == 5


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.UNCERTAIN.value == "uncertain"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(ConfidenceLevel) == 4


class TestRiskCategory:
    """Tests for RiskCategory enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert RiskCategory.TECHNICAL.value == "technical"
        assert RiskCategory.COMMERCIAL.value == "commercial"
        assert RiskCategory.CAPACITY.value == "capacity"
        assert RiskCategory.QUALITY.value == "quality"
        assert RiskCategory.DELIVERY.value == "delivery"
        assert RiskCategory.SUPPLY_CHAIN.value == "supply_chain"
        assert RiskCategory.FINANCIAL.value == "financial"
        assert RiskCategory.STRATEGIC.value == "strategic"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(RiskCategory) == 8


class TestRiskSeverity:
    """Tests for RiskSeverity enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert RiskSeverity.CRITICAL.value == "critical"
        assert RiskSeverity.HIGH.value == "high"
        assert RiskSeverity.MEDIUM.value == "medium"
        assert RiskSeverity.LOW.value == "low"
        assert RiskSeverity.NEGLIGIBLE.value == "negligible"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(RiskSeverity) == 5
    
    def test_ordering(self):
        """Test severity ordering concept."""
        severities = [
            RiskSeverity.NEGLIGIBLE,
            RiskSeverity.LOW,
            RiskSeverity.MEDIUM,
            RiskSeverity.HIGH,
            RiskSeverity.CRITICAL,
        ]
        assert len(severities) == 5


class TestGapSeverity:
    """Tests for GapSeverity enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert GapSeverity.BLOCKING.value == "blocking"
        assert GapSeverity.MAJOR.value == "major"
        assert GapSeverity.MINOR.value == "minor"
        assert GapSeverity.INFORMATIONAL.value == "informational"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(GapSeverity) == 4


class TestActionPriority:
    """Tests for ActionPriority enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert ActionPriority.IMMEDIATE.value == "immediate"
        assert ActionPriority.HIGH.value == "high"
        assert ActionPriority.MEDIUM.value == "medium"
        assert ActionPriority.LOW.value == "low"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(ActionPriority) == 4


class TestScoringRationale:
    """Tests for ScoringRationale enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert ScoringRationale.HISTORICAL_MATCH.value == "historical_match"
        assert ScoringRationale.CAPABILITY_ANALYSIS.value == "capability_analysis"
        assert ScoringRationale.CUSTOMER_HISTORY.value == "customer_history"
        assert ScoringRationale.INDUSTRY_STANDARD.value == "industry_standard"
        assert ScoringRationale.EXPERT_RULE.value == "expert_rule"
        assert ScoringRationale.PATTERN_MATCH.value == "pattern_match"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(ScoringRationale) == 6


# ============================================================================
# Data Class Tests
# ============================================================================

class TestCriterionData:
    """Tests for CriterionData dataclass."""
    
    def test_creation(self):
        """Test creating criterion data."""
        criterion = CriterionData(
            id=uuid4(),
            code="TEST-001",
            name="Test Criterion",
            category="technical",
            max_score=Decimal("10.0"),
            weight=Decimal("1.0"),
        )
        
        assert criterion.code == "TEST-001"
        assert criterion.name == "Test Criterion"
        assert criterion.category == "technical"
        assert criterion.max_score == Decimal("10.0")
        assert criterion.is_blocker is False
        assert criterion.blocker_threshold is None
    
    def test_blocker_criterion(self):
        """Test blocker criterion."""
        criterion = CriterionData(
            id=uuid4(),
            code="TEST-001",
            name="Test",
            category="quality",
            max_score=Decimal("10.0"),
            weight=Decimal("1.5"),
            is_blocker=True,
            blocker_threshold=Decimal("5.0"),
        )
        
        assert criterion.is_blocker is True
        assert criterion.blocker_threshold == Decimal("5.0")


class TestScoreData:
    """Tests for ScoreData dataclass."""
    
    def test_creation(self):
        """Test creating score data."""
        score = ScoreData(
            criterion_id=uuid4(),
            criterion_code="TEST-001",
            score=Decimal("7.5"),
        )
        
        assert score.score == Decimal("7.5")
        assert score.max_score == Decimal("10.0")
        assert score.weight == Decimal("1.0")
        assert score.is_blocker_triggered is False
    
    def test_blocker_triggered(self):
        """Test blocker triggered score."""
        score = ScoreData(
            criterion_id=uuid4(),
            criterion_code="TEST-001",
            score=Decimal("2.0"),
            is_blocker_triggered=True,
        )
        
        assert score.is_blocker_triggered is True


class TestQualificationData:
    """Tests for QualificationData dataclass."""
    
    def test_creation(self, sample_scores):
        """Test creating qualification data."""
        qualification = QualificationData(
            id=uuid4(),
            rfq_id=uuid4(),
            scores=sample_scores,
            total_score=Decimal("75.0"),
            percentage_score=Decimal("75.0"),
        )
        
        assert qualification.result == "pending"
        assert qualification.has_blockers is False
        assert len(qualification.scores) == 5
    
    def test_with_blockers(self, sample_scores):
        """Test qualification with blockers."""
        qualification = QualificationData(
            id=uuid4(),
            rfq_id=uuid4(),
            scores=sample_scores,
            has_blockers=True,
        )
        
        assert qualification.has_blockers is True


class TestScoringRecommendation:
    """Tests for ScoringRecommendation dataclass."""
    
    def test_creation(self):
        """Test creating scoring recommendation."""
        rec = ScoringRecommendation(
            criterion_id=uuid4(),
            criterion_code="TEST-001",
            criterion_name="Test",
            recommended_score=Decimal("7.5"),
            max_score=Decimal("10.0"),
            confidence=ConfidenceLevel.HIGH,
            rationale=ScoringRationale.HISTORICAL_MATCH,
            explanation="Based on historical data",
        )
        
        assert rec.recommended_score == Decimal("7.5")
        assert rec.confidence == ConfidenceLevel.HIGH
        assert rec.similar_cases == 0


class TestIdentifiedRisk:
    """Tests for IdentifiedRisk dataclass."""
    
    def test_creation(self):
        """Test creating identified risk."""
        risk = IdentifiedRisk(
            category=RiskCategory.TECHNICAL,
            severity=RiskSeverity.HIGH,
            title="Test Risk",
            description="Risk description",
            impact="Impact description",
            probability=Decimal("0.7"),
            risk_score=Decimal("56"),
        )
        
        assert risk.severity == RiskSeverity.HIGH
        assert risk.probability == Decimal("0.7")
        assert risk.id is not None
    
    def test_defaults(self):
        """Test default values."""
        risk = IdentifiedRisk()
        
        assert risk.category == RiskCategory.TECHNICAL
        assert risk.severity == RiskSeverity.MEDIUM
        assert risk.probability == Decimal("0.5")


class TestGap:
    """Tests for Gap dataclass."""
    
    def test_creation(self):
        """Test creating gap."""
        gap = Gap(
            criterion_code="TEST-001",
            criterion_name="Test Criterion",
            severity=GapSeverity.MAJOR,
            current_score=Decimal("5.0"),
            required_score=Decimal("7.0"),
            gap_amount=Decimal("2.0"),
        )
        
        assert gap.severity == GapSeverity.MAJOR
        assert gap.gap_amount == Decimal("2.0")
    
    def test_defaults(self):
        """Test default values."""
        gap = Gap()
        
        assert gap.severity == GapSeverity.MINOR
        assert gap.estimated_effort == "medium"


class TestRecommendedAction:
    """Tests for RecommendedAction dataclass."""
    
    def test_creation(self):
        """Test creating action."""
        action = RecommendedAction(
            priority=ActionPriority.HIGH,
            title="Action Title",
            description="Action description",
            expected_outcome="Expected outcome",
            responsible_role="Manager",
            timeline="1 week",
        )
        
        assert action.priority == ActionPriority.HIGH
        assert action.id is not None
    
    def test_defaults(self):
        """Test default values."""
        action = RecommendedAction()
        
        assert action.priority == ActionPriority.MEDIUM
        assert len(action.related_gaps) == 0


class TestDecisionSupport:
    """Tests for DecisionSupport dataclass."""
    
    def test_creation(self):
        """Test creating decision support."""
        decision = DecisionSupport(
            recommendation=DecisionRecommendation.GO,
            confidence=ConfidenceLevel.HIGH,
            score_summary="Good score",
        )
        
        assert decision.recommendation == DecisionRecommendation.GO
        assert decision.confidence == ConfidenceLevel.HIGH
    
    def test_defaults(self):
        """Test default values."""
        decision = DecisionSupport()
        
        assert decision.recommendation == DecisionRecommendation.NEEDS_MORE_INFO
        assert decision.confidence == ConfidenceLevel.UNCERTAIN
        assert len(decision.key_strengths) == 0


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""
    
    def test_creation(self):
        """Test creating benchmark result."""
        benchmark = BenchmarkResult(
            criterion_code="TEST-001",
            criterion_name="Test",
            current_score=Decimal("8.0"),
            benchmark_score=Decimal("7.5"),
            percentile=75,
            status="above_benchmark",
        )
        
        assert benchmark.percentile == 75
        assert benchmark.status == "above_benchmark"


class TestQualificationAdvisory:
    """Tests for QualificationAdvisory dataclass."""
    
    def test_creation(self):
        """Test creating advisory."""
        advisory = QualificationAdvisory(
            qualification_id=uuid4(),
            advisory_type=AdvisoryType.DECISION_SUPPORT,
        )
        
        assert advisory.id is not None
        assert advisory.advisory_type == AdvisoryType.DECISION_SUPPORT
        assert len(advisory.scoring_recommendations) == 0
    
    def test_defaults(self):
        """Test default values."""
        advisory = QualificationAdvisory()
        
        assert advisory.overall_risk_level == RiskSeverity.MEDIUM
        assert advisory.generation_time_ms == 0


# ============================================================================
# Service Initialization Tests
# ============================================================================

class TestServiceInitialization:
    """Tests for service initialization."""
    
    def test_default_initialization(self):
        """Test default initialization."""
        service = AIQualificationAdvisoryService()
        
        assert service.go_threshold == Decimal("70.0")
        assert service.conditional_threshold == Decimal("50.0")
        assert service.blocker_threshold == Decimal("3.0")
    
    def test_custom_initialization(self):
        """Test custom initialization."""
        service = AIQualificationAdvisoryService(
            go_threshold=Decimal("75.0"),
            conditional_threshold=Decimal("60.0"),
        )
        
        assert service.go_threshold == Decimal("75.0")
        assert service.conditional_threshold == Decimal("60.0")


# ============================================================================
# Scoring Recommendation Tests
# ============================================================================

class TestScoringRecommendations:
    """Tests for scoring recommendations."""
    
    def test_generate_recommendations(
        self, service, sample_criteria, sample_rfq_context
    ):
        """Test generating scoring recommendations."""
        recommendations = service.generate_scoring_recommendations(
            sample_criteria, sample_rfq_context
        )
        
        assert len(recommendations) == 5
        assert all(isinstance(r, ScoringRecommendation) for r in recommendations)
    
    def test_recommendation_scores_in_range(
        self, service, sample_criteria, sample_rfq_context
    ):
        """Test recommendation scores are within valid range."""
        recommendations = service.generate_scoring_recommendations(
            sample_criteria, sample_rfq_context
        )
        
        for rec in recommendations:
            assert Decimal("1.0") <= rec.recommended_score <= rec.max_score
    
    def test_existing_customer_bonus(self, service, sample_criteria):
        """Test existing customer gives bonus."""
        context_existing = {"existing_customer": True}
        context_new = {"existing_customer": False}
        
        recs_existing = service.generate_scoring_recommendations(
            sample_criteria[:1], context_existing
        )
        recs_new = service.generate_scoring_recommendations(
            sample_criteria[:1], context_new
        )
        
        # Existing customer should get higher score
        assert recs_existing[0].recommended_score >= recs_new[0].recommended_score
    
    def test_high_complexity_penalty(self, service, sample_criteria):
        """Test high complexity gives penalty."""
        context_high = {"part_complexity": "high"}
        context_low = {"part_complexity": "low"}
        
        recs_high = service.generate_scoring_recommendations(
            sample_criteria[:1], context_high
        )
        recs_low = service.generate_scoring_recommendations(
            sample_criteria[:1], context_low
        )
        
        # High complexity should get lower score
        assert recs_high[0].recommended_score < recs_low[0].recommended_score
    
    def test_familiar_process_bonus(self, service, sample_criteria):
        """Test familiar process gives bonus."""
        context_familiar = {"familiar_process": True}
        context_new = {"familiar_process": False}
        
        recs_familiar = service.generate_scoring_recommendations(
            sample_criteria[:1], context_familiar
        )
        recs_new = service.generate_scoring_recommendations(
            sample_criteria[:1], context_new
        )
        
        assert recs_familiar[0].recommended_score > recs_new[0].recommended_score
    
    def test_high_volume_bonus(self, service, sample_criteria):
        """Test high volume gives bonus."""
        context_high = {"annual_volume": 50000}
        context_low = {"annual_volume": 100}
        
        recs_high = service.generate_scoring_recommendations(
            sample_criteria[:1], context_high
        )
        recs_low = service.generate_scoring_recommendations(
            sample_criteria[:1], context_low
        )
        
        assert recs_high[0].recommended_score >= recs_low[0].recommended_score
    
    def test_recommendation_has_explanation(
        self, service, sample_criteria, sample_rfq_context
    ):
        """Test recommendations include explanations."""
        recommendations = service.generate_scoring_recommendations(
            sample_criteria, sample_rfq_context
        )
        
        for rec in recommendations:
            assert len(rec.explanation) > 0
            assert "benchmark" in rec.explanation.lower()
    
    def test_confidence_levels(self, service, sample_criteria):
        """Test confidence level determination."""
        # Multiple factors should give high confidence
        context_many = {
            "existing_customer": True,
            "part_complexity": "low",
            "familiar_process": True,
        }
        
        recs = service.generate_scoring_recommendations(
            sample_criteria[:1], context_many
        )
        
        assert recs[0].confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


# ============================================================================
# Risk Assessment Tests
# ============================================================================

class TestRiskAssessment:
    """Tests for risk assessment."""
    
    def test_assess_risks(
        self, service, sample_qualification, sample_rfq_context
    ):
        """Test risk assessment."""
        risks, severity, score = service.assess_risks(
            sample_qualification, sample_rfq_context
        )
        
        assert isinstance(risks, list)
        assert isinstance(severity, RiskSeverity)
        assert isinstance(score, Decimal)
    
    def test_low_score_creates_risk(self, service, sample_qualification):
        """Test low scores create risks."""
        # Modify a score to be very low
        sample_qualification.scores[0].score = Decimal("2.0")
        
        risks, _, _ = service.assess_risks(sample_qualification, {})
        
        low_score_risks = [r for r in risks if "low score" in r.title.lower()]
        assert len(low_score_risks) > 0
    
    def test_blocker_triggered_creates_critical_risk(self, service, sample_qualification):
        """Test blocker trigger creates critical risk."""
        sample_qualification.scores[0].is_blocker_triggered = True
        
        risks, _, _ = service.assess_risks(sample_qualification, {})
        
        blocker_risks = [r for r in risks if "blocker" in r.title.lower()]
        assert len(blocker_risks) > 0
        assert blocker_risks[0].severity == RiskSeverity.CRITICAL
    
    def test_qualification_with_blockers(self, service, sample_qualification):
        """Test qualification with blockers."""
        sample_qualification.has_blockers = True
        
        risks, severity, _ = service.assess_risks(sample_qualification, {})
        
        assert severity == RiskSeverity.CRITICAL
    
    def test_new_customer_risk(self, service, sample_qualification):
        """Test new customer creates risk."""
        context = {"existing_customer": False}
        
        risks, _, _ = service.assess_risks(sample_qualification, context)
        
        customer_risks = [r for r in risks if "customer" in r.title.lower()]
        assert len(customer_risks) > 0
    
    def test_new_process_risk(self, service, sample_qualification):
        """Test new process creates risk."""
        context = {"new_process_required": True}
        
        risks, _, _ = service.assess_risks(sample_qualification, context)
        
        process_risks = [r for r in risks if "process" in r.title.lower()]
        assert len(process_risks) > 0
    
    def test_aggressive_timeline_risk(self, service, sample_qualification):
        """Test aggressive timeline creates risk."""
        context = {"aggressive_timeline": True}
        
        risks, _, _ = service.assess_risks(sample_qualification, context)
        
        timeline_risks = [r for r in risks if "timeline" in r.title.lower()]
        assert len(timeline_risks) > 0
    
    def test_low_margin_risk(self, service, sample_qualification):
        """Test low margin creates risk."""
        context = {"estimated_margin_percent": 8}
        
        risks, _, _ = service.assess_risks(sample_qualification, context)
        
        margin_risks = [r for r in risks if "margin" in r.title.lower()]
        assert len(margin_risks) > 0
        assert margin_risks[0].severity == RiskSeverity.CRITICAL
    
    def test_risk_score_calculation(self, service, sample_qualification):
        """Test risk score calculation."""
        context = {
            "existing_customer": False,
            "aggressive_timeline": True,
            "estimated_margin_percent": 12,
        }
        
        risks, severity, score = service.assess_risks(sample_qualification, context)
        
        # Should have elevated risk
        assert severity in [RiskSeverity.MEDIUM, RiskSeverity.HIGH, RiskSeverity.CRITICAL]
        assert score > Decimal("0")
    
    def test_no_risks_when_all_good(self, service, sample_qualification, sample_rfq_context):
        """Test no risks when qualification is good."""
        # Ensure all scores are high
        for score_data in sample_qualification.scores:
            score_data.score = Decimal("9.0")
        
        risks, severity, score = service.assess_risks(
            sample_qualification, sample_rfq_context
        )
        
        # Should have low or no risks (just the existing_customer one)
        assert severity in [RiskSeverity.NEGLIGIBLE, RiskSeverity.LOW, RiskSeverity.MEDIUM]


# ============================================================================
# Gap Analysis Tests
# ============================================================================

class TestGapAnalysis:
    """Tests for gap analysis."""
    
    def test_analyze_gaps(self, service, sample_qualification, sample_criteria):
        """Test gap analysis."""
        gaps = service.analyze_gaps(sample_qualification, sample_criteria)
        
        assert isinstance(gaps, list)
        assert all(isinstance(g, Gap) for g in gaps)
    
    def test_no_gaps_when_scores_high(
        self, service, sample_qualification, sample_criteria
    ):
        """Test no gaps when all scores are high."""
        # Set all scores to maximum
        for i, score_data in enumerate(sample_qualification.scores):
            score_data.score = sample_criteria[i].max_score
        
        gaps = service.analyze_gaps(sample_qualification, sample_criteria)
        
        assert len(gaps) == 0
    
    def test_gaps_sorted_by_severity(
        self, service, sample_qualification, sample_criteria
    ):
        """Test gaps are sorted by severity."""
        # Create variety of gap sizes
        sample_qualification.scores[0].score = Decimal("2.0")  # Large gap
        sample_qualification.scores[1].score = Decimal("5.0")  # Medium gap
        sample_qualification.scores[2].score = Decimal("6.5")  # Small gap
        
        gaps = service.analyze_gaps(sample_qualification, sample_criteria)
        
        if len(gaps) > 1:
            # Verify sorted by severity (blocking first, then major, etc.)
            severity_order = {
                GapSeverity.BLOCKING: 0,
                GapSeverity.MAJOR: 1,
                GapSeverity.MINOR: 2,
                GapSeverity.INFORMATIONAL: 3,
            }
            for i in range(len(gaps) - 1):
                assert severity_order[gaps[i].severity] <= severity_order[gaps[i + 1].severity]
    
    def test_blocker_criterion_creates_blocking_gap(
        self, service, sample_qualification, sample_criteria
    ):
        """Test blocker criterion creates blocking gap."""
        # Set low score on blocker criterion
        sample_qualification.scores[0].score = Decimal("2.0")
        
        gaps = service.analyze_gaps(sample_qualification, sample_criteria)
        
        tech_gaps = [g for g in gaps if g.criterion_code == "TECH-001"]
        if tech_gaps:
            assert tech_gaps[0].severity == GapSeverity.BLOCKING
    
    def test_gap_includes_closing_actions(
        self, service, sample_qualification, sample_criteria
    ):
        """Test gaps include suggested closing actions."""
        sample_qualification.scores[0].score = Decimal("3.0")
        
        gaps = service.analyze_gaps(sample_qualification, sample_criteria)
        
        if gaps:
            assert len(gaps[0].closing_actions) > 0
    
    def test_gap_effort_estimation(
        self, service, sample_qualification, sample_criteria
    ):
        """Test gap effort estimation."""
        # Large gap should have high effort
        sample_qualification.scores[0].score = Decimal("1.0")
        
        gaps = service.analyze_gaps(sample_qualification, sample_criteria)
        
        large_gaps = [g for g in gaps if g.gap_amount >= Decimal("5.0")]
        if large_gaps:
            assert large_gaps[0].estimated_effort == "high"
    
    def test_custom_target_score(
        self, service, sample_qualification, sample_criteria
    ):
        """Test using custom target score percentage."""
        # With 90% target, should have more gaps
        gaps_90 = service.analyze_gaps(
            sample_qualification, sample_criteria, target_score_percent=Decimal("90.0")
        )
        
        # With 50% target, should have fewer gaps
        gaps_50 = service.analyze_gaps(
            sample_qualification, sample_criteria, target_score_percent=Decimal("50.0")
        )
        
        assert len(gaps_90) >= len(gaps_50)


# ============================================================================
# Decision Support Tests
# ============================================================================

class TestDecisionSupport:
    """Tests for decision support."""
    
    def test_generate_decision_support(
        self, service, sample_qualification
    ):
        """Test generating decision support."""
        risks = []
        gaps = []
        
        decision = service.generate_decision_support(
            sample_qualification, risks, gaps
        )
        
        assert isinstance(decision, DecisionSupport)
        assert decision.recommendation is not None
        assert decision.confidence is not None
    
    def test_go_recommendation_for_high_score(
        self, service, sample_qualification
    ):
        """Test GO recommendation for high scores."""
        sample_qualification.percentage_score = Decimal("85.0")
        
        decision = service.generate_decision_support(
            sample_qualification, [], []
        )
        
        assert decision.recommendation == DecisionRecommendation.GO
        assert decision.confidence == ConfidenceLevel.HIGH
    
    def test_conditional_for_medium_score(
        self, service, sample_qualification
    ):
        """Test conditional recommendation for medium scores."""
        sample_qualification.percentage_score = Decimal("60.0")
        
        decision = service.generate_decision_support(
            sample_qualification, [], []
        )
        
        assert decision.recommendation == DecisionRecommendation.CONDITIONAL_GO
    
    def test_no_go_for_low_score(
        self, service, sample_qualification
    ):
        """Test NO GO recommendation for low scores."""
        sample_qualification.percentage_score = Decimal("35.0")
        
        decision = service.generate_decision_support(
            sample_qualification, [], []
        )
        
        assert decision.recommendation == DecisionRecommendation.NO_GO
    
    def test_no_go_with_blockers(
        self, service, sample_qualification
    ):
        """Test NO GO when blockers present."""
        sample_qualification.has_blockers = True
        sample_qualification.percentage_score = Decimal("85.0")  # Even with high score
        
        decision = service.generate_decision_support(
            sample_qualification, [], []
        )
        
        assert decision.recommendation == DecisionRecommendation.NO_GO
    
    def test_conditional_with_critical_risks(
        self, service, sample_qualification
    ):
        """Test conditional recommendation with critical risks."""
        sample_qualification.percentage_score = Decimal("80.0")
        
        critical_risk = IdentifiedRisk(
            severity=RiskSeverity.CRITICAL,
            title="Critical Issue",
        )
        
        decision = service.generate_decision_support(
            sample_qualification, [critical_risk], []
        )
        
        assert decision.recommendation == DecisionRecommendation.CONDITIONAL_GO
    
    def test_key_strengths_extraction(
        self, service, sample_qualification
    ):
        """Test extraction of key strengths."""
        # Set high scores
        for score_data in sample_qualification.scores:
            score_data.score = Decimal("9.0")
        sample_qualification.percentage_score = Decimal("90.0")
        
        decision = service.generate_decision_support(
            sample_qualification, [], []
        )
        
        assert len(decision.key_strengths) > 0
    
    def test_key_concerns_extraction(
        self, service, sample_qualification
    ):
        """Test extraction of key concerns."""
        sample_qualification.scores[0].score = Decimal("2.0")
        
        risk = IdentifiedRisk(
            severity=RiskSeverity.HIGH,
            title="High Risk Item",
        )
        gap = Gap(
            criterion_code="TEST",
            criterion_name="Test",
            severity=GapSeverity.BLOCKING,
        )
        
        decision = service.generate_decision_support(
            sample_qualification, [risk], [gap]
        )
        
        assert len(decision.key_concerns) > 0
    
    def test_conditions_for_conditional_approval(
        self, service, sample_qualification
    ):
        """Test conditions generated for conditional approval."""
        sample_qualification.percentage_score = Decimal("60.0")
        
        risk = IdentifiedRisk(
            severity=RiskSeverity.HIGH,
            title="Risk",
            mitigation="Do something",
        )
        
        decision = service.generate_decision_support(
            sample_qualification, [risk], []
        )
        
        assert len(decision.conditions) > 0
    
    def test_alternative_options(self, service, sample_qualification):
        """Test alternative options are provided."""
        decision = service.generate_decision_support(
            sample_qualification, [], []
        )
        
        assert len(decision.alternative_options) > 0


# ============================================================================
# Benchmark Comparison Tests
# ============================================================================

class TestBenchmarkComparison:
    """Tests for benchmark comparison."""
    
    def test_compare_to_benchmarks(
        self, service, sample_qualification, sample_criteria
    ):
        """Test benchmark comparison."""
        results = service.compare_to_benchmarks(
            sample_qualification, sample_criteria
        )
        
        assert len(results) == 5
        assert all(isinstance(r, BenchmarkResult) for r in results)
    
    def test_benchmark_status_above(
        self, service, sample_qualification, sample_criteria
    ):
        """Test above benchmark status."""
        # Set very high score
        sample_qualification.scores[0].score = Decimal("10.0")
        
        results = service.compare_to_benchmarks(
            sample_qualification, sample_criteria
        )
        
        tech_result = [r for r in results if r.criterion_code == "TECH-001"][0]
        assert tech_result.status == "above_benchmark"
    
    def test_benchmark_status_below(
        self, service, sample_qualification, sample_criteria
    ):
        """Test below benchmark status."""
        # Set very low score
        sample_qualification.scores[0].score = Decimal("3.0")
        
        results = service.compare_to_benchmarks(
            sample_qualification, sample_criteria
        )
        
        tech_result = [r for r in results if r.criterion_code == "TECH-001"][0]
        assert tech_result.status == "below_benchmark"
    
    def test_percentile_calculation(
        self, service, sample_qualification, sample_criteria
    ):
        """Test percentile calculation."""
        results = service.compare_to_benchmarks(
            sample_qualification, sample_criteria
        )
        
        for result in results:
            assert 1 <= result.percentile <= 99


# ============================================================================
# Full Advisory Generation Tests
# ============================================================================

class TestAdvisoryGeneration:
    """Tests for full advisory generation."""
    
    def test_generate_advisory(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test full advisory generation."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert isinstance(advisory, QualificationAdvisory)
        assert advisory.id is not None
        assert advisory.qualification_id == sample_qualification.id
    
    def test_advisory_includes_all_components(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test advisory includes all components."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert len(advisory.scoring_recommendations) > 0
        assert advisory.decision is not None
        assert len(advisory.benchmarks) > 0
        assert len(advisory.executive_summary) > 0
    
    def test_advisory_stored(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test advisory is stored for retrieval."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        retrieved = service.get_advisory(advisory.id)
        
        assert retrieved is not None
        assert retrieved.id == advisory.id
    
    def test_advisory_generation_time_tracked(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test generation time is tracked."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert advisory.generation_time_ms >= 0
    
    def test_advisory_has_key_findings(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test advisory includes key findings."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert isinstance(advisory.key_findings, list)
    
    def test_advisory_has_actions_when_issues(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test advisory generates actions when issues exist."""
        # Create low scores to trigger issues
        sample_qualification.scores[0].score = Decimal("2.0")
        sample_qualification.scores[0].is_blocker_triggered = True
        
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert len(advisory.actions) > 0
    
    def test_executive_summary_content(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test executive summary has expected content."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        summary = advisory.executive_summary
        
        assert "Advisory" in summary or "Summary" in summary
        assert sample_qualification.customer_name in summary


# ============================================================================
# Advisory Retrieval Tests
# ============================================================================

class TestAdvisoryRetrieval:
    """Tests for advisory retrieval."""
    
    def test_get_advisory(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test getting advisory by ID."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        retrieved = service.get_advisory(advisory.id)
        
        assert retrieved == advisory
    
    def test_get_nonexistent_advisory(self, service):
        """Test getting nonexistent advisory returns None."""
        result = service.get_advisory(uuid4())
        
        assert result is None
    
    def test_list_advisories(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test listing advisories."""
        # Generate multiple advisories
        for _ in range(3):
            service.generate_advisory(
                sample_qualification, sample_criteria, sample_rfq_context
            )
        
        advisories = service.list_advisories()
        
        assert len(advisories) == 3
    
    def test_list_advisories_filter_by_qualification(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test filtering advisories by qualification ID."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        # Create another qualification
        other_qualification = QualificationData(
            id=uuid4(),
            rfq_id=uuid4(),
            scores=[],
        )
        service.generate_advisory(
            other_qualification, sample_criteria, sample_rfq_context
        )
        
        advisories = service.list_advisories(
            qualification_id=sample_qualification.id
        )
        
        assert len(advisories) == 1
        assert advisories[0].qualification_id == sample_qualification.id
    
    def test_list_advisories_limit(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test limiting advisory list."""
        for _ in range(5):
            service.generate_advisory(
                sample_qualification, sample_criteria, sample_rfq_context
            )
        
        advisories = service.list_advisories(limit=3)
        
        assert len(advisories) == 3


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_scores(self, service, sample_criteria, sample_rfq_context):
        """Test with empty scores."""
        qualification = QualificationData(
            id=uuid4(),
            rfq_id=uuid4(),
            scores=[],
        )
        
        advisory = service.generate_advisory(
            qualification, sample_criteria, sample_rfq_context
        )
        
        assert advisory is not None
    
    def test_empty_criteria(
        self, service, sample_qualification, sample_rfq_context
    ):
        """Test with empty criteria."""
        advisory = service.generate_advisory(
            sample_qualification, [], sample_rfq_context
        )
        
        assert advisory is not None
    
    def test_empty_rfq_context(
        self, service, sample_qualification, sample_criteria
    ):
        """Test with empty RFQ context."""
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, {}
        )
        
        assert advisory is not None
    
    def test_none_scores(self, service, sample_criteria, sample_rfq_context):
        """Test with None scores."""
        scores = [
            ScoreData(
                criterion_id=sample_criteria[0].id,
                criterion_code="TEST-001",
                score=None,  # Not yet scored
            )
        ]
        
        qualification = QualificationData(
            id=uuid4(),
            rfq_id=uuid4(),
            scores=scores,
        )
        
        risks, _, _ = service.assess_risks(qualification, sample_rfq_context)
        
        # Should not crash, risks should still be assessed
        assert isinstance(risks, list)
    
    def test_zero_percentage_score(
        self, service, sample_qualification, sample_criteria, sample_rfq_context
    ):
        """Test with zero percentage score."""
        sample_qualification.percentage_score = Decimal("0")
        
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert advisory.decision.recommendation == DecisionRecommendation.NO_GO
    
    def test_very_high_values(
        self, service, sample_qualification, sample_criteria, sample_rfq_context
    ):
        """Test with very high estimated value."""
        sample_qualification.estimated_value = Decimal("999999999")
        
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        assert advisory is not None
    
    def test_unknown_category_in_code(self, service, sample_qualification):
        """Test with unknown category prefix in criterion code."""
        sample_qualification.scores[0].criterion_code = "UNKNOWN-001"
        
        risks, _, _ = service.assess_risks(sample_qualification, {})
        
        # Should handle gracefully
        assert isinstance(risks, list)


# ============================================================================
# Constants Tests
# ============================================================================

class TestConstants:
    """Tests for service constants."""
    
    def test_category_benchmarks_exist(self):
        """Test category benchmarks are defined."""
        assert "technical" in CATEGORY_BENCHMARKS
        assert "commercial" in CATEGORY_BENCHMARKS
        assert "capacity" in CATEGORY_BENCHMARKS
        assert "quality" in CATEGORY_BENCHMARKS
    
    def test_category_benchmark_structure(self):
        """Test benchmark structure."""
        for category, benchmarks in CATEGORY_BENCHMARKS.items():
            assert "average_score" in benchmarks
            assert "std_dev" in benchmarks
            assert "min_acceptable" in benchmarks
            assert "excellent_threshold" in benchmarks
    
    def test_risk_factors_exist(self):
        """Test risk factors are defined."""
        assert "technical" in RISK_FACTORS
        assert "commercial" in RISK_FACTORS
        assert "capacity" in RISK_FACTORS
    
    def test_risk_factor_structure(self):
        """Test risk factor structure."""
        for category, factors in RISK_FACTORS.items():
            for factor in factors:
                assert len(factor) == 3
                assert isinstance(factor[0], str)
                assert isinstance(factor[1], RiskSeverity)
                assert isinstance(factor[2], str)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(
        self,
        service,
        sample_qualification,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test complete advisory workflow."""
        # Step 1: Generate advisory
        advisory = service.generate_advisory(
            sample_qualification, sample_criteria, sample_rfq_context
        )
        
        # Step 2: Verify all components
        assert len(advisory.scoring_recommendations) == 5
        assert advisory.decision.recommendation in DecisionRecommendation
        assert len(advisory.benchmarks) == 5
        
        # Step 3: Retrieve and verify
        retrieved = service.get_advisory(advisory.id)
        assert retrieved.id == advisory.id
        
        # Step 4: List advisories
        all_advisories = service.list_advisories()
        assert len(all_advisories) >= 1
    
    def test_multiple_qualifications(
        self,
        service,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test handling multiple qualifications."""
        qualifications = []
        
        for i in range(3):
            q = QualificationData(
                id=uuid4(),
                rfq_id=uuid4(),
                scores=[
                    ScoreData(
                        criterion_id=sample_criteria[0].id,
                        criterion_code="TECH-001",
                        score=Decimal("7.0") + Decimal(str(i)),
                    )
                ],
                percentage_score=Decimal("70.0") + Decimal(str(i * 5)),
            )
            qualifications.append(q)
        
        advisories = []
        for q in qualifications:
            adv = service.generate_advisory(q, sample_criteria, sample_rfq_context)
            advisories.append(adv)
        
        assert len(advisories) == 3
        assert len(set(a.id for a in advisories)) == 3  # All unique IDs
    
    def test_advisory_with_mixed_conditions(
        self,
        service,
        sample_criteria,
        sample_rfq_context,
    ):
        """Test advisory with mixed positive and negative conditions."""
        # Some good, some bad scores
        scores = [
            ScoreData(
                criterion_id=sample_criteria[0].id,
                criterion_code="TECH-001",
                score=Decimal("9.0"),  # Good
            ),
            ScoreData(
                criterion_id=sample_criteria[1].id,
                criterion_code="COMM-001",
                score=Decimal("2.0"),  # Bad
            ),
            ScoreData(
                criterion_id=sample_criteria[2].id,
                criterion_code="CAP-001",
                score=Decimal("8.0"),  # Good
            ),
        ]
        
        qualification = QualificationData(
            id=uuid4(),
            rfq_id=uuid4(),
            scores=scores,
            percentage_score=Decimal("63.0"),
        )
        
        # Mixed context
        context = {
            "existing_customer": True,  # Good
            "aggressive_timeline": True,  # Bad
            "estimated_margin_percent": 20,  # OK
        }
        
        advisory = service.generate_advisory(
            qualification, sample_criteria, context
        )
        
        # Should have both strengths and concerns
        assert len(advisory.decision.key_strengths) > 0 or len(advisory.decision.key_concerns) > 0
        assert len(advisory.identified_risks) > 0
