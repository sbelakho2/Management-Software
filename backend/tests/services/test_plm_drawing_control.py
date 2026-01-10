"""
Tests for PLM Drawing Control Service.

Tests:
- Document management
- Revision management (create, approve, release, obsolete)
- Immutable hash verification
- Impact analysis
- Training re-certification triggers
- Shop floor distribution
- PLM synchronization
- Search and statistics
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from sensei.services.plm_drawing_control import (
    # Enums
    RevisionStatus,
    DocumentType,
    ChangeType,
    ImpactType,
    AccessLevel,
    PLMSystem,
    # Data models
    DocumentRevision,
    ControlledDocument,
    RevisionLink,
    RevisionImpact,
    TrainingRecertification,
    ShopFloorAccess,
    DocumentAccess,
    PLMSyncRecord,
    ObsoleteWatermark,
    # Helper classes
    RevisionNumberGenerator,
    # Service
    PLMDrawingControlService,
    create_plm_drawing_control_service,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def service():
    """Create a PLM Drawing Control service."""
    return create_plm_drawing_control_service()


@pytest.fixture
def sample_document(service):
    """Create a sample document."""
    return service.create_document(
        document_number="DWG-001",
        title="Main Assembly Drawing",
        document_type=DocumentType.DRAWING,
        part_number="PART-001",
        product_family="Product A",
        owner="John Doe",
    )


@pytest.fixture
def sample_revision(service, sample_document):
    """Create a sample revision."""
    return service.create_revision(
        document_id=sample_document.id,
        content="Drawing content version A",
        created_by="engineer@company.com",
        file_type="pdf",
        change_type=ChangeType.MINOR,
        change_description="Initial drawing release",
    )


# =============================================================================
# TEST ENUMS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_revision_status_values(self):
        """Test revision status enum values."""
        assert RevisionStatus.DRAFT.value == "draft"
        assert RevisionStatus.IN_REVIEW.value == "in_review"
        assert RevisionStatus.APPROVED.value == "approved"
        assert RevisionStatus.RELEASED.value == "released"
        assert RevisionStatus.OBSOLETE.value == "obsolete"
    
    def test_document_type_values(self):
        """Test document type enum values."""
        assert DocumentType.DRAWING.value == "drawing"
        assert DocumentType.BOM.value == "bom"
        assert DocumentType.WORK_INSTRUCTION.value == "work_instruction"
        assert DocumentType.STANDARD_WORK.value == "standard_work"
    
    def test_change_type_values(self):
        """Test change type enum values."""
        assert ChangeType.MINOR.value == "minor"
        assert ChangeType.MAJOR.value == "major"
        assert ChangeType.CRITICAL.value == "critical"
    
    def test_impact_type_values(self):
        """Test impact type enum values."""
        assert ImpactType.CTQ_UPDATE.value == "ctq_update"
        assert ImpactType.TRAINING_RECERT.value == "training_recert"
    
    def test_access_level_values(self):
        """Test access level enum values."""
        assert AccessLevel.VIEW_ONLY.value == "view_only"
        assert AccessLevel.PRINT.value == "print"
        assert AccessLevel.DOWNLOAD.value == "download"


# =============================================================================
# TEST DATA MODELS
# =============================================================================


class TestDataModels:
    """Test data model classes."""
    
    def test_document_revision_creation(self):
        """Test DocumentRevision creation."""
        revision = DocumentRevision(
            id="rev-001",
            document_id="doc-001",
            revision_number="A",
            version=1,
            status=RevisionStatus.DRAFT,
            content_hash="abc123",
        )
        
        assert revision.id == "rev-001"
        assert revision.document_id == "doc-001"
        assert revision.revision_number == "A"
        assert revision.version == 1
        assert revision.status == RevisionStatus.DRAFT
    
    def test_controlled_document_creation(self):
        """Test ControlledDocument creation."""
        doc = ControlledDocument(
            id="doc-001",
            document_number="DWG-001",
            title="Test Drawing",
            document_type=DocumentType.DRAWING,
        )
        
        assert doc.id == "doc-001"
        assert doc.document_number == "DWG-001"
        assert doc.title == "Test Drawing"
        assert doc.is_active is True
    
    def test_revision_impact_creation(self):
        """Test RevisionImpact creation."""
        impact = RevisionImpact(
            id="impact-001",
            revision_id="rev-001",
            impact_type=ImpactType.TRAINING_RECERT,
            affected_entity_type="training",
            affected_entity_id="skill-001",
            description="Training required",
        )
        
        assert impact.id == "impact-001"
        assert impact.requires_action is True
        assert impact.resolved is False
    
    def test_shop_floor_access_creation(self):
        """Test ShopFloorAccess creation."""
        access = ShopFloorAccess(
            id="access-001",
            document_id="doc-001",
            revision_id="rev-001",
            station_id="station-001",
            access_level=AccessLevel.VIEW_ONLY,
        )
        
        assert access.id == "access-001"
        assert access.is_active is True
    
    def test_obsolete_watermark_creation(self):
        """Test ObsoleteWatermark creation."""
        watermark = ObsoleteWatermark(
            id="wm-001",
            document_id="doc-001",
            revision_id="rev-001",
        )
        
        assert watermark.watermark_text == "OBSOLETE"
        assert watermark.watermark_color == "red"
        assert watermark.watermark_opacity == 0.5


# =============================================================================
# TEST REVISION NUMBER GENERATOR
# =============================================================================


class TestRevisionNumberGenerator:
    """Test revision number generation."""
    
    def test_alpha_first_revision(self):
        """Test first alpha revision."""
        result = RevisionNumberGenerator.alpha(None)
        assert result == "A"
    
    def test_alpha_increment(self):
        """Test alpha revision increment."""
        assert RevisionNumberGenerator.alpha("A") == "B"
        assert RevisionNumberGenerator.alpha("B") == "C"
        assert RevisionNumberGenerator.alpha("Y") == "Z"
    
    def test_alpha_rollover(self):
        """Test alpha revision rollover from Z to AA."""
        assert RevisionNumberGenerator.alpha("Z") == "AA"
        assert RevisionNumberGenerator.alpha("AA") == "AB"
        assert RevisionNumberGenerator.alpha("AZ") == "BA"
    
    def test_numeric_first_revision(self):
        """Test first numeric revision."""
        result = RevisionNumberGenerator.numeric(None)
        assert result == "1"
    
    def test_numeric_increment(self):
        """Test numeric revision increment."""
        assert RevisionNumberGenerator.numeric("1") == "2"
        assert RevisionNumberGenerator.numeric("10") == "11"
        assert RevisionNumberGenerator.numeric("99") == "100"
    
    def test_semantic_first_revision(self):
        """Test first semantic revision."""
        result = RevisionNumberGenerator.semantic(None)
        assert result == "1.0.0"
    
    def test_semantic_minor_change(self):
        """Test semantic revision minor change."""
        result = RevisionNumberGenerator.semantic("1.0.0", ChangeType.MINOR)
        assert result == "1.0.1"
    
    def test_semantic_major_change(self):
        """Test semantic revision major change."""
        result = RevisionNumberGenerator.semantic("1.0.1", ChangeType.MAJOR)
        assert result == "1.1.0"
    
    def test_semantic_critical_change(self):
        """Test semantic revision critical change."""
        result = RevisionNumberGenerator.semantic("1.1.0", ChangeType.CRITICAL)
        assert result == "2.0.0"
    
    def test_dated_revision(self):
        """Test dated revision generation."""
        result = RevisionNumberGenerator.dated("REV")
        assert result.startswith("REV-")
        assert len(result) == 16  # REV-YYYYMMDD-001


# =============================================================================
# TEST DOCUMENT MANAGEMENT
# =============================================================================


class TestDocumentManagement:
    """Test document management operations."""
    
    def test_create_document(self, service):
        """Test creating a document."""
        doc = service.create_document(
            document_number="DWG-001",
            title="Main Assembly Drawing",
            document_type=DocumentType.DRAWING,
            part_number="PART-001",
        )
        
        assert doc is not None
        assert doc.document_number == "DWG-001"
        assert doc.document_type == DocumentType.DRAWING
        assert doc.is_active is True
    
    def test_get_document(self, service, sample_document):
        """Test getting a document by ID."""
        retrieved = service.get_document(sample_document.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_document.id
        assert retrieved.document_number == sample_document.document_number
    
    def test_get_document_not_found(self, service):
        """Test getting a non-existent document."""
        result = service.get_document("non-existent")
        assert result is None
    
    def test_get_document_by_number(self, service, sample_document):
        """Test getting a document by document number."""
        retrieved = service.get_document_by_number("DWG-001")
        
        assert retrieved is not None
        assert retrieved.id == sample_document.id
    
    def test_get_documents_by_type(self, service):
        """Test getting documents by type."""
        service.create_document("DWG-001", "Drawing 1", DocumentType.DRAWING)
        service.create_document("DWG-002", "Drawing 2", DocumentType.DRAWING)
        service.create_document("BOM-001", "BOM 1", DocumentType.BOM)
        
        drawings = service.get_documents_by_type(DocumentType.DRAWING)
        boms = service.get_documents_by_type(DocumentType.BOM)
        
        assert len(drawings) == 2
        assert len(boms) == 1
    
    def test_get_documents_by_part(self, service):
        """Test getting documents by part number."""
        service.create_document("DWG-001", "Drawing 1", DocumentType.DRAWING, part_number="PART-A")
        service.create_document("BOM-001", "BOM 1", DocumentType.BOM, part_number="PART-A")
        service.create_document("DWG-002", "Drawing 2", DocumentType.DRAWING, part_number="PART-B")
        
        part_a_docs = service.get_documents_by_part("PART-A")
        
        assert len(part_a_docs) == 2
    
    def test_update_document(self, service, sample_document):
        """Test updating a document."""
        updated = service.update_document(
            sample_document.id,
            title="Updated Title",
            owner="Jane Doe",
        )
        
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.owner == "Jane Doe"


# =============================================================================
# TEST REVISION MANAGEMENT
# =============================================================================


class TestRevisionManagement:
    """Test revision management operations."""
    
    def test_create_revision(self, service, sample_document):
        """Test creating a revision."""
        revision = service.create_revision(
            document_id=sample_document.id,
            content="Drawing content",
            created_by="engineer@company.com",
            change_type=ChangeType.MINOR,
        )
        
        assert revision is not None
        assert revision.revision_number == "A"
        assert revision.version == 1
        assert revision.status == RevisionStatus.DRAFT
    
    def test_create_second_revision(self, service, sample_document):
        """Test creating a second revision."""
        service.create_revision(
            document_id=sample_document.id,
            content="Content A",
            created_by="engineer@company.com",
        )
        
        revision = service.create_revision(
            document_id=sample_document.id,
            content="Content B",
            created_by="engineer@company.com",
        )
        
        assert revision.revision_number == "B"
        assert revision.version == 2
    
    def test_create_revision_invalid_document(self, service):
        """Test creating a revision for invalid document."""
        result = service.create_revision(
            document_id="non-existent",
            content="Content",
            created_by="engineer@company.com",
        )
        
        assert result is None
    
    def test_get_revision(self, service, sample_revision):
        """Test getting a revision by ID."""
        retrieved = service.get_revision(sample_revision.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_revision.id
    
    def test_get_revisions_for_document(self, service, sample_document):
        """Test getting all revisions for a document."""
        service.create_revision(sample_document.id, "Content A", "user")
        service.create_revision(sample_document.id, "Content B", "user")
        service.create_revision(sample_document.id, "Content C", "user")
        
        revisions = service.get_revisions_for_document(sample_document.id)
        
        assert len(revisions) == 3
        assert revisions[0].revision_number == "A"
        assert revisions[2].revision_number == "C"
    
    def test_approve_revision(self, service, sample_revision):
        """Test approving a revision."""
        approved = service.approve_revision(
            sample_revision.id,
            approved_by="manager@company.com",
        )
        
        assert approved is not None
        assert approved.status == RevisionStatus.APPROVED
        assert approved.approved_by == "manager@company.com"
        assert approved.approved_at is not None
    
    def test_approve_revision_invalid_status(self, service, sample_revision):
        """Test approving already released revision."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        # Try to approve a released revision
        result = service.approve_revision(sample_revision.id, "manager")
        assert result is None
    
    def test_release_revision(self, service, sample_document, sample_revision):
        """Test releasing a revision."""
        service.approve_revision(sample_revision.id, "manager")
        
        released = service.release_revision(sample_revision.id)
        
        assert released is not None
        assert released.status == RevisionStatus.RELEASED
        assert released.released_at is not None
        
        # Check document is updated
        doc = service.get_document(sample_document.id)
        assert doc.current_revision_id == sample_revision.id
        assert doc.current_revision_number == "A"
    
    def test_release_unapproved_revision(self, service, sample_revision):
        """Test releasing an unapproved revision."""
        result = service.release_revision(sample_revision.id)
        assert result is None
    
    def test_obsolete_revision(self, service, sample_revision):
        """Test obsoleting a revision."""
        obsoleted = service.obsolete_revision(sample_revision.id)
        
        assert obsoleted is not None
        assert obsoleted.status == RevisionStatus.OBSOLETE
        assert obsoleted.obsoleted_at is not None
    
    def test_supersede_previous_revision(self, service, sample_document):
        """Test that releasing new revision obsoletes previous."""
        rev_a = service.create_revision(sample_document.id, "Content A", "user")
        service.approve_revision(rev_a.id, "manager")
        service.release_revision(rev_a.id)
        
        rev_b = service.create_revision(sample_document.id, "Content B", "user")
        service.approve_revision(rev_b.id, "manager")
        service.release_revision(rev_b.id)
        
        # Previous revision should be obsolete
        rev_a_updated = service.get_revision(rev_a.id)
        assert rev_a_updated.status == RevisionStatus.OBSOLETE
    
    def test_get_latest_released_revision(self, service, sample_document):
        """Test getting latest released revision."""
        rev_a = service.create_revision(sample_document.id, "Content A", "user")
        service.approve_revision(rev_a.id, "manager")
        service.release_revision(rev_a.id)
        
        rev_b = service.create_revision(sample_document.id, "Content B", "user")
        service.approve_revision(rev_b.id, "manager")
        service.release_revision(rev_b.id)
        
        latest = service.get_latest_released_revision(sample_document.id)
        
        assert latest is not None
        assert latest.revision_number == "B"


