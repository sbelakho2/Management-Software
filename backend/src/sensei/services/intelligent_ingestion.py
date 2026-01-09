"""
Intelligent Data Ingestion 2.0 - Universal Zero-Shot Parser.

Advanced document parsing with Vision-LLM integration, hybrid OCR fallback,
multi-page handling, and high-fidelity table extraction.

Features:
- Vision-LLM for drawings and POs
- Hybrid OCR fallback (Tesseract/PaddleOCR style)
- Multi-page document stitching
- Table/BOM extraction
- Confidence-based HITL triggering
- Auto-standard update with diff analysis
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, BinaryIO
import math
import re
import uuid
import hashlib


# =============================================================================
# Enums
# =============================================================================

class DocumentFormat(Enum):
    """Supported document formats."""
    
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    DXF = "dxf"
    DWG = "dwg"
    UNKNOWN = "unknown"


class ParsingStrategy(Enum):
    """Document parsing strategy."""
    
    VISION_LLM = "vision_llm"
    OCR = "ocr"
    HYBRID = "hybrid"
    METADATA_ONLY = "metadata_only"


class ExtractionType(Enum):
    """Type of data extraction."""
    
    BOM = "bom"
    PRICE_TABLE = "price_table"
    DRAWING_SPECS = "drawing_specs"
    TEXT_CONTENT = "text_content"
    METADATA = "metadata"


class ConfidenceLevel(Enum):
    """Confidence level of parsing."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FAILED = "failed"


class HITLReason(Enum):
    """Reason for Human-in-the-Loop trigger."""
    
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_DATA = "ambiguous_data"
    MULTI_PAGE_CONFLICT = "multi_page_conflict"
    TABLE_STRUCTURE_UNCLEAR = "table_structure_unclear"
    OCR_ERRORS = "ocr_errors"
    MANUAL_OVERRIDE = "manual_override"


# =============================================================================
# Constants
# =============================================================================

CONFIDENCE_THRESHOLD = 0.85
FALLBACK_THRESHOLD = 0.6
SUPPORTED_FORMATS = [DocumentFormat.PDF, DocumentFormat.PNG, DocumentFormat.JPG, 
                     DocumentFormat.JPEG, DocumentFormat.DXF, DocumentFormat.DWG]

# Common BOM column headers
BOM_HEADERS = [
    "item", "part", "number", "qty", "quantity", "description", "material",
    "unit", "price", "cost", "weight", "finish", "supplier", "revision"
]

# Price table headers
PRICE_HEADERS = [
    "unit price", "total", "amount", "cost", "price", "subtotal", "tax",
    "discount", "extended", "each"
]


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class DocumentPage:
    """Single page of a document."""
    
    page_number: int
    content: str = ""
    tables: list["TableData"] = field(default_factory=list)
    raw_text: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableCell:
    """Single cell in a table."""
    
    row: int
    column: int
    value: str
    confidence: float = 1.0
    merged_rows: int = 1
    merged_cols: int = 1


@dataclass
class TableData:
    """Extracted table data."""
    
    table_id: str
    rows: int
    columns: int
    cells: list[TableCell] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    table_type: ExtractionType = ExtractionType.TEXT_CONTENT
    confidence: float = 0.0
    source_page: int = 1
    
    def get_cell(self, row: int, col: int) -> TableCell | None:
        """Get cell at position."""
        for cell in self.cells:
            if cell.row == row and cell.column == col:
                return cell
        return None
    
    def get_row_values(self, row: int) -> list[str]:
        """Get all values in a row."""
        row_cells = sorted(
            [c for c in self.cells if c.row == row],
            key=lambda x: x.column
        )
        return [c.value for c in row_cells]
    
    def to_dict_list(self) -> list[dict[str, str]]:
        """Convert to list of dictionaries."""
        if not self.headers:
            return []
        
        result = []
        max_row = max((c.row for c in self.cells), default=0)
        
        for row in range(1, max_row + 1):  # Skip header row
            row_dict = {}
            for col, header in enumerate(self.headers):
                cell = self.get_cell(row, col)
                row_dict[header] = cell.value if cell else ""
            result.append(row_dict)
        
        return result


