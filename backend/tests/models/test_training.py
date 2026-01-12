"""
Tests for Training and Skills models.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal

import pytest

from sensei.core.time import utcnow_naive

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


class TestSkillModel:
    """Test cases for Skill model."""

    def test_skill_creation_basic(self):
        """Test basic skill creation."""
        skill = Skill(
            name="CNC Operation",
            code="SKL-CNC-001",
            skill_category=SkillCategory.TECHNICAL,
        )

        assert skill.name == "CNC Operation"
        assert skill.code == "SKL-CNC-001"
        assert skill.skill_category == SkillCategory.TECHNICAL

    def test_skill_creation_full(self):
        """Test skill with all fields."""
        skill = Skill(
            name="Soldering",
            code="SKL-SOLDER",
            description="Surface mount and through-hole soldering",
            skill_category=SkillCategory.TECHNICAL,
            proficiency_levels=["Beginner", "Intermediate", "Advanced", "Expert"],
            minimum_required_level=2,
            is_safety_critical=True,
            is_quality_critical=True,
            requires_recertification=True,
            recertification_interval_days=180,
            initial_training_hours=Decimal("16.0"),
            recertification_hours=Decimal("4.0"),
        )

        assert skill.skill_category == SkillCategory.TECHNICAL
        assert len(skill.proficiency_levels) == 4
        assert skill.minimum_required_level == 2
        assert skill.is_safety_critical is True
        assert skill.is_quality_critical is True
        assert skill.recertification_interval_days == 180

    def test_skill_category_values(self):
        """Test all skill category values."""
        for category in SkillCategory:
            skill = Skill(
                name=f"Test {category.value}",
                code=f"SKL-{category.value}",
                skill_category=category,
            )
            assert skill.skill_category == category

    def test_skill_level_count(self):
        """Test level_count property."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
            proficiency_levels=["L1", "L2", "L3", "L4", "L5"],
        )

        assert skill.level_count == 5

    def test_skill_get_level_name(self):
        """Test get_level_name method."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
            proficiency_levels=["Novice", "Basic", "Proficient", "Expert"],
        )

        assert skill.get_level_name(0) == "Novice"
        assert skill.get_level_name(3) == "Expert"
        assert skill.get_level_name(10) is None
        assert skill.get_level_name(-1) is None

    def test_skill_repr(self):
        """Test string representation."""
        skill = Skill(
            name="Test Skill",
            code="SKL-TEST",
        )
        skill.id = 1

        assert "Skill" in repr(skill)
        assert "SKL-TEST" in repr(skill)


class TestSkillRequirementModel:
    """Test cases for SkillRequirement model."""

    def test_skill_requirement_for_station(self):
        """Test skill requirement for station."""
        req = SkillRequirement(
            skill_id=1,
            station_id=5,
            minimum_proficiency_level=2,
            is_mandatory=True,
        )

        assert req.skill_id == 1
        assert req.station_id == 5
        assert req.product_id is None
        assert req.minimum_proficiency_level == 2
        assert req.is_mandatory is True

    def test_skill_requirement_for_product(self):
        """Test skill requirement for product."""
        req = SkillRequirement(
            skill_id=1,
            product_id=10,
            minimum_proficiency_level=3,
            is_mandatory=False,
            notes="Nice to have",
        )

        assert req.product_id == 10
        assert req.station_id is None
        assert req.is_mandatory is False

    def test_skill_requirement_repr(self):
        """Test string representation."""
        req = SkillRequirement(
            skill_id=1,
            station_id=5,
        )

        assert "SkillRequirement" in repr(req)
        assert "station" in repr(req)


class TestTrainingModel:
    """Test cases for Training model."""

    def test_training_creation_basic(self):
        """Test basic training creation."""
        training = Training(
            name="Basic Soldering",
            skill_id=1,
            training_type=TrainingType.CLASSROOM,
            status=TrainingStatus.SCHEDULED,
        )

        assert training.name == "Basic Soldering"
        assert training.skill_id == 1
        assert training.training_type == TrainingType.CLASSROOM
        assert training.status == TrainingStatus.SCHEDULED

    def test_training_creation_full(self):
        """Test training with all fields."""
        scheduled = date.today() + timedelta(days=7)

        training = Training(
            name="Advanced CNC Programming",
            code="TRN-CNC-ADV",
            description="Advanced G-code and CAM programming",
            skill_id=5,
            training_type=TrainingType.WORKSHOP,
            duration_hours=Decimal("24.0"),
            max_participants=10,
            scheduled_date=scheduled,
            location="Training Room A",
            status=TrainingStatus.SCHEDULED,
            trainer_id=100,
            provides_certification=True,
            certification_level_granted=3,
            cost_per_person=Decimal("500.00"),
        )

        assert training.code == "TRN-CNC-ADV"
        assert training.training_type == TrainingType.WORKSHOP
        assert training.duration_hours == Decimal("24.0")
        assert training.max_participants == 10
        assert training.cost_per_person == Decimal("500.00")

    def test_training_type_values(self):
        """Test all training type values."""
        for training_type in TrainingType:
            training = Training(
                name=f"Test {training_type.value}",
                skill_id=1,
                training_type=training_type,
            )
            assert training.training_type == training_type

    def test_training_status_values(self):
        """Test all status values."""
        for status in TrainingStatus:
            training = Training(
                name=f"Test {status.value}",
                skill_id=1,
                status=status,
            )
            assert training.status == status

    def test_training_is_upcoming(self):
        """Test is_upcoming property."""
        training_future = Training(
            name="Future Training",
            skill_id=1,
            scheduled_date=date.today() + timedelta(days=7),
        )

        training_past = Training(
            name="Past Training",
            skill_id=1,
            scheduled_date=date.today() - timedelta(days=7),
        )

        training_no_date = Training(
            name="No Date Training",
            skill_id=1,
        )

        assert training_future.is_upcoming is True
        assert training_past.is_upcoming is False
        assert training_no_date.is_upcoming is False

    def test_training_has_capacity(self):
        """Test has_capacity property."""
        # No limit
        training_unlimited = Training(
            name="Unlimited",
            skill_id=1,
            max_participants=None,
        )

        # With limit but no participants
        training_with_limit = Training(
            name="Limited",
            skill_id=1,
            max_participants=5,
        )

        assert training_unlimited.has_capacity is True
        assert training_with_limit.has_capacity is True

    def test_training_repr(self):
        """Test string representation."""
        training = Training(
            name="Test Training",
            skill_id=1,
            training_type=TrainingType.CLASSROOM,
            status=TrainingStatus.SCHEDULED,
        )
        training.id = 1

        assert "Training" in repr(training)
        assert "Test Training" in repr(training)


class TestTrainingParticipantModel:
    """Test cases for TrainingParticipant model."""

    def test_participant_creation_basic(self):
        """Test basic participant creation."""
        participant = TrainingParticipant(
            training_id=1,
            user_id=5,
            enrollment_status=EnrollmentStatus.ENROLLED,
            attendance_status=AttendanceStatus.PENDING,
        )

        assert participant.training_id == 1
        assert participant.user_id == 5
        assert participant.enrollment_status == EnrollmentStatus.ENROLLED
        assert participant.attendance_status == AttendanceStatus.PENDING

    def test_participant_creation_full(self):
        """Test participant with all fields."""
        participant = TrainingParticipant(
            training_id=1,
            user_id=5,
            enrollment_status=EnrollmentStatus.COMPLETED,
            attendance_status=AttendanceStatus.ATTENDED,
            score=Decimal("92.5"),
            passed=True,
            completed_at=utcnow_naive(),
            certificate_number="CERT-2024-0001",
            certificate_issued_at=utcnow_naive(),
            notes="Excellent participation",
        )

        assert participant.enrollment_status == EnrollmentStatus.COMPLETED
        assert participant.attendance_status == AttendanceStatus.ATTENDED
        assert participant.score == Decimal("92.5")
        assert participant.passed is True
        assert participant.certificate_number == "CERT-2024-0001"

    def test_enrollment_status_values(self):
        """Test all enrollment status values."""
        for status in EnrollmentStatus:
            participant = TrainingParticipant(
                training_id=1,
                user_id=1,
                enrollment_status=status,
            )
            assert participant.enrollment_status == status

    def test_attendance_status_values(self):
        """Test all attendance status values."""
        for status in AttendanceStatus:
            participant = TrainingParticipant(
                training_id=1,
                user_id=1,
                attendance_status=status,
            )
            assert participant.attendance_status == status

    def test_participant_repr(self):
        """Test string representation."""
        participant = TrainingParticipant(
            training_id=1,
            user_id=5,
        )

        assert "TrainingParticipant" in repr(participant)


class TestUserSkillModel:
    """Test cases for UserSkill model."""

    def test_user_skill_creation_basic(self):
        """Test basic user skill creation."""
        user_skill = UserSkill(
            user_id=1,
            skill_id=5,
            proficiency_level=0,
            certification_status=CertificationStatus.NOT_CERTIFIED,
        )

        assert user_skill.user_id == 1
        assert user_skill.skill_id == 5
        assert user_skill.proficiency_level == 0
        assert user_skill.certification_status == CertificationStatus.NOT_CERTIFIED

    def test_user_skill_creation_full(self):
        """Test user skill with all fields."""
        user_skill = UserSkill(
            user_id=1,
            skill_id=5,
            proficiency_level=3,
            certification_status=CertificationStatus.CERTIFIED,
            certified_date=date.today() - timedelta(days=100),
            expiration_date=date.today() + timedelta(days=265),
            certified_by_id=100,
            certificate_number="CERT-2024-0001",
        )

        assert user_skill.proficiency_level == 3
        assert user_skill.certification_status == CertificationStatus.CERTIFIED
        assert user_skill.certificate_number == "CERT-2024-0001"

    def test_certification_status_values(self):
        """Test all certification status values."""
        for status in CertificationStatus:
            user_skill = UserSkill(
                user_id=1,
                skill_id=1,
                certification_status=status,
            )
            assert user_skill.certification_status == status

    def test_user_skill_is_certified(self):
        """Test is_certified property."""
        certified = UserSkill(
            user_id=1,
            skill_id=1,
            certification_status=CertificationStatus.CERTIFIED,
        )

        not_certified = UserSkill(
            user_id=1,
            skill_id=1,
            certification_status=CertificationStatus.NOT_CERTIFIED,
        )

        expired = UserSkill(
            user_id=1,
            skill_id=1,
            certification_status=CertificationStatus.EXPIRED,
        )

        assert certified.is_certified is True
        assert not_certified.is_certified is False
        assert expired.is_certified is False

    def test_user_skill_is_expired(self):
        """Test is_expired property."""
        expired = UserSkill(
            user_id=1,
            skill_id=1,
            expiration_date=date.today() - timedelta(days=10),
        )

        valid = UserSkill(
            user_id=1,
            skill_id=1,
            expiration_date=date.today() + timedelta(days=100),
        )

        no_expiry = UserSkill(
            user_id=1,
            skill_id=1,
        )

        assert expired.is_expired is True
        assert valid.is_expired is False
        assert no_expiry.is_expired is False

    def test_user_skill_days_until_expiration(self):
        """Test days_until_expiration property."""
        user_skill = UserSkill(
            user_id=1,
            skill_id=1,
            expiration_date=date.today() + timedelta(days=30),
        )

        no_expiry = UserSkill(
            user_id=1,
            skill_id=1,
        )

        assert user_skill.days_until_expiration == 30
        assert no_expiry.days_until_expiration is None

    def test_user_skill_needs_recertification_soon(self):
        """Test needs_recertification_soon property."""
        needs_soon = UserSkill(
            user_id=1,
            skill_id=1,
            expiration_date=date.today() + timedelta(days=15),
        )

        not_soon = UserSkill(
            user_id=1,
            skill_id=1,
            expiration_date=date.today() + timedelta(days=60),
        )

        already_expired = UserSkill(
            user_id=1,
            skill_id=1,
            expiration_date=date.today() - timedelta(days=5),
        )

        no_expiry = UserSkill(
            user_id=1,
            skill_id=1,
        )

        assert needs_soon.needs_recertification_soon is True
        assert not_soon.needs_recertification_soon is False
        assert already_expired.needs_recertification_soon is False
        assert no_expiry.needs_recertification_soon is False

    def test_user_skill_repr(self):
        """Test string representation."""
        user_skill = UserSkill(
            user_id=1,
            skill_id=5,
            certification_status=CertificationStatus.NOT_CERTIFIED,
        )

        assert "UserSkill" in repr(user_skill)


class TestTrainingRelationships:
    """Test Training model relationships."""

    def test_skill_has_requirements_list(self):
        """Test that skill has requirements list."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
        )
        assert hasattr(skill, 'requirements')

    def test_skill_has_user_skills_list(self):
        """Test that skill has user_skills list."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
        )
        assert hasattr(skill, 'user_skills')

    def test_skill_has_trainings_list(self):
        """Test that skill has trainings list."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
        )
        assert hasattr(skill, 'trainings')

    def test_training_has_participants_list(self):
        """Test that training has participants list."""
        training = Training(
            name="Test",
            skill_id=1,
        )
        assert hasattr(training, 'participants')