# =============================================================================
# TEST HASH VERIFICATION
# =============================================================================


class TestHashVerification:
    """Test immutable hash verification."""
    
    def test_content_hash_generated(self, service, sample_revision):
        """Test that content hash is generated."""
        assert sample_revision.content_hash is not None
        assert len(sample_revision.content_hash) == 64  # SHA-256
    
    def test_verify_revision_integrity_valid(self, service, sample_document):
        """Test verifying valid revision content."""
        content = "Drawing content"
        revision = service.create_revision(
            sample_document.id, content, "user"
        )
        
        is_valid = service.verify_revision_integrity(revision.id, content)
        assert is_valid is True
    
    def test_verify_revision_integrity_invalid(self, service, sample_document):
        """Test verifying tampered revision content."""
        content = "Original content"
        revision = service.create_revision(
            sample_document.id, content, "user"
        )
        
        is_valid = service.verify_revision_integrity(revision.id, "Tampered content")
        assert is_valid is False
    
    def test_verify_revision_integrity_bytes(self, service, sample_document):
        """Test verifying binary content."""
        content = b"\x89PNG\r\n\x1a\n"
        revision = service.create_revision(
            sample_document.id, content, "user"
        )
        
        is_valid = service.verify_revision_integrity(revision.id, content)
        assert is_valid is True


