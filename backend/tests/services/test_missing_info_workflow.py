"""
Tests for Missing Info Workflow Service.
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4

from sensei.services.missing_info_workflow import (
    MissingFieldCategory,
    MissingFieldPriority,
    InfoRequestStatus,
    TaskStatus,
    ReminderFrequency,
    MissingFieldSpec,
    IdentifiedMissingField,
    InfoRequest,
    GeneratedTask,
    EmailTemplate,
    RFQData,
    AnalysisResult,
    WorkflowConfig,
    MissingInfoWorkflowService,
    get_missing_info_workflow_service,
    reset_missing_info_workflow_service,
)


# ============================================================================
# Enum Tests
# ============================================================================


class TestMissingFieldCategory:
    """Tests for MissingFieldCategory enum."""
    
    def test_all_categories(self):
        """Test all category values exist."""
        assert MissingFieldCategory.CUSTOMER_INFO.value == "customer_info"
        assert MissingFieldCategory.PRODUCT_SPECS.value == "product_specs"
        assert MissingFieldCategory.COMMERCIAL.value == "commercial"
        assert MissingFieldCategory.TECHNICAL.value == "technical"
        assert MissingFieldCategory.COMPLIANCE.value == "compliance"
        assert MissingFieldCategory.VOLUME_DEMAND.value == "volume_demand"
        assert MissingFieldCategory.LOGISTICS.value == "logistics"
        assert MissingFieldCategory.QUALITY.value == "quality"
        assert MissingFieldCategory.TIMELINE.value == "timeline"
    
    def test_category_count(self):
        """Test number of categories."""
        assert len(MissingFieldCategory) == 9


class TestMissingFieldPriority:
    """Tests for MissingFieldPriority enum."""
    
    def test_all_priorities(self):
        """Test all priority values exist."""
        assert MissingFieldPriority.CRITICAL.value == "critical"
        assert MissingFieldPriority.HIGH.value == "high"
        assert MissingFieldPriority.MEDIUM.value == "medium"
        assert MissingFieldPriority.LOW.value == "low"


class TestInfoRequestStatus:
    """Tests for InfoRequestStatus enum."""
    
    def test_all_statuses(self):
        """Test all status values exist."""
        assert InfoRequestStatus.DRAFT.value == "draft"
        assert InfoRequestStatus.SENT.value == "sent"
        assert InfoRequestStatus.ACKNOWLEDGED.value == "acknowledged"
        assert InfoRequestStatus.PARTIALLY_RECEIVED.value == "partially_received"
        assert InfoRequestStatus.COMPLETED.value == "completed"
        assert InfoRequestStatus.CANCELLED.value == "cancelled"
        assert InfoRequestStatus.EXPIRED.value == "expired"


class TestTaskStatus:
    """Tests for TaskStatus enum."""
    
    def test_all_statuses(self):
        """Test all task status values exist."""
        assert TaskStatus.OPEN.value == "open"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestReminderFrequency:
    """Tests for ReminderFrequency enum."""
    
    def test_all_frequencies(self):
        """Test all frequency values exist."""
        assert ReminderFrequency.DAILY.value == "daily"
        assert ReminderFrequency.EVERY_OTHER_DAY.value == "every_other_day"
        assert ReminderFrequency.WEEKLY.value == "weekly"
        assert ReminderFrequency.CUSTOM.value == "custom"


# ============================================================================
# Dataclass Tests
# ============================================================================


class TestMissingFieldSpec:
    """Tests for MissingFieldSpec dataclass."""
    
    def test_create_minimal_spec(self):
        """Test creating a spec with required fields only."""
        spec = MissingFieldSpec(
            field_name="test_field",
            field_label="Test Field",
            category=MissingFieldCategory.CUSTOMER_INFO,
            priority=MissingFieldPriority.MEDIUM,
            question_template="Please provide test field.",
        )
        
        assert spec.field_name == "test_field"
        assert spec.field_label == "Test Field"
        assert spec.category == MissingFieldCategory.CUSTOMER_INFO
        assert spec.priority == MissingFieldPriority.MEDIUM
        assert spec.question_template == "Please provide test field."
        assert spec.help_text is None
        assert spec.example_value is None
        assert spec.is_blocking is False
        assert spec.requires_attachment is False
    
    def test_create_full_spec(self):
        """Test creating a spec with all fields."""
        spec = MissingFieldSpec(
            field_name="bom_uploaded",
            field_label="Bill of Materials",
            category=MissingFieldCategory.PRODUCT_SPECS,
            priority=MissingFieldPriority.CRITICAL,
            question_template="Please upload the BOM.",
            help_text="Include all components.",
            example_value="See attached sample BOM",
            is_blocking=True,
            requires_attachment=True,
        )
        
        assert spec.is_blocking is True
        assert spec.requires_attachment is True
        assert spec.help_text == "Include all components."


class TestIdentifiedMissingField:
    """Tests for IdentifiedMissingField dataclass."""
    
    def test_create_identified_field(self):
        """Test creating an identified missing field."""
        rfq_id = uuid4()
        field = IdentifiedMissingField(
            id=uuid4(),
            rfq_id=rfq_id,
            field_name="volume_annual",
            field_label="Annual Volume",
            category=MissingFieldCategory.VOLUME_DEMAND,
            priority=MissingFieldPriority.CRITICAL,
            question_text="Please provide annual volume.",
            help_text="This helps us plan capacity.",
            is_blocking=True,
            requires_attachment=False,
        )
        
        assert field.rfq_id == rfq_id
        assert field.field_name == "volume_annual"
        assert field.resolved_at is None
        assert field.resolved_value is None


class TestRFQData:
    """Tests for RFQData dataclass."""
    
    def test_create_minimal_rfq_data(self):
        """Test creating RFQ data with minimal fields."""
        rfq_id = uuid4()
        data = RFQData(
            rfq_id=rfq_id,
            rfq_number="RFQ-2024-001",
            customer_name="Acme Corp",
            contact_name=None,
            contact_email=None,
            product_name=None,
            part_number=None,
        )
        
        assert data.rfq_id == rfq_id
        assert data.rfq_number == "RFQ-2024-001"
        assert data.customer_name == "Acme Corp"
        assert data.contact_name is None
        assert data.volume_annual is None
        assert data.bom_uploaded is False
    
    def test_create_complete_rfq_data(self):
        """Test creating RFQ data with all fields populated."""
        rfq_id = uuid4()
        data = RFQData(
            rfq_id=rfq_id,
            rfq_number="RFQ-2024-002",
            customer_name="Tech Corp",
            contact_name="John Doe",
            contact_email="john@techcorp.com",
            product_name="Widget Pro",
            part_number="WP-001",
            customer_address="123 Main St",
            product_specs="Full specs here",
            bom_uploaded=True,
            volume_annual=50000,
            volume_per_order=5000,
            target_price=10.50,
            currency="USD",
            incoterms="FOB",
            delivery_location="Chicago, IL",
            lead_time_required=8,
            sample_required=True,
            sample_quantity=10,
            certification_requirements=["ISO 9001"],
            compliance_requirements=["RoHS"],
            packaging_specs="Standard packaging",
            testing_requirements="Full QC",
            quality_requirements="AQL 2.5",
            ramp_plan="Q1: 5000, Q2: 15000",
            sop_date=date(2024, 6, 1),
            drawings_uploaded=True,
            revision_level="Rev C",
        )
        
        assert data.volume_annual == 50000
        assert data.bom_uploaded is True
        assert data.drawings_uploaded is True


class TestWorkflowConfig:
    """Tests for WorkflowConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = WorkflowConfig()
        
        assert config.default_reminder_frequency == ReminderFrequency.EVERY_OTHER_DAY
        assert config.max_reminders == 3
        assert config.request_expiry_days == 14
        assert config.task_due_days == 3
        assert config.auto_create_tasks is True
        assert config.auto_send_reminders is True
        assert config.include_help_text_in_email is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = WorkflowConfig(
            default_reminder_frequency=ReminderFrequency.WEEKLY,
            max_reminders=5,
            request_expiry_days=30,
            task_due_days=7,
            auto_create_tasks=False,
        )
        
        assert config.default_reminder_frequency == ReminderFrequency.WEEKLY
        assert config.max_reminders == 5
        assert config.request_expiry_days == 30
        assert config.auto_create_tasks is False


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance for testing."""
    reset_missing_info_workflow_service()
    return MissingInfoWorkflowService()


@pytest.fixture
def sample_rfq_data():
    """Create sample RFQ data with some missing fields."""
    return RFQData(
        rfq_id=uuid4(),
        rfq_number="RFQ-2024-001",
        customer_name="Acme Corporation",
        contact_name="John Smith",
        contact_email="john.smith@acme.com",
        product_name="Widget Assembly",
        part_number="WA-001",
        customer_address=None,  # Missing
        product_specs=None,  # Missing - blocking
        bom_uploaded=False,  # Missing - blocking
        volume_annual=None,  # Missing - blocking
        volume_per_order=5000,
        target_price=None,  # Missing
        currency="USD",
        incoterms=None,  # Missing
    )


@pytest.fixture
def complete_rfq_data():
    """Create RFQ data with all fields populated."""
    return RFQData(
        rfq_id=uuid4(),
        rfq_number="RFQ-2024-002",
        customer_name="Complete Corp",
        contact_name="Jane Doe",
        contact_email="jane@complete.com",
        product_name="Complete Widget",
        part_number="CW-001",
        customer_address="123 Complete St",
        product_specs="Full specifications",
        bom_uploaded=True,
        volume_annual=100000,
        volume_per_order=10000,
        target_price=15.00,
        currency="USD",
        incoterms="FOB",
        delivery_location="New York, NY",
        lead_time_required=6,
        sample_required=False,
        sample_quantity=10,  # Provide a value even if not required
        certification_requirements=["ISO 9001", "IATF 16949"],
        compliance_requirements=["RoHS", "REACH"],
        packaging_specs="Custom box",
        testing_requirements="100% functional test",
        quality_requirements="AQL 1.0",
        ramp_plan="Flat rate production",
        sop_date=date(2024, 6, 1),
        drawings_uploaded=True,
        revision_level="Rev B",
    )


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestServiceInitialization:
    """Tests for service initialization."""
    
    def test_default_initialization(self, service):
        """Test service initializes with defaults."""
        assert service.config is not None
        assert len(service._field_specs) > 0
        assert len(service._email_templates) > 0
    
    def test_custom_config(self):
        """Test service with custom config."""
        config = WorkflowConfig(max_reminders=10)
        svc = MissingInfoWorkflowService(config=config)
        assert svc.config.max_reminders == 10
    
    def test_default_field_specs_registered(self, service):
        """Test that default field specs are registered."""
        # Check some known fields
        spec = service.get_field_spec("volume_annual")
        assert spec is not None
        assert spec.priority == MissingFieldPriority.CRITICAL
        assert spec.is_blocking is True
        
        spec = service.get_field_spec("bom_uploaded")
        assert spec is not None
        assert spec.requires_attachment is True
    
    def test_default_email_templates_registered(self, service):
        """Test that default email templates are registered."""
        templates = service.list_email_templates()
        assert len(templates) >= 2  # English and French
        
        default = service.get_default_email_template()
        assert default is not None
        assert default.language == "en"


# ============================================================================
# Field Specification Tests
# ============================================================================


class TestFieldSpecifications:
    """Tests for field specification management."""
    
    def test_get_existing_spec(self, service):
        """Test getting an existing field spec."""
        spec = service.get_field_spec("product_specs")
        assert spec is not None
        assert spec.category == MissingFieldCategory.PRODUCT_SPECS
    
    def test_get_nonexistent_spec(self, service):
        """Test getting a nonexistent field spec."""
        spec = service.get_field_spec("nonexistent_field")
        assert spec is None
    
    def test_list_all_specs(self, service):
        """Test listing all field specs."""
        specs = service.list_field_specs()
        assert len(specs) > 0
    
    def test_list_specs_by_category(self, service):
        """Test listing specs by category."""
        specs = service.list_field_specs(category=MissingFieldCategory.CUSTOMER_INFO)
        assert len(specs) > 0
        assert all(s.category == MissingFieldCategory.CUSTOMER_INFO for s in specs)
    
    def test_list_specs_by_priority(self, service):
        """Test listing specs by priority."""
        specs = service.list_field_specs(priority=MissingFieldPriority.CRITICAL)
        assert len(specs) > 0
        assert all(s.priority == MissingFieldPriority.CRITICAL for s in specs)
    
    def test_list_blocking_specs_only(self, service):
        """Test listing only blocking specs."""
        specs = service.list_field_specs(blocking_only=True)
        assert len(specs) > 0
        assert all(s.is_blocking for s in specs)
    
    def test_add_custom_spec(self, service):
        """Test adding a custom field spec."""
        custom_spec = MissingFieldSpec(
            field_name="custom_field",
            field_label="Custom Field",
            category=MissingFieldCategory.TECHNICAL,
            priority=MissingFieldPriority.HIGH,
            question_template="Please provide custom field value.",
        )
        
        service.add_field_spec(custom_spec)
        
        retrieved = service.get_field_spec("custom_field")
        assert retrieved is not None
        assert retrieved.field_label == "Custom Field"
    
    def test_remove_field_spec(self, service):
        """Test removing a field spec."""
        # First add a spec
        custom_spec = MissingFieldSpec(
            field_name="removable_field",
            field_label="Removable",
            category=MissingFieldCategory.TECHNICAL,
            priority=MissingFieldPriority.LOW,
            question_template="Test",
        )
        service.add_field_spec(custom_spec)
        
        # Verify it exists
        assert service.get_field_spec("removable_field") is not None
        
        # Remove it
        result = service.remove_field_spec("removable_field")
        assert result is True
        
        # Verify it's gone
        assert service.get_field_spec("removable_field") is None
    
    def test_remove_nonexistent_spec(self, service):
        """Test removing a nonexistent spec."""
        result = service.remove_field_spec("nonexistent")
        assert result is False


# ============================================================================
# RFQ Analysis Tests
# ============================================================================


class TestRFQAnalysis:
    """Tests for RFQ analysis."""
    
    def test_analyze_rfq_with_missing_fields(self, service, sample_rfq_data):
        """Test analyzing an RFQ with missing fields."""
        result = service.analyze_rfq(sample_rfq_data)
        
        assert result.rfq_id == sample_rfq_data.rfq_id
        assert result.rfq_number == "RFQ-2024-001"
        assert result.missing_count > 0
        assert result.total_fields_checked > 0
        assert result.completeness_score < 100.0
    
    def test_analyze_complete_rfq(self, service, complete_rfq_data):
        """Test analyzing a complete RFQ."""
        result = service.analyze_rfq(complete_rfq_data)
        
        assert result.missing_count == 0
        assert result.blocking_count == 0
        assert result.completeness_score == 100.0
        assert result.can_transition is True
    
    def test_analyze_identifies_blocking_fields(self, service, sample_rfq_data):
        """Test that blocking fields are correctly identified."""
        result = service.analyze_rfq(sample_rfq_data)
        
        assert result.blocking_count > 0
        assert result.can_transition is False
        
        blocking = [mf for mf in result.missing_fields if mf.is_blocking]
        assert len(blocking) == result.blocking_count
    
    def test_analyze_groups_by_category(self, service, sample_rfq_data):
        """Test that results are grouped by category."""
        result = service.analyze_rfq(sample_rfq_data)
        
        assert len(result.by_category) > 0
        
        # Verify counts match
        total = sum(len(fields) for fields in result.by_category.values())
        assert total == result.missing_count
    
    def test_analyze_groups_by_priority(self, service, sample_rfq_data):
        """Test that results are grouped by priority."""
        result = service.analyze_rfq(sample_rfq_data)
        
        assert len(result.by_priority) > 0
        
        # Verify counts match
        total = sum(len(fields) for fields in result.by_priority.values())
        assert total == result.missing_count
    
    def test_analyze_handles_empty_lists(self, service):
        """Test analyzing RFQ with empty lists (e.g., empty certifications)."""
        rfq = RFQData(
            rfq_id=uuid4(),
            rfq_number="RFQ-2024-003",
            customer_name="Test Corp",
            contact_name="Test",
            contact_email="test@test.com",
            product_name="Test Product",
            part_number="TP-001",
            certification_requirements=[],  # Empty list = missing
            compliance_requirements=[],  # Empty list = missing
        )
        
        result = service.analyze_rfq(rfq)
        
        # Should detect empty lists as missing
        field_names = [mf.field_name for mf in result.missing_fields]
        assert "certification_requirements" in field_names
        assert "compliance_requirements" in field_names
    
    def test_analyze_handles_empty_strings(self, service):
        """Test analyzing RFQ with empty strings."""
        rfq = RFQData(
            rfq_id=uuid4(),
            rfq_number="RFQ-2024-004",
            customer_name="Test Corp",
            contact_name="",  # Empty string = missing
            contact_email="test@test.com",
            product_name="Test",
            part_number="TP-001",
            customer_address="   ",  # Whitespace only = missing
        )
        
        result = service.analyze_rfq(rfq)
        
        field_names = [mf.field_name for mf in result.missing_fields]
        assert "contact_name" in field_names
        assert "customer_address" in field_names


# ============================================================================
# Email Template Tests
# ============================================================================


class TestEmailTemplates:
    """Tests for email template management."""
    
    def test_get_default_template(self, service):
        """Test getting default email template."""
        template = service.get_default_email_template()
        
        assert template is not None
        assert template.is_default is True
        assert "{rfq_number}" in template.subject_template
        assert "{missing_fields_list}" in template.body_template
    
    def test_list_all_templates(self, service):
        """Test listing all email templates."""
        templates = service.list_email_templates()
        assert len(templates) >= 2
    
    def test_list_templates_by_language(self, service):
        """Test listing templates by language."""
        en_templates = service.list_email_templates(language="en")
        assert len(en_templates) >= 1
        assert all(t.language == "en" for t in en_templates)
        
        fr_templates = service.list_email_templates(language="fr")
        assert len(fr_templates) >= 1
        assert all(t.language == "fr" for t in fr_templates)
    
    def test_create_custom_template(self, service):
        """Test creating a custom email template."""
        template = service.create_email_template(
            name="Custom Template",
            subject_template="Action Required: {rfq_number}",
            body_template="Dear {contact_name},\n\n{missing_fields_list}",
            language="en",
        )
        
        assert template.id is not None
        assert template.name == "Custom Template"
        
        # Should be retrievable
        retrieved = service.get_email_template(template.id)
        assert retrieved is not None
        assert retrieved.name == "Custom Template"
    
    def test_create_new_default_template(self, service):
        """Test creating a new default template."""
        old_default = service.get_default_email_template()
        assert old_default.is_default is True
        
        new_template = service.create_email_template(
            name="New Default",
            subject_template="New Default Subject",
            body_template="New Default Body",
            is_default=True,
        )
        
        # Old default should no longer be default
        old_default = service.get_email_template(old_default.id)
        assert old_default.is_default is False
        
        # New template should be default
        assert new_template.is_default is True
        assert service.get_default_email_template().id == new_template.id


# ============================================================================
# Email Generation Tests
# ============================================================================


class TestEmailGeneration:
    """Tests for email text generation."""
    
    def test_generate_email_text(self, service, sample_rfq_data):
        """Test generating email text."""
        result = service.analyze_rfq(sample_rfq_data)
        
        subject, body = service.generate_email_text(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Test Sender",
            sender_title="Sales Rep",
        )
        
        assert "RFQ-2024-001" in subject
        assert "John Smith" in body
        assert "Test Sender" in body
        assert "Sales Rep" in body
    
    def test_generate_email_includes_field_questions(self, service, sample_rfq_data):
        """Test that email includes field questions."""
        result = service.analyze_rfq(sample_rfq_data)
        
        _, body = service.generate_email_text(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Sender",
        )
        
        # Should include some field labels
        assert any(mf.field_label in body for mf in result.missing_fields)
    
    def test_generate_email_with_custom_template(self, service, sample_rfq_data):
        """Test generating email with custom template."""
        custom = service.create_email_template(
            name="Custom",
            subject_template="CUSTOM: {rfq_number}",
            body_template="CUSTOM BODY for {contact_name}",
        )
        
        result = service.analyze_rfq(sample_rfq_data)
        
        subject, body = service.generate_email_text(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Sender",
            template_id=custom.id,
        )
        
        assert subject.startswith("CUSTOM:")
        assert body.startswith("CUSTOM BODY")
    
    def test_generate_email_fallback_contact_name(self, service):
        """Test email generation with missing contact name."""
        rfq = RFQData(
            rfq_id=uuid4(),
            rfq_number="RFQ-2024-005",
            customer_name="Test Corp",
            contact_name=None,  # Missing
            contact_email="test@test.com",
            product_name=None,
            part_number=None,
        )
        
        result = service.analyze_rfq(rfq)
        
        _, body = service.generate_email_text(
            rfq_data=rfq,
            missing_fields=result.missing_fields,
            sender_name="Sender",
        )
        
        # Should use fallback "Customer"
        assert "Customer" in body or "Dear" in body


# ============================================================================
# Info Request Tests
# ============================================================================


class TestInfoRequests:
    """Tests for info request management."""
    
    def test_create_info_request(self, service, sample_rfq_data):
        """Test creating an info request."""
        result = service.analyze_rfq(sample_rfq_data)
        created_by = uuid4()
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Sales Rep",
            created_by=created_by,
            sender_title="Senior Rep",
        )
        
        assert request.id is not None
        assert request.rfq_id == sample_rfq_data.rfq_id
        assert request.status == InfoRequestStatus.DRAFT
        assert request.recipient_name == "John Smith"
        assert request.recipient_email == "john.smith@acme.com"
        assert len(request.missing_fields) > 0
        assert request.created_by == created_by
        assert request.expires_at is not None
    
    def test_create_info_request_with_override_recipient(self, service, sample_rfq_data):
        """Test creating request with override recipient."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
            recipient_name="Override Name",
            recipient_email="override@email.com",
        )
        
        assert request.recipient_name == "Override Name"
        assert request.recipient_email == "override@email.com"
    
    def test_get_info_request(self, service, sample_rfq_data):
        """Test getting an info request by ID."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        retrieved = service.get_info_request(request.id)
        assert retrieved is not None
        assert retrieved.id == request.id
    
    def test_get_nonexistent_request(self, service):
        """Test getting a nonexistent request."""
        result = service.get_info_request(uuid4())
        assert result is None
    
    def test_list_info_requests(self, service, sample_rfq_data):
        """Test listing info requests."""
        result = service.analyze_rfq(sample_rfq_data)
        user_id = uuid4()
        
        # Create multiple requests
        for i in range(3):
            service.create_info_request(
                rfq_data=sample_rfq_data,
                missing_fields=result.missing_fields,
                sender_name=f"Rep {i}",
                created_by=user_id,
            )
        
        requests = service.list_info_requests()
        assert len(requests) >= 3
    
    def test_list_requests_by_rfq(self, service, sample_rfq_data):
        """Test listing requests by RFQ."""
        result = service.analyze_rfq(sample_rfq_data)
        
        service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        requests = service.list_info_requests(rfq_id=sample_rfq_data.rfq_id)
        assert len(requests) >= 1
        assert all(r.rfq_id == sample_rfq_data.rfq_id for r in requests)
    
    def test_list_requests_by_status(self, service, sample_rfq_data):
        """Test listing requests by status."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Mark as sent
        service.mark_request_sent(request.id)
        
        draft_requests = service.list_info_requests(status=InfoRequestStatus.DRAFT)
        sent_requests = service.list_info_requests(status=InfoRequestStatus.SENT)
        
        assert request.id not in [r.id for r in draft_requests]
        assert request.id in [r.id for r in sent_requests]


