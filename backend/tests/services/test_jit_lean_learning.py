"""
Tests for Just-in-Time Lean Learning & Knowledge Synthesis.

Tests micro-lessons, knowledge retrieval, and standard work evolution.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from sensei.services.jit_lean_learning import (
    # Enums
    LessonCategory,
    TriggerType,
    LessonStatus,
    StandardWorkStatus,
    PerformerLevel,
    # Data models
    MicroLesson,
    LessonDelivery,
    KnowledgeDocument,
    KnowledgeLink,
    StandardWork,
    StandardWorkDraft,
    OperatorPerformance,
    BestPracticeSuggestion,
    # Classes
    MicroLessonEngine,
    KnowledgeRetrievalEngine,
    StandardWorkEvolutionEngine,
    JITLeanLearning,
    # Factory functions
    create_jit_lean_learning,
    create_micro_lesson_engine,
    create_knowledge_retrieval_engine,
    create_standard_work_engine,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def lesson_engine() -> MicroLessonEngine:
    """Create micro-lesson engine."""
    return create_micro_lesson_engine()


@pytest.fixture
def knowledge_engine() -> KnowledgeRetrievalEngine:
    """Create knowledge retrieval engine."""
    return create_knowledge_retrieval_engine()


@pytest.fixture
def evolution_engine() -> StandardWorkEvolutionEngine:
    """Create standard work evolution engine."""
    return create_standard_work_engine()


@pytest.fixture
def jit_learning() -> JITLeanLearning:
    """Create JIT Lean Learning."""
    return create_jit_lean_learning()


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_lesson_category_values(self):
        """Test LessonCategory enum values."""
        assert LessonCategory.SMED.value == "smed"
        assert LessonCategory.FIVE_S.value == "five_s"
        assert LessonCategory.POKA_YOKE.value == "poka_yoke"
        assert LessonCategory.KANBAN.value == "kanban"
        assert LessonCategory.TPM.value == "tpm"
    
    def test_trigger_type_values(self):
        """Test TriggerType enum values."""
        assert TriggerType.HIGH_CHANGEOVER_TIME.value == "high_changeover_time"
        assert TriggerType.HIGH_DEFECT_RATE.value == "high_defect_rate"
        assert TriggerType.LOW_OEE.value == "low_oee"
        assert TriggerType.NEW_OPERATOR.value == "new_operator"
    
    def test_lesson_status_values(self):
        """Test LessonStatus enum values."""
        assert LessonStatus.PENDING.value == "pending"
        assert LessonStatus.DELIVERED.value == "delivered"
        assert LessonStatus.VIEWED.value == "viewed"
        assert LessonStatus.COMPLETED.value == "completed"
        assert LessonStatus.SKIPPED.value == "skipped"
    
    def test_standard_work_status_values(self):
        """Test StandardWorkStatus enum values."""
        assert StandardWorkStatus.DRAFT.value == "draft"
        assert StandardWorkStatus.PENDING_REVIEW.value == "pending_review"
        assert StandardWorkStatus.APPROVED.value == "approved"
        assert StandardWorkStatus.ACTIVE.value == "active"
        assert StandardWorkStatus.DEPRECATED.value == "deprecated"
    
    def test_performer_level_values(self):
        """Test PerformerLevel enum values."""
        assert PerformerLevel.DEVELOPING.value == "developing"
        assert PerformerLevel.PROFICIENT.value == "proficient"
        assert PerformerLevel.ADVANCED.value == "advanced"
        assert PerformerLevel.SUPER_PERFORMER.value == "super_performer"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data models."""
    
    def test_micro_lesson_creation(self):
        """Test MicroLesson creation."""
        lesson = MicroLesson(
            lesson_id="test_lesson",
            category=LessonCategory.SMED,
            title="SMED Basics",
            summary="Learn SMED fundamentals",
            content="Full lesson content...",
        )
        assert lesson.duration_seconds == 60
        assert lesson.lesson_id == "test_lesson"
    
    def test_lesson_delivery_creation(self):
        """Test LessonDelivery creation."""
        delivery = LessonDelivery(
            delivery_id="del_001",
            lesson_id="lesson_001",
            trigger_type=TriggerType.HIGH_CHANGEOVER_TIME,
            trigger_context={"changeover_minutes": 45},
            recipient_id="operator_001",
            delivered_at=datetime.now(),
        )
        assert delivery.status == LessonStatus.PENDING
    
    def test_knowledge_document_creation(self):
        """Test KnowledgeDocument creation."""
        doc = KnowledgeDocument(
            document_id="doc_001",
            title="SMED Guide",
            category=LessonCategory.SMED,
            summary="Complete SMED guide",
            content="Full document content...",
            keywords=["smed", "changeover"],
        )
        assert len(doc.keywords) == 2
    
    def test_knowledge_link_creation(self):
        """Test KnowledgeLink creation."""
        link = KnowledgeLink(
            link_id="link_001",
            a3_id="a3_001",
            a3_field="countermeasure",
            document_ids=["doc_001", "doc_002"],
            relevance_score=0.85,
        )
        assert len(link.document_ids) == 2
    
    def test_standard_work_creation(self):
        """Test StandardWork creation."""
        standard = StandardWork(
            standard_id="std_001",
            title="Assembly Process",
            process_name="Widget Assembly",
            work_center_id="wc_001",
            version="1.0",
            content="Standard work content...",
            steps=[{"step": 1, "action": "Pick part"}],
            cycle_time_seconds=120,
        )
        assert standard.status == StandardWorkStatus.DRAFT
    
    def test_standard_work_draft_creation(self):
        """Test StandardWorkDraft creation."""
        draft = StandardWorkDraft(
            draft_id="draft_001",
            source_a3_id="a3_001",
            source_countermeasure="Add inspection step",
            target_standard_id="std_001",
            proposed_changes={"new_steps": []},
            rationale="Improve quality",
            created_at=datetime.now(),
        )
        assert draft.status == "pending"
    
    def test_operator_performance_creation(self):
        """Test OperatorPerformance creation and level calculation."""
        # Super performer
        super_perf = OperatorPerformance(
            operator_id="op_001",
            name="John Super",
            work_center_id="wc_001",
            oee_score=98,
            quality_score=99,
            productivity_score=96,
        )
        assert super_perf.level == PerformerLevel.SUPER_PERFORMER
        assert super_perf.overall_score >= 95
        
        # Developing performer
        dev_perf = OperatorPerformance(
            operator_id="op_002",
            name="New Operator",
            work_center_id="wc_001",
            oee_score=60,
            quality_score=65,
            productivity_score=55,
        )
        assert dev_perf.level == PerformerLevel.DEVELOPING
    
    def test_best_practice_suggestion_creation(self):
        """Test BestPracticeSuggestion creation."""
        suggestion = BestPracticeSuggestion(
            suggestion_id="sugg_001",
            super_performer_id="op_001",
            super_performer_name="John Super",
            technique="Pre-staging materials",
            observed_benefit="20% faster setup",
            current_baseline=75.0,
            performer_result=95.0,
            improvement_potential=20.0,
            suggested_at=datetime.now(),
        )
        assert suggestion.status == "pending"


