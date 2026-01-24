"""
Training Matrix API Endpoints.

Provides REST API for:
- Generating training matrix (users × skills)
- Gap analysis (identify missing/deficient skills)
- Expiration alerts (flag expiring certifications)
- User skill summaries
- Station readiness reports
"""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from sensei.services.hr.training_matrix import (
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
)


router = APIRouter(tags=["Training Matrix"])


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class SkillCellSchema(BaseModel):
    """Schema for a skill cell in the matrix."""
    
    skill_id: int
    skill_code: str
    skill_name: str
    proficiency_level: int
    proficiency_name: str
    certification_status: str
    expiration_date: date | None = None
    days_until_expiration: int | None = None
    is_required: bool = False
    minimum_required_level: int | None = None
    has_gap: bool = False
    gap_severity: str | None = None


class MatrixRowSchema(BaseModel):
    """Schema for a row in the training matrix."""
    
    user_id: str
    user_name: str
    user_email: str
    department: str | None = None
    role: str | None = None
    assigned_stations: list[str] = Field(default_factory=list)
    skills: list[SkillCellSchema] = Field(default_factory=list)
    total_gaps: int = 0
    critical_gaps: int = 0
    expiring_soon: int = 0


class SkillColumnSchema(BaseModel):
    """Schema for skill column metadata."""
    
    skill_id: int
    skill_code: str
    skill_name: str
    skill_category: str | None = None
    is_safety_critical: bool = False
    is_quality_critical: bool = False
    proficiency_levels: list[str] = Field(default_factory=list)


class TrainingMatrixResponse(BaseModel):
    """Response schema for the training matrix."""
    
    rows: list[MatrixRowSchema]
    skill_columns: list[SkillColumnSchema]
    total_users: int
    total_skills: int
    total_gaps: int
    critical_gaps: int
    expiring_certifications: int
    generated_at: str


class SkillGapSchema(BaseModel):
    """Schema for a skill gap."""
    
    user_id: str
    user_name: str
    skill_id: int
    skill_name: str
    skill_code: str
    station_id: int | None = None
    station_name: str | None = None
    required_level: int
    current_level: int
    certification_status: str
    severity: str
    is_safety_critical: bool = False
    is_quality_critical: bool = False
    recommended_action: str = ""


class GapAnalysisResponse(BaseModel):
    """Response schema for gap analysis."""
    
    gaps: list[SkillGapSchema]
    total_gaps: int
    by_severity: dict[str, int]
    by_skill: dict[str, int]
    by_station: dict[str, int]
    analyzed_at: str


class ExpiringCertificationSchema(BaseModel):
    """Schema for an expiring certification."""
    
    user_id: str
    user_name: str
    skill_id: int
    skill_name: str
    skill_code: str
    certification_status: str
    expiration_date: date
    days_until_expiration: int
    urgency: str
    requires_recertification: bool = True
    recertification_hours: float = 0.0


class RecertificationTaskSchema(BaseModel):
    """Schema for a suggested recertification task."""
    
    user_id: str
    user_name: str
    skill_id: int
    skill_name: str
    title: str
    description: str
    due_date: date
    priority: str
    is_safety_critical: bool = False


class ExpirationAlertResponse(BaseModel):
    """Response schema for expiration alerts."""
    
    alerts: list[ExpiringCertificationSchema]
    total_alerts: int
    by_urgency: dict[str, int]
    suggested_tasks: list[RecertificationTaskSchema]
    checked_at: str


class UserSkillSummaryResponse(BaseModel):
    """Response schema for user skill summary."""
    
    user_id: str
    total_skills: int
    certified: int
    in_training: int
    expired: int
    not_certified: int = 0
    expiring_soon: int = 0
    gaps: int = 0
    required_skills_count: int
    skill_details: list[dict[str, Any]]


class StationReadinessResponse(BaseModel):
    """Response schema for station readiness."""
    
    station_id: int
    station_name: str
    total_assigned_users: int
    required_skills_count: int = 0
    skills_with_qualified_users: int = 0
    skills_with_gaps: int = 0
    critical_skill_gaps: int = 0
    overall_readiness_percent: float
    required_skills: list[dict[str, Any]]


