"""
PDF Generation Service.

Handles generation of various PDF documents including:
- Quote PDFs with brand templates
- Qualification Report PDFs
- Today Snapshot PDFs
- Obeya Snapshot PDFs
- Week in Review PDFs
- 8D Report PDFs
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from datetime import timezone
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4
import base64
import hashlib

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PDFDocumentType(str, Enum):
    """Types of PDF documents that can be generated."""
    
    QUOTE = "quote"
    QUALIFICATION_REPORT = "qualification_report"
    TODAY_SNAPSHOT = "today_snapshot"
    OBEYA_SNAPSHOT = "obeya_snapshot"
    WEEK_IN_REVIEW = "week_in_review"
    EIGHT_D_REPORT = "8d_report"
    RFQ_SUMMARY = "rfq_summary"
    A3_REPORT = "a3_report"
    TRAINING_CERTIFICATE = "training_certificate"


class PDFLanguage(str, Enum):
    """Supported languages for PDF generation."""
    
    ENGLISH = "en"
    FRENCH = "fr"
    ARABIC = "ar"


class PDFBrandTemplate(str, Enum):
    """Brand templates for PDF generation."""
    
    DEFAULT = "default"
    CORPORATE = "corporate"
    MINIMAL = "minimal"
    CUSTOMER_FACING = "customer_facing"
    INTERNAL = "internal"


class PDFStatus(str, Enum):
    """Status of PDF generation."""
    
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class WatermarkType(str, Enum):
    """Types of watermarks for PDFs."""
    
    NONE = "none"
    DRAFT = "draft"
    CONFIDENTIAL = "confidential"
    INTERNAL_ONLY = "internal_only"
    REVISION = "revision"
    SUPERSEDED = "superseded"


@dataclass
class BrandingConfig:
    """Branding configuration for PDF generation."""
    
    template: PDFBrandTemplate = PDFBrandTemplate.DEFAULT
    logo_base64: Optional[str] = None
    primary_color: str = "#1a365d"
    secondary_color: str = "#2b6cb0"
    accent_color: str = "#38a169"
    font_family: str = "Helvetica"
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    include_page_numbers: bool = True
    include_generated_date: bool = True
    include_confidentiality_notice: bool = False
    confidentiality_text: str = "CONFIDENTIAL - For authorized use only"
    legal_boilerplate: Optional[str] = None
    customer_specific_footer: Optional[str] = None


@dataclass
class WatermarkConfig:
    """Watermark configuration for PDFs."""
    
    watermark_type: WatermarkType = WatermarkType.NONE
    custom_text: Optional[str] = None
    opacity: float = 0.15
    angle: float = 45.0
    font_size: int = 72
    color: str = "#cccccc"
    include_revision_number: bool = False
    revision_text: Optional[str] = None


@dataclass
class PDFGenerationOptions:
    """Options for PDF generation."""
    
    language: PDFLanguage = PDFLanguage.ENGLISH
    branding: BrandingConfig = field(default_factory=BrandingConfig)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    paper_size: str = "A4"
    orientation: str = "portrait"
    margin_top: float = 25.0
    margin_bottom: float = 25.0
    margin_left: float = 20.0
    margin_right: float = 20.0
    include_table_of_contents: bool = False
    include_appendices: bool = False
    compress: bool = True
    encrypt: bool = False
    password: Optional[str] = None


@dataclass
class PDFSection:
    """A section in a PDF document."""
    
    id: str
    title: str
    content: dict[str, Any]
    order: int
    include_in_toc: bool = True
    page_break_before: bool = False
    page_break_after: bool = False


@dataclass
class PDFAttachment:
    """An attachment to include in or with the PDF."""
    
    id: UUID
    filename: str
    content_type: str
    data_base64: Optional[str] = None
    storage_path: Optional[str] = None
    embed_inline: bool = False
    page_number: Optional[int] = None


@dataclass
class GeneratedPDF:
    """Result of PDF generation."""
    
    id: UUID
    document_type: PDFDocumentType
    filename: str
    content_base64: str
    content_hash: str
    size_bytes: int
    page_count: int
    generated_at: datetime
    generated_by: UUID
    options: PDFGenerationOptions
    source_entity_type: str
    source_entity_id: UUID
    source_version: Optional[str] = None
    status: PDFStatus = PDFStatus.COMPLETED
    storage_path: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuotePDFData:
    """Data for generating a Quote PDF."""
    
    quote_id: UUID
    quote_number: str
    revision: str
    customer_name: str
    product_name: str
    part_number: str
    validity_date: date
    currency: str
    incoterms: str
    payment_terms: str
    lead_time_days: int
    moq: int
    
    # Pricing
    line_items: list[dict[str, Any]]
    price_breaks: list[dict[str, Any]]
    total_price: float
    unit_price: float
    
    # Additional info
    assumptions: list[str]
    conditions: list[str]
    exclusions: list[str]
    
    # Approval info (required)
    prepared_by: str
    
    # Optional fields
    customer_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    
    # Internal (optional - for internal versions)
    include_margin: bool = False
    margin_percentage: Optional[float] = None
    cost_breakdown: Optional[dict[str, float]] = None
    
    # Optional approval info
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class QualificationPDFData:
    """Data for generating a Qualification Report PDF."""
    
    qualification_id: UUID
    rfq_id: UUID
    rfq_number: str
    customer_name: str
    product_family: str
    opportunity_value: float
    currency: str
    
    # Scoring
    capability_score: float
    strategic_score: float
    risk_score: float
    commercial_score: float
    operational_score: float
    overall_score: float
    
    # Decision
    decision: str  # NO_QUOTE, QUOTE, QUOTE_WITH_CONDITIONS
    decision_rationale: str
    conditions: list[str]
    
    # Risk items
    risks: list[dict[str, Any]]
    
    # Override info
    is_override: bool = False
    override_reason: Optional[str] = None
    override_approved_by: Optional[str] = None
    
    # Dates
    qualified_at: datetime = field(default_factory=_utcnow)
    qualified_by: str = ""


@dataclass
class TodaySnapshotPDFData:
    """Data for generating a Today Snapshot PDF."""
    
    user_id: UUID
    user_name: str
    snapshot_date: date
    
    # Top priorities
    top_priorities: list[dict[str, Any]]
    
    # Risks by category
    risks_by_category: dict[str, list[dict[str, Any]]]
    top_risks: list[dict[str, Any]]
    
    # Commitments
    overdue_commitments: list[dict[str, Any]]
    due_today_commitments: list[dict[str, Any]]
    
    # Abnormalities
    abnormality_counts: dict[str, int]
    critical_abnormalities: list[dict[str, Any]]
    
    # LSW status
    lsw_summary: dict[str, Any]
    
    # Quick metrics
    metrics: list[dict[str, Any]]
    
    # Optional greeting
    greeting: Optional[str] = None


@dataclass
class ObeyaSnapshotPDFData:
    """Data for generating an Obeya Snapshot PDF."""
    
    snapshot_date: date
    period_start: date
    period_end: date
    
    # SQDCP sections
    safety_items: list[dict[str, Any]]
    quality_items: list[dict[str, Any]]
    delivery_items: list[dict[str, Any]]
    cost_items: list[dict[str, Any]]
    people_items: list[dict[str, Any]]
    
    # Red items summary
    red_items: list[dict[str, Any]]
    red_items_count: int
    
    # Trends
    trends: dict[str, dict[str, Any]]
    
    # Countermeasures
    countermeasures_in_progress: list[dict[str, Any]]
    countermeasures_due: list[dict[str, Any]]


@dataclass
class WeekInReviewPDFData:
    """Data for generating a Week in Review PDF."""
    
    week_start: date
    week_end: date
    generated_by: str
    
    # Today summary
    today_summary: TodaySnapshotPDFData
    
    # Obeya summary
    obeya_summary: ObeyaSnapshotPDFData
    
    # Top risks
    top_risks: list[dict[str, Any]]
    
    # Open A3s
    open_a3s: list[dict[str, Any]]
    
    # Key metrics
    key_metrics: list[dict[str, Any]]
    
    # Highlights and lowlights
    highlights: list[str]
    lowlights: list[str]
    
    # Next week focus
    next_week_priorities: list[str]


@dataclass
class EightDReportPDFData:
    """Data for generating an 8D Report PDF."""
    
    capa_id: UUID
    capa_number: str
    report_date: date
    
    # D1: Team
    team_leader: str
    team_members: list[str]
    
    # D2: Problem Description
    problem_description: str
    problem_source: str
    affected_products: list[str]
    affected_quantity: int
    detection_date: date
    customer_impact: Optional[str]
    
    # D3: Containment Actions
    containment_actions: list[dict[str, Any]]
    containment_effective: bool
    
    # D4: Root Cause Analysis
    root_cause_method: str  # 5-Why, Fishbone, etc.
    root_cause_analysis: str
    root_causes: list[str]
    contributing_factors: list[str]
    linked_a3_id: Optional[UUID]
    
    # D5: Corrective Actions
    corrective_actions: list[dict[str, Any]]
    
    # D6: Implementation Verification
    verification_method: str
    verification_results: str
    verification_date: Optional[date]
    verified_by: Optional[str]
    verification_passed: bool
    
    # D7: Preventive Actions
    preventive_actions: list[dict[str, Any]]
    standard_work_updates: list[dict[str, Any]]
    
    # D8: Closure
    lessons_learned: list[str]
    team_recognition: Optional[str]
    closure_date: Optional[date]
    closed_by: Optional[str]
    effectiveness_check_date: Optional[date]
    effectiveness_status: Optional[str]


@dataclass
class PDFGenerationRequest:
    """Request to generate a PDF."""
    
    id: UUID
    document_type: PDFDocumentType
    source_entity_type: str
    source_entity_id: UUID
    source_version: Optional[str]
    requested_by: UUID
    requested_at: datetime
    options: PDFGenerationOptions
    data: Any  # One of the *PDFData dataclasses
    status: PDFStatus = PDFStatus.PENDING
    priority: int = 5
    callback_url: Optional[str] = None


@dataclass
class PDFTemplate:
    """A reusable PDF template."""
    
    id: UUID
    name: str
    document_type: PDFDocumentType
    branding: BrandingConfig
    watermark: WatermarkConfig
    default_options: PDFGenerationOptions
    sections: list[PDFSection]
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    created_by: Optional[UUID] = None


class PDFGenerationService:
    """
    Service for generating PDF documents.
    
    Handles the complete lifecycle of PDF generation including:
    - Template management
    - Document generation
    - Caching and storage
    - Version binding (immutable linking)
    """
    
    def __init__(self) -> None:
        """Initialize the PDF generation service."""
        self._templates: dict[UUID, PDFTemplate] = {}
        self._generated_pdfs: dict[UUID, GeneratedPDF] = {}
        self._generation_requests: dict[UUID, PDFGenerationRequest] = {}
        self._default_templates: dict[PDFDocumentType, UUID] = {}
        self._register_default_templates()
    
    def _register_default_templates(self) -> None:
        """Register default templates for each document type."""
        # Quote template
        quote_template = PDFTemplate(
            id=uuid4(),
            name="Default Quote Template",
            document_type=PDFDocumentType.QUOTE,
            branding=BrandingConfig(
                template=PDFBrandTemplate.CUSTOMER_FACING,
                include_confidentiality_notice=True,
            ),
            watermark=WatermarkConfig(watermark_type=WatermarkType.NONE),
            default_options=PDFGenerationOptions(
                language=PDFLanguage.ENGLISH,
                include_table_of_contents=False,
            ),
            sections=[
                PDFSection(
                    id="header",
                    title="Quote Header",
                    content={},
                    order=1,
                    include_in_toc=False,
                ),
                PDFSection(
                    id="customer_info",
                    title="Customer Information",
                    content={},
                    order=2,
                ),
                PDFSection(
                    id="product_details",
                    title="Product Details",
                    content={},
                    order=3,
                ),
                PDFSection(
                    id="pricing",
                    title="Pricing",
                    content={},
                    order=4,
                ),
                PDFSection(
                    id="terms",
                    title="Terms & Conditions",
                    content={},
                    order=5,
                ),
                PDFSection(
                    id="assumptions",
                    title="Assumptions",
                    content={},
                    order=6,
                ),
            ],
            is_default=True,
        )
        self._templates[quote_template.id] = quote_template
        self._default_templates[PDFDocumentType.QUOTE] = quote_template.id
        
        # Qualification Report template
        qual_template = PDFTemplate(
            id=uuid4(),
            name="Default Qualification Report Template",
            document_type=PDFDocumentType.QUALIFICATION_REPORT,
            branding=BrandingConfig(
                template=PDFBrandTemplate.INTERNAL,
                include_confidentiality_notice=True,
                confidentiality_text="INTERNAL USE ONLY",
            ),
            watermark=WatermarkConfig(watermark_type=WatermarkType.INTERNAL_ONLY),
            default_options=PDFGenerationOptions(
                language=PDFLanguage.ENGLISH,
                include_table_of_contents=True,
            ),
            sections=[
                PDFSection(id="summary", title="Executive Summary", content={}, order=1),
                PDFSection(id="rfq_details", title="RFQ Details", content={}, order=2),
                PDFSection(id="scoring", title="Qualification Scoring", content={}, order=3),
                PDFSection(id="risks", title="Risk Assessment", content={}, order=4),
                PDFSection(id="decision", title="Decision & Rationale", content={}, order=5),
                PDFSection(id="conditions", title="Conditions", content={}, order=6),
            ],
            is_default=True,
        )
        self._templates[qual_template.id] = qual_template
        self._default_templates[PDFDocumentType.QUALIFICATION_REPORT] = qual_template.id
        
        # Today Snapshot template
        today_template = PDFTemplate(
            id=uuid4(),
            name="Default Today Snapshot Template",
            document_type=PDFDocumentType.TODAY_SNAPSHOT,
            branding=BrandingConfig(template=PDFBrandTemplate.MINIMAL),
            watermark=WatermarkConfig(watermark_type=WatermarkType.NONE),
            default_options=PDFGenerationOptions(
                language=PDFLanguage.ENGLISH,
                paper_size="A4",
            ),
            sections=[
                PDFSection(id="priorities", title="Top 3 Priorities", content={}, order=1),
                PDFSection(id="risks", title="Key Risks", content={}, order=2),
                PDFSection(id="commitments", title="Commitments", content={}, order=3),
                PDFSection(id="abnormalities", title="Abnormalities", content={}, order=4),
                PDFSection(id="lsw", title="LSW Status", content={}, order=5),
                PDFSection(id="metrics", title="Quick Metrics", content={}, order=6),
            ],
            is_default=True,
        )
        self._templates[today_template.id] = today_template
        self._default_templates[PDFDocumentType.TODAY_SNAPSHOT] = today_template.id
        
        # Obeya Snapshot template
        obeya_template = PDFTemplate(
            id=uuid4(),
            name="Default Obeya Snapshot Template",
            document_type=PDFDocumentType.OBEYA_SNAPSHOT,
            branding=BrandingConfig(template=PDFBrandTemplate.CORPORATE),
            watermark=WatermarkConfig(watermark_type=WatermarkType.NONE),
            default_options=PDFGenerationOptions(
                language=PDFLanguage.ENGLISH,
                orientation="landscape",
                include_table_of_contents=False,
            ),
            sections=[
                PDFSection(id="safety", title="Safety", content={}, order=1),
                PDFSection(id="quality", title="Quality", content={}, order=2),
                PDFSection(id="delivery", title="Delivery", content={}, order=3),
                PDFSection(id="cost", title="Cost", content={}, order=4),
                PDFSection(id="people", title="People", content={}, order=5),
                PDFSection(id="red_items", title="Red Items Summary", content={}, order=6),
            ],
            is_default=True,
        )
        self._templates[obeya_template.id] = obeya_template
        self._default_templates[PDFDocumentType.OBEYA_SNAPSHOT] = obeya_template.id
        
        # Week in Review template
        wir_template = PDFTemplate(
            id=uuid4(),
            name="Default Week in Review Template",
            document_type=PDFDocumentType.WEEK_IN_REVIEW,
            branding=BrandingConfig(
                template=PDFBrandTemplate.CORPORATE,
                include_confidentiality_notice=True,
            ),
            watermark=WatermarkConfig(watermark_type=WatermarkType.NONE),
            default_options=PDFGenerationOptions(
                language=PDFLanguage.ENGLISH,
                include_table_of_contents=True,
            ),
            sections=[
                PDFSection(id="executive_summary", title="Executive Summary", content={}, order=1),
                PDFSection(id="today_summary", title="Today Summary", content={}, order=2),
                PDFSection(id="obeya_summary", title="Obeya Summary", content={}, order=3),
                PDFSection(id="top_risks", title="Top Risks", content={}, order=4),
                PDFSection(id="open_a3s", title="Open A3s", content={}, order=5),
                PDFSection(id="key_metrics", title="Key Metrics", content={}, order=6),
                PDFSection(id="next_week", title="Next Week Focus", content={}, order=7),
            ],
            is_default=True,
        )
        self._templates[wir_template.id] = wir_template
        self._default_templates[PDFDocumentType.WEEK_IN_REVIEW] = wir_template.id
        
        # 8D Report template
        eight_d_template = PDFTemplate(
            id=uuid4(),
            name="Default 8D Report Template",
            document_type=PDFDocumentType.EIGHT_D_REPORT,
            branding=BrandingConfig(
                template=PDFBrandTemplate.CORPORATE,
                include_confidentiality_notice=True,
            ),
            watermark=WatermarkConfig(watermark_type=WatermarkType.NONE),
            default_options=PDFGenerationOptions(
                language=PDFLanguage.ENGLISH,
                include_table_of_contents=True,
            ),
            sections=[
                PDFSection(id="d1_team", title="D1: Team", content={}, order=1),
                PDFSection(id="d2_problem", title="D2: Problem Description", content={}, order=2),
                PDFSection(id="d3_containment", title="D3: Containment Actions", content={}, order=3),
                PDFSection(id="d4_root_cause", title="D4: Root Cause Analysis", content={}, order=4),
                PDFSection(id="d5_corrective", title="D5: Corrective Actions", content={}, order=5),
                PDFSection(id="d6_verification", title="D6: Verification", content={}, order=6),
                PDFSection(id="d7_preventive", title="D7: Preventive Actions", content={}, order=7),
                PDFSection(id="d8_closure", title="D8: Closure", content={}, order=8),
            ],
            is_default=True,
        )
        self._templates[eight_d_template.id] = eight_d_template
        self._default_templates[PDFDocumentType.EIGHT_D_REPORT] = eight_d_template.id
    
    # Template Management
    
    def get_template(self, template_id: UUID) -> Optional[PDFTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_default_template(self, document_type: PDFDocumentType) -> Optional[PDFTemplate]:
        """Get the default template for a document type."""
        template_id = self._default_templates.get(document_type)
        if template_id:
            return self._templates.get(template_id)
        return None
    
    def list_templates(
        self,
        document_type: Optional[PDFDocumentType] = None,
        active_only: bool = True,
    ) -> list[PDFTemplate]:
        """List available templates."""
        templates = list(self._templates.values())
        
        if document_type:
            templates = [t for t in templates if t.document_type == document_type]
        
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        return sorted(templates, key=lambda t: (t.document_type.value, t.name))

    def create_template(
        self,
        name: str,
        document_type: PDFDocumentType,
        branding: BrandingConfig,
        watermark: WatermarkConfig,
        default_options: PDFGenerationOptions,
        sections: list[PDFSection],
        created_by: UUID,
        is_default: bool = False,
    ) -> PDFTemplate:
        """Create a new PDF template."""
        template = PDFTemplate(
            id=uuid4(),
            name=name,
            document_type=document_type,
            branding=branding,
            watermark=watermark,
            default_options=default_options,
            sections=sections,
            is_default=is_default,
            created_by=created_by,
        )
        
        if is_default:
            # Unset previous default
            if document_type in self._default_templates:
                old_default_id = self._default_templates[document_type]
                if old_default_id in self._templates:
                    self._templates[old_default_id].is_default = False
            self._default_templates[document_type] = template.id
        
        self._templates[template.id] = template
        return template
    
    def update_template(
        self,
        template_id: UUID,
        name: Optional[str] = None,
        branding: Optional[BrandingConfig] = None,
        watermark: Optional[WatermarkConfig] = None,
        default_options: Optional[PDFGenerationOptions] = None,
        sections: Optional[list[PDFSection]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[PDFTemplate]:
        """Update an existing template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        if name is not None:
            template.name = name
        if branding is not None:
            template.branding = branding
        if watermark is not None:
            template.watermark = watermark
        if default_options is not None:
            template.default_options = default_options
        if sections is not None:
            template.sections = sections
        if is_active is not None:
            template.is_active = is_active
        
        template.updated_at = _utcnow()
        return template
    
    def set_default_template(
        self,
        template_id: UUID,
    ) -> bool:
        """Set a template as the default for its document type."""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        # Unset previous default
        doc_type = template.document_type
        if doc_type in self._default_templates:
            old_default_id = self._default_templates[doc_type]
            if old_default_id in self._templates:
                self._templates[old_default_id].is_default = False
        
        template.is_default = True
        self._default_templates[doc_type] = template_id
        return True
    
    # PDF Generation
    
    def _generate_pdf_content(
        self,
        document_type: PDFDocumentType,
        data: Any,
        options: PDFGenerationOptions,
        template: PDFTemplate,
    ) -> tuple[str, int]:
        """
        Generate PDF content.
        
        In a real implementation, this would use a PDF library like
        ReportLab, WeasyPrint, or similar. For now, we generate
        a simulated PDF structure.
        
        Returns: (base64_content, page_count)
        """
        # Build a structured document representation
        document = {
            "document_type": document_type.value,
            "generated_at": _utcnow().isoformat(),
            "language": options.language.value,
            "template_id": str(template.id),
            "branding": {
                "template": template.branding.template.value,
                "primary_color": template.branding.primary_color,
                "font_family": template.branding.font_family,
                "header_text": template.branding.header_text,
                "footer_text": template.branding.footer_text,
            },
            "watermark": {
                "type": options.watermark.watermark_type.value,
                "opacity": options.watermark.opacity,
            },
            "sections": [],
            "data": {},
        }
        
        # Add sections based on template
        for section in sorted(template.sections, key=lambda s: s.order):
            document["sections"].append({
                "id": section.id,
                "title": section.title,
                "page_break_before": section.page_break_before,
            })
        
        # Add data based on document type
        page_count = 1
        
        if document_type == PDFDocumentType.QUOTE:
            quote_data: QuotePDFData = data
            document["data"] = {
                "quote_number": quote_data.quote_number,
                "revision": quote_data.revision,
                "customer": quote_data.customer_name,
                "product": quote_data.product_name,
                "part_number": quote_data.part_number,
                "total_price": quote_data.total_price,
                "validity_date": quote_data.validity_date.isoformat(),
                "line_items_count": len(quote_data.line_items),
                "conditions_count": len(quote_data.conditions),
                "assumptions_count": len(quote_data.assumptions),
            }
            # Estimate pages based on content
            page_count = max(1, (len(quote_data.line_items) // 15) + 2)
        
        elif document_type == PDFDocumentType.QUALIFICATION_REPORT:
            qual_data: QualificationPDFData = data
            document["data"] = {
                "rfq_number": qual_data.rfq_number,
                "customer": qual_data.customer_name,
                "decision": qual_data.decision,
                "overall_score": qual_data.overall_score,
                "risks_count": len(qual_data.risks),
                "conditions_count": len(qual_data.conditions),
            }
            page_count = 2 + (len(qual_data.risks) // 5)
        
        elif document_type == PDFDocumentType.TODAY_SNAPSHOT:
            today_data: TodaySnapshotPDFData = data
            document["data"] = {
                "user_name": today_data.user_name,
                "snapshot_date": today_data.snapshot_date.isoformat(),
                "priorities_count": len(today_data.top_priorities),
                "risks_count": sum(len(r) for r in today_data.risks_by_category.values()),
                "overdue_commitments": len(today_data.overdue_commitments),
            }
            page_count = 1
        
        elif document_type == PDFDocumentType.OBEYA_SNAPSHOT:
            obeya_data: ObeyaSnapshotPDFData = data
            document["data"] = {
                "snapshot_date": obeya_data.snapshot_date.isoformat(),
                "red_items_count": obeya_data.red_items_count,
                "safety_count": len(obeya_data.safety_items),
                "quality_count": len(obeya_data.quality_items),
                "delivery_count": len(obeya_data.delivery_items),
                "cost_count": len(obeya_data.cost_items),
                "people_count": len(obeya_data.people_items),
            }
            page_count = 2
        
        elif document_type == PDFDocumentType.WEEK_IN_REVIEW:
            wir_data: WeekInReviewPDFData = data
            document["data"] = {
                "week_start": wir_data.week_start.isoformat(),
                "week_end": wir_data.week_end.isoformat(),
                "top_risks_count": len(wir_data.top_risks),
                "open_a3s_count": len(wir_data.open_a3s),
                "highlights_count": len(wir_data.highlights),
                "lowlights_count": len(wir_data.lowlights),
            }
            page_count = 4
        
        elif document_type == PDFDocumentType.EIGHT_D_REPORT:
            eight_d_data: EightDReportPDFData = data
            document["data"] = {
                "capa_number": eight_d_data.capa_number,
                "team_size": len(eight_d_data.team_members) + 1,
                "containment_actions_count": len(eight_d_data.containment_actions),
                "corrective_actions_count": len(eight_d_data.corrective_actions),
                "preventive_actions_count": len(eight_d_data.preventive_actions),
                "root_causes_count": len(eight_d_data.root_causes),
                "lessons_learned_count": len(eight_d_data.lessons_learned),
            }
            page_count = 3 + (len(eight_d_data.corrective_actions) // 5)
        
        # Serialize to JSON and encode as base64
        import json
        json_content = json.dumps(document, indent=2, default=str)
        content_base64 = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")
        
        return content_base64, page_count
    
    def generate_pdf(
        self,
        document_type: PDFDocumentType,
        data: Any,
        source_entity_type: str,
        source_entity_id: UUID,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
        source_version: Optional[str] = None,
    ) -> GeneratedPDF:
        """
        Generate a PDF document.
        
        Args:
            document_type: Type of PDF to generate
            data: Data for the PDF (type depends on document_type)
            source_entity_type: Type of source entity (quote, rfq, etc.)
            source_entity_id: ID of the source entity
            generated_by: User generating the PDF
            options: Generation options (uses defaults if not provided)
            template_id: Template to use (uses default if not provided)
            source_version: Version of source entity (for immutable binding)
        
        Returns:
            Generated PDF object
        """
        # Get template
        if template_id:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
        else:
            template = self.get_default_template(document_type)
            if not template:
                raise ValueError(f"No default template for: {document_type}")
        
        # Merge options with template defaults
        if options is None:
            options = template.default_options
        
        # Generate content
        content_base64, page_count = self._generate_pdf_content(
            document_type=document_type,
            data=data,
            options=options,
            template=template,
        )
        
        # Calculate hash for content verification
        content_hash = hashlib.sha256(content_base64.encode()).hexdigest()
        
        # Generate filename
        timestamp = _utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_type.value}_{source_entity_id}_{timestamp}.pdf"
        
        # Create result
        generated_pdf = GeneratedPDF(
            id=uuid4(),
            document_type=document_type,
            filename=filename,
            content_base64=content_base64,
            content_hash=content_hash,
            size_bytes=len(content_base64),
            page_count=page_count,
            generated_at=_utcnow(),
            generated_by=generated_by,
            options=options,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            source_version=source_version,
            status=PDFStatus.COMPLETED,
            expires_at=_utcnow() + timedelta(days=30),
            metadata={
                "template_id": str(template.id),
                "template_name": template.name,
            },
        )
        
        self._generated_pdfs[generated_pdf.id] = generated_pdf
        return generated_pdf
    
    def generate_quote_pdf(
        self,
        data: QuotePDFData,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
        include_internal: bool = False,
    ) -> GeneratedPDF:
        """Generate a Quote PDF."""
        # Determine if internal version
        if include_internal and data.include_margin:
            # Use internal template with margin info
            if options is None:
                options = PDFGenerationOptions(
                    watermark=WatermarkConfig(
                        watermark_type=WatermarkType.INTERNAL_ONLY,
                    ),
                )
        
        return self.generate_pdf(
            document_type=PDFDocumentType.QUOTE,
            data=data,
            source_entity_type="quote",
            source_entity_id=data.quote_id,
            generated_by=generated_by,
            options=options,
            template_id=template_id,
            source_version=data.revision,
        )
    
    def generate_qualification_pdf(
        self,
        data: QualificationPDFData,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
    ) -> GeneratedPDF:
        """Generate a Qualification Report PDF."""
        return self.generate_pdf(
            document_type=PDFDocumentType.QUALIFICATION_REPORT,
            data=data,
            source_entity_type="qualification",
            source_entity_id=data.qualification_id,
            generated_by=generated_by,
            options=options,
            template_id=template_id,
        )
    
    def generate_today_snapshot_pdf(
        self,
        data: TodaySnapshotPDFData,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
    ) -> GeneratedPDF:
        """Generate a Today Snapshot PDF."""
        return self.generate_pdf(
            document_type=PDFDocumentType.TODAY_SNAPSHOT,
            data=data,
            source_entity_type="today_snapshot",
            source_entity_id=data.user_id,
            generated_by=generated_by,
            options=options,
            template_id=template_id,
            source_version=data.snapshot_date.isoformat(),
        )
    
    def generate_obeya_snapshot_pdf(
        self,
        data: ObeyaSnapshotPDFData,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
    ) -> GeneratedPDF:
        """Generate an Obeya Snapshot PDF."""
        snapshot_id = uuid4()  # Generate ID for this snapshot
        return self.generate_pdf(
            document_type=PDFDocumentType.OBEYA_SNAPSHOT,
            data=data,
            source_entity_type="obeya_snapshot",
            source_entity_id=snapshot_id,
            generated_by=generated_by,
            options=options,
            template_id=template_id,
            source_version=data.snapshot_date.isoformat(),
        )
    
    def generate_week_in_review_pdf(
        self,
        data: WeekInReviewPDFData,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
    ) -> GeneratedPDF:
        """Generate a Week in Review PDF."""
        review_id = uuid4()  # Generate ID for this review
        return self.generate_pdf(
            document_type=PDFDocumentType.WEEK_IN_REVIEW,
            data=data,
            source_entity_type="week_in_review",
            source_entity_id=review_id,
            generated_by=generated_by,
            options=options,
            template_id=template_id,
            source_version=f"{data.week_start.isoformat()}_{data.week_end.isoformat()}",
        )
    
    def generate_8d_report_pdf(
        self,
        data: EightDReportPDFData,
        generated_by: UUID,
        options: Optional[PDFGenerationOptions] = None,
        template_id: Optional[UUID] = None,
    ) -> GeneratedPDF:
        """Generate an 8D Report PDF."""
        return self.generate_pdf(
            document_type=PDFDocumentType.EIGHT_D_REPORT,
            data=data,
            source_entity_type="capa",
            source_entity_id=data.capa_id,
            generated_by=generated_by,
            options=options,
            template_id=template_id,
        )
    
    # PDF Retrieval
    
    def get_generated_pdf(self, pdf_id: UUID) -> Optional[GeneratedPDF]:
        """Get a generated PDF by ID."""
        pdf = self._generated_pdfs.get(pdf_id)
        if pdf and pdf.expires_at and pdf.expires_at < _utcnow():
            pdf.status = PDFStatus.EXPIRED
        return pdf
    
    def list_generated_pdfs(
        self,
        source_entity_type: Optional[str] = None,
        source_entity_id: Optional[UUID] = None,
        document_type: Optional[PDFDocumentType] = None,
        generated_by: Optional[UUID] = None,
        include_expired: bool = False,
    ) -> list[GeneratedPDF]:
        """List generated PDFs with optional filters."""
        pdfs = list(self._generated_pdfs.values())
        
        # Update expired status
        now = _utcnow()
        for pdf in pdfs:
            if pdf.expires_at and pdf.expires_at < now:
                pdf.status = PDFStatus.EXPIRED
        
        if source_entity_type:
            pdfs = [p for p in pdfs if p.source_entity_type == source_entity_type]
        
        if source_entity_id:
            pdfs = [p for p in pdfs if p.source_entity_id == source_entity_id]
        
        if document_type:
            pdfs = [p for p in pdfs if p.document_type == document_type]
        
        if generated_by:
            pdfs = [p for p in pdfs if p.generated_by == generated_by]
        
        if not include_expired:
            pdfs = [p for p in pdfs if p.status != PDFStatus.EXPIRED]
        
        return sorted(pdfs, key=lambda p: p.generated_at, reverse=True)
    
    def get_pdfs_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        version: Optional[str] = None,
    ) -> list[GeneratedPDF]:
        """Get all PDFs generated for a specific entity."""
        pdfs = self.list_generated_pdfs(
            source_entity_type=entity_type,
            source_entity_id=entity_id,
        )
        
        if version:
            pdfs = [p for p in pdfs if p.source_version == version]
        
        return pdfs
    
    def verify_pdf_integrity(self, pdf_id: UUID) -> bool:
        """Verify the integrity of a generated PDF using its hash."""
        pdf = self._generated_pdfs.get(pdf_id)
        if not pdf:
            return False
        
        calculated_hash = hashlib.sha256(pdf.content_base64.encode()).hexdigest()
        return calculated_hash == pdf.content_hash
    
    def delete_pdf(self, pdf_id: UUID) -> bool:
        """Delete a generated PDF."""
        if pdf_id in self._generated_pdfs:
            del self._generated_pdfs[pdf_id]
            return True
        return False
    
    def cleanup_expired_pdfs(self) -> int:
        """Remove all expired PDFs and return count removed."""
        now = _utcnow()
        expired_ids = [
            pdf_id
            for pdf_id, pdf in self._generated_pdfs.items()
            if pdf.expires_at and pdf.expires_at < now
        ]
        
        for pdf_id in expired_ids:
            del self._generated_pdfs[pdf_id]
        
        return len(expired_ids)


# Singleton instance
_pdf_generation_service: Optional[PDFGenerationService] = None


def get_pdf_generation_service() -> PDFGenerationService:
    """Get the singleton PDF generation service instance."""
    global _pdf_generation_service
    if _pdf_generation_service is None:
        _pdf_generation_service = PDFGenerationService()
    return _pdf_generation_service


def reset_pdf_generation_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _pdf_generation_service
    _pdf_generation_service = None
