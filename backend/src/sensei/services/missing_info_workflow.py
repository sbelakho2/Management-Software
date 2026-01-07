"""
Missing Info Workflow Service.

Handles automated workflows for incomplete RFQs:
- Auto-generates "Missing Info Request" email text based on empty fields
- Auto-creates tasks for missing items
- Tracks info requests and responses
- Supports follow-up reminders
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4


class MissingFieldCategory(str, Enum):
    """Categories of missing RFQ fields."""
    
    CUSTOMER_INFO = "customer_info"
    PRODUCT_SPECS = "product_specs"
    COMMERCIAL = "commercial"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    VOLUME_DEMAND = "volume_demand"
    LOGISTICS = "logistics"
    QUALITY = "quality"
    TIMELINE = "timeline"


class MissingFieldPriority(str, Enum):
    """Priority level for missing fields."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InfoRequestStatus(str, Enum):
    """Status of an information request."""
    
    DRAFT = "draft"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_RECEIVED = "partially_received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class TaskStatus(str, Enum):
    """Status of a generated task."""
    
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReminderFrequency(str, Enum):
    """Frequency of follow-up reminders."""
    
    DAILY = "daily"
    EVERY_OTHER_DAY = "every_other_day"
    WEEKLY = "weekly"
    CUSTOM = "custom"


@dataclass
class MissingFieldSpec:
    """Specification for a missing field."""
    
    field_name: str
    field_label: str
    category: MissingFieldCategory
    priority: MissingFieldPriority
    question_template: str
    help_text: Optional[str] = None
    example_value: Optional[str] = None
    is_blocking: bool = False  # Blocks transition if missing
    requires_attachment: bool = False


@dataclass
class IdentifiedMissingField:
    """An identified missing field in an RFQ."""
    
    id: UUID
    rfq_id: UUID
    field_name: str
    field_label: str
    category: MissingFieldCategory
    priority: MissingFieldPriority
    question_text: str
    help_text: Optional[str]
    is_blocking: bool
    requires_attachment: bool
    identified_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_value: Optional[str] = None
    resolved_by: Optional[UUID] = None


@dataclass
class InfoRequest:
    """An information request sent to a customer/contact."""
    
    id: UUID
    rfq_id: UUID
    recipient_name: str
    recipient_email: str
    subject: str
    body_text: str
    body_html: Optional[str]
    missing_fields: list[IdentifiedMissingField]
    status: InfoRequestStatus
    created_by: UUID
    created_at: datetime
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    reminder_frequency: Optional[ReminderFrequency] = None
    next_reminder_at: Optional[datetime] = None
    reminder_count: int = 0
    max_reminders: int = 3
    notes: Optional[str] = None


@dataclass
class GeneratedTask:
    """A task generated for a missing info item."""
    
    id: UUID
    rfq_id: UUID
    missing_field_id: UUID
    title: str
    description: str
    assigned_to: Optional[UUID]
    due_date: date
    priority: MissingFieldPriority
    status: TaskStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    notes: Optional[str] = None
    linked_info_request_id: Optional[UUID] = None


