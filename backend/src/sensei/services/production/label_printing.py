"""
Label Printing & Barcode Standards Service.

Provides:
- Configurable label templates (4x6, A4, Butterfly)
- Barcode standards (GS1-128, DataMatrix, customer-specific)
- Scanner error handling workflows
- Label generation and printing queue
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from dataclasses import dataclass, field
from uuid import UUID, uuid4
import logging
import re
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


class LabelSize(str, Enum):
    """Standard label sizes."""
    THERMAL_4X6 = "4x6"  # 4x6 inch thermal labels
    THERMAL_4X2 = "4x2"  # 4x2 inch thermal labels
    THERMAL_2X1 = "2x1"  # 2x1 inch thermal labels
    A4_SHEET = "a4"  # A4 sheet labels
    BUTTERFLY = "butterfly"  # Small part butterfly labels
    CUSTOM = "custom"


class BarcodeType(str, Enum):
    """Barcode types supported."""
    CODE128 = "code128"
    CODE39 = "code39"
    GS1_128 = "gs1-128"
    DATAMATRIX = "datamatrix"
    QR_CODE = "qr_code"
    EAN13 = "ean13"
    UPC_A = "upc_a"
    ITF14 = "itf14"
    PDF417 = "pdf417"


class LabelType(str, Enum):
    """Types of labels."""
    PART_LABEL = "part_label"
    LOT_LABEL = "lot_label"
    SERIAL_LABEL = "serial_label"
    SHIPPING_LABEL = "shipping_label"
    LOCATION_LABEL = "location_label"
    WORK_ORDER_LABEL = "work_order_label"
    RECEIVING_LABEL = "receiving_label"
    INSPECTION_LABEL = "inspection_label"
    PACKING_LIST = "packing_list"


class PrinterType(str, Enum):
    """Types of label printers."""
    THERMAL_DIRECT = "thermal_direct"
    THERMAL_TRANSFER = "thermal_transfer"
    INKJET = "inkjet"
    LASER = "laser"


class PrintStatus(str, Enum):
    """Print job status."""
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanErrorType(str, Enum):
    """Types of scan errors."""
    UNRECOGNIZED = "unrecognized"  # Barcode not in system
    WRONG_TYPE = "wrong_type"  # Expected 2D, got 1D
    DAMAGED = "damaged"  # Partial read
    EXPIRED = "expired"  # Lot/item expired
    QUARANTINED = "quarantined"  # Item in quarantine
    ALREADY_CONSUMED = "already_consumed"  # Already used
    WRONG_LOCATION = "wrong_location"  # Scanned in wrong location


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class LabelTemplate:
    """A label template definition."""
    id: str
    name: str
    label_type: LabelType
    size: LabelSize
    width_mm: float
    height_mm: float
    barcode_type: BarcodeType = BarcodeType.DATAMATRIX
    fields: list[dict[str, Any]] = field(default_factory=list)
    layout_zpl: str | None = None  # ZPL for Zebra printers
    layout_html: str | None = None  # HTML for PDF generation
    is_customer_specific: bool = False
    customer_id: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Printer:
    """A configured printer."""
    id: str
    name: str
    printer_type: PrinterType
    connection_string: str  # IP:port or USB path
    default_template_id: str | None = None
    supported_sizes: list[LabelSize] = field(default_factory=list)
    supported_barcode_types: list[BarcodeType] = field(default_factory=list)
    is_online: bool = True
    location_id: str | None = None
    dpi: int = 203  # Common: 203, 300, 600
    last_heartbeat: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PrintJob:
    """A print job in the queue."""
    id: str
    printer_id: str
    template_id: str
    label_type: LabelType
    status: PrintStatus = PrintStatus.QUEUED
    copies: int = 1
    data: dict[str, Any] = field(default_factory=dict)
    barcode_data: str | None = None
    requested_by: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    priority: int = 0  # Higher = more urgent


@dataclass
class BarcodeValidation:
    """Barcode validation result."""
    is_valid: bool
    barcode_type: BarcodeType | None = None
    raw_data: str | None = None
    parsed_data: dict[str, Any] = field(default_factory=dict)
    entity_type: str | None = None  # lot, serial, part, etc.
    entity_id: str | None = None
    error_type: ScanErrorType | None = None
    error_message: str | None = None
    recovery_actions: list[str] = field(default_factory=list)


@dataclass
class GS1Element:
    """A GS1 Application Identifier element."""
    ai: str  # Application Identifier
    name: str
    value: str
    length: int


@dataclass
class ScanRecoveryWorkflow:
    """A recovery workflow for scan errors."""
    id: str
    error_type: ScanErrorType
    workflow_steps: list[dict[str, Any]] = field(default_factory=list)
    auto_actions: list[str] = field(default_factory=list)
    requires_supervisor: bool = False
    timeout_seconds: int = 300


# =============================================================================
# LABEL PRINTING SERVICE
# =============================================================================


class LabelPrintingService:
    """
    Label Printing & Barcode Standards Service.
    
    Provides:
    - Template management for various label sizes
    - Barcode generation (GS1-128, DataMatrix, etc.)
    - Print queue management
    - Scanner error handling with recovery workflows
    """
    
    # GS1 Application Identifiers
    GS1_AIS = {
        "00": ("SSCC", 18),  # Serial Shipping Container Code
        "01": ("GTIN", 14),  # Global Trade Item Number
        "02": ("CONTENT", 14),  # GTIN of contained items
        "10": ("BATCH_LOT", 20),  # Batch or Lot Number
        "11": ("PROD_DATE", 6),  # Production Date YYMMDD
        "12": ("DUE_DATE", 6),  # Due Date YYMMDD
        "13": ("PACK_DATE", 6),  # Packaging Date YYMMDD
        "15": ("BEST_BEFORE", 6),  # Best Before Date YYMMDD
        "17": ("EXPIRY", 6),  # Expiration Date YYMMDD
        "21": ("SERIAL", 20),  # Serial Number
        "30": ("VAR_COUNT", 8),  # Variable Count
        "37": ("COUNT", 8),  # Count of trade items
        "91": ("INTERNAL", 90),  # Company internal info
        "92": ("INTERNAL_2", 90),  # Company internal info
    }
    
    def __init__(self):
        # Storage
        self._templates: dict[str, LabelTemplate] = {}
        self._printers: dict[str, Printer] = {}
        self._print_jobs: list[PrintJob] = []
        self._recovery_workflows: dict[str, ScanRecoveryWorkflow] = {}
        
        # Registered barcodes cache (backed by production registry integration)
        self._registered_barcodes: dict[str, dict[str, Any]] = {}
        
        # Initialize default templates
        self._init_default_templates()
        self._init_recovery_workflows()
    
    def _init_default_templates(self) -> None:
        """Initialize default label templates."""
        # 4x6 Shipping Label
        self.create_template(
            name="Standard Shipping Label",
            label_type=LabelType.SHIPPING_LABEL,
            size=LabelSize.THERMAL_4X6,
            width_mm=101.6,
            height_mm=152.4,
            barcode_type=BarcodeType.GS1_128,
            fields=[
                {"name": "ship_to_name", "label": "Ship To", "type": "text", "x": 5, "y": 5},
                {"name": "ship_to_address", "label": "Address", "type": "text", "x": 5, "y": 15},
                {"name": "po_number", "label": "PO#", "type": "text", "x": 5, "y": 35},
                {"name": "part_number", "label": "Part#", "type": "text", "x": 5, "y": 45},
                {"name": "quantity", "label": "Qty", "type": "text", "x": 5, "y": 55},
                {"name": "barcode", "label": "", "type": "barcode", "x": 5, "y": 70},
            ],
        )
        
        # 4x2 Part Label
        self.create_template(
            name="Standard Part Label",
            label_type=LabelType.PART_LABEL,
            size=LabelSize.THERMAL_4X2,
            width_mm=101.6,
            height_mm=50.8,
            barcode_type=BarcodeType.DATAMATRIX,
            fields=[
                {"name": "part_number", "label": "P/N", "type": "text", "x": 5, "y": 5},
                {"name": "description", "label": "Desc", "type": "text", "x": 5, "y": 15},
                {"name": "barcode", "label": "", "type": "barcode", "x": 60, "y": 5},
            ],
        )
        
        # 2x1 Butterfly Label (small parts)
        self.create_template(
            name="Butterfly Small Part Label",
            label_type=LabelType.PART_LABEL,
            size=LabelSize.BUTTERFLY,
            width_mm=50.8,
            height_mm=25.4,
            barcode_type=BarcodeType.DATAMATRIX,
            fields=[
                {"name": "part_number", "label": "", "type": "text", "x": 2, "y": 2, "font_size": 6},
                {"name": "barcode", "label": "", "type": "barcode", "x": 2, "y": 10, "size": 12},
            ],
        )
        
        # Lot Label with GS1-128
        self.create_template(
            name="Lot Traceability Label",
            label_type=LabelType.LOT_LABEL,
            size=LabelSize.THERMAL_4X2,
            width_mm=101.6,
            height_mm=50.8,
            barcode_type=BarcodeType.GS1_128,
            fields=[
                {"name": "part_number", "label": "P/N", "type": "text"},
                {"name": "lot_number", "label": "Lot", "type": "text"},
                {"name": "quantity", "label": "Qty", "type": "text"},
                {"name": "expiry_date", "label": "Exp", "type": "text"},
                {"name": "barcode", "label": "", "type": "barcode"},
            ],
        )
        
        # Serial Number Label
        self.create_template(
            name="Serial Number Label",
            label_type=LabelType.SERIAL_LABEL,
            size=LabelSize.THERMAL_2X1,
            width_mm=50.8,
            height_mm=25.4,
            barcode_type=BarcodeType.DATAMATRIX,
            fields=[
                {"name": "serial_number", "label": "S/N", "type": "text"},
                {"name": "barcode", "label": "", "type": "barcode"},
            ],
        )
    
    def _init_recovery_workflows(self) -> None:
        """Initialize default scan error recovery workflows."""
        # Unrecognized barcode
        self.create_recovery_workflow(
            error_type=ScanErrorType.UNRECOGNIZED,
            workflow_steps=[
                {"step": 1, "action": "verify_barcode_readable", "instruction": "Ensure barcode is clean and undamaged"},
                {"step": 2, "action": "try_manual_entry", "instruction": "Enter the number manually if visible"},
                {"step": 3, "action": "check_alternative_label", "instruction": "Look for alternative label on item"},
                {"step": 4, "action": "escalate", "instruction": "Contact supervisor if issue persists"},
            ],
        )
        
        # Wrong barcode type
        self.create_recovery_workflow(
            error_type=ScanErrorType.WRONG_TYPE,
            workflow_steps=[
                {"step": 1, "action": "identify_correct_label", "instruction": "Locate the correct barcode type (2D vs 1D)"},
                {"step": 2, "action": "switch_scanner_mode", "instruction": "Switch scanner to correct mode if available"},
                {"step": 3, "action": "use_different_scanner", "instruction": "Use appropriate scanner for barcode type"},
            ],
        )
        
        # Damaged barcode
        self.create_recovery_workflow(
            error_type=ScanErrorType.DAMAGED,
            workflow_steps=[
                {"step": 1, "action": "clean_barcode", "instruction": "Clean barcode surface"},
                {"step": 2, "action": "adjust_angle", "instruction": "Try scanning at different angles"},
                {"step": 3, "action": "manual_entry", "instruction": "Use backup human-readable text"},
                {"step": 4, "action": "reprint_label", "instruction": "Request label reprint if needed"},
            ],
        )
        
        # Quarantined item
        self.create_recovery_workflow(
            error_type=ScanErrorType.QUARANTINED,
            workflow_steps=[
                {"step": 1, "action": "stop", "instruction": "Do not use this item"},
                {"step": 2, "action": "notify_quality", "instruction": "Contact Quality department"},
                {"step": 3, "action": "document", "instruction": "Document location where item was found"},
            ],
            requires_supervisor=True,
        )
        
        # Expired item
        self.create_recovery_workflow(
            error_type=ScanErrorType.EXPIRED,
            workflow_steps=[
                {"step": 1, "action": "stop", "instruction": "Do not use this item"},
                {"step": 2, "action": "quarantine", "instruction": "Move to quarantine area"},
                {"step": 3, "action": "notify", "instruction": "Notify inventory control"},
            ],
            requires_supervisor=True,
        )
    
    # =========================================================================
    # TEMPLATE MANAGEMENT
    # =========================================================================
    
    def create_template(
        self,
        name: str,
        label_type: LabelType,
        size: LabelSize,
        width_mm: float,
        height_mm: float,
        barcode_type: BarcodeType = BarcodeType.DATAMATRIX,
        fields: list[dict[str, Any]] | None = None,
        layout_zpl: str | None = None,
        layout_html: str | None = None,
        is_customer_specific: bool = False,
        customer_id: str | None = None,
    ) -> LabelTemplate:
        """Create a label template."""
        template_id = str(uuid4())
        
        template = LabelTemplate(
            id=template_id,
            name=name,
            label_type=label_type,
            size=size,
            width_mm=width_mm,
            height_mm=height_mm,
            barcode_type=barcode_type,
            fields=fields or [],
            layout_zpl=layout_zpl,
            layout_html=layout_html,
            is_customer_specific=is_customer_specific,
            customer_id=customer_id,
        )
        
        self._templates[template_id] = template
        logger.info(f"Created template: {name}")
        return template
    
    def get_template(self, template_id: str) -> LabelTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_templates(
        self,
        label_type: LabelType | None = None,
        size: LabelSize | None = None,
        customer_id: str | None = None,
    ) -> list[LabelTemplate]:
        """Get templates, optionally filtered."""
        templates = list(self._templates.values())
        
        if label_type:
            templates = [t for t in templates if t.label_type == label_type]
        
        if size:
            templates = [t for t in templates if t.size == size]
        
        if customer_id:
            templates = [t for t in templates if t.customer_id == customer_id or not t.is_customer_specific]
        
        return templates
    
    def update_template(
        self,
        template_id: str,
        fields: list[dict[str, Any]] | None = None,
        layout_zpl: str | None = None,
        layout_html: str | None = None,
    ) -> LabelTemplate | None:
        """Update a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        if fields is not None:
            template.fields = fields
        if layout_zpl is not None:
            template.layout_zpl = layout_zpl
        if layout_html is not None:
            template.layout_html = layout_html
        
        template.updated_at = datetime.now(timezone.utc)
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template (soft delete)."""
        template = self._templates.get(template_id)
        if not template:
            return False
        
        template.is_active = False
        template.updated_at = datetime.now(timezone.utc)
        return True
    
    # =========================================================================
    # PRINTER MANAGEMENT
    # =========================================================================
    
    def register_printer(
        self,
        name: str,
        printer_type: PrinterType,
        connection_string: str,
        supported_sizes: list[LabelSize] | None = None,
        supported_barcode_types: list[BarcodeType] | None = None,
        location_id: str | None = None,
        dpi: int = 203,
    ) -> Printer:
        """Register a label printer."""
        printer_id = str(uuid4())
        
        printer = Printer(
            id=printer_id,
            name=name,
            printer_type=printer_type,
            connection_string=connection_string,
            supported_sizes=supported_sizes or [LabelSize.THERMAL_4X6, LabelSize.THERMAL_4X2],
            supported_barcode_types=supported_barcode_types or [BarcodeType.DATAMATRIX, BarcodeType.GS1_128],
            location_id=location_id,
            dpi=dpi,
        )
        
        self._printers[printer_id] = printer
        logger.info(f"Registered printer: {name}")
        return printer
    
    def get_printer(self, printer_id: str) -> Printer | None:
        """Get a printer by ID."""
        return self._printers.get(printer_id)
    
    def get_printers(
        self,
        location_id: str | None = None,
        is_online: bool | None = None,
    ) -> list[Printer]:
        """Get all printers, optionally filtered."""
        printers = list(self._printers.values())
        
        if location_id:
            printers = [p for p in printers if p.location_id == location_id]
        
        if is_online is not None:
            printers = [p for p in printers if p.is_online == is_online]
        
        return printers
    
    def update_printer_status(
        self,
        printer_id: str,
        is_online: bool,
    ) -> Printer | None:
        """Update printer online status."""
        printer = self._printers.get(printer_id)
        if not printer:
            return None
        
        printer.is_online = is_online
        printer.last_heartbeat = datetime.now(timezone.utc)
        return printer
    
    # =========================================================================
    # BARCODE GENERATION
    # =========================================================================
    
    def generate_gs1_128(
        self,
        gtin: str | None = None,
        lot_number: str | None = None,
        serial_number: str | None = None,
        expiry_date: datetime | None = None,
        quantity: int | None = None,
        sscc: str | None = None,
        internal_data: str | None = None,
    ) -> str:
        """Generate a GS1-128 barcode string."""
        elements = []
        fnc1 = chr(29)  # GS1 Function Code 1 separator
        
        if sscc:
            elements.append(f"00{sscc}")
        
        if gtin:
            # Pad GTIN to 14 digits
            gtin_padded = gtin.zfill(14)
            elements.append(f"01{gtin_padded}")
        
        if lot_number:
            elements.append(f"10{lot_number}")
        
        if expiry_date:
            date_str = expiry_date.strftime("%y%m%d")
            elements.append(f"17{date_str}")
        
        if serial_number:
            elements.append(f"21{serial_number}")
        
        if quantity:
            elements.append(f"37{quantity}")
        
        if internal_data:
            elements.append(f"91{internal_data}")
        
        # Join with FNC1 separator for variable-length fields
        return fnc1.join(elements)
    
    def parse_gs1_128(self, barcode_data: str) -> list[GS1Element]:
        """Parse a GS1-128 barcode string."""
        elements = []
        fnc1 = chr(29)
        
        # Split on FNC1
        parts = barcode_data.split(fnc1)
        
        for part in parts:
            if not part:
                continue
            
            # Try to match known AIs
            for ai, (name, max_length) in self.GS1_AIS.items():
                if part.startswith(ai):
                    value = part[len(ai):]
                    elements.append(GS1Element(
                        ai=ai,
                        name=name,
                        value=value,
                        length=len(value),
                    ))
                    break
        
        return elements
    
    def generate_datamatrix_data(
        self,
        entity_type: str,
        entity_id: str,
        additional_data: dict[str, Any] | None = None,
    ) -> str:
        """Generate DataMatrix barcode data."""
        # Simple format: TYPE|ID|KEY1=VAL1|KEY2=VAL2
        parts = [entity_type.upper(), entity_id]
        
        if additional_data:
            for key, value in additional_data.items():
                parts.append(f"{key}={value}")
        
        return "|".join(parts)
    
    def parse_datamatrix(self, barcode_data: str) -> dict[str, Any]:
        """Parse DataMatrix barcode data."""
        parts = barcode_data.split("|")
        
        result: dict[str, Any] = {
            "entity_type": parts[0].lower() if len(parts) > 0 else None,
            "entity_id": parts[1] if len(parts) > 1 else None,
            "additional": {},
        }
        
        for part in parts[2:]:
            if "=" in part:
                key, value = part.split("=", 1)
                result["additional"][key] = value
        
        return result
    
    def generate_customer_barcode(
        self,
        customer_id: str,
        format_spec: str,
        data: dict[str, Any],
    ) -> str:
        """Generate customer-specific barcode format."""
        # Parse format spec and substitute values
        # Format: {field_name:padding}
        result = format_spec
        
        for key, value in data.items():
            # Simple substitution
            result = result.replace(f"{{{key}}}", str(value))
            
            # Handle padding
            pattern = rf"\{{{key}:(\d+)\}}"
            match = re.search(pattern, format_spec)
            if match:
                padding = int(match.group(1))
                padded_value = str(value).zfill(padding)
                result = re.sub(pattern, padded_value, result)
        
        return result
    
    def register_barcode(
        self,
        barcode_data: str,
        entity_type: str,
        entity_id: str,
        barcode_type: BarcodeType,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a barcode in the system."""
        registration = {
            "barcode_data": barcode_data,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "barcode_type": barcode_type.value,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        
        self._registered_barcodes[barcode_data] = registration
        return registration
    
    # =========================================================================
    # PRINT QUEUE MANAGEMENT
    # =========================================================================
    
    def queue_print_job(
        self,
        printer_id: str,
        template_id: str,
        data: dict[str, Any],
        copies: int = 1,
        requested_by: str | None = None,
        priority: int = 0,
    ) -> PrintJob:
        """Queue a print job."""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        printer = self._printers.get(printer_id)
        if not printer:
            raise ValueError(f"Printer not found: {printer_id}")
        
        job_id = str(uuid4())
        
        # Generate barcode data based on template type
        barcode_data = self._generate_barcode_for_template(template, data)
        
        job = PrintJob(
            id=job_id,
            printer_id=printer_id,
            template_id=template_id,
            label_type=template.label_type,
            copies=copies,
            data=data,
            barcode_data=barcode_data,
            requested_by=requested_by,
            priority=priority,
        )
        
        self._print_jobs.append(job)
        logger.info(f"Queued print job: {job_id}")
        return job
    
    def _generate_barcode_for_template(
        self,
        template: LabelTemplate,
        data: dict[str, Any],
    ) -> str:
        """Generate barcode data based on template settings."""
        if template.barcode_type == BarcodeType.GS1_128:
            return self.generate_gs1_128(
                gtin=data.get("gtin"),
                lot_number=data.get("lot_number"),
                serial_number=data.get("serial_number"),
                expiry_date=data.get("expiry_date"),
                quantity=data.get("quantity"),
            )
        elif template.barcode_type == BarcodeType.DATAMATRIX:
            entity_type = template.label_type.value.replace("_label", "")
            entity_id = data.get("id") or data.get("part_number") or data.get("serial_number", "")
            return self.generate_datamatrix_data(entity_type, entity_id)
        else:
            # Simple concatenation for other types
            return "|".join(str(v) for v in data.values() if v)
    
    def get_print_job(self, job_id: str) -> PrintJob | None:
        """Get a print job by ID."""
        for job in self._print_jobs:
            if job.id == job_id:
                return job
        return None
    
    def get_pending_jobs(self, printer_id: str | None = None) -> list[PrintJob]:
        """Get pending print jobs."""
        jobs = [j for j in self._print_jobs if j.status == PrintStatus.QUEUED]
        
        if printer_id:
            jobs = [j for j in jobs if j.printer_id == printer_id]
        
        # Sort by priority (descending) then by requested time (ascending)
        jobs.sort(key=lambda j: (-j.priority, j.requested_at))
        
        return jobs
    
    def start_print_job(self, job_id: str) -> PrintJob | None:
        """Mark a print job as started."""
        job = self.get_print_job(job_id)
        if not job:
            return None
        
        job.status = PrintStatus.PRINTING
        job.started_at = datetime.now(timezone.utc)
        return job
    
    def complete_print_job(self, job_id: str) -> PrintJob | None:
        """Mark a print job as completed."""
        job = self.get_print_job(job_id)
        if not job:
            return None
        
        job.status = PrintStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        return job
    
    def fail_print_job(self, job_id: str, error_message: str) -> PrintJob | None:
        """Mark a print job as failed."""
        job = self.get_print_job(job_id)
        if not job:
            return None
        
        job.status = PrintStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        return job
    
    def cancel_print_job(self, job_id: str) -> PrintJob | None:
        """Cancel a print job."""
        job = self.get_print_job(job_id)
        if not job or job.status not in [PrintStatus.QUEUED, PrintStatus.PRINTING]:
            return None
        
        job.status = PrintStatus.CANCELLED
        return job
    
    def requeue_job(self, job_id: str) -> PrintJob | None:
        """Requeue a failed print job."""
        job = self.get_print_job(job_id)
        if not job or job.status != PrintStatus.FAILED:
            return None
        
        job.status = PrintStatus.QUEUED
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        return job
    
    # =========================================================================
    # SCAN VALIDATION & ERROR HANDLING
    # =========================================================================
    
    def validate_barcode(
        self,
        barcode_data: str,
        expected_type: BarcodeType | None = None,
    ) -> BarcodeValidation:
        """Validate a scanned barcode."""
        result = BarcodeValidation(
            is_valid=False,
            raw_data=barcode_data,
        )
        
        # Detect barcode type
        detected_type = self._detect_barcode_type(barcode_data)
        result.barcode_type = detected_type
        
        # Check if wrong type
        if expected_type and detected_type != expected_type:
            result.error_type = ScanErrorType.WRONG_TYPE
            result.error_message = f"Expected {expected_type.value}, got {detected_type.value if detected_type else 'unknown'}"
            result.recovery_actions = self._get_recovery_actions(ScanErrorType.WRONG_TYPE)
            return result
        
        # Check if registered
        if barcode_data in self._registered_barcodes:
            reg = self._registered_barcodes[barcode_data]
            result.is_valid = True
            result.entity_type = reg["entity_type"]
            result.entity_id = reg["entity_id"]
            result.parsed_data = reg.get("metadata", {})
            return result
        
        # Try to parse based on detected type
        if detected_type == BarcodeType.GS1_128:
            elements = self.parse_gs1_128(barcode_data)
            if elements:
                result.parsed_data = {e.name: e.value for e in elements}
                # Look up by lot or serial
                lot = result.parsed_data.get("BATCH_LOT")
                serial = result.parsed_data.get("SERIAL")
                if lot or serial:
                    result.is_valid = True
                    result.entity_type = "serial" if serial else "lot"
                    result.entity_id = serial or lot
                    return result
        
        elif detected_type == BarcodeType.DATAMATRIX:
            parsed = self.parse_datamatrix(barcode_data)
            if parsed.get("entity_type") and parsed.get("entity_id"):
                result.parsed_data = parsed
                result.entity_type = parsed["entity_type"]
                result.entity_id = parsed["entity_id"]
                result.is_valid = True
                return result
        
        # Unrecognized
        result.error_type = ScanErrorType.UNRECOGNIZED
        result.error_message = "Barcode not found in system"
        result.recovery_actions = self._get_recovery_actions(ScanErrorType.UNRECOGNIZED)
        return result
    
    def _detect_barcode_type(self, barcode_data: str) -> BarcodeType | None:
        """Detect the type of barcode from its data."""
        fnc1 = chr(29)
        
        # GS1-128: Contains FNC1 separators or starts with known AIs
        if fnc1 in barcode_data:
            return BarcodeType.GS1_128
        
        # Check for GS1 AIs at start
        for ai in self.GS1_AIS.keys():
            if barcode_data.startswith(ai) and barcode_data[len(ai):len(ai)+1].isdigit():
                return BarcodeType.GS1_128
        
        # DataMatrix: Contains pipe separators (our format)
        if "|" in barcode_data:
            return BarcodeType.DATAMATRIX
        
        # Code128: Alphanumeric
        if barcode_data.isalnum():
            return BarcodeType.CODE128
        
        return None
    
    def _get_recovery_actions(self, error_type: ScanErrorType) -> list[str]:
        """Get recovery actions for an error type."""
        workflow = self._recovery_workflows.get(error_type.value)
        if workflow:
            return [step["instruction"] for step in workflow.workflow_steps]
        return ["Contact supervisor for assistance"]
    
    def create_recovery_workflow(
        self,
        error_type: ScanErrorType,
        workflow_steps: list[dict[str, Any]],
        auto_actions: list[str] | None = None,
        requires_supervisor: bool = False,
        timeout_seconds: int = 300,
    ) -> ScanRecoveryWorkflow:
        """Create a scan error recovery workflow."""
        workflow = ScanRecoveryWorkflow(
            id=str(uuid4()),
            error_type=error_type,
            workflow_steps=workflow_steps,
            auto_actions=auto_actions or [],
            requires_supervisor=requires_supervisor,
            timeout_seconds=timeout_seconds,
        )
        
        self._recovery_workflows[error_type.value] = workflow
        return workflow
    
    def get_recovery_workflow(self, error_type: ScanErrorType) -> ScanRecoveryWorkflow | None:
        """Get the recovery workflow for an error type."""
        return self._recovery_workflows.get(error_type.value)
    
    # =========================================================================
    # LABEL GENERATION
    # =========================================================================
    
    def generate_label_content(
        self,
        template_id: str,
        data: dict[str, Any],
        output_format: str = "zpl",
    ) -> str:
        """Generate label content from template and data."""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        if output_format == "zpl":
            return self._generate_zpl(template, data)
        elif output_format == "html":
            return self._generate_html(template, data)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_zpl(self, template: LabelTemplate, data: dict[str, Any]) -> str:
        """Generate ZPL code for Zebra printers."""
        if template.layout_zpl:
            # Use custom ZPL, substituting placeholders
            zpl = template.layout_zpl
            for key, value in data.items():
                zpl = zpl.replace(f"${{{key}}}", str(value or ""))
            return zpl
        
        # Generate basic ZPL
        lines = [
            "^XA",  # Start format
            f"^PW{int(template.width_mm * 8)}",  # Print width (8 dots/mm for 203dpi)
            f"^LL{int(template.height_mm * 8)}",  # Label length
        ]
        
        y_pos = 30
        for field in template.fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "text")
            value = data.get(field_name, "")
            x = field.get("x", 10) * 8
            y = field.get("y", y_pos) * 8
            
            if field_type == "text":
                label = field.get("label", "")
                if label:
                    lines.append(f"^FO{x},{y}^A0N,20,20^FD{label}: {value}^FS")
                else:
                    lines.append(f"^FO{x},{y}^A0N,20,20^FD{value}^FS")
            
            elif field_type == "barcode":
                barcode_data = self._generate_barcode_for_template(template, data)
                if template.barcode_type == BarcodeType.DATAMATRIX:
                    lines.append(f"^FO{x},{y}^BXN,4,200^FD{barcode_data}^FS")
                elif template.barcode_type == BarcodeType.GS1_128:
                    lines.append(f"^FO{x},{y}^BCN,80,Y,N,N^FD{barcode_data}^FS")
                else:
                    lines.append(f"^FO{x},{y}^BCN,80,Y,N,N^FD{barcode_data}^FS")
            
            y_pos += 25
        
        lines.append("^XZ")  # End format
        return "\n".join(lines)
    
    def _generate_html(self, template: LabelTemplate, data: dict[str, Any]) -> str:
        """Generate HTML for PDF label generation."""
        if template.layout_html:
            html = template.layout_html
            for key, value in data.items():
                html = html.replace(f"${{{key}}}", str(value or ""))
            return html
        
        # Generate basic HTML
        lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Label: {template.name}</title>",
            "<style>",
            f".label {{ width: {template.width_mm}mm; height: {template.height_mm}mm; border: 1px solid #000; padding: 5mm; }}",
            ".field { margin: 2mm 0; }",
            ".label-text { font-size: 10pt; }",
            ".barcode { font-family: monospace; font-size: 12pt; }",
            "</style>",
            "</head>",
            "<body>",
            '<div class="label">',
        ]
        
        for field in template.fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "text")
            value = data.get(field_name, "")
            label = field.get("label", "")
            
            if field_type == "text":
                if label:
                    lines.append(f'<div class="field label-text"><strong>{label}:</strong> {value}</div>')
                else:
                    lines.append(f'<div class="field label-text">{value}</div>')
            
            elif field_type == "barcode":
                barcode_data = self._generate_barcode_for_template(template, data)
                lines.append(f'<div class="field barcode">[BARCODE: {barcode_data}]</div>')
        
        lines.extend([
            "</div>",
            "</body>",
            "</html>",
        ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> dict[str, Any]:
        """Get label printing statistics."""
        jobs = self._print_jobs
        
        return {
            "total_templates": len(self._templates),
            "active_templates": len([t for t in self._templates.values() if t.is_active]),
            "total_printers": len(self._printers),
            "online_printers": len([p for p in self._printers.values() if p.is_online]),
            "total_jobs": len(jobs),
            "jobs_by_status": {
                status.value: len([j for j in jobs if j.status == status])
                for status in PrintStatus
            },
            "registered_barcodes": len(self._registered_barcodes),
            "recovery_workflows": len(self._recovery_workflows),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_label_printing_service() -> LabelPrintingService:
    """Factory function to create a Label Printing service."""
    return LabelPrintingService()
