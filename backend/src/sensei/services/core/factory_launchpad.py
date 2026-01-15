"""
Sensei Factory Launchpad: Greenfield Growth & Scalable Deployment.

Implements the Deployment Maturity Model (L0-L5) to orchestrate feature sets
based on factory lifecycle, ensuring the software scales its utility at the
speed of physical infrastructure growth.

Features:
- Deployment Maturity Model (L0-L5) with feature orchestration
- Maturity-Locked State Machines (restrict actions by maturity level)
- Dynamic UI Masking & Perspective Toggling
- Automated "Level Up" Checklists
- Pre-Operational Readiness & Rehearsal
- Infrastructure Rollout Dashboard
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Any, Callable

from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.strategic_v2 import SiteMaturityRecord, LevelUpChecklistRecord


# =============================================================================
# ENUMS
# =============================================================================


class MaturityLevel(IntEnum):
    """
    Factory Deployment Maturity Levels.
    
    L0: Strategic Foundation (Sales Mode) - CRM, RFQ, Quotes, Basic A3
    L1: Design & Planning (Project Mode) - Factory Architect, CapEx Forecasting
    L2: NPI & Infrastructure (Engineering Mode) - Product Catalog, CTQs, BOMs
    L3: Commissioning & Training (Rehearsal Mode) - Virtual Gemba, Training
    L4: Pilot Production (Operational Mode) - Work Orders, Stations, Quality
    L5: Full Lean Velocity (TPS Mode) - Andon, Obeya, Jidoka, TPM
    """
    
    L0_STRATEGIC = 0
    L1_PLANNING = 1
    L2_ENGINEERING = 2
    L3_REHEARSAL = 3
    L4_OPERATIONAL = 4
    L5_TPS = 5


class MaturityTransitionStatus(Enum):
    """Status of a maturity level transition."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class FeatureModule(Enum):
    """Feature modules that can be enabled/disabled by maturity level."""
    
    # L0: Strategic Foundation
    CRM = "crm"
    RFQ = "rfq"
    QUOTES = "quotes"
    BASIC_A3 = "basic_a3"
    KNOWLEDGE_PACK_PUBLIC = "knowledge_pack_public"
    
    # L1: Design & Planning
    FACTORY_ARCHITECT = "factory_architect"
    UTILITY_MAPPING = "utility_mapping"
    CAPEX_FORECASTING = "capex_forecasting"
    RECRUITING_ROADMAP = "recruiting_roadmap"
    
    # L2: NPI & Infrastructure
    PRODUCT_CATALOG = "product_catalog"
    CTQ_MANAGEMENT = "ctq_management"
    BOM_MANAGEMENT = "bom_management"
    SUPPLIER_ONBOARDING = "supplier_onboarding"
    EDGE_IOT_PROVISIONING = "edge_iot_provisioning"
    
    # L3: Commissioning & Training
    VIRTUAL_GEMBA = "virtual_gemba"
    SIMULATION_TRAINING = "simulation_training"
    STANDARD_WORK_REHEARSALS = "standard_work_rehearsals"
    TRAINING_MATRIX = "training_matrix"
    
    # L4: Pilot Production
    WORK_ORDERS = "work_orders"
    STATIONS = "stations"
    BASIC_QUALITY = "basic_quality"
    TODAY_SCREEN = "today_screen"
    LEADER_STANDARD_WORK = "leader_standard_work"
    
    # L5: Full Lean Velocity
    ANDON = "andon"
    OBEYA_SQDCP = "obeya_sqdcp"
    ADVANCED_RAG = "advanced_rag"
    JIDOKA = "jidoka"
    TPM = "tpm"
    PREDICTIVE_ANALYTICS = "predictive_analytics"


class ChecklistItemStatus(Enum):
    """Status of a level-up checklist item."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ValidationSeverity(Enum):
    """Severity of validation issues."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


class SiteStatus(Enum):
    """Status of a factory site."""
    
    PLANNED = "planned"
    UNDER_CONSTRUCTION = "under_construction"
    COMMISSIONING = "commissioning"
    PILOT = "pilot"
    OPERATIONAL = "operational"
    FULL_TPS = "full_tps"


class HardwareAssetType(Enum):
    """Types of hardware assets for rollout tracking."""
    
    TABLET = "tablet"
    BARCODE_SCANNER = "barcode_scanner"
    EDGE_GATEWAY = "edge_gateway"
    IOT_SENSOR = "iot_sensor"
    CAMERA = "camera"
    PLC = "plc"
    LABEL_PRINTER = "label_printer"


class HardwareAssetStatus(Enum):
    """Status of hardware asset rollout."""
    
    ORDERED = "ordered"
    DELIVERED = "delivered"
    CONFIGURED = "configured"
    DEPLOYED = "deployed"
    ACTIVE = "active"
    FAILED = "failed"


# =============================================================================
# CONSTANTS
# =============================================================================


