"""
Tests for GM Day-1 Setup Wizard Service
"""

import uuid
from datetime import datetime

import pytest

from sensei.services.core.setup_wizard import (
    SetupWizardService,
    WizardStatus,
    WizardStep,
    PipelineStageType,
    ApprovalThresholdType,
    LSWFrequency,
    RoleType,
    OrganizationProfile,
    PipelineStage,
    ApprovalThreshold,
    RoleAssignment,
    TemplateConfig,
    LSWChecklistItem,
    LSWCadenceConfig,
    ObeyaConfig,
    WizardStepData,
    WizardProgress,
    StartWizardRequest,
    UpdateStepRequest,
    CompleteWizardRequest,
    get_default_pipeline_stages,
    get_default_approval_thresholds,
    get_default_lsw_items,
    get_default_obeya_config,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset service storage before each test."""
    SetupWizardService.reset_storage()
    yield
    SetupWizardService.reset_storage()


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid.uuid4()


@pytest.fixture
def organization_id():
    """Create a test organization ID."""
    return uuid.uuid4()


@pytest.fixture
def service(user_id):
    """Create a service instance."""
    return SetupWizardService(user_id=user_id)


@pytest.fixture
def started_wizard(service, organization_id):
    """Create a started wizard."""
    request = StartWizardRequest(organization_id=organization_id)
    response = service.start_wizard(request)
    return response.wizard_id


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum types."""
    
    def test_wizard_status_values(self):
        """Test WizardStatus enum values."""
        assert WizardStatus.NOT_STARTED == "not_started"
        assert WizardStatus.IN_PROGRESS == "in_progress"
        assert WizardStatus.COMPLETED == "completed"
        assert WizardStatus.SKIPPED == "skipped"
    
    def test_wizard_step_values(self):
        """Test WizardStep enum has all expected steps."""
        expected_steps = [
            "welcome",
            "organization_profile",
            "pipeline_stages",
            "approval_thresholds",
            "role_assignments",
            "templates",
            "lsw_cadence",
            "first_obeya",
            "review",
            "complete",
        ]
        actual_steps = [step.value for step in WizardStep]
        assert actual_steps == expected_steps
    
    def test_pipeline_stage_type_values(self):
        """Test PipelineStageType enum values."""
        assert PipelineStageType.PROSPECT == "prospect"
        assert PipelineStageType.QUALIFICATION == "qualification"
        assert PipelineStageType.PROPOSAL == "proposal"
        assert PipelineStageType.NEGOTIATION == "negotiation"
        assert PipelineStageType.CLOSED_WON == "closed_won"
        assert PipelineStageType.CLOSED_LOST == "closed_lost"
    
    def test_approval_threshold_type_values(self):
        """Test ApprovalThresholdType enum values."""
        assert ApprovalThresholdType.QUOTE_VALUE == "quote_value"
        assert ApprovalThresholdType.MARGIN_PERCENTAGE == "margin_percentage"
        assert ApprovalThresholdType.DISCOUNT_PERCENTAGE == "discount_percentage"
        assert ApprovalThresholdType.QUALIFICATION_SCORE == "qualification_score"
    
    def test_lsw_frequency_values(self):
        """Test LSWFrequency enum values."""
        assert LSWFrequency.DAILY == "daily"
        assert LSWFrequency.WEEKLY == "weekly"
        assert LSWFrequency.MONTHLY == "monthly"
    
    def test_role_type_values(self):
        """Test RoleType enum values."""
        assert RoleType.GENERAL_MANAGER == "general_manager"
        assert RoleType.SALES_MANAGER == "sales_manager"
        assert RoleType.SALES_REP == "sales_rep"
        assert RoleType.ENGINEER == "engineer"
        assert RoleType.FINANCE == "finance"
        assert RoleType.QUALITY == "quality"
        assert RoleType.OPERATIONS == "operations"


# =============================================================================
# Data Model Tests
# =============================================================================


class TestDataModels:
    """Tests for data models."""
    
    def test_organization_profile_defaults(self):
        """Test OrganizationProfile default values."""
        profile = OrganizationProfile(name="Test Org")
        assert profile.name == "Test Org"
        assert profile.timezone == "UTC"
        assert profile.fiscal_year_start == 1
        assert profile.currency == "USD"
        assert profile.industry is None
        assert profile.logo_url is None
    
    def test_organization_profile_custom_values(self):
        """Test OrganizationProfile with custom values."""
        profile = OrganizationProfile(
            name="Acme Corp",
            industry="Manufacturing",
            timezone="America/New_York",
            fiscal_year_start=7,
            currency="EUR",
            logo_url="https://example.com/logo.png",
        )
        assert profile.name == "Acme Corp"
        assert profile.industry == "Manufacturing"
        assert profile.fiscal_year_start == 7
    
    def test_pipeline_stage_model(self):
        """Test PipelineStage model."""
        stage = PipelineStage(
            id="test-stage",
            name="Test Stage",
            type=PipelineStageType.PROPOSAL,
            order=0,
            probability=50,
        )
        assert stage.id == "test-stage"
        assert stage.type == PipelineStageType.PROPOSAL
        assert stage.probability == 50
        assert stage.is_active is True
        assert stage.required_fields == []
    
    def test_approval_threshold_model(self):
        """Test ApprovalThreshold model."""
        threshold = ApprovalThreshold(
            type=ApprovalThresholdType.QUOTE_VALUE,
            value=100000.0,
            approver_roles=[RoleType.GENERAL_MANAGER],
            requires_override=True,
        )
        assert threshold.type == ApprovalThresholdType.QUOTE_VALUE
        assert threshold.value == 100000.0
        assert RoleType.GENERAL_MANAGER in threshold.approver_roles
    
    def test_role_assignment_model(self):
        """Test RoleAssignment model."""
        assignment = RoleAssignment(
            user_id=uuid.uuid4(),
            user_email="test@example.com",
            user_name="Test User",
            role=RoleType.SALES_REP,
        )
        assert assignment.user_email == "test@example.com"
        assert assignment.role == RoleType.SALES_REP
        assert assignment.is_primary is False
    
    def test_template_config_model(self):
        """Test TemplateConfig model."""
        template = TemplateConfig(
            id="tpl-1",
            name="Standard Quote",
            type="quote",
            is_default=True,
        )
        assert template.id == "tpl-1"
        assert template.type == "quote"
        assert template.is_default is True
    
    def test_lsw_checklist_item_model(self):
        """Test LSWChecklistItem model."""
        item = LSWChecklistItem(
            id="item-1",
            title="Daily Review",
            frequency=LSWFrequency.DAILY,
        )
        assert item.id == "item-1"
        assert item.frequency == LSWFrequency.DAILY
        assert item.is_required is True
    
    def test_lsw_cadence_config_model(self):
        """Test LSWCadenceConfig model."""
        config = LSWCadenceConfig(
            daily_items=[
                LSWChecklistItem(id="d1", title="Daily 1", frequency=LSWFrequency.DAILY)
            ],
            weekly_items=[],
            monthly_items=[],
        )
        assert len(config.daily_items) == 1
        assert config.notification_time == "08:00"
        assert config.weekly_review_day == 5
    
    def test_obeya_config_model(self):
        """Test ObeyaConfig model."""
        config = ObeyaConfig(name="Main Obeya")
        assert config.name == "Main Obeya"
        assert "safety" in config.sections
        assert config.update_frequency == "daily"
    
    def test_wizard_step_data_model(self):
        """Test WizardStepData model."""
        step_data = WizardStepData(step=WizardStep.WELCOME)
        assert step_data.step == WizardStep.WELCOME
        assert step_data.status == WizardStatus.NOT_STARTED
        assert step_data.data == {}
        assert step_data.validation_errors == []
    
    def test_wizard_progress_model(self):
        """Test WizardProgress model."""
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        wizard = WizardProgress(
            id=uuid.uuid4(),
            organization_id=org_id,
            user_id=user_id,
        )
        assert wizard.organization_id == org_id
        assert wizard.status == WizardStatus.NOT_STARTED
        assert wizard.current_step == WizardStep.WELCOME


# =============================================================================
# Default Configuration Tests
# =============================================================================


class TestDefaultConfigurations:
    """Tests for default configuration generators."""
    
    def test_get_default_pipeline_stages(self):
        """Test default pipeline stages."""
        stages = get_default_pipeline_stages()
        assert len(stages) == 6
        
        stage_types = {s.type for s in stages}
        assert PipelineStageType.PROSPECT in stage_types
        assert PipelineStageType.QUALIFICATION in stage_types
        assert PipelineStageType.PROPOSAL in stage_types
        assert PipelineStageType.NEGOTIATION in stage_types
        assert PipelineStageType.CLOSED_WON in stage_types
        assert PipelineStageType.CLOSED_LOST in stage_types
    
    def test_default_pipeline_stages_order(self):
        """Test default stages are in correct order."""
        stages = get_default_pipeline_stages()
        orders = [s.order for s in stages]
        assert orders == sorted(orders)
    
    def test_default_pipeline_stages_probabilities(self):
        """Test default stage probabilities are reasonable."""
        stages = get_default_pipeline_stages()
        for stage in stages:
            assert 0 <= stage.probability <= 100
        
        # Closed won should be 100%
        closed_won = next(s for s in stages if s.type == PipelineStageType.CLOSED_WON)
        assert closed_won.probability == 100
        
        # Closed lost should be 0%
        closed_lost = next(s for s in stages if s.type == PipelineStageType.CLOSED_LOST)
        assert closed_lost.probability == 0
    
    def test_get_default_approval_thresholds(self):
        """Test default approval thresholds."""
        thresholds = get_default_approval_thresholds()
        assert len(thresholds) == 4
        
        types = {t.type for t in thresholds}
        assert ApprovalThresholdType.QUOTE_VALUE in types
        assert ApprovalThresholdType.MARGIN_PERCENTAGE in types
        assert ApprovalThresholdType.DISCOUNT_PERCENTAGE in types
        assert ApprovalThresholdType.QUALIFICATION_SCORE in types
    
    def test_default_thresholds_have_approvers(self):
        """Test all thresholds have approver roles."""
        thresholds = get_default_approval_thresholds()
        for threshold in thresholds:
            assert len(threshold.approver_roles) > 0
    
    def test_get_default_lsw_items(self):
        """Test default LSW items."""
        config = get_default_lsw_items()
        
        assert len(config.daily_items) > 0
        assert len(config.weekly_items) > 0
        assert len(config.monthly_items) > 0
        
        # All daily items should have daily frequency
        for item in config.daily_items:
            assert item.frequency == LSWFrequency.DAILY
        
        # All weekly items should have weekly frequency
        for item in config.weekly_items:
            assert item.frequency == LSWFrequency.WEEKLY
        
        # All monthly items should have monthly frequency
        for item in config.monthly_items:
            assert item.frequency == LSWFrequency.MONTHLY
    
    def test_get_default_obeya_config(self):
        """Test default Obeya configuration."""
        config = get_default_obeya_config()
        
        assert config.name == "Main Obeya"
        assert len(config.sections) == 5
        assert len(config.metrics) > 0
        assert config.update_frequency == "daily"


# =============================================================================
# SetupWizardService Tests
# =============================================================================


class TestSetupWizardService:
    """Tests for SetupWizardService."""
    
    class TestInitialization:
        """Tests for service initialization."""
        
        def test_service_initialization(self, user_id):
            """Test service can be initialized."""
            service = SetupWizardService(user_id=user_id)
            assert service.user_id == user_id
        
        def test_step_order_is_complete(self):
            """Test STEP_ORDER contains all steps."""
            assert len(SetupWizardService.STEP_ORDER) == len(WizardStep)
            for step in WizardStep:
                assert step in SetupWizardService.STEP_ORDER
    
    class TestStepNavigation:
        """Tests for step navigation."""
        
        def test_get_step_index(self, service):
            """Test getting step index."""
            assert service.get_step_index(WizardStep.WELCOME) == 0
            assert service.get_step_index(WizardStep.COMPLETE) == 9
        
        def test_get_next_step(self, service):
            """Test getting next step."""
            assert service.get_next_step(WizardStep.WELCOME) == WizardStep.ORGANIZATION_PROFILE
            assert service.get_next_step(WizardStep.REVIEW) == WizardStep.COMPLETE
            assert service.get_next_step(WizardStep.COMPLETE) is None
        
        def test_get_previous_step(self, service):
            """Test getting previous step."""
            assert service.get_previous_step(WizardStep.ORGANIZATION_PROFILE) == WizardStep.WELCOME
            assert service.get_previous_step(WizardStep.COMPLETE) == WizardStep.REVIEW
            assert service.get_previous_step(WizardStep.WELCOME) is None
    
    class TestStartWizard:
        """Tests for starting wizard."""
        
        def test_start_new_wizard(self, service, organization_id):
            """Test starting a new wizard."""
            request = StartWizardRequest(organization_id=organization_id)
            response = service.start_wizard(request)
            
            assert response.wizard_id is not None
            assert response.current_step == WizardStep.WELCOME
            assert response.progress_percentage == 0.0
            assert len(response.steps) == 10
        
        def test_resume_existing_wizard(self, service, organization_id):
            """Test resuming an existing wizard."""
            # Start first wizard
            request = StartWizardRequest(organization_id=organization_id)
            first_response = service.start_wizard(request)
            
            # Update a step
            update_request = UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test Org", "timezone": "UTC"},
                mark_complete=True,
            )
            service.update_step(first_response.wizard_id, update_request)
            
            # Try to start again - should resume
            second_response = service.start_wizard(request)
            
            assert second_response.wizard_id == first_response.wizard_id
        
        def test_start_wizard_skip_to_step(self, service, organization_id):
            """Test starting wizard and skipping to a step."""
            request = StartWizardRequest(
                organization_id=organization_id,
                skip_to_step=WizardStep.PIPELINE_STAGES,
            )
            response = service.start_wizard(request)
            
            assert response.current_step == WizardStep.PIPELINE_STAGES
        
        def test_started_wizard_is_in_progress(self, service, organization_id):
            """Test started wizard has IN_PROGRESS status."""
            request = StartWizardRequest(organization_id=organization_id)
            response = service.start_wizard(request)
            
            wizard = service.get_wizard(response.wizard_id)
            assert wizard is not None
            assert wizard.status == WizardStatus.IN_PROGRESS
    
    class TestGetWizard:
        """Tests for getting wizard."""
        
        def test_get_wizard_by_id(self, service, started_wizard):
            """Test getting wizard by ID."""
            wizard = service.get_wizard(started_wizard)
            assert wizard is not None
            assert wizard.id == started_wizard
        
        def test_get_nonexistent_wizard(self, service):
            """Test getting nonexistent wizard."""
            wizard = service.get_wizard(uuid.uuid4())
            assert wizard is None
        
        def test_get_wizard_by_organization(self, service, organization_id, started_wizard):
            """Test getting wizard by organization."""
            wizard = service.get_wizard_by_organization(organization_id)
            assert wizard is not None
            assert wizard.id == started_wizard
        
        def test_get_wizard_by_organization_no_wizard(self, service):
            """Test getting wizard for org without wizard."""
            wizard = service.get_wizard_by_organization(uuid.uuid4())
            assert wizard is None
    
    class TestValidateStepData:
        """Tests for step data validation."""
        
        def test_validate_organization_profile_valid(self, service):
            """Test valid organization profile."""
            errors = service.validate_step_data(
                WizardStep.ORGANIZATION_PROFILE,
                {"name": "Test Org", "timezone": "UTC"},
            )
            assert len(errors) == 0
        
        def test_validate_organization_profile_missing_name(self, service):
            """Test organization profile without name."""
            errors = service.validate_step_data(
                WizardStep.ORGANIZATION_PROFILE,
                {"timezone": "UTC"},
            )
            assert "Organization name is required" in errors
        
        def test_validate_organization_profile_missing_timezone(self, service):
            """Test organization profile without timezone."""
            errors = service.validate_step_data(
                WizardStep.ORGANIZATION_PROFILE,
                {"name": "Test Org"},
            )
            assert "Timezone is required" in errors
        
        def test_validate_pipeline_stages_valid(self, service):
            """Test valid pipeline stages."""
            errors = service.validate_step_data(
                WizardStep.PIPELINE_STAGES,
                {"stages": [
                    {"type": "closed_won"},
                    {"type": "closed_lost"},
                ]},
            )
            assert len(errors) == 0
        
        def test_validate_pipeline_stages_empty(self, service):
            """Test empty pipeline stages."""
            errors = service.validate_step_data(
                WizardStep.PIPELINE_STAGES,
                {"stages": []},
            )
            assert "At least one pipeline stage is required" in errors
        
        def test_validate_pipeline_stages_missing_closed_won(self, service):
            """Test pipeline stages without closed_won."""
            errors = service.validate_step_data(
                WizardStep.PIPELINE_STAGES,
                {"stages": [{"type": "prospect"}, {"type": "closed_lost"}]},
            )
            assert "A 'Closed Won' stage is required" in errors
        
        def test_validate_pipeline_stages_missing_closed_lost(self, service):
            """Test pipeline stages without closed_lost."""
            errors = service.validate_step_data(
                WizardStep.PIPELINE_STAGES,
                {"stages": [{"type": "prospect"}, {"type": "closed_won"}]},
            )
            assert "A 'Closed Lost' stage is required" in errors
        
        def test_validate_approval_thresholds_negative_value(self, service):
            """Test negative threshold value."""
            errors = service.validate_step_data(
                WizardStep.APPROVAL_THRESHOLDS,
                {"thresholds": [{"value": -10}]},
            )
            assert "Threshold values cannot be negative" in errors
        
        def test_validate_role_assignments_no_gm(self, service):
            """Test role assignments without GM."""
            errors = service.validate_step_data(
                WizardStep.ROLE_ASSIGNMENTS,
                {"assignments": [{"role": "sales_rep"}]},
            )
            assert "At least one General Manager must be assigned" in errors
        
        def test_validate_role_assignments_with_gm(self, service):
            """Test role assignments with GM."""
            errors = service.validate_step_data(
                WizardStep.ROLE_ASSIGNMENTS,
                {"assignments": [{"role": "general_manager"}]},
            )
            assert len(errors) == 0
        
        def test_validate_lsw_cadence_empty(self, service):
            """Test empty LSW cadence."""
            errors = service.validate_step_data(
                WizardStep.LSW_CADENCE,
                {"daily_items": [], "weekly_items": []},
            )
            assert "At least one LSW checklist item is required" in errors
        
        def test_validate_lsw_cadence_with_items(self, service):
            """Test LSW cadence with items."""
            errors = service.validate_step_data(
                WizardStep.LSW_CADENCE,
                {"daily_items": [{"id": "1", "title": "Test"}]},
            )
            assert len(errors) == 0
        
        def test_validate_first_obeya_missing_name(self, service):
            """Test Obeya without name."""
            errors = service.validate_step_data(
                WizardStep.FIRST_OBEYA,
                {},
            )
            assert "Obeya board name is required" in errors
        
        def test_validate_first_obeya_with_name(self, service):
            """Test Obeya with name."""
            errors = service.validate_step_data(
                WizardStep.FIRST_OBEYA,
                {"name": "Main Obeya"},
            )
            assert len(errors) == 0
    
    class TestUpdateStep:
        """Tests for updating wizard steps."""
        
        def test_update_step_success(self, service, started_wizard):
            """Test updating a step successfully."""
            request = UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test Org", "timezone": "UTC"},
                mark_complete=True,
            )
            response = service.update_step(started_wizard, request)
            
            assert response.step == WizardStep.ORGANIZATION_PROFILE
            assert response.status == WizardStatus.COMPLETED
            assert len(response.validation_errors) == 0
            assert response.next_step == WizardStep.PIPELINE_STAGES
        
        def test_update_step_with_errors(self, service, started_wizard):
            """Test updating a step with validation errors."""
            request = UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={},  # Missing required fields
                mark_complete=True,
            )
            response = service.update_step(started_wizard, request)
            
            assert response.status == WizardStatus.IN_PROGRESS  # Not completed
            assert len(response.validation_errors) > 0
            assert response.next_step is None
        
        def test_update_step_without_marking_complete(self, service, started_wizard):
            """Test updating step without marking complete."""
            request = UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test Org", "timezone": "UTC"},
                mark_complete=False,
            )
            response = service.update_step(started_wizard, request)
            
            assert response.status == WizardStatus.IN_PROGRESS
            assert response.next_step is None
        
        def test_update_nonexistent_wizard(self, service):
            """Test updating step on nonexistent wizard."""
            request = UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test"},
            )
            response = service.update_step(uuid.uuid4(), request)
            
            assert "Wizard not found" in response.validation_errors
    
    class TestNavigateToStep:
        """Tests for navigating to steps."""
        
        def test_navigate_to_previous_step(self, service, started_wizard):
            """Test navigating to a previous step."""
            # Complete first step
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test", "timezone": "UTC"},
                mark_complete=True,
            ))
            
            # Navigate back to welcome
            result = service.navigate_to_step(started_wizard, WizardStep.WELCOME)
            assert result == WizardStep.WELCOME
        
        def test_navigate_to_nonexistent_wizard(self, service):
            """Test navigating on nonexistent wizard."""
            result = service.navigate_to_step(uuid.uuid4(), WizardStep.WELCOME)
            assert result is None
    
    class TestGetSummary:
        """Tests for getting wizard summary."""
        
        def test_get_summary_empty(self, service, started_wizard):
            """Test getting summary of empty wizard."""
            summary = service.get_summary(started_wizard)
            assert summary.organization_profile is None
            assert summary.pipeline_stages == []
        
        def test_get_summary_with_data(self, service, started_wizard):
            """Test getting summary with completed steps."""
            # Complete organization profile
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test Org", "timezone": "America/New_York"},
                mark_complete=True,
            ))
            
            summary = service.get_summary(started_wizard)
            assert summary.organization_profile is not None
            assert summary.organization_profile.name == "Test Org"
        
        def test_get_summary_nonexistent_wizard(self, service):
            """Test getting summary of nonexistent wizard."""
            summary = service.get_summary(uuid.uuid4())
            assert summary.organization_profile is None
    
    class TestCompleteWizard:
        """Tests for completing wizard."""
        
        def test_complete_wizard_with_incomplete_steps(self, service, started_wizard):
            """Test completing wizard with incomplete steps."""
            request = CompleteWizardRequest(apply_configuration=True)
            response = service.complete_wizard(started_wizard, request)
            
            assert response.success is False
            assert len(response.errors) > 0
            assert "Incomplete steps" in response.errors[0]
        
        def test_complete_wizard_success(self, service, started_wizard):
            """Test completing wizard successfully."""
            # Complete all required steps
            steps_data = [
                (WizardStep.WELCOME, {}),
                (WizardStep.ORGANIZATION_PROFILE, {"name": "Test Org", "timezone": "UTC"}),
                (WizardStep.PIPELINE_STAGES, {"stages": [
                    {"type": "closed_won"}, {"type": "closed_lost"}
                ]}),
                (WizardStep.APPROVAL_THRESHOLDS, {"thresholds": []}),
                (WizardStep.ROLE_ASSIGNMENTS, {"assignments": [{"role": "general_manager"}]}),
                (WizardStep.TEMPLATES, {"templates": []}),
                (WizardStep.LSW_CADENCE, {"daily_items": [{"id": "1", "title": "Test"}]}),
                (WizardStep.FIRST_OBEYA, {"name": "Main Obeya"}),
                (WizardStep.REVIEW, {}),
            ]
            
            for step, data in steps_data:
                service.update_step(started_wizard, UpdateStepRequest(
                    step=step,
                    data=data,
                    mark_complete=True,
                ))
            
            request = CompleteWizardRequest(apply_configuration=True)
            response = service.complete_wizard(started_wizard, request)
            
            assert response.success is True
            assert len(response.applied_configs) > 0
            assert response.redirect_url == "/dashboard"
        
        def test_complete_nonexistent_wizard(self, service):
            """Test completing nonexistent wizard."""
            request = CompleteWizardRequest()
            response = service.complete_wizard(uuid.uuid4(), request)
            
            assert response.success is False
            assert "Wizard not found" in response.errors
    
    class TestGetDefaultsForStep:
        """Tests for getting step defaults."""
        
        def test_get_defaults_pipeline_stages(self, service):
            """Test getting defaults for pipeline stages."""
            defaults = service.get_defaults_for_step(WizardStep.PIPELINE_STAGES)
            assert "stages" in defaults
            assert len(defaults["stages"]) == 6
        
        def test_get_defaults_approval_thresholds(self, service):
            """Test getting defaults for approval thresholds."""
            defaults = service.get_defaults_for_step(WizardStep.APPROVAL_THRESHOLDS)
            assert "thresholds" in defaults
            assert len(defaults["thresholds"]) == 4
        
        def test_get_defaults_lsw_cadence(self, service):
            """Test getting defaults for LSW cadence."""
            defaults = service.get_defaults_for_step(WizardStep.LSW_CADENCE)
            assert "daily_items" in defaults
            assert "weekly_items" in defaults
            assert "monthly_items" in defaults
        
        def test_get_defaults_first_obeya(self, service):
            """Test getting defaults for first Obeya."""
            defaults = service.get_defaults_for_step(WizardStep.FIRST_OBEYA)
            assert "name" in defaults
            assert "sections" in defaults
        
        def test_get_defaults_unknown_step(self, service):
            """Test getting defaults for step without defaults."""
            defaults = service.get_defaults_for_step(WizardStep.WELCOME)
            assert defaults == {}
    
    class TestSkipStep:
        """Tests for skipping steps."""
        
        def test_skip_optional_step(self, service, started_wizard):
            """Test skipping an optional step."""
            # First complete required steps up to templates
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.WELCOME,
                data={},
                mark_complete=True,
            ))
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test", "timezone": "UTC"},
                mark_complete=True,
            ))
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.PIPELINE_STAGES,
                data={"stages": [{"type": "closed_won"}, {"type": "closed_lost"}]},
                mark_complete=True,
            ))
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.APPROVAL_THRESHOLDS,
                data={"thresholds": []},
                mark_complete=True,
            ))
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.ROLE_ASSIGNMENTS,
                data={"assignments": [{"role": "general_manager"}]},
                mark_complete=True,
            ))
            
            # Skip templates step
            next_step = service.skip_step(started_wizard, WizardStep.TEMPLATES)
            assert next_step == WizardStep.LSW_CADENCE
            
            wizard = service.get_wizard(started_wizard)
            assert wizard.steps[WizardStep.TEMPLATES].status == WizardStatus.SKIPPED
        
        def test_skip_required_step_fails(self, service, started_wizard):
            """Test that required steps cannot be skipped."""
            result = service.skip_step(started_wizard, WizardStep.ORGANIZATION_PROFILE)
            assert result is None
        
        def test_skip_nonexistent_wizard(self, service):
            """Test skipping step on nonexistent wizard."""
            result = service.skip_step(uuid.uuid4(), WizardStep.TEMPLATES)
            assert result is None
    
    class TestResetWizard:
        """Tests for resetting wizard."""
        
        def test_reset_wizard(self, service, started_wizard):
            """Test resetting a wizard."""
            # Complete some steps
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test", "timezone": "UTC"},
                mark_complete=True,
            ))
            
            # Reset
            result = service.reset_wizard(started_wizard)
            assert result is True
            
            wizard = service.get_wizard(started_wizard)
            assert wizard.current_step == WizardStep.WELCOME
            assert wizard.status == WizardStatus.IN_PROGRESS
        
        def test_reset_nonexistent_wizard(self, service):
            """Test resetting nonexistent wizard."""
            result = service.reset_wizard(uuid.uuid4())
            assert result is False
    
    class TestDeleteWizard:
        """Tests for deleting wizard."""
        
        def test_delete_wizard(self, service, started_wizard):
            """Test deleting a wizard."""
            result = service.delete_wizard(started_wizard)
            assert result is True
            
            wizard = service.get_wizard(started_wizard)
            assert wizard is None
        
        def test_delete_nonexistent_wizard(self, service):
            """Test deleting nonexistent wizard."""
            result = service.delete_wizard(uuid.uuid4())
            assert result is False
    
    class TestCalculateProgress:
        """Tests for progress calculation."""
        
        def test_calculate_progress_empty(self, service, started_wizard):
            """Test progress calculation for empty wizard."""
            wizard = service.get_wizard(started_wizard)
            progress = service.calculate_progress(wizard)
            assert progress == 0.0
        
        def test_calculate_progress_partial(self, service, started_wizard):
            """Test progress calculation for partially complete wizard."""
            # Complete 2 of 8 countable steps
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.ORGANIZATION_PROFILE,
                data={"name": "Test", "timezone": "UTC"},
                mark_complete=True,
            ))
            service.update_step(started_wizard, UpdateStepRequest(
                step=WizardStep.PIPELINE_STAGES,
                data={"stages": [{"type": "closed_won"}, {"type": "closed_lost"}]},
                mark_complete=True,
            ))
            
            wizard = service.get_wizard(started_wizard)
            progress = service.calculate_progress(wizard)
            assert progress == 25.0  # 2 of 8 = 25%
        
        def test_calculate_progress_completed(self, service, started_wizard):
            """Test progress calculation for completed wizard."""
            wizard = service.get_wizard(started_wizard)
            wizard.status = WizardStatus.COMPLETED
            
            progress = service.calculate_progress(wizard)
            assert progress == 100.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestSetupWizardIntegration:
    """Integration tests for setup wizard flow."""
    
    def test_complete_wizard_flow(self, service, organization_id):
        """Test complete wizard flow from start to finish."""
        # Start wizard
        start_response = service.start_wizard(StartWizardRequest(
            organization_id=organization_id
        ))
        wizard_id = start_response.wizard_id
        
        # Step 1: Welcome (just mark complete)
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.WELCOME,
            data={},
            mark_complete=True,
        ))
        
        # Step 2: Organization Profile
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.ORGANIZATION_PROFILE,
            data={"name": "Acme Manufacturing", "timezone": "America/Chicago"},
            mark_complete=True,
        ))
        
        # Step 3: Pipeline Stages (use defaults)
        defaults = service.get_defaults_for_step(WizardStep.PIPELINE_STAGES)
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.PIPELINE_STAGES,
            data=defaults,
            mark_complete=True,
        ))
        
        # Step 4: Approval Thresholds (use defaults)
        defaults = service.get_defaults_for_step(WizardStep.APPROVAL_THRESHOLDS)
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.APPROVAL_THRESHOLDS,
            data=defaults,
            mark_complete=True,
        ))
        
        # Step 5: Role Assignments
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.ROLE_ASSIGNMENTS,
            data={"assignments": [
                {"role": "general_manager", "user_id": str(uuid.uuid4()), 
                 "user_email": "gm@example.com", "user_name": "GM User"},
            ]},
            mark_complete=True,
        ))
        
        # Step 6: Templates (skip)
        service.skip_step(wizard_id, WizardStep.TEMPLATES)
        
        # Step 7: LSW Cadence (use defaults)
        defaults = service.get_defaults_for_step(WizardStep.LSW_CADENCE)
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.LSW_CADENCE,
            data=defaults,
            mark_complete=True,
        ))
        
        # Step 8: First Obeya (use defaults)
        defaults = service.get_defaults_for_step(WizardStep.FIRST_OBEYA)
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.FIRST_OBEYA,
            data=defaults,
            mark_complete=True,
        ))
        
        # Step 9: Review
        summary = service.get_summary(wizard_id)
        assert summary.organization_profile is not None
        assert summary.organization_profile.name == "Acme Manufacturing"
        
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.REVIEW,
            data={},
            mark_complete=True,
        ))
        
        # Step 10: Complete
        complete_response = service.complete_wizard(wizard_id, CompleteWizardRequest(
            apply_configuration=True
        ))
        
        assert complete_response.success is True
        assert len(complete_response.applied_configs) >= 5
        assert complete_response.redirect_url == "/dashboard"
        
        # Verify wizard is marked complete
        wizard = service.get_wizard(wizard_id)
        assert wizard.status == WizardStatus.COMPLETED
    
    def test_wizard_resume_after_partial_completion(self, service, organization_id):
        """Test resuming wizard after partial completion."""
        # Start and partially complete
        start_response = service.start_wizard(StartWizardRequest(
            organization_id=organization_id
        ))
        wizard_id = start_response.wizard_id
        
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.WELCOME,
            data={},
            mark_complete=True,
        ))
        service.update_step(wizard_id, UpdateStepRequest(
            step=WizardStep.ORGANIZATION_PROFILE,
            data={"name": "Test Org", "timezone": "UTC"},
            mark_complete=True,
        ))
        
        # "Leave" and come back (simulated by starting wizard again)
        resume_response = service.start_wizard(StartWizardRequest(
            organization_id=organization_id
        ))
        
        # Should get same wizard
        assert resume_response.wizard_id == wizard_id
        
        # Progress should be preserved
        wizard = service.get_wizard(wizard_id)
        assert wizard.steps[WizardStep.ORGANIZATION_PROFILE].status == WizardStatus.COMPLETED
    
    def test_wizard_validation_prevents_bad_data(self, service, started_wizard):
        """Test that validation prevents saving bad data as complete."""
        # Try to complete with invalid data
        response = service.update_step(started_wizard, UpdateStepRequest(
            step=WizardStep.PIPELINE_STAGES,
            data={"stages": []},  # No stages
            mark_complete=True,
        ))
        
        assert response.status == WizardStatus.IN_PROGRESS
        assert "At least one pipeline stage is required" in response.validation_errors
        
        # Wizard should not advance
        wizard = service.get_wizard(started_wizard)
        assert wizard.steps[WizardStep.PIPELINE_STAGES].status != WizardStatus.COMPLETED
