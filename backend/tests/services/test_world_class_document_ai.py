"""
Comprehensive Tests for World-Class Document AI Service.

Tests validate:
1. Data model integrity
2. Enum values
3. Bounding box normalization
4. Layout analysis
5. Table recognition
6. Engineering drawing processing
7. Vision-LLM integration
8. RAG chunk generation
"""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime

from sensei.services.ai.world_class_document_ai import (
    # Enums
    DocumentCategory,
    ElementType,
    ProcessingStrategy,
    VisionLLMProvider,
    GDTSymbol,
    ToleranceType,
    # Data Models
    BoundingBox,
    DocumentElement,
    TableCell,
    ExtractedTable,
    GDTCallout,
    DimensionCallout,
    TitleBlockData,
    KeyValuePair,
    ExtractedFigure,
    DocumentPage,
    ProcessedDocument,
    # Service Classes
    LayoutAnalyzer,
    TableStructureRecognizer,
    VisionLLMEnricher,
    EngineeringDrawingProcessor,
    DocumentClassifier,
    KeyValueExtractor,
    WorldClassDocumentAI,
)


# Helper for running async functions in tests
def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


# =============================================================================
# Test Enums
# =============================================================================


class TestEnums:
    """Test all enum definitions."""

    def test_document_category_values(self) -> None:
        """Verify DocumentCategory has expected values."""
        expected = [
            "rfq", "purchase_order", "invoice", "drawing",
            "specification", "quality_report", "work_instruction",
            "email", "general"
        ]
        actual = [c.value for c in DocumentCategory]
        assert set(expected) == set(actual)

    def test_element_type_values(self) -> None:
        """Verify ElementType has expected values."""
        expected = [
            "title", "narrative_text", "list_item", "table",
            "image", "figure", "header", "footer", "page_number",
            "caption", "code", "form_field", "signature", "stamp",
            "barcode", "qr_code", "gdt_callout", "dimension", 
            "title_block", "revision_cloud"
        ]
        actual = [e.value for e in ElementType]
        assert set(expected) == set(actual)

    def test_processing_strategy_values(self) -> None:
        """Verify ProcessingStrategy has expected values."""
        expected = [
            "layout_lm", "vision_llm", "donut", "hybrid_ocr",
            "table_transformer", "cad_parser", "auto"
        ]
        actual = [p.value for p in ProcessingStrategy]
        assert set(expected) == set(actual)

    def test_vision_llm_provider_values(self) -> None:
        """Verify VisionLLMProvider has expected values."""
        expected = ["gpt4_vision", "claude_vision", "gemini_pro_vision", "llava", "moondream", "qwen_vl"]
        actual = [v.value for v in VisionLLMProvider]
        assert set(expected) == set(actual)

    def test_gdt_symbol_values(self) -> None:
        """Verify GDTSymbol has expected values."""
        assert GDTSymbol.FLATNESS.value == "flatness"
        assert GDTSymbol.PARALLELISM.value == "parallelism"
        assert GDTSymbol.POSITION.value == "position"
        assert len(list(GDTSymbol)) >= 10  # Should have at least 10 GD&T symbols

    def test_tolerance_type_values(self) -> None:
        """Verify ToleranceType has expected values."""
        expected = ["bilateral", "unilateral", "limit", "reference", "basic"]
        actual = [t.value for t in ToleranceType]
        assert set(expected) == set(actual)


# =============================================================================
# Test Bounding Box
# =============================================================================


class TestBoundingBox:
    """Test BoundingBox data model."""

    def test_bounding_box_creation(self) -> None:
        """Test creating a bounding box."""
        bbox = BoundingBox(x0=0, y0=0, x1=500, y1=500)
        assert bbox.x0 == 0
        assert bbox.y0 == 0
        assert bbox.x1 == 500
        assert bbox.y1 == 500

    def test_bounding_box_full_page(self) -> None:
        """Test bounding box covering full page (0-1000 normalized)."""
        bbox = BoundingBox(x0=0, y0=0, x1=1000, y1=1000)
        assert bbox.x0 == 0
        assert bbox.x1 == 1000

    def test_bounding_box_center(self) -> None:
        """Test bounding box in center of page."""
        bbox = BoundingBox(x0=250, y0=250, x1=750, y1=750)
        # Width should be 500/1000 = 50% of page
        width = bbox.x1 - bbox.x0
        assert width == 500


# =============================================================================
# Test Document Element
# =============================================================================