# =============================================================================
# MICRO-LESSON ENGINE TESTS
# =============================================================================


class TestMicroLessonEngine:
    """Test MicroLessonEngine."""
    
    def test_engine_initialization(self, lesson_engine):
        """Test engine initializes with lessons."""
        assert len(lesson_engine.lessons) > 0
        assert len(lesson_engine.trigger_mappings) > 0
    
    def test_detect_trigger_high_changeover(self, lesson_engine):
        """Test detecting high changeover trigger."""
        trigger = lesson_engine.detect_trigger({"changeover_time_minutes": 45})
        assert trigger == TriggerType.HIGH_CHANGEOVER_TIME
    
    def test_detect_trigger_high_defect_rate(self, lesson_engine):
        """Test detecting high defect rate trigger."""
        trigger = lesson_engine.detect_trigger({"defect_rate_pct": 5})
        assert trigger == TriggerType.HIGH_DEFECT_RATE
    
    def test_detect_trigger_low_oee(self, lesson_engine):
        """Test detecting low OEE trigger."""
        trigger = lesson_engine.detect_trigger({"oee_pct": 55})
        assert trigger == TriggerType.LOW_OEE
    
    def test_detect_trigger_high_inventory(self, lesson_engine):
        """Test detecting high inventory trigger."""
        trigger = lesson_engine.detect_trigger({"inventory_days": 10})
        assert trigger == TriggerType.HIGH_INVENTORY
    
    def test_detect_trigger_waiting(self, lesson_engine):
        """Test detecting waiting waste trigger."""
        trigger = lesson_engine.detect_trigger({"idle_time_pct": 25})
        assert trigger == TriggerType.WAITING_WASTE
    
    def test_detect_trigger_no_trigger(self, lesson_engine):
        """Test no trigger detected for normal data."""
        trigger = lesson_engine.detect_trigger({
            "changeover_time_minutes": 10,
            "defect_rate_pct": 1,
            "oee_pct": 85,
        })
        assert trigger is None
    
    def test_get_lesson_for_trigger(self, lesson_engine):
        """Test getting lesson for a trigger."""
        delivery = lesson_engine.get_lesson_for_trigger(
            TriggerType.HIGH_CHANGEOVER_TIME,
            "operator_001",
        )
        
        assert delivery is not None
        assert delivery.trigger_type == TriggerType.HIGH_CHANGEOVER_TIME
        assert delivery.status == LessonStatus.DELIVERED
    
    def test_get_lesson_content(self, lesson_engine):
        """Test getting lesson content."""
        lesson = lesson_engine.get_lesson_content("smed_intro")
        
        assert lesson is not None
        assert lesson.category == LessonCategory.SMED
        assert "SMED" in lesson.title
    
    def test_mark_viewed(self, lesson_engine):
        """Test marking lesson as viewed."""
        delivery = lesson_engine.get_lesson_for_trigger(
            TriggerType.HIGH_CHANGEOVER_TIME,
            "operator_002",
        )
        
        result = lesson_engine.mark_viewed(delivery.delivery_id)
        
        assert result
        assert delivery.status == LessonStatus.VIEWED
        assert delivery.viewed_at is not None
    
    def test_mark_completed_with_feedback(self, lesson_engine):
        """Test marking lesson as completed with feedback."""
        delivery = lesson_engine.get_lesson_for_trigger(
            TriggerType.HIGH_DEFECT_RATE,
            "operator_003",
        )
        
        result = lesson_engine.mark_completed(
            delivery.delivery_id,
            rating=5,
            comment="Very helpful!",
        )
        
        assert result
        assert delivery.status == LessonStatus.COMPLETED
        assert delivery.feedback_rating == 5
        assert delivery.feedback_comment == "Very helpful!"
    
    def test_get_delivery_stats(self, lesson_engine):
        """Test getting delivery statistics."""
        # Create some deliveries
        d1 = lesson_engine.get_lesson_for_trigger(TriggerType.HIGH_CHANGEOVER_TIME, "op1")
        d2 = lesson_engine.get_lesson_for_trigger(TriggerType.HIGH_DEFECT_RATE, "op1")
        
        lesson_engine.mark_viewed(d1.delivery_id)
        lesson_engine.mark_completed(d2.delivery_id, rating=4)
        
        stats = lesson_engine.get_delivery_stats("op1")
        
        assert stats["total_delivered"] == 2
        assert stats["viewed"] == 2  # completed counts as viewed
        assert stats["completed"] == 1


