"""
CSV Export Service.

Provides functionality to export entities to CSV format for
reporting, data analysis, and external integration.

Features:
- Export pipeline/opportunity data
- Export tasks and work orders
- Export products and quotes
- Configurable columns
- Data transformation
- Filtering and sorting
- Streaming for large datasets
- Export history tracking
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class ExportableEntityType(str, Enum):
    """Entity types that can be exported."""
    
    OPPORTUNITY = "opportunity"
    RFQ = "rfq"
    QUOTE = "quote"
    TASK = "task"
    WORK_ORDER = "work_order"
    PRODUCT = "product"
    RISK = "risk"
    CAPA = "capa"
    USER = "user"
    CUSTOMER = "customer"


class ExportFormat(str, Enum):
    """Export formats."""
    
    CSV = "csv"
    TSV = "tsv"


class ExportStatus(str, Enum):
    """Status of an export job."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ColumnConfig:
    """Configuration for a column in export."""
    
    field_name: str
    header: str | None = None  # Column header (defaults to field_name)
    transformer: Callable[[Any], str] | None = None
    default_value: str = ""
    include: bool = True
    order: int = 0  # Column ordering


@dataclass
class ExportConfig:
    """Configuration for an export operation."""
    
    entity_type: ExportableEntityType
    
    # Column selection
    columns: list[ColumnConfig] = field(default_factory=list)
    include_all_columns: bool = False  # Include all available columns
    exclude_columns: list[str] = field(default_factory=list)
    
    # Format
    format: ExportFormat = ExportFormat.CSV
    include_header: bool = True
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    null_value: str = ""
    boolean_true: str = "Yes"
    boolean_false: str = "No"
    
    # Filtering
    filters: dict[str, Any] = field(default_factory=dict)
    
    # Sorting
    sort_by: str | None = None
    sort_descending: bool = False
    
    # Pagination
    limit: int | None = None
    offset: int = 0


@dataclass
class ExportResult:
    """Result of an export operation."""
    
    id: UUID = field(default_factory=uuid4)
    entity_type: ExportableEntityType = ExportableEntityType.TASK
    status: ExportStatus = ExportStatus.PENDING
    
    # Content
    content: str = ""
    row_count: int = 0
    
    # File info
    filename: str = ""
    content_type: str = "text/csv"
    
    # Timestamps
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Error handling
    error_message: str | None = None
    
    # Metadata
    created_by: UUID | None = None
    config: ExportConfig | None = None