class TestDocumentElement:
    """Test DocumentElement data model."""

    def test_document_element_creation(self) -> None:
        """Test creating a document element."""
        bbox = BoundingBox(x0=100, y0=100, x1=900, y1=150)
        element = DocumentElement(
            element_id="elem_001",
            element_type=ElementType.TITLE,
            text="Test Document Title",
            bbox=bbox,
            confidence=0.95,
        )
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Document Title"
        assert element.confidence == 0.95
        assert element.element_id == "elem_001"

    def test_document_element_with_parent(self) -> None:
        """Test element with parent ID."""
        bbox = BoundingBox(x0=50, y0=200, x1=950, y1=250)
        element = DocumentElement(
            element_id="elem_002",
            element_type=ElementType.LIST_ITEM,
            text="• First item",
            bbox=bbox,
            confidence=0.88,
            parent_id="list_123",
        )
        assert element.parent_id == "list_123"

    def test_document_element_with_metadata(self) -> None:
        """Test element with metadata."""
        element = DocumentElement(
            element_id="elem_003",
            element_type=ElementType.NARRATIVE_TEXT,
            text="Some content",
            metadata={"font": "Arial", "size": 12},
        )
        assert element.metadata["font"] == "Arial"


# =============================================================================
# Test Table Extraction
# =============================================================================


class TestTableExtraction:
    """Test table-related data models."""

    def test_table_cell_creation(self) -> None:
        """Test creating a table cell."""
        bbox = BoundingBox(x0=100, y0=200, x1=300, y1=250)
        cell = TableCell(
            row=0,
            col=0,
            text="Cell Content",
            rowspan=1,
            colspan=1,
            bbox=bbox,
            is_header=True,
        )
        assert cell.text == "Cell Content"
        assert cell.is_header is True
        assert cell.row == 0
        assert cell.col == 0

    def test_table_cell_spanning(self) -> None:
        """Test table cell with spanning."""
        bbox = BoundingBox(x0=100, y0=200, x1=500, y1=250)
        cell = TableCell(
            row=0,
            col=0,
            text="Merged Cell",
            rowspan=2,
            colspan=3,
            bbox=bbox,
            is_header=False,
        )
        assert cell.rowspan == 2
        assert cell.colspan == 3

    def test_extracted_table_creation(self) -> None:
        """Test creating an extracted table."""
        bbox = BoundingBox(x0=50, y0=100, x1=950, y1=400)
        header_cell = TableCell(
            row=0,
            col=0,
            text="Header",
            rowspan=1,
            colspan=1,
            bbox=BoundingBox(x0=50, y0=100, x1=250, y1=150),
            is_header=True,
        )
        data_cell = TableCell(
            row=1,
            col=0,
            text="Data",
            rowspan=1,
            colspan=1,
            bbox=BoundingBox(x0=50, y0=150, x1=250, y1=200),
            is_header=False,
        )
        table = ExtractedTable(
            table_id="table_001",
            bbox=bbox,
            rows=2,
            cols=1,
            cells=[header_cell, data_cell],
            confidence=0.92,
        )
        assert table.rows == 2
        assert table.cols == 1
        assert len(table.cells) == 2


# =============================================================================
# Test GD&T Extraction
# =============================================================================


class TestGDTExtraction:
    """Test GD&T-related data models."""

    def test_gdt_callout_creation(self) -> None:
        """Test creating a GD&T callout."""
        bbox = BoundingBox(x0=300, y0=400, x1=400, y1=450)
        callout = GDTCallout(
            callout_id="gdt_001",
            symbol=GDTSymbol.POSITION,
            tolerance_value=0.05,
            datum_references=["A", "B", "C"],
            material_condition="MMC",
            bbox=bbox,
        )
        assert callout.symbol == GDTSymbol.POSITION
        assert callout.tolerance_value == 0.05
        assert len(callout.datum_references) == 3

    def test_dimension_callout_creation(self) -> None:
        """Test creating a dimension callout."""
        bbox = BoundingBox(x0=200, y0=300, x1=350, y1=350)
        dimension = DimensionCallout(
            dimension_id="dim_001",
            nominal_value=25.4,
            tolerance_type=ToleranceType.BILATERAL,
            tolerance_plus=0.1,
            tolerance_minus=0.1,
            unit="mm",
            bbox=bbox,
            is_ctq=False,
        )
        assert dimension.nominal_value == 25.4
        assert dimension.tolerance_type == ToleranceType.BILATERAL
        assert dimension.unit == "mm"

    def test_dimension_ctq_flag(self) -> None:
        """Test dimension with CTQ flag."""
        dimension = DimensionCallout(
            dimension_id="dim_002",
            nominal_value=10.0,
            tolerance_type=ToleranceType.LIMIT,
            tolerance_plus=0.0,
            tolerance_minus=0.0,
            unit="mm",
            is_ctq=True,
        )
        assert dimension.is_ctq is True


