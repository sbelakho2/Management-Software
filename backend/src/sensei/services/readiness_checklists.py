"""
Readiness Checklists Service.

Provides comprehensive checklist management for:
- Supplier Readiness Assessments
- PPAP-lite (Production Part Approval Process) checklists
- Custom project-specific checklists

Each checklist:
- Has configurable sections and items
- Tracks completion status and evidence
- Supports approvals and sign-offs
- Can block NPI stage transitions when incomplete
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class ChecklistType(str, Enum):
    """Types of checklists."""
    
    SUPPLIER_READINESS = "supplier_readiness"
    PPAP_LITE = "ppap_lite"
    PROCESS_VALIDATION = "process_validation"
    QUALITY_SYSTEM = "quality_system"
    CUSTOM = "custom"


class ChecklistStatus(str, Enum):
    """Overall checklist status."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ItemStatus(str, Enum):
    """Individual checklist item status."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    NOT_APPLICABLE = "not_applicable"
    FAILED = "failed"
    WAIVED = "waived"


class ItemPriority(str, Enum):
    """Item priority/criticality."""
    
    CRITICAL = "critical"  # Must be complete
    MAJOR = "major"  # Should be complete
    MINOR = "minor"  # Nice to have
    INFORMATIONAL = "informational"  # For reference only


class PPAPLevel(int, Enum):
    """PPAP submission levels."""
    
    LEVEL_1 = 1  # Warrant only
    LEVEL_2 = 2  # Warrant + limited samples
    LEVEL_3 = 3  # Warrant + samples + partial docs (default)
    LEVEL_4 = 4  # Warrant + samples + full docs
    LEVEL_5 = 5  # Full docs available at supplier


@dataclass
class ChecklistItemDefinition:
    """Template definition for a checklist item."""
    
    id: str = ""
    section: str = ""
    name: str = ""
    description: str = ""
    priority: ItemPriority = ItemPriority.MAJOR
    requires_evidence: bool = False
    requires_approval: bool = False
    evidence_guidance: str = ""
    ppap_element: str | None = None  # For PPAP items (e.g., "1.1", "2.1")


@dataclass
class ChecklistItem:
    """An individual checklist item instance."""
    
    id: UUID = field(default_factory=uuid4)
    checklist_id: UUID = field(default_factory=uuid4)
    definition_id: str = ""
    section: str = ""
    name: str = ""
    description: str = ""
    priority: ItemPriority = ItemPriority.MAJOR
    
    # Status
    status: ItemStatus = ItemStatus.NOT_STARTED
    status_notes: str = ""
    
    # Evidence
    requires_evidence: bool = False
    evidence_provided: bool = False
    evidence_notes: str = ""
    attachment_ids: list[UUID] = field(default_factory=list)
    
    # Approval
    requires_approval: bool = False
    approved: bool = False
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    
    # Waiver (if applicable)
    waived: bool = False
    waived_by: UUID | None = None
    waived_at: datetime | None = None
    waiver_reason: str = ""
    waiver_expiration: datetime | None = None
    
    # Metadata
    completed_by: UUID | None = None
    completed_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_satisfied(self) -> bool:
        """Check if item is satisfied (complete, N/A, or waived)."""
        return self.status in (
            ItemStatus.COMPLETE,
            ItemStatus.NOT_APPLICABLE,
            ItemStatus.WAIVED,
        )
    
    def is_blocking(self) -> bool:
        """Check if item is blocking progress."""
        return (
            self.priority in (ItemPriority.CRITICAL, ItemPriority.MAJOR)
            and not self.is_satisfied()
        )


@dataclass
class ChecklistSection:
    """A section grouping related items."""
    
    id: str = ""
    name: str = ""
    description: str = ""
    sequence: int = 0
    items: list[ChecklistItem] = field(default_factory=list)
    
    def get_completion_percentage(self) -> Decimal:
        """Calculate section completion percentage."""
        if not self.items:
            return Decimal("100")
        
        satisfied = sum(1 for item in self.items if item.is_satisfied())
        return Decimal(satisfied * 100) / Decimal(len(self.items))
    
    def get_blocking_items(self) -> list[ChecklistItem]:
        """Get items blocking progress."""
        return [item for item in self.items if item.is_blocking()]


@dataclass
class Checklist:
    """A complete checklist instance."""
    
    id: UUID = field(default_factory=uuid4)
    checklist_type: ChecklistType = ChecklistType.SUPPLIER_READINESS
    name: str = ""
    description: str = ""
    
    # Linked entities
    npi_project_id: UUID | None = None
    supplier_id: UUID | None = None
    product_id: UUID | None = None
    
    # PPAP-specific
    ppap_level: PPAPLevel | None = None
    customer_specific_requirements: list[str] = field(default_factory=list)
    
    # Status
    status: ChecklistStatus = ChecklistStatus.NOT_STARTED
    
    # Items (organized by section)
    sections: list[ChecklistSection] = field(default_factory=list)
    
    # Validity
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    
    # Review/Approval
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: UUID = field(default_factory=uuid4)
    
    def get_all_items(self) -> list[ChecklistItem]:
        """Get all items across all sections."""
        items = []
        for section in self.sections:
            items.extend(section.items)
        return items
    
    def get_completion_percentage(self) -> Decimal:
        """Calculate overall completion percentage."""
        items = self.get_all_items()
        if not items:
            return Decimal("100")
        
        satisfied = sum(1 for item in items if item.is_satisfied())
        return Decimal(satisfied * 100) / Decimal(len(items))
    
    def get_blocking_items(self) -> list[ChecklistItem]:
        """Get all items blocking progress."""
        blocking = []
        for section in self.sections:
            blocking.extend(section.get_blocking_items())
        return blocking
    
    def is_complete(self) -> bool:
        """Check if checklist is complete (no blocking items)."""
        return len(self.get_blocking_items()) == 0
    
    def is_approved(self) -> bool:
        """Check if checklist is approved."""
        return self.status == ChecklistStatus.APPROVED


@dataclass
class ChecklistTemplate:
    """Template for creating checklists."""
    
    id: UUID = field(default_factory=uuid4)
    checklist_type: ChecklistType = ChecklistType.SUPPLIER_READINESS
    name: str = ""
    description: str = ""
    version: str = "1.0"
    is_active: bool = True
    
    # Template sections and items
    sections: list[dict[str, Any]] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReadinessChecklistsService:
    """
    Service for managing readiness checklists.
    
    Provides:
    - Supplier readiness assessment checklists
    - PPAP-lite checklists with configurable levels
    - Custom checklist creation
    - Progress tracking and blocking logic
    - Template management
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._checklists: dict[UUID, Checklist] = {}
        self._templates: dict[UUID, ChecklistTemplate] = {}
        self._init_default_templates()
    
    def _init_default_templates(self) -> None:
        """Initialize default checklist templates."""
        # Supplier Readiness Template
        supplier_template = self._create_supplier_readiness_template()
        self._templates[supplier_template.id] = supplier_template
        
        # PPAP-lite Template
        ppap_template = self._create_ppap_lite_template()
        self._templates[ppap_template.id] = ppap_template
    
    def _create_supplier_readiness_template(self) -> ChecklistTemplate:
        """Create default supplier readiness template."""
        sections = [
            {
                "id": "quality_system",
                "name": "Quality System",
                "description": "Quality management system requirements",
                "sequence": 1,
                "items": [
                    {
                        "id": "qs_1",
                        "name": "ISO 9001 Certification",
                        "description": "Supplier has valid ISO 9001 certification",
                        "priority": "critical",
                        "requires_evidence": True,
                        "evidence_guidance": "Provide copy of current ISO 9001 certificate",
                    },
                    {
                        "id": "qs_2",
                        "name": "Quality Manual",
                        "description": "Quality manual reviewed and adequate",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "Provide quality manual or relevant sections",
                    },
                    {
                        "id": "qs_3",
                        "name": "Inspection Capabilities",
                        "description": "Adequate inspection equipment and procedures",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "Equipment list and calibration records",
                    },
                    {
                        "id": "qs_4",
                        "name": "Corrective Action Process",
                        "description": "Documented corrective action procedure",
                        "priority": "major",
                        "requires_evidence": False,
                    },
                ],
            },
            {
                "id": "capacity",
                "name": "Capacity & Capability",
                "description": "Production capacity and technical capability",
                "sequence": 2,
                "items": [
                    {
                        "id": "cap_1",
                        "name": "Production Capacity",
                        "description": "Sufficient capacity for projected volumes",
                        "priority": "critical",
                        "requires_evidence": True,
                        "evidence_guidance": "Capacity analysis or commitment letter",
                    },
                    {
                        "id": "cap_2",
                        "name": "Equipment Adequacy",
                        "description": "Required equipment available and suitable",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "Equipment list with specifications",
                    },
                    {
                        "id": "cap_3",
                        "name": "Technical Competence",
                        "description": "Demonstrated technical capability for product",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "Similar product references or samples",
                    },
                    {
                        "id": "cap_4",
                        "name": "Backup/Contingency Plan",
                        "description": "Contingency plan for disruptions",
                        "priority": "minor",
                        "requires_evidence": False,
                    },
                ],
            },
            {
                "id": "logistics",
                "name": "Logistics & Delivery",
                "description": "Delivery and logistics capabilities",
                "sequence": 3,
                "items": [
                    {
                        "id": "log_1",
                        "name": "On-Time Delivery History",
                        "description": "Track record of on-time delivery",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "OTD metrics or customer references",
                    },
                    {
                        "id": "log_2",
                        "name": "Lead Time Commitment",
                        "description": "Committed lead times are acceptable",
                        "priority": "major",
                        "requires_evidence": False,
                    },
                    {
                        "id": "log_3",
                        "name": "Packaging Standards",
                        "description": "Packaging meets requirements",
                        "priority": "minor",
                        "requires_evidence": True,
                        "evidence_guidance": "Packaging specification agreement",
                    },
                ],
            },
            {
                "id": "commercial",
                "name": "Commercial",
                "description": "Commercial and contractual requirements",
                "sequence": 4,
                "items": [
                    {
                        "id": "com_1",
                        "name": "Pricing Agreement",
                        "description": "Pricing agreed and documented",
                        "priority": "critical",
                        "requires_evidence": True,
                        "evidence_guidance": "Signed quotation or pricing agreement",
                    },
                    {
                        "id": "com_2",
                        "name": "Payment Terms",
                        "description": "Payment terms agreed",
                        "priority": "major",
                        "requires_evidence": False,
                    },
                    {
                        "id": "com_3",
                        "name": "Contract/PO",
                        "description": "Contract or blanket PO in place",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "Signed contract or PO confirmation",
                    },
                    {
                        "id": "com_4",
                        "name": "NDA/Confidentiality",
                        "description": "NDA signed if required",
                        "priority": "major",
                        "requires_evidence": True,
                        "evidence_guidance": "Signed NDA",
                    },
                ],
            },
        ]
        
        return ChecklistTemplate(
            checklist_type=ChecklistType.SUPPLIER_READINESS,
            name="Supplier Readiness Assessment",
            description="Standard supplier readiness checklist for NPI",
            sections=sections,
        )
    
    def _create_ppap_lite_template(self) -> ChecklistTemplate:
        """Create default PPAP-lite template."""
        sections = [
            {
                "id": "design_records",
                "name": "Design Records",
                "description": "Design documentation requirements",
                "sequence": 1,
                "items": [
                    {
                        "id": "ppap_1_1",
                        "name": "Design Records",
                        "description": "Customer design records (drawings, specs)",
                        "priority": "critical",
                        "requires_evidence": True,
                        "ppap_element": "1",
                        "evidence_guidance": "Latest revision drawings and specifications",
                    },
                    {
                        "id": "ppap_1_2",
                        "name": "Engineering Change Documents",
                        "description": "Authorized engineering change documents",
                        "priority": "major",
                        "requires_evidence": True,
                        "ppap_element": "2",
                        "evidence_guidance": "ECN/ECO documentation if applicable",
                    },
                ],
            },
            {
                "id": "process_documentation",
                "name": "Process Documentation",
                "description": "Process and flow documentation",
                "sequence": 2,
                "items": [
                    {
                        "id": "ppap_2_1",
                        "name": "Process Flow Diagram",
                        "description": "Process flow diagram for production",
                        "priority": "critical",
                        "requires_evidence": True,
                        "ppap_element": "5",
                        "evidence_guidance": "Complete process flow with all operations",
                    },
                    {
                        "id": "ppap_2_2",
                        "name": "PFMEA",
                        "description": "Process Failure Mode and Effects Analysis",
                        "priority": "major",
                        "requires_evidence": True,
                        "ppap_element": "6",
                        "evidence_guidance": "PFMEA document",
                    },
                    {
                        "id": "ppap_2_3",
                        "name": "Control Plan",
                        "description": "Production control plan",
                        "priority": "critical",
                        "requires_evidence": True,
                        "ppap_element": "7",
                        "evidence_guidance": "Control plan covering all CTQs",
                    },
                ],
            },
            {
                "id": "measurement",
                "name": "Measurement & Analysis",
                "description": "Measurement system and capability studies",
                "sequence": 3,
                "items": [
                    {
                        "id": "ppap_3_1",
                        "name": "MSA Studies",
                        "description": "Measurement System Analysis (Gage R&R)",
                        "priority": "major",
                        "requires_evidence": True,
                        "ppap_element": "8",
                        "evidence_guidance": "MSA/Gage R&R results for key characteristics",
                    },
                    {
                        "id": "ppap_3_2",
                        "name": "Dimensional Results",
                        "description": "Dimensional inspection results",
                        "priority": "critical",
                        "requires_evidence": True,
                        "ppap_element": "9",
                        "evidence_guidance": "Dimensional report (ballooned drawing + results)",
                    },
                    {
                        "id": "ppap_3_3",
                        "name": "Material Test Results",
                        "description": "Material/performance test results",
                        "priority": "major",
                        "requires_evidence": True,
                        "ppap_element": "10",
                        "evidence_guidance": "Material certificates and test reports",
                    },
                    {
                        "id": "ppap_3_4",
                        "name": "Initial Process Study",
                        "description": "Initial process capability study (Ppk/Cpk)",
                        "priority": "major",
                        "requires_evidence": True,
                        "ppap_element": "11",
                        "evidence_guidance": "Capability study results (target Ppk ≥ 1.67)",
                    },
                ],
            },
            {
                "id": "samples",
                "name": "Sample Parts",
                "description": "Sample part requirements",
                "sequence": 4,
                "items": [
                    {
                        "id": "ppap_4_1",
                        "name": "Sample Production Parts",
                        "description": "Sample parts from production run",
                        "priority": "critical",
                        "requires_evidence": True,
                        "ppap_element": "14",
                        "evidence_guidance": "Sample parts (quantity per customer requirement)",
                    },
                    {
                        "id": "ppap_4_2",
                        "name": "Master Sample",
                        "description": "Master/reference sample retained",
                        "priority": "major",
                        "requires_evidence": True,
                        "ppap_element": "15",
                        "evidence_guidance": "Photo or confirmation of master sample",
                    },
                ],
            },
            {
                "id": "approval",
                "name": "Approval Documentation",
                "description": "Final approval documentation",
                "sequence": 5,
                "items": [
                    {
                        "id": "ppap_5_1",
                        "name": "Part Submission Warrant (PSW)",
                        "description": "Completed and signed PSW",
                        "priority": "critical",
                        "requires_evidence": True,
                        "requires_approval": True,
                        "ppap_element": "18",
                        "evidence_guidance": "Signed PSW form",
                    },
                    {
                        "id": "ppap_5_2",
                        "name": "Appearance Approval Report",
                        "description": "AAR if appearance is specified",
                        "priority": "minor",
                        "requires_evidence": True,
                        "ppap_element": "16",
                        "evidence_guidance": "Signed AAR if applicable",
                    },
                ],
            },
        ]
        
        return ChecklistTemplate(
            checklist_type=ChecklistType.PPAP_LITE,
            name="PPAP-lite Checklist",
            description="Simplified PPAP checklist for production part approval",
            sections=sections,
        )
    
    # -------------------------------------------------------------------------
    # Template Management
    # -------------------------------------------------------------------------
    
    def get_templates(
        self,
        checklist_type: ChecklistType | None = None,
        active_only: bool = True,
    ) -> list[ChecklistTemplate]:
        """Get available templates."""
        templates = list(self._templates.values())
        
        if checklist_type is not None:
            templates = [t for t in templates if t.checklist_type == checklist_type]
        
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        return sorted(templates, key=lambda t: t.name)
    
    def get_template(self, template_id: UUID) -> ChecklistTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_template_by_type(
        self,
        checklist_type: ChecklistType,
    ) -> ChecklistTemplate | None:
        """Get the default template for a type."""
        for template in self._templates.values():
            if template.checklist_type == checklist_type and template.is_active:
                return template
        return None
    
    def create_template(
        self,
        name: str,
        checklist_type: ChecklistType,
        sections: list[dict[str, Any]],
        description: str = "",
    ) -> ChecklistTemplate:
        """Create a new checklist template."""
        template = ChecklistTemplate(
            name=name,
            checklist_type=checklist_type,
            description=description,
            sections=sections,
        )
        self._templates[template.id] = template
        return template
    
    # -------------------------------------------------------------------------
    # Checklist Creation
    # -------------------------------------------------------------------------
    
    def create_checklist(
        self,
        checklist_type: ChecklistType,
        name: str,
        description: str = "",
        npi_project_id: UUID | None = None,
        supplier_id: UUID | None = None,
        product_id: UUID | None = None,
        ppap_level: PPAPLevel | None = None,
        template_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> Checklist:
        """Create a new checklist from a template."""
        # Find template
        if template_id:
            template = self._templates.get(template_id)
        else:
            template = self.get_template_by_type(checklist_type)
        
        if template is None:
            # Create empty checklist
            checklist = Checklist(
                checklist_type=checklist_type,
                name=name,
                description=description,
                npi_project_id=npi_project_id,
                supplier_id=supplier_id,
                product_id=product_id,
                ppap_level=ppap_level,
                created_by=created_by or uuid4(),
            )
        else:
            # Create from template
            checklist = Checklist(
                checklist_type=checklist_type,
                name=name or template.name,
                description=description or template.description,
                npi_project_id=npi_project_id,
                supplier_id=supplier_id,
                product_id=product_id,
                ppap_level=ppap_level,
                created_by=created_by or uuid4(),
            )
            
            # Populate sections and items from template
            for section_def in template.sections:
                section = ChecklistSection(
                    id=section_def["id"],
                    name=section_def["name"],
                    description=section_def.get("description", ""),
                    sequence=section_def.get("sequence", 0),
                )
                
                for item_def in section_def.get("items", []):
                    priority = ItemPriority(item_def.get("priority", "major"))
                    
                    item = ChecklistItem(
                        checklist_id=checklist.id,
                        definition_id=item_def["id"],
                        section=section.id,
                        name=item_def["name"],
                        description=item_def.get("description", ""),
                        priority=priority,
                        requires_evidence=item_def.get("requires_evidence", False),
                        requires_approval=item_def.get("requires_approval", False),
                    )
                    section.items.append(item)
                
                checklist.sections.append(section)
        
        self._checklists[checklist.id] = checklist
        return checklist
    
    def create_supplier_readiness_checklist(
        self,
        supplier_id: UUID,
        npi_project_id: UUID | None = None,
        product_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> Checklist:
        """Create a supplier readiness checklist."""
        return self.create_checklist(
            checklist_type=ChecklistType.SUPPLIER_READINESS,
            name="Supplier Readiness Assessment",
            supplier_id=supplier_id,
            npi_project_id=npi_project_id,
            product_id=product_id,
            created_by=created_by,
        )
    
    def create_ppap_checklist(
        self,
        supplier_id: UUID,
        product_id: UUID,
        ppap_level: PPAPLevel = PPAPLevel.LEVEL_3,
        npi_project_id: UUID | None = None,
        customer_requirements: list[str] | None = None,
        created_by: UUID | None = None,
    ) -> Checklist:
        """Create a PPAP-lite checklist."""
        checklist = self.create_checklist(
            checklist_type=ChecklistType.PPAP_LITE,
            name="PPAP Submission",
            supplier_id=supplier_id,
            product_id=product_id,
            npi_project_id=npi_project_id,
            ppap_level=ppap_level,
            created_by=created_by,
        )
        
        if customer_requirements:
            checklist.customer_specific_requirements = customer_requirements
        
        return checklist
    
    # -------------------------------------------------------------------------
    # Checklist Retrieval
    # -------------------------------------------------------------------------
    
    def get_checklist(self, checklist_id: UUID) -> Checklist | None:
        """Get a checklist by ID."""
        return self._checklists.get(checklist_id)
    
    def list_checklists(
        self,
        checklist_type: ChecklistType | None = None,
        npi_project_id: UUID | None = None,
        supplier_id: UUID | None = None,
        status: ChecklistStatus | None = None,
    ) -> list[Checklist]:
        """List checklists with optional filters."""
        checklists = list(self._checklists.values())
        
        if checklist_type is not None:
            checklists = [c for c in checklists if c.checklist_type == checklist_type]
        
        if npi_project_id is not None:
            checklists = [c for c in checklists if c.npi_project_id == npi_project_id]
        
        if supplier_id is not None:
            checklists = [c for c in checklists if c.supplier_id == supplier_id]
        
        if status is not None:
            checklists = [c for c in checklists if c.status == status]
        
        return sorted(checklists, key=lambda c: c.created_at, reverse=True)
    
    def get_project_checklists(
        self,
        npi_project_id: UUID,
    ) -> list[Checklist]:
        """Get all checklists for an NPI project."""
        return self.list_checklists(npi_project_id=npi_project_id)
    
    def get_supplier_checklists(
        self,
        supplier_id: UUID,
    ) -> list[Checklist]:
        """Get all checklists for a supplier."""
        return self.list_checklists(supplier_id=supplier_id)
    
    # -------------------------------------------------------------------------
    # Item Management
    # -------------------------------------------------------------------------
    
    def get_item(
        self,
        checklist_id: UUID,
        item_id: UUID,
    ) -> ChecklistItem | None:
        """Get a specific item from a checklist."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return None
        
        for section in checklist.sections:
            for item in section.items:
                if item.id == item_id:
                    return item
        
        return None
    
    def update_item_status(
        self,
        checklist_id: UUID,
        item_id: UUID,
        status: ItemStatus,
        notes: str = "",
        completed_by: UUID | None = None,
    ) -> ChecklistItem | None:
        """Update an item's status."""
        item = self.get_item(checklist_id, item_id)
        if item is None:
            return None
        
        item.status = status
        item.status_notes = notes
        item.updated_at = datetime.now(timezone.utc)
        
        if status == ItemStatus.COMPLETE:
            item.completed_by = completed_by
            item.completed_at = datetime.now(timezone.utc)
        
        # Update checklist status
        self._update_checklist_status(checklist_id)
        
        return item
    
    def add_item_evidence(
        self,
        checklist_id: UUID,
        item_id: UUID,
        attachment_ids: list[UUID],
        notes: str = "",
    ) -> ChecklistItem | None:
        """Add evidence to an item."""
        item = self.get_item(checklist_id, item_id)
        if item is None:
            return None
        
        item.attachment_ids.extend(attachment_ids)
        if notes:
            item.evidence_notes = f"{item.evidence_notes}\n{notes}".strip()
        item.evidence_provided = True
        item.updated_at = datetime.now(timezone.utc)
        
        # Auto-update status if not started
        if item.status == ItemStatus.NOT_STARTED:
            item.status = ItemStatus.IN_PROGRESS
        
        return item
    
    def approve_item(
        self,
        checklist_id: UUID,
        item_id: UUID,
        approved_by: UUID,
    ) -> ChecklistItem | None:
        """Approve an item that requires approval."""
        item = self.get_item(checklist_id, item_id)
        if item is None:
            return None
        
        item.approved = True
        item.approved_by = approved_by
        item.approved_at = datetime.now(timezone.utc)
        item.status = ItemStatus.COMPLETE
        item.updated_at = datetime.now(timezone.utc)
        
        self._update_checklist_status(checklist_id)
        
        return item
    
    def waive_item(
        self,
        checklist_id: UUID,
        item_id: UUID,
        waived_by: UUID,
        reason: str,
        expiration: datetime | None = None,
    ) -> ChecklistItem | None:
        """Waive an item requirement."""
        item = self.get_item(checklist_id, item_id)
        if item is None:
            return None
        
        item.status = ItemStatus.WAIVED
        item.waived = True
        item.waived_by = waived_by
        item.waived_at = datetime.now(timezone.utc)
        item.waiver_reason = reason
        item.waiver_expiration = expiration
        item.updated_at = datetime.now(timezone.utc)
        
        self._update_checklist_status(checklist_id)
        
        return item
    
    def mark_item_not_applicable(
        self,
        checklist_id: UUID,
        item_id: UUID,
        reason: str,
        marked_by: UUID,
    ) -> ChecklistItem | None:
        """Mark an item as not applicable."""
        item = self.get_item(checklist_id, item_id)
        if item is None:
            return None
        
        item.status = ItemStatus.NOT_APPLICABLE
        item.status_notes = reason
        item.completed_by = marked_by
        item.completed_at = datetime.now(timezone.utc)
        item.updated_at = datetime.now(timezone.utc)
        
        self._update_checklist_status(checklist_id)
        
        return item
    
    def _update_checklist_status(self, checklist_id: UUID) -> None:
        """Update checklist status based on items."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return
        
        items = checklist.get_all_items()
        if not items:
            return
        
        # Count statuses
        not_started = sum(1 for i in items if i.status == ItemStatus.NOT_STARTED)
        in_progress = sum(
            1 for i in items
            if i.status in (ItemStatus.IN_PROGRESS, ItemStatus.FAILED)
        )
        satisfied = sum(1 for i in items if i.is_satisfied())
        
        # Determine checklist status
        if not_started == len(items):
            checklist.status = ChecklistStatus.NOT_STARTED
        elif satisfied == len(items):
            if checklist.status != ChecklistStatus.APPROVED:
                checklist.status = ChecklistStatus.PENDING_REVIEW
        else:
            checklist.status = ChecklistStatus.IN_PROGRESS
        
        checklist.updated_at = datetime.now(timezone.utc)
    
    # -------------------------------------------------------------------------
    # Checklist Approval
    # -------------------------------------------------------------------------
    
    def submit_for_review(
        self,
        checklist_id: UUID,
    ) -> Checklist | None:
        """Submit checklist for review."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return None
        
        if not checklist.is_complete():
            return None  # Cannot submit with blocking items
        
        checklist.status = ChecklistStatus.PENDING_REVIEW
        checklist.updated_at = datetime.now(timezone.utc)
        
        return checklist
    
    def approve_checklist(
        self,
        checklist_id: UUID,
        approved_by: UUID,
        notes: str = "",
        valid_until: datetime | None = None,
    ) -> Checklist | None:
        """Approve a checklist."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return None
        
        checklist.status = ChecklistStatus.APPROVED
        checklist.reviewed_by = approved_by
        checklist.reviewed_at = datetime.now(timezone.utc)
        checklist.review_notes = notes
        checklist.valid_from = datetime.now(timezone.utc)
        checklist.valid_until = valid_until
        checklist.updated_at = datetime.now(timezone.utc)
        
        return checklist
    
    def reject_checklist(
        self,
        checklist_id: UUID,
        rejected_by: UUID,
        reason: str,
    ) -> Checklist | None:
        """Reject a checklist."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return None
        
        checklist.status = ChecklistStatus.REJECTED
        checklist.reviewed_by = rejected_by
        checklist.reviewed_at = datetime.now(timezone.utc)
        checklist.review_notes = reason
        checklist.updated_at = datetime.now(timezone.utc)
        
        return checklist
    
    # -------------------------------------------------------------------------
    # Progress & Reporting
    # -------------------------------------------------------------------------
    
    def get_checklist_summary(
        self,
        checklist_id: UUID,
    ) -> dict[str, Any] | None:
        """Get a summary of checklist progress."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return None
        
        items = checklist.get_all_items()
        blocking = checklist.get_blocking_items()
        
        status_counts = {
            "not_started": 0,
            "in_progress": 0,
            "complete": 0,
            "not_applicable": 0,
            "failed": 0,
            "waived": 0,
        }
        
        for item in items:
            status_counts[item.status.value] += 1
        
        section_summaries = []
        for section in checklist.sections:
            section_summaries.append({
                "id": section.id,
                "name": section.name,
                "total_items": len(section.items),
                "completion_percentage": float(section.get_completion_percentage()),
                "blocking_items": len(section.get_blocking_items()),
            })
        
        return {
            "checklist_id": checklist.id,
            "name": checklist.name,
            "type": checklist.checklist_type.value,
            "status": checklist.status.value,
            "total_items": len(items),
            "completion_percentage": float(checklist.get_completion_percentage()),
            "blocking_items_count": len(blocking),
            "is_complete": checklist.is_complete(),
            "is_approved": checklist.is_approved(),
            "status_counts": status_counts,
            "sections": section_summaries,
        }
    
    def get_blocking_items(
        self,
        checklist_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get details of blocking items."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return []
        
        blocking = checklist.get_blocking_items()
        
        return [
            {
                "id": item.id,
                "section": item.section,
                "name": item.name,
                "description": item.description,
                "priority": item.priority.value,
                "status": item.status.value,
                "requires_evidence": item.requires_evidence,
                "evidence_provided": item.evidence_provided,
                "requires_approval": item.requires_approval,
                "approved": item.approved,
            }
            for item in blocking
        ]
    
    def get_ppap_status(
        self,
        checklist_id: UUID,
    ) -> dict[str, Any] | None:
        """Get PPAP-specific status information."""
        checklist = self._checklists.get(checklist_id)
        if checklist is None:
            return None
        
        if checklist.checklist_type != ChecklistType.PPAP_LITE:
            return None
        
        items = checklist.get_all_items()
        
        # Group by PPAP element
        elements: dict[str, dict[str, Any]] = {}
        for item in items:
            # Parse ppap_element from definition_id (e.g., "ppap_1_1" -> "1")
            parts = item.definition_id.split("_")
            if len(parts) >= 2:
                element = parts[1]
                if element not in elements:
                    elements[element] = {
                        "element": element,
                        "items": [],
                        "complete": True,
                    }
                elements[element]["items"].append(item.name)
                if not item.is_satisfied():
                    elements[element]["complete"] = False
        
        return {
            "checklist_id": checklist.id,
            "ppap_level": checklist.ppap_level.value if checklist.ppap_level else None,
            "status": checklist.status.value,
            "elements": list(elements.values()),
            "customer_requirements": checklist.customer_specific_requirements,
            "ready_for_submission": checklist.is_complete(),
        }