class ThresholdsResponse(BaseModel):
    """Response schema for expiration thresholds."""
    
    thresholds: dict[str, int]


class ThresholdUpdateRequest(BaseModel):
    """Request schema for updating thresholds."""
    
    urgency: str = Field(..., description="One of: critical, urgent, warning, upcoming")
    days: int = Field(..., gt=0, description="Number of days for this threshold")


# Request Body Schemas for POST endpoints
class GenerateMatrixRequest(BaseModel):
    """Request body for generating training matrix."""
    
    users: list[dict[str, Any]] = Field(default_factory=list, description="Users to include")
    skills: list[dict[str, Any]] = Field(default_factory=list, description="Skills to include")
    user_skills: list[dict[str, Any]] = Field(default_factory=list, description="User skill records")
    skill_requirements: list[dict[str, Any]] = Field(default_factory=list, description="Skill requirements")
    user_stations: dict[str, list[dict[str, Any]]] | None = Field(default=None, description="User station assignments")
    reference_date: date | None = Field(default=None, description="Reference date for calculations")


class GapAnalysisRequest(BaseModel):
    """Request body for gap analysis."""
    
    users: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    user_skills: list[dict[str, Any]] = Field(default_factory=list)
    skill_requirements: list[dict[str, Any]] = Field(default_factory=list)
    user_stations: dict[str, list[dict[str, Any]]] | None = None
    station_id: int | None = Field(default=None, description="Filter by station")
    severity: str | None = Field(default=None, description="Filter by gap severity")


class ExpirationCheckRequest(BaseModel):
    """Request body for checking expirations."""
    
    user_skills: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    users: list[dict[str, Any]] = Field(default_factory=list)
    days_ahead: int = Field(default=90, ge=1, le=365, description="Days to look ahead")
    urgency: str | None = Field(default=None, description="Filter by urgency level")
    reference_date: date | None = None


class UserSkillSummaryRequest(BaseModel):
    """Request body for user skill summary."""
    
    user_skills: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    skill_requirements: list[dict[str, Any]] = Field(default_factory=list)
    user_stations: list[dict[str, Any]] | None = None
    reference_date: date | None = None


class StationReadinessRequest(BaseModel):
    """Request body for station readiness."""
    
    station_name: str = Field(default="Station", description="Station name")
    users: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    user_skills: list[dict[str, Any]] = Field(default_factory=list)
    skill_requirements: list[dict[str, Any]] = Field(default_factory=list)
    assigned_users: list[str] = Field(default_factory=list, description="List of assigned user IDs")


# ==============================================================================
# API Routes
# ==============================================================================

# Global service instance
_service = TrainingMatrixService()


def get_service() -> TrainingMatrixService:
    """Get the training matrix service singleton."""
    return _service


# ------------------------------------------------------------------------------
# Matrix Generation
# ------------------------------------------------------------------------------

@router.post("/generate", response_model=TrainingMatrixResponse)
def generate_matrix(
    request: GenerateMatrixRequest,
) -> TrainingMatrixResponse:
    """
    Generate a training matrix showing users (rows) × skills (columns).
    
    The matrix shows each user's proficiency and certification status for each skill,
    highlights gaps where users don't meet station requirements, and flags
    certifications expiring soon.
    """
    service = get_service()
    
    # Convert str keys to UUID keys for user_stations
    user_stations_uuid: dict[UUID, list[dict[str, Any]]] | None = None
    if request.user_stations:
        user_stations_uuid = {UUID(k): v for k, v in request.user_stations.items()}
    
    result = service.generate_matrix(
        users=request.users,
        skills=request.skills,
        user_skills=request.user_skills,
        skill_requirements=request.skill_requirements,
        user_stations=user_stations_uuid,
        reference_date=request.reference_date or date.today(),
    )
    
    return _convert_matrix_result(result)


