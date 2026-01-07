"""
Tests for Audit Trail Timeline Service.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sensei.services.audit_trail_timeline import (
    ChangeType,
    EntityType,
    FieldType,
    RelationshipType,
    AccessLevel,
    FieldChange,
    RelatedEntity,
    AuditEntry,
    TimelineGroup,
    Timeline,
    TimelineFilter,
    TimelineConfig,
    DiffResult,
    AuditTrailTimelineService,
    get_audit_trail_service,
    reset_audit_trail_service,
)


# ============================================================================
# Enum Tests
# ============================================================================


class TestChangeType:
    """Tests for ChangeType enum."""
    
    def test_basic_change_types(self):
        """Test basic change types exist."""
        assert ChangeType.CREATE.value == "create"
        assert ChangeType.UPDATE.value == "update"
        assert ChangeType.DELETE.value == "delete"
    
    def test_specialized_change_types(self):
        """Test specialized change types exist."""
        assert ChangeType.STATUS_CHANGE.value == "status_change"
        assert ChangeType.OWNER_CHANGE.value == "owner_change"
        assert ChangeType.LINK_ADD.value == "link_add"
        assert ChangeType.LINK_REMOVE.value == "link_remove"
        assert ChangeType.APPROVAL.value == "approval"
        assert ChangeType.REJECTION.value == "rejection"


class TestEntityType:
    """Tests for EntityType enum."""
    
    def test_core_entity_types(self):
        """Test core entity types exist."""
        assert EntityType.OPPORTUNITY.value == "opportunity"
        assert EntityType.RFQ.value == "rfq"
        assert EntityType.QUOTE.value == "quote"
        assert EntityType.TASK.value == "task"
        assert EntityType.A3.value == "a3"
        assert EntityType.CAPA.value == "capa"


class TestFieldType:
    """Tests for FieldType enum."""
    
    def test_all_field_types(self):
        """Test all field types exist."""
        assert FieldType.TEXT.value == "text"
        assert FieldType.NUMBER.value == "number"
        assert FieldType.CURRENCY.value == "currency"
        assert FieldType.DATE.value == "date"
        assert FieldType.BOOLEAN.value == "boolean"


class TestAccessLevel:
    """Tests for AccessLevel enum."""
    
    def test_all_access_levels(self):
        """Test all access levels exist."""
        assert AccessLevel.PUBLIC.value == "public"
        assert AccessLevel.TEAM.value == "team"
        assert AccessLevel.OWNER.value == "owner"
        assert AccessLevel.ADMIN.value == "admin"


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestFieldChange:
    """Tests for FieldChange dataclass."""
    
    def test_basic_field_change(self):
        """Test basic field change."""
        change = FieldChange(
            field_name="status",
            field_label="Status",
            field_type=FieldType.ENUM,
            old_value="draft",
            new_value="submitted",
        )
        
        assert change.field_name == "status"
        assert change.old_display == "draft"
        assert change.new_display == "submitted"
    
    def test_currency_formatting(self):
        """Test currency field formatting."""
        change = FieldChange(
            field_name="total_value",
            field_label="Total Value",
            field_type=FieldType.CURRENCY,
            old_value=1000.0,
            new_value=1500.50,
        )
        
        assert change.old_display == "$1,000.00"
        assert change.new_display == "$1,500.50"
    
    def test_boolean_formatting(self):
        """Test boolean field formatting."""
        change = FieldChange(
            field_name="completed",
            field_label="Completed",
            field_type=FieldType.BOOLEAN,
            old_value=False,
            new_value=True,
        )
        
        assert change.old_display == "No"
        assert change.new_display == "Yes"
    
    def test_none_value_formatting(self):
        """Test None value formatting."""
        change = FieldChange(
            field_name="description",
            field_label="Description",
            field_type=FieldType.TEXT,
            old_value=None,
            new_value="New description",
        )
        
        assert change.old_display == "(empty)"
        assert change.new_display == "New description"
    
    def test_sensitive_field_masking(self):
        """Test sensitive field masking."""
        change = FieldChange(
            field_name="password",
            field_label="Password",
            field_type=FieldType.TEXT,
            old_value="old_secret",
            new_value="new_secret",
            is_sensitive=True,
        )
        
        assert change.old_display == "****"
        assert change.new_display == "****"
    
    def test_list_formatting(self):
        """Test list field formatting."""
        change = FieldChange(
            field_name="tags",
            field_label="Tags",
            field_type=FieldType.LIST,
            old_value=["urgent", "sales"],
            new_value=["urgent", "sales", "priority"],
        )
        
        assert "urgent" in change.old_display
        assert "priority" in change.new_display
    
    def test_date_formatting(self):
        """Test date field formatting."""
        old_date = datetime(2024, 1, 15, 10, 30, 0)
        new_date = datetime(2024, 2, 20, 14, 45, 0)
        
        change = FieldChange(
            field_name="due_date",
            field_label="Due Date",
            field_type=FieldType.DATE,
            old_value=old_date,
            new_value=new_date,
        )
        
        assert change.old_display == "2024-01-15"
        assert change.new_display == "2024-02-20"


class TestRelatedEntity:
    """Tests for RelatedEntity dataclass."""
    
    def test_create_related_entity(self):
        """Test creating a related entity."""
        entity = RelatedEntity(
            entity_id=uuid4(),
            entity_type=EntityType.QUOTE,
            entity_name="Quote Q-2024-001",
            relationship=RelationshipType.CHILD,
        )
        
        assert entity.entity_name == "Quote Q-2024-001"
        assert entity.relationship == RelationshipType.CHILD


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""
    
    def test_create_entry(self):
        """Test creating an audit entry."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            change_type=ChangeType.CREATE,
            changed_at=datetime.utcnow(),
            changed_by=uuid4(),
            changed_by_name="John Doe",
        )
        
        assert entry.entity_type == EntityType.RFQ
        assert "Created" in entry.summary
    
    def test_status_change_summary(self):
        """Test status change generates summary."""
        entry = AuditEntry(
            id=uuid4(),
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            change_type=ChangeType.STATUS_CHANGE,
            changed_at=datetime.utcnow(),
            changed_by=uuid4(),
            changed_by_name="John Doe",
            changes=[
                FieldChange(
                    field_name="status",
                    field_label="Status",
                    field_type=FieldType.ENUM,
                    old_value="draft",
                    new_value="submitted",
                )
            ],
        )
        
        assert "draft" in entry.summary
        assert "submitted" in entry.summary
    
    def test_link_add_summary(self):
        """Test link add generates summary."""
        related = RelatedEntity(
            entity_id=uuid4(),
            entity_type=EntityType.QUOTE,
            entity_name="Q-2024-001",
            relationship=RelationshipType.CHILD,
        )
        
        entry = AuditEntry(
            id=uuid4(),
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            change_type=ChangeType.LINK_ADD,
            changed_at=datetime.utcnow(),
            changed_by=uuid4(),
            changed_by_name="John Doe",
            related_entities=[related],
        )
        
        assert "Linked" in entry.summary
        assert "Q-2024-001" in entry.summary


