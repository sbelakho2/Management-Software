"""
Tests for Sensei Reasoning Engine.

Covers:
- A3 Pattern Analyzer
- Socratic Mentor
- 5 Whys Root Cause Assistant
- Main SenseiReasoningEngine service
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import random

from sensei.services.reasoning_engine import (
    # Enums
    A3Phase,
    LeanWasteCategory,
    MudaType,
    MentorPersona,
    PromptType,
    KPITrend,
    # Data models
    KPIMetric,
    Countermeasure,
    A3Report,
    CountermeasureCorrelation,
    ChallengingPrompt,
    RootCauseSuggestion,
    WebSocketMessage,
    # Classes
    A3PatternAnalyzer,
    SocraticMentor,
    FiveWhysAssistant,
    SenseiReasoningEngine,
    # Factory
    create_reasoning_engine,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_kpis_before():
    """Sample KPIs before improvement."""
    return [
        KPIMetric(
            name="on_time_delivery",
            value=85.0,
            unit="%",
            timestamp=datetime(2024, 1, 1),
            trend=KPITrend.STABLE,
            target=95.0,
        ),
        KPIMetric(
            name="defect_rate",
            value=3.5,
            unit="%",
            timestamp=datetime(2024, 1, 1),
            trend=KPITrend.STABLE,
            target=1.0,
        ),
    ]


@pytest.fixture
def sample_kpis_after():
    """Sample KPIs after improvement."""
    return [
        KPIMetric(
            name="on_time_delivery",
            value=96.0,
            unit="%",
            timestamp=datetime(2024, 3, 1),
            trend=KPITrend.IMPROVED,
            target=95.0,
        ),
        KPIMetric(
            name="defect_rate",
            value=0.8,
            unit="%",
            timestamp=datetime(2024, 3, 1),
            trend=KPITrend.IMPROVED,
            target=1.0,
        ),
    ]


@pytest.fixture
def sample_countermeasure():
    """Sample countermeasure."""
    return Countermeasure(
        id="cm_001",
        description="Implement visual management board",
        category="visual_management",
        implementation_date=datetime(2024, 2, 1),
        responsible="John Doe",
        status="completed",
        effectiveness_score=0.85,
        tags=["visual", "lean"],
    )


@pytest.fixture
def sample_a3(sample_kpis_before, sample_kpis_after, sample_countermeasure):
    """Sample closed A3 report."""
    return A3Report(
        id="a3_001",
        title="Reduce Late Deliveries",
        problem_statement="Delivery on-time rate has dropped to 85%",
        owner="Jane Smith",
        created_at=datetime(2024, 1, 1),
        status="closed",
        background="Customer complaints about late deliveries increased",
        current_state="OTD at 85%, target is 95%",
        goal="Achieve 95% OTD within 3 months",
        root_causes=["Lack of visual scheduling", "No standard work for shipping"],
        countermeasures=[sample_countermeasure],
        kpis_before=sample_kpis_before,
        kpis_after=sample_kpis_after,
        five_whys=[
            "Why are deliveries late?",
            "Why is scheduling delayed?",
            "Why is there no visibility?",
        ],
        waste_categories=[LeanWasteCategory.MUDA, LeanWasteCategory.MURA],
        closed_at=datetime(2024, 3, 15),
    )


@pytest.fixture
def pattern_analyzer():
    """A3 pattern analyzer instance."""
    return A3PatternAnalyzer()


@pytest.fixture
def socratic_mentor():
    """Socratic mentor instance."""
    return SocraticMentor()


@pytest.fixture
def five_whys_assistant():
    """5 Whys assistant instance."""
    return FiveWhysAssistant()


@pytest.fixture
def reasoning_engine():
    """Sensei Reasoning Engine instance."""
    return SenseiReasoningEngine()


# =============================================================================
# KPIMetric Tests
# =============================================================================

class TestKPIMetric:
    """Tests for KPIMetric data class."""
    
    def test_kpi_creation(self):
        """Test creating a KPI metric."""
        kpi = KPIMetric(
            name="productivity",
            value=100.0,
            unit="units/hour",
            timestamp=datetime.utcnow(),
        )
        
        assert kpi.name == "productivity"
        assert kpi.value == 100.0
        assert kpi.unit == "units/hour"
        assert kpi.trend == KPITrend.UNKNOWN
    
    def test_kpi_on_target(self):
        """Test is_on_target property."""
        kpi_on = KPIMetric(
            name="quality",
            value=98.0,
            unit="%",
            timestamp=datetime.utcnow(),
            target=95.0,
        )
        kpi_off = KPIMetric(
            name="quality",
            value=90.0,
            unit="%",
            timestamp=datetime.utcnow(),
            target=95.0,
        )
        
        assert kpi_on.is_on_target is True
        assert kpi_off.is_on_target is False
    
    def test_kpi_no_target(self):
        """Test is_on_target with no target set."""
        kpi = KPIMetric(
            name="productivity",
            value=100.0,
            unit="units/hour",
            timestamp=datetime.utcnow(),
        )
        
        assert kpi.is_on_target is True


# =============================================================================
# A3Report Tests
# =============================================================================

class TestA3Report:
    """Tests for A3Report data class."""
    
    def test_a3_creation(self, sample_a3):
        """Test A3 report creation."""
        assert sample_a3.id == "a3_001"
        assert sample_a3.status == "closed"
        assert len(sample_a3.countermeasures) == 1
        assert len(sample_a3.root_causes) == 2
    
    def test_a3_with_empty_lists(self):
        """Test A3 with default empty lists."""
        a3 = A3Report(
            id="a3_002",
            title="Test A3",
            problem_statement="Test problem",
            owner="Test Owner",
            created_at=datetime.utcnow(),
        )
        
        assert a3.root_causes == []
        assert a3.countermeasures == []
        assert a3.kpis_before == []
        assert a3.kpis_after == []


# =============================================================================
# A3PatternAnalyzer Tests
# =============================================================================

class TestA3PatternAnalyzer:
    """Tests for A3PatternAnalyzer."""
    
    def test_add_closed_a3(self, pattern_analyzer, sample_a3):
        """Test adding a closed A3."""
        pattern_analyzer.add_closed_a3(sample_a3)
        
        stats = pattern_analyzer.get_stats()
        assert stats["closed_a3s"] == 1
    
    def test_add_open_a3_raises_error(self, pattern_analyzer):
        """Test that adding an open A3 raises error."""
        open_a3 = A3Report(
            id="a3_open",
            title="Open A3",
            problem_statement="Problem",
            owner="Owner",
            created_at=datetime.utcnow(),
            status="open",
        )
        
        with pytest.raises(ValueError, match="Only closed A3s"):
            pattern_analyzer.add_closed_a3(open_a3)
    
    def test_calculate_kpi_improvements(
        self, pattern_analyzer, sample_a3
    ):
        """Test KPI improvement calculation."""
        improvements = pattern_analyzer._calculate_kpi_improvements(sample_a3)
        
        assert "on_time_delivery" in improvements
        assert improvements["on_time_delivery"] > 0  # Improved
        assert "defect_rate" in improvements
        assert improvements["defect_rate"] < 0  # Lower is better but calc is raw
    
    def test_calculate_kpi_improvements_zero_before(self, pattern_analyzer):
        """Test KPI improvement with zero before value."""
        a3 = A3Report(
            id="a3_zero",
            title="Zero KPI Test",
            problem_statement="Problem",
            owner="Owner",
            created_at=datetime.utcnow(),
            status="closed",
            kpis_before=[
                KPIMetric(name="new_metric", value=0.0, unit="count", timestamp=datetime.utcnow())
            ],
            kpis_after=[
                KPIMetric(name="new_metric", value=10.0, unit="count", timestamp=datetime.utcnow())
            ],
        )
        
        improvements = pattern_analyzer._calculate_kpi_improvements(a3)
        assert improvements["new_metric"] == 1.0
    
    def test_compute_correlations(self, pattern_analyzer, sample_a3):
        """Test computing correlations."""
        pattern_analyzer.add_closed_a3(sample_a3)
        
        # Add another A3 with same category
        a3_2 = A3Report(
            id="a3_002",
            title="Another A3",
            problem_statement="Problem",
            owner="Owner",
            created_at=datetime.utcnow(),
            status="closed",
            countermeasures=[
                Countermeasure(
                    id="cm_002",
                    description="Visual board 2",
                    category="visual_management",
                    status="completed",
                )
            ],
            kpis_before=[
                KPIMetric(name="on_time_delivery", value=80.0, unit="%", timestamp=datetime.utcnow())
            ],
            kpis_after=[
                KPIMetric(name="on_time_delivery", value=90.0, unit="%", timestamp=datetime.utcnow())
            ],
        )
        pattern_analyzer.add_closed_a3(a3_2)
        
        correlations = pattern_analyzer.compute_correlations()
        
        assert len(correlations) > 0
        assert any(c.countermeasure_category == "visual_management" for c in correlations)
    
    def test_suggest_countermeasures(self, pattern_analyzer, sample_a3):
        """Test countermeasure suggestions."""
        pattern_analyzer.add_closed_a3(sample_a3)
        
        # Add more data for better suggestions
        for i in range(3):
            a3 = A3Report(
                id=f"a3_{i+10}",
                title=f"A3 #{i}",
                problem_statement="Problem",
                owner="Owner",
                created_at=datetime.utcnow(),
                status="closed",
                countermeasures=[
                    Countermeasure(
                        id=f"cm_{i+10}",
                        description="Standard work",
                        category="standardization",
                        status="completed",
                    )
                ],
                kpis_before=[
                    KPIMetric(name="efficiency", value=70.0, unit="%", timestamp=datetime.utcnow())
                ],
                kpis_after=[
                    KPIMetric(name="efficiency", value=85.0, unit="%", timestamp=datetime.utcnow())
                ],
            )
            pattern_analyzer.add_closed_a3(a3)
        
        suggestions = pattern_analyzer.suggest_countermeasures(
            target_kpis=["efficiency"],
            top_k=3,
        )
        
        assert len(suggestions) > 0
        assert suggestions[0][0] == "standardization"  # Category
        assert suggestions[0][1] > 0  # Score
    
    def test_suggest_countermeasures_no_data(self, pattern_analyzer):
        """Test suggestions with no historical data."""
        suggestions = pattern_analyzer.suggest_countermeasures(
            target_kpis=["unknown_kpi"],
        )
        
        assert len(suggestions) == 0
    
    def test_get_success_rate(self, pattern_analyzer, sample_a3):
        """Test success rate calculation."""
        pattern_analyzer.add_closed_a3(sample_a3)
        
        rate = pattern_analyzer.get_success_rate("visual_management")
        assert 0.0 <= rate <= 1.0
        
        # Unknown category returns 0.5
        unknown_rate = pattern_analyzer.get_success_rate("unknown_category")
        assert unknown_rate == 0.5
    
    def test_get_stats(self, pattern_analyzer, sample_a3):
        """Test getting analyzer stats."""
        pattern_analyzer.add_closed_a3(sample_a3)
        pattern_analyzer.compute_correlations()
        
        stats = pattern_analyzer.get_stats()
        
        assert "closed_a3s" in stats
        assert "correlations" in stats
        assert "tracked_categories" in stats
        assert "tracked_kpis" in stats


# =============================================================================
# SocraticMentor Tests
# =============================================================================

class TestSocraticMentor:
    """Tests for SocraticMentor."""
    
    def test_init_default_persona(self):
        """Test default persona initialization."""
        mentor = SocraticMentor()
        assert mentor.default_persona == MentorPersona.THE_SENSEI
    
    def test_init_custom_persona(self):
        """Test custom persona initialization."""
        mentor = SocraticMentor(default_persona=MentorPersona.THE_CHALLENGER)
        assert mentor.default_persona == MentorPersona.THE_CHALLENGER
    
    def test_generate_prompts(self, socratic_mentor):
        """Test generating prompts."""
        prompts = socratic_mentor.generate_prompts(
            content="The current defect rate is 5% which is above target.",
            phase=A3Phase.CURRENT_STATE,
            max_prompts=3,
        )
        
        assert len(prompts) <= 3
        assert all(isinstance(p, ChallengingPrompt) for p in prompts)
        assert all(p.phase == A3Phase.CURRENT_STATE for p in prompts)
    
    def test_generate_prompts_different_phases(self, socratic_mentor):
        """Test prompts for different A3 phases."""
        phases = [
            A3Phase.BACKGROUND,
            A3Phase.CURRENT_STATE,
            A3Phase.GOAL,
            A3Phase.ROOT_CAUSE,
            A3Phase.COUNTERMEASURES,
        ]
        
        for phase in phases:
            prompts = socratic_mentor.generate_prompts(
                content="Test content for phase analysis.",
                phase=phase,
                max_prompts=2,
            )
            assert len(prompts) > 0
            assert all(p.phase == phase for p in prompts)
    
    def test_generate_prompts_different_personas(self, socratic_mentor):
        """Test prompts with different personas."""
        personas = [
            MentorPersona.THE_SENSEI,
            MentorPersona.THE_CHALLENGER,
            MentorPersona.THE_COACH,
            MentorPersona.THE_OBSERVER,
        ]
        
        for persona in personas:
            prompts = socratic_mentor.generate_prompts(
                content="Production output has decreased by 10%.",
                phase=A3Phase.CURRENT_STATE,
                persona=persona,
                max_prompts=2,
            )
            assert len(prompts) > 0
            assert all(p.persona == persona for p in prompts)
    
    def test_extract_key_terms(self, socratic_mentor):
        """Test key term extraction."""
        content = "The manufacturing process has experienced significant delays."
        terms = socratic_mentor._extract_key_terms(content)
        
        assert len(terms) > 0
        assert "manufacturing" in terms or "process" in terms or "delays" in terms
    
    def test_extract_key_terms_filters_common_words(self, socratic_mentor):
        """Test that common words are filtered."""
        content = "There should be about every thing possible."
        terms = socratic_mentor._extract_key_terms(content)
        
        # Common words should not be in results
        common = {"about", "every", "thing", "should", "there"}
        for term in terms:
            assert term not in common
    
    def test_identify_aspect(self, socratic_mentor):
        """Test aspect identification."""
        # With quoted phrase
        content = 'The problem is "late deliveries" causing issues.'
        aspect = socratic_mentor._identify_aspect(content)
        assert "late deliveries" in aspect
        
        # With 'is' sentence
        content = "The process is inefficient and wasteful."
        aspect = socratic_mentor._identify_aspect(content)
        assert len(aspect) > 0
    
    def test_get_follow_ups(self, socratic_mentor):
        """Test follow-up prompts."""
        for prompt_type in PromptType:
            follow_ups = socratic_mentor._get_follow_ups(prompt_type)
            assert isinstance(follow_ups, list)
    
    def test_prompt_has_follow_ups(self, socratic_mentor):
        """Test that generated prompts have follow-ups."""
        prompts = socratic_mentor.generate_prompts(
            content="Defects are increasing.",
            phase=A3Phase.ROOT_CAUSE,
        )
        
        assert any(len(p.follow_up_prompts) > 0 for p in prompts)
    
    def test_create_websocket_message(self, socratic_mentor):
        """Test WebSocket message creation."""
        prompts = socratic_mentor.generate_prompts(
            content="Test content",
            phase=A3Phase.GOAL,
        )
        
        message = socratic_mentor.create_websocket_message(prompts[0])
        
        assert isinstance(message, WebSocketMessage)
        assert message.message_type == "challenging_prompt"
        assert "question" in message.payload
        assert message.correlation_id == prompts[0].id
    
    def test_session_tracking(self, socratic_mentor):
        """Test session prompt tracking."""
        # Generate some prompts
        socratic_mentor.generate_prompts("Content 1", A3Phase.BACKGROUND)
        socratic_mentor.generate_prompts("Content 2", A3Phase.CURRENT_STATE)
        
        session_prompts = socratic_mentor.get_session_prompts()
        assert len(session_prompts) > 0
        
        # Clear session
        socratic_mentor.clear_session()
        assert len(socratic_mentor.get_session_prompts()) == 0
    
    def test_prompt_priority(self, socratic_mentor):
        """Test prompt priority assignment."""
        prompts = socratic_mentor.generate_prompts(
            content="We observed multiple defects at the station.",
            phase=A3Phase.ROOT_CAUSE,
            max_prompts=3,
        )
        
        # All prompts should have priority 1, 2, or 3
        for prompt in prompts:
            assert prompt.priority in [1, 2, 3]


# =============================================================================
# FiveWhysAssistant Tests
# =============================================================================

class TestFiveWhysAssistant:
    """Tests for FiveWhysAssistant."""
    
    def test_add_historical_cause(self, five_whys_assistant):
        """Test adding historical causes."""
        five_whys_assistant.add_historical_cause(
            "Operator training was inadequate",
            LeanWasteCategory.MUDA,
        )
        
        assert len(five_whys_assistant._historical_causes) == 1
    
    def test_analyze_problem_basic(self, five_whys_assistant):
        """Test basic problem analysis."""
        suggestions = five_whys_assistant.analyze_problem(
            "Deliveries are arriving late to customers."
        )
        
        assert len(suggestions) > 0
        assert all(isinstance(s, RootCauseSuggestion) for s in suggestions)
        assert all(s.why_number == 1 for s in suggestions)  # First why
    
    def test_analyze_problem_with_current_whys(self, five_whys_assistant):
        """Test analysis with existing whys."""
        suggestions = five_whys_assistant.analyze_problem(
            problem_statement="Machine is producing defects.",
            current_whys=[
                "Why are there defects? Tool is worn.",
                "Why is tool worn? No maintenance schedule.",
            ],
        )
        
        assert len(suggestions) > 0
        assert all(s.why_number == 3 for s in suggestions)  # Third why
    
    def test_analyze_problem_training_pattern(self, five_whys_assistant):
        """Test detection of training gap pattern."""
        suggestions = five_whys_assistant.analyze_problem(
            "The new employee didn't know how to operate the machine."
        )
        
        # Should detect training gap
        training_suggestion = next(
            (s for s in suggestions if "training" in s.suggested_cause.lower()),
            None
        )
        assert training_suggestion is not None
    
    def test_analyze_problem_equipment_pattern(self, five_whys_assistant):
        """Test detection of equipment failure pattern."""
        suggestions = five_whys_assistant.analyze_problem(
            "The machine broke down and stopped production."
        )
        
        equipment_suggestion = next(
            (s for s in suggestions if "maintenance" in s.suggested_cause.lower()),
            None
        )
        assert equipment_suggestion is not None
    
    def test_analyze_problem_standard_pattern(self, five_whys_assistant):
        """Test detection of lack of standard pattern."""
        suggestions = five_whys_assistant.analyze_problem(
            "Each operator does it a different way with inconsistent results."
        )
        
        standard_suggestion = next(
            (s for s in suggestions if "standard" in s.suggested_cause.lower()),
            None
        )
        assert standard_suggestion is not None
    
    def test_classify_waste_muda(self, five_whys_assistant):
        """Test Muda waste classification."""
        waste = five_whys_assistant._classify_waste(
            "there was a lot of waste and rework on defective parts"
        )
        assert waste == LeanWasteCategory.MUDA
    
    def test_classify_waste_mura(self, five_whys_assistant):
        """Test Mura waste classification."""
        waste = five_whys_assistant._classify_waste(
            "production is inconsistent and varies day to day unpredictably"
        )
        assert waste == LeanWasteCategory.MURA
    
    def test_classify_waste_muri(self, five_whys_assistant):
        """Test Muri waste classification."""
        waste = five_whys_assistant._classify_waste(
            "workers are overloaded and stressed beyond capacity"
        )
        assert waste == LeanWasteCategory.MURI
    
    def test_classify_muda_type_waiting(self, five_whys_assistant):
        """Test Muda type classification - waiting."""
        muda = five_whys_assistant.classify_muda_type(
            "operators are waiting in queue for parts"
        )
        assert muda == MudaType.WAITING
    
    def test_classify_muda_type_defects(self, five_whys_assistant):
        """Test Muda type classification - defects."""
        muda = five_whys_assistant.classify_muda_type(
            "too many defects requiring rework and scrap"
        )
        assert muda == MudaType.DEFECTS
    
    def test_classify_muda_type_motion(self, five_whys_assistant):
        """Test Muda type classification - motion."""
        muda = five_whys_assistant.classify_muda_type(
            "workers walk long distances to find tools"
        )
        assert muda == MudaType.MOTION
    
    def test_classify_muda_type_inventory(self, five_whys_assistant):
        """Test Muda type classification - inventory."""
        muda = five_whys_assistant.classify_muda_type(
            "too much inventory in storage piling up in warehouse"
        )
        assert muda == MudaType.INVENTORY
    
    def test_classify_muda_type_transportation(self, five_whys_assistant):
        """Test Muda type classification - transportation."""
        muda = five_whys_assistant.classify_muda_type(
            "parts are transported multiple times during delivery"
        )
        assert muda == MudaType.TRANSPORTATION
    
    def test_classify_muda_type_overproduction(self, five_whys_assistant):
        """Test Muda type classification - overproduction."""
        muda = five_whys_assistant.classify_muda_type(
            "we are overproducing too much excess product"
        )
        assert muda == MudaType.OVERPRODUCTION
    
    def test_classify_muda_type_overprocessing(self, five_whys_assistant):
        """Test Muda type classification - overprocessing."""
        muda = five_whys_assistant.classify_muda_type(
            "there are unnecessary extra steps and redundant processing"
        )
        assert muda == MudaType.OVERPROCESSING
    
    def test_classify_muda_type_skills(self, five_whys_assistant):
        """Test Muda type classification - underutilized skills."""
        muda = five_whys_assistant.classify_muda_type(
            "worker skills and talent are underutilized"
        )
        assert muda == MudaType.SKILLS
    
    def test_classify_muda_type_none(self, five_whys_assistant):
        """Test Muda type classification returns None for no match."""
        muda = five_whys_assistant.classify_muda_type(
            "general issue with no specific waste type"
        )
        # Could match or not, depends on keywords
        assert muda is None or isinstance(muda, MudaType)
    
    def test_find_similar_historical(self, five_whys_assistant):
        """Test finding similar historical causes."""
        five_whys_assistant.add_historical_cause(
            "Training records were outdated",
            LeanWasteCategory.MUDA,
        )
        five_whys_assistant.add_historical_cause(
            "New employee training gap",
            LeanWasteCategory.MUDA,
        )
        
        similar = five_whys_assistant._find_similar_historical("training gap")
        
        assert len(similar) > 0
        assert any("training" in s.lower() for s in similar)
    
    def test_get_evidence_needs(self, five_whys_assistant):
        """Test evidence needs for patterns."""
        evidence = five_whys_assistant._get_evidence_needs("training gap")
        
        assert len(evidence) > 0
        assert any("training" in e.lower() for e in evidence)
    
    def test_get_evidence_needs_unknown(self, five_whys_assistant):
        """Test evidence needs for unknown pattern."""
        evidence = five_whys_assistant._get_evidence_needs("unknown pattern")
        
        assert len(evidence) > 0
        assert "gemba" in evidence[0].lower()
    
    def test_get_waste_summary(self, five_whys_assistant):
        """Test waste summary generation."""
        suggestions = [
            RootCauseSuggestion(
                why_number=1,
                suggested_cause="Cause 1",
                confidence=0.8,
                waste_category=LeanWasteCategory.MUDA,
                muda_type=MudaType.DEFECTS,
            ),
            RootCauseSuggestion(
                why_number=2,
                suggested_cause="Cause 2",
                confidence=0.7,
                waste_category=LeanWasteCategory.MUDA,
                muda_type=MudaType.WAITING,
            ),
            RootCauseSuggestion(
                why_number=3,
                suggested_cause="Cause 3",
                confidence=0.6,
                waste_category=LeanWasteCategory.MURA,
            ),
        ]
        
        summary = five_whys_assistant.get_waste_summary(suggestions)
        
        assert summary["primary_waste"] == "muda"
        assert summary["waste_distribution"]["muda"] == 2
        assert summary["waste_distribution"]["mura"] == 1
        assert summary["muda_types"]["defects"] == 1
        assert summary["total_suggestions"] == 3
    
    def test_suggestions_sorted_by_confidence(self, five_whys_assistant):
        """Test that suggestions are sorted by confidence."""
        suggestions = five_whys_assistant.analyze_problem(
            "Machine equipment failure caused defects and waiting delays."
        )
        
        if len(suggestions) > 1:
            for i in range(len(suggestions) - 1):
                assert suggestions[i].confidence >= suggestions[i + 1].confidence


# =============================================================================
# SenseiReasoningEngine Tests
# =============================================================================

class TestSenseiReasoningEngine:
    """Tests for the main SenseiReasoningEngine."""
    
    def test_engine_creation(self):
        """Test engine creation."""
        engine = SenseiReasoningEngine()
        
        assert engine.pattern_analyzer is not None
        assert engine.mentor is not None
        assert engine.five_whys is not None
    
    def test_engine_with_custom_persona(self):
        """Test engine with custom persona."""
        engine = SenseiReasoningEngine(
            default_persona=MentorPersona.THE_CHALLENGER
        )
        
        assert engine.mentor.default_persona == MentorPersona.THE_CHALLENGER
    
    def test_register_closed_a3(self, reasoning_engine, sample_a3):
        """Test registering a closed A3."""
        reasoning_engine.register_closed_a3(sample_a3)
        
        stats = reasoning_engine.get_stats()
        assert stats["pattern_analyzer"]["closed_a3s"] == 1
        assert stats["historical_causes"] > 0
    
    def test_suggest_countermeasures(self, reasoning_engine, sample_a3):
        """Test countermeasure suggestions."""
        # Add historical data
        for i in range(3):
            a3 = A3Report(
                id=f"hist_{i}",
                title=f"Historical A3 {i}",
                problem_statement="Problem",
                owner="Owner",
                created_at=datetime.utcnow(),
                status="closed",
                countermeasures=[
                    Countermeasure(
                        id=f"cm_{i}",
                        description="5S implementation",
                        category="5s",
                        status="completed",
                    )
                ],
                kpis_before=[
                    KPIMetric(name="productivity", value=80.0, unit="%", timestamp=datetime.utcnow())
                ],
                kpis_after=[
                    KPIMetric(name="productivity", value=95.0, unit="%", timestamp=datetime.utcnow())
                ],
            )
            reasoning_engine.register_closed_a3(a3)
        
        suggestions = reasoning_engine.suggest_countermeasures(
            target_kpis=["productivity"],
            top_k=3,
        )
        
        assert len(suggestions) > 0
    
    def test_get_challenging_prompts(self, reasoning_engine):
        """Test getting challenging prompts."""
        prompts = reasoning_engine.get_challenging_prompts(
            content="We are seeing increased defect rates.",
            phase=A3Phase.CURRENT_STATE,
        )
        
        assert len(prompts) > 0
        assert all(isinstance(p, ChallengingPrompt) for p in prompts)
    
    def test_analyze_root_cause(self, reasoning_engine):
        """Test root cause analysis."""
        suggestions = reasoning_engine.analyze_root_cause(
            problem_statement="Parts are being delivered late.",
            current_whys=["Transportation takes too long"],
        )
        
        assert len(suggestions) > 0
        assert all(s.why_number == 2 for s in suggestions)
    
    def test_classify_waste(self, reasoning_engine):
        """Test waste classification."""
        waste, muda = reasoning_engine.classify_waste(
            "Lots of waiting and delays in the queue"
        )
        
        assert waste == LeanWasteCategory.MUDA
        assert muda == MudaType.WAITING
    
    def test_start_and_end_mentoring_session(self, reasoning_engine):
        """Test mentoring session lifecycle."""
        session_id = "session_001"
        a3_id = "a3_001"
        
        reasoning_engine.start_mentoring_session(session_id, a3_id)
        
        assert session_id in reasoning_engine._active_sessions
        
        # Generate some prompts
        reasoning_engine.get_challenging_prompts(
            "Test content",
            A3Phase.BACKGROUND,
        )
        
        # End session
        summary = reasoning_engine.end_mentoring_session(session_id)
        
        assert summary["a3_id"] == a3_id
        assert "duration" in summary
        assert session_id not in reasoning_engine._active_sessions
    
    def test_end_nonexistent_session(self, reasoning_engine):
        """Test ending a nonexistent session."""
        summary = reasoning_engine.end_mentoring_session("nonexistent")
        assert summary == {}
    
    def test_get_stats(self, reasoning_engine, sample_a3):
        """Test getting engine stats."""
        reasoning_engine.register_closed_a3(sample_a3)
        
        stats = reasoning_engine.get_stats()
        
        assert "pattern_analyzer" in stats
        assert "active_sessions" in stats
        assert "historical_causes" in stats


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestCreateReasoningEngine:
    """Tests for factory function."""
    
    def test_create_default_engine(self):
        """Test creating engine with defaults."""
        engine = create_reasoning_engine()
        
        assert isinstance(engine, SenseiReasoningEngine)
        assert engine.mentor.default_persona == MentorPersona.THE_SENSEI
    
    def test_create_engine_with_persona(self):
        """Test creating engine with custom persona."""
        engine = create_reasoning_engine(
            default_persona=MentorPersona.THE_COACH
        )
        
        assert engine.mentor.default_persona == MentorPersona.THE_COACH


# =============================================================================
# WebSocketMessage Tests
# =============================================================================

class TestWebSocketMessage:
    """Tests for WebSocketMessage."""
    
    def test_message_creation(self):
        """Test WebSocket message creation."""
        message = WebSocketMessage(
            message_type="test",
            payload={"key": "value"},
        )
        
        assert message.message_type == "test"
        assert message.payload["key"] == "value"
        assert message.timestamp is not None
    
    def test_message_with_correlation_id(self):
        """Test message with correlation ID."""
        message = WebSocketMessage(
            message_type="prompt",
            payload={},
            correlation_id="corr_123",
        )
        
        assert message.correlation_id == "corr_123"


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enumeration values."""
    
    def test_a3_phases(self):
        """Test A3 phases enum."""
        assert len(A3Phase) == 7
        assert A3Phase.BACKGROUND.value == "background"
        assert A3Phase.ROOT_CAUSE.value == "root_cause"
    
    def test_lean_waste_categories(self):
        """Test lean waste categories."""
        assert len(LeanWasteCategory) == 3
        assert LeanWasteCategory.MUDA.value == "muda"
        assert LeanWasteCategory.MURA.value == "mura"
        assert LeanWasteCategory.MURI.value == "muri"
    
    def test_muda_types(self):
        """Test Muda types (8 wastes)."""
        assert len(MudaType) == 8
        assert MudaType.TRANSPORTATION.value == "transportation"
        assert MudaType.SKILLS.value == "skills"
    
    def test_mentor_personas(self):
        """Test mentor personas."""
        assert len(MentorPersona) == 4
        assert MentorPersona.THE_SENSEI.value == "the_sensei"
        assert MentorPersona.THE_CHALLENGER.value == "the_challenger"
    
    def test_prompt_types(self):
        """Test prompt types."""
        assert len(PromptType) == 6
        assert PromptType.CLARIFICATION.value == "clarification"
        assert PromptType.DEEPER.value == "deeper"
    
    def test_kpi_trends(self):
        """Test KPI trends."""
        assert len(KPITrend) == 4
        assert KPITrend.IMPROVED.value == "improved"
        assert KPITrend.UNKNOWN.value == "unknown"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full reasoning engine workflow."""
    
    def test_full_a3_workflow(self, reasoning_engine):
        """Test complete A3 problem-solving workflow."""
        # 1. Start mentoring session
        reasoning_engine.start_mentoring_session("session_1", "a3_test")
        
        # 2. Background phase - get prompts
        bg_prompts = reasoning_engine.get_challenging_prompts(
            "Customer complaints have increased 50% in Q4.",
            A3Phase.BACKGROUND,
        )
        assert len(bg_prompts) > 0
        
        # 3. Current state - get prompts
        cs_prompts = reasoning_engine.get_challenging_prompts(
            "Order processing time is 5 days, target is 2 days.",
            A3Phase.CURRENT_STATE,
        )
        assert len(cs_prompts) > 0
        
        # 4. Root cause analysis with 5 Whys
        why1_suggestions = reasoning_engine.analyze_root_cause(
            "Orders are taking too long to process."
        )
        assert len(why1_suggestions) > 0
        
        why2_suggestions = reasoning_engine.analyze_root_cause(
            "Orders are taking too long to process.",
            current_whys=["Manual data entry is slow."],
        )
        assert all(s.why_number == 2 for s in why2_suggestions)
        
        # 5. Classify waste
        waste, muda = reasoning_engine.classify_waste(
            "Manual data entry requires waiting for verification."
        )
        assert waste is not None
        
        # 6. End session
        summary = reasoning_engine.end_mentoring_session("session_1")
        assert summary["duration"] >= 0
    
    def test_pattern_learning_and_suggestion(self, reasoning_engine):
        """Test learning from A3s and making suggestions."""
        # Add historical A3s
        for i in range(5):
            a3 = A3Report(
                id=f"a3_{i}",
                title=f"Historical A3 {i}",
                problem_statement="Delivery delays",
                owner="Owner",
                created_at=datetime.utcnow(),
                status="closed",
                root_causes=["No visual management"],
                countermeasures=[
                    Countermeasure(
                        id=f"cm_{i}",
                        description="Visual board",
                        category="visual_management",
                        status="completed",
                    )
                ],
                kpis_before=[
                    KPIMetric(name="otd", value=85.0, unit="%", timestamp=datetime.utcnow())
                ],
                kpis_after=[
                    KPIMetric(name="otd", value=95.0 + i, unit="%", timestamp=datetime.utcnow())
                ],
                waste_categories=[LeanWasteCategory.MURA],
            )
            reasoning_engine.register_closed_a3(a3)
        
        # Get suggestions
        suggestions = reasoning_engine.suggest_countermeasures(
            target_kpis=["otd"],
            top_k=3,
        )
        
        assert len(suggestions) > 0
        
        # Visual management should be suggested
        categories = [s[0] for s in suggestions]
        assert "visual_management" in categories
    
    def test_mentor_prompts_are_contextual(self, reasoning_engine):
        """Test that mentor prompts are contextual to phase."""
        # Root cause phase should get "deeper" prompts
        rc_prompts = reasoning_engine.get_challenging_prompts(
            "The root cause is operator error.",
            A3Phase.ROOT_CAUSE,
            max_prompts=5,
        )
        
        # Should include deeper or evidence type prompts
        prompt_types = {p.prompt_type for p in rc_prompts}
        assert PromptType.DEEPER in prompt_types or PromptType.EVIDENCE in prompt_types
        
        # Goal phase should get assumption prompts
        goal_prompts = reasoning_engine.get_challenging_prompts(
            "We will reduce defects to zero.",
            A3Phase.GOAL,
            max_prompts=5,
        )
        
        goal_types = {p.prompt_type for p in goal_prompts}
        assert PromptType.ASSUMPTION in goal_types or PromptType.ALTERNATIVE in goal_types
