"""
RFQ Completeness Scoring Service.

Implements the RFQ completeness scoring algorithm that:
- Calculates a completeness score (0-100) based on filled fields
- Categorizes fields into required, important, and optional
- Identifies missing fields for "Missing Info Request" generation
- Determines if an RFQ can transition to Qualification status
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class FieldCategory(str, Enum):
    """Categories of RFQ fields by importance."""
    
    REQUIRED = "required"       # Must be filled (blocks qualification without override)
    IMPORTANT = "important"     # Should be filled (impacts score heavily)
    OPTIONAL = "optional"       # Nice to have (minimal impact on score)


@dataclass
class MissingField:
    """Represents a missing field in an RFQ."""
    
    field_name: str
    display_name: str
    category: FieldCategory
    weight: int
    description: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "field_name": self.field_name,
            "display_name": self.display_name,
            "category": self.category.value,
            "weight": self.weight,
            "description": self.description,
        }


@dataclass
class CompletenessResult:
    """Result of the RFQ completeness calculation."""
    
    score: int  # 0-100
    total_weight: int
    earned_weight: int
    missing_fields: list[MissingField] = field(default_factory=list)
    filled_fields: list[str] = field(default_factory=list)
    can_qualify: bool = False
    requires_override: bool = False
    override_reason: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "total_weight": self.total_weight,
            "earned_weight": self.earned_weight,
            "missing_fields": [f.to_dict() for f in self.missing_fields],
            "filled_fields": self.filled_fields,
            "can_qualify": self.can_qualify,
            "requires_override": self.requires_override,
            "override_reason": self.override_reason,
        }
    
    def generate_missing_info_email(self, customer_name: str, rfq_number: str) -> str:
        """
        Generate email text for requesting missing information from customer.
        
        Args:
            customer_name: Name of the customer to address
            rfq_number: The RFQ reference number
            
        Returns:
            Formatted email text
        """
        if not self.missing_fields:
            return ""
        
        # Group by category
        required_fields = [f for f in self.missing_fields if f.category == FieldCategory.REQUIRED]
        important_fields = [f for f in self.missing_fields if f.category == FieldCategory.IMPORTANT]
        optional_fields = [f for f in self.missing_fields if f.category == FieldCategory.OPTIONAL]
        
        lines = [
            f"Dear {customer_name},",
            "",
            f"Thank you for your RFQ ({rfq_number}). To provide you with an accurate quotation, "
            "we require some additional information.",
            "",
        ]
        
        if required_fields:
            lines.append("**Required Information (needed to proceed):**")
            for f in required_fields:
                desc = f" - {f.description}" if f.description else ""
                lines.append(f"• {f.display_name}{desc}")
            lines.append("")
        
        if important_fields:
            lines.append("**Important Information (for accurate pricing):**")
            for f in important_fields:
                desc = f" - {f.description}" if f.description else ""
                lines.append(f"• {f.display_name}{desc}")
            lines.append("")
        
        if optional_fields:
            lines.append("**Additional Information (if available):**")
            for f in optional_fields:
                desc = f" - {f.description}" if f.description else ""
                lines.append(f"• {f.display_name}{desc}")
            lines.append("")
        
        lines.extend([
            "Please provide this information at your earliest convenience so we can "
            "proceed with your quotation.",
            "",
            "Best regards,",
            "The Quotations Team",
        ])
        
        return "\n".join(lines)


# Field definitions with weights and categories
RFQ_FIELD_DEFINITIONS: list[dict] = [
    # Required fields (blocks qualification without override)
    {
        "field_name": "account_id",
        "display_name": "Customer Account",
        "category": FieldCategory.REQUIRED,
        "weight": 15,
        "description": "The customer requesting the quote",
    },
    {
        "field_name": "title",
        "display_name": "RFQ Title",
        "category": FieldCategory.REQUIRED,
        "weight": 10,
        "description": "Brief description of what is being requested",
    },
    {
        "field_name": "quantity",
        "display_name": "Quantity",
        "category": FieldCategory.REQUIRED,
        "weight": 15,
        "description": "Initial order quantity",
    },
    {
        "field_name": "due_date",
        "display_name": "Quote Due Date",
        "category": FieldCategory.REQUIRED,
        "weight": 10,
        "description": "When the customer needs the quote by",
    },
    
    # Important fields (heavily impacts score)
    {
        "field_name": "part_number",
        "display_name": "Part Number",
        "category": FieldCategory.IMPORTANT,
        "weight": 8,
        "description": "Customer's part number or reference",
    },
    {
        "field_name": "part_name",
        "display_name": "Part Name/Description",
        "category": FieldCategory.IMPORTANT,
        "weight": 5,
        "description": "Name or description of the part",
    },
    {
        "field_name": "drawing_number",
        "display_name": "Drawing Number",
        "category": FieldCategory.IMPORTANT,
        "weight": 7,
        "description": "Reference drawing or specification document",
    },
    {
        "field_name": "material_spec",
        "display_name": "Material Specification",
        "category": FieldCategory.IMPORTANT,
        "weight": 8,
        "description": "Material requirements (grade, type, spec)",
    },
    {
        "field_name": "annual_volume",
        "display_name": "Annual Volume",
        "category": FieldCategory.IMPORTANT,
        "weight": 6,
        "description": "Expected annual usage volume",
    },
    {
        "field_name": "contact_id",
        "display_name": "Customer Contact",
        "category": FieldCategory.IMPORTANT,
        "weight": 5,
        "description": "Primary contact for this RFQ",
    },
    {
        "field_name": "primary_process",
        "display_name": "Primary Manufacturing Process",
        "category": FieldCategory.IMPORTANT,
        "weight": 5,
        "description": "Main manufacturing process required",
    },
    {
        "field_name": "delivery_terms",
        "display_name": "Delivery Terms (Incoterms)",
        "category": FieldCategory.IMPORTANT,
        "weight": 4,
        "description": "Incoterms or delivery arrangement",
    },
    
    # Optional fields (nice to have)
    {
        "field_name": "target_price",
        "display_name": "Target Price",
        "category": FieldCategory.OPTIONAL,
        "weight": 3,
        "description": "Customer's target price if known",
    },
    {
        "field_name": "finish_requirements",
        "display_name": "Finish Requirements",
        "category": FieldCategory.OPTIONAL,
        "weight": 3,
        "description": "Surface finish or coating requirements",
    },
    {
        "field_name": "tolerance_requirements",
        "display_name": "Tolerance Requirements",
        "category": FieldCategory.OPTIONAL,
        "weight": 3,
        "description": "Critical tolerances or dimensional requirements",
    },
    {
        "field_name": "quality_requirements",
        "display_name": "Quality Requirements",
        "category": FieldCategory.OPTIONAL,
        "weight": 3,
        "description": "Quality standards or certifications needed",
    },
    {
        "field_name": "packaging_requirements",
        "display_name": "Packaging Requirements",
        "category": FieldCategory.OPTIONAL,
        "weight": 2,
        "description": "Special packaging needs",
    },
    {
        "field_name": "delivery_location",
        "display_name": "Delivery Location",
        "category": FieldCategory.OPTIONAL,
        "weight": 2,
        "description": "Shipping destination",
    },
    {
        "field_name": "lead_time_required",
        "display_name": "Required Lead Time",
        "category": FieldCategory.OPTIONAL,
        "weight": 2,
        "description": "Customer's required lead time in days",
    },
    {
        "field_name": "certifications_required",
        "display_name": "Certifications Required",
        "category": FieldCategory.OPTIONAL,
        "weight": 2,
        "description": "Required certifications (ISO, AS9100, etc.)",
    },
    {
        "field_name": "description",
        "display_name": "Detailed Description",
        "category": FieldCategory.OPTIONAL,
        "weight": 2,
        "description": "Additional details about the request",
    },
]


class RFQCompletenessService:
    """
    Service for calculating RFQ completeness scores and managing qualification gates.
    """
    
    # Default threshold for qualification (can be overridden)
    DEFAULT_QUALIFICATION_THRESHOLD: int = 70
    
    def __init__(
        self,
        qualification_threshold: int | None = None,
        field_definitions: list[dict] | None = None,
    ):
        """
        Initialize the completeness service.
        
        Args:
            qualification_threshold: Minimum score required to qualify (default: 70)
            field_definitions: Custom field definitions (default: use standard definitions)
        """
        self.qualification_threshold = (
            qualification_threshold
            if qualification_threshold is not None
            else self.DEFAULT_QUALIFICATION_THRESHOLD
        )
        self.field_definitions = field_definitions or RFQ_FIELD_DEFINITIONS
    
    def _is_field_filled(self, value: Any) -> bool:
        """
        Check if a field value is considered "filled" (not empty).
        
        This checks for presence, not validity. Zero values are considered filled
        because someone explicitly entered them. Validation of business rules
        (e.g., quantity must be positive) is a separate concern.
        
        Args:
            value: The field value to check
            
        Returns:
            True if the field has a value (not None or empty)
        """
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        # Numbers (including zero) count as filled - validity is checked separately
        return True
    
    def _get_field_value(self, rfq: Any, field_name: str) -> Any:
        """
        Get a field value from an RFQ object or dictionary.
        
        Args:
            rfq: RFQ model instance or dictionary
            field_name: Name of the field to get
            
        Returns:
            The field value
        """
        if isinstance(rfq, dict):
            return rfq.get(field_name)
        return getattr(rfq, field_name, None)
    
    def calculate_completeness(self, rfq: Any) -> CompletenessResult:
        """
        Calculate the completeness score for an RFQ.
        
        Args:
            rfq: RFQ model instance or dictionary with RFQ data
            
        Returns:
            CompletenessResult with score, missing fields, and qualification status
        """
        total_weight = 0
        earned_weight = 0
        missing_fields: list[MissingField] = []
        filled_fields: list[str] = []
        has_missing_required = False
        
        for field_def in self.field_definitions:
            field_name = field_def["field_name"]
            display_name = field_def["display_name"]
            category = field_def["category"]
            weight = field_def["weight"]
            description = field_def.get("description")
            
            total_weight += weight
            value = self._get_field_value(rfq, field_name)
            
            if self._is_field_filled(value):
                earned_weight += weight
                filled_fields.append(field_name)
            else:
                missing_field = MissingField(
                    field_name=field_name,
                    display_name=display_name,
                    category=category,
                    weight=weight,
                    description=description,
                )
                missing_fields.append(missing_field)
                
                if category == FieldCategory.REQUIRED:
                    has_missing_required = True
        
        # Calculate percentage score
        score = round((earned_weight / total_weight) * 100) if total_weight > 0 else 0
        
        # Determine qualification eligibility
        meets_threshold = score >= self.qualification_threshold
        can_qualify = meets_threshold and not has_missing_required
        requires_override = not can_qualify and meets_threshold
        
        override_reason = None
        if not can_qualify:
            if not meets_threshold:
                override_reason = (
                    f"Score ({score}%) is below qualification threshold "
                    f"({self.qualification_threshold}%)"
                )
            elif has_missing_required:
                required_missing = [
                    f.display_name
                    for f in missing_fields
                    if f.category == FieldCategory.REQUIRED
                ]
                override_reason = (
                    f"Required fields missing: {', '.join(required_missing)}"
                )
        
        return CompletenessResult(
            score=score,
            total_weight=total_weight,
            earned_weight=earned_weight,
            missing_fields=missing_fields,
            filled_fields=filled_fields,
            can_qualify=can_qualify,
            requires_override=not can_qualify,
            override_reason=override_reason,
        )
    
    def can_transition_to_qualification(
        self,
        rfq: Any,
        allow_override: bool = False,
        override_rationale: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Check if an RFQ can transition to Qualification status.
        
        Args:
            rfq: RFQ model instance or dictionary
            allow_override: Whether GM override is being used
            override_rationale: Rationale for the override (required if allow_override=True)
            
        Returns:
            Tuple of (can_transition, error_message)
        """
        result = self.calculate_completeness(rfq)
        
        if result.can_qualify:
            return True, None
        
        if allow_override:
            if not override_rationale or len(override_rationale.strip()) < 10:
                return False, "Override rationale must be at least 10 characters"
            return True, None
        
        return False, result.override_reason
    
    def generate_missing_info_tasks(
        self,
        rfq: Any,
        rfq_id: UUID,
        assigned_to_id: UUID | None = None,
    ) -> list[dict]:
        """
        Generate task definitions for missing RFQ fields.
        
        Args:
            rfq: RFQ model instance or dictionary
            rfq_id: UUID of the RFQ
            assigned_to_id: User to assign tasks to (optional)
            
        Returns:
            List of task definitions to be created
        """
        result = self.calculate_completeness(rfq)
        tasks: list[dict] = []
        
        # Only create tasks for required and important fields
        for missing_field in result.missing_fields:
            if missing_field.category in [FieldCategory.REQUIRED, FieldCategory.IMPORTANT]:
                task = {
                    "title": f"Obtain {missing_field.display_name}",
                    "description": (
                        f"Missing information for RFQ: {missing_field.display_name}.\n"
                        f"{missing_field.description or ''}"
                    ),
                    "entity_type": "rfq",
                    "entity_id": str(rfq_id),
                    "priority": (
                        "high" if missing_field.category == FieldCategory.REQUIRED else "medium"
                    ),
                    "assigned_to_id": assigned_to_id,
                    "tags": ["missing-info", "rfq"],
                }
                tasks.append(task)
        
        return tasks
    
    def get_field_definitions(self) -> list[dict]:
        """Get the current field definitions."""
        return [
            {
                "field_name": f["field_name"],
                "display_name": f["display_name"],
                "category": f["category"].value if isinstance(f["category"], FieldCategory) else f["category"],
                "weight": f["weight"],
                "description": f.get("description"),
            }
            for f in self.field_definitions
        ]