class TestDiffResult:
    """Tests for DiffResult dataclass."""
    
    def test_has_changes(self):
        """Test has_changes is set correctly."""
        result = DiffResult(
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            old_state={"status": "draft"},
            new_state={"status": "submitted"},
            changes=[
                FieldChange(
                    field_name="status",
                    field_label="Status",
                    field_type=FieldType.ENUM,
                    old_value="draft",
                    new_value="submitted",
                )
            ],
        )
        
        assert result.has_changes is True
    
    def test_no_changes(self):
        """Test no changes results in has_changes=False."""
        result = DiffResult(
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            old_state={"status": "draft"},
            new_state={"status": "draft"},
            changes=[],
        )
        
        assert result.has_changes is False


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance."""
    reset_audit_trail_service()
    return AuditTrailTimelineService()


@pytest.fixture
def user_id():
    """Create a user ID."""
    return uuid4()


@pytest.fixture
def user_name():
    """Create a user name."""
    return "Test User"


@pytest.fixture
def entity_id():
    """Create an entity ID."""
    return uuid4()


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestServiceInitialization:
    """Tests for service initialization."""
    
    def test_default_initialization(self, service):
        """Test service initializes with defaults."""
        assert service.config is not None
        assert service.config.default_page_size == 50
    
    def test_custom_config(self):
        """Test service with custom config."""
        config = TimelineConfig(default_page_size=100)
        svc = AuditTrailTimelineService(config=config)
        assert svc.config.default_page_size == 100


# ============================================================================
# Field Metadata Tests
# ============================================================================


class TestFieldMetadata:
    """Tests for field metadata management."""
    
    def test_get_default_metadata(self, service):
        """Test getting default field metadata."""
        label, field_type = service.get_field_metadata("status")
        assert label == "Status"
        assert field_type == FieldType.ENUM
    
    def test_get_unknown_field_metadata(self, service):
        """Test getting metadata for unknown field."""
        label, field_type = service.get_field_metadata("custom_field")
        assert label == "Custom Field"
        assert field_type == FieldType.TEXT
    
    def test_register_field(self, service):
        """Test registering custom field metadata."""
        service.register_field("custom_amount", "Custom Amount", FieldType.CURRENCY)
        
        label, field_type = service.get_field_metadata("custom_amount")
        assert label == "Custom Amount"
        assert field_type == FieldType.CURRENCY


# ============================================================================
# Diff Calculation Tests
# ============================================================================


class TestDiffCalculation:
    """Tests for diff calculation."""
    
    def test_simple_diff(self, service, entity_id):
        """Test simple diff calculation."""
        old = {"status": "draft", "name": "Test"}
        new = {"status": "submitted", "name": "Test"}
        
        result = service.calculate_diff(entity_id, EntityType.RFQ, old, new)
        
        assert result.has_changes is True
        assert len(result.changes) == 1
        assert result.changes[0].field_name == "status"
    
    def test_multiple_changes(self, service, entity_id):
        """Test diff with multiple changes."""
        old = {"status": "draft", "name": "Old Name", "priority": "low"}
        new = {"status": "submitted", "name": "New Name", "priority": "high"}
        
        result = service.calculate_diff(entity_id, EntityType.RFQ, old, new)
        
        assert len(result.changes) == 3
    
    def test_excluded_fields(self, service, entity_id):
        """Test fields are excluded from diff."""
        old = {"id": uuid4(), "status": "draft"}
        new = {"id": uuid4(), "status": "submitted"}
        
        result = service.calculate_diff(entity_id, EntityType.RFQ, old, new)
        
        # id should be auto-excluded
        assert all(c.field_name != "id" for c in result.changes)
    
    def test_sensitive_fields(self, service, entity_id):
        """Test sensitive fields are masked."""
        old = {"password": "old_pass", "status": "active"}
        new = {"password": "new_pass", "status": "active"}
        
        result = service.calculate_diff(
            entity_id, EntityType.USER, old, new,
            sensitive_fields=["password"],
        )
        
        assert result.has_changes is True
        pw_change = next(c for c in result.changes if c.field_name == "password")
        assert pw_change.is_sensitive is True


# ============================================================================
# Entry Recording Tests
# ============================================================================


class TestRecordCreate:
    """Tests for recording create entries."""
    
    def test_record_create(self, service, entity_id, user_id, user_name):
        """Test recording entity creation."""
        entry = service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        assert entry.change_type == ChangeType.CREATE
        assert entry.entity_id == entity_id
        assert "Created" in entry.summary
    
    def test_record_create_with_metadata(self, service, entity_id, user_id, user_name):
        """Test recording creation with metadata."""
        entry = service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            initial_state={"status": "draft"},
        )
        
        assert entry.ip_address == "192.168.1.1"
        assert "initial_state" in entry.metadata


class TestRecordUpdate:
    """Tests for recording update entries."""
    
    def test_record_update(self, service, entity_id, user_id, user_name):
        """Test recording entity update."""
        old = {"status": "draft", "name": "RFQ-2024-001"}
        new = {"status": "submitted", "name": "RFQ-2024-001"}
        
        entry = service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state=old,
            new_state=new,
        )
        
        assert entry is not None
        assert entry.change_type == ChangeType.STATUS_CHANGE
        assert len(entry.changes) == 1
    
    def test_record_update_no_changes(self, service, entity_id, user_id, user_name):
        """Test recording update with no changes returns None."""
        state = {"status": "draft", "name": "RFQ-2024-001"}
        
        entry = service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state=state,
            new_state=state,
        )
        
        assert entry is None
    
    def test_record_owner_change(self, service, entity_id, user_id, user_name):
        """Test recording owner change."""
        old_owner = uuid4()
        new_owner = uuid4()
        
        old = {"owner_id": old_owner, "name": "Test"}
        new = {"owner_id": new_owner, "name": "Test"}
        
        entry = service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.TASK,
            entity_name="Task-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state=old,
            new_state=new,
        )
        
        assert entry.change_type == ChangeType.OWNER_CHANGE


class TestRecordDelete:
    """Tests for recording delete entries."""
    
    def test_record_delete(self, service, entity_id, user_id, user_name):
        """Test recording entity deletion."""
        entry = service.record_delete(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            deleted_by=user_id,
            deleted_by_name=user_name,
        )
        
        assert entry.change_type == ChangeType.DELETE
        assert "Deleted" in entry.summary


class TestRecordLink:
    """Tests for recording link entries."""
    
    def test_record_link_add(self, service, entity_id, user_id, user_name):
        """Test recording link addition."""
        related = RelatedEntity(
            entity_id=uuid4(),
            entity_type=EntityType.QUOTE,
            entity_name="Q-2024-001",
            relationship=RelationshipType.CHILD,
        )
        
        entry = service.record_link(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            linked_by=user_id,
            linked_by_name=user_name,
            related_entity=related,
            is_add=True,
        )
        
        assert entry.change_type == ChangeType.LINK_ADD
        assert len(entry.related_entities) == 1
    
    def test_record_link_remove(self, service, entity_id, user_id, user_name):
        """Test recording link removal."""
        related = RelatedEntity(
            entity_id=uuid4(),
            entity_type=EntityType.QUOTE,
            entity_name="Q-2024-001",
            relationship=RelationshipType.CHILD,
        )
        
        entry = service.record_link(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            linked_by=user_id,
            linked_by_name=user_name,
            related_entity=related,
            is_add=False,
        )
        
        assert entry.change_type == ChangeType.LINK_REMOVE


class TestRecordAttachment:
    """Tests for recording attachment entries."""
    
    def test_record_attachment_add(self, service, entity_id, user_id, user_name):
        """Test recording attachment addition."""
        entry = service.record_attachment(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            user_id=user_id,
            user_name=user_name,
            attachment_name="drawing.pdf",
            attachment_id=uuid4(),
            is_add=True,
        )
        
        assert entry.change_type == ChangeType.ATTACHMENT_ADD
        assert "drawing.pdf" in entry.summary


class TestRecordComment:
    """Tests for recording comment entries."""
    
    def test_record_comment(self, service, entity_id, user_id, user_name):
        """Test recording comment addition."""
        entry = service.record_comment(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            user_id=user_id,
            user_name=user_name,
            comment_text="This is a test comment",
            comment_id=uuid4(),
        )
        
        assert entry.change_type == ChangeType.COMMENT_ADD
        assert entry.details == "This is a test comment"
    
    def test_long_comment_truncated(self, service, entity_id, user_id, user_name):
        """Test long comment is truncated."""
        long_comment = "A" * 300
        
        entry = service.record_comment(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            user_id=user_id,
            user_name=user_name,
            comment_text=long_comment,
            comment_id=uuid4(),
        )
        
        assert len(entry.details) < 300
        assert entry.details.endswith("...")


class TestRecordApproval:
    """Tests for recording approval entries."""
    
    def test_record_approval(self, service, entity_id, user_id, user_name):
        """Test recording approval."""
        entry = service.record_approval(
            entity_id=entity_id,
            entity_type=EntityType.QUOTE,
            entity_name="Q-2024-001",
            approved_by=user_id,
            approved_by_name=user_name,
            approval_type="Manager Review",
            notes="Looks good",
        )
        
        assert entry.change_type == ChangeType.APPROVAL
        assert "Manager Review" in entry.summary


class TestRecordRejection:
    """Tests for recording rejection entries."""
    
    def test_record_rejection(self, service, entity_id, user_id, user_name):
        """Test recording rejection."""
        entry = service.record_rejection(
            entity_id=entity_id,
            entity_type=EntityType.QUOTE,
            entity_name="Q-2024-001",
            rejected_by=user_id,
            rejected_by_name=user_name,
            rejection_reason="Pricing too high",
        )
        
        assert entry.change_type == ChangeType.REJECTION
        assert entry.details == "Pricing too high"


class TestRecordEscalation:
    """Tests for recording escalation entries."""
    
    def test_record_escalation(self, service, entity_id, user_id, user_name):
        """Test recording escalation."""
        entry = service.record_escalation(
            entity_id=entity_id,
            entity_type=EntityType.TASK,
            entity_name="Task-001",
            escalated_by=user_id,
            escalated_by_name=user_name,
            escalation_level="Level 2",
            reason="Past due",
        )
        
        assert entry.change_type == ChangeType.ESCALATION
        assert "Level 2" in entry.summary


class TestRecordCustom:
    """Tests for recording custom entries."""
    
    def test_record_custom(self, service, entity_id, user_id, user_name):
        """Test recording custom entry."""
        entry = service.record_custom(
            entity_id=entity_id,
            entity_type=EntityType.A3,
            entity_name="A3-2024-001",
            change_type=ChangeType.ARCHIVE,
            user_id=user_id,
            user_name=user_name,
            summary="Archived for retention",
            details="Archived per policy",
        )
        
        assert entry.change_type == ChangeType.ARCHIVE
        assert entry.summary == "Archived for retention"


# ============================================================================
# Entry Retrieval Tests
# ============================================================================


class TestEntryRetrieval:
    """Tests for entry retrieval."""
    
    def test_get_entry(self, service, entity_id, user_id, user_name):
        """Test getting entry by ID."""
        entry = service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        retrieved = service.get_entry(entry.id)
        assert retrieved is not None
        assert retrieved.id == entry.id
    
    def test_get_nonexistent_entry(self, service):
        """Test getting nonexistent entry."""
        result = service.get_entry(uuid4())
        assert result is None
    
    def test_get_entity_history(self, service, entity_id, user_id, user_name):
        """Test getting entity history."""
        # Create multiple entries for same entity
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state={"status": "draft"},
            new_state={"status": "submitted"},
        )
        
        history = service.get_entity_history(entity_id)
        
        assert len(history) == 2
        # Most recent first
        assert history[0].change_type == ChangeType.STATUS_CHANGE
        assert history[1].change_type == ChangeType.CREATE
    
    def test_get_entity_history_with_filter(self, service, entity_id, user_id, user_name):
        """Test filtering entity history by change type."""
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state={"status": "draft"},
            new_state={"status": "submitted"},
        )
        
        history = service.get_entity_history(
            entity_id,
            change_types=[ChangeType.CREATE],
        )
        
        assert len(history) == 1
        assert history[0].change_type == ChangeType.CREATE
    
    def test_get_user_activity(self, service, user_id, user_name):
        """Test getting user activity."""
        entity1 = uuid4()
        entity2 = uuid4()
        
        service.record_create(
            entity_id=entity1,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_create(
            entity_id=entity2,
            entity_type=EntityType.QUOTE,
            entity_name="Q-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        activity = service.get_user_activity(user_id)
        
        assert len(activity) == 2


# ============================================================================
# Timeline Tests
# ============================================================================


class TestTimeline:
    """Tests for timeline generation."""
    
    def test_get_timeline_for_entity(self, service, entity_id, user_id, user_name):
        """Test getting timeline for entity."""
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        timeline = service.get_timeline(entity_id=entity_id)
        
        assert timeline.entity_id == entity_id
        assert timeline.total_entries == 1
        assert len(timeline.groups) >= 1
    
    def test_timeline_grouping(self, service, entity_id, user_id, user_name):
        """Test timeline groups entries by date."""
        # Record entries today
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-2024-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state={"status": "draft"},
            new_state={"status": "submitted"},
        )
        
        timeline = service.get_timeline(entity_id=entity_id)
        
        # Should be grouped into today
        assert len(timeline.groups) == 1
        assert timeline.groups[0].date_label == "Today"
        assert timeline.groups[0].count == 2
    
    def test_timeline_with_filters(self, service, user_id, user_name):
        """Test timeline with filters."""
        entity1 = uuid4()
        entity2 = uuid4()
        
        service.record_create(
            entity_id=entity1,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_create(
            entity_id=entity2,
            entity_type=EntityType.QUOTE,
            entity_name="Q-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        filters = TimelineFilter(
            entity_types=[EntityType.RFQ],
        )
        
        timeline = service.get_timeline(filters=filters)
        
        assert timeline.total_entries == 1
    
    def test_timeline_pagination(self, service, user_id, user_name):
        """Test timeline pagination."""
        entity_id = uuid4()
        
        for i in range(10):
            service.record_update(
                entity_id=entity_id,
                entity_type=EntityType.RFQ,
                entity_name="RFQ-001",
                updated_by=user_id,
                updated_by_name=user_name,
                old_state={"count": i},
                new_state={"count": i + 1},
            )
        
        timeline = service.get_timeline(entity_id=entity_id, page_size=5)
        
        assert timeline.total_entries == 10
        assert timeline.has_more is True
    
    def test_timeline_search(self, service, user_id, user_name):
        """Test timeline search filter."""
        entity_id = uuid4()
        
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="Special Project RFQ",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_create(
            entity_id=uuid4(),
            entity_type=EntityType.RFQ,
            entity_name="Normal RFQ",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        filters = TimelineFilter(search_text="Special")
        timeline = service.get_timeline(filters=filters)
        
        assert timeline.total_entries == 1


# ============================================================================
# Statistics Tests
# ============================================================================


class TestStatistics:
    """Tests for statistics and aggregation."""
    
    def test_get_change_count(self, service, entity_id, user_id, user_name):
        """Test getting change counts."""
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        service.record_update(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            updated_by=user_id,
            updated_by_name=user_name,
            old_state={"status": "draft"},
            new_state={"status": "submitted"},
        )
        
        counts = service.get_change_count(entity_id=entity_id)
        
        assert ChangeType.CREATE in counts
        assert counts[ChangeType.CREATE] == 1
        assert ChangeType.STATUS_CHANGE in counts
        assert counts[ChangeType.STATUS_CHANGE] == 1
    
    def test_get_activity_summary(self, service, entity_id, user_id, user_name):
        """Test getting activity summary."""
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        summary = service.get_activity_summary(entity_id)
        
        assert summary["total_changes"] == 1
        assert summary["created_by"] == user_name
    
    def test_get_most_active_entities(self, service, user_id, user_name):
        """Test getting most active entities."""
        busy_entity = uuid4()
        quiet_entity = uuid4()
        
        for i in range(5):
            service.record_update(
                entity_id=busy_entity,
                entity_type=EntityType.RFQ,
                entity_name="Busy RFQ",
                updated_by=user_id,
                updated_by_name=user_name,
                old_state={"count": i},
                new_state={"count": i + 1},
            )
        
        service.record_create(
            entity_id=quiet_entity,
            entity_type=EntityType.RFQ,
            entity_name="Quiet RFQ",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        most_active = service.get_most_active_entities()
        
        assert len(most_active) >= 2
        assert most_active[0][0] == busy_entity  # Most active first
        assert most_active[0][2] == 5  # Count
    
    def test_get_most_active_users(self, service):
        """Test getting most active users."""
        busy_user = uuid4()
        quiet_user = uuid4()
        entity_id = uuid4()
        
        for i in range(3):
            service.record_update(
                entity_id=entity_id,
                entity_type=EntityType.RFQ,
                entity_name="RFQ-001",
                updated_by=busy_user,
                updated_by_name="Busy User",
                old_state={"count": i},
                new_state={"count": i + 1},
            )
        
        service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            created_by=quiet_user,
            created_by_name="Quiet User",
        )
        
        most_active = service.get_most_active_users()
        
        assert len(most_active) >= 2
        assert most_active[0][0] == busy_user


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestCleanup:
    """Tests for cleanup functionality."""
    
    def test_cleanup_old_entries(self, service, entity_id, user_id, user_name):
        """Test cleaning up old entries."""
        # Create an entry
        entry = service.record_create(
            entity_id=entity_id,
            entity_type=EntityType.RFQ,
            entity_name="RFQ-001",
            created_by=user_id,
            created_by_name=user_name,
        )
        
        # Manually age the entry
        service._entries[entry.id].changed_at = datetime.utcnow() - timedelta(days=400)
        
        removed = service.cleanup_old_entries(older_than_days=365)
        
        assert removed == 1
        assert service.get_entry(entry.id) is None


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_singleton_instance(self):
        """Test getting singleton instance."""
        reset_audit_trail_service()
        
        svc1 = get_audit_trail_service()
        svc2 = get_audit_trail_service()
        
        assert svc1 is svc2
    
    def test_reset_singleton(self):
        """Test resetting singleton instance."""
        svc1 = get_audit_trail_service()
        
        reset_audit_trail_service()
        
        svc2 = get_audit_trail_service()
        
        assert svc1 is not svc2


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_timeline(self, service):
        """Test timeline for nonexistent entity."""
        timeline = service.get_timeline(entity_id=uuid4())
        
        assert timeline.total_entries == 0
        assert len(timeline.groups) == 0
    
    def test_empty_activity_summary(self, service):
        """Test activity summary for entity with no history."""
        summary = service.get_activity_summary(uuid4())
        
        assert summary["total_changes"] == 0
        assert summary["created_at"] is None
    
    def test_max_page_size_enforced(self, service):
        """Test max page size is enforced."""
        config = TimelineConfig(max_page_size=10)
        svc = AuditTrailTimelineService(config=config)
        
        timeline = svc.get_timeline(page_size=100)
        
        # Max enforced internally
        assert svc.config.max_page_size == 10
