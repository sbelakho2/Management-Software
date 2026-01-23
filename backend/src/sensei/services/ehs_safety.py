"""
EHS / Safety Compliance Service.

Provides comprehensive Environment, Health, and Safety (EHS) management including:
- Incident & Near-Miss Management (record, classify, investigate, close)
- Risk Assessment (JSA - Job Safety Analysis, PPE Matrix)
- Compliance Training & Audits (EHS training matrix, audit pack generation)
- Safety gating for operator certification
- Andon-style safety alerts

This module implements Section 21.4 of the Development Plan.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


# =============================================================================
# ENUMERATIONS
# =============================================================================


class IncidentSeverity(str, Enum):
    """Severity classification for safety incidents."""
    NEAR_MISS = "near_miss"  # No injury, potential hazard
    FIRST_AID = "first_aid"  # Minor injury, first aid only
    RECORDABLE = "recordable"  # OSHA recordable injury
    LOST_TIME = "lost_time"  # Injury causing lost work time
    CRITICAL = "critical"  # Severe injury, hospitalization
    FATAL = "fatal"  # Fatality


class IncidentType(str, Enum):
    """Type of safety incident."""
    INJURY = "injury"  # Personal injury
    ILLNESS = "illness"  # Occupational illness
    PROPERTY_DAMAGE = "property_damage"  # Equipment/property damage
    ENVIRONMENTAL = "environmental"  # Environmental spill/release
    FIRE = "fire"  # Fire or explosion
    ERGONOMIC = "ergonomic"  # Repetitive strain, ergonomic
    CHEMICAL = "chemical"  # Chemical exposure
    ELECTRICAL = "electrical"  # Electrical incident
    SLIP_TRIP_FALL = "slip_trip_fall"  # Slip, trip, or fall
    STRUCK_BY = "struck_by"  # Struck by object
    CAUGHT_BETWEEN = "caught_between"  # Caught in/between
    OTHER = "other"


class IncidentStatus(str, Enum):
    """Status of incident investigation."""
    REPORTED = "reported"  # Initial report
    UNDER_INVESTIGATION = "under_investigation"  # Being investigated
    ROOT_CAUSE_IDENTIFIED = "root_cause_identified"  # 5-Why complete
    CORRECTIVE_ACTION = "corrective_action"  # Actions being implemented
    VERIFICATION = "verification"  # Verifying effectiveness
    CLOSED = "closed"  # Investigation complete
    CANCELLED = "cancelled"  # Invalid/duplicate report


class BodyPart(str, Enum):
    """Body part affected (for injury tracking)."""
    HEAD = "head"
    EYE = "eye"
    EAR = "ear"
    NECK = "neck"
    SHOULDER = "shoulder"
    ARM = "arm"
    ELBOW = "elbow"
    WRIST = "wrist"
    HAND = "hand"
    FINGER = "finger"
    BACK = "back"
    CHEST = "chest"
    ABDOMEN = "abdomen"
    HIP = "hip"
    LEG = "leg"
    KNEE = "knee"
    ANKLE = "ankle"
    FOOT = "foot"
    TOE = "toe"
    MULTIPLE = "multiple"


class HazardCategory(str, Enum):
    """Hazard category for JSA."""
    MECHANICAL = "mechanical"  # Moving parts, pinch points
    ELECTRICAL = "electrical"  # Electrical hazards
    CHEMICAL = "chemical"  # Chemical exposure
    THERMAL = "thermal"  # Heat, cold
    NOISE = "noise"  # Excessive noise
    RADIATION = "radiation"  # Ionizing/non-ionizing radiation
    BIOLOGICAL = "biological"  # Biological agents
    ERGONOMIC = "ergonomic"  # Repetitive motion, lifting
    ENVIRONMENTAL = "environmental"  # Slips, trips, falls
    PRESSURE = "pressure"  # Pressure vessels
    CONFINED_SPACE = "confined_space"  # Confined space entry
    HEIGHT = "height"  # Working at height
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk level (Severity × Probability)."""
    LOW = "low"  # Acceptable risk
    MEDIUM = "medium"  # Requires controls
    HIGH = "high"  # Significant controls required
    CRITICAL = "critical"  # Work must not proceed


class PPEType(str, Enum):
    """Personal Protective Equipment types."""
    SAFETY_GLASSES = "safety_glasses"
    FACE_SHIELD = "face_shield"
    WELDING_HELMET = "welding_helmet"
    HARD_HAT = "hard_hat"
    HEARING_PROTECTION = "hearing_protection"
    RESPIRATOR = "respirator"
    DUST_MASK = "dust_mask"
    NITRILE_GLOVES = "nitrile_gloves"
    CUT_RESISTANT_GLOVES = "cut_resistant_gloves"
    CHEMICAL_GLOVES = "chemical_gloves"
    WELDING_GLOVES = "welding_gloves"
    SAFETY_SHOES = "safety_shoes"
    METATARSAL_GUARDS = "metatarsal_guards"
    FALL_PROTECTION = "fall_protection"
    FR_CLOTHING = "fr_clothing"  # Flame resistant
    HI_VIS_VEST = "hi_vis_vest"
    LAB_COAT = "lab_coat"
    APRON = "apron"


