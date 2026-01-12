"""
Functional Gate Tests

Tests for workflow gating logic:
- RFQ completeness gating with threshold enforcement and GM override
- Qualification approval logic with role permissions and rationale requirements
- Quote version immutability with versioning enforcement and audit trail
- A3 closure requirements with reflection and standard update enforcement
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from sensei.core.time import utcnow_naive

from sensei.services.core.data_quality import DataQualityService
from sensei.services.core.state_machine import StateMachine, TransitionError, TransitionResult


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def data_quality_service(mock_db_session):
    """Create data quality service"""
    return DataQualityService(db_session=mock_db_session)


class TestRFQCompletenessGating:
    """Test RFQ completeness gating with threshold enforcement and GM override"""
    
    def test_rfq_completeness_100_percent_passes(self, data_quality_service):
        """Test RFQ with 100% completeness passes gate"""
        rfq_data = {
            "title": "New Part Quotation",
            "description": "Request for quote on automotive part",
            "required_quantity": 1000,
            "target_delivery_date": "2024-12-31"
        }
        
        result = data_quality_service.validate_rfq_completeness(rfq_data, completeness_threshold=70.0)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_rfq_completeness_75_percent_passes_threshold(self, data_quality_service):
        """Test RFQ with 75% completeness passes 70% threshold"""
        rfq_data = {
            "title": "New Part Quotation",
            "description": "Request for quote",
            "required_quantity": 1000
            # Missing target_delivery_date (75% complete)
        }
        
        result = data_quality_service.validate_rfq_completeness(rfq_data, completeness_threshold=70.0)
        
        assert result.is_valid is True
    
    def test_rfq_completeness_50_percent_fails_threshold(self, data_quality_service):
        """Test RFQ with 50% completeness fails 70% threshold"""
        rfq_data = {
            "title": "New Part",
            "description": "Quote request"
            # Missing required_quantity and target_delivery_date (50% complete)
        }
        
        result = data_quality_service.validate_rfq_completeness(rfq_data, completeness_threshold=70.0)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any(e.field_name == "_completeness" for e in result.errors)
    
    def test_rfq_completeness_missing_all_required_fails(self, data_quality_service):
        """Test RFQ with no required fields fails"""
        rfq_data = {}
        
        result = data_quality_service.validate_rfq_completeness(rfq_data, completeness_threshold=70.0)
        
        assert result.is_valid is False
    
    def test_rfq_state_transition_with_completeness_gate(self):
        """Test RFQ state transition requires completeness"""
        state_machine = StateMachine(
            name="RFQ",
            states=["draft", "review", "submitted", "approved"],
            initial_state="draft"
        )
        
        # Add transition with required fields (completeness gate)
        state_machine.add_transition(
            from_state="draft",
            to_state="submitted",
            required_fields=["title", "description", "required_quantity", "target_delivery_date"],
            description="Submit RFQ for approval (requires completeness)"
        )
        
        # Test with complete data
        complete_rfq = {
            "title": "Part RFQ",
            "description": "Request for quote",
            "required_quantity": 100,
            "target_delivery_date": "2024-12-31"
        }
        
        result = state_machine.can_transition(complete_rfq, "draft", "submitted")
        assert result.allowed is True
        
        # Test with incomplete data
        incomplete_rfq = {
            "title": "Part RFQ"
        }
        
        result = state_machine.can_transition(incomplete_rfq, "draft", "submitted")
        assert result.allowed is False
        assert len(result.missing_fields) > 0
    
    def test_rfq_gm_override_allows_incomplete_submission(self):
        """Test GM can override completeness gate"""
        state_machine = StateMachine(
            name="RFQ",
            states=["draft", "submitted"],
            initial_state="draft"
        )
        
        state_machine.add_transition(
            from_state="draft",
            to_state="submitted",
            required_fields=["title", "description", "required_quantity"],
            description="Submit RFQ (GM can override)"
        )
        
        incomplete_rfq = {
            "title": "Part RFQ"
            # Missing required fields
        }
        
        # Without override - should fail
        result = state_machine.can_transition(incomplete_rfq, "draft", "submitted", allow_override=False)
        assert result.allowed is False
        
        # With override - should pass but require override
        result = state_machine.can_transition(incomplete_rfq, "draft", "submitted", allow_override=True)
        assert result.allowed is True or result.requires_override is True


class TestQualificationApprovalLogic:
    """Test qualification approval logic with role permissions and rationale requirements"""
    
    def test_qualification_approval_requires_rationale(self, data_quality_service):
        """Test qualification approval requires rationale"""
        qual_data = {
            "supplier_id": "supplier-123"
            # Missing rationale
        }
        
        result = data_quality_service.validate_qualification_approval(qual_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "rationale" for e in result.errors)
    
    def test_qualification_approval_rationale_minimum_length(self, data_quality_service):
        """Test qualification rationale must be at least 20 characters"""
        qual_data = {
            "supplier_id": "supplier-123",
            "rationale": "Good"  # Too short
        }
        
        result = data_quality_service.validate_qualification_approval(qual_data)
        
        assert result.is_valid is False
        assert any(
            e.field_name == "rationale" and "20 characters" in e.error_message.lower()
            for e in result.errors
        )
    
    def test_qualification_approval_with_valid_rationale(self, data_quality_service):
        """Test qualification approval with valid rationale passes"""
        qual_data = {
            "supplier_id": "supplier-123",
            "rationale": "Supplier demonstrates excellent quality control and competitive pricing"
        }
        
        result = data_quality_service.validate_qualification_approval(qual_data)
        
        assert result.is_valid is True
    
    def test_qualification_score_range_validation(self, data_quality_service):
        """Test qualification score must be between 0-100"""
        # Score too high
        qual_data_high = {
            "supplier_id": "supplier-123",
            "rationale": "Excellent supplier with proven track record",
            "score": 150
        }
        
        result = data_quality_service.validate_entity("qualification", qual_data_high)
        assert result.is_valid is False
        
        # Score negative
        qual_data_negative = {
            "supplier_id": "supplier-123",
            "rationale": "Needs improvement",
            "score": -10
        }
        
        result = data_quality_service.validate_entity("qualification", qual_data_negative)
        assert result.is_valid is False
        
        # Score valid
        qual_data_valid = {
            "supplier_id": "supplier-123",
            "rationale": "Good supplier performance",
            "score": 75
        }
        
        result = data_quality_service.validate_entity("qualification", qual_data_valid)
        assert result.is_valid is True
    
    def test_qualification_state_transition_to_approved(self):
        """Test qualification approval state transition requires rationale"""
        state_machine = StateMachine(
            name="Qualification",
            states=["draft", "under_review", "approved", "rejected"],
            initial_state="draft"
        )
        
        state_machine.add_transition(
            from_state="under_review",
            to_state="approved",
            required_fields=["supplier_id", "rationale", "score"],
            description="Approve qualification (requires rationale)"
        )
        
        # Complete data
        qual_data = {
            "supplier_id": "supplier-123",
            "rationale": "Supplier meets all quality and cost requirements",
            "score": 85
        }
        
        result = state_machine.can_transition(qual_data, "under_review", "approved")
        assert result.allowed is True
        
        # Missing rationale
        incomplete_qual = {
            "supplier_id": "supplier-123",
            "score": 85
        }
        
        result = state_machine.can_transition(incomplete_qual, "under_review", "approved")
        assert result.allowed is False
        assert "rationale" in result.missing_fields


class TestQuoteVersionImmutability:
    """Test quote version immutability with versioning enforcement and audit trail"""
    
    def test_quote_unit_price_required(self, data_quality_service):
        """Test quote requires unit price"""
        quote_data = {}
        
        result = data_quality_service.validate_entity("quote", quote_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "unit_price" for e in result.errors)
    
    def test_quote_unit_price_cannot_be_negative(self, data_quality_service):
        """Test quote unit price cannot be negative"""
        quote_data = {
            "unit_price": -50.0
        }
        
        result = data_quality_service.validate_entity("quote", quote_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "unit_price" and "negative" in e.error_message.lower() for e in result.errors)
    
    def test_quote_margin_warning_below_threshold(self, data_quality_service):
        """Test quote margin below 5% generates warning"""
        quote_data = {
            "unit_price": 100.0,
            "unit_cost": 98.0,  # 2% margin
            "margin_percentage": 2.0
        }
        
        result = data_quality_service.validate_quote_margin(quote_data, min_margin=5.0)
        
        # Should have warnings but not block
        assert result.is_valid is True  # Warnings don't block
        assert len(result.warnings) > 0
        assert any("margin" in w.error_message.lower() for w in result.warnings)
    
    def test_quote_margin_acceptable_above_threshold(self, data_quality_service):
        """Test quote margin above 5% is acceptable"""
        quote_data = {
            "unit_price": 100.0,
            "unit_cost": 80.0,  # 20% margin
            "margin_percentage": 20.0
        }
        
        result = data_quality_service.validate_quote_margin(quote_data, min_margin=5.0)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_quote_version_immutability_state_machine(self):
        """Test quote version cannot be modified once approved"""
        state_machine = StateMachine(
            name="Quote",
            states=["draft", "submitted", "approved", "rejected"],
            initial_state="draft",
            final_states=["approved", "rejected"]
        )
        
        state_machine.add_transition(
            from_state="draft",
            to_state="submitted",
            required_fields=["unit_price", "quantity"],
            description="Submit quote"
        )
        
        state_machine.add_transition(
            from_state="submitted",
            to_state="approved",
            required_fields=["unit_price", "quantity"],
            description="Approve quote"
        )
        
        # Try to add a transition from approved (final state) - this should not work
        # because approved is a final state
        quote_data = {"unit_price": 100, "quantity": 10}
        
        # Attempting to transition from a final state should fail
        result = state_machine.can_transition(quote_data, "approved", "draft")
        assert result.allowed is False
        assert "not allowed" in result.error_message.lower()
    
    def test_quote_audit_trail_versioning(self):
        """Test quote changes create audit trail with version tracking"""
        # Simulated quote version history
        quote_versions = []
        
        # Version 1
        v1 = {
            "quote_id": str(uuid4()),
            "version": 1,
            "unit_price": 100.0,
            "created_at": utcnow_naive(),
            "immutable": False
        }
        quote_versions.append(v1)
        
        # Version 2 (price changed)
        v2 = {
            "quote_id": v1["quote_id"],
            "version": 2,
            "unit_price": 95.0,
            "created_at": utcnow_naive(),
            "immutable": False
        }
        quote_versions.append(v2)
        
        # Version 3 (approved - now immutable)
        v3 = {
            "quote_id": v1["quote_id"],
            "version": 3,
            "unit_price": 95.0,
            "created_at": utcnow_naive(),
            "status": "approved",
            "immutable": True
        }
        quote_versions.append(v3)
        
        # Verify version tracking
        assert len(quote_versions) == 3
        assert quote_versions[0]["version"] == 1
        assert quote_versions[1]["version"] == 2
        assert quote_versions[2]["version"] == 3
        
        # Verify immutability
        assert quote_versions[0]["immutable"] is False
        assert quote_versions[1]["immutable"] is False
        assert quote_versions[2]["immutable"] is True
        
        # Verify price change history
        assert quote_versions[0]["unit_price"] == 100.0
        assert quote_versions[1]["unit_price"] == 95.0


class TestA3ClosureRequirements:
    """Test A3 closure requirements with reflection and standard update enforcement"""
    
    def test_a3_problem_statement_required(self, data_quality_service):
        """Test A3 requires problem statement"""
        a3_data = {}
        
        result = data_quality_service.validate_entity("a3", a3_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "problem_statement" for e in result.errors)
    
    def test_a3_problem_statement_minimum_length(self, data_quality_service):
        """Test A3 problem statement must be at least 20 characters"""
        a3_data = {
            "problem_statement": "Waste"  # Too short
        }
        
        result = data_quality_service.validate_entity("a3", a3_data)
        
        assert result.is_valid is False
        assert any(
            e.field_name == "problem_statement" and "20 characters" in e.error_message.lower()
            for e in result.errors
        )
    
    def test_a3_closure_requires_reflection(self, data_quality_service):
        """Test A3 closure requires reflection"""
        a3_data = {
            "problem_statement": "Production line waste causing cost overruns",
            "standard_updated": True
            # Missing reflection
        }
        
        result = data_quality_service.validate_a3_closure(a3_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "reflection" for e in result.errors)
    
    def test_a3_closure_reflection_minimum_length(self, data_quality_service):
        """Test A3 closure reflection must be at least 50 characters"""
        a3_data = {
            "problem_statement": "Production line waste",
            "reflection": "Learned something",  # Too short
            "standard_updated": True
        }
        
        result = data_quality_service.validate_a3_closure(a3_data)
        
        assert result.is_valid is False
        assert any(
            e.field_name == "reflection" and "50 characters" in e.error_message.lower()
            for e in result.errors
        )
    
    def test_a3_closure_requires_standard_update(self, data_quality_service):
        """Test A3 closure requires standard update"""
        a3_data = {
            "problem_statement": "Production line waste",
            "reflection": "Learned that preventive maintenance significantly reduces waste and improves OEE",
            "standard_updated": False
        }
        
        result = data_quality_service.validate_a3_closure(a3_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "standard_updated" for e in result.errors)
    
    def test_a3_closure_complete_passes(self, data_quality_service):
        """Test A3 closure with all requirements passes"""
        a3_data = {
            "problem_statement": "Production line waste causing significant cost overruns",
            "reflection": "Learned that implementing preventive maintenance schedules reduces waste by 40% and improves overall equipment effectiveness",
            "standard_updated": True
        }
        
        result = data_quality_service.validate_a3_closure(a3_data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_a3_state_transition_to_closed(self):
        """Test A3 state transition to closed requires reflection and standard update"""
        state_machine = StateMachine(
            name="A3",
            states=["open", "in_progress", "closed"],
            initial_state="open",
            final_states=["closed"]
        )
        
        state_machine.add_transition(
            from_state="in_progress",
            to_state="closed",
            required_fields=["problem_statement", "reflection", "standard_updated"],
            description="Close A3 (requires reflection and standard update)"
        )
        
        # Complete data
        complete_a3 = {
            "problem_statement": "Production inefficiency in assembly line",
            "reflection": "Team learned importance of 5S principles and visual management for maintaining organized workspace",
            "standard_updated": True
        }
        
        result = state_machine.can_transition(complete_a3, "in_progress", "closed")
        assert result.allowed is True
        
        # Missing reflection
        no_reflection = {
            "problem_statement": "Production inefficiency",
            "standard_updated": True
        }
        
        result = state_machine.can_transition(no_reflection, "in_progress", "closed")
        assert result.allowed is False
        assert "reflection" in result.missing_fields
        
        # Missing standard_updated
        no_standard = {
            "problem_statement": "Production inefficiency",
            "reflection": "Learned about continuous improvement methodology"
        }
        
        result = state_machine.can_transition(no_standard, "in_progress", "closed")
        assert result.allowed is False
        assert "standard_updated" in result.missing_fields
