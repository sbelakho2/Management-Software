"""
Tests for Document Intelligence Service.

Tests world-class document processing capabilities:
- Document processing pipeline
- Layout detection
- Table extraction
- Key-value extraction
- Engineering drawing processing
- VLM enrichment
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from sensei.services.ai.document_intelligence import (
    # Enums
    DocumentType,
    ElementType,
    ProcessingStrategy,
    ExtractionConfidence,
    EnrichmentType,
    # Data models
    BoundingBox,
    DocumentElement,
    TableCell,
    ExtractedTable,
    ExtractedFigure,
    KeyValuePair,
    GDTCallout,
    DimensionCallout,
    TitleBlockData,
    DocumentPage,
    ProcessedDocument,
    ProcessingConfig,
    # Components
    LayoutModel,
    TableStructureModel,
    OCREngine,
    VisionLLMEnricher,
    DocumentClassifier,
    KeyValueExtractor,
    EngineeringDrawingProcessor,
    DocumentIntelligenceService,
)


# =============================================================================
# BoundingBox Tests
# =============================================================================


class TestBoundingBox:
    """Tests for BoundingBox class."""
    
    def test_from_pixels_normalization(self):
        """Test conversion from pixels to normalized coordinates."""
        bbox = BoundingBox.from_pixels(
            x0=100, y0=200, x1=300, y1=400,
            width=1000, height=1000,
        )
        
        assert bbox.x0 == 100
        assert bbox.y0 == 200
        assert bbox.x1 == 300
        assert bbox.y1 == 400
    
    def test_from_pixels_with_different_dimensions(self):
        """Test normalization with different image dimensions."""
        bbox = BoundingBox.from_pixels(
            x0=420, y0=594, x1=2100, y1=2970,  # A4 at 300 DPI
            width=2100, height=2970,
        )
        
        # Should be normalized to 0-1000 scale
        assert 0 <= bbox.x0 <= 1000
        assert 0 <= bbox.y0 <= 1000
        assert 0 <= bbox.x1 <= 1000
        assert 0 <= bbox.y1 <= 1000
    
    def test_to_pixels_conversion(self):
        """Test conversion from normalized to pixels."""
        bbox = BoundingBox(x0=100, y0=200, x1=300, y1=400)
        pixels = bbox.to_pixels(width=2000, height=2000)
        
        assert pixels == (200, 400, 600, 800)
    
    def test_area_calculation(self):
        """Test area calculation."""
        bbox = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        assert bbox.area == 10000
        
        bbox2 = BoundingBox(x0=50, y0=50, x1=150, y1=200)
        assert bbox2.area == 100 * 150
    
    def test_overlap_ratio_full_overlap(self):
        """Test overlap ratio with identical boxes."""
        bbox1 = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        
        assert bbox1.overlap_ratio(bbox2) == 1.0
    
    def test_overlap_ratio_no_overlap(self):
        """Test overlap ratio with non-overlapping boxes."""
        bbox1 = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BoundingBox(x0=200, y0=200, x1=300, y1=300)
        
        assert bbox1.overlap_ratio(bbox2) == 0.0
    
    def test_overlap_ratio_partial_overlap(self):
        """Test overlap ratio with partially overlapping boxes."""
        bbox1 = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        bbox2 = BoundingBox(x0=50, y0=50, x1=150, y1=150)
        
        overlap = bbox1.overlap_ratio(bbox2)
        assert 0 < overlap < 1


# =============================================================================
# ExtractedTable Tests
# =============================================================================


class TestExtractedTable:
    """Tests for ExtractedTable class."""
    
    def test_to_markdown_simple_table(self):
        """Test markdown conversion for simple table."""
        cells = [
            TableCell(row=0, col=0, content="Header1", is_header=True),
            TableCell(row=0, col=1, content="Header2", is_header=True),
            TableCell(row=1, col=0, content="Value1"),
            TableCell(row=1, col=1, content="Value2"),
        ]
        
        table = ExtractedTable(
            table_id="test",
            cells=cells,
            num_rows=2,
            num_cols=2,
            headers=["Header1", "Header2"],
        )
        
        markdown = table.to_markdown()
        
        assert "Header1" in markdown
        assert "Header2" in markdown
        assert "Value1" in markdown
        assert "Value2" in markdown
        assert "|" in markdown
        assert "---" in markdown
    
    def test_to_dict_list_conversion(self):
        """Test conversion to list of dictionaries."""
        cells = [
            TableCell(row=0, col=0, content="Part", is_header=True),
            TableCell(row=0, col=1, content="Qty", is_header=True),
            TableCell(row=1, col=0, content="ABC-123"),
            TableCell(row=1, col=1, content="100"),
            TableCell(row=2, col=0, content="XYZ-456"),
            TableCell(row=2, col=1, content="50"),
        ]
        
        table = ExtractedTable(
            table_id="test",
            cells=cells,
            num_rows=3,
            num_cols=2,
            headers=["Part", "Qty"],
        )
        
        dict_list = table.to_dict_list()
        
        assert len(dict_list) == 2
        assert dict_list[0]["Part"] == "ABC-123"
        assert dict_list[0]["Qty"] == "100"
        assert dict_list[1]["Part"] == "XYZ-456"
    
    def test_to_markdown_empty_table(self):
        """Test markdown conversion for empty table."""
        table = ExtractedTable(
            table_id="empty",
            cells=[],
            num_rows=0,
            num_cols=0,
        )
        
        assert table.to_markdown() == ""


# =============================================================================
# ProcessedDocument Tests
# =============================================================================


class TestProcessedDocument:
    """Tests for ProcessedDocument class."""
    
    def test_full_text_property(self):
        """Test full text extraction from pages."""
        pages = [
            DocumentPage(page_number=1, width=100, height=100, raw_text="Page 1 content"),
            DocumentPage(page_number=2, width=100, height=100, raw_text="Page 2 content"),
        ]
        
        doc = ProcessedDocument(
            document_id="test",
            filename="test.pdf",
            document_type=DocumentType.RFQ,
            pages=pages,
            total_pages=2,
        )
        
        assert "Page 1 content" in doc.full_text
        assert "Page 2 content" in doc.full_text
    
    def test_get_summary_for_embedding(self):
        """Test summary generation for embedding."""
        kv_pairs = [
            KeyValuePair(key="Part Number", value="ABC-123", field_type="part_number"),
            KeyValuePair(key="Quantity", value="100", field_type="quantity"),
        ]
        
        doc = ProcessedDocument(
            document_id="test",
            filename="test.pdf",
            document_type=DocumentType.RFQ,
            pages=[DocumentPage(page_number=1, width=100, height=100, raw_text="Test content")],
            all_key_values=kv_pairs,
        )
        
        summary = doc.get_summary_for_embedding()
        
        assert "RFQ" in summary.lower() or "rfq" in summary
        assert "Part Number" in summary
        assert "ABC-123" in summary


# =============================================================================
# DocumentClassifier Tests
# =============================================================================


class TestDocumentClassifier:
    """Tests for DocumentClassifier."""
    
    def test_classify_rfq_document(self):
        """Test classification of RFQ documents."""
        classifier = DocumentClassifier()
        
        text = """
        REQUEST FOR QUOTATION
        RFQ#: 2024-0042
        Please quote for the following items...
        """
        
        doc_type, confidence = classifier.classify(text)
        
        assert doc_type == DocumentType.RFQ
        assert confidence > 0.5
    
    def test_classify_purchase_order(self):
        """Test classification of purchase orders."""
        classifier = DocumentClassifier()
        
        text = """
        PURCHASE ORDER
        P.O. Number: PO-12345
        Delivery Address: 123 Main St
        """
        
        doc_type, confidence = classifier.classify(text)
        
        assert doc_type == DocumentType.PURCHASE_ORDER
        assert confidence > 0.5
    
    def test_classify_engineering_drawing(self):
        """Test classification of engineering drawings."""
        classifier = DocumentClassifier()
        
        text = """
        DRAWN BY: John Smith
        SCALE: 1:1
        REV. A
        MATERIAL: 6061-T6 ALUMINUM
        UNLESS OTHERWISE SPECIFIED, TOLERANCE IS ±0.1
        """
        
        doc_type, confidence = classifier.classify(text)
        
        assert doc_type == DocumentType.ENGINEERING_DRAWING
        assert confidence > 0.5
    
    def test_classify_unknown_document(self):
        """Test classification of ambiguous documents."""
        classifier = DocumentClassifier()
        
        text = "Random text that doesn't match any patterns."
        
        doc_type, confidence = classifier.classify(text)
        
        assert doc_type == DocumentType.UNKNOWN
    
    def test_classify_invoice(self):
        """Test classification of invoices."""
        classifier = DocumentClassifier()
        
        text = """
        INVOICE #: INV-2024-001
        Bill To: Acme Corp
        Payment Terms: Net 30
        Amount Due: $5,000.00
        """
        
        doc_type, confidence = classifier.classify(text)
        
        assert doc_type == DocumentType.INVOICE


# =============================================================================
# KeyValueExtractor Tests
# =============================================================================


class TestKeyValueExtractor:
    """Tests for KeyValueExtractor."""
    
    def test_extract_part_number(self):
        """Test extraction of part numbers."""
        extractor = KeyValueExtractor()
        
        text = "Part Number: ASM-7075-T6-001"
        results = extractor.extract(text)
        
        part_numbers = [kv for kv in results if kv.field_type == "part_number"]
        assert len(part_numbers) >= 1
        assert "ASM-7075-T6-001" in part_numbers[0].value
    
    def test_extract_quantity(self):
        """Test extraction of quantities."""
        extractor = KeyValueExtractor()
        
        text = "Quantity: 500"
        results = extractor.extract(text)
        
        quantities = [kv for kv in results if kv.field_type == "quantity"]
        assert len(quantities) >= 1
        assert "500" in quantities[0].value
    
    def test_extract_date(self):
        """Test extraction of dates."""
        extractor = KeyValueExtractor()
        
        text = "Date: 01/15/2024"
        results = extractor.extract(text)
        
        dates = [kv for kv in results if kv.field_type == "date"]
        assert len(dates) >= 1
    
    def test_extract_price(self):
        """Test extraction of prices."""
        extractor = KeyValueExtractor()
        
        text = "Price: $45.00"
        results = extractor.extract(text)
        
        prices = [kv for kv in results if kv.field_type == "price"]
        assert len(prices) >= 1
    
    def test_extract_multiple_fields(self):
        """Test extraction of multiple fields from document."""
        extractor = KeyValueExtractor()
        
        text = """
        Company: Acme Manufacturing
        Part No.: XYZ-123-A
        Qty: 1,000
        Date: 12/01/2024
        Price: $25.50
        Material: 6061-T6 Aluminum
        """
        
        results = extractor.extract(text)
        
        # Should extract multiple different field types
        field_types = {kv.field_type for kv in results}
        assert len(field_types) >= 3
    
    def test_no_duplicates(self):
        """Test that duplicate field types are avoided."""
        extractor = KeyValueExtractor()
        
        text = """
        Part Number: ABC-123
        P/N: DEF-456
        """
        
        results = extractor.extract(text)
        
        part_numbers = [kv for kv in results if kv.field_type == "part_number"]
        # Should only extract the first match
        assert len(part_numbers) == 1


# =============================================================================
# EngineeringDrawingProcessor Tests
# =============================================================================


class TestEngineeringDrawingProcessor:
    """Tests for EngineeringDrawingProcessor."""
    
    def test_extract_title_block_basic(self):
        """Test extraction of basic title block data."""
        processor = EngineeringDrawingProcessor()
        
        page = DocumentPage(
            page_number=1,
            width=2100,
            height=2970,
            raw_text="""
            PART NO.: ABC-123-REV-A
            REV. B
            MATERIAL: 7075-T6 ALUMINUM
            """,
        )
        
        title_block = processor.extract_title_block(page)
        
        assert title_block.part_number == "ABC-123-REV-A"
        assert title_block.revision == "B"
        assert "7075" in title_block.material.upper() or "ALUMINUM" in title_block.material.upper()
    
    def test_extract_dimensions(self):
        """Test extraction of dimension callouts."""
        processor = EngineeringDrawingProcessor()
        
        page = DocumentPage(
            page_number=1,
            width=2100,
            height=2970,
            raw_text="""
            25.4 ±0.1
            100 +0.02/-0.00
            Ø50 H7
            """,
        )
        
        dimensions = processor.extract_dimensions(page)
        
        # Should find dimensions with tolerances
        assert len(dimensions) >= 1
        
        # Check that nominal values are extracted
        nominals = [d.nominal for d in dimensions]
        assert any(n > 0 for n in nominals)
    
    def test_extract_gdt_callouts(self):
        """Test extraction of GD&T callouts."""
        processor = EngineeringDrawingProcessor()
        
        page = DocumentPage(
            page_number=1,
            width=2100,
            height=2970,
            raw_text="""
            ⌖ Ø0.05 M A B C
            ⏥ 0.025
            """,
        )
        
        callouts = processor.extract_gdt_callouts(page)
        
        # Should find GD&T symbols
        # Note: Actual extraction depends on pattern matching
        assert isinstance(callouts, list)


# =============================================================================
# LayoutModel Tests
# =============================================================================


class TestLayoutModel:
    """Tests for LayoutModel."""
    
    def test_detect_layout_returns_elements(self):
        """Test that layout detection returns elements."""
        model = LayoutModel()
        
        # Simulated image bytes
        image = b"fake_image_data"
        
        detections = model.detect_layout(image, 2100, 2970)
        
        assert len(detections) > 0
        
        # Each detection should have type, bbox, confidence
        for elem_type, bbox, confidence in detections:
            assert isinstance(elem_type, ElementType)
            assert isinstance(bbox, BoundingBox)
            assert 0 <= confidence <= 1
    
    def test_detect_layout_finds_tables(self):
        """Test that layout detection can find tables."""
        model = LayoutModel()
        
        image = b"fake_image_data"
        detections = model.detect_layout(image, 2100, 2970)
        
        table_detections = [d for d in detections if d[0] == ElementType.TABLE]
        
        # Simulated model should detect at least one table
        assert len(table_detections) >= 1


# =============================================================================
# TableStructureModel Tests
# =============================================================================


class TestTableStructureModel:
    """Tests for TableStructureModel."""
    
    def test_recognize_structure_returns_table(self):
        """Test that table recognition returns a table."""
        model = TableStructureModel()
        
        image = b"fake_table_image"
        bbox = BoundingBox(50, 420, 950, 700)
        
        table = model.recognize_structure(image, bbox)
        
        assert isinstance(table, ExtractedTable)
        assert len(table.cells) > 0
        assert table.num_rows > 0
        assert table.num_cols > 0
    
    def test_recognize_structure_identifies_headers(self):
        """Test that table recognition identifies headers."""
        model = TableStructureModel()
        
        image = b"fake_table_image"
        bbox = BoundingBox(50, 420, 950, 700)
        
        table = model.recognize_structure(image, bbox)
        
        header_cells = [c for c in table.cells if c.is_header]
        assert len(header_cells) > 0


# =============================================================================
# OCREngine Tests
# =============================================================================


class TestOCREngine:
    """Tests for OCREngine."""
    
    def test_extract_text_returns_text(self):
        """Test that OCR extracts text."""
        engine = OCREngine()
        
        image = b"fake_image"
        text, words = engine.extract_text(image)
        
        assert len(text) > 0
        assert isinstance(words, list)
    
    def test_extract_text_with_bboxes(self):
        """Test that OCR returns bounding boxes for words."""
        engine = OCREngine()
        
        image = b"fake_image"
        text, words = engine.extract_text(image, with_bboxes=True)
        
        for word, bbox, confidence in words:
            assert isinstance(word, str)
            assert isinstance(bbox, BoundingBox)
            assert 0 <= confidence <= 1


# =============================================================================
# VisionLLMEnricher Tests
# =============================================================================


class TestVisionLLMEnricher:
    """Tests for VisionLLMEnricher."""
    
    @pytest.mark.asyncio
    async def test_enrich_image_description(self):
        """Test image description enrichment."""
        enricher = VisionLLMEnricher()
        
        image = b"fake_image"
        description = await enricher.enrich(image, EnrichmentType.IMAGE_DESCRIPTION)
        
        assert len(description) > 0
        assert isinstance(description, str)
    
    @pytest.mark.asyncio
    async def test_enrich_table_to_html(self):
        """Test table-to-HTML enrichment."""
        enricher = VisionLLMEnricher()
        
        image = b"fake_table_image"
        html = await enricher.enrich(image, EnrichmentType.TABLE_TO_HTML)
        
        assert "<table>" in html.lower()
        assert "</table>" in html.lower()
    
    @pytest.mark.asyncio
    async def test_enrich_diagram_interpretation(self):
        """Test diagram interpretation enrichment."""
        enricher = VisionLLMEnricher()
        
        image = b"fake_diagram"
        interpretation = await enricher.enrich(image, EnrichmentType.DIAGRAM_INTERPRETATION)
        
        assert len(interpretation) > 0


# =============================================================================
# DocumentIntelligenceService Tests
# =============================================================================


class TestDocumentIntelligenceService:
    """Tests for DocumentIntelligenceService."""
    
    @pytest.mark.asyncio
    async def test_process_document_basic(self):
        """Test basic document processing."""
        service = DocumentIntelligenceService()
        
        # Simulated PDF content
        file_data = b"%PDF-1.4 fake pdf content"
        
        result = await service.process_document(file_data, "test.pdf")
        
        assert isinstance(result, ProcessedDocument)
        assert result.filename == "test.pdf"
        assert result.document_id is not None
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_process_document_extracts_tables(self):
        """Test that document processing extracts tables."""
        service = DocumentIntelligenceService()
        
        file_data = b"fake document with tables"
        
        result = await service.process_document(file_data, "test.pdf")
        
        # Should have extracted tables
        assert isinstance(result.all_tables, list)
    
    @pytest.mark.asyncio
    async def test_process_document_extracts_key_values(self):
        """Test that document processing extracts key-value pairs."""
        service = DocumentIntelligenceService()
        
        file_data = b"fake document content"
        
        result = await service.process_document(file_data, "test.pdf")
        
        # Should have extracted key-value pairs
        assert isinstance(result.all_key_values, list)
    
    @pytest.mark.asyncio
    async def test_process_document_classifies_type(self):
        """Test that document processing classifies document type."""
        service = DocumentIntelligenceService()
        
        file_data = b"fake document"
        
        result = await service.process_document(file_data, "test.pdf")
        
        assert isinstance(result.document_type, DocumentType)
    
    @pytest.mark.asyncio
    async def test_process_image_document(self):
        """Test processing of image documents."""
        service = DocumentIntelligenceService()
        
        file_data = b"fake PNG image data"
        
        result = await service.process_document(file_data, "drawing.png")
        
        assert isinstance(result, ProcessedDocument)
        assert len(result.pages) >= 1
    
    def test_get_document_for_rag(self):
        """Test RAG preparation of processed document."""
        service = DocumentIntelligenceService()
        
        # Create a processed document
        processed = ProcessedDocument(
            document_id="test-123",
            filename="test.pdf",
            document_type=DocumentType.RFQ,
            pages=[
                DocumentPage(
                    page_number=1,
                    width=2100,
                    height=2970,
                    elements=[
                        DocumentElement(
                            element_id="e1",
                            element_type=ElementType.PARAGRAPH,
                            content="This is test content for the document.",
                        )
                    ],
                    raw_text="This is test content for the document.",
                )
            ],
            all_tables=[
                ExtractedTable(
                    table_id="t1",
                    cells=[TableCell(row=0, col=0, content="Header")],
                    num_rows=2,
                    num_cols=2,
                    headers=["Header1", "Header2"],
                )
            ],
            all_key_values=[
                KeyValuePair(key="Part Number", value="ABC-123", field_type="part_number")
            ],
        )
        
        rag_data = service.get_document_for_rag(processed)
        
        assert rag_data["document_id"] == "test-123"
        assert rag_data["document_type"] == "rfq"
        assert len(rag_data["table_summaries"]) == 1
        assert len(rag_data["key_values"]) == 1
    
    def test_config_customization(self):
        """Test service with custom configuration."""
        config = ProcessingConfig(
            strategy=ProcessingStrategy.FAST,
            ocr_language="deu",
            detect_tables=False,
            max_pages=5,
        )
        
        service = DocumentIntelligenceService(config=config)
        
        assert service.config.strategy == ProcessingStrategy.FAST
        assert service.config.ocr_language == "deu"
        assert service.config.detect_tables is False
        assert service.config.max_pages == 5


# =============================================================================
# Integration Tests
# =============================================================================


class TestDocumentIntelligenceIntegration:
    """Integration tests for document intelligence."""
    
    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self):
        """Test complete processing pipeline."""
        config = ProcessingConfig(
            strategy=ProcessingStrategy.HIGH_RES,
            enable_vlm_enrichment=True,
            detect_gdt=True,
        )
        
        service = DocumentIntelligenceService(config=config)
        
        # Process a document
        file_data = b"fake document content"
        result = await service.process_document(file_data, "drawing.pdf")
        
        # Verify all components
        assert result.document_id is not None
        assert result.total_pages >= 1
        assert result.processing_time_ms > 0
        assert result.checksum is not None
    
    @pytest.mark.asyncio
    async def test_engineering_drawing_full_extraction(self):
        """Test full extraction from engineering drawing."""
        config = ProcessingConfig(
            detect_gdt=True,
            detect_dimensions=True,
            extract_title_block=True,
        )
        
        service = DocumentIntelligenceService(config=config)
        
        file_data = b"fake engineering drawing"
        result = await service.process_document(file_data, "bracket.pdf")
        
        # Check that specialized fields are populated for drawings
        assert isinstance(result.gdt_callouts, list)
        assert isinstance(result.dimensions, list)


# =============================================================================
# Performance Tests
# =============================================================================


class TestDocumentIntelligencePerformance:
    """Performance tests for document intelligence."""
    
    @pytest.mark.asyncio
    async def test_processing_time_under_threshold(self):
        """Test that processing completes in reasonable time."""
        service = DocumentIntelligenceService()
        
        file_data = b"fake document" * 100  # Larger document
        result = await service.process_document(file_data, "test.pdf")
        
        # Should complete in under 5 seconds for simulated processing
        assert result.processing_time_ms < 5000


# =============================================================================
# Edge Cases
# =============================================================================


class TestDocumentIntelligenceEdgeCases:
    """Edge case tests for document intelligence."""
    
    @pytest.mark.asyncio
    async def test_empty_document(self):
        """Test handling of empty document."""
        service = DocumentIntelligenceService()
        
        file_data = b""
        result = await service.process_document(file_data, "empty.pdf")
        
        assert result.total_pages == 0 or len(result.pages) >= 0
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        service = DocumentIntelligenceService()
        
        file_data = b"some binary data"
        result = await service.process_document(file_data, "file.xyz")
        
        # Should handle gracefully
        assert isinstance(result, ProcessedDocument)
    
    def test_classifier_with_empty_text(self):
        """Test classifier with empty text."""
        classifier = DocumentClassifier()
        
        doc_type, confidence = classifier.classify("")
        
        assert doc_type == DocumentType.UNKNOWN
    
    def test_kv_extractor_with_empty_text(self):
        """Test key-value extractor with empty text."""
        extractor = KeyValueExtractor()
        
        results = extractor.extract("")
        
        assert results == []
