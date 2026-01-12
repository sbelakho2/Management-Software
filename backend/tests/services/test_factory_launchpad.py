"""
Tests for Factory Launchpad: Greenfield Growth & Scalable Deployment.

Tests the Deployment Maturity Model (L0-L5), feature orchestration,
maturity-locked state machines, UI visibility, and hardware rollout tracking.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sensei.services.core.factory_launchpad import (
    # Enums
    MaturityLevel,
    MaturityTransitionStatus,
    FeatureModule,
    ChecklistItemStatus,
    ValidationSeverity,
    SiteStatus,
    HardwareAssetType,
    HardwareAssetStatus,
    # Data models
    SiteConfig,
    ChecklistItem,
    LevelUpChecklist,
    ValidationIssue,
    ActionValidationResult,
    HardwareAsset,
    RolloutProgress,
    FeatureAccess,
    UIVisibilityConfig,
    # Constants
    MATURITY_FEATURES,
    MATURITY_DESCRIPTIONS,
    DEFAULT_LEVEL_UP_CHECKLISTS,
    FIELD_VALIDATION_RULES,
    # Classes
    MaturityManager,
    UIVisibilityManager,
    HardwareRolloutTracker,
    FactoryLaunchpad,
    # Factory functions
    create_factory_launchpad,
    create_maturity_manager,
    create_ui_visibility_manager,
    create_hardware_tracker,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def maturity_manager() -> MaturityManager:
    """Create a maturity manager."""
    return create_maturity_manager()


@pytest.fixture
def launchpad() -> FactoryLaunchpad:
    """Create a factory launchpad."""
    return create_factory_launchpad()


@pytest.fixture
def hardware_tracker() -> HardwareRolloutTracker:
    """Create a hardware tracker."""
    return create_hardware_tracker()


@pytest.fixture
def registered_site(maturity_manager: MaturityManager) -> SiteConfig:
    """Create a registered site."""
    return maturity_manager.register_site(
        site_id="site-001",
        site_name="Test Factory",
        initial_level=MaturityLevel.L0_STRATEGIC,
        timezone="America/New_York",
    )


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_maturity_level_values(self):
        """Test MaturityLevel enum values."""
        assert MaturityLevel.L0_STRATEGIC.value == 0
        assert MaturityLevel.L1_PLANNING.value == 1
        assert MaturityLevel.L2_ENGINEERING.value == 2
        assert MaturityLevel.L3_REHEARSAL.value == 3
        assert MaturityLevel.L4_OPERATIONAL.value == 4
        assert MaturityLevel.L5_TPS.value == 5
    
    def test_maturity_level_ordering(self):
        """Test that maturity levels can be compared."""
        assert MaturityLevel.L0_STRATEGIC < MaturityLevel.L1_PLANNING
        assert MaturityLevel.L1_PLANNING < MaturityLevel.L5_TPS
        assert MaturityLevel.L5_TPS > MaturityLevel.L0_STRATEGIC
    
    def test_maturity_transition_status_values(self):
        """Test MaturityTransitionStatus enum values."""
        assert MaturityTransitionStatus.NOT_STARTED.value == "not_started"
        assert MaturityTransitionStatus.IN_PROGRESS.value == "in_progress"
        assert MaturityTransitionStatus.BLOCKED.value == "blocked"
        assert MaturityTransitionStatus.COMPLETED.value == "completed"
    
    def test_feature_module_values(self):
        """Test FeatureModule enum has expected values."""
        # L0 features
        assert FeatureModule.CRM.value == "crm"
        assert FeatureModule.RFQ.value == "rfq"
        assert FeatureModule.QUOTES.value == "quotes"
        # L5 features
        assert FeatureModule.ANDON.value == "andon"
        assert FeatureModule.JIDOKA.value == "jidoka"
    
    def test_checklist_item_status_values(self):
        """Test ChecklistItemStatus enum values."""
        assert ChecklistItemStatus.NOT_STARTED.value == "not_started"
        assert ChecklistItemStatus.COMPLETED.value == "completed"
        assert ChecklistItemStatus.BLOCKED.value == "blocked"
    
    def test_validation_severity_values(self):
        """Test ValidationSeverity enum values."""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.BLOCKING.value == "blocking"
    
    def test_site_status_values(self):
        """Test SiteStatus enum values."""
        assert SiteStatus.PLANNED.value == "planned"
        assert SiteStatus.OPERATIONAL.value == "operational"
        assert SiteStatus.FULL_TPS.value == "full_tps"
    
    def test_hardware_asset_type_values(self):
        """Test HardwareAssetType enum values."""
        assert HardwareAssetType.TABLET.value == "tablet"
        assert HardwareAssetType.EDGE_GATEWAY.value == "edge_gateway"
        assert HardwareAssetType.PLC.value == "plc"
    
    def test_hardware_asset_status_values(self):
        """Test HardwareAssetStatus enum values."""
        assert HardwareAssetStatus.ORDERED.value == "ordered"
        assert HardwareAssetStatus.ACTIVE.value == "active"
        assert HardwareAssetStatus.FAILED.value == "failed"


# =============================================================================
# CONSTANTS TESTS
# =============================================================================


class TestConstants:
    """Test constants and mappings."""
    
    def test_maturity_features_coverage(self):
        """Test that all levels have features defined."""
        for level in MaturityLevel:
            assert level in MATURITY_FEATURES
            assert len(MATURITY_FEATURES[level]) > 0
    
    def test_maturity_features_no_overlap(self):
        """Test that features are unique to each level."""
        all_features = []
        for features in MATURITY_FEATURES.values():
            for f in features:
                assert f not in all_features, f"Feature {f} appears in multiple levels"
                all_features.append(f)
    
    def test_maturity_descriptions_coverage(self):
        """Test that all levels have descriptions."""
        for level in MaturityLevel:
            assert level in MATURITY_DESCRIPTIONS
            desc = MATURITY_DESCRIPTIONS[level]
            assert "name" in desc
            assert "mode" in desc
            assert "focus" in desc
            assert "entry_criteria" in desc
            assert "exit_criteria" in desc
    
    def test_level_up_checklists_coverage(self):
        """Test that level transitions have checklists."""
        # Should have checklists for L0->L1, L1->L2, etc.
        assert (MaturityLevel.L0_STRATEGIC, MaturityLevel.L1_PLANNING) in DEFAULT_LEVEL_UP_CHECKLISTS
        assert (MaturityLevel.L1_PLANNING, MaturityLevel.L2_ENGINEERING) in DEFAULT_LEVEL_UP_CHECKLISTS
        assert (MaturityLevel.L4_OPERATIONAL, MaturityLevel.L5_TPS) in DEFAULT_LEVEL_UP_CHECKLISTS
    
    def test_field_validation_rules_valid_levels(self):
        """Test field validation rules have valid maturity levels."""
        for field, level in FIELD_VALIDATION_RULES.items():
            assert isinstance(field, str)
            assert level in MaturityLevel.__members__.values() or isinstance(level, int)


# =============================================================================
# SITE CONFIG TESTS
# =============================================================================


class TestSiteConfig:
    """Test SiteConfig data class."""
    
    def test_site_config_creation(self):
        """Test creating a site config."""
        config = SiteConfig(
            site_id="site-001",
            site_name="Test Factory",
        )
        assert config.site_id == "site-001"
        assert config.site_name == "Test Factory"
        assert config.current_level == MaturityLevel.L0_STRATEGIC
        assert config.status == SiteStatus.PLANNED
    
    def test_get_enabled_features_l0(self):
        """Test getting enabled features at L0."""
        config = SiteConfig(
            site_id="site-001",
            site_name="Test",
            current_level=MaturityLevel.L0_STRATEGIC,
        )
        features = config.get_enabled_features()
        assert FeatureModule.CRM in features
        assert FeatureModule.RFQ in features
        assert FeatureModule.ANDON not in features
    
    def test_get_enabled_features_l3(self):
        """Test getting enabled features at L3 includes L0-L3."""
        config = SiteConfig(
            site_id="site-001",
            site_name="Test",
            current_level=MaturityLevel.L3_REHEARSAL,
        )
        features = config.get_enabled_features()
        # Should include L0 features
        assert FeatureModule.CRM in features
        # Should include L3 features
        assert FeatureModule.VIRTUAL_GEMBA in features
        # Should not include L4+ features
        assert FeatureModule.WORK_ORDERS not in features
    
    def test_is_feature_enabled(self):
        """Test checking if specific feature is enabled."""
        config = SiteConfig(
            site_id="site-001",
            site_name="Test",
            current_level=MaturityLevel.L2_ENGINEERING,
        )
        assert config.is_feature_enabled(FeatureModule.CTQ_MANAGEMENT)
        assert not config.is_feature_enabled(FeatureModule.ANDON)
    
    def test_get_level_info(self):
        """Test getting level info."""
        config = SiteConfig(
            site_id="site-001",
            site_name="Test",
            current_level=MaturityLevel.L1_PLANNING,
        )
        info = config.get_level_info()
        assert info["name"] == "Design & Planning"
        assert info["mode"] == "Project Mode"


# =============================================================================
# CHECKLIST ITEM TESTS
# =============================================================================


class TestChecklistItem:
    """Test ChecklistItem data class."""
    
    def test_checklist_item_creation(self):
        """Test creating a checklist item."""
        item = ChecklistItem(
            item_id="item-001",
            title="Test Item",
            required=True,
        )
        assert item.item_id == "item-001"
        assert item.title == "Test Item"
        assert item.required
        assert item.status == ChecklistItemStatus.NOT_STARTED
    
    def test_is_complete_false(self):
        """Test is_complete returns false for not started."""
        item = ChecklistItem(item_id="item-001", title="Test")
        assert not item.is_complete
    
    def test_is_complete_true(self):
        """Test is_complete returns true for completed."""
        item = ChecklistItem(
            item_id="item-001",
            title="Test",
            status=ChecklistItemStatus.COMPLETED,
        )
        assert item.is_complete
    
    def test_is_blocking_required_incomplete(self):
        """Test is_blocking for required incomplete item."""
        item = ChecklistItem(item_id="item-001", title="Test", required=True)
        assert item.is_blocking
    
    def test_is_blocking_optional(self):
        """Test is_blocking for optional item."""
        item = ChecklistItem(item_id="item-001", title="Test", required=False)
        assert not item.is_blocking
    
    def test_is_blocking_required_complete(self):
        """Test is_blocking for completed required item."""
        item = ChecklistItem(
            item_id="item-001",
            title="Test",
            required=True,
            status=ChecklistItemStatus.COMPLETED,
        )
        assert not item.is_blocking


# =============================================================================
# LEVEL UP CHECKLIST TESTS
# =============================================================================


class TestLevelUpChecklist:
    """Test LevelUpChecklist data class."""
    
    def test_checklist_creation(self):
        """Test creating a level-up checklist."""
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
        )
        assert checklist.checklist_id == "cl-001"
        assert checklist.from_level == MaturityLevel.L0_STRATEGIC
        assert checklist.to_level == MaturityLevel.L1_PLANNING
        assert checklist.status == MaturityTransitionStatus.NOT_STARTED
    
    def test_completion_percentage_empty(self):
        """Test completion percentage with no items."""
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=[],
        )
        assert checklist.completion_percentage == 100.0
    
    def test_completion_percentage_partial(self):
        """Test completion percentage with some items complete."""
        items = [
            ChecklistItem(item_id="1", title="Item 1", status=ChecklistItemStatus.COMPLETED),
            ChecklistItem(item_id="2", title="Item 2", status=ChecklistItemStatus.NOT_STARTED),
        ]
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=items,
        )
        assert checklist.completion_percentage == 50.0
    
    def test_required_items_complete_all_done(self):
        """Test required_items_complete when all required are done."""
        items = [
            ChecklistItem(item_id="1", title="Required", required=True, status=ChecklistItemStatus.COMPLETED),
            ChecklistItem(item_id="2", title="Optional", required=False, status=ChecklistItemStatus.NOT_STARTED),
        ]
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=items,
        )
        assert checklist.required_items_complete
    
    def test_required_items_complete_not_done(self):
        """Test required_items_complete when required items pending."""
        items = [
            ChecklistItem(item_id="1", title="Required", required=True, status=ChecklistItemStatus.NOT_STARTED),
        ]
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=items,
        )
        assert not checklist.required_items_complete
    
    def test_blocking_items(self):
        """Test getting blocking items."""
        items = [
            ChecklistItem(item_id="1", title="Done", required=True, status=ChecklistItemStatus.COMPLETED),
            ChecklistItem(item_id="2", title="Blocking", required=True, status=ChecklistItemStatus.NOT_STARTED),
            ChecklistItem(item_id="3", title="Optional", required=False, status=ChecklistItemStatus.NOT_STARTED),
        ]
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=items,
        )
        blocking = checklist.blocking_items
        assert len(blocking) == 1
        assert blocking[0].title == "Blocking"
    
    def test_can_complete_success(self):
        """Test can_complete when all required items done."""
        items = [
            ChecklistItem(item_id="1", title="Done", required=True, status=ChecklistItemStatus.COMPLETED),
        ]
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=items,
        )
        can_complete, reasons = checklist.can_complete()
        assert can_complete
        assert len(reasons) == 0
    
    def test_can_complete_blocked(self):
        """Test can_complete when required items pending."""
        items = [
            ChecklistItem(item_id="1", title="Pending", required=True, status=ChecklistItemStatus.NOT_STARTED),
        ]
        checklist = LevelUpChecklist(
            checklist_id="cl-001",
            site_id="site-001",
            from_level=MaturityLevel.L0_STRATEGIC,
            to_level=MaturityLevel.L1_PLANNING,
            items=items,
        )
        can_complete, reasons = checklist.can_complete()
        assert not can_complete
        assert "Pending" in reasons[0]


# =============================================================================
# MATURITY MANAGER TESTS
# =============================================================================


class TestMaturityManager:
    """Test MaturityManager class."""
    
    def test_register_site(self, maturity_manager: MaturityManager):
        """Test registering a new site."""
        site = maturity_manager.register_site(
            site_id="site-001",
            site_name="Test Factory",
            timezone="America/New_York",
        )
        assert site.site_id == "site-001"
        assert site.site_name == "Test Factory"
        assert site.current_level == MaturityLevel.L0_STRATEGIC
    
    def test_register_site_with_initial_level(self, maturity_manager: MaturityManager):
        """Test registering site with non-default level."""
        site = maturity_manager.register_site(
            site_id="site-001",
            site_name="Existing Factory",
            initial_level=MaturityLevel.L4_OPERATIONAL,
        )
        assert site.current_level == MaturityLevel.L4_OPERATIONAL
    
    def test_get_site(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting a registered site."""
        site = maturity_manager.get_site("site-001")
        assert site is not None
        assert site.site_name == "Test Factory"
    
    def test_get_site_not_found(self, maturity_manager: MaturityManager):
        """Test getting a non-existent site."""
        site = maturity_manager.get_site("nonexistent")
        assert site is None
    
    def test_get_all_sites(self, maturity_manager: MaturityManager):
        """Test getting all sites."""
        maturity_manager.register_site("site-001", "Factory 1")
        maturity_manager.register_site("site-002", "Factory 2")
        sites = maturity_manager.get_all_sites()
        assert len(sites) == 2
    
    def test_get_current_level(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting current level for a site."""
        level = maturity_manager.get_current_level("site-001")
        assert level == MaturityLevel.L0_STRATEGIC
    
    def test_get_enabled_features(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting enabled features for a site."""
        features = maturity_manager.get_enabled_features("site-001")
        assert FeatureModule.CRM in features
        assert FeatureModule.ANDON not in features
    
    def test_is_feature_enabled(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test checking if feature is enabled."""
        assert maturity_manager.is_feature_enabled("site-001", FeatureModule.RFQ)
        assert not maturity_manager.is_feature_enabled("site-001", FeatureModule.WORK_ORDERS)
    
    def test_create_level_up_checklist(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test creating a level-up checklist."""
        checklist = maturity_manager.create_level_up_checklist("site-001")
        assert checklist is not None
        assert checklist.from_level == MaturityLevel.L0_STRATEGIC
        assert checklist.to_level == MaturityLevel.L1_PLANNING
        assert len(checklist.items) > 0
    
    def test_create_level_up_checklist_to_target(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test creating checklist to specific target level."""
        checklist = maturity_manager.create_level_up_checklist(
            "site-001",
            target_level=MaturityLevel.L1_PLANNING,
        )
        assert checklist is not None
        assert checklist.to_level == MaturityLevel.L1_PLANNING
    
    def test_create_level_up_checklist_invalid_target(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test creating checklist with invalid target (same as current)."""
        # When target_level is provided but is same as current level, should return None
        # First, let's test with a level lower than current
        maturity_manager.register_site(
            site_id="advanced-site",
            site_name="Advanced Factory",
            initial_level=MaturityLevel.L3_REHEARSAL,
        )
        
        # Try to create checklist to a lower level (L1 < L3)
        checklist = maturity_manager.create_level_up_checklist(
            "advanced-site",
            target_level=MaturityLevel.L1_PLANNING,
        )
        assert checklist is None
        
        # Also test beyond max level
        maturity_manager.register_site(
            site_id="max-site",
            site_name="Max Level Factory",
            initial_level=MaturityLevel.L5_TPS,
        )
        checklist = maturity_manager.create_level_up_checklist("max-site")
        assert checklist is None  # Can't level up from L5
    
    def test_get_checklist(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting a checklist by ID."""
        checklist = maturity_manager.create_level_up_checklist("site-001")
        retrieved = maturity_manager.get_checklist(checklist.checklist_id)
        assert retrieved is not None
        assert retrieved.checklist_id == checklist.checklist_id
    
    def test_get_site_checklists(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting all checklists for a site."""
        maturity_manager.create_level_up_checklist("site-001")
        checklists = maturity_manager.get_site_checklists("site-001")
        assert len(checklists) == 1
    
    def test_complete_checklist_item(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test completing a checklist item."""
        checklist = maturity_manager.create_level_up_checklist("site-001")
        item_id = checklist.items[0].item_id
        
        success = maturity_manager.complete_checklist_item(
            checklist_id=checklist.checklist_id,
            item_id=item_id,
            user_id="user-001",
            evidence_notes="Verified on site visit",
        )
        assert success
        
        # Verify item is completed
        updated_checklist = maturity_manager.get_checklist(checklist.checklist_id)
        item = next(i for i in updated_checklist.items if i.item_id == item_id)
        assert item.status == ChecklistItemStatus.COMPLETED
        assert item.completed_by == "user-001"
    
    def test_attempt_level_up_success(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test successful level-up."""
        checklist = maturity_manager.create_level_up_checklist("site-001")
        
        # Complete all required items
        for item in checklist.items:
            if item.required:
                maturity_manager.complete_checklist_item(
                    checklist.checklist_id,
                    item.item_id,
                    "user-001",
                )
        
        success, reasons = maturity_manager.attempt_level_up("site-001", checklist.checklist_id)
        assert success
        assert len(reasons) == 0
        
        # Verify level changed
        site = maturity_manager.get_site("site-001")
        assert site.current_level == MaturityLevel.L1_PLANNING
    
    def test_attempt_level_up_blocked(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test blocked level-up due to incomplete items."""
        checklist = maturity_manager.create_level_up_checklist("site-001")
        
        # Don't complete any items
        success, reasons = maturity_manager.attempt_level_up("site-001", checklist.checklist_id)
        assert not success
        assert len(reasons) > 0
        
        # Verify level unchanged
        site = maturity_manager.get_site("site-001")
        assert site.current_level == MaturityLevel.L0_STRATEGIC
    
    def test_validate_action_allowed(self, maturity_manager: MaturityManager):
        """Test validating action that is allowed."""
        maturity_manager.register_site(
            "site-001",
            "Factory",
            initial_level=MaturityLevel.L4_OPERATIONAL,
        )
        
        result = maturity_manager.validate_action(
            site_id="site-001",
            action="start_work_order",
            required_level=MaturityLevel.L4_OPERATIONAL,
        )
        assert result.allowed
        assert len(result.issues) == 0
    
    def test_validate_action_blocked(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test validating action that is blocked."""
        result = maturity_manager.validate_action(
            site_id="site-001",
            action="start_work_order",
            required_level=MaturityLevel.L4_OPERATIONAL,
        )
        assert not result.allowed
        assert len(result.issues) > 0
        assert result.issues[0].severity == ValidationSeverity.BLOCKING
    
    def test_validate_action_field_validation(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test field validation in action validation."""
        result = maturity_manager.validate_action(
            site_id="site-001",
            action="create_item",
            required_level=MaturityLevel.L0_STRATEGIC,
            fields={"machine_id": "machine-001"},  # Requires L3
        )
        assert not result.allowed
        field_issue = next((i for i in result.issues if i.field == "machine_id"), None)
        assert field_issue is not None
    
    def test_level_change_callback(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test level change callback is called."""
        callback_called = []
        
        def on_level_change(site_id, old_level, new_level):
            callback_called.append((site_id, old_level, new_level))
        
        maturity_manager.register_level_change_callback(on_level_change)
        
        # Level up
        checklist = maturity_manager.create_level_up_checklist("site-001")
        for item in checklist.items:
            if item.required:
                maturity_manager.complete_checklist_item(
                    checklist.checklist_id,
                    item.item_id,
                    "user-001",
                )
        maturity_manager.attempt_level_up("site-001", checklist.checklist_id)
        
        assert len(callback_called) == 1
        assert callback_called[0] == ("site-001", MaturityLevel.L0_STRATEGIC, MaturityLevel.L1_PLANNING)


# =============================================================================
# UI VISIBILITY MANAGER TESTS
# =============================================================================


class TestUIVisibilityManager:
    """Test UIVisibilityManager class."""
    
    def test_get_visibility_config(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting visibility config."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        config = ui_manager.get_visibility_config("site-001")
        
        assert config.site_id == "site-001"
        assert config.current_level == MaturityLevel.L0_STRATEGIC
        assert len(config.features) > 0
    
    def test_feature_visibility_enabled(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test that enabled features are visible."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        config = ui_manager.get_visibility_config("site-001")
        
        crm_access = next((f for f in config.features if f.feature == FeatureModule.CRM), None)
        assert crm_access is not None
        assert crm_access.enabled
        assert crm_access.visible
    
    def test_feature_visibility_disabled(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test that disabled features are not visible."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        config = ui_manager.get_visibility_config("site-001")
        
        andon_access = next((f for f in config.features if f.feature == FeatureModule.ANDON), None)
        assert andon_access is not None
        assert not andon_access.enabled
        assert not andon_access.visible
    
    def test_enable_preview(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test enabling future state preview."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        ui_manager.enable_preview("site-001", MaturityLevel.L3_REHEARSAL)
        
        config = ui_manager.get_visibility_config("site-001", include_preview=True)
        assert config.show_future_preview
        assert config.preview_level == MaturityLevel.L3_REHEARSAL
        
        # L3 features should be visible in preview
        gemba_access = next((f for f in config.features if f.feature == FeatureModule.VIRTUAL_GEMBA), None)
        assert gemba_access.visible
    
    def test_disable_preview(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test disabling preview."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        ui_manager.enable_preview("site-001", MaturityLevel.L3_REHEARSAL)
        ui_manager.disable_preview("site-001")
        
        config = ui_manager.get_visibility_config("site-001", include_preview=True)
        assert not config.show_future_preview
    
    def test_is_feature_visible(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test checking feature visibility."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        
        assert ui_manager.is_feature_visible("site-001", FeatureModule.CRM)
        assert not ui_manager.is_feature_visible("site-001", FeatureModule.ANDON)
    
    def test_get_hidden_features(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting hidden features."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        hidden = ui_manager.get_hidden_features("site-001")
        
        assert FeatureModule.ANDON in hidden
        assert FeatureModule.CRM not in hidden
    
    def test_get_upcoming_features(self, maturity_manager: MaturityManager, registered_site: SiteConfig):
        """Test getting upcoming features."""
        ui_manager = create_ui_visibility_manager(maturity_manager)
        upcoming = ui_manager.get_upcoming_features("site-001")
        
        assert MaturityLevel.L1_PLANNING in upcoming
        assert FeatureModule.FACTORY_ARCHITECT in upcoming[MaturityLevel.L1_PLANNING]


# =============================================================================
# HARDWARE ROLLOUT TRACKER TESTS
# =============================================================================


class TestHardwareRolloutTracker:
    """Test HardwareRolloutTracker class."""
    
    def test_register_asset(self, hardware_tracker: HardwareRolloutTracker):
        """Test registering a hardware asset."""
        asset = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Production Tablet 1",
            site_id="site-001",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        assert asset.asset_id is not None
        assert asset.asset_type == HardwareAssetType.TABLET
        assert asset.status == HardwareAssetStatus.ORDERED
    
    def test_get_asset(self, hardware_tracker: HardwareRolloutTracker):
        """Test getting an asset by ID."""
        asset = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.EDGE_GATEWAY,
            name="Gateway 1",
            site_id="site-001",
        )
        retrieved = hardware_tracker.get_asset(asset.asset_id)
        assert retrieved is not None
        assert retrieved.name == "Gateway 1"
    
    def test_get_asset_by_mac(self, hardware_tracker: HardwareRolloutTracker):
        """Test getting asset by MAC address."""
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.IOT_SENSOR,
            name="Sensor 1",
            site_id="site-001",
            mac_address="11:22:33:44:55:66",
        )
        asset = hardware_tracker.get_asset_by_mac("11:22:33:44:55:66")
        assert asset is not None
        assert asset.name == "Sensor 1"
    
    def test_get_site_assets(self, hardware_tracker: HardwareRolloutTracker):
        """Test getting all assets for a site."""
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 1",
            site_id="site-001",
        )
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 2",
            site_id="site-001",
        )
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 3",
            site_id="site-002",
        )
        
        assets = hardware_tracker.get_site_assets("site-001")
        assert len(assets) == 2
    
    def test_get_station_assets(self, hardware_tracker: HardwareRolloutTracker):
        """Test getting assets for a station."""
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.BARCODE_SCANNER,
            name="Scanner 1",
            site_id="site-001",
            station_id="station-001",
        )
        assets = hardware_tracker.get_station_assets("station-001")
        assert len(assets) == 1
    
    def test_update_asset_status(self, hardware_tracker: HardwareRolloutTracker):
        """Test updating asset status."""
        asset = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.EDGE_GATEWAY,
            name="Gateway 1",
            site_id="site-001",
        )
        
        success = hardware_tracker.update_asset_status(
            asset.asset_id,
            HardwareAssetStatus.DEPLOYED,
            ip_address="192.168.1.100",
        )
        assert success
        
        updated = hardware_tracker.get_asset(asset.asset_id)
        assert updated.status == HardwareAssetStatus.DEPLOYED
        assert updated.ip_address == "192.168.1.100"
    
    def test_link_to_station(self, hardware_tracker: HardwareRolloutTracker):
        """Test linking asset to station."""
        asset = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.PLC,
            name="PLC 1",
            site_id="site-001",
        )
        
        success = hardware_tracker.link_to_station(asset.asset_id, "station-001")
        assert success
        
        updated = hardware_tracker.get_asset(asset.asset_id)
        assert updated.station_id == "station-001"
    
    def test_discover_asset_new(self, hardware_tracker: HardwareRolloutTracker):
        """Test discovering a new asset."""
        asset = hardware_tracker.discover_asset(
            mac_address="AA:BB:CC:DD:EE:FF",
            ip_address="192.168.1.50",
            asset_type=HardwareAssetType.IOT_SENSOR,
            site_id="site-001",
        )
        assert asset is not None
        assert asset.status == HardwareAssetStatus.DELIVERED
        assert asset.last_seen is not None
    
    def test_discover_asset_existing(self, hardware_tracker: HardwareRolloutTracker):
        """Test discovering an existing asset."""
        # Register first
        original = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.EDGE_GATEWAY,
            name="Gateway 1",
            site_id="site-001",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        
        # Discover
        discovered = hardware_tracker.discover_asset(
            mac_address="AA:BB:CC:DD:EE:FF",
            ip_address="192.168.1.100",
        )
        
        assert discovered.asset_id == original.asset_id
        assert discovered.ip_address == "192.168.1.100"
        assert discovered.status == HardwareAssetStatus.DELIVERED
    
    def test_get_discovery_log(self, hardware_tracker: HardwareRolloutTracker):
        """Test getting discovery log."""
        hardware_tracker.discover_asset(
            mac_address="AA:BB:CC:DD:EE:FF",
            ip_address="192.168.1.50",
            site_id="site-001",
        )
        
        log = hardware_tracker.get_discovery_log(site_id="site-001")
        assert len(log) == 1
        assert log[0]["mac_address"] == "AA:BB:CC:DD:EE:FF"
    
    def test_get_rollout_progress(self, hardware_tracker: HardwareRolloutTracker):
        """Test getting rollout progress."""
        # Register various assets
        asset1 = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 1",
            site_id="site-001",
        )
        asset2 = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 2",
            site_id="site-001",
        )
        asset3 = hardware_tracker.register_asset(
            asset_type=HardwareAssetType.EDGE_GATEWAY,
            name="Gateway 1",
            site_id="site-001",
        )
        
        # Deploy some
        hardware_tracker.update_asset_status(asset1.asset_id, HardwareAssetStatus.ACTIVE)
        hardware_tracker.update_asset_status(asset3.asset_id, HardwareAssetStatus.DEPLOYED)
        
        progress = hardware_tracker.get_rollout_progress("site-001")
        assert progress.total_assets == 3
        assert progress.deployed_assets == 2
        assert progress.active_assets == 1
    
    def test_rollout_progress_by_type(self, hardware_tracker: HardwareRolloutTracker):
        """Test rollout progress by asset type."""
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 1",
            site_id="site-001",
        )
        hardware_tracker.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Tablet 2",
            site_id="site-001",
        )
        
        progress = hardware_tracker.get_rollout_progress("site-001")
        assert HardwareAssetType.TABLET in progress.by_type
        assert progress.by_type[HardwareAssetType.TABLET]["total"] == 2


# =============================================================================
# FACTORY LAUNCHPAD TESTS
# =============================================================================


class TestFactoryLaunchpad:
    """Test FactoryLaunchpad class."""
    
    def test_create_launchpad(self, launchpad: FactoryLaunchpad):
        """Test creating a launchpad."""
        assert launchpad.maturity is not None
        assert launchpad.ui is not None
        assert launchpad.hardware is not None
    
    def test_initialize_site(self, launchpad: FactoryLaunchpad):
        """Test initializing a site."""
        site = launchpad.initialize_site(
            site_id="site-001",
            site_name="New Factory",
            timezone="Europe/London",
        )
        assert site.site_id == "site-001"
        assert site.current_level == MaturityLevel.L0_STRATEGIC
    
    def test_get_site_dashboard(self, launchpad: FactoryLaunchpad):
        """Test getting site dashboard."""
        launchpad.initialize_site("site-001", "Test Factory")
        dashboard = launchpad.get_site_dashboard("site-001")
        
        assert dashboard["site_id"] == "site-001"
        assert dashboard["current_level"] == "L0_STRATEGIC"
        assert "enabled_features" in dashboard
        assert "hardware_rollout" in dashboard
    
    def test_get_site_dashboard_not_found(self, launchpad: FactoryLaunchpad):
        """Test getting dashboard for non-existent site."""
        dashboard = launchpad.get_site_dashboard("nonexistent")
        assert "error" in dashboard
    
    def test_validate_work_order_start_blocked(self, launchpad: FactoryLaunchpad):
        """Test work order validation at L0."""
        launchpad.initialize_site("site-001", "New Factory")
        
        result = launchpad.validate_work_order_start(
            "site-001",
            {"product_id": "prod-001"},
        )
        assert not result.allowed
        assert result.required_level == MaturityLevel.L4_OPERATIONAL
    
    def test_validate_work_order_start_allowed(self, launchpad: FactoryLaunchpad):
        """Test work order validation at L4."""
        launchpad.initialize_site(
            "site-001",
            "Operational Factory",
            initial_level=MaturityLevel.L4_OPERATIONAL,
        )
        
        result = launchpad.validate_work_order_start(
            "site-001",
            {"product_id": "prod-001"},
        )
        assert result.allowed
    
    def test_validate_andon_trigger(self, launchpad: FactoryLaunchpad):
        """Test Andon validation requires L5."""
        launchpad.initialize_site(
            "site-001",
            "Factory",
            initial_level=MaturityLevel.L4_OPERATIONAL,
        )
        
        result = launchpad.validate_andon_trigger("site-001", {})
        assert not result.allowed
        assert result.required_level == MaturityLevel.L5_TPS
    
    def test_get_maturity_roadmap(self, launchpad: FactoryLaunchpad):
        """Test getting maturity roadmap."""
        launchpad.initialize_site("site-001", "Factory")
        roadmap = launchpad.get_maturity_roadmap("site-001")
        
        assert len(roadmap) == 6  # L0 through L5
        
        # Check L0 is current
        l0 = next(r for r in roadmap if r["level"] == "L0_STRATEGIC")
        assert l0["is_current"]
        assert not l0["is_future"]
        
        # Check L5 is future
        l5 = next(r for r in roadmap if r["level"] == "L5_TPS")
        assert l5["is_future"]
        assert not l5["is_current"]
    
    def test_full_level_up_workflow(self, launchpad: FactoryLaunchpad):
        """Test complete level-up workflow."""
        # Initialize site
        site = launchpad.initialize_site("site-001", "New Factory")
        assert site.current_level == MaturityLevel.L0_STRATEGIC
        
        # Create checklist
        checklist = launchpad.maturity.create_level_up_checklist("site-001")
        assert checklist is not None
        
        # Complete all required items
        for item in checklist.items:
            if item.required:
                launchpad.maturity.complete_checklist_item(
                    checklist.checklist_id,
                    item.item_id,
                    "admin-001",
                    evidence_notes="Verified",
                )
        
        # Level up
        success, reasons = launchpad.maturity.attempt_level_up(
            "site-001",
            checklist.checklist_id,
        )
        assert success
        
        # Verify new level
        updated_site = launchpad.maturity.get_site("site-001")
        assert updated_site.current_level == MaturityLevel.L1_PLANNING
        
        # Verify new features available
        assert launchpad.maturity.is_feature_enabled("site-001", FeatureModule.FACTORY_ARCHITECT)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for Factory Launchpad."""
    
    def test_full_factory_rollout_simulation(self, launchpad: FactoryLaunchpad):
        """Simulate a full factory rollout from L0 to L5."""
        # Initialize at L0
        site = launchpad.initialize_site(
            site_id="factory-alpha",
            site_name="Alpha Manufacturing",
        )
        
        # Register some hardware
        launchpad.hardware.register_asset(
            asset_type=HardwareAssetType.TABLET,
            name="Floor Tablet 1",
            site_id="factory-alpha",
        )
        
        # Progress through each level
        current_level = MaturityLevel.L0_STRATEGIC
        while current_level < MaturityLevel.L5_TPS:
            # Create checklist for next level
            checklist = launchpad.maturity.create_level_up_checklist("factory-alpha")
            if not checklist:
                break
            
            # Complete all items
            for item in checklist.items:
                launchpad.maturity.complete_checklist_item(
                    checklist.checklist_id,
                    item.item_id,
                    "admin",
                )
            
            # Level up
            success, _ = launchpad.maturity.attempt_level_up(
                "factory-alpha",
                checklist.checklist_id,
            )
            assert success
            
            current_level = launchpad.maturity.get_current_level("factory-alpha")
        
        # Verify reached L5
        final_site = launchpad.maturity.get_site("factory-alpha")
        assert final_site.current_level == MaturityLevel.L5_TPS
        assert final_site.status == SiteStatus.FULL_TPS
        
        # Verify all features enabled
        features = final_site.get_enabled_features()
        assert FeatureModule.ANDON in features
        assert FeatureModule.JIDOKA in features
        assert FeatureModule.PREDICTIVE_ANALYTICS in features
    
    def test_multi_site_management(self, launchpad: FactoryLaunchpad):
        """Test managing multiple sites at different maturity levels."""
        # Initialize sites at different levels
        site_a = launchpad.initialize_site(
            "site-a",
            "Factory A",
            initial_level=MaturityLevel.L0_STRATEGIC,
        )
        site_b = launchpad.initialize_site(
            "site-b",
            "Factory B",
            initial_level=MaturityLevel.L3_REHEARSAL,
        )
        site_c = launchpad.initialize_site(
            "site-c",
            "Factory C",
            initial_level=MaturityLevel.L5_TPS,
        )
        
        # Verify different feature sets
        features_a = launchpad.maturity.get_enabled_features("site-a")
        features_b = launchpad.maturity.get_enabled_features("site-b")
        features_c = launchpad.maturity.get_enabled_features("site-c")
        
        assert len(features_a) < len(features_b) < len(features_c)
        
        # Verify Andon only available in site C
        assert not launchpad.maturity.is_feature_enabled("site-a", FeatureModule.ANDON)
        assert not launchpad.maturity.is_feature_enabled("site-b", FeatureModule.ANDON)
        assert launchpad.maturity.is_feature_enabled("site-c", FeatureModule.ANDON)
    
    def test_hardware_discovery_integration(self, launchpad: FactoryLaunchpad):
        """Test hardware discovery with maturity tracking."""
        launchpad.initialize_site("site-001", "Factory")
        
        # Pre-register expected assets
        expected = launchpad.hardware.register_asset(
            asset_type=HardwareAssetType.EDGE_GATEWAY,
            name="Main Gateway",
            site_id="site-001",
            mac_address="AA:BB:CC:DD:EE:01",
        )
        
        # Simulate discovery
        discovered = launchpad.hardware.discover_asset(
            mac_address="AA:BB:CC:DD:EE:01",
            ip_address="192.168.1.100",
        )
        
        assert discovered.asset_id == expected.asset_id
        assert discovered.status == HardwareAssetStatus.DELIVERED
        
        # Verify discovery logged
        log = launchpad.hardware.get_discovery_log("site-001")
        assert len(log) == 1
        
        # Get rollout progress
        progress = launchpad.hardware.get_rollout_progress("site-001")
        assert progress.total_assets == 1


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_factory_launchpad(self):
        """Test creating factory launchpad."""
        launchpad = create_factory_launchpad()
        assert isinstance(launchpad, FactoryLaunchpad)
    
    def test_create_maturity_manager(self):
        """Test creating maturity manager."""
        manager = create_maturity_manager()
        assert isinstance(manager, MaturityManager)
    
    def test_create_ui_visibility_manager(self):
        """Test creating UI visibility manager."""
        maturity = create_maturity_manager()
        ui = create_ui_visibility_manager(maturity)
        assert isinstance(ui, UIVisibilityManager)
    
    def test_create_hardware_tracker(self):
        """Test creating hardware tracker."""
        tracker = create_hardware_tracker()
        assert isinstance(tracker, HardwareRolloutTracker)