# =============================================================================
# TEST IMPACT ANALYSIS
# =============================================================================


class TestImpactAnalysis:
    """Test revision impact analysis."""
    
    def test_drawing_revision_creates_impacts(self, service):
        """Test that drawing revision creates impacts."""
        doc = service.create_document("DWG-001", "Drawing", DocumentType.DRAWING)
        rev = service.create_revision(doc.id, "Content", "user")
        service.approve_revision(rev.id, "manager")
        service.release_revision(rev.id)
        
        impacts = service.get_pending_impacts(rev.id)
        
        # Drawing should create standard work and inspection plan impacts
        assert len(impacts) >= 2
        impact_types = [i.impact_type for i in impacts]
        assert ImpactType.STANDARD_WORK_UPDATE in impact_types
        assert ImpactType.INSPECTION_PLAN_UPDATE in impact_types
    
    def test_work_instruction_triggers_recert(self, service):
        """Test that work instruction revision triggers re-certification."""
        doc = service.create_document("WI-001", "Work Instruction", DocumentType.WORK_INSTRUCTION)
        rev = service.create_revision(doc.id, "Content", "user")
        service.approve_revision(rev.id, "manager")
        service.release_revision(rev.id)
        
        impacts = service.get_pending_impacts(rev.id)
        impact_types = [i.impact_type for i in impacts]
        
        assert ImpactType.TRAINING_RECERT in impact_types
    
    def test_resolve_impact(self, service, sample_document):
        """Test resolving an impact."""
        rev = service.create_revision(sample_document.id, "Content", "user")
        service.approve_revision(rev.id, "manager")
        service.release_revision(rev.id)
        
        impacts = service.get_pending_impacts(rev.id)
        if impacts:
            resolved = service.resolve_impact(impacts[0].id, "qa_manager")
            
            assert resolved is not None
            assert resolved.resolved is True
            assert resolved.resolved_by == "qa_manager"
    
    def test_get_pending_recertifications(self, service):
        """Test getting pending re-certifications."""
        doc = service.create_document("WI-001", "Work Instruction", DocumentType.WORK_INSTRUCTION)
        rev = service.create_revision(doc.id, "Content", "user")
        service.approve_revision(rev.id, "manager")
        service.release_revision(rev.id)
        
        recerts = service.get_pending_recertifications()
        
        assert len(recerts) >= 1
        assert recerts[0].status == "pending"
    
    def test_complete_recertification(self, service):
        """Test completing a re-certification."""
        doc = service.create_document("WI-001", "Work Instruction", DocumentType.WORK_INSTRUCTION)
        rev = service.create_revision(doc.id, "Content", "user")
        service.approve_revision(rev.id, "manager")
        service.release_revision(rev.id)
        
        recerts = service.get_pending_recertifications()
        if recerts:
            completed = service.complete_recertification(recerts[0].id)
            
            assert completed is not None
            assert completed.status == "completed"
            assert completed.completed_at is not None