# =============================================================================
# KNOWLEDGE RETRIEVAL ENGINE TESTS
# =============================================================================


class TestKnowledgeRetrievalEngine:
    """Test KnowledgeRetrievalEngine."""
    
    def test_engine_initialization(self, knowledge_engine):
        """Test engine initializes with knowledge pack."""
        assert len(knowledge_engine.documents) > 0
    
    def test_add_document(self, knowledge_engine):
        """Test adding a document."""
        doc = KnowledgeDocument(
            document_id="new_doc",
            title="New Document",
            category=LessonCategory.KAIZEN,
            summary="Summary",
            content="Content",
        )
        
        doc_id = knowledge_engine.add_document(doc)
        
        assert doc_id == "new_doc"
        assert "new_doc" in knowledge_engine.documents
    
    def test_search_documents_by_title(self, knowledge_engine):
        """Test searching documents by title."""
        results = knowledge_engine.search_documents("SMED")
        
        assert len(results) >= 1
        assert any("SMED" in r[0].title for r in results)
    
    def test_search_documents_by_keyword(self, knowledge_engine):
        """Test searching documents by keyword."""
        results = knowledge_engine.search_documents("changeover")
        
        assert len(results) >= 1
    
    def test_search_documents_with_a3_field(self, knowledge_engine):
        """Test searching with A3 field relevance."""
        results = knowledge_engine.search_documents(
            "countermeasure mistake proofing",
            a3_field="countermeasure",
        )
        
        assert len(results) >= 1
    
    def test_link_to_a3(self, knowledge_engine):
        """Test creating links from A3 to documents."""
        link = knowledge_engine.link_to_a3(
            "a3_001",
            "countermeasure",
            "Implement poka-yoke device to prevent errors",
        )
        
        assert link.a3_id == "a3_001"
        assert len(link.document_ids) >= 1
    
    def test_get_links_for_a3(self, knowledge_engine):
        """Test getting all links for an A3."""
        knowledge_engine.link_to_a3("a3_001", "problem_statement", "Defects occurring")
        knowledge_engine.link_to_a3("a3_001", "countermeasure", "Add inspection")
        
        links = knowledge_engine.get_links_for_a3("a3_001")
        
        assert len(links) == 2
    
    def test_get_recommended_documents(self, knowledge_engine):
        """Test getting recommended documents for an A3."""
        knowledge_engine.link_to_a3("a3_002", "root_cause", "5 why analysis needed")
        
        docs = knowledge_engine.get_recommended_documents("a3_002")
        
        assert len(docs) >= 1