# =============================================================================
# Test Title Block
# =============================================================================


class TestTitleBlock:
    """Test TitleBlockData data model."""

    def test_title_block_creation(self) -> None:
        """Test creating a title block."""
        title_block = TitleBlockData(
            part_number="DWG-001-REV-A",
            revision="A",
            part_name="Test Part Assembly",
            drawn_by="J. Smith",
            approved_by="M. Jones",
            material="Aluminum 6061-T6",
            scale="1:2",
        )
        assert title_block.part_number == "DWG-001-REV-A"
        assert title_block.revision == "A"
        assert title_block.material == "Aluminum 6061-T6"

    def test_title_block_partial(self) -> None:
        """Test title block with partial data."""
        title_block = TitleBlockData(
            part_number="DWG-002",
            part_name="Simple Part",
        )
        assert title_block.part_number == "DWG-002"
        assert title_block.revision is None
        assert title_block.drawn_by is None


# =============================================================================
# Test Document Page and Processed Document
# =============================================================================


class TestDocumentStructure:
    """Test DocumentPage and ProcessedDocument models."""

    def test_document_page_creation(self) -> None:
        """Test creating a document page."""
        page = DocumentPage(
            page_number=1,
            width=612,
            height=792,
            elements=[],
            tables=[],
        )
        assert page.page_number == 1
        assert page.width == 612
        assert page.height == 792

    def test_processed_document_creation(self) -> None:
        """Test creating a processed document."""
        page = DocumentPage(
            page_number=1,
            width=612,
            height=792,
            elements=[],
            tables=[],
        )
        doc = ProcessedDocument(
            document_id="doc_001",
            filename="test.pdf",
            category=DocumentCategory.SPECIFICATION,
            pages=[page],
            processing_strategy=ProcessingStrategy.LAYOUT_LM,
        )
        assert doc.document_id == "doc_001"
        assert doc.category == DocumentCategory.SPECIFICATION
        assert len(doc.pages) == 1


# =============================================================================
# Test LayoutAnalyzer
# =============================================================================


class TestLayoutAnalyzer:
    """Test LayoutAnalyzer service class."""

    @pytest.fixture
    def analyzer(self) -> LayoutAnalyzer:
        return LayoutAnalyzer()

    def test_analyzer_initialization(self, analyzer: LayoutAnalyzer) -> None:
        """Test analyzer can be initialized."""
        assert analyzer is not None

    def test_analyze_layout_returns_elements(self, analyzer: LayoutAnalyzer) -> None:
        """Test that analyze_layout returns a list of elements."""
        mock_image_bytes = b"mock_image_data"
        ocr_words: list = []
        elements = analyzer.analyze_layout(
            mock_image_bytes, 
            ocr_words,
            page_width=612, 
            page_height=792
        )
        assert isinstance(elements, list)


# =============================================================================
# Test TableStructureRecognizer
# =============================================================================


class TestTableStructureRecognizer:
    """Test TableStructureRecognizer service class."""

    @pytest.fixture
    def recognizer(self) -> TableStructureRecognizer:
        return TableStructureRecognizer()

    def test_recognizer_initialization(self, recognizer: TableStructureRecognizer) -> None:
        """Test recognizer can be initialized."""
        assert recognizer is not None

    def test_detect_tables_returns_list(self, recognizer: TableStructureRecognizer) -> None:
        """Test that detect_tables returns a list of bounding boxes."""
        mock_image_bytes = b"mock_image_data"
        bboxes = recognizer.detect_tables(mock_image_bytes, 612, 792)
        assert isinstance(bboxes, list)


# =============================================================================
# Test VisionLLMEnricher
# =============================================================================


class TestVisionLLMEnricher:
    """Test VisionLLMEnricher service class."""

    @pytest.fixture
    def enricher(self) -> VisionLLMEnricher:
        return VisionLLMEnricher()

    def test_enricher_initialization(self, enricher: VisionLLMEnricher) -> None:
        """Test enricher can be initialized."""
        assert enricher is not None

    def test_default_provider(self, enricher: VisionLLMEnricher) -> None:
        """Test default provider is set."""
        # Access private attribute since provider is internal
        assert enricher._provider in list(VisionLLMProvider)


