"""
Comprehensive tests for RFQ Completeness Service.

Tests the scoring algorithm, field validation, qualification gate logic,
email generation, and task generation.
"""

import pytest
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sensei.services.sales.rfq_completeness import (
    RFQCompletenessService,
    CompletenessResult,
    MissingField,
    FieldCategory,
    RFQ_FIELD_DEFINITIONS,
)


# =============================================================================
# Mock RFQ for Testing
# =============================================================================


@dataclass
class MockRFQ:
    """Mock RFQ object for testing completeness calculations."""
    
    # Required fields
    account_id: Optional[str] = None
    title: Optional[str] = None
    quantity: Optional[int] = None
    due_date: Optional[date] = None
    
    # Important fields
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    drawing_number: Optional[str] = None
    material_spec: Optional[str] = None
    annual_volume: Optional[int] = None
    contact_id: Optional[str] = None
    primary_process: Optional[str] = None
    delivery_terms: Optional[str] = None
    
    # Optional fields
    target_price: Optional[Decimal] = None
    finish_requirements: Optional[str] = None
    tolerance_requirements: Optional[str] = None
    quality_requirements: Optional[str] = None
    packaging_requirements: Optional[str] = None
    delivery_location: Optional[str] = None
    lead_time_required: Optional[int] = None
    certifications_required: Optional[str] = None
    description: Optional[str] = None
    
    # Other fields (for context)
    rfq_number: str = "RFQ-2024-001"
    status: str = "draft"


# =============================================================================
# Service Initialization Tests
# =============================================================================


class TestServiceInitialization:
    """Test service initialization and configuration."""
    
    def test_default_initialization(self):
        """Test service initializes with default threshold."""
        service = RFQCompletenessService()
        assert service.qualification_threshold == 70
        assert len(service.field_definitions) == 21
    
    def test_custom_threshold(self):
        """Test service can be initialized with custom threshold."""
        service = RFQCompletenessService(qualification_threshold=80)
        assert service.qualification_threshold == 80
    
    def test_zero_threshold(self):
        """Test service with zero threshold."""
        service = RFQCompletenessService(qualification_threshold=0)
        assert service.qualification_threshold == 0
    
    def test_hundred_threshold(self):
        """Test service with 100% threshold."""
        service = RFQCompletenessService(qualification_threshold=100)
        assert service.qualification_threshold == 100
    
    def test_field_definitions_structure(self):
        """Test field definitions have correct structure."""
        service = RFQCompletenessService()
        
        for definition in service.field_definitions:
            assert "weight" in definition
            assert "category" in definition
            assert "display_name" in definition
            assert "description" in definition
            assert "field_name" in definition
            assert isinstance(definition["weight"], int)
            assert isinstance(definition["category"], FieldCategory)
            assert isinstance(definition["display_name"], str)
            assert isinstance(definition["description"], str)


# =============================================================================
# Completeness Calculation Tests
# =============================================================================