@dataclass
class BOMEntry:
    """Bill of Materials entry."""
    
    item_number: str
    part_number: str = ""
    description: str = ""
    quantity: float = 1.0
    unit: str = "EA"
    material: str = ""
    unit_price: float | None = None
    extended_price: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedBOM:
    """Extracted Bill of Materials."""
    
    bom_id: str
    entries: list[BOMEntry] = field(default_factory=list)
    total_items: int = 0
    confidence: float = 0.0
    source_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def total_value(self) -> float:
        """Calculate total BOM value."""
        total = 0.0
        for entry in self.entries:
            if entry.extended_price is not None:
                total += entry.extended_price
            elif entry.unit_price is not None:
                total += entry.unit_price * entry.quantity
        return total


@dataclass
class DrawingSpec:
    """Extracted drawing specifications."""
    
    spec_id: str
    drawing_number: str = ""
    revision: str = ""
    title: str = ""
    material: str = ""
    finish: str = ""
    tolerances: dict[str, str] = field(default_factory=dict)
    dimensions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsingResult:
    """Result of document parsing."""
    
    result_id: str
    document_id: str
    format: DocumentFormat
    strategy_used: ParsingStrategy
    pages: list[DocumentPage] = field(default_factory=list)
    bom: ExtractedBOM | None = None
    drawing_specs: DrawingSpec | None = None
    tables: list[TableData] = field(default_factory=list)
    overall_confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    requires_hitl: bool = False
    hitl_reasons: list[HITLReason] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    parsed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StandardWorkVersion:
    """Version of standard work document."""
    
    version_id: str
    version_number: str
    content: str
    sections: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    approved: bool = False


@dataclass
class StandardWorkDiff:
    """Difference between standard work versions."""
    
    diff_id: str
    old_version_id: str
    new_version_id: str
    added_sections: list[str] = field(default_factory=list)
    removed_sections: list[str] = field(default_factory=list)
    modified_sections: list[tuple[str, str, str]] = field(default_factory=list)  # (section, old, new)
    summary: str = ""


# =============================================================================
# OCR Engine (Simulated)
# =============================================================================

class OCREngine:
    """
    Simulated OCR engine (Tesseract/PaddleOCR style).
    
    In production, this would integrate with actual OCR libraries.
    """
    
    def __init__(self):
        """Initialize OCR engine."""
        self._language = "eng"
    
    def extract_text(self, image_data: bytes) -> tuple[str, float]:
        """
        Extract text from image.
        
        Returns:
            Tuple of (text, confidence)
        """
        # Simulated OCR - in production would use actual OCR
        # Generate hash-based pseudo text for testing
        hash_val = hashlib.md5(image_data).hexdigest()
        
        # Simulate different confidence based on content
        confidence = 0.85 + (int(hash_val[0], 16) / 100)
        confidence = min(0.99, confidence)
        
        # Simulated extracted text
        text = f"OCR extracted content from document {hash_val[:8]}"
        
        return text, confidence
    
    def extract_structured(
        self,
        image_data: bytes,
    ) -> tuple[list[dict[str, Any]], float]:
        """
        Extract structured data (tables, lists) from image.
        
        Returns:
            Tuple of (structures, confidence)
        """
        hash_val = hashlib.md5(image_data).hexdigest()
        confidence = 0.80 + (int(hash_val[1], 16) / 80)
        
        structures = [
            {
                "type": "table",
                "rows": 5,
                "columns": 4,
                "data": [["Col1", "Col2", "Col3", "Col4"]],
            }
        ]
        
        return structures, confidence


# =============================================================================
# Vision LLM Parser
# =============================================================================

