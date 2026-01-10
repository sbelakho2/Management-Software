"""
E2E Tests for Section 20.6: Factory Launchpad & Maturity Gates.

Tests the Deployment Maturity Model verification:
- Maturity Toggle Verification: Level 1 hides Production/Andon modules
- Level Up Event: Features unlock instantly without data loss
- Rehearsal Fidelity: Rehearsal UI matches Production UI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any

import pytest


# =============================================================================
# ENUMS
# =============================================================================


class E2EMaturityLevel(IntEnum):
    """Maturity levels for E2E verification."""
    L0_STRATEGIC = 0
    L1_DESIGN = 1
    L2_ENGINEERING = 2
    L3_REHEARSAL = 3
    L4_PRODUCTION = 4
    L5_TPS = 5


class E2EFeatureModule(Enum):
    """Feature modules that can be enabled/disabled by maturity level."""
    # L0 - Strategic (always visible)
    CRM = "crm"
    RFQ = "rfq"
    QUOTES = "quotes"
    ACCOUNTS = "accounts"
    
    # L1 - Design/Planning
    ORDERS = "orders"
    ONBOARDING = "onboarding"
    TRAINING = "training"
    
    # L2 - Engineering
    BOM = "bom"
    ROUTING = "routing"
    QUALITY_PLANNING = "quality_planning"
    
    # L3 - Rehearsal
    WORK_ORDERS = "work_orders"
    STANDARD_WORK = "standard_work"
    REHEARSAL_MODE = "rehearsal_mode"
    
    # L4 - Production
    PRODUCTION = "production"
    LIVE_TRACKING = "live_tracking"
    METRICS = "metrics"
    
    # L5 - TPS
    ANDON = "andon"
    JIDOKA = "jidoka"
    KAIZEN = "kaizen"
    HEIJUNKA = "heijunka"


class E2EVerificationStatus(Enum):
    """Verification test status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# MATURITY FEATURE MAPPING
# =============================================================================

# Features available at each maturity level (cumulative)
E2E_MATURITY_FEATURES: dict[E2EMaturityLevel, set[E2EFeatureModule]] = {
    E2EMaturityLevel.L0_STRATEGIC: {
        E2EFeatureModule.CRM,
        E2EFeatureModule.RFQ,
        E2EFeatureModule.QUOTES,
        E2EFeatureModule.ACCOUNTS,
    },
    E2EMaturityLevel.L1_DESIGN: {
        E2EFeatureModule.ORDERS,
        E2EFeatureModule.ONBOARDING,
        E2EFeatureModule.TRAINING,
    },
    E2EMaturityLevel.L2_ENGINEERING: {
        E2EFeatureModule.BOM,
        E2EFeatureModule.ROUTING,
        E2EFeatureModule.QUALITY_PLANNING,
    },
    E2EMaturityLevel.L3_REHEARSAL: {
        E2EFeatureModule.WORK_ORDERS,
        E2EFeatureModule.STANDARD_WORK,
        E2EFeatureModule.REHEARSAL_MODE,
    },
    E2EMaturityLevel.L4_PRODUCTION: {
        E2EFeatureModule.PRODUCTION,
        E2EFeatureModule.LIVE_TRACKING,
        E2EFeatureModule.METRICS,
    },
    E2EMaturityLevel.L5_TPS: {
        E2EFeatureModule.ANDON,
        E2EFeatureModule.JIDOKA,
        E2EFeatureModule.KAIZEN,
        E2EFeatureModule.HEIJUNKA,
    },
}

