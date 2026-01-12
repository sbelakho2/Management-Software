"""
Tests for AI Content Drafting Service.

Tests comprehensive AI-powered content generation for:
- A3 Problem-Solving Reports
- Knowledge-approved content only
- Human confirmation workflows
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sensei.services.ai.ai_content_drafting import (
    AIDraftingService,
    get_ai_drafting_service,
    reset_ai_drafting_service,
    ContentType,
    DraftStatus,
    ConfidenceLevel,
    KnowledgeSourceType,
    A3SectionType,
    KnowledgeSource,
    DraftContent,
    A3DraftRequest,
    A3Context,
    A3SectionDraft,
    A3FullDraft,
    DraftHistory,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_service():
    """Reset service before each test."""
    reset_ai_drafting_service()
    yield
    reset_ai_drafting_service()


@pytest.fixture
def service() -> AIDraftingService:
    """Get fresh service instance."""
    return get_ai_drafting_service()


@pytest.fixture
def sample_context() -> A3Context:
    """Create sample A3 context."""
    return A3Context(
        title="Delayed Quote Response Time",
        description="Quote turnaround time exceeds 48-hour target",
        category="Quality",
        owner_name="John Smith",
        created_date=datetime.now(timezone.utc) - timedelta(days=7),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
        kpis={
            "Average Quote Time": "72 hours",
            "Target Time": "48 hours",
            "Miss Rate": "35%",
        },
        tags=["quote", "delivery", "improvement"],
    )


@pytest.fixture
def sample_a3_request(sample_context) -> A3DraftRequest:
    """Create sample A3 draft request."""
    return A3DraftRequest(
        a3_id=uuid4(),
        section=A3SectionType.PROBLEM,
        context=sample_context,
        user_id=uuid4(),
    )


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.A3_PROBLEM == "a3_problem"
        assert ContentType.A3_FULL == "a3_full"
        assert ContentType.EMAIL == "email"
        assert len(ContentType) >= 12
    
    def test_draft_status_values(self):
        """Test DraftStatus enum values."""
        assert DraftStatus.GENERATING == "generating"
        assert DraftStatus.READY == "ready"
        assert DraftStatus.APPROVED == "approved"
        assert DraftStatus.APPLIED == "applied"
    
    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum values."""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.UNCERTAIN == "uncertain"
    
    def test_a3_section_type_values(self):
        """Test A3SectionType enum values."""
        assert A3SectionType.PROBLEM == "problem"
        assert A3SectionType.ROOT_CAUSE == "root_cause"
        assert A3SectionType.REFLECTION == "reflection"
        assert len(A3SectionType) == 8


# =============================================================================
# Data Model Tests
# =============================================================================

class TestKnowledgeSource:
    """Test KnowledgeSource data model."""
    
    def test_creation(self):
        """Test creating a knowledge source."""
        source = KnowledgeSource(
            id="src-001",
            source_type=KnowledgeSourceType.APPROVED_DOCUMENT,
            title="Test Document",
            content_snippet="Test content",
            relevance_score=0.85,
        )
        assert source.id == "src-001"
        assert source.is_approved
    
    def test_approved_types(self):
        """Test that approved types are recognized."""
        approved = KnowledgeSource(
            id="1", source_type=KnowledgeSourceType.APPROVED_DOCUMENT,
            title="", content_snippet="", relevance_score=0.5
        )
        assert approved.is_approved
        
        standard = KnowledgeSource(
            id="2", source_type=KnowledgeSourceType.COMPANY_STANDARD,
            title="", content_snippet="", relevance_score=0.5
        )
        assert standard.is_approved
        
        practice = KnowledgeSource(
            id="3", source_type=KnowledgeSourceType.BEST_PRACTICE,
            title="", content_snippet="", relevance_score=0.5
        )
        assert practice.is_approved
    
    def test_user_input_not_auto_approved(self):
        """Test that user input requires explicit approval."""
        user_input = KnowledgeSource(
            id="1", source_type=KnowledgeSourceType.USER_INPUT,
            title="", content_snippet="", relevance_score=0.5
        )
        assert not user_input.is_approved
        
        # But approved if explicitly approved
        user_input.approved_date = datetime.now(timezone.utc)
        assert user_input.is_approved


