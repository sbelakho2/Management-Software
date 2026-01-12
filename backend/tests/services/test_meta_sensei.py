"""
Tests for Meta-Sensei: Self-Evolving Knowledge & Intelligence Platform.

Tests cover:
- Self-Evolving Knowledge Base (synthesis, deduplication, site-specific learning)
- Autonomous Documentation & Plan Maintenance
- Code Quality & Technical Debt Guard
- Meta-Learning from Success (best practices, A3 evolution)
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sensei.services.ai.meta_sensei import (
    # Enums
    TemplateType,
    DeduplicationStrategy,
    SiteTermType,
    DocSyncAction,
    CodeIssueType,
    CodeIssueSeverity,
    RefactoringType,
    # Data models
    UserCorrection,
    StandardTemplate,
    KnowledgeChunk,
    DeduplicationResult,
    SiteTerm,
    SiteReranker,
    FeatureDetection,
    DocSyncResult,
    PlanItem,
    PlanSyncResult,
    CodeIssue,
    RefactoringSuggestion,
    QuotePerformance,
    BestPractice,
    A3Effectiveness,
    ReasoningWeight,
    # Knowledge components
    AutonomousKnowledgeSynthesizer,
    SemanticDeduplicator,
    SiteSpecificLearner,
    # Documentation components
    DocImplementationSync,
    DevelopmentPlanTracker,
    # Code quality components
    OnDeviceCodeAuditor,
    AutonomousRefactoringSuggestor,
    # Meta-learning components
    BestPracticeExtractor,
    PrivacyPreservingAggregator,
    A3RecommendationEvolver,
    # Orchestrator
    MetaSensei,
    # Factories
    create_knowledge_synthesizer,
    create_deduplicator,
    create_site_learner,
    create_doc_sync,
    create_plan_tracker,
    create_code_auditor,
    create_refactoring_suggestor,
    create_practice_extractor,
    create_a3_evolver,
    create_meta_sensei,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_corrections():
    """Sample user corrections for testing."""
    base_time = datetime.now()
    corrections = []
    
    # Create 6 similar corrections that should cluster together
    for i in range(6):
        corrections.append(UserCorrection(
            id=f"corr_{i}",
            original_text="Dear Customer, We are pleased to offer...",
            corrected_text="Dear Valued Customer, We are delighted to present...",
            correction_type=TemplateType.RFQ,
            context={"segment": "automotive"},
            user_id=f"user_{i % 3}",
            timestamp=base_time - timedelta(hours=i),
            site_id="site_1",
        ))
    
    return corrections


@pytest.fixture
def sample_chunks():
    """Sample knowledge chunks for testing."""
    return [
        KnowledgeChunk(
            id="chunk_1",
            content="Quality control procedures for automotive parts",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
            metadata={"source": "manual"},
            score=0.9,
            created_at=datetime.now(),
            source="document_1",
        ),
        KnowledgeChunk(
            id="chunk_2",
            content="Quality control guidelines for auto components",  # Similar to chunk_1
            embedding=[0.11, 0.21, 0.31, 0.41, 0.51],  # Similar embedding
            metadata={"source": "manual"},
            score=0.85,
            created_at=datetime.now() - timedelta(days=1),
            source="document_2",
        ),
        KnowledgeChunk(
            id="chunk_3",
            content="Supplier negotiation strategies",  # Different content
            embedding=[0.9, 0.8, 0.7, 0.6, 0.5],  # Different embedding
            metadata={"source": "training"},
            score=0.95,
            created_at=datetime.now(),
            source="document_3",
        ),
    ]


@pytest.fixture
def sample_quotes():
    """Sample quote performance data."""
    quotes = []
    base_time = datetime.now()
    
    # High-performing automotive quotes
    for i in range(6):
        quotes.append(QuotePerformance(
            quote_id=f"quote_auto_{i}",
            margin=0.25 + (i * 0.01),
            win_rate=0.85,
            assumptions=["Standard lead time: 4 weeks", "Material cost escalation clause"],
            segment="automotive",
            site_id="site_1",
            created_at=base_time - timedelta(days=i),
            outcome="won",
        ))
    
    # Medium-performing aerospace quotes
    for i in range(4):
        quotes.append(QuotePerformance(
            quote_id=f"quote_aero_{i}",
            margin=0.18,
            win_rate=0.6,
            assumptions=["Extended warranty: 24 months"],
            segment="aerospace",
            site_id="site_1",
            created_at=base_time - timedelta(days=i),
            outcome="won" if i < 2 else "lost",
        ))
    
    return quotes


@pytest.fixture
def sample_a3s():
    """Sample A3 effectiveness data."""
    return [
        # Process category A3s (need 3+)
        A3Effectiveness(
            a3_id="a3_1",
            countermeasure="Implement process checklist for assembly",
            effectiveness_score=0.9,
            time_to_resolution=5.0,
            recurrence_rate=0.1,
            cost_savings=5000,
            closed_at=datetime.now() - timedelta(days=30),
        ),
        A3Effectiveness(
            a3_id="a3_3",
            countermeasure="Process flow optimization",
            effectiveness_score=0.95,
            time_to_resolution=10.0,
            recurrence_rate=0.05,
            cost_savings=8000,
            closed_at=datetime.now() - timedelta(days=15),
        ),
        A3Effectiveness(
            a3_id="a3_5",
            countermeasure="Update process documentation",
            effectiveness_score=0.88,
            time_to_resolution=3.0,
            recurrence_rate=0.12,
            cost_savings=2000,
            closed_at=datetime.now() - timedelta(days=20),
        ),
        # Training category A3s (need 3+)
        A3Effectiveness(
            a3_id="a3_2",
            countermeasure="Training program for new operators",
            effectiveness_score=0.85,
            time_to_resolution=14.0,
            recurrence_rate=0.15,
            cost_savings=3000,
            closed_at=datetime.now() - timedelta(days=60),
        ),
        A3Effectiveness(
            a3_id="a3_6",
            countermeasure="Skill training for quality inspectors",
            effectiveness_score=0.82,
            time_to_resolution=10.0,
            recurrence_rate=0.18,
            cost_savings=2500,
            closed_at=datetime.now() - timedelta(days=45),
        ),
        A3Effectiveness(
            a3_id="a3_7",
            countermeasure="Knowledge transfer training sessions",
            effectiveness_score=0.78,
            time_to_resolution=7.0,
            recurrence_rate=0.2,
            cost_savings=1800,
            closed_at=datetime.now() - timedelta(days=35),
        ),
        # Equipment category A3s (need 3+)
        A3Effectiveness(
            a3_id="a3_4",
            countermeasure="Equipment calibration schedule",
            effectiveness_score=0.8,
            time_to_resolution=7.0,
            recurrence_rate=0.2,
            cost_savings=2500,
            closed_at=datetime.now() - timedelta(days=45),
        ),
        A3Effectiveness(
            a3_id="a3_8",
            countermeasure="Machine maintenance improvement",
            effectiveness_score=0.87,
            time_to_resolution=12.0,
            recurrence_rate=0.1,
            cost_savings=4000,
            closed_at=datetime.now() - timedelta(days=25),
        ),
        A3Effectiveness(
            a3_id="a3_9",
            countermeasure="Tool replacement schedule",
            effectiveness_score=0.75,
            time_to_resolution=5.0,
            recurrence_rate=0.22,
            cost_savings=1500,
            closed_at=datetime.now() - timedelta(days=40),
        ),
    ]


@pytest.fixture
def temp_source_dir():
    """Create a temporary source directory with Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample Python file with various patterns
        sample_code = '''"""Sample module for testing."""

import os
import subprocess


def simple_function(x: int) -> int:
    """A simple function."""
    return x * 2


class SampleClass:
    """A sample class."""
    
    def __init__(self):
        self.password = "secret123"  # Security issue
    
    def long_method(self, data):
        """A method that is too long."""
        result = []
        for i in range(len(data)):  # Performance issue
            if data[i] > 0:
                if data[i] < 100:
                    if data[i] % 2 == 0:
                        result.append(data[i])
        return result


def dangerous_function(user_input):
    """A function with security issues."""
    eval(user_input)  # Security issue
    os.system(user_input)  # Security issue
'''
        
        src_file = Path(tmpdir) / "sample.py"
        src_file.write_text(sample_code)
        
        yield tmpdir


