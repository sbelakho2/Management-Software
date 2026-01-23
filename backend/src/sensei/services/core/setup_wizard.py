"""
GM Day-1 Setup Wizard Service

Provides guided setup for new General Managers including:
- Pipeline stages configuration
- Approval thresholds
- Role assignments
- Template setup
- First LSW cadence
- First Obeya creation

This service persists wizard progress and allows resuming incomplete setups.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class WizardStatus(str, Enum):
    """Status of the setup wizard."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class WizardStep(str, Enum):
    """Steps in the setup wizard."""
    
    WELCOME = "welcome"
    ORGANIZATION_PROFILE = "organization_profile"
    PIPELINE_STAGES = "pipeline_stages"
    APPROVAL_THRESHOLDS = "approval_thresholds"
    ROLE_ASSIGNMENTS = "role_assignments"
    TEMPLATES = "templates"
    LSW_CADENCE = "lsw_cadence"
    FIRST_OBEYA = "first_obeya"
    REVIEW = "review"
    COMPLETE = "complete"


class PipelineStageType(str, Enum):
    """Types of pipeline stages."""
    
    PROSPECT = "prospect"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ApprovalThresholdType(str, Enum):
    """Types of approval thresholds."""
    
    QUOTE_VALUE = "quote_value"
    MARGIN_PERCENTAGE = "margin_percentage"
    DISCOUNT_PERCENTAGE = "discount_percentage"
    QUALIFICATION_SCORE = "qualification_score"


