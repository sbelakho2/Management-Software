"""
Tests for Label Printing & Barcode Standards Service.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sensei.services.label_printing import (
    # Enums
    LabelSize,
    BarcodeType,
    LabelType,
    PrinterType,
    PrintStatus,
    ScanErrorType,
    # Data Models
    LabelTemplate,
    Printer,
    PrintJob,
    BarcodeValidation,
    GS1Element,
    ScanRecoveryWorkflow,
    # Service
    LabelPrintingService,
    create_label_printing_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def service():
    """Create a fresh service instance."""
    return LabelPrintingService()


@pytest.fixture
def sample_printer(service):
    """Create a sample printer."""
    return service.register_printer(
        name="Zebra ZT411",
        printer_type=PrinterType.THERMAL_TRANSFER,
        connection_string="192.168.1.100:9100",
        supported_sizes=[LabelSize.THERMAL_4X6, LabelSize.THERMAL_4X2],
        supported_barcode_types=[BarcodeType.DATAMATRIX, BarcodeType.GS1_128],
        location_id="shipping-area",
        dpi=300,
    )


@pytest.fixture
def sample_template(service):
    """Get a sample template (using default)."""
    templates = service.get_templates(label_type=LabelType.PART_LABEL)
    return templates[0] if templates else None


# =============================================================================
# TEST: ENUMS
# =============================================================================


class TestEnums:
    """Tests for enumeration types."""
    
    def test_label_size_values(self):
        """Test LabelSize enum values."""
        assert LabelSize.THERMAL_4X6 == "4x6"
        assert LabelSize.THERMAL_4X2 == "4x2"
        assert LabelSize.THERMAL_2X1 == "2x1"
        assert LabelSize.A4_SHEET == "a4"
        assert LabelSize.BUTTERFLY == "butterfly"
    
    def test_barcode_type_values(self):
        """Test BarcodeType enum values."""
        assert BarcodeType.CODE128 == "code128"
        assert BarcodeType.GS1_128 == "gs1-128"
        assert BarcodeType.DATAMATRIX == "datamatrix"
        assert BarcodeType.QR_CODE == "qr_code"
        assert BarcodeType.EAN13 == "ean13"
    
    def test_label_type_values(self):
        """Test LabelType enum values."""
        assert LabelType.PART_LABEL == "part_label"
        assert LabelType.LOT_LABEL == "lot_label"
        assert LabelType.SERIAL_LABEL == "serial_label"
        assert LabelType.SHIPPING_LABEL == "shipping_label"
        assert LabelType.WORK_ORDER_LABEL == "work_order_label"
    
    def test_printer_type_values(self):
        """Test PrinterType enum values."""
        assert PrinterType.THERMAL_DIRECT == "thermal_direct"
        assert PrinterType.THERMAL_TRANSFER == "thermal_transfer"
        assert PrinterType.INKJET == "inkjet"
        assert PrinterType.LASER == "laser"
    
    def test_print_status_values(self):
        """Test PrintStatus enum values."""
        assert PrintStatus.QUEUED == "queued"
        assert PrintStatus.PRINTING == "printing"
        assert PrintStatus.COMPLETED == "completed"
        assert PrintStatus.FAILED == "failed"
    
    def test_scan_error_type_values(self):
        """Test ScanErrorType enum values."""
        assert ScanErrorType.UNRECOGNIZED == "unrecognized"
        assert ScanErrorType.WRONG_TYPE == "wrong_type"
        assert ScanErrorType.DAMAGED == "damaged"
        assert ScanErrorType.EXPIRED == "expired"
        assert ScanErrorType.QUARANTINED == "quarantined"


# =============================================================================
# TEST: DATA MODELS
# =============================================================================


class TestDataModels:
    """Tests for data models."""
    
    def test_label_template_creation(self):
        """Test LabelTemplate creation."""
        template = LabelTemplate(
            id="tpl-001",
            name="Test Template",
            label_type=LabelType.PART_LABEL,
            size=LabelSize.THERMAL_4X2,
            width_mm=101.6,
            height_mm=50.8,
            barcode_type=BarcodeType.DATAMATRIX,
        )
        
        assert template.id == "tpl-001"
        assert template.name == "Test Template"
        assert template.size == LabelSize.THERMAL_4X2
        assert template.is_active is True
    
    def test_printer_creation(self):
        """Test Printer creation."""
        printer = Printer(
            id="prt-001",
            name="Test Printer",
            printer_type=PrinterType.THERMAL_TRANSFER,
            connection_string="192.168.1.100:9100",
            dpi=300,
        )
        
        assert printer.id == "prt-001"
        assert printer.is_online is True
        assert printer.dpi == 300
    
    def test_print_job_creation(self):
        """Test PrintJob creation."""
        job = PrintJob(
            id="job-001",
            printer_id="prt-001",
            template_id="tpl-001",
            label_type=LabelType.PART_LABEL,
            copies=5,
            data={"part_number": "PN-10001"},
        )
        
        assert job.id == "job-001"
        assert job.copies == 5
        assert job.status == PrintStatus.QUEUED
    
    def test_barcode_validation_creation(self):
        """Test BarcodeValidation creation."""
        validation = BarcodeValidation(
            is_valid=True,
            barcode_type=BarcodeType.DATAMATRIX,
            raw_data="PART|PN-10001",
            entity_type="part",
            entity_id="PN-10001",
        )
        
        assert validation.is_valid is True
        assert validation.entity_type == "part"
    
    def test_gs1_element_creation(self):
        """Test GS1Element creation."""
        element = GS1Element(
            ai="10",
            name="BATCH_LOT",
            value="LOT12345",
            length=8,
        )
        
        assert element.ai == "10"
        assert element.name == "BATCH_LOT"
        assert element.value == "LOT12345"


# =============================================================================
# TEST: TEMPLATE MANAGEMENT
# =============================================================================


class TestTemplateManagement:
    """Tests for template management functions."""
    
    def test_default_templates_created(self, service):
        """Test that default templates are created on init."""
        templates = service.get_templates()
        assert len(templates) >= 5  # At least 5 default templates
        
        # Check for specific templates
        shipping = service.get_templates(label_type=LabelType.SHIPPING_LABEL)
        assert len(shipping) >= 1
        
        part = service.get_templates(label_type=LabelType.PART_LABEL)
        assert len(part) >= 1
    
    def test_create_template(self, service):
        """Test creating a custom template."""
        template = service.create_template(
            name="Custom WIP Label",
            label_type=LabelType.WORK_ORDER_LABEL,
            size=LabelSize.THERMAL_4X2,
            width_mm=101.6,
            height_mm=50.8,
            barcode_type=BarcodeType.DATAMATRIX,
            fields=[
                {"name": "work_order", "label": "WO#", "type": "text"},
                {"name": "operation", "label": "OP", "type": "text"},
                {"name": "barcode", "type": "barcode"},
            ],
        )
        
        assert template.id is not None
        assert template.name == "Custom WIP Label"
        assert len(template.fields) == 3
        assert template.is_active is True
    
    def test_create_customer_specific_template(self, service):
        """Test creating customer-specific template."""
        template = service.create_template(
            name="Acme Corp Label",
            label_type=LabelType.SHIPPING_LABEL,
            size=LabelSize.THERMAL_4X6,
            width_mm=101.6,
            height_mm=152.4,
            is_customer_specific=True,
            customer_id="cust-acme-001",
        )
        
        assert template.is_customer_specific is True
        assert template.customer_id == "cust-acme-001"
    
    def test_get_template(self, service, sample_template):
        """Test getting a template by ID."""
        template = service.get_template(sample_template.id)
        assert template is not None
        assert template.id == sample_template.id
    
    def test_get_templates_by_type(self, service):
        """Test filtering templates by type."""
        lot_templates = service.get_templates(label_type=LabelType.LOT_LABEL)
        assert len(lot_templates) >= 1
        for t in lot_templates:
            assert t.label_type == LabelType.LOT_LABEL
    
    def test_get_templates_by_size(self, service):
        """Test filtering templates by size."""
        templates_4x2 = service.get_templates(size=LabelSize.THERMAL_4X2)
        for t in templates_4x2:
            assert t.size == LabelSize.THERMAL_4X2
    
    def test_update_template(self, service, sample_template):
        """Test updating a template."""
        new_fields = [{"name": "updated_field", "type": "text"}]
        
        updated = service.update_template(
            sample_template.id,
            fields=new_fields,
        )
        
        assert updated is not None
        assert len(updated.fields) == 1
        assert updated.fields[0]["name"] == "updated_field"
    
    def test_delete_template(self, service, sample_template):
        """Test soft deleting a template."""
        result = service.delete_template(sample_template.id)
        assert result is True
        
        template = service.get_template(sample_template.id)
        assert template.is_active is False


# =============================================================================
# TEST: PRINTER MANAGEMENT
# =============================================================================


class TestPrinterManagement:
    """Tests for printer management functions."""
    
    def test_register_printer(self, service):
        """Test registering a printer."""
        printer = service.register_printer(
            name="Zebra ZT230",
            printer_type=PrinterType.THERMAL_DIRECT,
            connection_string="192.168.1.101:9100",
            supported_sizes=[LabelSize.THERMAL_4X6],
            location_id="receiving-area",
            dpi=203,
        )
        
        assert printer.id is not None
        assert printer.name == "Zebra ZT230"
        assert printer.is_online is True
        assert printer.dpi == 203
    
    def test_get_printer(self, service, sample_printer):
        """Test getting a printer by ID."""
        printer = service.get_printer(sample_printer.id)
        assert printer is not None
        assert printer.id == sample_printer.id
    
    def test_get_printers(self, service, sample_printer):
        """Test getting all printers."""
        printers = service.get_printers()
        assert len(printers) >= 1
    
    def test_get_printers_by_location(self, service, sample_printer):
        """Test filtering printers by location."""
        printers = service.get_printers(location_id="shipping-area")
        assert len(printers) >= 1
        for p in printers:
            assert p.location_id == "shipping-area"
    
    def test_get_online_printers(self, service, sample_printer):
        """Test filtering online printers."""
        printers = service.get_printers(is_online=True)
        for p in printers:
            assert p.is_online is True
    
    def test_update_printer_status(self, service, sample_printer):
        """Test updating printer status."""
        updated = service.update_printer_status(sample_printer.id, is_online=False)
        
        assert updated is not None
        assert updated.is_online is False
        assert updated.last_heartbeat is not None


# =============================================================================
# TEST: BARCODE GENERATION
# =============================================================================


class TestBarcodeGeneration:
    """Tests for barcode generation functions."""
    
    def test_generate_gs1_128_basic(self, service):
        """Test basic GS1-128 barcode generation."""
        barcode = service.generate_gs1_128(
            gtin="12345678901234",
            lot_number="LOT12345",
        )
        
        assert "01" in barcode  # GTIN AI
        assert "10" in barcode  # LOT AI
        assert "LOT12345" in barcode
    
    def test_generate_gs1_128_with_expiry(self, service):
        """Test GS1-128 with expiry date."""
        expiry = datetime(2025, 12, 31, tzinfo=timezone.utc)
        
        barcode = service.generate_gs1_128(
            gtin="12345678901234",
            expiry_date=expiry,
        )
        
        assert "17" in barcode  # Expiry AI
        assert "251231" in barcode  # YYMMDD
    
    def test_generate_gs1_128_with_serial(self, service):
        """Test GS1-128 with serial number."""
        barcode = service.generate_gs1_128(
            gtin="12345678901234",
            serial_number="SN-001234",
        )
        
        assert "21" in barcode  # Serial AI
        assert "SN-001234" in barcode
    
    def test_generate_gs1_128_sscc(self, service):
        """Test GS1-128 SSCC generation."""
        barcode = service.generate_gs1_128(
            sscc="123456789012345678",
        )
        
        assert "00" in barcode  # SSCC AI
        assert "123456789012345678" in barcode
    
    def test_parse_gs1_128(self, service):
        """Test parsing GS1-128 barcode."""
        fnc1 = chr(29)
        barcode = f"0112345678901234{fnc1}10LOT12345{fnc1}21SN001"
        
        elements = service.parse_gs1_128(barcode)
        
        assert len(elements) >= 2
        ai_dict = {e.ai: e.value for e in elements}
        assert "01" in ai_dict
        assert "10" in ai_dict
    
    def test_generate_datamatrix_data(self, service):
        """Test DataMatrix data generation."""
        data = service.generate_datamatrix_data(
            entity_type="lot",
            entity_id="LOT-12345",
            additional_data={"qty": "100", "uom": "EA"},
        )
        
        assert "LOT|LOT-12345" in data
        assert "qty=100" in data
        assert "uom=EA" in data
    
    def test_parse_datamatrix(self, service):
        """Test parsing DataMatrix data."""
        data = "LOT|LOT-12345|qty=100|uom=EA"
        
        parsed = service.parse_datamatrix(data)
        
        assert parsed["entity_type"] == "lot"
        assert parsed["entity_id"] == "LOT-12345"
        assert parsed["additional"]["qty"] == "100"
    
    def test_generate_customer_barcode(self, service):
        """Test customer-specific barcode format."""
        data = service.generate_customer_barcode(
            customer_id="cust-001",
            format_spec="ACME-{part_number}-{quantity:4}",
            data={"part_number": "PN-100", "quantity": "50"},
        )
        
        assert data == "ACME-PN-100-0050"
    
    def test_register_barcode(self, service):
        """Test registering a barcode."""
        reg = service.register_barcode(
            barcode_data="LOT|LOT-12345",
            entity_type="lot",
            entity_id="lot-uuid-001",
            barcode_type=BarcodeType.DATAMATRIX,
            metadata={"part_number": "PN-10001"},
        )
        
        assert reg["barcode_data"] == "LOT|LOT-12345"
        assert reg["entity_type"] == "lot"
        assert reg["registered_at"] is not None


# =============================================================================
# TEST: PRINT QUEUE MANAGEMENT
# =============================================================================


class TestPrintQueueManagement:
    """Tests for print queue management functions."""
    
    def test_queue_print_job(self, service, sample_printer, sample_template):
        """Test queuing a print job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001", "description": "Test Part"},
            copies=3,
            requested_by="user-001",
        )
        
        assert job.id is not None
        assert job.status == PrintStatus.QUEUED
        assert job.copies == 3
        assert job.barcode_data is not None
    
    def test_queue_print_job_invalid_printer(self, service, sample_template):
        """Test queuing with invalid printer."""
        with pytest.raises(ValueError, match="Printer not found"):
            service.queue_print_job(
                printer_id="non-existent",
                template_id=sample_template.id,
                data={},
            )
    
    def test_queue_print_job_invalid_template(self, service, sample_printer):
        """Test queuing with invalid template."""
        with pytest.raises(ValueError, match="Template not found"):
            service.queue_print_job(
                printer_id=sample_printer.id,
                template_id="non-existent",
                data={},
            )
    
    def test_get_print_job(self, service, sample_printer, sample_template):
        """Test getting a print job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001"},
        )
        
        retrieved = service.get_print_job(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id
    
    def test_get_pending_jobs(self, service, sample_printer, sample_template):
        """Test getting pending jobs."""
        # Queue several jobs
        for i in range(3):
            service.queue_print_job(
                printer_id=sample_printer.id,
                template_id=sample_template.id,
                data={"part_number": f"PN-{i}"},
            )
        
        pending = service.get_pending_jobs()
        assert len(pending) >= 3
    
    def test_pending_jobs_sorted_by_priority(self, service, sample_printer, sample_template):
        """Test that pending jobs are sorted by priority."""
        # Queue jobs with different priorities
        low = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "LOW"},
            priority=0,
        )
        high = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "HIGH"},
            priority=10,
        )
        
        pending = service.get_pending_jobs()
        
        # High priority should come first
        high_idx = next(i for i, j in enumerate(pending) if j.id == high.id)
        low_idx = next(i for i, j in enumerate(pending) if j.id == low.id)
        assert high_idx < low_idx
    
    def test_start_print_job(self, service, sample_printer, sample_template):
        """Test starting a print job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001"},
        )
        
        started = service.start_print_job(job.id)
        
        assert started.status == PrintStatus.PRINTING
        assert started.started_at is not None
    
    def test_complete_print_job(self, service, sample_printer, sample_template):
        """Test completing a print job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001"},
        )
        service.start_print_job(job.id)
        
        completed = service.complete_print_job(job.id)
        
        assert completed.status == PrintStatus.COMPLETED
        assert completed.completed_at is not None
    
    def test_fail_print_job(self, service, sample_printer, sample_template):
        """Test failing a print job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001"},
        )
        
        failed = service.fail_print_job(job.id, "Printer offline")
        
        assert failed.status == PrintStatus.FAILED
        assert failed.error_message == "Printer offline"
    
    def test_cancel_print_job(self, service, sample_printer, sample_template):
        """Test cancelling a print job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001"},
        )
        
        cancelled = service.cancel_print_job(job.id)
        
        assert cancelled.status == PrintStatus.CANCELLED
    
    def test_requeue_failed_job(self, service, sample_printer, sample_template):
        """Test requeuing a failed job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-10001"},
        )
        service.fail_print_job(job.id, "Temporary error")
        
        requeued = service.requeue_job(job.id)
        
        assert requeued.status == PrintStatus.QUEUED
        assert requeued.error_message is None


