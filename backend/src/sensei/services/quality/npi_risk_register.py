"""
NPI Risk Register Service.

Extends the base risk management with NPI-specific risk categories,
templates, and workflows for managing risks across the New Product
Introduction lifecycle.

Features:
- NPI-specific risk categories (design, manufacturing, supplier, etc.)
- Phase-specific risk templates
- Risk aggregation across NPI projects
- Risk heat map generation
- FMEA-style severity/occurrence/detection scoring
- Risk review scheduling and tracking
- Mitigation action tracking
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class NPIRiskCategory(str, Enum):
    """NPI-specific risk categories."""
    
    # Design Risks
    DESIGN_COMPLEXITY = "design_complexity"
    DESIGN_FEASIBILITY = "design_feasibility"
    TOLERANCE_CAPABILITY = "tolerance_capability"
    MATERIAL_SELECTION = "material_selection"
    DFM_ISSUES = "dfm_issues"
    
    # Manufacturing Risks
    PROCESS_CAPABILITY = "process_capability"
    EQUIPMENT_AVAILABILITY = "equipment_availability"
    TOOLING_DESIGN = "tooling_design"
    CYCLE_TIME = "cycle_time"
    YIELD_RATE = "yield_rate"
    
    # Supplier Risks
    SUPPLIER_CAPABILITY = "supplier_capability"
    SUPPLIER_CAPACITY = "supplier_capacity"
    SUPPLIER_QUALITY = "supplier_quality"
    LEAD_TIME = "lead_time"
    SINGLE_SOURCE = "single_source"
    
    # Quality Risks
    CTQ_ACHIEVEMENT = "ctq_achievement"
    INSPECTION_CAPABILITY = "inspection_capability"
    FIRST_ARTICLE_FAILURE = "first_article_failure"
    PPAP_REJECTION = "ppap_rejection"
    
    # Program Risks
    SCHEDULE_DELAY = "schedule_delay"
    RESOURCE_AVAILABILITY = "resource_availability"
    CUSTOMER_REQUIREMENT_CHANGE = "customer_requirement_change"
    BUDGET_OVERRUN = "budget_overrun"
    
    # Other
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    ENVIRONMENTAL = "environmental"
    OTHER = "other"


class RiskPhase(str, Enum):
    """NPI phases for risk contextualization."""
    
    INTAKE = "intake"
    DFM = "dfm"
    PROTOTYPE = "prototype"
    PILOT = "pilot"
    SOP = "sop"
    ALL_PHASES = "all_phases"


class RiskPriority(str, Enum):
    """Risk priority based on RPN or risk score."""
    
    CRITICAL = "critical"  # RPN > 200 or High severity
    HIGH = "high"  # RPN 100-200
    MEDIUM = "medium"  # RPN 50-100
    LOW = "low"  # RPN < 50


class MitigationStatus(str, Enum):
    """Status of risk mitigation actions."""
    
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    INEFFECTIVE = "ineffective"
    CANCELLED = "cancelled"


class ReviewStatus(str, Enum):
    """Status of risk review."""
    
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


@dataclass
class MitigationAction:
    """A mitigation action for a risk."""
    
    id: UUID = field(default_factory=uuid4)
    risk_id: UUID = field(default_factory=uuid4)
    
    # Action details
    description: str = ""
    action_type: str = "mitigate"  # avoid, mitigate, transfer, accept
    
    # Assignment
    owner_id: UUID | None = None
    due_date: datetime | None = None
    
    # Status
    status: MitigationStatus = MitigationStatus.PLANNED
    
    # Progress
    progress_percentage: int = 0
    progress_notes: str | None = None
    
    # Completion
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    
    # Effectiveness
    effectiveness_rating: int | None = None  # 1-5
    effectiveness_notes: str | None = None
    
    # Expected impact on risk scores
    expected_severity_reduction: int = 0
    expected_occurrence_reduction: int = 0
    expected_detection_improvement: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RiskReview:
    """A scheduled or completed risk review."""
    
    id: UUID = field(default_factory=uuid4)
    risk_id: UUID = field(default_factory=uuid4)
    
    # Schedule
    scheduled_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_date: datetime | None = None
    status: ReviewStatus = ReviewStatus.PENDING
    
    # Reviewer
    reviewer_id: UUID | None = None
    
    # Review content
    previous_severity: int = 0
    previous_occurrence: int = 0
    previous_detection: int = 0
    previous_rpn: int = 0
    
    updated_severity: int | None = None
    updated_occurrence: int | None = None
    updated_detection: int | None = None
    updated_rpn: int | None = None
    
    # Findings
    status_changed: bool = False
    new_mitigations_needed: bool = False
    risk_escalated: bool = False
    risk_closed: bool = False
    
    notes: str | None = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NPIRisk:
    """An NPI-specific risk register entry."""
    
    id: UUID = field(default_factory=uuid4)
    risk_number: str = ""
    
    # NPI Context
    npi_project_id: UUID | None = None
    phase: RiskPhase = RiskPhase.ALL_PHASES
    
    # Product/Part reference
    product_id: UUID | None = None
    part_number: str | None = None
    operation_number: str | None = None
    
    # Basic info
    title: str = ""
    description: str = ""
    category: NPIRiskCategory = NPIRiskCategory.OTHER
    
    # FMEA-style scoring (1-10 each)
    severity: int = 5  # Impact if failure occurs
    occurrence: int = 5  # Probability of failure
    detection: int = 5  # Ability to detect before customer impact
    
    # Initial scores (captured at creation for trend tracking)
    initial_severity: int = 5
    initial_occurrence: int = 5
    initial_detection: int = 5
    
    # Risk Priority Number = S * O * D
    @property
    def rpn(self) -> int:
        """Calculate Risk Priority Number."""
        return self.severity * self.occurrence * self.detection
    
    @property
    def initial_rpn(self) -> int:
        """Calculate initial Risk Priority Number."""
        return self.initial_severity * self.initial_occurrence * self.initial_detection
    
    # Priority based on RPN
    @property
    def priority(self) -> RiskPriority:
        """Calculate priority from RPN."""
        rpn_val = self.rpn
        if rpn_val > 200 or self.severity >= 9:
            return RiskPriority.CRITICAL
        if rpn_val > 100:
            return RiskPriority.HIGH
        if rpn_val > 50:
            return RiskPriority.MEDIUM
        return RiskPriority.LOW
    
    # Potential effects
    failure_mode: str | None = None
    potential_effects: list[str] = field(default_factory=list)
    potential_causes: list[str] = field(default_factory=list)
    current_controls: list[str] = field(default_factory=list)
    
    # Impact estimates
    potential_cost_impact: Decimal | None = None
    potential_schedule_impact_days: int | None = None
    currency: str = "MAD"
    
    # Status
    status: str = "open"  # open, mitigating, monitoring, closed, occurred
    
    # Assignment
    owner_id: UUID | None = None
    identified_by: UUID | None = None
    
    # Dates
    identified_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    target_resolution_date: datetime | None = None
    resolved_date: datetime | None = None
    
    # Review schedule
    review_frequency_days: int = 14  # Default bi-weekly
    next_review_date: datetime | None = None
    last_review_date: datetime | None = None
    
    # Mitigations
    mitigations: list[MitigationAction] = field(default_factory=list)
    
    # Reviews
    reviews: list[RiskReview] = field(default_factory=list)
    
    # Tags and notes
    tags: list[str] = field(default_factory=list)
    notes: str | None = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_open_mitigations(self) -> list[MitigationAction]:
        """Get mitigations that are not yet complete."""
        return [
            m for m in self.mitigations
            if m.status not in (
                MitigationStatus.IMPLEMENTED,
                MitigationStatus.VERIFIED,
                MitigationStatus.CANCELLED,
            )
        ]
    
    def get_overdue_mitigations(self) -> list[MitigationAction]:
        """Get mitigations past their due date."""
        now = datetime.now(timezone.utc)
        return [
            m for m in self.mitigations
            if m.due_date and m.due_date < now
            and m.status not in (
                MitigationStatus.IMPLEMENTED,
                MitigationStatus.VERIFIED,
                MitigationStatus.CANCELLED,
            )
        ]
    
    def is_review_due(self) -> bool:
        """Check if a review is due."""
        if not self.next_review_date:
            return True
        return datetime.now(timezone.utc) >= self.next_review_date


@dataclass
class RiskTemplate:
    """A template for common NPI risks."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    category: NPIRiskCategory = NPIRiskCategory.OTHER
    phase: RiskPhase = RiskPhase.ALL_PHASES
    
    # Default scores
    default_severity: int = 5
    default_occurrence: int = 5
    default_detection: int = 5
    
    # Template content
    failure_mode_template: str = ""
    potential_effects_template: list[str] = field(default_factory=list)
    potential_causes_template: list[str] = field(default_factory=list)
    recommended_controls: list[str] = field(default_factory=list)
    recommended_mitigations: list[str] = field(default_factory=list)
    
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HeatMapCell:
    """A cell in the risk heat map."""
    
    severity: int
    occurrence: int
    count: int = 0
    risk_ids: list[UUID] = field(default_factory=list)
    
    @property
    def level(self) -> str:
        """Get risk level for this cell."""
        score = self.severity * self.occurrence
        if score >= 50:
            return "critical"
        if score >= 25:
            return "high"
        if score >= 10:
            return "medium"
        return "low"