# Feature modules available at each maturity level
MATURITY_FEATURES: dict[MaturityLevel, set[FeatureModule]] = {
    MaturityLevel.L0_STRATEGIC: {
        FeatureModule.CRM,
        FeatureModule.RFQ,
        FeatureModule.QUOTES,
        FeatureModule.BASIC_A3,
        FeatureModule.KNOWLEDGE_PACK_PUBLIC,
    },
    MaturityLevel.L1_PLANNING: {
        FeatureModule.FACTORY_ARCHITECT,
        FeatureModule.UTILITY_MAPPING,
        FeatureModule.CAPEX_FORECASTING,
        FeatureModule.RECRUITING_ROADMAP,
    },
    MaturityLevel.L2_ENGINEERING: {
        FeatureModule.PRODUCT_CATALOG,
        FeatureModule.CTQ_MANAGEMENT,
        FeatureModule.BOM_MANAGEMENT,
        FeatureModule.SUPPLIER_ONBOARDING,
        FeatureModule.EDGE_IOT_PROVISIONING,
    },
    MaturityLevel.L3_REHEARSAL: {
        FeatureModule.VIRTUAL_GEMBA,
        FeatureModule.SIMULATION_TRAINING,
        FeatureModule.STANDARD_WORK_REHEARSALS,
        FeatureModule.TRAINING_MATRIX,
    },
    MaturityLevel.L4_OPERATIONAL: {
        FeatureModule.WORK_ORDERS,
        FeatureModule.STATIONS,
        FeatureModule.BASIC_QUALITY,
        FeatureModule.TODAY_SCREEN,
        FeatureModule.LEADER_STANDARD_WORK,
    },
    MaturityLevel.L5_TPS: {
        FeatureModule.ANDON,
        FeatureModule.OBEYA_SQDCP,
        FeatureModule.ADVANCED_RAG,
        FeatureModule.JIDOKA,
        FeatureModule.TPM,
        FeatureModule.PREDICTIVE_ANALYTICS,
    },
}


# Level descriptions
MATURITY_DESCRIPTIONS: dict[MaturityLevel, dict[str, str]] = {
    MaturityLevel.L0_STRATEGIC: {
        "name": "Strategic Foundation",
        "mode": "Sales Mode",
        "focus": "CRM, RFQ, Quotes, Basic A3, Knowledge Pack (Public Resources)",
        "entry_criteria": "Initial system setup",
        "exit_criteria": "Site location secured",
    },
    MaturityLevel.L1_PLANNING: {
        "name": "Design & Planning",
        "mode": "Project Mode",
        "focus": "Factory Architect, Utility Mapping, CapEx Forecasting, Recruiting Roadmap",
        "entry_criteria": "Facility footprint available",
        "exit_criteria": "Layout approved, critical equipment ordered",
    },
    MaturityLevel.L2_ENGINEERING: {
        "name": "NPI & Infrastructure",
        "mode": "Engineering Mode",
        "focus": "Product Catalog, CTQs, BOMs, Supplier Onboarding, Edge/IoT Provisioning",
        "entry_criteria": "Machine delivery schedules confirmed",
        "exit_criteria": "Digital Twin-lite validated, edge gateways discovered",
    },
    MaturityLevel.L3_REHEARSAL: {
        "name": "Commissioning & Training",
        "mode": "Rehearsal Mode",
        "focus": "Virtual Gemba, Simulation Training, Standard Work Rehearsals, Training Matrix",
        "entry_criteria": "Physical site power/data active",
        "exit_criteria": "80% of operators certified on Rehearsal Mode",
    },
    MaturityLevel.L4_OPERATIONAL: {
        "name": "Pilot Production",
        "mode": "Operational Mode",
        "focus": "Work Orders, Stations, Basic Quality (NCR), Today Screen, Leader Standard Work",
        "entry_criteria": "First machine SAT (Site Acceptance Test) passed",
        "exit_criteria": "Stable first-pass-yield (FPY) > 90% for pilot batch",
    },
    MaturityLevel.L5_TPS: {
        "name": "Full Lean Velocity",
        "mode": "TPS Mode",
        "focus": "Andon, Obeya (SQDCP), Advanced RAG, Jidoka, TPM, Predictive Analytics",
        "entry_criteria": "Production ramp-up to 50% capacity",
        "exit_criteria": "System running with zero-admin autopilot",
    },
}


# Default checklist items for each level transition
DEFAULT_LEVEL_UP_CHECKLISTS: dict[tuple[MaturityLevel, MaturityLevel], list[dict]] = {
    (MaturityLevel.L0_STRATEGIC, MaturityLevel.L1_PLANNING): [
        {"id": "site_location", "title": "Site Location Secured", "required": True},
        {"id": "initial_layout", "title": "Initial Layout Concept Defined", "required": False},
        {"id": "budget_approved", "title": "Project Budget Approved", "required": True},
    ],
    (MaturityLevel.L1_PLANNING, MaturityLevel.L2_ENGINEERING): [
        {"id": "layout_approved", "title": "Factory Layout Approved", "required": True},
        {"id": "equipment_ordered", "title": "Critical Equipment Ordered", "required": True},
        {"id": "utility_requirements", "title": "Utility Requirements Calculated", "required": True},
        {"id": "bom_structure", "title": "Initial BOM Structure Created", "required": False},
    ],
    (MaturityLevel.L2_ENGINEERING, MaturityLevel.L3_REHEARSAL): [
        {"id": "machine_delivery", "title": "Machine Delivery Schedules Confirmed", "required": True},
        {"id": "edge_gateways", "title": "Edge Gateways Provisioned", "required": True},
        {"id": "digital_twin", "title": "Digital Twin-lite Validated", "required": True},
        {"id": "training_content", "title": "Training Content Prepared", "required": True},
    ],
    (MaturityLevel.L3_REHEARSAL, MaturityLevel.L4_OPERATIONAL): [
        {"id": "power_data_active", "title": "Physical Site Power/Data Active", "required": True},
        {"id": "operator_certification", "title": "80% Operators Certified", "required": True},
        {"id": "first_machine_sat", "title": "First Machine SAT Passed", "required": True},
        {"id": "standard_work", "title": "Standard Work Documents Finalized", "required": True},
    ],
    (MaturityLevel.L4_OPERATIONAL, MaturityLevel.L5_TPS): [
        {"id": "fpy_target", "title": "FPY > 90% Achieved for Pilot Batch", "required": True},
        {"id": "capacity_50", "title": "Production at 50% Capacity", "required": True},
        {"id": "obeya_operational", "title": "Obeya Board Fully Operational", "required": True},
        {"id": "andon_configured", "title": "Andon System Configured", "required": True},
        {"id": "predictive_models", "title": "Predictive Models Trained", "required": False},
    ],
}


