"""
Tests for PDF Generation Service.

Tests cover:
- Template management (CRUD, defaults)
- PDF generation for all document types
- PDF retrieval and listing
- Version binding and integrity
- Expiration and cleanup
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from uuid import uuid4

from sensei.services.utils.pdf_generation import (
    PDFGenerationService,
    PDFDocumentType,
    PDFLanguage,
    PDFBrandTemplate,
    PDFStatus,
    WatermarkType,
    BrandingConfig,
    WatermarkConfig,
    PDFGenerationOptions,
    PDFSection,
    PDFTemplate,
    GeneratedPDF,
    QuotePDFData,
    QualificationPDFData,
    TodaySnapshotPDFData,
    ObeyaSnapshotPDFData,
    WeekInReviewPDFData,
    EightDReportPDFData,
    get_pdf_generation_service,
    reset_pdf_generation_service,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TestPDFDocumentType:
    """Tests for PDFDocumentType enum."""
    
    def test_all_document_types_exist(self):
        """Test all expected document types are defined."""
        assert PDFDocumentType.QUOTE == "quote"
        assert PDFDocumentType.QUALIFICATION_REPORT == "qualification_report"
        assert PDFDocumentType.TODAY_SNAPSHOT == "today_snapshot"
        assert PDFDocumentType.OBEYA_SNAPSHOT == "obeya_snapshot"
        assert PDFDocumentType.WEEK_IN_REVIEW == "week_in_review"
        assert PDFDocumentType.EIGHT_D_REPORT == "8d_report"
        assert PDFDocumentType.RFQ_SUMMARY == "rfq_summary"
        assert PDFDocumentType.A3_REPORT == "a3_report"
        assert PDFDocumentType.TRAINING_CERTIFICATE == "training_certificate"
        assert PDFDocumentType.STARZ_PAYSLIP == "starz_payslip"
        assert PDFDocumentType.STARZ_PURCHASE_ORDER == "starz_purchase_order"
        assert PDFDocumentType.STARZ_QUOTATION == "starz_quotation"
        assert PDFDocumentType.STARZ_WMS_LABEL == "starz_wms_label"
    
    def test_document_type_count(self):
        """Test total count of document types."""
        assert len(PDFDocumentType) == 13


class TestPDFLanguage:
    """Tests for PDFLanguage enum."""
    
    def test_all_languages_exist(self):
        """Test all expected languages are defined."""
        assert PDFLanguage.ENGLISH == "en"
        assert PDFLanguage.FRENCH == "fr"
        assert PDFLanguage.ARABIC == "ar"


class TestPDFBrandTemplate:
    """Tests for PDFBrandTemplate enum."""
    
    def test_all_brand_templates_exist(self):
        """Test all expected brand templates are defined."""
        assert PDFBrandTemplate.DEFAULT == "default"
        assert PDFBrandTemplate.CORPORATE == "corporate"
        assert PDFBrandTemplate.MINIMAL == "minimal"
        assert PDFBrandTemplate.CUSTOMER_FACING == "customer_facing"
        assert PDFBrandTemplate.INTERNAL == "internal"


class TestWatermarkType:
    """Tests for WatermarkType enum."""
    
    def test_all_watermark_types_exist(self):
        """Test all expected watermark types are defined."""
        assert WatermarkType.NONE == "none"
        assert WatermarkType.DRAFT == "draft"
        assert WatermarkType.CONFIDENTIAL == "confidential"
        assert WatermarkType.INTERNAL_ONLY == "internal_only"
        assert WatermarkType.REVISION == "revision"
        assert WatermarkType.SUPERSEDED == "superseded"


class TestBrandingConfig:
    """Tests for BrandingConfig dataclass."""
    
    def test_default_values(self):
        """Test default branding configuration."""
        config = BrandingConfig()
        
        assert config.template == PDFBrandTemplate.DEFAULT
        assert config.logo_base64 is None
        assert config.primary_color == "#1a365d"
        assert config.secondary_color == "#2b6cb0"
        assert config.accent_color == "#38a169"
        assert config.font_family == "Helvetica"
        assert config.include_page_numbers is True
        assert config.include_generated_date is True
        assert config.include_confidentiality_notice is False
    
    def test_custom_branding(self):
        """Test custom branding configuration."""
        config = BrandingConfig(
            template=PDFBrandTemplate.CORPORATE,
            primary_color="#000000",
            header_text="Company Name",
            footer_text="Confidential",
            include_confidentiality_notice=True,
        )
        
        assert config.template == PDFBrandTemplate.CORPORATE
        assert config.primary_color == "#000000"
        assert config.header_text == "Company Name"
        assert config.footer_text == "Confidential"
        assert config.include_confidentiality_notice is True


class TestWatermarkConfig:
    """Tests for WatermarkConfig dataclass."""
    
    def test_default_values(self):
        """Test default watermark configuration."""
        config = WatermarkConfig()
        
        assert config.watermark_type == WatermarkType.NONE
        assert config.custom_text is None
        assert config.opacity == 0.15
        assert config.angle == 45.0
        assert config.font_size == 72
    
    def test_custom_watermark(self):
        """Test custom watermark configuration."""
        config = WatermarkConfig(
            watermark_type=WatermarkType.DRAFT,
            custom_text="PRELIMINARY",
            opacity=0.25,
        )
        
        assert config.watermark_type == WatermarkType.DRAFT
        assert config.custom_text == "PRELIMINARY"
        assert config.opacity == 0.25


class TestPDFGenerationOptions:
    """Tests for PDFGenerationOptions dataclass."""
    
    def test_default_values(self):
        """Test default generation options."""
        options = PDFGenerationOptions()
        
        assert options.language == PDFLanguage.ENGLISH
        assert options.paper_size == "A4"
        assert options.orientation == "portrait"
        assert options.margin_top == 25.0
        assert options.include_table_of_contents is False
        assert options.compress is True
        assert options.encrypt is False
    
    def test_custom_options(self):
        """Test custom generation options."""
        options = PDFGenerationOptions(
            language=PDFLanguage.FRENCH,
            paper_size="Letter",
            orientation="landscape",
            include_table_of_contents=True,
            encrypt=True,
            password="secret123",
        )
        
        assert options.language == PDFLanguage.FRENCH
        assert options.paper_size == "Letter"
        assert options.orientation == "landscape"
        assert options.include_table_of_contents is True
        assert options.encrypt is True
        assert options.password == "secret123"


class TestPDFSection:
    """Tests for PDFSection dataclass."""
    
    def test_section_creation(self):
        """Test creating a PDF section."""
        section = PDFSection(
            id="header",
            title="Document Header",
            content={"key": "value"},
            order=1,
        )
        
        assert section.id == "header"
        assert section.title == "Document Header"
        assert section.content == {"key": "value"}
        assert section.order == 1
        assert section.include_in_toc is True
        assert section.page_break_before is False
        assert section.page_break_after is False


class TestQuotePDFData:
    """Tests for QuotePDFData dataclass."""
    
    def test_quote_data_creation(self):
        """Test creating quote PDF data."""
        quote_id = uuid4()
        data = QuotePDFData(
            quote_id=quote_id,
            quote_number="Q-2026-001",
            revision="A",
            customer_name="ACME Corp",
            product_name="Widget X",
            part_number="WDG-001",
            validity_date=date(2026, 2, 1),
            currency="USD",
            incoterms="EXW",
            payment_terms="Net 30",
            lead_time_days=45,
            moq=100,
            line_items=[{"item": "Widget", "qty": 100, "price": 10.00}],
            price_breaks=[{"qty": 100, "price": 10.00}, {"qty": 500, "price": 9.50}],
            total_price=1000.00,
            unit_price=10.00,
            assumptions=["Based on current material costs"],
            conditions=["Price valid for 30 days"],
            exclusions=["Shipping not included"],
            prepared_by="Sales Engineer",
            customer_address="123 Main St",
            contact_name="John Doe",
            contact_email="john@acme.com",
            notes="Special handling required",
        )
        
        assert data.quote_id == quote_id
        assert data.quote_number == "Q-2026-001"
        assert data.revision == "A"
        assert data.customer_name == "ACME Corp"
        assert data.total_price == 1000.00
        assert len(data.line_items) == 1
        assert len(data.price_breaks) == 2
        assert data.include_margin is False


class TestQualificationPDFData:
    """Tests for QualificationPDFData dataclass."""
    
    def test_qualification_data_creation(self):
        """Test creating qualification PDF data."""
        qual_id = uuid4()
        rfq_id = uuid4()
        
        data = QualificationPDFData(
            qualification_id=qual_id,
            rfq_id=rfq_id,
            rfq_number="RFQ-2026-001",
            customer_name="ACME Corp",
            product_family="Widgets",
            opportunity_value=100000.00,
            currency="USD",
            capability_score=85.0,
            strategic_score=70.0,
            risk_score=20.0,
            commercial_score=75.0,
            operational_score=80.0,
            overall_score=72.0,
            decision="QUOTE_WITH_CONDITIONS",
            decision_rationale="Good fit with manageable risks",
            conditions=["MOQ: 500 units", "Lead time: 8 weeks"],
            risks=[{"category": "Technical", "description": "New process"}],
        )
        
        assert data.qualification_id == qual_id
        assert data.rfq_id == rfq_id
        assert data.overall_score == 72.0
        assert data.decision == "QUOTE_WITH_CONDITIONS"
        assert len(data.conditions) == 2
        assert data.is_override is False


class TestTodaySnapshotPDFData:
    """Tests for TodaySnapshotPDFData dataclass."""
    
    def test_today_snapshot_data_creation(self):
        """Test creating today snapshot PDF data."""
        user_id = uuid4()
        
        data = TodaySnapshotPDFData(
            user_id=user_id,
            user_name="John Manager",
            snapshot_date=date.today(),
            top_priorities=[{"title": "Close Deal A", "due": "Today"}],
            risks_by_category={"delivery": [{"desc": "Late shipment"}]},
            top_risks=[{"category": "delivery", "desc": "Late shipment"}],
            overdue_commitments=[{"title": "Follow-up call"}],
            due_today_commitments=[{"title": "Quote submission"}],
            abnormality_counts={"stale_rfq": 2, "late_quote": 1},
            critical_abnormalities=[{"type": "late_quote", "desc": "Quote 3 days late"}],
            lsw_summary={"completed": 5, "pending": 2},
            metrics=[{"name": "Open Quotes", "value": 12}],
            greeting="Good morning, John!",
        )
        
        assert data.user_id == user_id
        assert data.user_name == "John Manager"
        assert len(data.top_priorities) == 1
        assert len(data.overdue_commitments) == 1
        assert data.greeting == "Good morning, John!"


class TestObeyaSnapshotPDFData:
    """Tests for ObeyaSnapshotPDFData dataclass."""
    
    def test_obeya_snapshot_data_creation(self):
        """Test creating obeya snapshot PDF data."""
        data = ObeyaSnapshotPDFData(
            snapshot_date=date.today(),
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            safety_items=[{"title": "Safety training completed"}],
            quality_items=[{"title": "NC rate down 15%"}],
            delivery_items=[{"title": "On-time delivery 98%"}],
            cost_items=[{"title": "Scrap reduction"}],
            people_items=[{"title": "New hire onboarded"}],
            red_items=[{"category": "quality", "desc": "Customer complaint"}],
            red_items_count=1,
            trends={"quality": {"direction": "up", "change": 15}},
            countermeasures_in_progress=[{"action": "Root cause analysis"}],
            countermeasures_due=[{"action": "Implement fix", "due": "2026-01-10"}],
        )
        
        assert data.snapshot_date == date.today()
        assert len(data.safety_items) == 1
        assert len(data.quality_items) == 1
        assert data.red_items_count == 1


class TestEightDReportPDFData:
    """Tests for EightDReportPDFData dataclass."""
    
    def test_8d_report_data_creation(self):
        """Test creating 8D report PDF data."""
        capa_id = uuid4()
        
        data = EightDReportPDFData(
            capa_id=capa_id,
            capa_number="CAPA-2026-001",
            report_date=date.today(),
            team_leader="Quality Manager",
            team_members=["Engineer 1", "Engineer 2"],
            problem_description="Defective parts found in batch",
            problem_source="Customer complaint",
            affected_products=["Widget A", "Widget B"],
            affected_quantity=50,
            detection_date=date.today() - timedelta(days=5),
            customer_impact="Customer received defective goods",
            containment_actions=[
                {"action": "Quarantine stock", "status": "completed"}
            ],
            containment_effective=True,
            root_cause_method="5-Why",
            root_cause_analysis="Why 1 -> Why 2 -> Why 3 -> Root cause",
            root_causes=["Incorrect tool setting"],
            contributing_factors=["Operator training gap"],
            linked_a3_id=None,
            corrective_actions=[
                {"action": "Calibrate tools", "status": "completed"}
            ],
            verification_method="Inspection",
            verification_results="100% pass rate",
            verification_date=date.today(),
            verified_by="QA Inspector",
            verification_passed=True,
            preventive_actions=[
                {"action": "Update procedure", "status": "in_progress"}
            ],
            standard_work_updates=[
                {"document": "SOP-001", "change": "Added calibration check"}
            ],
            lessons_learned=["Daily calibration check required"],
            team_recognition="Team completed analysis in 3 days",
            closure_date=None,
            closed_by=None,
            effectiveness_check_date=date.today() + timedelta(days=30),
            effectiveness_status="pending",
        )
        
        assert data.capa_id == capa_id
        assert data.capa_number == "CAPA-2026-001"
        assert len(data.team_members) == 2
        assert len(data.root_causes) == 1
        assert data.verification_passed is True


class TestPDFGenerationService:
    """Tests for PDFGenerationService."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test."""
        reset_pdf_generation_service()
        return PDFGenerationService()
    
    @pytest.fixture
    def sample_quote_data(self):
        """Create sample quote data."""
        return QuotePDFData(
            quote_id=uuid4(),
            quote_number="Q-2026-001",
            revision="A",
            customer_name="ACME Corp",
            product_name="Widget X",
            part_number="WDG-001",
            validity_date=date(2026, 2, 1),
            currency="USD",
            incoterms="EXW",
            payment_terms="Net 30",
            lead_time_days=45,
            moq=100,
            line_items=[{"item": "Widget", "qty": 100, "price": 10.00}],
            price_breaks=[{"qty": 100, "price": 10.00}],
            total_price=1000.00,
            unit_price=10.00,
            assumptions=["Based on current costs"],
            conditions=["30 day validity"],
            exclusions=["Shipping"],
            prepared_by="Sales Engineer",
            customer_address="123 Main St",
            contact_name="John Doe",
            contact_email="john@acme.com",
        )
    
    @pytest.fixture
    def sample_qualification_data(self):
        """Create sample qualification data."""
        return QualificationPDFData(
            qualification_id=uuid4(),
            rfq_id=uuid4(),
            rfq_number="RFQ-2026-001",
            customer_name="ACME Corp",
            product_family="Widgets",
            opportunity_value=100000.00,
            currency="USD",
            capability_score=85.0,
            strategic_score=70.0,
            risk_score=20.0,
            commercial_score=75.0,
            operational_score=80.0,
            overall_score=72.0,
            decision="QUOTE",
            decision_rationale="Good fit",
            conditions=[],
            risks=[],
        )
    
    @pytest.fixture
    def sample_today_data(self):
        """Create sample today snapshot data."""
        return TodaySnapshotPDFData(
            user_id=uuid4(),
            user_name="John Manager",
            snapshot_date=date.today(),
            top_priorities=[],
            risks_by_category={},
            top_risks=[],
            overdue_commitments=[],
            due_today_commitments=[],
            abnormality_counts={},
            critical_abnormalities=[],
            lsw_summary={},
            metrics=[],
        )
    
    @pytest.fixture
    def sample_obeya_data(self):
        """Create sample obeya snapshot data."""
        return ObeyaSnapshotPDFData(
            snapshot_date=date.today(),
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            safety_items=[],
            quality_items=[],
            delivery_items=[],
            cost_items=[],
            people_items=[],
            red_items=[],
            red_items_count=0,
            trends={},
            countermeasures_in_progress=[],
            countermeasures_due=[],
        )
    
    @pytest.fixture
    def sample_8d_data(self):
        """Create sample 8D report data."""
        return EightDReportPDFData(
            capa_id=uuid4(),
            capa_number="CAPA-2026-001",
            report_date=date.today(),
            team_leader="Quality Manager",
            team_members=["Engineer 1"],
            problem_description="Defect found",
            problem_source="Customer",
            affected_products=["Widget A"],
            affected_quantity=10,
            detection_date=date.today(),
            customer_impact=None,
            containment_actions=[],
            containment_effective=False,
            root_cause_method="5-Why",
            root_cause_analysis="Analysis",
            root_causes=["Root cause"],
            contributing_factors=[],
            linked_a3_id=None,
            corrective_actions=[],
            verification_method="Inspection",
            verification_results="",
            verification_date=None,
            verified_by=None,
            verification_passed=False,
            preventive_actions=[],
            standard_work_updates=[],
            lessons_learned=[],
            team_recognition=None,
            closure_date=None,
            closed_by=None,
            effectiveness_check_date=None,
            effectiveness_status=None,
        )