class LSWFrequency(str, Enum):
    """Frequency options for LSW checklists."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class RoleType(str, Enum):
    """Role types for the organization."""
    
    GENERAL_MANAGER = "general_manager"
    SALES_MANAGER = "sales_manager"
    SALES_REP = "sales_rep"
    ENGINEER = "engineer"
    FINANCE = "finance"
    QUALITY = "quality"
    OPERATIONS = "operations"


# =============================================================================
# Data Models
# =============================================================================


class OrganizationProfile(BaseModel):
    """Organization profile configuration."""
    
    name: str = Field(..., description="Organization name")
    industry: Optional[str] = Field(None, description="Industry vertical")
    timezone: str = Field("UTC", description="Default timezone")
    fiscal_year_start: int = Field(1, ge=1, le=12, description="Fiscal year start month (1-12)")
    currency: str = Field("USD", description="Default currency code")
    logo_url: Optional[str] = Field(None, description="Organization logo URL")


class PipelineStage(BaseModel):
    """Pipeline stage configuration."""
    
    id: str = Field(..., description="Unique stage identifier")
    name: str = Field(..., description="Display name")
    type: PipelineStageType = Field(..., description="Stage type")
    order: int = Field(..., ge=0, description="Display order")
    probability: int = Field(0, ge=0, le=100, description="Win probability percentage")
    is_active: bool = Field(True, description="Whether stage is active")
    required_fields: list[str] = Field(default_factory=list, description="Required fields for this stage")
    auto_tasks: list[str] = Field(default_factory=list, description="Auto-generated tasks for this stage")


class ApprovalThreshold(BaseModel):
    """Approval threshold configuration."""
    
    type: ApprovalThresholdType = Field(..., description="Threshold type")
    value: float = Field(..., description="Threshold value")
    approver_roles: list[RoleType] = Field(default_factory=list, description="Roles that can approve")
    requires_override: bool = Field(False, description="Whether override requires justification")
    description: str = Field("", description="Description of what triggers this threshold")


class RoleAssignment(BaseModel):
    """Role assignment for a user."""
    
    user_id: UUID = Field(..., description="User ID")
    user_email: str = Field(..., description="User email")
    user_name: str = Field(..., description="User display name")
    role: RoleType = Field(..., description="Assigned role")
    is_primary: bool = Field(False, description="Whether this is the primary holder of this role")
    permissions: list[str] = Field(default_factory=list, description="Additional permissions")


class TemplateConfig(BaseModel):
    """Template configuration."""
    
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    type: str = Field(..., description="Template type (rfq, quote, email, etc.)")
    description: str = Field("", description="Template description")
    is_default: bool = Field(False, description="Whether this is the default template")
    content_preview: Optional[str] = Field(None, description="Preview of template content")


class LSWChecklistItem(BaseModel):
    """LSW checklist item."""
    
    id: str = Field(..., description="Item ID")
    title: str = Field(..., description="Item title")
    description: str = Field("", description="Item description")
    frequency: LSWFrequency = Field(..., description="How often this item should be done")
    category: str = Field("general", description="Item category")
    is_required: bool = Field(True, description="Whether item is required")
    order: int = Field(0, description="Display order")


class LSWCadenceConfig(BaseModel):
    """LSW cadence configuration."""
    
    daily_items: list[LSWChecklistItem] = Field(default_factory=list)
    weekly_items: list[LSWChecklistItem] = Field(default_factory=list)
    monthly_items: list[LSWChecklistItem] = Field(default_factory=list)
    notification_time: str = Field("08:00", description="Time to send daily reminders (HH:MM)")
    weekly_review_day: int = Field(5, ge=0, le=6, description="Day of week for weekly review (0=Mon)")
    monthly_review_day: int = Field(1, ge=1, le=28, description="Day of month for monthly review")


class ObeyaConfig(BaseModel):
    """Obeya board configuration."""
    
    name: str = Field(..., description="Obeya board name")
    description: str = Field("", description="Board description")
    metrics: list[str] = Field(default_factory=list, description="Key metrics to display")
    sections: list[str] = Field(
        default_factory=lambda: ["safety", "quality", "delivery", "cost", "morale"],
        description="Board sections"
    )
    update_frequency: str = Field("daily", description="How often the board should be updated")
    visibility: str = Field("organization", description="Who can view the board")


class WizardStepData(BaseModel):
    """Data for a single wizard step."""
    
    step: WizardStep = Field(..., description="Step identifier")
    status: WizardStatus = Field(WizardStatus.NOT_STARTED, description="Step status")
    data: dict[str, Any] = Field(default_factory=dict, description="Step data")
    started_at: Optional[datetime] = Field(None, description="When step was started")
    completed_at: Optional[datetime] = Field(None, description="When step was completed")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors")


class WizardProgress(BaseModel):
    """Overall wizard progress."""
    
    id: UUID = Field(..., description="Wizard session ID")
    organization_id: UUID = Field(..., description="Organization ID")
    user_id: UUID = Field(..., description="User ID who started the wizard")
    status: WizardStatus = Field(WizardStatus.NOT_STARTED, description="Overall wizard status")
    current_step: WizardStep = Field(WizardStep.WELCOME, description="Current step")
    steps: dict[WizardStep, WizardStepData] = Field(default_factory=dict, description="Step data")
    started_at: Optional[datetime] = Field(None, description="When wizard was started")
    completed_at: Optional[datetime] = Field(None, description="When wizard was completed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Request/Response Models
# =============================================================================


class StartWizardRequest(BaseModel):
    """Request to start a new wizard session."""
    
    organization_id: UUID = Field(..., description="Organization ID")
    skip_to_step: Optional[WizardStep] = Field(None, description="Optional step to skip to")


class StartWizardResponse(BaseModel):
    """Response from starting a wizard."""
    
    wizard_id: UUID = Field(..., description="Wizard session ID")
    current_step: WizardStep = Field(..., description="Current step")
    progress_percentage: float = Field(..., description="Progress percentage")
    steps: list[WizardStepData] = Field(..., description="All step data")


class UpdateStepRequest(BaseModel):
    """Request to update a wizard step."""
    
    step: WizardStep = Field(..., description="Step to update")
    data: dict[str, Any] = Field(..., description="Step data")
    mark_complete: bool = Field(False, description="Whether to mark step as complete")


class UpdateStepResponse(BaseModel):
    """Response from updating a step."""
    
    step: WizardStep = Field(..., description="Updated step")
    status: WizardStatus = Field(..., description="Step status")
    validation_errors: list[str] = Field(..., description="Validation errors")
    next_step: Optional[WizardStep] = Field(None, description="Next step if current is complete")


class CompleteWizardRequest(BaseModel):
    """Request to complete the wizard."""
    
    apply_configuration: bool = Field(True, description="Whether to apply the configuration")


class CompleteWizardResponse(BaseModel):
    """Response from completing the wizard."""
    
    success: bool = Field(..., description="Whether completion was successful")
    applied_configs: list[str] = Field(..., description="List of applied configurations")
    errors: list[str] = Field(..., description="Any errors during application")
    redirect_url: Optional[str] = Field(None, description="Where to redirect after completion")


class GetWizardSummaryResponse(BaseModel):
    """Summary of wizard configuration for review."""
    
    organization_profile: Optional[OrganizationProfile] = None
    pipeline_stages: list[PipelineStage] = Field(default_factory=list)
    approval_thresholds: list[ApprovalThreshold] = Field(default_factory=list)
    role_assignments: list[RoleAssignment] = Field(default_factory=list)
    templates: list[TemplateConfig] = Field(default_factory=list)
    lsw_cadence: Optional[LSWCadenceConfig] = None
    first_obeya: Optional[ObeyaConfig] = None


# =============================================================================
# Default Configurations
# =============================================================================


def get_default_pipeline_stages() -> list[PipelineStage]:
    """Get default pipeline stages."""
    return [
        PipelineStage(
            id="prospect",
            name="Prospect",
            type=PipelineStageType.PROSPECT,
            order=0,
            probability=10,
            is_active=True,
            required_fields=["customer_name", "contact_email"],
            auto_tasks=["Initial contact", "Qualify lead"],
        ),
        PipelineStage(
            id="qualification",
            name="Qualification",
            type=PipelineStageType.QUALIFICATION,
            order=1,
            probability=25,
            is_active=True,
            required_fields=["budget", "timeline", "decision_maker"],
            auto_tasks=["Complete RFQ", "Technical review"],
        ),
        PipelineStage(
            id="proposal",
            name="Proposal",
            type=PipelineStageType.PROPOSAL,
            order=2,
            probability=50,
            is_active=True,
            required_fields=["quote_number"],
            auto_tasks=["Create quote", "Send proposal"],
        ),
        PipelineStage(
            id="negotiation",
            name="Negotiation",
            type=PipelineStageType.NEGOTIATION,
            order=3,
            probability=75,
            is_active=True,
            required_fields=[],
            auto_tasks=["Negotiate terms", "Final approval"],
        ),
        PipelineStage(
            id="closed_won",
            name="Closed Won",
            type=PipelineStageType.CLOSED_WON,
            order=4,
            probability=100,
            is_active=True,
            required_fields=["po_number"],
            auto_tasks=["Process order", "Handoff to operations"],
        ),
        PipelineStage(
            id="closed_lost",
            name="Closed Lost",
            type=PipelineStageType.CLOSED_LOST,
            order=5,
            probability=0,
            is_active=True,
            required_fields=["loss_reason"],
            auto_tasks=["Document loss reason", "Schedule follow-up"],
        ),
    ]


def get_default_approval_thresholds() -> list[ApprovalThreshold]:
    """Get default approval thresholds."""
    return [
        ApprovalThreshold(
            type=ApprovalThresholdType.QUOTE_VALUE,
            value=100000.0,
            approver_roles=[RoleType.GENERAL_MANAGER],
            requires_override=True,
            description="Quotes over $100,000 require GM approval",
        ),
        ApprovalThreshold(
            type=ApprovalThresholdType.MARGIN_PERCENTAGE,
            value=20.0,
            approver_roles=[RoleType.GENERAL_MANAGER, RoleType.FINANCE],
            requires_override=True,
            description="Quotes with margin below 20% require GM or Finance approval",
        ),
        ApprovalThreshold(
            type=ApprovalThresholdType.DISCOUNT_PERCENTAGE,
            value=15.0,
            approver_roles=[RoleType.SALES_MANAGER],
            requires_override=False,
            description="Discounts over 15% require Sales Manager approval",
        ),
        ApprovalThreshold(
            type=ApprovalThresholdType.QUALIFICATION_SCORE,
            value=70.0,
            approver_roles=[RoleType.GENERAL_MANAGER],
            requires_override=True,
            description="RFQs with qualification score below 70 require GM override to proceed",
        ),
    ]


def get_default_lsw_items() -> LSWCadenceConfig:
    """Get default LSW checklist items."""
    daily_items = [
        LSWChecklistItem(
            id="daily-1",
            title="Review Today Dashboard",
            description="Check Today dashboard for urgent items and due dates",
            frequency=LSWFrequency.DAILY,
            category="operations",
            is_required=True,
            order=1,
        ),
        LSWChecklistItem(
            id="daily-2",
            title="Process Inbox",
            description="Review and respond to customer inquiries",
            frequency=LSWFrequency.DAILY,
            category="communication",
            is_required=True,
            order=2,
        ),
        LSWChecklistItem(
            id="daily-3",
            title="Update Pipeline",
            description="Update opportunity stages and notes",
            frequency=LSWFrequency.DAILY,
            category="sales",
            is_required=True,
            order=3,
        ),
        LSWChecklistItem(
            id="daily-4",
            title="Team Check-in",
            description="Brief touchpoint with team members",
            frequency=LSWFrequency.DAILY,
            category="leadership",
            is_required=True,
            order=4,
        ),
    ]
    
    weekly_items = [
        LSWChecklistItem(
            id="weekly-1",
            title="Pipeline Review Meeting",
            description="Review pipeline health with sales team",
            frequency=LSWFrequency.WEEKLY,
            category="sales",
            is_required=True,
            order=1,
        ),
        LSWChecklistItem(
            id="weekly-2",
            title="Update Obeya Board",
            description="Update metrics and action items on Obeya board",
            frequency=LSWFrequency.WEEKLY,
            category="operations",
            is_required=True,
            order=2,
        ),
        LSWChecklistItem(
            id="weekly-3",
            title="Quality Review",
            description="Review quality metrics and open NCRs",
            frequency=LSWFrequency.WEEKLY,
            category="quality",
            is_required=True,
            order=3,
        ),
        LSWChecklistItem(
            id="weekly-4",
            title="Week in Review Export",
            description="Generate and review Week in Review report",
            frequency=LSWFrequency.WEEKLY,
            category="reporting",
            is_required=True,
            order=4,
        ),
    ]
    
    monthly_items = [
        LSWChecklistItem(
            id="monthly-1",
            title="KPI Review",
            description="Review monthly KPI targets vs actuals",
            frequency=LSWFrequency.MONTHLY,
            category="operations",
            is_required=True,
            order=1,
        ),
        LSWChecklistItem(
            id="monthly-2",
            title="Team Performance Review",
            description="Review team metrics and development needs",
            frequency=LSWFrequency.MONTHLY,
            category="leadership",
            is_required=True,
            order=2,
        ),
        LSWChecklistItem(
            id="monthly-3",
            title="Process Improvement",
            description="Identify one process improvement opportunity",
            frequency=LSWFrequency.MONTHLY,
            category="continuous_improvement",
            is_required=True,
            order=3,
        ),
        LSWChecklistItem(
            id="monthly-4",
            title="Training Review",
            description="Review training completion and gaps",
            frequency=LSWFrequency.MONTHLY,
            category="training",
            is_required=True,
            order=4,
        ),
    ]
    
    return LSWCadenceConfig(
        daily_items=daily_items,
        weekly_items=weekly_items,
        monthly_items=monthly_items,
        notification_time="08:00",
        weekly_review_day=4,  # Friday
        monthly_review_day=1,
    )


def get_default_obeya_config() -> ObeyaConfig:
    """Get default Obeya configuration."""
    return ObeyaConfig(
        name="Main Obeya",
        description="Primary Obeya board for tracking key metrics and initiatives",
        metrics=[
            "Pipeline Value",
            "Win Rate",
            "Average Quote Cycle Time",
            "On-Time Delivery",
            "Customer Satisfaction",
        ],
        sections=["safety", "quality", "delivery", "cost", "morale"],
        update_frequency="daily",
        visibility="organization",
    )


# =============================================================================
# Service Class
# =============================================================================


class SetupWizardService:
    """Service for managing GM Day-1 Setup Wizard."""
    
    # Step order for navigation
    STEP_ORDER = [
        WizardStep.WELCOME,
        WizardStep.ORGANIZATION_PROFILE,
        WizardStep.PIPELINE_STAGES,
        WizardStep.APPROVAL_THRESHOLDS,
        WizardStep.ROLE_ASSIGNMENTS,
        WizardStep.TEMPLATES,
        WizardStep.LSW_CADENCE,
        WizardStep.FIRST_OBEYA,
        WizardStep.REVIEW,
        WizardStep.COMPLETE,
    ]
    
    # In-memory storage for wizard progress (would be database in production)
    _wizards: dict[UUID, WizardProgress] = {}
    
    @classmethod
    def reset_storage(cls) -> None:
        """Reset in-memory storage (for testing)."""
        cls._wizards = {}
    
    def __init__(self, user_id: UUID):
        """Initialize service with user context."""
        self.user_id = user_id
    
    def get_step_index(self, step: WizardStep) -> int:
        """Get index of a step in the wizard."""
        return self.STEP_ORDER.index(step)
    
    def get_next_step(self, current_step: WizardStep) -> Optional[WizardStep]:
        """Get the next step after the current one."""
        current_index = self.get_step_index(current_step)
        if current_index < len(self.STEP_ORDER) - 1:
            return self.STEP_ORDER[current_index + 1]
        return None
    
    def get_previous_step(self, current_step: WizardStep) -> Optional[WizardStep]:
        """Get the previous step before the current one."""
        current_index = self.get_step_index(current_step)
        if current_index > 0:
            return self.STEP_ORDER[current_index - 1]
        return None
    
    def calculate_progress(self, wizard: WizardProgress) -> float:
        """Calculate progress percentage."""
        if wizard.status == WizardStatus.COMPLETED:
            return 100.0
        
        # Welcome and Complete don't count toward progress
        countable_steps = self.STEP_ORDER[1:-1]
        completed = sum(
            1 for step in countable_steps
            if wizard.steps.get(step, WizardStepData(step=step)).status == WizardStatus.COMPLETED
        )
        return (completed / len(countable_steps)) * 100
    
    def _initialize_steps(self, wizard: WizardProgress) -> None:
        """Initialize all steps with default data."""
        for step in self.STEP_ORDER:
            wizard.steps[step] = WizardStepData(
                step=step,
                status=WizardStatus.NOT_STARTED,
                started_at=None,
                completed_at=None,
            )
    
    def start_wizard(
        self,
        request: StartWizardRequest,
    ) -> StartWizardResponse:
        """Start a new wizard session or resume existing one."""
        import uuid
        
        # Check for existing incomplete wizard
        for wizard in self._wizards.values():
            if (
                wizard.organization_id == request.organization_id
                and wizard.status == WizardStatus.IN_PROGRESS
            ):
                # Resume existing wizard
                return StartWizardResponse(
                    wizard_id=wizard.id,
                    current_step=wizard.current_step,
                    progress_percentage=self.calculate_progress(wizard),
                    steps=list(wizard.steps.values()),
                )
        
        # Create new wizard
        wizard_id = uuid.uuid4()
        wizard = WizardProgress(
            id=wizard_id,
            organization_id=request.organization_id,
            user_id=self.user_id,
            status=WizardStatus.IN_PROGRESS,
            current_step=request.skip_to_step or WizardStep.WELCOME,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        self._initialize_steps(wizard)
        
        # Mark welcome as started
        wizard.steps[WizardStep.WELCOME].status = WizardStatus.IN_PROGRESS
        wizard.steps[WizardStep.WELCOME].started_at = datetime.now(timezone.utc)
        
        # If skipping to a step, mark prior steps as skipped
        if request.skip_to_step:
            for step in self.STEP_ORDER:
                if step == request.skip_to_step:
                    break
                wizard.steps[step].status = WizardStatus.SKIPPED
        
        self._wizards[wizard_id] = wizard
        
        return StartWizardResponse(
            wizard_id=wizard_id,
            current_step=wizard.current_step,
            progress_percentage=self.calculate_progress(wizard),
            steps=list(wizard.steps.values()),
        )
    
    def get_wizard(self, wizard_id: UUID) -> Optional[WizardProgress]:
        """Get wizard by ID."""
        return self._wizards.get(wizard_id)
    
    def get_wizard_by_organization(
        self,
        organization_id: UUID,
    ) -> Optional[WizardProgress]:
        """Get active wizard for an organization."""
        for wizard in self._wizards.values():
            if (
                wizard.organization_id == organization_id
                and wizard.status == WizardStatus.IN_PROGRESS
            ):
                return wizard
        return None
    
    def validate_step_data(
        self,
        step: WizardStep,
        data: dict[str, Any],
    ) -> list[str]:
        """Validate data for a specific step."""
        errors: list[str] = []
        
        if step == WizardStep.ORGANIZATION_PROFILE:
            if not data.get("name"):
                errors.append("Organization name is required")
            if not data.get("timezone"):
                errors.append("Timezone is required")
        
        elif step == WizardStep.PIPELINE_STAGES:
            stages = data.get("stages", [])
            if not stages:
                errors.append("At least one pipeline stage is required")
            
            # Check for required stage types
            stage_types = {s.get("type") for s in stages}
            if "closed_won" not in stage_types:
                errors.append("A 'Closed Won' stage is required")
            if "closed_lost" not in stage_types:
                errors.append("A 'Closed Lost' stage is required")
        
        elif step == WizardStep.APPROVAL_THRESHOLDS:
            thresholds = data.get("thresholds", [])
            for threshold in thresholds:
                if threshold.get("value", 0) < 0:
                    errors.append("Threshold values cannot be negative")
        
        elif step == WizardStep.ROLE_ASSIGNMENTS:
            assignments = data.get("assignments", [])
            # Check for at least one GM
            has_gm = any(
                a.get("role") == RoleType.GENERAL_MANAGER.value
                for a in assignments
            )
            if not has_gm:
                errors.append("At least one General Manager must be assigned")
        
        elif step == WizardStep.LSW_CADENCE:
            if not data.get("daily_items") and not data.get("weekly_items"):
                errors.append("At least one LSW checklist item is required")
        
        elif step == WizardStep.FIRST_OBEYA:
            if not data.get("name"):
                errors.append("Obeya board name is required")
        
        return errors
    
    def update_step(
        self,
        wizard_id: UUID,
        request: UpdateStepRequest,
    ) -> UpdateStepResponse:
        """Update a wizard step."""
        wizard = self._wizards.get(wizard_id)
        if not wizard:
            return UpdateStepResponse(
                step=request.step,
                status=WizardStatus.NOT_STARTED,
                validation_errors=["Wizard not found"],
                next_step=None,
            )
        
        step_data = wizard.steps.get(request.step)
        if not step_data:
            step_data = WizardStepData(
                step=request.step,
                status=WizardStatus.NOT_STARTED,
                started_at=None,
                completed_at=None,
            )
            wizard.steps[request.step] = step_data
        
        # Validate data
        errors = self.validate_step_data(request.step, request.data)
        
        # Update step data
        step_data.data = request.data
        step_data.validation_errors = errors
        
        if step_data.status == WizardStatus.NOT_STARTED:
            step_data.status = WizardStatus.IN_PROGRESS
            step_data.started_at = datetime.now(timezone.utc)
        
        # Mark complete if requested and no errors
        next_step = None
        if request.mark_complete:
            if not errors:
                step_data.status = WizardStatus.COMPLETED
                step_data.completed_at = datetime.now(timezone.utc)
                next_step = self.get_next_step(request.step)
                if next_step:
                    wizard.current_step = next_step
            else:
                # Can't complete with errors
                step_data.status = WizardStatus.IN_PROGRESS
        
        wizard.updated_at = datetime.now(timezone.utc)
        
        return UpdateStepResponse(
            step=request.step,
            status=step_data.status,
            validation_errors=errors,
            next_step=next_step,
        )
    
    def navigate_to_step(
        self,
        wizard_id: UUID,
        step: WizardStep,
    ) -> Optional[WizardStep]:
        """Navigate to a specific step."""
        wizard = self._wizards.get(wizard_id)
        if not wizard:
            return None
        
        # Can only navigate to completed steps or the next incomplete step
        current_index = self.get_step_index(wizard.current_step)
        target_index = self.get_step_index(step)
        
        if target_index <= current_index or all(
            wizard.steps.get(s, WizardStepData(
                step=s,
                status=WizardStatus.NOT_STARTED,
                started_at=None,
                completed_at=None,
            )).status == WizardStatus.COMPLETED
            for s in self.STEP_ORDER[:target_index]
        ):
            wizard.current_step = step
            wizard.updated_at = datetime.now(timezone.utc)
            return step
        
        return None
    
    def get_summary(self, wizard_id: UUID) -> GetWizardSummaryResponse:
        """Get summary of wizard configuration."""
        wizard = self._wizards.get(wizard_id)
        if not wizard:
            return GetWizardSummaryResponse()
        
        summary = GetWizardSummaryResponse()
        
        # Organization profile
        org_data = wizard.steps.get(WizardStep.ORGANIZATION_PROFILE, WizardStepData(
            step=WizardStep.ORGANIZATION_PROFILE,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if org_data:
            summary.organization_profile = OrganizationProfile(**org_data)
        
        # Pipeline stages
        stages_data = wizard.steps.get(WizardStep.PIPELINE_STAGES, WizardStepData(
            step=WizardStep.PIPELINE_STAGES,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if stages_data.get("stages"):
            summary.pipeline_stages = [PipelineStage(**s) for s in stages_data["stages"]]
        
        # Approval thresholds
        thresholds_data = wizard.steps.get(WizardStep.APPROVAL_THRESHOLDS, WizardStepData(
            step=WizardStep.APPROVAL_THRESHOLDS,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if thresholds_data.get("thresholds"):
            summary.approval_thresholds = [ApprovalThreshold(**t) for t in thresholds_data["thresholds"]]
        
        # Role assignments
        roles_data = wizard.steps.get(WizardStep.ROLE_ASSIGNMENTS, WizardStepData(
            step=WizardStep.ROLE_ASSIGNMENTS,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if roles_data.get("assignments"):
            summary.role_assignments = [RoleAssignment(**r) for r in roles_data["assignments"]]
        
        # Templates
        templates_data = wizard.steps.get(WizardStep.TEMPLATES, WizardStepData(
            step=WizardStep.TEMPLATES,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if templates_data.get("templates"):
            summary.templates = [TemplateConfig(**t) for t in templates_data["templates"]]
        
        # LSW cadence
        lsw_data = wizard.steps.get(WizardStep.LSW_CADENCE, WizardStepData(
            step=WizardStep.LSW_CADENCE,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if lsw_data:
            summary.lsw_cadence = LSWCadenceConfig(**lsw_data)
        
        # First Obeya
        obeya_data = wizard.steps.get(WizardStep.FIRST_OBEYA, WizardStepData(
            step=WizardStep.FIRST_OBEYA,
            status=WizardStatus.NOT_STARTED,
            started_at=None,
            completed_at=None,
        )).data
        if obeya_data:
            summary.first_obeya = ObeyaConfig(**obeya_data)
        
        return summary
    
    def complete_wizard(
        self,
        wizard_id: UUID,
        request: CompleteWizardRequest,
    ) -> CompleteWizardResponse:
        """Complete the wizard and optionally apply configuration."""
        wizard = self._wizards.get(wizard_id)
        if not wizard:
            return CompleteWizardResponse(
                success=False,
                applied_configs=[],
                errors=["Wizard not found"],
                redirect_url=None,
            )
        
        # Validate all steps are complete (except welcome and complete)
        incomplete_steps = []
        for step in self.STEP_ORDER[1:-1]:  # Skip welcome and complete
            step_data = wizard.steps.get(step, WizardStepData(
                step=step,
                status=WizardStatus.NOT_STARTED,
                started_at=None,
                completed_at=None,
            ))
            if step_data.status not in [WizardStatus.COMPLETED, WizardStatus.SKIPPED]:
                incomplete_steps.append(step.value)
        
        if incomplete_steps:
            return CompleteWizardResponse(
                success=False,
                applied_configs=[],
                errors=[f"Incomplete steps: {', '.join(incomplete_steps)}"],
                redirect_url=None,
            )
        
        applied_configs: list[str] = []
        errors: list[str] = []
        
        if request.apply_configuration:
            # Apply each configuration (in production, this would call other services)
            try:
                # Organization profile
                if wizard.steps.get(WizardStep.ORGANIZATION_PROFILE, WizardStepData(
                    step=WizardStep.ORGANIZATION_PROFILE,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("Organization Profile")
                
                # Pipeline stages
                if wizard.steps.get(WizardStep.PIPELINE_STAGES, WizardStepData(
                    step=WizardStep.PIPELINE_STAGES,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("Pipeline Stages")
                
                # Approval thresholds
                if wizard.steps.get(WizardStep.APPROVAL_THRESHOLDS, WizardStepData(
                    step=WizardStep.APPROVAL_THRESHOLDS,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("Approval Thresholds")
                
                # Role assignments
                if wizard.steps.get(WizardStep.ROLE_ASSIGNMENTS, WizardStepData(
                    step=WizardStep.ROLE_ASSIGNMENTS,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("Role Assignments")
                
                # Templates
                if wizard.steps.get(WizardStep.TEMPLATES, WizardStepData(
                    step=WizardStep.TEMPLATES,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("Templates")
                
                # LSW cadence
                if wizard.steps.get(WizardStep.LSW_CADENCE, WizardStepData(
                    step=WizardStep.LSW_CADENCE,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("LSW Cadence")
                
                # First Obeya
                if wizard.steps.get(WizardStep.FIRST_OBEYA, WizardStepData(
                    step=WizardStep.FIRST_OBEYA,
                    status=WizardStatus.NOT_STARTED,
                    started_at=None,
                    completed_at=None,
                )).status == WizardStatus.COMPLETED:
                    applied_configs.append("First Obeya")
                
            except Exception as e:
                errors.append(f"Error applying configuration: {str(e)}")
        
        # Mark wizard as complete
        if not errors:
            wizard.status = WizardStatus.COMPLETED
            wizard.current_step = WizardStep.COMPLETE
            wizard.completed_at = datetime.now(timezone.utc)
            wizard.steps[WizardStep.COMPLETE] = WizardStepData(
                step=WizardStep.COMPLETE,
                status=WizardStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        
        return CompleteWizardResponse(
            success=len(errors) == 0,
            applied_configs=applied_configs,
            errors=errors,
            redirect_url="/dashboard" if not errors else None,
        )
    
    def get_defaults_for_step(
        self,
        step: WizardStep,
    ) -> dict[str, Any]:
        """Get default values for a step."""
        if step == WizardStep.PIPELINE_STAGES:
            return {
                "stages": [s.model_dump() for s in get_default_pipeline_stages()]
            }
        
        elif step == WizardStep.APPROVAL_THRESHOLDS:
            return {
                "thresholds": [t.model_dump() for t in get_default_approval_thresholds()]
            }
        
        elif step == WizardStep.LSW_CADENCE:
            return get_default_lsw_items().model_dump()
        
        elif step == WizardStep.FIRST_OBEYA:
            return get_default_obeya_config().model_dump()
        
        return {}
    
    def skip_step(
        self,
        wizard_id: UUID,
        step: WizardStep,
    ) -> Optional[WizardStep]:
        """Skip a step and move to the next one."""
        wizard = self._wizards.get(wizard_id)
        if not wizard:
            return None
        
        # Can't skip required steps
        required_steps = {
            WizardStep.WELCOME,
            WizardStep.ORGANIZATION_PROFILE,
            WizardStep.PIPELINE_STAGES,
            WizardStep.REVIEW,
            WizardStep.COMPLETE,
        }
        
        if step in required_steps:
            return None
        
        step_data = wizard.steps.get(step, WizardStepData(step=step))
        step_data.status = WizardStatus.SKIPPED
        wizard.steps[step] = step_data
        
        next_step = self.get_next_step(step)
        if next_step:
            wizard.current_step = next_step
        
        wizard.updated_at = datetime.now(timezone.utc)
        
        return next_step
    
    def reset_wizard(
        self,
        wizard_id: UUID,
    ) -> bool:
        """Reset a wizard to start over."""
        wizard = self._wizards.get(wizard_id)
        if not wizard:
            return False
        
        # Reset all steps
        self._initialize_steps(wizard)
        wizard.status = WizardStatus.IN_PROGRESS
        wizard.current_step = WizardStep.WELCOME
        wizard.completed_at = None
        wizard.updated_at = datetime.now(timezone.utc)
        
        return True
    
    def delete_wizard(
        self,
        wizard_id: UUID,
    ) -> bool:
        """Delete a wizard session."""
        if wizard_id in self._wizards:
            del self._wizards[wizard_id]
            return True
        return False