@dataclass
class EmailTemplate:
    """Template for generating email text."""
    
    id: UUID
    name: str
    subject_template: str
    body_template: str
    body_html_template: Optional[str]
    language: str = "en"
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RFQData:
    """RFQ data for analysis."""
    
    rfq_id: UUID
    rfq_number: str
    customer_name: str
    contact_name: Optional[str]
    contact_email: Optional[str]
    product_name: Optional[str]
    part_number: Optional[str]
    
    # Field values (None = missing)
    customer_address: Optional[str] = None
    product_specs: Optional[str] = None
    bom_uploaded: bool = False
    volume_annual: Optional[int] = None
    volume_per_order: Optional[int] = None
    target_price: Optional[float] = None
    currency: Optional[str] = None
    incoterms: Optional[str] = None
    delivery_location: Optional[str] = None
    lead_time_required: Optional[int] = None
    sample_required: bool = False
    sample_quantity: Optional[int] = None
    certification_requirements: Optional[list[str]] = None
    compliance_requirements: Optional[list[str]] = None
    packaging_specs: Optional[str] = None
    testing_requirements: Optional[str] = None
    quality_requirements: Optional[str] = None
    ramp_plan: Optional[str] = None
    sop_date: Optional[date] = None
    drawings_uploaded: bool = False
    revision_level: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of analyzing an RFQ for missing info."""
    
    rfq_id: UUID
    rfq_number: str
    total_fields_checked: int
    missing_fields: list[IdentifiedMissingField]
    missing_count: int
    blocking_count: int
    completeness_score: float
    by_category: dict[str, list[IdentifiedMissingField]]
    by_priority: dict[str, list[IdentifiedMissingField]]
    can_transition: bool
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowConfig:
    """Configuration for the missing info workflow."""
    
    default_reminder_frequency: ReminderFrequency = ReminderFrequency.EVERY_OTHER_DAY
    max_reminders: int = 3
    request_expiry_days: int = 14
    task_due_days: int = 3
    auto_create_tasks: bool = True
    auto_send_reminders: bool = True
    include_help_text_in_email: bool = True
    include_examples_in_email: bool = True
    group_by_category_in_email: bool = True


# Default field specifications
DEFAULT_FIELD_SPECS: list[MissingFieldSpec] = [
    # Customer Info
    MissingFieldSpec(
        field_name="customer_address",
        field_label="Customer Address",
        category=MissingFieldCategory.CUSTOMER_INFO,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please provide the complete customer address for shipping and invoicing purposes.",
        help_text="Include street address, city, state/province, postal code, and country.",
    ),
    MissingFieldSpec(
        field_name="contact_name",
        field_label="Primary Contact Name",
        category=MissingFieldCategory.CUSTOMER_INFO,
        priority=MissingFieldPriority.HIGH,
        question_template="Please provide the name of the primary contact for this RFQ.",
        is_blocking=True,
    ),
    MissingFieldSpec(
        field_name="contact_email",
        field_label="Contact Email",
        category=MissingFieldCategory.CUSTOMER_INFO,
        priority=MissingFieldPriority.HIGH,
        question_template="Please provide the email address for the primary contact.",
        is_blocking=True,
    ),
    
    # Product Specs
    MissingFieldSpec(
        field_name="product_specs",
        field_label="Product Specifications",
        category=MissingFieldCategory.PRODUCT_SPECS,
        priority=MissingFieldPriority.CRITICAL,
        question_template="Please provide the complete product specifications or a link to the specification document.",
        help_text="Include all relevant technical requirements, tolerances, and performance criteria.",
        is_blocking=True,
    ),
    MissingFieldSpec(
        field_name="bom_uploaded",
        field_label="Bill of Materials",
        category=MissingFieldCategory.PRODUCT_SPECS,
        priority=MissingFieldPriority.CRITICAL,
        question_template="Please upload the Bill of Materials (BOM) for this product.",
        help_text="The BOM should include all components with quantities, part numbers, and descriptions.",
        is_blocking=True,
        requires_attachment=True,
    ),
    MissingFieldSpec(
        field_name="drawings_uploaded",
        field_label="Engineering Drawings",
        category=MissingFieldCategory.PRODUCT_SPECS,
        priority=MissingFieldPriority.HIGH,
        question_template="Please upload the engineering drawings for this product.",
        help_text="Include 2D or 3D drawings with all dimensions and tolerances specified.",
        requires_attachment=True,
    ),
    MissingFieldSpec(
        field_name="revision_level",
        field_label="Specification Revision",
        category=MissingFieldCategory.PRODUCT_SPECS,
        priority=MissingFieldPriority.HIGH,
        question_template="Please confirm the revision level of the specifications and drawings.",
        help_text="This ensures we are quoting on the correct version.",
        is_blocking=True,
    ),
    
    # Commercial
    MissingFieldSpec(
        field_name="target_price",
        field_label="Target Price",
        category=MissingFieldCategory.COMMERCIAL,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please provide your target price for this product (if available).",
        help_text="Understanding your budget helps us provide competitive options.",
        example_value="$10.00 USD per unit",
    ),
    MissingFieldSpec(
        field_name="currency",
        field_label="Currency",
        category=MissingFieldCategory.COMMERCIAL,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please specify the currency for this quotation.",
        example_value="USD, EUR, GBP",
    ),
    MissingFieldSpec(
        field_name="incoterms",
        field_label="Incoterms",
        category=MissingFieldCategory.COMMERCIAL,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please specify the preferred Incoterms for delivery.",
        help_text="Common options include EXW, FOB, CIF, DDP.",
        example_value="EXW, FOB Shanghai",
    ),
    
    # Volume & Demand
    MissingFieldSpec(
        field_name="volume_annual",
        field_label="Annual Volume",
        category=MissingFieldCategory.VOLUME_DEMAND,
        priority=MissingFieldPriority.CRITICAL,
        question_template="Please provide the expected annual volume for this product.",
        help_text="This helps us determine pricing tiers and capacity planning.",
        example_value="50,000 units per year",
        is_blocking=True,
    ),
    MissingFieldSpec(
        field_name="volume_per_order",
        field_label="Order Quantity",
        category=MissingFieldCategory.VOLUME_DEMAND,
        priority=MissingFieldPriority.HIGH,
        question_template="Please provide the expected quantity per order/release.",
        example_value="5,000 units per order",
    ),
    MissingFieldSpec(
        field_name="ramp_plan",
        field_label="Ramp-up Plan",
        category=MissingFieldCategory.VOLUME_DEMAND,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please provide the volume ramp-up plan from initial production to full volume.",
        help_text="Include expected volumes by month/quarter.",
    ),
    
    # Logistics
    MissingFieldSpec(
        field_name="delivery_location",
        field_label="Delivery Location",
        category=MissingFieldCategory.LOGISTICS,
        priority=MissingFieldPriority.HIGH,
        question_template="Please provide the delivery location for the finished goods.",
        help_text="Include complete address for logistics planning.",
    ),
    MissingFieldSpec(
        field_name="lead_time_required",
        field_label="Required Lead Time",
        category=MissingFieldCategory.LOGISTICS,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please specify the required lead time from order to delivery.",
        example_value="6-8 weeks",
    ),
    MissingFieldSpec(
        field_name="packaging_specs",
        field_label="Packaging Requirements",
        category=MissingFieldCategory.LOGISTICS,
        priority=MissingFieldPriority.LOW,
        question_template="Please specify any packaging requirements or preferences.",
        help_text="Include labeling, packing quantities, and special handling requirements.",
    ),
    
    # Compliance
    MissingFieldSpec(
        field_name="certification_requirements",
        field_label="Certifications Required",
        category=MissingFieldCategory.COMPLIANCE,
        priority=MissingFieldPriority.HIGH,
        question_template="Please list all required certifications for this product.",
        help_text="Examples: ISO 9001, IATF 16949, AS9100, CE, UL, etc.",
        example_value="IATF 16949, REACH, RoHS",
    ),
    MissingFieldSpec(
        field_name="compliance_requirements",
        field_label="Compliance Requirements",
        category=MissingFieldCategory.COMPLIANCE,
        priority=MissingFieldPriority.HIGH,
        question_template="Please specify all compliance and regulatory requirements.",
        help_text="Include environmental, safety, and industry-specific requirements.",
    ),
    
    # Quality
    MissingFieldSpec(
        field_name="quality_requirements",
        field_label="Quality Requirements",
        category=MissingFieldCategory.QUALITY,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please specify any special quality requirements or acceptance criteria.",
        help_text="Include inspection requirements, AQL levels, testing requirements.",
    ),
    MissingFieldSpec(
        field_name="testing_requirements",
        field_label="Testing Requirements",
        category=MissingFieldCategory.QUALITY,
        priority=MissingFieldPriority.MEDIUM,
        question_template="Please specify any testing requirements for this product.",
        help_text="Include functional testing, environmental testing, reliability testing, etc.",
    ),
    MissingFieldSpec(
        field_name="sample_quantity",
        field_label="Sample Quantity",
        category=MissingFieldCategory.QUALITY,
        priority=MissingFieldPriority.LOW,
        question_template="If samples are required, please specify the quantity needed.",
        example_value="10 pieces for validation",
    ),
    
    # Timeline
    MissingFieldSpec(
        field_name="sop_date",
        field_label="Start of Production Date",
        category=MissingFieldCategory.TIMELINE,
        priority=MissingFieldPriority.HIGH,
        question_template="Please provide the target Start of Production (SOP) date.",
        help_text="This helps us plan capacity and resource allocation.",
    ),
]


class MissingInfoWorkflowService:
    """
    Service for managing missing information workflows.
    
    Handles:
    - Analyzing RFQs for missing fields
    - Generating email text for info requests
    - Creating tasks for missing items
    - Tracking request status and reminders
    """
    
    def __init__(self, config: Optional[WorkflowConfig] = None) -> None:
        """Initialize the service."""
        self.config = config or WorkflowConfig()
        self._field_specs: dict[str, MissingFieldSpec] = {}
        self._email_templates: dict[UUID, EmailTemplate] = {}
        self._info_requests: dict[UUID, InfoRequest] = {}
        self._tasks: dict[UUID, GeneratedTask] = {}
        self._identified_fields: dict[UUID, IdentifiedMissingField] = {}
        self._default_email_template_id: Optional[UUID] = None
        
        self._register_default_field_specs()
        self._register_default_email_templates()
    
    def _register_default_field_specs(self) -> None:
        """Register default field specifications."""
        for spec in DEFAULT_FIELD_SPECS:
            self._field_specs[spec.field_name] = spec
    
    def _register_default_email_templates(self) -> None:
        """Register default email templates."""
        # English template
        en_template = EmailTemplate(
            id=uuid4(),
            name="Default Missing Info Request (English)",
            subject_template="Information Required for RFQ: {rfq_number} - {customer_name}",
            body_template="""Dear {contact_name},

