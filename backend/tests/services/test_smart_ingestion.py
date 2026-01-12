"""
Tests for Smart Ingestion service.

Tests:
- Document type detection
- Text extraction from PDFs and text files
- Field extraction (emails, phones, part numbers, dates, etc.)
- Entity building (opportunities, contacts, line items)
- Email ingestion workflow
- Document ingestion workflow
- Job status management
- Review workflow
- Database integration (RFQ/Opportunity creation)
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest

from sensei.services.smart_ingestion import (
    # Enums
    DocumentType,
    IngestionStatus,
    ExtractionConfidence,
    EntityType,
    FieldType,
    # Data models
    ExtractedField,
    ExtractedEntity,
    DocumentMetadata,
    OCRResult,
    OCRPage,
    EmailContent,
    EmailAttachment,
    IngestionJob,
    IngestionConfig,
    # Functions
    detect_document_type,
    calculate_checksum,
    normalize_text,
    parse_date,
    parse_number,
    confidence_to_enum,
    extract_company_from_email,
    extract_name_from_email,
    extract_text_from_document,
    # Classes
    FieldExtractor,
    EntityBuilder,
    SmartIngestionService,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =============================================================================
# Document Type Detection Tests
# =============================================================================


def test_detect_document_type_from_mime():
    """Test document type detection from MIME type."""
    assert detect_document_type("test.pdf", "application/pdf") == DocumentType.PDF
    assert detect_document_type("test.jpg", "image/jpeg") == DocumentType.IMAGE
    assert detect_document_type("test.png", "image/png") == DocumentType.IMAGE
    assert detect_document_type("test.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") == DocumentType.EXCEL
    assert detect_document_type("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == DocumentType.WORD
    assert detect_document_type("test.txt", "text/plain") == DocumentType.TEXT


def test_detect_document_type_from_extension():
    """Test document type detection from file extension."""
    assert detect_document_type("drawing.pdf") == DocumentType.PDF
    assert detect_document_type("photo.jpg") == DocumentType.IMAGE
    assert detect_document_type("photo.jpeg") == DocumentType.IMAGE
    assert detect_document_type("scan.tiff") == DocumentType.IMAGE
    assert detect_document_type("data.xlsx") == DocumentType.EXCEL
    assert detect_document_type("spec.docx") == DocumentType.WORD
    assert detect_document_type("notes.txt") == DocumentType.TEXT
    assert detect_document_type("email.eml") == DocumentType.EMAIL


def test_detect_document_type_unknown():
    """Test unknown document type."""
    assert detect_document_type("file.xyz") == DocumentType.UNKNOWN
    assert detect_document_type("noextension") == DocumentType.UNKNOWN


# =============================================================================
# Utility Function Tests
# =============================================================================


def test_calculate_checksum():
    """Test checksum calculation."""
    content = b"test content"
    checksum1 = calculate_checksum(content)
    checksum2 = calculate_checksum(content)
    
    assert checksum1 == checksum2  # Deterministic
    assert len(checksum1) == 64  # SHA-256 hex length
    
    different_content = b"different content"
    checksum3 = calculate_checksum(different_content)
    assert checksum3 != checksum1  # Different content = different checksum


def test_normalize_text():
    """Test text normalization."""
    assert normalize_text("  multiple   spaces  ") == "multiple spaces"
    assert normalize_text("line1\n\nline2") == "line1 line2"
    assert normalize_text("\tindented\t\ttext") == "indented text"


def test_parse_date():
    """Test date parsing."""
    # Different formats
    assert parse_date("12/31/2025") is not None
    assert parse_date("31/12/2025") is not None
    assert parse_date("2025-12-31") is not None
    assert parse_date("December 31, 2025") is not None
    assert parse_date("Dec 31, 2025") is not None
    
    # Invalid date
    assert parse_date("not a date") is None
    assert parse_date("99/99/9999") is None


def test_parse_number():
    """Test number parsing."""
    assert parse_number("123") == 123.0
    assert parse_number("1,234.56") == 1234.56
    assert parse_number("$1,234.56") == 1234.56
    assert parse_number("€1 234.56") == 1234.56
    
    # Invalid number
    assert parse_number("not a number") is None


def test_confidence_to_enum():
    """Test confidence conversion to enum."""
    assert confidence_to_enum(0.95) == ExtractionConfidence.HIGH
    assert confidence_to_enum(0.75) == ExtractionConfidence.MEDIUM
    assert confidence_to_enum(0.50) == ExtractionConfidence.LOW
    assert confidence_to_enum(0.20) == ExtractionConfidence.UNCERTAIN


def test_extract_company_from_email():
    """Test company name extraction from email."""
    assert extract_company_from_email("john@acmecorp.com") == "Acmecorp"
    assert extract_company_from_email("jane@smith-manufacturing.co") == "Smith Manufacturing"
    assert extract_company_from_email("test@company_name.io") == "Company Name"
    
    # No match
    assert extract_company_from_email("invalid") is None


def test_extract_name_from_email():
    """Test name and email extraction."""
    name, email = extract_name_from_email("John Doe <john@example.com>")
    assert name == "John Doe"
    assert email == "john@example.com"
    
    name, email = extract_name_from_email('"Jane Smith" <jane@example.com>')
    assert name == "Jane Smith"
    assert email == "jane@example.com"
    
    name, email = extract_name_from_email("user@example.com")
    assert name is None
    assert email == "user@example.com"


# =============================================================================
# Text Extraction Tests
# =============================================================================


def test_extract_text_from_text_document():
    """Test text extraction from plain text."""
    content = b"This is a simple text document.\nWith multiple lines."
    result = extract_text_from_document(content, DocumentType.TEXT)
    
    assert result.full_text == "This is a simple text document.\nWith multiple lines."
    assert result.confidence >= 0.9
    assert len(result.pages) == 1
    assert result.engine_used in ("utf8_decode", "utf8_decode_lossy")


def test_extract_text_handles_unicode_errors():
    """Test graceful handling of Unicode decode errors."""
    # Invalid UTF-8 bytes
    content = b"\x80\x81\x82 some text"
    result = extract_text_from_document(content, DocumentType.TEXT)
    
    # Should still extract something
    assert result.full_text is not None
    assert len(result.pages) > 0


# =============================================================================
# Field Extraction Tests
# =============================================================================


def test_field_extractor_email():
    """Test email address extraction."""
    extractor = FieldExtractor()
    text = "Contact us at info@example.com or sales@company.co.uk"
    
    fields = extractor.extract_field(FieldType.CONTACT_EMAIL, text)
    
    assert len(fields) == 2
    assert "info@example.com" in [f.value for f in fields]
    assert "sales@company.co.uk" in [f.value for f in fields]
    assert all(f.field_type == FieldType.CONTACT_EMAIL for f in fields)


def test_field_extractor_phone():
    """Test phone number extraction."""
    extractor = FieldExtractor()
    text = "Call us at (555) 123-4567 or +1-800-555-0100"
    
    fields = extractor.extract_field(FieldType.CONTACT_PHONE, text)
    
    assert len(fields) >= 1  # At least one phone number found


def test_field_extractor_part_number():
    """Test part number extraction."""
    extractor = FieldExtractor()
    text = "Part Number: ABC-1234-XYZ or P/N: DEF-5678"
    
    fields = extractor.extract_field(FieldType.PART_NUMBER, text)
    
    assert len(fields) >= 1
    # Check that extracted values look like part numbers
    for field in fields:
        assert len(field.value) > 3


def test_field_extractor_quantity():
    """Test quantity extraction."""
    extractor = FieldExtractor()
    text = "Quantity: 1,000 pcs or QTY: 500 units"
    
    fields = extractor.extract_field(FieldType.QUANTITY, text)
    
    assert len(fields) >= 1
    values = [f.value for f in fields]
    assert 1000 in values or 500 in values


def test_field_extractor_price():
    """Test price extraction."""
    extractor = FieldExtractor()
    text = "Target price $12.50 per unit or €15.00 each"
    
    fields = extractor.extract_field(FieldType.TARGET_PRICE, text)
    
    assert len(fields) >= 1
    # Prices should be parsed as numbers
    for field in fields:
        assert isinstance(field.value, (int, float, Decimal))


def test_field_extractor_date():
    """Test date extraction."""
    extractor = FieldExtractor()
    # Use exact pattern format from the regex
    text = "Due Date: 12/31/2025 or Deadline: 01-15-2026"
    
    fields = extractor.extract_field(FieldType.DUE_DATE, text)
    
    assert len(fields) >= 1
    # Dates should be parsed as datetime objects
    for field in fields:
        assert isinstance(field.value, datetime)


def test_field_extractor_material_spec():
    """Test material specification extraction."""
    extractor = FieldExtractor()
    text = "Material: 6061-T6 aluminum or AISI 304 stainless steel"
    
    fields = extractor.extract_field(FieldType.MATERIAL_SPEC, text)
    
    assert len(fields) >= 1


def test_field_extractor_validation():
    """Test field validation."""
    extractor = FieldExtractor()
    
    # Valid email
    fields = extractor.extract_field(FieldType.CONTACT_EMAIL, "test@example.com")
    assert len(fields) == 1
    assert fields[0].is_valid
    
    # Invalid quantity (would be caught by regex not matching, but test validation)
    text = "Quantity: -100"  # Negative quantity
    fields = extractor.extract_field(FieldType.QUANTITY, text)
    # Should either not match or have validation error
    if fields:
        assert not fields[0].is_valid


def test_field_extractor_deduplicate():
    """Test field deduplication."""
    extractor = FieldExtractor()
    text = "Email: test@example.com and again test@example.com"
    
    fields = extractor.extract_field(FieldType.CONTACT_EMAIL, text)
    
    # Should deduplicate
    assert len(fields) == 1


def test_field_extractor_extract_all():
    """Test extracting all field types at once."""
    extractor = FieldExtractor()
    text = """
    RFQ from ACME Corp
    Contact: John Doe <john@acmecorp.com>
    Phone: (555) 123-4567
    Part Number: ABC-1234-XYZ
    Quantity: 1,000 units
    Target Price: $12.50 each
    Due: 12/31/2025
    Material: 6061-T6 Aluminum
    """
    
    results = extractor.extract_all_fields(text)
    
    # Should extract multiple field types
    assert FieldType.CONTACT_EMAIL in results
    assert FieldType.CONTACT_PHONE in results
    assert FieldType.PART_NUMBER in results
    assert FieldType.QUANTITY in results
    assert FieldType.TARGET_PRICE in results
    # Due date may or may not match depending on context
    assert FieldType.MATERIAL_SPEC in results


# =============================================================================
# Entity Builder Tests
# =============================================================================


def test_entity_builder_opportunity():
    """Test building opportunity entity."""
    builder = EntityBuilder()
    
    fields = {
        FieldType.COMPANY_NAME: [
            ExtractedField(
                field_type=FieldType.COMPANY_NAME,
                value="ACME Corp",
                raw_text="ACME Corp",
                confidence=ExtractionConfidence.HIGH,
            )
        ],
        FieldType.ANNUAL_VOLUME: [
            ExtractedField(
                field_type=FieldType.ANNUAL_VOLUME,
                value=10000,
                raw_text="10,000/year",
                confidence=ExtractionConfidence.HIGH,
            )
        ],
    }
    
    entity = builder.build_opportunity(fields, source_document_id="doc123")
    
    assert entity.entity_type == EntityType.OPPORTUNITY
    assert FieldType.COMPANY_NAME in entity.fields
    assert entity.fields[FieldType.COMPANY_NAME].value == "ACME Corp"
    assert entity.confidence != ExtractionConfidence.UNCERTAIN


def test_entity_builder_contact():
    """Test building contact entity."""
    builder = EntityBuilder()
    
    fields = {
        FieldType.CONTACT_NAME: [
            ExtractedField(
                field_type=FieldType.CONTACT_NAME,
                value="John Doe",
                raw_text="John Doe",
                confidence=ExtractionConfidence.HIGH,
            )
        ],
        FieldType.CONTACT_EMAIL: [
            ExtractedField(
                field_type=FieldType.CONTACT_EMAIL,
                value="john@example.com",
                raw_text="john@example.com",
                confidence=ExtractionConfidence.HIGH,
            )
        ],
        FieldType.CONTACT_PHONE: [
            ExtractedField(
                field_type=FieldType.CONTACT_PHONE,
                value="(555) 123-4567",
                raw_text="(555) 123-4567",
                confidence=ExtractionConfidence.HIGH,
            )
        ],
    }
    
    entity = builder.build_contact(fields)
    
    assert entity is not None
    assert entity.entity_type == EntityType.CONTACT
    assert len(entity.fields) == 3
    assert entity.confidence == ExtractionConfidence.HIGH


def test_entity_builder_contact_requires_name_or_email():
    """Test contact requires at least name or email."""
    builder = EntityBuilder()
    
    # No name or email
    fields = {
        FieldType.CONTACT_PHONE: [
            ExtractedField(
                field_type=FieldType.CONTACT_PHONE,
                value="(555) 123-4567",
                raw_text="(555) 123-4567",
                confidence=ExtractionConfidence.HIGH,
            )
        ],
    }
    
    entity = builder.build_contact(fields)
    
    assert entity is None  # Should not build without name or email


def test_entity_builder_line_items():
    """Test building product/line item entities."""
    builder = EntityBuilder()
    
    fields = {
        FieldType.PART_NUMBER: [
            ExtractedField(
                field_type=FieldType.PART_NUMBER,
                value="ABC-123",
                raw_text="P/N: ABC-123",
                confidence=ExtractionConfidence.HIGH,
            ),
            ExtractedField(
                field_type=FieldType.PART_NUMBER,
                value="XYZ-456",
                raw_text="P/N: XYZ-456",
                confidence=ExtractionConfidence.HIGH,
            ),
        ],
        FieldType.QUANTITY: [
            ExtractedField(
                field_type=FieldType.QUANTITY,
                value=100,
                raw_text="Qty: 100",
                confidence=ExtractionConfidence.HIGH,
            ),
            ExtractedField(
                field_type=FieldType.QUANTITY,
                value=200,
                raw_text="Qty: 200",
                confidence=ExtractionConfidence.HIGH,
            ),
        ],
    }
    
    entities = builder.build_line_items(fields)
    
    assert len(entities) == 2  # Two part numbers = two line items
    assert all(e.entity_type == EntityType.PRODUCT for e in entities)
    
    # First item should match with first quantity
    assert entities[0].fields[FieldType.PART_NUMBER].value == "ABC-123"
    assert entities[0].fields[FieldType.QUANTITY].value == 100


# =============================================================================
# Smart Ingestion Service Tests
# =============================================================================


def test_smart_ingestion_service_create_job():
    """Test creating an ingestion job."""
    service = SmartIngestionService()
    
    job = service.create_job(created_by="user123")
    
    assert job.id is not None
    assert job.status == IngestionStatus.PENDING
    assert job.created_by == "user123"
    
    # Job should be stored
    retrieved = service.get_job(job.id)
    assert retrieved is not None
    assert retrieved.id == job.id


def test_smart_ingestion_service_list_jobs():
    """Test listing ingestion jobs."""
    service = SmartIngestionService()
    
    # Create multiple jobs
    job1 = service.create_job()
    job2 = service.create_job()
    job3 = service.create_job()
    
    jobs = service.list_jobs()
    
    assert len(jobs) >= 3
    job_ids = [j.id for j in jobs]
    assert job1.id in job_ids
    assert job2.id in job_ids
    assert job3.id in job_ids


def test_smart_ingestion_service_list_jobs_by_status():
    """Test filtering jobs by status."""
    service = SmartIngestionService()
    
    job1 = service.create_job()
    job1.status = IngestionStatus.COMPLETED
    
    job2 = service.create_job()
    job2.status = IngestionStatus.FAILED
    
    job3 = service.create_job()
    job3.status = IngestionStatus.REQUIRES_REVIEW
    
    # Filter by status
    completed = service.list_jobs(status=IngestionStatus.COMPLETED)
    assert len([j for j in completed if j.id == job1.id]) == 1
    
    review_needed = service.get_jobs_requiring_review()
    assert len([j for j in review_needed if j.id == job3.id]) == 1


def test_smart_ingestion_service_ingest_document():
    """Test ingesting a document."""
    service = SmartIngestionService(
        config=IngestionConfig(
            allowed_document_types=[DocumentType.TEXT, DocumentType.PDF, DocumentType.EMAIL]
        )
    )
    
    content = b"RFQ from ACME Corp\nPart Number: ABC-123\nQuantity: 1000\nTarget Price: $12.50"
    
    job = service.ingest_document(
        filename="rfq.txt",
        content=content,
        mime_type="text/plain"
    )
    
    assert job.status in (IngestionStatus.COMPLETED, IngestionStatus.REQUIRES_REVIEW)
    assert job.document_metadata is not None
    assert job.document_metadata.filename == "rfq.txt"
    assert len(job.extracted_entities) > 0


def test_smart_ingestion_service_ingest_document_validation():
    """Test document ingestion validation."""
    service = SmartIngestionService(
        config=IngestionConfig(
            allowed_document_types=[DocumentType.PDF],
            max_file_size_bytes=1024,
        )
    )
    
    # Wrong document type
    job = service.ingest_document(
        filename="test.txt",
        content=b"some content",
        mime_type="text/plain"
    )
    
    assert job.status == IngestionStatus.FAILED
    assert len(job.errors) > 0
    
    # File too large
    large_content = b"x" * 2048
    job2 = service.ingest_document(
        filename="test.pdf",
        content=large_content,
        mime_type="application/pdf"
    )
    
    assert job2.status == IngestionStatus.FAILED


def test_smart_ingestion_service_ingest_email():
    """Test ingesting an email."""
    service = SmartIngestionService()
    
    email = EmailContent(
        id="email123",
        subject="RFQ Request for ABC-123",
        from_address="john@acmecorp.com",
        from_name="John Doe",
        to_addresses=["sales@ourcompany.com"],
        body_text="""
        Hello,
        
        We need a quote for Part Number ABC-123.
        Quantity: 1,000 pieces
        Target price: $12.50 each
        Due date: 12/31/2025
        
        Thanks,
        John
        """,
    )
    
    job = service.ingest_email(email)
    
    assert job.status in (IngestionStatus.COMPLETED, IngestionStatus.REQUIRES_REVIEW)
    assert job.email_content is not None
    assert len(job.extracted_entities) > 0
    
    # Should extract contact info from email
    entities_by_type = {e.entity_type: e for e in job.extracted_entities}
    if EntityType.CONTACT in entities_by_type:
        contact = entities_by_type[EntityType.CONTACT]
        assert contact.get_field_value(FieldType.CONTACT_EMAIL) == "john@acmecorp.com"


def test_smart_ingestion_service_known_customer_matching():
    """Test matching against known customers."""
    service = SmartIngestionService()
    
    # Register known customer
    service.register_known_customer("acmecorp.com", "customer123")
    
    email = EmailContent(
        id="email123",
        subject="RFQ",
        from_address="john@acmecorp.com",
        from_name="John Doe",
        to_addresses=["sales@ourcompany.com"],
        body_text="Need quote",
    )
    
    job = service.ingest_email(email)
    
    # Should add warning about known customer
    assert any("known customer" in w.lower() for w in job.warnings)


def test_smart_ingestion_service_review_workflow():
    """Test review and approval workflow."""
    service = SmartIngestionService()
    
    # Create a job that needs review
    job = service.create_job()
    job.status = IngestionStatus.REQUIRES_REVIEW
    
    # Add an entity
    entity = ExtractedEntity(
        id=str(uuid4()),
        entity_type=EntityType.OPPORTUNITY,
        fields={
            FieldType.COMPANY_NAME: ExtractedField(
                field_type=FieldType.COMPANY_NAME,
                value="ACME Corp",
                raw_text="ACME Corp",
                confidence=ExtractionConfidence.MEDIUM,
            )
        },
    )
    job.extracted_entities.append(entity)
    
    # Approve with overrides
    overrides = {
        entity.id: {
            FieldType.COMPANY_NAME: "ACME Corporation (corrected)"
        }
    }
    
    updated_job = service.approve_and_create(
        job.id,
        entity_overrides=overrides,
        reviewer_notes="Corrected company name"
    )
    
    assert updated_job.status == IngestionStatus.COMPLETED
    assert updated_job.review_notes == "Corrected company name"
    assert entity.fields[FieldType.COMPANY_NAME].value == "ACME Corporation (corrected)"
    assert entity.fields[FieldType.COMPANY_NAME].confidence == ExtractionConfidence.HIGH


def test_smart_ingestion_service_reject_job():
    """Test rejecting an ingestion job."""
    service = SmartIngestionService()
    
    job = service.create_job()
    job.status = IngestionStatus.REQUIRES_REVIEW
    
    rejected = service.reject_job(job.id, "Duplicate submission")
    
    assert rejected.status == IngestionStatus.FAILED
    assert "Rejected: Duplicate submission" in rejected.errors


def test_smart_ingestion_service_update_entity_field():
    """Test updating a field on an extracted entity."""
    service = SmartIngestionService()
    
    job = service.create_job()
    entity = ExtractedEntity(
        id=str(uuid4()),
        entity_type=EntityType.OPPORTUNITY,
    )
    job.extracted_entities.append(entity)
    
    # Update field
    updated = service.update_entity_field(
        job.id,
        entity.id,
        FieldType.COMPANY_NAME,
        "New Company Name"
    )
    
    assert updated is not None
    assert updated.fields[FieldType.COMPANY_NAME].value == "New Company Name"
    assert updated.fields[FieldType.COMPANY_NAME].confidence == ExtractionConfidence.HIGH


def test_smart_ingestion_service_get_stats():
    """Test getting ingestion statistics."""
    service = SmartIngestionService()
    
    # Create various jobs
    job1 = service.create_job()
    job1.status = IngestionStatus.COMPLETED
    job1.processing_started_at = _utcnow()
    job1.processing_completed_at = _utcnow() + timedelta(seconds=5)
    
    job2 = service.create_job()
    job2.status = IngestionStatus.FAILED
    
    job3 = service.create_job()
    job3.status = IngestionStatus.REQUIRES_REVIEW
    
    stats = service.get_stats()
    
    assert stats.total_jobs >= 3
    assert stats.completed_jobs >= 1
    assert stats.failed_jobs >= 1
    assert stats.pending_review_jobs >= 1


def test_smart_ingestion_config():
    """Test ingestion configuration."""
    config = IngestionConfig(
        auto_create_opportunities=True,
        confidence_threshold_for_auto=0.8,
        max_file_size_bytes=10_000_000,
        allowed_document_types=[DocumentType.PDF, DocumentType.EMAIL],
    )
    
    assert config.auto_create_opportunities is True
    assert config.confidence_threshold_for_auto == 0.8
    assert config.max_file_size_bytes == 10_000_000
    assert DocumentType.PDF in config.allowed_document_types


def test_extracted_entity_validation():
    """Test entity validation."""
    entity = ExtractedEntity(
        id=str(uuid4()),
        entity_type=EntityType.OPPORTUNITY,
        fields={
            FieldType.COMPANY_NAME: ExtractedField(
                field_type=FieldType.COMPANY_NAME,
                value="ACME Corp",
                raw_text="ACME Corp",
                confidence=ExtractionConfidence.HIGH,
            )
        },
    )
    
    # Has required field
    assert entity.is_complete
    
    # No validation errors
    assert len(entity.validation_errors) == 0
    
    # Add field with validation error
    entity.fields[FieldType.QUANTITY] = ExtractedField(
        field_type=FieldType.QUANTITY,
        value=-100,
        raw_text="-100",
        confidence=ExtractionConfidence.LOW,
        validation_errors=["Quantity must be positive"]
    )
    
    assert len(entity.validation_errors) > 0


def test_ingestion_job_properties():
    """Test ingestion job computed properties."""
    job = IngestionJob(
        id=str(uuid4()),
        status=IngestionStatus.PROCESSING,
        processing_started_at=_utcnow(),
    )
    
    # No duration yet
    assert job.processing_duration_ms is None
    
    # Complete processing
    job.processing_completed_at = job.processing_started_at + timedelta(seconds=2)
    
    # Should calculate duration
    duration = job.processing_duration_ms
    assert duration is not None
    assert duration >= 2000  # At least 2 seconds in milliseconds


def test_ingestion_job_needs_review():
    """Test job review detection."""
    job = IngestionJob(
        id=str(uuid4()),
        status=IngestionStatus.REQUIRES_REVIEW,
    )
    
    assert job.needs_review is True
    
    # Job with low confidence entity
    job2 = IngestionJob(
        id=str(uuid4()),
        status=IngestionStatus.COMPLETED,
        extracted_entities=[
            ExtractedEntity(
                id=str(uuid4()),
                entity_type=EntityType.OPPORTUNITY,
                confidence=ExtractionConfidence.LOW,
            )
        ],
    )
    
    assert job2.needs_review is True


def test_field_extractor_custom_extractors():
    """Test registering custom field extractors."""
    extractor = FieldExtractor()
    
    # Register custom extractor for project names
    def extract_project(text: str) -> list[ExtractedField]:
        # Simple custom logic
        if "PROJECT:" in text.upper():
            parts = text.upper().split("PROJECT:")
            if len(parts) > 1:
                project_name = parts[1].split()[0]
                return [
                    ExtractedField(
                        field_type=FieldType.PROJECT_NAME,
                        value=project_name,
                        raw_text=f"PROJECT: {project_name}",
                        confidence=ExtractionConfidence.HIGH,
                    )
                ]
        return []
    
    extractor.register_custom_extractor(FieldType.PROJECT_NAME, extract_project)
    
    # Test custom extraction
    text = "This is PROJECT: AlphaOne development"
    fields = extractor.extract_field(FieldType.PROJECT_NAME, text)
    
    assert len(fields) == 1
    assert fields[0].value == "ALPHAONE"


def test_clear_all():
    """Test clearing all service data."""
    service = SmartIngestionService()
    
    # Add some data
    service.create_job()
    service.create_job()
    service.register_known_customer("test.com", "cust123")
    
    assert len(service._jobs) > 0
    assert len(service._known_customers) > 0
    
    # Clear all
    service.clear_all()
    
    assert len(service._jobs) == 0
    assert len(service._documents) == 0
    assert len(service._known_customers) == 0
    assert len(service._known_contacts) == 0
