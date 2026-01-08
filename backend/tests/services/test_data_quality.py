"""
Tests for Data Quality Validation Service

Validates field-level validation, required field enforcement, data type validation,
business rule validation, and validation error reporting.
"""

from unittest.mock import Mock

import pytest

from sensei.services.data_quality import (
    DataQualityService,
    Severity,
    ValidationError,
    ValidationResult,
    ValidationRule,
    ValidationType,
)


@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def service(mock_db_session):
    """Create data quality service"""
    return DataQualityService(db_session=mock_db_session)


class TestValidationRule:
    """Test ValidationRule dataclass"""
    
    def test_rule_creation(self):
        """Test creating validation rule"""
        rule = ValidationRule(
            field_name="email",
            validation_type=ValidationType.REQUIRED,
            severity=Severity.ERROR,
            error_message="Email is required"
        )
        
        assert rule.field_name == "email"
        assert rule.validation_type == ValidationType.REQUIRED
        assert rule.severity == Severity.ERROR
        assert rule.error_message == "Email is required"


class TestValidationError:
    """Test ValidationError dataclass"""
    
    def test_error_creation(self):
        """Test creating validation error"""
        error = ValidationError(
            field_name="price",
            validation_type=ValidationType.RANGE,
            severity=Severity.ERROR,
            error_message="Price must be positive",
            actual_value=-10,
            expected=">= 0"
        )
        
        assert error.field_name == "price"
        assert error.validation_type == ValidationType.RANGE
        assert error.severity == Severity.ERROR
        assert error.actual_value == -10


class TestValidationResult:
    """Test ValidationResult"""
    
    def test_result_creation(self):
        """Test creating validation result"""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert len(result.info) == 0
    
    def test_add_error(self):
        """Test adding error to result"""
        result = ValidationResult(is_valid=True)
        
        error = ValidationError(
            field_name="test",
            validation_type=ValidationType.REQUIRED,
            severity=Severity.ERROR,
            error_message="Test error"
        )
        
        result.add_error(error)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.has_errors is True
    
    def test_add_warning(self):
        """Test adding warning to result"""
        result = ValidationResult(is_valid=True)
        
        warning = ValidationError(
            field_name="test",
            validation_type=ValidationType.LENGTH,
            severity=Severity.WARNING,
            error_message="Test warning"
        )
        
        result.add_error(warning)
        
        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.has_errors is False
    
    def test_total_issues(self):
        """Test total issues count"""
        result = ValidationResult(is_valid=True)
        
        result.errors.append(ValidationError(
            field_name="f1",
            validation_type=ValidationType.REQUIRED,
            severity=Severity.ERROR,
            error_message="Error"
        ))
        
        result.warnings.append(ValidationError(
            field_name="f2",
            validation_type=ValidationType.LENGTH,
            severity=Severity.WARNING,
            error_message="Warning"
        ))
        
        assert result.total_issues == 2