# ============================================================================
# Request Status Tests
# ============================================================================


class TestRequestStatusTransitions:
    """Tests for request status transitions."""
    
    def test_mark_request_sent(self, service, sample_rfq_data):
        """Test marking request as sent."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        updated = service.mark_request_sent(request.id)
        
        assert updated.status == InfoRequestStatus.SENT
        assert updated.sent_at is not None
    
    def test_mark_request_acknowledged(self, service, sample_rfq_data):
        """Test marking request as acknowledged."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        service.mark_request_sent(request.id)
        updated = service.mark_request_acknowledged(request.id)
        
        assert updated.status == InfoRequestStatus.ACKNOWLEDGED
        assert updated.acknowledged_at is not None
    
    def test_mark_request_completed(self, service, sample_rfq_data):
        """Test marking request as completed."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Complete with resolved fields
        field_id = result.missing_fields[0].id
        resolved = {field_id: "Resolved value"}
        
        updated = service.mark_request_completed(request.id, resolved_fields=resolved)
        
        assert updated.status == InfoRequestStatus.COMPLETED
        assert updated.completed_at is not None
    
    def test_cancel_request(self, service, sample_rfq_data):
        """Test cancelling a request."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        updated = service.cancel_request(request.id)
        
        assert updated.status == InfoRequestStatus.CANCELLED
    
    def test_status_transition_nonexistent_request(self, service):
        """Test status transition on nonexistent request."""
        result = service.mark_request_sent(uuid4())
        assert result is None


