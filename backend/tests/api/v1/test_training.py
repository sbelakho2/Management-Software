"""Tests for Training API endpoints.

Tests cover:
- Skills CRUD operations
- Skill Requirements management
- Training CRUD and workflow
- Training Participants (enrollment, completion)
- User Skills (certification management)
"""

from __future__ import annotations

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sensei.api.v1.endpoints.training import (
    router,
    create_skill,
    get_skill,
    list_skills,
    update_skill,
    delete_skill,
    create_skill_requirement,
    list_skill_requirements,
    delete_skill_requirement,
    create_training,
    get_training,
    list_trainings,
    update_training,
    delete_training,
    start_training,
    complete_training,
    cancel_training,
    enroll_participant,
    list_participants,
    update_participant,
    complete_participation,
    remove_participant,
    create_user_skill,
    list_user_skills,
    update_user_skill,
    certify_user_skill,
    revoke_certification,
    delete_user_skill,
    SkillCreate,
    SkillUpdate,
    SkillRequirementCreate,
    TrainingCreate,
    TrainingUpdate,
    ParticipantEnroll,
    ParticipantUpdate,
    ParticipantComplete,
    UserSkillCreate,
    UserSkillUpdate,
    UserSkillCertify,
)
from sensei.api.exceptions import ConflictError, NotFoundError
from sensei.models.training import (
    Skill,
    SkillCategory,
    SkillRequirement,
    Training,
    TrainingType,
    TrainingStatus,
    TrainingParticipant,
    EnrollmentStatus,
    AttendanceStatus,
    UserSkill,
    CertificationStatus,
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Create a mock current user."""
    user = MagicMock()
    user.id = uuid4()
    return user


@pytest.fixture
def sample_skill_data() -> dict[str, Any]:
    """Sample skill data."""
    return {
        "name": "CNC Programming",
        "code": "CNC-PROG",
        "description": "CNC machine programming",
        "skill_category": SkillCategory.TECHNICAL,
        "proficiency_levels": ["Awareness", "Basic", "Proficient", "Expert"],
        "minimum_required_level": 2,
        "is_safety_critical": True,
        "is_quality_critical": True,
        "requires_recertification": True,
        "recertification_interval_days": 365,
        "initial_training_hours": Decimal("16.0"),
        "recertification_hours": Decimal("4.0"),
    }


@pytest.fixture
def sample_training_data() -> dict[str, Any]:
    """Sample training data."""
    return {
        "name": "CNC Programming Basics",
        "code": "TRN-CNC-001",
        "description": "Introduction to CNC programming",
        "skill_id": 1,
        "training_type": TrainingType.CLASSROOM,
        "duration_hours": Decimal("16.0"),
        "max_participants": 10,
        "scheduled_date": date.today() + timedelta(days=7),
        "location": "Training Room A",
        "provides_certification": True,
        "certification_level_granted": 2,
        "cost_per_person": Decimal("500.00"),
    }


class TestSkillCRUD:
    """Tests for Skill CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_skill_success(
        self, mock_db: AsyncMock, mock_user: MagicMock, sample_skill_data: dict
    ):
        """Test successful skill creation."""
        skill_create = SkillCreate(**sample_skill_data)

        # Mock no existing skill with same code
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        captured_skill = None

        def capture_skill(obj):
            nonlocal captured_skill
            captured_skill = obj

        mock_db.add.side_effect = capture_skill

        async def refresh_skill(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
            obj.deleted_at = None
            obj.proficiency_levels = sample_skill_data["proficiency_levels"]

        mock_db.refresh.side_effect = refresh_skill

        result = await create_skill(skill_create, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Skill created successfully"
        assert result.data.name == sample_skill_data["name"]
        assert result.data.code == sample_skill_data["code"]

    @pytest.mark.asyncio
    async def test_create_skill_duplicate_code(
        self, mock_db: AsyncMock, mock_user: MagicMock, sample_skill_data: dict
    ):
        """Test skill creation with duplicate code raises error."""
        skill_create = SkillCreate(**sample_skill_data)

        # Mock existing skill with same code
        existing_skill = MagicMock(spec=Skill)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_skill
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError) as exc:
            await create_skill(skill_create, mock_db, mock_user)
        assert "already exists" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_skill_success(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test get skill by ID."""
        skill = MagicMock(spec=Skill)
        skill.id = 1
        skill.name = "Test Skill"
        skill.code = "TEST-001"
        skill.description = "Test description"
        skill.skill_category = SkillCategory.TECHNICAL
        skill.proficiency_levels = ["Awareness", "Basic", "Proficient"]
        skill.minimum_required_level = 2
        skill.is_safety_critical = False
        skill.is_quality_critical = True
        skill.requires_recertification = True
        skill.recertification_interval_days = 365
        skill.initial_training_hours = Decimal("8.0")
        skill.recertification_hours = Decimal("2.0")
        skill.created_at = datetime.utcnow()
        skill.updated_at = datetime.utcnow()
        skill.is_deleted = False
        skill.level_count = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = skill
        mock_db.execute.return_value = mock_result

        result = await get_skill(1, mock_db, mock_user)

        assert result.success is True
        assert result.data.id == 1
        assert result.data.name == "Test Skill"
        assert result.data.level_count == 3

    @pytest.mark.asyncio
    async def test_get_skill_not_found(self, mock_db: AsyncMock, mock_user: MagicMock):
        """Test get skill not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_skill(999, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_skills_with_filters(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test listing skills with filters."""
        skill = MagicMock(spec=Skill)
        skill.id = 1
        skill.name = "Safety Skill"
        skill.code = "SAFETY-001"
        skill.description = "Safety training"
        skill.skill_category = SkillCategory.SAFETY
        skill.proficiency_levels = ["Awareness", "Basic", "Proficient"]
        skill.minimum_required_level = 1
        skill.is_safety_critical = True
        skill.is_quality_critical = False
        skill.requires_recertification = True
        skill.recertification_interval_days = 180
        skill.initial_training_hours = Decimal("4.0")
        skill.recertification_hours = Decimal("1.0")
        skill.created_at = datetime.utcnow()
        skill.updated_at = datetime.utcnow()
        skill.is_deleted = False
        skill.level_count = 3

        # Count query returns 1
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Data query returns skills
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [skill]

        mock_db.execute.side_effect = [count_result, data_result]

        result = await list_skills(
            mock_db,
            mock_user,
            category=SkillCategory.SAFETY,
            is_safety_critical=True,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].skill_category == SkillCategory.SAFETY
        assert result.pagination.total_items == 1

    @pytest.mark.asyncio
    async def test_update_skill_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test skill update."""
        skill = MagicMock(spec=Skill)
        skill.id = 1
        skill.name = "Old Name"
        skill.code = "TEST-001"
        skill.description = "Old description"
        skill.skill_category = SkillCategory.TECHNICAL
        skill.proficiency_levels = ["Awareness", "Basic"]
        skill.minimum_required_level = 1
        skill.is_safety_critical = False
        skill.is_quality_critical = False
        skill.requires_recertification = True
        skill.recertification_interval_days = 365
        skill.initial_training_hours = Decimal("8.0")
        skill.recertification_hours = Decimal("2.0")
        skill.created_at = datetime.utcnow()
        skill.updated_at = datetime.utcnow()
        skill.is_deleted = False
        skill.level_count = 2

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = skill
        mock_db.execute.return_value = mock_result

        update_data = SkillUpdate(name="New Name", is_safety_critical=True)
        result = await update_skill(1, update_data, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Skill updated successfully"

    @pytest.mark.asyncio
    async def test_delete_skill_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test skill deletion (soft delete)."""
        skill = MagicMock(spec=Skill)
        skill.id = 1
        skill.is_deleted = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = skill
        mock_db.execute.return_value = mock_result

        result = await delete_skill(1, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Skill deleted successfully"
        assert skill.is_deleted is True


class TestSkillRequirements:
    """Tests for Skill Requirement operations."""

    @pytest.mark.asyncio
    async def test_create_skill_requirement_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test creating a skill requirement."""
        data = SkillRequirementCreate(
            skill_id=1,
            station_id=10,
            minimum_proficiency_level=2,
            is_mandatory=True,
        )

        # Mock skill exists
        skill_result = MagicMock()
        skill = MagicMock(spec=Skill)
        skill_result.scalar_one_or_none.return_value = skill

        # Mock no duplicate
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [skill_result, dup_result]

        captured_req = None

        def capture_req(obj):
            nonlocal captured_req
            captured_req = obj

        mock_db.add.side_effect = capture_req

        async def refresh_req(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()

        mock_db.refresh.side_effect = refresh_req

        result = await create_skill_requirement(data, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Skill requirement created successfully"

    @pytest.mark.asyncio
    async def test_create_skill_requirement_no_target(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test creating requirement without station or product fails."""
        data = SkillRequirementCreate(
            skill_id=1,
            # No station_id or product_id
        )

        with pytest.raises(ConflictError) as exc:
            await create_skill_requirement(data, mock_db, mock_user)
        assert "station_id or product_id" in str(exc.value)

    @pytest.mark.asyncio
    async def test_list_skill_requirements(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test listing skill requirements."""
        req = MagicMock(spec=SkillRequirement)
        req.id = 1
        req.skill_id = 1
        req.station_id = 10
        req.product_id = None
        req.minimum_proficiency_level = 2
        req.is_mandatory = True
        req.notes = None
        req.created_at = datetime.utcnow()
        req.updated_at = datetime.utcnow()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [req]

        mock_db.execute.side_effect = [count_result, data_result]

        result = await list_skill_requirements(
            mock_db, mock_user, skill_id=1, page=1, page_size=20
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].skill_id == 1

    @pytest.mark.asyncio
    async def test_delete_skill_requirement(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test deleting a skill requirement."""
        req = MagicMock(spec=SkillRequirement)
        req.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = req
        mock_db.execute.return_value = mock_result

        result = await delete_skill_requirement(1, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Skill requirement deleted successfully"
        mock_db.delete.assert_called_once_with(req)


class TestTrainingCRUD:
    """Tests for Training CRUD and workflow operations."""

    @pytest.mark.asyncio
    async def test_create_training_success(
        self, mock_db: AsyncMock, mock_user: MagicMock, sample_training_data: dict
    ):
        """Test creating a training."""
        training_create = TrainingCreate(**sample_training_data)

        # Mock skill exists
        skill_result = MagicMock()
        skill = MagicMock(spec=Skill)
        skill_result.scalar_one_or_none.return_value = skill
        mock_db.execute.return_value = skill_result

        captured_training = None

        def capture_training(obj):
            nonlocal captured_training
            captured_training = obj

        mock_db.add.side_effect = capture_training

        async def refresh_training(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
            obj.deleted_at = None
            obj.status = TrainingStatus.SCHEDULED
            obj.participants = []
            # Note: enrolled_count, has_capacity, is_upcoming are computed properties
            # and will work automatically since we set participants = []

        mock_db.refresh.side_effect = refresh_training

        result = await create_training(training_create, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Training created successfully"

    @pytest.mark.asyncio
    async def test_get_training_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test getting a training by ID."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.name = "Test Training"
        training.code = "TRN-001"
        training.description = "Test description"
        training.skill_id = 1
        training.training_type = TrainingType.CLASSROOM
        training.duration_hours = Decimal("8.0")
        training.max_participants = 10
        training.scheduled_date = date.today() + timedelta(days=7)
        training.scheduled_start_time = None
        training.scheduled_end_time = None
        training.location = "Room A"
        training.status = TrainingStatus.SCHEDULED
        training.trainer_id = None
        training.external_trainer_name = "John Doe"
        training.provides_certification = True
        training.certification_level_granted = 2
        training.cost_per_person = Decimal("500.00")
        training.materials_url = None
        training.syllabus = None
        training.notes = None
        training.created_at = datetime.utcnow()
        training.updated_at = datetime.utcnow()
        training.is_deleted = False
        training.participants = []
        training.enrolled_count = 0
        training.has_capacity = True
        training.is_upcoming = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = training
        mock_db.execute.return_value = mock_result

        result = await get_training(1, mock_db, mock_user)

        assert result.success is True
        assert result.data.id == 1
        assert result.data.name == "Test Training"
        assert result.data.enrolled_count == 0
        assert result.data.has_capacity is True

    @pytest.mark.asyncio
    async def test_get_training_not_found(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test getting training that doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await get_training(999, mock_db, mock_user)

    @pytest.mark.asyncio
    async def test_list_trainings_with_filters(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test listing trainings with filters."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.name = "CNC Training"
        training.code = "TRN-CNC-001"
        training.description = "CNC machine training"
        training.skill_id = 1
        training.training_type = TrainingType.ON_THE_JOB
        training.duration_hours = Decimal("16.0")
        training.max_participants = 5
        training.scheduled_date = date.today() + timedelta(days=14)
        training.scheduled_start_time = None
        training.scheduled_end_time = None
        training.location = "Shop Floor"
        training.status = TrainingStatus.SCHEDULED
        training.trainer_id = uuid4()
        training.external_trainer_name = None
        training.provides_certification = True
        training.certification_level_granted = 3
        training.cost_per_person = None
        training.materials_url = None
        training.syllabus = None
        training.notes = None
        training.created_at = datetime.utcnow()
        training.updated_at = datetime.utcnow()
        training.is_deleted = False
        training.participants = []
        training.enrolled_count = 3
        training.has_capacity = True
        training.is_upcoming = True

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [training]

        mock_db.execute.side_effect = [count_result, data_result]

        result = await list_trainings(
            mock_db,
            mock_user,
            skill_id=1,
            training_type=TrainingType.ON_THE_JOB,
            upcoming_only=True,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].training_type == TrainingType.ON_THE_JOB

    @pytest.mark.asyncio
    async def test_update_training_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test updating a training."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.name = "Old Name"
        training.code = "TRN-001"
        training.description = None
        training.skill_id = 1
        training.training_type = TrainingType.CLASSROOM
        training.duration_hours = Decimal("8.0")
        training.max_participants = 10
        training.scheduled_date = date.today() + timedelta(days=7)
        training.scheduled_start_time = None
        training.scheduled_end_time = None
        training.location = None
        training.status = TrainingStatus.SCHEDULED
        training.trainer_id = None
        training.external_trainer_name = None
        training.provides_certification = True
        training.certification_level_granted = 2
        training.cost_per_person = None
        training.materials_url = None
        training.syllabus = None
        training.notes = None
        training.created_at = datetime.utcnow()
        training.updated_at = datetime.utcnow()
        training.is_deleted = False
        training.participants = []
        training.enrolled_count = 0
        training.has_capacity = True
        training.is_upcoming = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = training
        mock_db.execute.return_value = mock_result

        update_data = TrainingUpdate(name="New Name", location="Room B")
        result = await update_training(1, update_data, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Training updated successfully"

    @pytest.mark.asyncio
    async def test_training_workflow_start(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test starting a training."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.name = "Test Training"
        training.code = "TRN-001"
        training.description = None
        training.skill_id = 1
        training.training_type = TrainingType.CLASSROOM
        training.duration_hours = Decimal("8.0")
        training.max_participants = 10
        training.scheduled_date = date.today()
        training.scheduled_start_time = None
        training.scheduled_end_time = None
        training.location = None
        training.status = TrainingStatus.SCHEDULED
        training.trainer_id = None
        training.external_trainer_name = None
        training.provides_certification = True
        training.certification_level_granted = 2
        training.cost_per_person = None
        training.materials_url = None
        training.syllabus = None
        training.notes = None
        training.created_at = datetime.utcnow()
        training.updated_at = datetime.utcnow()
        training.is_deleted = False
        training.participants = []
        training.enrolled_count = 5
        training.has_capacity = True
        training.is_upcoming = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = training
        mock_db.execute.return_value = mock_result

        result = await start_training(1, mock_db, mock_user)

        assert result.success is True
        assert training.status == TrainingStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_training_workflow_complete(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test completing a training."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.name = "Test Training"
        training.code = "TRN-001"
        training.description = None
        training.skill_id = 1
        training.training_type = TrainingType.CLASSROOM
        training.duration_hours = Decimal("8.0")
        training.max_participants = 10
        training.scheduled_date = date.today()
        training.scheduled_start_time = None
        training.scheduled_end_time = None
        training.location = None
        training.status = TrainingStatus.IN_PROGRESS
        training.trainer_id = None
        training.external_trainer_name = None
        training.provides_certification = True
        training.certification_level_granted = 2
        training.cost_per_person = None
        training.materials_url = None
        training.syllabus = None
        training.notes = None
        training.created_at = datetime.utcnow()
        training.updated_at = datetime.utcnow()
        training.is_deleted = False
        training.participants = []
        training.enrolled_count = 5
        training.has_capacity = True
        training.is_upcoming = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = training
        mock_db.execute.return_value = mock_result

        result = await complete_training(1, mock_db, mock_user)

        assert result.success is True
        assert training.status == TrainingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_training_workflow_cancel(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test cancelling a training."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.name = "Test Training"
        training.code = "TRN-001"
        training.description = None
        training.skill_id = 1
        training.training_type = TrainingType.CLASSROOM
        training.duration_hours = Decimal("8.0")
        training.max_participants = 10
        training.scheduled_date = date.today() + timedelta(days=7)
        training.scheduled_start_time = None
        training.scheduled_end_time = None
        training.location = None
        training.status = TrainingStatus.SCHEDULED
        training.trainer_id = None
        training.external_trainer_name = None
        training.provides_certification = True
        training.certification_level_granted = 2
        training.cost_per_person = None
        training.materials_url = None
        training.syllabus = None
        training.notes = None
        training.created_at = datetime.utcnow()
        training.updated_at = datetime.utcnow()
        training.is_deleted = False
        training.participants = []
        training.enrolled_count = 0
        training.has_capacity = True
        training.is_upcoming = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = training
        mock_db.execute.return_value = mock_result

        result = await cancel_training(1, mock_db, mock_user)

        assert result.success is True
        assert training.status == TrainingStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_delete_training_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test deleting a training (soft delete)."""
        training = MagicMock(spec=Training)
        training.id = 1
        training.is_deleted = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = training
        mock_db.execute.return_value = mock_result

        result = await delete_training(1, mock_db, mock_user)

        assert result.success is True
        assert result.message == "Training deleted successfully"
        assert training.is_deleted is True


class TestTrainingParticipants:
    """Tests for Training Participant operations."""

    @pytest.mark.asyncio
    async def test_enroll_participant_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test enrolling a participant in training."""
        user_id = uuid4()
        data = ParticipantEnroll(user_id=user_id)

        # Mock training exists with capacity
        training = MagicMock(spec=Training)
        training.id = 1
        training.max_participants = 10
        training.participants = []
        training.has_capacity = True

        training_result = MagicMock()
        training_result.scalar_one_or_none.return_value = training

        # Mock no duplicate
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [training_result, dup_result]

        captured_participant = None

        def capture_participant(obj):
            nonlocal captured_participant
            captured_participant = obj

        mock_db.add.side_effect = capture_participant

        async def refresh_participant(obj):
            obj.id = 1
            obj.training_id = 1
            obj.user_id = user_id
            obj.enrollment_status = EnrollmentStatus.ENROLLED
            obj.attendance_status = AttendanceStatus.PENDING
            obj.score = None
            obj.passed = None
            obj.completed_at = None
            obj.certificate_number = None
            obj.certificate_issued_at = None
            obj.notes = None
            obj.manager_notes = None
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()

        mock_db.refresh.side_effect = refresh_participant

        result = await enroll_participant(1, data, mock_db, mock_user)

        assert result.success is True
        assert "enrolled" in result.message

    @pytest.mark.asyncio
    async def test_enroll_participant_waitlisted(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test enrolling when training is at capacity (waitlisted)."""
        user_id = uuid4()
        data = ParticipantEnroll(user_id=user_id)

        # Mock training at capacity
        training = MagicMock(spec=Training)
        training.id = 1
        training.max_participants = 5
        training.participants = [MagicMock() for _ in range(5)]
        training.has_capacity = False

        training_result = MagicMock()
        training_result.scalar_one_or_none.return_value = training

        # Mock no duplicate
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [training_result, dup_result]

        captured_participant = None

        def capture_participant(obj):
            nonlocal captured_participant
            captured_participant = obj

        mock_db.add.side_effect = capture_participant

        async def refresh_participant(obj):
            obj.id = 1
            obj.training_id = 1
            obj.user_id = user_id
            obj.enrollment_status = EnrollmentStatus.WAITLISTED
            obj.attendance_status = AttendanceStatus.PENDING
            obj.score = None
            obj.passed = None
            obj.completed_at = None
            obj.certificate_number = None
            obj.certificate_issued_at = None
            obj.notes = None
            obj.manager_notes = None
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()

        mock_db.refresh.side_effect = refresh_participant

        result = await enroll_participant(1, data, mock_db, mock_user)

        assert result.success is True
        assert "waitlisted" in result.message

    @pytest.mark.asyncio
    async def test_list_participants(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test listing training participants."""
        participant = MagicMock(spec=TrainingParticipant)
        participant.id = 1
        participant.training_id = 1
        participant.user_id = uuid4()
        participant.enrollment_status = EnrollmentStatus.ENROLLED
        participant.attendance_status = AttendanceStatus.PENDING
        participant.score = None
        participant.passed = None
        participant.completed_at = None
        participant.certificate_number = None
        participant.certificate_issued_at = None
        participant.notes = None
        participant.manager_notes = None
        participant.created_at = datetime.utcnow()
        participant.updated_at = datetime.utcnow()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [participant]

        mock_db.execute.side_effect = [count_result, data_result]

        result = await list_participants(1, mock_db, mock_user, page=1, page_size=20)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].enrollment_status == EnrollmentStatus.ENROLLED

    @pytest.mark.asyncio
    async def test_complete_participation_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test completing a participant's training."""
        participant = MagicMock(spec=TrainingParticipant)
        participant.id = 1
        participant.training_id = 1
        participant.user_id = uuid4()
        participant.enrollment_status = EnrollmentStatus.ENROLLED
        participant.attendance_status = AttendanceStatus.PENDING
        participant.score = None
        participant.passed = None
        participant.completed_at = None
        participant.certificate_number = None
        participant.certificate_issued_at = None
        participant.notes = None
        participant.manager_notes = None
        participant.created_at = datetime.utcnow()
        participant.updated_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = participant
        mock_db.execute.return_value = mock_result

        data = ParticipantComplete(score=Decimal("95.5"), passed=True)
        result = await complete_participation(1, 1, data, mock_db, mock_user)

        assert result.success is True
        assert participant.enrollment_status == EnrollmentStatus.COMPLETED
        assert participant.attendance_status == AttendanceStatus.ATTENDED
        assert participant.passed is True


class TestUserSkills:
    """Tests for User Skill operations."""

    @pytest.mark.asyncio
    async def test_create_user_skill_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test creating a user skill record."""
        user_id = uuid4()
        data = UserSkillCreate(user_id=user_id, skill_id=1, proficiency_level=1)

        # Mock skill exists
        skill_result = MagicMock()
        skill = MagicMock(spec=Skill)
        skill_result.scalar_one_or_none.return_value = skill

        # Mock no duplicate
        dup_result = MagicMock()
        dup_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [skill_result, dup_result]

        captured_user_skill = None

        def capture_user_skill(obj):
            nonlocal captured_user_skill
            captured_user_skill = obj

        mock_db.add.side_effect = capture_user_skill

        async def refresh_user_skill(obj):
            obj.id = 1
            obj.user_id = user_id
            obj.skill_id = 1
            obj.proficiency_level = 1
            obj.certification_status = CertificationStatus.NOT_CERTIFIED
            obj.certified_date = None
            obj.expiration_date = None
            obj.last_recertification_date = None
            obj.certified_by_id = None
            obj.certificate_number = None
            obj.assessment_scores = None
            obj.notes = None
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()
            # Note: is_certified, is_expired, days_until_expiration, 
            # needs_recertification_soon are computed properties

        mock_db.refresh.side_effect = refresh_user_skill

        result = await create_user_skill(data, mock_db, mock_user)

        assert result.success is True
        assert result.message == "User skill created successfully"

    @pytest.mark.asyncio
    async def test_list_user_skills_with_filters(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test listing user skills with filters."""
        user_id = uuid4()
        user_skill = MagicMock(spec=UserSkill)
        user_skill.id = 1
        user_skill.user_id = user_id
        user_skill.skill_id = 1
        user_skill.proficiency_level = 3
        user_skill.certification_status = CertificationStatus.CERTIFIED
        user_skill.certified_date = date.today() - timedelta(days=30)
        user_skill.expiration_date = date.today() + timedelta(days=335)
        user_skill.last_recertification_date = None
        user_skill.certified_by_id = uuid4()
        user_skill.certificate_number = "CERT-001"
        user_skill.assessment_scores = None
        user_skill.notes = None
        user_skill.created_at = datetime.utcnow()
        user_skill.updated_at = datetime.utcnow()
        user_skill.is_certified = True
        user_skill.is_expired = False
        user_skill.days_until_expiration = 335
        user_skill.needs_recertification_soon = False

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = [user_skill]

        mock_db.execute.side_effect = [count_result, data_result]

        result = await list_user_skills(
            mock_db,
            mock_user,
            user_id=user_id,
            certification_status=CertificationStatus.CERTIFIED,
            page=1,
            page_size=20,
        )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].certification_status == CertificationStatus.CERTIFIED
        assert result.data[0].is_certified is True

    @pytest.mark.asyncio
    async def test_certify_user_skill_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test certifying a user for a skill."""
        user_id = uuid4()
        user_skill = MagicMock(spec=UserSkill)
        user_skill.id = 1
        user_skill.user_id = user_id
        user_skill.skill_id = 1
        user_skill.proficiency_level = 1
        user_skill.certification_status = CertificationStatus.NOT_CERTIFIED
        user_skill.certified_date = None
        user_skill.expiration_date = None
        user_skill.last_recertification_date = None
        user_skill.certified_by_id = None
        user_skill.certificate_number = None
        user_skill.assessment_scores = None
        user_skill.notes = None
        user_skill.created_at = datetime.utcnow()
        user_skill.updated_at = datetime.utcnow()
        user_skill.is_certified = False
        user_skill.is_expired = False
        user_skill.days_until_expiration = None
        user_skill.needs_recertification_soon = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user_skill
        mock_db.execute.return_value = mock_result

        data = UserSkillCertify(
            proficiency_level=3,
            expiration_date=date.today() + timedelta(days=365),
            certificate_number="CERT-002",
        )

        result = await certify_user_skill(1, data, mock_db, mock_user)

        assert result.success is True
        assert "certified" in result.message.lower()
        assert user_skill.certification_status == CertificationStatus.CERTIFIED
        assert user_skill.proficiency_level == 3

    @pytest.mark.asyncio
    async def test_revoke_certification_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test revoking a user's certification."""
        user_id = uuid4()
        user_skill = MagicMock(spec=UserSkill)
        user_skill.id = 1
        user_skill.user_id = user_id
        user_skill.skill_id = 1
        user_skill.proficiency_level = 3
        user_skill.certification_status = CertificationStatus.CERTIFIED
        user_skill.certified_date = date.today() - timedelta(days=30)
        user_skill.expiration_date = date.today() + timedelta(days=335)
        user_skill.last_recertification_date = None
        user_skill.certified_by_id = uuid4()
        user_skill.certificate_number = "CERT-001"
        user_skill.assessment_scores = None
        user_skill.notes = None
        user_skill.created_at = datetime.utcnow()
        user_skill.updated_at = datetime.utcnow()
        user_skill.is_certified = True
        user_skill.is_expired = False
        user_skill.days_until_expiration = 335
        user_skill.needs_recertification_soon = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user_skill
        mock_db.execute.return_value = mock_result

        result = await revoke_certification(1, mock_db, mock_user)

        assert result.success is True
        assert "revoked" in result.message.lower()
        assert user_skill.certification_status == CertificationStatus.REVOKED

    @pytest.mark.asyncio
    async def test_revoke_certification_invalid_status(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test revoking certification that isn't certified."""
        user_skill = MagicMock(spec=UserSkill)
        user_skill.id = 1
        user_skill.certification_status = CertificationStatus.NOT_CERTIFIED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user_skill
        mock_db.execute.return_value = mock_result

        with pytest.raises(ConflictError) as exc:
            await revoke_certification(1, mock_db, mock_user)
        assert "Cannot revoke" in str(exc.value)

    @pytest.mark.asyncio
    async def test_delete_user_skill_success(
        self, mock_db: AsyncMock, mock_user: MagicMock
    ):
        """Test deleting a user skill record."""
        user_skill = MagicMock(spec=UserSkill)
        user_skill.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user_skill
        mock_db.execute.return_value = mock_result

        result = await delete_user_skill(1, mock_db, mock_user)

        assert result.success is True
        assert result.message == "User skill deleted successfully"
        mock_db.delete.assert_called_once_with(user_skill)
