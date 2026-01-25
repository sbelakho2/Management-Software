"""
AI Qualification Advisory Service.

Provides AI-powered qualification analysis and recommendations for RFQs:
- Automated Scoring Suggestions
- Risk Assessment
- Go/No-Go Recommendations
- Gap Analysis
- Improvement Suggestions
- Benchmark Comparisons

Key Features:
- Intelligent scoring recommendations based on historical data
- Comprehensive risk analysis
- Actionable improvement recommendations
- Decision support with confidence levels
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4

from sensei.core.time import utcnow_naive


# ============================================================================
# Enums
# ============================================================================

class AdvisoryType(str, Enum):
    """Type of advisory generated."""

    SCORING_SUGGESTION = "scoring_suggestion"
    RISK_ASSESSMENT = "risk_assessment"
    DECISION_SUPPORT = "decision_support"
    GAP_ANALYSIS = "gap_analysis"
    BENCHMARK_COMPARISON = "benchmark_comparison"
    IMPROVEMENT_PLAN = "improvement_plan"


class DecisionRecommendation(str, Enum):
    """Decision recommendation output."""

    GO = "go"
    CONDITIONAL_GO = "conditional_go"
    NO_GO = "no_go"
    NEEDS_MORE_INFO = "needs_more_info"
    ESCALATE = "escalate"


class ConfidenceLevel(str, Enum):
    """Confidence for recommendations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class RiskCategory(str, Enum):
    """Risk category taxonomy."""

    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    CAPACITY = "capacity"
    QUALITY = "quality"
    DELIVERY = "delivery"
    SUPPLY_CHAIN = "supply_chain"
    FINANCIAL = "financial"
    STRATEGIC = "strategic"