class VisionLLMParser:
    """
    Vision-LLM based document parser.
    
    Uses vision-language models for intelligent document understanding.
    In production, would integrate with LLaVA, Moondream2, etc.
    """
    
    def __init__(self, model_name: str = "vision-llm-7b"):
        """Initialize Vision LLM parser."""
        self._model_name = model_name
        self._loaded = True
    
    def is_available(self) -> bool:
        """Check if Vision LLM is available."""
        return self._loaded
    
    def parse_document(
        self,
        document_data: bytes,
        extraction_type: ExtractionType = ExtractionType.TEXT_CONTENT,
    ) -> tuple[dict[str, Any], float]:
        """
        Parse document using Vision LLM.
        
        Returns:
            Tuple of (parsed_data, confidence)
        """
        hash_val = hashlib.md5(document_data).hexdigest()
        
        # Simulate Vision LLM parsing
        base_confidence = 0.88 + (int(hash_val[2], 16) / 100)
        
        if extraction_type == ExtractionType.BOM:
            result = {
                "type": "bom",
                "items": [
                    {"item": "1", "part": "ABC-001", "qty": 10, "desc": "Widget A"},
                    {"item": "2", "part": "ABC-002", "qty": 5, "desc": "Widget B"},
                ],
            }
        elif extraction_type == ExtractionType.DRAWING_SPECS:
            result = {
                "type": "drawing",
                "drawing_number": f"DWG-{hash_val[:6].upper()}",
                "revision": "A",
                "material": "Aluminum 6061-T6",
            }
        else:
            result = {
                "type": "text",
                "content": f"Vision LLM extracted content from {hash_val[:8]}",
            }
        
        return result, min(0.99, base_confidence)
    
    def extract_tables(
        self,
        document_data: bytes,
    ) -> list[TableData]:
        """Extract tables from document."""
        hash_val = hashlib.md5(document_data).hexdigest()
        
        # Simulate table extraction
        table = TableData(
            table_id=f"TBL-{hash_val[:6]}",
            rows=5,
            columns=4,
            headers=["Item", "Part Number", "Quantity", "Description"],
            table_type=ExtractionType.BOM,
            confidence=0.90,
        )
        
        # Add cells
        for row in range(5):
            for col in range(4):
                table.cells.append(TableCell(
                    row=row,
                    column=col,
                    value=f"R{row}C{col}",
                    confidence=0.9,
                ))
        
        return [table]


# =============================================================================
# Table Extractor
# =============================================================================