# ============================================================================
# Reminder Tests
# ============================================================================


class TestReminders:
    """Tests for reminder functionality."""
    
    def test_increment_reminder(self, service, sample_rfq_data):
        """Test incrementing reminder count."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        initial_count = request.reminder_count
        
        updated = service.increment_reminder(request.id)
        
        assert updated.reminder_count == initial_count + 1
    
    def test_reminder_stops_at_max(self, service, sample_rfq_data):
        """Test that reminders stop at max count."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Increment to max
        for _ in range(request.max_reminders):
            service.increment_reminder(request.id)
        
        # Should have no next reminder
        updated = service.get_info_request(request.id)
        assert updated.next_reminder_at is None
    
    def test_get_requests_needing_reminders(self, service, sample_rfq_data):
        """Test getting requests that need reminders."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Mark as sent and set past reminder time
        service.mark_request_sent(request.id)
        request.next_reminder_at = datetime.utcnow() - timedelta(hours=1)
        
        needing_reminders = service.get_requests_needing_reminders()
        
        assert request.id in [r.id for r in needing_reminders]


# ============================================================================
# Expiration Tests
# ============================================================================


class TestExpiration:
    """Tests for request expiration."""
    
    def test_get_expired_requests(self, service, sample_rfq_data):
        """Test getting expired requests."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Mark as sent and set past expiry
        service.mark_request_sent(request.id)
        request.expires_at = datetime.utcnow() - timedelta(days=1)
        
        expired = service.get_expired_requests()
        
        assert request.id in [r.id for r in expired]
    
    def test_expire_requests(self, service, sample_rfq_data):
        """Test expiring requests."""
        result = service.analyze_rfq(sample_rfq_data)
        
        request = service.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Mark as sent and set past expiry
        service.mark_request_sent(request.id)
        request.expires_at = datetime.utcnow() - timedelta(days=1)
        
        count = service.expire_requests()
        
        assert count >= 1
        
        updated = service.get_info_request(request.id)
        assert updated.status == InfoRequestStatus.EXPIRED