class TestCompletenessCalculation:
    """Test completeness score calculations."""
    
    def test_empty_rfq_score(self):
        """Test score for RFQ with no fields filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ()
        
        result = service.calculate_completeness(rfq)
        
        assert result.score == 0
        assert len(result.missing_fields) == 21
        assert result.earned_weight == 0
        assert result.can_qualify is False
        assert result.requires_override is True
    
    def test_fully_complete_rfq(self):
        """Test score for RFQ with all fields filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            # Required
            account_id=str(uuid4()),
            title="Test Part RFQ",
            quantity=1000,
            due_date=date.today() + timedelta(days=30),
            # Important
            part_number="PN-12345",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Aluminum 6061-T6",
            annual_volume=10000,
            contact_id=str(uuid4()),
            primary_process="CNC Machining",
            delivery_terms="FOB Origin",
            # Optional
            target_price=Decimal("25.00"),
            finish_requirements="Anodize Black",
            tolerance_requirements="+/- 0.005",
            quality_requirements="ISO 9001",
            packaging_requirements="Individual bags",
            delivery_location="Plant A",
            lead_time_required=14,
            certifications_required="NADCAP",
            description="Test widget for assembly line",
        )
        
        result = service.calculate_completeness(rfq)
        
        assert result.score == 100
        assert len(result.missing_fields) == 0
        assert len(result.filled_fields) == 21
        assert result.can_qualify is True
        assert result.requires_override is False
    
    def test_required_fields_only(self):
        """Test score with only required fields filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        
        result = service.calculate_completeness(rfq)
        
        # Required fields: 15 + 10 + 15 + 10 = 50 weight
        # Total weight = 120
        # Score = 50/120 * 100 = 41.67, rounded to 42
        assert result.score == 42
        assert len(result.filled_fields) == 4
        assert len(result.missing_fields) == 17
        
        # Check that no required fields are missing
        required_missing = [
            f for f in result.missing_fields 
            if f.category == FieldCategory.REQUIRED
        ]
        assert len(required_missing) == 0
    
    def test_important_fields_add_to_score(self):
        """Test that important fields contribute to the score."""
        service = RFQCompletenessService()
        
        # Just required fields
        rfq_basic = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        result_basic = service.calculate_completeness(rfq_basic)
        
        # Required + important fields
        rfq_with_important = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
            part_number="PN-123",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Steel",
            annual_volume=5000,
            contact_id=str(uuid4()),
            primary_process="Machining",
            delivery_terms="FOB",
        )
        result_with_important = service.calculate_completeness(rfq_with_important)
        
        assert result_with_important.score > result_basic.score
        # Required = 50, Important = 48, Total earned = 98, Score = 82%
        assert result_with_important.score == 82
    
    def test_optional_fields_contribute_to_score(self):
        """Test that optional fields also contribute to score."""
        service = RFQCompletenessService()
        
        # Required + important
        rfq_no_optional = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
            part_number="PN-123",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Steel",
            annual_volume=5000,
            contact_id=str(uuid4()),
            primary_process="Machining",
            delivery_terms="FOB",
        )
        
        # Required + important + optional
        rfq_with_optional = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
            part_number="PN-123",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Steel",
            annual_volume=5000,
            contact_id=str(uuid4()),
            primary_process="Machining",
            delivery_terms="FOB",
            target_price=Decimal("10.00"),
            finish_requirements="Chrome",
        )
        
        result_no_optional = service.calculate_completeness(rfq_no_optional)
        result_with_optional = service.calculate_completeness(rfq_with_optional)
        
        assert result_with_optional.score > result_no_optional.score
    
    def test_zero_quantity_counts_as_filled(self):
        """Test that zero quantity is considered a filled value."""
        service = RFQCompletenessService()
        rfq = MockRFQ(quantity=0)
        
        result = service.calculate_completeness(rfq)
        
        assert "quantity" in result.filled_fields
    
    def test_empty_string_counts_as_missing(self):
        """Test that empty string is considered missing."""
        service = RFQCompletenessService()
        rfq = MockRFQ(title="", part_number="")
        
        result = service.calculate_completeness(rfq)
        
        assert "title" not in result.filled_fields
        assert "part_number" not in result.filled_fields
    
    def test_whitespace_string_counts_as_missing(self):
        """Test that whitespace-only string is considered missing."""
        service = RFQCompletenessService()
        rfq = MockRFQ(title="   ", part_number="\t\n")
        
        result = service.calculate_completeness(rfq)
        
        assert "title" not in result.filled_fields
        assert "part_number" not in result.filled_fields


# =============================================================================
# Missing Fields Tests
# =============================================================================


class TestMissingFields:
    """Test missing field tracking."""
    
    def test_missing_fields_have_correct_attributes(self):
        """Test that missing fields have all required attributes."""
        service = RFQCompletenessService()
        rfq = MockRFQ()  # All fields empty
        
        result = service.calculate_completeness(rfq)
        
        for field in result.missing_fields:
            assert isinstance(field, MissingField)
            assert field.field_name is not None
            assert field.display_name is not None
            assert field.category in [FieldCategory.REQUIRED, FieldCategory.IMPORTANT, FieldCategory.OPTIONAL]
            assert field.weight > 0
            assert field.description is not None
    
    def test_missing_fields_categorization(self):
        """Test that missing fields are correctly categorized."""
        service = RFQCompletenessService()
        rfq = MockRFQ()  # All fields empty
        
        result = service.calculate_completeness(rfq)
        
        required = [f for f in result.missing_fields if f.category == FieldCategory.REQUIRED]
        important = [f for f in result.missing_fields if f.category == FieldCategory.IMPORTANT]
        optional = [f for f in result.missing_fields if f.category == FieldCategory.OPTIONAL]
        
        assert len(required) == 4  # account_id, title, quantity, due_date
        assert len(important) == 8  # 8 important fields
        assert len(optional) == 9  # 9 optional fields
    
    def test_missing_field_to_dict(self):
        """Test MissingField to_dict conversion."""
        field = MissingField(
            field_name="part_number",
            display_name="Part Number",
            category=FieldCategory.IMPORTANT,
            weight=8,
            description="Customer part number",
        )
        
        d = field.to_dict()
        
        assert d["field_name"] == "part_number"
        assert d["display_name"] == "Part Number"
        assert d["category"] == "important"  # lowercase per enum value
        assert d["weight"] == 8
        assert d["description"] == "Customer part number"


# =============================================================================
# Qualification Gate Tests
# =============================================================================


class TestQualificationGate:
    """Test qualification transition logic."""
    
    def test_can_qualify_with_full_score(self):
        """Test that RFQ with full score can qualify."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test Part RFQ",
            quantity=1000,
            due_date=date.today() + timedelta(days=30),
            part_number="PN-12345",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Steel",
            annual_volume=10000,
            contact_id=str(uuid4()),
            primary_process="CNC",
            delivery_terms="FOB",
        )
        
        can_qualify, error = service.can_transition_to_qualification(rfq)
        
        assert can_qualify is True
        assert error is None
    
    def test_cannot_qualify_missing_required_fields(self):
        """Test that RFQ cannot qualify without required fields."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            # Missing account_id (required)
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        
        can_qualify, error = service.can_transition_to_qualification(rfq)
        
        assert can_qualify is False
        # Score is too low (29%), so that error shows before required field check
        assert "below qualification threshold" in error or "Score" in error
    
    def test_cannot_qualify_low_score(self):
        """Test that RFQ cannot qualify with low score."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )  # Score = 42%, below 70% threshold
        
        can_qualify, error = service.can_transition_to_qualification(rfq)
        
        assert can_qualify is False
        assert "Score" in error or "below" in error
    
    def test_can_qualify_with_override(self):
        """Test that override allows qualification below threshold."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )  # Score = 42%, below 70% threshold
        
        can_qualify, error = service.can_transition_to_qualification(
            rfq,
            allow_override=True,
            override_rationale="Customer is urgent, will provide details later",
        )
        
        assert can_qualify is True
        assert error is None
    
    def test_override_without_rationale_fails(self):
        """Test that override without rationale fails."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        
        can_qualify, error = service.can_transition_to_qualification(
            rfq,
            allow_override=True,
            override_rationale="",  # Empty rationale
        )
        
        assert can_qualify is False
        assert "rationale" in error.lower()
    
    def test_override_can_bypass_required_fields(self):
        """Test that override CAN bypass missing required fields (GM authority)."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            # Missing all required fields
        )
        
        # With override, GM can push it through despite missing required fields
        can_qualify, error = service.can_transition_to_qualification(
            rfq,
            allow_override=True,
            override_rationale="Urgent request from executive customer - will obtain details post-qualification",
        )
        
        assert can_qualify is True
        assert error is None
    
    def test_custom_threshold_affects_qualification(self):
        """Test that custom threshold changes qualification requirements."""
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )  # Score = 42%
        
        # With 50% threshold - cannot qualify
        service_high = RFQCompletenessService(qualification_threshold=50)
        can_qualify, _ = service_high.can_transition_to_qualification(rfq)
        assert can_qualify is False
        
        # With 40% threshold - can qualify
        service_low = RFQCompletenessService(qualification_threshold=40)
        can_qualify, _ = service_low.can_transition_to_qualification(rfq)
        assert can_qualify is True


# =============================================================================
# Email Generation Tests
# =============================================================================


class TestEmailGeneration:
    """Test missing info email generation."""
    
    def test_email_generation_with_missing_fields(self):
        """Test email is generated for missing fields."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Widget RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        
        result = service.calculate_completeness(rfq)
        email = result.generate_missing_info_email("Acme Corp", "RFQ-2024-001")
        
        assert "Acme Corp" in email
        assert "RFQ-2024-001" in email
        assert "REQUIRED" in email or "Part Number" in email
    
    def test_email_generation_no_missing_fields(self):
        """Test email when no fields are missing."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
            part_number="PN-123",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Steel",
            annual_volume=5000,
            contact_id=str(uuid4()),
            primary_process="Machining",
            delivery_terms="FOB",
            target_price=Decimal("10.00"),
            finish_requirements="Chrome",
            tolerance_requirements="+/- 0.01",
            quality_requirements="ISO 9001",
            packaging_requirements="Box",
            delivery_location="Plant A",
            lead_time_required=7,
            certifications_required="IATF",
            description="Test widget",
        )
        
        result = service.calculate_completeness(rfq)
        email = result.generate_missing_info_email("Acme Corp", "RFQ-2024-001")
        
        # When complete, no email is needed - returns empty string
        assert email == ""
    
    def test_email_separates_required_and_important(self):
        """Test email categorizes missing info correctly."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            # Only account_id filled
            account_id=str(uuid4()),
        )
        
        result = service.calculate_completeness(rfq)
        email = result.generate_missing_info_email("Test Customer", "RFQ-001")
        
        # Should have required fields section
        assert "Title" in email or "title" in email
        assert "Quantity" in email or "quantity" in email


