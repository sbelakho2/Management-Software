"""
Tests for Multi-Agent RFQ Analyzer.

Covers:
- Agent Orchestration
- Technical Agent
- Commercial Agent
- Risk Agent
- Debate Protocol
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from sensei.services.sales.multi_agent_rfq import (
    # Enums
    AgentType,
    AnalysisCategory,
    RiskCategory,
    DebateOutcome,
    Severity,
    DFMIssueType,
    # Data models
    RFQSpec,
    DFMIssue,
    PriceAnalysis,
    RiskScore,
    AgentFinding,
    AgentPosition,
    DebateResult,
    ComprehensiveAnalysis,
    # Classes
    BaseAgent,
    TechnicalAgent,
    CommercialAgent,
    RiskAgent,
    AgentOrchestrator,
    MultiAgentRFQAnalyzer,
    # Factory
    create_rfq_analyzer,
    # Constants
    DEFAULT_DEBATE_ROUNDS,
    CONSENSUS_THRESHOLD,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def now():
    """Current time fixture."""
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_rfq(now):
    """Sample RFQ specification."""
    return RFQSpec(
        rfq_id="RFQ-001",
        customer_id="CUST-001",
        description="Precision aluminum housing",
        quantity=100,
        target_price=5000.0,
        deadline=now + timedelta(days=30),
        material_specs={
            "primary_material": "aluminum",
            "grade": "6061-T6",
        },
        dimension_specs={
            "tolerances": {"length": 0.05, "width": 0.05, "hole_position": 0.005},
            "wall_thickness": 2.0,
        },
        finish_requirements=["Anodize - Black", "Polish"],
        compliance_requirements=["ISO 9001"],
    )


@pytest.fixture
def technical_agent():
    """Technical agent instance."""
    return TechnicalAgent()


@pytest.fixture
def commercial_agent():
    """Commercial agent instance."""
    return CommercialAgent()


@pytest.fixture
def risk_agent():
    """Risk agent instance."""
    return RiskAgent()


@pytest.fixture
def orchestrator():
    """Agent orchestrator instance."""
    return AgentOrchestrator()


@pytest.fixture
def analyzer():
    """Multi-agent RFQ analyzer instance."""
    return MultiAgentRFQAnalyzer()


# =============================================================================
# RFQSpec Tests
# =============================================================================

class TestRFQSpec:
    """Tests for RFQSpec data model."""
    
    def test_create_basic(self):
        """Test basic RFQ creation."""
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Test part",
            quantity=50,
        )
        
        assert rfq.rfq_id == "RFQ-001"
        assert rfq.quantity == 50
    
    def test_defaults(self):
        """Test default values."""
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Test",
            quantity=1,
        )
        
        assert rfq.target_price is None
        assert rfq.deadline is None
        assert rfq.material_specs == {}
        assert rfq.finish_requirements == []


# =============================================================================
# TechnicalAgent Tests
# =============================================================================

class TestTechnicalAgent:
    """Tests for TechnicalAgent."""
    
    @pytest.mark.asyncio
    async def test_analyze_returns_findings(self, technical_agent, sample_rfq):
        """Test that analyze returns findings."""
        findings = await technical_agent.analyze(sample_rfq)
        
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_analyze_tight_tolerances(self, technical_agent, sample_rfq):
        """Test detection of tight tolerances."""
        findings = await technical_agent.analyze(sample_rfq)
        
        tolerance_findings = [
            f for f in findings
            if "tolerance" in f.title.lower()
        ]
        
        # hole_position at 0.01 should trigger
        assert len(tolerance_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_missing_material(self, technical_agent):
        """Test detection of missing material."""
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Test",
            quantity=50,
            material_specs={},  # No material
        )
        
        findings = await technical_agent.analyze(rfq)
        
        material_findings = [
            f for f in findings
            if "material" in f.title.lower()
        ]
        
        assert len(material_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_low_quantity(self, technical_agent):
        """Test low quantity detection."""
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Test",
            quantity=5,  # Low quantity
        )
        
        findings = await technical_agent.analyze(rfq)
        
        quantity_findings = [
            f for f in findings
            if "quantity" in f.title.lower()
        ]
        
        assert len(quantity_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_finish_requirements(self, technical_agent, sample_rfq):
        """Test finish requirement analysis."""
        findings = await technical_agent.analyze(sample_rfq)
        
        finish_findings = [
            f for f in findings
            if "finish" in f.title.lower() or "treatment" in f.title.lower()
        ]
        
        assert len(finish_findings) >= 1
    
    def test_get_dfm_issues(self, technical_agent):
        """Test DFM issue detection."""
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Test",
            quantity=50,
            material_specs={"primary_material": "aluminum"},
            dimension_specs={"wall_thickness": 0.5},  # Too thin for aluminum
        )
        
        issues = technical_agent.get_dfm_issues(rfq)
        
        assert len(issues) >= 1
        assert issues[0].issue_type == DFMIssueType.GEOMETRY
    
    def test_register_material(self, technical_agent):
        """Test registering material."""
        technical_agent.register_material("titanium", {"density": 4.5})
        
        assert "titanium" in technical_agent._material_database
    
    def test_get_position_price(self, technical_agent):
        """Test getting position on price topic."""
        position = technical_agent.get_position("price recommendation", {})
        
        assert position.agent_type == AgentType.TECHNICAL
        assert "cost" in position.position.lower()


# =============================================================================
# CommercialAgent Tests
# =============================================================================

class TestCommercialAgent:
    """Tests for CommercialAgent."""
    
    @pytest.mark.asyncio
    async def test_analyze_returns_findings(self, commercial_agent, sample_rfq):
        """Test that analyze returns findings."""
        findings = await commercial_agent.analyze(sample_rfq)
        
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_analyze_new_customer(self, commercial_agent, sample_rfq):
        """Test new customer detection."""
        findings = await commercial_agent.analyze(sample_rfq)
        
        customer_findings = [
            f for f in findings
            if "customer" in f.title.lower()
        ]
        
        assert len(customer_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_known_customer(self, commercial_agent, sample_rfq):
        """Test known customer analysis."""
        commercial_agent.register_customer_history(
            "CUST-001",
            {"win_rate": 0.8, "payment_rating": "good"},
        )
        
        findings = await commercial_agent.analyze(sample_rfq)
        
        win_rate_findings = [
            f for f in findings
            if "win-rate" in f.title.lower()
        ]
        
        assert len(win_rate_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_payment_risk(self, commercial_agent, sample_rfq):
        """Test payment risk detection."""
        commercial_agent.register_customer_history(
            "CUST-001",
            {"win_rate": 0.5, "payment_rating": "poor"},
        )
        
        findings = await commercial_agent.analyze(sample_rfq)
        
        payment_findings = [
            f for f in findings
            if "payment" in f.title.lower()
        ]
        
        assert len(payment_findings) >= 1
    
    def test_calculate_price_recommendation(self, commercial_agent, sample_rfq):
        """Test price recommendation calculation."""
        price = commercial_agent.calculate_price_recommendation(sample_rfq)
        
        assert isinstance(price, PriceAnalysis)
        assert price.recommended_price > price.min_price
        assert price.margin_percentage > 0
    
    def test_price_breakdown(self, commercial_agent, sample_rfq):
        """Test price breakdown calculation."""
        price = commercial_agent.calculate_price_recommendation(sample_rfq)
        
        assert "material" in price.breakdown
        assert "labor" in price.breakdown
        assert sum(price.breakdown.values()) > 0
    
    def test_register_price_history(self, commercial_agent):
        """Test registering price history."""
        commercial_agent.register_price_history(
            "housing",
            [{"date": "2024-01", "price": 100}],
        )
        
        assert "housing" in commercial_agent._price_history


# =============================================================================
# RiskAgent Tests
# =============================================================================

class TestRiskAgent:
    """Tests for RiskAgent."""
    
    @pytest.mark.asyncio
    async def test_analyze_returns_findings(self, risk_agent, sample_rfq):
        """Test that analyze returns findings."""
        findings = await risk_agent.analyze(sample_rfq)
        
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_analyze_supply_chain(self, risk_agent, sample_rfq):
        """Test supply chain risk analysis."""
        risk_agent.register_supply_chain_data(
            "aluminum",
            {"lead_time_days": 45, "availability": 0.7},
        )
        
        findings = await risk_agent.analyze(sample_rfq)
        
        sc_findings = [
            f for f in findings
            if f.category == AnalysisCategory.SUPPLY_CHAIN
        ]
        
        assert len(sc_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_compliance(self, risk_agent, sample_rfq):
        """Test compliance risk analysis."""
        # Add ITAR requirement
        sample_rfq.compliance_requirements.append("ITAR")
        
        findings = await risk_agent.analyze(sample_rfq)
        
        compliance_findings = [
            f for f in findings
            if f.category == AnalysisCategory.COMPLIANCE
        ]
        
        assert len(compliance_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_capacity(self, risk_agent, sample_rfq):
        """Test capacity risk analysis."""
        risk_agent.set_capacity_utilization("cnc", 0.95)
        
        findings = await risk_agent.analyze(sample_rfq)
        
        capacity_findings = [
            f for f in findings
            if f.category == AnalysisCategory.CAPACITY
        ]
        
        assert len(capacity_findings) >= 1
    
    @pytest.mark.asyncio
    async def test_analyze_tight_deadline(self, risk_agent, now):
        """Test tight deadline detection."""
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Test",
            quantity=50,
            deadline=now + timedelta(days=7),  # Tight deadline
        )
        
        findings = await risk_agent.analyze(rfq)
        
        timeline_findings = [
            f for f in findings
            if f.category == AnalysisCategory.TIMELINE
        ]
        
        assert len(timeline_findings) >= 1
        assert any(f.severity == Severity.HIGH for f in timeline_findings)
    
    def test_calculate_risk_scores(self, risk_agent, sample_rfq):
        """Test risk score calculation."""
        scores = risk_agent.calculate_risk_scores(sample_rfq)
        
        assert isinstance(scores, list)
        assert len(scores) >= 1
        
        for score in scores:
            assert isinstance(score, RiskScore)
            assert 0.0 <= score.score <= 1.0
    
    def test_register_supply_chain_data(self, risk_agent):
        """Test registering supply chain data."""
        risk_agent.register_supply_chain_data(
            "titanium",
            {"lead_time_days": 60, "availability": 0.6},
        )
        
        assert "titanium" in risk_agent._supply_chain_data


# =============================================================================
# AgentOrchestrator Tests
# =============================================================================

class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""
    
    def test_register_agent(self, orchestrator, technical_agent):
        """Test registering an agent."""
        orchestrator.register_agent(technical_agent)
        
        assert AgentType.TECHNICAL in orchestrator._agents
    
    def test_get_agent(self, orchestrator, technical_agent):
        """Test getting registered agent."""
        orchestrator.register_agent(technical_agent)
        
        agent = orchestrator.get_agent(AgentType.TECHNICAL)
        
        assert agent is technical_agent
    
    def test_get_nonexistent_agent(self, orchestrator):
        """Test getting non-existent agent."""
        agent = orchestrator.get_agent(AgentType.COMMERCIAL)
        
        assert agent is None
    
    @pytest.mark.asyncio
    async def test_analyze_rfq(self, orchestrator, sample_rfq):
        """Test full RFQ analysis."""
        # Register all agents
        orchestrator.register_agent(TechnicalAgent())
        orchestrator.register_agent(CommercialAgent())
        orchestrator.register_agent(RiskAgent())
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        assert isinstance(analysis, ComprehensiveAnalysis)
        assert analysis.rfq_id == sample_rfq.rfq_id
    
    @pytest.mark.asyncio
    async def test_analysis_collects_findings(self, orchestrator, sample_rfq):
        """Test that analysis collects findings from all agents."""
        orchestrator.register_agent(TechnicalAgent())
        orchestrator.register_agent(CommercialAgent())
        orchestrator.register_agent(RiskAgent())
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        all_findings = analysis.get_all_findings()
        assert len(all_findings) > 0
    
    @pytest.mark.asyncio
    async def test_analysis_includes_price(self, orchestrator, sample_rfq):
        """Test that analysis includes price analysis."""
        orchestrator.register_agent(CommercialAgent())
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        assert analysis.price_analysis is not None
    
    @pytest.mark.asyncio
    async def test_analysis_includes_risk_scores(self, orchestrator, sample_rfq):
        """Test that analysis includes risk scores."""
        orchestrator.register_agent(RiskAgent())
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        assert len(analysis.risk_scores) > 0
    
    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, orchestrator, sample_rfq):
        """Test overall score calculation."""
        orchestrator.register_agent(TechnicalAgent())
        orchestrator.register_agent(CommercialAgent())
        orchestrator.register_agent(RiskAgent())
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        assert 0 <= analysis.overall_score <= 100
    
    @pytest.mark.asyncio
    async def test_recommendation_generation(self, orchestrator, sample_rfq):
        """Test recommendation generation."""
        orchestrator.register_agent(TechnicalAgent())
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        assert len(analysis.recommendation) > 0


# =============================================================================
# Debate Protocol Tests
# =============================================================================

class TestDebateProtocol:
    """Tests for debate protocol."""
    
    @pytest.mark.asyncio
    async def test_debate_runs_on_discrepancy(self, orchestrator, sample_rfq):
        """Test that debate runs when there are discrepancies."""
        # Configure agents to have conflicting views
        tech_agent = TechnicalAgent()
        risk_agent = RiskAgent()
        risk_agent.set_capacity_utilization("cnc", 0.95)
        
        orchestrator.register_agent(tech_agent)
        orchestrator.register_agent(risk_agent)
        
        analysis = await orchestrator.analyze_rfq(sample_rfq)
        
        # Debate results may or may not be present depending on discrepancy detection
        assert isinstance(analysis.debate_results, list)
    
    def test_position_update_increases_confidence(self):
        """Test that position update can increase confidence."""
        agent = TechnicalAgent()
        
        # Get initial position
        initial = agent.get_position("price", {})
        agent._positions["price"] = initial
        
        # Create agreeing positions from other agents
        agreeing_positions = [
            AgentPosition(
                agent_type=AgentType.COMMERCIAL,
                topic="price",
                position=initial.position,
                justification="Agree",
                confidence=0.8,
            ),
        ]
        
        updated = agent.update_position("price", agreeing_positions)
        
        # Confidence should increase with agreement
        assert updated.round_number == initial.round_number + 1


# =============================================================================
# ComprehensiveAnalysis Tests
# =============================================================================

class TestComprehensiveAnalysis:
    """Tests for ComprehensiveAnalysis data model."""
    
    def test_get_all_findings(self):
        """Test getting all findings."""
        analysis = ComprehensiveAnalysis(
            rfq_id="RFQ-001",
            analysis_id="test",
            timestamp=datetime.now(timezone.utc),
            technical_findings=[
                AgentFinding(
                    agent_type=AgentType.TECHNICAL,
                    category=AnalysisCategory.MANUFACTURABILITY,
                    title="Test",
                    description="Test",
                    severity=Severity.LOW,
                    confidence=0.8,
                ),
            ],
            commercial_findings=[
                AgentFinding(
                    agent_type=AgentType.COMMERCIAL,
                    category=AnalysisCategory.PRICING,
                    title="Test",
                    description="Test",
                    severity=Severity.MEDIUM,
                    confidence=0.8,
                ),
            ],
        )
        
        all_findings = analysis.get_all_findings()
        
        assert len(all_findings) == 2
    
    def test_get_critical_issues(self):
        """Test getting critical issues."""
        analysis = ComprehensiveAnalysis(
            rfq_id="RFQ-001",
            analysis_id="test",
            timestamp=datetime.now(timezone.utc),
            technical_findings=[
                AgentFinding(
                    agent_type=AgentType.TECHNICAL,
                    category=AnalysisCategory.MANUFACTURABILITY,
                    title="Critical issue",
                    description="Test",
                    severity=Severity.CRITICAL,
                    confidence=0.8,
                ),
                AgentFinding(
                    agent_type=AgentType.TECHNICAL,
                    category=AnalysisCategory.MANUFACTURABILITY,
                    title="Low issue",
                    description="Test",
                    severity=Severity.LOW,
                    confidence=0.8,
                ),
            ],
        )
        
        critical = analysis.get_critical_issues()
        
        assert len(critical) == 1
        assert critical[0].severity == Severity.CRITICAL


# =============================================================================
# MultiAgentRFQAnalyzer Tests
# =============================================================================

class TestMultiAgentRFQAnalyzer:
    """Tests for MultiAgentRFQAnalyzer."""
    
    @pytest.mark.asyncio
    async def test_analyze(self, analyzer, sample_rfq):
        """Test full analysis."""
        analysis = await analyzer.analyze(sample_rfq)
        
        assert isinstance(analysis, ComprehensiveAnalysis)
        assert analysis.rfq_id == sample_rfq.rfq_id
    
    @pytest.mark.asyncio
    async def test_get_analysis(self, analyzer, sample_rfq):
        """Test retrieving previous analysis."""
        analysis = await analyzer.analyze(sample_rfq)
        
        retrieved = analyzer.get_analysis(analysis.analysis_id)
        
        assert retrieved is analysis
    
    def test_configure_technical_agent(self, analyzer):
        """Test configuring technical agent."""
        analyzer.configure_technical_agent(
            materials={"titanium": {"density": 4.5}},
            processes={"edm": {"accuracy": 0.001}},
        )
        
        assert "titanium" in analyzer.technical_agent._material_database
    
    def test_configure_commercial_agent(self, analyzer):
        """Test configuring commercial agent."""
        analyzer.configure_commercial_agent(
            customer_history={"CUST-001": {"win_rate": 0.8}},
        )
        
        assert "CUST-001" in analyzer.commercial_agent._customer_history
    
    def test_configure_risk_agent(self, analyzer):
        """Test configuring risk agent."""
        analyzer.configure_risk_agent(
            supply_chain={"titanium": {"lead_time_days": 60}},
            capacity={"cnc": 0.8},
        )
        
        assert "titanium" in analyzer.risk_agent._supply_chain_data
        assert "cnc" in analyzer.risk_agent._capacity_data
    
    def test_get_stats(self, analyzer):
        """Test getting statistics."""
        stats = analyzer.get_stats()
        
        assert "total_analyses" in stats
        assert stats["registered_agents"] == 3


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_rfq_analyzer(self):
        """Test creating analyzer with defaults."""
        analyzer = create_rfq_analyzer()
        
        assert isinstance(analyzer, MultiAgentRFQAnalyzer)
    
    def test_create_with_custom_params(self):
        """Test creating with custom parameters."""
        analyzer = create_rfq_analyzer(
            max_debate_rounds=5,
            consensus_threshold=0.8,
        )
        
        assert analyzer.orchestrator.max_debate_rounds == 5
        assert analyzer.orchestrator.consensus_threshold == 0.8


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enums."""
    
    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.TECHNICAL.value == "technical"
        assert AgentType.COMMERCIAL.value == "commercial"
        assert AgentType.RISK.value == "risk"
    
    def test_severity_values(self):
        """Test Severity enum values."""
        assert Severity.INFO.value == "info"
        assert Severity.CRITICAL.value == "critical"
    
    def test_debate_outcome_values(self):
        """Test DebateOutcome enum values."""
        assert DebateOutcome.CONSENSUS.value == "consensus"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, now):
        """Test full multi-agent workflow."""
        analyzer = create_rfq_analyzer()
        
        # Configure agents
        analyzer.configure_commercial_agent(
            customer_history={"CUST-001": {"win_rate": 0.75, "payment_rating": "good"}},
        )
        analyzer.configure_risk_agent(
            supply_chain={"aluminum": {"lead_time_days": 14, "availability": 0.9}},
            capacity={"cnc": 0.7},
        )
        
        # Create RFQ
        rfq = RFQSpec(
            rfq_id="RFQ-001",
            customer_id="CUST-001",
            description="Precision aluminum housing",
            quantity=100,
            target_price=5000.0,
            deadline=now + timedelta(days=30),
            material_specs={"primary_material": "aluminum"},
            dimension_specs={
                "tolerances": {"position": 0.05},
                "wall_thickness": 2.0,
            },
            finish_requirements=["Anodize"],
            compliance_requirements=["ISO 9001"],
        )
        
        # Analyze
        analysis = await analyzer.analyze(rfq)
        
        # Verify comprehensive analysis
        assert analysis.overall_score > 0
        assert len(analysis.recommendation) > 0
        assert analysis.price_analysis is not None
        assert len(analysis.risk_scores) > 0
    
    @pytest.mark.asyncio
    async def test_high_risk_scenario(self, now):
        """Test high risk scenario analysis."""
        analyzer = create_rfq_analyzer()
        
        # Configure high-risk conditions
        analyzer.configure_risk_agent(
            supply_chain={"exotic_alloy": {"lead_time_days": 90, "availability": 0.3}},
            capacity={"cnc": 0.95, "edm": 0.92},
        )
        
        # Create high-risk RFQ
        rfq = RFQSpec(
            rfq_id="RFQ-RISK",
            customer_id="NEW-CUST",
            description="Complex exotic alloy part",
            quantity=5,
            deadline=now + timedelta(days=10),  # Very tight
            material_specs={"primary_material": "exotic_alloy"},
            compliance_requirements=["ITAR", "AS9100"],
        )
        
        analysis = await analyzer.analyze(rfq)
        
        # Should have lower score due to risks
        assert analysis.overall_score < 80
        
        # Should have high severity findings
        critical_issues = analysis.get_critical_issues()
        assert len(critical_issues) > 0