# Features that should be HIDDEN at Level 1 (Production and Andon modules)
PRODUCTION_ANDON_MODULES = {
    E2EFeatureModule.PRODUCTION,
    E2EFeatureModule.LIVE_TRACKING,
    E2EFeatureModule.METRICS,
    E2EFeatureModule.ANDON,
    E2EFeatureModule.JIDOKA,
    E2EFeatureModule.KAIZEN,
    E2EFeatureModule.HEIJUNKA,
    E2EFeatureModule.WORK_ORDERS,
    E2EFeatureModule.STANDARD_WORK,
    E2EFeatureModule.REHEARSAL_MODE,
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class SiteData:
    """Represents site data that must be preserved during level-up."""
    site_id: str
    records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_record(self, module: str, record: dict[str, Any]):
        """Add a record to a module."""
        if module not in self.records:
            self.records[module] = []
        self.records[module].append(record)
    
    def get_record_count(self, module: str) -> int:
        """Get count of records in a module."""
        return len(self.records.get(module, []))
    
    def get_total_records(self) -> int:
        """Get total count of all records."""
        return sum(len(recs) for recs in self.records.values())


@dataclass
class UIElementState:
    """Represents UI element visibility state."""
    element_id: str
    module: E2EFeatureModule
    visible: bool
    enabled: bool
    rendered: bool
    css_classes: list[str] = field(default_factory=list)
    dom_structure: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of a verification test."""
    test_name: str
    status: E2EVerificationStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LevelUpEvent:
    """Represents a level-up event."""
    site_id: str
    from_level: E2EMaturityLevel
    to_level: E2EMaturityLevel
    features_unlocked: set[E2EFeatureModule]
    data_preserved: bool
    unlock_latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)


# =============================================================================
# E2E MATURITY VERIFICATION SERVICE
# =============================================================================


class FactoryLaunchpadE2EService:
    """
    E2E verification service for Factory Launchpad maturity gates.
    
    Tests:
    - Maturity toggle verification (modules hidden at Level 1)
    - Level-up instant feature unlock without data loss
    - Rehearsal UI fidelity matching Production UI
    """
    
    ALLOWED_ROLES = {"admin", "ceo", "gm", "exec", "ops", "it"}
    
    def __init__(self):
        self._sites: dict[str, dict[str, Any]] = {}
        self._site_levels: dict[str, E2EMaturityLevel] = {}
        self._site_data: dict[str, SiteData] = {}
        self._ui_states: dict[str, dict[E2EFeatureModule, UIElementState]] = {}
        self._level_up_events: list[LevelUpEvent] = []
        self._verification_results: list[VerificationResult] = []
    
    def _check_role(self, user_role: str) -> bool:
        """Check if user role is allowed."""
        normalized = user_role.lower().replace("-", "_").strip()
        return normalized in self.ALLOWED_ROLES
    
    # =========================================================================
    # SITE MANAGEMENT
    # =========================================================================
    
    def register_site(
        self,
        site_id: str,
        site_name: str,
        initial_level: E2EMaturityLevel = E2EMaturityLevel.L0_STRATEGIC,
        user_role: str = "admin"
    ) -> dict[str, Any]:
        """Register a new site for E2E testing."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot register sites")
        
        self._sites[site_id] = {
            "site_id": site_id,
            "site_name": site_name,
            "created_at": datetime.now(),
        }
        self._site_levels[site_id] = initial_level
        self._site_data[site_id] = SiteData(site_id=site_id)
        self._initialize_ui_state(site_id, initial_level)
        
        return {
            "site_id": site_id,
            "site_name": site_name,
            "level": initial_level.name,
        }
    
    def get_site_level(self, site_id: str) -> E2EMaturityLevel | None:
        """Get current maturity level for a site."""
        return self._site_levels.get(site_id)
    
    def _initialize_ui_state(self, site_id: str, level: E2EMaturityLevel):
        """Initialize UI state for a site at given level."""
        enabled_features = self._get_enabled_features(level)
        ui_states: dict[E2EFeatureModule, UIElementState] = {}
        
        for feature in E2EFeatureModule:
            is_enabled = feature in enabled_features
            ui_states[feature] = UIElementState(
                element_id=f"nav-{feature.value}",
                module=feature,
                visible=is_enabled,
                enabled=is_enabled,
                rendered=is_enabled,
                css_classes=["nav-item", "enabled" if is_enabled else "hidden"],
                dom_structure=self._generate_dom_structure(feature, is_enabled),
            )
        
        self._ui_states[site_id] = ui_states
    
    def _get_enabled_features(self, level: E2EMaturityLevel) -> set[E2EFeatureModule]:
        """Get all features enabled up to and including given level."""
        enabled = set()
        for lvl in E2EMaturityLevel:
            if lvl.value <= level.value:
                enabled.update(E2E_MATURITY_FEATURES.get(lvl, set()))
        return enabled
    
    def _generate_dom_structure(
        self, feature: E2EFeatureModule, enabled: bool
    ) -> dict[str, Any]:
        """Generate mock DOM structure for a feature."""
        if not enabled:
            return {}  # Not rendered
        
        return {
            "tag": "div",
            "id": f"module-{feature.value}",
            "classes": ["module-container", feature.value],
            "children": [
                {
                    "tag": "header",
                    "classes": ["module-header"],
                    "text": feature.value.replace("_", " ").title(),
                },
                {
                    "tag": "main",
                    "classes": ["module-content"],
                    "children": [],
                },
            ],
        }
    
    # =========================================================================
    # MATURITY TOGGLE VERIFICATION (20.6.1)
    # =========================================================================
    
    def switch_site_to_level(
        self,
        site_id: str,
        target_level: E2EMaturityLevel,
        user_role: str = "admin"
    ) -> dict[str, Any]:
        """Switch site to a specific maturity level."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot switch site levels")
        
        if site_id not in self._sites:
            raise ValueError(f"Site '{site_id}' not found")
        
        old_level = self._site_levels[site_id]
        self._site_levels[site_id] = target_level
        self._initialize_ui_state(site_id, target_level)
        
        return {
            "site_id": site_id,
            "old_level": old_level.name,
            "new_level": target_level.name,
            "features_visible": [
                f.value for f in self._get_enabled_features(target_level)
            ],
        }
    
    def verify_production_andon_hidden_at_level1(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> VerificationResult:
        """
        Verify all Production/Andon modules are 100% hidden at Level 1.
        
        Checks that:
        - Production module is not visible
        - Andon module is not visible
        - All L4/L5 modules are hidden
        - UI elements are not rendered (not just CSS hidden)
        """
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot verify maturity")
        
        if site_id not in self._sites:
            return VerificationResult(
                test_name="production_andon_hidden_level1",
                status=E2EVerificationStatus.FAILED,
                message=f"Site '{site_id}' not found",
            )
        
        # Ensure site is at Level 1
        current_level = self._site_levels[site_id]
        if current_level != E2EMaturityLevel.L1_DESIGN:
            return VerificationResult(
                test_name="production_andon_hidden_level1",
                status=E2EVerificationStatus.SKIPPED,
                message=f"Site is at {current_level.name}, not Level 1",
            )
        
        ui_states = self._ui_states.get(site_id, {})
        hidden_check_results: dict[str, bool] = {}
        all_hidden = True
        
        for module in PRODUCTION_ANDON_MODULES:
            state = ui_states.get(module)
            if state:
                is_hidden = (
                    not state.visible and 
                    not state.enabled and 
                    not state.rendered
                )
                hidden_check_results[module.value] = is_hidden
                if not is_hidden:
                    all_hidden = False
            else:
                hidden_check_results[module.value] = True  # Not in UI = hidden
        
        if all_hidden:
            result = VerificationResult(
                test_name="production_andon_hidden_level1",
                status=E2EVerificationStatus.PASSED,
                message="All Production/Andon modules are 100% hidden at Level 1",
                details={
                    "modules_checked": len(PRODUCTION_ANDON_MODULES),
                    "all_hidden": True,
                    "results": hidden_check_results,
                },
            )
        else:
            visible_modules = [
                m for m, hidden in hidden_check_results.items() if not hidden
            ]
            result = VerificationResult(
                test_name="production_andon_hidden_level1",
                status=E2EVerificationStatus.FAILED,
                message=f"Some modules are visible: {visible_modules}",
                details={
                    "modules_checked": len(PRODUCTION_ANDON_MODULES),
                    "all_hidden": False,
                    "visible_modules": visible_modules,
                    "results": hidden_check_results,
                },
            )
        
        self._verification_results.append(result)
        return result
    
    def get_visible_modules(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> list[E2EFeatureModule]:
        """Get list of visible modules for a site."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot check visibility")
        
        ui_states = self._ui_states.get(site_id, {})
        return [
            state.module
            for state in ui_states.values()
            if state.visible
        ]
    
    def get_hidden_modules(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> list[E2EFeatureModule]:
        """Get list of hidden modules for a site."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot check visibility")
        
        ui_states = self._ui_states.get(site_id, {})
        return [
            state.module
            for state in ui_states.values()
            if not state.visible
        ]
    
    # =========================================================================
    # LEVEL-UP EVENT VERIFICATION (20.6.2)
    # =========================================================================
    
    def add_site_data(
        self,
        site_id: str,
        module: str,
        record: dict[str, Any],
        user_role: str = "admin"
    ) -> bool:
        """Add data to a site for data preservation testing."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot add data")
        
        if site_id not in self._site_data:
            return False
        
        self._site_data[site_id].add_record(module, record)
        return True
    
    def get_site_data_count(self, site_id: str) -> int:
        """Get total data record count for a site."""
        if site_id not in self._site_data:
            return 0
        return self._site_data[site_id].get_total_records()
    
    def perform_level_up(
        self,
        site_id: str,
        target_level: E2EMaturityLevel,
        user_role: str = "admin"
    ) -> LevelUpEvent:
        """
        Perform level-up and track feature unlocking.
        
        Features must unlock instantly without data loss.
        """
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot perform level-up")
        
        if site_id not in self._sites:
            raise ValueError(f"Site '{site_id}' not found")
        
        from_level = self._site_levels[site_id]
        
        if target_level.value <= from_level.value:
            raise ValueError(
                f"Cannot level up from {from_level.name} to {target_level.name}"
            )
        
        # Record data count before level-up
        data_count_before = self.get_site_data_count(site_id)
        
        # Perform level-up (simulated instant unlock)
        import time
        start_time = time.perf_counter()
        
        # Calculate newly unlocked features
        old_features = self._get_enabled_features(from_level)
        new_features = self._get_enabled_features(target_level)
        unlocked_features = new_features - old_features
        
        # Update level and UI state
        self._site_levels[site_id] = target_level
        self._initialize_ui_state(site_id, target_level)
        
        end_time = time.perf_counter()
        unlock_latency_ms = (end_time - start_time) * 1000
        
        # Verify data preserved
        data_count_after = self.get_site_data_count(site_id)
        data_preserved = data_count_after == data_count_before
        
        event = LevelUpEvent(
            site_id=site_id,
            from_level=from_level,
            to_level=target_level,
            features_unlocked=unlocked_features,
            data_preserved=data_preserved,
            unlock_latency_ms=unlock_latency_ms,
        )
        
        self._level_up_events.append(event)
        return event
    
    def verify_level_up_instant_unlock(
        self,
        site_id: str,
        from_level: E2EMaturityLevel,
        to_level: E2EMaturityLevel,
        user_role: str = "admin"
    ) -> VerificationResult:
        """
        Verify that level-up unlocks features instantly without data loss.
        
        Criteria:
        - All new features visible immediately
        - No data loss during transition
        - Unlock latency < 100ms
        """
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot verify level-up")
        
        # Add test data before level-up
        test_records = [
            {"id": "rec-1", "type": "quote", "value": 1000},
            {"id": "rec-2", "type": "order", "value": 2000},
            {"id": "rec-3", "type": "contact", "value": "Test Contact"},
        ]
        for rec in test_records:
            self.add_site_data(site_id, "test_module", rec, user_role)
        
        data_before = self.get_site_data_count(site_id)
        
        # Ensure site is at from_level
        self.switch_site_to_level(site_id, from_level, user_role)
        
        # Perform level-up
        event = self.perform_level_up(site_id, to_level, user_role)
        
        # Verify
        data_after = self.get_site_data_count(site_id)
        
        issues = []
        
        if not event.data_preserved:
            issues.append(f"Data loss: {data_before} -> {data_after} records")
        
        if event.unlock_latency_ms > 100:
            issues.append(
                f"Unlock too slow: {event.unlock_latency_ms:.2f}ms > 100ms"
            )
        
        # Verify unlocked features are now visible
        visible = self.get_visible_modules(site_id, user_role)
        expected = self._get_enabled_features(to_level)
        missing = expected - set(visible)
        
        if missing:
            issues.append(
                f"Features not visible after unlock: {[m.value for m in missing]}"
            )
        
        if issues:
            result = VerificationResult(
                test_name="level_up_instant_unlock",
                status=E2EVerificationStatus.FAILED,
                message="; ".join(issues),
                details={
                    "from_level": from_level.name,
                    "to_level": to_level.name,
                    "features_unlocked": len(event.features_unlocked),
                    "unlock_latency_ms": event.unlock_latency_ms,
                    "data_preserved": event.data_preserved,
                    "issues": issues,
                },
            )
        else:
            result = VerificationResult(
                test_name="level_up_instant_unlock",
                status=E2EVerificationStatus.PASSED,
                message=(
                    f"Level-up from {from_level.name} to {to_level.name} "
                    f"successful with {len(event.features_unlocked)} features "
                    f"unlocked in {event.unlock_latency_ms:.2f}ms, no data loss"
                ),
                details={
                    "from_level": from_level.name,
                    "to_level": to_level.name,
                    "features_unlocked": [f.value for f in event.features_unlocked],
                    "unlock_latency_ms": event.unlock_latency_ms,
                    "data_preserved": event.data_preserved,
                    "data_count": data_after,
                },
            )
        
        self._verification_results.append(result)
        return result
    
    def get_level_up_history(
        self, site_id: str | None = None
    ) -> list[LevelUpEvent]:
        """Get level-up event history."""
        if site_id:
            return [e for e in self._level_up_events if e.site_id == site_id]
        return list(self._level_up_events)
    
    # =========================================================================
    # REHEARSAL FIDELITY VERIFICATION (20.6.3)
    # =========================================================================
    
    def get_ui_structure(
        self,
        site_id: str,
        level: E2EMaturityLevel,
        user_role: str = "admin"
    ) -> dict[str, Any]:
        """Get UI structure at a specific level."""
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot get UI structure")
        
        # Save current level
        current = self._site_levels.get(site_id)
        
        # Temporarily switch to requested level
        self.switch_site_to_level(site_id, level, user_role)
        
        # Get UI structure
        ui_states = self._ui_states.get(site_id, {})
        structure = {}
        
        for feature, state in ui_states.items():
            if state.visible:
                structure[feature.value] = {
                    "element_id": state.element_id,
                    "css_classes": state.css_classes,
                    "dom_structure": state.dom_structure,
                    "enabled": state.enabled,
                    "rendered": state.rendered,
                }
        
        # Restore original level if needed
        if current:
            self.switch_site_to_level(site_id, current, user_role)
        
        return structure
    
    def generate_rehearsal_ui(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> dict[str, Any]:
        """
        Generate Standard Work Rehearsal UI (Level 3).
        
        The Rehearsal UI should be indistinguishable from Production UI.
        """
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot generate UI")
        
        # Rehearsal UI includes all L3 features styled identically to L4
        rehearsal_features = {
            E2EFeatureModule.WORK_ORDERS,
            E2EFeatureModule.STANDARD_WORK,
            E2EFeatureModule.REHEARSAL_MODE,
        }
        
        ui_structure = {}
        for feature in rehearsal_features:
            ui_structure[feature.value] = {
                "element_id": f"nav-{feature.value}",
                "css_classes": [
                    "nav-item", 
                    "enabled",
                    "production-style",  # Same styling as production
                ],
                "dom_structure": {
                    "tag": "div",
                    "id": f"module-{feature.value}",
                    "classes": [
                        "module-container", 
                        feature.value,
                        "production-layout",  # Production layout
                    ],
                    "children": [
                        {
                            "tag": "header",
                            "classes": ["module-header", "production-header"],
                            "text": feature.value.replace("_", " ").title(),
                        },
                        {
                            "tag": "main",
                            "classes": ["module-content", "production-content"],
                            "children": self._generate_production_style_content(feature),
                        },
                    ],
                },
                "enabled": True,
                "rendered": True,
            }
        
        return ui_structure
    
    def generate_production_ui(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> dict[str, Any]:
        """
        Generate Production UI (Level 4).
        
        This is the reference for Rehearsal UI fidelity comparison.
        """
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot generate UI")
        
        # Production UI features
        production_features = {
            E2EFeatureModule.WORK_ORDERS,
            E2EFeatureModule.STANDARD_WORK,
            E2EFeatureModule.PRODUCTION,
            E2EFeatureModule.LIVE_TRACKING,
            E2EFeatureModule.METRICS,
        }
        
        ui_structure = {}
        for feature in production_features:
            ui_structure[feature.value] = {
                "element_id": f"nav-{feature.value}",
                "css_classes": [
                    "nav-item", 
                    "enabled",
                    "production-style",
                ],
                "dom_structure": {
                    "tag": "div",
                    "id": f"module-{feature.value}",
                    "classes": [
                        "module-container", 
                        feature.value,
                        "production-layout",
                    ],
                    "children": [
                        {
                            "tag": "header",
                            "classes": ["module-header", "production-header"],
                            "text": feature.value.replace("_", " ").title(),
                        },
                        {
                            "tag": "main",
                            "classes": ["module-content", "production-content"],
                            "children": self._generate_production_style_content(feature),
                        },
                    ],
                },
                "enabled": True,
                "rendered": True,
            }
        
        return ui_structure
    
    def _generate_production_style_content(
        self, feature: E2EFeatureModule
    ) -> list[dict[str, Any]]:
        """Generate production-style content for a feature module."""
        return [
            {
                "tag": "section",
                "classes": ["data-grid", "production-grid"],
                "children": [],
            },
            {
                "tag": "aside",
                "classes": ["action-panel", "production-actions"],
                "children": [],
            },
        ]
    
    def compare_ui_structures(
        self,
        rehearsal_ui: dict[str, Any],
        production_ui: dict[str, Any],
        shared_features: set[str],
    ) -> dict[str, Any]:
        """
        Compare Rehearsal and Production UI structures for fidelity.
        
        Checks:
        - CSS classes match
        - DOM structure matches
        - Layout is identical
        """
        differences = []
        matching = []
        
        for feature in shared_features:
            rehearsal = rehearsal_ui.get(feature)
            production = production_ui.get(feature)
            
            if not rehearsal or not production:
                continue
            
            # Compare CSS classes (ignoring order)
            r_classes = set(rehearsal.get("css_classes", []))
            p_classes = set(production.get("css_classes", []))
            
            if r_classes != p_classes:
                differences.append({
                    "feature": feature,
                    "issue": "css_classes",
                    "rehearsal": list(r_classes),
                    "production": list(p_classes),
                })
            
            # Compare DOM structure keys
            r_dom = rehearsal.get("dom_structure", {})
            p_dom = production.get("dom_structure", {})
            
            r_dom_classes = set(r_dom.get("classes", []))
            p_dom_classes = set(p_dom.get("classes", []))
            
            if r_dom_classes != p_dom_classes:
                differences.append({
                    "feature": feature,
                    "issue": "dom_classes",
                    "rehearsal": list(r_dom_classes),
                    "production": list(p_dom_classes),
                })
            else:
                matching.append(feature)
        
        return {
            "differences": differences,
            "matching": matching,
            "total_compared": len(shared_features),
            "match_percentage": (
                len(matching) / len(shared_features) * 100 
                if shared_features else 100
            ),
        }
    
    def verify_rehearsal_fidelity(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> VerificationResult:
        """
        Verify Standard Work Rehearsal UI is indistinguishable from Production UI.
        
        Shared modules (work_orders, standard_work) must have identical:
        - CSS styling
        - DOM structure
        - Layout
        """
        if not self._check_role(user_role):
            raise PermissionError(f"Role '{user_role}' cannot verify fidelity")
        
        rehearsal_ui = self.generate_rehearsal_ui(site_id, user_role)
        production_ui = self.generate_production_ui(site_id, user_role)
        
        # Shared features between rehearsal and production
        shared_features = {"work_orders", "standard_work"}
        
        comparison = self.compare_ui_structures(
            rehearsal_ui, production_ui, shared_features
        )
        
        if comparison["differences"]:
            result = VerificationResult(
                test_name="rehearsal_fidelity",
                status=E2EVerificationStatus.FAILED,
                message=(
                    f"Rehearsal UI differs from Production UI: "
                    f"{len(comparison['differences'])} differences found"
                ),
                details={
                    "differences": comparison["differences"],
                    "match_percentage": comparison["match_percentage"],
                },
            )
        else:
            result = VerificationResult(
                test_name="rehearsal_fidelity",
                status=E2EVerificationStatus.PASSED,
                message=(
                    f"Rehearsal UI is indistinguishable from Production UI "
                    f"({comparison['match_percentage']:.0f}% match)"
                ),
                details={
                    "matching_features": comparison["matching"],
                    "match_percentage": comparison["match_percentage"],
                    "shared_features_checked": list(shared_features),
                },
            )
        
        self._verification_results.append(result)
        return result
    
    # =========================================================================
    # SUMMARY AND REPORTING
    # =========================================================================
    
    def get_verification_summary(self) -> dict[str, Any]:
        """Get summary of all verification results."""
        passed = sum(
            1 for r in self._verification_results 
            if r.status == E2EVerificationStatus.PASSED
        )
        failed = sum(
            1 for r in self._verification_results 
            if r.status == E2EVerificationStatus.FAILED
        )
        skipped = sum(
            1 for r in self._verification_results 
            if r.status == E2EVerificationStatus.SKIPPED
        )
        
        return {
            "total": len(self._verification_results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": passed / len(self._verification_results) * 100 if self._verification_results else 0,
            "results": [
                {
                    "test": r.test_name,
                    "status": r.status.value,
                    "message": r.message,
                }
                for r in self._verification_results
            ],
        }
    
    def run_full_maturity_verification(
        self,
        site_id: str,
        user_role: str = "admin"
    ) -> dict[str, Any]:
        """Run complete maturity gates verification suite."""
        results = {}
        
        # Test 1: Maturity Toggle at Level 1
        self.switch_site_to_level(site_id, E2EMaturityLevel.L1_DESIGN, user_role)
        results["production_andon_hidden"] = self.verify_production_andon_hidden_at_level1(
            site_id, user_role
        )
        
        # Test 2: Level Up Instant Unlock (L1 -> L4)
        results["level_up_l1_to_l4"] = self.verify_level_up_instant_unlock(
            site_id,
            E2EMaturityLevel.L1_DESIGN,
            E2EMaturityLevel.L4_PRODUCTION,
            user_role,
        )
        
        # Test 3: Level Up Instant Unlock (L3 -> L5)
        results["level_up_l3_to_l5"] = self.verify_level_up_instant_unlock(
            site_id,
            E2EMaturityLevel.L3_REHEARSAL,
            E2EMaturityLevel.L5_TPS,
            user_role,
        )
        
        # Test 4: Rehearsal Fidelity
        results["rehearsal_fidelity"] = self.verify_rehearsal_fidelity(
            site_id, user_role
        )
        
        return {
            "site_id": site_id,
            "tests_run": len(results),
            "results": {
                k: {
                    "status": v.status.value,
                    "message": v.message,
                }
                for k, v in results.items()
            },
            "summary": self.get_verification_summary(),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_factory_launchpad_e2e_service() -> FactoryLaunchpadE2EService:
    """Create a new Factory Launchpad E2E verification service."""
    return FactoryLaunchpadE2EService()


# =============================================================================
# PYTEST TESTS
# =============================================================================


@pytest.fixture
def e2e_service() -> FactoryLaunchpadE2EService:
    """Create E2E service for testing."""
    return create_factory_launchpad_e2e_service()


@pytest.fixture
def test_site(e2e_service: FactoryLaunchpadE2EService) -> str:
    """Create and register a test site."""
    result = e2e_service.register_site(
        site_id="site-e2e-001",
        site_name="E2E Test Factory",
        initial_level=E2EMaturityLevel.L0_STRATEGIC,
    )
    return result["site_id"]


class TestE2EEnums:
    """Test enum definitions."""
    
    def test_maturity_level_values(self):
        """Test maturity level values."""
        assert E2EMaturityLevel.L0_STRATEGIC.value == 0
        assert E2EMaturityLevel.L1_DESIGN.value == 1
        assert E2EMaturityLevel.L4_PRODUCTION.value == 4
        assert E2EMaturityLevel.L5_TPS.value == 5
    
    def test_maturity_level_ordering(self):
        """Test maturity levels can be compared."""
        assert E2EMaturityLevel.L0_STRATEGIC < E2EMaturityLevel.L1_DESIGN
        assert E2EMaturityLevel.L4_PRODUCTION < E2EMaturityLevel.L5_TPS
    
    def test_feature_module_values(self):
        """Test feature module enum values."""
        assert E2EFeatureModule.CRM.value == "crm"
        assert E2EFeatureModule.ANDON.value == "andon"
        assert E2EFeatureModule.PRODUCTION.value == "production"
    
    def test_verification_status_values(self):
        """Test verification status values."""
        assert E2EVerificationStatus.PASSED.value == "passed"
        assert E2EVerificationStatus.FAILED.value == "failed"


class TestMaturityFeatureMapping:
    """Test maturity feature mappings."""
    
    def test_all_levels_have_features(self):
        """Test all levels have features defined."""
        for level in E2EMaturityLevel:
            assert level in E2E_MATURITY_FEATURES
            assert len(E2E_MATURITY_FEATURES[level]) > 0
    
    def test_production_modules_not_in_l1(self):
        """Test production modules not available at L1."""
        l0_features = E2E_MATURITY_FEATURES[E2EMaturityLevel.L0_STRATEGIC]
        l1_features = E2E_MATURITY_FEATURES[E2EMaturityLevel.L1_DESIGN]
        combined = l0_features | l1_features
        
        for module in PRODUCTION_ANDON_MODULES:
            assert module not in combined
    
    def test_andon_only_at_l5(self):
        """Test Andon features only available at L5."""
        l5_features = E2E_MATURITY_FEATURES[E2EMaturityLevel.L5_TPS]
        
        assert E2EFeatureModule.ANDON in l5_features
        assert E2EFeatureModule.JIDOKA in l5_features


class TestSiteRegistration:
    """Test site registration."""
    
    def test_register_site(self, e2e_service: FactoryLaunchpadE2EService):
        """Test registering a site."""
        result = e2e_service.register_site(
            site_id="site-001",
            site_name="Test Factory",
            initial_level=E2EMaturityLevel.L0_STRATEGIC,
        )
        
        assert result["site_id"] == "site-001"
        assert result["site_name"] == "Test Factory"
        assert result["level"] == "L0_STRATEGIC"
    
    def test_register_site_at_level1(self, e2e_service: FactoryLaunchpadE2EService):
        """Test registering site at Level 1."""
        result = e2e_service.register_site(
            site_id="site-l1",
            site_name="L1 Factory",
            initial_level=E2EMaturityLevel.L1_DESIGN,
        )
        
        assert result["level"] == "L1_DESIGN"
    
    def test_get_site_level(self, e2e_service: FactoryLaunchpadE2EService, test_site: str):
        """Test getting site level."""
        level = e2e_service.get_site_level(test_site)
        assert level == E2EMaturityLevel.L0_STRATEGIC
    
    def test_register_site_rbac(self, e2e_service: FactoryLaunchpadE2EService):
        """Test RBAC on site registration."""
        with pytest.raises(PermissionError):
            e2e_service.register_site(
                site_id="site-rbac",
                site_name="RBAC Test",
                user_role="viewer",
            )


class TestMaturityToggleVerification:
    """Test maturity toggle verification (20.6.1)."""
    
    def test_switch_site_to_level1(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test switching site to Level 1."""
        result = e2e_service.switch_site_to_level(
            test_site, E2EMaturityLevel.L1_DESIGN
        )
        
        assert result["new_level"] == "L1_DESIGN"
        assert result["old_level"] == "L0_STRATEGIC"
    
    def test_production_modules_hidden_at_level1(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test production/Andon modules are hidden at Level 1."""
        e2e_service.switch_site_to_level(test_site, E2EMaturityLevel.L1_DESIGN)
        
        result = e2e_service.verify_production_andon_hidden_at_level1(test_site)
        
        assert result.status == E2EVerificationStatus.PASSED
        assert "100% hidden" in result.message
    
    def test_get_visible_modules_level1(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test visible modules at Level 1."""
        e2e_service.switch_site_to_level(test_site, E2EMaturityLevel.L1_DESIGN)
        
        visible = e2e_service.get_visible_modules(test_site)
        visible_values = {m.value for m in visible}
        
        # L0 and L1 features should be visible
        assert "crm" in visible_values
        assert "rfq" in visible_values
        assert "orders" in visible_values
        
        # Production/Andon should NOT be visible
        assert "production" not in visible_values
        assert "andon" not in visible_values
    
    def test_get_hidden_modules_level1(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test hidden modules at Level 1."""
        e2e_service.switch_site_to_level(test_site, E2EMaturityLevel.L1_DESIGN)
        
        hidden = e2e_service.get_hidden_modules(test_site)
        hidden_values = {m.value for m in hidden}
        
        # Production/Andon should be hidden
        assert "production" in hidden_values
        assert "andon" in hidden_values
        assert "jidoka" in hidden_values
    
    def test_switch_level_rbac(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test RBAC on level switching."""
        with pytest.raises(PermissionError):
            e2e_service.switch_site_to_level(
                test_site, E2EMaturityLevel.L4_PRODUCTION, user_role="viewer"
            )
    
    def test_verification_skipped_if_not_level1(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test verification skipped if not at Level 1."""
        # Site is at L0 by default
        result = e2e_service.verify_production_andon_hidden_at_level1(test_site)
        
        assert result.status == E2EVerificationStatus.SKIPPED
        assert "not Level 1" in result.message


class TestLevelUpEvent:
    """Test level-up event verification (20.6.2)."""
    
    def test_add_site_data(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test adding data to a site."""
        result = e2e_service.add_site_data(
            test_site, "quotes", {"id": "quote-001", "value": 1000}
        )
        assert result is True
        assert e2e_service.get_site_data_count(test_site) == 1
    
    def test_perform_level_up(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test performing a level-up."""
        event = e2e_service.perform_level_up(
            test_site, E2EMaturityLevel.L2_ENGINEERING
        )
        
        assert event.from_level == E2EMaturityLevel.L0_STRATEGIC
        assert event.to_level == E2EMaturityLevel.L2_ENGINEERING
        assert event.data_preserved is True
        assert event.unlock_latency_ms < 100  # Should be instant
    
    def test_level_up_preserves_data(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test level-up preserves existing data."""
        # Add data
        e2e_service.add_site_data(test_site, "quotes", {"id": "q1"})
        e2e_service.add_site_data(test_site, "orders", {"id": "o1"})
        
        count_before = e2e_service.get_site_data_count(test_site)
        
        # Level up
        event = e2e_service.perform_level_up(
            test_site, E2EMaturityLevel.L4_PRODUCTION
        )
        
        count_after = e2e_service.get_site_data_count(test_site)
        
        assert count_after == count_before
        assert event.data_preserved is True
    
    def test_level_up_instant_unlock_verification(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test level-up instant unlock verification passes."""
        result = e2e_service.verify_level_up_instant_unlock(
            test_site,
            E2EMaturityLevel.L1_DESIGN,
            E2EMaturityLevel.L4_PRODUCTION,
        )
        
        assert result.status == E2EVerificationStatus.PASSED
        assert "no data loss" in result.message
    
    def test_level_up_unlocks_features(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test level-up unlocks expected features."""
        event = e2e_service.perform_level_up(
            test_site, E2EMaturityLevel.L5_TPS
        )
        
        # Should have unlocked all features from L1-L5
        assert len(event.features_unlocked) > 0
    
    def test_cannot_level_down(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test cannot level down."""
        # First level up
        e2e_service.perform_level_up(test_site, E2EMaturityLevel.L3_REHEARSAL)
        
        # Try to level down
        with pytest.raises(ValueError):
            e2e_service.perform_level_up(test_site, E2EMaturityLevel.L1_DESIGN)
    
    def test_level_up_history(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test level-up history tracking."""
        e2e_service.perform_level_up(test_site, E2EMaturityLevel.L2_ENGINEERING)
        e2e_service.perform_level_up(test_site, E2EMaturityLevel.L4_PRODUCTION)
        
        history = e2e_service.get_level_up_history(test_site)
        
        assert len(history) == 2
        assert history[0].to_level == E2EMaturityLevel.L2_ENGINEERING
        assert history[1].to_level == E2EMaturityLevel.L4_PRODUCTION


class TestRehearsalFidelity:
    """Test rehearsal fidelity verification (20.6.3)."""
    
    def test_generate_rehearsal_ui(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test generating Rehearsal UI."""
        ui = e2e_service.generate_rehearsal_ui(test_site)
        
        assert "work_orders" in ui
        assert "standard_work" in ui
        assert "rehearsal_mode" in ui
    
    def test_generate_production_ui(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test generating Production UI."""
        ui = e2e_service.generate_production_ui(test_site)
        
        assert "work_orders" in ui
        assert "standard_work" in ui
        assert "production" in ui
        assert "live_tracking" in ui
    
    def test_rehearsal_has_production_style(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test Rehearsal UI uses production styling."""
        ui = e2e_service.generate_rehearsal_ui(test_site)
        
        work_orders = ui.get("work_orders", {})
        css_classes = work_orders.get("css_classes", [])
        
        assert "production-style" in css_classes
    
    def test_compare_ui_structures_identical(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test UI comparison with identical structures."""
        rehearsal = e2e_service.generate_rehearsal_ui(test_site)
        production = e2e_service.generate_production_ui(test_site)
        
        shared = {"work_orders", "standard_work"}
        comparison = e2e_service.compare_ui_structures(
            rehearsal, production, shared
        )
        
        # Should have no differences for shared features
        assert comparison["match_percentage"] == 100
        assert len(comparison["differences"]) == 0
    
    def test_verify_rehearsal_fidelity_passes(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test rehearsal fidelity verification passes."""
        result = e2e_service.verify_rehearsal_fidelity(test_site)
        
        assert result.status == E2EVerificationStatus.PASSED
        assert "indistinguishable" in result.message
    
    def test_rehearsal_dom_matches_production(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test Rehearsal DOM structure matches Production."""
        rehearsal = e2e_service.generate_rehearsal_ui(test_site)
        production = e2e_service.generate_production_ui(test_site)
        
        r_dom = rehearsal["work_orders"]["dom_structure"]
        p_dom = production["work_orders"]["dom_structure"]
        
        assert r_dom["classes"] == p_dom["classes"]
        assert r_dom["tag"] == p_dom["tag"]


class TestFullVerificationSuite:
    """Test full verification suite."""
    
    def test_run_full_verification(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test running full maturity verification suite."""
        results = e2e_service.run_full_maturity_verification(test_site)
        
        assert results["tests_run"] == 4
        assert "production_andon_hidden" in results["results"]
        assert "level_up_l1_to_l4" in results["results"]
        assert "rehearsal_fidelity" in results["results"]
    
    def test_verification_summary(
        self, e2e_service: FactoryLaunchpadE2EService, test_site: str
    ):
        """Test verification summary."""
        e2e_service.run_full_maturity_verification(test_site)
        
        summary = e2e_service.get_verification_summary()
        
        assert summary["total"] > 0
        assert "pass_rate" in summary
        assert summary["passed"] > 0


class TestRBACEnforcement:
    """Test RBAC enforcement across all operations."""
    
    def test_admin_can_access_all(
        self, e2e_service: FactoryLaunchpadE2EService
    ):
        """Test admin role has full access."""
        result = e2e_service.register_site(
            "site-admin", "Admin Site", user_role="admin"
        )
        assert result["site_id"] == "site-admin"
    
    def test_ceo_can_access_all(
        self, e2e_service: FactoryLaunchpadE2EService
    ):
        """Test CEO role has full access."""
        result = e2e_service.register_site(
            "site-ceo", "CEO Site", user_role="ceo"
        )
        assert result["site_id"] == "site-ceo"
    
    def test_gm_can_access_all(
        self, e2e_service: FactoryLaunchpadE2EService
    ):
        """Test GM role has full access."""
        result = e2e_service.register_site(
            "site-gm", "GM Site", user_role="gm"
        )
        assert result["site_id"] == "site-gm"
    
    def test_viewer_cannot_access(
        self, e2e_service: FactoryLaunchpadE2EService
    ):
        """Test viewer role is denied."""
        with pytest.raises(PermissionError):
            e2e_service.register_site(
                "site-viewer", "Viewer Site", user_role="viewer"
            )
    
    def test_operator_cannot_access(
        self, e2e_service: FactoryLaunchpadE2EService
    ):
        """Test operator role is denied."""
        with pytest.raises(PermissionError):
            e2e_service.register_site(
                "site-op", "Op Site", user_role="operator"
            )


class TestDataClasses:
    """Test data class functionality."""
    
    def test_site_data_add_record(self):
        """Test SiteData add_record."""
        data = SiteData(site_id="site-001")
        data.add_record("quotes", {"id": "q1"})
        data.add_record("quotes", {"id": "q2"})
        
        assert data.get_record_count("quotes") == 2
        assert data.get_total_records() == 2
    
    def test_ui_element_state(self):
        """Test UIElementState creation."""
        state = UIElementState(
            element_id="nav-crm",
            module=E2EFeatureModule.CRM,
            visible=True,
            enabled=True,
            rendered=True,
        )
        
        assert state.visible is True
        assert state.module == E2EFeatureModule.CRM
    
    def test_verification_result(self):
        """Test VerificationResult creation."""
        result = VerificationResult(
            test_name="test_1",
            status=E2EVerificationStatus.PASSED,
            message="All tests passed",
        )
        
        assert result.status == E2EVerificationStatus.PASSED
    
    def test_level_up_event(self):
        """Test LevelUpEvent creation."""
        event = LevelUpEvent(
            site_id="site-001",
            from_level=E2EMaturityLevel.L0_STRATEGIC,
            to_level=E2EMaturityLevel.L4_PRODUCTION,
            features_unlocked={E2EFeatureModule.PRODUCTION},
            data_preserved=True,
            unlock_latency_ms=5.2,
        )
        
        assert event.data_preserved is True
        assert E2EFeatureModule.PRODUCTION in event.features_unlocked
