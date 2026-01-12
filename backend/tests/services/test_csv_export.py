"""
Tests for CSV Export Service.

Verifies:
- Basic export functionality
- Column configuration
- Filtering and sorting
- Export templates
- Format options
- Value transformations
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from sensei.services.utils.csv_export import (
    ColumnConfig,
    CSVExportService,
    ExportableEntityType,
    ExportConfig,
    ExportFormat,
    ExportResult,
    ExportStatus,
    ExportTemplate,
)


class TestBasicExport:
    """Tests for basic export operations."""
    
    def test_export_empty_collection(self) -> None:
        """Test exporting empty collection."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.status == ExportStatus.COMPLETED
        assert result.row_count == 0
        assert "Title" in result.content  # Header still present
    
    def test_export_single_entity(self) -> None:
        """Test exporting a single entity."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            status="in_progress",
            priority="high",
        )
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.status == ExportStatus.COMPLETED
        assert result.row_count == 1
        assert "Test Task" in result.content
    
    def test_export_multiple_entities(self) -> None:
        """Test exporting multiple entities."""
        service = CSVExportService()
        
        for i in range(5):
            service.create_mock_entity(
                ExportableEntityType.TASK,
                title=f"Task {i}",
            )
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.status == ExportStatus.COMPLETED
        assert result.row_count == 5
    
    def test_export_generates_filename(self) -> None:
        """Test that export generates a filename."""
        service = CSVExportService()
        
        service.create_mock_entity(ExportableEntityType.TASK, title="Test")
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.filename.startswith("task_export_")
        assert result.filename.endswith(".csv")
    
    def test_export_sets_content_type(self) -> None:
        """Test that export sets correct content type."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.content_type == "text/csv"
    
    def test_export_tracks_timestamps(self) -> None:
        """Test that export tracks start/end timestamps."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.started_at <= result.completed_at


class TestColumnConfiguration:
    """Tests for column configuration."""
    
    def test_default_columns_included(self) -> None:
        """Test that default columns are included."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
        )
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        # Default task columns
        assert "Title" in result.content
        assert "Status" in result.content
        assert "Priority" in result.content
    
    def test_custom_columns(self) -> None:
        """Test using custom column configuration."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            custom_field="Custom Value",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("title", "Task Name"),
                ColumnConfig("custom_field", "Custom"),
            ],
        )
        
        result = service.export(config)
        
        assert "Task Name" in result.content
        assert "Custom" in result.content
        assert "Test Task" in result.content
        assert "Custom Value" in result.content
    
    def test_exclude_columns(self) -> None:
        """Test excluding specific columns."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            description="Description",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            exclude_columns=["description"],
        )
        
        result = service.export(config)
        
        assert "Description" not in result.content.split("\n")[0]  # Not in header
    
    def test_column_ordering(self) -> None:
        """Test that columns are ordered correctly."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("status", "Status", order=2),
                ColumnConfig("title", "Title", order=1),
            ],
        )
        
        result = service.export(config)
        
        header = result.content.split("\n")[0]
        assert header.index("Title") < header.index("Status")
    
    def test_column_default_value(self) -> None:
        """Test column default value for missing fields."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            # missing_field not set
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("title", "Title"),
                ColumnConfig("missing_field", "Missing", default_value="N/A"),
            ],
        )
        
        result = service.export(config)
        
        assert "N/A" in result.content


class TestFiltering:
    """Tests for filtering exports."""
    
    def test_filter_by_status(self) -> None:
        """Test filtering by status."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Active Task",
            status="active",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Completed Task",
            status="completed",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            filters={"status": "active"},
        )
        
        result = service.export(config)
        
        assert result.row_count == 1
        assert "Active Task" in result.content
        assert "Completed Task" not in result.content
    
    def test_filter_by_list(self) -> None:
        """Test filtering by list of values."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="High Priority",
            priority="high",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Medium Priority",
            priority="medium",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Low Priority",
            priority="low",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            filters={"priority": ["high", "medium"]},
        )
        
        result = service.export(config)
        
        assert result.row_count == 2
        assert "Low Priority" not in result.content
    
    def test_filter_greater_than(self) -> None:
        """Test filtering with greater than operator."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.OPPORTUNITY,
            name="Small Deal",
            value=1000,
        )
        service.create_mock_entity(
            ExportableEntityType.OPPORTUNITY,
            name="Big Deal",
            value=100000,
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.OPPORTUNITY,
            filters={"value": {"gt": 50000}},
        )
        
        result = service.export(config)
        
        assert result.row_count == 1
        assert "Big Deal" in result.content
    
    def test_filter_contains(self) -> None:
        """Test filtering with contains operator."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Important Task",
            description="This is urgent",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Normal Task",
            description="This is normal",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            filters={"description": {"contains": "urgent"}},
        )
        
        result = service.export(config)
        
        assert result.row_count == 1
        assert "Important Task" in result.content


