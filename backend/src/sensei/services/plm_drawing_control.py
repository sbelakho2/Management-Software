"""
PLM Drawing Control Service.

Provides manufacturing-grade drawing and revision control with:
- Unified revision management between PLM and Sensei OS
- Immutable hash-linking for revision integrity
- Automated revision impact analysis
- Controlled shop-floor distribution
- Training re-certification workflow triggers
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import hashlib
import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class RevisionStatus(str, Enum):
    """Document revision status."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    RELEASED = "released"
    OBSOLETE = "obsolete"
    SUPERSEDED = "superseded"


class DocumentType(str, Enum):
    """Types of controlled documents."""
    DRAWING = "drawing"
    BOM = "bom"
    ROUTING = "routing"
    SPECIFICATION = "specification"
    WORK_INSTRUCTION = "work_instruction"
    INSPECTION_PLAN = "inspection_plan"
    CTQ_DOCUMENT = "ctq_document"
    CONTROL_PLAN = "control_plan"
    PFMEA = "pfmea"
    STANDARD_WORK = "standard_work"


class ChangeType(str, Enum):
    """Types of document changes."""
    MINOR = "minor"  # Typo fixes, formatting
    MAJOR = "major"  # Significant content changes
    CRITICAL = "critical"  # Safety, quality-critical changes


class ImpactType(str, Enum):
    """Types of revision impact."""
    CTQ_UPDATE = "ctq_update"
    STANDARD_WORK_UPDATE = "standard_work_update"
    INSPECTION_PLAN_UPDATE = "inspection_plan_update"
    TRAINING_RECERT = "training_recert"
    TOOLING_CHANGE = "tooling_change"
    PROCESS_CHANGE = "process_change"


class AccessLevel(str, Enum):
    """Shop floor access levels."""
    VIEW_ONLY = "view_only"
    PRINT = "print"
    DOWNLOAD = "download"
    ANNOTATE = "annotate"


class PLMSystem(str, Enum):
    """Supported PLM systems."""
    TEAMCENTER = "teamcenter"
    WINDCHILL = "windchill"
    ENOVIA = "enovia"
    ARAS = "aras"
    SOLIDWORKS_PDM = "solidworks_pdm"
    AUTODESK_VAULT = "autodesk_vault"
    CUSTOM = "custom"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class DocumentRevision:
    """A document revision with immutable hash."""
    id: str
    document_id: str
    revision_number: str
    version: int
    status: RevisionStatus
    content_hash: str
    file_path: str | None = None
    file_size: int = 0
    file_type: str | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: str | None = None
    approved_at: datetime | None = None
    released_at: datetime | None = None
    obsoleted_at: datetime | None = None
    change_type: ChangeType = ChangeType.MINOR
    change_description: str | None = None
    plm_revision_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ControlledDocument:
    """A controlled document with revision history."""
    id: str
    document_number: str
    title: str
    document_type: DocumentType
    current_revision_id: str | None = None
    current_revision_number: str | None = None
    part_number: str | None = None
    product_family: str | None = None
    site_id: str | None = None
    owner: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    plm_document_id: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RevisionLink:
    """Link between revisions showing dependency."""
    id: str
    source_revision_id: str
    target_revision_id: str
    link_type: str  # e.g., "derived_from", "supersedes", "references"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RevisionImpact:
    """Impact of a revision change."""
    id: str
    revision_id: str
    impact_type: ImpactType
    affected_entity_type: str  # e.g., "ctq", "standard_work", "training"
    affected_entity_id: str
    description: str
    requires_action: bool = True
    action_due_date: datetime | None = None
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TrainingRecertification:
    """Training re-certification triggered by revision."""
    id: str
    revision_id: str
    employee_id: str
    skill_id: str
    skill_name: str
    current_certification_date: datetime | None = None
    required_by: datetime | None = None
    status: str = "pending"  # pending, in_progress, completed, waived
    completed_at: datetime | None = None
    waived_by: str | None = None
    waiver_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ShopFloorAccess:
    """Shop floor access control for documents."""
    id: str
    document_id: str
    revision_id: str
    station_id: str | None = None
    work_center_id: str | None = None
    access_level: AccessLevel = AccessLevel.VIEW_ONLY
    is_active: bool = True
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    granted_by: str | None = None
    expires_at: datetime | None = None