class TestTemplateManagement(TestPDFGenerationService):
    """Tests for template management."""
    
    def test_default_templates_registered(self, service):
        """Test that default templates are registered on init."""
        templates = service.list_templates()
        
        # Should have at least one default template per major type
        assert len(templates) >= 6
        
        # Check each major type has a default
        for doc_type in [
            PDFDocumentType.QUOTE,
            PDFDocumentType.QUALIFICATION_REPORT,
            PDFDocumentType.TODAY_SNAPSHOT,
            PDFDocumentType.OBEYA_SNAPSHOT,
            PDFDocumentType.WEEK_IN_REVIEW,
            PDFDocumentType.EIGHT_D_REPORT,
        ]:
            default = service.get_default_template(doc_type)
            assert default is not None
            assert default.document_type == doc_type
            assert default.is_default is True
    
    def test_get_template_by_id(self, service):
        """Test getting a template by ID."""
        templates = service.list_templates()
        template = templates[0]
        
        retrieved = service.get_template(template.id)
        
        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.name == template.name
    
    def test_get_nonexistent_template(self, service):
        """Test getting a nonexistent template returns None."""
        result = service.get_template(uuid4())
        assert result is None
    
    def test_list_templates_by_document_type(self, service):
        """Test listing templates filtered by document type."""
        quote_templates = service.list_templates(document_type=PDFDocumentType.QUOTE)
        
        assert len(quote_templates) >= 1
        for template in quote_templates:
            assert template.document_type == PDFDocumentType.QUOTE
    
    def test_create_template(self, service):
        """Test creating a new template."""
        created_by = uuid4()
        
        template = service.create_template(
            name="Custom Quote Template",
            document_type=PDFDocumentType.QUOTE,
            branding=BrandingConfig(template=PDFBrandTemplate.CORPORATE),
            watermark=WatermarkConfig(watermark_type=WatermarkType.DRAFT),
            default_options=PDFGenerationOptions(language=PDFLanguage.FRENCH),
            sections=[
                PDFSection(id="header", title="Header", content={}, order=1),
            ],
            created_by=created_by,
        )
        
        assert template.id is not None
        assert template.name == "Custom Quote Template"
        assert template.document_type == PDFDocumentType.QUOTE
        assert template.branding.template == PDFBrandTemplate.CORPORATE
        assert template.created_by == created_by
        assert template.is_default is False
    
    def test_create_template_as_default(self, service):
        """Test creating a new template as default."""
        created_by = uuid4()
        
        # Get current default
        old_default = service.get_default_template(PDFDocumentType.QUOTE)
        assert old_default is not None
        
        # Create new default
        new_template = service.create_template(
            name="New Default Quote",
            document_type=PDFDocumentType.QUOTE,
            branding=BrandingConfig(),
            watermark=WatermarkConfig(),
            default_options=PDFGenerationOptions(),
            sections=[],
            created_by=created_by,
            is_default=True,
        )
        
        # Check new is default
        assert new_template.is_default is True
        current_default = service.get_default_template(PDFDocumentType.QUOTE)
        assert current_default.id == new_template.id
        
        # Check old is no longer default
        old_template = service.get_template(old_default.id)
        assert old_template.is_default is False
    
    def test_update_template(self, service):
        """Test updating a template."""
        templates = service.list_templates(document_type=PDFDocumentType.QUOTE)
        template = templates[0]
        original_name = template.name
        
        updated = service.update_template(
            template_id=template.id,
            name="Updated Name",
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.name != original_name
    
    def test_update_template_branding(self, service):
        """Test updating template branding."""
        templates = service.list_templates()
        template = templates[0]
        
        new_branding = BrandingConfig(
            primary_color="#ff0000",
            header_text="New Header",
        )
        
        updated = service.update_template(
            template_id=template.id,
            branding=new_branding,
        )
        
        assert updated is not None
        assert updated.branding.primary_color == "#ff0000"
        assert updated.branding.header_text == "New Header"
    
    def test_update_nonexistent_template(self, service):
        """Test updating a nonexistent template."""
        result = service.update_template(
            template_id=uuid4(),
            name="New Name",
        )
        assert result is None
    
    def test_set_default_template(self, service):
        """Test setting a template as default."""
        created_by = uuid4()
        
        # Create a non-default template
        template = service.create_template(
            name="To Be Default",
            document_type=PDFDocumentType.QUOTE,
            branding=BrandingConfig(),
            watermark=WatermarkConfig(),
            default_options=PDFGenerationOptions(),
            sections=[],
            created_by=created_by,
            is_default=False,
        )
        
        assert template.is_default is False
        
        # Set as default
        result = service.set_default_template(template.id)
        
        assert result is True
        assert template.is_default is True
        
        current_default = service.get_default_template(PDFDocumentType.QUOTE)
        assert current_default.id == template.id
    
    def test_set_default_nonexistent_template(self, service):
        """Test setting a nonexistent template as default."""
        result = service.set_default_template(uuid4())
        assert result is False
    
    def test_deactivate_template(self, service):
        """Test deactivating a template."""
        templates = service.list_templates()
        template = templates[0]
        
        service.update_template(template.id, is_active=False)
        
        # Should not appear in active-only list
        active_templates = service.list_templates(active_only=True)
        active_ids = [t.id for t in active_templates]
        assert template.id not in active_ids
        
        # Should appear when including inactive
        all_templates = service.list_templates(active_only=False)
        all_ids = [t.id for t in all_templates]
        assert template.id in all_ids


class TestQuotePDFGeneration(TestPDFGenerationService):
    """Tests for quote PDF generation."""
    
    def test_generate_quote_pdf(self, service, sample_quote_data):
        """Test generating a quote PDF."""
        user_id = uuid4()
        
        pdf = service.generate_quote_pdf(
            data=sample_quote_data,
            generated_by=user_id,
        )
        
        assert pdf.id is not None
        assert pdf.document_type == PDFDocumentType.QUOTE
        assert pdf.source_entity_type == "quote"
        assert pdf.source_entity_id == sample_quote_data.quote_id
        assert pdf.source_version == "A"
        assert pdf.generated_by == user_id
        assert pdf.status == PDFStatus.COMPLETED
        assert pdf.filename.endswith(".pdf")
        assert pdf.content_base64 is not None
        assert pdf.content_hash is not None
        assert pdf.page_count >= 1
    
    def test_generate_quote_pdf_with_options(self, service, sample_quote_data):
        """Test generating a quote PDF with custom options."""
        user_id = uuid4()
        options = PDFGenerationOptions(
            language=PDFLanguage.FRENCH,
            watermark=WatermarkConfig(watermark_type=WatermarkType.DRAFT),
        )
        
        pdf = service.generate_quote_pdf(
            data=sample_quote_data,
            generated_by=user_id,
            options=options,
        )
        
        assert pdf.options.language == PDFLanguage.FRENCH
    
    def test_generate_internal_quote_pdf(self, service, sample_quote_data):
        """Test generating an internal quote PDF with margin info."""
        user_id = uuid4()
        sample_quote_data.include_margin = True
        sample_quote_data.margin_percentage = 25.0
        
        pdf = service.generate_quote_pdf(
            data=sample_quote_data,
            generated_by=user_id,
            include_internal=True,
        )
        
        assert pdf.status == PDFStatus.COMPLETED
        # Internal version should have internal watermark
        assert pdf.options.watermark.watermark_type == WatermarkType.INTERNAL_ONLY


class TestQualificationPDFGeneration(TestPDFGenerationService):
    """Tests for qualification PDF generation."""
    
    def test_generate_qualification_pdf(self, service, sample_qualification_data):
        """Test generating a qualification report PDF."""
        user_id = uuid4()
        
        pdf = service.generate_qualification_pdf(
            data=sample_qualification_data,
            generated_by=user_id,
        )
        
        assert pdf.id is not None
        assert pdf.document_type == PDFDocumentType.QUALIFICATION_REPORT
        assert pdf.source_entity_type == "qualification"
        assert pdf.source_entity_id == sample_qualification_data.qualification_id
        assert pdf.status == PDFStatus.COMPLETED


class TestTodaySnapshotPDFGeneration(TestPDFGenerationService):
    """Tests for today snapshot PDF generation."""
    
    def test_generate_today_snapshot_pdf(self, service, sample_today_data):
        """Test generating a today snapshot PDF."""
        user_id = uuid4()
        
        pdf = service.generate_today_snapshot_pdf(
            data=sample_today_data,
            generated_by=user_id,
        )
        
        assert pdf.id is not None
        assert pdf.document_type == PDFDocumentType.TODAY_SNAPSHOT
        assert pdf.source_entity_type == "today_snapshot"
        assert pdf.source_entity_id == sample_today_data.user_id
        assert pdf.source_version == sample_today_data.snapshot_date.isoformat()
        assert pdf.status == PDFStatus.COMPLETED


class TestObeyaSnapshotPDFGeneration(TestPDFGenerationService):
    """Tests for obeya snapshot PDF generation."""
    
    def test_generate_obeya_snapshot_pdf(self, service, sample_obeya_data):
        """Test generating an obeya snapshot PDF."""
        user_id = uuid4()
        
        pdf = service.generate_obeya_snapshot_pdf(
            data=sample_obeya_data,
            generated_by=user_id,
        )
        
        assert pdf.id is not None
        assert pdf.document_type == PDFDocumentType.OBEYA_SNAPSHOT
        assert pdf.source_entity_type == "obeya_snapshot"
        assert pdf.status == PDFStatus.COMPLETED


class TestWeekInReviewPDFGeneration(TestPDFGenerationService):
    """Tests for week in review PDF generation."""
    
    def test_generate_week_in_review_pdf(self, service, sample_today_data, sample_obeya_data):
        """Test generating a week in review PDF."""
        user_id = uuid4()
        
        data = WeekInReviewPDFData(
            week_start=date.today() - timedelta(days=7),
            week_end=date.today(),
            generated_by="John Manager",
            today_summary=sample_today_data,
            obeya_summary=sample_obeya_data,
            top_risks=[],
            open_a3s=[],
            key_metrics=[],
            highlights=["Closed 3 deals"],
            lowlights=["Missed delivery target"],
            next_week_priorities=["Focus on quotes"],
        )
        
        pdf = service.generate_week_in_review_pdf(
            data=data,
            generated_by=user_id,
        )
        
        assert pdf.id is not None
        assert pdf.document_type == PDFDocumentType.WEEK_IN_REVIEW
        assert pdf.source_entity_type == "week_in_review"
        assert pdf.status == PDFStatus.COMPLETED


class TestEightDReportPDFGeneration(TestPDFGenerationService):
    """Tests for 8D report PDF generation."""
    
    def test_generate_8d_report_pdf(self, service, sample_8d_data):
        """Test generating an 8D report PDF."""
        user_id = uuid4()
        
        pdf = service.generate_8d_report_pdf(
            data=sample_8d_data,
            generated_by=user_id,
        )
        
        assert pdf.id is not None
        assert pdf.document_type == PDFDocumentType.EIGHT_D_REPORT
        assert pdf.source_entity_type == "capa"
        assert pdf.source_entity_id == sample_8d_data.capa_id
        assert pdf.status == PDFStatus.COMPLETED


class TestPDFRetrieval(TestPDFGenerationService):
    """Tests for PDF retrieval and listing."""
    
    def test_get_generated_pdf(self, service, sample_quote_data):
        """Test getting a generated PDF by ID."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        retrieved = service.get_generated_pdf(pdf.id)
        
        assert retrieved is not None
        assert retrieved.id == pdf.id
        assert retrieved.content_base64 == pdf.content_base64
    
    def test_get_nonexistent_pdf(self, service):
        """Test getting a nonexistent PDF."""
        result = service.get_generated_pdf(uuid4())
        assert result is None
    
    def test_list_generated_pdfs(self, service, sample_quote_data, sample_qualification_data):
        """Test listing generated PDFs."""
        user_id = uuid4()
        
        service.generate_quote_pdf(sample_quote_data, user_id)
        service.generate_qualification_pdf(sample_qualification_data, user_id)
        
        pdfs = service.list_generated_pdfs()
        
        assert len(pdfs) == 2
    
    def test_list_pdfs_by_document_type(self, service, sample_quote_data, sample_qualification_data):
        """Test listing PDFs filtered by document type."""
        user_id = uuid4()
        
        service.generate_quote_pdf(sample_quote_data, user_id)
        service.generate_qualification_pdf(sample_qualification_data, user_id)
        
        quote_pdfs = service.list_generated_pdfs(document_type=PDFDocumentType.QUOTE)
        
        assert len(quote_pdfs) == 1
        assert quote_pdfs[0].document_type == PDFDocumentType.QUOTE
    
    def test_list_pdfs_by_source_entity(self, service, sample_quote_data):
        """Test listing PDFs by source entity."""
        user_id = uuid4()
        
        service.generate_quote_pdf(sample_quote_data, user_id)
        
        pdfs = service.list_generated_pdfs(
            source_entity_type="quote",
            source_entity_id=sample_quote_data.quote_id,
        )
        
        assert len(pdfs) == 1
        assert pdfs[0].source_entity_id == sample_quote_data.quote_id
    
    def test_list_pdfs_by_user(self, service, sample_quote_data):
        """Test listing PDFs by generating user."""
        user_id = uuid4()
        other_user = uuid4()
        
        service.generate_quote_pdf(sample_quote_data, user_id)
        
        # Change quote ID for second PDF
        sample_quote_data.quote_id = uuid4()
        service.generate_quote_pdf(sample_quote_data, other_user)
        
        user_pdfs = service.list_generated_pdfs(generated_by=user_id)
        
        assert len(user_pdfs) == 1
        assert user_pdfs[0].generated_by == user_id
    
    def test_get_pdfs_for_entity(self, service, sample_quote_data):
        """Test getting all PDFs for a specific entity."""
        user_id = uuid4()
        
        # Generate multiple versions
        service.generate_quote_pdf(sample_quote_data, user_id)
        
        sample_quote_data.revision = "B"
        service.generate_quote_pdf(sample_quote_data, user_id)
        
        all_pdfs = service.get_pdfs_for_entity("quote", sample_quote_data.quote_id)
        
        assert len(all_pdfs) == 2
    
    def test_get_pdfs_for_entity_version(self, service, sample_quote_data):
        """Test getting PDFs for a specific entity version."""
        user_id = uuid4()
        
        # Generate revision A
        service.generate_quote_pdf(sample_quote_data, user_id)
        
        # Generate revision B
        sample_quote_data.revision = "B"
        service.generate_quote_pdf(sample_quote_data, user_id)
        
        version_b_pdfs = service.get_pdfs_for_entity(
            "quote",
            sample_quote_data.quote_id,
            version="B",
        )
        
        assert len(version_b_pdfs) == 1
        assert version_b_pdfs[0].source_version == "B"


class TestPDFIntegrity(TestPDFGenerationService):
    """Tests for PDF integrity verification."""
    
    def test_verify_pdf_integrity_valid(self, service, sample_quote_data):
        """Test verifying integrity of a valid PDF."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        is_valid = service.verify_pdf_integrity(pdf.id)
        
        assert is_valid is True
    
    def test_verify_pdf_integrity_nonexistent(self, service):
        """Test verifying integrity of nonexistent PDF."""
        is_valid = service.verify_pdf_integrity(uuid4())
        
        assert is_valid is False
    
    def test_content_hash_is_unique(self, service, sample_quote_data):
        """Test that different content produces different hashes."""
        user_id = uuid4()
        
        pdf1 = service.generate_quote_pdf(sample_quote_data, user_id)
        
        sample_quote_data.quote_id = uuid4()
        sample_quote_data.quote_number = "Q-2026-002"
        pdf2 = service.generate_quote_pdf(sample_quote_data, user_id)
        
        assert pdf1.content_hash != pdf2.content_hash


class TestPDFExpiration(TestPDFGenerationService):
    """Tests for PDF expiration and cleanup."""
    
    def test_pdf_has_expiration(self, service, sample_quote_data):
        """Test that generated PDFs have expiration dates."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        assert pdf.expires_at is not None
        assert pdf.expires_at > _utcnow()
    
    def test_get_expired_pdf_updates_status(self, service, sample_quote_data):
        """Test that getting an expired PDF updates its status."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        # Manually expire the PDF
        pdf.expires_at = _utcnow() - timedelta(days=1)
        
        retrieved = service.get_generated_pdf(pdf.id)
        
        assert retrieved.status == PDFStatus.EXPIRED
    
    def test_list_excludes_expired_by_default(self, service, sample_quote_data):
        """Test that listing excludes expired PDFs by default."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        # Manually expire the PDF
        pdf.expires_at = _utcnow() - timedelta(days=1)
        
        pdfs = service.list_generated_pdfs()
        
        assert len(pdfs) == 0
    
    def test_list_includes_expired_when_requested(self, service, sample_quote_data):
        """Test that listing can include expired PDFs."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        # Manually expire the PDF
        pdf.expires_at = _utcnow() - timedelta(days=1)
        
        pdfs = service.list_generated_pdfs(include_expired=True)
        
        assert len(pdfs) == 1
        assert pdfs[0].status == PDFStatus.EXPIRED
    
    def test_cleanup_expired_pdfs(self, service, sample_quote_data):
        """Test cleaning up expired PDFs."""
        user_id = uuid4()
        
        # Generate multiple PDFs
        pdf1 = service.generate_quote_pdf(sample_quote_data, user_id)
        
        sample_quote_data.quote_id = uuid4()
        pdf2 = service.generate_quote_pdf(sample_quote_data, user_id)
        
        # Expire one of them
        pdf1.expires_at = _utcnow() - timedelta(days=1)
        
        # Cleanup
        removed_count = service.cleanup_expired_pdfs()
        
        assert removed_count == 1
        
        # Check only non-expired remains
        remaining = service.list_generated_pdfs(include_expired=True)
        assert len(remaining) == 1
        assert remaining[0].id == pdf2.id


class TestPDFDeletion(TestPDFGenerationService):
    """Tests for PDF deletion."""
    
    def test_delete_pdf(self, service, sample_quote_data):
        """Test deleting a PDF."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        result = service.delete_pdf(pdf.id)
        
        assert result is True
        assert service.get_generated_pdf(pdf.id) is None
    
    def test_delete_nonexistent_pdf(self, service):
        """Test deleting a nonexistent PDF."""
        result = service.delete_pdf(uuid4())
        assert result is False


class TestGenericPDFGeneration(TestPDFGenerationService):
    """Tests for generic PDF generation."""
    
    def test_generate_pdf_with_custom_template(self, service, sample_quote_data):
        """Test generating a PDF with a custom template."""
        user_id = uuid4()
        
        # Create custom template
        template = service.create_template(
            name="Custom",
            document_type=PDFDocumentType.QUOTE,
            branding=BrandingConfig(primary_color="#000000"),
            watermark=WatermarkConfig(),
            default_options=PDFGenerationOptions(),
            sections=[
                PDFSection(id="custom", title="Custom Section", content={}, order=1),
            ],
            created_by=user_id,
        )
        
        pdf = service.generate_quote_pdf(
            sample_quote_data,
            user_id,
            template_id=template.id,
        )
        
        assert pdf.metadata["template_id"] == str(template.id)
        assert pdf.metadata["template_name"] == "Custom"
    
    def test_generate_pdf_invalid_template_raises(self, service, sample_quote_data):
        """Test that invalid template ID raises error."""
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="Template not found"):
            service.generate_pdf(
                document_type=PDFDocumentType.QUOTE,
                data=sample_quote_data,
                source_entity_type="quote",
                source_entity_id=sample_quote_data.quote_id,
                generated_by=user_id,
                template_id=uuid4(),
            )


class TestSingleton(TestPDFGenerationService):
    """Tests for singleton pattern."""
    
    def test_get_service_returns_singleton(self):
        """Test that get_pdf_generation_service returns singleton."""
        reset_pdf_generation_service()
        
        service1 = get_pdf_generation_service()
        service2 = get_pdf_generation_service()
        
        assert service1 is service2
    
    def test_reset_service_creates_new_instance(self):
        """Test that reset creates a new instance."""
        service1 = get_pdf_generation_service()
        
        reset_pdf_generation_service()
        
        service2 = get_pdf_generation_service()
        
        assert service1 is not service2


class TestEdgeCases(TestPDFGenerationService):
    """Tests for edge cases."""
    
    def test_generate_pdf_with_many_line_items(self, service):
        """Test generating a PDF with many line items."""
        user_id = uuid4()
        
        data = QuotePDFData(
            quote_id=uuid4(),
            quote_number="Q-2026-LARGE",
            revision="A",
            customer_name="Big Customer",
            product_name="Many Items",
            part_number="MULTI-001",
            validity_date=date(2026, 2, 1),
            currency="USD",
            incoterms="EXW",
            payment_terms="Net 30",
            lead_time_days=45,
            moq=100,
            line_items=[{"item": f"Item {i}", "qty": 100, "price": 10.00} for i in range(100)],
            price_breaks=[],
            total_price=100000.00,
            unit_price=10.00,
            assumptions=[],
            conditions=[],
            exclusions=[],
            prepared_by="Sales",
        )
        
        pdf = service.generate_quote_pdf(data, user_id)
        
        assert pdf.page_count >= 7  # 100 items / 15 per page + 2
    
    def test_generate_pdf_with_empty_data(self, service, sample_today_data):
        """Test generating a PDF with minimal/empty data."""
        user_id = uuid4()
        
        # Today snapshot with all empty lists
        pdf = service.generate_today_snapshot_pdf(sample_today_data, user_id)
        
        assert pdf.status == PDFStatus.COMPLETED
        assert pdf.page_count >= 1
    
    def test_template_sections_sorted_by_order(self, service):
        """Test that template sections are maintained in order."""
        templates = service.list_templates(document_type=PDFDocumentType.QUOTE)
        template = templates[0]
        
        orders = [s.order for s in template.sections]
        assert orders == sorted(orders)
    
    def test_pdf_filename_format(self, service, sample_quote_data):
        """Test that PDF filename follows expected format."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        assert pdf.filename.startswith("quote_")
        assert pdf.filename.endswith(".pdf")
        assert str(sample_quote_data.quote_id) in pdf.filename
    
    def test_pdf_metadata_includes_template_info(self, service, sample_quote_data):
        """Test that PDF metadata includes template information."""
        user_id = uuid4()
        pdf = service.generate_quote_pdf(sample_quote_data, user_id)
        
        assert "template_id" in pdf.metadata
        assert "template_name" in pdf.metadata