# =============================================================================
# STANDARD WORK EVOLUTION ENGINE TESTS
# =============================================================================


class TestStandardWorkEvolutionEngine:
    """Test StandardWorkEvolutionEngine."""
    
    def test_register_standard(self, evolution_engine):
        """Test registering a standard."""
        standard = StandardWork(
            standard_id="std_001",
            title="Assembly Standard",
            process_name="Widget Assembly",
            work_center_id="wc_001",
            version="1.0",
            content="Content",
            steps=[],
            cycle_time_seconds=120,
        )
        
        std_id = evolution_engine.register_standard(standard)
        
        assert std_id == "std_001"
        assert "std_001" in evolution_engine.standards
    
    def test_create_standard(self, evolution_engine):
        """Test creating a new standard."""
        standard = evolution_engine.create_standard(
            title="New Standard",
            process_name="New Process",
            work_center_id="wc_001",
            steps=[{"step": 1, "action": "Start"}],
            cycle_time_seconds=60,
            key_points=["Be careful"],
        )
        
        assert standard.standard_id
        assert standard.status == StandardWorkStatus.DRAFT
    
    def test_draft_update_from_a3(self, evolution_engine):
        """Test drafting standard update from A3 countermeasure."""
        # First create a standard
        evolution_engine.create_standard(
            "Existing Standard",
            "Process",
            "wc_001",
            [],
            120,
        )
        
        # Create draft from A3
        draft = evolution_engine.draft_update_from_a3(
            a3_id="a3_001",
            countermeasure="Add quality check step at station 3",
            work_center_id="wc_001",
        )
        
        assert draft.source_a3_id == "a3_001"
        assert draft.status == "pending"
        assert "new_quality_checks" in draft.proposed_changes
    
    def test_approve_draft(self, evolution_engine):
        """Test approving a draft."""
        # Create standard and draft
        std = evolution_engine.create_standard(
            "Standard", "Process", "wc_test", [], 60
        )
        draft = evolution_engine.draft_update_from_a3(
            "a3_test",
            "Add important key point check",
            work_center_id="wc_test",
        )
        draft.target_standard_id = std.standard_id
        
        result = evolution_engine.approve_draft(draft.draft_id, "reviewer_1")
        
        assert result
        assert draft.status == "approved"
        assert draft.reviewed_by == "reviewer_1"
    
    def test_register_operator_performance(self, evolution_engine):
        """Test registering operator performance."""
        perf = evolution_engine.register_operator_performance(
            "op_001",
            "John Doe",
            "wc_001",
            oee_score=85,
            quality_score=90,
            productivity_score=82,
            techniques=["Pre-staging", "Visual checks"],
        )
        
        assert perf.level == PerformerLevel.ADVANCED
        assert "op_001" in evolution_engine.performers
    
    def test_identify_super_performers(self, evolution_engine):
        """Test identifying super performers."""
        # Register various performers
        evolution_engine.register_operator_performance(
            "op_super", "Super Star", "wc_001", 98, 99, 97,
            techniques=["Technique A"],
        )
        evolution_engine.register_operator_performance(
            "op_normal", "Normal Joe", "wc_001", 75, 80, 72,
        )
        
        super_performers = evolution_engine.identify_super_performers("wc_001")
        
        assert len(super_performers) == 1
        assert super_performers[0].operator_id == "op_super"
    
    def test_suggest_best_practice_codification(self, evolution_engine):
        """Test suggesting best practice codification."""
        # Set up performers
        evolution_engine.register_operator_performance(
            "op_super", "Super Star", "wc_001", 98, 99, 97,
            techniques=["Pre-staging materials", "Visual management"],
        )
        evolution_engine.register_operator_performance(
            "op_normal", "Normal Joe", "wc_001", 70, 75, 68,
        )
        
        # Create standard for work center
        evolution_engine.create_standard(
            "WC Standard", "Process", "wc_001", [], 60
        )
        
        suggestions = evolution_engine.suggest_best_practice_codification("wc_001")
        
        assert len(suggestions) >= 1
        assert suggestions[0].super_performer_id == "op_super"
        assert suggestions[0].improvement_potential > 0
    
    def test_get_pending_drafts(self, evolution_engine):
        """Test getting pending drafts."""
        evolution_engine.draft_update_from_a3("a3_1", "Countermeasure 1")
        evolution_engine.draft_update_from_a3("a3_2", "Countermeasure 2")
        
        pending = evolution_engine.get_pending_drafts()
        
        assert len(pending) == 2