class TestDataQualityService:
    """Test DataQualityService"""
    
    def test_service_initialization(self, service):
        """Test service initialization"""
        assert service.rules is not None
        assert "_global" in service.rules or len(service.rules) > 0
    
    def test_register_rule(self, service):
        """Test registering validation rule"""
        rule = ValidationRule(
            field_name="test_field",
            validation_type=ValidationType.REQUIRED,
            applies_to_entity="test_entity"
        )
        
        service.register_rule(rule)
        
        rules = service.get_rules_for_entity("test_entity")
        assert any(r.field_name == "test_field" for r in rules)
    
    def test_get_rules_for_entity(self, service):
        """Test getting rules for entity"""
        rules = service.get_rules_for_entity("rfq")
        
        assert len(rules) > 0
        assert all(r.applies_to_entity == "rfq" or r.applies_to_entity is None for r in rules)
    
    def test_get_rules_for_entity_with_state(self, service):
        """Test getting rules for entity with state"""
        rules = service.get_rules_for_entity("qualification", state="approved")
        
        # Should include rules without state restriction and rules for "approved" state
        assert len(rules) > 0
        assert any(r.field_name == "rationale" for r in rules)
    
    def test_validate_required_field_missing(self, service):
        """Test required field validation - missing value"""
        rule = ValidationRule(
            field_name="title",
            validation_type=ValidationType.REQUIRED,
            error_message="Title is required"
        )
        
        error = service.validate_field("title", None, rule)
        
        assert error is not None
        assert error.field_name == "title"
        assert error.validation_type == ValidationType.REQUIRED
    
    def test_validate_required_field_empty_string(self, service):
        """Test required field validation - empty string"""
        rule = ValidationRule(
            field_name="title",
            validation_type=ValidationType.REQUIRED,
            error_message="Title is required"
        )
        
        error = service.validate_field("title", "", rule)
        
        assert error is not None
    
    def test_validate_required_field_present(self, service):
        """Test required field validation - value present"""
        rule = ValidationRule(
            field_name="title",
            validation_type=ValidationType.REQUIRED,
            error_message="Title is required"
        )
        
        error = service.validate_field("title", "My Title", rule)
        
        assert error is None
    
    def test_validate_data_type_valid(self, service):
        """Test data type validation - valid type"""
        rule = ValidationRule(
            field_name="quantity",
            validation_type=ValidationType.DATA_TYPE,
            expected_type=int
        )
        
        error = service.validate_field("quantity", 10, rule)
        
        assert error is None
    
    def test_validate_data_type_invalid(self, service):
        """Test data type validation - invalid type"""
        rule = ValidationRule(
            field_name="quantity",
            validation_type=ValidationType.DATA_TYPE,
            expected_type=int
        )
        
        error = service.validate_field("quantity", "not_an_int", rule)
        
        assert error is not None
        assert error.validation_type == ValidationType.DATA_TYPE
    
    def test_validate_range_within_bounds(self, service):
        """Test range validation - within bounds"""
        rule = ValidationRule(
            field_name="price",
            validation_type=ValidationType.RANGE,
            min_value=0,
            max_value=1000
        )
        
        error = service.validate_field("price", 500, rule)
        
        assert error is None
    
    def test_validate_range_below_minimum(self, service):
        """Test range validation - below minimum"""
        rule = ValidationRule(
            field_name="price",
            validation_type=ValidationType.RANGE,
            min_value=0
        )
        
        error = service.validate_field("price", -10, rule)
        
        assert error is not None
        assert error.validation_type == ValidationType.RANGE
        assert error.actual_value == -10
    
    def test_validate_range_above_maximum(self, service):
        """Test range validation - above maximum"""
        rule = ValidationRule(
            field_name="score",
            validation_type=ValidationType.RANGE,
            max_value=100
        )
        
        error = service.validate_field("score", 150, rule)
        
        assert error is not None
    
    def test_validate_length_within_bounds(self, service):
        """Test length validation - within bounds"""
        rule = ValidationRule(
            field_name="title",
            validation_type=ValidationType.LENGTH,
            min_length=3,
            max_length=50
        )
        
        error = service.validate_field("title", "Valid Title", rule)
        
        assert error is None
    
    def test_validate_length_too_short(self, service):
        """Test length validation - too short"""
        rule = ValidationRule(
            field_name="title",
            validation_type=ValidationType.LENGTH,
            min_length=10
        )
        
        error = service.validate_field("title", "Short", rule)
        
        assert error is not None
        assert error.validation_type == ValidationType.LENGTH
    
    def test_validate_length_too_long(self, service):
        """Test length validation - too long"""
        rule = ValidationRule(
            field_name="code",
            validation_type=ValidationType.LENGTH,
            max_length=5
        )
        
        error = service.validate_field("code", "TOOLONG123", rule)
        
        assert error is not None
    
    def test_validate_enum_valid_value(self, service):
        """Test enum validation - valid value"""
        rule = ValidationRule(
            field_name="status",
            validation_type=ValidationType.ENUM,
            allowed_values=["draft", "submitted", "approved"]
        )
        
        error = service.validate_field("status", "draft", rule)
        
        assert error is None
    
    def test_validate_enum_invalid_value(self, service):
        """Test enum validation - invalid value"""
        rule = ValidationRule(
            field_name="status",
            validation_type=ValidationType.ENUM,
            allowed_values=["draft", "submitted", "approved"]
        )
        
        error = service.validate_field("status", "invalid", rule)
        
        assert error is not None
        assert error.validation_type == ValidationType.ENUM
    
    def test_validate_pattern_valid(self, service):
        """Test pattern validation - valid pattern"""
        rule = ValidationRule(
            field_name="email",
            validation_type=ValidationType.PATTERN,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        
        error = service.validate_field("email", "user@example.com", rule)
        
        assert error is None
    
    def test_validate_pattern_invalid(self, service):
        """Test pattern validation - invalid pattern"""
        rule = ValidationRule(
            field_name="email",
            validation_type=ValidationType.PATTERN,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )
        
        error = service.validate_field("email", "invalid-email", rule)
        
        assert error is not None
        assert error.validation_type == ValidationType.PATTERN
    
    def test_validate_custom_validator_pass(self, service):
        """Test custom validator - passing"""
        def is_even(value, context):
            return int(value) % 2 == 0
        
        rule = ValidationRule(
            field_name="count",
            validation_type=ValidationType.CUSTOM,
            custom_validator=is_even,
            error_message="Count must be even"
        )
        
        error = service.validate_field("count", 10, rule)
        
        assert error is None
    
    def test_validate_custom_validator_fail(self, service):
        """Test custom validator - failing"""
        def is_even(value, context):
            return int(value) % 2 == 0
        
        rule = ValidationRule(
            field_name="count",
            validation_type=ValidationType.CUSTOM,
            custom_validator=is_even,
            error_message="Count must be even"
        )
        
        error = service.validate_field("count", 11, rule)
        
        assert error is not None
        assert error.validation_type == ValidationType.CUSTOM
    
    def test_validate_entity_rfq(self, service):
        """Test validating RFQ entity"""
        rfq_data = {
            "title": "Test RFQ",
            "description": "Test description",
            "required_quantity": 100,
            "target_price": 50.0
        }
        
        result = service.validate_entity("rfq", rfq_data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_entity_rfq_missing_required(self, service):
        """Test validating RFQ with missing required fields"""
        rfq_data = {
            "description": "Test description"
            # Missing title and required_quantity
        }
        
        result = service.validate_entity("rfq", rfq_data)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any(e.field_name == "title" for e in result.errors)
        assert any(e.field_name == "required_quantity" for e in result.errors)
    
    def test_validate_entity_qualification(self, service):
        """Test validating qualification entity"""
        qual_data = {
            "supplier_id": "supplier-123",
            "rationale": "Supplier has excellent track record and competitive pricing",
            "score": 85
        }
        
        result = service.validate_entity("qualification", qual_data, state="approved")
        
        assert result.is_valid is True
    
    def test_validate_entity_qualification_short_rationale(self, service):
        """Test validating qualification with short rationale"""
        qual_data = {
            "supplier_id": "supplier-123",
            "rationale": "Good",  # Too short
            "score": 85
        }
        
        result = service.validate_entity("qualification", qual_data, state="approved")
        
        assert result.is_valid is False
        assert any(e.field_name == "rationale" and e.validation_type == ValidationType.LENGTH for e in result.errors)
    
    def test_validate_entity_quote(self, service):
        """Test validating quote entity"""
        quote_data = {
            "unit_price": 100.0,
            "margin_percentage": 10.0
        }
        
        result = service.validate_entity("quote", quote_data)
        
        # May have warnings about margin but should be valid
        assert len(result.errors) == 0
    
    def test_validate_entity_quote_negative_price(self, service):
        """Test validating quote with negative price"""
        quote_data = {
            "unit_price": -50.0
        }
        
        result = service.validate_entity("quote", quote_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "unit_price" and e.validation_type == ValidationType.RANGE for e in result.errors)
    
    def test_validate_entity_a3(self, service):
        """Test validating A3 entity"""
        a3_data = {
            "problem_statement": "Excessive waste in production line causing cost overruns"
        }
        
        result = service.validate_entity("a3", a3_data)
        
        assert result.is_valid is True
    
    def test_validate_entity_a3_short_problem_statement(self, service):
        """Test validating A3 with short problem statement"""
        a3_data = {
            "problem_statement": "Waste"  # Too short
        }
        
        result = service.validate_entity("a3", a3_data)
        
        assert result.is_valid is False
    
    def test_validate_rfq_completeness_complete(self, service):
        """Test RFQ completeness validation - complete"""
        rfq_data = {
            "title": "Test RFQ",
            "description": "Detailed description",
            "required_quantity": 100,
            "target_delivery_date": "2024-12-31"
        }
        
        result = service.validate_rfq_completeness(rfq_data)
        
        assert result.is_valid is True
    
    def test_validate_rfq_completeness_incomplete(self, service):
        """Test RFQ completeness validation - incomplete"""
        rfq_data = {
            "title": "Test RFQ"
            # Missing other required fields
        }
        
        result = service.validate_rfq_completeness(rfq_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "_completeness" for e in result.errors)
    
    def test_validate_qualification_approval(self, service):
        """Test qualification approval validation"""
        qual_data = {
            "supplier_id": "supplier-123",
            "rationale": "Supplier demonstrates excellent quality control and has competitive pricing"
        }
        
        result = service.validate_qualification_approval(qual_data)
        
        assert result.is_valid is True
    
    def test_validate_qualification_approval_missing_rationale(self, service):
        """Test qualification approval validation - missing rationale"""
        qual_data = {
            "supplier_id": "supplier-123"
        }
        
        result = service.validate_qualification_approval(qual_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "rationale" for e in result.errors)
    
    def test_validate_quote_margin_acceptable(self, service):
        """Test quote margin validation - acceptable margin"""
        quote_data = {
            "unit_price": 100.0,
            "unit_cost": 80.0,
            "margin_percentage": 20.0
        }
        
        result = service.validate_quote_margin(quote_data)
        
        # Should pass or have only warnings
        assert len(result.errors) == 0
    
    def test_validate_quote_margin_low(self, service):
        """Test quote margin validation - low margin"""
        quote_data = {
            "unit_price": 100.0,
            "unit_cost": 98.0,  # Only 2% margin
            "margin_percentage": 2.0
        }
        
        result = service.validate_quote_margin(quote_data)
        
        # Should have warning about low margin
        assert len(result.warnings) > 0
    
    def test_validate_a3_closure_complete(self, service):
        """Test A3 closure validation - complete"""
        a3_data = {
            "problem_statement": "Production line waste causing cost overruns",
            "reflection": "Learned that preventive maintenance reduces waste significantly and improves overall equipment effectiveness",
            "standard_updated": True
        }
        
        result = service.validate_a3_closure(a3_data)
        
        assert result.is_valid is True
    
    def test_validate_a3_closure_missing_reflection(self, service):
        """Test A3 closure validation - missing reflection"""
        a3_data = {
            "problem_statement": "Production line waste",
            "standard_updated": True
        }
        
        result = service.validate_a3_closure(a3_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "reflection" for e in result.errors)
    
    def test_validate_a3_closure_standard_not_updated(self, service):
        """Test A3 closure validation - standard not updated"""
        a3_data = {
            "problem_statement": "Production line waste",
            "reflection": "Learned important lessons about maintenance",
            "standard_updated": False
        }
        
        result = service.validate_a3_closure(a3_data)
        
        assert result.is_valid is False
        assert any(e.field_name == "standard_updated" for e in result.errors)
    
    def test_get_validation_summary(self, service):
        """Test getting validation summary"""
        summary = service.get_validation_summary("rfq")
        
        assert summary["entity_type"] == "rfq"
        assert summary["total_rules"] > 0
        assert "rules_by_type" in summary
        assert "rules_by_severity" in summary
        assert "required_fields" in summary
        assert "title" in summary["required_fields"]