@dataclass
class ExportTemplate:
    """A saved export template."""
    
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    entity_type: ExportableEntityType = ExportableEntityType.TASK
    config: ExportConfig | None = None
    
    # Ownership
    created_by: UUID | None = None
    organization_id: UUID | None = None
    is_default: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CSVExportService:
    """
    Service for exporting entities to CSV format.
    
    Supports configurable columns, filtering, and templates.
    """
    
    def __init__(self) -> None:
        """Initialize the service."""
        self._results: dict[UUID, ExportResult] = {}
        self._templates: dict[UUID, ExportTemplate] = {}
        
        # Mock entity storage for testing
        self._mock_entities: dict[ExportableEntityType, dict[UUID, dict[str, Any]]] = {
            et: {} for et in ExportableEntityType
        }
        
        # Default column configs per entity type
        self._default_columns: dict[ExportableEntityType, list[ColumnConfig]] = {
            ExportableEntityType.OPPORTUNITY: [
                ColumnConfig("name", "Opportunity Name", order=1),
                ColumnConfig("customer_name", "Customer", order=2),
                ColumnConfig("stage", "Stage", order=3),
                ColumnConfig("value", "Value", order=4),
                ColumnConfig("probability", "Probability (%)", order=5),
                ColumnConfig("expected_close_date", "Expected Close", order=6),
                ColumnConfig("owner_name", "Owner", order=7),
                ColumnConfig("created_at", "Created", order=8),
                ColumnConfig("status", "Status", order=9),
            ],
            ExportableEntityType.RFQ: [
                ColumnConfig("rfq_number", "RFQ Number", order=1),
                ColumnConfig("customer_name", "Customer", order=2),
                ColumnConfig("description", "Description", order=3),
                ColumnConfig("received_date", "Received", order=4),
                ColumnConfig("due_date", "Due Date", order=5),
                ColumnConfig("status", "Status", order=6),
                ColumnConfig("assigned_to_name", "Assigned To", order=7),
            ],
            ExportableEntityType.QUOTE: [
                ColumnConfig("quote_number", "Quote Number", order=1),
                ColumnConfig("customer_name", "Customer", order=2),
                ColumnConfig("total_value", "Total Value", order=3),
                ColumnConfig("status", "Status", order=4),
                ColumnConfig("valid_until", "Valid Until", order=5),
                ColumnConfig("created_at", "Created", order=6),
            ],
            ExportableEntityType.TASK: [
                ColumnConfig("title", "Title", order=1),
                ColumnConfig("description", "Description", order=2),
                ColumnConfig("status", "Status", order=3),
                ColumnConfig("priority", "Priority", order=4),
                ColumnConfig("due_date", "Due Date", order=5),
                ColumnConfig("assigned_to_name", "Assigned To", order=6),
                ColumnConfig("created_at", "Created", order=7),
                ColumnConfig("completed_at", "Completed", order=8),
            ],
            ExportableEntityType.WORK_ORDER: [
                ColumnConfig("work_order_number", "WO Number", order=1),
                ColumnConfig("product_name", "Product", order=2),
                ColumnConfig("quantity", "Quantity", order=3),
                ColumnConfig("status", "Status", order=4),
                ColumnConfig("priority", "Priority", order=5),
                ColumnConfig("start_date", "Start Date", order=6),
                ColumnConfig("due_date", "Due Date", order=7),
            ],
            ExportableEntityType.PRODUCT: [
                ColumnConfig("part_number", "Part Number", order=1),
                ColumnConfig("name", "Name", order=2),
                ColumnConfig("description", "Description", order=3),
                ColumnConfig("category", "Category", order=4),
                ColumnConfig("unit_price", "Unit Price", order=5),
                ColumnConfig("status", "Status", order=6),
            ],
            ExportableEntityType.RISK: [
                ColumnConfig("title", "Title", order=1),
                ColumnConfig("category", "Category", order=2),
                ColumnConfig("severity", "Severity", order=3),
                ColumnConfig("occurrence", "Occurrence", order=4),
                ColumnConfig("detection", "Detection", order=5),
                ColumnConfig("rpn", "RPN", order=6),
                ColumnConfig("status", "Status", order=7),
                ColumnConfig("owner_name", "Owner", order=8),
            ],
            ExportableEntityType.CAPA: [
                ColumnConfig("capa_number", "CAPA Number", order=1),
                ColumnConfig("title", "Title", order=2),
                ColumnConfig("type", "Type", order=3),
                ColumnConfig("status", "Status", order=4),
                ColumnConfig("root_cause", "Root Cause", order=5),
                ColumnConfig("owner_name", "Owner", order=6),
                ColumnConfig("due_date", "Due Date", order=7),
            ],
            ExportableEntityType.USER: [
                ColumnConfig("name", "Name", order=1),
                ColumnConfig("email", "Email", order=2),
                ColumnConfig("role", "Role", order=3),
                ColumnConfig("department", "Department", order=4),
                ColumnConfig("status", "Status", order=5),
            ],
            ExportableEntityType.CUSTOMER: [
                ColumnConfig("name", "Name", order=1),
                ColumnConfig("contact_name", "Contact", order=2),
                ColumnConfig("email", "Email", order=3),
                ColumnConfig("phone", "Phone", order=4),
                ColumnConfig("industry", "Industry", order=5),
                ColumnConfig("status", "Status", order=6),
            ],
        }
    
    # ---------------------
    # Export Operations
    # ---------------------
    
    def export(
        self,
        config: ExportConfig,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export entities to CSV."""
        result = ExportResult(
            entity_type=config.entity_type,
            status=ExportStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
            created_by=created_by,
            config=config,
        )
        
        try:
            # Get entities
            entities = self._get_entities(config)
            
            # Get columns
            columns = self._get_columns(config)
            
            # Generate CSV
            output = io.StringIO()
            delimiter = "\t" if config.format == ExportFormat.TSV else ","
            
            writer = csv.writer(output, delimiter=delimiter)
            
            # Write header
            if config.include_header:
                headers = [col.header or col.field_name for col in columns]
                writer.writerow(headers)
            
            # Write rows
            for entity in entities:
                row = self._entity_to_row(entity, columns, config)
                writer.writerow(row)
            
            # Finalize result
            result.content = output.getvalue()
            result.row_count = len(entities)
            result.status = ExportStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            
            # Generate filename
            timestamp = result.completed_at.strftime("%Y%m%d_%H%M%S")
            ext = "tsv" if config.format == ExportFormat.TSV else "csv"
            result.filename = f"{config.entity_type.value}_export_{timestamp}.{ext}"
            result.content_type = "text/tab-separated-values" if config.format == ExportFormat.TSV else "text/csv"
            
        except Exception as e:
            result.status = ExportStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
        
        self._results[result.id] = result
        return result
    
    def export_with_template(
        self,
        template_id: UUID,
        filters: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export using a saved template."""
        template = self._templates.get(template_id)
        if not template or not template.config:
            result = ExportResult(
                status=ExportStatus.FAILED,
                error_message="Template not found",
                created_by=created_by,
            )
            self._results[result.id] = result
            return result
        
        # Create config from template
        config = ExportConfig(
            entity_type=template.entity_type,
            columns=template.config.columns,
            include_all_columns=template.config.include_all_columns,
            exclude_columns=template.config.exclude_columns,
            format=template.config.format,
            include_header=template.config.include_header,
            date_format=template.config.date_format,
            datetime_format=template.config.datetime_format,
            null_value=template.config.null_value,
            boolean_true=template.config.boolean_true,
            boolean_false=template.config.boolean_false,
            filters=filters or template.config.filters,
            sort_by=template.config.sort_by,
            sort_descending=template.config.sort_descending,
        )
        
        return self.export(config, created_by)
    
    def _get_entities(
        self,
        config: ExportConfig,
    ) -> list[dict[str, Any]]:
        """Get entities matching the config."""
        entities = list(self._mock_entities[config.entity_type].values())
        
        # Apply filters
        for field_name, value in config.filters.items():
            entities = [
                e for e in entities
                if self._matches_filter(e, field_name, value)
            ]
        
        # Apply sorting
        if config.sort_by:
            sort_field = config.sort_by
            entities.sort(
                key=lambda e: str(e.get(sort_field) or ""),
                reverse=config.sort_descending,
            )
        
        # Apply pagination
        if config.offset:
            entities = entities[config.offset:]
        if config.limit:
            entities = entities[:config.limit]
        
        return entities
    
    def _matches_filter(
        self,
        entity: dict[str, Any],
        field_name: str,
        value: Any,
    ) -> bool:
        """Check if entity matches a filter."""
        entity_value = entity.get(field_name)
        
        if isinstance(value, list):
            return entity_value in value
        
        if isinstance(value, dict):
            # Handle operators like {"gt": 100, "lt": 200}
            for op, op_value in value.items():
                if op == "gt" and not (entity_value and entity_value > op_value):
                    return False
                if op == "lt" and not (entity_value and entity_value < op_value):
                    return False
                if op == "gte" and not (entity_value and entity_value >= op_value):
                    return False
                if op == "lte" and not (entity_value and entity_value <= op_value):
                    return False
                if op == "ne" and entity_value == op_value:
                    return False
                if op == "contains" and op_value not in str(entity_value or ""):
                    return False
            return True
        
        return entity_value == value
    
    def _get_columns(
        self,
        config: ExportConfig,
    ) -> list[ColumnConfig]:
        """Get columns for export."""
        if config.columns:
            # Use specified columns
            columns = [c for c in config.columns if c.include]
        elif config.include_all_columns:
            # Get all columns from default + any in entities
            columns = list(self._default_columns.get(config.entity_type, []))
        else:
            # Use default columns
            columns = list(self._default_columns.get(config.entity_type, []))
        
        # Exclude columns
        columns = [
            c for c in columns
            if c.field_name not in config.exclude_columns
        ]
        
        # Sort by order
        columns.sort(key=lambda c: c.order)
        
        return columns
    
    def _entity_to_row(
        self,
        entity: dict[str, Any],
        columns: list[ColumnConfig],
        config: ExportConfig,
    ) -> list[str]:
        """Convert an entity to a row."""
        row = []
        
        for col in columns:
            value = entity.get(col.field_name)
            
            # Apply transformer if exists
            if col.transformer:
                value = col.transformer(value)
            else:
                value = self._format_value(value, config)
            
            if value is None or value == "":
                value = col.default_value
            
            row.append(str(value))
        
        return row
    
    def _format_value(
        self,
        value: Any,
        config: ExportConfig,
    ) -> str:
        """Format a value for CSV output."""
        if value is None:
            return config.null_value
        
        if isinstance(value, bool):
            return config.boolean_true if value else config.boolean_false
        
        if isinstance(value, datetime):
            return value.strftime(config.datetime_format)
        
        if isinstance(value, (list, dict)):
            return str(value)
        
        return str(value)
    
    # ---------------------
    # Template Management
    # ---------------------
    
    def create_template(
        self,
        name: str,
        entity_type: ExportableEntityType,
        config: ExportConfig,
        description: str = "",
        created_by: UUID | None = None,
        organization_id: UUID | None = None,
    ) -> ExportTemplate:
        """Create a new export template."""
        template = ExportTemplate(
            name=name,
            description=description,
            entity_type=entity_type,
            config=config,
            created_by=created_by,
            organization_id=organization_id,
        )
        
        self._templates[template.id] = template
        return template
    
    def get_template(self, template_id: UUID) -> ExportTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_templates(
        self,
        entity_type: ExportableEntityType | None = None,
        organization_id: UUID | None = None,
    ) -> list[ExportTemplate]:
        """Get templates with optional filtering."""
        templates = list(self._templates.values())
        
        if entity_type:
            templates = [t for t in templates if t.entity_type == entity_type]
        
        if organization_id:
            templates = [
                t for t in templates
                if t.organization_id == organization_id or t.is_default
            ]
        
        return sorted(templates, key=lambda t: t.name)
    
    def update_template(
        self,
        template_id: UUID,
        **updates: Any,
    ) -> ExportTemplate | None:
        """Update a template."""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now(timezone.utc)
        return template
    
    def delete_template(self, template_id: UUID) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False
    
    # ---------------------
    # Result Management
    # ---------------------
    
    def get_result(self, result_id: UUID) -> ExportResult | None:
        """Get an export result by ID."""
        return self._results.get(result_id)
    
    def get_user_exports(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[ExportResult]:
        """Get export history for a user."""
        results = [
            r for r in self._results.values()
            if r.created_by == user_id
        ]
        
        return sorted(
            results,
            key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:limit]
    
    # ---------------------
    # Convenience Methods
    # ---------------------
    
    def export_pipeline(
        self,
        filters: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export opportunities/pipeline."""
        config = ExportConfig(
            entity_type=ExportableEntityType.OPPORTUNITY,
            filters=filters or {},
        )
        return self.export(config, created_by)
    
    def export_tasks(
        self,
        filters: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export tasks."""
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            filters=filters or {},
        )
        return self.export(config, created_by)
    
    def export_work_orders(
        self,
        filters: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export work orders."""
        config = ExportConfig(
            entity_type=ExportableEntityType.WORK_ORDER,
            filters=filters or {},
        )
        return self.export(config, created_by)
    
    def export_products(
        self,
        filters: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export products."""
        config = ExportConfig(
            entity_type=ExportableEntityType.PRODUCT,
            filters=filters or {},
        )
        return self.export(config, created_by)
    
    def export_quotes(
        self,
        filters: dict[str, Any] | None = None,
        created_by: UUID | None = None,
    ) -> ExportResult:
        """Export quotes."""
        config = ExportConfig(
            entity_type=ExportableEntityType.QUOTE,
            filters=filters or {},
        )
        return self.export(config, created_by)
    
    # ---------------------
    # Default Columns
    # ---------------------
    
    def get_default_columns(
        self,
        entity_type: ExportableEntityType,
    ) -> list[ColumnConfig]:
        """Get default columns for an entity type."""
        return list(self._default_columns.get(entity_type, []))
    
    def get_available_columns(
        self,
        entity_type: ExportableEntityType,
    ) -> list[str]:
        """Get all available column names for an entity type."""
        default = self._default_columns.get(entity_type, [])
        return [col.field_name for col in default]
    
    # ---------------------
    # Mock Entity Management (for testing)
    # ---------------------
    
    def create_mock_entity(
        self,
        entity_type: ExportableEntityType,
        entity_id: UUID | None = None,
        **fields: Any,
    ) -> UUID:
        """Create a mock entity for testing."""
        if entity_id is None:
            entity_id = uuid4()
        
        entity = {
            "id": entity_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": "active",
            **fields,
        }
        
        self._mock_entities[entity_type][entity_id] = entity
        return entity_id