# =============================================================================
# TEST SHOP FLOOR DISTRIBUTION
# =============================================================================


class TestShopFloorDistribution:
    """Test shop floor document distribution."""
    
    def test_grant_access(self, service, sample_document, sample_revision):
        """Test granting shop floor access."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        access = service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
            access_level=AccessLevel.VIEW_ONLY,
            granted_by="admin",
        )
        
        assert access is not None
        assert access.station_id == "station-001"
        assert access.access_level == AccessLevel.VIEW_ONLY
        assert access.is_active is True
    
    def test_grant_access_no_released_revision(self, service, sample_document):
        """Test granting access when no released revision exists."""
        access = service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
        )
        
        assert access is None
    
    def test_revoke_access(self, service, sample_document, sample_revision):
        """Test revoking shop floor access."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        access = service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
        )
        
        result = service.revoke_shop_floor_access(access.id)
        
        assert result is True
    
    def test_get_accessible_documents(self, service, sample_document, sample_revision):
        """Test getting accessible documents for a station."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
        )
        
        accessible = service.get_accessible_documents(station_id="station-001")
        
        assert len(accessible) == 1
        doc, rev = accessible[0]
        assert doc.id == sample_document.id
        assert rev.status == RevisionStatus.RELEASED
    
    def test_check_access(self, service, sample_document, sample_revision):
        """Test checking access level."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
            access_level=AccessLevel.PRINT,
        )
        
        access_level = service.check_access(
            document_id=sample_document.id,
            station_id="station-001",
        )
        
        assert access_level == AccessLevel.PRINT
    
    def test_check_access_no_access(self, service, sample_document):
        """Test checking access when none granted."""
        access_level = service.check_access(
            document_id=sample_document.id,
            station_id="station-001",
        )
        
        assert access_level is None
    
    def test_log_document_access(self, service, sample_document, sample_revision):
        """Test logging document access."""
        log = service.log_document_access(
            document_id=sample_document.id,
            revision_id=sample_revision.id,
            accessed_by="operator@company.com",
            access_type="view",
            station_id="station-001",
        )
        
        assert log is not None
        assert log.accessed_by == "operator@company.com"
        assert log.access_type == "view"
    
    def test_get_access_logs(self, service, sample_document, sample_revision):
        """Test getting access logs."""
        service.log_document_access(
            sample_document.id, sample_revision.id, "user1", "view"
        )
        service.log_document_access(
            sample_document.id, sample_revision.id, "user2", "print"
        )
        
        logs = service.get_access_logs(document_id=sample_document.id)
        
        assert len(logs) == 2
    
    def test_get_access_logs_by_user(self, service, sample_document, sample_revision):
        """Test getting access logs by user."""
        service.log_document_access(
            sample_document.id, sample_revision.id, "user1", "view"
        )
        service.log_document_access(
            sample_document.id, sample_revision.id, "user2", "print"
        )
        
        logs = service.get_access_logs(accessed_by="user1")
        
        assert len(logs) == 1
        assert logs[0].accessed_by == "user1"