Thank you for your RFQ ({rfq_number}) for {product_name}.

To proceed with your quotation, we require the following information:

{missing_fields_list}

Please provide this information at your earliest convenience. You can reply directly to this email with the requested details.

If you have any questions, please don't hesitate to contact us.

Best regards,
{sender_name}
{sender_title}""",
            body_html_template=None,
            language="en",
            is_default=True,
        )
        self._email_templates[en_template.id] = en_template
        self._default_email_template_id = en_template.id
        
        # French template
        fr_template = EmailTemplate(
            id=uuid4(),
            name="Default Missing Info Request (French)",
            subject_template="Informations requises pour RFQ: {rfq_number} - {customer_name}",
            body_template="""Cher/Chère {contact_name},

Merci pour votre demande de devis ({rfq_number}) pour {product_name}.

Pour procéder à votre devis, nous avons besoin des informations suivantes:

{missing_fields_list}

Veuillez nous fournir ces informations dans les meilleurs délais. Vous pouvez répondre directement à cet email avec les détails demandés.

Si vous avez des questions, n'hésitez pas à nous contacter.

Cordialement,
{sender_name}
{sender_title}""",
            body_html_template=None,
            language="fr",
            is_default=False,
        )
        self._email_templates[fr_template.id] = fr_template
    
    # Field Specification Management
    
    def get_field_spec(self, field_name: str) -> Optional[MissingFieldSpec]:
        """Get a field specification by name."""
        return self._field_specs.get(field_name)
    
    def list_field_specs(
        self,
        category: Optional[MissingFieldCategory] = None,
        priority: Optional[MissingFieldPriority] = None,
        blocking_only: bool = False,
    ) -> list[MissingFieldSpec]:
        """List field specifications with optional filters."""
        specs = list(self._field_specs.values())
        
        if category:
            specs = [s for s in specs if s.category == category]
        
        if priority:
            specs = [s for s in specs if s.priority == priority]
        
        if blocking_only:
            specs = [s for s in specs if s.is_blocking]
        
        return specs
    
    def add_field_spec(self, spec: MissingFieldSpec) -> None:
        """Add or update a field specification."""
        self._field_specs[spec.field_name] = spec
    
    def remove_field_spec(self, field_name: str) -> bool:
        """Remove a field specification."""
        if field_name in self._field_specs:
            del self._field_specs[field_name]
            return True
        return False
    
    # RFQ Analysis
    
    def analyze_rfq(self, rfq_data: RFQData) -> AnalysisResult:
        """
        Analyze an RFQ for missing fields.
        
        Args:
            rfq_data: The RFQ data to analyze
            
        Returns:
            AnalysisResult with all missing fields identified
        """
        missing_fields: list[IdentifiedMissingField] = []
        total_checked = 0
        
        for field_name, spec in self._field_specs.items():
            total_checked += 1
            value = getattr(rfq_data, field_name, None)
            
            # Check if field is missing
            is_missing = False
            if value is None:
                is_missing = True
            elif isinstance(value, bool) and not value:
                # For boolean fields like bom_uploaded, False means missing
                if field_name in ("bom_uploaded", "drawings_uploaded"):
                    is_missing = True
            elif isinstance(value, str) and not value.strip():
                is_missing = True
            elif isinstance(value, list) and len(value) == 0:
                is_missing = True
            
            if is_missing:
                identified = IdentifiedMissingField(
                    id=uuid4(),
                    rfq_id=rfq_data.rfq_id,
                    field_name=field_name,
                    field_label=spec.field_label,
                    category=spec.category,
                    priority=spec.priority,
                    question_text=spec.question_template,
                    help_text=spec.help_text,
                    is_blocking=spec.is_blocking,
                    requires_attachment=spec.requires_attachment,
                )
                missing_fields.append(identified)
                self._identified_fields[identified.id] = identified
        
        # Group by category
        by_category: dict[str, list[IdentifiedMissingField]] = {}
        for mf in missing_fields:
            cat = mf.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(mf)
        
        # Group by priority
        by_priority: dict[str, list[IdentifiedMissingField]] = {}
        for mf in missing_fields:
            pri = mf.priority.value
            if pri not in by_priority:
                by_priority[pri] = []
            by_priority[pri].append(mf)
        
        # Calculate completeness score
        if total_checked > 0:
            completeness_score = ((total_checked - len(missing_fields)) / total_checked) * 100
        else:
            completeness_score = 100.0
        
        # Check if can transition (no blocking fields missing)
        blocking_count = sum(1 for mf in missing_fields if mf.is_blocking)
        can_transition = blocking_count == 0
        
        return AnalysisResult(
            rfq_id=rfq_data.rfq_id,
            rfq_number=rfq_data.rfq_number,
            total_fields_checked=total_checked,
            missing_fields=missing_fields,
            missing_count=len(missing_fields),
            blocking_count=blocking_count,
            completeness_score=round(completeness_score, 1),
            by_category=by_category,
            by_priority=by_priority,
            can_transition=can_transition,
        )
    
    # Email Generation
    
    def get_email_template(self, template_id: UUID) -> Optional[EmailTemplate]:
        """Get an email template by ID."""
        return self._email_templates.get(template_id)
    
    def get_default_email_template(self) -> Optional[EmailTemplate]:
        """Get the default email template."""
        if self._default_email_template_id:
            return self._email_templates.get(self._default_email_template_id)
        return None
    
    def list_email_templates(
        self,
        language: Optional[str] = None,
        active_only: bool = True,
    ) -> list[EmailTemplate]:
        """List available email templates."""
        templates = list(self._email_templates.values())
        
        if language:
            templates = [t for t in templates if t.language == language]
        
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        return templates
    
    def create_email_template(
        self,
        name: str,
        subject_template: str,
        body_template: str,
        language: str = "en",
        body_html_template: Optional[str] = None,
        is_default: bool = False,
    ) -> EmailTemplate:
        """Create a new email template."""
        template = EmailTemplate(
            id=uuid4(),
            name=name,
            subject_template=subject_template,
            body_template=body_template,
            body_html_template=body_html_template,
            language=language,
            is_default=is_default,
        )
        
        if is_default:
            # Unset previous default
            if self._default_email_template_id:
                old_default = self._email_templates.get(self._default_email_template_id)
                if old_default:
                    old_default.is_default = False
            self._default_email_template_id = template.id
        
        self._email_templates[template.id] = template
        return template
    
    def _format_missing_fields_list(
        self,
        missing_fields: list[IdentifiedMissingField],
        group_by_category: bool = True,
        include_help: bool = True,
    ) -> str:
        """Format missing fields as a list for email."""
        lines = []
        
        if group_by_category:
            # Group by category
            by_category: dict[str, list[IdentifiedMissingField]] = {}
            for mf in missing_fields:
                cat = mf.category.value.replace("_", " ").title()
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(mf)
            
            for category, fields in by_category.items():
                lines.append(f"\n{category}:")
                for f in fields:
                    lines.append(f"  • {f.field_label}: {f.question_text}")
                    if include_help and f.help_text:
                        lines.append(f"    ({f.help_text})")
                    if f.requires_attachment:
                        lines.append("    [Attachment required]")
        else:
            for f in missing_fields:
                priority_marker = "⚠️ " if f.is_blocking else ""
                lines.append(f"• {priority_marker}{f.field_label}: {f.question_text}")
                if include_help and f.help_text:
                    lines.append(f"  ({f.help_text})")
                if f.requires_attachment:
                    lines.append("  [Attachment required]")
        
        return "\n".join(lines)
    
    def generate_email_text(
        self,
        rfq_data: RFQData,
        missing_fields: list[IdentifiedMissingField],
        sender_name: str,
        sender_title: str = "",
        template_id: Optional[UUID] = None,
    ) -> tuple[str, str]:
        """
        Generate email subject and body for missing info request.
        
        Args:
            rfq_data: The RFQ data
            missing_fields: List of missing fields to include
            sender_name: Name of the sender
            sender_title: Title of the sender
            template_id: Optional template ID to use
            
        Returns:
            Tuple of (subject, body)
        """
        template = None
        if template_id:
            template = self.get_email_template(template_id)
        if not template:
            template = self.get_default_email_template()
        
        if not template:
            # Fallback if no template
            subject = f"Information Required for RFQ: {rfq_data.rfq_number}"
            body = "Please provide the requested information."
            return subject, body
        
        # Format missing fields list
        fields_list = self._format_missing_fields_list(
            missing_fields,
            group_by_category=self.config.group_by_category_in_email,
            include_help=self.config.include_help_text_in_email,
        )
        
        # Build substitution dict
        subs = {
            "rfq_number": rfq_data.rfq_number,
            "customer_name": rfq_data.customer_name,
            "contact_name": rfq_data.contact_name or "Customer",
            "product_name": rfq_data.product_name or "your product",
            "missing_fields_list": fields_list,
            "sender_name": sender_name,
            "sender_title": sender_title,
        }
        
        # Format subject and body
        subject = template.subject_template.format(**subs)
        body = template.body_template.format(**subs)
        
        return subject, body
    
    # Info Request Management
    
    def create_info_request(
        self,
        rfq_data: RFQData,
        missing_fields: list[IdentifiedMissingField],
        sender_name: str,
        created_by: UUID,
        sender_title: str = "",
        recipient_name: Optional[str] = None,
        recipient_email: Optional[str] = None,
        template_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> InfoRequest:
        """
        Create a new information request.
        
        Args:
            rfq_data: The RFQ data
            missing_fields: Fields to request info for
            sender_name: Name of sender
            created_by: User ID creating the request
            sender_title: Title of sender
            recipient_name: Override recipient name
            recipient_email: Override recipient email
            template_id: Email template to use
            notes: Internal notes
            
        Returns:
            Created InfoRequest
        """
        # Generate email text
        subject, body = self.generate_email_text(
            rfq_data=rfq_data,
            missing_fields=missing_fields,
            sender_name=sender_name,
            sender_title=sender_title,
            template_id=template_id,
        )
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=self.config.request_expiry_days)
        
        # Calculate first reminder
        next_reminder_at = None
        if self.config.auto_send_reminders:
            if self.config.default_reminder_frequency == ReminderFrequency.DAILY:
                next_reminder_at = datetime.utcnow() + timedelta(days=1)
            elif self.config.default_reminder_frequency == ReminderFrequency.EVERY_OTHER_DAY:
                next_reminder_at = datetime.utcnow() + timedelta(days=2)
            elif self.config.default_reminder_frequency == ReminderFrequency.WEEKLY:
                next_reminder_at = datetime.utcnow() + timedelta(days=7)
        
        request = InfoRequest(
            id=uuid4(),
            rfq_id=rfq_data.rfq_id,
            recipient_name=recipient_name or rfq_data.contact_name or "Customer",
            recipient_email=recipient_email or rfq_data.contact_email or "",
            subject=subject,
            body_text=body,
            body_html=None,
            missing_fields=missing_fields,
            status=InfoRequestStatus.DRAFT,
            created_by=created_by,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            reminder_frequency=self.config.default_reminder_frequency,
            next_reminder_at=next_reminder_at,
            max_reminders=self.config.max_reminders,
            notes=notes,
        )
        
        self._info_requests[request.id] = request
        return request
    
    def get_info_request(self, request_id: UUID) -> Optional[InfoRequest]:
        """Get an info request by ID."""
        return self._info_requests.get(request_id)
    
    def list_info_requests(
        self,
        rfq_id: Optional[UUID] = None,
        status: Optional[InfoRequestStatus] = None,
        created_by: Optional[UUID] = None,
    ) -> list[InfoRequest]:
        """List info requests with optional filters."""
        requests = list(self._info_requests.values())
        
        if rfq_id:
            requests = [r for r in requests if r.rfq_id == rfq_id]
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        if created_by:
            requests = [r for r in requests if r.created_by == created_by]
        
        return sorted(requests, key=lambda r: r.created_at, reverse=True)
    
    def mark_request_sent(self, request_id: UUID) -> Optional[InfoRequest]:
        """Mark an info request as sent."""
        request = self._info_requests.get(request_id)
        if not request:
            return None
        
        request.status = InfoRequestStatus.SENT
        request.sent_at = datetime.utcnow()
        return request
    
    def mark_request_acknowledged(self, request_id: UUID) -> Optional[InfoRequest]:
        """Mark an info request as acknowledged."""
        request = self._info_requests.get(request_id)
        if not request:
            return None
        
        request.status = InfoRequestStatus.ACKNOWLEDGED
        request.acknowledged_at = datetime.utcnow()
        return request
    
    def mark_request_completed(
        self,
        request_id: UUID,
        resolved_fields: Optional[dict[UUID, str]] = None,
    ) -> Optional[InfoRequest]:
        """Mark an info request as completed."""
        request = self._info_requests.get(request_id)
        if not request:
            return None
        
        request.status = InfoRequestStatus.COMPLETED
        request.completed_at = datetime.utcnow()
        
        # Update resolved fields
        if resolved_fields:
            for mf in request.missing_fields:
                if mf.id in resolved_fields:
                    mf.resolved_at = datetime.utcnow()
                    mf.resolved_value = resolved_fields[mf.id]
        
        return request
    
    def cancel_request(self, request_id: UUID) -> Optional[InfoRequest]:
        """Cancel an info request."""
        request = self._info_requests.get(request_id)
        if not request:
            return None
        
        request.status = InfoRequestStatus.CANCELLED
        return request
    
    def increment_reminder(self, request_id: UUID) -> Optional[InfoRequest]:
        """Increment reminder count and schedule next reminder."""
        request = self._info_requests.get(request_id)
        if not request:
            return None
        
        request.reminder_count += 1
        
        if request.reminder_count >= request.max_reminders:
            request.next_reminder_at = None
        else:
            # Schedule next reminder
            if request.reminder_frequency == ReminderFrequency.DAILY:
                request.next_reminder_at = datetime.utcnow() + timedelta(days=1)
            elif request.reminder_frequency == ReminderFrequency.EVERY_OTHER_DAY:
                request.next_reminder_at = datetime.utcnow() + timedelta(days=2)
            elif request.reminder_frequency == ReminderFrequency.WEEKLY:
                request.next_reminder_at = datetime.utcnow() + timedelta(days=7)
        
        return request
    
    def get_requests_needing_reminders(self) -> list[InfoRequest]:
        """Get all requests that need reminders sent."""
        now = datetime.utcnow()
        return [
            r for r in self._info_requests.values()
            if r.status == InfoRequestStatus.SENT
            and r.next_reminder_at is not None
            and r.next_reminder_at <= now
            and r.reminder_count < r.max_reminders
        ]
    
    def get_expired_requests(self) -> list[InfoRequest]:
        """Get all expired requests."""
        now = datetime.utcnow()
        return [
            r for r in self._info_requests.values()
            if r.status in (InfoRequestStatus.SENT, InfoRequestStatus.ACKNOWLEDGED)
            and r.expires_at is not None
            and r.expires_at < now
        ]
    
    def expire_requests(self) -> int:
        """Mark expired requests and return count."""
        expired = self.get_expired_requests()
        for request in expired:
            request.status = InfoRequestStatus.EXPIRED
        return len(expired)
    
    # Task Management
    
    def create_tasks_for_missing_fields(
        self,
        rfq_id: UUID,
        missing_fields: list[IdentifiedMissingField],
        assigned_to: Optional[UUID] = None,
        linked_request_id: Optional[UUID] = None,
    ) -> list[GeneratedTask]:
        """
        Create tasks for missing fields.
        
        Args:
            rfq_id: The RFQ ID
            missing_fields: Fields to create tasks for
            assigned_to: Optional user to assign tasks to
            linked_request_id: Optional linked info request ID
            
        Returns:
            List of created tasks
        """
        tasks = []
        due_date = date.today() + timedelta(days=self.config.task_due_days)
        
        for mf in missing_fields:
            task = GeneratedTask(
                id=uuid4(),
                rfq_id=rfq_id,
                missing_field_id=mf.id,
                title=f"Get missing info: {mf.field_label}",
                description=f"RFQ requires: {mf.question_text}",
                assigned_to=assigned_to,
                due_date=due_date,
                priority=mf.priority,
                status=TaskStatus.OPEN,
                linked_info_request_id=linked_request_id,
            )
            tasks.append(task)
            self._tasks[task.id] = task
        
        return tasks
    
    def get_task(self, task_id: UUID) -> Optional[GeneratedTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        rfq_id: Optional[UUID] = None,
        assigned_to: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
    ) -> list[GeneratedTask]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())
        
        if rfq_id:
            tasks = [t for t in tasks if t.rfq_id == rfq_id]
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        return sorted(tasks, key=lambda t: t.due_date)
    
    def complete_task(
        self,
        task_id: UUID,
        completed_by: UUID,
        notes: Optional[str] = None,
    ) -> Optional[GeneratedTask]:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.completed_by = completed_by
        if notes:
            task.notes = notes
        
        return task
    
    def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        notes: Optional[str] = None,
    ) -> Optional[GeneratedTask]:
        """Update a task's status."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        task.status = status
        if notes:
            task.notes = notes
        
        return task
    
    # Full Workflow
    
    def process_rfq(
        self,
        rfq_data: RFQData,
        sender_name: str,
        created_by: UUID,
        sender_title: str = "",
        assigned_to: Optional[UUID] = None,
        auto_create_request: bool = True,
        auto_create_tasks: bool = True,
    ) -> tuple[AnalysisResult, Optional[InfoRequest], list[GeneratedTask]]:
        """
        Process an RFQ through the missing info workflow.
        
        Analyzes the RFQ, optionally creates an info request and tasks.
        
        Args:
            rfq_data: The RFQ data to process
            sender_name: Name for email sender
            created_by: User processing the RFQ
            sender_title: Title for email sender
            assigned_to: User to assign tasks to
            auto_create_request: Whether to create an info request
            auto_create_tasks: Whether to create tasks
            
        Returns:
            Tuple of (analysis_result, info_request, tasks)
        """
        # Analyze RFQ
        analysis = self.analyze_rfq(rfq_data)
        
        info_request = None
        tasks: list[GeneratedTask] = []
        
        if analysis.missing_count > 0:
            # Create info request if requested
            if auto_create_request:
                info_request = self.create_info_request(
                    rfq_data=rfq_data,
                    missing_fields=analysis.missing_fields,
                    sender_name=sender_name,
                    created_by=created_by,
                    sender_title=sender_title,
                )
            
            # Create tasks if requested
            if auto_create_tasks and self.config.auto_create_tasks:
                tasks = self.create_tasks_for_missing_fields(
                    rfq_id=rfq_data.rfq_id,
                    missing_fields=analysis.missing_fields,
                    assigned_to=assigned_to,
                    linked_request_id=info_request.id if info_request else None,
                )
        
        return analysis, info_request, tasks


# Singleton instance
_missing_info_workflow_service: Optional[MissingInfoWorkflowService] = None


def get_missing_info_workflow_service() -> MissingInfoWorkflowService:
    """Get the singleton missing info workflow service instance."""
    global _missing_info_workflow_service
    if _missing_info_workflow_service is None:
        _missing_info_workflow_service = MissingInfoWorkflowService()
    return _missing_info_workflow_service


def reset_missing_info_workflow_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _missing_info_workflow_service
    _missing_info_workflow_service = None