class CertificationType(str, Enum):
    """EHS certification types."""
    FORKLIFT = "forklift"
    OVERHEAD_CRANE = "overhead_crane"
    LOTO = "loto"  # Lockout/Tagout
    CONFINED_SPACE = "confined_space"
    FALL_PROTECTION = "fall_protection"
    FIRST_AID = "first_aid"
    CPR_AED = "cpr_aed"
    FIRE_EXTINGUISHER = "fire_extinguisher"
    HAZMAT = "hazmat"
    ELECTRICAL_SAFETY = "electrical_safety"
    ERGONOMICS = "ergonomics"
    CHEMICAL_HANDLING = "chemical_handling"
    RESPIRATORY_PROTECTION = "respiratory_protection"
    HOT_WORK = "hot_work"
    GENERAL_SAFETY = "general_safety"


class CertificationStatus(str, Enum):
    """Status of safety certification."""
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"  # Within 60 days
    EXPIRED = "expired"
    PENDING_RENEWAL = "pending_renewal"
    NOT_CERTIFIED = "not_certified"


class AlertPriority(str, Enum):
    """Safety alert priority (Andon-style)."""
    INFORMATION = "information"  # FYI
    WARNING = "warning"  # Caution needed
    URGENT = "urgent"  # Immediate attention
    CRITICAL = "critical"  # Stop work, evacuate if needed


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SafetyIncident:
    """Safety incident record."""
    id: str
    incident_number: str
    incident_type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.REPORTED
    
    # Location
    location_id: Optional[str] = None
    work_center_id: Optional[str] = None
    station_id: Optional[str] = None
    
    # Details
    description: str = ""
    immediate_actions_taken: str = ""
    photos: list[str] = field(default_factory=list)  # File references
    
    # People involved
    reported_by: Optional[str] = None
    injured_employee_id: Optional[str] = None
    body_parts_affected: list[BodyPart] = field(default_factory=list)
    witnesses: list[str] = field(default_factory=list)
    
    # Investigation
    investigator_id: Optional[str] = None
    investigation_started: Optional[datetime] = None
    five_why_analysis: list[dict] = field(default_factory=list)  # [{"why": "...", "answer": "..."}]
    root_cause: Optional[str] = None
    contributing_factors: list[str] = field(default_factory=list)
    
    # Corrective actions
    corrective_actions: list[dict] = field(default_factory=list)  # [{"action": "...", "responsible": "...", "due_date": "...", "status": "..."}]
    preventive_actions: list[dict] = field(default_factory=list)
    
    # Closure
    verification_notes: str = ""
    closed_by: Optional[str] = None
    
    # OSHA/Regulatory
    osha_recordable: bool = False
    osha_case_number: Optional[str] = None
    days_away_from_work: int = 0
    days_restricted_duty: int = 0
    
    # Timestamps
    incident_datetime: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reported_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class JSAHazard:
    """Individual hazard within a JSA."""
    id: str
    step_number: int
    task_step: str
    hazard_category: HazardCategory
    hazard_description: str
    potential_consequences: str
    initial_risk_level: RiskLevel
    
    # Controls
    engineering_controls: list[str] = field(default_factory=list)
    administrative_controls: list[str] = field(default_factory=list)
    ppe_required: list[PPEType] = field(default_factory=list)
    
    # Residual risk
    residual_risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class JobSafetyAnalysis:
    """Job Safety Analysis (JSA) document."""
    id: str
    jsa_number: str
    work_center_id: str
    station_id: Optional[str] = None
    job_name: str = ""
    job_description: str = ""
    
    # Hazard analysis
    hazards: list[JSAHazard] = field(default_factory=list)
    
    # Overall requirements
    ppe_matrix: list[PPEType] = field(default_factory=list)  # Aggregate PPE for station
    training_required: list[CertificationType] = field(default_factory=list)
    loto_required: bool = False
    permit_required: bool = False
    
    # Approval
    prepared_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    
    # Revision control
    revision: int = 1
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None  # For periodic review
    
    # Status
    is_active: bool = True
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EmployeeCertification:
    """Employee safety certification record."""
    id: str
    employee_id: str
    certification_type: CertificationType
    certification_name: str = ""
    
    # Dates
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    
    # Training details
    training_provider: str = ""
    training_hours: Decimal = Decimal("0")
    certificate_number: Optional[str] = None
    certificate_document: Optional[str] = None  # File reference
    
    # Status
    status: CertificationStatus = CertificationStatus.ACTIVE
    
    # Verification
    verified_by: Optional[str] = None
    verified_date: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SafetyAlert:
    """Safety alert (Andon-style)."""
    id: str
    alert_number: str
    priority: AlertPriority
    title: str
    message: str
    
    # Source
    incident_id: Optional[str] = None
    triggered_by: Optional[str] = None
    
    # Scope
    location_ids: list[str] = field(default_factory=list)  # Affected locations
    work_center_ids: list[str] = field(default_factory=list)
    
    # Status
    is_active: bool = True
    acknowledged_by: list[str] = field(default_factory=list)
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    cleared_at: Optional[datetime] = None
    cleared_by: Optional[str] = None