# =============================================================================
# Test EngineeringDrawingProcessor
# =============================================================================


class TestEngineeringDrawingProcessor:
    """Test EngineeringDrawingProcessor service class."""

    @pytest.fixture
    def processor(self) -> EngineeringDrawingProcessor:
        return EngineeringDrawingProcessor()

    def test_processor_initialization(self, processor: EngineeringDrawingProcessor) -> None:
        """Test processor can be initialized."""
        assert processor is not None

    def test_process_drawing_returns_tuple(self, processor: EngineeringDrawingProcessor) -> None:
        """Test process_drawing returns expected structure."""
        mock_image_bytes = b"mock_image_data"
        mock_text = "Part Number: ABC-123 Rev: A Material: Steel"
        mock_words: list = []
        result = run_async(processor.process_drawing(mock_image_bytes, mock_text, mock_words))
        assert isinstance(result, tuple)
        assert len(result) == 3  # title_block, gdt_callouts, dimensions


# =============================================================================
# Test DocumentClassifier
# =============================================================================


class TestDocumentClassifier:
    """Test DocumentClassifier service class."""

    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        return DocumentClassifier()

    def test_classifier_initialization(self, classifier: DocumentClassifier) -> None:
        """Test classifier can be initialized."""
        assert classifier is not None

    def test_classify_returns_valid_category(self, classifier: DocumentClassifier) -> None:
        """Test classify returns a valid category."""
        mock_text = "PURCHASE ORDER\nPO Number: 12345"
        category, confidence = classifier.classify(mock_text)
        assert isinstance(category, DocumentCategory)
        assert 0.0 <= confidence <= 1.0


# =============================================================================
# Test KeyValueExtractor
# =============================================================================


class TestKeyValueExtractor:
    """Test KeyValueExtractor service class."""

    @pytest.fixture
    def extractor(self) -> KeyValueExtractor:
        return KeyValueExtractor()

    def test_extractor_initialization(self, extractor: KeyValueExtractor) -> None:
        """Test extractor can be initialized."""
        assert extractor is not None

    def test_extract_returns_pairs(self, extractor: KeyValueExtractor) -> None:
        """Test extract returns a list of key-value pairs."""
        mock_text = "Date: 01/15/2025\nAmount: $100.00"
        pairs = extractor.extract(mock_text)
        assert isinstance(pairs, list)


# =============================================================================
# Test WorldClassDocumentAI Main Service
# =============================================================================


class TestWorldClassDocumentAI:
    """Test WorldClassDocumentAI main service class."""

    @pytest.fixture
    def service(self) -> WorldClassDocumentAI:
        return WorldClassDocumentAI()

    def test_service_initialization(self, service: WorldClassDocumentAI) -> None:
        """Test service can be initialized."""
        assert service is not None

    def test_process_document_returns_processed_document(self, service: WorldClassDocumentAI) -> None:
        """Test process_document returns ProcessedDocument."""
        mock_pdf_bytes = b"%PDF-1.4 mock pdf content"
        result = run_async(service.process_document(mock_pdf_bytes, filename="test.pdf"))
        assert isinstance(result, ProcessedDocument)
        assert result.filename == "test.pdf"

    def test_get_rag_chunks_returns_list(self, service: WorldClassDocumentAI) -> None:
        """Test get_rag_chunks returns list of dicts."""
        mock_pdf_bytes = b"%PDF-1.4 mock pdf content"
        doc = run_async(service.process_document(mock_pdf_bytes, filename="test.pdf"))
        
        chunks = service.get_rag_chunks(doc)
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert isinstance(chunk, dict)

    def test_strategy_selection(self, service: WorldClassDocumentAI) -> None:
        """Test that strategy can be specified."""
        mock_pdf_bytes = b"%PDF-1.4 mock pdf content"
        
        result = run_async(service.process_document(
            mock_pdf_bytes,
            filename="test.pdf",
            strategy=ProcessingStrategy.VISION_LLM
        ))
        assert result.processing_strategy == ProcessingStrategy.VISION_LLM


