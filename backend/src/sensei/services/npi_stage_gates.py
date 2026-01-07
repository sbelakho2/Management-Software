"""
NPI Stage Gates Service.

Implements the New Product Introduction (NPI) stage-gate workflow:
Intake → DFM → Prototype → Pilot → SOP

Each stage has:
- Required artifacts that must be complete before transition
- Optional artifacts that are tracked but don't block
- Approval requirements for stage transitions
- Automatic task generation for missing items
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class NPIStage(str, Enum):
    """NPI workflow stages."""
    
    INTAKE = "intake"
    DFM = "dfm"  # Design for Manufacturing
    PROTOTYPE = "prototype"
    PILOT = "pilot"
    SOP = "sop"  # Start of Production
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ArtifactType(str, Enum):
    """Types of artifacts required at various stages."""
    
    # Intake stage artifacts
    CUSTOMER_REQUIREMENTS = "customer_requirements"
    INITIAL_SPECS = "initial_specs"
    VOLUME_FORECAST = "volume_forecast"
    TARGET_PRICING = "target_pricing"
    
    # DFM stage artifacts
    CTQ_DEFINITION = "ctq_definition"
    PROCESS_CAPABILITY_STUDY = "process_capability_study"
    DFM_REVIEW = "dfm_review"
    TOOLING_PLAN = "tooling_plan"
    
    # Prototype stage artifacts
    PROTOTYPE_BUILD = "prototype_build"
    PROTOTYPE_TEST_RESULTS = "prototype_test_results"
    DESIGN_VALIDATION = "design_validation"
    SUPPLIER_QUOTES = "supplier_quotes"
    
    # Pilot stage artifacts
    PILOT_BUILD = "pilot_build"
    PROCESS_VALIDATION = "process_validation"
    SUPPLIER_READINESS = "supplier_readiness"
    PPAP_SUBMISSION = "ppap_submission"
    OPERATOR_TRAINING = "operator_training"
    
    # SOP stage artifacts
    PRODUCTION_APPROVAL = "production_approval"
    STANDARD_WORK_APPROVED = "standard_work_approved"
    CONTROL_PLAN = "control_plan"
    CUSTOMER_APPROVAL = "customer_approval"


class ArtifactStatus(str, Enum):
    """Status of an artifact."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAIVED = "waived"


class GateDecision(str, Enum):
    """Gate review decision."""
    
    GO = "go"
    NO_GO = "no_go"
    CONDITIONAL_GO = "conditional_go"
    HOLD = "hold"


class TransitionBlockReason(str, Enum):
    """Reasons for blocking stage transition."""
    
    MISSING_REQUIRED_ARTIFACT = "missing_required_artifact"
    ARTIFACT_NOT_APPROVED = "artifact_not_approved"
    PENDING_APPROVAL = "pending_approval"
    FAILED_GATE_REVIEW = "failed_gate_review"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"


@dataclass
class NPIArtifact:
    """An artifact required for NPI stage gates."""
    
    id: UUID = field(default_factory=uuid4)
    npi_project_id: UUID = field(default_factory=uuid4)
    artifact_type: ArtifactType = ArtifactType.CUSTOMER_REQUIREMENTS
    name: str = ""
    description: str = ""
    status: ArtifactStatus = ArtifactStatus.NOT_STARTED
    is_required: bool = True
    required_for_stage: NPIStage = NPIStage.INTAKE
    
    # Content and evidence
    attachment_ids: list[UUID] = field(default_factory=list)
    evidence_notes: str = ""
    
    # Review information
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str = ""
    
    # Waiver information (if waived)
    waived_by: UUID | None = None
    waived_at: datetime | None = None
    waiver_reason: str = ""
    waiver_expiration: datetime | None = None
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID = field(default_factory=uuid4)
    
    def is_complete(self) -> bool:
        """Check if artifact is complete (approved or waived)."""
        return self.status in (ArtifactStatus.APPROVED, ArtifactStatus.WAIVED)
    
    def is_waiver_valid(self) -> bool:
        """Check if waiver is still valid."""
        if self.status != ArtifactStatus.WAIVED:
            return False
        if self.waiver_expiration is None:
            return True
        return datetime.now(timezone.utc) < self.waiver_expiration