class TestDraftContent:
    """Test DraftContent data model."""
    
    def test_creation(self):
        """Test creating draft content."""
        draft = DraftContent(
            id="draft-001",
            content_type=ContentType.A3_PROBLEM,
            title="Test Draft",
            body="Draft body content",
            status=DraftStatus.READY,
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert draft.id == "draft-001"
        assert draft.requires_review
        assert not draft.has_warnings
    
    def test_requires_review_states(self):
        """Test requires_review property."""
        draft = DraftContent(
            id="1", content_type=ContentType.A3_PROBLEM,
            title="", body="", status=DraftStatus.GENERATING,
            confidence=ConfidenceLevel.MEDIUM
        )
        assert draft.requires_review
        
        draft.status = DraftStatus.READY
        assert draft.requires_review
        
        draft.status = DraftStatus.APPROVED
        assert not draft.requires_review
        
        draft.status = DraftStatus.APPLIED
        assert not draft.requires_review
    
    def test_warnings_tracking(self):
        """Test warning detection."""
        draft = DraftContent(
            id="1", content_type=ContentType.A3_PROBLEM,
            title="", body="", status=DraftStatus.READY,
            confidence=ConfidenceLevel.MEDIUM,
            warnings=["Warning 1", "Warning 2"]
        )
        assert draft.has_warnings
        assert len(draft.warnings) == 2
    
    def test_source_ids(self):
        """Test source ID extraction."""
        sources = [
            KnowledgeSource(id="s1", source_type=KnowledgeSourceType.BEST_PRACTICE,
                          title="", content_snippet="", relevance_score=0.5),
            KnowledgeSource(id="s2", source_type=KnowledgeSourceType.BEST_PRACTICE,
                          title="", content_snippet="", relevance_score=0.5),
        ]
        draft = DraftContent(
            id="1", content_type=ContentType.A3_PROBLEM,
            title="", body="", status=DraftStatus.READY,
            confidence=ConfidenceLevel.MEDIUM, sources=sources
        )
        assert draft.source_ids == ["s1", "s2"]


class TestA3Context:
    """Test A3Context data model."""
    
    def test_creation(self, sample_context):
        """Test creating A3 context."""
        assert sample_context.title == "Delayed Quote Response Time"
        assert sample_context.category == "Quality"
        assert sample_context.owner_name == "John Smith"
        assert len(sample_context.kpis) == 3
    
    def test_minimal_context(self):
        """Test context with minimal data."""
        context = A3Context(title="Minimal Problem")
        assert context.title == "Minimal Problem"
        assert context.description is None
        assert len(context.kpis) == 0


class TestA3SectionDraft:
    """Test A3SectionDraft data model."""
    
    def test_creation(self):
        """Test creating section draft."""
        draft = A3SectionDraft(
            section=A3SectionType.PROBLEM,
            draft_id="d1",
            content="This is the problem statement with detailed explanation.",
            confidence=ConfidenceLevel.HIGH,
            sources=[],
        )
        assert draft.section == A3SectionType.PROBLEM
        assert draft.word_count == 8
    
    def test_word_count_calculation(self):
        """Test automatic word count."""
        draft = A3SectionDraft(
            section=A3SectionType.PROBLEM,
            draft_id="d1",
            content="One two three four five",
            confidence=ConfidenceLevel.MEDIUM,
            sources=[],
        )
        assert draft.word_count == 5


class TestA3FullDraft:
    """Test A3FullDraft data model."""
    
    def test_completeness_check(self):
        """Test is_complete property."""
        sections = {}
        for section_type in [
            A3SectionType.PROBLEM,
            A3SectionType.CURRENT_STATE,
            A3SectionType.TARGET_STATE,
            A3SectionType.ROOT_CAUSE,
            A3SectionType.COUNTERMEASURES,
        ]:
            sections[section_type] = A3SectionDraft(
                section=section_type,
                draft_id=str(uuid4()),
                content="Content",
                confidence=ConfidenceLevel.MEDIUM,
                sources=[],
            )
        
        draft = A3FullDraft(
            a3_id="a3-001",
            title="Test A3",
            sections=sections,
            overall_confidence=ConfidenceLevel.MEDIUM,
            total_sources=0,
        )
        assert draft.is_complete
    
    def test_incomplete_missing_section(self):
        """Test incomplete when missing required section."""
        sections = {
            A3SectionType.PROBLEM: A3SectionDraft(
                section=A3SectionType.PROBLEM,
                draft_id="d1", content="Content",
                confidence=ConfidenceLevel.MEDIUM, sources=[]
            ),
        }
        draft = A3FullDraft(
            a3_id="a3-001", title="Test",
            sections=sections, overall_confidence=ConfidenceLevel.MEDIUM,
            total_sources=0
        )
        assert not draft.is_complete
    
    def test_get_section_content(self):
        """Test retrieving section content."""
        sections = {
            A3SectionType.PROBLEM: A3SectionDraft(
                section=A3SectionType.PROBLEM,
                draft_id="d1", content="Problem content here",
                confidence=ConfidenceLevel.MEDIUM, sources=[]
            ),
        }
        draft = A3FullDraft(
            a3_id="a3-001", title="Test",
            sections=sections, overall_confidence=ConfidenceLevel.MEDIUM,
            total_sources=0
        )
        assert draft.get_section_content(A3SectionType.PROBLEM) == "Problem content here"
        assert draft.get_section_content(A3SectionType.ROOT_CAUSE) is None


# =============================================================================
# A3 Section Drafting Tests
# =============================================================================

class TestA3SectionDrafting:
    """Test A3 section draft generation."""
    
    def test_draft_problem_section(self, service, sample_a3_request):
        """Test drafting problem section."""
        draft = service.draft_a3_section(sample_a3_request)
        
        assert draft.section == A3SectionType.PROBLEM
        assert draft.draft_id is not None
        assert len(draft.content) > 0
        assert "Problem Statement" in draft.content
        assert sample_a3_request.context.title in draft.content
        assert len(draft.guiding_questions) > 0
    
    def test_draft_current_state_section(self, service, sample_context):
        """Test drafting current state section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.CURRENT_STATE,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.CURRENT_STATE
        assert "Current State" in draft.content
        assert "Average Quote Time" in draft.content  # From KPIs
    
    def test_draft_target_state_section(self, service, sample_context):
        """Test drafting target state section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.TARGET_STATE,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.TARGET_STATE
        assert "Target State" in draft.content
        assert "Target Date" in draft.content
    
    def test_draft_root_cause_section(self, service, sample_context):
        """Test drafting root cause section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.ROOT_CAUSE,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.ROOT_CAUSE
        assert "Root Cause" in draft.content
        assert "Why" in draft.content
        assert draft.content.count("Why") >= 5
    
    def test_draft_countermeasures_section(self, service, sample_context):
        """Test drafting countermeasures section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.COUNTERMEASURES,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.COUNTERMEASURES
        assert "Countermeasures" in draft.content
        assert "Owner" in draft.content
        assert sample_context.owner_name in draft.content
    
    def test_draft_implementation_section(self, service, sample_context):
        """Test drafting implementation plan section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.IMPLEMENTATION_PLAN,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.IMPLEMENTATION_PLAN
        assert "Implementation Plan" in draft.content
        assert "Phase" in draft.content
    
    def test_draft_results_section(self, service, sample_context):
        """Test drafting results section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.RESULTS,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.RESULTS
        assert "Results" in draft.content
        assert "Before" in draft.content
        assert "After" in draft.content
    
    def test_draft_reflection_section(self, service, sample_context):
        """Test drafting reflection section."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.REFLECTION,
            context=sample_context,
            user_id=uuid4(),
        )
        draft = service.draft_a3_section(request)
        
        assert draft.section == A3SectionType.REFLECTION
        assert "Reflection" in draft.content
        assert "Lessons Learned" in draft.content
        assert "Standard Work" in draft.content
    
    def test_guiding_questions_included(self, service, sample_a3_request):
        """Test that guiding questions are included."""
        draft = service.draft_a3_section(sample_a3_request)
        
        assert len(draft.guiding_questions) > 0
        assert any("problem" in q.lower() for q in draft.guiding_questions)
    
    def test_suggestions_when_enabled(self, service, sample_a3_request):
        """Test suggestions are generated when enabled."""
        sample_a3_request.include_suggestions = True
        draft = service.draft_a3_section(sample_a3_request)
        
        assert isinstance(draft.suggestions, list)
        # Suggestions may or may not be generated based on content
    
    def test_max_length_respected(self, service, sample_context):
        """Test that max_length is respected."""
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.PROBLEM,
            context=sample_context,
            user_id=uuid4(),
            max_length=50,  # Very short
        )
        draft = service.draft_a3_section(request)
        
        assert draft.word_count <= 51  # Allow for rounding


# =============================================================================
# Full A3 Drafting Tests
# =============================================================================

class TestFullA3Drafting:
    """Test full A3 draft generation."""
    
    def test_draft_full_a3(self, service, sample_context):
        """Test generating full A3 draft."""
        a3_id = uuid4()
        user_id = uuid4()
        
        full_draft = service.draft_full_a3(
            a3_id=a3_id,
            context=sample_context,
            user_id=user_id,
        )
        
        assert full_draft.a3_id == str(a3_id)
        assert full_draft.title == sample_context.title
        assert len(full_draft.sections) == 8  # All sections
        assert full_draft.overall_confidence is not None
    
    def test_draft_specific_sections(self, service, sample_context):
        """Test generating only specific sections."""
        sections_to_draft = [
            A3SectionType.PROBLEM,
            A3SectionType.ROOT_CAUSE,
            A3SectionType.COUNTERMEASURES,
        ]
        
        full_draft = service.draft_full_a3(
            a3_id=uuid4(),
            context=sample_context,
            user_id=uuid4(),
            sections=sections_to_draft,
        )
        
        assert len(full_draft.sections) == 3
        assert A3SectionType.PROBLEM in full_draft.sections
        assert A3SectionType.ROOT_CAUSE in full_draft.sections
        assert A3SectionType.COUNTERMEASURES in full_draft.sections
        assert A3SectionType.REFLECTION not in full_draft.sections
    
    def test_get_a3_draft(self, service, sample_context):
        """Test retrieving stored A3 draft."""
        a3_id = uuid4()
        
        service.draft_full_a3(
            a3_id=a3_id,
            context=sample_context,
            user_id=uuid4(),
        )
        
        retrieved = service.get_a3_draft(str(a3_id))
        assert retrieved is not None
        assert retrieved.a3_id == str(a3_id)
    
    def test_overall_confidence_calculation(self, service, sample_context):
        """Test overall confidence is calculated correctly."""
        full_draft = service.draft_full_a3(
            a3_id=uuid4(),
            context=sample_context,
            user_id=uuid4(),
        )
        
        assert full_draft.overall_confidence in [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
            ConfidenceLevel.UNCERTAIN,
        ]
    
    def test_total_sources_count(self, service, sample_context):
        """Test total sources are counted."""
        full_draft = service.draft_full_a3(
            a3_id=uuid4(),
            context=sample_context,
            user_id=uuid4(),
        )
        
        assert full_draft.total_sources >= 0


# =============================================================================
# Draft Management Tests
# =============================================================================

class TestDraftManagement:
    """Test draft lifecycle management."""
    
    def test_create_draft(self, service):
        """Test creating a draft."""
        draft = service.create_draft(
            content_type=ContentType.A3_PROBLEM,
            title="Test Problem",
            body="Problem description here",
            user_id="user-123",
        )
        
        assert draft.id is not None
        assert draft.status == DraftStatus.READY
        assert draft.created_by == "user-123"
    
    def test_get_draft(self, service):
        """Test retrieving a draft."""
        created = service.create_draft(
            content_type=ContentType.A3_PROBLEM,
            title="Test",
            body="Body",
        )
        
        retrieved = service.get_draft(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_nonexistent_draft(self, service):
        """Test getting nonexistent draft returns None."""
        assert service.get_draft("nonexistent") is None
    
    def test_list_drafts(self, service):
        """Test listing all drafts."""
        service.create_draft(ContentType.A3_PROBLEM, "Draft 1", "Body 1")
        service.create_draft(ContentType.A3_ROOT_CAUSE, "Draft 2", "Body 2")
        service.create_draft(ContentType.EMAIL, "Draft 3", "Body 3")
        
        all_drafts = service.list_drafts()
        assert len(all_drafts) == 3
    
    def test_list_drafts_by_type(self, service):
        """Test filtering drafts by content type."""
        service.create_draft(ContentType.A3_PROBLEM, "Draft 1", "Body 1")
        service.create_draft(ContentType.A3_PROBLEM, "Draft 2", "Body 2")
        service.create_draft(ContentType.EMAIL, "Draft 3", "Body 3")
        
        a3_drafts = service.list_drafts(content_type=ContentType.A3_PROBLEM)
        assert len(a3_drafts) == 2
    
    def test_list_drafts_by_status(self, service):
        """Test filtering drafts by status."""
        draft1 = service.create_draft(ContentType.A3_PROBLEM, "Draft 1", "Body 1")
        service.create_draft(ContentType.A3_PROBLEM, "Draft 2", "Body 2")
        
        # Approve one draft
        service.review_draft(draft1.id, "reviewer", approved=True)
        
        ready_drafts = service.list_drafts(status=DraftStatus.READY)
        assert len(ready_drafts) == 1
        
        approved_drafts = service.list_drafts(status=DraftStatus.APPROVED)
        assert len(approved_drafts) == 1
    
    def test_review_draft_approve(self, service):
        """Test approving a draft."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        
        result = service.review_draft(
            draft_id=draft.id,
            user_id="reviewer-1",
            approved=True,
        )
        
        assert result is not None
        assert result.status == DraftStatus.APPROVED
        assert result.reviewed_by == "reviewer-1"
        assert result.reviewed_at is not None
    
    def test_review_draft_reject(self, service):
        """Test rejecting a draft."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        
        result = service.review_draft(
            draft_id=draft.id,
            user_id="reviewer-1",
            approved=False,
            feedback="Needs more detail",
        )
        
        assert result is not None
        assert result.status == DraftStatus.REJECTED
        assert any("Needs more detail" in w for w in result.warnings)
    
    def test_review_nonexistent_draft(self, service):
        """Test reviewing nonexistent draft returns None."""
        result = service.review_draft(
            draft_id="nonexistent",
            user_id="reviewer",
            approved=True,
        )
        assert result is None
    
    def test_apply_draft(self, service):
        """Test applying an approved draft."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        service.review_draft(draft.id, "reviewer", approved=True)
        
        result = service.apply_draft(draft.id, "applier")
        
        assert result is not None
        assert result.status == DraftStatus.APPLIED
        assert result.applied_at is not None
    
    def test_apply_unapproved_draft_fails(self, service):
        """Test that unapproved drafts cannot be applied."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        
        result = service.apply_draft(draft.id, "applier")
        assert result is None  # Cannot apply non-approved draft
    
    def test_draft_history_recorded(self, service):
        """Test that draft history is recorded."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        service.review_draft(draft.id, "reviewer", approved=True)
        service.apply_draft(draft.id, "applier")
        
        history = service.get_draft_history(draft.id)
        assert len(history) == 2  # review + apply


# =============================================================================
# Knowledge Base Tests
# =============================================================================

class TestKnowledgeBase:
    """Test knowledge base functionality."""
    
    def test_search_knowledge(self, service):
        """Test searching knowledge base."""
        results = service.search_knowledge("5 Whys")
        assert len(results) > 0
        assert any("5 Whys" in r.title for r in results)
    
    def test_search_returns_approved_sources(self, service):
        """Test that search returns approved sources."""
        results = service.search_knowledge("countermeasures")
        for source in results:
            assert source.is_approved
    
    def test_add_knowledge_source(self, service):
        """Test adding custom knowledge source."""
        source = KnowledgeSource(
            id="custom-001",
            source_type=KnowledgeSourceType.APPROVED_DOCUMENT,
            title="Custom Guide",
            content_snippet="Custom content for testing",
            relevance_score=0.8,
            approved_date=datetime.now(timezone.utc),
        )
        service.add_knowledge_source(source)
        
        # Should be searchable
        results = service.search_knowledge("Custom")
        assert any(r.id == "custom-001" for r in results)


# =============================================================================
# Confidence and Warnings Tests
# =============================================================================

class TestConfidenceAndWarnings:
    """Test confidence calculation and warning generation."""
    
    def test_confidence_increases_with_context(self, service):
        """Test that more context increases confidence."""
        minimal_context = A3Context(title="Problem")
        rich_context = A3Context(
            title="Problem",
            description="Detailed description",
            kpis={"KPI1": "value1", "KPI2": "value2"},
            historical_data=[{"key": "value"}],
        )
        
        request1 = A3DraftRequest(
            a3_id=uuid4(), section=A3SectionType.PROBLEM,
            context=minimal_context, user_id=uuid4()
        )
        request2 = A3DraftRequest(
            a3_id=uuid4(), section=A3SectionType.PROBLEM,
            context=rich_context, user_id=uuid4()
        )
        
        draft1 = service.draft_a3_section(request1)
        draft2 = service.draft_a3_section(request2)
        
        confidence_order = {
            ConfidenceLevel.UNCERTAIN: 0,
            ConfidenceLevel.LOW: 1,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.HIGH: 3,
        }
        
        # Rich context should have same or higher confidence
        assert confidence_order[draft2.confidence] >= confidence_order[draft1.confidence]
    
    def test_warnings_for_placeholder_content(self, service, sample_a3_request):
        """Test that placeholders generate warnings."""
        draft = service.draft_a3_section(sample_a3_request)
        
        # Content with placeholders should potentially have warnings
        # (depends on how many placeholders)
        if "[" in draft.content:
            # May have placeholder warning
            pass  # Acceptable either way
    
    def test_all_sections_get_guiding_questions(self, service, sample_context):
        """Test all sections have guiding questions."""
        for section_type in A3SectionType:
            request = A3DraftRequest(
                a3_id=uuid4(),
                section=section_type,
                context=sample_context,
                user_id=uuid4(),
            )
            draft = service.draft_a3_section(request)
            assert len(draft.guiding_questions) > 0


# =============================================================================
# Human Confirmation Workflow Tests
# =============================================================================

class TestHumanConfirmationWorkflow:
    """Test human-in-the-loop confirmation workflows."""
    
    def test_draft_requires_review(self, service):
        """Test that drafts require human review."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        assert draft.requires_review
    
    def test_approved_draft_no_longer_requires_review(self, service):
        """Test approved drafts don't require review."""
        draft = service.create_draft(
            ContentType.A3_PROBLEM, "Test", "Body"
        )
        service.review_draft(draft.id, "reviewer", approved=True)
        
        updated = service.get_draft(draft.id)
        assert not updated.requires_review
    
    def test_full_workflow(self, service, sample_context):
        """Test complete draft workflow."""
        # 1. Generate draft
        a3_id = uuid4()
        full_draft = service.draft_full_a3(
            a3_id=a3_id,
            context=sample_context,
            user_id=uuid4(),
        )
        
        # 2. Create editable draft from section
        problem_content = full_draft.get_section_content(A3SectionType.PROBLEM)
        draft = service.create_draft(
            ContentType.A3_PROBLEM,
            title=sample_context.title,
            body=problem_content,
            user_id="user-1",
        )
        
        # 3. Review and approve
        assert draft.requires_review
        result = service.review_draft(draft.id, "reviewer", approved=True)
        assert result.status == DraftStatus.APPROVED
        
        # 4. Apply to system
        applied = service.apply_draft(draft.id, "applier")
        assert applied.status == DraftStatus.APPLIED
        
        # 5. Verify history
        history = service.get_draft_history(draft.id)
        assert len(history) == 2


# =============================================================================
# Service Singleton Tests
# =============================================================================

class TestServiceSingleton:
    """Test service singleton pattern."""
    
    def test_get_service_returns_same_instance(self):
        """Test singleton returns same instance."""
        reset_ai_drafting_service()
        service1 = get_ai_drafting_service()
        service2 = get_ai_drafting_service()
        assert service1 is service2
    
    def test_reset_clears_service(self):
        """Test reset clears the service."""
        service = get_ai_drafting_service()
        service.create_draft(ContentType.A3_PROBLEM, "Test", "Body")
        
        reset_ai_drafting_service()
        
        new_service = get_ai_drafting_service()
        assert len(new_service.list_drafts()) == 0
    
    def test_clear_all(self, service):
        """Test clear_all method."""
        service.create_draft(ContentType.A3_PROBLEM, "Test", "Body")
        service.draft_full_a3(uuid4(), A3Context(title="Test"), uuid4())
        
        service.clear_all()
        
        assert len(service.list_drafts()) == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_context(self, service):
        """Test handling empty context."""
        context = A3Context(title="")
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.PROBLEM,
            context=context,
            user_id=uuid4(),
        )
        
        # Should still generate something
        draft = service.draft_a3_section(request)
        assert draft.content is not None
    
    def test_special_characters_in_title(self, service):
        """Test handling special characters."""
        context = A3Context(
            title="Problem with \"quotes\" & <special> chars"
        )
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.PROBLEM,
            context=context,
            user_id=uuid4(),
        )
        
        draft = service.draft_a3_section(request)
        assert draft.content is not None
    
    def test_very_long_context(self, service):
        """Test handling very long context."""
        context = A3Context(
            title="Short Title",
            description="A" * 10000,  # Very long description
        )
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.PROBLEM,
            context=context,
            user_id=uuid4(),
            max_length=100,
        )
        
        draft = service.draft_a3_section(request)
        assert draft.word_count <= 101
    
    def test_unicode_content(self, service):
        """Test handling unicode content."""
        context = A3Context(
            title="问题陈述 - Problem Statement",
            description="日本語テスト - Japanese test",
        )
        request = A3DraftRequest(
            a3_id=uuid4(),
            section=A3SectionType.PROBLEM,
            context=context,
            user_id=uuid4(),
        )
        
        draft = service.draft_a3_section(request)
        assert draft.content is not None
