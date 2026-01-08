"""
Smart Ingestion Service

Provides OCR and AI-powered parsing for:
- Incoming RFQ emails and attachments
- PDF documents (quotes, drawings, specs)
- Auto-creation of opportunities from parsed data
- Intelligent field extraction and entity resolution
"""
from __future__ import annotations

import base64
import hashlib
import mimetypes
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sensei.models.rfq import RFQ
    from sensei.models.opportunity import Opportunity
    from sensei.models.account import Account, Contact


# =============================================================================
# Enums
# =============================================================================

class DocumentType(str, Enum):
    """Types of documents that can be ingested."""
    EMAIL = "email"
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "excel"
    WORD = "word"
    TEXT = "text"
    UNKNOWN = "unknown"


class IngestionStatus(str, Enum):
    """Status of an ingestion job."""
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class ExtractionConfidence(str, Enum):
    """Confidence level of extracted data."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    CONTACT = "contact"
    PRODUCT = "product"
    QUOTE = "quote"
    ATTACHMENT = "attachment"


class FieldType(str, Enum):
    """Types of fields that can be extracted."""
    COMPANY_NAME = "company_name"
    CONTACT_NAME = "contact_name"
    CONTACT_EMAIL = "contact_email"
    CONTACT_PHONE = "contact_phone"
    PART_NUMBER = "part_number"
    PART_DESCRIPTION = "part_description"
    QUANTITY = "quantity"
    TARGET_PRICE = "target_price"
    DUE_DATE = "due_date"
    DELIVERY_DATE = "delivery_date"
    MATERIAL_SPEC = "material_spec"
    DRAWING_NUMBER = "drawing_number"
    REVISION = "revision"
    TOLERANCE = "tolerance"
    ANNUAL_VOLUME = "annual_volume"
    PROJECT_NAME = "project_name"
    RFQ_NUMBER = "rfq_number"
    CURRENCY = "currency"
    INCOTERMS = "incoterms"
    SHIPPING_ADDRESS = "shipping_address"
    SPECIAL_REQUIREMENTS = "special_requirements"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ExtractedField:
    """A single extracted field from a document."""
    field_type: FieldType
    value: Any
    raw_text: str
    confidence: ExtractionConfidence
    source_location: str | None = None  # Page/line/region info
    alternatives: list[Any] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Check if the extracted field is valid."""
        return len(self.validation_errors) == 0
    
    @property
    def needs_review(self) -> bool:
        """Check if field needs manual review."""
        return self.confidence in (ExtractionConfidence.LOW, ExtractionConfidence.UNCERTAIN)


@dataclass
class ExtractedEntity:
    """An entity extracted from a document."""
    id: str
    entity_type: EntityType
    fields: dict[FieldType, ExtractedField] = field(default_factory=dict)
    confidence: ExtractionConfidence = ExtractionConfidence.MEDIUM
    source_document_id: str | None = None
    created_entity_id: str | None = None  # ID if entity was created in system
    
    def get_field_value(self, field_type: FieldType, default: Any = None) -> Any:
        """Get the value of a field."""
        field = self.fields.get(field_type)
        return field.value if field else default
    
    @property
    def validation_errors(self) -> list[str]:
        """Get all validation errors from fields."""
        errors = []
        for field in self.fields.values():
            errors.extend(field.validation_errors)
        return errors
    
    @property
    def is_complete(self) -> bool:
        """Check if entity has all required fields."""
        required_fields = REQUIRED_FIELDS_BY_ENTITY.get(self.entity_type, set())
        return all(ft in self.fields for ft in required_fields)


@dataclass
class DocumentMetadata:
    """Metadata about an ingested document."""
    id: str
    filename: str
    document_type: DocumentType
    mime_type: str
    size_bytes: int
    checksum: str
    page_count: int = 1
    ingestion_timestamp: datetime = field(default_factory=datetime.utcnow)
    source_email_id: str | None = None
    source_email_subject: str | None = None
    source_email_from: str | None = None
    language: str = "en"
    

@dataclass
class OCRResult:
    """Result from OCR processing."""
    document_id: str
    pages: list[OCRPage]
    full_text: str
    confidence: float  # 0.0 to 1.0
    processing_time_ms: int
    engine_used: str = "tesseract"
    language_detected: str = "en"


@dataclass
class OCRPage:
    """OCR result for a single page."""
    page_number: int
    text: str
    confidence: float
    words: list[OCRWord] = field(default_factory=list)
    tables: list[OCRTable] = field(default_factory=list)


@dataclass
class OCRWord:
    """A single word from OCR."""
    text: str
    confidence: float
    bounding_box: tuple[int, int, int, int]  # x, y, width, height


@dataclass
class OCRTable:
    """A table extracted from OCR."""
    rows: list[list[str]]
    bounding_box: tuple[int, int, int, int]
    confidence: float


@dataclass
class EmailContent:
    """Parsed email content."""
    id: str
    subject: str
    from_address: str
    from_name: str | None
    to_addresses: list[str]
    cc_addresses: list[str] = field(default_factory=list)
    body_text: str = ""
    body_html: str = ""
    received_date: datetime = field(default_factory=datetime.utcnow)
    attachments: list[EmailAttachment] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class EmailAttachment:
    """An email attachment."""
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    content_base64: str | None = None  # Base64 encoded content
    checksum: str | None = None


@dataclass
class IngestionJob:
    """A document ingestion job."""
    id: str
    status: IngestionStatus
    document_metadata: DocumentMetadata | None = None
    email_content: EmailContent | None = None
    ocr_result: OCRResult | None = None
    extracted_entities: list[ExtractedEntity] = field(default_factory=list)
    created_entity_ids: dict[str, str] = field(default_factory=dict)  # extraction_id -> system_id
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str | None = None
    review_notes: str | None = None
    
    @property
    def processing_duration_ms(self) -> int | None:
        """Get processing duration in milliseconds."""
        if self.processing_started_at and self.processing_completed_at:
            delta = self.processing_completed_at - self.processing_started_at
            return int(delta.total_seconds() * 1000)
        return None
    
    @property
    def needs_review(self) -> bool:
        """Check if job needs manual review."""
        return (
            self.status == IngestionStatus.REQUIRES_REVIEW or
            any(e.confidence in (ExtractionConfidence.LOW, ExtractionConfidence.UNCERTAIN) 
                for e in self.extracted_entities)
        )


@dataclass
class IngestionConfig:
    """Configuration for ingestion processing."""
    auto_create_opportunities: bool = True
    auto_create_customers: bool = False
    confidence_threshold_for_auto: float = 0.75
    require_review_below_confidence: float = 0.5
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50MB
    allowed_document_types: list[DocumentType] = field(
        default_factory=lambda: [DocumentType.EMAIL, DocumentType.PDF, DocumentType.IMAGE]
    )
    ocr_languages: list[str] = field(default_factory=lambda: ["en"])
    extract_tables: bool = True
    extract_line_items: bool = True