@router.post("/generate/mock", response_model=TrainingMatrixResponse)
def generate_mock_matrix(
    num_users: int = Query(default=10, ge=1, le=100, description="Number of users"),
    num_skills: int = Query(default=5, ge=1, le=20, description="Number of skills"),
) -> TrainingMatrixResponse:
    """
    Generate a mock training matrix for testing/demo purposes.
    """
    from uuid import uuid4
    from datetime import timedelta
    import random
    
    today = date.today()
    
    # Generate mock users
    departments = ["Production", "Quality", "Engineering", "Maintenance"]
    roles = ["Operator", "Team Lead", "Supervisor", "Engineer"]
    users = [
        {
            "id": uuid4(),
            "name": f"User {i+1}",
            "email": f"user{i+1}@example.com",
            "department": random.choice(departments),
            "role": random.choice(roles),
        }
        for i in range(num_users)
    ]
    
    # Generate mock skills
    skill_categories = ["technical", "safety", "quality", "leadership"]
    skills = [
        {
            "id": i + 1,
            "name": f"Skill {i+1}",
            "code": f"SKL-{i+1:03d}",
            "skill_category": random.choice(skill_categories),
            "proficiency_levels": ["Awareness", "Basic", "Proficient", "Expert"],
            "is_safety_critical": random.random() < 0.3,
            "is_quality_critical": random.random() < 0.4,
            "requires_recertification": True,
            "recertification_hours": random.randint(2, 8),
        }
        for i in range(num_skills)
    ]
    
    # Generate mock user skills
    statuses = ["certified", "in_training", "expired", "not_certified"]
    user_skills = []
    for user in users:
        # Each user has a random subset of skills
        for skill in random.sample(skills, k=random.randint(1, len(skills))):
            status = random.choices(statuses, weights=[0.6, 0.15, 0.1, 0.15])[0]
            exp_days = random.randint(-30, 365) if status == "certified" else None
            user_skills.append({
                "user_id": user["id"],
                "skill_id": skill["id"],
                "proficiency_level": random.randint(0, 3),
                "certification_status": status,
                "expiration_date": today + timedelta(days=exp_days) if exp_days else None,
            })
    
    service = get_service()
    result = service.generate_matrix(
        users=users,
        skills=skills,
        user_skills=user_skills,
        skill_requirements=[],
        reference_date=today,
    )
    
    return _convert_matrix_result(result)


# ------------------------------------------------------------------------------
# Gap Analysis
# ------------------------------------------------------------------------------

@router.post("/gaps/analyze", response_model=GapAnalysisResponse)
def analyze_gaps(
    request: GapAnalysisRequest | None = None,
) -> GapAnalysisResponse:
    """
    Analyze skill gaps for users based on station requirements.
    
    A gap exists when:
    - User is assigned to a station that requires a skill they don't have
    - User's proficiency level is below the required minimum
    - User's certification has expired
    """
    if request is None:
        request = GapAnalysisRequest()
    
    service = get_service()
    
    # Convert str keys to UUID keys for user_stations
    user_stations_uuid: dict[UUID, list[dict[str, Any]]] | None = None
    if request.user_stations:
        user_stations_uuid = {UUID(k): v for k, v in request.user_stations.items()}
    
    result = service.analyze_gaps(
        users=request.users,
        skills=request.skills,
        user_skills=request.user_skills,
        skill_requirements=request.skill_requirements,
        user_stations=user_stations_uuid,
    )
    
    return _convert_gap_result(result, request.station_id, request.severity)


@router.get("/gaps/summary")
def get_gap_summary() -> dict[str, Any]:
    """
    Get a summary of gaps across the organization.
    """
    return {
        "message": "Use POST /gaps/analyze with user and skill data to get gap analysis",
        "severity_levels": [s.value for s in GapSeverity],
        "description": {
            "critical": "Safety-critical skill gap - requires immediate action",
            "high": "Quality-critical skill gap - requires priority attention",
            "medium": "Proficiency below requirement",
            "low": "Optional skill improvement opportunity",
        },
    }


# ------------------------------------------------------------------------------
# Expiration Alerts
# ------------------------------------------------------------------------------

@router.post("/expirations/check", response_model=ExpirationAlertResponse)
def check_expirations(
    request: ExpirationCheckRequest | None = None,
) -> ExpirationAlertResponse:
    """
    Check for expiring certifications.
    
    Returns certifications that are:
    - Already expired
    - Expiring within the specified window
    - Categorized by urgency level
    
    Also suggests recertification tasks to be created.
    """
    if request is None:
        request = ExpirationCheckRequest()
    
    service = get_service()
    
    result = service.check_expiring_certifications(
        user_skills=request.user_skills,
        skills=request.skills,
        users=request.users,
        reference_date=request.reference_date or date.today(),
        days_ahead=request.days_ahead,
    )
    
    return _convert_expiration_result(result, request.urgency)