# Dynamic field validation rules by maturity level
FIELD_VALIDATION_RULES: dict[str, dict[str, int]] = {
    # Field name -> minimum maturity level required
    "machine_id": MaturityLevel.L3_REHEARSAL,
    "station_id": MaturityLevel.L4_OPERATIONAL,
    "andon_trigger": MaturityLevel.L5_TPS,
    "oee_target": MaturityLevel.L4_OPERATIONAL,
    "predictive_score": MaturityLevel.L5_TPS,
}


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SiteConfig:
    """Configuration for a factory site."""
    
    site_id: str
    site_name: str
    current_level: MaturityLevel = MaturityLevel.L0_STRATEGIC
    target_level: MaturityLevel | None = None
    status: SiteStatus = SiteStatus.PLANNED
    timezone: str = "UTC"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_enabled_features(self) -> set[FeatureModule]:
        """Get all enabled features for current maturity level."""
        enabled = set()
        for level in MaturityLevel:
            if level <= self.current_level:
                enabled.update(MATURITY_FEATURES.get(level, set()))
        return enabled
    
    def is_feature_enabled(self, feature: FeatureModule) -> bool:
        """Check if a specific feature is enabled."""
        return feature in self.get_enabled_features()
    
    def get_level_info(self) -> dict[str, str]:
        """Get information about current level."""
        return MATURITY_DESCRIPTIONS.get(self.current_level, {})


