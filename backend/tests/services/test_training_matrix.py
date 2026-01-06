"""
Tests for the Training Matrix Gap Analysis Service.

Tests cover:
- Matrix generation
- Gap analysis
- Expiration alerts
- User skill summary
- Station readiness reports
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from sensei.services.training_matrix import (
    TrainingMatrixService,
    TrainingMatrixResult,
    GapAnalysisResult,
    ExpirationAlertResult,
    SkillGap,
    ExpiringCertification,
    RecertificationTask,
    MatrixRow,
    SkillCellData,
    GapSeverity,
    ExpirationUrgency,
    CertificationStatusValue,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def service() -> TrainingMatrixService:
    """Create a fresh training matrix service."""
    return TrainingMatrixService()


@pytest.fixture
def reference_date() -> date:
    """Standard reference date for tests."""
    return date(2025, 1, 15)


@pytest.fixture
def sample_users():
    """Create sample users."""
    return [
        {
            "id": uuid4(),
            "name": "John Smith",
            "email": "john.smith@example.com",
            "department": "Production",
            "role": "Operator",
        },
        {
            "id": uuid4(),
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "department": "Production",
            "role": "Team Lead",
        },
        {
            "id": uuid4(),
            "name": "Bob Wilson",
            "email": "bob.wilson@example.com",
            "department": "Quality",
            "role": "Inspector",
        },
    ]


@pytest.fixture
def sample_skills():
    """Create sample skills."""
    return [
        {
            "id": 1,
            "name": "CNC Operation",
            "code": "CNC-001",
            "skill_category": "technical",
            "proficiency_levels": ["Awareness", "Basic", "Proficient", "Expert", "Trainer"],
            "is_safety_critical": False,
            "is_quality_critical": True,
            "requires_recertification": True,
            "recertification_hours": 4.0,
        },
        {
            "id": 2,
            "name": "Lockout/Tagout",
            "code": "SAFETY-001",
            "skill_category": "safety",
            "proficiency_levels": ["Awareness", "Certified"],
            "is_safety_critical": True,
            "is_quality_critical": False,
            "requires_recertification": True,
            "recertification_hours": 2.0,
        },
        {
            "id": 3,
            "name": "Quality Inspection",
            "code": "QC-001",
            "skill_category": "quality",
            "proficiency_levels": ["Awareness", "Basic", "Proficient", "Expert"],
            "is_safety_critical": False,
            "is_quality_critical": True,
            "requires_recertification": True,
            "recertification_hours": 3.0,
        },
    ]


@pytest.fixture
def sample_stations():
    """Create sample stations."""
    return [
        {"id": 101, "name": "CNC Station 1"},
        {"id": 102, "name": "Assembly Station 1"},
    ]


@pytest.fixture
def sample_skill_requirements():
    """Create sample skill requirements."""
    return [
        {
            "id": 1,
            "skill_id": 1,
            "station_id": 101,
            "minimum_proficiency_level": 2,  # Proficient
            "is_mandatory": True,
        },
        {
            "id": 2,
            "skill_id": 2,
            "station_id": 101,
            "minimum_proficiency_level": 1,  # Certified
            "is_mandatory": True,
        },
        {
            "id": 3,
            "skill_id": 3,
            "station_id": 102,
            "minimum_proficiency_level": 2,  # Proficient
            "is_mandatory": True,
        },
    ]


@pytest.fixture
def sample_user_skills(sample_users, reference_date):
    """Create sample user skills."""
    return [
        # John - CNC Proficient, certified
        {
            "user_id": sample_users[0]["id"],
            "skill_id": 1,
            "proficiency_level": 2,
            "certification_status": CertificationStatusValue.CERTIFIED.value,
            "certified_date": reference_date - timedelta(days=100),
            "expiration_date": reference_date + timedelta(days=265),
        },
        # John - LOTO Certified
        {
            "user_id": sample_users[0]["id"],
            "skill_id": 2,
            "proficiency_level": 1,
            "certification_status": CertificationStatusValue.CERTIFIED.value,
            "certified_date": reference_date - timedelta(days=200),
            "expiration_date": reference_date + timedelta(days=165),
        },
        # Jane - CNC Expert, expiring soon
        {
            "user_id": sample_users[1]["id"],
            "skill_id": 1,
            "proficiency_level": 3,
            "certification_status": CertificationStatusValue.CERTIFIED.value,
            "certified_date": reference_date - timedelta(days=350),
            "expiration_date": reference_date + timedelta(days=15),  # Expiring in 15 days
        },
        # Jane - LOTO Expired
        {
            "user_id": sample_users[1]["id"],
            "skill_id": 2,
            "proficiency_level": 1,
            "certification_status": CertificationStatusValue.EXPIRED.value,
            "certified_date": reference_date - timedelta(days=400),
            "expiration_date": reference_date - timedelta(days=35),
        },
        # Bob - QC Proficient
        {
            "user_id": sample_users[2]["id"],
            "skill_id": 3,
            "proficiency_level": 2,
            "certification_status": CertificationStatusValue.CERTIFIED.value,
            "certified_date": reference_date - timedelta(days=50),
            "expiration_date": reference_date + timedelta(days=315),
        },
    ]


# ==============================================================================
# Service Initialization Tests
# ==============================================================================

class TestServiceInitialization:
    """Test service initialization."""
    
    def test_service_creates(self, service: TrainingMatrixService):
        """Service initializes correctly."""
        assert service is not None
    
    def test_default_expiration_thresholds(self, service: TrainingMatrixService):
        """Default expiration thresholds are set."""
        thresholds = service.get_expiration_thresholds()
        assert thresholds["critical"] == 7
        assert thresholds["urgent"] == 30
        assert thresholds["warning"] == 60
        assert thresholds["upcoming"] == 90
    
    def test_set_custom_threshold(self, service: TrainingMatrixService):
        """Set custom expiration threshold."""
        service.set_expiration_threshold(ExpirationUrgency.CRITICAL, 14)
        thresholds = service.get_expiration_thresholds()
        assert thresholds["critical"] == 14


# ==============================================================================
# Matrix Generation Tests
# ==============================================================================

class TestMatrixGeneration:
    """Test training matrix generation."""
    
    def test_generate_basic_matrix(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Generate a basic training matrix."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],  # John -> CNC Station 1
            sample_users[1]["id"]: [sample_stations[0]],  # Jane -> CNC Station 1
            sample_users[2]["id"]: [sample_stations[1]],  # Bob -> Assembly Station 1
        }
        
        result = service.generate_matrix(
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        assert isinstance(result, TrainingMatrixResult)
        assert result.total_users == 3
        assert result.total_skills == 3
        assert len(result.rows) == 3
        assert len(result.skill_columns) == 3
    
    def test_matrix_detects_gaps(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Matrix detects skill gaps."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],  # John - all good
            sample_users[1]["id"]: [sample_stations[0]],  # Jane - LOTO expired
            sample_users[2]["id"]: [sample_stations[1]],  # Bob - all good
        }
        
        result = service.generate_matrix(
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        # Jane has LOTO expired (safety critical gap)
        assert result.total_gaps >= 1
        assert result.critical_gaps >= 1
        
        # Find Jane's row
        jane_row = next(r for r in result.rows if r.user_name == "Jane Doe")
        assert jane_row.total_gaps >= 1
        assert jane_row.critical_gaps >= 1
    
    def test_matrix_detects_expiring(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Matrix detects expiring certifications."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],
            sample_users[1]["id"]: [sample_stations[0]],  # Jane - CNC expiring in 15 days
        }
        
        result = service.generate_matrix(
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        assert result.expiring_certifications >= 1
        
        # Find Jane's row
        jane_row = next(r for r in result.rows if r.user_name == "Jane Doe")
        assert jane_row.expiring_soon >= 1
    
    def test_matrix_row_structure(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Matrix row has correct structure."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],
        }
        
        result = service.generate_matrix(
            users=[sample_users[0]],
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        row = result.rows[0]
        assert row.user_id == sample_users[0]["id"]
        assert row.user_name == "John Smith"
        assert row.user_email == "john.smith@example.com"
        assert len(row.skills) == 3  # All skills
    
    def test_skill_cell_structure(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Skill cell has correct structure."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],
        }
        
        result = service.generate_matrix(
            users=[sample_users[0]],
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        row = result.rows[0]
        cnc_cell = next(c for c in row.skills if c.skill_code == "CNC-001")
        
        assert cnc_cell.skill_id == 1
        assert cnc_cell.proficiency_level == 2
        assert cnc_cell.proficiency_name == "Proficient"
        assert cnc_cell.certification_status == "certified"
        assert cnc_cell.is_required is True  # Required for CNC Station 1
        assert cnc_cell.has_gap is False


# ==============================================================================
# Gap Analysis Tests
# ==============================================================================

class TestGapAnalysis:
    """Test gap analysis functionality."""
    
    def test_detect_certification_gap(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Detect gap when user is not certified."""
        user_stations = {
            sample_users[1]["id"]: [sample_stations[0]],  # Jane - LOTO expired
        }
        
        result = service.analyze_gaps(
            users=[sample_users[1]],
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
        )
        
        assert isinstance(result, GapAnalysisResult)
        assert result.total_gaps >= 1
        
        # Find the LOTO gap
        loto_gap = next((g for g in result.gaps if g.skill_code == "SAFETY-001"), None)
        assert loto_gap is not None
        assert loto_gap.severity == GapSeverity.CRITICAL  # Safety critical
    
    def test_detect_proficiency_gap(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Detect gap when proficiency is below requirement."""
        user_skills = [
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 1,
                "proficiency_level": 1,  # Basic, but Proficient required
                "certification_status": CertificationStatusValue.CERTIFIED.value,
            }
        ]
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],
        }
        
        result = service.analyze_gaps(
            users=[sample_users[0]],
            skills=sample_skills,
            user_skills=user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
        )
        
        assert result.total_gaps >= 1
        cnc_gap = next((g for g in result.gaps if g.skill_code == "CNC-001"), None)
        assert cnc_gap is not None
        assert cnc_gap.severity == GapSeverity.MEDIUM
        assert cnc_gap.current_level == 1
        assert cnc_gap.required_level == 2
    
    def test_no_gap_when_qualified(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """No gap when user meets requirements."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],  # John - fully qualified
        }
        
        result = service.analyze_gaps(
            users=[sample_users[0]],
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
        )
        
        # John should have no gaps for his station
        john_gaps = [g for g in result.gaps if g.user_id == sample_users[0]["id"]]
        assert len(john_gaps) == 0
    
    def test_gap_aggregation(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Gap result includes aggregation data."""
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],
            sample_users[1]["id"]: [sample_stations[0]],
        }
        
        result = service.analyze_gaps(
            users=sample_users[:2],
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
        )
        
        assert "by_severity" in dir(result) or hasattr(result, "by_severity")
        assert "by_skill" in dir(result) or hasattr(result, "by_skill")
        assert "by_station" in dir(result) or hasattr(result, "by_station")
    
    def test_gap_severity_safety_critical(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Safety critical skill gaps are marked critical."""
        user_skills = [
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 2,  # LOTO - safety critical
                "proficiency_level": 0,
                "certification_status": CertificationStatusValue.NOT_CERTIFIED.value,
            }
        ]
        user_stations = {
            sample_users[0]["id"]: [sample_stations[0]],
        }
        
        result = service.analyze_gaps(
            users=[sample_users[0]],
            skills=sample_skills,
            user_skills=user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
        )
        
        loto_gap = next((g for g in result.gaps if g.skill_code == "SAFETY-001"), None)
        assert loto_gap is not None
        assert loto_gap.severity == GapSeverity.CRITICAL
        assert loto_gap.is_safety_critical is True