# =============================================================================
# TEST PLM SYNCHRONIZATION
# =============================================================================


class TestPLMSynchronization:
    """Test PLM synchronization operations."""
    
    def test_sync_from_plm_new_document(self, service):
        """Test syncing a new document from PLM."""
        sync_record = service.sync_from_plm(
            plm_document_id="PLM-DOC-001",
            plm_revision_id="PLM-REV-001",
            content="Drawing content from PLM",
            metadata={
                "document_number": "DWG-001",
                "title": "Drawing from PLM",
                "document_type": "drawing",
                "created_by": "plm_user",
            },
        )
        
        assert sync_record is not None
        assert sync_record.sync_direction == "inbound"
        assert sync_record.sync_status == "success"
        assert sync_record.revision_after == "A"
    
    def test_sync_from_plm_existing_document(self, service):
        """Test syncing to existing document from PLM."""
        # First sync
        service.sync_from_plm(
            plm_document_id="PLM-DOC-001",
            plm_revision_id="PLM-REV-001",
            content="Content A",
            metadata={"document_number": "DWG-001", "title": "Drawing"},
        )
        
        # Second sync
        sync_record = service.sync_from_plm(
            plm_document_id="PLM-DOC-001",
            plm_revision_id="PLM-REV-002",
            content="Content B",
            metadata={"document_number": "DWG-001", "title": "Drawing"},
        )
        
        assert sync_record.revision_after == "B"
    
    def test_sync_to_plm(self, service, sample_document, sample_revision):
        """Test syncing to PLM."""
        sync_record = service.sync_to_plm(
            document_id=sample_document.id,
            revision_id=sample_revision.id,
        )
        
        assert sync_record is not None
        assert sync_record.sync_direction == "outbound"
        assert sync_record.sync_status == "success"
    
    def test_get_plm_sync_history(self, service, sample_document, sample_revision):
        """Test getting PLM sync history."""
        service.sync_to_plm(sample_document.id, sample_revision.id)
        service.sync_to_plm(sample_document.id, sample_revision.id)
        
        history = service.get_plm_sync_history(sample_document.id)
        
        assert len(history) == 2


