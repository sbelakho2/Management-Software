"""
Training Matrix Gap Analysis Service for Sensei OS.

Implements:
- Matrix display: Users (rows) × Skills (columns) with proficiency/status
- Gap analysis: Identify users missing required skills for their stations
- Expiration alerts: Flag certifications expiring within configurable days
- Auto-generate recertification task suggestions
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GapSeverity(str, Enum):
    """Severity of a skill gap."""
    
    CRITICAL = "critical"   # Safety/quality critical skill missing
    HIGH = "high"           # Mandatory skill missing
    MEDIUM = "medium"       # Below required proficiency
    LOW = "low"             # Nice-to-have skill missing


class ExpirationUrgency(str, Enum):
    """Urgency level for expiring certifications."""
    
    EXPIRED = "expired"          # Already expired
    CRITICAL = "critical"        # Expires within 7 days
    URGENT = "urgent"            # Expires within 30 days
    WARNING = "warning"          # Expires within 60 days
    UPCOMING = "upcoming"        # Expires within 90 days


class CertificationStatusValue(str, Enum):
    """Certification status values (matching model enum)."""
    
    NOT_CERTIFIED = "not_certified"
    IN_TRAINING = "in_training"
    CERTIFIED = "certified"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass
class SkillCellData:
    """
    Data for a single cell in the training matrix.
    
    Represents a user's status for a specific skill.
    """
    skill_id: int
    skill_name: str
    skill_code: str
    proficiency_level: int
    proficiency_name: str
    certification_status: str
    certified_date: date | None = None
    expiration_date: date | None = None
    days_until_expiration: int | None = None
    is_required: bool = False
    required_level: int = 0
    minimum_required_level: int | None = None
    has_gap: bool = False
    gap_severity: GapSeverity | None = None
    expiration_urgency: ExpirationUrgency | None = None


@dataclass
class MatrixRow:
    """
    A row in the training matrix (represents one user).
    """
    user_id: UUID
    user_name: str
    user_email: str
    department: str | None = None
    role: str | None = None
    assigned_stations: list[str] = field(default_factory=list)
    skills: list[SkillCellData] = field(default_factory=list)
    total_gaps: int = 0
    critical_gaps: int = 0
    expiring_soon: int = 0


@dataclass
class SkillGap:
    """
    Represents a detected skill gap for a user.
    """
    user_id: UUID
    user_name: str
    skill_id: int
    skill_name: str
    skill_code: str
    required_level: int
    current_level: int
    certification_status: str
    severity: GapSeverity
    station_id: int | None = None
    station_name: str | None = None
    is_safety_critical: bool = False
    is_quality_critical: bool = False
    recommended_action: str = ""


@dataclass
class ExpiringCertification:
    """
    Represents an expiring or expired certification.
    """
    user_id: UUID
    user_name: str
    skill_id: int
    skill_name: str
    skill_code: str
    certification_status: str
    expiration_date: date
    days_until_expiration: int
    urgency: ExpirationUrgency
    requires_recertification: bool = True
    recertification_hours: float = 0.0


@dataclass
class RecertificationTask:
    """
    Suggested recertification task to be created.
    """
    user_id: UUID
    user_name: str
    skill_id: int
    skill_name: str
    title: str
    description: str
    due_date: date
    priority: str
    is_safety_critical: bool = False


@dataclass
class TrainingMatrixResult:
    """
    Complete training matrix result.
    """
    rows: list[MatrixRow]
    skill_columns: list[dict[str, Any]]
    total_users: int
    total_skills: int
    total_gaps: int
    critical_gaps: int
    expiring_certifications: int
    generated_at: datetime = field(default_factory=_utcnow)


@dataclass
class GapAnalysisResult:
    """
    Result of gap analysis.
    """
    gaps: list[SkillGap]
    total_gaps: int
    by_severity: dict[str, int]
    by_skill: dict[str, int]
    by_user: dict[str, int]
    by_station: dict[str, int]
    users_with_gaps: int
    analyzed_at: datetime = field(default_factory=_utcnow)


@dataclass
class ExpirationAlertResult:
    """
    Result of expiration alert check.
    """
    alerts: list[ExpiringCertification]
    total_alerts: int
    by_urgency: dict[str, int]
    by_skill: dict[str, int]
    users_affected: int
    suggested_tasks: list[RecertificationTask]
    checked_at: datetime = field(default_factory=_utcnow)


class TrainingMatrixService(PersistentServiceMixin):
    """
    Service for training matrix analysis and gap detection.
    
    Provides methods to:
    - Generate training matrix views
    - Detect skill gaps
    - Alert on expiring certifications
    - Generate recertification task suggestions
    """

    SERVICE_NAME = "training_matrix"
    
    # Default expiration thresholds (days)
    EXPIRATION_THRESHOLDS = {
        ExpirationUrgency.CRITICAL: 7,
        ExpirationUrgency.URGENT: 30,
        ExpirationUrgency.WARNING: 60,
        ExpirationUrgency.UPCOMING: 90,
    }
    
    # Default recertification lead time (days before expiration)
    RECERTIFICATION_LEAD_DAYS = 30

    _DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")
    
    def __init__(self) -> None:
        """Initialize the training matrix service."""
        self._custom_thresholds: dict[ExpirationUrgency, int] = {}
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        thresholds = await self.load_state(self._DEFAULT_TENANT_ID, "expiration_thresholds") or {}
        self._custom_thresholds = {
            ExpirationUrgency(key): int(value) for key, value in thresholds.items()
        }
        self._state_loaded = True

    async def persist_all(self) -> None:
        thresholds = {urgency.value: days for urgency, days in self._custom_thresholds.items()}
        await self.save_state(self._DEFAULT_TENANT_ID, "expiration_thresholds", thresholds)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()
    
    def set_expiration_threshold(
        self,
        urgency: ExpirationUrgency,
        days: int,
    ) -> None:
        """Set custom expiration threshold."""
        self._custom_thresholds[urgency] = days

    async def set_expiration_threshold_async(
        self,
        urgency: ExpirationUrgency,
        days: int,
    ) -> None:
        await self._ensure_loaded()
        self.set_expiration_threshold(urgency, days)
        await self.persist_all()
    
    def get_expiration_thresholds(self) -> dict[str, int]:
        """Get current expiration thresholds."""
        result = {k.value: v for k, v in self.EXPIRATION_THRESHOLDS.items()}
        for urgency, days in self._custom_thresholds.items():
            result[urgency.value] = days
        return result

    async def get_expiration_thresholds_async(self) -> dict[str, int]:
        await self._ensure_loaded()
        return self.get_expiration_thresholds()
    
    def _get_threshold(self, urgency: ExpirationUrgency) -> int:
        """Get threshold for an urgency level."""
        return self._custom_thresholds.get(
            urgency,
            self.EXPIRATION_THRESHOLDS.get(urgency, 30)
        )
    
    def generate_matrix(
        self,
        users: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        user_skills: list[dict[str, Any]],
        skill_requirements: list[dict[str, Any]],
        user_stations: dict[UUID, list[dict[str, Any]]] | None = None,
        reference_date: date | None = None,
    ) -> TrainingMatrixResult:
        """
        Generate a training matrix.
        
        Args:
            users: List of user dicts with id, name, email, department, role
            skills: List of skill dicts with id, name, code, proficiency_levels
            user_skills: List of user skill records linking users to skills
            skill_requirements: List of skill requirements for stations/products
            user_stations: Optional mapping of user_id to their assigned stations
            reference_date: Reference date for expiration checks (default: today)
        
        Returns:
            TrainingMatrixResult with rows and skill columns
        """
        ref_date = reference_date or date.today()
        
        # Build lookup maps
        skill_map = {s["id"]: s for s in skills}
        user_skill_map: dict[tuple[UUID, int], dict] = {}
        for us in user_skills:
            key = (us["user_id"], us["skill_id"])
            user_skill_map[key] = us
        
        # Build station requirement map: station_id -> [skill_id, ...]
        station_skill_reqs: dict[int, list[dict]] = {}
        for req in skill_requirements:
            if req.get("station_id"):
                station_id = req["station_id"]
                if station_id not in station_skill_reqs:
                    station_skill_reqs[station_id] = []
                station_skill_reqs[station_id].append(req)
        
        # Build skill column metadata
        skill_columns = [
            {
                "skill_id": s["id"],
                "skill_name": s["name"],
                "skill_code": s["code"],
                "skill_category": s.get("skill_category", "technical"),
                "is_safety_critical": s.get("is_safety_critical", False),
                "is_quality_critical": s.get("is_quality_critical", False),
                "proficiency_levels": s.get("proficiency_levels", []),
            }
            for s in skills
        ]
        
        rows: list[MatrixRow] = []
        total_gaps = 0
        total_critical = 0
        total_expiring = 0
        
        for user in users:
            user_id = user["id"]
            user_stations_list = user_stations.get(user_id, []) if user_stations else []
            
            # Get required skills for user's stations
            required_skills: dict[int, dict] = {}  # skill_id -> requirement
            for station in user_stations_list:
                station_id = station.get("id") or station.get("station_id")
                if station_id in station_skill_reqs:
                    for req in station_skill_reqs[station_id]:
                        skill_id = req["skill_id"]
                        # Keep the highest requirement
                        if skill_id not in required_skills:
                            required_skills[skill_id] = req
                        elif req["minimum_proficiency_level"] > required_skills[skill_id]["minimum_proficiency_level"]:
                            required_skills[skill_id] = req
            
            # Build skill cells
            skill_cells: list[SkillCellData] = []
            row_gaps = 0
            row_critical = 0
            row_expiring = 0
            
            for skill in skills:
                skill_id = skill["id"]
                user_skill = user_skill_map.get((user_id, skill_id))
                
                # Get proficiency info
                proficiency_level = 0
                proficiency_name = "None"
                cert_status = CertificationStatusValue.NOT_CERTIFIED.value
                certified_date = None
                expiration_date = None
                
                if user_skill:
                    proficiency_level = user_skill.get("proficiency_level", 0)
                    proficiency_levels = skill.get("proficiency_levels", [])
                    if 0 <= proficiency_level < len(proficiency_levels):
                        proficiency_name = proficiency_levels[proficiency_level]
                    cert_status = user_skill.get("certification_status", cert_status)
                    certified_date = user_skill.get("certified_date")
                    expiration_date = user_skill.get("expiration_date")
                
                # Check if skill is required
                is_required = skill_id in required_skills
                required_level = required_skills.get(skill_id, {}).get(
                    "minimum_proficiency_level", 0
                )
                
                # Gap detection
                has_gap = False
                gap_severity = None
                
                if is_required:
                    if cert_status in (
                        CertificationStatusValue.NOT_CERTIFIED.value,
                        CertificationStatusValue.EXPIRED.value,
                        CertificationStatusValue.SUSPENDED.value,
                        CertificationStatusValue.REVOKED.value,
                    ):
                        has_gap = True
                        if skill.get("is_safety_critical") or skill.get("is_quality_critical"):
                            gap_severity = GapSeverity.CRITICAL
                            row_critical += 1
                        else:
                            gap_severity = GapSeverity.HIGH
                        row_gaps += 1
                    elif proficiency_level < required_level:
                        has_gap = True
                        gap_severity = GapSeverity.MEDIUM
                        row_gaps += 1
                
                # Expiration check
                expiration_urgency = None
                days_until_expiration = None
                if expiration_date and cert_status == CertificationStatusValue.CERTIFIED.value:
                    days_until_expiration = (expiration_date - ref_date).days
                    if days_until_expiration < 0:
                        expiration_urgency = ExpirationUrgency.EXPIRED
                        row_expiring += 1
                    elif days_until_expiration <= self._get_threshold(ExpirationUrgency.CRITICAL):
                        expiration_urgency = ExpirationUrgency.CRITICAL
                        row_expiring += 1
                    elif days_until_expiration <= self._get_threshold(ExpirationUrgency.URGENT):
                        expiration_urgency = ExpirationUrgency.URGENT
                        row_expiring += 1
                    elif days_until_expiration <= self._get_threshold(ExpirationUrgency.WARNING):
                        expiration_urgency = ExpirationUrgency.WARNING
                    elif days_until_expiration <= self._get_threshold(ExpirationUrgency.UPCOMING):
                        expiration_urgency = ExpirationUrgency.UPCOMING
                
                cell = SkillCellData(
                    skill_id=skill_id,
                    skill_name=skill["name"],
                    skill_code=skill["code"],
                    proficiency_level=proficiency_level,
                    proficiency_name=proficiency_name,
                    certification_status=cert_status,
                    certified_date=certified_date,
                    expiration_date=expiration_date,
                    days_until_expiration=days_until_expiration,
                    is_required=is_required,
                    required_level=required_level,
                    minimum_required_level=required_level if is_required else None,
                    has_gap=has_gap,
                    gap_severity=gap_severity,
                    expiration_urgency=expiration_urgency,
                )
                skill_cells.append(cell)
            
            row = MatrixRow(
                user_id=user_id,
                user_name=user.get("name", "Unknown"),
                user_email=user.get("email", ""),
                department=user.get("department"),
                role=user.get("role"),
                assigned_stations=[
                    s.get("name", f"Station {s.get('id')}") for s in user_stations_list
                ],
                skills=skill_cells,
                total_gaps=row_gaps,
                critical_gaps=row_critical,
                expiring_soon=row_expiring,
            )
            rows.append(row)
            
            total_gaps += row_gaps
            total_critical += row_critical
            total_expiring += row_expiring
        
        return TrainingMatrixResult(
            rows=rows,
            skill_columns=skill_columns,
            total_users=len(users),
            total_skills=len(skills),
            total_gaps=total_gaps,
            critical_gaps=total_critical,
            expiring_certifications=total_expiring,
        )

    def generate_mock_matrix(
        self,
        num_users: int = 10,
        num_skills: int = 5,
    ) -> TrainingMatrixResult:
        """Generate a mock training matrix for testing."""
        num_users = max(1, min(100, num_users))
        num_skills = max(1, min(50, num_skills))

        skill_columns = [
            {
                "skill_id": idx + 1,
                "skill_code": f"SK-{idx + 1:03d}",
                "skill_name": f"Skill {idx + 1}",
                "skill_category": "General",
                "is_safety_critical": idx % 3 == 0,
                "is_quality_critical": idx % 4 == 0,
                "proficiency_levels": ["Novice", "Qualified", "Expert"],
            }
            for idx in range(num_skills)
        ]

        rows: list[MatrixRow] = []
        for u in range(num_users):
            skills: list[SkillCellData] = []
            for s in range(num_skills):
                skills.append(
                    SkillCellData(
                        skill_id=skill_columns[s]["skill_id"],
                        skill_name=skill_columns[s]["skill_name"],
                        skill_code=skill_columns[s]["skill_code"],
                        proficiency_level=2,
                        proficiency_name="Qualified",
                        certification_status=CertificationStatusValue.CERTIFIED.value,
                        certified_date=date.today(),
                        expiration_date=None,
                        days_until_expiration=None,
                        is_required=True,
                        required_level=2,
                        minimum_required_level=2,
                        has_gap=False,
                        gap_severity=None,
                        expiration_urgency=None,
                    )
                )

            rows.append(
                MatrixRow(
                    user_id=UUID(int=u + 1),
                    user_name=f"User {u + 1}",
                    user_email=f"user{u + 1}@example.com",
                    department="Operations",
                    role="Operator",
                    assigned_stations=["Station A"],
                    skills=skills,
                    total_gaps=0,
                    critical_gaps=0,
                    expiring_soon=0,
                )
            )

        return TrainingMatrixResult(
            rows=rows,
            skill_columns=skill_columns,
            total_users=num_users,
            total_skills=num_skills,
            total_gaps=0,
            critical_gaps=0,
            expiring_certifications=0,
        )
    def analyze_gaps(
        self,
        users: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        user_skills: list[dict[str, Any]],
        skill_requirements: list[dict[str, Any]],
        user_stations: dict[UUID, list[dict[str, Any]]] | None = None,
        include_non_mandatory: bool = False,
    ) -> GapAnalysisResult:
        """
        Analyze skill gaps for users based on their station assignments.
        
        Args:
            users: List of user dicts
            skills: List of skill dicts
            user_skills: List of user skill records
            skill_requirements: List of skill requirements
            user_stations: Mapping of user_id to their assigned stations
            include_non_mandatory: Whether to include non-mandatory skill gaps
        
        Returns:
            GapAnalysisResult with detected gaps
        """
        # Build lookup maps
        skill_map = {s["id"]: s for s in skills}
        user_map = {u["id"]: u for u in users}
        user_skill_map: dict[tuple[UUID, int], dict] = {}
        for us in user_skills:
            key = (us["user_id"], us["skill_id"])
            user_skill_map[key] = us
        
        # Build station requirement map
        station_skill_reqs: dict[int, list[dict]] = {}
        for req in skill_requirements:
            if req.get("station_id"):
                station_id = req["station_id"]
                if station_id not in station_skill_reqs:
                    station_skill_reqs[station_id] = []
                station_skill_reqs[station_id].append(req)
        
        gaps: list[SkillGap] = []
        by_severity: dict[str, int] = {s.value: 0 for s in GapSeverity}
        by_skill: dict[str, int] = {}
        by_user: dict[str, int] = {}
        by_station: dict[str, int] = {}
        users_with_gaps_set: set[UUID] = set()
        
        for user in users:
            user_id = user["id"]
            user_name = user.get("name", "Unknown")
            user_stations_list = user_stations.get(user_id, []) if user_stations else []
            
            for station in user_stations_list:
                station_id = station.get("id") or station.get("station_id")
                station_name = station.get("name", f"Station {station_id}")
                
                if station_id not in station_skill_reqs:
                    continue
                
                for req in station_skill_reqs[station_id]:
                    if not include_non_mandatory and not req.get("is_mandatory", True):
                        continue
                    
                    skill_id = req["skill_id"]
                    skill = skill_map.get(skill_id)
                    if not skill:
                        continue
                    
                    required_level = req.get("minimum_proficiency_level", 0)
                    user_skill = user_skill_map.get((user_id, skill_id))
                    
                    current_level = 0
                    cert_status = CertificationStatusValue.NOT_CERTIFIED.value
                    
                    if user_skill:
                        current_level = user_skill.get("proficiency_level", 0)
                        cert_status = user_skill.get(
                            "certification_status",
                            CertificationStatusValue.NOT_CERTIFIED.value
                        )
                    
                    # Check for gap
                    has_gap = False
                    severity = GapSeverity.LOW
                    recommended_action = ""
                    
                    if cert_status in (
                        CertificationStatusValue.NOT_CERTIFIED.value,
                        CertificationStatusValue.EXPIRED.value,
                        CertificationStatusValue.SUSPENDED.value,
                        CertificationStatusValue.REVOKED.value,
                    ):
                        has_gap = True
                        if skill.get("is_safety_critical"):
                            severity = GapSeverity.CRITICAL
                            recommended_action = "IMMEDIATE: Enroll in safety training - do not assign to station"
                        elif skill.get("is_quality_critical"):
                            severity = GapSeverity.CRITICAL
                            recommended_action = "URGENT: Enroll in quality certification training"
                        elif req.get("is_mandatory", True):
                            severity = GapSeverity.HIGH
                            recommended_action = f"Enroll in {skill['name']} training"
                        else:
                            severity = GapSeverity.LOW
                            recommended_action = f"Consider {skill['name']} training when available"
                    elif current_level < required_level:
                        has_gap = True
                        severity = GapSeverity.MEDIUM
                        proficiency_levels = skill.get("proficiency_levels", [])
                        required_name = (
                            proficiency_levels[required_level]
                            if required_level < len(proficiency_levels)
                            else f"Level {required_level}"
                        )
                        recommended_action = f"Advance to {required_name} proficiency"
                    
                    if has_gap:
                        gap = SkillGap(
                            user_id=user_id,
                            user_name=user_name,
                            skill_id=skill_id,
                            skill_name=skill["name"],
                            skill_code=skill["code"],
                            station_id=station_id,
                            station_name=station_name,
                            required_level=required_level,
                            current_level=current_level,
                            certification_status=cert_status,
                            severity=severity,
                            is_safety_critical=skill.get("is_safety_critical", False),
                            is_quality_critical=skill.get("is_quality_critical", False),
                            recommended_action=recommended_action,
                        )
                        gaps.append(gap)
                        
                        # Update counts
                        by_severity[severity.value] += 1
                        by_skill[skill["code"]] = by_skill.get(skill["code"], 0) + 1
                        by_user[str(user_id)] = by_user.get(str(user_id), 0) + 1
                        by_station[station_name] = by_station.get(station_name, 0) + 1
                        users_with_gaps_set.add(user_id)
        
        return GapAnalysisResult(
            gaps=gaps,
            total_gaps=len(gaps),
            by_severity=by_severity,
            by_skill=by_skill,
            by_user=by_user,
            by_station=by_station,
            users_with_gaps=len(users_with_gaps_set),
        )
    
    def check_expiring_certifications(
        self,
        user_skills: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        users: list[dict[str, Any]],
        reference_date: date | None = None,
        days_ahead: int = 90,
    ) -> ExpirationAlertResult:
        """
        Check for expiring certifications.
        
        Args:
            user_skills: List of user skill records
            skills: List of skill dicts
            users: List of user dicts
            reference_date: Reference date (default: today)
            days_ahead: Days to look ahead for expiration
        
        Returns:
            ExpirationAlertResult with alerts and suggested tasks
        """
        ref_date = reference_date or date.today()
        cutoff_date = ref_date + timedelta(days=days_ahead)
        
        skill_map = {s["id"]: s for s in skills}
        user_map = {u["id"]: u for u in users}
        
        alerts: list[ExpiringCertification] = []
        suggested_tasks: list[RecertificationTask] = []
        by_urgency: dict[str, int] = {u.value: 0 for u in ExpirationUrgency}
        by_skill: dict[str, int] = {}
        users_affected_set: set[UUID] = set()
        
        for us in user_skills:
            expiration_date = us.get("expiration_date")
            cert_status = us.get("certification_status")
            
            # Only check certified skills
            if cert_status != CertificationStatusValue.CERTIFIED.value:
                continue
            
            if not expiration_date:
                continue
            
            # Check if within range
            if expiration_date > cutoff_date:
                continue
            
            skill_id = us["skill_id"]
            user_id = us["user_id"]
            skill = skill_map.get(skill_id, {})
            user = user_map.get(user_id, {})
            
            days_until = (expiration_date - ref_date).days
            
            # Determine urgency
            if days_until < 0:
                urgency = ExpirationUrgency.EXPIRED
            elif days_until <= self._get_threshold(ExpirationUrgency.CRITICAL):
                urgency = ExpirationUrgency.CRITICAL
            elif days_until <= self._get_threshold(ExpirationUrgency.URGENT):
                urgency = ExpirationUrgency.URGENT
            elif days_until <= self._get_threshold(ExpirationUrgency.WARNING):
                urgency = ExpirationUrgency.WARNING
            else:
                urgency = ExpirationUrgency.UPCOMING
            
            requires_recert = skill.get("requires_recertification", True)
            recert_hours = float(skill.get("recertification_hours", 2.0))
            
            alert = ExpiringCertification(
                user_id=user_id,
                user_name=user.get("name", "Unknown"),
                skill_id=skill_id,
                skill_name=skill.get("name", "Unknown"),
                skill_code=skill.get("code", ""),
                certification_status=cert_status,
                expiration_date=expiration_date,
                days_until_expiration=days_until,
                urgency=urgency,
                requires_recertification=requires_recert,
                recertification_hours=recert_hours,
            )
            alerts.append(alert)
            
            by_urgency[urgency.value] += 1
            skill_code = skill.get("code", str(skill_id))
            by_skill[skill_code] = by_skill.get(skill_code, 0) + 1
            users_affected_set.add(user_id)
            
            # Generate recertification task suggestion
            if requires_recert and days_until <= self.RECERTIFICATION_LEAD_DAYS:
                priority = "urgent" if urgency in (
                    ExpirationUrgency.EXPIRED,
                    ExpirationUrgency.CRITICAL
                ) else "high" if urgency == ExpirationUrgency.URGENT else "normal"
                
                due_date = expiration_date if days_until > 0 else ref_date + timedelta(days=7)
                
                task = RecertificationTask(
                    user_id=user_id,
                    user_name=user.get("name", "Unknown"),
                    skill_id=skill_id,
                    skill_name=skill.get("name", "Unknown"),
                    title=f"Recertification: {skill.get('name', 'Skill')} for {user.get('name', 'User')}",
                    description=(
                        f"Certification for {skill.get('name')} expires on {expiration_date}. "
                        f"Complete recertification training ({recert_hours} hours)."
                    ),
                    due_date=due_date,
                    priority=priority,
                    is_safety_critical=skill.get("is_safety_critical", False),
                )
                suggested_tasks.append(task)
        
        return ExpirationAlertResult(
            alerts=alerts,
            total_alerts=len(alerts),
            by_urgency=by_urgency,
            by_skill=by_skill,
            users_affected=len(users_affected_set),
            suggested_tasks=suggested_tasks,
        )
    
    def get_user_skill_summary(
        self,
        user_id: UUID,
        user_skills: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        skill_requirements: list[dict[str, Any]],
        user_stations: list[dict[str, Any]] | None = None,
        reference_date: date | None = None,
    ) -> dict[str, Any]:
        """
        Get a skill summary for a specific user.
        
        Args:
            user_id: User ID
            user_skills: List of user skill records
            skills: List of skill dicts
            skill_requirements: List of skill requirements
            user_stations: List of stations assigned to user
            reference_date: Reference date for expiration checks
        
        Returns:
            Summary dict with user's skill status
        """
        ref_date = reference_date or date.today()
        
        skill_map = {s["id"]: s for s in skills}
        
        # Filter user skills for this user
        user_skill_records = [us for us in user_skills if us["user_id"] == user_id]
        user_skill_map = {us["skill_id"]: us for us in user_skill_records}
        
        # Get required skills for user's stations
        required_skill_ids: set[int] = set()
        if user_stations:
            station_ids = [
                s.get("id") or s.get("station_id") for s in user_stations
            ]
            for req in skill_requirements:
                if req.get("station_id") in station_ids:
                    required_skill_ids.add(req["skill_id"])
        
        # Count statistics
        total_skills = len(user_skill_records)
        certified_count = 0
        in_training_count = 0
        expired_count = 0
        not_certified_count = 0
        expiring_soon = 0
        gaps = 0
        
        skill_details: list[dict] = []
        
        for us in user_skill_records:
            skill_id = us["skill_id"]
            skill = skill_map.get(skill_id, {})
            cert_status = us.get("certification_status", "not_certified")
            expiration_date = us.get("expiration_date")
            
            if cert_status == CertificationStatusValue.CERTIFIED.value:
                certified_count += 1
            elif cert_status == CertificationStatusValue.IN_TRAINING.value:
                in_training_count += 1
            elif cert_status == CertificationStatusValue.EXPIRED.value:
                expired_count += 1
            else:
                not_certified_count += 1
            
            # Check expiration
            days_until = None
            if expiration_date and cert_status == CertificationStatusValue.CERTIFIED.value:
                days_until = (expiration_date - ref_date).days
                if days_until <= 30:
                    expiring_soon += 1
            
            # Check gap
            is_gap = (
                skill_id in required_skill_ids and
                cert_status not in (
                    CertificationStatusValue.CERTIFIED.value,
                    CertificationStatusValue.IN_TRAINING.value,
                )
            )
            if is_gap:
                gaps += 1
            
            skill_details.append({
                "skill_id": skill_id,
                "skill_name": skill.get("name", "Unknown"),
                "skill_code": skill.get("code", ""),
                "proficiency_level": us.get("proficiency_level", 0),
                "certification_status": cert_status,
                "certified_date": us.get("certified_date"),
                "expiration_date": expiration_date,
                "days_until_expiration": days_until,
                "is_required": skill_id in required_skill_ids,
                "has_gap": is_gap,
            })
        
        return {
            "user_id": str(user_id),
            "total_skills": total_skills,
            "certified": certified_count,
            "in_training": in_training_count,
            "expired": expired_count,
            "not_certified": not_certified_count,
            "expiring_soon": expiring_soon,
            "gaps": gaps,
            "required_skills_count": len(required_skill_ids),
            "skill_details": skill_details,
        }
    
    def get_station_readiness(
        self,
        station_id: int,
        station_name: str,
        users: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        user_skills: list[dict[str, Any]],
        skill_requirements: list[dict[str, Any]],
        assigned_users: list[UUID],
    ) -> dict[str, Any]:
        """
        Get skill readiness report for a station.
        
        Args:
            station_id: Station ID
            station_name: Station name
            users: List of user dicts
            skills: List of skill dicts
            user_skills: List of user skill records
            skill_requirements: List of skill requirements
            assigned_users: List of user IDs assigned to this station
        
        Returns:
            Station readiness report
        """
        skill_map = {s["id"]: s for s in skills}
        user_map = {u["id"]: u for u in users}
        
        # Get requirements for this station
        station_reqs = [
            req for req in skill_requirements
            if req.get("station_id") == station_id
        ]
        
        # Build user skill lookup
        user_skill_lookup: dict[tuple[UUID, int], dict] = {}
        for us in user_skills:
            key = (us["user_id"], us["skill_id"])
            user_skill_lookup[key] = us
        
        # Analyze each required skill
        required_skills_status: list[dict] = []
        total_qualified = 0
        total_gaps = 0
        critical_gaps = 0
        
        for req in station_reqs:
            skill_id = req["skill_id"]
            skill = skill_map.get(skill_id, {})
            required_level = req.get("minimum_proficiency_level", 0)
            is_mandatory = req.get("is_mandatory", True)
            
            qualified_users: list[dict] = []
            gap_users: list[dict] = []
            
            for user_id in assigned_users:
                user = user_map.get(user_id, {})
                user_skill = user_skill_lookup.get((user_id, skill_id))
                
                if user_skill:
                    cert_status = user_skill.get("certification_status")
                    level = user_skill.get("proficiency_level", 0)
                    
                    if (
                        cert_status == CertificationStatusValue.CERTIFIED.value
                        and level >= required_level
                    ):
                        qualified_users.append({
                            "user_id": str(user_id),
                            "user_name": user.get("name", "Unknown"),
                            "proficiency_level": level,
                        })
                    else:
                        gap_users.append({
                            "user_id": str(user_id),
                            "user_name": user.get("name", "Unknown"),
                            "certification_status": cert_status,
                            "current_level": level,
                        })
                else:
                    gap_users.append({
                        "user_id": str(user_id),
                        "user_name": user.get("name", "Unknown"),
                        "certification_status": CertificationStatusValue.NOT_CERTIFIED.value,
                        "current_level": 0,
                    })
            
            coverage = (
                len(qualified_users) / len(assigned_users) * 100
                if assigned_users else 0
            )
            
            skill_status = {
                "skill_id": skill_id,
                "skill_name": skill.get("name", "Unknown"),
                "skill_code": skill.get("code", ""),
                "required_level": required_level,
                "is_mandatory": is_mandatory,
                "is_quality_critical": skill.get("is_quality_critical", False),
                "qualified_count": len(qualified_users),
                "gap_count": len(gap_users),
                "coverage_percent": round(coverage, 1),
                "qualified_users": qualified_users,
                "gap_users": gap_users,
            }
            required_skills_status.append(skill_status)
            
            if qualified_users:
                total_qualified += 1
            if gap_users:
                total_gaps += 1
            if gap_users and is_mandatory:
                if skill.get("is_safety_critical") or skill.get("is_quality_critical"):
                    critical_gaps += 1
        
        overall_readiness = (
            total_qualified / len(station_reqs) * 100
            if station_reqs else 100
        )
        
        return {
            "station_id": station_id,
            "station_name": station_name,
            "total_assigned_users": len(assigned_users),
            "required_skills_count": len(station_reqs),
            "skills_with_qualified_users": total_qualified,
            "skills_with_gaps": total_gaps,
            "critical_skill_gaps": critical_gaps,
            "overall_readiness_percent": round(overall_readiness, 1),
            "required_skills": required_skills_status,
        }