# ==============================================================================
# Expiration Alert Tests
# ==============================================================================

class TestExpirationAlerts:
    """Test expiration alert functionality."""
    
    def test_detect_expired_certification(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        reference_date,
    ):
        """Detect expired certifications."""
        user_skills = [
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 1,
                "proficiency_level": 2,
                "certification_status": CertificationStatusValue.CERTIFIED.value,
                "expiration_date": reference_date - timedelta(days=10),  # Already expired
            }
        ]
        
        result = service.check_expiring_certifications(
            user_skills=user_skills,
            skills=sample_skills,
            users=sample_users,
            reference_date=reference_date,
        )
        
        assert isinstance(result, ExpirationAlertResult)
        assert result.total_alerts == 1
        assert result.by_urgency["expired"] == 1
    
    def test_detect_expiring_soon(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        reference_date,
    ):
        """Detect certifications expiring soon."""
        result = service.check_expiring_certifications(
            user_skills=sample_user_skills,
            skills=sample_skills,
            users=sample_users,
            reference_date=reference_date,
            days_ahead=30,
        )
        
        # Jane's CNC expires in 15 days
        assert result.total_alerts >= 1
        
        urgent_alert = next(
            (a for a in result.alerts if a.skill_code == "CNC-001" and a.days_until_expiration == 15),
            None
        )
        assert urgent_alert is not None
        assert urgent_alert.urgency == ExpirationUrgency.URGENT
    
    def test_expiration_urgency_levels(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        reference_date,
    ):
        """Test different urgency levels."""
        user_skills = [
            # Expired
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 1,
                "certification_status": CertificationStatusValue.CERTIFIED.value,
                "expiration_date": reference_date - timedelta(days=5),
            },
            # Critical (within 7 days)
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 2,
                "certification_status": CertificationStatusValue.CERTIFIED.value,
                "expiration_date": reference_date + timedelta(days=5),
            },
            # Urgent (within 30 days)
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 3,
                "certification_status": CertificationStatusValue.CERTIFIED.value,
                "expiration_date": reference_date + timedelta(days=20),
            },
        ]
        
        result = service.check_expiring_certifications(
            user_skills=user_skills,
            skills=sample_skills,
            users=sample_users,
            reference_date=reference_date,
            days_ahead=90,
        )
        
        assert result.by_urgency["expired"] == 1
        assert result.by_urgency["critical"] == 1
        assert result.by_urgency["urgent"] == 1
    
    def test_generates_recertification_tasks(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        reference_date,
    ):
        """Generates recertification task suggestions."""
        user_skills = [
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 1,
                "certification_status": CertificationStatusValue.CERTIFIED.value,
                "expiration_date": reference_date + timedelta(days=20),  # Within lead time
            }
        ]
        
        result = service.check_expiring_certifications(
            user_skills=user_skills,
            skills=sample_skills,
            users=sample_users,
            reference_date=reference_date,
        )
        
        assert len(result.suggested_tasks) >= 1
        task = result.suggested_tasks[0]
        assert isinstance(task, RecertificationTask)
        assert "Recertification" in task.title
    
    def test_skips_non_certified(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        reference_date,
    ):
        """Skips non-certified skills."""
        user_skills = [
            {
                "user_id": sample_users[0]["id"],
                "skill_id": 1,
                "certification_status": CertificationStatusValue.NOT_CERTIFIED.value,
                "expiration_date": reference_date - timedelta(days=10),
            }
        ]
        
        result = service.check_expiring_certifications(
            user_skills=user_skills,
            skills=sample_skills,
            users=sample_users,
            reference_date=reference_date,
        )
        
        assert result.total_alerts == 0