# =============================================================================
# JIT LEAN LEARNING TESTS
# =============================================================================


class TestJITLeanLearning:
    """Test JITLeanLearning orchestrator."""
    
    def test_creation(self, jit_learning):
        """Test JIT Lean Learning creation."""
        assert jit_learning.lesson_engine is not None
        assert jit_learning.knowledge_engine is not None
        assert jit_learning.evolution_engine is not None
    
    def test_process_operational_data_with_trigger(self, jit_learning):
        """Test processing operational data that triggers a lesson."""
        result = jit_learning.process_operational_data(
            {"changeover_time_minutes": 45},
            "operator_001",
        )
        
        assert result["trigger_detected"] == "high_changeover_time"
        assert result["lesson_delivered"] is not None
        assert "SMED" in result["lesson_delivered"]["title"]
    
    def test_process_operational_data_no_trigger(self, jit_learning):
        """Test processing operational data without trigger."""
        result = jit_learning.process_operational_data(
            {"changeover_time_minutes": 10, "oee_pct": 90},
            "operator_001",
        )
        
        assert result["trigger_detected"] is None
        assert result["lesson_delivered"] is None
    
    def test_get_lesson_content(self, jit_learning):
        """Test getting lesson content."""
        content = jit_learning.get_lesson_content("smed_intro")
        
        assert content is not None
        assert content["category"] == "smed"
        assert "key_takeaways" in content
    
    def test_link_a3_to_knowledge(self, jit_learning):
        """Test linking A3 to knowledge."""
        result = jit_learning.link_a3_to_knowledge(
            a3_id="a3_test",
            problem_statement="High defect rate in machining",
            root_cause="Tool wear not detected",
            countermeasure="Implement poka-yoke inspection",
        )
        
        assert result["a3_id"] == "a3_test"
        assert "problem_statement" in result["links"]
        assert "root_cause" in result["links"]
        assert "countermeasure" in result["links"]
    
    def test_close_a3_with_standard_update(self, jit_learning):
        """Test closing A3 with standard work update."""
        # Create a standard first
        jit_learning.evolution_engine.create_standard(
            "Machine Standard",
            "Machining",
            "wc_machining",
            [],
            300,
        )
        
        result = jit_learning.close_a3_with_standard_update(
            a3_id="a3_close",
            countermeasure="Add verification step after each part",
            work_center_id="wc_machining",
        )
        
        assert result["a3_id"] == "a3_close"
        assert result["draft_id"]
        assert result["status"] == "pending"
    
    def test_analyze_best_practices(self, jit_learning):
        """Test analyzing best practices."""
        # Set up data
        jit_learning.evolution_engine.register_operator_performance(
            "super_1", "Super Operator", "wc_test",
            98, 99, 97,
            techniques=["Technique 1", "Technique 2"],
        )
        jit_learning.evolution_engine.register_operator_performance(
            "normal_1", "Normal Operator", "wc_test",
            72, 75, 70,
        )
        jit_learning.evolution_engine.create_standard(
            "Test Standard", "Test", "wc_test", [], 60
        )
        
        result = jit_learning.analyze_best_practices("wc_test")
        
        assert result["work_center_id"] == "wc_test"
        assert len(result["super_performers"]) == 1
        assert len(result["suggestions"]) >= 1
    
    def test_get_learning_dashboard(self, jit_learning):
        """Test getting learning dashboard."""
        # Create some activity
        jit_learning.process_operational_data(
            {"changeover_time_minutes": 50},
            "op_1",
        )
        
        dashboard = jit_learning.get_learning_dashboard("op_1")
        
        assert "lessons" in dashboard
        assert "knowledge" in dashboard
        assert "standards" in dashboard
        assert dashboard["lessons"]["total_delivered"] >= 1


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_jit_lean_learning(self):
        """Test creating JIT Lean Learning."""
        learning = create_jit_lean_learning()
        assert isinstance(learning, JITLeanLearning)
    
    def test_create_micro_lesson_engine(self):
        """Test creating micro-lesson engine."""
        engine = create_micro_lesson_engine()
        assert isinstance(engine, MicroLessonEngine)
    
    def test_create_knowledge_retrieval_engine(self):
        """Test creating knowledge retrieval engine."""
        engine = create_knowledge_retrieval_engine()
        assert isinstance(engine, KnowledgeRetrievalEngine)
    
    def test_create_standard_work_engine(self):
        """Test creating standard work engine."""
        engine = create_standard_work_engine()
        assert isinstance(engine, StandardWorkEvolutionEngine)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestJITLeanLearningIntegration:
    """Integration tests for JIT Lean Learning."""
    
    def test_full_a3_to_standard_workflow(self, jit_learning):
        """Test complete A3 to standard work update workflow."""
        # 1. Create a standard for work center
        std = jit_learning.evolution_engine.create_standard(
            title="Assembly Process",
            process_name="Widget Assembly",
            work_center_id="assembly_01",
            steps=[{"step": 1, "action": "Get parts"}],
            cycle_time_seconds=180,
            key_points=["Check part orientation"],
        )
        
        # 2. Link A3 to knowledge
        knowledge_result = jit_learning.link_a3_to_knowledge(
            a3_id="a3_assembly_defects",
            problem_statement="High defect rate in widget assembly",
            root_cause="Part orientation not verified before assembly",
            countermeasure="Add poka-yoke fixture to verify orientation",
        )
        
        assert len(knowledge_result["recommended_documents"]) > 0
        
        # 3. Close A3 and create standard update draft
        close_result = jit_learning.close_a3_with_standard_update(
            a3_id="a3_assembly_defects",
            countermeasure="Add poka-yoke fixture with key orientation check",
            work_center_id="assembly_01",
        )
        
        assert close_result["draft_id"]
        
        # 4. Approve the draft
        approved = jit_learning.evolution_engine.approve_draft(
            close_result["draft_id"],
            "lean_manager",
        )
        
        assert approved
        
        # 5. Verify standard was updated
        updated_std = jit_learning.evolution_engine.standards[std.standard_id]
        assert len(updated_std.key_points) > 1
    
    def test_operational_trigger_to_learning(self, jit_learning):
        """Test complete flow from operational trigger to learning completion."""
        operator_id = "new_operator_01"
        
        # 1. Detect trigger from operational data
        result = jit_learning.process_operational_data(
            {"changeover_time_minutes": 60, "new_operator": True},
            operator_id,
        )
        
        assert result["lesson_delivered"]
        delivery_id = result["lesson_delivered"]["delivery_id"]
        
        # 2. Get lesson content
        lesson_id = result["lesson_delivered"]["lesson_id"]
        content = jit_learning.get_lesson_content(lesson_id)
        
        assert content["content"]
        assert content["key_takeaways"]
        
        # 3. Mark as viewed
        jit_learning.lesson_engine.mark_viewed(delivery_id)
        
        # 4. Complete with feedback
        jit_learning.lesson_engine.mark_completed(
            delivery_id,
            rating=5,
            comment="Very helpful for understanding SMED",
        )
        
        # 5. Check stats
        stats = jit_learning.lesson_engine.get_delivery_stats(operator_id)
        assert stats["completed"] == 1
        assert stats["average_rating"] == 5
    
    def test_super_performer_to_standard_codification(self, jit_learning):
        """Test identifying super performer and codifying techniques."""
        wc_id = "machining_01"
        
        # 1. Register operators with varying performance
        jit_learning.evolution_engine.register_operator_performance(
            "master_machinist", "Master Machinist", wc_id,
            oee_score=98, quality_score=99, productivity_score=96,
            techniques=[
                "Pre-measures all tools before shift",
                "Uses chip color to monitor tool wear",
                "Pre-stages materials by priority",
            ],
        )
        
        for i in range(3):
            jit_learning.evolution_engine.register_operator_performance(
                f"regular_op_{i}", f"Regular Operator {i}", wc_id,
                oee_score=70 + i*3, quality_score=75 + i*2, productivity_score=68 + i*4,
            )
        
        # 2. Create standard for work center
        jit_learning.evolution_engine.create_standard(
            "Machining Standard",
            "CNC Machining",
            wc_id,
            [{"step": 1, "action": "Load part"}],
            600,
        )
        
        # 3. Analyze best practices
        analysis = jit_learning.analyze_best_practices(wc_id)
        
        assert len(analysis["super_performers"]) == 1
        assert analysis["super_performers"][0]["name"] == "Master Machinist"
        assert len(analysis["suggestions"]) == 3  # One per technique
        
        # 4. Verify suggestions have improvement potential
        for suggestion in analysis["suggestions"]:
            assert suggestion["improvement_potential"] > 0
    
    def test_comprehensive_learning_dashboard(self, jit_learning):
        """Test comprehensive learning dashboard."""
        # Create various activities
        jit_learning.process_operational_data(
            {"defect_rate_pct": 5},
            "op_1",
        )
        jit_learning.process_operational_data(
            {"oee_pct": 50},
            "op_2",
        )
        
        jit_learning.link_a3_to_knowledge(
            "a3_1",
            countermeasure="Test countermeasure",
        )
        
        jit_learning.evolution_engine.create_standard(
            "Std 1", "Process", "wc_1", [], 60
        )
        jit_learning.evolution_engine.draft_update_from_a3(
            "a3_draft", "Countermeasure text"
        )
        
        jit_learning.evolution_engine.register_operator_performance(
            "super", "Super", "wc_1", 98, 99, 97, ["Tech 1"]
        )
        
        # Get dashboard
        dashboard = jit_learning.get_learning_dashboard()
        
        assert dashboard["lessons"]["total_delivered"] >= 2
        assert dashboard["knowledge"]["total_documents"] > 0
        assert dashboard["standards"]["total_standards"] >= 1
        assert dashboard["standards"]["pending_drafts"] >= 1
        assert dashboard["standards"]["super_performers"] >= 1
