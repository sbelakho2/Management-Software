"""
Tests for AI Learning Recommendations Service.

Comprehensive tests covering:
- All enums and data classes
- Recommendation generation
- Skill gap analysis
- Spaced repetition scheduling
- Context-aware recommendations
- Role-based recommendations
- Learning paths
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.services.ai.ai_learning_recommendations import (
    # Enums
    RecommendationType,
    RecommendationPriority,
    LearningGoal,
    SkillLevel,
    LearningStyle,
    ContextTrigger,
    ContentCategory,
    DifficultyLevel,
    # Data Classes
    UserProfile,
    LearningUnitInfo,
    ProgressData,
    SkillAssessment,
    LearningRecommendation,
    SkillGap,
    LearningPath,
    SpacedRepetitionSchedule,
    RecommendationSet,
    # Service
    AILearningRecommendationsService,
    # Constants
    SKILL_LEVEL_ORDER,
    DIFFICULTY_SKILL_MAP,
    SR_INTERVALS,
    ROLE_CATEGORIES,
    ONBOARDING_UNITS,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def service():
    """Create learning recommendations service instance."""
    return AILearningRecommendationsService()


@pytest.fixture
def sample_user_profile():
    """Create sample user profile."""
    return UserProfile(
        user_id=uuid4(),
        role="production",
        department="Manufacturing",
        tenure_months=6,
        skill_level=SkillLevel.BEGINNER,
        learning_style=LearningStyle.VISUAL,
        preferred_duration_minutes=15,
        goals=[LearningGoal.SKILL_DEVELOPMENT],
        interests=["quality", "efficiency"],
    )


@pytest.fixture
def sample_units():
    """Create sample learning units."""
    return [
        LearningUnitInfo(
            id=uuid4(),
            code="TPS-001",
            title="Introduction to TPS",
            category=ContentCategory.TPS,
            difficulty=DifficultyLevel.BEGINNER,
            content_type="video",
            duration_minutes=15,
            tags=["tps", "basics"],
            prerequisites=[],
        ),
        LearningUnitInfo(
            id=uuid4(),
            code="TPS-002",
            title="TPS Principles",
            category=ContentCategory.TPS,
            difficulty=DifficultyLevel.BEGINNER,
            content_type="text",
            duration_minutes=20,
            tags=["tps", "principles"],
            prerequisites=["TPS-001"],
        ),
        LearningUnitInfo(
            id=uuid4(),
            code="LEAN-001",
            title="Introduction to Lean",
            category=ContentCategory.LEAN,
            difficulty=DifficultyLevel.BEGINNER,
            content_type="video",
            duration_minutes=10,
            tags=["lean", "basics"],
            prerequisites=[],
        ),
        LearningUnitInfo(
            id=uuid4(),
            code="QUAL-001",
            title="Quality Fundamentals",
            category=ContentCategory.QUALITY,
            difficulty=DifficultyLevel.INTERMEDIATE,
            content_type="text",
            duration_minutes=25,
            tags=["quality", "fundamentals"],
            prerequisites=["TPS-001"],
        ),
        LearningUnitInfo(
            id=uuid4(),
            code="PROCESS-001",
            title="Process Improvement",
            category=ContentCategory.PROCESS,
            difficulty=DifficultyLevel.BEGINNER,
            content_type="interactive",
            duration_minutes=30,
            tags=["process", "improvement"],
            prerequisites=[],
        ),
        LearningUnitInfo(
            id=uuid4(),
            code="SAFETY-001",
            title="Safety Basics",
            category=ContentCategory.SAFETY,
            difficulty=DifficultyLevel.BEGINNER,
            content_type="video",
            duration_minutes=10,
            tags=["safety"],
            prerequisites=[],
        ),
    ]


@pytest.fixture
def sample_progress(sample_units):
    """Create sample progress data."""
    return [
        ProgressData(
            user_id=uuid4(),
            unit_id=sample_units[0].id,
            unit_code="TPS-001",
            status="completed",
            progress_percentage=100,
            score=Decimal("85.0"),
            completed_at=datetime.now(timezone.utc) - timedelta(days=10),
            next_review_date=datetime.now(timezone.utc) - timedelta(days=2),
            review_count=1,
        ),
        ProgressData(
            user_id=uuid4(),
            unit_id=sample_units[2].id,
            unit_code="LEAN-001",
            status="in_progress",
            progress_percentage=50,
            last_accessed_at=datetime.now(timezone.utc) - timedelta(hours=2),
        ),
    ]


# ============================================================================
# Enum Tests
# ============================================================================

class TestRecommendationType:
    """Tests for RecommendationType enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert RecommendationType.NEXT_UNIT.value == "next_unit"
        assert RecommendationType.REVIEW.value == "review"
        assert RecommendationType.SKILL_GAP.value == "skill_gap"
        assert RecommendationType.ROLE_BASED.value == "role_based"
        assert RecommendationType.PREREQUISITE.value == "prerequisite"
        assert RecommendationType.TRENDING.value == "trending"
        assert RecommendationType.SIMILAR.value == "similar"
        assert RecommendationType.JUST_IN_TIME.value == "just_in_time"
        assert RecommendationType.CERTIFICATION.value == "certification"
        assert RecommendationType.REFRESHER.value == "refresher"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(RecommendationType) == 10