# =============================================================================
# Test Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def service(self) -> WorldClassDocumentAI:
        return WorldClassDocumentAI()

    def test_engineering_drawing_workflow(self, service: WorldClassDocumentAI) -> None:
        """Test complete engineering drawing processing workflow."""
        mock_drawing = b"%PDF-1.4 engineering drawing content"
        
        result = run_async(service.process_document(
            mock_drawing,
            filename="part_drawing.pdf",
            strategy=ProcessingStrategy.CAD_PARSER
        ))
        
        assert result is not None
        assert result.processing_strategy == ProcessingStrategy.CAD_PARSER

    def test_sop_document_workflow(self, service: WorldClassDocumentAI) -> None:
        """Test complete SOP document processing workflow."""
        mock_sop = b"%PDF-1.4 standard operating procedure"
        
        result = run_async(service.process_document(
            mock_sop,
            filename="sop_001.pdf",
            strategy=ProcessingStrategy.LAYOUT_LM
        ))
        
        assert result is not None
        assert result.filename == "sop_001.pdf"

    def test_quality_report_workflow(self, service: WorldClassDocumentAI) -> None:
        """Test complete quality report processing workflow."""
        mock_report = b"%PDF-1.4 quality inspection report"
        
        result = run_async(service.process_document(
            mock_report,
            filename="qa_report.pdf",
            strategy=ProcessingStrategy.HYBRID_OCR
        ))
        
        chunks = service.get_rag_chunks(result)
        
        assert result is not None
        assert isinstance(chunks, list)


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def service(self) -> WorldClassDocumentAI:
        return WorldClassDocumentAI()

    def test_empty_document_handling(self, service: WorldClassDocumentAI) -> None:
        """Test handling of empty document."""
        result = run_async(service.process_document(b"", filename="empty.pdf"))
        assert result is not None
        assert result.page_count >= 0

    def test_invalid_document_handling(self, service: WorldClassDocumentAI) -> None:
        """Test handling of invalid document content."""
        result = run_async(service.process_document(b"not a valid pdf", filename="invalid.pdf"))
        assert result is not None

    def test_unicode_filename_handling(self, service: WorldClassDocumentAI) -> None:
        """Test handling of unicode filenames."""
        mock_pdf = b"%PDF-1.4 content"
        result = run_async(service.process_document(
            mock_pdf,
            filename="文档_αβγ_日本語.pdf"
        ))
        assert result is not None
        assert "文档" in result.filename


# =============================================================================
# Test GD&T Recognition
# =============================================================================


class TestGDTRecognition:
    """Test GD&T symbol recognition capabilities."""

    def test_all_gdt_symbols_defined(self) -> None:
        """Verify all major GD&T symbols are defined."""
        expected_symbols = [
            "flatness", "straightness", "circularity", "cylindricity",
            "parallelism", "perpendicularity", "angularity",
            "position", "concentricity", "symmetry",
            "runout", "total_runout", "profile_line", "profile_surface"
        ]
        defined_values = [s.value for s in GDTSymbol]
        
        for expected in expected_symbols:
            assert expected in defined_values, f"GD&T symbol '{expected}' not defined"

    def test_gdt_callout_with_all_data(self) -> None:
        """Test creating a fully specified GD&T callout."""
        bbox = BoundingBox(x0=100, y0=100, x1=200, y1=150)
        callout = GDTCallout(
            callout_id="gdt_001",
            symbol=GDTSymbol.POSITION,
            tolerance_value=0.025,
            datum_references=["A", "B", "C"],
            material_condition="MMC",
            bbox=bbox,
        )
        
        assert callout.symbol == GDTSymbol.POSITION
        assert callout.tolerance_value == 0.025
        assert callout.datum_references == ["A", "B", "C"]
        assert callout.material_condition == "MMC"


# =============================================================================
# Test RAG Chunk Generation
# =============================================================================


class TestRAGChunkGeneration:
    """Test RAG chunk generation for knowledge base."""

    @pytest.fixture
    def service(self) -> WorldClassDocumentAI:
        return WorldClassDocumentAI()

    def test_rag_chunks_are_dicts(self, service: WorldClassDocumentAI) -> None:
        """Verify RAG chunks are dictionaries."""
        mock_pdf = b"%PDF-1.4 document content"
        doc = run_async(service.process_document(mock_pdf, filename="test.pdf"))
        chunks = service.get_rag_chunks(doc)
        
        for chunk in chunks:
            assert isinstance(chunk, dict)
            assert "type" in chunk
            assert "content" in chunk

    def test_rag_chunks_have_required_fields(self, service: WorldClassDocumentAI) -> None:
        """Verify RAG chunks have required fields."""
        mock_pdf = b"%PDF-1.4 document content with more text " * 100
        doc = run_async(service.process_document(mock_pdf, filename="test.pdf"))
        chunks = service.get_rag_chunks(doc)
        
        for chunk in chunks:
            assert "type" in chunk
            assert chunk["type"] in ("text", "table", "figure", "title_block", "gdt")