class TestSorting:
    """Tests for sorting exports."""
    
    def test_sort_ascending(self) -> None:
        """Test ascending sort order."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="B Task",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="A Task",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="C Task",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            sort_by="title",
        )
        
        result = service.export(config)
        
        lines = result.content.strip().split("\n")
        assert "A Task" in lines[1]  # After header
    
    def test_sort_descending(self) -> None:
        """Test descending sort order."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="A Task",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="C Task",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            sort_by="title",
            sort_descending=True,
        )
        
        result = service.export(config)
        
        lines = result.content.strip().split("\n")
        assert "C Task" in lines[1]


class TestPagination:
    """Tests for pagination."""
    
    def test_limit(self) -> None:
        """Test limiting number of rows."""
        service = CSVExportService()
        
        for i in range(10):
            service.create_mock_entity(
                ExportableEntityType.TASK,
                title=f"Task {i}",
            )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            limit=5,
        )
        
        result = service.export(config)
        
        assert result.row_count == 5
    
    def test_offset(self) -> None:
        """Test offset for pagination."""
        service = CSVExportService()
        
        for i in range(5):
            service.create_mock_entity(
                ExportableEntityType.TASK,
                title=f"Task {i}",
            )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            sort_by="title",
            offset=2,
        )
        
        result = service.export(config)
        
        assert result.row_count == 3
    
    def test_limit_and_offset(self) -> None:
        """Test limit and offset together."""
        service = CSVExportService()
        
        for i in range(10):
            service.create_mock_entity(
                ExportableEntityType.TASK,
                title=f"Task {i:02d}",
            )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            sort_by="title",
            limit=3,
            offset=2,
        )
        
        result = service.export(config)
        
        assert result.row_count == 3