# =============================================================================
# TEST REVISION COMPARISON
# =============================================================================


class TestRevisionComparison:
    """Test revision comparison operations."""
    
    def test_compare_revisions(self, service, sample_document):
        """Test comparing two revisions."""
        rev_a = service.create_revision(sample_document.id, "Content A", "user")
        rev_b = service.create_revision(sample_document.id, "Content B", "user")
        
        comparison = service.compare_revisions(rev_a.id, rev_b.id)
        
        assert comparison["revision_a"]["number"] == "A"
        assert comparison["revision_b"]["number"] == "B"
        assert comparison["content_changed"] is True
        assert comparison["version_difference"] == 1
    
    def test_compare_same_content(self, service, sample_document):
        """Test comparing revisions with same content."""
        rev_a = service.create_revision(sample_document.id, "Same content", "user")
        rev_b = service.create_revision(sample_document.id, "Same content", "user")
        
        comparison = service.compare_revisions(rev_a.id, rev_b.id)
        
        assert comparison["content_changed"] is False
    
    def test_compare_invalid_revision(self, service, sample_revision):
        """Test comparing with invalid revision."""
        comparison = service.compare_revisions(sample_revision.id, "non-existent")
        
        assert "error" in comparison
    
    def test_compare_different_documents(self, service):
        """Test comparing revisions from different documents."""
        doc1 = service.create_document("DWG-001", "Drawing 1", DocumentType.DRAWING)
        doc2 = service.create_document("DWG-002", "Drawing 2", DocumentType.DRAWING)
        
        rev1 = service.create_revision(doc1.id, "Content 1", "user")
        rev2 = service.create_revision(doc2.id, "Content 2", "user")
        
        comparison = service.compare_revisions(rev1.id, rev2.id)
        
        assert "error" in comparison