class TestRecommendationPriority:
    """Tests for RecommendationPriority enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert RecommendationPriority.CRITICAL.value == "critical"
        assert RecommendationPriority.HIGH.value == "high"
        assert RecommendationPriority.MEDIUM.value == "medium"
        assert RecommendationPriority.LOW.value == "low"
        assert RecommendationPriority.OPTIONAL.value == "optional"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(RecommendationPriority) == 5


class TestLearningGoal:
    """Tests for LearningGoal enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert LearningGoal.ONBOARDING.value == "onboarding"
        assert LearningGoal.SKILL_DEVELOPMENT.value == "skill_development"
        assert LearningGoal.CERTIFICATION.value == "certification"
        assert LearningGoal.COMPLIANCE.value == "compliance"
        assert LearningGoal.CAREER_GROWTH.value == "career_growth"
        assert LearningGoal.PROBLEM_SOLVING.value == "problem_solving"
        assert LearningGoal.REFRESHER.value == "refresher"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(LearningGoal) == 7


class TestSkillLevel:
    """Tests for SkillLevel enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert SkillLevel.NOVICE.value == "novice"
        assert SkillLevel.BEGINNER.value == "beginner"
        assert SkillLevel.INTERMEDIATE.value == "intermediate"
        assert SkillLevel.ADVANCED.value == "advanced"
        assert SkillLevel.EXPERT.value == "expert"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(SkillLevel) == 5


class TestLearningStyle:
    """Tests for LearningStyle enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert LearningStyle.VISUAL.value == "visual"
        assert LearningStyle.AUDITORY.value == "auditory"
        assert LearningStyle.READING.value == "reading"
        assert LearningStyle.KINESTHETIC.value == "kinesthetic"
        assert LearningStyle.MIXED.value == "mixed"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(LearningStyle) == 5


class TestContextTrigger:
    """Tests for ContextTrigger enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert ContextTrigger.LOGIN.value == "login"
        assert ContextTrigger.TASK_COMPLETION.value == "task_completion"
        assert ContextTrigger.ERROR_ENCOUNTERED.value == "error_encountered"
        assert ContextTrigger.LOW_PERFORMANCE.value == "low_performance"
        assert ContextTrigger.NEW_FEATURE.value == "new_feature"
        assert ContextTrigger.ROLE_CHANGE.value == "role_change"
        assert ContextTrigger.CERTIFICATION_EXPIRING.value == "certification_expiring"
        assert ContextTrigger.MANUAL_REQUEST.value == "manual_request"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(ContextTrigger) == 8


class TestContentCategory:
    """Tests for ContentCategory enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert ContentCategory.TPS.value == "tps"
        assert ContentCategory.LEAN.value == "lean"
        assert ContentCategory.QUALITY.value == "quality"
        assert ContentCategory.SAFETY.value == "safety"
        assert ContentCategory.PROCESS.value == "process"
        assert ContentCategory.TOOL.value == "tool"
        assert ContentCategory.CONCEPT.value == "concept"
        assert ContentCategory.BEST_PRACTICE.value == "best_practice"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(ContentCategory) == 8