@router.get("/expirations/thresholds", response_model=ThresholdsResponse)
def get_expiration_thresholds() -> ThresholdsResponse:
    """
    Get the current expiration alert thresholds.
    """
    service = get_service()
    thresholds = service.get_expiration_thresholds()
    return ThresholdsResponse(thresholds=thresholds)


@router.put("/expirations/thresholds")
def update_expiration_threshold(
    request: ThresholdUpdateRequest,
) -> ThresholdsResponse:
    """
    Update an expiration alert threshold.
    """
    service = get_service()
    
    urgency_map = {
        "critical": ExpirationUrgency.CRITICAL,
        "urgent": ExpirationUrgency.URGENT,
        "warning": ExpirationUrgency.WARNING,
        "upcoming": ExpirationUrgency.UPCOMING,
    }
    
    if request.urgency not in urgency_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid urgency: {request.urgency}. Must be one of: critical, urgent, warning, upcoming"
        )
    
    service.set_expiration_threshold(urgency_map[request.urgency], request.days)
    return ThresholdsResponse(thresholds=service.get_expiration_thresholds())


# ------------------------------------------------------------------------------
# User Summary
# ------------------------------------------------------------------------------

@router.post("/users/{user_id}/summary", response_model=UserSkillSummaryResponse)
def get_user_skill_summary(
    user_id: UUID,
    request: UserSkillSummaryRequest | None = None,
) -> UserSkillSummaryResponse:
    """
    Get a skill summary for a specific user.
    """
    if request is None:
        request = UserSkillSummaryRequest()
    
    service = get_service()
    
    result = service.get_user_skill_summary(
        user_id=user_id,
        user_skills=request.user_skills,
        skills=request.skills,
        skill_requirements=request.skill_requirements,
        user_stations=request.user_stations,
        reference_date=request.reference_date or date.today(),
    )
    
    return UserSkillSummaryResponse(**result)


# ------------------------------------------------------------------------------
# Station Readiness
# ------------------------------------------------------------------------------

@router.post("/stations/{station_id}/readiness", response_model=StationReadinessResponse)
def get_station_readiness(
    station_id: int,
    request: StationReadinessRequest | None = None,
) -> StationReadinessResponse:
    """
    Get readiness report for a station.
    
    Shows how well-prepared assigned users are to work at the station,
    based on the skill requirements defined for that station.
    """
    if request is None:
        request = StationReadinessRequest()
    
    service = get_service()
    
    # Convert string IDs to UUIDs
    user_ids = [UUID(uid) for uid in request.assigned_users]
    
    result = service.get_station_readiness(
        station_id=station_id,
        station_name=request.station_name,
        users=request.users,
        skills=request.skills,
        user_skills=request.user_skills,
        skill_requirements=request.skill_requirements,
        assigned_users=user_ids,
    )
    
    return StationReadinessResponse(**result)


# ------------------------------------------------------------------------------
# Reference Data
# ------------------------------------------------------------------------------

@router.get("/severities")
def get_gap_severities() -> list[dict[str, str]]:
    """Get all available gap severity levels."""
    return [
        {"value": s.value, "name": s.name}
        for s in GapSeverity
    ]


@router.get("/urgencies")
def get_urgency_levels() -> list[dict[str, str]]:
    """Get all available expiration urgency levels."""
    return [
        {"value": u.value, "name": u.name}
        for u in ExpirationUrgency
    ]


# ==============================================================================
# Helper Functions
# ==============================================================================