class TestFormatOptions:
    """Tests for format options."""
    
    def test_csv_format(self) -> None:
        """Test CSV format uses comma delimiter."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            status="active",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            format=ExportFormat.CSV,
        )
        
        result = service.export(config)
        
        assert "," in result.content
        assert result.content_type == "text/csv"
    
    def test_tsv_format(self) -> None:
        """Test TSV format uses tab delimiter."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            status="active",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            format=ExportFormat.TSV,
        )
        
        result = service.export(config)
        
        assert "\t" in result.content
        assert result.filename.endswith(".tsv")
        assert result.content_type == "text/tab-separated-values"
    
    def test_no_header(self) -> None:
        """Test export without header row."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            include_header=False,
        )
        
        result = service.export(config)
        
        lines = result.content.strip().split("\n")
        assert len(lines) == 1
        assert "Test Task" in lines[0]
    
    def test_boolean_formatting(self) -> None:
        """Test boolean value formatting."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            is_urgent=True,
            is_completed=False,
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("is_urgent", "Urgent"),
                ColumnConfig("is_completed", "Completed"),
            ],
            boolean_true="TRUE",
            boolean_false="FALSE",
        )
        
        result = service.export(config)
        
        assert "TRUE" in result.content
        assert "FALSE" in result.content
    
    def test_null_value_formatting(self) -> None:
        """Test null value formatting."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            description=None,
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("title", "Title"),
                ColumnConfig("description", "Description"),
            ],
            null_value="(empty)",
        )
        
        result = service.export(config)
        
        assert "(empty)" in result.content
    
    def test_datetime_formatting(self) -> None:
        """Test datetime value formatting."""
        service = CSVExportService()
        
        test_date = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            due_date=test_date,
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[ColumnConfig("due_date", "Due Date")],
            datetime_format="%Y-%m-%d %H:%M",
        )
        
        result = service.export(config)
        
        assert "2024-06-15 14:30" in result.content


class TestValueTransformers:
    """Tests for value transformers."""
    
    def test_custom_transformer(self) -> None:
        """Test custom transformer function."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            priority="high",
        )
        
        def priority_transformer(value: str) -> str:
            return value.upper() if value else ""
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("title", "Title"),
                ColumnConfig(
                    "priority",
                    "Priority",
                    transformer=priority_transformer,
                ),
            ],
        )
        
        result = service.export(config)
        
        assert "HIGH" in result.content
    
    def test_transformer_with_none(self) -> None:
        """Test transformer handles None values."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            optional_field=None,
        )
        
        def safe_transformer(value: str) -> str:
            return f"[{value}]" if value else "N/A"
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig(
                    "optional_field",
                    "Optional",
                    transformer=safe_transformer,
                ),
            ],
        )
        
        result = service.export(config)
        
        assert "N/A" in result.content


class TestExportTemplates:
    """Tests for export templates."""
    
    def test_create_template(self) -> None:
        """Test creating an export template."""
        service = CSVExportService()
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[ColumnConfig("title", "Title")],
        )
        
        template = service.create_template(
            name="Task Export",
            entity_type=ExportableEntityType.TASK,
            config=config,
            description="Export all tasks",
        )
        
        assert template.id is not None
        assert template.name == "Task Export"
    
    def test_get_template(self) -> None:
        """Test retrieving a template."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        template = service.create_template(
            name="Test Template",
            entity_type=ExportableEntityType.TASK,
            config=config,
        )
        
        retrieved = service.get_template(template.id)
        
        assert retrieved is not None
        assert retrieved.name == "Test Template"
    
    def test_export_with_template(self) -> None:
        """Test exporting using a template."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[ColumnConfig("title", "Task Title")],
        )
        
        template = service.create_template(
            name="Task Template",
            entity_type=ExportableEntityType.TASK,
            config=config,
        )
        
        result = service.export_with_template(template.id)
        
        assert result.status == ExportStatus.COMPLETED
        assert "Task Title" in result.content
    
    def test_export_with_template_not_found(self) -> None:
        """Test export with non-existent template."""
        service = CSVExportService()
        
        result = service.export_with_template(uuid4())
        
        assert result.status == ExportStatus.FAILED
        assert "not found" in result.error_message.lower()
    
    def test_export_with_template_override_filters(self) -> None:
        """Test overriding filters when using template."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Active Task",
            status="active",
        )
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Completed Task",
            status="completed",
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            filters={"status": "active"},
        )
        
        template = service.create_template(
            name="Task Template",
            entity_type=ExportableEntityType.TASK,
            config=config,
        )
        
        # Override filter
        result = service.export_with_template(
            template.id,
            filters={"status": "completed"},
        )
        
        assert result.row_count == 1
        assert "Completed Task" in result.content
    
    def test_get_templates_by_entity_type(self) -> None:
        """Test filtering templates by entity type."""
        service = CSVExportService()
        
        task_config = ExportConfig(entity_type=ExportableEntityType.TASK)
        opp_config = ExportConfig(entity_type=ExportableEntityType.OPPORTUNITY)
        
        service.create_template(
            name="Task Template",
            entity_type=ExportableEntityType.TASK,
            config=task_config,
        )
        service.create_template(
            name="Opp Template",
            entity_type=ExportableEntityType.OPPORTUNITY,
            config=opp_config,
        )
        
        task_templates = service.get_templates(
            entity_type=ExportableEntityType.TASK,
        )
        
        assert len(task_templates) == 1
        assert task_templates[0].name == "Task Template"
    
    def test_update_template(self) -> None:
        """Test updating a template."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        template = service.create_template(
            name="Original Name",
            entity_type=ExportableEntityType.TASK,
            config=config,
        )
        
        updated = service.update_template(
            template.id,
            name="Updated Name",
            description="New description",
        )
        
        assert updated.name == "Updated Name"
        assert updated.description == "New description"
    
    def test_delete_template(self) -> None:
        """Test deleting a template."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        template = service.create_template(
            name="To Delete",
            entity_type=ExportableEntityType.TASK,
            config=config,
        )
        
        result = service.delete_template(template.id)
        
        assert result is True
        assert service.get_template(template.id) is None