class TableExtractor:
    """
    High-fidelity table extraction from documents.
    
    Handles BOMs, price tables, and complex multi-row tables.
    """
    
    def __init__(self):
        """Initialize table extractor."""
        self._bom_patterns = re.compile(
            r'(?i)(bom|bill\s+of\s+materials|parts\s+list)',
        )
        self._price_patterns = re.compile(
            r'(?i)(price|cost|total|amount|subtotal)',
        )
    
    def _identify_table_type(self, headers: list[str]) -> ExtractionType:
        """Identify table type from headers."""
        headers_lower = [h.lower() for h in headers]
        
        # Check for BOM
        bom_matches = sum(
            1 for h in headers_lower
            if any(bom_h in h for bom_h in BOM_HEADERS)
        )
        
        # Check for price table
        price_matches = sum(
            1 for h in headers_lower
            if any(price_h in h for price_h in PRICE_HEADERS)
        )
        
        if bom_matches >= 2:
            return ExtractionType.BOM
        elif price_matches >= 2:
            return ExtractionType.PRICE_TABLE
        else:
            return ExtractionType.TEXT_CONTENT
    
    def _parse_number(self, value: str) -> float | None:
        """Parse numeric value from string."""
        if not value:
            return None
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,€£]', '', value.strip())
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def extract_bom(self, table: TableData) -> ExtractedBOM | None:
        """Extract BOM from table data."""
        if not table.headers:
            return None
        
        entries = []
        headers_lower = [h.lower() for h in table.headers]
        
        # Map headers to fields
        field_map = {}
        for i, h in enumerate(headers_lower):
            if any(x in h for x in ["item", "#", "no"]):
                field_map["item_number"] = i
            elif any(x in h for x in ["part", "p/n", "pn"]):
                field_map["part_number"] = i
            elif any(x in h for x in ["desc", "description"]):
                field_map["description"] = i
            elif any(x in h for x in ["qty", "quantity"]):
                field_map["quantity"] = i
            elif any(x in h for x in ["unit", "uom"]):
                field_map["unit"] = i
            elif any(x in h for x in ["material", "mat"]):
                field_map["material"] = i
            elif "price" in h or "cost" in h:
                if "unit" in h:
                    field_map["unit_price"] = i
                elif "ext" in h or "total" in h:
                    field_map["extended_price"] = i
        
        # Extract entries
        for row_data in table.to_dict_list():
            entry = BOMEntry(
                item_number=row_data.get(table.headers[field_map.get("item_number", 0)], ""),
            )
            
            if "part_number" in field_map:
                entry.part_number = row_data.get(table.headers[field_map["part_number"]], "")
            if "description" in field_map:
                entry.description = row_data.get(table.headers[field_map["description"]], "")
            if "quantity" in field_map:
                qty = self._parse_number(row_data.get(table.headers[field_map["quantity"]], "1"))
                entry.quantity = qty if qty is not None else 1.0
            if "unit" in field_map:
                entry.unit = row_data.get(table.headers[field_map["unit"]], "EA")
            if "material" in field_map:
                entry.material = row_data.get(table.headers[field_map["material"]], "")
            if "unit_price" in field_map:
                entry.unit_price = self._parse_number(
                    row_data.get(table.headers[field_map["unit_price"]], "")
                )
            if "extended_price" in field_map:
                entry.extended_price = self._parse_number(
                    row_data.get(table.headers[field_map["extended_price"]], "")
                )
            
            if entry.item_number or entry.part_number:
                entries.append(entry)
        
        return ExtractedBOM(
            bom_id=str(uuid.uuid4()),
            entries=entries,
            total_items=len(entries),
            confidence=table.confidence,
            source_pages=[table.source_page],
        )
    
    def merge_multi_page_tables(
        self,
        tables: list[TableData],
    ) -> list[TableData]:
        """Merge tables that span multiple pages."""
        if len(tables) <= 1:
            return tables
        
        merged = []
        current_merge: TableData | None = None
        
        for table in sorted(tables, key=lambda t: t.source_page):
            if current_merge is None:
                current_merge = table
            elif (
                table.table_type == current_merge.table_type and
                table.headers == current_merge.headers
            ):
                # Merge tables
                row_offset = current_merge.rows
                for cell in table.cells:
                    if cell.row > 0:  # Skip header row
                        current_merge.cells.append(TableCell(
                            row=cell.row + row_offset - 1,
                            column=cell.column,
                            value=cell.value,
                            confidence=cell.confidence,
                        ))
                current_merge.rows += table.rows - 1  # Exclude header
            else:
                merged.append(current_merge)
                current_merge = table
        
        if current_merge:
            merged.append(current_merge)
        
        return merged


# =============================================================================
# Multi-Page Stitcher
# =============================================================================

class MultiPageStitcher:
    """
    Handle multi-page document stitching.
    
    Detects and joins content that spans multiple pages.
    """
    
    def __init__(self):
        """Initialize stitcher."""
        self._continuation_patterns = [
            re.compile(r'(?i)continued\s+(on\s+)?next\s+page'),
            re.compile(r'(?i)see\s+page\s+\d+'),
            re.compile(r'(?i)continued\s+from\s+(page\s+)?\d+'),
            re.compile(r'\.\.\.$'),  # Ellipsis at end
        ]
    
    def detect_continuation(self, page: DocumentPage) -> bool:
        """Detect if page continues to next page."""
        content = page.content + page.raw_text
        
        for pattern in self._continuation_patterns:
            if pattern.search(content):
                return True
        
        return False
    
    def stitch_pages(
        self,
        pages: list[DocumentPage],
    ) -> list[DocumentPage]:
        """Stitch together continued pages."""
        if len(pages) <= 1:
            return pages
        
        stitched = []
        current_group: list[DocumentPage] = []
        
        for page in sorted(pages, key=lambda p: p.page_number):
            current_group.append(page)
            
            if not self.detect_continuation(page):
                # Merge group
                if len(current_group) == 1:
                    stitched.append(current_group[0])
                else:
                    merged = self._merge_page_group(current_group)
                    stitched.append(merged)
                current_group = []
        
        # Handle remaining
        if current_group:
            if len(current_group) == 1:
                stitched.append(current_group[0])
            else:
                merged = self._merge_page_group(current_group)
                stitched.append(merged)
        
        return stitched
    
    def _merge_page_group(self, pages: list[DocumentPage]) -> DocumentPage:
        """Merge a group of pages into one."""
        merged = DocumentPage(
            page_number=pages[0].page_number,
            content="\n\n".join(p.content for p in pages),
            raw_text="\n\n".join(p.raw_text for p in pages),
            confidence=sum(p.confidence for p in pages) / len(pages),
        )
        
        # Merge tables
        for page in pages:
            merged.tables.extend(page.tables)
        
        # Merge metadata
        for page in pages:
            merged.metadata.update(page.metadata)
        merged.metadata["merged_pages"] = [p.page_number for p in pages]
        
        return merged