# =============================================================================
# TEST SEARCH
# =============================================================================


class TestSearch:
    """Test search operations."""
    
    def test_search_by_query(self, service):
        """Test searching documents by query."""
        service.create_document("DWG-001", "Main Assembly Drawing", DocumentType.DRAWING)
        service.create_document("DWG-002", "Sub Assembly Drawing", DocumentType.DRAWING)
        service.create_document("BOM-001", "Bill of Materials", DocumentType.BOM)
        
        results = service.search_documents("Assembly")
        
        assert len(results) == 2
    
    def test_search_by_document_number(self, service):
        """Test searching by document number."""
        service.create_document("DWG-001", "Drawing 1", DocumentType.DRAWING)
        service.create_document("DWG-002", "Drawing 2", DocumentType.DRAWING)
        
        results = service.search_documents("DWG-001")
        
        assert len(results) == 1
        assert results[0].document_number == "DWG-001"
    
    def test_search_with_type_filter(self, service):
        """Test searching with document type filter."""
        service.create_document("DWG-001", "Test Drawing", DocumentType.DRAWING)
        service.create_document("BOM-001", "Test BOM", DocumentType.BOM)
        
        results = service.search_documents("Test", document_type=DocumentType.DRAWING)
        
        assert len(results) == 1
        assert results[0].document_type == DocumentType.DRAWING
    
    def test_search_case_insensitive(self, service):
        """Test that search is case insensitive."""
        service.create_document("DWG-001", "ASSEMBLY DRAWING", DocumentType.DRAWING)
        
        results = service.search_documents("assembly")
        
        assert len(results) == 1


# =============================================================================
# TEST STATISTICS
# =============================================================================


class TestStatistics:
    """Test statistics operations."""
    
    def test_get_document_statistics(self, service):
        """Test getting document statistics."""
        service.create_document("DWG-001", "Drawing 1", DocumentType.DRAWING)
        service.create_document("DWG-002", "Drawing 2", DocumentType.DRAWING)
        service.create_document("BOM-001", "BOM 1", DocumentType.BOM)
        
        stats = service.get_document_statistics()
        
        assert stats["total_documents"] == 3
        assert stats["by_document_type"]["drawing"] == 2
        assert stats["by_document_type"]["bom"] == 1
    
    def test_statistics_include_revisions(self, service, sample_document):
        """Test that statistics include revision counts."""
        service.create_revision(sample_document.id, "Content A", "user")
        service.create_revision(sample_document.id, "Content B", "user")
        
        stats = service.get_document_statistics()
        
        assert stats["total_revisions"] == 2