@pytest.fixture
def temp_doc_file():
    """Create a temporary documentation file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = Path(tmpdir) / "IMPLEMENTATION_SUMMARY.md"
        doc_path.write_text(
            "# Implementation Summary\n\n"
            "## existing_function\n\n"
            "Already documented feature.\n"
        )
        yield str(doc_path)


@pytest.fixture
def temp_plan_file():
    """Create a temporary development plan file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "Development_Plan.md"
        plan_path.write_text(
            "# Development Plan\n\n"
            "## Phase 1\n\n"
            "- [ ] Implement feature A\n"
            "- [x] Implement feature B\n"
            "- [ ] Add sample tests\n"
            "    - [ ] Unit tests\n"
            "    - [ ] Integration tests\n"
        )
        yield str(plan_path)


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test all enums."""
    
    def test_template_type_values(self):
        assert TemplateType.RFQ.value == "rfq"
        assert TemplateType.QUOTE.value == "quote"
        assert TemplateType.BOM.value == "bom"
        assert TemplateType.ASSUMPTION.value == "assumption"
    
    def test_deduplication_strategy_values(self):
        assert DeduplicationStrategy.MERGE.value == "merge"
        assert DeduplicationStrategy.KEEP_LATEST.value == "keep_latest"
        assert DeduplicationStrategy.KEEP_HIGHEST_SCORE.value == "keep_highest_score"
        assert DeduplicationStrategy.ARCHIVE.value == "archive"
    
    def test_site_term_type_values(self):
        assert SiteTermType.PART_NAME.value == "part_name"
        assert SiteTermType.PROCESS.value == "process"
        assert SiteTermType.MATERIAL.value == "material"
    
    def test_doc_sync_action_values(self):
        assert DocSyncAction.ADD.value == "add"
        assert DocSyncAction.UPDATE.value == "update"
        assert DocSyncAction.REMOVE.value == "remove"
    
    def test_code_issue_type_values(self):
        assert CodeIssueType.SECURITY.value == "security"
        assert CodeIssueType.PERFORMANCE.value == "performance"
        assert CodeIssueType.COMPLEXITY.value == "complexity"
    
    def test_code_issue_severity_values(self):
        assert CodeIssueSeverity.CRITICAL.value == "critical"
        assert CodeIssueSeverity.HIGH.value == "high"
        assert CodeIssueSeverity.MEDIUM.value == "medium"
        assert CodeIssueSeverity.LOW.value == "low"
    
    def test_refactoring_type_values(self):
        assert RefactoringType.EXTRACT_METHOD.value == "extract_method"
        assert RefactoringType.SIMPLIFY_CONDITIONAL.value == "simplify_conditional"
        assert RefactoringType.REDUCE_NESTING.value == "reduce_nesting"


# =============================================================================
# AUTONOMOUS KNOWLEDGE SYNTHESIZER TESTS
# =============================================================================


class TestAutonomousKnowledgeSynthesizer:
    """Test knowledge synthesis functionality."""
    
    def test_init_default_params(self):
        synth = AutonomousKnowledgeSynthesizer()
        assert synth.min_corrections == 5
        assert synth.similarity_threshold == 0.8
        assert synth.confidence_threshold == 0.75
    
    def test_init_custom_params(self):
        synth = AutonomousKnowledgeSynthesizer(
            min_corrections=10,
            similarity_threshold=0.9,
            confidence_threshold=0.85,
        )
        assert synth.min_corrections == 10
        assert synth.similarity_threshold == 0.9
    
    def test_add_correction(self, sample_corrections):
        synth = AutonomousKnowledgeSynthesizer()
        for corr in sample_corrections:
            synth.add_correction(corr)
        
        assert len(synth.corrections) == 6
    
    def test_synthesize_templates_sufficient_corrections(self, sample_corrections):
        synth = AutonomousKnowledgeSynthesizer(min_corrections=5)
        for corr in sample_corrections:
            synth.add_correction(corr)
        
        templates = synth.synthesize_templates()
        assert len(templates) >= 1
        
        template = templates[0]
        assert template.template_type == TemplateType.RFQ
        assert template.confidence >= 0.75
    
    def test_synthesize_templates_insufficient_corrections(self):
        synth = AutonomousKnowledgeSynthesizer(min_corrections=10)
        # Add only 3 corrections
        for i in range(3):
            synth.add_correction(UserCorrection(
                id=f"corr_{i}",
                original_text="original",
                corrected_text="corrected",
                correction_type=TemplateType.QUOTE,
                context={},
                user_id="user_1",
                timestamp=datetime.now(),
            ))
        
        templates = synth.synthesize_templates()
        assert len(templates) == 0
    
    def test_get_template_for_type(self, sample_corrections):
        synth = AutonomousKnowledgeSynthesizer(min_corrections=5)
        for corr in sample_corrections:
            synth.add_correction(corr)
        
        synth.synthesize_templates()
        rfq_templates = synth.get_template_for_type(TemplateType.RFQ)
        quote_templates = synth.get_template_for_type(TemplateType.QUOTE)
        
        assert len(rfq_templates) >= 1
        assert len(quote_templates) == 0
    
    def test_update_template(self, sample_corrections):
        synth = AutonomousKnowledgeSynthesizer(min_corrections=5)
        for corr in sample_corrections:
            synth.add_correction(corr)
        
        templates = synth.synthesize_templates()
        if templates:
            template_id = templates[0].id
            updated = synth.update_template(template_id, "New content")
            assert updated is not None
            assert updated.content == "New content"
            assert updated.version == 2
    
    def test_update_nonexistent_template(self):
        synth = AutonomousKnowledgeSynthesizer()
        result = synth.update_template("nonexistent", "content")
        assert result is None


# =============================================================================
# SEMANTIC DEDUPLICATOR TESTS
# =============================================================================


class TestSemanticDeduplicator:
    """Test semantic deduplication functionality."""
    
    def test_init_default_params(self):
        dedup = SemanticDeduplicator()
        assert dedup.similarity_threshold == 0.92
        assert dedup.strategy == DeduplicationStrategy.MERGE
    
    def test_add_chunk(self, sample_chunks):
        dedup = SemanticDeduplicator()
        for chunk in sample_chunks:
            dedup.add_chunk(chunk)
        
        assert len(dedup.chunks) == 3
    
    def test_find_duplicates_similar_chunks(self):
        dedup = SemanticDeduplicator(similarity_threshold=0.9)
        
        # Add two very similar chunks
        dedup.add_chunk(KnowledgeChunk(
            id="c1",
            content="Test content",
            embedding=[1.0, 0.0, 0.0],
            metadata={},
            score=0.9,
            created_at=datetime.now(),
            source="test",
        ))
        dedup.add_chunk(KnowledgeChunk(
            id="c2",
            content="Test content similar",
            embedding=[0.99, 0.01, 0.0],  # Very similar
            metadata={},
            score=0.85,
            created_at=datetime.now(),
            source="test",
        ))
        
        duplicates = dedup.find_duplicates()
        assert len(duplicates) >= 1
    
    def test_find_duplicates_different_chunks(self):
        dedup = SemanticDeduplicator(similarity_threshold=0.95)
        
        # Add two very different chunks
        dedup.add_chunk(KnowledgeChunk(
            id="c1",
            content="Content A",
            embedding=[1.0, 0.0, 0.0],
            metadata={},
            score=0.9,
            created_at=datetime.now(),
            source="test",
        ))
        dedup.add_chunk(KnowledgeChunk(
            id="c2",
            content="Content B",
            embedding=[0.0, 1.0, 0.0],  # Orthogonal - very different
            metadata={},
            score=0.85,
            created_at=datetime.now(),
            source="test",
        ))
        
        duplicates = dedup.find_duplicates()
        assert len(duplicates) == 0
    
    def test_deduplicate_merge_strategy(self):
        dedup = SemanticDeduplicator(
            similarity_threshold=0.9,
            strategy=DeduplicationStrategy.MERGE,
        )
        
        dedup.add_chunk(KnowledgeChunk(
            id="c1",
            content="Content",
            embedding=[1.0, 0.0, 0.0],
            metadata={},
            score=0.9,
            created_at=datetime.now(),
            source="test",
        ))
        dedup.add_chunk(KnowledgeChunk(
            id="c2",
            content="Similar",
            embedding=[0.99, 0.01, 0.0],
            metadata={},
            score=0.85,
            created_at=datetime.now(),
            source="test",
        ))
        
        result = dedup.deduplicate()
        assert result.original_count == 2
        assert result.deduplicated_count == 1
        assert len(result.merged_chunks) == 1
    
    def test_deduplicate_keep_latest_strategy(self):
        dedup = SemanticDeduplicator(
            similarity_threshold=0.9,
            strategy=DeduplicationStrategy.KEEP_LATEST,
        )
        
        old_time = datetime.now() - timedelta(days=7)
        new_time = datetime.now()
        
        dedup.add_chunk(KnowledgeChunk(
            id="old",
            content="Old content",
            embedding=[1.0, 0.0, 0.0],
            metadata={},
            score=0.95,
            created_at=old_time,
            source="test",
        ))
        dedup.add_chunk(KnowledgeChunk(
            id="new",
            content="New content",
            embedding=[0.99, 0.01, 0.0],
            metadata={},
            score=0.85,
            created_at=new_time,
            source="test",
        ))
        
        result = dedup.deduplicate()
        assert "new" in dedup.chunks
    
    def test_deduplicate_archive_strategy(self):
        dedup = SemanticDeduplicator(
            similarity_threshold=0.9,
            strategy=DeduplicationStrategy.ARCHIVE,
        )
        
        dedup.add_chunk(KnowledgeChunk(
            id="c1",
            content="Content 1",
            embedding=[1.0, 0.0, 0.0],
            metadata={},
            score=0.9,
            created_at=datetime.now(),
            source="test",
        ))
        dedup.add_chunk(KnowledgeChunk(
            id="c2",
            content="Content 2",
            embedding=[0.99, 0.01, 0.0],
            metadata={},
            score=0.85,
            created_at=datetime.now(),
            source="test",
        ))
        
        result = dedup.deduplicate()
        assert len(result.archived_chunks) >= 1


# =============================================================================
# SITE-SPECIFIC LEARNER TESTS
# =============================================================================


class TestSiteSpecificLearner:
    """Test site-specific learning functionality."""
    
    def test_init(self):
        learner = SiteSpecificLearner("site_1")
        assert learner.site_id == "site_1"
        assert len(learner.terms) == 0
    
    def test_learn_term(self):
        learner = SiteSpecificLearner("site_1")
        learner.learn_term("Widget-X100", SiteTermType.PART_NAME, "Used in assembly line A")
        
        assert "widget-x100" in learner.terms
        assert learner.terms["widget-x100"].frequency == 1
    
    def test_learn_term_multiple_times(self):
        learner = SiteSpecificLearner("site_1")
        learner.learn_term("Widget-X100", SiteTermType.PART_NAME, "Context 1")
        learner.learn_term("Widget-X100", SiteTermType.PART_NAME, "Context 2")
        learner.learn_term("Widget-X100", SiteTermType.PART_NAME, "Context 3")
        
        term = learner.terms["widget-x100"]
        assert term.frequency == 3
        assert len(term.contexts) == 3
    
    def test_add_synonym(self):
        learner = SiteSpecificLearner("site_1")
        learner.learn_term("Widget", SiteTermType.PART_NAME, "Context")
        
        result = learner.add_synonym("Widget", "Gadget")
        assert result is True
        assert "Gadget" in learner.terms["widget"].synonyms
    
    def test_add_synonym_nonexistent_term(self):
        learner = SiteSpecificLearner("site_1")
        result = learner.add_synonym("NonExistent", "Synonym")
        assert result is False
    
    def test_train_reranker(self):
        learner = SiteSpecificLearner("site_1")
        
        # Learn multiple terms
        for i in range(5):
            learner.learn_term(f"Part-{i}", SiteTermType.PART_NAME, f"Context {i}")
        learner.learn_term("Part-0", SiteTermType.PART_NAME, "Additional context")
        
        reranker = learner.train_reranker()
        
        assert reranker.site_id == "site_1"
        assert len(reranker.terms) == 5
        assert len(reranker.term_weights) == 5
        assert reranker.accuracy > 0
    
    def test_rerank_results_no_reranker(self):
        learner = SiteSpecificLearner("site_1")
        results = [("Content A", 0.9), ("Content B", 0.8)]
        
        reranked = learner.rerank_results(results)
        assert reranked == results
    
    def test_rerank_results_with_reranker(self):
        learner = SiteSpecificLearner("site_1")
        learner.learn_term("important", SiteTermType.PROCESS, "Context")
        learner.learn_term("important", SiteTermType.PROCESS, "Context 2")
        learner.train_reranker()
        
        results = [
            ("Regular content", 0.8),
            ("Content with important term", 0.75),
        ]
        
        reranked = learner.rerank_results(results)
        # The result with "important" should be boosted above the regular content
        # Find the boosted result
        important_score = next(s for c, s in reranked if "important" in c)
        regular_score = next(s for c, s in reranked if "Regular" in c)
        assert important_score > 0.75  # Should be boosted from original


# =============================================================================
# DOCUMENTATION SYNC TESTS
# =============================================================================


class TestDocImplementationSync:
    """Test documentation sync functionality."""
    
    def test_init(self, temp_source_dir, temp_doc_file):
        sync = DocImplementationSync(temp_source_dir, temp_doc_file)
        assert sync.source_dir == Path(temp_source_dir)
        assert sync.doc_file == Path(temp_doc_file)
    
    def test_scan_source_files(self, temp_source_dir, temp_doc_file):
        sync = DocImplementationSync(temp_source_dir, temp_doc_file)
        features = sync.scan_source_files()
        
        # Should find functions and classes
        assert len(features) >= 2
        names = [f.name for f in features]
        assert "simple_function" in names
        assert "SampleClass" in names
    
    def test_load_documented_features(self, temp_source_dir, temp_doc_file):
        sync = DocImplementationSync(temp_source_dir, temp_doc_file)
        documented = sync.load_documented_features()
        
        assert "existing_function" in documented
    
    def test_generate_doc_updates(self, temp_source_dir, temp_doc_file):
        sync = DocImplementationSync(temp_source_dir, temp_doc_file)
        sync.scan_source_files()
        updates = sync.generate_doc_updates()
        
        # Should have updates for undocumented features
        assert len(updates) >= 1
        assert all(action == DocSyncAction.ADD for action, _ in updates)
    
    def test_sync(self, temp_source_dir, temp_doc_file):
        sync = DocImplementationSync(temp_source_dir, temp_doc_file)
        result = sync.sync()
        
        assert isinstance(result, DocSyncResult)
        assert len(result.features_detected) >= 2
        assert result.sync_time is not None


# =============================================================================
# DEVELOPMENT PLAN TRACKER TESTS
# =============================================================================


class TestDevelopmentPlanTracker:
    """Test development plan tracking functionality."""
    
    def test_init(self, temp_plan_file, temp_source_dir):
        tracker = DevelopmentPlanTracker(temp_plan_file, temp_source_dir)
        assert tracker.plan_file == Path(temp_plan_file)
    
    def test_parse_plan(self, temp_plan_file, temp_source_dir):
        tracker = DevelopmentPlanTracker(temp_plan_file, temp_source_dir)
        items = tracker.parse_plan()
        
        assert len(items) == 5
        checked_items = [i for i in items if i.checked]
        assert len(checked_items) == 1
    
    def test_parse_plan_sections(self, temp_plan_file, temp_source_dir):
        tracker = DevelopmentPlanTracker(temp_plan_file, temp_source_dir)
        items = tracker.parse_plan()
        
        # All items should have section info
        for item in items:
            assert item.section is not None
    
    def test_verify_item_with_matching_file(self, temp_source_dir, temp_plan_file):
        tracker = DevelopmentPlanTracker(temp_plan_file, temp_source_dir)
        tracker.parse_plan()
        
        # Create a mock item that matches our sample.py file
        item = PlanItem(
            line_number=1,
            text="Add sample module",
            checked=False,
            indent_level=0,
            section="Phase 1",
        )
        
        result = tracker.verify_item_implementation(item)
        assert result is True
    
    def test_sync_plan(self, temp_source_dir, temp_plan_file):
        tracker = DevelopmentPlanTracker(temp_plan_file, temp_source_dir)
        result = tracker.sync_plan()
        
        assert isinstance(result, PlanSyncResult)
        assert result.total_items == 5
        assert result.checked_items >= 1


# =============================================================================
# CODE AUDITOR TESTS
# =============================================================================


class TestOnDeviceCodeAuditor:
    """Test code auditing functionality."""
    
    def test_init(self, temp_source_dir):
        auditor = OnDeviceCodeAuditor(temp_source_dir)
        assert auditor.source_dir == Path(temp_source_dir)
    
    def test_audit_finds_security_issues(self, temp_source_dir):
        auditor = OnDeviceCodeAuditor(temp_source_dir)
        issues = auditor.audit()
        
        security_issues = [i for i in issues if i.issue_type == CodeIssueType.SECURITY]
        assert len(security_issues) >= 2  # eval and os.system
    
    def test_audit_finds_performance_issues(self, temp_source_dir):
        auditor = OnDeviceCodeAuditor(temp_source_dir)
        issues = auditor.audit()
        
        perf_issues = [i for i in issues if i.issue_type == CodeIssueType.PERFORMANCE]
        assert len(perf_issues) >= 1  # range(len())
    
    def test_audit_sorted_by_severity(self, temp_source_dir):
        auditor = OnDeviceCodeAuditor(temp_source_dir)
        issues = auditor.audit()
        
        if len(issues) >= 2:
            severity_order = {
                CodeIssueSeverity.CRITICAL: 0,
                CodeIssueSeverity.HIGH: 1,
                CodeIssueSeverity.MEDIUM: 2,
                CodeIssueSeverity.LOW: 3,
                CodeIssueSeverity.INFO: 4,
            }
            for i in range(len(issues) - 1):
                assert severity_order[issues[i].severity] <= severity_order[issues[i + 1].severity]
    
    def test_get_issues_by_type(self, temp_source_dir):
        auditor = OnDeviceCodeAuditor(temp_source_dir)
        auditor.audit()
        
        security = auditor.get_issues_by_type(CodeIssueType.SECURITY)
        assert all(i.issue_type == CodeIssueType.SECURITY for i in security)
    
    def test_get_issues_by_severity(self, temp_source_dir):
        auditor = OnDeviceCodeAuditor(temp_source_dir)
        auditor.audit()
        
        critical = auditor.get_issues_by_severity(CodeIssueSeverity.CRITICAL)
        assert all(i.severity == CodeIssueSeverity.CRITICAL for i in critical)
    
    def test_audit_nonexistent_dir(self):
        auditor = OnDeviceCodeAuditor("/nonexistent/path")
        issues = auditor.audit()
        assert issues == []


# =============================================================================
# REFACTORING SUGGESTOR TESTS
# =============================================================================


class TestAutonomousRefactoringSuggestor:
    """Test refactoring suggestion functionality."""
    
    def test_init(self, temp_source_dir):
        suggestor = AutonomousRefactoringSuggestor(temp_source_dir)
        assert suggestor.source_dir == Path(temp_source_dir)
    
    def test_analyze(self, temp_source_dir):
        suggestor = AutonomousRefactoringSuggestor(temp_source_dir)
        suggestions = suggestor.analyze()
        
        # Should find at least the nested conditionals
        assert len(suggestions) >= 1
    
    def test_suggestions_have_required_fields(self, temp_source_dir):
        suggestor = AutonomousRefactoringSuggestor(temp_source_dir)
        suggestions = suggestor.analyze()
        
        for s in suggestions:
            assert s.suggestion_id is not None
            assert s.file_path is not None
            assert s.refactoring_type in RefactoringType
            assert s.description is not None
    
    def test_get_hot_paths_no_profiling(self, temp_source_dir):
        suggestor = AutonomousRefactoringSuggestor(temp_source_dir)
        suggestor.analyze()
        
        hot = suggestor.get_hot_paths()
        assert len(hot) <= 10
    
    def test_get_hot_paths_with_profiling(self, temp_source_dir):
        suggestor = AutonomousRefactoringSuggestor(temp_source_dir)
        suggestor.analyze()
        
        profiling = {str(Path(temp_source_dir) / "sample.py"): 100.0}
        hot = suggestor.get_hot_paths(profiling)
        
        # Only suggestions from profiled files
        for s in hot:
            assert s.file_path in profiling


# =============================================================================
# BEST PRACTICE EXTRACTOR TESTS
# =============================================================================


class TestBestPracticeExtractor:
    """Test best practice extraction functionality."""
    
    def test_init(self):
        extractor = BestPracticeExtractor()
        assert extractor.min_margin == 0.2
        assert extractor.min_win_rate == 0.7
        assert extractor.min_samples == 5
    
    def test_add_quote(self, sample_quotes):
        extractor = BestPracticeExtractor()
        for quote in sample_quotes:
            extractor.add_quote(quote)
        
        assert len(extractor.quotes) == 10
    
    def test_extract_best_practices(self, sample_quotes):
        extractor = BestPracticeExtractor(min_margin=0.2, min_samples=5)
        for quote in sample_quotes:
            extractor.add_quote(quote)
        
        practices = extractor.extract_best_practices()
        
        # Should have at least one practice for automotive
        assert len(practices) >= 1
        auto_practices = [p for p in practices if p.segment == "automotive"]
        assert len(auto_practices) >= 1
    
    def test_extract_best_practices_insufficient_samples(self):
        extractor = BestPracticeExtractor(min_samples=20)
        for i in range(5):
            extractor.add_quote(QuotePerformance(
                quote_id=f"q{i}",
                margin=0.3,
                win_rate=0.9,
                assumptions=["Standard terms"],
                segment="test",
                site_id="site_1",
                created_at=datetime.now(),
                outcome="won",
            ))
        
        practices = extractor.extract_best_practices()
        assert len(practices) == 0
    
    def test_get_practices_for_segment(self, sample_quotes):
        extractor = BestPracticeExtractor(min_margin=0.2, min_samples=5)
        for quote in sample_quotes:
            extractor.add_quote(quote)
        
        extractor.extract_best_practices()
        
        auto = extractor.get_practices_for_segment("automotive")
        assert all(p.segment == "automotive" for p in auto)


# =============================================================================
# PRIVACY PRESERVING AGGREGATOR TESTS
# =============================================================================


class TestPrivacyPreservingAggregator:
    """Test privacy-preserving aggregation functionality."""
    
    def test_anonymize_text_names(self):
        agg = PrivacyPreservingAggregator()
        text = "Contact John Smith for details"
        result = agg.anonymize_text(text)
        
        assert "John Smith" not in result
        assert "[PERSON]" in result
    
    def test_anonymize_text_phone(self):
        agg = PrivacyPreservingAggregator()
        text = "Call us at 555-123-4567"
        result = agg.anonymize_text(text)
        
        assert "555-123-4567" not in result
        assert "[PHONE]" in result
    
    def test_anonymize_text_email(self):
        agg = PrivacyPreservingAggregator()
        text = "Email: john@example.com"
        result = agg.anonymize_text(text)
        
        assert "john@example.com" not in result
        assert "[EMAIL]" in result
    
    def test_anonymize_text_amount(self):
        agg = PrivacyPreservingAggregator()
        text = "The total cost is $1,500.00"
        result = agg.anonymize_text(text)
        
        assert "$1,500.00" not in result
        assert "[AMOUNT]" in result
    
    def test_anonymize_practice(self):
        agg = PrivacyPreservingAggregator()
        practice = BestPractice(
            id="bp_1",
            name="John Smith's approach",
            description="Contact customer at 555-123-4567",
            source_quotes=["q1", "q2", "q3"],
            assumptions=["Price is $1,000"],
            segment="automotive",
            avg_margin=0.25,
            win_rate=0.9,
            extracted_at=datetime.now(),
            anonymized=False,
        )
        
        anon = agg.anonymize_practice(practice)
        
        assert anon.anonymized is True
        assert len(anon.source_quotes) == 0  # Removed
        assert "[PERSON]" in anon.name
    
    def test_anonymize_batch(self):
        agg = PrivacyPreservingAggregator()
        practices = [
            BestPractice(
                id=f"bp_{i}",
                name=f"Practice {i}",
                description="Description",
                source_quotes=[],
                assumptions=[],
                segment="test",
                avg_margin=0.2,
                win_rate=0.8,
                extracted_at=datetime.now(),
                anonymized=False,
            )
            for i in range(3)
        ]
        
        anonymized = agg.anonymize_batch(practices)
        assert len(anonymized) == 3
        assert all(p.anonymized for p in anonymized)
    
    def test_verify_anonymization_clean(self):
        agg = PrivacyPreservingAggregator()
        text = "This is clean text with no PII"
        assert agg.verify_anonymization(text) is True
    
    def test_verify_anonymization_with_pii(self):
        agg = PrivacyPreservingAggregator()
        text = "Contact john@example.com for details"
        assert agg.verify_anonymization(text) is False


# =============================================================================
# A3 RECOMMENDATION EVOLVER TESTS
# =============================================================================


class TestA3RecommendationEvolver:
    """Test A3 recommendation evolution functionality."""
    
    def test_init(self):
        evolver = A3RecommendationEvolver()
        assert evolver.learning_rate == 0.1
    
    def test_add_a3_result(self, sample_a3s):
        evolver = A3RecommendationEvolver()
        for a3 in sample_a3s:
            evolver.add_a3_result(a3)
        
        assert len(evolver.a3_history) == 9
    
    def test_evolve_weights(self, sample_a3s):
        evolver = A3RecommendationEvolver()
        for a3 in sample_a3s:
            evolver.add_a3_result(a3)
        
        weights = evolver.evolve_weights()
        
        # Should have weights for process and training categories
        assert "process" in weights
        assert "training" in weights
        assert "equipment" in weights
    
    def test_get_weight_existing(self, sample_a3s):
        evolver = A3RecommendationEvolver()
        for a3 in sample_a3s:
            evolver.add_a3_result(a3)
        
        evolver.evolve_weights()
        
        weight = evolver.get_weight("process")
        assert 0 <= weight <= 2.0
    
    def test_get_weight_nonexistent(self):
        evolver = A3RecommendationEvolver()
        weight = evolver.get_weight("nonexistent")
        assert weight == 0.5  # Default
    
    def test_recommend_countermeasure_priority(self, sample_a3s):
        evolver = A3RecommendationEvolver()
        for a3 in sample_a3s:
            evolver.add_a3_result(a3)
        
        evolver.evolve_weights()
        
        countermeasures = [
            "Update process documentation",
            "Training for operators",
            "Replace equipment",
        ]
        
        prioritized = evolver.recommend_countermeasure_priority(countermeasures)
        
        assert len(prioritized) == 3
        # Should be sorted by weight (descending)
        for i in range(len(prioritized) - 1):
            assert prioritized[i][1] >= prioritized[i + 1][1]


# =============================================================================
# META-SENSEI ORCHESTRATOR TESTS
# =============================================================================


class TestMetaSensei:
    """Test MetaSensei orchestrator functionality."""
    
    def test_init(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(
            source_dir=temp_source_dir,
            doc_file=temp_doc_file,
            plan_file=temp_plan_file,
            site_id="test_site",
        )
        
        assert meta.source_dir == temp_source_dir
        assert meta.site_id == "test_site"
        assert meta.knowledge_synthesizer is not None
        assert meta.deduplicator is not None
    
    def test_run_knowledge_synthesis(self, temp_source_dir, temp_doc_file, temp_plan_file, sample_corrections):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        
        # Add corrections
        for corr in sample_corrections:
            meta.knowledge_synthesizer.add_correction(corr)
        
        templates = meta.run_knowledge_synthesis()
        assert len(templates) >= 1
    
    def test_run_deduplication(self, temp_source_dir, temp_doc_file, temp_plan_file, sample_chunks):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        
        for chunk in sample_chunks:
            meta.deduplicator.add_chunk(chunk)
        
        result = meta.run_deduplication()
        assert isinstance(result, DeduplicationResult)
    
    def test_train_site_model(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        
        meta.site_learner.learn_term("TestTerm", SiteTermType.PART_NAME, "Context")
        
        model = meta.train_site_model()
        assert isinstance(model, SiteReranker)
    
    def test_sync_documentation(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        result = meta.sync_documentation()
        
        assert isinstance(result, DocSyncResult)
    
    def test_sync_plan(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        result = meta.sync_plan()
        
        assert isinstance(result, PlanSyncResult)
    
    def test_run_code_audit(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        issues = meta.run_code_audit()
        
        assert isinstance(issues, list)
        assert len(issues) >= 1
    
    def test_get_refactoring_suggestions(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        suggestions = meta.get_refactoring_suggestions()
        
        assert isinstance(suggestions, list)
    
    def test_extract_best_practices(self, temp_source_dir, temp_doc_file, temp_plan_file, sample_quotes):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        
        for quote in sample_quotes:
            meta.practice_extractor.add_quote(quote)
        
        practices = meta.extract_best_practices()
        # Should be anonymized
        assert all(p.anonymized for p in practices)
    
    def test_evolve_reasoning_weights(self, temp_source_dir, temp_doc_file, temp_plan_file, sample_a3s):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        
        for a3 in sample_a3s:
            meta.a3_evolver.add_a3_result(a3)
        
        weights = meta.evolve_reasoning_weights()
        assert len(weights) >= 1
    
    def test_run_full_cycle(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = MetaSensei(temp_source_dir, temp_doc_file, temp_plan_file)
        
        result = meta.run_full_cycle()
        
        assert "templates_created" in result
        assert "deduplication" in result
        assert "doc_sync" in result
        assert "plan_sync" in result
        assert "code_issues" in result
        assert "cycle_time" in result


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_knowledge_synthesizer(self):
        synth = create_knowledge_synthesizer(min_corrections=10)
        assert synth.min_corrections == 10
    
    def test_create_deduplicator(self):
        dedup = create_deduplicator(
            similarity_threshold=0.95,
            strategy=DeduplicationStrategy.ARCHIVE,
        )
        assert dedup.similarity_threshold == 0.95
        assert dedup.strategy == DeduplicationStrategy.ARCHIVE
    
    def test_create_site_learner(self):
        learner = create_site_learner("site_x")
        assert learner.site_id == "site_x"
    
    def test_create_doc_sync(self, temp_source_dir, temp_doc_file):
        sync = create_doc_sync(temp_source_dir, temp_doc_file)
        assert sync.source_dir == Path(temp_source_dir)
    
    def test_create_plan_tracker(self, temp_plan_file, temp_source_dir):
        tracker = create_plan_tracker(temp_plan_file, temp_source_dir)
        assert tracker.plan_file == Path(temp_plan_file)
    
    def test_create_code_auditor(self, temp_source_dir):
        auditor = create_code_auditor(temp_source_dir)
        assert auditor.source_dir == Path(temp_source_dir)
    
    def test_create_refactoring_suggestor(self, temp_source_dir):
        suggestor = create_refactoring_suggestor(temp_source_dir)
        assert suggestor.source_dir == Path(temp_source_dir)
    
    def test_create_practice_extractor(self):
        extractor = create_practice_extractor(min_margin=0.15, min_win_rate=0.65)
        assert extractor.min_margin == 0.15
        assert extractor.min_win_rate == 0.65
    
    def test_create_a3_evolver(self):
        evolver = create_a3_evolver(learning_rate=0.2)
        assert evolver.learning_rate == 0.2
    
    def test_create_meta_sensei(self, temp_source_dir, temp_doc_file, temp_plan_file):
        meta = create_meta_sensei(
            source_dir=temp_source_dir,
            doc_file=temp_doc_file,
            plan_file=temp_plan_file,
            site_id="factory_test",
        )
        assert meta.site_id == "factory_test"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data model instantiation."""
    
    def test_user_correction(self):
        corr = UserCorrection(
            id="c1",
            original_text="original",
            corrected_text="corrected",
            correction_type=TemplateType.RFQ,
            context={"key": "value"},
            user_id="user1",
            timestamp=datetime.now(),
            site_id="site1",
        )
        assert corr.id == "c1"
        assert corr.correction_type == TemplateType.RFQ
    
    def test_standard_template(self):
        template = StandardTemplate(
            id="t1",
            name="Template 1",
            template_type=TemplateType.QUOTE,
            content="Content here",
            source_corrections=["c1", "c2"],
            confidence=0.9,
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert template.confidence == 0.9
    
    def test_knowledge_chunk(self):
        chunk = KnowledgeChunk(
            id="k1",
            content="Knowledge content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"source": "doc"},
            score=0.85,
            created_at=datetime.now(),
            source="document",
        )
        assert len(chunk.embedding) == 3
    
    def test_code_issue(self):
        issue = CodeIssue(
            issue_id="i1",
            file_path="/path/to/file.py",
            line_number=42,
            issue_type=CodeIssueType.SECURITY,
            severity=CodeIssueSeverity.CRITICAL,
            message="Security vulnerability",
            code_snippet="eval(input)",
            suggestion="Avoid eval()",
        )
        assert issue.severity == CodeIssueSeverity.CRITICAL
    
    def test_refactoring_suggestion(self):
        suggestion = RefactoringSuggestion(
            suggestion_id="r1",
            file_path="/path/to/file.py",
            line_range=(10, 50),
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            description="Extract method",
            original_code="def long_method...",
            suggested_code="def shorter_method...",
            estimated_improvement="Readability +30%",
            priority=1,
        )
        assert suggestion.refactoring_type == RefactoringType.EXTRACT_METHOD
    
    def test_best_practice(self):
        practice = BestPractice(
            id="bp1",
            name="Best Practice 1",
            description="Description",
            source_quotes=["q1", "q2"],
            assumptions=["A1", "A2"],
            segment="automotive",
            avg_margin=0.25,
            win_rate=0.9,
            extracted_at=datetime.now(),
            anonymized=False,
        )
        assert practice.avg_margin == 0.25
    
    def test_reasoning_weight(self):
        weight = ReasoningWeight(
            category="process",
            weight=0.75,
            source_a3s=["a1", "a2"],
            last_updated=datetime.now(),
            adjustment_history=[],
        )
        assert weight.weight == 0.75


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_synthesizer_empty_corrections(self):
        synth = AutonomousKnowledgeSynthesizer()
        templates = synth.synthesize_templates()
        assert templates == []
    
    def test_deduplicator_empty_chunks(self):
        dedup = SemanticDeduplicator()
        result = dedup.deduplicate()
        assert result.original_count == 0
        assert result.deduplicated_count == 0
    
    def test_deduplicator_zero_vector(self):
        dedup = SemanticDeduplicator()
        dedup.add_chunk(KnowledgeChunk(
            id="c1",
            content="Content",
            embedding=[0.0, 0.0, 0.0],  # Zero vector
            metadata={},
            score=0.5,
            created_at=datetime.now(),
            source="test",
        ))
        dedup.add_chunk(KnowledgeChunk(
            id="c2",
            content="Content 2",
            embedding=[0.0, 0.0, 0.0],  # Zero vector
            metadata={},
            score=0.5,
            created_at=datetime.now(),
            source="test",
        ))
        
        # Should not raise, similarity should be 0
        dups = dedup.find_duplicates()
        assert len(dups) == 0
    
    def test_site_learner_empty_training(self):
        learner = SiteSpecificLearner("site_1")
        reranker = learner.train_reranker()
        
        assert len(reranker.terms) == 0
        assert len(reranker.term_weights) == 0
    
    def test_extractor_no_winning_quotes(self):
        extractor = BestPracticeExtractor()
        
        for i in range(10):
            extractor.add_quote(QuotePerformance(
                quote_id=f"q{i}",
                margin=0.3,
                win_rate=0.0,
                assumptions=["Term"],
                segment="test",
                site_id="site",
                created_at=datetime.now(),
                outcome="lost",  # All lost
            ))
        
        practices = extractor.extract_best_practices()
        assert len(practices) == 0
    
    def test_evolver_insufficient_a3s(self):
        evolver = A3RecommendationEvolver()
        
        # Only 2 A3s per category - not enough
        evolver.add_a3_result(A3Effectiveness(
            a3_id="a1",
            countermeasure="Process improvement",
            effectiveness_score=0.9,
            time_to_resolution=5,
            recurrence_rate=0.1,
            cost_savings=1000,
            closed_at=datetime.now(),
        ))
        evolver.add_a3_result(A3Effectiveness(
            a3_id="a2",
            countermeasure="Another process step",
            effectiveness_score=0.85,
            time_to_resolution=7,
            recurrence_rate=0.15,
            cost_savings=800,
            closed_at=datetime.now(),
        ))
        
        weights = evolver.evolve_weights()
        assert "process" not in weights  # Not enough samples
    
    def test_doc_sync_nonexistent_source(self, temp_doc_file):
        sync = DocImplementationSync("/nonexistent/path", temp_doc_file)
        features = sync.scan_source_files()
        assert features == []
    
    def test_plan_tracker_nonexistent_plan(self, temp_source_dir):
        tracker = DevelopmentPlanTracker("/nonexistent/plan.md", temp_source_dir)
        items = tracker.parse_plan()
        assert items == []