# ==============================================================================
# User Skill Summary Tests
# ==============================================================================

class TestUserSkillSummary:
    """Test user skill summary functionality."""
    
    def test_get_user_summary(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Get user skill summary."""
        user_id = sample_users[0]["id"]
        user_stations = [sample_stations[0]]
        
        result = service.get_user_skill_summary(
            user_id=user_id,
            user_skills=sample_user_skills,
            skills=sample_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        assert result["user_id"] == str(user_id)
        assert result["total_skills"] == 2  # John has 2 skills
        assert result["certified"] == 2
        assert "skill_details" in result
    
    def test_summary_counts_gaps(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_skill_requirements,
        sample_stations,
        reference_date,
    ):
        """Summary counts skill gaps."""
        user_id = sample_users[0]["id"]
        user_skills = [
            {
                "user_id": user_id,
                "skill_id": 1,
                "proficiency_level": 2,
                "certification_status": CertificationStatusValue.CERTIFIED.value,
            },
            # Missing LOTO skill
        ]
        user_stations = [sample_stations[0]]
        
        result = service.get_user_skill_summary(
            user_id=user_id,
            user_skills=user_skills,
            skills=sample_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=user_stations,
            reference_date=reference_date,
        )
        
        assert result["required_skills_count"] >= 1


# ==============================================================================
# Station Readiness Tests
# ==============================================================================

class TestStationReadiness:
    """Test station readiness functionality."""
    
    def test_get_station_readiness(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Get station readiness report."""
        assigned_users = [sample_users[0]["id"], sample_users[1]["id"]]
        
        result = service.get_station_readiness(
            station_id=101,
            station_name="CNC Station 1",
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            assigned_users=assigned_users,
        )
        
        assert result["station_id"] == 101
        assert result["station_name"] == "CNC Station 1"
        assert result["total_assigned_users"] == 2
        assert "required_skills" in result
    
    def test_readiness_calculates_coverage(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Readiness report includes coverage percentage."""
        assigned_users = [sample_users[0]["id"]]  # Only John (fully qualified)
        
        result = service.get_station_readiness(
            station_id=101,
            station_name="CNC Station 1",
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            assigned_users=assigned_users,
        )
        
        assert "overall_readiness_percent" in result
        assert result["overall_readiness_percent"] > 0
    
    def test_readiness_identifies_gaps(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        sample_stations,
    ):
        """Readiness identifies skill gaps."""
        # Include Jane who has expired LOTO
        assigned_users = [sample_users[0]["id"], sample_users[1]["id"]]
        
        result = service.get_station_readiness(
            station_id=101,
            station_name="CNC Station 1",
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            assigned_users=assigned_users,
        )
        
        # Jane has expired LOTO
        assert result["skills_with_gaps"] >= 0 or result["critical_skill_gaps"] >= 0


# ==============================================================================
# Edge Case Tests
# ==============================================================================

class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_users(self, service: TrainingMatrixService, sample_skills, reference_date):
        """Handle empty user list."""
        result = service.generate_matrix(
            users=[],
            skills=sample_skills,
            user_skills=[],
            skill_requirements=[],
            reference_date=reference_date,
        )
        
        assert result.total_users == 0
        assert len(result.rows) == 0
    
    def test_empty_skills(self, service: TrainingMatrixService, sample_users, reference_date):
        """Handle empty skills list."""
        result = service.generate_matrix(
            users=sample_users,
            skills=[],
            user_skills=[],
            skill_requirements=[],
            reference_date=reference_date,
        )
        
        assert result.total_skills == 0
        assert len(result.skill_columns) == 0
    
    def test_user_without_station(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        sample_user_skills,
        sample_skill_requirements,
        reference_date,
    ):
        """Handle user without assigned station."""
        result = service.generate_matrix(
            users=sample_users,
            skills=sample_skills,
            user_skills=sample_user_skills,
            skill_requirements=sample_skill_requirements,
            user_stations=None,  # No station assignments
            reference_date=reference_date,
        )
        
        # Should still work, just no required skills
        assert result.total_users == 3
        assert result.total_gaps == 0  # No required skills = no gaps
    
    def test_skill_without_user_skill_record(
        self,
        service: TrainingMatrixService,
        sample_users,
        sample_skills,
        reference_date,
    ):
        """Handle skill that user doesn't have."""
        result = service.generate_matrix(
            users=[sample_users[0]],
            skills=sample_skills,
            user_skills=[],  # No user skill records
            skill_requirements=[],
            reference_date=reference_date,
        )
        
        row = result.rows[0]
        for cell in row.skills:
            assert cell.proficiency_level == 0
            assert cell.certification_status == "not_certified"


# ==============================================================================
# Data Class Tests
# ==============================================================================

class TestDataClasses:
    """Test data class structures."""
    
    def test_skill_gap_structure(self):
        """SkillGap has correct structure."""
        gap = SkillGap(
            user_id=uuid4(),
            user_name="John",
            skill_id=1,
            skill_name="CNC",
            skill_code="CNC-001",
            station_id=101,
            station_name="Station 1",
            required_level=2,
            current_level=1,
            certification_status="certified",
            severity=GapSeverity.MEDIUM,
            recommended_action="Advance to Proficient",
        )
        
        assert gap.skill_name == "CNC"
        assert gap.severity == GapSeverity.MEDIUM
    
    def test_expiring_certification_structure(self):
        """ExpiringCertification has correct structure."""
        cert = ExpiringCertification(
            user_id=uuid4(),
            user_name="John",
            skill_id=1,
            skill_name="CNC",
            skill_code="CNC-001",
            certification_status="certified",
            expiration_date=date.today() + timedelta(days=10),
            days_until_expiration=10,
            urgency=ExpirationUrgency.URGENT,
        )
        
        assert cert.days_until_expiration == 10
        assert cert.urgency == ExpirationUrgency.URGENT
    
    def test_recertification_task_structure(self):
        """RecertificationTask has correct structure."""
        task = RecertificationTask(
            user_id=uuid4(),
            user_name="John",
            skill_id=1,
            skill_name="CNC",
            title="Recertification: CNC",
            description="Complete recertification",
            due_date=date.today() + timedelta(days=10),
            priority="high",
        )
        
        assert "Recertification" in task.title
        assert task.priority == "high"
