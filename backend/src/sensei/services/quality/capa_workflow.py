"""
CAPA Workflow Integration Service.

Handles Corrective and Preventive Action (CAPA) workflow:
- Auto-create CAPA from NC when severity = CRITICAL or recurrence detected
- Link CAPA to A3 reports and Standard Work
- Enforce closure gates (verification, effectiveness)
- Track CAPA lifecycle and metrics
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4


class NCType(str, Enum):
    """Type of Non-Conformance."""
    
    INTERNAL = "internal"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    PROCESS = "process"
    PRODUCT = "product"
    DOCUMENTATION = "documentation"


class NCSeverity(str, Enum):
    """Severity level of a Non-Conformance."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CAPAType(str, Enum):
    """Type of CAPA."""
    
    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    CORRECTIVE_AND_PREVENTIVE = "corrective_and_preventive"


class CAPAStatus(str, Enum):
    """Status of a CAPA."""
    
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    OPEN = "open"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    ACTION_PLANNING = "action_planning"
    IMPLEMENTING = "implementing"
    VERIFICATION = "verification"
    EFFECTIVENESS_CHECK = "effectiveness_check"
    PENDING_CLOSURE = "pending_closure"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CAPAPriority(str, Enum):
    """Priority level for CAPA."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ActionStatus(str, Enum):
    """Status of a corrective/preventive action."""
    
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ClosureGateType(str, Enum):
    """Types of closure gates."""
    
    ROOT_CAUSE_IDENTIFIED = "root_cause_identified"
    CONTAINMENT_ACTIONS_COMPLETE = "containment_actions_complete"
    CORRECTIVE_ACTIONS_COMPLETE = "corrective_actions_complete"
    PREVENTIVE_ACTIONS_COMPLETE = "preventive_actions_complete"
    VERIFICATION_COMPLETE = "verification_complete"
    EFFECTIVENESS_VERIFIED = "effectiveness_verified"
    DOCUMENTATION_UPDATED = "documentation_updated"
    STANDARD_WORK_UPDATED = "standard_work_updated"
    TRAINING_COMPLETE = "training_complete"
    MANAGER_APPROVAL = "manager_approval"
    QUALITY_APPROVAL = "quality_approval"


class LinkType(str, Enum):
    """Types of linked entities."""
    
    A3_REPORT = "a3_report"
    STANDARD_WORK = "standard_work"
    NC_RECORD = "nc_record"
    AUDIT_FINDING = "audit_finding"
    RISK = "risk"
    FMEA = "fmea"
    CONTROL_PLAN = "control_plan"
    TRAINING_RECORD = "training_record"


@dataclass
class NonConformance:
    """A Non-Conformance record."""
    
    id: UUID
    nc_number: str
    nc_type: NCType
    severity: NCSeverity
    title: str
    description: str
    
    # Source info
    detected_by: UUID
    detected_at: datetime
    detected_location: Optional[str] = None
    
    # Product/process info
    product_id: Optional[UUID] = None
    product_name: Optional[str] = None
    process_id: Optional[UUID] = None
    process_name: Optional[str] = None
    work_order_id: Optional[UUID] = None
    
    # Defect details
    defect_code: Optional[str] = None
    defect_category: Optional[str] = None
    quantity_affected: int = 1
    
    # Recurrence tracking
    is_recurrence: bool = False
    related_nc_ids: list[UUID] = field(default_factory=list)
    recurrence_count: int = 0
    
    # Status
    is_closed: bool = False
    closed_at: Optional[datetime] = None
    
    # CAPA link
    capa_id: Optional[UUID] = None
    capa_required: bool = False


@dataclass
class RootCauseAnalysis:
    """Root cause analysis details."""
    
    id: UUID
    capa_id: UUID
    method: str  # 5-why, fishbone, 8D, etc.
    analysis_details: str
    root_causes: list[str]
    contributing_factors: list[str] = field(default_factory=list)
    performed_by: UUID = field(default_factory=uuid4)
    performed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None


@dataclass
class CorrectiveAction:
    """A corrective or preventive action."""
    
    id: UUID
    capa_id: UUID
    action_type: str  # "containment", "corrective", "preventive"
    description: str
    expected_result: str
    assigned_to: UUID
    due_date: date
    status: ActionStatus = ActionStatus.PLANNED
    priority: CAPAPriority = CAPAPriority.MEDIUM
    
    # Tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    
    # Verification
    verification_method: Optional[str] = None
    verification_result: Optional[str] = None
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    
    # Notes
    notes: Optional[str] = None
    evidence_links: list[str] = field(default_factory=list)


@dataclass
class ClosureGate:
    """A closure gate requirement."""
    
    id: UUID
    capa_id: UUID
    gate_type: ClosureGateType
    description: str
    is_required: bool
    is_passed: bool = False
    passed_at: Optional[datetime] = None
    passed_by: Optional[UUID] = None
    evidence: Optional[str] = None
    notes: Optional[str] = None
    order: int = 0


@dataclass
class EntityLink:
    """A link to another entity."""
    
    id: UUID
    capa_id: UUID
    link_type: LinkType
    linked_entity_id: UUID
    linked_entity_name: str
    link_description: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID = field(default_factory=uuid4)


@dataclass
class EffectivenessCheck:
    """Effectiveness verification record."""
    
    id: UUID
    capa_id: UUID
    check_date: date
    performed_by: UUID
    method: str
    criteria: str
    result: str
    is_effective: bool
    evidence: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CAPA:
    """A Corrective and Preventive Action record."""
    
    id: UUID
    capa_number: str
    capa_type: CAPAType
    status: CAPAStatus
    priority: CAPAPriority
    title: str
    description: str
    
    # Source
    source_nc_id: Optional[UUID] = None
    source_audit_finding_id: Optional[UUID] = None
    source_customer_complaint_id: Optional[UUID] = None
    source_description: Optional[str] = None
    
    # Problem statement
    problem_statement: str = ""
    immediate_containment: Optional[str] = None
    
    # Ownership
    owner_id: UUID = field(default_factory=uuid4)
    created_by: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Timeline
    target_completion_date: Optional[date] = None
    actual_completion_date: Optional[date] = None
    
    # Root cause
    root_cause_analysis: Optional[RootCauseAnalysis] = None
    
    # Actions
    actions: list[CorrectiveAction] = field(default_factory=list)
    
    # Closure gates
    closure_gates: list[ClosureGate] = field(default_factory=list)
    
    # Links
    linked_entities: list[EntityLink] = field(default_factory=list)
    
    # Effectiveness
    effectiveness_checks: list[EffectivenessCheck] = field(default_factory=list)
    is_effective: Optional[bool] = None
    
    # Approval
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    closed_by: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    
    # Recurrence
    is_recurrence: bool = False
    related_capa_ids: list[UUID] = field(default_factory=list)


@dataclass
class CAPACreationResult:
    """Result of creating a CAPA."""
    
    success: bool
    capa: Optional[CAPA]
    auto_created: bool = False
    creation_reason: Optional[str] = None
    linked_nc_id: Optional[UUID] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ClosureCheckResult:
    """Result of checking closure readiness."""
    
    can_close: bool
    passed_gates: list[ClosureGate]
    failed_gates: list[ClosureGate]
    pending_actions: list[CorrectiveAction]
    missing_requirements: list[str]


@dataclass
class RecurrenceCheckResult:
    """Result of checking for recurrence."""
    
    is_recurrence: bool
    recurrence_count: int
    related_nc_ids: list[UUID]
    related_capa_ids: list[UUID]
    time_period_days: int
    recommendation: str


@dataclass
class CAPAConfig:
    """Configuration for CAPA workflow."""
    
    auto_create_on_critical: bool = True
    auto_create_on_recurrence: bool = True
    recurrence_threshold: int = 2  # Number of occurrences to trigger
    recurrence_period_days: int = 90  # Time window for recurrence check
    default_target_days: int = 30  # Default days to complete CAPA
    require_root_cause: bool = True
    require_effectiveness_check: bool = True
    effectiveness_check_days: int = 30  # Days after closure for effectiveness check
    require_manager_approval: bool = True
    require_quality_approval: bool = True


# Default closure gates
DEFAULT_CLOSURE_GATES: list[tuple[ClosureGateType, str, bool]] = [
    (ClosureGateType.ROOT_CAUSE_IDENTIFIED, "Root cause must be identified and documented", True),
    (ClosureGateType.CONTAINMENT_ACTIONS_COMPLETE, "All containment actions completed", True),
    (ClosureGateType.CORRECTIVE_ACTIONS_COMPLETE, "All corrective actions completed and verified", True),
    (ClosureGateType.PREVENTIVE_ACTIONS_COMPLETE, "Preventive actions implemented", False),
    (ClosureGateType.VERIFICATION_COMPLETE, "Verification of actions effectiveness", True),
    (ClosureGateType.EFFECTIVENESS_VERIFIED, "Effectiveness check completed and verified", True),
    (ClosureGateType.DOCUMENTATION_UPDATED, "All relevant documentation updated", True),
    (ClosureGateType.STANDARD_WORK_UPDATED, "Standard work updated if applicable", False),
    (ClosureGateType.TRAINING_COMPLETE, "Required training completed", False),
    (ClosureGateType.MANAGER_APPROVAL, "Manager approval obtained", True),
    (ClosureGateType.QUALITY_APPROVAL, "Quality approval obtained", True),
]


class CAPAWorkflowIntegrationService:
    """
    Service for CAPA workflow integration.
    
    Handles:
    - Auto-creation of CAPA from NC
    - Root cause analysis tracking
    - Action management
    - Closure gate enforcement
    - Entity linking (A3, Standard Work)
    - Effectiveness verification
    """
    
    def __init__(self, config: Optional[CAPAConfig] = None) -> None:
        """Initialize the service."""
        self.config = config or CAPAConfig()
        
        self._capas: dict[UUID, CAPA] = {}
        self._ncs: dict[UUID, NonConformance] = {}
        self._next_capa_number = 1
        self._next_nc_number = 1
    
    def _generate_capa_number(self) -> str:
        """Generate a unique CAPA number."""
        number = f"CAPA-{datetime.now(timezone.utc).year}-{self._next_capa_number:04d}"
        self._next_capa_number += 1
        return number
    
    def _generate_nc_number(self) -> str:
        """Generate a unique NC number."""
        number = f"NC-{datetime.now(timezone.utc).year}-{self._next_nc_number:04d}"
        self._next_nc_number += 1
        return number
    
    # Non-Conformance Management
    
    def register_nc(
        self,
        nc_type: NCType,
        severity: NCSeverity,
        title: str,
        description: str,
        detected_by: UUID,
        product_id: Optional[UUID] = None,
        product_name: Optional[str] = None,
        process_id: Optional[UUID] = None,
        process_name: Optional[str] = None,
        defect_code: Optional[str] = None,
        defect_category: Optional[str] = None,
        quantity_affected: int = 1,
    ) -> tuple[NonConformance, Optional[CAPACreationResult]]:
        """
        Register a new Non-Conformance.
        
        May automatically create a CAPA based on severity or recurrence.
        
        Returns:
            Tuple of (NC, CAPACreationResult if auto-created)
        """
        # Check for recurrence
        recurrence_result = self._check_recurrence(
            nc_type=nc_type,
            product_id=product_id,
            process_id=process_id,
            defect_code=defect_code,
            defect_category=defect_category,
        )
        
        nc = NonConformance(
            id=uuid4(),
            nc_number=self._generate_nc_number(),
            nc_type=nc_type,
            severity=severity,
            title=title,
            description=description,
            detected_by=detected_by,
            detected_at=datetime.now(timezone.utc),
            product_id=product_id,
            product_name=product_name,
            process_id=process_id,
            process_name=process_name,
            defect_code=defect_code,
            defect_category=defect_category,
            quantity_affected=quantity_affected,
            is_recurrence=recurrence_result.is_recurrence,
            related_nc_ids=recurrence_result.related_nc_ids,
            recurrence_count=recurrence_result.recurrence_count,
        )
        
        self._ncs[nc.id] = nc
        
        # Check if CAPA should be auto-created
        capa_result = None
        
        if self.config.auto_create_on_critical and severity == NCSeverity.CRITICAL:
            nc.capa_required = True
            capa_result = self.create_capa_from_nc(
                nc_id=nc.id,
                created_by=detected_by,
                auto_created=True,
                creation_reason="Auto-created due to CRITICAL severity",
            )
        elif self.config.auto_create_on_recurrence and recurrence_result.is_recurrence:
            nc.capa_required = True
            capa_result = self.create_capa_from_nc(
                nc_id=nc.id,
                created_by=detected_by,
                auto_created=True,
                creation_reason=f"Auto-created due to recurrence ({recurrence_result.recurrence_count} occurrences)",
            )
        
        return nc, capa_result
    
    def _check_recurrence(
        self,
        nc_type: NCType,
        product_id: Optional[UUID],
        process_id: Optional[UUID],
        defect_code: Optional[str],
        defect_category: Optional[str],
    ) -> RecurrenceCheckResult:
        """Check for recurrence of similar NCs."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.recurrence_period_days)
        
        related_ncs: list[NonConformance] = []
        related_capa_ids: list[UUID] = []
        
        for nc in self._ncs.values():
            if nc.detected_at < cutoff_date:
                continue
            
            # Check for similarity
            is_similar = False
            
            # Same product
            if product_id and nc.product_id == product_id:
                if defect_code and nc.defect_code == defect_code:
                    is_similar = True
                elif defect_category and nc.defect_category == defect_category:
                    is_similar = True
            
            # Same process
            if process_id and nc.process_id == process_id:
                if defect_code and nc.defect_code == defect_code:
                    is_similar = True
                elif defect_category and nc.defect_category == defect_category:
                    is_similar = True
            
            # Same defect code regardless of product/process
            if defect_code and nc.defect_code == defect_code:
                is_similar = True
            
            if is_similar:
                related_ncs.append(nc)
                if nc.capa_id:
                    related_capa_ids.append(nc.capa_id)
        
        is_recurrence = len(related_ncs) >= self.config.recurrence_threshold
        
        recommendation = "No action required"
        if is_recurrence:
            recommendation = f"CAPA recommended: {len(related_ncs)} similar NCs in {self.config.recurrence_period_days} days"
        elif len(related_ncs) > 0:
            remaining = self.config.recurrence_threshold - len(related_ncs)
            recommendation = f"Monitor: {remaining} more occurrence(s) will trigger recurrence"
        
        return RecurrenceCheckResult(
            is_recurrence=is_recurrence,
            recurrence_count=len(related_ncs),
            related_nc_ids=[nc.id for nc in related_ncs],
            related_capa_ids=list(set(related_capa_ids)),
            time_period_days=self.config.recurrence_period_days,
            recommendation=recommendation,
        )
    
    def get_nc(self, nc_id: UUID) -> Optional[NonConformance]:
        """Get an NC by ID."""
        return self._ncs.get(nc_id)
    
    def list_ncs(
        self,
        nc_type: Optional[NCType] = None,
        severity: Optional[NCSeverity] = None,
        include_closed: bool = False,
    ) -> list[NonConformance]:
        """List NCs with optional filters."""
        ncs = list(self._ncs.values())
        
        if nc_type:
            ncs = [nc for nc in ncs if nc.nc_type == nc_type]
        
        if severity:
            ncs = [nc for nc in ncs if nc.severity == severity]
        
        if not include_closed:
            ncs = [nc for nc in ncs if not nc.is_closed]
        
        return sorted(ncs, key=lambda n: n.detected_at, reverse=True)
    
    # CAPA Management
    
    def create_capa_from_nc(
        self,
        nc_id: UUID,
        created_by: UUID,
        capa_type: CAPAType = CAPAType.CORRECTIVE_AND_PREVENTIVE,
        priority: Optional[CAPAPriority] = None,
        owner_id: Optional[UUID] = None,
        auto_created: bool = False,
        creation_reason: Optional[str] = None,
    ) -> CAPACreationResult:
        """Create a CAPA from a Non-Conformance."""
        nc = self._ncs.get(nc_id)
        if not nc:
            return CAPACreationResult(
                success=False,
                capa=None,
                creation_reason="NC not found",
            )
        
        # Determine priority from severity
        if priority is None:
            if nc.severity == NCSeverity.CRITICAL:
                priority = CAPAPriority.URGENT
            elif nc.severity == NCSeverity.HIGH:
                priority = CAPAPriority.HIGH
            elif nc.severity == NCSeverity.MEDIUM:
                priority = CAPAPriority.MEDIUM
            else:
                priority = CAPAPriority.LOW
        
        # Create CAPA
        capa = CAPA(
            id=uuid4(),
            capa_number=self._generate_capa_number(),
            capa_type=capa_type,
            status=CAPAStatus.OPEN,
            priority=priority,
            title=f"CAPA for: {nc.title}",
            description=nc.description,
            source_nc_id=nc.id,
            source_description=f"NC: {nc.nc_number} - {nc.title}",
            problem_statement=nc.description,
            owner_id=owner_id or created_by,
            created_by=created_by,
            target_completion_date=date.today() + timedelta(days=self.config.default_target_days),
            is_recurrence=nc.is_recurrence,
            related_capa_ids=[],
        )
        
        # Add default closure gates
        capa.closure_gates = self._create_default_closure_gates(capa.id)
        
        # Link NC to CAPA
        nc.capa_id = capa.id
        
        self._capas[capa.id] = capa
        
        return CAPACreationResult(
            success=True,
            capa=capa,
            auto_created=auto_created,
            creation_reason=creation_reason,
            linked_nc_id=nc.id,
        )
    
    def create_capa(
        self,
        title: str,
        description: str,
        created_by: UUID,
        capa_type: CAPAType = CAPAType.CORRECTIVE_AND_PREVENTIVE,
        priority: CAPAPriority = CAPAPriority.MEDIUM,
        owner_id: Optional[UUID] = None,
        source_description: Optional[str] = None,
        target_days: Optional[int] = None,
    ) -> CAPA:
        """Create a standalone CAPA."""
        capa = CAPA(
            id=uuid4(),
            capa_number=self._generate_capa_number(),
            capa_type=capa_type,
            status=CAPAStatus.OPEN,
            priority=priority,
            title=title,
            description=description,
            source_description=source_description,
            problem_statement=description,
            owner_id=owner_id or created_by,
            created_by=created_by,
            target_completion_date=date.today() + timedelta(
                days=target_days or self.config.default_target_days
            ),
        )
        
        # Add default closure gates
        capa.closure_gates = self._create_default_closure_gates(capa.id)
        
        self._capas[capa.id] = capa
        return capa
    
    def _create_default_closure_gates(self, capa_id: UUID) -> list[ClosureGate]:
        """Create default closure gates for a CAPA."""
        gates = []
        for order, (gate_type, description, required) in enumerate(DEFAULT_CLOSURE_GATES):
            gate = ClosureGate(
                id=uuid4(),
                capa_id=capa_id,
                gate_type=gate_type,
                description=description,
                is_required=required,
                order=order,
            )
            gates.append(gate)
        return gates
    
    def get_capa(self, capa_id: UUID) -> Optional[CAPA]:
        """Get a CAPA by ID."""
        return self._capas.get(capa_id)
    
    def list_capas(
        self,
        status: Optional[CAPAStatus] = None,
        priority: Optional[CAPAPriority] = None,
        owner_id: Optional[UUID] = None,
        include_closed: bool = False,
    ) -> list[CAPA]:
        """List CAPAs with optional filters."""
        capas = list(self._capas.values())
        
        if status:
            capas = [c for c in capas if c.status == status]
        
        if priority:
            capas = [c for c in capas if c.priority == priority]
        
        if owner_id:
            capas = [c for c in capas if c.owner_id == owner_id]
        
        if not include_closed:
            capas = [c for c in capas if c.status not in (CAPAStatus.CLOSED, CAPAStatus.CANCELLED)]
        
        return sorted(capas, key=lambda c: c.created_at, reverse=True)
    
    # Root Cause Analysis
    
    def add_root_cause_analysis(
        self,
        capa_id: UUID,
        method: str,
        analysis_details: str,
        root_causes: list[str],
        performed_by: UUID,
        contributing_factors: Optional[list[str]] = None,
    ) -> Optional[RootCauseAnalysis]:
        """Add root cause analysis to a CAPA."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        rca = RootCauseAnalysis(
            id=uuid4(),
            capa_id=capa_id,
            method=method,
            analysis_details=analysis_details,
            root_causes=root_causes,
            contributing_factors=contributing_factors or [],
            performed_by=performed_by,
        )
        
        capa.root_cause_analysis = rca
        
        # Update status
        if capa.status == CAPAStatus.OPEN:
            capa.status = CAPAStatus.ROOT_CAUSE_ANALYSIS
        
        return rca
    
    def verify_root_cause(
        self,
        capa_id: UUID,
        verified_by: UUID,
    ) -> bool:
        """Verify root cause analysis."""
        capa = self._capas.get(capa_id)
        if not capa or not capa.root_cause_analysis:
            return False
        
        capa.root_cause_analysis.verified = True
        capa.root_cause_analysis.verified_by = verified_by
        capa.root_cause_analysis.verified_at = datetime.now(timezone.utc)
        
        # Pass the root cause gate
        for gate in capa.closure_gates:
            if gate.gate_type == ClosureGateType.ROOT_CAUSE_IDENTIFIED:
                gate.is_passed = True
                gate.passed_at = datetime.now(timezone.utc)
                gate.passed_by = verified_by
                break
        
        return True
    
    # Action Management
    
    def add_action(
        self,
        capa_id: UUID,
        action_type: str,
        description: str,
        expected_result: str,
        assigned_to: UUID,
        due_date: date,
        priority: CAPAPriority = CAPAPriority.MEDIUM,
        verification_method: Optional[str] = None,
    ) -> Optional[CorrectiveAction]:
        """Add a corrective/preventive action to a CAPA."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        action = CorrectiveAction(
            id=uuid4(),
            capa_id=capa_id,
            action_type=action_type,
            description=description,
            expected_result=expected_result,
            assigned_to=assigned_to,
            due_date=due_date,
            priority=priority,
            verification_method=verification_method,
        )
        
        capa.actions.append(action)
        
        # Update status
        if capa.status in (CAPAStatus.ROOT_CAUSE_ANALYSIS, CAPAStatus.OPEN):
            capa.status = CAPAStatus.ACTION_PLANNING
        
        return action
    
    def start_action(self, capa_id: UUID, action_id: UUID) -> Optional[CorrectiveAction]:
        """Mark an action as started."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        for action in capa.actions:
            if action.id == action_id:
                action.status = ActionStatus.IN_PROGRESS
                action.started_at = datetime.now(timezone.utc)
                
                # Update CAPA status
                if capa.status == CAPAStatus.ACTION_PLANNING:
                    capa.status = CAPAStatus.IMPLEMENTING
                
                return action
        
        return None
    
    def complete_action(
        self,
        capa_id: UUID,
        action_id: UUID,
        completed_by: UUID,
        notes: Optional[str] = None,
        evidence_links: Optional[list[str]] = None,
    ) -> Optional[CorrectiveAction]:
        """Mark an action as completed."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        for action in capa.actions:
            if action.id == action_id:
                action.status = ActionStatus.COMPLETED
                action.completed_at = datetime.now(timezone.utc)
                action.completed_by = completed_by
                if notes:
                    action.notes = notes
                if evidence_links:
                    action.evidence_links = evidence_links
                return action
        
        return None
    
    def verify_action(
        self,
        capa_id: UUID,
        action_id: UUID,
        verified_by: UUID,
        verification_result: str,
    ) -> Optional[CorrectiveAction]:
        """Verify a completed action."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        for action in capa.actions:
            if action.id == action_id:
                action.status = ActionStatus.VERIFIED
                action.verified_by = verified_by
                action.verified_at = datetime.now(timezone.utc)
                action.verification_result = verification_result
                return action
        
        return None
    
    def get_overdue_actions(self, capa_id: Optional[UUID] = None) -> list[CorrectiveAction]:
        """Get overdue actions."""
        today = date.today()
        overdue = []
        
        capas = [self._capas[capa_id]] if capa_id else list(self._capas.values())
        
        for capa in capas:
            if capa.status in (CAPAStatus.CLOSED, CAPAStatus.CANCELLED):
                continue
            
            for action in capa.actions:
                if action.status in (ActionStatus.PLANNED, ActionStatus.IN_PROGRESS):
                    if action.due_date < today:
                        action.status = ActionStatus.OVERDUE
                        overdue.append(action)
        
        return overdue
    
    # Entity Linking
    
    def link_a3_report(
        self,
        capa_id: UUID,
        a3_id: UUID,
        a3_name: str,
        created_by: UUID,
        description: Optional[str] = None,
    ) -> Optional[EntityLink]:
        """Link an A3 report to a CAPA."""
        return self._add_entity_link(
            capa_id=capa_id,
            link_type=LinkType.A3_REPORT,
            entity_id=a3_id,
            entity_name=a3_name,
            created_by=created_by,
            description=description,
        )
    
    def link_standard_work(
        self,
        capa_id: UUID,
        standard_work_id: UUID,
        standard_work_name: str,
        created_by: UUID,
        description: Optional[str] = None,
    ) -> Optional[EntityLink]:
        """Link Standard Work to a CAPA."""
        return self._add_entity_link(
            capa_id=capa_id,
            link_type=LinkType.STANDARD_WORK,
            entity_id=standard_work_id,
            entity_name=standard_work_name,
            created_by=created_by,
            description=description,
        )
    
    def link_training_record(
        self,
        capa_id: UUID,
        training_id: UUID,
        training_name: str,
        created_by: UUID,
        description: Optional[str] = None,
    ) -> Optional[EntityLink]:
        """Link a training record to a CAPA."""
        return self._add_entity_link(
            capa_id=capa_id,
            link_type=LinkType.TRAINING_RECORD,
            entity_id=training_id,
            entity_name=training_name,
            created_by=created_by,
            description=description,
        )
    
    def _add_entity_link(
        self,
        capa_id: UUID,
        link_type: LinkType,
        entity_id: UUID,
        entity_name: str,
        created_by: UUID,
        description: Optional[str] = None,
    ) -> Optional[EntityLink]:
        """Add an entity link to a CAPA."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        link = EntityLink(
            id=uuid4(),
            capa_id=capa_id,
            link_type=link_type,
            linked_entity_id=entity_id,
            linked_entity_name=entity_name,
            link_description=description,
            created_by=created_by,
        )
        
        capa.linked_entities.append(link)
        return link
    
    def get_linked_entities(
        self,
        capa_id: UUID,
        link_type: Optional[LinkType] = None,
    ) -> list[EntityLink]:
        """Get linked entities for a CAPA."""
        capa = self._capas.get(capa_id)
        if not capa:
            return []
        
        links = capa.linked_entities
        
        if link_type:
            links = [l for l in links if l.link_type == link_type]
        
        return links
    
    # Closure Gates
    
    def pass_closure_gate(
        self,
        capa_id: UUID,
        gate_type: ClosureGateType,
        passed_by: UUID,
        evidence: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ClosureGate]:
        """Pass a closure gate."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        for gate in capa.closure_gates:
            if gate.gate_type == gate_type:
                gate.is_passed = True
                gate.passed_at = datetime.now(timezone.utc)
                gate.passed_by = passed_by
                gate.evidence = evidence
                gate.notes = notes
                return gate
        
        return None
    
    def check_closure_readiness(self, capa_id: UUID) -> ClosureCheckResult:
        """Check if a CAPA is ready to be closed."""
        capa = self._capas.get(capa_id)
        if not capa:
            return ClosureCheckResult(
                can_close=False,
                passed_gates=[],
                failed_gates=[],
                pending_actions=[],
                missing_requirements=["CAPA not found"],
            )
        
        passed_gates = []
        failed_gates = []
        pending_actions = []
        missing_requirements = []
        
        # Check gates
        for gate in capa.closure_gates:
            if gate.is_passed:
                passed_gates.append(gate)
            elif gate.is_required:
                failed_gates.append(gate)
                missing_requirements.append(f"Gate not passed: {gate.description}")
        
        # Check actions
        for action in capa.actions:
            if action.status not in (ActionStatus.VERIFIED, ActionStatus.CANCELLED):
                pending_actions.append(action)
                missing_requirements.append(f"Action pending: {action.description}")
        
        # Check root cause
        if self.config.require_root_cause:
            if not capa.root_cause_analysis or not capa.root_cause_analysis.verified:
                missing_requirements.append("Root cause analysis not verified")
        
        can_close = len(failed_gates) == 0 and len(pending_actions) == 0 and len(missing_requirements) == 0
        
        return ClosureCheckResult(
            can_close=can_close,
            passed_gates=passed_gates,
            failed_gates=failed_gates,
            pending_actions=pending_actions,
            missing_requirements=missing_requirements,
        )
    
    # Effectiveness Verification
    
    def add_effectiveness_check(
        self,
        capa_id: UUID,
        performed_by: UUID,
        method: str,
        criteria: str,
        result: str,
        is_effective: bool,
        check_date: Optional[date] = None,
        evidence: Optional[str] = None,
        follow_up_required: bool = False,
        follow_up_date: Optional[date] = None,
    ) -> Optional[EffectivenessCheck]:
        """Add an effectiveness check to a CAPA."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        check = EffectivenessCheck(
            id=uuid4(),
            capa_id=capa_id,
            check_date=check_date or date.today(),
            performed_by=performed_by,
            method=method,
            criteria=criteria,
            result=result,
            is_effective=is_effective,
            evidence=evidence,
            follow_up_required=follow_up_required,
            follow_up_date=follow_up_date,
        )
        
        capa.effectiveness_checks.append(check)
        capa.is_effective = is_effective
        
        # Pass the effectiveness gate if effective
        if is_effective:
            for gate in capa.closure_gates:
                if gate.gate_type == ClosureGateType.EFFECTIVENESS_VERIFIED:
                    gate.is_passed = True
                    gate.passed_at = datetime.now(timezone.utc)
                    gate.passed_by = performed_by
                    break
        
        return check
    
    def get_pending_effectiveness_checks(self) -> list[CAPA]:
        """Get CAPAs needing effectiveness checks."""
        result = []
        check_threshold = date.today() - timedelta(days=self.config.effectiveness_check_days)
        
        for capa in self._capas.values():
            if capa.status != CAPAStatus.CLOSED:
                continue
            
            if capa.closed_at and capa.closed_at.date() <= check_threshold:
                # Check if we have a recent effectiveness check
                has_recent_check = any(
                    ec.check_date >= check_threshold
                    for ec in capa.effectiveness_checks
                )
                
                if not has_recent_check:
                    result.append(capa)
        
        return result
    
    # Status Transitions
    
    def update_status(self, capa_id: UUID, new_status: CAPAStatus) -> Optional[CAPA]:
        """Update CAPA status."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        capa.status = new_status
        return capa
    
    def close_capa(
        self,
        capa_id: UUID,
        closed_by: UUID,
        force: bool = False,
    ) -> tuple[bool, Optional[CAPA], list[str]]:
        """
        Close a CAPA.
        
        Args:
            capa_id: CAPA ID
            closed_by: User closing the CAPA
            force: Force close even if gates not passed
            
        Returns:
            Tuple of (success, CAPA, list of issues)
        """
        capa = self._capas.get(capa_id)
        if not capa:
            return False, None, ["CAPA not found"]
        
        # Check closure readiness
        if not force:
            check = self.check_closure_readiness(capa_id)
            if not check.can_close:
                return False, capa, check.missing_requirements
        
        capa.status = CAPAStatus.CLOSED
        capa.closed_by = closed_by
        capa.closed_at = datetime.now(timezone.utc)
        capa.actual_completion_date = date.today()
        
        # Close linked NC
        if capa.source_nc_id:
            nc = self._ncs.get(capa.source_nc_id)
            if nc:
                nc.is_closed = True
                nc.closed_at = datetime.now(timezone.utc)
        
        return True, capa, []
    
    def cancel_capa(
        self,
        capa_id: UUID,
        cancelled_by: UUID,
        reason: str,
    ) -> Optional[CAPA]:
        """Cancel a CAPA."""
        capa = self._capas.get(capa_id)
        if not capa:
            return None
        
        capa.status = CAPAStatus.CANCELLED
        capa.closed_by = cancelled_by
        capa.closed_at = datetime.now(timezone.utc)
        
        return capa
    
    # Metrics
    
    def get_capa_metrics(self) -> dict[str, Any]:
        """Get overall CAPA metrics."""
        capas = list(self._capas.values())
        
        if not capas:
            return {
                "total_capas": 0,
                "open_capas": 0,
                "closed_capas": 0,
            }
        
        open_capas = [c for c in capas if c.status not in (CAPAStatus.CLOSED, CAPAStatus.CANCELLED)]
        closed_capas = [c for c in capas if c.status == CAPAStatus.CLOSED]
        
        # Calculate average closure time
        avg_closure_days = None
        if closed_capas:
            closure_times = []
            for c in closed_capas:
                if c.closed_at and c.created_at:
                    days = (c.closed_at - c.created_at).days
                    closure_times.append(days)
            if closure_times:
                avg_closure_days = sum(closure_times) / len(closure_times)
        
        # Count by status
        by_status = {}
        for status in CAPAStatus:
            count = len([c for c in capas if c.status == status])
            if count > 0:
                by_status[status.value] = count
        
        # Count by priority
        by_priority = {}
        for priority in CAPAPriority:
            count = len([c for c in open_capas if c.priority == priority])
            if count > 0:
                by_priority[priority.value] = count
        
        # Effectiveness rate
        effective_count = len([c for c in closed_capas if c.is_effective is True])
        effectiveness_rate = (effective_count / len(closed_capas) * 100) if closed_capas else None
        
        return {
            "total_capas": len(capas),
            "open_capas": len(open_capas),
            "closed_capas": len(closed_capas),
            "by_status": by_status,
            "by_priority": by_priority,
            "avg_closure_days": round(avg_closure_days, 1) if avg_closure_days else None,
            "effectiveness_rate_percent": round(effectiveness_rate, 1) if effectiveness_rate else None,
            "overdue_actions": len(self.get_overdue_actions()),
        }


# Singleton instance
_capa_workflow_service: Optional[CAPAWorkflowIntegrationService] = None


def get_capa_workflow_service() -> CAPAWorkflowIntegrationService:
    """Get the singleton CAPA workflow service instance."""
    global _capa_workflow_service
    if _capa_workflow_service is None:
        _capa_workflow_service = CAPAWorkflowIntegrationService()
    return _capa_workflow_service


def reset_capa_workflow_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _capa_workflow_service
    _capa_workflow_service = None