# =============================================================================
# Task Generation Tests
# =============================================================================


class TestTaskGeneration:
    """Test task generation for missing fields."""
    
    def test_task_generation_for_missing_fields(self):
        """Test tasks are generated for missing fields."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        
        rfq_id = uuid4()
        assigned_to_id = uuid4()
        
        tasks = service.generate_missing_info_tasks(rfq, rfq_id, assigned_to_id)
        
        # Should generate tasks for important missing fields (not required since they're filled)
        assert len(tasks) > 0
        
        for task in tasks:
            assert "title" in task
            assert "description" in task
            assert "entity_id" in task  # Uses entity_id, not rfq_id
            assert task["entity_id"] == str(rfq_id)
            assert task["assigned_to_id"] == assigned_to_id
    
    def test_task_generation_no_missing_fields(self):
        """Test no tasks when all fields are filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
            part_number="PN-123",
            part_name="Widget",
            drawing_number="DWG-001",
            material_spec="Steel",
            annual_volume=5000,
            contact_id=str(uuid4()),
            primary_process="Machining",
            delivery_terms="FOB",
            target_price=Decimal("10.00"),
            finish_requirements="Chrome",
            tolerance_requirements="+/- 0.01",
            quality_requirements="ISO 9001",
            packaging_requirements="Box",
            delivery_location="Plant A",
            lead_time_required=7,
            certifications_required="IATF",
            description="Test widget",
        )
        
        tasks = service.generate_missing_info_tasks(rfq, uuid4(), uuid4())
        
        assert len(tasks) == 0
    
    def test_tasks_only_for_required_and_important(self):
        """Test tasks are only generated for required and important fields."""
        service = RFQCompletenessService()
        rfq = MockRFQ()  # All fields empty
        
        tasks = service.generate_missing_info_tasks(rfq, uuid4(), uuid4())
        
        # Should only have tasks for required (4) and important (8) = 12 tasks
        assert len(tasks) == 12
        
        # Verify no optional fields have tasks
        task_titles = [t["title"] for t in tasks]
        optional_fields = ["target_price", "finish_requirements", "tolerance_requirements"]
        for opt_field in optional_fields:
            assert not any(opt_field.replace("_", " ").title() in title for title in task_titles)
    
    def test_task_has_proper_structure(self):
        """Test task structure is correct for API consumption."""
        service = RFQCompletenessService()
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Test RFQ",
            quantity=100,
            due_date=date.today() + timedelta(days=30),
        )
        
        rfq_id = uuid4()
        assigned_to_id = uuid4()
        
        tasks = service.generate_missing_info_tasks(rfq, rfq_id, assigned_to_id)
        
        assert len(tasks) > 0
        task = tasks[0]
        
        # Check all expected fields
        assert "title" in task
        assert "description" in task
        assert "priority" in task
        assert "entity_type" in task
        assert "entity_id" in task
        assert "assigned_to_id" in task
        assert "tags" in task
        
        # Check values
        assert task["priority"] in ["high", "medium"]
        assert task["entity_type"] == "rfq"
        assert "missing-info" in task["tags"]