@dataclass
class ChecklistItem:
    """A checklist item for level-up transition."""
    
    item_id: str
    title: str
    description: str = ""
    required: bool = True
    status: ChecklistItemStatus = ChecklistItemStatus.NOT_STARTED
    completed_at: datetime | None = None
    completed_by: str | None = None
    evidence_notes: str = ""
    evidence_attachments: list[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if item is complete."""
        return self.status == ChecklistItemStatus.COMPLETED
    
    @property
    def is_blocking(self) -> bool:
        """Check if this item blocks level-up."""
        return self.required and not self.is_complete


@dataclass
class LevelUpChecklist:
    """Checklist for transitioning between maturity levels."""
    
    checklist_id: str
    site_id: str
    from_level: MaturityLevel
    to_level: MaturityLevel
    items: list[ChecklistItem] = field(default_factory=list)
    status: MaturityTransitionStatus = MaturityTransitionStatus.NOT_STARTED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.items:
            return 100.0
        completed = sum(1 for item in self.items if item.is_complete)
        return (completed / len(self.items)) * 100
    
    @property
    def required_items_complete(self) -> bool:
        """Check if all required items are complete."""
        return all(item.is_complete for item in self.items if item.required)
    
    @property
    def blocking_items(self) -> list[ChecklistItem]:
        """Get list of items blocking level-up."""
        return [item for item in self.items if item.is_blocking]
    
    def can_complete(self) -> tuple[bool, list[str]]:
        """Check if checklist can be completed."""
        blocking = self.blocking_items
        if blocking:
            reasons = [f"Incomplete required item: {item.title}" for item in blocking]
            return False, reasons
        return True, []


@dataclass
class ValidationIssue:
    """A validation issue for maturity-locked actions."""
    
    issue_id: str
    severity: ValidationSeverity
    field: str
    message: str
    current_level: MaturityLevel
    required_level: MaturityLevel
    suggestion: str = ""


@dataclass
class ActionValidationResult:
    """Result of validating an action against maturity level."""
    
    allowed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    required_level: MaturityLevel | None = None
    current_level: MaturityLevel | None = None
    
    def add_issue(self, issue: ValidationIssue):
        """Add a validation issue."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.BLOCKING:
            self.allowed = False


@dataclass
class HardwareAsset:
    """A hardware asset for rollout tracking."""
    
    asset_id: str
    asset_type: HardwareAssetType
    name: str
    mac_address: str | None = None
    serial_number: str | None = None
    station_id: str | None = None
    site_id: str | None = None
    status: HardwareAssetStatus = HardwareAssetStatus.ORDERED
    ip_address: str | None = None
    last_seen: datetime | None = None
    firmware_version: str | None = None
    notes: str = ""
    
    @property
    def is_active(self) -> bool:
        """Check if asset is active."""
        return self.status == HardwareAssetStatus.ACTIVE


@dataclass
class RolloutProgress:
    """Progress of hardware rollout for a site."""
    
    site_id: str
    total_assets: int
    deployed_assets: int
    active_assets: int
    failed_assets: int
    by_type: dict[HardwareAssetType, dict[str, int]] = field(default_factory=dict)
    
    @property
    def deployment_percentage(self) -> float:
        """Calculate deployment percentage."""
        if self.total_assets == 0:
            return 100.0
        return (self.deployed_assets / self.total_assets) * 100
    
    @property
    def health_percentage(self) -> float:
        """Calculate health percentage (active vs deployed)."""
        if self.deployed_assets == 0:
            return 100.0
        return (self.active_assets / self.deployed_assets) * 100


@dataclass
class FeatureAccess:
    """Feature access configuration for UI masking."""
    
    feature: FeatureModule
    enabled: bool
    visible: bool
    reason: str = ""
    available_at_level: MaturityLevel | None = None


@dataclass
class UIVisibilityConfig:
    """UI visibility configuration based on maturity level."""
    
    site_id: str
    current_level: MaturityLevel
    features: list[FeatureAccess] = field(default_factory=list)
    show_future_preview: bool = False
    preview_level: MaturityLevel | None = None


# =============================================================================
# MATURITY MANAGER
# =============================================================================


class AsyncMaturityManager:
    """
    Manages deployment maturity levels for factory sites with DB persistence.
    """
    
    def __init__(self):
        self._level_change_callbacks: list[Callable[[str, MaturityLevel, MaturityLevel], None]] = []
    
    async def register_site(
        self,
        db: AsyncSession,
        site_id: str,
        site_name: str,
        initial_level: MaturityLevel = MaturityLevel.L0_STRATEGIC,
        timezone: str = "UTC",
        metadata: dict[str, Any] | None = None,
    ) -> SiteMaturityRecord:
        """Register a new site with initial maturity level in the database."""
        record = SiteMaturityRecord(
            site_id=site_id,
            site_name=site_name,
            current_level=initial_level.value,
            target_level=initial_level.value + 1,
            deployment_metadata={
                "timezone": timezone,
                **(metadata or {})
            }
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
    
    async def get_site(self, db: AsyncSession, site_id: str) -> SiteMaturityRecord | None:
        """Get site configuration from database."""
        stmt = select(SiteMaturityRecord).where(SiteMaturityRecord.site_id == site_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_current_level(self, db: AsyncSession, site_id: str) -> MaturityLevel | None:
        """Get current maturity level for a site."""
        site = await self.get_site(db, site_id)
        return MaturityLevel(site.current_level) if site else None
    
    async def create_level_up_checklist(
        self,
        db: AsyncSession,
        site_id: str,
        target_level: MaturityLevel | None = None,
    ) -> LevelUpChecklistRecord | None:
        """Create a checklist for level-up transition in the database."""
        site = await self.get_site(db, site_id)
        if not site:
            return None
        
        from_level = site.current_level
        
        # Check if already at max level
        if from_level >= MaturityLevel.L5_TPS.value:
            return None
        
        # Calculate target level
        to_level = target_level.value if target_level is not None else from_level + 1
        
        if to_level <= from_level or to_level > MaturityLevel.L5_TPS.value:
            return None
        
        # Get default items
        default_items = DEFAULT_LEVEL_UP_CHECKLISTS.get((MaturityLevel(from_level), MaturityLevel(to_level)), [])
        
        items = [
            {
                "item_id": item["id"],
                "title": item["title"],
                "required": item.get("required", True),
                "completed": False
            }
            for item in default_items
        ]
        
        checklist = LevelUpChecklistRecord(
            site_id=site_id,
            from_level=from_level,
            to_level=to_level,
            items=items,
            is_completed=False
        )
        
        db.add(checklist)
        
        # Update site target level
        site.target_level = to_level
        site.is_in_transition = True
        
        await db.commit()
        await db.refresh(checklist)
        return checklist


class MaturityManager:
    """
    Manages deployment maturity levels for factory sites in memory.
    """
    
    def __init__(self):
        self._sites: dict[str, SiteConfig] = {}
        self._checklists: dict[str, LevelUpChecklist] = {}
        self._level_change_callbacks: list[Callable[[str, MaturityLevel, MaturityLevel], None]] = []
    
    def register_site(
        self,
        site_id: str,
        site_name: str,
        initial_level: MaturityLevel = MaturityLevel.L0_STRATEGIC,
        timezone: str = "UTC",
        metadata: dict[str, Any] | None = None,
    ) -> SiteConfig:
        """Register a new site with initial maturity level in memory."""
        target_level = None
        if initial_level < MaturityLevel.L5_TPS:
            target_level = MaturityLevel(initial_level.value + 1)

        site = SiteConfig(
            site_id=site_id,
            site_name=site_name,
            current_level=initial_level,
            target_level=target_level,
            timezone=timezone,
            metadata=metadata or {},
        )
        self._sites[site_id] = site
        return site
    
    def get_site(self, site_id: str) -> SiteConfig | None:
        """Get site configuration from memory."""
        return self._sites.get(site_id)
    
    def get_all_sites(self) -> list[SiteConfig]:
        """Get all registered sites."""
        return list(self._sites.values())
    
    def get_current_level(self, site_id: str) -> MaturityLevel | None:
        """Get current maturity level for a site."""
        site = self.get_site(site_id)
        return site.current_level if site else None
    
    def get_enabled_features(self, site_id: str) -> set[FeatureModule]:
        """Get enabled features for a site."""
        site = self.get_site(site_id)
        return site.get_enabled_features() if site else set()
    
    def is_feature_enabled(self, site_id: str, feature: FeatureModule) -> bool:
        """Check if a specific feature is enabled for a site."""
        site = self.get_site(site_id)
        return site.is_feature_enabled(feature) if site else False
    
    def create_level_up_checklist(
        self,
        site_id: str,
        target_level: MaturityLevel | None = None,
    ) -> LevelUpChecklist | None:
        """Create a checklist for level-up transition in memory."""
        site = self.get_site(site_id)
        if not site:
            return None
        
        from_level = site.current_level
        
        # Check if already at max level
        if from_level >= MaturityLevel.L5_TPS:
            return None
        
        # Calculate target level
        if target_level is None:
            to_level = MaturityLevel(from_level.value + 1)
        else:
            to_level = target_level
        
        if to_level <= from_level or to_level > MaturityLevel.L5_TPS:
            return None
        
        # Get default items
        default_items = DEFAULT_LEVEL_UP_CHECKLISTS.get((from_level, to_level), [])
        
        items = [
            ChecklistItem(
                item_id=item["id"],
                title=item["title"],
                description=item.get("description", ""),
                required=item.get("required", True),
            )
            for item in default_items
        ]
        
        checklist = LevelUpChecklist(
            checklist_id=str(uuid.uuid4()),
            site_id=site_id,
            from_level=from_level,
            to_level=to_level,
            items=items,
        )
        
        self._checklists[checklist.checklist_id] = checklist
        
        # Update site target level
        site.target_level = to_level
        site.updated_at = datetime.now()
        
        return checklist
    
    def get_checklist(self, checklist_id: str) -> LevelUpChecklist | None:
        """Get a level-up checklist."""
        return self._checklists.get(checklist_id)
    
    def get_site_checklists(self, site_id: str) -> list[LevelUpChecklist]:
        """Get all checklists for a site."""
        return [c for c in self._checklists.values() if c.site_id == site_id]
    
    def complete_checklist_item(
        self,
        checklist_id: str,
        item_id: str,
        user_id: str,
        evidence_notes: str = "",
        evidence_attachments: list[str] | None = None,
    ) -> bool:
        """Mark a checklist item as complete."""
        checklist = self._checklists.get(checklist_id)
        if not checklist:
            return False
        
        for item in checklist.items:
            if item.item_id == item_id:
                item.status = ChecklistItemStatus.COMPLETED
                item.completed_at = datetime.now()
                item.completed_by = user_id
                item.evidence_notes = evidence_notes
                item.evidence_attachments = evidence_attachments or []
                
                # Update checklist status
                if checklist.status == MaturityTransitionStatus.NOT_STARTED:
                    checklist.status = MaturityTransitionStatus.IN_PROGRESS
                    checklist.started_at = datetime.now()
                
                return True
        
        return False
    
    def attempt_level_up(self, site_id: str, checklist_id: str) -> tuple[bool, list[str]]:
        """Attempt to level up a site using completed checklist."""
        site = self._sites.get(site_id)
        checklist = self._checklists.get(checklist_id)
        
        if not site or not checklist:
            return False, ["Site or checklist not found"]
        
        if checklist.site_id != site_id:
            return False, ["Checklist does not belong to this site"]
        
        can_complete, reasons = checklist.can_complete()
        if not can_complete:
            checklist.status = MaturityTransitionStatus.BLOCKED
            return False, reasons
        
        old_level = site.current_level
        new_level = checklist.to_level
        
        # Perform level up
        site.current_level = new_level
        site.target_level = None
        site.updated_at = datetime.now()
        
        checklist.status = MaturityTransitionStatus.COMPLETED
        checklist.completed_at = datetime.now()
        
        # Update site status based on level
        if new_level >= MaturityLevel.L5_TPS:
            site.status = SiteStatus.FULL_TPS
        elif new_level >= MaturityLevel.L4_OPERATIONAL:
            site.status = SiteStatus.OPERATIONAL
        elif new_level >= MaturityLevel.L3_REHEARSAL:
            site.status = SiteStatus.COMMISSIONING
        elif new_level >= MaturityLevel.L1_PLANNING:
            site.status = SiteStatus.UNDER_CONSTRUCTION
        
        # Notify callbacks
        for callback in self._level_change_callbacks:
            callback(site_id, old_level, new_level)
        
        return True, []
    
    def register_level_change_callback(
        self,
        callback: Callable[[str, MaturityLevel, MaturityLevel], None],
    ):
        """Register callback for level changes."""
        self._level_change_callbacks.append(callback)
    
    def validate_action(
        self,
        site_id: str,
        action: str,
        required_level: MaturityLevel,
        fields: dict[str, Any] | None = None,
    ) -> ActionValidationResult:
        """Validate an action against site maturity level."""
        site = self._sites.get(site_id)
        if not site:
            return ActionValidationResult(
                allowed=False,
                issues=[
                    ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        severity=ValidationSeverity.BLOCKING,
                        field="site_id",
                        message="Site not found",
                        current_level=MaturityLevel.L0_STRATEGIC,
                        required_level=required_level,
                    )
                ],
            )
        
        result = ActionValidationResult(
            allowed=True,
            current_level=site.current_level,
            required_level=required_level,
        )
        
        # Check if action is allowed at current level
        if site.current_level < required_level:
            result.add_issue(
                ValidationIssue(
                    issue_id=str(uuid.uuid4()),
                    severity=ValidationSeverity.BLOCKING,
                    field=action,
                    message=f"Action '{action}' requires maturity level {required_level.name} or higher",
                    current_level=site.current_level,
                    required_level=required_level,
                    suggestion=f"Complete level-up to {required_level.name} before performing this action",
                )
            )
        
        # Validate individual fields
        if fields:
            for field_name, value in fields.items():
                if value is not None and field_name in FIELD_VALIDATION_RULES:
                    min_level = FIELD_VALIDATION_RULES[field_name]
                    if site.current_level < min_level:
                        result.add_issue(
                            ValidationIssue(
                                issue_id=str(uuid.uuid4()),
                                severity=ValidationSeverity.BLOCKING,
                                field=field_name,
                                message=f"Field '{field_name}' requires maturity level {min_level} or higher",
                                current_level=site.current_level,
                                required_level=MaturityLevel(min_level),
                                suggestion=f"Remove {field_name} or level-up to use this field",
                            )
                        )
        
        return result


# =============================================================================
# UI VISIBILITY MANAGER
# =============================================================================


class UIVisibilityManager:
    """
    Manages UI visibility based on maturity level.
    
    Provides:
    - Dynamic UI masking for non-relevant modules
    - Future state preview toggle for admins
    - Feature access configuration
    """
    
    def __init__(self, maturity_manager: MaturityManager):
        self._maturity_manager = maturity_manager
        self._preview_enabled: dict[str, MaturityLevel] = {}
    
    def get_visibility_config(
        self,
        site_id: str,
        include_preview: bool = False,
    ) -> UIVisibilityConfig:
        """Get UI visibility configuration for a site."""
        site = self._maturity_manager.get_site(site_id)
        if not site:
            return UIVisibilityConfig(
                site_id=site_id,
                current_level=MaturityLevel.L0_STRATEGIC,
                features=[],
            )
        
        current_level = site.current_level
        enabled_features = site.get_enabled_features()
        
        preview_level = self._preview_enabled.get(site_id)
        if include_preview and preview_level:
            # Include features up to preview level
            for level in MaturityLevel:
                if level <= preview_level:
                    enabled_features.update(MATURITY_FEATURES.get(level, set()))
        
        features = []
        for feature in FeatureModule:
            # Find which level this feature is available at
            available_level = None
            for level in MaturityLevel:
                if feature in MATURITY_FEATURES.get(level, set()):
                    available_level = level
                    break
            
            is_enabled = feature in enabled_features
            is_visible = is_enabled or (
                include_preview and preview_level and available_level and available_level <= preview_level
            )
            
            access = FeatureAccess(
                feature=feature,
                enabled=is_enabled,
                visible=is_visible,
                available_at_level=available_level,
                reason="" if is_enabled else f"Available at {available_level.name if available_level else 'unknown'} level",
            )
            features.append(access)
        
        return UIVisibilityConfig(
            site_id=site_id,
            current_level=current_level,
            features=features,
            show_future_preview=preview_level is not None,
            preview_level=preview_level,
        )
    
    def enable_preview(self, site_id: str, preview_level: MaturityLevel):
        """Enable future state preview for a site."""
        self._preview_enabled[site_id] = preview_level
    
    def disable_preview(self, site_id: str):
        """Disable future state preview for a site."""
        self._preview_enabled.pop(site_id, None)
    
    def is_feature_visible(
        self,
        site_id: str,
        feature: FeatureModule,
        include_preview: bool = False,
    ) -> bool:
        """Check if a feature is visible for a site."""
        config = self.get_visibility_config(site_id, include_preview)
        for f in config.features:
            if f.feature == feature:
                return f.visible
        return False
    
    def get_hidden_features(self, site_id: str) -> list[FeatureModule]:
        """Get list of features hidden for current maturity level."""
        config = self.get_visibility_config(site_id, include_preview=False)
        return [f.feature for f in config.features if not f.visible]
    
    def get_upcoming_features(self, site_id: str) -> dict[MaturityLevel, list[FeatureModule]]:
        """Get features that will be unlocked at each future level."""
        site = self._maturity_manager.get_site(site_id)
        if not site:
            return {}
        
        upcoming = {}
        for level in MaturityLevel:
            if level > site.current_level:
                features = list(MATURITY_FEATURES.get(level, set()))
                if features:
                    upcoming[level] = features
        
        return upcoming


# =============================================================================
# HARDWARE ROLLOUT TRACKER
# =============================================================================


class HardwareRolloutTracker:
    """
    Tracks hardware asset rollout for factory infrastructure.
    
    Provides:
    - Asset registration and tracking
    - Discovery audit logging
    - Rollout progress monitoring
    - Station linking
    """
    
    def __init__(self):
        self._assets: dict[str, HardwareAsset] = {}
        self._discovery_log: list[dict[str, Any]] = []
    
    def register_asset(
        self,
        asset_type: HardwareAssetType,
        name: str,
        site_id: str,
        mac_address: str | None = None,
        serial_number: str | None = None,
        station_id: str | None = None,
    ) -> HardwareAsset:
        """Register a new hardware asset."""
        asset = HardwareAsset(
            asset_id=str(uuid.uuid4()),
            asset_type=asset_type,
            name=name,
            site_id=site_id,
            mac_address=mac_address,
            serial_number=serial_number,
            station_id=station_id,
        )
        self._assets[asset.asset_id] = asset
        return asset
    
    def get_asset(self, asset_id: str) -> HardwareAsset | None:
        """Get a hardware asset by ID."""
        return self._assets.get(asset_id)
    
    def get_asset_by_mac(self, mac_address: str) -> HardwareAsset | None:
        """Get a hardware asset by MAC address."""
        for asset in self._assets.values():
            if asset.mac_address == mac_address:
                return asset
        return None
    
    def get_site_assets(self, site_id: str) -> list[HardwareAsset]:
        """Get all assets for a site."""
        return [a for a in self._assets.values() if a.site_id == site_id]
    
    def get_station_assets(self, station_id: str) -> list[HardwareAsset]:
        """Get all assets for a station."""
        return [a for a in self._assets.values() if a.station_id == station_id]
    
    def update_asset_status(
        self,
        asset_id: str,
        status: HardwareAssetStatus,
        ip_address: str | None = None,
        firmware_version: str | None = None,
    ) -> bool:
        """Update hardware asset status."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        
        old_status = asset.status
        asset.status = status
        asset.last_seen = datetime.now()
        
        if ip_address:
            asset.ip_address = ip_address
        if firmware_version:
            asset.firmware_version = firmware_version
        
        # Log discovery event if newly discovered
        if old_status == HardwareAssetStatus.ORDERED and status != HardwareAssetStatus.ORDERED:
            self._log_discovery(asset)
        
        return True
    
    def link_to_station(self, asset_id: str, station_id: str) -> bool:
        """Link an asset to a station."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        
        asset.station_id = station_id
        return True
    
    def discover_asset(
        self,
        mac_address: str,
        ip_address: str,
        asset_type: HardwareAssetType | None = None,
        name: str | None = None,
        site_id: str | None = None,
    ) -> HardwareAsset:
        """Handle automatic discovery of a hardware asset."""
        # Check if asset already exists
        existing = self.get_asset_by_mac(mac_address)
        if existing:
            old_status = existing.status
            existing.ip_address = ip_address
            existing.last_seen = datetime.now()
            if existing.status == HardwareAssetStatus.ORDERED:
                existing.status = HardwareAssetStatus.DELIVERED
                # Log discovery when status changes from ORDERED
                self._log_discovery(existing)
            return existing
        
        # Create new asset from discovery
        asset = HardwareAsset(
            asset_id=str(uuid.uuid4()),
            asset_type=asset_type or HardwareAssetType.IOT_SENSOR,
            name=name or f"Discovered-{mac_address[-8:]}",
            mac_address=mac_address,
            ip_address=ip_address,
            site_id=site_id,
            status=HardwareAssetStatus.DELIVERED,
            last_seen=datetime.now(),
        )
        self._assets[asset.asset_id] = asset
        self._log_discovery(asset)
        
        return asset
    
    def _log_discovery(self, asset: HardwareAsset):
        """Log asset discovery event."""
        self._discovery_log.append({
            "timestamp": datetime.now().isoformat(),
            "asset_id": asset.asset_id,
            "asset_type": asset.asset_type.value,
            "mac_address": asset.mac_address,
            "ip_address": asset.ip_address,
            "site_id": asset.site_id,
        })
    
    def get_discovery_log(
        self,
        site_id: str | None = None,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get discovery audit log."""
        log = self._discovery_log
        
        if site_id:
            log = [e for e in log if e.get("site_id") == site_id]
        
        if since:
            log = [e for e in log if datetime.fromisoformat(e["timestamp"]) > since]
        
        return log
    
    def get_rollout_progress(self, site_id: str) -> RolloutProgress:
        """Get rollout progress for a site."""
        assets = self.get_site_assets(site_id)
        
        total = len(assets)
        deployed = sum(1 for a in assets if a.status in [
            HardwareAssetStatus.DEPLOYED,
            HardwareAssetStatus.ACTIVE,
        ])
        active = sum(1 for a in assets if a.status == HardwareAssetStatus.ACTIVE)
        failed = sum(1 for a in assets if a.status == HardwareAssetStatus.FAILED)
        
        # By type breakdown
        by_type = {}
        for asset_type in HardwareAssetType:
            type_assets = [a for a in assets if a.asset_type == asset_type]
            if type_assets:
                by_type[asset_type] = {
                    "total": len(type_assets),
                    "deployed": sum(1 for a in type_assets if a.status in [
                        HardwareAssetStatus.DEPLOYED,
                        HardwareAssetStatus.ACTIVE,
                    ]),
                    "active": sum(1 for a in type_assets if a.status == HardwareAssetStatus.ACTIVE),
                }
        
        return RolloutProgress(
            site_id=site_id,
            total_assets=total,
            deployed_assets=deployed,
            active_assets=active,
            failed_assets=failed,
            by_type=by_type,
        )


# =============================================================================
# FACTORY LAUNCHPAD (Main Class)
# =============================================================================


class FactoryLaunchpad:
    """
    Main Factory Launchpad orchestrator.
    
    Combines:
    - Maturity management
    - UI visibility
    - Hardware rollout tracking
    - Level-up workflow
    """
    
    def __init__(self):
        self._maturity_manager = MaturityManager()
        self._ui_manager = UIVisibilityManager(self._maturity_manager)
        self._hardware_tracker = HardwareRolloutTracker()
    
    @property
    def maturity(self) -> MaturityManager:
        """Get maturity manager."""
        return self._maturity_manager
    
    @property
    def ui(self) -> UIVisibilityManager:
        """Get UI visibility manager."""
        return self._ui_manager
    
    @property
    def hardware(self) -> HardwareRolloutTracker:
        """Get hardware rollout tracker."""
        return self._hardware_tracker
    
    def initialize_site(
        self,
        site_id: str,
        site_name: str,
        initial_level: MaturityLevel = MaturityLevel.L0_STRATEGIC,
        timezone: str = "UTC",
    ) -> SiteConfig:
        """Initialize a new factory site."""
        return self._maturity_manager.register_site(
            site_id=site_id,
            site_name=site_name,
            initial_level=initial_level,
            timezone=timezone,
        )
    
    def get_site_dashboard(self, site_id: str) -> dict[str, Any]:
        """Get comprehensive dashboard for a site."""
        site = self._maturity_manager.get_site(site_id)
        if not site:
            return {"error": "Site not found"}
        
        level_info = site.get_level_info()
        enabled_features = site.get_enabled_features()
        upcoming = self._ui_manager.get_upcoming_features(site_id)
        rollout = self._hardware_tracker.get_rollout_progress(site_id)
        checklists = self._maturity_manager.get_site_checklists(site_id)
        
        active_checklist = None
        for cl in checklists:
            if cl.status in [MaturityTransitionStatus.NOT_STARTED, MaturityTransitionStatus.IN_PROGRESS]:
                active_checklist = cl
                break
        
        return {
            "site_id": site_id,
            "site_name": site.site_name,
            "current_level": site.current_level.name,
            "level_info": level_info,
            "status": site.status.value,
            "enabled_features": [f.value for f in enabled_features],
            "enabled_features_count": len(enabled_features),
            "upcoming_features": {
                level.name: [f.value for f in features]
                for level, features in upcoming.items()
            },
            "hardware_rollout": {
                "total": rollout.total_assets,
                "deployed": rollout.deployed_assets,
                "active": rollout.active_assets,
                "deployment_percentage": rollout.deployment_percentage,
                "health_percentage": rollout.health_percentage,
            },
            "active_checklist": {
                "checklist_id": active_checklist.checklist_id,
                "from_level": active_checklist.from_level.name,
                "to_level": active_checklist.to_level.name,
                "completion_percentage": active_checklist.completion_percentage,
                "blocking_items": [i.title for i in active_checklist.blocking_items],
            } if active_checklist else None,
        }
    
    def validate_work_order_start(
        self,
        site_id: str,
        work_order_data: dict[str, Any],
    ) -> ActionValidationResult:
        """Validate if a work order can be started at current maturity level."""
        return self._maturity_manager.validate_action(
            site_id=site_id,
            action="start_work_order",
            required_level=MaturityLevel.L4_OPERATIONAL,
            fields=work_order_data,
        )
    
    def validate_andon_trigger(
        self,
        site_id: str,
        andon_data: dict[str, Any],
    ) -> ActionValidationResult:
        """Validate if Andon can be triggered at current maturity level."""
        return self._maturity_manager.validate_action(
            site_id=site_id,
            action="trigger_andon",
            required_level=MaturityLevel.L5_TPS,
            fields=andon_data,
        )
    
    def get_maturity_roadmap(self, site_id: str) -> list[dict[str, Any]]:
        """Get maturity roadmap for a site."""
        site = self._maturity_manager.get_site(site_id)
        if not site:
            return []
        
        roadmap = []
        for level in MaturityLevel:
            info = MATURITY_DESCRIPTIONS.get(level, {})
            features = MATURITY_FEATURES.get(level, set())
            
            roadmap.append({
                "level": level.name,
                "level_number": level.value,
                "name": info.get("name", ""),
                "mode": info.get("mode", ""),
                "focus": info.get("focus", ""),
                "entry_criteria": info.get("entry_criteria", ""),
                "exit_criteria": info.get("exit_criteria", ""),
                "features": [f.value for f in features],
                "is_current": level == site.current_level,
                "is_completed": level < site.current_level,
                "is_future": level > site.current_level,
            })
        
        return roadmap


# =============================================================================
# SINGLETON & FACTORY FUNCTIONS
# =============================================================================


_factory_launchpad: FactoryLaunchpad | None = None


def get_factory_launchpad() -> FactoryLaunchpad:
    """Get the Factory Launchpad singleton."""
    global _factory_launchpad
    if _factory_launchpad is None:
        _factory_launchpad = FactoryLaunchpad()
    return _factory_launchpad


def create_factory_launchpad() -> FactoryLaunchpad:
    """Create a new Factory Launchpad instance."""
    return FactoryLaunchpad()


def create_maturity_manager() -> MaturityManager:
    """Create a new Maturity Manager instance."""
    return MaturityManager()


def create_ui_visibility_manager(maturity_manager: MaturityManager) -> UIVisibilityManager:
    """Create a new UI Visibility Manager instance."""
    return UIVisibilityManager(maturity_manager)


def create_hardware_tracker() -> HardwareRolloutTracker:
    """Create a new Hardware Rollout Tracker instance."""
    return HardwareRolloutTracker()