class TestConvenienceMethods:
    """Tests for convenience export methods."""
    
    def test_export_pipeline(self) -> None:
        """Test pipeline export convenience method."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.OPPORTUNITY,
            name="Test Opportunity",
        )
        
        result = service.export_pipeline()
        
        assert result.status == ExportStatus.COMPLETED
        assert result.entity_type == ExportableEntityType.OPPORTUNITY
    
    def test_export_tasks(self) -> None:
        """Test task export convenience method."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
        )
        
        result = service.export_tasks()
        
        assert result.status == ExportStatus.COMPLETED
        assert result.entity_type == ExportableEntityType.TASK
    
    def test_export_work_orders(self) -> None:
        """Test work order export convenience method."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.WORK_ORDER,
            work_order_number="WO-001",
        )
        
        result = service.export_work_orders()
        
        assert result.status == ExportStatus.COMPLETED
        assert result.entity_type == ExportableEntityType.WORK_ORDER
    
    def test_export_products(self) -> None:
        """Test product export convenience method."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.PRODUCT,
            part_number="P-001",
        )
        
        result = service.export_products()
        
        assert result.status == ExportStatus.COMPLETED
    
    def test_export_quotes(self) -> None:
        """Test quote export convenience method."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.QUOTE,
            quote_number="Q-001",
        )
        
        result = service.export_quotes()
        
        assert result.status == ExportStatus.COMPLETED


class TestResultManagement:
    """Tests for result management."""
    
    def test_get_result(self) -> None:
        """Test retrieving an export result."""
        service = CSVExportService()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        retrieved = service.get_result(result.id)
        
        assert retrieved is not None
        assert retrieved.id == result.id
    
    def test_get_user_exports(self) -> None:
        """Test getting export history for a user."""
        service = CSVExportService()
        
        user_id = uuid4()
        other_user_id = uuid4()
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        
        service.export(config, created_by=user_id)
        service.export(config, created_by=user_id)
        service.export(config, created_by=other_user_id)
        
        user_exports = service.get_user_exports(user_id)
        
        assert len(user_exports) == 2
        assert all(e.created_by == user_id for e in user_exports)
    
    def test_get_user_exports_limit(self) -> None:
        """Test limiting user export history."""
        service = CSVExportService()
        
        user_id = uuid4()
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        
        for _ in range(10):
            service.export(config, created_by=user_id)
        
        exports = service.get_user_exports(user_id, limit=5)
        
        assert len(exports) == 5


class TestDefaultColumns:
    """Tests for default column configuration."""
    
    def test_get_default_columns(self) -> None:
        """Test getting default columns for entity type."""
        service = CSVExportService()
        
        columns = service.get_default_columns(ExportableEntityType.TASK)
        
        assert len(columns) > 0
        assert any(c.field_name == "title" for c in columns)
        assert any(c.field_name == "status" for c in columns)
    
    def test_get_available_columns(self) -> None:
        """Test getting available column names."""
        service = CSVExportService()
        
        columns = service.get_available_columns(ExportableEntityType.OPPORTUNITY)
        
        assert "name" in columns
        assert "customer_name" in columns
        assert "value" in columns


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_export_with_special_characters(self) -> None:
        """Test export handles special characters."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Task with, comma",
            description='Task with "quotes"',
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("title", "Title"),
                ColumnConfig("description", "Description"),
            ],
        )
        
        result = service.export(config)
        
        assert result.status == ExportStatus.COMPLETED
        # CSV should properly escape these
        assert "Task with, comma" in result.content or '"Task with, comma"' in result.content
    
    def test_export_with_newlines(self) -> None:
        """Test export handles newlines in data."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            description="Line 1\nLine 2",
        )
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.status == ExportStatus.COMPLETED
    
    def test_export_with_unicode(self) -> None:
        """Test export handles unicode characters."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Task with émojis 🚀",
            description="日本語テスト",
        )
        
        config = ExportConfig(entity_type=ExportableEntityType.TASK)
        result = service.export(config)
        
        assert result.status == ExportStatus.COMPLETED
        assert "émojis" in result.content
        assert "日本語" in result.content
    
    def test_export_empty_string_vs_null(self) -> None:
        """Test distinguishing empty string from null."""
        service = CSVExportService()
        
        service.create_mock_entity(
            ExportableEntityType.TASK,
            title="Test Task",
            description="",  # Empty string
            notes=None,  # Null
        )
        
        config = ExportConfig(
            entity_type=ExportableEntityType.TASK,
            columns=[
                ColumnConfig("description", "Description"),
                ColumnConfig("notes", "Notes"),
            ],
            null_value="(null)",
        )
        
        result = service.export(config)
        
        # Empty string should be empty, null should be "(null)"
        assert "(null)" in result.content