# =============================================================================
# TEST FACTORY FUNCTION
# =============================================================================


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_service_default(self):
        """Test creating service with defaults."""
        service = create_plm_drawing_control_service()
        
        assert service is not None
        assert service.revision_format == "alpha"
    
    def test_create_service_with_plm(self):
        """Test creating service with PLM system."""
        service = create_plm_drawing_control_service(
            plm_system=PLMSystem.TEAMCENTER,
            revision_format="semantic",
        )
        
        assert service.plm_system == PLMSystem.TEAMCENTER
        assert service.revision_format == "semantic"
    
    def test_semantic_revision_format(self):
        """Test service with semantic revision format."""
        service = create_plm_drawing_control_service(revision_format="semantic")
        
        doc = service.create_document("DWG-001", "Drawing", DocumentType.DRAWING)
        rev = service.create_revision(doc.id, "Content", "user")
        
        assert rev.revision_number == "1.0.0"
    
    def test_numeric_revision_format(self):
        """Test service with numeric revision format."""
        service = create_plm_drawing_control_service(revision_format="numeric")
        
        doc = service.create_document("DWG-001", "Drawing", DocumentType.DRAWING)
        rev = service.create_revision(doc.id, "Content", "user")
        
        assert rev.revision_number == "1"


# =============================================================================
# TEST WATERMARKS
# =============================================================================


class TestWatermarks:
    """Test obsolete watermark functionality."""
    
    def test_watermark_applied_on_obsolete(self, service, sample_revision):
        """Test that watermark is applied when revision is obsoleted."""
        service.obsolete_revision(sample_revision.id)
        
        assert sample_revision.id in service._watermarks
        watermark = service._watermarks[sample_revision.id]
        assert watermark.watermark_text == "OBSOLETE"
    
    def test_watermark_properties(self, service, sample_revision):
        """Test watermark has correct properties."""
        service.obsolete_revision(sample_revision.id)
        
        watermark = service._watermarks[sample_revision.id]
        assert watermark.watermark_color == "red"
        assert watermark.watermark_opacity == 0.5


# =============================================================================
# TEST REVISION LINKS
# =============================================================================


class TestRevisionLinks:
    """Test revision link functionality."""
    
    def test_revision_link_created(self, service, sample_document):
        """Test that revision links are created."""
        rev_a = service.create_revision(sample_document.id, "Content A", "user")
        service.approve_revision(rev_a.id, "manager")
        service.release_revision(rev_a.id)
        
        rev_b = service.create_revision(sample_document.id, "Content B", "user")
        
        # Check that link was created
        links = [l for l in service._revision_links if l.source_revision_id == rev_b.id]
        assert len(links) == 1
        assert links[0].target_revision_id == rev_a.id
        assert links[0].link_type == "supersedes"


# =============================================================================
# TEST EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Test edge cases."""
    
    def test_expired_access(self, service, sample_document, sample_revision):
        """Test that expired access is not returned."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        # Grant access that expired yesterday
        access = service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        
        accessible = service.get_accessible_documents(station_id="station-001")
        assert len(accessible) == 0
    
    def test_inactive_access(self, service, sample_document, sample_revision):
        """Test that inactive access is not returned."""
        service.approve_revision(sample_revision.id, "manager")
        service.release_revision(sample_revision.id)
        
        access = service.grant_shop_floor_access(
            document_id=sample_document.id,
            station_id="station-001",
        )
        service.revoke_shop_floor_access(access.id)
        
        accessible = service.get_accessible_documents(station_id="station-001")
        assert len(accessible) == 0
    
    def test_empty_content_hash(self, service, sample_document):
        """Test hash for empty content."""
        revision = service.create_revision(
            sample_document.id,
            content="",
            created_by="user",
        )
        
        assert revision.content_hash is not None
        assert len(revision.content_hash) == 64