# =============================================================================
# Standard Work Manager
# =============================================================================

class StandardWorkManager:
    """
    Manage standard work documents and auto-updates.
    """
    
    def __init__(self):
        """Initialize manager."""
        self._versions: dict[str, list[StandardWorkVersion]] = {}
    
    def get_current_version(self, doc_id: str) -> StandardWorkVersion | None:
        """Get current version of standard work."""
        versions = self._versions.get(doc_id, [])
        if not versions:
            return None
        return versions[-1]
    
    def add_version(self, doc_id: str, version: StandardWorkVersion):
        """Add new version."""
        if doc_id not in self._versions:
            self._versions[doc_id] = []
        self._versions[doc_id].append(version)
    
    def compute_diff(
        self,
        old_version: StandardWorkVersion,
        new_version: StandardWorkVersion,
    ) -> StandardWorkDiff:
        """Compute differences between versions."""
        old_sections = set(old_version.sections.keys())
        new_sections = set(new_version.sections.keys())
        
        added = list(new_sections - old_sections)
        removed = list(old_sections - new_sections)
        
        modified = []
        for section in old_sections & new_sections:
            if old_version.sections[section] != new_version.sections[section]:
                modified.append((
                    section,
                    old_version.sections[section],
                    new_version.sections[section],
                ))
        
        # Generate summary
        changes = []
        if added:
            changes.append(f"Added {len(added)} sections")
        if removed:
            changes.append(f"Removed {len(removed)} sections")
        if modified:
            changes.append(f"Modified {len(modified)} sections")
        
        summary = "; ".join(changes) if changes else "No changes"
        
        return StandardWorkDiff(
            diff_id=str(uuid.uuid4()),
            old_version_id=old_version.version_id,
            new_version_id=new_version.version_id,
            added_sections=added,
            removed_sections=removed,
            modified_sections=modified,
            summary=summary,
        )
    
    def generate_draft_from_a3(
        self,
        current_version: StandardWorkVersion,
        a3_countermeasures: list[str],
    ) -> StandardWorkVersion:
        """Generate new draft from A3 countermeasures."""
        # Parse current version number
        current_num = current_version.version_number
        match = re.match(r'(\d+)\.(\d+)', current_num)
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            new_version_num = f"{major}.{minor + 1}"
        else:
            new_version_num = "1.1"
        
        # Create new sections with countermeasures integrated
        new_sections = current_version.sections.copy()
        
        # Add countermeasures section
        countermeasure_content = "\n".join(
            f"- {cm}" for cm in a3_countermeasures
        )
        new_sections["countermeasures"] = countermeasure_content
        
        # Update content
        new_content = current_version.content + "\n\n## New Countermeasures\n" + countermeasure_content
        
        return StandardWorkVersion(
            version_id=str(uuid.uuid4()),
            version_number=new_version_num,
            content=new_content,
            sections=new_sections,
            approved=False,
        )


# =============================================================================
# Universal Zero-Shot Parser
# =============================================================================