@dataclass
class DocumentAccess:
    """Log of document access on shop floor."""
    id: str
    document_id: str
    revision_id: str
    accessed_by: str
    accessed_at: datetime
    access_type: str  # view, print, download
    station_id: str | None = None
    device_id: str | None = None
    ip_address: str | None = None


@dataclass
class PLMSyncRecord:
    """Record of PLM synchronization."""
    id: str
    document_id: str
    plm_document_id: str
    sync_direction: str  # inbound, outbound
    sync_status: str  # success, failed, conflict
    synced_at: datetime
    revision_before: str | None = None
    revision_after: str | None = None
    conflict_details: str | None = None


@dataclass
class ObsoleteWatermark:
    """Watermark configuration for obsolete documents."""
    id: str
    document_id: str
    revision_id: str
    watermark_text: str = "OBSOLETE"
    watermark_color: str = "red"
    watermark_opacity: float = 0.5
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# REVISION GENERATOR
# =============================================================================


class RevisionNumberGenerator:
    """Generates revision numbers in various formats."""
    
    @staticmethod
    def alpha(current: str | None = None) -> str:
        """Generate alphabetic revisions (A, B, C, ... Z, AA, AB, ...)."""
        if not current:
            return "A"
        
        if len(current) == 1:
            if current == "Z":
                return "AA"
            return chr(ord(current) + 1)
        
        # Multi-character
        last = current[-1]
        if last == "Z":
            return RevisionNumberGenerator.alpha(current[:-1]) + "A"
        return current[:-1] + chr(ord(last) + 1)
    
    @staticmethod
    def numeric(current: str | None = None) -> str:
        """Generate numeric revisions (1, 2, 3, ...)."""
        if not current:
            return "1"
        return str(int(current) + 1)
    
    @staticmethod
    def semantic(current: str | None = None, change_type: ChangeType = ChangeType.MINOR) -> str:
        """Generate semantic versions (1.0.0, 1.0.1, 1.1.0, 2.0.0)."""
        if not current:
            return "1.0.0"
        
        parts = current.split(".")
        if len(parts) != 3:
            return "1.0.0"
        
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        
        if change_type == ChangeType.CRITICAL:
            return f"{major + 1}.0.0"
        elif change_type == ChangeType.MAJOR:
            return f"{major}.{minor + 1}.0"
        else:
            return f"{major}.{minor}.{patch + 1}"
    
    @staticmethod
    def dated(prefix: str = "REV") -> str:
        """Generate date-based revisions (REV-20260109-001)."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{prefix}-{date_str}-001"


# =============================================================================
# PLM DRAWING CONTROL SERVICE
# =============================================================================


class PLMDrawingControlService:
    """
    Manufacturing-grade PLM drawing and revision control.
    
    Provides:
    - Unified revision management
    - Immutable hash-linking
    - Automated impact analysis
    - Controlled shop-floor distribution
    - Training re-certification triggers
    """
    
    def __init__(
        self,
        plm_system: PLMSystem | None = None,
        revision_format: str = "alpha",  # alpha, numeric, semantic
    ):
        self.plm_system = plm_system
        self.revision_format = revision_format
        self._rev_generator = RevisionNumberGenerator()
        
        # Storage
        self._documents: dict[str, ControlledDocument] = {}
        self._revisions: dict[str, DocumentRevision] = {}
        self._revision_links: list[RevisionLink] = []
        self._impacts: list[RevisionImpact] = []
        self._recertifications: list[TrainingRecertification] = []
        self._shop_floor_access: list[ShopFloorAccess] = []
        self._access_logs: list[DocumentAccess] = []
        self._plm_sync_records: list[PLMSyncRecord] = []
        self._watermarks: dict[str, ObsoleteWatermark] = {}
        
        # Impact rules - maps document type to affected entity types
        self._impact_rules: dict[DocumentType, list[ImpactType]] = {
            DocumentType.DRAWING: [
                ImpactType.STANDARD_WORK_UPDATE,
                ImpactType.INSPECTION_PLAN_UPDATE,
            ],
            DocumentType.BOM: [
                ImpactType.STANDARD_WORK_UPDATE,
                ImpactType.CTQ_UPDATE,
            ],
            DocumentType.ROUTING: [
                ImpactType.STANDARD_WORK_UPDATE,
                ImpactType.PROCESS_CHANGE,
            ],
            DocumentType.SPECIFICATION: [
                ImpactType.CTQ_UPDATE,
                ImpactType.INSPECTION_PLAN_UPDATE,
            ],
            DocumentType.WORK_INSTRUCTION: [
                ImpactType.TRAINING_RECERT,
            ],
            DocumentType.STANDARD_WORK: [
                ImpactType.TRAINING_RECERT,
            ],
        }
    
    # =========================================================================
    # DOCUMENT MANAGEMENT
    # =========================================================================
    
    def create_document(
        self,
        document_number: str,
        title: str,
        document_type: DocumentType,
        part_number: str | None = None,
        product_family: str | None = None,
        site_id: str | None = None,
        owner: str | None = None,
        plm_document_id: str | None = None,
    ) -> ControlledDocument:
        """Create a new controlled document."""
        doc_id = str(uuid4())
        
        document = ControlledDocument(
            id=doc_id,
            document_number=document_number,
            title=title,
            document_type=document_type,
            part_number=part_number,
            product_family=product_family,
            site_id=site_id,
            owner=owner,
            plm_document_id=plm_document_id,
        )
        
        self._documents[doc_id] = document
        logger.info(f"Created document: {document_number} ({document_type.value})")
        return document
    
    def get_document(self, document_id: str) -> ControlledDocument | None:
        """Get a document by ID."""
        return self._documents.get(document_id)
    
    def get_document_by_number(self, document_number: str) -> ControlledDocument | None:
        """Get a document by document number."""
        for doc in self._documents.values():
            if doc.document_number == document_number:
                return doc
        return None
    
    def get_documents_by_type(self, document_type: DocumentType) -> list[ControlledDocument]:
        """Get all documents of a specific type."""
        return [d for d in self._documents.values() if d.document_type == document_type]
    
    def get_documents_by_part(self, part_number: str) -> list[ControlledDocument]:
        """Get all documents for a part number."""
        return [d for d in self._documents.values() if d.part_number == part_number]
    
    def update_document(
        self,
        document_id: str,
        **kwargs,
    ) -> ControlledDocument | None:
        """Update a document."""
        document = self._documents.get(document_id)
        if not document:
            return None
        
        for key, value in kwargs.items():
            if hasattr(document, key):
                setattr(document, key, value)
        
        document.updated_at = datetime.now(timezone.utc)
        return document
    
    # =========================================================================
    # REVISION MANAGEMENT
    # =========================================================================
    
    def create_revision(
        self,
        document_id: str,
        content: bytes | str,
        created_by: str,
        file_path: str | None = None,
        file_type: str | None = None,
        change_type: ChangeType = ChangeType.MINOR,
        change_description: str | None = None,
        plm_revision_id: str | None = None,
    ) -> DocumentRevision | None:
        """Create a new revision for a document."""
        document = self._documents.get(document_id)
        if not document:
            logger.error(f"Document not found: {document_id}")
            return None
        
        # Get the latest revision number (from all revisions, not just released)
        doc_revisions = [r for r in self._revisions.values() if r.document_id == document_id]
        if doc_revisions:
            # Sort by version to get latest
            latest_rev = max(doc_revisions, key=lambda r: r.version)
            current_rev = latest_rev.revision_number
        else:
            current_rev = None
        
        # Generate revision number
        if self.revision_format == "alpha":
            new_rev = self._rev_generator.alpha(current_rev)
        elif self.revision_format == "numeric":
            new_rev = self._rev_generator.numeric(current_rev)
        elif self.revision_format == "semantic":
            new_rev = self._rev_generator.semantic(current_rev, change_type)
        else:
            new_rev = self._rev_generator.alpha(current_rev)
        
        # Calculate content hash
        if isinstance(content, str):
            content_bytes = content.encode()
        else:
            content_bytes = content
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # Get version number
        version = len(doc_revisions) + 1
        
        revision_id = str(uuid4())
        revision = DocumentRevision(
            id=revision_id,
            document_id=document_id,
            revision_number=new_rev,
            version=version,
            status=RevisionStatus.DRAFT,
            content_hash=content_hash,
            file_path=file_path,
            file_size=len(content_bytes),
            file_type=file_type,
            created_by=created_by,
            change_type=change_type,
            change_description=change_description,
            plm_revision_id=plm_revision_id,
        )
        
        self._revisions[revision_id] = revision
        
        # Link to previous revision
        if document.current_revision_id:
            link = RevisionLink(
                id=str(uuid4()),
                source_revision_id=revision_id,
                target_revision_id=document.current_revision_id,
                link_type="supersedes",
            )
            self._revision_links.append(link)
        
        logger.info(f"Created revision {new_rev} for document {document.document_number}")
        return revision
    
    def get_revision(self, revision_id: str) -> DocumentRevision | None:
        """Get a revision by ID."""
        return self._revisions.get(revision_id)
    
    def get_revisions_for_document(self, document_id: str) -> list[DocumentRevision]:
        """Get all revisions for a document."""
        revisions = [r for r in self._revisions.values() if r.document_id == document_id]
        return sorted(revisions, key=lambda r: r.version)
    
    def get_current_revision(self, document_id: str) -> DocumentRevision | None:
        """Get the current released revision for a document."""
        document = self._documents.get(document_id)
        if not document or not document.current_revision_id:
            return None
        return self._revisions.get(document.current_revision_id)
    
    def get_latest_released_revision(self, document_id: str) -> DocumentRevision | None:
        """Get the latest released revision for a document."""
        revisions = self.get_revisions_for_document(document_id)
        released = [r for r in revisions if r.status == RevisionStatus.RELEASED]
        return released[-1] if released else None
    
    def approve_revision(
        self,
        revision_id: str,
        approved_by: str,
    ) -> DocumentRevision | None:
        """Approve a revision (moves from draft/in_review to approved)."""
        revision = self._revisions.get(revision_id)
        if not revision:
            return None
        
        if revision.status not in (RevisionStatus.DRAFT, RevisionStatus.IN_REVIEW):
            logger.warning(f"Cannot approve revision in status: {revision.status}")
            return None
        
        revision.status = RevisionStatus.APPROVED
        revision.approved_by = approved_by
        revision.approved_at = datetime.now(timezone.utc)
        
        logger.info(f"Approved revision {revision.revision_number}")
        return revision
    
    def release_revision(
        self,
        revision_id: str,
        released_by: str | None = None,
    ) -> DocumentRevision | None:
        """Release a revision and make it current."""
        revision = self._revisions.get(revision_id)
        if not revision:
            return None
        
        if revision.status != RevisionStatus.APPROVED:
            logger.warning(f"Cannot release revision in status: {revision.status}")
            return None
        
        document = self._documents.get(revision.document_id)
        if not document:
            return None
        
        # Obsolete previous revision
        if document.current_revision_id:
            self.obsolete_revision(document.current_revision_id, "Superseded by new revision")
        
        # Release new revision
        revision.status = RevisionStatus.RELEASED
        revision.released_at = datetime.now(timezone.utc)
        
        # Update document
        document.current_revision_id = revision_id
        document.current_revision_number = revision.revision_number
        document.updated_at = datetime.now(timezone.utc)
        
        # Analyze impact
        self._analyze_revision_impact(revision)
        
        logger.info(f"Released revision {revision.revision_number} for {document.document_number}")
        return revision
    
    def obsolete_revision(
        self,
        revision_id: str,
        reason: str | None = None,
    ) -> DocumentRevision | None:
        """Mark a revision as obsolete."""
        revision = self._revisions.get(revision_id)
        if not revision:
            return None
        
        revision.status = RevisionStatus.OBSOLETE
        revision.obsoleted_at = datetime.now(timezone.utc)
        
        # Apply watermark
        self._apply_obsolete_watermark(revision_id)
        
        logger.info(f"Obsoleted revision {revision.revision_number}")
        return revision
    
    def _apply_obsolete_watermark(self, revision_id: str) -> ObsoleteWatermark:
        """Apply obsolete watermark to a revision."""
        revision = self._revisions.get(revision_id)
        
        watermark = ObsoleteWatermark(
            id=str(uuid4()),
            document_id=revision.document_id if revision else "",
            revision_id=revision_id,
            watermark_text="OBSOLETE",
            watermark_color="red",
            watermark_opacity=0.5,
        )
        
        self._watermarks[revision_id] = watermark
        return watermark
    
    def verify_revision_integrity(self, revision_id: str, content: bytes | str) -> bool:
        """Verify revision content matches stored hash."""
        revision = self._revisions.get(revision_id)
        if not revision:
            return False
        
        if isinstance(content, str):
            content_bytes = content.encode()
        else:
            content_bytes = content
        
        computed_hash = hashlib.sha256(content_bytes).hexdigest()
        return computed_hash == revision.content_hash
    
    # =========================================================================
    # IMPACT ANALYSIS
    # =========================================================================
    
    def _analyze_revision_impact(self, revision: DocumentRevision) -> list[RevisionImpact]:
        """Analyze the impact of a revision release."""
        impacts = []
        document = self._documents.get(revision.document_id)
        if not document:
            return impacts
        
        # Get impact rules for this document type
        impact_types = self._impact_rules.get(document.document_type, [])
        
        for impact_type in impact_types:
            impact = RevisionImpact(
                id=str(uuid4()),
                revision_id=revision.id,
                impact_type=impact_type,
                affected_entity_type=impact_type.value,
                affected_entity_id=f"{document.document_number}_{impact_type.value}",
                description=self._generate_impact_description(
                    document, revision, impact_type
                ),
                requires_action=True,
                action_due_date=datetime.now(timezone.utc) + timedelta(days=7),
            )
            impacts.append(impact)
            self._impacts.append(impact)
            
            # Trigger training re-certification if needed
            if impact_type == ImpactType.TRAINING_RECERT:
                self._trigger_training_recert(revision, document)
        
        logger.info(f"Identified {len(impacts)} impacts for revision {revision.revision_number}")
        return impacts
    
    def _generate_impact_description(
        self,
        document: ControlledDocument,
        revision: DocumentRevision,
        impact_type: ImpactType,
    ) -> str:
        """Generate impact description."""
        descriptions = {
            ImpactType.CTQ_UPDATE: f"CTQ requirements may need update due to {document.document_type.value} revision {revision.revision_number}",
            ImpactType.STANDARD_WORK_UPDATE: f"Standard work documents may need update due to {document.document_type.value} revision {revision.revision_number}",
            ImpactType.INSPECTION_PLAN_UPDATE: f"Inspection plans may need update due to {document.document_type.value} revision {revision.revision_number}",
            ImpactType.TRAINING_RECERT: f"Operator training re-certification required due to {document.document_type.value} revision {revision.revision_number}",
            ImpactType.TOOLING_CHANGE: f"Tooling changes may be required due to {document.document_type.value} revision {revision.revision_number}",
            ImpactType.PROCESS_CHANGE: f"Process changes may be required due to {document.document_type.value} revision {revision.revision_number}",
        }
        return descriptions.get(impact_type, f"Impact from {document.document_type.value} revision")
    
    def _trigger_training_recert(
        self,
        revision: DocumentRevision,
        document: ControlledDocument,
    ) -> list[TrainingRecertification]:
        """Trigger training re-certification for affected employees."""
        recerts = []
        
        # In a real implementation, this would query the training matrix
        # For now, we create placeholder recertifications
        if revision.change_type == ChangeType.CRITICAL:
            # Critical changes require immediate recertification
            due_date = datetime.now(timezone.utc) + timedelta(days=3)
        else:
            due_date = datetime.now(timezone.utc) + timedelta(days=14)
        
        recert = TrainingRecertification(
            id=str(uuid4()),
            revision_id=revision.id,
            employee_id="pending_assignment",
            skill_id=f"skill_{document.document_number}",
            skill_name=f"Operation per {document.document_number}",
            required_by=due_date,
        )
        
        recerts.append(recert)
        self._recertifications.append(recert)
        
        return recerts
    
    def get_pending_impacts(self, revision_id: str | None = None) -> list[RevisionImpact]:
        """Get pending (unresolved) revision impacts."""
        impacts = self._impacts
        if revision_id:
            impacts = [i for i in impacts if i.revision_id == revision_id]
        return [i for i in impacts if not i.resolved]
    
    def resolve_impact(
        self,
        impact_id: str,
        resolved_by: str,
    ) -> RevisionImpact | None:
        """Mark an impact as resolved."""
        for impact in self._impacts:
            if impact.id == impact_id:
                impact.resolved = True
                impact.resolved_by = resolved_by
                impact.resolved_at = datetime.now(timezone.utc)
                return impact
        return None
    
    def get_pending_recertifications(
        self,
        employee_id: str | None = None,
    ) -> list[TrainingRecertification]:
        """Get pending training re-certifications."""
        recerts = self._recertifications
        if employee_id:
            recerts = [r for r in recerts if r.employee_id == employee_id]
        return [r for r in recerts if r.status == "pending"]
    
    def complete_recertification(
        self,
        recert_id: str,
    ) -> TrainingRecertification | None:
        """Mark a re-certification as complete."""
        for recert in self._recertifications:
            if recert.id == recert_id:
                recert.status = "completed"
                recert.completed_at = datetime.now(timezone.utc)
                return recert
        return None
    
    # =========================================================================
    # SHOP FLOOR DISTRIBUTION
    # =========================================================================
    
    def grant_shop_floor_access(
        self,
        document_id: str,
        station_id: str | None = None,
        work_center_id: str | None = None,
        access_level: AccessLevel = AccessLevel.VIEW_ONLY,
        granted_by: str | None = None,
        expires_at: datetime | None = None,
    ) -> ShopFloorAccess | None:
        """Grant shop floor access to a document."""
        document = self._documents.get(document_id)
        if not document or not document.current_revision_id:
            return None
        
        access = ShopFloorAccess(
            id=str(uuid4()),
            document_id=document_id,
            revision_id=document.current_revision_id,
            station_id=station_id,
            work_center_id=work_center_id,
            access_level=access_level,
            granted_by=granted_by,
            expires_at=expires_at,
        )
        
        self._shop_floor_access.append(access)
        logger.info(f"Granted {access_level.value} access to document {document.document_number}")
        return access
    
    def revoke_shop_floor_access(self, access_id: str) -> bool:
        """Revoke shop floor access."""
        for access in self._shop_floor_access:
            if access.id == access_id:
                access.is_active = False
                return True
        return False
    
    def get_accessible_documents(
        self,
        station_id: str | None = None,
        work_center_id: str | None = None,
    ) -> list[tuple[ControlledDocument, DocumentRevision]]:
        """Get documents accessible from a station/work center."""
        result = []
        now = datetime.now(timezone.utc)
        
        for access in self._shop_floor_access:
            if not access.is_active:
                continue
            
            if access.expires_at and access.expires_at < now:
                continue
            
            if station_id and access.station_id != station_id:
                continue
            
            if work_center_id and access.work_center_id != work_center_id:
                continue
            
            document = self._documents.get(access.document_id)
            if not document:
                continue
            
            # Only return released revisions
            revision = self.get_latest_released_revision(access.document_id)
            if revision:
                result.append((document, revision))
        
        return result
    
    def check_access(
        self,
        document_id: str,
        station_id: str | None = None,
        work_center_id: str | None = None,
    ) -> AccessLevel | None:
        """Check access level for a document at a station/work center."""
        now = datetime.now(timezone.utc)
        
        for access in self._shop_floor_access:
            if access.document_id != document_id:
                continue
            
            if not access.is_active:
                continue
            
            if access.expires_at and access.expires_at < now:
                continue
            
            if station_id and access.station_id and access.station_id != station_id:
                continue
            
            if work_center_id and access.work_center_id and access.work_center_id != work_center_id:
                continue
            
            return access.access_level
        
        return None
    
    def log_document_access(
        self,
        document_id: str,
        revision_id: str,
        accessed_by: str,
        access_type: str,
        station_id: str | None = None,
        device_id: str | None = None,
        ip_address: str | None = None,
    ) -> DocumentAccess:
        """Log a document access event."""
        access_log = DocumentAccess(
            id=str(uuid4()),
            document_id=document_id,
            revision_id=revision_id,
            accessed_by=accessed_by,
            accessed_at=datetime.now(timezone.utc),
            station_id=station_id,
            device_id=device_id,
            access_type=access_type,
            ip_address=ip_address,
        )
        
        self._access_logs.append(access_log)
        return access_log
    
    def get_access_logs(
        self,
        document_id: str | None = None,
        accessed_by: str | None = None,
        since: datetime | None = None,
    ) -> list[DocumentAccess]:
        """Get document access logs."""
        logs = self._access_logs
        
        if document_id:
            logs = [l for l in logs if l.document_id == document_id]
        
        if accessed_by:
            logs = [l for l in logs if l.accessed_by == accessed_by]
        
        if since:
            logs = [l for l in logs if l.accessed_at >= since]
        
        return sorted(logs, key=lambda l: l.accessed_at, reverse=True)
    
    # =========================================================================
    # PLM SYNCHRONIZATION
    # =========================================================================
    
    def sync_from_plm(
        self,
        plm_document_id: str,
        plm_revision_id: str,
        content: bytes | str,
        metadata: dict[str, Any],
    ) -> PLMSyncRecord:
        """Sync a document revision from PLM."""
        # Find or create document
        document = None
        for doc in self._documents.values():
            if doc.plm_document_id == plm_document_id:
                document = doc
                break
        
        if not document:
            # Create new document
            document = self.create_document(
                document_number=metadata.get("document_number", plm_document_id),
                title=metadata.get("title", "Imported from PLM"),
                document_type=DocumentType(metadata.get("document_type", "drawing")),
                plm_document_id=plm_document_id,
            )
        
        revision_before = document.current_revision_number
        
        # Create revision
        revision = self.create_revision(
            document_id=document.id,
            content=content,
            created_by=metadata.get("created_by", "PLM_SYNC"),
            plm_revision_id=plm_revision_id,
            change_description="Imported from PLM",
        )
        
        sync_status = "success" if revision else "failed"
        
        sync_record = PLMSyncRecord(
            id=str(uuid4()),
            document_id=document.id,
            plm_document_id=plm_document_id,
            sync_direction="inbound",
            sync_status=sync_status,
            synced_at=datetime.now(timezone.utc),
            revision_before=revision_before,
            revision_after=revision.revision_number if revision else None,
        )
        
        self._plm_sync_records.append(sync_record)
        return sync_record
    
    def sync_to_plm(
        self,
        document_id: str,
        revision_id: str,
    ) -> PLMSyncRecord:
        """Sync a document revision to PLM."""
        document = self._documents.get(document_id)
        revision = self._revisions.get(revision_id)
        
        sync_record = PLMSyncRecord(
            id=str(uuid4()),
            document_id=document_id,
            plm_document_id=document.plm_document_id if document else "",
            sync_direction="outbound",
            sync_status="success",  # Would be actual result in real implementation
            synced_at=datetime.now(timezone.utc),
            revision_before=None,
            revision_after=revision.revision_number if revision else None,
        )
        
        self._plm_sync_records.append(sync_record)
        return sync_record
    
    def get_plm_sync_history(
        self,
        document_id: str | None = None,
    ) -> list[PLMSyncRecord]:
        """Get PLM sync history."""
        records = self._plm_sync_records
        if document_id:
            records = [r for r in records if r.document_id == document_id]
        return sorted(records, key=lambda r: r.synced_at, reverse=True)
    
    # =========================================================================
    # REVISION COMPARISON
    # =========================================================================
    
    def compare_revisions(
        self,
        revision_id_a: str,
        revision_id_b: str,
    ) -> dict[str, Any]:
        """Compare two revisions of a document."""
        rev_a = self._revisions.get(revision_id_a)
        rev_b = self._revisions.get(revision_id_b)
        
        if not rev_a or not rev_b:
            return {"error": "One or both revisions not found"}
        
        if rev_a.document_id != rev_b.document_id:
            return {"error": "Revisions are from different documents"}
        
        return {
            "revision_a": {
                "id": rev_a.id,
                "number": rev_a.revision_number,
                "version": rev_a.version,
                "status": rev_a.status.value,
                "hash": rev_a.content_hash,
                "created_at": rev_a.created_at.isoformat(),
            },
            "revision_b": {
                "id": rev_b.id,
                "number": rev_b.revision_number,
                "version": rev_b.version,
                "status": rev_b.status.value,
                "hash": rev_b.content_hash,
                "created_at": rev_b.created_at.isoformat(),
            },
            "content_changed": rev_a.content_hash != rev_b.content_hash,
            "version_difference": rev_b.version - rev_a.version,
        }
    
    # =========================================================================
    # SEARCH & QUERY
    # =========================================================================
    
    def search_documents(
        self,
        query: str,
        document_type: DocumentType | None = None,
        part_number: str | None = None,
        status: RevisionStatus | None = None,
    ) -> list[ControlledDocument]:
        """Search for documents."""
        results = []
        query_lower = query.lower()
        
        for doc in self._documents.values():
            if not doc.is_active:
                continue
            
            if document_type and doc.document_type != document_type:
                continue
            
            if part_number and doc.part_number != part_number:
                continue
            
            # Check if current revision matches status
            if status:
                current_rev = self.get_current_revision(doc.id)
                if not current_rev or current_rev.status != status:
                    continue
            
            # Search in document number and title
            if (
                query_lower in doc.document_number.lower()
                or query_lower in doc.title.lower()
            ):
                results.append(doc)
        
        return results
    
    # =========================================================================
    # STATISTICS & REPORTING
    # =========================================================================
    
    def get_document_statistics(self) -> dict[str, Any]:
        """Get document statistics."""
        docs = list(self._documents.values())
        revisions = list(self._revisions.values())
        
        by_type = {}
        for doc in docs:
            doc_type = doc.document_type.value
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
        
        by_status = {}
        for rev in revisions:
            status = rev.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_documents": len(docs),
            "total_revisions": len(revisions),
            "by_document_type": by_type,
            "by_revision_status": by_status,
            "pending_impacts": len(self.get_pending_impacts()),
            "pending_recertifications": len(self.get_pending_recertifications()),
            "active_shop_floor_access": len([a for a in self._shop_floor_access if a.is_active]),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_plm_drawing_control_service(
    plm_system: PLMSystem | None = None,
    revision_format: str = "alpha",
) -> PLMDrawingControlService:
    """Factory function to create a PLM Drawing Control service."""
    return PLMDrawingControlService(
        plm_system=plm_system,
        revision_format=revision_format,
    )