# =============================================================================
# Field Definitions Tests
# =============================================================================


class TestFieldDefinitions:
    """Test field definitions retrieval."""
    
    def test_get_field_definitions(self):
        """Test getting field definitions."""
        service = RFQCompletenessService()
        
        definitions = service.get_field_definitions()
        
        assert len(definitions) == 21
        
        for field in definitions:
            assert "field_name" in field
            assert "display_name" in field
            assert "category" in field
            assert "weight" in field
            assert "description" in field
    
    def test_field_definitions_weight_sum(self):
        """Test total weight of all fields."""
        service = RFQCompletenessService()
        
        definitions = service.get_field_definitions()
        total_weight = sum(f["weight"] for f in definitions)
        
        # Verify total weight matches expected
        assert total_weight == 120


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_none_rfq_attribute(self):
        """Test handling of None RFQ attribute gracefully."""
        service = RFQCompletenessService()
        
        # Create RFQ with explicit None values
        rfq = MockRFQ(
            account_id=None,
            title=None,
            quantity=None,
        )
        
        result = service.calculate_completeness(rfq)
        
        assert result.score >= 0
        assert result.score <= 100
    
    def test_decimal_zero_target_price(self):
        """Test that Decimal(0) is considered filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ(target_price=Decimal("0.00"))
        
        result = service.calculate_completeness(rfq)
        
        assert "target_price" in result.filled_fields
    
    def test_negative_quantity_counts_as_filled(self):
        """Test that negative quantity is still considered filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ(quantity=-1)
        
        result = service.calculate_completeness(rfq)
        
        # Negative is still a value, validation is separate concern
        assert "quantity" in result.filled_fields
    
    def test_past_due_date_counts_as_filled(self):
        """Test that past due date is considered filled."""
        service = RFQCompletenessService()
        rfq = MockRFQ(due_date=date.today() - timedelta(days=30))
        
        result = service.calculate_completeness(rfq)
        
        assert "due_date" in result.filled_fields
    
    def test_very_long_string_counts_as_filled(self):
        """Test handling of very long string values."""
        service = RFQCompletenessService()
        long_string = "A" * 10000
        rfq = MockRFQ(title=long_string, description=long_string)
        
        result = service.calculate_completeness(rfq)
        
        assert "title" in result.filled_fields
        assert "description" in result.filled_fields


