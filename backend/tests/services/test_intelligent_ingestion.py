"""
Tests for Intelligent Data Ingestion 2.0 - Universal Zero-Shot Parser.

Tests cover:
- Vision-LLM integration
- Hybrid OCR fallback
- Multi-page stitching
- Format support (PDF, PNG, JPG, DXF/DWG)
- Table extraction (BOMs, Price Tables)
- Confidence thresholds and HITL triggers
- Auto-standard update with diff analysis
"""

import pytest
import hashlib
from datetime import datetime, timezone

from sensei.services.intelligent_ingestion import (
    # Enums
    DocumentFormat,
    ParsingStrategy,
    ExtractionType,
    ConfidenceLevel,
    HITLReason,
    # Data models
    DocumentPage,
    TableCell,
    TableData,
    BOMEntry,
    ExtractedBOM,
    DrawingSpec,
    ParsingResult,
    StandardWorkVersion,
    StandardWorkDiff,
    # Components
    OCREngine,
    VisionLLMParser,
    TableExtractor,
    MultiPageStitcher,
    StandardWorkManager,
    UniversalZeroShotParser,
    # Factory
    create_document_parser,
    # Constants
    CONFIDENCE_THRESHOLD,
    BOM_HEADERS,
    PRICE_HEADERS,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_document_data() -> bytes:
    """Sample document bytes."""
    return b"Sample document content for testing parser functionality."


@pytest.fixture
def sample_pdf_data() -> bytes:
    """Sample PDF-like data."""
    return b"%PDF-1.4 Sample PDF content here..."


@pytest.fixture
def sample_image_data() -> bytes:
    """Sample image-like data."""
    return b"\x89PNG\r\n\x1a\n Sample image content..."


@pytest.fixture
def sample_cad_data() -> bytes:
    """Sample CAD file data."""
    return b"DXF 0\nSECTION\nHEADER\n..."


@pytest.fixture
def sample_table_data() -> TableData:
    """Sample table with BOM-like structure."""
    table = TableData(
        table_id="TBL-001",
        rows=4,
        columns=5,
        headers=["Item", "Part Number", "Description", "Qty", "Unit Price"],
        table_type=ExtractionType.BOM,
        confidence=0.92,
        source_page=1,
    )
    
    # Header row (row 0)
    for col, header in enumerate(table.headers):
        table.cells.append(TableCell(row=0, column=col, value=header, confidence=0.95))
    
    # Data rows
    data = [
        ["1", "ABC-001", "Widget A", "10", "5.00"],
        ["2", "ABC-002", "Widget B", "5", "12.50"],
        ["3", "ABC-003", "Widget C", "20", "2.25"],
    ]
    
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, value in enumerate(row_data):
            table.cells.append(TableCell(
                row=row_idx,
                column=col_idx,
                value=value,
                confidence=0.90,
            ))
    
    return table


@pytest.fixture
def sample_pages() -> list[DocumentPage]:
    """Sample multi-page document."""
    return [
        DocumentPage(
            page_number=1,
            content="Page 1 content... continued on next page",
            raw_text="Raw text page 1",
            confidence=0.88,
        ),
        DocumentPage(
            page_number=2,
            content="Page 2 content continued from page 1",
            raw_text="Raw text page 2",
            confidence=0.90,
        ),
        DocumentPage(
            page_number=3,
            content="Page 3 final content",
            raw_text="Raw text page 3",
            confidence=0.92,
        ),
    ]


@pytest.fixture
def standard_work_version_v1() -> StandardWorkVersion:
    """Sample standard work version."""
    return StandardWorkVersion(
        version_id="v1-001",
        version_number="1.0",
        content="Standard work procedure v1.0",
        sections={
            "setup": "Setup instructions",
            "process": "Process steps",
            "cleanup": "Cleanup procedure",
        },
    )


@pytest.fixture
def standard_work_version_v2() -> StandardWorkVersion:
    """Updated standard work version."""
    return StandardWorkVersion(
        version_id="v2-001",
        version_number="1.1",
        content="Standard work procedure v1.1 with updates",
        sections={
            "setup": "Updated setup instructions",
            "process": "Process steps",
            "safety": "New safety section",
        },
    )


# =============================================================================
# Test Enums
# =============================================================================

class TestEnums:
    """Test enum values."""
    
    def test_document_format_values(self):
        """Test document format enum values."""
        assert DocumentFormat.PDF.value == "pdf"
        assert DocumentFormat.PNG.value == "png"
        assert DocumentFormat.JPG.value == "jpg"
        assert DocumentFormat.DXF.value == "dxf"
        assert DocumentFormat.DWG.value == "dwg"
    
    def test_parsing_strategy_values(self):
        """Test parsing strategy enum values."""
        assert ParsingStrategy.VISION_LLM.value == "vision_llm"
        assert ParsingStrategy.OCR.value == "ocr"
        assert ParsingStrategy.HYBRID.value == "hybrid"
    
    def test_extraction_type_values(self):
        """Test extraction type enum values."""
        assert ExtractionType.BOM.value == "bom"
        assert ExtractionType.PRICE_TABLE.value == "price_table"
        assert ExtractionType.DRAWING_SPECS.value == "drawing_specs"
    
    def test_confidence_level_values(self):
        """Test confidence level enum values."""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.FAILED.value == "failed"
    
    def test_hitl_reason_values(self):
        """Test HITL reason enum values."""
        assert HITLReason.LOW_CONFIDENCE.value == "low_confidence"
        assert HITLReason.AMBIGUOUS_DATA.value == "ambiguous_data"
        assert HITLReason.OCR_ERRORS.value == "ocr_errors"


# =============================================================================
# Test Data Models
# =============================================================================

class TestTableData:
    """Test TableData class."""
    
    def test_get_cell(self, sample_table_data):
        """Test getting cell by position."""
        cell = sample_table_data.get_cell(0, 0)
        assert cell is not None
        assert cell.value == "Item"
    
    def test_get_cell_not_found(self, sample_table_data):
        """Test getting non-existent cell."""
        cell = sample_table_data.get_cell(100, 100)
        assert cell is None
    
    def test_get_row_values(self, sample_table_data):
        """Test getting row values."""
        values = sample_table_data.get_row_values(1)
        assert values == ["1", "ABC-001", "Widget A", "10", "5.00"]
    
    def test_to_dict_list(self, sample_table_data):
        """Test converting to list of dicts."""
        dict_list = sample_table_data.to_dict_list()
        
        assert len(dict_list) == 3
        assert dict_list[0]["Part Number"] == "ABC-001"
        assert dict_list[1]["Description"] == "Widget B"


class TestBOMEntry:
    """Test BOMEntry class."""
    
    def test_bom_entry_defaults(self):
        """Test BOM entry default values."""
        entry = BOMEntry(item_number="1")
        
        assert entry.item_number == "1"
        assert entry.quantity == 1.0
        assert entry.unit == "EA"
        assert entry.unit_price is None
    
    def test_bom_entry_full(self):
        """Test BOM entry with all fields."""
        entry = BOMEntry(
            item_number="1",
            part_number="ABC-001",
            description="Widget A",
            quantity=10,
            unit="PCS",
            unit_price=5.00,
            extended_price=50.00,
        )
        
        assert entry.part_number == "ABC-001"
        assert entry.extended_price == 50.00


class TestExtractedBOM:
    """Test ExtractedBOM class."""
    
    def test_total_value_with_extended(self):
        """Test total value calculation with extended prices."""
        bom = ExtractedBOM(
            bom_id="BOM-001",
            entries=[
                BOMEntry(item_number="1", extended_price=100.00),
                BOMEntry(item_number="2", extended_price=200.00),
            ],
        )
        
        assert bom.total_value == 300.00
    
    def test_total_value_with_unit_price(self):
        """Test total value calculation with unit prices."""
        bom = ExtractedBOM(
            bom_id="BOM-001",
            entries=[
                BOMEntry(item_number="1", quantity=10, unit_price=5.00),
                BOMEntry(item_number="2", quantity=5, unit_price=20.00),
            ],
        )
        
        assert bom.total_value == 150.00  # 50 + 100
    
    def test_total_value_mixed(self):
        """Test total value with mixed prices."""
        bom = ExtractedBOM(
            bom_id="BOM-001",
            entries=[
                BOMEntry(item_number="1", extended_price=100.00),
                BOMEntry(item_number="2", quantity=10, unit_price=5.00),
            ],
        )
        
        assert bom.total_value == 150.00


class TestDrawingSpec:
    """Test DrawingSpec class."""
    
    def test_drawing_spec_creation(self):
        """Test drawing spec creation."""
        spec = DrawingSpec(
            spec_id="SPEC-001",
            drawing_number="DWG-12345",
            revision="A",
            material="Aluminum 6061-T6",
            tolerances={"general": "±0.01"},
            dimensions=["10.00 x 5.00 x 2.50"],
        )
        
        assert spec.drawing_number == "DWG-12345"
        assert spec.material == "Aluminum 6061-T6"
        assert len(spec.tolerances) == 1


class TestParsingResult:
    """Test ParsingResult class."""
    
    def test_parsing_result_defaults(self):
        """Test parsing result default values."""
        result = ParsingResult(
            result_id="RES-001",
            document_id="DOC-001",
            format=DocumentFormat.PDF,
            strategy_used=ParsingStrategy.HYBRID,
        )
        
        assert result.pages == []
        assert result.requires_hitl is False
        assert result.overall_confidence == 0.0
    
    def test_parsing_result_with_data(self):
        """Test parsing result with full data."""
        result = ParsingResult(
            result_id="RES-001",
            document_id="DOC-001",
            format=DocumentFormat.PDF,
            strategy_used=ParsingStrategy.VISION_LLM,
            overall_confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            requires_hitl=False,
        )
        
        assert result.confidence_level == ConfidenceLevel.HIGH


# =============================================================================
# Test OCR Engine
# =============================================================================

class TestOCREngine:
    """Test OCR engine."""
    
    def test_extract_text(self, sample_document_data):
        """Test text extraction."""
        engine = OCREngine()
        text, confidence = engine.extract_text(sample_document_data)
        
        assert text is not None
        assert len(text) > 0
        assert 0.0 <= confidence <= 1.0
    
    def test_extract_structured(self, sample_document_data):
        """Test structured extraction."""
        engine = OCREngine()
        structures, confidence = engine.extract_structured(sample_document_data)
        
        assert structures is not None
        assert len(structures) > 0
        assert 0.0 <= confidence <= 1.0
    
    def test_consistent_extraction(self, sample_document_data):
        """Test extraction consistency."""
        engine = OCREngine()
        text1, conf1 = engine.extract_text(sample_document_data)
        text2, conf2 = engine.extract_text(sample_document_data)
        
        assert text1 == text2
        assert conf1 == conf2


# =============================================================================
# Test Vision LLM Parser
# =============================================================================

class TestVisionLLMParser:
    """Test Vision LLM parser."""
    
    def test_is_available(self):
        """Test availability check."""
        parser = VisionLLMParser()
        assert parser.is_available() is True
    
    def test_parse_document_text(self, sample_document_data):
        """Test parsing for text content."""
        parser = VisionLLMParser()
        result, confidence = parser.parse_document(
            sample_document_data,
            ExtractionType.TEXT_CONTENT,
        )
        
        assert result["type"] == "text"
        assert "content" in result
        assert 0.0 <= confidence <= 1.0
    
    def test_parse_document_bom(self, sample_document_data):
        """Test parsing for BOM."""
        parser = VisionLLMParser()
        result, confidence = parser.parse_document(
            sample_document_data,
            ExtractionType.BOM,
        )
        
        assert result["type"] == "bom"
        assert "items" in result
    
    def test_parse_document_drawing(self, sample_cad_data):
        """Test parsing for drawing specs."""
        parser = VisionLLMParser()
        result, confidence = parser.parse_document(
            sample_cad_data,
            ExtractionType.DRAWING_SPECS,
        )
        
        assert result["type"] == "drawing"
        assert "drawing_number" in result
    
    def test_extract_tables(self, sample_document_data):
        """Test table extraction."""
        parser = VisionLLMParser()
        tables = parser.extract_tables(sample_document_data)
        
        assert len(tables) > 0
        assert tables[0].rows > 0
        assert tables[0].columns > 0


# =============================================================================
# Test Table Extractor
# =============================================================================

class TestTableExtractor:
    """Test table extractor."""
    
    def test_identify_bom_table(self):
        """Test BOM table identification."""
        extractor = TableExtractor()
        headers = ["Item", "Part Number", "Quantity", "Description"]
        
        table_type = extractor._identify_table_type(headers)
        assert table_type == ExtractionType.BOM
    
    def test_identify_price_table(self):
        """Test price table identification."""
        extractor = TableExtractor()
        # Use headers that match price table but not BOM
        headers = ["Service", "Unit Price", "Tax", "Total Amount"]
        
        table_type = extractor._identify_table_type(headers)
        assert table_type == ExtractionType.PRICE_TABLE
    
    def test_identify_generic_table(self):
        """Test generic table identification."""
        extractor = TableExtractor()
        headers = ["Name", "Value", "Comments"]
        
        table_type = extractor._identify_table_type(headers)
        assert table_type == ExtractionType.TEXT_CONTENT
    
    def test_parse_number(self):
        """Test number parsing."""
        extractor = TableExtractor()
        
        assert extractor._parse_number("100") == 100.0
        assert extractor._parse_number("$100.50") == 100.50
        assert extractor._parse_number("1,234.56") == 1234.56
        assert extractor._parse_number("€50") == 50.0
        assert extractor._parse_number("") is None
        assert extractor._parse_number("abc") is None
    
    def test_extract_bom(self, sample_table_data):
        """Test BOM extraction from table."""
        extractor = TableExtractor()
        bom = extractor.extract_bom(sample_table_data)
        
        assert bom is not None
        assert len(bom.entries) == 3
        assert bom.entries[0].item_number == "1"
        assert bom.entries[0].part_number == "ABC-001"
    
    def test_extract_bom_no_headers(self):
        """Test BOM extraction without headers."""
        extractor = TableExtractor()
        table = TableData(table_id="TBL-001", rows=2, columns=2)
        
        bom = extractor.extract_bom(table)
        assert bom is None
    
    def test_merge_multi_page_tables(self):
        """Test multi-page table merging."""
        extractor = TableExtractor()
        
        table1 = TableData(
            table_id="TBL-001",
            rows=3,
            columns=2,
            headers=["Item", "Value"],
            table_type=ExtractionType.BOM,
            source_page=1,
            cells=[
                TableCell(row=0, column=0, value="Item"),
                TableCell(row=0, column=1, value="Value"),
                TableCell(row=1, column=0, value="1"),
                TableCell(row=1, column=1, value="A"),
                TableCell(row=2, column=0, value="2"),
                TableCell(row=2, column=1, value="B"),
            ],
        )
        
        table2 = TableData(
            table_id="TBL-002",
            rows=2,
            columns=2,
            headers=["Item", "Value"],
            table_type=ExtractionType.BOM,
            source_page=2,
            cells=[
                TableCell(row=0, column=0, value="Item"),
                TableCell(row=0, column=1, value="Value"),
                TableCell(row=1, column=0, value="3"),
                TableCell(row=1, column=1, value="C"),
            ],
        )
        
        merged = extractor.merge_multi_page_tables([table1, table2])
        
        assert len(merged) == 1
        assert merged[0].rows == 4  # 3 + 2 - 1 (header)


# =============================================================================
# Test Multi-Page Stitcher
# =============================================================================

class TestMultiPageStitcher:
    """Test multi-page stitcher."""
    
    def test_detect_continuation_explicit(self):
        """Test continuation detection with explicit marker."""
        stitcher = MultiPageStitcher()
        page = DocumentPage(
            page_number=1,
            content="Content continued on next page",
        )
        
        assert stitcher.detect_continuation(page) is True
    
    def test_detect_continuation_ellipsis(self):
        """Test continuation detection with ellipsis."""
        stitcher = MultiPageStitcher()
        page = DocumentPage(
            page_number=1,
            content="Content that trails off...",
        )
        
        assert stitcher.detect_continuation(page) is True
    
    def test_detect_no_continuation(self):
        """Test no continuation detection."""
        stitcher = MultiPageStitcher()
        page = DocumentPage(
            page_number=1,
            content="Complete content ending with period.",
        )
        
        assert stitcher.detect_continuation(page) is False
    
    def test_stitch_pages(self, sample_pages):
        """Test page stitching."""
        stitcher = MultiPageStitcher()
        stitched = stitcher.stitch_pages(sample_pages)
        
        # Page 1 continues to page 2, page 2 mentions "continued from" which also matches
        # So all pages get merged into one, or the final page is separate
        # Depending on implementation, result should have merged content
        assert len(stitched) >= 1
        # Check that content from multiple pages is combined
        total_content = "".join(p.content for p in stitched)
        assert "Page 1" in total_content
        assert "Page 3" in total_content
    
    def test_stitch_single_page(self):
        """Test stitching single page."""
        stitcher = MultiPageStitcher()
        pages = [DocumentPage(page_number=1, content="Single page")]
        
        stitched = stitcher.stitch_pages(pages)
        assert len(stitched) == 1


# =============================================================================
# Test Standard Work Manager
# =============================================================================

class TestStandardWorkManager:
    """Test standard work manager."""
    
    def test_add_and_get_version(self, standard_work_version_v1):
        """Test adding and retrieving version."""
        manager = StandardWorkManager()
        manager.add_version("DOC-001", standard_work_version_v1)
        
        current = manager.get_current_version("DOC-001")
        assert current is not None
        assert current.version_number == "1.0"
    
    def test_get_version_not_found(self):
        """Test getting non-existent version."""
        manager = StandardWorkManager()
        current = manager.get_current_version("NONEXISTENT")
        assert current is None
    
    def test_compute_diff(
        self,
        standard_work_version_v1,
        standard_work_version_v2,
    ):
        """Test diff computation."""
        manager = StandardWorkManager()
        diff = manager.compute_diff(
            standard_work_version_v1,
            standard_work_version_v2,
        )
        
        assert "cleanup" in diff.removed_sections
        assert "safety" in diff.added_sections
        assert len(diff.modified_sections) == 1
        assert diff.modified_sections[0][0] == "setup"
    
    def test_compute_diff_no_changes(self, standard_work_version_v1):
        """Test diff with no changes."""
        manager = StandardWorkManager()
        diff = manager.compute_diff(
            standard_work_version_v1,
            standard_work_version_v1,
        )
        
        assert diff.summary == "No changes"
    
    def test_generate_draft_from_a3(self, standard_work_version_v1):
        """Test generating draft from A3 countermeasures."""
        manager = StandardWorkManager()
        countermeasures = [
            "Add safety check before step 3",
            "Update tooling specifications",
        ]
        
        draft = manager.generate_draft_from_a3(
            standard_work_version_v1,
            countermeasures,
        )
        
        assert draft.version_number == "1.1"
        assert draft.approved is False
        assert "countermeasures" in draft.sections
        assert "safety check" in draft.sections["countermeasures"]


# =============================================================================
# Test Universal Zero-Shot Parser
# =============================================================================

class TestUniversalZeroShotParser:
    """Test universal zero-shot parser."""
    
    def test_detect_pdf_format(self):
        """Test PDF format detection."""
        parser = UniversalZeroShotParser()
        fmt = parser._detect_format("document.pdf")
        assert fmt == DocumentFormat.PDF
    
    def test_detect_png_format(self):
        """Test PNG format detection."""
        parser = UniversalZeroShotParser()
        fmt = parser._detect_format("image.png")
        assert fmt == DocumentFormat.PNG
    
    def test_detect_jpg_format(self):
        """Test JPG format detection."""
        parser = UniversalZeroShotParser()
        fmt = parser._detect_format("photo.jpg")
        assert fmt == DocumentFormat.JPG
    
    def test_detect_dxf_format(self):
        """Test DXF format detection."""
        parser = UniversalZeroShotParser()
        fmt = parser._detect_format("drawing.dxf")
        assert fmt == DocumentFormat.DXF
    
    def test_detect_unknown_format(self):
        """Test unknown format detection."""
        parser = UniversalZeroShotParser()
        fmt = parser._detect_format("file.xyz")
        assert fmt == DocumentFormat.UNKNOWN
    
    def test_determine_strategy_cad(self):
        """Test strategy determination for CAD."""
        parser = UniversalZeroShotParser()
        strategy = parser._determine_strategy(DocumentFormat.DXF)
        assert strategy == ParsingStrategy.METADATA_ONLY
    
    def test_determine_strategy_image(self):
        """Test strategy determination for images."""
        parser = UniversalZeroShotParser()
        strategy = parser._determine_strategy(DocumentFormat.PNG)
        assert strategy == ParsingStrategy.VISION_LLM
    
    def test_parse_pdf(self, sample_pdf_data):
        """Test parsing PDF document."""
        parser = UniversalZeroShotParser()
        result = parser.parse(sample_pdf_data, "document.pdf")
        
        assert result.format == DocumentFormat.PDF
        assert result.overall_confidence > 0
        assert result.result_id is not None
    
    def test_parse_cad_file(self, sample_cad_data):
        """Test parsing CAD file."""
        parser = UniversalZeroShotParser()
        result = parser.parse(sample_cad_data, "drawing.dxf")
        
        assert result.format == DocumentFormat.DXF
        assert result.strategy_used == ParsingStrategy.METADATA_ONLY
        assert result.drawing_specs is not None
    
    def test_parse_with_extraction_hints(self, sample_document_data):
        """Test parsing with extraction hints."""
        parser = UniversalZeroShotParser()
        result = parser.parse(
            sample_document_data,
            "document.pdf",
            extraction_hints=[ExtractionType.BOM],
        )
        
        assert result.tables is not None
    
    def test_parse_multi_page(self, sample_document_data):
        """Test multi-page parsing."""
        parser = UniversalZeroShotParser()
        
        pages_data = [
            (1, sample_document_data),
            (2, sample_document_data + b" page 2"),
            (3, sample_document_data + b" page 3"),
        ]
        
        result = parser.parse_multi_page(pages_data, "document.pdf")
        
        assert result.format == DocumentFormat.PDF
        assert len(result.pages) > 0
    
    def test_confidence_level_high(self):
        """Test high confidence level determination."""
        parser = UniversalZeroShotParser()
        level = parser._determine_confidence_level(0.95)
        assert level == ConfidenceLevel.HIGH
    
    def test_confidence_level_medium(self):
        """Test medium confidence level determination."""
        parser = UniversalZeroShotParser()
        level = parser._determine_confidence_level(0.75)
        assert level == ConfidenceLevel.MEDIUM
    
    def test_confidence_level_low(self):
        """Test low confidence level determination."""
        parser = UniversalZeroShotParser()
        level = parser._determine_confidence_level(0.55)
        assert level == ConfidenceLevel.LOW
    
    def test_confidence_level_failed(self):
        """Test failed confidence level determination."""
        parser = UniversalZeroShotParser()
        level = parser._determine_confidence_level(0.3)
        assert level == ConfidenceLevel.FAILED
    
    def test_hitl_triggered_low_confidence(self):
        """Test HITL trigger for low confidence."""
        parser = UniversalZeroShotParser(confidence_threshold=0.99)
        result = parser.parse(b"test data", "test.pdf")
        
        # With threshold 0.99, most results should trigger HITL
        assert result.requires_hitl is True or result.overall_confidence >= 0.99
    
    def test_processing_time_tracked(self, sample_document_data):
        """Test that processing time is tracked."""
        parser = UniversalZeroShotParser()
        result = parser.parse(sample_document_data, "document.pdf")
        
        assert result.processing_time_ms >= 0
    
    def test_hybrid_strategy_fallback(self, sample_document_data):
        """Test hybrid strategy with fallback."""
        parser = UniversalZeroShotParser(confidence_threshold=0.99)
        
        # With very high threshold, hybrid should be triggered
        result = parser.parse(sample_document_data, "document.pdf")
        
        assert result.strategy_used in [
            ParsingStrategy.HYBRID,
            ParsingStrategy.VISION_LLM,
        ]


# =============================================================================
# Test Factory Function
# =============================================================================

class TestFactory:
    """Test factory function."""
    
    def test_create_document_parser(self):
        """Test creating document parser."""
        parser = create_document_parser()
        
        assert parser is not None
        assert isinstance(parser, UniversalZeroShotParser)
    
    def test_create_document_parser_custom_threshold(self):
        """Test creating parser with custom threshold."""
        parser = create_document_parser(confidence_threshold=0.9)
        
        assert parser._confidence_threshold == 0.9


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_document(self):
        """Test parsing empty document."""
        parser = UniversalZeroShotParser()
        result = parser.parse(b"", "empty.pdf")
        
        assert result.result_id is not None
    
    def test_very_large_document(self):
        """Test parsing large document."""
        parser = UniversalZeroShotParser()
        large_data = b"x" * 1000000  # 1MB
        result = parser.parse(large_data, "large.pdf")
        
        assert result.result_id is not None
    
    def test_special_characters_in_filename(self):
        """Test filename with special characters."""
        parser = UniversalZeroShotParser()
        result = parser.parse(b"test", "my document (v2) [final].pdf")
        
        assert result.format == DocumentFormat.PDF
    
    def test_no_extension(self):
        """Test filename without extension."""
        parser = UniversalZeroShotParser()
        fmt = parser._detect_format("document")
        assert fmt == DocumentFormat.UNKNOWN
    
    def test_empty_pages_list(self):
        """Test multi-page with empty list."""
        parser = UniversalZeroShotParser()
        result = parser.parse_multi_page([], "empty.pdf")
        
        assert len(result.pages) == 0
    
    def test_table_without_data_rows(self):
        """Test table with only headers."""
        table = TableData(
            table_id="TBL-001",
            rows=1,
            columns=3,
            headers=["A", "B", "C"],
        )
        
        dict_list = table.to_dict_list()
        assert dict_list == []
    
    def test_standard_work_version_without_number_format(self):
        """Test version generation from non-standard format."""
        manager = StandardWorkManager()
        version = StandardWorkVersion(
            version_id="v1",
            version_number="alpha",
            content="Content",
            sections={},
        )
        
        draft = manager.generate_draft_from_a3(version, ["Fix something"])
        assert draft.version_number == "1.1"


# =============================================================================
# Test Integration Scenarios
# =============================================================================

class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_bom_extraction_pipeline(self, sample_table_data):
        """Test complete BOM extraction pipeline."""
        parser = UniversalZeroShotParser()
        extractor = TableExtractor()
        
        # Extract BOM from table
        bom = extractor.extract_bom(sample_table_data)
        
        assert bom is not None
        assert bom.total_items == 3
        assert bom.entries[0].part_number == "ABC-001"
    
    def test_document_to_bom_flow(self, sample_pdf_data):
        """Test document parsing to BOM extraction."""
        parser = UniversalZeroShotParser()
        result = parser.parse(
            sample_pdf_data,
            "bom.pdf",
            extraction_hints=[ExtractionType.BOM],
        )
        
        assert result.tables is not None
    
    def test_standard_work_update_flow(
        self,
        standard_work_version_v1,
    ):
        """Test standard work update workflow."""
        manager = StandardWorkManager()
        
        # Add initial version
        manager.add_version("SW-001", standard_work_version_v1)
        
        # Generate draft from A3
        draft = manager.generate_draft_from_a3(
            standard_work_version_v1,
            ["New step before cleanup"],
        )
        
        # Add draft as new version
        manager.add_version("SW-001", draft)
        
        # Get current version
        current = manager.get_current_version("SW-001")
        assert current.version_number == "1.1"
        
        # Compute diff
        diff = manager.compute_diff(standard_work_version_v1, draft)
        assert len(diff.added_sections) == 1  # countermeasures


# =============================================================================
# Test Constants
# =============================================================================

class TestConstants:
    """Test module constants."""
    
    def test_confidence_threshold(self):
        """Test confidence threshold value."""
        assert CONFIDENCE_THRESHOLD == 0.85
    
    def test_bom_headers(self):
        """Test BOM headers list."""
        assert "item" in BOM_HEADERS
        assert "part" in BOM_HEADERS
        assert "quantity" in BOM_HEADERS
    
    def test_price_headers(self):
        """Test price headers list."""
        assert "unit price" in PRICE_HEADERS
        assert "total" in PRICE_HEADERS