# ============================================================================
# Task Tests
# ============================================================================


class TestTaskManagement:
    """Tests for task management."""
    
    def test_create_tasks_for_missing_fields(self, service, sample_rfq_data):
        """Test creating tasks for missing fields."""
        result = service.analyze_rfq(sample_rfq_data)
        
        tasks = service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
        )
        
        assert len(tasks) == len(result.missing_fields)
        
        for task in tasks:
            assert task.rfq_id == sample_rfq_data.rfq_id
            assert task.status == TaskStatus.OPEN
            assert task.due_date >= date.today()
    
    def test_create_tasks_with_assignment(self, service, sample_rfq_data):
        """Test creating tasks with user assignment."""
        result = service.analyze_rfq(sample_rfq_data)
        assigned_to = uuid4()
        
        tasks = service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
            assigned_to=assigned_to,
        )
        
        assert all(t.assigned_to == assigned_to for t in tasks)
    
    def test_get_task(self, service, sample_rfq_data):
        """Test getting a task by ID."""
        result = service.analyze_rfq(sample_rfq_data)
        
        tasks = service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
        )
        
        task = tasks[0]
        retrieved = service.get_task(task.id)
        
        assert retrieved is not None
        assert retrieved.id == task.id
    
    def test_list_tasks_by_rfq(self, service, sample_rfq_data):
        """Test listing tasks by RFQ."""
        result = service.analyze_rfq(sample_rfq_data)
        
        service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
        )
        
        tasks = service.list_tasks(rfq_id=sample_rfq_data.rfq_id)
        
        assert len(tasks) >= len(result.missing_fields)
        assert all(t.rfq_id == sample_rfq_data.rfq_id for t in tasks)
    
    def test_list_tasks_by_assigned_user(self, service, sample_rfq_data):
        """Test listing tasks by assigned user."""
        result = service.analyze_rfq(sample_rfq_data)
        user_id = uuid4()
        
        service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
            assigned_to=user_id,
        )
        
        tasks = service.list_tasks(assigned_to=user_id)
        
        assert len(tasks) >= len(result.missing_fields)
    
    def test_complete_task(self, service, sample_rfq_data):
        """Test completing a task."""
        result = service.analyze_rfq(sample_rfq_data)
        
        tasks = service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
        )
        
        task = tasks[0]
        completed_by = uuid4()
        
        updated = service.complete_task(task.id, completed_by=completed_by, notes="Done")
        
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.completed_by == completed_by
        assert updated.notes == "Done"
    
    def test_update_task_status(self, service, sample_rfq_data):
        """Test updating task status."""
        result = service.analyze_rfq(sample_rfq_data)
        
        tasks = service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
        )
        
        task = tasks[0]
        
        updated = service.update_task_status(task.id, TaskStatus.IN_PROGRESS)
        
        assert updated.status == TaskStatus.IN_PROGRESS