class RiskSeverity(str, Enum):
    """Risk severity level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class GapSeverity(str, Enum):
    """Gap severity level."""
    
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"
    INFORMATIONAL = "informational"


class ActionPriority(str, Enum):
    """Action priority level."""
    
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScoringRationale(str, Enum):
    """Rationale for scoring suggestion."""
    
    HISTORICAL_MATCH = "historical_match"
    CAPABILITY_ANALYSIS = "capability_analysis"
    CUSTOMER_HISTORY = "customer_history"
    INDUSTRY_STANDARD = "industry_standard"
    EXPERT_RULE = "expert_rule"
    PATTERN_MATCH = "pattern_match"


# Benchmark data is expected to be provided via rfq_context.
CATEGORY_BENCHMARKS = {
    "technical": {
        "average_score": Decimal("7.2"),
        "std_dev": Decimal("1.1"),
        "min_acceptable": Decimal("4.0"),
        "excellent_threshold": Decimal("9.0"),
    },
    "commercial": {
        "average_score": Decimal("6.8"),
        "std_dev": Decimal("1.0"),
        "min_acceptable": Decimal("3.5"),
        "excellent_threshold": Decimal("8.5"),
    },
    "capacity": {
        "average_score": Decimal("6.5"),
        "std_dev": Decimal("1.2"),
        "min_acceptable": Decimal("3.0"),
        "excellent_threshold": Decimal("8.0"),
    },
    "quality": {
        "average_score": Decimal("7.5"),
        "std_dev": Decimal("0.9"),
        "min_acceptable": Decimal("4.5"),
        "excellent_threshold": Decimal("9.2"),
    },
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CriterionData:
    """Qualification criterion data."""
    
    id: UUID
    code: str
    name: str
    category: str
    max_score: Decimal
    weight: Decimal
    is_blocker: bool = False
    blocker_threshold: Optional[Decimal] = None
    scoring_guide: Optional[dict[str, str]] = None


@dataclass
class ScoreData:
    """Score data for a criterion."""
    
    criterion_id: UUID
    criterion_code: str
    score: Optional[Decimal] = None
    max_score: Decimal = Decimal("10.0")
    weight: Decimal = Decimal("1.0")
    notes: Optional[str] = None
    is_blocker_triggered: bool = False


@dataclass
class QualificationData:
    """Full qualification data."""
    
    id: UUID
    rfq_id: UUID
    scores: list[ScoreData]
    total_score: Optional[Decimal] = None
    percentage_score: Optional[Decimal] = None
    result: str = "pending"
    has_blockers: bool = False
    customer_name: Optional[str] = None
    part_description: Optional[str] = None
    estimated_value: Optional[Decimal] = None
    process_types: list[str] = field(default_factory=list)


@dataclass
class ScoringRecommendation:
    """Recommended score for a criterion."""
    
    criterion_id: UUID
    criterion_code: str
    criterion_name: str
    recommended_score: Decimal
    max_score: Decimal
    confidence: ConfidenceLevel
    rationale: ScoringRationale
    explanation: str
    similar_cases: int = 0
    suggested_notes: Optional[str] = None


@dataclass
class IdentifiedRisk:
    """Identified risk item."""
    
    id: UUID = field(default_factory=uuid4)
    category: RiskCategory = RiskCategory.TECHNICAL
    severity: RiskSeverity = RiskSeverity.MEDIUM
    title: str = ""
    description: str = ""
    impact: str = ""
    probability: Decimal = Decimal("0.5")
    risk_score: Decimal = Decimal("0")
    mitigation: Optional[str] = None
    related_criteria: list[str] = field(default_factory=list)


@dataclass
class Gap:
    """Identified capability gap."""
    
    id: UUID = field(default_factory=uuid4)
    criterion_code: str = ""
    criterion_name: str = ""
    severity: GapSeverity = GapSeverity.MINOR
    current_score: Optional[Decimal] = None
    required_score: Decimal = Decimal("0")
    gap_amount: Decimal = Decimal("0")
    description: str = ""
    impact: str = ""
    closing_actions: list[str] = field(default_factory=list)
    estimated_effort: str = "medium"
    estimated_timeline: Optional[str] = None


@dataclass
class RecommendedAction:
    """Recommended action item."""
    
    id: UUID = field(default_factory=uuid4)
    priority: ActionPriority = ActionPriority.MEDIUM
    title: str = ""
    description: str = ""
    expected_outcome: str = ""
    responsible_role: str = ""
    timeline: str = ""
    related_gaps: list[UUID] = field(default_factory=list)
    related_risks: list[UUID] = field(default_factory=list)


@dataclass
class DecisionSupport:
    """Decision support analysis."""
    
    recommendation: DecisionRecommendation = DecisionRecommendation.NEEDS_MORE_INFO
    confidence: ConfidenceLevel = ConfidenceLevel.UNCERTAIN
    score_summary: str = ""
    key_strengths: list[str] = field(default_factory=list)
    key_concerns: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    risk_summary: str = ""
    business_case: str = ""
    alternative_options: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    """Benchmark comparison result."""
    
    criterion_code: str = ""
    criterion_name: str = ""
    current_score: Optional[Decimal] = None
    benchmark_score: Decimal = Decimal("0")
    percentile: Optional[int] = None
    status: str = ""  # above_benchmark, at_benchmark, below_benchmark
    similar_projects: int = 0


@dataclass
class QualificationAdvisory:
    """Complete qualification advisory."""
    
    id: UUID = field(default_factory=uuid4)
    qualification_id: UUID = field(default_factory=uuid4)
    advisory_type: AdvisoryType = AdvisoryType.DECISION_SUPPORT
    
    # Scoring Recommendations
    scoring_recommendations: list[ScoringRecommendation] = field(default_factory=list)
    
    # Risk Assessment
    identified_risks: list[IdentifiedRisk] = field(default_factory=list)
    overall_risk_level: RiskSeverity = RiskSeverity.MEDIUM
    risk_score: Decimal = Decimal("0")
    
    # Decision Support
    decision: DecisionSupport = field(default_factory=DecisionSupport)
    
    # Gap Analysis
    gaps: list[Gap] = field(default_factory=list)
    
    # Recommended Actions
    actions: list[RecommendedAction] = field(default_factory=list)
    
    # Benchmark Comparison
    benchmarks: list[BenchmarkResult] = field(default_factory=list)
    
    # Summary
    executive_summary: str = ""
    key_findings: list[str] = field(default_factory=list)
    
    # Metadata
    generated_at: datetime = field(default_factory=utcnow_naive)
    generation_time_ms: int = 0


# ============================================================================
# Benchmark inputs are provided via rfq_context
# ============================================================================

# Risk factors by category
RISK_FACTORS = {
    "technical": [
        ("New process required", RiskSeverity.HIGH, "Requires developing new manufacturing processes"),
        ("Tight tolerances", RiskSeverity.MEDIUM, "Specifications exceed standard capability"),
        ("Complex geometry", RiskSeverity.MEDIUM, "Part geometry presents manufacturing challenges"),
    ],
    "commercial": [
        ("Low margin", RiskSeverity.HIGH, "Profit margin below target threshold"),
        ("Aggressive pricing", RiskSeverity.MEDIUM, "Customer expecting competitive pricing"),
        ("Payment terms", RiskSeverity.LOW, "Non-standard payment terms requested"),
    ],
    "capacity": [
        ("Resource conflict", RiskSeverity.HIGH, "Overlaps with other high-priority programs"),
        ("Equipment limitation", RiskSeverity.MEDIUM, "Current equipment capacity constrained"),
        ("Skill shortage", RiskSeverity.MEDIUM, "Specialized skills required not readily available"),
    ],
    "quality": [
        ("Certification gap", RiskSeverity.HIGH, "Required certifications not currently held"),
        ("First article risk", RiskSeverity.MEDIUM, "New part type with complex FAIR requirements"),
        ("Inspection complexity", RiskSeverity.LOW, "Advanced inspection methods required"),
    ],
    "delivery": [
        ("Tight timeline", RiskSeverity.HIGH, "Delivery schedule leaves minimal buffer"),
        ("Lead time risk", RiskSeverity.MEDIUM, "Material lead times may impact delivery"),
        ("Ramp-up challenge", RiskSeverity.MEDIUM, "Aggressive production ramp required"),
    ],
}


# ============================================================================
# Service Class
# ============================================================================

class AIQualificationAdvisoryService:
    """
    AI-powered qualification advisory service.
    
    Provides intelligent analysis and recommendations for RFQ qualification:
    - Scoring suggestions based on historical patterns
    - Comprehensive risk assessment
    - Go/No-Go decision support
    - Gap analysis and improvement plans
    """
    
    def __init__(
        self,
        go_threshold: Decimal = Decimal("70.0"),
        conditional_threshold: Decimal = Decimal("50.0"),
        blocker_threshold: Decimal = Decimal("3.0"),
        high_confidence_threshold: Decimal = Decimal("0.8"),
    ):
        """
        Initialize the service.
        
        Args:
            go_threshold: Score percentage for GO decision
            conditional_threshold: Score percentage for conditional decision
            blocker_threshold: Score below which criterion triggers blocker
            high_confidence_threshold: Threshold for high confidence recommendations
        """
        self.go_threshold = go_threshold
        self.conditional_threshold = conditional_threshold
        self.blocker_threshold = blocker_threshold
        self.high_confidence_threshold = high_confidence_threshold
        
        self._advisories: dict[UUID, QualificationAdvisory] = {}
    
    # ========================================================================
    # Scoring Recommendations
    # ========================================================================
    
    def generate_scoring_recommendations(
        self,
        criteria: list[CriterionData],
        rfq_context: dict[str, Any],
    ) -> list[ScoringRecommendation]:
        """
        Generate scoring recommendations for qualification criteria.
        
        Args:
            criteria: List of criteria to score
            rfq_context: Context about the RFQ (customer, part, etc.)
            
        Returns:
            List of scoring recommendations
        """
        recommendations = []
        
        for criterion in criteria:
            recommendation = self._generate_criterion_recommendation(
                criterion, rfq_context
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_criterion_recommendation(
        self,
        criterion: CriterionData,
        rfq_context: dict[str, Any],
    ) -> ScoringRecommendation:
        """Generate recommendation for a single criterion."""
        category = criterion.category.lower()
        benchmarks = self._resolve_benchmarks(
            category,
            rfq_context,
            fallback_score=criterion.max_score * Decimal("0.7"),
            max_score=criterion.max_score,
        )
        
        # Determine base score from benchmarks
        base_score = benchmarks["average_score"]
        
        # Adjust based on context
        adjustment = Decimal("0")
        rationale = ScoringRationale.HISTORICAL_MATCH
        explanation_parts = []
        
        # Customer relationship adjustment
        if rfq_context.get("existing_customer"):
            adjustment += Decimal("0.5")
            explanation_parts.append("Existing customer relationship (+0.5)")
        
        # Part complexity adjustment
        complexity = rfq_context.get("part_complexity", "medium")
        if complexity == "high":
            adjustment -= Decimal("1.0")
            explanation_parts.append("High part complexity (-1.0)")
        elif complexity == "low":
            adjustment += Decimal("0.5")
            explanation_parts.append("Low part complexity (+0.5)")
        
        # Volume considerations
        volume = rfq_context.get("annual_volume", 0)
        if volume > 10000:
            adjustment += Decimal("0.5")
            explanation_parts.append("High volume opportunity (+0.5)")
        
        # Process familiarity
        if rfq_context.get("familiar_process"):
            adjustment += Decimal("1.0")
            rationale = ScoringRationale.CAPABILITY_ANALYSIS
            explanation_parts.append("Familiar process type (+1.0)")
        
        # Calculate final score
        recommended_score = min(
            max(base_score + adjustment, Decimal("1.0")),
            criterion.max_score
        )
        
        # Determine confidence
        confidence = self._determine_confidence(
            len(explanation_parts),
            recommended_score,
            benchmarks,
        )
        
        explanation = (
            f"Based on category benchmark ({category}: {benchmarks['average_score']}/10). "
            + " ".join(explanation_parts)
        )
        
        return ScoringRecommendation(
            criterion_id=criterion.id,
            criterion_code=criterion.code,
            criterion_name=criterion.name,
            recommended_score=recommended_score.quantize(Decimal("0.1")),
            max_score=criterion.max_score,
            confidence=confidence,
            rationale=rationale,
            explanation=explanation,
            similar_cases=int(rfq_context.get("similar_cases", {}).get(category, 0)),
            suggested_notes=self._generate_suggested_notes(criterion, recommended_score),
        )
    
    def _determine_confidence(
        self,
        factor_count: int,
        score: Decimal,
        benchmarks: dict,
    ) -> ConfidenceLevel:
        """Determine confidence level based on available data."""
        if factor_count >= 3:
            return ConfidenceLevel.HIGH
        elif factor_count >= 1:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_suggested_notes(
        self,
        criterion: CriterionData,
        score: Decimal,
    ) -> str:
        """Generate suggested notes for a score."""
        if criterion.scoring_guide:
            # Find matching guide entry
            for threshold, description in sorted(
                criterion.scoring_guide.items(),
                key=lambda x: float(x[0]),
                reverse=True,
            ):
                if score >= Decimal(threshold):
                    return description
        
        # Default notes based on score
        if score >= Decimal("8.0"):
            return "Fully capable. Strong performance in this area."
        elif score >= Decimal("6.0"):
            return "Capable with minor considerations."
        elif score >= Decimal("4.0"):
            return "Partially capable. Some gaps exist."
        else:
            return "Significant gaps exist. Careful consideration required."

    def _resolve_benchmarks(
        self,
        category: str,
        rfq_context: dict[str, Any],
        fallback_score: Decimal,
        max_score: Decimal,
    ) -> dict[str, Decimal]:
        """Resolve benchmark data from provided context or historical scores."""
        benchmarks = rfq_context.get("benchmarks", {}).get(category)
        if benchmarks:
            return {
                "average_score": Decimal(str(benchmarks["average_score"])),
                "std_dev": Decimal(str(benchmarks.get("std_dev", 0))),
                "min_acceptable": Decimal(str(benchmarks.get("min_acceptable", 0))),
                "excellent_threshold": Decimal(str(benchmarks.get("excellent_threshold", max_score))),
            }

        category_defaults = CATEGORY_BENCHMARKS.get(category)
        if category_defaults:
            return {
                "average_score": category_defaults["average_score"],
                "std_dev": category_defaults["std_dev"],
                "min_acceptable": category_defaults["min_acceptable"],
                "excellent_threshold": category_defaults["excellent_threshold"],
            }

        recent_scores = rfq_context.get("recent_scores", {}).get(category, [])
        if recent_scores:
            scores = [Decimal(str(s)) for s in recent_scores]
            avg = sum(scores) / Decimal(len(scores))
            variance = sum((s - avg) ** 2 for s in scores) / Decimal(len(scores))
            std_dev = variance.sqrt() if variance > 0 else Decimal("0")
            return {
                "average_score": avg,
                "std_dev": std_dev,
                "min_acceptable": min(scores),
                "excellent_threshold": max(scores),
            }

        return {
            "average_score": fallback_score,
            "std_dev": Decimal("0"),
            "min_acceptable": min(fallback_score, max_score),
            "excellent_threshold": max_score,
        }
    
    # ========================================================================
    # Risk Assessment
    # ========================================================================
    
    def assess_risks(
        self,
        qualification: QualificationData,
        criteria: list[CriterionData] | dict[str, Any] | None = None,
        rfq_context: dict[str, Any] | None = None,
    ) -> tuple[list[IdentifiedRisk], RiskSeverity, Decimal]:
        """
        Assess risks for a qualification.
        
        Args:
            qualification: Qualification data with scores
            rfq_context: Context about the RFQ
            
        Returns:
            Tuple of (risks, overall_severity, risk_score)
        """
        if isinstance(criteria, dict):
            rfq_context = criteria
            criteria = None
        rfq_context = rfq_context or {}
        risks = []
        
        # Analyze score-based risks
        criteria_map = {c.id: c for c in (criteria or [])}

        for score_data in qualification.scores:
            if score_data.score is not None:
                criterion = criteria_map.get(score_data.criterion_id)
                category = (criterion.category if criterion else self._get_category_from_code(score_data.criterion_code)).lower()
                max_score = criterion.max_score if criterion else (score_data.max_score or Decimal("10"))
                score_risks = self._assess_score_risks(score_data, category, max_score, rfq_context)
                risks.extend(score_risks)
        
        # Analyze context-based risks
        context_risks = self._assess_context_risks(rfq_context)
        risks.extend(context_risks)
        
        # Analyze blocker risks
        if qualification.has_blockers:
            risks.append(IdentifiedRisk(
                category=RiskCategory.TECHNICAL,
                severity=RiskSeverity.CRITICAL,
                title="Qualification Blocker Present",
                description="One or more blocking criteria have been triggered",
                impact="Cannot proceed without resolving blocker conditions",
                probability=Decimal("1.0"),
                risk_score=Decimal("100"),
            ))
        
        # Calculate overall risk
        overall_severity, risk_score = self._calculate_overall_risk(risks)
        
        return risks, overall_severity, risk_score
    
    def _assess_score_risks(
        self,
        score_data: ScoreData,
        category: str,
        max_score: Decimal,
        rfq_context: dict[str, Any],
    ) -> list[IdentifiedRisk]:
        """Assess risks based on individual scores."""
        risks: list[IdentifiedRisk] = []
        
        if score_data.score is None:
            return risks
        
        benchmarks = self._resolve_benchmarks(
            category,
            rfq_context,
            fallback_score=score_data.score or Decimal("0"),
            max_score=max_score,
        )
        min_acceptable = benchmarks["min_acceptable"]
        
        # Check if score is below minimum
        if score_data.score < min_acceptable:
            severity = RiskSeverity.HIGH if score_data.score < Decimal("3.0") else RiskSeverity.MEDIUM
            
            risks.append(IdentifiedRisk(
                category=RiskCategory(category) if category in [e.value for e in RiskCategory] else RiskCategory.TECHNICAL,
                severity=severity,
                title=f"Low Score: {score_data.criterion_code}",
                description=f"Score of {score_data.score} is below minimum acceptable of {min_acceptable}",
                impact="May impact qualification result or require mitigation",
                probability=Decimal("0.8"),
                risk_score=self._calculate_risk_score(severity, Decimal("0.8")),
                related_criteria=[score_data.criterion_code],
            ))
        
        # Check for blocker trigger
        if score_data.is_blocker_triggered:
            risks.append(IdentifiedRisk(
                category=RiskCategory(category) if category in [e.value for e in RiskCategory] else RiskCategory.TECHNICAL,
                severity=RiskSeverity.CRITICAL,
                title=f"Blocker Triggered: {score_data.criterion_code}",
                description=f"Criterion score triggered blocker condition",
                impact="Qualification cannot proceed without resolution",
                probability=Decimal("1.0"),
                risk_score=Decimal("100"),
                related_criteria=[score_data.criterion_code],
            ))
        
        return risks
    
    def _assess_context_risks(
        self,
        rfq_context: dict[str, Any],
    ) -> list[IdentifiedRisk]:
        """Assess risks based on RFQ context."""
        risks = []
        
        # New customer risk
        if not rfq_context.get("existing_customer"):
            risks.append(IdentifiedRisk(
                category=RiskCategory.COMMERCIAL,
                severity=RiskSeverity.MEDIUM,
                title="New Customer",
                description="First-time customer with no established relationship",
                impact="Higher uncertainty in payment terms and specifications",
                probability=Decimal("0.6"),
                risk_score=Decimal("30"),
                mitigation="Consider credit check and conservative payment terms",
            ))
        
        # New process risk
        if rfq_context.get("new_process_required"):
            risks.append(IdentifiedRisk(
                category=RiskCategory.TECHNICAL,
                severity=RiskSeverity.HIGH,
                title="New Process Development Required",
                description="RFQ requires development of new manufacturing processes",
                impact="Additional investment and timeline risk",
                probability=Decimal("0.7"),
                risk_score=Decimal("56"),
                mitigation="Include NRE charges and add schedule buffer",
            ))
        
        # Tight timeline risk
        if rfq_context.get("aggressive_timeline"):
            risks.append(IdentifiedRisk(
                category=RiskCategory.DELIVERY,
                severity=RiskSeverity.HIGH,
                title="Aggressive Timeline",
                description="Requested timeline is shorter than standard",
                impact="Risk of delivery delays or quality issues",
                probability=Decimal("0.6"),
                risk_score=Decimal("48"),
                mitigation="Negotiate timeline or add resources",
            ))
        
        # Low margin risk
        margin = rfq_context.get("estimated_margin_percent", 20)
        if margin < 15:
            severity = RiskSeverity.CRITICAL if margin < 10 else RiskSeverity.HIGH
            risks.append(IdentifiedRisk(
                category=RiskCategory.FINANCIAL,
                severity=severity,
                title="Low Profit Margin",
                description=f"Estimated margin of {margin}% is below target",
                impact="May not be financially viable",
                probability=Decimal("0.9"),
                risk_score=Decimal("72") if severity == RiskSeverity.HIGH else Decimal("90"),
                mitigation="Review cost estimates or renegotiate pricing",
            ))
        
        return risks
    
    def _get_category_from_code(self, code: str) -> str:
        """Extract category from criterion code."""
        # Assume format like "TECH-001", "COMM-002", etc.
        prefix = code.split("-")[0].lower() if "-" in code else "technical"
        
        category_map = {
            "tech": "technical",
            "comm": "commercial",
            "cap": "capacity",
            "qual": "quality",
            "strat": "strategic",
            "risk": "risk",
            "sc": "supply_chain",
        }
        
        return category_map.get(prefix, "technical")
    
    def _calculate_risk_score(
        self,
        severity: RiskSeverity,
        probability: Decimal,
    ) -> Decimal:
        """Calculate risk score from severity and probability."""
        severity_weights = {
            RiskSeverity.CRITICAL: Decimal("100"),
            RiskSeverity.HIGH: Decimal("80"),
            RiskSeverity.MEDIUM: Decimal("50"),
            RiskSeverity.LOW: Decimal("25"),
            RiskSeverity.NEGLIGIBLE: Decimal("10"),
        }
        
        base_score = severity_weights.get(severity, Decimal("50"))
        return (base_score * probability).quantize(Decimal("0.1"))
    
    def _calculate_overall_risk(
        self,
        risks: list[IdentifiedRisk],
    ) -> tuple[RiskSeverity, Decimal]:
        """Calculate overall risk level from individual risks."""
        if not risks:
            return RiskSeverity.NEGLIGIBLE, Decimal("0")
        
        # Check for critical risks
        critical_count = sum(1 for r in risks if r.severity == RiskSeverity.CRITICAL)
        if critical_count > 0:
            return RiskSeverity.CRITICAL, Decimal("95")
        
        # Calculate weighted average
        total_score = sum((r.risk_score for r in risks), Decimal("0"))
        avg_score: Decimal = total_score / len(risks) if risks else Decimal("0")
        
        # Determine severity
        if avg_score >= Decimal("70"):
            severity = RiskSeverity.HIGH
        elif avg_score >= Decimal("40"):
            severity = RiskSeverity.MEDIUM
        elif avg_score >= Decimal("20"):
            severity = RiskSeverity.LOW
        else:
            severity = RiskSeverity.NEGLIGIBLE
        
        return severity, avg_score.quantize(Decimal("0.1"))
    
    # ========================================================================
    # Gap Analysis
    # ========================================================================
    
    def analyze_gaps(
        self,
        qualification: QualificationData,
        criteria: list[CriterionData],
        target_score_percent: Decimal = Decimal("70.0"),
    ) -> list[Gap]:
        """
        Analyze gaps between current scores and targets.
        
        Args:
            qualification: Current qualification data
            criteria: Criterion definitions
            target_score_percent: Target score percentage
            
        Returns:
            List of identified gaps
        """
        gaps = []
        criteria_map = {c.id: c for c in criteria}
        
        for score_data in qualification.scores:
            criterion = criteria_map.get(score_data.criterion_id)
            if not criterion:
                continue
            
            # Calculate required score for target percentage
            required_score = (target_score_percent / Decimal("100")) * score_data.max_score
            
            current_score = score_data.score or Decimal("0")
            gap_amount = required_score - current_score
            
            if gap_amount > Decimal("0"):
                severity = self._determine_gap_severity(gap_amount, criterion)
                
                gaps.append(Gap(
                    criterion_code=criterion.code,
                    criterion_name=criterion.name,
                    severity=severity,
                    current_score=current_score,
                    required_score=required_score.quantize(Decimal("0.1")),
                    gap_amount=gap_amount.quantize(Decimal("0.1")),
                    description=f"Score of {current_score} is below required {required_score.quantize(Decimal('0.1'))}",
                    impact=self._determine_gap_impact(criterion, gap_amount),
                    closing_actions=self._suggest_gap_closing_actions(criterion, gap_amount),
                    estimated_effort=self._estimate_gap_effort(gap_amount),
                    estimated_timeline=self._estimate_gap_timeline(gap_amount, criterion),
                ))
        
        # Sort by severity
        severity_order = {
            GapSeverity.BLOCKING: 0,
            GapSeverity.MAJOR: 1,
            GapSeverity.MINOR: 2,
            GapSeverity.INFORMATIONAL: 3,
        }
        gaps.sort(key=lambda g: severity_order.get(g.severity, 4))
        
        return gaps
    
    def _determine_gap_severity(
        self,
        gap_amount: Decimal,
        criterion: CriterionData,
    ) -> GapSeverity:
        """Determine severity of a gap."""
        if criterion.is_blocker:
            return GapSeverity.BLOCKING
        
        gap_percentage = (gap_amount / criterion.max_score) * 100
        
        if gap_percentage >= Decimal("50"):
            return GapSeverity.MAJOR
        elif gap_percentage >= Decimal("20"):
            return GapSeverity.MINOR
        else:
            return GapSeverity.INFORMATIONAL
    
    def _determine_gap_impact(
        self,
        criterion: CriterionData,
        gap_amount: Decimal,
    ) -> str:
        """Determine impact description for a gap."""
        category = criterion.category.lower()
        
        impact_templates = {
            "technical": "May require additional engineering review or process development",
            "commercial": "Could impact pricing competitiveness or customer satisfaction",
            "capacity": "May require resource allocation changes or investment",
            "quality": "Risk of quality issues or certification challenges",
            "strategic": "May affect long-term business objectives",
            "risk": "Elevated exposure to operational or business risks",
            "supply_chain": "Potential for supply disruptions or delays",
        }
        
        return impact_templates.get(category, "May impact overall qualification result")
    
    def _suggest_gap_closing_actions(
        self,
        criterion: CriterionData,
        gap_amount: Decimal,
    ) -> list[str]:
        """Suggest actions to close a gap."""
        category = criterion.category.lower()
        
        action_suggestions = {
            "technical": [
                "Review technical specifications with engineering team",
                "Assess process capability for key requirements",
                "Identify equipment or tooling needs",
            ],
            "commercial": [
                "Review pricing strategy with sales team",
                "Clarify customer requirements and expectations",
                "Evaluate contract terms and conditions",
            ],
            "capacity": [
                "Assess current and planned capacity utilization",
                "Identify potential resource conflicts",
                "Evaluate outsourcing options if needed",
            ],
            "quality": [
                "Review quality system requirements",
                "Verify certification status for requirements",
                "Assess inspection and testing capabilities",
            ],
            "strategic": [
                "Evaluate alignment with business strategy",
                "Assess long-term customer relationship value",
                "Consider technology roadmap implications",
            ],
        }
        
        return action_suggestions.get(category, ["Review and address criterion requirements"])
    
    def _estimate_gap_effort(self, gap_amount: Decimal) -> str:
        """Estimate effort level to close a gap."""
        if gap_amount >= Decimal("5.0"):
            return "high"
        elif gap_amount >= Decimal("2.0"):
            return "medium"
        else:
            return "low"
    
    def _estimate_gap_timeline(
        self,
        gap_amount: Decimal,
        criterion: CriterionData,
    ) -> str:
        """Estimate timeline to close a gap."""
        if gap_amount >= Decimal("5.0"):
            return "4-8 weeks"
        elif gap_amount >= Decimal("2.0"):
            return "1-3 weeks"
        else:
            return "< 1 week"
    
    # ========================================================================
    # Decision Support
    # ========================================================================
    
    def generate_decision_support(
        self,
        qualification: QualificationData,
        risks: list[IdentifiedRisk],
        gaps: list[Gap],
    ) -> DecisionSupport:
        """
        Generate decision support analysis.
        
        Args:
            qualification: Qualification data
            risks: Identified risks
            gaps: Identified gaps
            
        Returns:
            DecisionSupport object
        """
        decision = DecisionSupport()
        
        # Determine recommendation based on scores
        score = qualification.percentage_score or Decimal("0")
        
        if qualification.has_blockers:
            decision.recommendation = DecisionRecommendation.NO_GO
            decision.confidence = ConfidenceLevel.HIGH
        elif score >= self.go_threshold:
            critical_risks = sum(1 for r in risks if r.severity == RiskSeverity.CRITICAL)
            if critical_risks > 0:
                decision.recommendation = DecisionRecommendation.CONDITIONAL_GO
                decision.confidence = ConfidenceLevel.MEDIUM
            else:
                decision.recommendation = DecisionRecommendation.GO
                decision.confidence = ConfidenceLevel.HIGH
        elif score >= self.conditional_threshold:
            decision.recommendation = DecisionRecommendation.CONDITIONAL_GO
            decision.confidence = ConfidenceLevel.MEDIUM
        elif score >= Decimal("30"):
            decision.recommendation = DecisionRecommendation.NO_GO
            decision.confidence = ConfidenceLevel.MEDIUM
        else:
            decision.recommendation = DecisionRecommendation.NO_GO
            decision.confidence = ConfidenceLevel.HIGH
        
        # Generate score summary
        decision.score_summary = self._generate_score_summary(qualification)
        
        # Extract strengths and concerns
        decision.key_strengths = self._extract_strengths(qualification)
        decision.key_concerns = self._extract_concerns(qualification, risks, gaps)
        
        # Generate conditions for conditional recommendation
        if decision.recommendation == DecisionRecommendation.CONDITIONAL_GO:
            decision.conditions = self._generate_conditions(risks, gaps)
        
        # Risk summary
        decision.risk_summary = self._generate_risk_summary(risks)
        
        # Business case
        decision.business_case = self._generate_business_case(qualification)
        
        # Alternative options
        decision.alternative_options = self._suggest_alternatives(decision.recommendation)
        
        return decision
    
    def _generate_score_summary(self, qualification: QualificationData) -> str:
        """Generate score summary text."""
        score = qualification.percentage_score
        if score is None:
            return "Qualification not yet scored"
        
        total = qualification.total_score or Decimal("0")
        
        if score >= Decimal("80"):
            assessment = "strong qualification"
        elif score >= Decimal("70"):
            assessment = "acceptable qualification"
        elif score >= Decimal("50"):
            assessment = "marginal qualification"
        else:
            assessment = "weak qualification"
        
        return (
            f"Overall score of {score}% indicates {assessment}. "
            f"Total weighted score: {total}"
        )
    
    def _extract_strengths(self, qualification: QualificationData) -> list[str]:
        """Extract key strengths from qualification."""
        strengths = []
        
        for score_data in qualification.scores:
            if score_data.score and score_data.score >= Decimal("8.0"):
                strengths.append(f"Strong performance: {score_data.criterion_code}")
        
        if qualification.percentage_score and qualification.percentage_score >= Decimal("75"):
            strengths.append("Overall qualification score exceeds expectations")
        
        if not qualification.has_blockers:
            strengths.append("No blocking issues identified")
        
        return strengths[:5]  # Limit to top 5
    
    def _extract_concerns(
        self,
        qualification: QualificationData,
        risks: list[IdentifiedRisk],
        gaps: list[Gap],
    ) -> list[str]:
        """Extract key concerns."""
        concerns = []
        
        # Low scores
        for score_data in qualification.scores:
            if score_data.score and score_data.score < Decimal("4.0"):
                concerns.append(f"Low score: {score_data.criterion_code}")
        
        # Critical risks
        for risk in risks:
            if risk.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]:
                concerns.append(f"Risk: {risk.title}")
        
        # Blocking gaps
        for gap in gaps:
            if gap.severity == GapSeverity.BLOCKING:
                concerns.append(f"Blocking gap: {gap.criterion_name}")
        
        return concerns[:5]  # Limit to top 5
    
    def _generate_conditions(
        self,
        risks: list[IdentifiedRisk],
        gaps: list[Gap],
    ) -> list[str]:
        """Generate conditions for conditional approval."""
        conditions = []
        
        # Add conditions for high risks
        for risk in risks:
            if risk.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]:
                if risk.mitigation:
                    conditions.append(risk.mitigation)
        
        # Add conditions for blocking/major gaps
        for gap in gaps:
            if gap.severity in [GapSeverity.BLOCKING, GapSeverity.MAJOR]:
                conditions.append(f"Address {gap.criterion_name} gap before proceeding")
        
        if not conditions:
            conditions.append("Complete all pending criterion evaluations")
        
        return conditions[:5]
    
    def _generate_risk_summary(self, risks: list[IdentifiedRisk]) -> str:
        """Generate risk summary text."""
        if not risks:
            return "No significant risks identified"
        
        critical = sum(1 for r in risks if r.severity == RiskSeverity.CRITICAL)
        high = sum(1 for r in risks if r.severity == RiskSeverity.HIGH)
        medium = sum(1 for r in risks if r.severity == RiskSeverity.MEDIUM)
        
        parts = []
        if critical:
            parts.append(f"{critical} critical")
        if high:
            parts.append(f"{high} high")
        if medium:
            parts.append(f"{medium} medium")
        
        return f"Risk profile: {', '.join(parts)} severity risks identified"
    
    def _generate_business_case(self, qualification: QualificationData) -> str:
        """Generate business case summary."""
        parts = []
        
        if qualification.estimated_value:
            parts.append(f"Estimated value: ${qualification.estimated_value:,.2f}")
        
        if qualification.customer_name:
            parts.append(f"Customer: {qualification.customer_name}")
        
        if not parts:
            return "Business case details not available"
        
        return ". ".join(parts)
    
    def _suggest_alternatives(
        self,
        recommendation: DecisionRecommendation,
    ) -> list[str]:
        """Suggest alternative options."""
        if recommendation == DecisionRecommendation.GO:
            return ["Proceed with quote development", "Consider aggressive pricing to win"]
        elif recommendation == DecisionRecommendation.CONDITIONAL_GO:
            return [
                "Proceed with conditions addressed",
                "Request additional information from customer",
                "Escalate to management for guidance",
            ]
        elif recommendation == DecisionRecommendation.NO_GO:
            return [
                "Decline with explanation to customer",
                "Counter-propose with modified scope",
                "Request timeline extension",
            ]
        else:
            return ["Gather additional information before deciding"]
    
    # ========================================================================
    # Benchmark Comparison
    # ========================================================================
    
    def compare_to_benchmarks(
        self,
        qualification: QualificationData,
        criteria: list[CriterionData] | dict[str, Any] | None = None,
        rfq_context: dict[str, Any] | None = None,
    ) -> list[BenchmarkResult]:
        """
        Compare qualification scores to benchmarks.
        
        Args:
            qualification: Qualification data
            criteria: Criterion definitions
            
        Returns:
            List of benchmark comparison results
        """
        if isinstance(criteria, dict):
            rfq_context = criteria
            criteria = None
        rfq_context = rfq_context or {}

        results = []
        criteria_map = {c.id: c for c in (criteria or [])}
        
        for score_data in qualification.scores:
            criterion = criteria_map.get(score_data.criterion_id)
            category = criterion.category.lower() if criterion else self._get_category_from_code(score_data.criterion_code)
            benchmarks = self._resolve_benchmarks(
                category,
                rfq_context,
                fallback_score=(criterion.max_score if criterion else (score_data.max_score or Decimal("10"))) * Decimal("0.7"),
                max_score=criterion.max_score if criterion else (score_data.max_score or Decimal("10")),
            )
            
            benchmark_score = benchmarks["average_score"]
            current = score_data.score or Decimal("0")
            
            # Determine status
            if current >= benchmark_score + Decimal("1.0"):
                status = "above_benchmark"
            elif current >= benchmark_score - Decimal("1.0"):
                status = "at_benchmark"
            else:
                status = "below_benchmark"
            
            # Calculate percentile (simplified)
            std_dev = benchmarks["std_dev"]
            if std_dev > 0:
                z_score = (current - benchmark_score) / std_dev
                # Simplified percentile calculation
                percentile = min(99, max(1, int(50 + z_score * 25)))
            else:
                percentile = 50
            
            results.append(BenchmarkResult(
                criterion_code=criterion.code if criterion else score_data.criterion_code,
                criterion_name=criterion.name if criterion else score_data.criterion_code,
                current_score=current,
                benchmark_score=benchmark_score,
                percentile=percentile,
                status=status,
                similar_projects=int(rfq_context.get("similar_projects", {}).get(category, 0)),
            ))
        
        return results
    
    # ========================================================================
    # Full Advisory Generation
    # ========================================================================
    
    def generate_advisory(
        self,
        qualification: QualificationData,
        criteria: list[CriterionData],
        rfq_context: dict[str, Any],
    ) -> QualificationAdvisory:
        """
        Generate complete qualification advisory.
        
        Args:
            qualification: Qualification data
            criteria: Criterion definitions
            rfq_context: RFQ context information
            
        Returns:
            Complete QualificationAdvisory
        """
        start_time = datetime.now(timezone.utc)
        
        # Generate scoring recommendations
        scoring_recommendations = self.generate_scoring_recommendations(
            criteria, rfq_context
        )
        
        # Assess risks
        risks, overall_risk_level, risk_score = self.assess_risks(
            qualification, criteria, rfq_context
        )
        
        # Analyze gaps
        gaps = self.analyze_gaps(qualification, criteria)
        
        # Generate decision support
        decision = self.generate_decision_support(qualification, risks, gaps)
        
        # Compare to benchmarks
        benchmarks = self.compare_to_benchmarks(qualification, criteria, rfq_context)
        
        # Generate actions
        actions = self._generate_recommended_actions(risks, gaps)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            qualification, decision, risks, gaps
        )
        
        # Extract key findings
        key_findings = self._extract_key_findings(
            qualification, decision, risks, gaps
        )
        
        # Calculate generation time
        generation_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        advisory = QualificationAdvisory(
            qualification_id=qualification.id,
            advisory_type=AdvisoryType.DECISION_SUPPORT,
            scoring_recommendations=scoring_recommendations,
            identified_risks=risks,
            overall_risk_level=overall_risk_level,
            risk_score=risk_score,
            decision=decision,
            gaps=gaps,
            actions=actions,
            benchmarks=benchmarks,
            executive_summary=executive_summary,
            key_findings=key_findings,
            generated_at=datetime.now(timezone.utc),
            generation_time_ms=generation_time,
        )
        
        # Store advisory
        self._advisories[advisory.id] = advisory
        
        return advisory
    
    def _generate_recommended_actions(
        self,
        risks: list[IdentifiedRisk],
        gaps: list[Gap],
    ) -> list[RecommendedAction]:
        """Generate recommended actions from risks and gaps."""
        actions = []
        
        # Actions from risks
        for risk in risks:
            if risk.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]:
                priority = ActionPriority.IMMEDIATE if risk.severity == RiskSeverity.CRITICAL else ActionPriority.HIGH
                actions.append(RecommendedAction(
                    priority=priority,
                    title=f"Mitigate: {risk.title}",
                    description=risk.mitigation or f"Address {risk.description}",
                    expected_outcome="Risk level reduced",
                    responsible_role="Program Manager",
                    timeline="Within 1 week" if priority == ActionPriority.IMMEDIATE else "Within 2 weeks",
                    related_risks=[risk.id],
                ))
        
        # Actions from gaps
        for gap in gaps:
            if gap.severity in [GapSeverity.BLOCKING, GapSeverity.MAJOR]:
                priority = ActionPriority.IMMEDIATE if gap.severity == GapSeverity.BLOCKING else ActionPriority.HIGH
                actions.append(RecommendedAction(
                    priority=priority,
                    title=f"Close Gap: {gap.criterion_name}",
                    description=f"Improve score from {gap.current_score} to {gap.required_score}",
                    expected_outcome="Gap closed, score improved",
                    responsible_role="Technical Lead",
                    timeline=gap.estimated_timeline or "TBD",
                    related_gaps=[gap.id],
                ))
        
        # Sort by priority
        priority_order = {
            ActionPriority.IMMEDIATE: 0,
            ActionPriority.HIGH: 1,
            ActionPriority.MEDIUM: 2,
            ActionPriority.LOW: 3,
        }
        actions.sort(key=lambda a: priority_order.get(a.priority, 4))
        
        return actions
    
    def _generate_executive_summary(
        self,
        qualification: QualificationData,
        decision: DecisionSupport,
        risks: list[IdentifiedRisk],
        gaps: list[Gap],
    ) -> str:
        """Generate executive summary."""
        recommendation_text = {
            DecisionRecommendation.GO: "proceed with quote",
            DecisionRecommendation.CONDITIONAL_GO: "proceed with conditions",
            DecisionRecommendation.NO_GO: "not proceed",
            DecisionRecommendation.NEEDS_MORE_INFO: "gather more information",
            DecisionRecommendation.ESCALATE: "escalate for management review",
        }
        
        rec_text = recommendation_text.get(decision.recommendation, "review further")
        
        summary = f"""