def _convert_matrix_result(result: TrainingMatrixResult) -> TrainingMatrixResponse:
    """Convert service result to API response."""
    from datetime import datetime, timezone
    
    rows = []
    for row in result.rows:
        skills = []
        for cell in row.skills:
            skills.append(SkillCellSchema(
                skill_id=cell.skill_id,
                skill_code=cell.skill_code,
                skill_name=cell.skill_name,
                proficiency_level=cell.proficiency_level,
                proficiency_name=cell.proficiency_name,
                certification_status=cell.certification_status,
                expiration_date=cell.expiration_date,
                days_until_expiration=cell.days_until_expiration,
                is_required=cell.is_required,
                minimum_required_level=cell.minimum_required_level,
                has_gap=cell.has_gap,
                gap_severity=cell.gap_severity.value if cell.gap_severity else None,
            ))
        
        rows.append(MatrixRowSchema(
            user_id=str(row.user_id),
            user_name=row.user_name,
            user_email=row.user_email,
            department=row.department,
            role=row.role,
            assigned_stations=row.assigned_stations,
            skills=skills,
            total_gaps=row.total_gaps,
            critical_gaps=row.critical_gaps,
            expiring_soon=row.expiring_soon,
        ))
    
    skill_columns = [
        SkillColumnSchema(
            skill_id=col["skill_id"],
            skill_code=col["skill_code"],
            skill_name=col["skill_name"],
            skill_category=col.get("skill_category"),
            is_safety_critical=col.get("is_safety_critical", False),
            is_quality_critical=col.get("is_quality_critical", False),
            proficiency_levels=col.get("proficiency_levels", []),
        )
        for col in result.skill_columns
    ]
    
    return TrainingMatrixResponse(
        rows=rows,
        skill_columns=skill_columns,
        total_users=result.total_users,
        total_skills=result.total_skills,
        total_gaps=result.total_gaps,
        critical_gaps=result.critical_gaps,
        expiring_certifications=result.expiring_certifications,
        generated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    )


def _convert_gap_result(
    result: GapAnalysisResult,
    station_id: int | None = None,
    severity: str | None = None,
) -> GapAnalysisResponse:
    """Convert gap analysis result to API response."""
    from datetime import datetime, timezone
    
    gaps = result.gaps
    
    # Apply filters
    if station_id is not None:
        gaps = [g for g in gaps if g.station_id == station_id]
    if severity:
        gaps = [g for g in gaps if g.severity.value == severity]
    
    gap_schemas = [
        SkillGapSchema(
            user_id=str(g.user_id),
            user_name=g.user_name,
            skill_id=g.skill_id,
            skill_name=g.skill_name,
            skill_code=g.skill_code,
            station_id=g.station_id,
            station_name=g.station_name,
            required_level=g.required_level,
            current_level=g.current_level,
            certification_status=g.certification_status,
            severity=g.severity.value,
            is_safety_critical=g.is_safety_critical,
            is_quality_critical=g.is_quality_critical,
            recommended_action=g.recommended_action,
        )
        for g in gaps
    ]
    
    return GapAnalysisResponse(
        gaps=gap_schemas,
        total_gaps=len(gap_schemas),
        by_severity=result.by_severity,
        by_skill=result.by_skill,
        by_station=result.by_station,
        analyzed_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    )


def _convert_expiration_result(
    result: ExpirationAlertResult,
    urgency: str | None = None,
) -> ExpirationAlertResponse:
    """Convert expiration alert result to API response."""
    from datetime import datetime, timezone
    
    alerts = result.alerts
    
    # Apply filter
    if urgency:
        alerts = [a for a in alerts if a.urgency.value == urgency]
    
    alert_schemas = [
        ExpiringCertificationSchema(
            user_id=str(a.user_id),
            user_name=a.user_name,
            skill_id=a.skill_id,
            skill_name=a.skill_name,
            skill_code=a.skill_code,
            certification_status=a.certification_status,
            expiration_date=a.expiration_date,
            days_until_expiration=a.days_until_expiration,
            urgency=a.urgency.value,
            requires_recertification=a.requires_recertification,
            recertification_hours=a.recertification_hours,
        )
        for a in alerts
    ]
    
    task_schemas = [
        RecertificationTaskSchema(
            user_id=str(t.user_id),
            user_name=t.user_name,
            skill_id=t.skill_id,
            skill_name=t.skill_name,
            title=t.title,
            description=t.description,
            due_date=t.due_date,
            priority=t.priority,
            is_safety_critical=t.is_safety_critical,
        )
        for t in result.suggested_tasks
    ]
    
    return ExpirationAlertResponse(
        alerts=alert_schemas,
        total_alerts=len(alert_schemas),
        by_urgency=result.by_urgency,
        suggested_tasks=task_schemas,
        checked_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    )