@dataclass
class GateReview:
    """A gate review event for stage transition."""
    
    id: UUID = field(default_factory=uuid4)
    npi_project_id: UUID = field(default_factory=uuid4)
    from_stage: NPIStage = NPIStage.INTAKE
    to_stage: NPIStage = NPIStage.DFM
    
    # Review details
    decision: GateDecision = GateDecision.HOLD
    decision_rationale: str = ""
    conditions: list[str] = field(default_factory=list)
    
    # Participants
    reviewed_by: UUID = field(default_factory=uuid4)
    review_team: list[UUID] = field(default_factory=list)
    
    # Timing
    scheduled_at: datetime | None = None
    conducted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Results tracking
    action_items: list[dict[str, Any]] = field(default_factory=list)
    follow_up_date: datetime | None = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TransitionResult:
    """Result of attempting a stage transition."""
    
    success: bool = False
    from_stage: NPIStage = NPIStage.INTAKE
    to_stage: NPIStage = NPIStage.DFM
    blocked_reasons: list[TransitionBlockReason] = field(default_factory=list)
    missing_artifacts: list[ArtifactType] = field(default_factory=list)
    pending_artifacts: list[ArtifactType] = field(default_factory=list)
    message: str = ""
    gate_review_id: UUID | None = None


@dataclass
class NPIProject:
    """An NPI project tracking a product from intake to production."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    product_id: UUID | None = None
    customer_id: UUID | None = None
    rfq_id: UUID | None = None
    quote_id: UUID | None = None
    
    # Current state
    current_stage: NPIStage = NPIStage.INTAKE
    stage_entered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Timeline
    target_sop_date: datetime | None = None
    actual_sop_date: datetime | None = None
    
    # Team
    project_manager_id: UUID | None = None
    engineering_lead_id: UUID | None = None
    quality_lead_id: UUID | None = None
    manufacturing_lead_id: UUID | None = None
    
    # Metrics
    estimated_annual_volume: int = 0
    estimated_unit_cost: Decimal = Decimal("0")
    estimated_investment: Decimal = Decimal("0")
    
    # Status
    is_active: bool = True
    priority: int = 3  # 1=highest, 5=lowest
    health_status: str = "green"  # green, yellow, red
    health_notes: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID = field(default_factory=uuid4)


@dataclass
class StageRequirements:
    """Requirements for entering a specific stage."""
    
    stage: NPIStage
    required_artifacts: list[ArtifactType]
    optional_artifacts: list[ArtifactType]
    required_approvers: list[str]  # Role names
    minimum_approval_count: int = 1


class NPIStageGatesService:
    """
    Service for managing NPI stage-gate workflow.
    
    Provides:
    - Project lifecycle management
    - Artifact tracking and validation
    - Stage transition logic with gating
    - Gate review management
    - Readiness assessment
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._projects: dict[UUID, NPIProject] = {}
        self._artifacts: dict[UUID, NPIArtifact] = {}
        self._gate_reviews: dict[UUID, GateReview] = {}
        self._stage_requirements = self._define_stage_requirements()
    
    def _define_stage_requirements(self) -> dict[NPIStage, StageRequirements]:
        """Define requirements for each stage."""
        return {
            NPIStage.INTAKE: StageRequirements(
                stage=NPIStage.INTAKE,
                required_artifacts=[],  # Entry point, no requirements
                optional_artifacts=[
                    ArtifactType.CUSTOMER_REQUIREMENTS,
                    ArtifactType.INITIAL_SPECS,
                ],
                required_approvers=[],
                minimum_approval_count=0,
            ),
            NPIStage.DFM: StageRequirements(
                stage=NPIStage.DFM,
                required_artifacts=[
                    ArtifactType.CUSTOMER_REQUIREMENTS,
                    ArtifactType.INITIAL_SPECS,
                    ArtifactType.VOLUME_FORECAST,
                ],
                optional_artifacts=[
                    ArtifactType.TARGET_PRICING,
                ],
                required_approvers=["engineering_manager", "quality_manager"],
                minimum_approval_count=1,
            ),
            NPIStage.PROTOTYPE: StageRequirements(
                stage=NPIStage.PROTOTYPE,
                required_artifacts=[
                    ArtifactType.CTQ_DEFINITION,
                    ArtifactType.DFM_REVIEW,
                    ArtifactType.TOOLING_PLAN,
                ],
                optional_artifacts=[
                    ArtifactType.PROCESS_CAPABILITY_STUDY,
                ],
                required_approvers=["engineering_manager", "quality_manager"],
                minimum_approval_count=2,
            ),
            NPIStage.PILOT: StageRequirements(
                stage=NPIStage.PILOT,
                required_artifacts=[
                    ArtifactType.PROTOTYPE_BUILD,
                    ArtifactType.PROTOTYPE_TEST_RESULTS,
                    ArtifactType.DESIGN_VALIDATION,
                    ArtifactType.SUPPLIER_QUOTES,
                ],
                optional_artifacts=[],
                required_approvers=["engineering_manager", "quality_manager", "gm"],
                minimum_approval_count=2,
            ),
            NPIStage.SOP: StageRequirements(
                stage=NPIStage.SOP,
                required_artifacts=[
                    ArtifactType.PILOT_BUILD,
                    ArtifactType.PROCESS_VALIDATION,
                    ArtifactType.SUPPLIER_READINESS,
                    ArtifactType.PPAP_SUBMISSION,
                    ArtifactType.OPERATOR_TRAINING,
                ],
                optional_artifacts=[],
                required_approvers=["quality_manager", "manufacturing_manager", "gm"],
                minimum_approval_count=3,
            ),
            NPIStage.COMPLETED: StageRequirements(
                stage=NPIStage.COMPLETED,
                required_artifacts=[
                    ArtifactType.PRODUCTION_APPROVAL,
                    ArtifactType.STANDARD_WORK_APPROVED,
                    ArtifactType.CONTROL_PLAN,
                    ArtifactType.CUSTOMER_APPROVAL,
                ],
                optional_artifacts=[],
                required_approvers=["gm"],
                minimum_approval_count=1,
            ),
        }
    
    # -------------------------------------------------------------------------
    # Project Management
    # -------------------------------------------------------------------------
    
    def create_project(
        self,
        name: str,
        description: str = "",
        product_id: UUID | None = None,
        customer_id: UUID | None = None,
        rfq_id: UUID | None = None,
        project_manager_id: UUID | None = None,
        target_sop_date: datetime | None = None,
        created_by: UUID | None = None,
    ) -> NPIProject:
        """Create a new NPI project."""
        project = NPIProject(
            name=name,
            description=description,
            product_id=product_id,
            customer_id=customer_id,
            rfq_id=rfq_id,
            project_manager_id=project_manager_id,
            target_sop_date=target_sop_date,
            created_by=created_by or uuid4(),
        )
        self._projects[project.id] = project
        
        # Auto-create required artifacts for all stages
        self._create_default_artifacts(project)
        
        return project
    
    def _create_default_artifacts(self, project: NPIProject) -> None:
        """Create default artifacts for all stages."""
        artifact_stage_map = {
            ArtifactType.CUSTOMER_REQUIREMENTS: NPIStage.DFM,
            ArtifactType.INITIAL_SPECS: NPIStage.DFM,
            ArtifactType.VOLUME_FORECAST: NPIStage.DFM,
            ArtifactType.TARGET_PRICING: NPIStage.DFM,
            ArtifactType.CTQ_DEFINITION: NPIStage.PROTOTYPE,
            ArtifactType.PROCESS_CAPABILITY_STUDY: NPIStage.PROTOTYPE,
            ArtifactType.DFM_REVIEW: NPIStage.PROTOTYPE,
            ArtifactType.TOOLING_PLAN: NPIStage.PROTOTYPE,
            ArtifactType.PROTOTYPE_BUILD: NPIStage.PILOT,
            ArtifactType.PROTOTYPE_TEST_RESULTS: NPIStage.PILOT,
            ArtifactType.DESIGN_VALIDATION: NPIStage.PILOT,
            ArtifactType.SUPPLIER_QUOTES: NPIStage.PILOT,
            ArtifactType.PILOT_BUILD: NPIStage.SOP,
            ArtifactType.PROCESS_VALIDATION: NPIStage.SOP,
            ArtifactType.SUPPLIER_READINESS: NPIStage.SOP,
            ArtifactType.PPAP_SUBMISSION: NPIStage.SOP,
            ArtifactType.OPERATOR_TRAINING: NPIStage.SOP,
            ArtifactType.PRODUCTION_APPROVAL: NPIStage.COMPLETED,
            ArtifactType.STANDARD_WORK_APPROVED: NPIStage.COMPLETED,
            ArtifactType.CONTROL_PLAN: NPIStage.COMPLETED,
            ArtifactType.CUSTOMER_APPROVAL: NPIStage.COMPLETED,
        }
        
        for artifact_type, required_stage in artifact_stage_map.items():
            requirements = self._stage_requirements.get(required_stage)
            is_required = (
                requirements is not None
                and artifact_type in requirements.required_artifacts
            )
            
            artifact = NPIArtifact(
                npi_project_id=project.id,
                artifact_type=artifact_type,
                name=artifact_type.value.replace("_", " ").title(),
                required_for_stage=required_stage,
                is_required=is_required,
                created_by=project.created_by,
            )
            self._artifacts[artifact.id] = artifact
    
    def get_project(self, project_id: UUID) -> NPIProject | None:
        """Get a project by ID."""
        return self._projects.get(project_id)
    
    def list_projects(
        self,
        stage: NPIStage | None = None,
        is_active: bool | None = None,
        customer_id: UUID | None = None,
    ) -> list[NPIProject]:
        """List projects with optional filters."""
        projects = list(self._projects.values())
        
        if stage is not None:
            projects = [p for p in projects if p.current_stage == stage]
        
        if is_active is not None:
            projects = [p for p in projects if p.is_active == is_active]
        
        if customer_id is not None:
            projects = [p for p in projects if p.customer_id == customer_id]
        
        return sorted(projects, key=lambda p: p.created_at, reverse=True)
    
    def update_project(
        self,
        project_id: UUID,
        **updates: Any,
    ) -> NPIProject | None:
        """Update project fields."""
        project = self._projects.get(project_id)
        if project is None:
            return None
        
        allowed_fields = {
            "name", "description", "product_id", "customer_id",
            "project_manager_id", "engineering_lead_id", "quality_lead_id",
            "manufacturing_lead_id", "target_sop_date", "estimated_annual_volume",
            "estimated_unit_cost", "estimated_investment", "priority",
            "health_status", "health_notes", "is_active",
        }
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(project, key, value)
        
        project.updated_at = datetime.now(timezone.utc)
        return project
    
    def cancel_project(
        self,
        project_id: UUID,
        reason: str,
        cancelled_by: UUID,
    ) -> NPIProject | None:
        """Cancel an NPI project."""
        project = self._projects.get(project_id)
        if project is None:
            return None
        
        project.current_stage = NPIStage.CANCELLED
        project.is_active = False
        project.health_notes = f"Cancelled: {reason}"
        project.updated_at = datetime.now(timezone.utc)
        
        return project
    
    # -------------------------------------------------------------------------
    # Artifact Management
    # -------------------------------------------------------------------------
    
    def get_artifact(self, artifact_id: UUID) -> NPIArtifact | None:
        """Get an artifact by ID."""
        return self._artifacts.get(artifact_id)
    
    def get_project_artifacts(
        self,
        project_id: UUID,
        stage: NPIStage | None = None,
        status: ArtifactStatus | None = None,
        required_only: bool = False,
    ) -> list[NPIArtifact]:
        """Get artifacts for a project."""
        artifacts = [
            a for a in self._artifacts.values()
            if a.npi_project_id == project_id
        ]
        
        if stage is not None:
            artifacts = [a for a in artifacts if a.required_for_stage == stage]
        
        if status is not None:
            artifacts = [a for a in artifacts if a.status == status]
        
        if required_only:
            artifacts = [a for a in artifacts if a.is_required]
        
        return sorted(artifacts, key=lambda a: a.artifact_type.value)
    
    def update_artifact_status(
        self,
        artifact_id: UUID,
        status: ArtifactStatus,
        notes: str = "",
        updated_by: UUID | None = None,
    ) -> NPIArtifact | None:
        """Update artifact status."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return None
        
        artifact.status = status
        artifact.updated_at = datetime.now(timezone.utc)
        
        if status == ArtifactStatus.APPROVED:
            artifact.reviewed_by = updated_by
            artifact.reviewed_at = datetime.now(timezone.utc)
            artifact.review_notes = notes
        
        return artifact
    
    def add_artifact_evidence(
        self,
        artifact_id: UUID,
        attachment_ids: list[UUID],
        evidence_notes: str = "",
    ) -> NPIArtifact | None:
        """Add evidence to an artifact."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return None
        
        artifact.attachment_ids.extend(attachment_ids)
        if evidence_notes:
            artifact.evidence_notes = (
                f"{artifact.evidence_notes}\n{evidence_notes}".strip()
            )
        artifact.updated_at = datetime.now(timezone.utc)
        
        # Auto-transition to in_progress if not started
        if artifact.status == ArtifactStatus.NOT_STARTED:
            artifact.status = ArtifactStatus.IN_PROGRESS
        
        return artifact
    
    def waive_artifact(
        self,
        artifact_id: UUID,
        reason: str,
        waived_by: UUID,
        expiration: datetime | None = None,
    ) -> NPIArtifact | None:
        """Waive an artifact requirement."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return None
        
        artifact.status = ArtifactStatus.WAIVED
        artifact.waived_by = waived_by
        artifact.waived_at = datetime.now(timezone.utc)
        artifact.waiver_reason = reason
        artifact.waiver_expiration = expiration
        artifact.updated_at = datetime.now(timezone.utc)
        
        return artifact
    
    def approve_artifact(
        self,
        artifact_id: UUID,
        approved_by: UUID,
        notes: str = "",
    ) -> NPIArtifact | None:
        """Approve an artifact."""
        return self.update_artifact_status(
            artifact_id=artifact_id,
            status=ArtifactStatus.APPROVED,
            notes=notes,
            updated_by=approved_by,
        )
    
    def reject_artifact(
        self,
        artifact_id: UUID,
        rejected_by: UUID,
        reason: str,
    ) -> NPIArtifact | None:
        """Reject an artifact."""
        artifact = self._artifacts.get(artifact_id)
        if artifact is None:
            return None
        
        artifact.status = ArtifactStatus.REJECTED
        artifact.reviewed_by = rejected_by
        artifact.reviewed_at = datetime.now(timezone.utc)
        artifact.review_notes = reason
        artifact.updated_at = datetime.now(timezone.utc)
        
        return artifact
    
    # -------------------------------------------------------------------------
    # Stage Transition Logic
    # -------------------------------------------------------------------------
    
    def get_next_stage(self, current_stage: NPIStage) -> NPIStage | None:
        """Get the next stage in the workflow."""
        stage_order = [
            NPIStage.INTAKE,
            NPIStage.DFM,
            NPIStage.PROTOTYPE,
            NPIStage.PILOT,
            NPIStage.SOP,
            NPIStage.COMPLETED,
        ]
        
        if current_stage in (NPIStage.COMPLETED, NPIStage.CANCELLED):
            return None
        
        try:
            idx = stage_order.index(current_stage)
            return stage_order[idx + 1]
        except (ValueError, IndexError):
            return None
    
    def get_previous_stage(self, current_stage: NPIStage) -> NPIStage | None:
        """Get the previous stage in the workflow."""
        stage_order = [
            NPIStage.INTAKE,
            NPIStage.DFM,
            NPIStage.PROTOTYPE,
            NPIStage.PILOT,
            NPIStage.SOP,
            NPIStage.COMPLETED,
        ]
        
        if current_stage == NPIStage.INTAKE:
            return None
        
        try:
            idx = stage_order.index(current_stage)
            return stage_order[idx - 1] if idx > 0 else None
        except ValueError:
            return None
    
    def check_stage_readiness(
        self,
        project_id: UUID,
        target_stage: NPIStage,
    ) -> TransitionResult:
        """Check if project is ready to transition to target stage."""
        project = self._projects.get(project_id)
        if project is None:
            return TransitionResult(
                success=False,
                message="Project not found",
            )
        
        requirements = self._stage_requirements.get(target_stage)
        if requirements is None:
            return TransitionResult(
                success=False,
                from_stage=project.current_stage,
                to_stage=target_stage,
                message=f"No requirements defined for stage {target_stage}",
            )
        
        artifacts = self.get_project_artifacts(project_id)
        
        missing_artifacts: list[ArtifactType] = []
        pending_artifacts: list[ArtifactType] = []
        blocked_reasons: list[TransitionBlockReason] = []
        
        for required_type in requirements.required_artifacts:
            artifact = next(
                (a for a in artifacts if a.artifact_type == required_type),
                None,
            )
            
            if artifact is None:
                missing_artifacts.append(required_type)
                blocked_reasons.append(TransitionBlockReason.MISSING_REQUIRED_ARTIFACT)
            elif not artifact.is_complete():
                pending_artifacts.append(required_type)
                blocked_reasons.append(TransitionBlockReason.ARTIFACT_NOT_APPROVED)
        
        is_ready = len(missing_artifacts) == 0 and len(pending_artifacts) == 0
        
        return TransitionResult(
            success=is_ready,
            from_stage=project.current_stage,
            to_stage=target_stage,
            blocked_reasons=list(set(blocked_reasons)),
            missing_artifacts=missing_artifacts,
            pending_artifacts=pending_artifacts,
            message="Ready for transition" if is_ready else "Blocked by incomplete artifacts",
        )
    
    def transition_stage(
        self,
        project_id: UUID,
        target_stage: NPIStage,
        transitioned_by: UUID,
        force: bool = False,
        override_reason: str = "",
    ) -> TransitionResult:
        """Attempt to transition project to a new stage."""
        project = self._projects.get(project_id)
        if project is None:
            return TransitionResult(
                success=False,
                message="Project not found",
            )
        
        # Check if target is valid next stage
        next_stage = self.get_next_stage(project.current_stage)
        if target_stage != next_stage and not force:
            return TransitionResult(
                success=False,
                from_stage=project.current_stage,
                to_stage=target_stage,
                message=f"Invalid transition. Next stage should be {next_stage}",
            )
        
        # Check readiness
        readiness = self.check_stage_readiness(project_id, target_stage)
        
        if not readiness.success and not force:
            return readiness
        
        if not readiness.success and force:
            if not override_reason:
                return TransitionResult(
                    success=False,
                    from_stage=project.current_stage,
                    to_stage=target_stage,
                    message="Override reason required for forced transition",
                )
        
        # Perform transition
        old_stage = project.current_stage
        project.current_stage = target_stage
        project.stage_entered_at = datetime.now(timezone.utc)
        project.updated_at = datetime.now(timezone.utc)
        
        # Record gate review
        review = GateReview(
            npi_project_id=project_id,
            from_stage=old_stage,
            to_stage=target_stage,
            decision=GateDecision.GO if readiness.success else GateDecision.CONDITIONAL_GO,
            decision_rationale=override_reason if force else "All requirements met",
            reviewed_by=transitioned_by,
        )
        self._gate_reviews[review.id] = review
        
        return TransitionResult(
            success=True,
            from_stage=old_stage,
            to_stage=target_stage,
            message=f"Successfully transitioned to {target_stage}",
            gate_review_id=review.id,
        )
    
    def rollback_stage(
        self,
        project_id: UUID,
        reason: str,
        rolled_back_by: UUID,
    ) -> TransitionResult:
        """Roll back to the previous stage."""
        project = self._projects.get(project_id)
        if project is None:
            return TransitionResult(
                success=False,
                message="Project not found",
            )
        
        previous_stage = self.get_previous_stage(project.current_stage)
        if previous_stage is None:
            return TransitionResult(
                success=False,
                from_stage=project.current_stage,
                to_stage=project.current_stage,
                message="Cannot roll back from first stage",
            )
        
        old_stage = project.current_stage
        project.current_stage = previous_stage
        project.stage_entered_at = datetime.now(timezone.utc)
        project.updated_at = datetime.now(timezone.utc)
        
        # Record the rollback
        review = GateReview(
            npi_project_id=project_id,
            from_stage=old_stage,
            to_stage=previous_stage,
            decision=GateDecision.NO_GO,
            decision_rationale=f"Rollback: {reason}",
            reviewed_by=rolled_back_by,
        )
        self._gate_reviews[review.id] = review
        
        return TransitionResult(
            success=True,
            from_stage=old_stage,
            to_stage=previous_stage,
            message=f"Rolled back to {previous_stage}",
            gate_review_id=review.id,
        )
    
    # -------------------------------------------------------------------------
    # Gate Reviews
    # -------------------------------------------------------------------------
    
    def create_gate_review(
        self,
        project_id: UUID,
        from_stage: NPIStage,
        to_stage: NPIStage,
        decision: GateDecision,
        decision_rationale: str,
        reviewed_by: UUID,
        review_team: list[UUID] | None = None,
        conditions: list[str] | None = None,
        action_items: list[dict[str, Any]] | None = None,
        follow_up_date: datetime | None = None,
    ) -> GateReview:
        """Record a gate review."""
        review = GateReview(
            npi_project_id=project_id,
            from_stage=from_stage,
            to_stage=to_stage,
            decision=decision,
            decision_rationale=decision_rationale,
            reviewed_by=reviewed_by,
            review_team=review_team or [],
            conditions=conditions or [],
            action_items=action_items or [],
            follow_up_date=follow_up_date,
        )
        self._gate_reviews[review.id] = review
        return review
    
    def get_gate_review(self, review_id: UUID) -> GateReview | None:
        """Get a gate review by ID."""
        return self._gate_reviews.get(review_id)
    
    def get_project_gate_reviews(
        self,
        project_id: UUID,
    ) -> list[GateReview]:
        """Get all gate reviews for a project."""
        reviews = [
            r for r in self._gate_reviews.values()
            if r.npi_project_id == project_id
        ]
        return sorted(reviews, key=lambda r: r.conducted_at)
    
    # -------------------------------------------------------------------------
    # Readiness Assessment
    # -------------------------------------------------------------------------
    
    def get_stage_completion_percentage(
        self,
        project_id: UUID,
        stage: NPIStage,
    ) -> Decimal:
        """Calculate completion percentage for a stage's requirements."""
        requirements = self._stage_requirements.get(stage)
        if requirements is None or not requirements.required_artifacts:
            return Decimal("100")
        
        artifacts = self.get_project_artifacts(project_id, stage=stage)
        
        required_count = len(requirements.required_artifacts)
        completed_count = sum(
            1 for a in artifacts
            if a.artifact_type in requirements.required_artifacts
            and a.is_complete()
        )
        
        return Decimal(completed_count * 100) / Decimal(required_count)
    
    def get_project_summary(
        self,
        project_id: UUID,
    ) -> dict[str, Any] | None:
        """Get a summary of project status."""
        project = self._projects.get(project_id)
        if project is None:
            return None
        
        artifacts = self.get_project_artifacts(project_id)
        
        total_artifacts = len(artifacts)
        completed_artifacts = sum(1 for a in artifacts if a.is_complete())
        required_artifacts = [a for a in artifacts if a.is_required]
        completed_required = sum(1 for a in required_artifacts if a.is_complete())
        
        next_stage = self.get_next_stage(project.current_stage)
        next_stage_readiness = None
        if next_stage:
            readiness = self.check_stage_readiness(project_id, next_stage)
            next_stage_readiness = {
                "stage": next_stage.value,
                "ready": readiness.success,
                "missing_count": len(readiness.missing_artifacts),
                "pending_count": len(readiness.pending_artifacts),
            }
        
        gate_reviews = self.get_project_gate_reviews(project_id)
        
        return {
            "project": project,
            "current_stage": project.current_stage.value,
            "stage_entered_at": project.stage_entered_at,
            "days_in_stage": (
                datetime.now(timezone.utc) - project.stage_entered_at
            ).days,
            "total_artifacts": total_artifacts,
            "completed_artifacts": completed_artifacts,
            "completion_percentage": (
                Decimal(completed_artifacts * 100) / Decimal(total_artifacts)
                if total_artifacts > 0 else Decimal("0")
            ),
            "required_artifacts_total": len(required_artifacts),
            "required_artifacts_complete": completed_required,
            "next_stage_readiness": next_stage_readiness,
            "gate_reviews_count": len(gate_reviews),
            "health_status": project.health_status,
        }
    
    def get_blocked_projects(self) -> list[dict[str, Any]]:
        """Get projects that are blocked from advancing."""
        blocked = []
        
        for project in self._projects.values():
            if not project.is_active:
                continue
            
            next_stage = self.get_next_stage(project.current_stage)
            if next_stage is None:
                continue
            
            readiness = self.check_stage_readiness(project.id, next_stage)
            if not readiness.success:
                blocked.append({
                    "project_id": project.id,
                    "project_name": project.name,
                    "current_stage": project.current_stage.value,
                    "target_stage": next_stage.value,
                    "missing_artifacts": [a.value for a in readiness.missing_artifacts],
                    "pending_artifacts": [a.value for a in readiness.pending_artifacts],
                    "days_in_stage": (
                        datetime.now(timezone.utc) - project.stage_entered_at
                    ).days,
                })
        
        return blocked
    
    def get_projects_by_health(
        self,
        health_status: str,
    ) -> list[NPIProject]:
        """Get projects by health status (green, yellow, red)."""
        return [
            p for p in self._projects.values()
            if p.is_active and p.health_status == health_status
        ]
    
    def update_project_health(
        self,
        project_id: UUID,
        health_status: str,
        health_notes: str,
    ) -> NPIProject | None:
        """Update project health status."""
        project = self._projects.get(project_id)
        if project is None:
            return None
        
        if health_status not in ("green", "yellow", "red"):
            return None
        
        project.health_status = health_status
        project.health_notes = health_notes
        project.updated_at = datetime.now(timezone.utc)
        
        return project