class TestTrainingValidation:
    """Test validation constraints."""

    def test_skill_explicit_recertification_interval(self):
        """Test explicit recertification interval is 365 days."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
            recertification_interval_days=365,
        )
        assert skill.recertification_interval_days == 365

    def test_skill_explicit_training_hours(self):
        """Test explicit initial training hours."""
        skill = Skill(
            name="Test",
            code="SKL-TEST",
            initial_training_hours=Decimal("8.0"),
        )
        assert skill.initial_training_hours == Decimal("8.0")

    def test_training_explicit_duration(self):
        """Test explicit training duration."""
        training = Training(
            name="Test",
            skill_id=1,
            duration_hours=Decimal("8.0"),
        )
        assert training.duration_hours == Decimal("8.0")


class TestTrainingEdgeCases:
    """Test edge cases for Training models."""

    def test_skill_with_custom_proficiency_levels(self):
        """Test skill with custom proficiency levels."""
        skill = Skill(
            name="Custom Levels",
            code="SKL-CUSTOM",
            proficiency_levels=["L1", "L2", "L3"],
        )

        assert skill.level_count == 3
        assert skill.get_level_name(0) == "L1"
        assert skill.get_level_name(2) == "L3"

    def test_user_skill_with_assessment_history(self):
        """Test user skill with assessment history."""
        history = [
            {
                "date": "2024-01-15",
                "score": 85,
                "type": "practical",
                "assessor_id": 100,
                "notes": "Good performance",
            },
            {
                "date": "2024-06-15",
                "score": 92,
                "type": "recertification",
                "assessor_id": 100,
            },
        ]

        user_skill = UserSkill(
            user_id=1,
            skill_id=1,
            assessment_scores=history,
        )

        assert len(user_skill.assessment_scores) == 2
        assert user_skill.assessment_scores[1]["score"] == 92

    def test_training_with_syllabus(self):
        """Test training with JSON syllabus."""
        syllabus = {
            "modules": [
                {"title": "Introduction", "duration_minutes": 30},
                {"title": "Theory", "duration_minutes": 120},
                {"title": "Practical", "duration_minutes": 180},
                {"title": "Assessment", "duration_minutes": 60},
            ],
            "objectives": ["Learn basics", "Apply in practice"],
        }

        training = Training(
            name="Structured Training",
            skill_id=1,
            syllabus=syllabus,
        )

        assert len(training.syllabus["modules"]) == 4

    def test_participant_score_boundary(self):
        """Test participant score at boundaries."""
        participant_zero = TrainingParticipant(
            training_id=1,
            user_id=1,
            score=Decimal("0.0"),
        )

        participant_perfect = TrainingParticipant(
            training_id=1,
            user_id=1,
            score=Decimal("100.0"),
        )

        assert participant_zero.score == Decimal("0.0")
        assert participant_perfect.score == Decimal("100.0")
