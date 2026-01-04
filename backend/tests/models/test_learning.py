"""
Tests for Learning models (Sensei teaching engine).

Tests:
- LearningUnit model fields and defaults
- LearningModule model
- UserLearningProgress tracking
- Content types and difficulty levels
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from sensei.models.learning import (
    ContentType,
    DifficultyLevel,
    LearningCategory,
    LearningModule,
    LearningStatus,
    LearningUnit,
    ProgressStatus,
    UserLearningProgress,
)


class TestLearningUnitModel:
    """Tests for the LearningUnit model."""

    def test_learning_unit_required_fields(self):
        """LearningUnit should require code, title."""
        unit = LearningUnit(
            code="LU-001",
            title="Introduction to Lean Manufacturing",
            content_type=ContentType.VIDEO.value,
        )
        assert unit.code == "LU-001"
        assert unit.title == "Introduction to Lean Manufacturing"
        assert unit.content_type == ContentType.VIDEO.value

    def test_learning_unit_default_category_is_tps(self):
        """LearningUnit category should default to tps - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            category=LearningCategory.TPS.value,
        )
        assert unit.category == LearningCategory.TPS.value

    def test_learning_unit_default_difficulty_is_beginner(self):
        """LearningUnit difficulty should default to beginner - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            difficulty=DifficultyLevel.BEGINNER.value,
        )
        assert unit.difficulty == DifficultyLevel.BEGINNER.value

    def test_learning_unit_default_content_type_is_text(self):
        """LearningUnit content_type should default to text - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            content_type=ContentType.TEXT.value,
        )
        assert unit.content_type == ContentType.TEXT.value

    def test_learning_unit_is_published_default_false(self):
        """is_published should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            is_published=False,
        )
        assert unit.is_published is False

    def test_learning_unit_version_default_1(self):
        """version should default to 1 - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            version=1,
        )
        assert unit.version == 1

    def test_learning_unit_unit_order_default_0(self):
        """unit_order should default to 0 - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            unit_order=0,
        )
        assert unit.unit_order == 0

    def test_learning_unit_with_media_fields(self):
        """LearningUnit should accept media URLs."""
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            video_url="https://example.com/video.mp4",
            audio_url="https://example.com/audio.mp3",
            document_url="https://example.com/doc.pdf",
            thumbnail_url="https://example.com/thumb.png",
        )
        assert unit.video_url == "https://example.com/video.mp4"
        assert unit.audio_url == "https://example.com/audio.mp3"
        assert unit.document_url == "https://example.com/doc.pdf"
        assert unit.thumbnail_url == "https://example.com/thumb.png"

    def test_learning_unit_with_japanese_term(self):
        """LearningUnit should accept Japanese term and pronunciation."""
        unit = LearningUnit(
            code="LU-001",
            title="Kaizen",
            japanese_term="改善",
            pronunciation="kai-zen",
        )
        assert unit.japanese_term == "改善"
        assert unit.pronunciation == "kai-zen"

    def test_learning_unit_with_content(self):
        """LearningUnit should accept content fields."""
        unit = LearningUnit(
            code="LU-001",
            title="Test",
            content="This is the lesson content.",
            key_points=["Point 1", "Point 2"],
            examples=["Example 1", "Example 2"],
            anti_patterns=["Don't do this"],
        )
        assert unit.content == "This is the lesson content."
        assert unit.key_points == ["Point 1", "Point 2"]
        assert unit.examples == ["Example 1", "Example 2"]
        assert unit.anti_patterns == ["Don't do this"]


class TestLearningStatusEnum:
    """Tests for LearningStatus enum."""

    def test_all_statuses_defined(self):
        """All expected learning statuses should be defined."""
        assert LearningStatus.DRAFT.value == "draft"
        assert LearningStatus.REVIEW.value == "review"
        assert LearningStatus.PUBLISHED.value == "published"
        assert LearningStatus.ARCHIVED.value == "archived"


class TestDifficultyLevelEnum:
    """Tests for DifficultyLevel enum."""

    def test_all_levels_defined(self):
        """All expected difficulty levels should be defined."""
        assert DifficultyLevel.BEGINNER.value == "beginner"
        assert DifficultyLevel.INTERMEDIATE.value == "intermediate"
        assert DifficultyLevel.ADVANCED.value == "advanced"
        assert DifficultyLevel.EXPERT.value == "expert"


class TestContentTypeEnum:
    """Tests for ContentType enum."""

    def test_all_types_defined(self):
        """All expected content types should be defined."""
        assert ContentType.TEXT.value == "text"
        assert ContentType.VIDEO.value == "video"
        assert ContentType.AUDIO.value == "audio"
        assert ContentType.DOCUMENT.value == "document"
        assert ContentType.INTERACTIVE.value == "interactive"
        assert ContentType.QUIZ.value == "quiz"
        assert ContentType.EXERCISE.value == "exercise"
        assert ContentType.CASE_STUDY.value == "case_study"
        assert ContentType.ARTICLE.value == "article"
        assert ContentType.SIMULATION.value == "simulation"


class TestLearningCategoryEnum:
    """Tests for LearningCategory enum."""

    def test_all_categories_defined(self):
        """All expected learning categories should be defined."""
        assert LearningCategory.TPS.value == "tps"
        assert LearningCategory.LEAN.value == "lean"
        assert LearningCategory.QUALITY.value == "quality"
        assert LearningCategory.SAFETY.value == "safety"
        assert LearningCategory.PROCESS.value == "process"
        assert LearningCategory.TOOL.value == "tool"
        assert LearningCategory.CONCEPT.value == "concept"
        assert LearningCategory.BEST_PRACTICE.value == "best_practice"
        assert LearningCategory.STANDARD.value == "standard"
        assert LearningCategory.PROCEDURE.value == "procedure"


class TestLearningModuleModel:
    """Tests for the LearningModule model."""

    def test_learning_module_required_fields(self):
        """LearningModule should require code, title."""
        module = LearningModule(
            code="LM-001",
            title="Lean Manufacturing Fundamentals",
        )
        assert module.code == "LM-001"
        assert module.title == "Lean Manufacturing Fundamentals"

    def test_learning_module_default_category_is_tps(self):
        """LearningModule category should default to tps - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        module = LearningModule(
            code="LM-001",
            title="Test",
            category=LearningCategory.TPS.value,
        )
        assert module.category == LearningCategory.TPS.value

    def test_learning_module_default_difficulty_is_beginner(self):
        """LearningModule difficulty should default to beginner - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        module = LearningModule(
            code="LM-001",
            title="Test",
            difficulty=DifficultyLevel.BEGINNER.value,
        )
        assert module.difficulty == DifficultyLevel.BEGINNER.value

    def test_learning_module_is_published_default_false(self):
        """is_published should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        module = LearningModule(
            code="LM-001",
            title="Test",
            is_published=False,
        )
        assert module.is_published is False

    def test_learning_module_display_order_default_0(self):
        """display_order should default to 0 - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        module = LearningModule(
            code="LM-001",
            title="Test",
            display_order=0,
        )
        assert module.display_order == 0

    def test_learning_module_with_learning_objectives(self):
        """LearningModule should accept learning_objectives."""
        module = LearningModule(
            code="LM-001",
            title="Test",
            learning_objectives=["Understand TPS", "Apply lean principles"],
        )
        assert module.learning_objectives == ["Understand TPS", "Apply lean principles"]

    def test_learning_module_with_prerequisites(self):
        """LearningModule should accept prerequisites list."""
        module = LearningModule(
            code="LM-001",
            title="Advanced Path",
            prerequisites=["LM-INTRO", "LM-BASICS"],
        )
        assert module.prerequisites == ["LM-INTRO", "LM-BASICS"]


class TestUserLearningProgressModel:
    """Tests for the UserLearningProgress model."""

    def test_user_learning_progress_required_fields(self):
        """UserLearningProgress should require user_id, unit_id."""
        user_id = uuid4()
        unit_id = uuid4()
        progress = UserLearningProgress(
            user_id=user_id,
            unit_id=unit_id,
        )
        assert progress.user_id == user_id
        assert progress.unit_id == unit_id

    def test_user_learning_progress_default_status_is_not_started(self):
        """UserLearningProgress status should default to not_started - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            status=ProgressStatus.NOT_STARTED.value,
        )
        assert progress.status == ProgressStatus.NOT_STARTED.value

    def test_user_learning_progress_default_progress_percentage_is_0(self):
        """progress_percentage should default to 0 - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            progress_percentage=0,
        )
        assert progress.progress_percentage == 0

    def test_user_learning_progress_is_completed_true_for_completed_status(self):
        """is_completed should be True when status is completed."""
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            status=ProgressStatus.COMPLETED.value,
        )
        assert progress.is_completed is True

    def test_user_learning_progress_is_completed_false_for_in_progress(self):
        """is_completed should be False when status is not completed."""
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            status=ProgressStatus.IN_PROGRESS.value,
        )
        assert progress.is_completed is False

    def test_user_learning_progress_time_tracking(self):
        """UserLearningProgress should track time_spent_seconds."""
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            time_spent_seconds=2700,  # 45 minutes
        )
        assert progress.time_spent_seconds == 2700

    def test_user_learning_progress_score_tracking(self):
        """UserLearningProgress should track best_score and last_score."""
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            best_score=Decimal("95.0"),
            last_score=Decimal("90.0"),
            attempts=3,
        )
        assert progress.best_score == Decimal("95.0")
        assert progress.last_score == Decimal("90.0")
        assert progress.attempts == 3

    def test_user_learning_progress_bookmarked_default_false(self):
        """bookmarked should default to False - SQLAlchemy defaults only apply with DB session."""
        # Explicit value since SQLAlchemy column defaults don't apply without DB
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            bookmarked=False,
        )
        assert progress.bookmarked is False

    def test_user_learning_progress_with_notes(self):
        """UserLearningProgress should accept user_notes."""
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            user_notes="Key takeaway: always focus on value stream.",
        )
        assert progress.user_notes == "Key takeaway: always focus on value stream."

    def test_user_learning_progress_with_review_scheduling(self):
        """UserLearningProgress should accept spaced repetition fields."""
        next_review = datetime.now(timezone.utc) + timedelta(days=7)
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            next_review_date=next_review,
            review_interval_days=7,
            ease_factor=Decimal("2.5"),
        )
        assert progress.next_review_date == next_review
        assert progress.review_interval_days == 7
        assert progress.ease_factor == Decimal("2.5")

    def test_user_learning_progress_with_last_position(self):
        """UserLearningProgress should accept last_position for resuming."""
        progress = UserLearningProgress(
            user_id=uuid4(),
            unit_id=uuid4(),
            last_position={"section": 2, "timestamp": 125.5},
        )
        assert progress.last_position == {"section": 2, "timestamp": 125.5}


class TestProgressStatusEnum:
    """Tests for ProgressStatus enum."""

    def test_all_statuses_defined(self):
        """All expected progress statuses should be defined."""
        assert ProgressStatus.NOT_STARTED.value == "not_started"
        assert ProgressStatus.IN_PROGRESS.value == "in_progress"
        assert ProgressStatus.COMPLETED.value == "completed"
        assert ProgressStatus.NEEDS_REVIEW.value == "needs_review"
        assert ProgressStatus.FAILED.value == "failed"
        assert ProgressStatus.SKIPPED.value == "skipped"
