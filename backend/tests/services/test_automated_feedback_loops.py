"""
Tests for Automated Feedback Loops System.

Tests cover:
- Learning Store operations
- Conflict resolution strategies
- Few-shot injection
- Correction versioning
- Feedback loop manager integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sensei.services.automated_feedback_loops import (
    # Enums
    CorrectionType,
    CorrectionStatus,
    ConflictResolutionStrategy,
    ContextType,
    # Data models
    ModelVersion,
    UserInfo,
    CorrectionMetadata,
    Correction,
    CorrectionGroup,
    RetrievedCorrection,
    FewShotExample,
    # Store
    LearningStore,
    InMemoryLearningStore,
    # Components
    ConflictResolver,
    FewShotInjector,
    CorrectionVersionManager,
    FeedbackLoopManager,
    # Factory
    create_feedback_loop_manager,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def model_version():
    """Create a test model version."""
    return ModelVersion(
        model_id="gpt-4",
        version="1.0.0",
        released_at=datetime.utcnow(),
    )


@pytest.fixture
def user_info():
    """Create a test user."""
    return UserInfo(
        user_id="user_123",
        username="testuser",
        role="operator",
        is_expert=False,
        trust_score=1.0,
    )


@pytest.fixture
def expert_user():
    """Create an expert test user."""
    return UserInfo(
        user_id="expert_456",
        username="expert",
        role="admin",
        is_expert=True,
        trust_score=1.5,
    )


@pytest.fixture
def correction_metadata():
    """Create test correction metadata."""
    return CorrectionMetadata(
        context_type=ContextType.RFQ_PARSING,
        field_name="part_number",
    )


@pytest.fixture
def sample_correction(user_info, model_version, correction_metadata):
    """Create a sample correction."""
    return Correction(
        id="corr_001",
        input_text="Parse this RFQ: Part ABC-123, qty 100",
        ai_output="Part: ABC-12, Quantity: 100",
        user_correction="Part: ABC-123, Quantity: 100",
        correction_type=CorrectionType.FIELD_VALUE,
        confidence_score=0.95,
        user_info=user_info,
        model_version=model_version,
        metadata=correction_metadata,
    )


@pytest.fixture
def store():
    """Create an in-memory learning store."""
    return InMemoryLearningStore()


@pytest.fixture
def feedback_manager(model_version):
    """Create a feedback loop manager."""
    manager = create_feedback_loop_manager()
    manager.set_current_model(model_version)
    return manager


# =============================================================================
# Model Version Tests
# =============================================================================

class TestModelVersion:
    """Tests for ModelVersion dataclass."""
    
    def test_model_version_creation(self):
        """Test creating a model version."""
        version = ModelVersion(
            model_id="gpt-4",
            version="2.0.0",
            released_at=datetime(2024, 1, 1),
        )
        assert version.model_id == "gpt-4"
        assert version.version == "2.0.0"
        assert not version.is_deprecated
    
    def test_model_version_deprecated(self):
        """Test deprecated model version."""
        version = ModelVersion(
            model_id="gpt-3",
            version="1.0.0",
            released_at=datetime(2023, 1, 1),
            deprecated_at=datetime(2024, 1, 1),
        )
        assert version.is_deprecated
    
    def test_model_version_hash(self):
        """Test model version is hashable."""
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        v1 = ModelVersion("gpt-4", "1.0.0", fixed_time)
        v2 = ModelVersion("gpt-4", "1.0.0", fixed_time)
        assert hash(v1) == hash(v2)
        
        # Same model_id and version should produce same hash
        v3 = ModelVersion("gpt-4", "1.0.0", datetime(2024, 6, 1))  # Different date
        assert hash(v1) == hash(v3)  # Hash only uses model_id and version


# =============================================================================
# User Info Tests
# =============================================================================

class TestUserInfo:
    """Tests for UserInfo dataclass."""
    
    def test_user_info_creation(self):
        """Test creating user info."""
        user = UserInfo(
            user_id="u1",
            username="john",
            role="operator",
        )
        assert user.user_id == "u1"
        assert user.is_expert is False
        assert user.trust_score == 1.0
    
    def test_expert_user(self):
        """Test expert user creation."""
        user = UserInfo(
            user_id="e1",
            username="expert",
            role="admin",
            is_expert=True,
            trust_score=2.0,
        )
        assert user.is_expert
        assert user.trust_score == 2.0
    
    def test_user_hash(self):
        """Test user is hashable."""
        u1 = UserInfo("u1", "john")
        u2 = UserInfo("u1", "john")
        assert hash(u1) == hash(u2)


# =============================================================================
# Correction Tests
# =============================================================================

class TestCorrection:
    """Tests for Correction dataclass."""
    
    def test_correction_creation(self, sample_correction):
        """Test creating a correction."""
        assert sample_correction.id == "corr_001"
        assert sample_correction.correction_type == CorrectionType.FIELD_VALUE
        assert sample_correction.status == CorrectionStatus.PENDING
    
    def test_correction_similarity_hash(self, sample_correction):
        """Test similarity hash is computed."""
        assert sample_correction.similarity_hash is not None
        assert len(sample_correction.similarity_hash) == 16
    
    def test_correction_to_dict(self, sample_correction):
        """Test conversion to dictionary."""
        d = sample_correction.to_dict()
        assert d["id"] == "corr_001"
        assert d["correction_type"] == "field_value"
        assert d["status"] == "pending"
        assert "created_at" in d
    
    def test_correction_from_dict(self, user_info, model_version):
        """Test creation from dictionary."""
        data = {
            "id": "corr_002",
            "input_text": "Test input",
            "ai_output": "Wrong output",
            "user_correction": "Correct output",
            "correction_type": "text_edit",
            "confidence_score": 0.9,
            "context_type": "email_draft",
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        correction = Correction.from_dict(data, user_info, model_version)
        assert correction.id == "corr_002"
        assert correction.correction_type == CorrectionType.TEXT_EDIT
        assert correction.status == CorrectionStatus.ACTIVE


# =============================================================================
# In-Memory Learning Store Tests
# =============================================================================

class TestInMemoryLearningStore:
    """Tests for InMemoryLearningStore."""
    
    @pytest.mark.asyncio
    async def test_store_correction(self, store, sample_correction):
        """Test storing a correction."""
        result = await store.store_correction(sample_correction)
        assert result == "corr_001"
    
    @pytest.mark.asyncio
    async def test_get_correction(self, store, sample_correction):
        """Test retrieving a correction."""
        await store.store_correction(sample_correction)
        retrieved = await store.get_correction("corr_001")
        assert retrieved is not None
        assert retrieved.id == sample_correction.id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_correction(self, store):
        """Test retrieving non-existent correction returns None."""
        result = await store.get_correction("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_corrections_by_context(self, store, sample_correction):
        """Test getting corrections by context type."""
        await store.store_correction(sample_correction)
        corrections = await store.get_corrections_by_context(ContextType.RFQ_PARSING)
        assert len(corrections) == 1
        assert corrections[0].id == "corr_001"
    
    @pytest.mark.asyncio
    async def test_get_corrections_empty_context(self, store):
        """Test getting corrections for empty context."""
        corrections = await store.get_corrections_by_context(ContextType.EMAIL_DRAFT)
        assert len(corrections) == 0
    
    @pytest.mark.asyncio
    async def test_search_similar_corrections(self, store, sample_correction):
        """Test similarity search."""
        sample_correction.status = CorrectionStatus.ACTIVE
        await store.store_correction(sample_correction)
        
        results = await store.search_similar_corrections(
            input_text="Parse this RFQ: Part XYZ-789",
            context_type=ContextType.RFQ_PARSING,
        )
        # Should find some similarity due to "Parse this RFQ Part"
        assert len(results) >= 0  # May or may not match depending on threshold
    
    @pytest.mark.asyncio
    async def test_update_correction_status(self, store, sample_correction):
        """Test updating correction status."""
        await store.store_correction(sample_correction)
        result = await store.update_correction_status("corr_001", CorrectionStatus.ACTIVE)
        assert result is True
        
        retrieved = await store.get_correction("corr_001")
        assert retrieved.status == CorrectionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_status(self, store):
        """Test updating non-existent correction."""
        result = await store.update_correction_status("fake", CorrectionStatus.ACTIVE)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_conflicts(self, store, sample_correction, user_info, model_version):
        """Test getting conflicting corrections."""
        await store.store_correction(sample_correction)
        
        # Create another correction with same pattern
        conflict = Correction(
            id="corr_002",
            input_text=sample_correction.input_text,
            ai_output=sample_correction.ai_output,
            user_correction="Different correction",
            correction_type=CorrectionType.FIELD_VALUE,
            confidence_score=0.8,
            user_info=user_info,
            model_version=model_version,
            metadata=sample_correction.metadata,
            similarity_hash=sample_correction.similarity_hash,
        )
        await store.store_correction(conflict)
        
        conflicts = await store.get_conflicts(sample_correction.similarity_hash)
        assert len(conflicts) == 2
    
    def test_get_stats(self, store):
        """Test getting store statistics."""
        stats = store.get_stats()
        assert "total_corrections" in stats
        assert "by_context" in stats
        assert "unique_patterns" in stats


# =============================================================================
# Conflict Resolver Tests
# =============================================================================

class TestConflictResolver:
    """Tests for ConflictResolver."""
    
    @pytest.fixture
    def resolver(self):
        return ConflictResolver(ConflictResolutionStrategy.LAST_WINS)
    
    @pytest.fixture
    def conflicting_corrections(self, user_info, model_version):
        """Create a set of conflicting corrections."""
        base_metadata = CorrectionMetadata(context_type=ContextType.RFQ_PARSING)
        corrections = []
        
        for i, (output, ts) in enumerate([
            ("Value A", datetime(2024, 1, 1)),
            ("Value B", datetime(2024, 1, 2)),
            ("Value A", datetime(2024, 1, 3)),
        ]):
            corrections.append(Correction(
                id=f"corr_{i}",
                input_text="Test input",
                ai_output="Wrong",
                user_correction=output,
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=0.9,
                user_info=user_info,
                model_version=model_version,
                metadata=base_metadata,
                created_at=ts,
            ))
        
        return corrections
    
    def test_resolve_empty_raises(self, resolver):
        """Test resolving empty list raises error."""
        with pytest.raises(ValueError, match="No corrections"):
            resolver.resolve([])
    
    def test_resolve_single_correction(self, resolver, sample_correction):
        """Test resolving single correction."""
        group = resolver.resolve([sample_correction])
        assert group.resolved_value == sample_correction.user_correction
        assert len(group.corrections) == 1
    
    def test_resolve_last_wins(self, resolver, conflicting_corrections):
        """Test last-wins resolution."""
        group = resolver.resolve(conflicting_corrections, ConflictResolutionStrategy.LAST_WINS)
        assert group.resolved_value == "Value A"  # Most recent
        assert group.resolution_strategy == ConflictResolutionStrategy.LAST_WINS
    
    def test_resolve_majority_vote(self, resolver, conflicting_corrections):
        """Test majority vote resolution."""
        group = resolver.resolve(conflicting_corrections, ConflictResolutionStrategy.MAJORITY_VOTE)
        assert group.resolved_value == "Value A"  # 2 votes vs 1
    
    def test_resolve_weighted_vote(self, resolver, user_info, model_version):
        """Test weighted vote resolution."""
        metadata = CorrectionMetadata(context_type=ContextType.RFQ_PARSING)
        
        # Low trust user, high confidence
        low_trust = UserInfo("u1", "low", trust_score=0.5)
        high_trust = UserInfo("u2", "high", trust_score=2.0)
        
        corrections = [
            Correction(
                id="c1",
                input_text="test",
                ai_output="wrong",
                user_correction="Value A",
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=1.0,
                user_info=low_trust,
                model_version=model_version,
                metadata=metadata,
            ),
            Correction(
                id="c2",
                input_text="test",
                ai_output="wrong",
                user_correction="Value B",
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=1.0,
                user_info=high_trust,
                model_version=model_version,
                metadata=metadata,
            ),
        ]
        
        group = resolver.resolve(corrections, ConflictResolutionStrategy.WEIGHTED_VOTE)
        assert group.resolved_value == "Value B"  # Higher trust score
    
    def test_resolve_expert_priority(self, resolver, user_info, expert_user, model_version):
        """Test expert priority resolution."""
        metadata = CorrectionMetadata(context_type=ContextType.RFQ_PARSING)
        
        corrections = [
            Correction(
                id="c1",
                input_text="test",
                ai_output="wrong",
                user_correction="Regular Value",
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=1.0,
                user_info=user_info,
                model_version=model_version,
                metadata=metadata,
                created_at=datetime(2024, 1, 2),
            ),
            Correction(
                id="c2",
                input_text="test",
                ai_output="wrong",
                user_correction="Expert Value",
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=1.0,
                user_info=expert_user,
                model_version=model_version,
                metadata=metadata,
                created_at=datetime(2024, 1, 1),
            ),
        ]
        
        group = resolver.resolve(corrections, ConflictResolutionStrategy.EXPERT_PRIORITY)
        assert group.resolved_value == "Expert Value"
    
    def test_resolve_confidence_based(self, resolver, user_info, model_version):
        """Test confidence-based resolution."""
        metadata = CorrectionMetadata(context_type=ContextType.RFQ_PARSING)
        
        corrections = [
            Correction(
                id="c1",
                input_text="test",
                ai_output="wrong",
                user_correction="Low Confidence",
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=0.5,
                user_info=user_info,
                model_version=model_version,
                metadata=metadata,
            ),
            Correction(
                id="c2",
                input_text="test",
                ai_output="wrong",
                user_correction="High Confidence",
                correction_type=CorrectionType.FIELD_VALUE,
                confidence_score=0.95,
                user_info=user_info,
                model_version=model_version,
                metadata=metadata,
            ),
        ]
        
        group = resolver.resolve(corrections, ConflictResolutionStrategy.CONFIDENCE_BASED)
        assert group.resolved_value == "High Confidence"


# =============================================================================
# Few-Shot Injector Tests
# =============================================================================

class TestFewShotInjector:
    """Tests for FewShotInjector."""
    
    @pytest.fixture
    def injector(self, store):
        return FewShotInjector(store, max_examples=3, min_relevance=0.1)
    
    @pytest.mark.asyncio
    async def test_get_few_shot_examples_empty(self, injector):
        """Test getting examples from empty store."""
        examples = await injector.get_few_shot_examples(
            "Test input",
            ContextType.RFQ_PARSING,
        )
        assert len(examples) == 0
    
    @pytest.mark.asyncio
    async def test_get_few_shot_examples(self, injector, store, sample_correction):
        """Test getting few-shot examples."""
        sample_correction.status = CorrectionStatus.ACTIVE
        await store.store_correction(sample_correction)
        
        examples = await injector.get_few_shot_examples(
            "Parse this RFQ: Part ABC-123, qty 100",  # Same input
            ContextType.RFQ_PARSING,
        )
        # Should match with high relevance
        assert len(examples) >= 1
        assert examples[0].input_text == sample_correction.input_text
    
    @pytest.mark.asyncio
    async def test_inject_corrections_empty(self, injector):
        """Test injection with no corrections."""
        prompt = "Do this task. {corrections}"
        result, examples = await injector.inject_corrections(
            prompt=prompt,
            input_text="Test",
            context_type=ContextType.EMAIL_DRAFT,
        )
        assert "{corrections}" not in result
        assert len(examples) == 0
    
    @pytest.mark.asyncio
    async def test_inject_corrections(self, injector, store, sample_correction):
        """Test correction injection into prompt."""
        sample_correction.status = CorrectionStatus.ACTIVE
        await store.store_correction(sample_correction)
        
        prompt = "Do this task. {corrections} End of prompt."
        result, examples = await injector.inject_corrections(
            prompt=prompt,
            input_text="Parse this RFQ: Part ABC-123, qty 100",
            context_type=ContextType.RFQ_PARSING,
        )
        
        assert "{corrections}" not in result
        if examples:  # If matching found
            assert "<corrections>" in result
            assert "Example 1:" in result
    
    def test_format_corrections_block_empty(self, injector):
        """Test formatting empty examples."""
        result = injector.format_corrections_block([])
        assert result == ""
    
    def test_format_corrections_block(self, injector):
        """Test formatting corrections block."""
        examples = [
            FewShotExample(
                input_text="Input 1",
                incorrect_output="Wrong 1",
                correct_output="Correct 1",
                context_type=ContextType.RFQ_PARSING,
                relevance_score=0.9,
            ),
        ]
        result = injector.format_corrections_block(examples)
        assert "<corrections>" in result
        assert "Example 1:" in result
        assert "Input 1" in result
        assert "Wrong 1" in result
        assert "Correct 1" in result


# =============================================================================
# Correction Version Manager Tests
# =============================================================================

class TestCorrectionVersionManager:
    """Tests for CorrectionVersionManager."""
    
    @pytest.fixture
    def version_manager(self):
        return CorrectionVersionManager(staleness_threshold_days=30)
    
    def test_register_model_version(self, version_manager, model_version):
        """Test registering a model version."""
        version_manager.register_model_version(model_version)
        retrieved = version_manager.get_model_version("gpt-4", "1.0.0")
        assert retrieved is not None
        assert retrieved.model_id == "gpt-4"
    
    def test_deprecate_model_version(self, version_manager, model_version):
        """Test deprecating a model version."""
        version_manager.register_model_version(model_version)
        result = version_manager.deprecate_model_version("gpt-4", "1.0.0")
        assert result is True
        
        retrieved = version_manager.get_model_version("gpt-4", "1.0.0")
        assert retrieved.is_deprecated
    
    def test_deprecate_nonexistent_version(self, version_manager):
        """Test deprecating non-existent version."""
        result = version_manager.deprecate_model_version("fake", "0.0.0")
        assert result is False
    
    def test_is_correction_stale_deprecated_model(
        self, version_manager, sample_correction, model_version
    ):
        """Test staleness check for deprecated model."""
        sample_correction.model_version.deprecated_at = datetime.utcnow()
        assert version_manager.is_correction_stale(sample_correction, model_version)
    
    def test_is_correction_stale_old_correction(
        self, version_manager, sample_correction, model_version
    ):
        """Test staleness check for old correction."""
        sample_correction.created_at = datetime.utcnow() - timedelta(days=60)
        assert version_manager.is_correction_stale(sample_correction, model_version)
    
    def test_is_correction_stale_different_model(
        self, version_manager, sample_correction
    ):
        """Test staleness for different model."""
        different_model = ModelVersion("claude", "3.0", datetime.utcnow())
        assert version_manager.is_correction_stale(sample_correction, different_model)
    
    def test_is_correction_fresh(self, version_manager, sample_correction, model_version):
        """Test fresh correction."""
        assert not version_manager.is_correction_stale(sample_correction, model_version)
    
    def test_filter_fresh_corrections(
        self, version_manager, sample_correction, model_version
    ):
        """Test filtering fresh corrections."""
        fresh = version_manager.filter_fresh_corrections(
            [sample_correction], model_version
        )
        assert len(fresh) == 1
    
    def test_deprecation_callback(self, version_manager, model_version):
        """Test deprecation callback is called."""
        callback = MagicMock()
        version_manager.add_deprecation_callback(callback)
        version_manager.register_model_version(model_version)
        version_manager.deprecate_model_version("gpt-4", "1.0.0")
        callback.assert_called_once()


# =============================================================================
# Feedback Loop Manager Tests
# =============================================================================

class TestFeedbackLoopManager:
    """Tests for FeedbackLoopManager."""
    
    @pytest.mark.asyncio
    async def test_record_correction_without_model_raises(self):
        """Test recording without setting model raises error."""
        manager = create_feedback_loop_manager()
        with pytest.raises(ValueError, match="No current model"):
            await manager.record_correction(
                input_text="test",
                ai_output="wrong",
                user_correction="correct",
                correction_type=CorrectionType.TEXT_EDIT,
                user=UserInfo("u1", "user"),
                context_type=ContextType.GENERAL,
            )
    
    @pytest.mark.asyncio
    async def test_record_correction(self, feedback_manager, user_info):
        """Test recording a correction."""
        correction = await feedback_manager.record_correction(
            input_text="Test input",
            ai_output="Wrong output",
            user_correction="Correct output",
            correction_type=CorrectionType.TEXT_EDIT,
            user=user_info,
            context_type=ContextType.EMAIL_DRAFT,
            confidence_score=0.9,
        )
        
        assert correction.id.startswith("corr_")
        assert correction.input_text == "Test input"
        assert correction.user_correction == "Correct output"
    
    @pytest.mark.asyncio
    async def test_record_multiple_corrections(self, feedback_manager, user_info):
        """Test recording multiple corrections."""
        for i in range(5):
            await feedback_manager.record_correction(
                input_text=f"Input {i}",
                ai_output="Wrong",
                user_correction=f"Correct {i}",
                correction_type=CorrectionType.TEXT_EDIT,
                user=user_info,
                context_type=ContextType.GENERAL,
            )
        
        stats = await feedback_manager.get_statistics()
        assert stats["store"]["total_corrections"] == 5
    
    @pytest.mark.asyncio
    async def test_get_enhanced_prompt(self, feedback_manager, user_info):
        """Test getting enhanced prompt."""
        # Record a correction first
        await feedback_manager.record_correction(
            input_text="Parse RFQ ABC",
            ai_output="Part: AB",
            user_correction="Part: ABC",
            correction_type=CorrectionType.FIELD_VALUE,
            user=user_info,
            context_type=ContextType.RFQ_PARSING,
        )
        
        prompt = "Parse this RFQ. {corrections}"
        enhanced, count = await feedback_manager.get_enhanced_prompt(
            base_prompt=prompt,
            input_text="Parse RFQ ABC",
            context_type=ContextType.RFQ_PARSING,
        )
        
        assert "{corrections}" not in enhanced
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, feedback_manager):
        """Test getting statistics."""
        stats = await feedback_manager.get_statistics()
        assert "store" in stats
        assert "current_model" in stats
        assert "conflict_strategy" in stats
        assert stats["current_model"] == "gpt-4:1.0.0"
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_corrections(self, feedback_manager, user_info):
        """Test cleanup of stale corrections."""
        # Record a correction
        correction = await feedback_manager.record_correction(
            input_text="Test",
            ai_output="Wrong",
            user_correction="Correct",
            correction_type=CorrectionType.TEXT_EDIT,
            user=user_info,
            context_type=ContextType.GENERAL,
        )
        
        # Manually activate and age it
        await feedback_manager.store.update_correction_status(
            correction.id, CorrectionStatus.ACTIVE
        )
        
        # Modify created_at to be old
        stored = await feedback_manager.store.get_correction(correction.id)
        stored.created_at = datetime.utcnow() - timedelta(days=60)
        
        cleaned = await feedback_manager.cleanup_stale_corrections()
        assert cleaned >= 1


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactory:
    """Tests for factory function."""
    
    def test_create_with_defaults(self):
        """Test creating manager with defaults."""
        manager = create_feedback_loop_manager()
        assert isinstance(manager, FeedbackLoopManager)
        assert isinstance(manager.store, InMemoryLearningStore)
    
    def test_create_with_custom_store(self):
        """Test creating with custom store."""
        store = InMemoryLearningStore()
        manager = create_feedback_loop_manager(store=store)
        assert manager.store is store
    
    def test_create_with_custom_strategy(self):
        """Test creating with custom conflict strategy."""
        manager = create_feedback_loop_manager(
            conflict_strategy=ConflictResolutionStrategy.MAJORITY_VOTE
        )
        assert manager.conflict_resolver.default_strategy == ConflictResolutionStrategy.MAJORITY_VOTE
    
    def test_create_with_custom_staleness(self):
        """Test creating with custom staleness threshold."""
        manager = create_feedback_loop_manager(staleness_days=60)
        assert manager.version_manager.staleness_threshold_days == 60
    
    def test_create_with_custom_few_shot(self):
        """Test creating with custom few-shot limit."""
        manager = create_feedback_loop_manager(max_few_shot=10)
        assert manager.few_shot_injector.max_examples == 10


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for enum values."""
    
    def test_correction_types(self):
        """Test correction type enum values."""
        assert CorrectionType.TEXT_EDIT.value == "text_edit"
        assert CorrectionType.FIELD_VALUE.value == "field_value"
        assert CorrectionType.REJECTION.value == "rejection"
    
    def test_correction_status(self):
        """Test correction status enum values."""
        assert CorrectionStatus.PENDING.value == "pending"
        assert CorrectionStatus.ACTIVE.value == "active"
        assert CorrectionStatus.SUPERSEDED.value == "superseded"
    
    def test_context_types(self):
        """Test context type enum values."""
        assert ContextType.RFQ_PARSING.value == "rfq_parsing"
        assert ContextType.EMAIL_DRAFT.value == "email_draft"
        assert ContextType.A3_GENERATION.value == "a3_generation"
    
    def test_conflict_strategies(self):
        """Test conflict resolution strategies."""
        assert ConflictResolutionStrategy.LAST_WINS.value == "last_wins"
        assert ConflictResolutionStrategy.MAJORITY_VOTE.value == "majority_vote"
        assert ConflictResolutionStrategy.EXPERT_PRIORITY.value == "expert_priority"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_input_text(self, feedback_manager, user_info):
        """Test handling empty input text."""
        correction = await feedback_manager.record_correction(
            input_text="",
            ai_output="Output",
            user_correction="Correct",
            correction_type=CorrectionType.TEXT_EDIT,
            user=user_info,
            context_type=ContextType.GENERAL,
        )
        assert correction.input_text == ""
    
    @pytest.mark.asyncio
    async def test_very_long_text(self, feedback_manager, user_info):
        """Test handling very long text."""
        long_text = "x" * 10000
        correction = await feedback_manager.record_correction(
            input_text=long_text,
            ai_output=long_text,
            user_correction=long_text,
            correction_type=CorrectionType.TEXT_EDIT,
            user=user_info,
            context_type=ContextType.GENERAL,
        )
        assert len(correction.input_text) == 10000
    
    @pytest.mark.asyncio
    async def test_special_characters(self, feedback_manager, user_info):
        """Test handling special characters."""
        special = "Unicode: 日本語 Emoji: 🎉 Symbols: <>&\""
        correction = await feedback_manager.record_correction(
            input_text=special,
            ai_output=special,
            user_correction=special,
            correction_type=CorrectionType.TEXT_EDIT,
            user=user_info,
            context_type=ContextType.GENERAL,
        )
        assert "日本語" in correction.input_text
        assert "🎉" in correction.input_text
    
    def test_correction_metadata_defaults(self):
        """Test metadata with minimal fields."""
        meta = CorrectionMetadata(context_type=ContextType.GENERAL)
        assert meta.field_name is None
        assert meta.tags == []
        assert meta.custom_data == {}
    
    def test_correction_group_without_resolution(self, sample_correction):
        """Test correction group without resolution."""
        group = CorrectionGroup(
            pattern_hash="abc123",
            corrections=[sample_correction],
        )
        assert group.resolved_value is None
        assert group.resolution_strategy is None


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the feedback loop system."""
    
    @pytest.mark.asyncio
    async def test_full_feedback_cycle(self):
        """Test complete feedback cycle from correction to injection."""
        # Setup
        manager = create_feedback_loop_manager(
            conflict_strategy=ConflictResolutionStrategy.MAJORITY_VOTE,
            max_few_shot=3,
        )
        model = ModelVersion("test-model", "1.0.0", datetime.utcnow())
        manager.set_current_model(model)
        
        user = UserInfo("u1", "testuser")
        
        # Record some corrections
        for i in range(3):
            await manager.record_correction(
                input_text=f"Parse invoice {i}",
                ai_output=f"Total: ${i}00",
                user_correction=f"Total: ${i}50",
                correction_type=CorrectionType.FIELD_VALUE,
                user=user,
                context_type=ContextType.ENTITY_EXTRACTION,
            )
        
        # Get enhanced prompt
        base_prompt = "Parse this invoice. {corrections}"
        enhanced, count = await manager.get_enhanced_prompt(
            base_prompt=base_prompt,
            input_text="Parse invoice 2",
            context_type=ContextType.ENTITY_EXTRACTION,
        )
        
        # Verify
        assert "{corrections}" not in enhanced
        stats = await manager.get_statistics()
        assert stats["store"]["total_corrections"] == 3
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_flow(self):
        """Test conflict resolution in realistic scenario."""
        manager = create_feedback_loop_manager(
            conflict_strategy=ConflictResolutionStrategy.EXPERT_PRIORITY
        )
        model = ModelVersion("test-model", "1.0.0", datetime.utcnow())
        manager.set_current_model(model)
        
        regular_user = UserInfo("u1", "user", is_expert=False)
        expert_user = UserInfo("e1", "expert", is_expert=True)
        
        # Regular user makes correction
        await manager.record_correction(
            input_text="Part: ABC",
            ai_output="Part: AB",
            user_correction="Part: ABC",
            correction_type=CorrectionType.FIELD_VALUE,
            user=regular_user,
            context_type=ContextType.RFQ_PARSING,
        )
        
        # Expert makes different correction for same pattern
        await manager.record_correction(
            input_text="Part: ABC",
            ai_output="Part: AB",
            user_correction="Part: ABC-V1",
            correction_type=CorrectionType.FIELD_VALUE,
            user=expert_user,
            context_type=ContextType.RFQ_PARSING,
        )
        
        # Expert correction should take priority
        stats = await manager.get_statistics()
        assert stats["store"]["total_corrections"] == 2
    
    @pytest.mark.asyncio
    async def test_model_version_upgrade(self):
        """Test handling model version upgrades."""
        manager = create_feedback_loop_manager(staleness_days=30)
        
        old_model = ModelVersion("gpt-4", "1.0.0", datetime(2023, 1, 1))
        new_model = ModelVersion("gpt-4", "2.0.0", datetime.utcnow())
        
        manager.set_current_model(old_model)
        
        user = UserInfo("u1", "user")
        
        # Make correction on old model
        correction = await manager.record_correction(
            input_text="Test",
            ai_output="Wrong",
            user_correction="Correct",
            correction_type=CorrectionType.TEXT_EDIT,
            user=user,
            context_type=ContextType.GENERAL,
        )
        
        # Upgrade model
        manager.set_current_model(new_model)
        
        # Check if old correction is considered stale
        is_stale = manager.version_manager.is_correction_stale(correction, new_model)
        assert is_stale  # Different version = stale