# ============================================================================
# Full Workflow Tests
# ============================================================================


class TestFullWorkflow:
    """Tests for the complete workflow."""
    
    def test_process_rfq_full_workflow(self, service, sample_rfq_data):
        """Test the complete process_rfq workflow."""
        created_by = uuid4()
        assigned_to = uuid4()
        
        analysis, request, tasks = service.process_rfq(
            rfq_data=sample_rfq_data,
            sender_name="Sales Rep",
            created_by=created_by,
            sender_title="Senior Rep",
            assigned_to=assigned_to,
        )
        
        # Verify analysis
        assert analysis.missing_count > 0
        
        # Verify request was created
        assert request is not None
        assert request.status == InfoRequestStatus.DRAFT
        assert len(request.missing_fields) == analysis.missing_count
        
        # Verify tasks were created
        assert len(tasks) == analysis.missing_count
        assert all(t.assigned_to == assigned_to for t in tasks)
        assert all(t.linked_info_request_id == request.id for t in tasks)
    
    def test_process_rfq_no_auto_request(self, service, sample_rfq_data):
        """Test process_rfq without auto-creating request."""
        analysis, request, tasks = service.process_rfq(
            rfq_data=sample_rfq_data,
            sender_name="Rep",
            created_by=uuid4(),
            auto_create_request=False,
        )
        
        assert analysis.missing_count > 0
        assert request is None
        # Tasks should still be created if config allows
    
    def test_process_rfq_no_auto_tasks(self, service, sample_rfq_data):
        """Test process_rfq without auto-creating tasks."""
        # Create service with tasks disabled
        config = WorkflowConfig(auto_create_tasks=False)
        svc = MissingInfoWorkflowService(config=config)
        
        analysis, request, tasks = svc.process_rfq(
            rfq_data=sample_rfq_data,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        assert analysis.missing_count > 0
        assert request is not None
        assert len(tasks) == 0
    
    def test_process_complete_rfq(self, service, complete_rfq_data):
        """Test processing a complete RFQ."""
        analysis, request, tasks = service.process_rfq(
            rfq_data=complete_rfq_data,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        assert analysis.missing_count == 0
        assert analysis.can_transition is True
        assert request is None  # No request needed
        assert len(tasks) == 0  # No tasks needed


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_singleton_instance(self):
        """Test getting singleton instance."""
        reset_missing_info_workflow_service()
        
        svc1 = get_missing_info_workflow_service()
        svc2 = get_missing_info_workflow_service()
        
        assert svc1 is svc2
    
    def test_reset_singleton(self):
        """Test resetting singleton instance."""
        svc1 = get_missing_info_workflow_service()
        
        reset_missing_info_workflow_service()
        
        svc2 = get_missing_info_workflow_service()
        
        assert svc1 is not svc2


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_analyze_rfq_no_fields(self, service):
        """Test analyzing RFQ with all defaults (many missing)."""
        rfq = RFQData(
            rfq_id=uuid4(),
            rfq_number="RFQ-EMPTY",
            customer_name="Empty Corp",
            contact_name=None,
            contact_email=None,
            product_name=None,
            part_number=None,
        )
        
        result = service.analyze_rfq(rfq)
        
        # Should have many missing fields
        assert result.missing_count > 10
        assert result.completeness_score < 50.0
        assert result.can_transition is False  # Blocking fields missing
    
    def test_task_priority_matches_field_priority(self, service, sample_rfq_data):
        """Test that task priority matches the missing field priority."""
        result = service.analyze_rfq(sample_rfq_data)
        
        tasks = service.create_tasks_for_missing_fields(
            rfq_id=sample_rfq_data.rfq_id,
            missing_fields=result.missing_fields,
        )
        
        for task in tasks:
            # Find the corresponding missing field
            mf = next(m for m in result.missing_fields if m.id == task.missing_field_id)
            assert task.priority == mf.priority
    
    def test_email_with_no_missing_fields(self, service, complete_rfq_data):
        """Test generating email with no missing fields."""
        subject, body = service.generate_email_text(
            rfq_data=complete_rfq_data,
            missing_fields=[],
            sender_name="Rep",
        )
        
        # Should still generate valid email
        assert subject != ""
        assert body != ""
    
    def test_multiple_rfqs_isolation(self, service):
        """Test that multiple RFQs are properly isolated."""
        rfq1 = RFQData(
            rfq_id=uuid4(),
            rfq_number="RFQ-001",
            customer_name="Corp 1",
            contact_name=None,
            contact_email=None,
            product_name=None,
            part_number=None,
        )
        
        rfq2 = RFQData(
            rfq_id=uuid4(),
            rfq_number="RFQ-002",
            customer_name="Corp 2",
            contact_name=None,
            contact_email=None,
            product_name=None,
            part_number=None,
        )
        
        result1 = service.analyze_rfq(rfq1)
        result2 = service.analyze_rfq(rfq2)
        
        # Create tasks for both
        tasks1 = service.create_tasks_for_missing_fields(
            rfq_id=rfq1.rfq_id,
            missing_fields=result1.missing_fields,
        )
        
        tasks2 = service.create_tasks_for_missing_fields(
            rfq_id=rfq2.rfq_id,
            missing_fields=result2.missing_fields,
        )
        
        # List by RFQ should be isolated
        listed1 = service.list_tasks(rfq_id=rfq1.rfq_id)
        listed2 = service.list_tasks(rfq_id=rfq2.rfq_id)
        
        assert all(t.rfq_id == rfq1.rfq_id for t in listed1)
        assert all(t.rfq_id == rfq2.rfq_id for t in listed2)
    
    def test_reminder_frequency_daily(self, service, sample_rfq_data):
        """Test daily reminder frequency scheduling."""
        config = WorkflowConfig(default_reminder_frequency=ReminderFrequency.DAILY)
        svc = MissingInfoWorkflowService(config=config)
        
        result = svc.analyze_rfq(sample_rfq_data)
        
        request = svc.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Next reminder should be ~1 day from now
        assert request.next_reminder_at is not None
        delta = request.next_reminder_at - datetime.utcnow()
        assert delta.days >= 0 and delta.days <= 1
    
    def test_reminder_frequency_weekly(self, service, sample_rfq_data):
        """Test weekly reminder frequency scheduling."""
        config = WorkflowConfig(default_reminder_frequency=ReminderFrequency.WEEKLY)
        svc = MissingInfoWorkflowService(config=config)
        
        result = svc.analyze_rfq(sample_rfq_data)
        
        request = svc.create_info_request(
            rfq_data=sample_rfq_data,
            missing_fields=result.missing_fields,
            sender_name="Rep",
            created_by=uuid4(),
        )
        
        # Next reminder should be ~7 days from now
        assert request.next_reminder_at is not None
        delta = request.next_reminder_at - datetime.utcnow()
        assert delta.days >= 6 and delta.days <= 7