# =============================================================================
# CompletenessResult Tests
# =============================================================================


class TestCompletenessResult:
    """Test CompletenessResult dataclass."""
    
    def test_result_immutability(self):
        """Test that result attributes work correctly."""
        result = CompletenessResult(
            score=75,
            total_weight=120,
            earned_weight=90,
            missing_fields=[],
            filled_fields=["field1", "field2"],
            can_qualify=True,
            requires_override=False,
            override_reason=None,
        )
        
        assert result.score == 75
        assert result.can_qualify is True
        assert len(result.filled_fields) == 2
    
    def test_result_with_missing_fields(self):
        """Test result with missing fields list."""
        missing = [
            MissingField(
                field_name="part_number",
                display_name="Part Number",
                category=FieldCategory.IMPORTANT,
                weight=8,
                description="Customer part number",
            )
        ]
        
        result = CompletenessResult(
            score=50,
            total_weight=120,
            earned_weight=60,
            missing_fields=missing,
            filled_fields=["title"],
            can_qualify=False,
            requires_override=True,
            override_reason="Score below threshold",
        )
        
        assert len(result.missing_fields) == 1
        assert result.missing_fields[0].field_name == "part_number"
        assert result.override_reason == "Score below threshold"


# =============================================================================
# Integration-Style Tests
# =============================================================================


class TestCompletenessWorkflow:
    """Test full completeness workflow scenarios."""
    
    def test_new_rfq_workflow(self):
        """Test typical new RFQ completeness workflow."""
        service = RFQCompletenessService()
        rfq_id = uuid4()
        user_id = uuid4()
        
        # Step 1: New RFQ with minimal data
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="New Widget RFQ",
        )
        
        result = service.calculate_completeness(rfq)
        assert result.score < 30  # Very incomplete
        assert result.can_qualify is False
        
        # Step 2: Generate tasks for follow-up
        tasks = service.generate_missing_info_tasks(rfq, rfq_id, user_id)
        assert len(tasks) > 0
        
        # Step 3: Try to qualify - should fail
        can_qualify, error = service.can_transition_to_qualification(rfq)
        assert can_qualify is False
    
    def test_progressive_completion_workflow(self):
        """Test RFQ getting progressively more complete."""
        service = RFQCompletenessService()
        
        # Start minimal
        rfq = MockRFQ(account_id=str(uuid4()))
        result1 = service.calculate_completeness(rfq)
        
        # Add required fields
        rfq.title = "Widget RFQ"
        rfq.quantity = 1000
        rfq.due_date = date.today() + timedelta(days=30)
        result2 = service.calculate_completeness(rfq)
        
        # Add important fields
        rfq.part_number = "PN-123"
        rfq.part_name = "Widget"
        rfq.material_spec = "Steel"
        rfq.annual_volume = 10000
        result3 = service.calculate_completeness(rfq)
        
        # Scores should increase
        assert result2.score > result1.score
        assert result3.score > result2.score
    
    def test_qualification_with_gm_override(self):
        """Test GM override workflow for urgent RFQ."""
        service = RFQCompletenessService()
        
        # RFQ with only required fields (below threshold)
        rfq = MockRFQ(
            account_id=str(uuid4()),
            title="Urgent Customer RFQ",
            quantity=500,
            due_date=date.today() + timedelta(days=7),
        )
        
        result = service.calculate_completeness(rfq)
        assert result.requires_override is True
        
        # Normal qualification fails
        can_qualify, error = service.can_transition_to_qualification(rfq)
        assert can_qualify is False
        
        # With override succeeds
        can_qualify, error = service.can_transition_to_qualification(
            rfq,
            allow_override=True,
            override_rationale="Critical customer, expedited process approved by GM",
        )
        assert can_qualify is True
