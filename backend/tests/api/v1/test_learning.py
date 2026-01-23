"""Tests for Learning API endpoints.

Full test coverage for learning engine operations:
- Module CRUD and publishing
- Unit CRUD and publishing
- User progress tracking
- Assessment management
- Learning path management
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from sensei.api.v1.endpoints.learning import (
    ModuleCreate,
    ModuleUpdate,
    UnitCreate,
    UnitUpdate,
    ProgressUpdate,
    AssessmentCreate,
    AssessmentUpdate,
    PathCreate,
    PathUpdate,
    create_module,
    get_module,
    list_modules,
    update_module,
    publish_module,
    delete_module,
    create_unit,
    get_unit,
    list_units,
    update_unit,
    publish_unit,
    delete_unit,
    get_my_progress,
    get_unit_progress,
    start_unit,
    update_progress,
    complete_unit,
    create_assessment,
    get_assessment,
    update_assessment,
    delete_assessment,
    create_path,
    get_path,
    list_paths,
    update_path,
    delete_path,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.learning import (
    LearningModule,
    LearningUnit,
    UserLearningProgress,
    LearningAssessment,
    LearningPath,
    LearningCategory,
    ContentType,
    DifficultyLevel,
    ProgressStatus,
)
from sensei.services.ai.reasoning_engine import A3Phase


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    return db


# =============================================================================
# Module Tests
# =============================================================================


class TestLearningModules:
    """Tests for Learning Module operations."""

    @pytest.fixture
    def sample_module_data(self):
        """Sample module data."""
        return {
            "id": uuid4(),
            "code": "TPS-101",
            "title": "Introduction to TPS",
            "description": "Learn the basics of Toyota Production System",
            "category": LearningCategory.TPS.value,
            "difficulty": DifficultyLevel.BEGINNER.value,
            "learning_objectives": ["Understand TPS principles"],
            "prerequisites": [],
            "estimated_duration_minutes": 60,
            "is_published": False,
            "published_at": None,
            "display_order": 1,
            "thumbnail_url": None,
            "tags": ["tps", "lean"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by_id": uuid4(),
            "updated_by_id": None,
        }

    def create_mock_module(self, data: dict, **overrides) -> MagicMock:
        """Create a mock module."""
        module = MagicMock(spec=LearningModule)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(module, key, value)
        return module

    @pytest.mark.asyncio
    async def test_create_module(self, mock_db, mock_user, sample_module_data):
        """Test creating a module."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            for key, value in sample_module_data.items():
                setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = ModuleCreate(
            code="TPS-101",
            title="Introduction to TPS",
            description="Learn the basics",
            category=LearningCategory.TPS,
            difficulty=DifficultyLevel.BEGINNER,
        )
        result = await create_module(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_module_duplicate_code(self, mock_db, mock_user, sample_module_data):
        """Test creating module with duplicate code."""
        existing_module = self.create_mock_module(sample_module_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_module
        mock_db.execute.return_value = mock_result

        data = ModuleCreate(code="TPS-101", title="Duplicate")
        with pytest.raises(ConflictError):
            await create_module(data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_module(self, mock_db, mock_user, sample_module_data):
        """Test getting a module."""
        module = self.create_mock_module(sample_module_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = module
        mock_db.execute.return_value = mock_result

        result = await get_module(sample_module_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.code == "TPS-101"

    @pytest.mark.asyncio
    async def test_get_module_not_found(self, mock_db, mock_user):
        """Test getting non-existent module."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_module(uuid4(), mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_modules(self, mock_db, mock_user, sample_module_data):
        """Test listing modules."""
        modules = [self.create_mock_module(sample_module_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = modules
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_modules(
            mock_db,
            mock_user,
            category=None,
            difficulty=None,
            published_only=False,
            search=None,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_update_module(self, mock_db, mock_user, sample_module_data):
        """Test updating a module."""
        module = self.create_mock_module(sample_module_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = module
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Title"

        mock_db.refresh = mock_refresh

        data = ModuleUpdate(title="Updated Title")
        result = await update_module(sample_module_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_publish_module(self, mock_db, mock_user, sample_module_data):
        """Test publishing a module."""
        module = self.create_mock_module(sample_module_data, is_published=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = module
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await publish_module(sample_module_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "published" in result.message.lower()

    @pytest.mark.asyncio
    async def test_publish_already_published(self, mock_db, mock_user, sample_module_data):
        """Test publishing already published module."""
        module = self.create_mock_module(sample_module_data, is_published=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = module
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await publish_module(sample_module_data["id"], mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_delete_module(self, mock_db, mock_user, sample_module_data):
        """Test deleting a module."""
        module = self.create_mock_module(sample_module_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = module
        mock_db.execute.return_value = mock_result

        result = await delete_module(sample_module_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "deleted" in result.message.lower()
        mock_db.delete.assert_called_once()


# =============================================================================
# Unit Tests
# =============================================================================


# Note: TestSocraticPedagogyRAG class removed - SocraticRAGRequest and socratic_rag
# endpoints do not exist in the current implementation


class TestLearningUnits:
    """Tests for Learning Unit operations."""

    @pytest.fixture
    def sample_unit_data(self):
        """Sample unit data."""
        return {
            "id": uuid4(),
            "code": "TPS-101-01",
            "title": "What is TPS?",
            "subtitle": "An introduction",
            "description": "Learn what TPS is",
            "module_id": uuid4(),
            "category": LearningCategory.TPS.value,
            "content_type": ContentType.TEXT.value,
            "difficulty": DifficultyLevel.BEGINNER.value,
            "content": "Content here",
            "content_rich": None,
            "video_url": None,
            "audio_url": None,
            "document_url": None,
            "thumbnail_url": None,
            "key_points": ["Point 1", "Point 2"],
            "examples": [],
            "anti_patterns": [],
            "related_units": [],
            "estimated_duration_minutes": 15,
            "unit_order": 1,
            "is_published": False,
            "published_at": None,
            "version": 1,
            "japanese_term": "トヨタ生産方式",
            "pronunciation": "Toyota Seisan Hoshiki",
            "source_reference": None,
            "tags": ["tps"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by_id": uuid4(),
            "updated_by_id": None,
        }

    def create_mock_unit(self, data: dict, **overrides) -> MagicMock:
        """Create a mock unit."""
        unit = MagicMock(spec=LearningUnit)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(unit, key, value)
        return unit

    @pytest.mark.asyncio
    async def test_create_unit(self, mock_db, mock_user, sample_unit_data):
        """Test creating a unit."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            for key, value in sample_unit_data.items():
                setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = UnitCreate(
            code="TPS-101-01",
            title="What is TPS?",
            category=LearningCategory.TPS,
            content_type=ContentType.TEXT,
        )
        result = await create_unit(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message

    @pytest.mark.asyncio
    async def test_create_unit_duplicate_code(self, mock_db, mock_user, sample_unit_data):
        """Test creating unit with duplicate code."""
        existing_unit = self.create_mock_unit(sample_unit_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_unit
        mock_db.execute.return_value = mock_result

        data = UnitCreate(code="TPS-101-01", title="Duplicate")
        with pytest.raises(ConflictError):
            await create_unit(data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_unit(self, mock_db, mock_user, sample_unit_data):
        """Test getting a unit."""
        unit = self.create_mock_unit(sample_unit_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = unit
        mock_db.execute.return_value = mock_result

        result = await get_unit(sample_unit_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.code == "TPS-101-01"

    @pytest.mark.asyncio
    async def test_list_units(self, mock_db, mock_user, sample_unit_data):
        """Test listing units."""
        units = [self.create_mock_unit(sample_unit_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = units
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_units(
            mock_db,
            mock_user,
            module_id=None,
            category=None,
            content_type=None,
            difficulty=None,
            published_only=False,
            search=None,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_update_unit(self, mock_db, mock_user, sample_unit_data):
        """Test updating a unit."""
        unit = self.create_mock_unit(sample_unit_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = unit
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Title"

        mock_db.refresh = mock_refresh

        data = UnitUpdate(title="Updated Title")
        result = await update_unit(sample_unit_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_publish_unit(self, mock_db, mock_user, sample_unit_data):
        """Test publishing a unit."""
        unit = self.create_mock_unit(sample_unit_data, is_published=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = unit
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await publish_unit(sample_unit_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "published" in result.message.lower()

    @pytest.mark.asyncio
    async def test_delete_unit(self, mock_db, mock_user, sample_unit_data):
        """Test deleting a unit."""
        unit = self.create_mock_unit(sample_unit_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = unit
        mock_db.execute.return_value = mock_result

        result = await delete_unit(sample_unit_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "deleted" in result.message.lower()


# =============================================================================
# Progress Tests
# =============================================================================


class TestUserProgress:
    """Tests for user progress tracking."""

    @pytest.fixture
    def sample_progress_data(self):
        """Sample progress data."""
        return {
            "id": uuid4(),
            "user_id": uuid4(),
            "unit_id": uuid4(),
            "status": ProgressStatus.IN_PROGRESS.value,
            "progress_percentage": 50,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "last_accessed_at": datetime.now(timezone.utc),
            "time_spent_seconds": 300,
            "best_score": None,
            "last_score": None,
            "attempts": 0,
            "bookmarked": False,
            "user_notes": None,
            "next_review_date": None,
            "last_position": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

    @pytest.fixture
    def sample_unit_data(self):
        """Sample unit data."""
        return {
            "id": uuid4(),
            "code": "TPS-101-01",
            "title": "What is TPS?",
        }

    def create_mock_progress(self, data: dict, **overrides) -> MagicMock:
        """Create a mock progress."""
        progress = MagicMock(spec=UserLearningProgress)
        merged = {**data, **overrides}
        for key, value in merged.items():
            if key != "is_completed":
                setattr(progress, key, value)
        progress.is_completed = merged.get("status") == ProgressStatus.COMPLETED.value
        return progress

    def create_mock_unit(self, data: dict) -> MagicMock:
        """Create a mock unit."""
        unit = MagicMock(spec=LearningUnit)
        for key, value in data.items():
            setattr(unit, key, value)
        return unit

    @pytest.mark.asyncio
    async def test_get_my_progress(self, mock_db, mock_user, sample_progress_data):
        """Test getting user's progress."""
        progress_list = [self.create_mock_progress(sample_progress_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = progress_list
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await get_my_progress(
            mock_db,
            mock_user,
            status=None,
            bookmarked_only=False,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_get_unit_progress(self, mock_db, mock_user, sample_progress_data):
        """Test getting progress for a unit."""
        progress = self.create_mock_progress(sample_progress_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = progress
        mock_db.execute.return_value = mock_result

        result = await get_unit_progress(
            sample_progress_data["unit_id"],
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert result.data.progress_percentage == 50

    @pytest.mark.asyncio
    async def test_start_unit_new(self, mock_db, mock_user, sample_unit_data, sample_progress_data):
        """Test starting a new unit."""
        unit = self.create_mock_unit(sample_unit_data)

        mock_unit_result = MagicMock()
        mock_unit_result.scalar_one_or_none.return_value = unit
        mock_progress_result = MagicMock()
        mock_progress_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [mock_unit_result, mock_progress_result]

        async def mock_refresh(obj):
            for key, value in sample_progress_data.items():
                setattr(obj, key, value)
            # is_completed is a computed property - don't set it

        mock_db.refresh = mock_refresh

        result = await start_unit(sample_unit_data["id"], mock_db, mock_user)

        assert result.success is True
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_unit_resume(self, mock_db, mock_user, sample_unit_data, sample_progress_data):
        """Test resuming an existing unit."""
        unit = self.create_mock_unit(sample_unit_data)
        progress = self.create_mock_progress(sample_progress_data)

        mock_unit_result = MagicMock()
        mock_unit_result.scalar_one_or_none.return_value = unit
        mock_progress_result = MagicMock()
        mock_progress_result.scalar_one_or_none.return_value = progress
        mock_db.execute.side_effect = [mock_unit_result, mock_progress_result]

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await start_unit(sample_unit_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "resumed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_update_progress(self, mock_db, mock_user, sample_progress_data):
        """Test updating progress."""
        progress = self.create_mock_progress(sample_progress_data, time_spent_seconds=300)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = progress
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        data = ProgressUpdate(progress_percentage=75, time_spent_seconds=60)
        result = await update_progress(
            sample_progress_data["unit_id"],
            data,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_complete_unit(self, mock_db, mock_user, sample_progress_data):
        """Test completing a unit."""
        progress = self.create_mock_progress(
            sample_progress_data,
            status=ProgressStatus.IN_PROGRESS.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = progress
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh = mock_refresh

        result = await complete_unit(sample_progress_data["unit_id"], mock_db, mock_user)

        assert result.success is True
        assert "completed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_complete_already_completed(self, mock_db, mock_user, sample_progress_data):
        """Test completing already completed unit."""
        progress = self.create_mock_progress(
            sample_progress_data,
            status=ProgressStatus.COMPLETED.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = progress
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError):
            await complete_unit(sample_progress_data["unit_id"], mock_db, mock_user)


# =============================================================================
# Assessment Tests
# =============================================================================


class TestAssessments:
    """Tests for assessment operations."""

    @pytest.fixture
    def sample_assessment_data(self):
        """Sample assessment data."""
        return {
            "id": uuid4(),
            "title": "TPS Knowledge Check",
            "description": "Test your knowledge",
            "unit_id": uuid4(),
            "questions": [
                {
                    "id": "q1",
                    "type": "multiple_choice",
                    "question": "What is TPS?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "points": 10,
                }
            ],
            "passing_score": Decimal("70.00"),
            "max_score": Decimal("100.00"),
            "time_limit_minutes": 30,
            "max_attempts": 3,
            "shuffle_questions": False,
            "show_correct_answers": True,
            "is_published": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by_id": uuid4(),
            "updated_by_id": None,
        }

    def create_mock_assessment(self, data: dict, **overrides) -> MagicMock:
        """Create a mock assessment."""
        assessment = MagicMock(spec=LearningAssessment)
        merged = {**data, **overrides}
        for key, value in merged.items():
            if key != "question_count":
                setattr(assessment, key, value)
        assessment.question_count = len(merged.get("questions", []))
        return assessment

    @pytest.mark.asyncio
    async def test_create_assessment(self, mock_db, mock_user, sample_assessment_data):
        """Test creating an assessment."""
        async def mock_refresh(obj):
            for key, value in sample_assessment_data.items():
                if key not in ("question_count",):  # question_count is computed
                    setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = AssessmentCreate(
            title="TPS Knowledge Check",
            questions=sample_assessment_data["questions"],
        )
        result = await create_assessment(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message

    @pytest.mark.asyncio
    async def test_get_assessment(self, mock_db, mock_user, sample_assessment_data):
        """Test getting an assessment."""
        assessment = self.create_mock_assessment(sample_assessment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assessment
        mock_db.execute.return_value = mock_result

        result = await get_assessment(sample_assessment_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.title == "TPS Knowledge Check"

    @pytest.mark.asyncio
    async def test_update_assessment(self, mock_db, mock_user, sample_assessment_data):
        """Test updating an assessment."""
        assessment = self.create_mock_assessment(sample_assessment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assessment
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Assessment"

        mock_db.refresh = mock_refresh

        data = AssessmentUpdate(title="Updated Assessment")
        result = await update_assessment(
            sample_assessment_data["id"],
            data,
            mock_db,
            mock_user,
        )

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_delete_assessment(self, mock_db, mock_user, sample_assessment_data):
        """Test deleting an assessment."""
        assessment = self.create_mock_assessment(sample_assessment_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assessment
        mock_db.execute.return_value = mock_result

        result = await delete_assessment(sample_assessment_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "deleted" in result.message.lower()


# =============================================================================
# Path Tests
# =============================================================================


class TestLearningPaths:
    """Tests for learning path operations."""

    @pytest.fixture
    def sample_path_data(self):
        """Sample path data."""
        return {
            "id": uuid4(),
            "path_code": "TPS-CERT",
            "title": "TPS Certification",
            "description": "Complete TPS certification path",
            "difficulty": DifficultyLevel.INTERMEDIATE.value,
            "status": "draft",
            "is_active": True,
            "is_certification_path": True,
            "estimated_hours": 40.0,
            "prerequisites": [],
            "thumbnail_url": None,
            "tags": ["certification", "tps"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "created_by_id": uuid4(),
            "updated_by_id": None,
        }

    def create_mock_path(self, data: dict, **overrides) -> MagicMock:
        """Create a mock path."""
        path = MagicMock(spec=LearningPath)
        merged = {**data, **overrides}
        for key, value in merged.items():
            setattr(path, key, value)
        return path

    @pytest.mark.asyncio
    async def test_create_path(self, mock_db, mock_user, sample_path_data):
        """Test creating a path."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            for key, value in sample_path_data.items():
                setattr(obj, key, value)

        mock_db.refresh = mock_refresh

        data = PathCreate(
            path_code="TPS-CERT",
            title="TPS Certification",
            is_certification_path=True,
        )
        result = await create_path(data, mock_db, mock_user)

        assert result.success is True
        assert "created successfully" in result.message

    @pytest.mark.asyncio
    async def test_create_path_duplicate_code(self, mock_db, mock_user, sample_path_data):
        """Test creating path with duplicate code."""
        existing_path = self.create_mock_path(sample_path_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_path
        mock_db.execute.return_value = mock_result

        data = PathCreate(path_code="TPS-CERT", title="Duplicate")
        with pytest.raises(ConflictError):
            await create_path(data, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_get_path(self, mock_db, mock_user, sample_path_data):
        """Test getting a path."""
        path = self.create_mock_path(sample_path_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = path
        mock_db.execute.return_value = mock_result

        result = await get_path(sample_path_data["id"], mock_db, mock_user)

        assert result.success is True
        assert result.data.path_code == "TPS-CERT"

    @pytest.mark.asyncio
    async def test_list_paths(self, mock_db, mock_user, sample_path_data):
        """Test listing paths."""
        paths = [self.create_mock_path(sample_path_data)]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = paths
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        result = await list_paths(
            mock_db,
            mock_user,
            difficulty=None,
            certification_only=False,
            active_only=True,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_update_path(self, mock_db, mock_user, sample_path_data):
        """Test updating a path."""
        path = self.create_mock_path(sample_path_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = path
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj):
            obj.title = "Updated Path"

        mock_db.refresh = mock_refresh

        data = PathUpdate(title="Updated Path")
        result = await update_path(sample_path_data["id"], data, mock_db, mock_user)

        assert result.success is True
        assert "updated successfully" in result.message

    @pytest.mark.asyncio
    async def test_delete_path(self, mock_db, mock_user, sample_path_data):
        """Test deleting a path."""
        path = self.create_mock_path(sample_path_data)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = path
        mock_db.execute.return_value = mock_result

        result = await delete_path(sample_path_data["id"], mock_db, mock_user)

        assert result.success is True
        assert "deleted" in result.message.lower()