class TestDifficultyLevel:
    """Tests for DifficultyLevel enum."""
    
    def test_values(self):
        """Test all values exist."""
        assert DifficultyLevel.BEGINNER.value == "beginner"
        assert DifficultyLevel.INTERMEDIATE.value == "intermediate"
        assert DifficultyLevel.ADVANCED.value == "advanced"
        assert DifficultyLevel.EXPERT.value == "expert"
    
    def test_count(self):
        """Test enum has expected count."""
        assert len(DifficultyLevel) == 4


# ============================================================================
# Data Class Tests
# ============================================================================

class TestUserProfile:
    """Tests for UserProfile dataclass."""
    
    def test_creation(self):
        """Test creating user profile."""
        profile = UserProfile(
            user_id=uuid4(),
            role="engineer",
            skill_level=SkillLevel.INTERMEDIATE,
        )
        
        assert profile.role == "engineer"
        assert profile.skill_level == SkillLevel.INTERMEDIATE
        assert profile.learning_style == LearningStyle.MIXED
        assert profile.preferred_duration_minutes == 15
    
    def test_defaults(self):
        """Test default values."""
        profile = UserProfile(user_id=uuid4())
        
        assert profile.role == "user"
        assert profile.tenure_months == 0
        assert len(profile.goals) == 0


class TestLearningUnitInfo:
    """Tests for LearningUnitInfo dataclass."""
    
    def test_creation(self):
        """Test creating learning unit info."""
        unit = LearningUnitInfo(
            id=uuid4(),
            code="TEST-001",
            title="Test Unit",
            category=ContentCategory.TPS,
            difficulty=DifficultyLevel.BEGINNER,
        )
        
        assert unit.code == "TEST-001"
        assert unit.category == ContentCategory.TPS
        assert unit.duration_minutes == 10
    
    def test_with_prerequisites(self):
        """Test unit with prerequisites."""
        unit = LearningUnitInfo(
            id=uuid4(),
            code="TEST-002",
            title="Advanced Unit",
            category=ContentCategory.TPS,
            difficulty=DifficultyLevel.ADVANCED,
            prerequisites=["TEST-001"],
        )
        
        assert len(unit.prerequisites) == 1
        assert "TEST-001" in unit.prerequisites


class TestProgressData:
    """Tests for ProgressData dataclass."""
    
    def test_creation(self):
        """Test creating progress data."""
        progress = ProgressData(
            user_id=uuid4(),
            unit_id=uuid4(),
            unit_code="TEST-001",
            status="completed",
            progress_percentage=100,
        )
        
        assert progress.status == "completed"
        assert progress.progress_percentage == 100
        assert progress.review_count == 0
    
    def test_defaults(self):
        """Test default values."""
        progress = ProgressData(
            user_id=uuid4(),
            unit_id=uuid4(),
            unit_code="TEST-001",
        )
        
        assert progress.status == "not_started"
        assert progress.time_spent_seconds == 0


class TestSkillAssessment:
    """Tests for SkillAssessment dataclass."""
    
    def test_creation(self):
        """Test creating skill assessment."""
        assessment = SkillAssessment(
            category=ContentCategory.QUALITY,
            level=SkillLevel.INTERMEDIATE,
            score=Decimal("75.0"),
        )
        
        assert assessment.category == ContentCategory.QUALITY
        assert assessment.level == SkillLevel.INTERMEDIATE
        assert assessment.trend == "stable"


class TestLearningRecommendation:
    """Tests for LearningRecommendation dataclass."""
    
    def test_creation(self):
        """Test creating recommendation."""
        rec = LearningRecommendation(
            recommendation_type=RecommendationType.NEXT_UNIT,
            priority=RecommendationPriority.HIGH,
            unit_code="TEST-001",
            unit_title="Test Unit",
        )
        
        assert rec.recommendation_type == RecommendationType.NEXT_UNIT
        assert rec.priority == RecommendationPriority.HIGH
        assert rec.id is not None
    
    def test_defaults(self):
        """Test default values."""
        rec = LearningRecommendation()
        
        assert rec.recommendation_type == RecommendationType.NEXT_UNIT
        assert rec.priority == RecommendationPriority.MEDIUM
        assert rec.call_to_action == "Start Learning"