@dataclass
class IngestionStats:
    """Statistics for ingestion jobs."""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    pending_review_jobs: int = 0
    entities_created: int = 0
    avg_processing_time_ms: float = 0.0
    avg_confidence: float = 0.0


# =============================================================================
# Constants
# =============================================================================

REQUIRED_FIELDS_BY_ENTITY: dict[EntityType, set[FieldType]] = {
    EntityType.OPPORTUNITY: {FieldType.COMPANY_NAME},
    EntityType.CUSTOMER: {FieldType.COMPANY_NAME},
    EntityType.CONTACT: {FieldType.CONTACT_NAME, FieldType.CONTACT_EMAIL},
    EntityType.PRODUCT: {FieldType.PART_NUMBER},
}

MIME_TYPE_TO_DOCUMENT_TYPE: dict[str, DocumentType] = {
    "application/pdf": DocumentType.PDF,
    "image/png": DocumentType.IMAGE,
    "image/jpeg": DocumentType.IMAGE,
    "image/tiff": DocumentType.IMAGE,
    "image/bmp": DocumentType.IMAGE,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.EXCEL,
    "application/vnd.ms-excel": DocumentType.EXCEL,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.WORD,
    "application/msword": DocumentType.WORD,
    "text/plain": DocumentType.TEXT,
    "message/rfc822": DocumentType.EMAIL,
}