Qualification Advisory Summary

RFQ: {qualification.customer_name or 'Unknown'} - {qualification.part_description or 'Unknown'}
Overall Score: {qualification.percentage_score or 'N/A'}%
Recommendation: {decision.recommendation.value.upper()} - {rec_text}
Confidence: {decision.confidence.value}

Risk Profile: {len(risks)} risks identified, {len([r for r in risks if r.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]])} require attention
Gaps: {len(gaps)} capability gaps identified, {len([g for g in gaps if g.severity in [GapSeverity.BLOCKING, GapSeverity.MAJOR]])} are significant

Key Points:
{chr(10).join('- ' + s for s in decision.key_strengths[:3]) if decision.key_strengths else '- No major strengths noted'}

Concerns:
{chr(10).join('- ' + c for c in decision.key_concerns[:3]) if decision.key_concerns else '- No major concerns noted'}
""".strip()
        
        return summary
    
    def _extract_key_findings(
        self,
        qualification: QualificationData,
        decision: DecisionSupport,
        risks: list[IdentifiedRisk],
        gaps: list[Gap],
    ) -> list[str]:
        """Extract key findings."""
        findings = []
        
        # Score-based findings
        if qualification.percentage_score is not None:
            if qualification.percentage_score >= Decimal("80"):
                findings.append("Strong overall qualification score")
            elif qualification.percentage_score < Decimal("50"):
                findings.append("Overall score below acceptable threshold")
        
        # Risk findings
        critical_risks = [r for r in risks if r.severity == RiskSeverity.CRITICAL]
        if critical_risks:
            findings.append(f"{len(critical_risks)} critical risk(s) require immediate attention")
        
        # Gap findings
        blocking_gaps = [g for g in gaps if g.severity == GapSeverity.BLOCKING]
        if blocking_gaps:
            findings.append(f"{len(blocking_gaps)} blocking gap(s) must be resolved")
        
        # Blocker findings
        if qualification.has_blockers:
            findings.append("Qualification has active blockers preventing approval")
        
        return findings
    
    # ========================================================================
    # Retrieval Methods
    # ========================================================================
    
    def get_advisory(self, advisory_id: UUID) -> Optional[QualificationAdvisory]:
        """Get stored advisory by ID."""
        return self._advisories.get(advisory_id)
    
    def list_advisories(
        self,
        qualification_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> list[QualificationAdvisory]:
        """List stored advisories."""
        advisories = list(self._advisories.values())
        
        if qualification_id:
            advisories = [a for a in advisories if a.qualification_id == qualification_id]
        
        advisories.sort(key=lambda a: a.generated_at, reverse=True)
        
        return advisories[:limit]