@dataclass
class JSAAcknowledgment:
    """Record of employee acknowledging JSA."""
    id: str
    employee_id: str
    jsa_id: str
    jsa_revision: int
    acknowledged_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature_data: Optional[str] = None  # Base64 signature if captured


@dataclass
class AuditPack:
    """Generated audit evidence bundle."""
    id: str
    pack_name: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: Optional[str] = None
    
    # Contents
    documents: list[dict] = field(default_factory=list)  # [{"type": "...", "name": "...", "file_ref": "..."}]
    
    # Scope
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    categories_included: list[str] = field(default_factory=list)


# =============================================================================
# SERVICE CLASS
# =============================================================================


class EHSSafetyService:
    """
    EHS / Safety Compliance Service.
    
    Manages:
    - Incident & Near-Miss reporting and investigation
    - Job Safety Analysis (JSA) and PPE Matrix
    - Employee safety certifications and training
    - Safety alerts and gating
    - Audit pack generation
    """
    
    def __init__(self):
        """Initialize the service."""
        self._incidents: dict[str, SafetyIncident] = {}
        self._jsas: dict[str, JobSafetyAnalysis] = {}
        self._certifications: dict[str, EmployeeCertification] = {}
        self._alerts: dict[str, SafetyAlert] = {}
        self._acknowledgments: dict[str, JSAAcknowledgment] = {}
        self._audit_packs: dict[str, AuditPack] = {}
        
        self._incident_counter = 0
        self._jsa_counter = 0
        self._alert_counter = 0
    
    # =========================================================================
    # INCIDENT & NEAR-MISS MANAGEMENT
    # =========================================================================
    
    def report_incident(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        description: str,
        location_id: Optional[str] = None,
        work_center_id: Optional[str] = None,
        station_id: Optional[str] = None,
        reported_by: Optional[str] = None,
        injured_employee_id: Optional[str] = None,
        body_parts: Optional[list[BodyPart]] = None,
        photos: Optional[list[str]] = None,
        immediate_actions: str = "",
        incident_datetime: Optional[datetime] = None,
    ) -> SafetyIncident:
        """
        Report a safety incident or near-miss.
        
        For near-misses: Use severity=NEAR_MISS and no injured_employee_id.
        Supports "3-click" mobile flow with photo upload.
        """
        self._incident_counter += 1
        incident_number = f"INC-{self._incident_counter:06d}"
        
        incident = SafetyIncident(
            id=str(uuid4()),
            incident_number=incident_number,
            incident_type=incident_type,
            severity=severity,
            description=description,
            location_id=location_id,
            work_center_id=work_center_id,
            station_id=station_id,
            reported_by=reported_by,
            injured_employee_id=injured_employee_id,
            body_parts_affected=body_parts or [],
            photos=photos or [],
            immediate_actions_taken=immediate_actions,
            incident_datetime=incident_datetime or datetime.now(timezone.utc),
        )
        
        # Determine if OSHA recordable
        if severity in [IncidentSeverity.RECORDABLE, IncidentSeverity.LOST_TIME, 
                        IncidentSeverity.CRITICAL, IncidentSeverity.FATAL]:
            incident.osha_recordable = True
        
        # Auto-trigger safety alert for critical/fatal incidents
        if severity in [IncidentSeverity.CRITICAL, IncidentSeverity.FATAL]:
            self._trigger_safety_alert(
                priority=AlertPriority.CRITICAL,
                title=f"Critical Safety Incident: {incident_number}",
                message=description[:200],
                incident_id=incident.id,
                location_ids=[location_id] if location_id else [],
            )
        
        self._incidents[incident.id] = incident
        return incident
    
    def report_near_miss(
        self,
        description: str,
        location_id: Optional[str] = None,
        work_center_id: Optional[str] = None,
        reported_by: Optional[str] = None,
        photos: Optional[list[str]] = None,
    ) -> SafetyIncident:
        """
        Quick near-miss report (3-click mobile flow).
        Simplified entry for rapid shop-floor reporting.
        """
        return self.report_incident(
            incident_type=IncidentType.OTHER,
            severity=IncidentSeverity.NEAR_MISS,
            description=description,
            location_id=location_id,
            work_center_id=work_center_id,
            reported_by=reported_by,
            photos=photos,
        )
    
    def get_incident(self, incident_id: str) -> Optional[SafetyIncident]:
        """Get incident by ID."""
        return self._incidents.get(incident_id)
    
    def get_incident_by_number(self, incident_number: str) -> Optional[SafetyIncident]:
        """Get incident by incident number."""
        for incident in self._incidents.values():
            if incident.incident_number == incident_number:
                return incident
        return None
    
    def get_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        incident_type: Optional[IncidentType] = None,
        location_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        open_only: bool = False,
    ) -> list[SafetyIncident]:
        """Get incidents with filtering."""
        results = list(self._incidents.values())
        
        if status:
            results = [i for i in results if i.status == status]
        if severity:
            results = [i for i in results if i.severity == severity]
        if incident_type:
            results = [i for i in results if i.incident_type == incident_type]
        if location_id:
            results = [i for i in results if i.location_id == location_id]
        if from_date:
            results = [i for i in results if i.incident_datetime >= from_date]
        if to_date:
            results = [i for i in results if i.incident_datetime <= to_date]
        if open_only:
            results = [i for i in results if i.status not in [IncidentStatus.CLOSED, IncidentStatus.CANCELLED]]
        
        return results
    
    def start_investigation(
        self,
        incident_id: str,
        investigator_id: str,
    ) -> Optional[SafetyIncident]:
        """Start investigation on an incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = IncidentStatus.UNDER_INVESTIGATION
        incident.investigator_id = investigator_id
        incident.investigation_started = datetime.now(timezone.utc)
        incident.updated_at = datetime.now(timezone.utc)
        
        return incident
    
    def add_five_why(
        self,
        incident_id: str,
        why_question: str,
        answer: str,
    ) -> Optional[SafetyIncident]:
        """Add a 5-Why analysis step."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        step_number = len(incident.five_why_analysis) + 1
        incident.five_why_analysis.append({
            "step": step_number,
            "why": why_question,
            "answer": answer,
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        incident.updated_at = datetime.now(timezone.utc)
        
        return incident
    
    def set_root_cause(
        self,
        incident_id: str,
        root_cause: str,
        contributing_factors: Optional[list[str]] = None,
    ) -> Optional[SafetyIncident]:
        """Set the root cause from 5-Why analysis."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        incident.root_cause = root_cause
        incident.contributing_factors = contributing_factors or []
        incident.status = IncidentStatus.ROOT_CAUSE_IDENTIFIED
        incident.updated_at = datetime.now(timezone.utc)
        
        return incident
    
    def add_corrective_action(
        self,
        incident_id: str,
        action_description: str,
        responsible_id: str,
        due_date: datetime,
        is_preventive: bool = False,
    ) -> Optional[SafetyIncident]:
        """Add a corrective or preventive action."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        action = {
            "id": str(uuid4()),
            "action": action_description,
            "responsible": responsible_id,
            "due_date": due_date.isoformat(),
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if is_preventive:
            incident.preventive_actions.append(action)
        else:
            incident.corrective_actions.append(action)
        
        incident.status = IncidentStatus.CORRECTIVE_ACTION
        incident.updated_at = datetime.now(timezone.utc)
        
        return incident
    
    def complete_action(
        self,
        incident_id: str,
        action_id: str,
        completion_notes: str = "",
    ) -> Optional[SafetyIncident]:
        """Mark a corrective/preventive action as complete."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        for action in incident.corrective_actions + incident.preventive_actions:
            if action.get("id") == action_id:
                action["status"] = "completed"
                action["completed_at"] = datetime.now(timezone.utc).isoformat()
                action["completion_notes"] = completion_notes
                break
        
        incident.updated_at = datetime.now(timezone.utc)
        return incident
    
    def close_incident(
        self,
        incident_id: str,
        closed_by: str,
        verification_notes: str = "",
    ) -> Optional[SafetyIncident]:
        """Close an incident after verification."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        
        incident.status = IncidentStatus.CLOSED
        incident.closed_by = closed_by
        incident.verification_notes = verification_notes
        incident.closed_at = datetime.now(timezone.utc)
        incident.updated_at = datetime.now(timezone.utc)
        
        return incident
    
    # =========================================================================
    # JOB SAFETY ANALYSIS (JSA) & PPE MATRIX
    # =========================================================================
    
    def create_jsa(
        self,
        work_center_id: str,
        job_name: str,
        job_description: str = "",
        station_id: Optional[str] = None,
        prepared_by: Optional[str] = None,
    ) -> JobSafetyAnalysis:
        """Create a new Job Safety Analysis document."""
        self._jsa_counter += 1
        jsa_number = f"JSA-{self._jsa_counter:05d}"
        
        jsa = JobSafetyAnalysis(
            id=str(uuid4()),
            jsa_number=jsa_number,
            work_center_id=work_center_id,
            station_id=station_id,
            job_name=job_name,
            job_description=job_description,
            prepared_by=prepared_by,
        )
        
        self._jsas[jsa.id] = jsa
        return jsa
    
    def add_hazard_to_jsa(
        self,
        jsa_id: str,
        task_step: str,
        hazard_category: HazardCategory,
        hazard_description: str,
        potential_consequences: str,
        initial_risk_level: RiskLevel,
        engineering_controls: Optional[list[str]] = None,
        administrative_controls: Optional[list[str]] = None,
        ppe_required: Optional[list[PPEType]] = None,
        residual_risk_level: Optional[RiskLevel] = None,
    ) -> Optional[JobSafetyAnalysis]:
        """Add a hazard step to a JSA."""
        jsa = self._jsas.get(jsa_id)
        if not jsa:
            return None
        
        step_number = len(jsa.hazards) + 1
        
        hazard = JSAHazard(
            id=str(uuid4()),
            step_number=step_number,
            task_step=task_step,
            hazard_category=hazard_category,
            hazard_description=hazard_description,
            potential_consequences=potential_consequences,
            initial_risk_level=initial_risk_level,
            engineering_controls=engineering_controls or [],
            administrative_controls=administrative_controls or [],
            ppe_required=ppe_required or [],
            residual_risk_level=residual_risk_level or RiskLevel.LOW,
        )
        
        jsa.hazards.append(hazard)
        
        # Update aggregate PPE matrix
        for ppe in hazard.ppe_required:
            if ppe not in jsa.ppe_matrix:
                jsa.ppe_matrix.append(ppe)
        
        # Check for LOTO requirement
        if hazard_category == HazardCategory.ELECTRICAL:
            jsa.loto_required = True
        
        jsa.updated_at = datetime.now(timezone.utc)
        return jsa
    
    def get_jsa(self, jsa_id: str) -> Optional[JobSafetyAnalysis]:
        """Get JSA by ID."""
        return self._jsas.get(jsa_id)
    
    def get_jsa_for_station(self, station_id: str) -> Optional[JobSafetyAnalysis]:
        """Get active JSA for a station."""
        for jsa in self._jsas.values():
            if jsa.station_id == station_id and jsa.is_active:
                return jsa
        return None
    
    def get_jsas(
        self,
        work_center_id: Optional[str] = None,
        active_only: bool = True,
    ) -> list[JobSafetyAnalysis]:
        """Get JSAs with filtering."""
        results = list(self._jsas.values())
        
        if work_center_id:
            results = [j for j in results if j.work_center_id == work_center_id]
        if active_only:
            results = [j for j in results if j.is_active]
        
        return results
    
    def approve_jsa(
        self,
        jsa_id: str,
        reviewed_by: str,
        approved_by: str,
    ) -> Optional[JobSafetyAnalysis]:
        """Approve a JSA for use."""
        jsa = self._jsas.get(jsa_id)
        if not jsa:
            return None
        
        jsa.reviewed_by = reviewed_by
        jsa.approved_by = approved_by
        jsa.approval_date = datetime.now(timezone.utc)
        jsa.effective_date = datetime.now(timezone.utc)
        jsa.expiry_date = datetime.now(timezone.utc) + timedelta(days=365)  # Annual review
        jsa.updated_at = datetime.now(timezone.utc)
        
        return jsa
    
    def set_jsa_training_requirements(
        self,
        jsa_id: str,
        training_required: list[CertificationType],
        permit_required: bool = False,
    ) -> Optional[JobSafetyAnalysis]:
        """Set training requirements for a JSA."""
        jsa = self._jsas.get(jsa_id)
        if not jsa:
            return None
        
        jsa.training_required = training_required
        jsa.permit_required = permit_required
        jsa.updated_at = datetime.now(timezone.utc)
        
        return jsa
    
    def get_ppe_matrix_for_station(self, station_id: str) -> list[PPEType]:
        """Get aggregate PPE requirements for a station."""
        jsa = self.get_jsa_for_station(station_id)
        if jsa:
            return jsa.ppe_matrix
        return []
    
    def revise_jsa(
        self,
        jsa_id: str,
        revised_by: str,
    ) -> Optional[JobSafetyAnalysis]:
        """Create a new revision of a JSA (marks old as inactive)."""
        old_jsa = self._jsas.get(jsa_id)
        if not old_jsa:
            return None
        
        # Deactivate old version
        old_jsa.is_active = False
        old_jsa.updated_at = datetime.now(timezone.utc)
        
        # Create new revision
        new_jsa = JobSafetyAnalysis(
            id=str(uuid4()),
            jsa_number=old_jsa.jsa_number,  # Keep same number
            work_center_id=old_jsa.work_center_id,
            station_id=old_jsa.station_id,
            job_name=old_jsa.job_name,
            job_description=old_jsa.job_description,
            hazards=list(old_jsa.hazards),  # Copy hazards
            ppe_matrix=list(old_jsa.ppe_matrix),
            training_required=list(old_jsa.training_required),
            loto_required=old_jsa.loto_required,
            permit_required=old_jsa.permit_required,
            prepared_by=revised_by,
            revision=old_jsa.revision + 1,
        )
        
        self._jsas[new_jsa.id] = new_jsa
        return new_jsa
    
    # =========================================================================
    # EMPLOYEE CERTIFICATIONS & TRAINING
    # =========================================================================
    
    def add_certification(
        self,
        employee_id: str,
        certification_type: CertificationType,
        certification_name: str = "",
        issue_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        training_provider: str = "",
        training_hours: Decimal = Decimal("0"),
        certificate_number: Optional[str] = None,
        certificate_document: Optional[str] = None,
    ) -> EmployeeCertification:
        """Add a certification for an employee."""
        cert = EmployeeCertification(
            id=str(uuid4()),
            employee_id=employee_id,
            certification_type=certification_type,
            certification_name=certification_name or certification_type.value,
            issue_date=issue_date,
            expiry_date=expiry_date,
            training_provider=training_provider,
            training_hours=training_hours,
            certificate_number=certificate_number,
            certificate_document=certificate_document,
        )
        
        # Determine status
        cert.status = self._calculate_cert_status(cert)
        
        self._certifications[cert.id] = cert
        return cert
    
    def _calculate_cert_status(self, cert: EmployeeCertification) -> CertificationStatus:
        """Calculate certification status based on dates."""
        if not cert.expiry_date:
            return CertificationStatus.ACTIVE
        
        now = datetime.now(timezone.utc)
        days_to_expiry = (cert.expiry_date - now).days
        
        if days_to_expiry < 0:
            return CertificationStatus.EXPIRED
        elif days_to_expiry <= 60:
            return CertificationStatus.EXPIRING_SOON
        else:
            return CertificationStatus.ACTIVE
    
    def get_certification(self, cert_id: str) -> Optional[EmployeeCertification]:
        """Get certification by ID."""
        return self._certifications.get(cert_id)
    
    def get_employee_certifications(
        self,
        employee_id: str,
        cert_type: Optional[CertificationType] = None,
        status: Optional[CertificationStatus] = None,
    ) -> list[EmployeeCertification]:
        """Get certifications for an employee."""
        results = [c for c in self._certifications.values() if c.employee_id == employee_id]
        
        # Recalculate statuses
        for cert in results:
            cert.status = self._calculate_cert_status(cert)
        
        if cert_type:
            results = [c for c in results if c.certification_type == cert_type]
        if status:
            results = [c for c in results if c.status == status]
        
        return results
    
    def get_expiring_certifications(
        self,
        days_ahead: int = 60,
    ) -> list[EmployeeCertification]:
        """Get certifications expiring within specified days."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days_ahead)
        
        results = []
        for cert in self._certifications.values():
            cert.status = self._calculate_cert_status(cert)
            if cert.expiry_date and now <= cert.expiry_date <= cutoff:
                results.append(cert)
        
        return results
    
    def renew_certification(
        self,
        cert_id: str,
        new_expiry_date: datetime,
        training_provider: str = "",
        training_hours: Decimal = Decimal("0"),
        new_certificate_number: Optional[str] = None,
    ) -> Optional[EmployeeCertification]:
        """Renew an existing certification."""
        cert = self._certifications.get(cert_id)
        if not cert:
            return None
        
        cert.issue_date = datetime.now(timezone.utc)
        cert.expiry_date = new_expiry_date
        cert.training_provider = training_provider or cert.training_provider
        cert.training_hours = training_hours or cert.training_hours
        if new_certificate_number:
            cert.certificate_number = new_certificate_number
        cert.status = CertificationStatus.ACTIVE
        cert.updated_at = datetime.now(timezone.utc)
        
        return cert
    
    def verify_certification(
        self,
        cert_id: str,
        verified_by: str,
    ) -> Optional[EmployeeCertification]:
        """Verify a certification record."""
        cert = self._certifications.get(cert_id)
        if not cert:
            return None
        
        cert.verified_by = verified_by
        cert.verified_date = datetime.now(timezone.utc)
        cert.updated_at = datetime.now(timezone.utc)
        
        return cert
    
    def get_training_matrix(
        self,
        employee_ids: Optional[list[str]] = None,
        cert_types: Optional[list[CertificationType]] = None,
    ) -> dict[str, dict[str, str]]:
        """
        Get training matrix showing certification status per employee.
        
        Returns: {employee_id: {cert_type: status}}
        """
        matrix: dict[str, dict[str, str]] = {}
        
        target_employees = employee_ids or list(set(c.employee_id for c in self._certifications.values()))
        target_certs = cert_types or list(CertificationType)
        
        for emp_id in target_employees:
            matrix[emp_id] = {}
            for cert_type in target_certs:
                certs = self.get_employee_certifications(emp_id, cert_type=cert_type)
                if certs:
                    # Use most recent/valid cert
                    best = max(certs, key=lambda c: c.expiry_date or datetime.max.replace(tzinfo=timezone.utc))
                    matrix[emp_id][cert_type.value] = best.status.value
                else:
                    matrix[emp_id][cert_type.value] = CertificationStatus.NOT_CERTIFIED.value
        
        return matrix
    
    # =========================================================================
    # SAFETY GATING
    # =========================================================================
    
    def check_operator_safety_clearance(
        self,
        employee_id: str,
        station_id: str,
    ) -> dict:
        """
        Check if an operator is cleared to work at a station.
        
        Checks:
        1. JSA acknowledgment
        2. Required training/certifications
        
        Returns: {"cleared": bool, "missing": [...], "warnings": [...]}
        """
        result: dict[str, Any] = {
            "cleared": True,
            "missing": [],
            "warnings": [],
        }
        
        # Get JSA for station
        jsa = self.get_jsa_for_station(station_id)
        if not jsa:
            # No JSA = allowed (but warning)
            result["warnings"].append("No JSA defined for station")
            return result
        
        # Check JSA acknowledgment
        ack = self._get_jsa_acknowledgment(employee_id, jsa.id, jsa.revision)
        if not ack:
            result["cleared"] = False
            result["missing"].append(f"JSA acknowledgment required: {jsa.jsa_number}")
        
        # Check required training
        for cert_type in jsa.training_required:
            certs = self.get_employee_certifications(employee_id, cert_type=cert_type)
            valid_certs = [c for c in certs if c.status in [CertificationStatus.ACTIVE, CertificationStatus.EXPIRING_SOON]]
            
            if not valid_certs:
                result["cleared"] = False
                result["missing"].append(f"Training required: {cert_type.value}")
            elif any(c.status == CertificationStatus.EXPIRING_SOON for c in valid_certs):
                result["warnings"].append(f"Certification expiring soon: {cert_type.value}")
        
        return result
    
    def acknowledge_jsa(
        self,
        employee_id: str,
        jsa_id: str,
        signature_data: Optional[str] = None,
    ) -> Optional[JSAAcknowledgment]:
        """Record employee acknowledgment of a JSA."""
        jsa = self._jsas.get(jsa_id)
        if not jsa:
            return None
        
        ack = JSAAcknowledgment(
            id=str(uuid4()),
            employee_id=employee_id,
            jsa_id=jsa_id,
            jsa_revision=jsa.revision,
            signature_data=signature_data,
        )
        
        self._acknowledgments[ack.id] = ack
        return ack
    
    def _get_jsa_acknowledgment(
        self,
        employee_id: str,
        jsa_id: str,
        revision: int,
    ) -> Optional[JSAAcknowledgment]:
        """Get acknowledgment for specific JSA revision."""
        for ack in self._acknowledgments.values():
            if (ack.employee_id == employee_id and 
                ack.jsa_id == jsa_id and 
                ack.jsa_revision == revision):
                return ack
        return None
    
    # =========================================================================
    # SAFETY ALERTS
    # =========================================================================
    
    def _trigger_safety_alert(
        self,
        priority: AlertPriority,
        title: str,
        message: str,
        incident_id: Optional[str] = None,
        location_ids: Optional[list[str]] = None,
        work_center_ids: Optional[list[str]] = None,
        triggered_by: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> SafetyAlert:
        """Create a safety alert (internal method)."""
        self._alert_counter += 1
        alert_number = f"ALERT-{self._alert_counter:05d}"
        
        alert = SafetyAlert(
            id=str(uuid4()),
            alert_number=alert_number,
            priority=priority,
            title=title,
            message=message,
            incident_id=incident_id,
            triggered_by=triggered_by,
            location_ids=location_ids or [],
            work_center_ids=work_center_ids or [],
        )
        
        if expires_in_hours:
            alert.expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        self._alerts[alert.id] = alert
        return alert
    
    def create_safety_alert(
        self,
        priority: AlertPriority,
        title: str,
        message: str,
        triggered_by: Optional[str] = None,
        location_ids: Optional[list[str]] = None,
        work_center_ids: Optional[list[str]] = None,
        expires_in_hours: Optional[int] = None,
    ) -> SafetyAlert:
        """Create a manual safety alert."""
        return self._trigger_safety_alert(
            priority=priority,
            title=title,
            message=message,
            triggered_by=triggered_by,
            location_ids=location_ids,
            work_center_ids=work_center_ids,
            expires_in_hours=expires_in_hours,
        )
    
    def get_alert(self, alert_id: str) -> Optional[SafetyAlert]:
        """Get alert by ID."""
        return self._alerts.get(alert_id)
    
    def get_active_alerts(
        self,
        location_id: Optional[str] = None,
        work_center_id: Optional[str] = None,
        priority: Optional[AlertPriority] = None,
    ) -> list[SafetyAlert]:
        """Get active safety alerts."""
        now = datetime.now(timezone.utc)
        results = []
        
        for alert in self._alerts.values():
            if not alert.is_active:
                continue
            if alert.expires_at and alert.expires_at < now:
                continue
            if location_id and location_id not in alert.location_ids:
                continue
            if work_center_id and work_center_id not in alert.work_center_ids:
                continue
            if priority and alert.priority != priority:
                continue
            results.append(alert)
        
        # Sort by priority (critical first)
        priority_order = {AlertPriority.CRITICAL: 0, AlertPriority.URGENT: 1, 
                         AlertPriority.WARNING: 2, AlertPriority.INFORMATION: 3}
        results.sort(key=lambda a: priority_order.get(a.priority, 4))
        
        return results
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> Optional[SafetyAlert]:
        """Acknowledge a safety alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        
        if acknowledged_by not in alert.acknowledged_by:
            alert.acknowledged_by.append(acknowledged_by)
        
        return alert
    
    def clear_alert(
        self,
        alert_id: str,
        cleared_by: str,
    ) -> Optional[SafetyAlert]:
        """Clear a safety alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        
        alert.is_active = False
        alert.cleared_at = datetime.now(timezone.utc)
        alert.cleared_by = cleared_by
        
        return alert
    
    # =========================================================================
    # AUDIT PACK GENERATION
    # =========================================================================
    
    def generate_audit_pack(
        self,
        pack_name: str,
        generated_by: Optional[str] = None,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
        include_incidents: bool = True,
        include_jsas: bool = True,
        include_training: bool = True,
        include_alerts: bool = True,
    ) -> AuditPack:
        """
        Generate an audit evidence bundle.
        
        One-click generation of evidence for audits:
        - Signed policies (JSAs)
        - Attendance/training logs
        - Incident reports
        """
        documents: list[dict[str, Any]] = []
        categories: list[str] = []
        
        if include_incidents:
            categories.append("incidents")
            incidents = self.get_incidents(
                from_date=date_range_start,
                to_date=date_range_end,
            )
            for inc in incidents:
                documents.append({
                    "type": "incident_report",
                    "name": f"Incident Report: {inc.incident_number}",
                    "reference_id": inc.id,
                    "severity": inc.severity.value,
                    "status": inc.status.value,
                    "date": inc.incident_datetime.isoformat(),
                })
        
        if include_jsas:
            categories.append("job_safety_analyses")
            jsas = self.get_jsas(active_only=False)
            for jsa in jsas:
                # Include acknowledgments
                acks = [a for a in self._acknowledgments.values() if a.jsa_id == jsa.id]
                documents.append({
                    "type": "jsa",
                    "name": f"JSA: {jsa.jsa_number} - {jsa.job_name}",
                    "reference_id": jsa.id,
                    "revision": jsa.revision,
                    "acknowledgment_count": len(acks),
                    "approved": jsa.approved_by is not None,
                })
        
        if include_training:
            categories.append("training_records")
            for cert in self._certifications.values():
                documents.append({
                    "type": "certification",
                    "name": f"Cert: {cert.certification_name}",
                    "reference_id": cert.id,
                    "employee_id": cert.employee_id,
                    "status": cert.status.value,
                    "expiry": cert.expiry_date.isoformat() if cert.expiry_date else None,
                })
        
        if include_alerts:
            categories.append("safety_alerts")
            for alert in self._alerts.values():
                if date_range_start and alert.created_at < date_range_start:
                    continue
                if date_range_end and alert.created_at > date_range_end:
                    continue
                documents.append({
                    "type": "alert",
                    "name": f"Alert: {alert.alert_number} - {alert.title}",
                    "reference_id": alert.id,
                    "priority": alert.priority.value,
                    "is_active": alert.is_active,
                })
        
        pack = AuditPack(
            id=str(uuid4()),
            pack_name=pack_name,
            generated_by=generated_by,
            documents=documents,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            categories_included=categories,
        )
        
        self._audit_packs[pack.id] = pack
        return pack
    
    def get_audit_pack(self, pack_id: str) -> Optional[AuditPack]:
        """Get audit pack by ID."""
        return self._audit_packs.get(pack_id)
    
    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================
    
    def get_statistics(self) -> dict:
        """Get EHS statistics."""
        incidents = list(self._incidents.values())
        
        # Incident counts by severity
        severity_counts = {}
        for sev in IncidentSeverity:
            severity_counts[sev.value] = len([i for i in incidents if i.severity == sev])
        
        # Incident counts by status
        status_counts = {}
        for stat in IncidentStatus:
            status_counts[stat.value] = len([i for i in incidents if i.status == stat])
        
        # OSHA metrics
        osha_recordable = len([i for i in incidents if i.osha_recordable])
        total_days_away = sum(i.days_away_from_work for i in incidents)
        total_restricted = sum(i.days_restricted_duty for i in incidents)
        
        # Certification metrics
        certs = list(self._certifications.values())
        for cert in certs:
            cert.status = self._calculate_cert_status(cert)  # type: ignore[assignment]
        
        cert_status_counts: dict[str, int] = {}
        for cert_stat in CertificationStatus:
            cert_status_counts[cert_stat.value] = len([c for c in certs if c.status == cert_stat])
        
        return {
            "total_incidents": len(incidents),
            "incidents_by_severity": severity_counts,
            "incidents_by_status": status_counts,
            "osha_recordable_count": osha_recordable,
            "total_days_away": total_days_away,
            "total_restricted_duty_days": total_restricted,
            "near_miss_count": severity_counts.get(IncidentSeverity.NEAR_MISS.value, 0),
            "open_incidents": len([i for i in incidents if i.status not in [IncidentStatus.CLOSED, IncidentStatus.CANCELLED]]),
            "total_jsas": len(self._jsas),
            "active_jsas": len([j for j in self._jsas.values() if j.is_active]),
            "total_certifications": len(certs),
            "certifications_by_status": cert_status_counts,
            "active_alerts": len([a for a in self._alerts.values() if a.is_active]),
            "audit_packs_generated": len(self._audit_packs),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_ehs_safety_service() -> EHSSafetyService:
    """Create and return an EHS Safety Service instance."""
    return EHSSafetyService()
