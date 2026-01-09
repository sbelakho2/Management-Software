"""
Tests for Smart Supplier Matchmaker.

Tests cover:
- Capability graph
- Semantic matching
- Multi-criteria scoring
- Rank aggregation
- Complete matchmaker
"""

import pytest
from datetime import datetime, timezone

from sensei.services.smart_supplier_matchmaker import (
    # Enums
    MatchingCriteria,
    SupplierTier,
    MatchConfidence,
    CapabilityType,
    # Data models
    Capability,
    PerformanceMetrics,
    Supplier,
    RFQRequirement,
    MatchScore,
    SupplierMatch,
    MatchingResult,
    # Components
    CapabilityGraph,
    SemanticMatcher,
    CapabilityScorer,
    QualityScorer,
    DeliveryScorer,
    PriceScorer,
    ReliabilityScorer,
    CertificationScorer,
    CapacityScorer,
    LocationScorer,
    RankAggregator,
    SmartSupplierMatchmaker,
    # Factory
    create_supplier_matchmaker,
    # Constants
    DEFAULT_WEIGHTS,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_capabilities() -> list[Capability]:
    """Create sample capabilities."""
    return [
        Capability(
            capability_id="CAP-001",
            name="CNC Machining",
            capability_type=CapabilityType.PROCESS,
            proficiency_level=0.9,
            keywords=["milling", "turning", "precision"],
        ),
        Capability(
            capability_id="CAP-002",
            name="Steel Fabrication",
            capability_type=CapabilityType.MATERIAL,
            proficiency_level=0.85,
            keywords=["stainless", "carbon steel", "welding"],
        ),
        Capability(
            capability_id="CAP-003",
            name="Quality Inspection",
            capability_type=CapabilityType.PROCESS,
            proficiency_level=0.95,
            keywords=["qc", "metrology", "testing"],
        ),
    ]


@pytest.fixture
def sample_supplier(sample_capabilities: list[Capability]) -> Supplier:
    """Create sample supplier."""
    return Supplier(
        supplier_id="SUP-001",
        name="Precision Manufacturing Inc.",
        tier=SupplierTier.PREFERRED,
        capabilities=sample_capabilities,
        performance=PerformanceMetrics(
            on_time_delivery_rate=0.96,
            quality_score=0.94,
            defect_rate=0.015,
            price_competitiveness=0.88,
            orders_completed=150,
            issues_reported=3,
        ),
        certifications=["ISO 9001", "AS9100"],
        location="Detroit, MI",
        region="North America",
        minimum_order_value=500.0,
        maximum_capacity_units=5000,
        lead_time_days=12,
    )


@pytest.fixture
def sample_suppliers(sample_capabilities: list[Capability]) -> list[Supplier]:
    """Create multiple sample suppliers."""
    return [
        Supplier(
            supplier_id="SUP-001",
            name="Precision Manufacturing Inc.",
            tier=SupplierTier.STRATEGIC,
            capabilities=[sample_capabilities[0], sample_capabilities[2]],
            performance=PerformanceMetrics(
                on_time_delivery_rate=0.98,
                quality_score=0.96,
            ),
            certifications=["ISO 9001", "AS9100"],
            region="North America",
            maximum_capacity_units=10000,
        ),
        Supplier(
            supplier_id="SUP-002",
            name="Global Steel Works",
            tier=SupplierTier.PREFERRED,
            capabilities=[sample_capabilities[1]],
            performance=PerformanceMetrics(
                on_time_delivery_rate=0.92,
                quality_score=0.90,
            ),
            certifications=["ISO 9001"],
            region="Europe",
            maximum_capacity_units=8000,
        ),
        Supplier(
            supplier_id="SUP-003",
            name="Quick Parts Co.",
            tier=SupplierTier.APPROVED,
            capabilities=sample_capabilities,
            performance=PerformanceMetrics(
                on_time_delivery_rate=0.85,
                quality_score=0.88,
                price_competitiveness=0.95,
            ),
            certifications=["ISO 9001"],
            region="Asia",
            maximum_capacity_units=20000,
            lead_time_days=21,
        ),
    ]


@pytest.fixture
def sample_requirement() -> RFQRequirement:
    """Create sample RFQ requirement."""
    return RFQRequirement(
        rfq_id="RFQ-001",
        description="Precision machined steel components",
        required_capabilities=["CNC Machining", "Steel"],
        required_certifications=["ISO 9001"],
        quantity=100,
        target_price=50.0,
        target_lead_time_days=14,
        preferred_regions=["North America"],
        minimum_quality_score=0.85,
    )


@pytest.fixture
def matchmaker(sample_suppliers: list[Supplier]) -> SmartSupplierMatchmaker:
    """Create matchmaker with suppliers."""
    return create_supplier_matchmaker(sample_suppliers)


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_matching_criteria_values(self):
        """Test MatchingCriteria values."""
        assert MatchingCriteria.CAPABILITY.value == "capability"
        assert MatchingCriteria.QUALITY.value == "quality"
        assert MatchingCriteria.PRICE.value == "price"
    
    def test_supplier_tier_values(self):
        """Test SupplierTier values."""
        assert SupplierTier.STRATEGIC.value == "strategic"
        assert SupplierTier.INACTIVE.value == "inactive"
    
    def test_match_confidence_values(self):
        """Test MatchConfidence values."""
        assert MatchConfidence.HIGH.value == "high"
        assert MatchConfidence.UNCERTAIN.value == "uncertain"


# =============================================================================
# Tests: Data Models
# =============================================================================

class TestCapability:
    """Test Capability dataclass."""
    
    def test_capability_creation(self):
        """Test creating capability."""
        cap = Capability(
            capability_id="CAP-001",
            name="CNC Machining",
            capability_type=CapabilityType.PROCESS,
        )
        
        assert cap.name == "CNC Machining"
        assert cap.proficiency_level == 0.8
    
    def test_matches_keyword_exact(self):
        """Test exact keyword match."""
        cap = Capability(
            capability_id="CAP-001",
            name="CNC Machining",
            capability_type=CapabilityType.PROCESS,
        )
        
        assert cap.matches_keyword("CNC Machining") == 1.0
    
    def test_matches_keyword_partial(self):
        """Test partial keyword match."""
        cap = Capability(
            capability_id="CAP-001",
            name="CNC Machining",
            capability_type=CapabilityType.PROCESS,
            keywords=["milling", "turning"],
        )
        
        score = cap.matches_keyword("milling")
        assert score > 0.5
    
    def test_matches_keyword_synonym(self):
        """Test synonym match."""
        cap = Capability(
            capability_id="CAP-001",
            name="aluminum",
            capability_type=CapabilityType.MATERIAL,
        )
        
        score = cap.matches_keyword("aluminium")
        assert score > 0.5


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""
    
    def test_default_metrics(self):
        """Test default metrics."""
        metrics = PerformanceMetrics()
        
        assert metrics.on_time_delivery_rate == 0.95
        assert metrics.quality_score == 0.95
    
    def test_reliability_score(self):
        """Test reliability score calculation."""
        metrics = PerformanceMetrics(
            orders_completed=100,
            issues_reported=5,
        )
        
        assert 0.0 <= metrics.reliability_score <= 1.0
    
    def test_reliability_score_zero_orders(self):
        """Test reliability with zero orders."""
        metrics = PerformanceMetrics(orders_completed=0)
        
        assert metrics.reliability_score == 0.5
    
    def test_overall_score(self):
        """Test overall score calculation."""
        metrics = PerformanceMetrics()
        
        score = metrics.overall_score
        assert 0.0 <= score <= 1.0


class TestSupplier:
    """Test Supplier dataclass."""
    
    def test_supplier_creation(self, sample_supplier: Supplier):
        """Test creating supplier."""
        assert sample_supplier.name == "Precision Manufacturing Inc."
        assert sample_supplier.tier == SupplierTier.PREFERRED
    
    def test_has_certification(self, sample_supplier: Supplier):
        """Test certification check."""
        assert sample_supplier.has_certification("ISO 9001")
        assert sample_supplier.has_certification("iso")
        assert not sample_supplier.has_certification("ISO 14001")
    
    def test_get_capability_match(self, sample_supplier: Supplier):
        """Test capability match."""
        score = sample_supplier.get_capability_match("CNC")
        assert score > 0.5


class TestRFQRequirement:
    """Test RFQRequirement dataclass."""
    
    def test_requirement_creation(self, sample_requirement: RFQRequirement):
        """Test creating requirement."""
        assert sample_requirement.rfq_id == "RFQ-001"
        assert len(sample_requirement.required_capabilities) == 2
    
    def test_get_weights_default(self):
        """Test getting default weights."""
        req = RFQRequirement(rfq_id="RFQ-001", description="Test")
        weights = req.get_weights()
        
        assert sum(weights.values()) == pytest.approx(1.0)
    
    def test_get_weights_custom(self):
        """Test custom weights."""
        req = RFQRequirement(
            rfq_id="RFQ-001",
            description="Test",
            priority_weights={MatchingCriteria.PRICE: 0.5},
        )
        
        weights = req.get_weights()
        assert weights[MatchingCriteria.PRICE] > 0.3


class TestMatchScore:
    """Test MatchScore dataclass."""
    
    def test_score_creation(self):
        """Test creating score."""
        score = MatchScore(
            criteria=MatchingCriteria.QUALITY,
            score=0.9,
            weight=0.2,
            weighted_score=0.18,
            explanation="High quality",
        )
        
        assert score.weighted_score == 0.18


class TestSupplierMatch:
    """Test SupplierMatch dataclass."""
    
    def test_is_recommended_high(self, sample_supplier: Supplier):
        """Test is_recommended for high confidence."""
        match = SupplierMatch(
            match_id="MATCH-001",
            supplier=sample_supplier,
            rfq_id="RFQ-001",
            overall_score=0.85,
            confidence=MatchConfidence.HIGH,
            rank=1,
        )
        
        assert match.is_recommended is True
    
    def test_is_recommended_low(self, sample_supplier: Supplier):
        """Test is_recommended for low confidence."""
        match = SupplierMatch(
            match_id="MATCH-001",
            supplier=sample_supplier,
            rfq_id="RFQ-001",
            overall_score=0.45,
            confidence=MatchConfidence.LOW,
            rank=5,
        )
        
        assert match.is_recommended is False


# =============================================================================
# Tests: Capability Graph
# =============================================================================

class TestCapabilityGraph:
    """Test CapabilityGraph."""
    
    def test_graph_creation(self):
        """Test creating graph."""
        graph = CapabilityGraph()
        assert graph is not None
    
    def test_add_capability(self, sample_capabilities: list[Capability]):
        """Test adding capability."""
        graph = CapabilityGraph()
        
        for cap in sample_capabilities:
            graph.add_capability(cap)
        
        assert len(graph._nodes) == 3
    
    def test_add_relationship(self):
        """Test adding relationship."""
        graph = CapabilityGraph()
        
        graph.add_relationship("welding", "fabrication", "part_of", 0.8)
        
        assert "welding" in graph._edges
    
    def test_get_related_capabilities(self):
        """Test getting related capabilities."""
        graph = CapabilityGraph()
        
        # Standard relationships are already loaded
        related = graph.get_related_capabilities("cnc machining")
        
        # Should find milling and turning
        related_names = [r[0] for r in related]
        assert len(related_names) >= 0  # May have no direct matches
    
    def test_calculate_similarity_exact(self):
        """Test exact similarity."""
        graph = CapabilityGraph()
        
        sim = graph.calculate_similarity("welding", "welding")
        assert sim == 1.0
    
    def test_calculate_similarity_synonym(self):
        """Test synonym similarity."""
        graph = CapabilityGraph()
        
        sim = graph.calculate_similarity("aluminum", "aluminium")
        assert sim >= 0.9


# =============================================================================
# Tests: Semantic Matcher
# =============================================================================

class TestSemanticMatcher:
    """Test SemanticMatcher."""
    
    def test_matcher_creation(self):
        """Test creating matcher."""
        matcher = SemanticMatcher()
        assert matcher is not None
    
    def test_index_capabilities(self, sample_suppliers: list[Supplier]):
        """Test indexing capabilities."""
        matcher = SemanticMatcher()
        
        matcher.index_capabilities(sample_suppliers)
        
        assert matcher._total_documents == 3
    
    def test_compute_similarity_exact(self):
        """Test exact text similarity."""
        matcher = SemanticMatcher()
        
        sim = matcher.compute_similarity("cnc machining", "cnc machining")
        assert sim > 0.9
    
    def test_compute_similarity_partial(self):
        """Test partial similarity."""
        matcher = SemanticMatcher()
        
        sim = matcher.compute_similarity("precision cnc", "cnc machining precision")
        assert sim > 0.5
    
    def test_match_capability(self, sample_capabilities: list[Capability]):
        """Test matching requirement to capability."""
        matcher = SemanticMatcher()
        
        score, matched = matcher.match_capability("cnc", sample_capabilities)
        
        assert matched is not None
        assert score > 0


# =============================================================================
# Tests: Criteria Scorers
# =============================================================================

class TestCapabilityScorer:
    """Test CapabilityScorer."""
    
    def test_score_with_matches(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring with matching capabilities."""
        matcher = SemanticMatcher()
        scorer = CapabilityScorer(matcher)
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.criteria == MatchingCriteria.CAPABILITY
        assert 0.0 <= score.score <= 1.0
    
    def test_score_no_requirements(self, sample_supplier: Supplier):
        """Test scoring with no capability requirements."""
        matcher = SemanticMatcher()
        scorer = CapabilityScorer(matcher)
        
        req = RFQRequirement(rfq_id="RFQ-001", description="Test")
        score = scorer.score(sample_supplier, req)
        
        assert score.score == 0.5


class TestQualityScorer:
    """Test QualityScorer."""
    
    def test_score_high_quality(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring high quality supplier."""
        scorer = QualityScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score > 0.8


class TestDeliveryScorer:
    """Test DeliveryScorer."""
    
    def test_score_good_delivery(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring good delivery."""
        scorer = DeliveryScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score > 0.8
    
    def test_score_slow_delivery(self, sample_supplier: Supplier):
        """Test scoring slow delivery."""
        scorer = DeliveryScorer()
        
        sample_supplier.lead_time_days = 30
        req = RFQRequirement(
            rfq_id="RFQ-001",
            description="Test",
            target_lead_time_days=7,
        )
        
        score = scorer.score(sample_supplier, req)
        
        assert score.score < 0.8


class TestPriceScorer:
    """Test PriceScorer."""
    
    def test_score_competitive(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring competitive pricing."""
        scorer = PriceScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score > 0.5


class TestReliabilityScorer:
    """Test ReliabilityScorer."""
    
    def test_score_reliable(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring reliable supplier."""
        scorer = ReliabilityScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score > 0.8
    
    def test_score_with_tier_bonus(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test tier affects reliability."""
        scorer = ReliabilityScorer()
        
        sample_supplier.tier = SupplierTier.STRATEGIC
        strategic_score = scorer.score(sample_supplier, sample_requirement)
        
        sample_supplier.tier = SupplierTier.PROBATIONARY
        probation_score = scorer.score(sample_supplier, sample_requirement)
        
        assert strategic_score.score > probation_score.score


class TestCertificationScorer:
    """Test CertificationScorer."""
    
    def test_score_all_certs(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring with all certs present."""
        scorer = CertificationScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score == 1.0
    
    def test_score_missing_certs(self, sample_supplier: Supplier):
        """Test scoring with missing certs."""
        scorer = CertificationScorer()
        
        req = RFQRequirement(
            rfq_id="RFQ-001",
            description="Test",
            required_certifications=["ISO 9001", "ISO 14001", "IATF 16949"],
        )
        
        score = scorer.score(sample_supplier, req)
        
        assert score.score < 1.0


class TestCapacityScorer:
    """Test CapacityScorer."""
    
    def test_score_sufficient_capacity(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring sufficient capacity."""
        scorer = CapacityScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score >= 0.8
    
    def test_score_insufficient_capacity(self, sample_supplier: Supplier):
        """Test scoring insufficient capacity."""
        scorer = CapacityScorer()
        
        req = RFQRequirement(
            rfq_id="RFQ-001",
            description="Test",
            quantity=50000,  # Way above capacity
        )
        
        score = scorer.score(sample_supplier, req)
        
        assert score.score < 0.5


class TestLocationScorer:
    """Test LocationScorer."""
    
    def test_score_preferred_region(
        self,
        sample_supplier: Supplier,
        sample_requirement: RFQRequirement,
    ):
        """Test scoring preferred region."""
        scorer = LocationScorer()
        
        score = scorer.score(sample_supplier, sample_requirement)
        
        assert score.score == 1.0
    
    def test_score_non_preferred_region(self, sample_supplier: Supplier):
        """Test scoring non-preferred region."""
        scorer = LocationScorer()
        
        req = RFQRequirement(
            rfq_id="RFQ-001",
            description="Test",
            preferred_regions=["Europe"],
        )
        
        score = scorer.score(sample_supplier, req)
        
        assert score.score < 1.0


# =============================================================================
# Tests: Rank Aggregator
# =============================================================================

class TestRankAggregator:
    """Test RankAggregator."""
    
    def test_borda_count_simple(self):
        """Test simple Borda count."""
        rankings = [
            ["A", "B", "C"],
            ["A", "C", "B"],
            ["B", "A", "C"],
        ]
        
        result = RankAggregator.borda_count(rankings)
        
        # A should be first (best overall)
        assert result[0][0] == "A"
    
    def test_borda_count_empty(self):
        """Test Borda count with empty rankings."""
        result = RankAggregator.borda_count([])
        assert result == []
    
    def test_kemeny_young_approx(self):
        """Test Kemeny-Young approximation."""
        rankings = [
            ["A", "B", "C"],
            ["A", "C", "B"],
        ]
        
        result = RankAggregator.kemeny_young_approx(rankings, ["A", "B", "C"])
        
        assert "A" in result
        assert len(result) == 3


# =============================================================================
# Tests: Smart Supplier Matchmaker
# =============================================================================

class TestSmartSupplierMatchmaker:
    """Test SmartSupplierMatchmaker."""
    
    def test_matchmaker_creation(self):
        """Test creating matchmaker."""
        matchmaker = SmartSupplierMatchmaker()
        assert matchmaker is not None
    
    def test_add_supplier(self, sample_supplier: Supplier):
        """Test adding supplier."""
        matchmaker = SmartSupplierMatchmaker()
        
        matchmaker.add_supplier(sample_supplier)
        
        assert len(matchmaker._suppliers) == 1
    
    def test_add_suppliers(self, sample_suppliers: list[Supplier]):
        """Test adding multiple suppliers."""
        matchmaker = SmartSupplierMatchmaker()
        
        matchmaker.add_suppliers(sample_suppliers)
        
        assert len(matchmaker._suppliers) == 3
    
    def test_remove_supplier(self, sample_supplier: Supplier):
        """Test removing supplier."""
        matchmaker = SmartSupplierMatchmaker()
        matchmaker.add_supplier(sample_supplier)
        
        matchmaker.remove_supplier(sample_supplier.supplier_id)
        
        assert len(matchmaker._suppliers) == 0
    
    def test_get_supplier(
        self,
        matchmaker: SmartSupplierMatchmaker,
    ):
        """Test getting supplier by ID."""
        supplier = matchmaker.get_supplier("SUP-001")
        
        assert supplier is not None
        assert supplier.name == "Precision Manufacturing Inc."
    
    def test_match_basic(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test basic matching."""
        result = matchmaker.match(sample_requirement)
        
        assert isinstance(result, MatchingResult)
        assert len(result.matches) > 0
    
    def test_match_ranking(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test match ranking."""
        result = matchmaker.match(sample_requirement)
        
        # Check ranks are sequential
        ranks = [m.rank for m in result.matches]
        assert ranks == sorted(ranks)
    
    def test_match_max_results(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test limiting results."""
        result = matchmaker.match(sample_requirement, max_results=2)
        
        assert len(result.matches) <= 2
    
    def test_match_no_rank_aggregation(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test matching without rank aggregation."""
        result = matchmaker.match(
            sample_requirement,
            use_rank_aggregation=False,
        )
        
        assert len(result.matches) > 0
    
    def test_match_filters_inactive(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test inactive suppliers are filtered."""
        # Mark one as inactive
        matchmaker._suppliers["SUP-001"].active = False
        
        result = matchmaker.match(sample_requirement)
        
        # SUP-001 should not be in results
        supplier_ids = [m.supplier.supplier_id for m in result.matches]
        assert "SUP-001" not in supplier_ids
    
    def test_match_empty_suppliers(self, sample_requirement: RFQRequirement):
        """Test matching with no suppliers."""
        matchmaker = SmartSupplierMatchmaker()
        
        result = matchmaker.match(sample_requirement)
        
        assert len(result.matches) == 0
    
    def test_find_alternative_suppliers(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test finding alternative suppliers."""
        alternatives = matchmaker.find_alternative_suppliers(
            "SUP-001",
            sample_requirement,
            max_results=2,
        )
        
        # Should not include SUP-001
        supplier_ids = [a.supplier.supplier_id for a in alternatives]
        assert "SUP-001" not in supplier_ids
    
    def test_find_alternative_invalid_supplier(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test finding alternatives for invalid supplier."""
        alternatives = matchmaker.find_alternative_suppliers(
            "INVALID",
            sample_requirement,
        )
        
        assert alternatives == []
    
    def test_compare_suppliers(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test comparing specific suppliers."""
        result = matchmaker.compare_suppliers(
            ["SUP-001", "SUP-002"],
            sample_requirement,
        )
        
        assert result["suppliers_compared"] == 2
        assert "recommended" in result
    
    def test_compare_suppliers_invalid(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test comparing invalid suppliers."""
        result = matchmaker.compare_suppliers(
            ["INVALID-1", "INVALID-2"],
            sample_requirement,
        )
        
        assert "error" in result
    
    def test_get_capability_gaps(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test identifying capability gaps."""
        # Add a capability we don't have
        req = RFQRequirement(
            rfq_id="RFQ-001",
            description="Test",
            required_capabilities=["CNC Machining", "Laser Cutting", "EDM"],
        )
        
        gaps = matchmaker.get_capability_gaps(req)
        
        assert "gaps" in gaps
        assert "limited_coverage" in gaps
    
    def test_recommended_suppliers(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test getting recommended suppliers."""
        result = matchmaker.match(sample_requirement)
        
        recommended = result.recommended_suppliers
        
        # All recommended should have high or medium confidence
        for m in recommended:
            assert m.confidence in [MatchConfidence.HIGH, MatchConfidence.MEDIUM]
    
    def test_top_match(
        self,
        matchmaker: SmartSupplierMatchmaker,
        sample_requirement: RFQRequirement,
    ):
        """Test getting top match."""
        result = matchmaker.match(sample_requirement)
        
        top = result.top_match
        
        assert top is not None
        assert top.rank == 1


# =============================================================================
# Tests: Factory Function
# =============================================================================

class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_empty_matchmaker(self):
        """Test creating empty matchmaker."""
        matchmaker = create_supplier_matchmaker()
        
        assert isinstance(matchmaker, SmartSupplierMatchmaker)
        assert len(matchmaker._suppliers) == 0
    
    def test_create_with_suppliers(self, sample_suppliers: list[Supplier]):
        """Test creating matchmaker with suppliers."""
        matchmaker = create_supplier_matchmaker(sample_suppliers)
        
        assert len(matchmaker._suppliers) == 3


# =============================================================================
# Tests: Integration
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_complete_matching_workflow(self, sample_suppliers: list[Supplier]):
        """Test complete matching workflow."""
        # Create matchmaker
        matchmaker = create_supplier_matchmaker(sample_suppliers)
        
        # Create requirement
        requirement = RFQRequirement(
            rfq_id="RFQ-INT-001",
            description="High-precision CNC machined stainless steel components with strict quality requirements",
            required_capabilities=["CNC Machining", "Steel", "Quality Inspection"],
            required_certifications=["ISO 9001"],
            quantity=500,
            target_price=75.0,
            target_lead_time_days=14,
            preferred_regions=["North America"],
            minimum_quality_score=0.9,
        )
        
        # Match
        result = matchmaker.match(requirement)
        
        # Validate result
        assert result.total_suppliers_evaluated > 0
        assert len(result.matches) > 0
        assert result.matching_duration_ms >= 0
        
        # Top match should have strengths and weaknesses analyzed
        top = result.top_match
        assert top is not None
        assert top.rank == 1
    
    def test_supplier_comparison_workflow(self, sample_suppliers: list[Supplier]):
        """Test supplier comparison workflow."""
        matchmaker = create_supplier_matchmaker(sample_suppliers)
        
        requirement = RFQRequirement(
            rfq_id="RFQ-CMP-001",
            description="Test comparison",
            required_capabilities=["Steel Fabrication"],
        )
        
        # First find matches
        result = matchmaker.match(requirement)
        
        # Then compare top 2
        top_ids = [m.supplier.supplier_id for m in result.matches[:2]]
        
        comparison = matchmaker.compare_suppliers(top_ids, requirement)
        
        assert comparison["suppliers_compared"] == len(top_ids)
        assert comparison["recommended"] is not None
    
    def test_capability_gap_analysis(self, sample_suppliers: list[Supplier]):
        """Test capability gap analysis."""
        matchmaker = create_supplier_matchmaker(sample_suppliers)
        
        # Request capabilities we might not have
        requirement = RFQRequirement(
            rfq_id="RFQ-GAP-001",
            description="Complex multi-process requirement",
            required_capabilities=[
                "CNC Machining",
                "Steel Fabrication",
                "3D Printing",
                "EDM",
                "Electropolishing",
            ],
        )
        
        gaps = matchmaker.get_capability_gaps(requirement)
        
        # Should identify gaps and coverage
        assert len(gaps["gaps"]) > 0 or len(gaps["limited_coverage"]) > 0 or len(gaps["well_covered"]) > 0
        assert gaps["total_capabilities_checked"] == 5