# Regex patterns for field extraction
PATTERNS: dict[FieldType, list[re.Pattern]] = {
    FieldType.CONTACT_EMAIL: [
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    ],
    FieldType.CONTACT_PHONE: [
        re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
        re.compile(r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'),
    ],
    FieldType.PART_NUMBER: [
        re.compile(r'\b(?:P/?N|Part\s*(?:No\.?|Number|#))[:.\s]*([A-Z0-9][-A-Z0-9_.]{2,30})\b', re.I),
        re.compile(r'\b([A-Z]{2,4}[-_]\d{4,}[-_]?[A-Z0-9]*)\b'),
    ],
    FieldType.DRAWING_NUMBER: [
        re.compile(r'\b(?:Dwg\.?|Drawing)[\s#:]*([A-Z0-9][-A-Z0-9_.]{2,30})\b', re.I),
    ],
    FieldType.RFQ_NUMBER: [
        re.compile(r'\b(?:RFQ|Request\s+for\s+Quote)[\s#:]*([A-Z0-9][-A-Z0-9_.]{2,20})\b', re.I),
        re.compile(r'\bRFQ[-_]?(\d{4,})\b', re.I),
    ],
    FieldType.QUANTITY: [
        re.compile(r'\b(?:Qty|Quantity|QTY)[:.\s]*(\d{1,9}(?:,\d{3})*)\b', re.I),
        re.compile(r'\b(\d{1,9}(?:,\d{3})*)\s*(?:pcs|pieces|units|ea)\b', re.I),
    ],
    FieldType.ANNUAL_VOLUME: [
        re.compile(r'\b(?:Annual|Yearly|EAU)[\s:]*(\d{1,9}(?:,\d{3})*)\b', re.I),
        re.compile(r'\b(\d{1,9}(?:,\d{3})*)\s*(?:/\s*year|annually|per\s+year)\b', re.I),
    ],
    FieldType.TARGET_PRICE: [
        re.compile(r'\b(?:Target|Price|Unit\s+Price)[\s:]*[$€£]?\s*(\d{1,6}(?:[.,]\d{2,4})?)\b', re.I),
        re.compile(r'[$€£]\s*(\d{1,6}(?:[.,]\d{2,4})?)\s*(?:per\s+unit|each|ea)\b', re.I),
    ],
    FieldType.CURRENCY: [
        re.compile(r'\b(USD|EUR|GBP|CAD|JPY|CNY)\b'),
        re.compile(r'([$€£¥])', re.I),
    ],
    FieldType.DUE_DATE: [
        re.compile(r'\b(?:Due|Deadline|Response\s+by|Quote\s+by)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', re.I),
        re.compile(r'\b(?:Due|Deadline)[\s:]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})\b', re.I),
    ],
    FieldType.DELIVERY_DATE: [
        re.compile(r'\b(?:Delivery|Ship|Need\s+by)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', re.I),
        re.compile(r'\b(?:Delivery|Ship\s+date)[\s:]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})\b', re.I),
    ],
    FieldType.MATERIAL_SPEC: [
        re.compile(r'\b(?:Material|Alloy|Grade)[\s:]*([A-Z0-9][-A-Z0-9\s.]{2,30})\b', re.I),
        re.compile(r'\b(ASTM\s+[A-Z]\d+[-\d]*|SAE\s+\d+|AISI\s+\d+)\b', re.I),
        re.compile(r'\b(6061[-\s]?T6|7075[-\s]?T6|304\s*SS|316\s*SS)\b', re.I),
    ],
    FieldType.TOLERANCE: [
        re.compile(r'[±+/-]\s*(\d+(?:\.\d+)?)\s*(?:mm|in|thou|")\b', re.I),
        re.compile(r'\b(?:Tolerance|Tol\.?)[\s:]*([±+/-]?\s*\d+(?:\.\d+)?)\b', re.I),
    ],
    FieldType.INCOTERMS: [
        re.compile(r'\b(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\b'),
    ],
}


# =============================================================================
# Utility Functions
# =============================================================================

def detect_document_type(filename: str, mime_type: str | None = None) -> DocumentType:
    """Detect document type from filename and/or MIME type."""
    if mime_type and mime_type in MIME_TYPE_TO_DOCUMENT_TYPE:
        return MIME_TYPE_TO_DOCUMENT_TYPE[mime_type]
    
    # Fallback to extension
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    extension_map = {
        'pdf': DocumentType.PDF,
        'png': DocumentType.IMAGE,
        'jpg': DocumentType.IMAGE,
        'jpeg': DocumentType.IMAGE,
        'tiff': DocumentType.IMAGE,
        'tif': DocumentType.IMAGE,
        'bmp': DocumentType.IMAGE,
        'xlsx': DocumentType.EXCEL,
        'xls': DocumentType.EXCEL,
        'docx': DocumentType.WORD,
        'doc': DocumentType.WORD,
        'txt': DocumentType.TEXT,
        'eml': DocumentType.EMAIL,
    }
    return extension_map.get(ext, DocumentType.UNKNOWN)


def calculate_checksum(content: bytes) -> str:
    """Calculate SHA-256 checksum of content."""
    return hashlib.sha256(content).hexdigest()


def normalize_text(text: str) -> str:
    """Normalize text for extraction."""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text.strip()


def parse_date(date_str: str) -> datetime | None:
    """Parse a date string in various formats."""
    formats = [
        '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d',
        '%m-%d-%Y', '%d-%m-%Y',
        '%B %d, %Y', '%b %d, %Y',
        '%B %d %Y', '%b %d %Y',
        '%m/%d/%y', '%d/%m/%y',
    ]
    date_str = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_number(num_str: str) -> float | None:
    """Parse a number string, handling commas and currency symbols."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[$€£¥,\s]', '', num_str)
    try:
        return float(cleaned)
    except ValueError:
        return None


def confidence_to_enum(confidence: float) -> ExtractionConfidence:
    """Convert numeric confidence to enum."""
    if confidence >= 0.85:
        return ExtractionConfidence.HIGH
    elif confidence >= 0.65:
        return ExtractionConfidence.MEDIUM
    elif confidence >= 0.4:
        return ExtractionConfidence.LOW
    else:
        return ExtractionConfidence.UNCERTAIN


def extract_company_from_email(email_address: str) -> str | None:
    """Extract company name from email domain."""
    match = re.match(r'.*@([^.]+)\.(com|org|net|co|io|ai)$', email_address, re.I)
    if match:
        company = match.group(1)
        # Title case and expand common abbreviations
        company = company.replace('-', ' ').replace('_', ' ')
        return company.title()
    return None


def extract_name_from_email(from_string: str) -> tuple[str | None, str | None]:
    """Extract name and email from 'Name <email@example.com>' format."""
    match = re.match(r'^([^<]+)<([^>]+)>$', from_string.strip())
    if match:
        name = match.group(1).strip().strip('"\'')
        email = match.group(2).strip()
        return name if name else None, email
    # Just an email address
    if '@' in from_string:
        return None, from_string.strip()
    return from_string.strip() if from_string.strip() else None, None


# =============================================================================
# PDF/Text Extraction (with graceful fallback)
# =============================================================================

def extract_text_from_document(content: bytes, document_type: DocumentType) -> OCRResult:
    """
    Extract text from document using available libraries.
    
    Tries in order:
    1. PyMuPDF (fitz) for PDFs
    2. pdfplumber for PDFs
    3. Plain text decoding
    4. Graceful fallback with minimal extraction
    
    OCR for images requires pytesseract/PIL which are optional dependencies.
    """
    import time
    start_time = time.time()
    
    doc_id = str(uuid.uuid4())
    extracted_text = ""
    engine_used = "none"
    confidence = 0.0
    pages_data: list[OCRPage] = []
    
    try:
        if document_type == DocumentType.PDF:
            extracted_text, pages_data, engine_used = _extract_pdf_text(content)
            confidence = 0.95  # High confidence for text-based PDFs
        elif document_type == DocumentType.IMAGE:
            extracted_text, confidence, engine_used = _extract_image_text(content)
            pages_data = [OCRPage(page_number=1, text=extracted_text, confidence=confidence)]
        elif document_type == DocumentType.TEXT:
            extracted_text = content.decode('utf-8', errors='replace')
            engine_used = "utf8_decode"
            confidence = 1.0
            pages_data = [OCRPage(page_number=1, text=extracted_text, confidence=1.0)]
        else:
            # Try as text first
            try:
                extracted_text = content.decode('utf-8', errors='strict')
                engine_used = "utf8_decode"
                confidence = 0.9
            except UnicodeDecodeError:
                extracted_text = content.decode('utf-8', errors='replace')
                engine_used = "utf8_decode_lossy"
                confidence = 0.6
            pages_data = [OCRPage(page_number=1, text=extracted_text, confidence=confidence)]
    
    except Exception as e:
        # Fallback: minimal extraction
        extracted_text = f"[Error extracting text: {str(e)}]"
        engine_used = "fallback"
        confidence = 0.1
        pages_data = [OCRPage(page_number=1, text=extracted_text, confidence=0.1)]
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return OCRResult(
        document_id=doc_id,
        pages=pages_data,
        full_text=extracted_text,
        confidence=confidence,
        processing_time_ms=processing_time,
        engine_used=engine_used,
        language_detected="en",
    )


def _extract_pdf_text(content: bytes) -> tuple[str, list[OCRPage], str]:
    """Extract text from PDF using available libraries."""
    
    # Try PyMuPDF (fitz) first
    try:
        import fitz  # PyMuPDF
        
        pdf_doc = fitz.open(stream=content, filetype="pdf")
        pages: list[OCRPage] = []
        full_text_parts: list[str] = []
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            page_text = page.get_text()
            pages.append(OCRPage(
                page_number=page_num + 1,
                text=page_text,
                confidence=0.95,
                words=[],
                tables=[],
            ))
            full_text_parts.append(page_text)
        
        pdf_doc.close()
        return "\n\n".join(full_text_parts), pages, "pymupdf"
    
    except ImportError:
        pass  # PyMuPDF not installed
    except Exception:
        pass  # PyMuPDF failed
    
    # Try pdfplumber
    try:
        import pdfplumber
        
        pdf_file = BytesIO(content)
        pages: list[OCRPage] = []
        full_text_parts: list[str] = []
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                pages.append(OCRPage(
                    page_number=page_num + 1,
                    text=page_text,
                    confidence=0.92,
                    words=[],
                    tables=[],
                ))
                full_text_parts.append(page_text)
        
        return "\n\n".join(full_text_parts), pages, "pdfplumber"
    
    except ImportError:
        pass  # pdfplumber not installed
    except Exception:
        pass  # pdfplumber failed
    
    # Fallback: attempt basic text extraction
    try:
        text = content.decode('latin-1', errors='replace')
        # Very naive extraction of readable text
        import string
        readable = ''.join(c for c in text if c in string.printable)
        pages = [OCRPage(page_number=1, text=readable, confidence=0.3)]
        return readable, pages, "fallback_text"
    except Exception:
        return "[Unable to extract PDF text - install PyMuPDF or pdfplumber]", [], "none"


def _extract_image_text(content: bytes) -> tuple[str, float, str]:
    """Extract text from image using OCR (requires pytesseract)."""
    
    try:
        from PIL import Image
        import pytesseract
        
        image = Image.open(BytesIO(content))
        text = pytesseract.image_to_string(image)
        return text, 0.85, "tesseract"
    
    except ImportError:
        # pytesseract or PIL not installed
        return "[OCR not available - install pytesseract and Pillow for image text extraction]", 0.1, "none"
    except Exception as e:
        return f"[OCR error: {str(e)}]", 0.1, "error"


# =============================================================================
# Field Extraction
# =============================================================================

class FieldExtractor:
    """Extracts structured fields from text."""
    
    def __init__(self, config: IngestionConfig | None = None):
        self.config = config or IngestionConfig()
        self._custom_extractors: dict[FieldType, Callable[[str], list[ExtractedField]]] = {}
    
    def register_custom_extractor(
        self,
        field_type: FieldType,
        extractor: Callable[[str], list[ExtractedField]]
    ) -> None:
        """Register a custom extractor for a field type."""
        self._custom_extractors[field_type] = extractor
    
    def extract_all_fields(self, text: str) -> dict[FieldType, list[ExtractedField]]:
        """Extract all supported fields from text."""
        results: dict[FieldType, list[ExtractedField]] = {}
        normalized = normalize_text(text)
        
        for field_type in FieldType:
            fields = self.extract_field(field_type, normalized)
            if fields:
                results[field_type] = fields
        
        return results
    
    def extract_field(self, field_type: FieldType, text: str) -> list[ExtractedField]:
        """Extract a specific field type from text."""
        # Check for custom extractor first
        if field_type in self._custom_extractors:
            return self._custom_extractors[field_type](text)
        
        # Use pattern-based extraction
        patterns = PATTERNS.get(field_type, [])
        results: list[ExtractedField] = []
        
        for pattern in patterns:
            for match in pattern.finditer(text):
                raw_text = match.group(0)
                value = match.group(1) if match.lastindex else match.group(0)
                
                # Validate and parse the value
                parsed_value, confidence, errors = self._validate_and_parse(
                    field_type, value, raw_text
                )
                
                results.append(ExtractedField(
                    field_type=field_type,
                    value=parsed_value,
                    raw_text=raw_text,
                    confidence=confidence,
                    source_location=f"char {match.start()}-{match.end()}",
                    validation_errors=errors,
                ))
        
        # Deduplicate by value
        seen_values: set = set()
        unique_results: list[ExtractedField] = []
        for field in results:
            value_key = str(field.value).lower() if field.value else ''
            if value_key not in seen_values:
                seen_values.add(value_key)
                unique_results.append(field)
        
        return unique_results
    
    def _validate_and_parse(
        self,
        field_type: FieldType,
        value: str,
        raw_text: str
    ) -> tuple[Any, ExtractionConfidence, list[str]]:
        """Validate and parse extracted value."""
        errors: list[str] = []
        confidence = ExtractionConfidence.MEDIUM
        parsed = value
        
        # Type-specific validation
        if field_type == FieldType.CONTACT_EMAIL:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
                errors.append("Invalid email format")
                confidence = ExtractionConfidence.LOW
        
        elif field_type == FieldType.CONTACT_PHONE:
            digits = re.sub(r'\D', '', value)
            if len(digits) < 7 or len(digits) > 15:
                errors.append("Phone number has invalid digit count")
                confidence = ExtractionConfidence.LOW
        
        elif field_type in (FieldType.QUANTITY, FieldType.ANNUAL_VOLUME):
            parsed_num = parse_number(value)
            if parsed_num is None:
                errors.append("Invalid number format")
                confidence = ExtractionConfidence.LOW
            elif parsed_num <= 0:
                errors.append("Quantity must be positive")
                confidence = ExtractionConfidence.LOW
            else:
                parsed = int(parsed_num)
                confidence = ExtractionConfidence.HIGH
        
        elif field_type == FieldType.TARGET_PRICE:
            parsed_num = parse_number(value)
            if parsed_num is None:
                errors.append("Invalid price format")
                confidence = ExtractionConfidence.LOW
            elif parsed_num < 0:
                errors.append("Price cannot be negative")
                confidence = ExtractionConfidence.LOW
            else:
                parsed = parsed_num
                confidence = ExtractionConfidence.HIGH
        
        elif field_type in (FieldType.DUE_DATE, FieldType.DELIVERY_DATE):
            parsed_date = parse_date(value)
            if parsed_date is None:
                errors.append("Could not parse date")
                confidence = ExtractionConfidence.LOW
            else:
                parsed = parsed_date
                if parsed_date < datetime.now():
                    errors.append("Date is in the past")
                    confidence = ExtractionConfidence.LOW
                else:
                    confidence = ExtractionConfidence.HIGH
        
        return parsed, confidence, errors
    
    def extract_from_email(self, email: EmailContent) -> dict[FieldType, list[ExtractedField]]:
        """Extract fields from email content."""
        results: dict[FieldType, list[ExtractedField]] = {}
        
        # Extract from headers
        if email.from_address:
            results[FieldType.CONTACT_EMAIL] = [
                ExtractedField(
                    field_type=FieldType.CONTACT_EMAIL,
                    value=email.from_address,
                    raw_text=email.from_address,
                    confidence=ExtractionConfidence.HIGH,
                    source_location="email_from",
                )
            ]
            
            # Try to get company from email domain
            company = extract_company_from_email(email.from_address)
            if company:
                results[FieldType.COMPANY_NAME] = [
                    ExtractedField(
                        field_type=FieldType.COMPANY_NAME,
                        value=company,
                        raw_text=email.from_address,
                        confidence=ExtractionConfidence.MEDIUM,
                        source_location="email_domain",
                    )
                ]
        
        if email.from_name:
            results[FieldType.CONTACT_NAME] = [
                ExtractedField(
                    field_type=FieldType.CONTACT_NAME,
                    value=email.from_name,
                    raw_text=email.from_name,
                    confidence=ExtractionConfidence.HIGH,
                    source_location="email_from_name",
                )
            ]
        
        # Extract from subject
        subject_fields = self.extract_all_fields(email.subject)
        for field_type, fields in subject_fields.items():
            for f in fields:
                f.source_location = f"subject: {f.source_location}"
            if field_type in results:
                results[field_type].extend(fields)
            else:
                results[field_type] = fields
        
        # Extract from body
        body_text = email.body_text or email.body_html
        if body_text:
            body_fields = self.extract_all_fields(body_text)
            for field_type, fields in body_fields.items():
                for f in fields:
                    f.source_location = f"body: {f.source_location}"
                if field_type in results:
                    results[field_type].extend(fields)
                else:
                    results[field_type] = fields
        
        return results


# =============================================================================
# Entity Builder
# =============================================================================

class EntityBuilder:
    """Builds entities from extracted fields."""
    
    def __init__(self, config: IngestionConfig | None = None):
        self.config = config or IngestionConfig()
    
    def build_opportunity(
        self,
        fields: dict[FieldType, list[ExtractedField]],
        source_document_id: str | None = None
    ) -> ExtractedEntity:
        """Build an opportunity entity from extracted fields."""
        entity = ExtractedEntity(
            id=str(uuid.uuid4()),
            entity_type=EntityType.OPPORTUNITY,
            source_document_id=source_document_id,
        )
        
        # Map fields to opportunity
        field_mapping: list[tuple[FieldType, ...]] = [
            (FieldType.COMPANY_NAME,),
            (FieldType.PROJECT_NAME,),
            (FieldType.RFQ_NUMBER,),
            (FieldType.DUE_DATE,),
            (FieldType.ANNUAL_VOLUME,),
            (FieldType.CURRENCY,),
        ]
        
        for field_types in field_mapping:
            for ft in field_types:
                if ft in fields and fields[ft]:
                    # Take the highest confidence field
                    best_field = max(
                        fields[ft],
                        key=lambda f: (
                            1.0 if f.confidence == ExtractionConfidence.HIGH else
                            0.7 if f.confidence == ExtractionConfidence.MEDIUM else
                            0.4 if f.confidence == ExtractionConfidence.LOW else 0.1
                        )
                    )
                    entity.fields[ft] = best_field
                    break
        
        # Calculate overall confidence
        if entity.fields:
            confidences = [
                1.0 if f.confidence == ExtractionConfidence.HIGH else
                0.7 if f.confidence == ExtractionConfidence.MEDIUM else
                0.4 if f.confidence == ExtractionConfidence.LOW else 0.1
                for f in entity.fields.values()
            ]
            avg_confidence = sum(confidences) / len(confidences)
            entity.confidence = confidence_to_enum(avg_confidence)
        else:
            entity.confidence = ExtractionConfidence.UNCERTAIN
        
        return entity
    
    def build_contact(
        self,
        fields: dict[FieldType, list[ExtractedField]],
        source_document_id: str | None = None
    ) -> ExtractedEntity | None:
        """Build a contact entity from extracted fields."""
        # Need at least name or email
        has_name = FieldType.CONTACT_NAME in fields and fields[FieldType.CONTACT_NAME]
        has_email = FieldType.CONTACT_EMAIL in fields and fields[FieldType.CONTACT_EMAIL]
        
        if not (has_name or has_email):
            return None
        
        entity = ExtractedEntity(
            id=str(uuid.uuid4()),
            entity_type=EntityType.CONTACT,
            source_document_id=source_document_id,
        )
        
        for ft in [FieldType.CONTACT_NAME, FieldType.CONTACT_EMAIL, FieldType.CONTACT_PHONE]:
            if ft in fields and fields[ft]:
                entity.fields[ft] = fields[ft][0]
        
        # Confidence based on how many fields we have
        field_count = len(entity.fields)
        if field_count >= 3:
            entity.confidence = ExtractionConfidence.HIGH
        elif field_count >= 2:
            entity.confidence = ExtractionConfidence.MEDIUM
        else:
            entity.confidence = ExtractionConfidence.LOW
        
        return entity
    
    def build_line_items(
        self,
        fields: dict[FieldType, list[ExtractedField]],
        source_document_id: str | None = None
    ) -> list[ExtractedEntity]:
        """Build product/line item entities from extracted fields."""
        entities: list[ExtractedEntity] = []
        
        # Each part number becomes a line item
        part_numbers = fields.get(FieldType.PART_NUMBER, [])
        quantities = fields.get(FieldType.QUANTITY, [])
        
        for i, pn_field in enumerate(part_numbers):
            entity = ExtractedEntity(
                id=str(uuid.uuid4()),
                entity_type=EntityType.PRODUCT,
                source_document_id=source_document_id,
            )
            entity.fields[FieldType.PART_NUMBER] = pn_field
            
            # Try to match with quantity by position
            if i < len(quantities):
                entity.fields[FieldType.QUANTITY] = quantities[i]
            
            # Add other relevant fields
            for ft in [
                FieldType.PART_DESCRIPTION,
                FieldType.MATERIAL_SPEC,
                FieldType.DRAWING_NUMBER,
                FieldType.TOLERANCE,
            ]:
                if ft in fields and fields[ft]:
                    entity.fields[ft] = fields[ft][0]
            
            entity.confidence = ExtractionConfidence.MEDIUM
            entities.append(entity)
        
        return entities


# =============================================================================
# Smart Ingestion Service
# =============================================================================

class SmartIngestionService:
    """
    Main service for smart document ingestion.
    
    Handles:
    - Document upload and processing
    - OCR for scanned documents
    - AI-powered field extraction
    - Entity creation and linking
    - Review workflow
    """
    
    def __init__(
        self,
        db: AsyncSession | None = None,
        config: IngestionConfig | None = None
    ):
        self.db = db
        self.config = config or IngestionConfig()
        self.extractor = FieldExtractor(self.config)
        self.entity_builder = EntityBuilder(self.config)
        
        # In-memory storage for jobs (would be database table in production)
        self._jobs: dict[str, IngestionJob] = {}
        self._documents: dict[str, tuple[DocumentMetadata, bytes]] = {}
        
        # Callbacks for entity creation (used when db session not provided)
        self._entity_creators: dict[EntityType, Callable[[ExtractedEntity], str | None]] = {}
        
        # Customer/contact lookup caches
        self._known_customers: dict[str, str] = {}  # domain -> customer_id
        self._known_contacts: dict[str, str] = {}  # email -> contact_id
    
    def register_entity_creator(
        self,
        entity_type: EntityType,
        creator: Callable[[ExtractedEntity], str | None]
    ) -> None:
        """Register a callback to create entities in the system."""
        self._entity_creators[entity_type] = creator
    
    def register_known_customer(self, email_domain: str, customer_id: str) -> None:
        """Register a known customer for email domain matching."""
        self._known_customers[email_domain.lower()] = customer_id
    
    def register_known_contact(self, email: str, contact_id: str) -> None:
        """Register a known contact for email matching."""
        self._known_contacts[email.lower()] = contact_id
    
    async def load_known_customers(self) -> None:
        """Load known customers from database for domain matching."""
        if not self.db:
            return
        
        try:
            from sqlalchemy import select
            from sensei.models.account import Account, Contact
            
            # Load accounts with email domains
            result = await self.db.execute(select(Account))
            accounts = result.scalars().all()
            
            for account in accounts:
                if account.email:
                    domain = account.email.split('@')[-1].lower()
                    self._known_customers[domain] = str(account.id)
            
            # Load contacts
            result = await self.db.execute(select(Contact))
            contacts = result.scalars().all()
            
            for contact in contacts:
                if contact.email:
                    self._known_contacts[contact.email.lower()] = str(contact.id)
        
        except ImportError:
            pass  # Models not available
    
    # =========================================================================
    # Job Management
    # =========================================================================
    
    def create_job(self, created_by: str | None = None) -> IngestionJob:
        """Create a new ingestion job."""
        job = IngestionJob(
            id=str(uuid.uuid4()),
            status=IngestionStatus.PENDING,
            created_by=created_by,
        )
        self._jobs[job.id] = job
        return job
    
    def get_job(self, job_id: str) -> IngestionJob | None:
        """Get an ingestion job by ID."""
        return self._jobs.get(job_id)
    
    def list_jobs(
        self,
        status: IngestionStatus | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[IngestionJob]:
        """List ingestion jobs with optional filtering."""
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[offset:offset + limit]
    
    def get_jobs_requiring_review(self) -> list[IngestionJob]:
        """Get all jobs that require manual review."""
        return [
            j for j in self._jobs.values()
            if j.status == IngestionStatus.REQUIRES_REVIEW
        ]
    
    def get_stats(self) -> IngestionStats:
        """Get ingestion statistics."""
        jobs = list(self._jobs.values())
        
        completed = [j for j in jobs if j.status == IngestionStatus.COMPLETED]
        failed = [j for j in jobs if j.status == IngestionStatus.FAILED]
        pending_review = [j for j in jobs if j.status == IngestionStatus.REQUIRES_REVIEW]
        
        processing_times = [
            j.processing_duration_ms for j in completed
            if j.processing_duration_ms is not None
        ]
        
        entities_created = sum(len(j.created_entity_ids) for j in completed)
        
        # Calculate average confidence
        all_entities = [e for j in completed for e in j.extracted_entities]
        if all_entities:
            confidence_values = [
                1.0 if e.confidence == ExtractionConfidence.HIGH else
                0.7 if e.confidence == ExtractionConfidence.MEDIUM else
                0.4 if e.confidence == ExtractionConfidence.LOW else 0.1
                for e in all_entities
            ]
            avg_confidence = sum(confidence_values) / len(confidence_values)
        else:
            avg_confidence = 0.0
        
        return IngestionStats(
            total_jobs=len(jobs),
            completed_jobs=len(completed),
            failed_jobs=len(failed),
            pending_review_jobs=len(pending_review),
            entities_created=entities_created,
            avg_processing_time_ms=sum(processing_times) / len(processing_times) if processing_times else 0,
            avg_confidence=avg_confidence,
        )
    
    # =========================================================================
    # Document Ingestion
    # =========================================================================
    
    def ingest_document(
        self,
        filename: str,
        content: bytes,
        mime_type: str | None = None,
        job_id: str | None = None
    ) -> IngestionJob:
        """
        Ingest a document and extract data.
        
        Args:
            filename: Original filename
            content: Document content as bytes
            mime_type: MIME type (optional, will be detected)
            job_id: Existing job ID to use (optional)
        
        Returns:
            IngestionJob with extraction results
        """
        # Get or create job
        if job_id:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
        else:
            job = self.create_job()
        
        job.status = IngestionStatus.PROCESSING
        job.processing_started_at = datetime.utcnow()
        
        try:
            # Detect document type
            detected_mime = mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
            doc_type = detect_document_type(filename, detected_mime)
            
            # Validate
            if doc_type not in self.config.allowed_document_types:
                raise ValueError(f"Document type not allowed: {doc_type}")
            
            if len(content) > self.config.max_file_size_bytes:
                raise ValueError(f"Document too large: {len(content)} bytes")
            
            # Create metadata
            metadata = DocumentMetadata(
                id=str(uuid.uuid4()),
                filename=filename,
                document_type=doc_type,
                mime_type=detected_mime,
                size_bytes=len(content),
                checksum=calculate_checksum(content),
            )
            job.document_metadata = metadata
            
            # Store document
            self._documents[metadata.id] = (metadata, content)
            
            # OCR if needed
            job.status = IngestionStatus.EXTRACTING
            if doc_type in (DocumentType.PDF, DocumentType.IMAGE):
                ocr_result = extract_text_from_document(content, doc_type)
                job.ocr_result = ocr_result
                text_to_parse = ocr_result.full_text
            else:
                text_to_parse = content.decode('utf-8', errors='ignore')
            
            # Extract fields
            fields = self.extractor.extract_all_fields(text_to_parse)
            
            # Build entities
            job.status = IngestionStatus.VALIDATING
            self._build_entities(job, fields)
            
            # Determine final status
            self._finalize_job(job)
            
        except Exception as e:
            job.status = IngestionStatus.FAILED
            job.errors.append(str(e))
        finally:
            job.processing_completed_at = datetime.utcnow()
        
        return job
    
    def ingest_email(
        self,
        email: EmailContent,
        job_id: str | None = None
    ) -> IngestionJob:
        """
        Ingest an email and extract RFQ data.
        
        Args:
            email: Parsed email content
            job_id: Existing job ID to use (optional)
        
        Returns:
            IngestionJob with extraction results
        """
        # Get or create job
        if job_id:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")
        else:
            job = self.create_job()
        
        job.status = IngestionStatus.PROCESSING
        job.processing_started_at = datetime.utcnow()
        job.email_content = email
        
        try:
            # Extract fields from email
            job.status = IngestionStatus.EXTRACTING
            fields = self.extractor.extract_from_email(email)
            
            # Check for known customer
            if email.from_address:
                domain = email.from_address.split('@')[-1].lower()
                if domain in self._known_customers:
                    job.warnings.append(
                        f"Matched known customer from domain: {domain}"
                    )
            
            # Check for known contact
            if email.from_address and email.from_address.lower() in self._known_contacts:
                job.warnings.append(
                    f"Matched known contact: {email.from_address}"
                )
            
            # Process attachments
            for attachment in email.attachments:
                if attachment.content_base64:
                    content = base64.b64decode(attachment.content_base64)
                    doc_type = detect_document_type(attachment.filename, attachment.mime_type)
                    
                    if doc_type in (DocumentType.PDF, DocumentType.IMAGE):
                        # OCR attachment
                        ocr_result = extract_text_from_document(content, doc_type)
                        attachment_fields = self.extractor.extract_all_fields(ocr_result.full_text)
                        
                        # Merge with email fields
                        for ft, field_list in attachment_fields.items():
                            for f in field_list:
                                f.source_location = f"attachment:{attachment.filename}:{f.source_location}"
                            if ft in fields:
                                fields[ft].extend(field_list)
                            else:
                                fields[ft] = field_list
            
            # Build entities
            job.status = IngestionStatus.VALIDATING
            self._build_entities(job, fields)
            
            # Determine final status
            self._finalize_job(job)
            
        except Exception as e:
            job.status = IngestionStatus.FAILED
            job.errors.append(str(e))
        finally:
            job.processing_completed_at = datetime.utcnow()
        
        return job
    
    def _build_entities(
        self,
        job: IngestionJob,
        fields: dict[FieldType, list[ExtractedField]]
    ) -> None:
        """Build extracted entities from fields."""
        source_id = job.document_metadata.id if job.document_metadata else None
        
        # Build opportunity
        opportunity = self.entity_builder.build_opportunity(fields, source_id)
        job.extracted_entities.append(opportunity)
        
        # Build contact
        contact = self.entity_builder.build_contact(fields, source_id)
        if contact:
            job.extracted_entities.append(contact)
        
        # Build line items
        if self.config.extract_line_items:
            line_items = self.entity_builder.build_line_items(fields, source_id)
            job.extracted_entities.extend(line_items)
    
    def _finalize_job(self, job: IngestionJob) -> None:
        """Finalize job status based on extraction results."""
        # Check confidence levels
        low_confidence = any(
            e.confidence in (ExtractionConfidence.LOW, ExtractionConfidence.UNCERTAIN)
            for e in job.extracted_entities
        )
        
        # Check for validation errors
        has_errors = any(
            e.validation_errors
            for e in job.extracted_entities
        )
        
        # Check required fields
        missing_required = not all(
            e.is_complete for e in job.extracted_entities
        )
        
        if has_errors or (low_confidence and self.config.require_review_below_confidence > 0):
            job.status = IngestionStatus.REQUIRES_REVIEW
        elif missing_required:
            job.status = IngestionStatus.REQUIRES_REVIEW
            job.warnings.append("Some entities are missing required fields")
        else:
            job.status = IngestionStatus.COMPLETED
            
            # Auto-create entities if configured
            if self.config.auto_create_opportunities:
                self._auto_create_entities(job)
    
    def _auto_create_entities(self, job: IngestionJob) -> None:
        """Automatically create entities in the system."""
        for entity in job.extracted_entities:
            if entity.entity_type not in self._entity_creators:
                continue
            
            # Check confidence threshold
            confidence_value = (
                1.0 if entity.confidence == ExtractionConfidence.HIGH else
                0.7 if entity.confidence == ExtractionConfidence.MEDIUM else
                0.4 if entity.confidence == ExtractionConfidence.LOW else 0.1
            )
            
            if confidence_value < self.config.confidence_threshold_for_auto:
                continue
            
            try:
                creator = self._entity_creators[entity.entity_type]
                created_id = creator(entity)
                if created_id:
                    entity.created_entity_id = created_id
                    job.created_entity_ids[entity.id] = created_id
            except Exception as e:
                job.warnings.append(
                    f"Failed to create {entity.entity_type.value}: {str(e)}"
                )
    
    # =========================================================================
    # Review Workflow
    # =========================================================================
    
    def approve_and_create(
        self,
        job_id: str,
        entity_overrides: dict[str, dict[FieldType, Any]] | None = None,
        reviewer_notes: str | None = None
    ) -> IngestionJob:
        """
        Approve a job and create entities.
        
        Args:
            job_id: Job to approve
            entity_overrides: Optional field value overrides by entity ID
            reviewer_notes: Optional review notes
        
        Returns:
            Updated IngestionJob
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        if job.status not in (IngestionStatus.REQUIRES_REVIEW, IngestionStatus.COMPLETED):
            raise ValueError(f"Job cannot be approved in status: {job.status}")
        
        # Apply overrides
        if entity_overrides:
            for entity in job.extracted_entities:
                if entity.id in entity_overrides:
                    for field_type, value in entity_overrides[entity.id].items():
                        if field_type in entity.fields:
                            entity.fields[field_type].value = value
                            entity.fields[field_type].confidence = ExtractionConfidence.HIGH
                            entity.fields[field_type].validation_errors = []
                        else:
                            entity.fields[field_type] = ExtractedField(
                                field_type=field_type,
                                value=value,
                                raw_text=str(value),
                                confidence=ExtractionConfidence.HIGH,
                            )
        
        job.review_notes = reviewer_notes
        
        # Create entities
        for entity in job.extracted_entities:
            if entity.created_entity_id:
                continue  # Already created
            
            if entity.entity_type not in self._entity_creators:
                continue
            
            try:
                creator = self._entity_creators[entity.entity_type]
                created_id = creator(entity)
                if created_id:
                    entity.created_entity_id = created_id
                    job.created_entity_ids[entity.id] = created_id
            except Exception as e:
                job.errors.append(
                    f"Failed to create {entity.entity_type.value}: {str(e)}"
                )
        
        job.status = IngestionStatus.COMPLETED
        return job
    
    def reject_job(
        self,
        job_id: str,
        reason: str
    ) -> IngestionJob:
        """
        Reject an ingestion job.
        
        Args:
            job_id: Job to reject
            reason: Reason for rejection
        
        Returns:
            Updated IngestionJob
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        job.status = IngestionStatus.FAILED
        job.errors.append(f"Rejected: {reason}")
        job.review_notes = reason
        
        return job
    
    def update_entity_field(
        self,
        job_id: str,
        entity_id: str,
        field_type: FieldType,
        value: Any
    ) -> ExtractedEntity | None:
        """
        Update a field value on an extracted entity.
        
        Args:
            job_id: Job ID
            entity_id: Entity ID to update
            field_type: Field to update
            value: New value
        
        Returns:
            Updated entity or None if not found
        """
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        for entity in job.extracted_entities:
            if entity.id == entity_id:
                if field_type in entity.fields:
                    entity.fields[field_type].value = value
                    entity.fields[field_type].confidence = ExtractionConfidence.HIGH
                    entity.fields[field_type].validation_errors = []
                else:
                    entity.fields[field_type] = ExtractedField(
                        field_type=field_type,
                        value=value,
                        raw_text=str(value),
                        confidence=ExtractionConfidence.HIGH,
                        source_location="manual_entry",
                    )
                return entity
        
        return None
    
    # =========================================================================
    # Document Access
    # =========================================================================
    
    def get_document(self, document_id: str) -> tuple[DocumentMetadata, bytes] | None:
        """Get a stored document by ID."""
        return self._documents.get(document_id)
    
    def get_document_text(self, job_id: str) -> str | None:
        """Get extracted text from a job's document."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        
        if job.ocr_result:
            return job.ocr_result.full_text
        
        if job.document_metadata:
            doc = self._documents.get(job.document_metadata.id)
            if doc:
                _, content = doc
                return content.decode('utf-8', errors='ignore')
        
        return None
    
    async def create_rfq_from_entity(
        self,
        entity: ExtractedEntity,
        created_by_id: str | None = None
    ) -> str | None:
        """
        Create an RFQ record from extracted entity.
        
        Args:
            entity: Extracted entity data
            created_by_id: User ID creating the RFQ
        
        Returns:
            Created RFQ ID or None if creation failed
        """
        if not self.db:
            return None
        
        try:
            from sqlalchemy import select, func
            from sensei.models.rfq import RFQ, RFQStatus, RFQPriority, RFQSource
            from sensei.models.account import Account
            from uuid import UUID
            
            # Generate RFQ number
            year = datetime.now().year
            prefix = f"RFQ-{year}-"
            
            result = await self.db.execute(
                select(func.max(RFQ.rfq_number))
                .where(RFQ.rfq_number.like(f"{prefix}%"))
            )
            last_number = result.scalar()
            
            if last_number:
                seq = int(last_number.split("-")[-1]) + 1
            else:
                seq = 1
            
            rfq_number = f"{prefix}{seq:05d}"
            
            # Extract field values
            company_name = entity.get_field_value(FieldType.COMPANY_NAME)
            customer_rfq_number = entity.get_field_value(FieldType.RFQ_NUMBER)
            part_number = entity.get_field_value(FieldType.PART_NUMBER)
            part_description = entity.get_field_value(FieldType.PART_DESCRIPTION)
            quantity = entity.get_field_value(FieldType.QUANTITY)
            annual_volume = entity.get_field_value(FieldType.ANNUAL_VOLUME)
            target_price = entity.get_field_value(FieldType.TARGET_PRICE)
            due_date = entity.get_field_value(FieldType.DUE_DATE)
            delivery_date = entity.get_field_value(FieldType.DELIVERY_DATE)
            material_spec = entity.get_field_value(FieldType.MATERIAL_SPEC)
            drawing_number = entity.get_field_value(FieldType.DRAWING_NUMBER)
            currency = entity.get_field_value(FieldType.CURRENCY, "MAD")
            
            # Find or create account
            account_id = None
            if company_name:
                result = await self.db.execute(
                    select(Account).where(Account.name.ilike(f"%{company_name}%")).limit(1)
                )
                account = result.scalar_one_or_none()
                if account:
                    account_id = account.id
                else:
                    # Create new account
                    new_account = Account(
                        name=company_name,
                        account_type="customer",
                        created_by_id=UUID(created_by_id) if created_by_id else None,
                    )
                    self.db.add(new_account)
                    await self.db.flush()
                    account_id = new_account.id
            
            if not account_id:
                # Can't create RFQ without account
                return None
            
            # Create RFQ
            rfq = RFQ(
                rfq_number=rfq_number,
                customer_rfq_number=customer_rfq_number,
                title=f"RFQ from {company_name}" if company_name else "Imported RFQ",
                account_id=account_id,
                status=RFQStatus.RECEIVED.value,
                priority=RFQPriority.MEDIUM.value,
                source=RFQSource.EMAIL.value,
                received_date=datetime.utcnow(),
                due_date=due_date,
                part_number=part_number,
                part_name=part_description,
                drawing_number=drawing_number,
                quantity=quantity,
                annual_volume=annual_volume,
                target_price=target_price,
                currency=currency,
                material_spec=material_spec,
                created_by_id=UUID(created_by_id) if created_by_id else None,
            )
            
            self.db.add(rfq)
            await self.db.flush()
            
            return str(rfq.id)
        
        except Exception as e:
            # Log error but don't crash
            return None
    
    async def create_opportunity_from_entity(
        self,
        entity: ExtractedEntity,
        created_by_id: str | None = None
    ) -> str | None:
        """
        Create an Opportunity record from extracted entity.
        
        Args:
            entity: Extracted entity data
            created_by_id: User ID creating the opportunity
        
        Returns:
            Created Opportunity ID or None if creation failed
        """
        if not self.db:
            return None
        
        try:
            from sqlalchemy import select, func
            from sensei.models.opportunity import Opportunity, OpportunityStage, OpportunityType, OpportunitySource
            from sensei.models.account import Account
            from uuid import UUID
            
            # Generate opportunity number
            year = datetime.now().year
            prefix = f"OPP-{year}-"
            
            result = await self.db.execute(
                select(func.max(Opportunity.opportunity_number))
                .where(Opportunity.opportunity_number.like(f"{prefix}%"))
            )
            last_number = result.scalar()
            
            if last_number:
                seq = int(last_number.split("-")[-1]) + 1
            else:
                seq = 1
            
            opp_number = f"{prefix}{seq:05d}"
            
            # Extract field values
            company_name = entity.get_field_value(FieldType.COMPANY_NAME)
            project_name = entity.get_field_value(FieldType.PROJECT_NAME)
            annual_volume = entity.get_field_value(FieldType.ANNUAL_VOLUME)
            target_price = entity.get_field_value(FieldType.TARGET_PRICE)
            quantity = entity.get_field_value(FieldType.QUANTITY)
            currency = entity.get_field_value(FieldType.CURRENCY, "MAD")
            
            # Find or create account
            account_id = None
            if company_name:
                result = await self.db.execute(
                    select(Account).where(Account.name.ilike(f"%{company_name}%")).limit(1)
                )
                account = result.scalar_one_or_none()
                if account:
                    account_id = account.id
                else:
                    # Create new account
                    new_account = Account(
                        name=company_name,
                        account_type="customer",
                        created_by_id=UUID(created_by_id) if created_by_id else None,
                    )
                    self.db.add(new_account)
                    await self.db.flush()
                    account_id = new_account.id
            
            if not account_id:
                return None
            
            # Create Opportunity
            opportunity = Opportunity(
                opportunity_number=opp_number,
                name=project_name or f"Opportunity from {company_name}",
                account_id=account_id,
                stage=OpportunityStage.PROSPECTING.value,
                opportunity_type=OpportunityType.NEW_BUSINESS.value,
                lead_source=OpportunitySource.RFQ.value,
                expected_quantity=quantity,
                expected_annual_volume=annual_volume,
                amount=target_price,
                currency=currency,
                probability=10,  # Initial low probability
                created_by_id=UUID(created_by_id) if created_by_id else None,
            )
            
            self.db.add(opportunity)
            await self.db.flush()
            
            return str(opportunity.id)
        
        except Exception as e:
            return None
    
    async def commit_changes(self) -> None:
        """Commit database changes."""
        if self.db:
            await self.db.commit()
    
    async def rollback_changes(self) -> None:
        """Rollback database changes."""
        if self.db:
            await self.db.rollback()
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def clear_all(self) -> None:
        """Clear all stored data (for testing)."""
        self._jobs.clear()
        self._documents.clear()
        self._known_customers.clear()
        self._known_contacts.clear()