# =============================================================================
# TEST: SCAN VALIDATION & ERROR HANDLING
# =============================================================================


class TestScanValidation:
    """Tests for scan validation and error handling."""
    
    def test_validate_registered_barcode(self, service):
        """Test validating a registered barcode."""
        # Register barcode
        service.register_barcode(
            barcode_data="LOT|LOT-12345",
            entity_type="lot",
            entity_id="lot-uuid-001",
            barcode_type=BarcodeType.DATAMATRIX,
        )
        
        result = service.validate_barcode("LOT|LOT-12345")
        
        assert result.is_valid is True
        assert result.entity_type == "lot"
        assert result.entity_id == "lot-uuid-001"
    
    def test_validate_gs1_128_barcode(self, service):
        """Test validating GS1-128 barcode."""
        fnc1 = chr(29)
        barcode = f"0112345678901234{fnc1}10LOT12345{fnc1}21SN001"
        
        result = service.validate_barcode(barcode)
        
        assert result.barcode_type == BarcodeType.GS1_128
        assert "BATCH_LOT" in result.parsed_data or "GTIN" in result.parsed_data
    
    def test_validate_datamatrix_barcode(self, service):
        """Test validating DataMatrix barcode."""
        barcode = "LOT|LOT-12345|qty=100"
        
        result = service.validate_barcode(barcode)
        
        assert result.barcode_type == BarcodeType.DATAMATRIX
        assert result.entity_type == "lot"
        assert result.entity_id == "LOT-12345"
    
    def test_validate_wrong_type(self, service):
        """Test validation with wrong expected type."""
        barcode = "LOT|LOT-12345"  # DataMatrix format
        
        result = service.validate_barcode(barcode, expected_type=BarcodeType.GS1_128)
        
        assert result.is_valid is False
        assert result.error_type == ScanErrorType.WRONG_TYPE
        assert len(result.recovery_actions) > 0
    
    def test_validate_unrecognized_barcode(self, service):
        """Test validation of unrecognized barcode."""
        result = service.validate_barcode("RANDOM_STRING_123")
        
        assert result.is_valid is False
        assert result.error_type == ScanErrorType.UNRECOGNIZED
        assert len(result.recovery_actions) > 0
    
    def test_recovery_workflow_exists(self, service):
        """Test that recovery workflows are initialized."""
        workflow = service.get_recovery_workflow(ScanErrorType.UNRECOGNIZED)
        
        assert workflow is not None
        assert len(workflow.workflow_steps) > 0
    
    def test_quarantine_recovery_requires_supervisor(self, service):
        """Test that quarantine recovery requires supervisor."""
        workflow = service.get_recovery_workflow(ScanErrorType.QUARANTINED)
        
        assert workflow is not None
        assert workflow.requires_supervisor is True
    
    def test_create_custom_recovery_workflow(self, service):
        """Test creating custom recovery workflow."""
        workflow = service.create_recovery_workflow(
            error_type=ScanErrorType.ALREADY_CONSUMED,
            workflow_steps=[
                {"step": 1, "action": "verify", "instruction": "Verify item status"},
                {"step": 2, "action": "escalate", "instruction": "Contact supervisor"},
            ],
            requires_supervisor=True,
        )
        
        assert workflow.id is not None
        assert len(workflow.workflow_steps) == 2
        assert workflow.requires_supervisor is True