class UniversalZeroShotParser:
    """
    Universal document parser with zero-shot capabilities.
    
    Combines Vision-LLM, OCR, and intelligent fallback strategies.
    """
    
    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        fallback_threshold: float = FALLBACK_THRESHOLD,
    ):
        """Initialize parser."""
        self._confidence_threshold = confidence_threshold
        self._fallback_threshold = fallback_threshold
        
        self._vision_llm = VisionLLMParser()
        self._ocr_engine = OCREngine()
        self._table_extractor = TableExtractor()
        self._page_stitcher = MultiPageStitcher()
        self._standard_work_manager = StandardWorkManager()
    
    def _detect_format(self, filename: str) -> DocumentFormat:
        """Detect document format from filename."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ""
        
        format_map = {
            "pdf": DocumentFormat.PDF,
            "png": DocumentFormat.PNG,
            "jpg": DocumentFormat.JPG,
            "jpeg": DocumentFormat.JPEG,
            "dxf": DocumentFormat.DXF,
            "dwg": DocumentFormat.DWG,
        }
        
        return format_map.get(ext, DocumentFormat.UNKNOWN)
    
    def _determine_strategy(
        self,
        doc_format: DocumentFormat,
    ) -> ParsingStrategy:
        """Determine parsing strategy based on format."""
        if doc_format in [DocumentFormat.DXF, DocumentFormat.DWG]:
            return ParsingStrategy.METADATA_ONLY
        
        if self._vision_llm.is_available():
            return ParsingStrategy.VISION_LLM
        
        return ParsingStrategy.OCR
    
    def _parse_with_vision_llm(
        self,
        document_data: bytes,
        extraction_type: ExtractionType,
    ) -> tuple[dict[str, Any], float]:
        """Parse using Vision LLM."""
        return self._vision_llm.parse_document(document_data, extraction_type)
    
    def _parse_with_ocr(
        self,
        document_data: bytes,
    ) -> tuple[str, list[dict[str, Any]], float]:
        """Parse using OCR."""
        text, text_conf = self._ocr_engine.extract_text(document_data)
        structures, struct_conf = self._ocr_engine.extract_structured(document_data)
        
        avg_conf = (text_conf + struct_conf) / 2
        
        return text, structures, avg_conf
    
    def _apply_hybrid_strategy(
        self,
        document_data: bytes,
        vision_result: dict[str, Any],
        vision_confidence: float,
    ) -> tuple[dict[str, Any], float]:
        """Apply hybrid strategy combining Vision LLM and OCR."""
        if vision_confidence >= self._confidence_threshold:
            return vision_result, vision_confidence
        
        # Fall back to OCR
        text, structures, ocr_conf = self._parse_with_ocr(document_data)
        
        # Combine results
        combined = vision_result.copy()
        combined["ocr_text"] = text
        combined["ocr_structures"] = structures
        
        # Weighted average of confidences
        combined_conf = (vision_confidence * 0.6 + ocr_conf * 0.4)
        
        return combined, combined_conf
    
    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level from score."""
        if confidence >= 0.9:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.5:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.FAILED
    
    def _check_hitl_required(
        self,
        confidence: float,
        parsing_result: ParsingResult,
    ) -> tuple[bool, list[HITLReason]]:
        """Check if HITL is required."""
        reasons = []
        
        if confidence < self._confidence_threshold:
            reasons.append(HITLReason.LOW_CONFIDENCE)
        
        if parsing_result.errors:
            reasons.append(HITLReason.OCR_ERRORS)
        
        # Check for ambiguous tables
        for table in parsing_result.tables:
            if table.confidence < 0.7:
                reasons.append(HITLReason.TABLE_STRUCTURE_UNCLEAR)
                break
        
        return len(reasons) > 0, reasons
    
    def parse(
        self,
        document_data: bytes,
        filename: str = "document.pdf",
        extraction_hints: list[ExtractionType] | None = None,
    ) -> ParsingResult:
        """
        Parse document using appropriate strategy.
        
        Args:
            document_data: Raw document bytes
            filename: Original filename for format detection
            extraction_hints: Hints about what to extract
        
        Returns:
            ParsingResult with extracted data
        """
        import time
        start_time = time.time()
        
        result = ParsingResult(
            result_id=str(uuid.uuid4()),
            document_id=hashlib.sha256(document_data).hexdigest()[:16],
            format=self._detect_format(filename),
            strategy_used=ParsingStrategy.HYBRID,
        )
        
        # Determine strategy
        strategy = self._determine_strategy(result.format)
        result.strategy_used = strategy
        
        if strategy == ParsingStrategy.METADATA_ONLY:
            # Only extract metadata for CAD files
            result.drawing_specs = DrawingSpec(
                spec_id=str(uuid.uuid4()),
                metadata={"format": result.format.value, "size": len(document_data)},
            )
            result.overall_confidence = 0.9
        else:
            # Parse with Vision LLM first
            extraction_type = (
                extraction_hints[0] if extraction_hints
                else ExtractionType.TEXT_CONTENT
            )
            
            vision_result, vision_conf = self._parse_with_vision_llm(
                document_data, extraction_type
            )
            
            # Apply hybrid if needed
            if vision_conf < self._confidence_threshold:
                combined, combined_conf = self._apply_hybrid_strategy(
                    document_data, vision_result, vision_conf
                )
                result.overall_confidence = combined_conf
                result.strategy_used = ParsingStrategy.HYBRID
            else:
                result.overall_confidence = vision_conf
            
            # Extract tables
            tables = self._vision_llm.extract_tables(document_data)
            
            # Merge multi-page tables
            tables = self._table_extractor.merge_multi_page_tables(tables)
            result.tables = tables
            
            # Extract BOM if applicable
            for table in tables:
                if table.table_type == ExtractionType.BOM:
                    bom = self._table_extractor.extract_bom(table)
                    if bom:
                        result.bom = bom
                        break
            
            # Extract drawing specs if vision result has them
            if vision_result.get("type") == "drawing":
                result.drawing_specs = DrawingSpec(
                    spec_id=str(uuid.uuid4()),
                    drawing_number=vision_result.get("drawing_number", ""),
                    revision=vision_result.get("revision", ""),
                    material=vision_result.get("material", ""),
                )
            
            # Create page
            page = DocumentPage(
                page_number=1,
                content=vision_result.get("content", ""),
                tables=tables,
                confidence=result.overall_confidence,
            )
            result.pages = [page]
        
        # Determine confidence level
        result.confidence_level = self._determine_confidence_level(
            result.overall_confidence
        )
        
        # Check HITL
        result.requires_hitl, result.hitl_reasons = self._check_hitl_required(
            result.overall_confidence, result
        )
        
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def parse_multi_page(
        self,
        pages_data: list[tuple[int, bytes]],
        filename: str = "document.pdf",
    ) -> ParsingResult:
        """Parse multi-page document."""
        all_pages = []
        all_tables = []
        confidences = []
        
        for page_num, page_data in pages_data:
            page_result = self.parse(page_data, filename)
            
            for page in page_result.pages:
                page.page_number = page_num
                all_pages.append(page)
            
            for table in page_result.tables:
                table.source_page = page_num
                all_tables.append(table)
            
            confidences.append(page_result.overall_confidence)
        
        # Stitch pages
        stitched_pages = self._page_stitcher.stitch_pages(all_pages)
        
        # Merge tables across pages
        merged_tables = self._table_extractor.merge_multi_page_tables(all_tables)
        
        # Build result
        result = ParsingResult(
            result_id=str(uuid.uuid4()),
            document_id=hashlib.sha256(
                b"".join(d for _, d in pages_data)
            ).hexdigest()[:16],
            format=self._detect_format(filename),
            strategy_used=ParsingStrategy.HYBRID,
            pages=stitched_pages,
            tables=merged_tables,
            overall_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        )
        
        # Extract BOM from merged tables
        for table in merged_tables:
            if table.table_type == ExtractionType.BOM:
                result.bom = self._table_extractor.extract_bom(table)
                break
        
        result.confidence_level = self._determine_confidence_level(
            result.overall_confidence
        )
        result.requires_hitl, result.hitl_reasons = self._check_hitl_required(
            result.overall_confidence, result
        )
        
        return result


# =============================================================================
# Factory Function
# =============================================================================

def create_document_parser(
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    fallback_threshold: float = FALLBACK_THRESHOLD,
) -> UniversalZeroShotParser:
    """Create and initialize document parser."""
    return UniversalZeroShotParser(
        confidence_threshold=confidence_threshold,
        fallback_threshold=fallback_threshold,
    )