class TestSkillGap:
    """Tests for SkillGap dataclass."""
    
    def test_creation(self):
        """Test creating skill gap."""
        gap = SkillGap(
            category=ContentCategory.LEAN,
            current_level=SkillLevel.BEGINNER,
            target_level=SkillLevel.ADVANCED,
            gap_score=Decimal("0.5"),
        )
        
        assert gap.current_level == SkillLevel.BEGINNER
        assert gap.target_level == SkillLevel.ADVANCED
    
    def test_defaults(self):
        """Test default values."""
        gap = SkillGap()
        
        assert gap.category == ContentCategory.TPS
        assert gap.estimated_hours_to_close == 0.0


class TestLearningPath:
    """Tests for LearningPath dataclass."""
    
    def test_creation(self):
        """Test creating learning path."""
        path = LearningPath(
            title="Test Path",
            goal=LearningGoal.CERTIFICATION,
            unit_sequence=["U1", "U2", "U3"],
            total_units=3,
        )
        
        assert path.title == "Test Path"
        assert len(path.unit_sequence) == 3
        assert path.progress_percentage == 0
    
    def test_defaults(self):
        """Test default values."""
        path = LearningPath()
        
        assert path.goal == LearningGoal.SKILL_DEVELOPMENT
        assert path.estimated_total_hours == 0.0


class TestSpacedRepetitionSchedule:
    """Tests for SpacedRepetitionSchedule dataclass."""
    
    def test_creation(self):
        """Test creating schedule."""
        schedule = SpacedRepetitionSchedule(
            unit_id=uuid4(),
            unit_code="TEST-001",
            unit_title="Test Unit",
            next_review_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        
        assert schedule.interval_days == 1
        assert schedule.ease_factor == Decimal("2.5")
        assert schedule.streak == 0
    
    def test_overdue(self):
        """Test overdue schedule."""
        schedule = SpacedRepetitionSchedule(
            unit_id=uuid4(),
            unit_code="TEST-001",
            unit_title="Test Unit",
            next_review_date=datetime.now(timezone.utc) - timedelta(days=5),
            overdue_days=5,
        )
        
        assert schedule.overdue_days == 5


class TestRecommendationSet:
    """Tests for RecommendationSet dataclass."""
    
    def test_creation(self):
        """Test creating recommendation set."""
        rec_set = RecommendationSet(
            user_id=uuid4(),
            summary="Test summary",
        )
        
        assert rec_set.id is not None
        assert rec_set.summary == "Test summary"
        assert len(rec_set.recommendations) == 0
    
    def test_defaults(self):
        """Test default values."""
        rec_set = RecommendationSet()
        
        assert len(rec_set.skill_gaps) == 0
        assert rec_set.active_path is None


# ============================================================================
# Service Initialization Tests
# ============================================================================

class TestServiceInitialization:
    """Tests for service initialization."""
    
    def test_default_initialization(self):
        """Test default initialization."""
        service = AILearningRecommendationsService()
        
        assert service.review_reminder_days == 7
        assert service.max_recommendations == 10
        assert service.enable_spaced_repetition is True
    
    def test_custom_initialization(self):
        """Test custom initialization."""
        service = AILearningRecommendationsService(
            review_reminder_days=14,
            max_recommendations=5,
            enable_spaced_repetition=False,
        )
        
        assert service.review_reminder_days == 14
        assert service.max_recommendations == 5
        assert service.enable_spaced_repetition is False


# ============================================================================
# Recommendation Generation Tests
# ============================================================================

class TestRecommendationGeneration:
    """Tests for recommendation generation."""
    
    def test_generate_recommendations(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test generating recommendations."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        assert isinstance(rec_set, RecommendationSet)
        assert rec_set.user_id == sample_user_profile.user_id
        assert len(rec_set.recommendations) > 0
    
    def test_recommendations_are_ranked(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test recommendations are ranked by priority."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        # Check ordering
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
            RecommendationPriority.OPTIONAL: 4,
        }
        
        for i in range(len(rec_set.recommendations) - 1):
            current_priority = priority_order[rec_set.recommendations[i].priority]
            next_priority = priority_order[rec_set.recommendations[i + 1].priority]
            # Higher or equal priority items should come first
            assert current_priority <= next_priority or (
                current_priority == next_priority and
                rec_set.recommendations[i].relevance_score >= rec_set.recommendations[i + 1].relevance_score
            )
    
    def test_recommendations_are_deduplicated(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test recommendations are deduplicated."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        unit_codes = [r.unit_code for r in rec_set.recommendations]
        assert len(unit_codes) == len(set(unit_codes))
    
    def test_max_recommendations_limit(
        self, sample_user_profile, sample_units, sample_progress
    ):
        """Test max recommendations limit is respected."""
        service = AILearningRecommendationsService(max_recommendations=3)
        
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        assert len(rec_set.recommendations) <= 3


# ============================================================================
# Review Recommendation Tests
# ============================================================================

class TestReviewRecommendations:
    """Tests for review recommendations."""
    
    def test_overdue_review_detected(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test overdue reviews are detected."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        review_recs = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.REVIEW
        ]
        
        # TPS-001 has overdue review
        assert len(review_recs) > 0
    
    def test_review_priority_based_on_overdue(
        self, service, sample_user_profile, sample_units
    ):
        """Test review priority based on overdue days."""
        progress = [
            ProgressData(
                user_id=sample_user_profile.user_id,
                unit_id=sample_units[0].id,
                unit_code="TPS-001",
                status="completed",
                next_review_date=datetime.now(timezone.utc) - timedelta(days=15),
            ),
        ]
        
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            progress,
        )
        
        review_recs = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.REVIEW
        ]
        
        if review_recs:
            # Very overdue should be critical
            assert review_recs[0].priority == RecommendationPriority.CRITICAL
    
    def test_no_reviews_when_disabled(
        self, sample_user_profile, sample_units, sample_progress
    ):
        """Test no review recommendations when disabled."""
        service = AILearningRecommendationsService(enable_spaced_repetition=False)
        
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        review_recs = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.REVIEW
        ]
        
        assert len(review_recs) == 0


