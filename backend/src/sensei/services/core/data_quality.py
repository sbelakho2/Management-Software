"""
Data Quality Validation Service

Provides field-level validation, required field enforcement, data type validation,
business rule validation, and validation error reporting for all entities.

Ensures data quality consistent with workflow gates (RFQ completeness, qualification rationale, etc.).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy.orm import Session


class ValidationType(str, Enum):
    """Type of validation rule"""
    REQUIRED = "required"
    DATA_TYPE = "data_type"
    FORMAT = "format"
    RANGE = "range"
    ENUM = "enum"
    LENGTH = "length"
    PATTERN = "pattern"
    CUSTOM = "custom"
    BUSINESS_RULE = "business_rule"


class Severity(str, Enum):
    """Validation error severity"""
    ERROR = "error"  # Blocks save/workflow progression
    WARNING = "warning"  # Logged but doesn't block
    INFO = "info"  # Informational only


@dataclass
class ValidationRule:
    """Data quality validation rule"""
    
    field_name: str
    validation_type: ValidationType
    severity: Severity = Severity.ERROR
    error_message: str = ""
    
    # Type validation
    expected_type: Optional[type] = None
    
    # Range validation
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    # Length validation
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    
    # Enum/Choice validation
    allowed_values: Optional[list[Any]] = None
    
    # Pattern validation
    pattern: Optional[str] = None
    
    # Custom validation
    custom_validator: Optional[Callable[[Any, dict[str, Any]], bool]] = None
    
    # Context
    applies_to_entity: Optional[str] = None  # Entity type this rule applies to
    applies_to_state: Optional[str] = None  # Workflow state this rule applies to
    enabled: bool = True


@dataclass
class ValidationError:
    """Data quality validation error"""
    
    field_name: str
    validation_type: ValidationType
    severity: Severity
    error_message: str
    actual_value: Any = None
    expected: Any = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of data quality validation"""
    
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)
    
    def add_error(self, error: ValidationError):
        """Add validation error"""
        if error.severity == Severity.ERROR:
            self.errors.append(error)
            self.is_valid = False
        elif error.severity == Severity.WARNING:
            self.warnings.append(error)
        else:
            self.info.append(error)
    
    @property
    def total_issues(self) -> int:
        """Total number of validation issues"""
        return len(self.errors) + len(self.warnings) + len(self.info)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are blocking errors"""
        return len(self.errors) > 0


class DataQualityService:
    """
    Data quality validation service
    
    Provides comprehensive field-level validation including:
    - Required field enforcement
    - Data type validation
    - Format validation (email, phone, URL)
    - Range validation (min/max)
    - Length validation
    - Pattern/regex validation
    - Business rule validation
    - Workflow-specific validation (gates)
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.rules: dict[str, list[ValidationRule]] = {}
        
        # Initialize default validation rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default validation rules for common entities"""
        
        # RFQ validation rules
        self.register_rule(ValidationRule(
            field_name="title",
            validation_type=ValidationType.REQUIRED,
            error_message="RFQ title is required",
            applies_to_entity="rfq"
        ))
        
        self.register_rule(ValidationRule(
            field_name="title",
            validation_type=ValidationType.LENGTH,
            min_length=3,
            max_length=200,
            error_message="RFQ title must be between 3 and 200 characters",
            applies_to_entity="rfq"
        ))
        
        self.register_rule(ValidationRule(
            field_name="description",
            validation_type=ValidationType.REQUIRED,
            error_message="RFQ description is required",
            applies_to_entity="rfq"
        ))
        
        self.register_rule(ValidationRule(
            field_name="required_quantity",
            validation_type=ValidationType.REQUIRED,
            error_message="Required quantity is mandatory",
            applies_to_entity="rfq"
        ))
        
        self.register_rule(ValidationRule(
            field_name="required_quantity",
            validation_type=ValidationType.RANGE,
            min_value=1,
            error_message="Required quantity must be at least 1",
            applies_to_entity="rfq"
        ))
        
        self.register_rule(ValidationRule(
            field_name="target_price",
            validation_type=ValidationType.RANGE,
            min_value=0,
            error_message="Target price cannot be negative",
            severity=Severity.WARNING,
            applies_to_entity="rfq"
        ))
        
        # Qualification validation rules
        self.register_rule(ValidationRule(
            field_name="supplier_id",
            validation_type=ValidationType.REQUIRED,
            error_message="Supplier is required for qualification",
            applies_to_entity="qualification"
        ))
        
        self.register_rule(ValidationRule(
            field_name="rationale",
            validation_type=ValidationType.REQUIRED,
            error_message="Rationale is required for qualification approval/rejection",
            applies_to_entity="qualification",
            applies_to_state="approved"
        ))
        
        self.register_rule(ValidationRule(
            field_name="rationale",
            validation_type=ValidationType.LENGTH,
            min_length=20,
            error_message="Rationale must be at least 20 characters",
            applies_to_entity="qualification",
            applies_to_state="approved"
        ))
        
        self.register_rule(ValidationRule(
            field_name="score",
            validation_type=ValidationType.RANGE,
            min_value=0,
            max_value=100,
            error_message="Qualification score must be between 0 and 100",
            applies_to_entity="qualification"
        ))
        
        # Quote validation rules
        self.register_rule(ValidationRule(
            field_name="unit_price",
            validation_type=ValidationType.REQUIRED,
            error_message="Unit price is required",
            applies_to_entity="quote"
        ))
        
        self.register_rule(ValidationRule(
            field_name="unit_price",
            validation_type=ValidationType.RANGE,
            min_value=0,
            error_message="Unit price cannot be negative",
            applies_to_entity="quote"
        ))
        
        self.register_rule(ValidationRule(
            field_name="margin_percentage",
            validation_type=ValidationType.RANGE,
            min_value=5.0,
            error_message="Quote margin must be at least 5%",
            severity=Severity.WARNING,
            applies_to_entity="quote"
        ))
        
        # A3 validation rules
        self.register_rule(ValidationRule(
            field_name="problem_statement",
            validation_type=ValidationType.REQUIRED,
            error_message="Problem statement is required",
            applies_to_entity="a3"
        ))
        
        self.register_rule(ValidationRule(
            field_name="problem_statement",
            validation_type=ValidationType.LENGTH,
            min_length=20,
            error_message="Problem statement must be at least 20 characters",
            applies_to_entity="a3"
        ))
        
        self.register_rule(ValidationRule(
            field_name="reflection",
            validation_type=ValidationType.REQUIRED,
            error_message="Reflection is required for A3 closure",
            applies_to_entity="a3",
            applies_to_state="closed"
        ))
        
        self.register_rule(ValidationRule(
            field_name="reflection",
            validation_type=ValidationType.LENGTH,
            min_length=50,
            error_message="Reflection must be at least 50 characters",
            applies_to_entity="a3",
            applies_to_state="closed"
        ))
        
        # User/Account validation rules
        self.register_rule(ValidationRule(
            field_name="email",
            validation_type=ValidationType.REQUIRED,
            error_message="Email is required",
            applies_to_entity="user"
        ))
        
        self.register_rule(ValidationRule(
            field_name="email",
            validation_type=ValidationType.FORMAT,
            pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            error_message="Invalid email format",
            applies_to_entity="user"
        ))
        
        self.register_rule(ValidationRule(
            field_name="phone",
            validation_type=ValidationType.FORMAT,
            pattern=r"^\+?[1-9]\d{1,14}$",
            error_message="Invalid phone number format (use E.164 format)",
            severity=Severity.WARNING,
            applies_to_entity="user"
        ))
    
    def register_rule(self, rule: ValidationRule):
        """Register a validation rule"""
        entity_key = rule.applies_to_entity or "_global"
        
        if entity_key not in self.rules:
            self.rules[entity_key] = []
        
        self.rules[entity_key].append(rule)
    
    def get_rules_for_entity(
        self,
        entity_type: str,
        state: Optional[str] = None
    ) -> list[ValidationRule]:
        """Get applicable validation rules for entity and state"""
        rules = []
        
        # Global rules
        if "_global" in self.rules:
            rules.extend(self.rules["_global"])
        
        # Entity-specific rules
        if entity_type in self.rules:
            for rule in self.rules[entity_type]:
                # Check if rule applies to current state
                if rule.applies_to_state is None or rule.applies_to_state == state:
                    rules.append(rule)
        
        return [r for r in rules if r.enabled]
    
    def validate_field(
        self,
        field_name: str,
        value: Any,
        rule: ValidationRule,
        context: Optional[dict[str, Any]] = None
    ) -> Optional[ValidationError]:
        """
        Validate a single field against a rule
        
        Returns ValidationError if validation fails, None if passes
        """
        context = context or {}
        
        # Required validation
        if rule.validation_type == ValidationType.REQUIRED:
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=rule.severity,
                    error_message=rule.error_message or f"{field_name} is required",
                    actual_value=value
                )
        
        # Skip other validations if value is None/empty
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        
        # Data type validation
        if rule.validation_type == ValidationType.DATA_TYPE and rule.expected_type:
            if not isinstance(value, rule.expected_type):
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=rule.severity,
                    error_message=rule.error_message or f"{field_name} must be of type {rule.expected_type.__name__}",
                    actual_value=value,
                    expected=rule.expected_type.__name__
                )
        
        # Range validation
        if rule.validation_type == ValidationType.RANGE:
            try:
                numeric_value = float(value)
                
                if rule.min_value is not None and numeric_value < rule.min_value:
                    return ValidationError(
                        field_name=field_name,
                        validation_type=rule.validation_type,
                        severity=rule.severity,
                        error_message=rule.error_message or f"{field_name} must be at least {rule.min_value}",
                        actual_value=value,
                        expected=f">= {rule.min_value}"
                    )
                
                if rule.max_value is not None and numeric_value > rule.max_value:
                    return ValidationError(
                        field_name=field_name,
                        validation_type=rule.validation_type,
                        severity=rule.severity,
                        error_message=rule.error_message or f"{field_name} must be at most {rule.max_value}",
                        actual_value=value,
                        expected=f"<= {rule.max_value}"
                    )
            except (ValueError, TypeError):
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=rule.severity,
                    error_message=f"{field_name} must be a numeric value",
                    actual_value=value
                )
        
        # Length validation
        if rule.validation_type == ValidationType.LENGTH:
            try:
                length = len(str(value))
                
                if rule.min_length is not None and length < rule.min_length:
                    return ValidationError(
                        field_name=field_name,
                        validation_type=rule.validation_type,
                        severity=rule.severity,
                        error_message=rule.error_message or f"{field_name} must be at least {rule.min_length} characters",
                        actual_value=value,
                        expected=f">= {rule.min_length} characters"
                    )
                
                if rule.max_length is not None and length > rule.max_length:
                    return ValidationError(
                        field_name=field_name,
                        validation_type=rule.validation_type,
                        severity=rule.severity,
                        error_message=rule.error_message or f"{field_name} must be at most {rule.max_length} characters",
                        actual_value=value,
                        expected=f"<= {rule.max_length} characters"
                    )
            except TypeError:
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=rule.severity,
                    error_message=f"{field_name} length cannot be determined",
                    actual_value=value
                )
        
        # Enum/Choice validation
        if rule.validation_type == ValidationType.ENUM and rule.allowed_values:
            if value not in rule.allowed_values:
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=rule.severity,
                    error_message=rule.error_message or f"{field_name} must be one of: {', '.join(map(str, rule.allowed_values))}",
                    actual_value=value,
                    expected=rule.allowed_values
                )
        
        # Pattern/Format validation
        if rule.validation_type in (ValidationType.PATTERN, ValidationType.FORMAT) and rule.pattern:
            if not re.match(rule.pattern, str(value)):
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=rule.severity,
                    error_message=rule.error_message or f"{field_name} does not match required pattern",
                    actual_value=value,
                    expected=rule.pattern
                )
        
        # Custom validation
        if rule.validation_type == ValidationType.CUSTOM and rule.custom_validator:
            try:
                if not rule.custom_validator(value, context):
                    return ValidationError(
                        field_name=field_name,
                        validation_type=rule.validation_type,
                        severity=rule.severity,
                        error_message=rule.error_message or f"{field_name} failed custom validation",
                        actual_value=value,
                        context=context
                    )
            except Exception as e:
                return ValidationError(
                    field_name=field_name,
                    validation_type=rule.validation_type,
                    severity=Severity.ERROR,
                    error_message=f"Custom validation error: {str(e)}",
                    actual_value=value,
                    context=context
                )
        
        return None
    
    def validate_entity(
        self,
        entity_type: str,
        data: dict[str, Any],
        state: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate an entire entity
        
        Args:
            entity_type: Type of entity (rfq, qualification, quote, a3, etc.)
            data: Dictionary of field values
            state: Current workflow state (for state-specific validation)
            context: Additional context for validation
        
        Returns:
            ValidationResult with all validation errors/warnings
        """
        result = ValidationResult(is_valid=True)
        context = context or {}
        
        # Get applicable rules
        rules = self.get_rules_for_entity(entity_type, state)
        
        # Validate each rule
        for rule in rules:
            # Get field value
            field_value = data.get(rule.field_name)
            
            # Validate field
            error = self.validate_field(rule.field_name, field_value, rule, context)
            
            if error:
                result.add_error(error)
        
        return result
    
    def validate_rfq_completeness(
        self,
        rfq_data: dict[str, Any],
        completeness_threshold: float = 70.0
    ) -> ValidationResult:
        """
        Validate RFQ completeness for workflow gating
        
        Checks required fields and calculates completeness score
        """
        result = self.validate_entity("rfq", rfq_data)
        
        # Additional business rule: completeness threshold
        required_fields = ["title", "description", "required_quantity", "target_delivery_date"]
        completed_fields = sum(1 for f in required_fields if rfq_data.get(f) is not None and rfq_data.get(f) != "")
        completeness = (completed_fields / len(required_fields)) * 100
        
        if completeness < completeness_threshold:
            result.add_error(ValidationError(
                field_name="_completeness",
                validation_type=ValidationType.BUSINESS_RULE,
                severity=Severity.ERROR,
                error_message=f"RFQ completeness ({completeness:.1f}%) below required threshold ({completeness_threshold}%)",
                actual_value=completeness,
                expected=f">= {completeness_threshold}%",
                context={"missing_fields": [f for f in required_fields if not rfq_data.get(f)]}
            ))
        
        return result
    
    def validate_qualification_approval(
        self,
        qualification_data: dict[str, Any]
    ) -> ValidationResult:
        """
        Validate qualification approval requirements
        
        Ensures rationale is provided and meets minimum requirements
        """
        return self.validate_entity("qualification", qualification_data, state="approved")
    
    def validate_quote_margin(
        self,
        quote_data: dict[str, Any],
        min_margin: float = 5.0
    ) -> ValidationResult:
        """
        Validate quote margin business rule
        
        Ensures quote maintains minimum profit margin
        """
        result = self.validate_entity("quote", quote_data)
        
        # Check margin calculation
        unit_price = quote_data.get("unit_price")
        unit_cost = quote_data.get("unit_cost")
        
        if unit_price is not None and unit_cost is not None:
            try:
                unit_price = float(unit_price)
                unit_cost = float(unit_cost)
                
                if unit_price > 0:
                    margin = ((unit_price - unit_cost) / unit_price) * 100
                    
                    if margin < min_margin:
                        result.add_error(ValidationError(
                            field_name="margin_percentage",
                            validation_type=ValidationType.BUSINESS_RULE,
                            severity=Severity.WARNING,
                            error_message=f"Quote margin ({margin:.2f}%) below recommended minimum ({min_margin}%)",
                            actual_value=margin,
                            expected=f">= {min_margin}%"
                        ))
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        return result
    
    def validate_a3_closure(
        self,
        a3_data: dict[str, Any]
    ) -> ValidationResult:
        """
        Validate A3 closure requirements
        
        Ensures reflection and standard update are provided
        """
        result = self.validate_entity("a3", a3_data, state="closed")
        
        # Additional check for standard update
        standard_updated = a3_data.get("standard_updated", False)
        if not standard_updated:
            result.add_error(ValidationError(
                field_name="standard_updated",
                validation_type=ValidationType.BUSINESS_RULE,
                severity=Severity.ERROR,
                error_message="Standard must be updated before closing A3",
                actual_value=False,
                expected=True
            ))
        
        return result
    
    def get_validation_summary(
        self,
        entity_type: str,
        state: Optional[str] = None
    ) -> dict[str, Any]:
        """Get summary of validation rules for an entity"""
        rules = self.get_rules_for_entity(entity_type, state)
        
        return {
            "entity_type": entity_type,
            "state": state,
            "total_rules": len(rules),
            "rules_by_type": {
                vtype.value: len([r for r in rules if r.validation_type == vtype])
                for vtype in ValidationType
            },
            "rules_by_severity": {
                sev.value: len([r for r in rules if r.severity == sev])
                for sev in Severity
            },
            "required_fields": [r.field_name for r in rules if r.validation_type == ValidationType.REQUIRED]
        }