# =============================================================================
# TEST: LABEL GENERATION
# =============================================================================


class TestLabelGeneration:
    """Tests for label generation functions."""
    
    def test_generate_zpl(self, service, sample_template):
        """Test ZPL generation."""
        zpl = service.generate_label_content(
            template_id=sample_template.id,
            data={
                "part_number": "PN-10001",
                "description": "Test Part Description",
            },
            output_format="zpl",
        )
        
        assert "^XA" in zpl  # Start format
        assert "^XZ" in zpl  # End format
        assert "PN-10001" in zpl
    
    def test_generate_html(self, service, sample_template):
        """Test HTML generation."""
        html = service.generate_label_content(
            template_id=sample_template.id,
            data={
                "part_number": "PN-10001",
                "description": "Test Part Description",
            },
            output_format="html",
        )
        
        assert "<!DOCTYPE html>" in html
        assert "PN-10001" in html
    
    def test_generate_with_custom_zpl_layout(self, service):
        """Test generation with custom ZPL layout."""
        template = service.create_template(
            name="Custom ZPL",
            label_type=LabelType.PART_LABEL,
            size=LabelSize.THERMAL_4X2,
            width_mm=101.6,
            height_mm=50.8,
            layout_zpl="^XA^FO10,10^A0N,30,30^FD${part_number}^FS^XZ",
        )
        
        zpl = service.generate_label_content(
            template_id=template.id,
            data={"part_number": "CUSTOM-001"},
            output_format="zpl",
        )
        
        assert "CUSTOM-001" in zpl
    
    def test_generate_invalid_template(self, service):
        """Test generation with invalid template."""
        with pytest.raises(ValueError, match="Template not found"):
            service.generate_label_content(
                template_id="non-existent",
                data={},
            )
    
    def test_generate_unsupported_format(self, service, sample_template):
        """Test generation with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            service.generate_label_content(
                template_id=sample_template.id,
                data={},
                output_format="pdf",  # Not implemented
            )


# =============================================================================
# TEST: STATISTICS
# =============================================================================


class TestStatistics:
    """Tests for statistics functions."""
    
    def test_get_statistics(self, service, sample_printer, sample_template):
        """Test getting service statistics."""
        # Create some jobs
        service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-1"},
        )
        
        stats = service.get_statistics()
        
        assert stats["total_templates"] >= 5  # Default templates
        assert stats["total_printers"] >= 1
        assert stats["total_jobs"] >= 1
        assert "jobs_by_status" in stats
        assert stats["recovery_workflows"] >= 4  # Default workflows


# =============================================================================
# TEST: FACTORY FUNCTION
# =============================================================================


class TestFactoryFunction:
    """Tests for factory function."""
    
    def test_create_label_printing_service(self):
        """Test factory function creates service."""
        service = create_label_printing_service()
        
        assert service is not None
        assert isinstance(service, LabelPrintingService)
        
        # Default templates should be created
        templates = service.get_templates()
        assert len(templates) >= 5
    
    def test_factory_creates_fresh_instance(self):
        """Test factory creates independent instances."""
        service1 = create_label_printing_service()
        service2 = create_label_printing_service()
        
        # Register printer in service1
        service1.register_printer(
            name="Printer 1",
            printer_type=PrinterType.THERMAL_DIRECT,
            connection_string="192.168.1.1:9100",
        )
        
        # Service2 should not have this printer
        printers1 = service1.get_printers()
        printers2 = service2.get_printers()
        
        assert len(printers1) == 1
        assert len(printers2) == 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_get_nonexistent_template(self, service):
        """Test getting non-existent template."""
        result = service.get_template("non-existent")
        assert result is None
    
    def test_get_nonexistent_printer(self, service):
        """Test getting non-existent printer."""
        result = service.get_printer("non-existent")
        assert result is None
    
    def test_update_nonexistent_template(self, service):
        """Test updating non-existent template."""
        result = service.update_template("non-existent", fields=[])
        assert result is None
    
    def test_delete_nonexistent_template(self, service):
        """Test deleting non-existent template."""
        result = service.delete_template("non-existent")
        assert result is False
    
    def test_update_nonexistent_printer(self, service):
        """Test updating non-existent printer."""
        result = service.update_printer_status("non-existent", is_online=True)
        assert result is None
    
    def test_get_nonexistent_print_job(self, service):
        """Test getting non-existent print job."""
        result = service.get_print_job("non-existent")
        assert result is None
    
    def test_start_nonexistent_job(self, service):
        """Test starting non-existent job."""
        result = service.start_print_job("non-existent")
        assert result is None
    
    def test_cancel_completed_job(self, service, sample_printer, sample_template):
        """Test cancelling a completed job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-1"},
        )
        service.complete_print_job(job.id)
        
        result = service.cancel_print_job(job.id)
        assert result is None  # Cannot cancel completed job
    
    def test_requeue_non_failed_job(self, service, sample_printer, sample_template):
        """Test requeuing a non-failed job."""
        job = service.queue_print_job(
            printer_id=sample_printer.id,
            template_id=sample_template.id,
            data={"part_number": "PN-1"},
        )
        
        result = service.requeue_job(job.id)  # Job is QUEUED, not FAILED
        assert result is None
    
    def test_barcode_detection_empty_string(self, service):
        """Test barcode validation with empty string."""
        result = service.validate_barcode("")
        assert result.is_valid is False
    
    def test_parse_empty_gs1_128(self, service):
        """Test parsing empty GS1-128."""
        elements = service.parse_gs1_128("")
        assert len(elements) == 0