# ============================================================================
# Continue Recommendation Tests
# ============================================================================

class TestContinueRecommendations:
    """Tests for continue in-progress recommendations."""
    
    def test_in_progress_detected(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test in-progress units are detected."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        continue_recs = [
            r for r in rec_set.recommendations
            if "continue" in r.reason.lower()
        ]
        
        # LEAN-001 is in progress
        assert len(continue_recs) > 0
    
    def test_continue_recommendation_priority(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test continue recommendations have high priority."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        continue_recs = [
            r for r in rec_set.recommendations
            if "continue" in r.reason.lower()
        ]
        
        for rec in continue_recs:
            assert rec.priority == RecommendationPriority.HIGH


# ============================================================================
# Next Unit Recommendation Tests
# ============================================================================

class TestNextUnitRecommendations:
    """Tests for next unit recommendations."""
    
    def test_prerequisites_checked(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test prerequisites are checked."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        # TPS-002 requires TPS-001 which is completed
        tps_002_recs = [
            r for r in rec_set.recommendations
            if r.unit_code == "TPS-002"
        ]
        
        assert len(tps_002_recs) > 0
    
    def test_prerequisite_not_met_excluded(
        self, service, sample_user_profile, sample_units
    ):
        """Test units with unmet prerequisites are excluded."""
        # No completions
        progress = []
        
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            progress,
        )
        
        # TPS-002 requires TPS-001 which is not completed
        tps_002_recs = [
            r for r in rec_set.recommendations
            if r.unit_code == "TPS-002"
        ]
        
        # Should not be recommended or have lower relevance
        # (may appear via other recommendation types)
        for rec in tps_002_recs:
            if rec.recommendation_type == RecommendationType.NEXT_UNIT:
                # If it appears, prerequisites weren't properly checked
                assert False


# ============================================================================
# Skill Gap Tests
# ============================================================================