class NPIRiskRegisterService:
    """
    Service for managing NPI-specific risks.
    
    Provides FMEA-style risk assessment with severity, occurrence,
    and detection scoring. Supports risk templates, mitigation
    tracking, and scheduled reviews.
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._risks: dict[UUID, NPIRisk] = {}
        self._templates: dict[UUID, RiskTemplate] = {}
        self._risk_counter: int = 0
        
        # Initialize default templates
        self._init_default_templates()
    
    def _init_default_templates(self) -> None:
        """Initialize default risk templates."""
        templates = [
            # Design risks
            RiskTemplate(
                name="Complex Geometry Risk",
                description="Risk from complex part geometry affecting manufacturability",
                category=NPIRiskCategory.DESIGN_COMPLEXITY,
                phase=RiskPhase.DFM,
                default_severity=6,
                default_occurrence=5,
                default_detection=4,
                failure_mode_template="Complex geometry causes manufacturing defects",
                potential_effects_template=[
                    "Increased scrap rate",
                    "Extended cycle times",
                    "Higher tooling costs",
                ],
                potential_causes_template=[
                    "Tight radii requirements",
                    "Deep draws",
                    "Multiple bends in sequence",
                ],
                recommended_controls=[
                    "DFM review with manufacturing",
                    "CAD simulation",
                    "Prototype validation",
                ],
                recommended_mitigations=[
                    "Simplify geometry where possible",
                    "Add intermediate forming operations",
                    "Review with tooling supplier",
                ],
            ),
            RiskTemplate(
                name="Tight Tolerance Risk",
                description="Risk from tolerances beyond process capability",
                category=NPIRiskCategory.TOLERANCE_CAPABILITY,
                phase=RiskPhase.DFM,
                default_severity=7,
                default_occurrence=5,
                default_detection=6,
                failure_mode_template="Process cannot consistently hold specified tolerances",
                potential_effects_template=[
                    "High rejection rate",
                    "Assembly fit issues",
                    "Customer complaints",
                ],
                potential_causes_template=[
                    "Tolerance tighter than Cpk capability",
                    "Material variation",
                    "Tool wear",
                ],
                recommended_controls=[
                    "Cpk study on similar parts",
                    "SPC monitoring",
                    "100% inspection on CTQs",
                ],
                recommended_mitigations=[
                    "Request tolerance review with customer",
                    "Upgrade equipment capability",
                    "Implement CMM inspection",
                ],
            ),
            # Supplier risks
            RiskTemplate(
                name="Single Source Supplier Risk",
                description="Risk from dependency on single supplier",
                category=NPIRiskCategory.SINGLE_SOURCE,
                phase=RiskPhase.PROTOTYPE,
                default_severity=8,
                default_occurrence=4,
                default_detection=3,
                failure_mode_template="Single supplier cannot meet demand or quality requirements",
                potential_effects_template=[
                    "Production stoppage",
                    "Schedule delays",
                    "Emergency expediting costs",
                ],
                potential_causes_template=[
                    "No qualified alternate supplier",
                    "Proprietary process",
                    "Capacity constraints",
                ],
                recommended_controls=[
                    "Supplier capacity verification",
                    "Safety stock",
                    "Regular supplier audits",
                ],
                recommended_mitigations=[
                    "Qualify alternate supplier",
                    "Develop in-house capability",
                    "Dual-source from start",
                ],
            ),
            RiskTemplate(
                name="Supplier Quality Risk",
                description="Risk of supplier quality issues affecting production",
                category=NPIRiskCategory.SUPPLIER_QUALITY,
                phase=RiskPhase.PILOT,
                default_severity=7,
                default_occurrence=5,
                default_detection=5,
                failure_mode_template="Incoming material/components fail quality requirements",
                potential_effects_template=[
                    "Production delays",
                    "Increased inspection costs",
                    "Customer escapes",
                ],
                potential_causes_template=[
                    "Insufficient supplier process controls",
                    "Specification misunderstanding",
                    "Capability gaps",
                ],
                recommended_controls=[
                    "PPAP approval",
                    "Incoming inspection",
                    "Supplier scorecard monitoring",
                ],
                recommended_mitigations=[
                    "Supplier development program",
                    "On-site quality audit",
                    "Statistical sampling plan",
                ],
            ),
            # Manufacturing risks
            RiskTemplate(
                name="Process Capability Risk",
                description="Risk that manufacturing process cannot meet requirements",
                category=NPIRiskCategory.PROCESS_CAPABILITY,
                phase=RiskPhase.PILOT,
                default_severity=7,
                default_occurrence=5,
                default_detection=4,
                failure_mode_template="Process Cpk below 1.33 for critical dimensions",
                potential_effects_template=[
                    "High scrap/rework",
                    "Sorting required",
                    "Customer concerns",
                ],
                potential_causes_template=[
                    "Equipment limitation",
                    "Operator skill variation",
                    "Tooling wear",
                ],
                recommended_controls=[
                    "Capability studies",
                    "SPC charts",
                    "Regular gage R&R",
                ],
                recommended_mitigations=[
                    "Equipment upgrade",
                    "Tool design improvement",
                    "Operator training",
                ],
            ),
            RiskTemplate(
                name="First Article Failure Risk",
                description="Risk of first article inspection failure",
                category=NPIRiskCategory.FIRST_ARTICLE_FAILURE,
                phase=RiskPhase.PROTOTYPE,
                default_severity=6,
                default_occurrence=4,
                default_detection=3,
                failure_mode_template="First article samples fail customer inspection",
                potential_effects_template=[
                    "Schedule delay",
                    "Re-work costs",
                    "Customer confidence impact",
                ],
                potential_causes_template=[
                    "Drawing interpretation error",
                    "Process setup issue",
                    "Material variance",
                ],
                recommended_controls=[
                    "Internal FAI before submission",
                    "Drawing review with customer",
                    "Sample approval process",
                ],
                recommended_mitigations=[
                    "Pre-submission review meeting",
                    "Pilot run before FAI",
                    "GD&T training",
                ],
            ),
            # Schedule risks
            RiskTemplate(
                name="Tooling Delay Risk",
                description="Risk of delays in tooling design or fabrication",
                category=NPIRiskCategory.TOOLING_DESIGN,
                phase=RiskPhase.DFM,
                default_severity=6,
                default_occurrence=5,
                default_detection=4,
                failure_mode_template="Tooling delivery delayed past SOP date",
                potential_effects_template=[
                    "Launch delay",
                    "Expediting costs",
                    "Customer penalties",
                ],
                potential_causes_template=[
                    "Design complexity underestimated",
                    "Tool supplier capacity",
                    "Multiple revision cycles",
                ],
                recommended_controls=[
                    "Tooling schedule tracking",
                    "Weekly status updates",
                    "Early tool trials",
                ],
                recommended_mitigations=[
                    "Front-load tooling design",
                    "Reserve backup tool shop",
                    "Parallel tool development",
                ],
            ),
        ]
        
        for template in templates:
            self._templates[template.id] = template
    
    # ---------------------
    # Risk Management
    # ---------------------
    
    def create_risk(
        self,
        title: str,
        description: str,
        category: NPIRiskCategory,
        npi_project_id: UUID | None = None,
        phase: RiskPhase = RiskPhase.ALL_PHASES,
        product_id: UUID | None = None,
        part_number: str | None = None,
        severity: int = 5,
        occurrence: int = 5,
        detection: int = 5,
        failure_mode: str | None = None,
        potential_effects: list[str] | None = None,
        potential_causes: list[str] | None = None,
        current_controls: list[str] | None = None,
        owner_id: UUID | None = None,
        identified_by: UUID | None = None,
        target_resolution_date: datetime | None = None,
        potential_cost_impact: Decimal | None = None,
        potential_schedule_impact_days: int | None = None,
        tags: list[str] | None = None,
    ) -> NPIRisk:
        """Create a new NPI risk."""
        self._risk_counter += 1
        risk_number = f"NPI-R-{self._risk_counter:04d}"
        
        # Calculate next review date
        next_review = datetime.now(timezone.utc) + timedelta(days=14)
        
        # Normalize scores
        sev = max(1, min(10, severity))
        occ = max(1, min(10, occurrence))
        det = max(1, min(10, detection))
        
        risk = NPIRisk(
            risk_number=risk_number,
            title=title,
            description=description,
            category=category,
            npi_project_id=npi_project_id,
            phase=phase,
            product_id=product_id,
            part_number=part_number,
            severity=sev,
            occurrence=occ,
            detection=det,
            initial_severity=sev,
            initial_occurrence=occ,
            initial_detection=det,
            failure_mode=failure_mode,
            potential_effects=potential_effects or [],
            potential_causes=potential_causes or [],
            current_controls=current_controls or [],
            owner_id=owner_id,
            identified_by=identified_by,
            target_resolution_date=target_resolution_date,
            potential_cost_impact=potential_cost_impact,
            potential_schedule_impact_days=potential_schedule_impact_days,
            tags=tags or [],
            next_review_date=next_review,
        )
        
        self._risks[risk.id] = risk
        return risk
    
    def create_risk_from_template(
        self,
        template_id: UUID,
        title: str,
        npi_project_id: UUID | None = None,
        product_id: UUID | None = None,
        part_number: str | None = None,
        owner_id: UUID | None = None,
        **overrides: Any,
    ) -> NPIRisk | None:
        """Create a risk from a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        return self.create_risk(
            title=title,
            description=template.description,
            category=template.category,
            npi_project_id=npi_project_id,
            phase=template.phase,
            product_id=product_id,
            part_number=part_number,
            severity=overrides.get("severity", template.default_severity),
            occurrence=overrides.get("occurrence", template.default_occurrence),
            detection=overrides.get("detection", template.default_detection),
            failure_mode=overrides.get("failure_mode", template.failure_mode_template),
            potential_effects=overrides.get(
                "potential_effects",
                template.potential_effects_template.copy(),
            ),
            potential_causes=overrides.get(
                "potential_causes",
                template.potential_causes_template.copy(),
            ),
            current_controls=overrides.get(
                "current_controls",
                template.recommended_controls.copy(),
            ),
            owner_id=owner_id,
            identified_by=overrides.get("identified_by"),
            target_resolution_date=overrides.get("target_resolution_date"),
            tags=overrides.get("tags"),
        )
    
    def get_risk(self, risk_id: UUID) -> NPIRisk | None:
        """Get a risk by ID."""
        return self._risks.get(risk_id)
    
    def get_risk_by_number(self, risk_number: str) -> NPIRisk | None:
        """Get a risk by its number."""
        for risk in self._risks.values():
            if risk.risk_number == risk_number:
                return risk
        return None
    
    def update_risk(
        self,
        risk_id: UUID,
        **updates: Any,
    ) -> NPIRisk | None:
        """Update risk fields."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        for key, value in updates.items():
            if hasattr(risk, key) and key not in ("id", "risk_number", "created_at"):
                # Validate score fields
                if key in ("severity", "occurrence", "detection") and value is not None:
                    value = max(1, min(10, value))
                setattr(risk, key, value)
        
        risk.updated_at = datetime.now(timezone.utc)
        return risk
    
    def update_risk_scores(
        self,
        risk_id: UUID,
        severity: int | None = None,
        occurrence: int | None = None,
        detection: int | None = None,
        updated_by: UUID | None = None,
        notes: str | None = None,
    ) -> NPIRisk | None:
        """Update risk S/O/D scores and create a review record."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        # Record previous scores for review
        review = RiskReview(
            risk_id=risk_id,
            reviewer_id=updated_by,
            previous_severity=risk.severity,
            previous_occurrence=risk.occurrence,
            previous_detection=risk.detection,
            previous_rpn=risk.rpn,
            completed_date=datetime.now(timezone.utc),
            status=ReviewStatus.COMPLETED,
            notes=notes,
        )
        
        # Update scores
        if severity is not None:
            risk.severity = max(1, min(10, severity))
        if occurrence is not None:
            risk.occurrence = max(1, min(10, occurrence))
        if detection is not None:
            risk.detection = max(1, min(10, detection))
        
        # Record new scores
        review.updated_severity = risk.severity
        review.updated_occurrence = risk.occurrence
        review.updated_detection = risk.detection
        review.updated_rpn = risk.rpn
        review.status_changed = (
            review.previous_rpn != review.updated_rpn
        )
        
        risk.reviews.append(review)
        risk.last_review_date = review.completed_date
        risk.next_review_date = review.completed_date + timedelta(days=risk.review_frequency_days)
        risk.updated_at = datetime.now(timezone.utc)
        
        return risk
    
    def close_risk(
        self,
        risk_id: UUID,
        closed_by: UUID,
        reason: str,
    ) -> NPIRisk | None:
        """Close a risk."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        risk.status = "closed"
        risk.resolved_date = datetime.now(timezone.utc)
        risk.notes = f"{risk.notes or ''}\n\nClosed: {reason}".strip()
        risk.updated_at = datetime.now(timezone.utc)
        
        return risk
    
    def mark_risk_occurred(
        self,
        risk_id: UUID,
        actual_impact: str,
        actual_cost: Decimal | None = None,
        lessons_learned: str | None = None,
    ) -> NPIRisk | None:
        """Mark that a risk has occurred."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        risk.status = "occurred"
        risk.notes = f"{risk.notes or ''}\n\nActual Impact: {actual_impact}".strip()
        if lessons_learned:
            risk.notes = f"{risk.notes}\n\nLessons Learned: {lessons_learned}"
        
        risk.updated_at = datetime.now(timezone.utc)
        
        return risk
    
    def list_risks(
        self,
        npi_project_id: UUID | None = None,
        phase: RiskPhase | None = None,
        category: NPIRiskCategory | None = None,
        priority: RiskPriority | None = None,
        status: str | None = None,
        owner_id: UUID | None = None,
        include_closed: bool = False,
    ) -> list[NPIRisk]:
        """List risks with optional filters."""
        risks = list(self._risks.values())
        
        if not include_closed:
            risks = [r for r in risks if r.status not in ("closed", "occurred")]
        
        if npi_project_id:
            risks = [r for r in risks if r.npi_project_id == npi_project_id]
        
        if phase:
            risks = [
                r for r in risks
                if r.phase == phase or r.phase == RiskPhase.ALL_PHASES
            ]
        
        if category:
            risks = [r for r in risks if r.category == category]
        
        if priority:
            risks = [r for r in risks if r.priority == priority]
        
        if status:
            risks = [r for r in risks if r.status == status]
        
        if owner_id:
            risks = [r for r in risks if r.owner_id == owner_id]
        
        # Sort by RPN descending (highest risk first)
        return sorted(risks, key=lambda r: r.rpn, reverse=True)
    
    # ---------------------
    # Mitigation Actions
    # ---------------------
    
    def add_mitigation(
        self,
        risk_id: UUID,
        description: str,
        action_type: str = "mitigate",
        owner_id: UUID | None = None,
        due_date: datetime | None = None,
        expected_severity_reduction: int = 0,
        expected_occurrence_reduction: int = 0,
        expected_detection_improvement: int = 0,
    ) -> MitigationAction | None:
        """Add a mitigation action to a risk."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        action = MitigationAction(
            risk_id=risk_id,
            description=description,
            action_type=action_type,
            owner_id=owner_id,
            due_date=due_date,
            expected_severity_reduction=expected_severity_reduction,
            expected_occurrence_reduction=expected_occurrence_reduction,
            expected_detection_improvement=expected_detection_improvement,
        )
        
        risk.mitigations.append(action)
        risk.status = "mitigating"
        risk.updated_at = datetime.now(timezone.utc)
        
        return action
    
    def update_mitigation_status(
        self,
        risk_id: UUID,
        mitigation_id: UUID,
        status: MitigationStatus,
        progress_percentage: int | None = None,
        progress_notes: str | None = None,
        completed_by: UUID | None = None,
    ) -> MitigationAction | None:
        """Update mitigation action status."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        mitigation = next(
            (m for m in risk.mitigations if m.id == mitigation_id),
            None,
        )
        if not mitigation:
            return None
        
        mitigation.status = status
        
        if progress_percentage is not None:
            mitigation.progress_percentage = max(0, min(100, progress_percentage))
        
        if progress_notes:
            mitigation.progress_notes = progress_notes
        
        if status in (MitigationStatus.IMPLEMENTED, MitigationStatus.VERIFIED):
            mitigation.completed_at = datetime.now(timezone.utc)
            mitigation.completed_by = completed_by
            mitigation.progress_percentage = 100
        
        mitigation.updated_at = datetime.now(timezone.utc)
        risk.updated_at = datetime.now(timezone.utc)
        
        return mitigation
    
    def verify_mitigation(
        self,
        risk_id: UUID,
        mitigation_id: UUID,
        verified_by: UUID,
        effectiveness_rating: int,
        effectiveness_notes: str | None = None,
    ) -> MitigationAction | None:
        """Verify a mitigation's effectiveness."""
        result = self.update_mitigation_status(
            risk_id,
            mitigation_id,
            MitigationStatus.VERIFIED,
            completed_by=verified_by,
        )
        
        if result:
            result.effectiveness_rating = max(1, min(5, effectiveness_rating))
            result.effectiveness_notes = effectiveness_notes
        
        return result
    
    def get_overdue_mitigations(
        self,
        npi_project_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Get all overdue mitigation actions."""
        overdue = []
        
        for risk in self._risks.values():
            if npi_project_id and risk.npi_project_id != npi_project_id:
                continue
            
            for mitigation in risk.get_overdue_mitigations():
                overdue.append({
                    "risk_id": risk.id,
                    "risk_number": risk.risk_number,
                    "risk_title": risk.title,
                    "mitigation_id": mitigation.id,
                    "mitigation_description": mitigation.description,
                    "due_date": mitigation.due_date,
                    "owner_id": mitigation.owner_id,
                    "days_overdue": (
                        datetime.now(timezone.utc) - mitigation.due_date
                    ).days if mitigation.due_date else 0,
                })
        
        return sorted(overdue, key=lambda x: x["days_overdue"], reverse=True)
    
    # ---------------------
    # Risk Reviews
    # ---------------------
    
    def schedule_review(
        self,
        risk_id: UUID,
        scheduled_date: datetime,
        reviewer_id: UUID | None = None,
    ) -> RiskReview | None:
        """Schedule a risk review."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        review = RiskReview(
            risk_id=risk_id,
            scheduled_date=scheduled_date,
            reviewer_id=reviewer_id,
            previous_severity=risk.severity,
            previous_occurrence=risk.occurrence,
            previous_detection=risk.detection,
            previous_rpn=risk.rpn,
        )
        
        risk.reviews.append(review)
        risk.next_review_date = scheduled_date
        
        return review
    
    def complete_review(
        self,
        risk_id: UUID,
        review_id: UUID,
        reviewer_id: UUID,
        updated_severity: int | None = None,
        updated_occurrence: int | None = None,
        updated_detection: int | None = None,
        new_mitigations_needed: bool = False,
        risk_escalated: bool = False,
        risk_closed: bool = False,
        notes: str | None = None,
    ) -> RiskReview | None:
        """Complete a scheduled risk review."""
        risk = self._risks.get(risk_id)
        if not risk:
            return None
        
        review = next(
            (r for r in risk.reviews if r.id == review_id),
            None,
        )
        if not review:
            return None
        
        # Update review
        review.completed_date = datetime.now(timezone.utc)
        review.reviewer_id = reviewer_id
        review.status = ReviewStatus.COMPLETED
        review.notes = notes
        
        review.new_mitigations_needed = new_mitigations_needed
        review.risk_escalated = risk_escalated
        review.risk_closed = risk_closed
        
        # Update risk scores if provided
        if updated_severity is not None:
            risk.severity = max(1, min(10, updated_severity))
        if updated_occurrence is not None:
            risk.occurrence = max(1, min(10, updated_occurrence))
        if updated_detection is not None:
            risk.detection = max(1, min(10, updated_detection))
        
        review.updated_severity = risk.severity
        review.updated_occurrence = risk.occurrence
        review.updated_detection = risk.detection
        review.updated_rpn = risk.rpn
        review.status_changed = review.previous_rpn != risk.rpn
        
        # Update risk
        risk.last_review_date = review.completed_date
        risk.next_review_date = review.completed_date + timedelta(
            days=risk.review_frequency_days,
        )
        risk.updated_at = datetime.now(timezone.utc)
        
        if risk_closed:
            risk.status = "closed"
            risk.resolved_date = review.completed_date
        
        return review
    
    def get_reviews_due(
        self,
        npi_project_id: UUID | None = None,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """Get risks with reviews due within specified days."""
        cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
        due = []
        
        for risk in self._risks.values():
            if risk.status in ("closed", "occurred"):
                continue
            
            if npi_project_id and risk.npi_project_id != npi_project_id:
                continue
            
            if risk.next_review_date and risk.next_review_date <= cutoff:
                days_until = (risk.next_review_date - datetime.now(timezone.utc)).days
                due.append({
                    "risk_id": risk.id,
                    "risk_number": risk.risk_number,
                    "title": risk.title,
                    "rpn": risk.rpn,
                    "priority": risk.priority.value,
                    "next_review_date": risk.next_review_date,
                    "days_until_due": days_until,
                    "overdue": days_until < 0,
                    "owner_id": risk.owner_id,
                })
        
        return sorted(due, key=lambda x: x["days_until_due"])
    
    # ---------------------
    # Templates
    # ---------------------
    
    def get_templates(
        self,
        category: NPIRiskCategory | None = None,
        phase: RiskPhase | None = None,
    ) -> list[RiskTemplate]:
        """Get risk templates."""
        templates = [t for t in self._templates.values() if t.is_active]
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if phase:
            templates = [
                t for t in templates
                if t.phase == phase or t.phase == RiskPhase.ALL_PHASES
            ]
        
        return templates
    
    def get_template(self, template_id: UUID) -> RiskTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def create_template(
        self,
        name: str,
        description: str,
        category: NPIRiskCategory,
        phase: RiskPhase = RiskPhase.ALL_PHASES,
        default_severity: int = 5,
        default_occurrence: int = 5,
        default_detection: int = 5,
        failure_mode_template: str = "",
        potential_effects_template: list[str] | None = None,
        potential_causes_template: list[str] | None = None,
        recommended_controls: list[str] | None = None,
        recommended_mitigations: list[str] | None = None,
    ) -> RiskTemplate:
        """Create a custom risk template."""
        template = RiskTemplate(
            name=name,
            description=description,
            category=category,
            phase=phase,
            default_severity=max(1, min(10, default_severity)),
            default_occurrence=max(1, min(10, default_occurrence)),
            default_detection=max(1, min(10, default_detection)),
            failure_mode_template=failure_mode_template,
            potential_effects_template=potential_effects_template or [],
            potential_causes_template=potential_causes_template or [],
            recommended_controls=recommended_controls or [],
            recommended_mitigations=recommended_mitigations or [],
        )
        
        self._templates[template.id] = template
        return template
    
    # ---------------------
    # Analytics & Reporting
    # ---------------------
    
    def get_heat_map(
        self,
        npi_project_id: UUID | None = None,
    ) -> list[HeatMapCell]:
        """Generate a risk heat map (Severity x Occurrence matrix)."""
        # Create 10x10 matrix
        cells: dict[tuple[int, int], HeatMapCell] = {}
        for s in range(1, 11):
            for o in range(1, 11):
                cells[(s, o)] = HeatMapCell(severity=s, occurrence=o)
        
        # Populate with risks
        for risk in self._risks.values():
            if risk.status in ("closed", "occurred"):
                continue
            
            if npi_project_id and risk.npi_project_id != npi_project_id:
                continue
            
            cell = cells[(risk.severity, risk.occurrence)]
            cell.count += 1
            cell.risk_ids.append(risk.id)
        
        # Return only cells with risks
        return [cell for cell in cells.values() if cell.count > 0]
    
    def get_risk_summary(
        self,
        npi_project_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Get summary statistics for risks."""
        risks = [
            r for r in self._risks.values()
            if r.status not in ("closed", "occurred")
        ]
        
        if npi_project_id:
            risks = [r for r in risks if r.npi_project_id == npi_project_id]
        
        if not risks:
            return {
                "total_open": 0,
                "by_priority": {},
                "by_category": {},
                "by_phase": {},
                "average_rpn": 0,
                "max_rpn": 0,
                "overdue_reviews": 0,
                "overdue_mitigations": 0,
            }
        
        # Priority counts
        by_priority = {}
        for priority in RiskPriority:
            count = len([r for r in risks if r.priority == priority])
            by_priority[priority.value] = count
        
        # Category counts
        by_category = {}
        for risk in risks:
            cat = risk.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        
        # Phase counts
        by_phase = {}
        for risk in risks:
            phase = risk.phase.value
            by_phase[phase] = by_phase.get(phase, 0) + 1
        
        # Calculate averages
        rpns = [r.rpn for r in risks]
        avg_rpn = sum(rpns) / len(rpns) if rpns else 0
        max_rpn = max(rpns) if rpns else 0
        
        # Overdue counts
        now = datetime.now(timezone.utc)
        overdue_reviews = len([
            r for r in risks
            if r.next_review_date and r.next_review_date < now
        ])
        
        overdue_mitigations = sum(
            len(r.get_overdue_mitigations()) for r in risks
        )
        
        return {
            "total_open": len(risks),
            "by_priority": by_priority,
            "by_category": by_category,
            "by_phase": by_phase,
            "average_rpn": round(avg_rpn, 1),
            "max_rpn": max_rpn,
            "overdue_reviews": overdue_reviews,
            "overdue_mitigations": overdue_mitigations,
        }
    
    def get_project_risk_report(
        self,
        npi_project_id: UUID,
    ) -> dict[str, Any]:
        """Generate comprehensive risk report for an NPI project."""
        risks = [
            r for r in self._risks.values()
            if r.npi_project_id == npi_project_id
        ]
        
        open_risks = [r for r in risks if r.status not in ("closed", "occurred")]
        closed_risks = [r for r in risks if r.status == "closed"]
        occurred_risks = [r for r in risks if r.status == "occurred"]
        
        critical_risks = [r for r in open_risks if r.priority == RiskPriority.CRITICAL]
        high_risks = [r for r in open_risks if r.priority == RiskPriority.HIGH]
        
        return {
            "project_id": npi_project_id,
            "total_risks": len(risks),
            "open_risks": len(open_risks),
            "closed_risks": len(closed_risks),
            "occurred_risks": len(occurred_risks),
            "critical_risks": len(critical_risks),
            "high_risks": len(high_risks),
            "top_risks": [
                {
                    "id": r.id,
                    "risk_number": r.risk_number,
                    "title": r.title,
                    "rpn": r.rpn,
                    "priority": r.priority.value,
                    "category": r.category.value,
                }
                for r in sorted(open_risks, key=lambda x: x.rpn, reverse=True)[:5]
            ],
            "heat_map": self.get_heat_map(npi_project_id),
            "overdue_mitigations": self.get_overdue_mitigations(npi_project_id),
            "reviews_due": self.get_reviews_due(npi_project_id),
        }
    
    def get_rpn_trend(
        self,
        risk_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get RPN trend over time for a risk."""
        risk = self._risks.get(risk_id)
        if not risk:
            return []
        
        trend = []
        
        # Add initial point using initial scores
        trend.append({
            "date": risk.created_at,
            "rpn": risk.initial_rpn,
            "event": "created",
        })
        
        # Add review points
        for review in risk.reviews:
            if review.status == ReviewStatus.COMPLETED and review.updated_rpn:
                trend.append({
                    "date": review.completed_date,
                    "rpn": review.updated_rpn,
                    "event": "review",
                })
        
        return sorted(trend, key=lambda x: x["date"])