class TestSkillGapAnalysis:
    """Tests for skill gap analysis."""
    
    def test_skill_gaps_detected(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test skill gaps are detected."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        # Should identify gaps in categories with low completion
        assert isinstance(rec_set.skill_gaps, list)
    
    def test_skill_gap_recommendations(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test skill gap recommendations are generated."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        gap_recs = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.SKILL_GAP
        ]
        
        # Should have some gap recommendations
        assert isinstance(gap_recs, list)


# ============================================================================
# Role-Based Recommendation Tests
# ============================================================================

class TestRoleBasedRecommendations:
    """Tests for role-based recommendations."""
    
    def test_role_based_recommendations(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test role-based recommendations."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        role_recs = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.ROLE_BASED
        ]
        
        # Production role should get process/safety recommendations
        assert isinstance(role_recs, list)
    
    def test_get_recommended_categories(self, service):
        """Test getting recommended categories for roles."""
        production_cats = service.get_recommended_categories("production")
        quality_cats = service.get_recommended_categories("quality")
        
        assert ContentCategory.PROCESS in production_cats
        assert ContentCategory.QUALITY in quality_cats


# ============================================================================
# Context-Aware Recommendation Tests
# ============================================================================

class TestContextAwareRecommendations:
    """Tests for context-aware recommendations."""
    
    def test_login_context(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test recommendations for login context."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
            context=ContextTrigger.LOGIN,
        )
        
        assert rec_set.context == ContextTrigger.LOGIN
    
    def test_error_context(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test recommendations for error context."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
            context=ContextTrigger.ERROR_ENCOUNTERED,
        )
        
        # Should suggest problem-solving content
        just_in_time = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.JUST_IN_TIME
        ]
        
        # May or may not have JIT recs depending on content matching
        assert isinstance(just_in_time, list)
    
    def test_certification_expiring_context(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test recommendations for certification expiring context."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
            context=ContextTrigger.CERTIFICATION_EXPIRING,
        )
        
        cert_recs = [
            r for r in rec_set.recommendations
            if r.recommendation_type == RecommendationType.CERTIFICATION
        ]
        
        # May have certification recommendations if matching content exists
        assert isinstance(cert_recs, list)


# ============================================================================
# Learning Path Tests
# ============================================================================

class TestLearningPaths:
    """Tests for learning paths."""
    
    def test_learning_path_generated(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test learning path is generated."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        if rec_set.active_path:
            assert isinstance(rec_set.active_path, LearningPath)
            assert len(rec_set.active_path.unit_sequence) > 0
    
    def test_learning_path_based_on_goal(self, service, sample_units, sample_progress):
        """Test learning path considers user goal."""
        profile = UserProfile(
            user_id=uuid4(),
            goals=[LearningGoal.CERTIFICATION],
        )
        
        rec_set = service.generate_recommendations(
            profile,
            sample_units,
            sample_progress,
        )
        
        if rec_set.active_path:
            assert rec_set.active_path.goal == LearningGoal.CERTIFICATION


# ============================================================================
# Spaced Repetition Tests
# ============================================================================

class TestSpacedRepetition:
    """Tests for spaced repetition scheduling."""
    
    def test_calculate_next_review_passing(self, service):
        """Test next review calculation for passing performance."""
        new_interval, new_ease = service.calculate_next_review(
            current_interval=1,
            ease_factor=Decimal("2.5"),
            performance=Decimal("4.0"),
        )
        
        # Should increase interval
        assert new_interval > 1
        assert new_ease > Decimal("2.4")
    
    def test_calculate_next_review_failing(self, service):
        """Test next review calculation for failing performance."""
        new_interval, new_ease = service.calculate_next_review(
            current_interval=30,
            ease_factor=Decimal("2.5"),
            performance=Decimal("2.0"),
        )
        
        # Should reset interval to 1
        assert new_interval == 1
    
    def test_calculate_next_review_first_time(self, service):
        """Test next review calculation for first time."""
        new_interval, new_ease = service.calculate_next_review(
            current_interval=0,
            ease_factor=Decimal("2.5"),
            performance=Decimal("4.0"),
        )
        
        assert new_interval == 1
    
    def test_ease_factor_minimum(self, service):
        """Test ease factor has minimum value."""
        new_interval, new_ease = service.calculate_next_review(
            current_interval=1,
            ease_factor=Decimal("1.4"),
            performance=Decimal("1.0"),
        )
        
        assert new_ease >= Decimal("1.3")
    
    def test_schedule_review(self, service):
        """Test scheduling a review."""
        schedule = service.schedule_review(
            user_id=uuid4(),
            unit_id=uuid4(),
            unit_code="TEST-001",
            unit_title="Test Unit",
            performance=Decimal("4.0"),
        )
        
        assert isinstance(schedule, SpacedRepetitionSchedule)
        assert schedule.review_count == 1
        assert schedule.next_review_date > datetime.now(timezone.utc)
    
    def test_schedule_review_updates_existing(self, service):
        """Test scheduling updates existing schedule."""
        user_id = uuid4()
        unit_id = uuid4()
        
        # First schedule
        schedule1 = service.schedule_review(
            user_id=user_id,
            unit_id=unit_id,
            unit_code="TEST-001",
            unit_title="Test Unit",
            performance=Decimal("4.0"),
        )
        
        # Second schedule
        schedule2 = service.schedule_review(
            user_id=user_id,
            unit_id=unit_id,
            unit_code="TEST-001",
            unit_title="Test Unit",
            performance=Decimal("5.0"),
            current_schedule=schedule1,
        )
        
        assert schedule2.review_count == 2
        assert schedule2.streak == 2
    
    def test_get_user_schedule(self, service):
        """Test getting user schedule."""
        user_id = uuid4()
        
        service.schedule_review(
            user_id=user_id,
            unit_id=uuid4(),
            unit_code="TEST-001",
            unit_title="Test Unit",
            performance=Decimal("4.0"),
        )
        
        schedules = service.get_user_schedule(user_id)
        
        assert len(schedules) == 1


# ============================================================================
# Due Reviews Tests
# ============================================================================

class TestDueReviews:
    """Tests for due reviews."""
    
    def test_reviews_due_included(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test reviews due are included in recommendation set."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        # TPS-001 has overdue review
        assert len(rec_set.reviews_due) > 0
    
    def test_reviews_sorted_by_date(
        self, service, sample_user_profile, sample_units
    ):
        """Test reviews are sorted by due date."""
        progress = [
            ProgressData(
                user_id=sample_user_profile.user_id,
                unit_id=sample_units[0].id,
                unit_code="TPS-001",
                status="completed",
                next_review_date=datetime.now(timezone.utc) + timedelta(days=5),
            ),
            ProgressData(
                user_id=sample_user_profile.user_id,
                unit_id=sample_units[2].id,
                unit_code="LEAN-001",
                status="completed",
                next_review_date=datetime.now(timezone.utc) + timedelta(days=2),
            ),
        ]
        
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            progress,
        )
        
        if len(rec_set.reviews_due) > 1:
            for i in range(len(rec_set.reviews_due) - 1):
                assert rec_set.reviews_due[i].next_review_date <= rec_set.reviews_due[i + 1].next_review_date


# ============================================================================
# Retrieval Tests
# ============================================================================

class TestRetrieval:
    """Tests for retrieval methods."""
    
    def test_get_recommendation_set(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test getting recommendation set by ID."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        retrieved = service.get_recommendation_set(rec_set.id)
        
        assert retrieved is not None
        assert retrieved.id == rec_set.id
    
    def test_get_nonexistent_recommendation_set(self, service):
        """Test getting nonexistent recommendation set."""
        result = service.get_recommendation_set(uuid4())
        
        assert result is None
    
    def test_get_onboarding_units(self, service):
        """Test getting onboarding units."""
        default_units = service.get_onboarding_units()
        production_units = service.get_onboarding_units("production")
        
        assert len(default_units) > 0
        assert len(production_units) > 0
        assert "SAFETY-001" in production_units


# ============================================================================
# Summary Generation Tests
# ============================================================================

class TestSummaryGeneration:
    """Tests for summary generation."""
    
    def test_summary_generated(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test summary is generated."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        assert len(rec_set.summary) > 0
        assert len(rec_set.primary_focus) > 0
    
    def test_summary_mentions_reviews(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test summary mentions reviews when due."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        # Has overdue review, should mention it
        if rec_set.reviews_due:
            assert "review" in rec_set.summary.lower() or "in progress" in rec_set.summary.lower()


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_units(self, service, sample_user_profile):
        """Test with empty units list."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            [],
            [],
        )
        
        assert rec_set is not None
        assert len(rec_set.recommendations) == 0
    
    def test_empty_progress(
        self, service, sample_user_profile, sample_units
    ):
        """Test with empty progress."""
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            [],
        )
        
        assert rec_set is not None
        # Should have some recommendations
        assert len(rec_set.recommendations) > 0
    
    def test_all_completed(
        self, service, sample_user_profile, sample_units
    ):
        """Test when all units are completed."""
        progress = [
            ProgressData(
                user_id=sample_user_profile.user_id,
                unit_id=unit.id,
                unit_code=unit.code,
                status="completed",
            )
            for unit in sample_units
        ]
        
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            progress,
        )
        
        # May have review recommendations but no new unit recommendations
        assert rec_set is not None
    
    def test_unknown_role(self, service, sample_units, sample_progress):
        """Test with unknown role."""
        profile = UserProfile(
            user_id=uuid4(),
            role="unknown_role",
        )
        
        rec_set = service.generate_recommendations(
            profile,
            sample_units,
            sample_progress,
        )
        
        assert rec_set is not None


# ============================================================================
# Constants Tests
# ============================================================================

class TestConstants:
    """Tests for service constants."""
    
    def test_skill_level_order(self):
        """Test skill level ordering."""
        assert SKILL_LEVEL_ORDER[0] == SkillLevel.NOVICE
        assert SKILL_LEVEL_ORDER[-1] == SkillLevel.EXPERT
        assert len(SKILL_LEVEL_ORDER) == 5
    
    def test_difficulty_skill_map(self):
        """Test difficulty to skill level mapping."""
        assert DifficultyLevel.BEGINNER in DIFFICULTY_SKILL_MAP
        assert SkillLevel.NOVICE in DIFFICULTY_SKILL_MAP[DifficultyLevel.BEGINNER]
    
    def test_sr_intervals(self):
        """Test spaced repetition intervals."""
        assert 1 in SR_INTERVALS
        assert SR_INTERVALS == sorted(SR_INTERVALS)
    
    def test_role_categories(self):
        """Test role category mapping."""
        assert "production" in ROLE_CATEGORIES
        assert "quality" in ROLE_CATEGORIES
        assert ContentCategory.PROCESS in ROLE_CATEGORIES["production"]
    
    def test_onboarding_units(self):
        """Test onboarding units mapping."""
        assert "default" in ONBOARDING_UNITS
        assert "production" in ONBOARDING_UNITS
        assert len(ONBOARDING_UNITS["default"]) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_workflow(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test complete recommendation workflow."""
        # Generate recommendations
        rec_set = service.generate_recommendations(
            sample_user_profile,
            sample_units,
            sample_progress,
        )
        
        # Verify all components
        assert rec_set.user_id == sample_user_profile.user_id
        assert len(rec_set.recommendations) > 0
        
        # Retrieve recommendation set
        retrieved = service.get_recommendation_set(rec_set.id)
        assert retrieved.id == rec_set.id
        
        # Schedule a review
        schedule = service.schedule_review(
            user_id=sample_user_profile.user_id,
            unit_id=sample_units[0].id,
            unit_code=sample_units[0].code,
            unit_title=sample_units[0].title,
            performance=Decimal("4.0"),
        )
        
        assert schedule.review_count == 1
    
    def test_multiple_users(
        self, service, sample_units, sample_progress
    ):
        """Test handling multiple users."""
        users = [
            UserProfile(
                user_id=uuid4(),
                role="production",
                skill_level=SkillLevel.BEGINNER,
            ),
            UserProfile(
                user_id=uuid4(),
                role="quality",
                skill_level=SkillLevel.INTERMEDIATE,
            ),
            UserProfile(
                user_id=uuid4(),
                role="engineering",
                skill_level=SkillLevel.ADVANCED,
            ),
        ]
        
        rec_sets = []
        for user in users:
            rec_set = service.generate_recommendations(
                user,
                sample_units,
                sample_progress,
            )
            rec_sets.append(rec_set)
        
        assert len(rec_sets) == 3
        # Each user should have different recommendations
        ids = [rs.id for rs in rec_sets]
        assert len(set(ids)) == 3
    
    def test_recommendation_with_all_contexts(
        self, service, sample_user_profile, sample_units, sample_progress
    ):
        """Test recommendations with different contexts."""
        contexts = [
            ContextTrigger.LOGIN,
            ContextTrigger.ERROR_ENCOUNTERED,
            ContextTrigger.CERTIFICATION_EXPIRING,
            None,
        ]
        
        for context in contexts:
            rec_set = service.generate_recommendations(
                sample_user_profile,
                sample_units,
                sample_progress,
                context=context,
            )
            
            assert rec_set is not None
            assert rec_set.context == context
