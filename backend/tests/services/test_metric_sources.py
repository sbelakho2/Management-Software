"""Tests for Metric Sources Service.

Tests the complete metric source configuration functionality
including source registration, validation, documentation, and usage tracking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from sensei.services.ops.metric_sources import (
    MetricSourcesService,
    MetricSourceDefinition,
    FieldMapping,
    FilterCondition,
    MetricSourceValidation,
    MetricSourceUsage,
    SourceEntityType,
    EventType,
    CalculationMethod,
    TimestampField,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service() -> MetricSourcesService:
    """Create a fresh MetricSourcesService instance."""
    return MetricSourcesService()


@pytest.fixture
def custom_source() -> MetricSourceDefinition:
    """Create a custom metric source for testing."""
    return MetricSourceDefinition(
        kpi_id="custom-test-kpi",
        name="Custom Test KPI",
        description="A test KPI for unit testing",
        entity_type=SourceEntityType.WORK_ORDER,
        calculation_method=CalculationMethod.AVERAGE,
        field_mappings=[
            FieldMapping("actual_hours", "Actual hours worked", "numeric"),
            FieldMapping("estimated_hours", "Estimated hours", "numeric"),
        ],
        filters=[
            FilterCondition("status", "eq", "completed", "Completed only"),
        ],
        trigger_events=[EventType.COMPLETED],
        formula="AVG(actual_hours)",
        unit="hours",
    )


@pytest.fixture
def duration_source() -> MetricSourceDefinition:
    """Create a duration-based metric source."""
    return MetricSourceDefinition(
        kpi_id="test-duration-kpi",
        name="Test Duration KPI",
        description="Tests duration calculation",
        entity_type=SourceEntityType.TASK,
        calculation_method=CalculationMethod.DURATION,
        start_timestamp="started_at",
        end_timestamp="completed_at",
        field_mappings=[
            FieldMapping("started_at", "Task start time", "timestamp"),
            FieldMapping("completed_at", "Task completion time", "timestamp"),
        ],
        trigger_events=[EventType.COMPLETED],
        unit="hours",
    )


@pytest.fixture
def percentage_source() -> MetricSourceDefinition:
    """Create a percentage-based metric source."""
    return MetricSourceDefinition(
        kpi_id="test-percentage-kpi",
        name="Test Percentage KPI",
        description="Tests percentage calculation",
        entity_type=SourceEntityType.INSPECTION_RECORD,
        calculation_method=CalculationMethod.PERCENTAGE,
        numerator_field="passed_count",
        denominator_field="total_count",
        trigger_events=[EventType.COMPLETED],
        unit="percentage",
    )


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Test enum values and completeness."""

    def test_source_entity_types_complete(self) -> None:
        """Verify all expected entity types exist."""
        expected = {
            "rfq", "quote", "quote_version", "opportunity", "qualification",
            "work_order", "non_conformance", "capa", "andon_event",
            "inspection_record", "training", "user_skill", "a3", "task",
            "lsw_item", "kanban_card", "production_cell", "obeya_item",
        }
        actual = {e.value for e in SourceEntityType}
        assert actual == expected

    def test_event_types_complete(self) -> None:
        """Verify all expected event types exist."""
        expected = {
            "created", "updated", "status_changed", "approved", "rejected",
            "completed", "closed", "escalated", "expired", "started", "resolved",
        }
        actual = {e.value for e in EventType}
        assert actual == expected

    def test_calculation_methods_complete(self) -> None:
        """Verify all calculation methods exist."""
        expected = {
            "count", "sum", "average", "percentage", "ratio",
            "rate", "duration", "difference", "formula",
        }
        actual = {e.value for e in CalculationMethod}
        assert actual == expected

    def test_timestamp_fields_complete(self) -> None:
        """Verify standard timestamp fields exist."""
        expected = {
            "created_at", "updated_at", "completed_at", "started_at",
            "closed_at", "resolved_at", "approved_at", "released_at",
            "due_date", "scheduled_start", "scheduled_end",
            "actual_start", "actual_end",
        }
        actual = {e.value for e in TimestampField}
        assert actual == expected


# ============================================================
# Dataclass Tests
# ============================================================


class TestFieldMapping:
    """Test FieldMapping dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic field mapping creation."""
        fm = FieldMapping("value", "Value field", "numeric")
        assert fm.source_field == "value"
        assert fm.description == "Value field"
        assert fm.data_type == "numeric"
        assert fm.transformation is None
        assert fm.default_value is None

    def test_with_transformation(self) -> None:
        """Test field mapping with transformation."""
        fm = FieldMapping(
            "raw_date",
            "Raw date string",
            "text",
            transformation="PARSE_DATE",
            default_value="1970-01-01",
        )
        assert fm.transformation == "PARSE_DATE"
        assert fm.default_value == "1970-01-01"

    def test_various_data_types(self) -> None:
        """Test various data types."""
        types = ["numeric", "text", "boolean", "timestamp", "date", "uuid", "enum", "integer"]
        for dt in types:
            fm = FieldMapping("field", "desc", dt)
            assert fm.data_type == dt


class TestFilterCondition:
    """Test FilterCondition dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic filter creation."""
        fc = FilterCondition("status", "eq", "active")
        assert fc.field == "status"
        assert fc.operator == "eq"
        assert fc.value == "active"
        assert fc.description == ""

    def test_with_description(self) -> None:
        """Test filter with description."""
        fc = FilterCondition("amount", "gte", 100, "Minimum amount filter")
        assert fc.description == "Minimum amount filter"

    def test_in_operator(self) -> None:
        """Test IN operator with list value."""
        fc = FilterCondition("status", "in", ["active", "pending", "completed"])
        assert fc.operator == "in"
        assert isinstance(fc.value, list)
        assert len(fc.value) == 3

    def test_is_null_operator(self) -> None:
        """Test IS_NULL operator."""
        fc = FilterCondition("deleted_at", "is_null", True)
        assert fc.operator == "is_null"
        assert fc.value is True


class TestMetricSourceDefinition:
    """Test MetricSourceDefinition dataclass."""

    def test_minimal_creation(self) -> None:
        """Test minimal source definition."""
        source = MetricSourceDefinition()
        assert source.id is not None
        assert source.kpi_id == ""
        assert source.is_active is True
        assert isinstance(source.created_at, datetime)

    def test_full_creation(self, custom_source: MetricSourceDefinition) -> None:
        """Test full source definition."""
        assert custom_source.kpi_id == "custom-test-kpi"
        assert custom_source.entity_type == SourceEntityType.WORK_ORDER
        assert custom_source.calculation_method == CalculationMethod.AVERAGE
        assert len(custom_source.field_mappings) == 2
        assert len(custom_source.filters) == 1

    def test_duration_source(self, duration_source: MetricSourceDefinition) -> None:
        """Test duration source creation."""
        assert duration_source.calculation_method == CalculationMethod.DURATION
        assert duration_source.start_timestamp == "started_at"
        assert duration_source.end_timestamp == "completed_at"

    def test_percentage_source(self, percentage_source: MetricSourceDefinition) -> None:
        """Test percentage source creation."""
        assert percentage_source.calculation_method == CalculationMethod.PERCENTAGE
        assert percentage_source.numerator_field == "passed_count"
        assert percentage_source.denominator_field == "total_count"

    def test_timestamps_auto_set(self) -> None:
        """Test that timestamps are automatically set."""
        before = datetime.now(timezone.utc)
        source = MetricSourceDefinition(kpi_id="test")
        after = datetime.now(timezone.utc)

        assert before <= source.created_at <= after
        assert before <= source.updated_at <= after


class TestMetricSourceValidation:
    """Test MetricSourceValidation dataclass."""

    def test_default_valid(self) -> None:
        """Test default validation is valid."""
        v = MetricSourceValidation()
        assert v.is_valid is True
        assert v.errors == []
        assert v.warnings == []

    def test_with_errors(self) -> None:
        """Test validation with errors."""
        v = MetricSourceValidation(
            is_valid=False,
            errors=["Missing field", "Invalid formula"],
        )
        assert v.is_valid is False
        assert len(v.errors) == 2

    def test_with_warnings(self) -> None:
        """Test validation with warnings."""
        v = MetricSourceValidation(
            is_valid=True,
            warnings=["No trigger events defined"],
        )
        assert v.is_valid is True
        assert len(v.warnings) == 1


class TestMetricSourceUsage:
    """Test MetricSourceUsage dataclass."""

    def test_default_values(self) -> None:
        """Test default usage values."""
        usage = MetricSourceUsage()
        assert usage.source_id == ""
        assert usage.calculation_count == 0
        assert usage.last_value is None
        assert usage.avg_calculation_time_ms == 0.0

    def test_with_values(self) -> None:
        """Test usage with values."""
        usage = MetricSourceUsage(
            source_id="kpi-1",
            kpi_id="kpi-1",
            last_calculated_at=datetime.now(timezone.utc),
            calculation_count=100,
            last_value=42.5,
            avg_calculation_time_ms=15.3,
        )
        assert usage.calculation_count == 100
        assert usage.last_value == 42.5


# ============================================================
# Service Initialization Tests
# ============================================================


class TestServiceInitialization:
    """Test service initialization."""

    def test_creates_default_sources(self, service: MetricSourcesService) -> None:
        """Test that default sources are created."""
        sources = service.get_all_sources()
        assert len(sources) > 0

    def test_default_sources_include_key_kpis(self, service: MetricSourcesService) -> None:
        """Test that key KPIs are included in defaults."""
        key_kpis = [
            "rfq-completeness",
            "quote-cycle-time",
            "qualification-discipline",
            "win-rate",
            "wo-on-time",
            "first-pass-yield",
            "capa-closure-rate",
            "andon-mttr",
            "training-compliance",
            "oee",
        ]
        for kpi_id in key_kpis:
            source = service.get_source(kpi_id)
            assert source is not None, f"Missing default source: {kpi_id}"

    def test_default_sources_are_active(self, service: MetricSourcesService) -> None:
        """Test that all default sources are active."""
        for source in service.get_all_sources():
            assert source.is_active is True

    def test_default_sources_have_descriptions(self, service: MetricSourcesService) -> None:
        """Test that default sources have descriptions."""
        for source in service.get_all_sources():
            assert source.description, f"Source {source.kpi_id} missing description"


# ============================================================
# Source Registration Tests
# ============================================================


class TestSourceRegistration:
    """Test source registration functionality."""

    def test_register_basic_source(self, service: MetricSourcesService) -> None:
        """Test registering a basic source."""
        source = service.register_source(
            kpi_id="new-kpi",
            name="New KPI",
            description="A new KPI",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
        )

        assert source.kpi_id == "new-kpi"
        assert source.name == "New KPI"
        assert service.get_source("new-kpi") is not None

    def test_register_with_field_mappings(self, service: MetricSourcesService) -> None:
        """Test registering with field mappings."""
        source = service.register_source(
            kpi_id="mapped-kpi",
            name="Mapped KPI",
            description="KPI with mappings",
            entity_type=SourceEntityType.QUOTE,
            calculation_method=CalculationMethod.SUM,
            field_mappings=[
                FieldMapping("amount", "Total amount", "numeric"),
                FieldMapping("discount", "Discount applied", "numeric"),
            ],
        )

        assert len(source.field_mappings) == 2
        assert source.field_mappings[0].source_field == "amount"

    def test_register_with_filters(self, service: MetricSourcesService) -> None:
        """Test registering with filters."""
        source = service.register_source(
            kpi_id="filtered-kpi",
            name="Filtered KPI",
            description="KPI with filters",
            entity_type=SourceEntityType.RFQ,
            calculation_method=CalculationMethod.COUNT,
            filters=[
                FilterCondition("status", "eq", "active"),
                FilterCondition("priority", "gte", 3),
            ],
        )

        assert len(source.filters) == 2

    def test_register_with_trigger_events(self, service: MetricSourcesService) -> None:
        """Test registering with trigger events."""
        source = service.register_source(
            kpi_id="event-kpi",
            name="Event KPI",
            description="KPI with events",
            entity_type=SourceEntityType.CAPA,
            calculation_method=CalculationMethod.COUNT,
            trigger_events=[EventType.CREATED, EventType.CLOSED],
        )

        assert len(source.trigger_events) == 2
        assert EventType.CREATED in source.trigger_events

    def test_register_duration_kpi(self, service: MetricSourcesService) -> None:
        """Test registering a duration KPI."""
        source = service.register_source(
            kpi_id="duration-kpi",
            name="Duration KPI",
            description="Measures time between events",
            entity_type=SourceEntityType.A3,
            calculation_method=CalculationMethod.DURATION,
            start_timestamp="opened_at",
            end_timestamp="closed_at",
            unit="days",
        )

        assert source.start_timestamp == "opened_at"
        assert source.end_timestamp == "closed_at"

    def test_register_percentage_kpi(self, service: MetricSourcesService) -> None:
        """Test registering a percentage KPI."""
        source = service.register_source(
            kpi_id="percent-kpi",
            name="Percentage KPI",
            description="Calculates a rate",
            entity_type=SourceEntityType.INSPECTION_RECORD,
            calculation_method=CalculationMethod.PERCENTAGE,
            numerator_field="passed",
            denominator_field="total",
            unit="percentage",
        )

        assert source.numerator_field == "passed"
        assert source.denominator_field == "total"

    def test_register_formula_kpi(self, service: MetricSourcesService) -> None:
        """Test registering a formula KPI."""
        source = service.register_source(
            kpi_id="formula-kpi",
            name="Formula KPI",
            description="Uses custom formula",
            entity_type=SourceEntityType.PRODUCTION_CELL,
            calculation_method=CalculationMethod.FORMULA,
            formula="a * b * c * 100",
            formula_description="Product of three factors",
        )

        assert source.formula == "a * b * c * 100"

    def test_register_with_group_by(self, service: MetricSourcesService) -> None:
        """Test registering with group by fields."""
        source = service.register_source(
            kpi_id="grouped-kpi",
            name="Grouped KPI",
            description="Grouped metric",
            entity_type=SourceEntityType.WORK_ORDER,
            calculation_method=CalculationMethod.AVERAGE,
            group_by_fields=["cell_id", "shift_date"],
        )

        assert source.group_by_fields == ["cell_id", "shift_date"]

    def test_register_overwrites_existing(self, service: MetricSourcesService) -> None:
        """Test that registering with same ID overwrites."""
        service.register_source(
            kpi_id="overwrite-test",
            name="Original",
            description="Original desc",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
        )

        service.register_source(
            kpi_id="overwrite-test",
            name="Updated",
            description="Updated desc",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.SUM,
        )

        source = service.get_source("overwrite-test")
        assert source is not None
        assert source.name == "Updated"
        assert source.calculation_method == CalculationMethod.SUM


# ============================================================
# Source Retrieval Tests
# ============================================================


class TestSourceRetrieval:
    """Test source retrieval functionality."""

    def test_get_source_by_id(self, service: MetricSourcesService) -> None:
        """Test getting a source by ID."""
        source = service.get_source("quote-cycle-time")
        assert source is not None
        assert source.name == "Quote Cycle Time"

    def test_get_nonexistent_source(self, service: MetricSourcesService) -> None:
        """Test getting a non-existent source."""
        source = service.get_source("does-not-exist")
        assert source is None

    def test_get_all_sources(self, service: MetricSourcesService) -> None:
        """Test getting all sources."""
        sources = service.get_all_sources()
        assert isinstance(sources, list)
        assert len(sources) >= 17  # Default sources

    def test_get_sources_by_entity_rfq(self, service: MetricSourcesService) -> None:
        """Test getting sources by RFQ entity."""
        sources = service.get_sources_by_entity(SourceEntityType.RFQ)
        assert len(sources) >= 1
        for source in sources:
            assert source.entity_type == SourceEntityType.RFQ

    def test_get_sources_by_entity_andon(self, service: MetricSourcesService) -> None:
        """Test getting sources by Andon entity."""
        sources = service.get_sources_by_entity(SourceEntityType.ANDON_EVENT)
        assert len(sources) >= 2  # MTTR and Ack SLA at minimum
        for source in sources:
            assert source.entity_type == SourceEntityType.ANDON_EVENT

    def test_get_sources_by_entity_empty(self, service: MetricSourcesService) -> None:
        """Test getting sources for entity with no sources."""
        # First clear and add one source for a different entity
        service._sources.clear()
        service.register_source(
            kpi_id="only-quote",
            name="Only Quote",
            description="Only for quotes",
            entity_type=SourceEntityType.QUOTE,
            calculation_method=CalculationMethod.COUNT,
        )

        sources = service.get_sources_by_entity(SourceEntityType.TRAINING)
        assert sources == []

    def test_get_sources_by_event_created(self, service: MetricSourcesService) -> None:
        """Test getting sources by CREATED event."""
        sources = service.get_sources_by_event(EventType.CREATED)
        for source in sources:
            assert EventType.CREATED in source.trigger_events

    def test_get_sources_by_event_completed(self, service: MetricSourcesService) -> None:
        """Test getting sources by COMPLETED event."""
        sources = service.get_sources_by_event(EventType.COMPLETED)
        assert len(sources) >= 1
        for source in sources:
            assert EventType.COMPLETED in source.trigger_events

    def test_get_sources_by_event_no_matches(self, service: MetricSourcesService) -> None:
        """Test getting sources for event with no triggers."""
        # Clear and add source without the STARTED event
        service._sources.clear()
        service.register_source(
            kpi_id="test",
            name="Test",
            description="Test",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
            trigger_events=[EventType.COMPLETED],
        )

        sources = service.get_sources_by_event(EventType.STARTED)
        assert sources == []


# ============================================================
# Source Update Tests
# ============================================================


class TestSourceUpdate:
    """Test source update functionality."""

    def test_update_name(self, service: MetricSourcesService) -> None:
        """Test updating source name."""
        original = service.get_source("quote-cycle-time")
        assert original is not None

        updated = service.update_source("quote-cycle-time", name="Updated Name")
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.updated_at >= original.updated_at

    def test_update_description(self, service: MetricSourcesService) -> None:
        """Test updating source description."""
        updated = service.update_source(
            "quote-cycle-time",
            description="New description",
        )
        assert updated is not None
        assert updated.description == "New description"

    def test_update_filters(self, service: MetricSourcesService) -> None:
        """Test updating source filters."""
        new_filters = [
            FilterCondition("status", "eq", "active"),
            FilterCondition("amount", "gte", 1000),
        ]

        updated = service.update_source("quote-cycle-time", filters=new_filters)
        assert updated is not None
        assert len(updated.filters) == 2

    def test_update_formula(self, service: MetricSourcesService) -> None:
        """Test updating source formula."""
        updated = service.update_source(
            "oee",
            formula="a * b * c * 100 * efficiency_factor",
        )
        assert updated is not None
        assert "efficiency_factor" in updated.formula

    def test_update_is_active(self, service: MetricSourcesService) -> None:
        """Test updating source active status."""
        updated = service.update_source("quote-cycle-time", is_active=False)
        assert updated is not None
        assert updated.is_active is False

    def test_update_multiple_fields(self, service: MetricSourcesService) -> None:
        """Test updating multiple fields at once."""
        updated = service.update_source(
            "quote-cycle-time",
            name="Multi Update",
            description="Multiple fields updated",
            is_active=False,
        )
        assert updated is not None
        assert updated.name == "Multi Update"
        assert updated.description == "Multiple fields updated"
        assert updated.is_active is False

    def test_update_nonexistent(self, service: MetricSourcesService) -> None:
        """Test updating non-existent source."""
        result = service.update_source("nonexistent", name="New Name")
        assert result is None

    def test_update_preserves_unmodified_fields(self, service: MetricSourcesService) -> None:
        """Test that update preserves unmodified fields."""
        original = service.get_source("oee")
        assert original is not None
        original_entity = original.entity_type

        updated = service.update_source("oee", name="Updated OEE")
        assert updated is not None
        assert updated.entity_type == original_entity


# ============================================================
# Source Deletion Tests
# ============================================================


class TestSourceDeletion:
    """Test source deletion functionality."""

    def test_delete_existing(self, service: MetricSourcesService) -> None:
        """Test deleting an existing source."""
        service.register_source(
            kpi_id="to-delete",
            name="To Delete",
            description="Will be deleted",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
        )

        assert service.get_source("to-delete") is not None
        result = service.delete_source("to-delete")
        assert result is True
        assert service.get_source("to-delete") is None

    def test_delete_nonexistent(self, service: MetricSourcesService) -> None:
        """Test deleting a non-existent source."""
        result = service.delete_source("nonexistent")
        assert result is False

    def test_delete_and_reregister(self, service: MetricSourcesService) -> None:
        """Test deleting and re-registering a source."""
        service.register_source(
            kpi_id="reregister",
            name="Original",
            description="Original",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
        )

        service.delete_source("reregister")

        service.register_source(
            kpi_id="reregister",
            name="New",
            description="New",
            entity_type=SourceEntityType.A3,
            calculation_method=CalculationMethod.SUM,
        )

        source = service.get_source("reregister")
        assert source is not None
        assert source.name == "New"
        assert source.entity_type == SourceEntityType.A3


# ============================================================
# Validation Tests
# ============================================================


class TestValidation:
    """Test source validation functionality."""

    def test_validate_valid_source(self, service: MetricSourcesService, custom_source: MetricSourceDefinition) -> None:
        """Test validating a valid source."""
        validation = service.validate_source(custom_source)
        assert validation.is_valid is True
        assert len(validation.errors) == 0

    def test_validate_missing_kpi_id(self, service: MetricSourcesService) -> None:
        """Test validation catches missing kpi_id."""
        source = MetricSourceDefinition(name="Test")
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("kpi_id" in e for e in validation.errors)

    def test_validate_missing_name(self, service: MetricSourcesService) -> None:
        """Test validation catches missing name."""
        source = MetricSourceDefinition(kpi_id="test-id")
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("name" in e for e in validation.errors)

    def test_validate_percentage_missing_numerator(self, service: MetricSourcesService) -> None:
        """Test validation catches missing numerator for percentage."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.PERCENTAGE,
            denominator_field="total",
        )
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("numerator" in e.lower() for e in validation.errors)

    def test_validate_percentage_missing_denominator(self, service: MetricSourcesService) -> None:
        """Test validation catches missing denominator for percentage."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.PERCENTAGE,
            numerator_field="count",
        )
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("denominator" in e.lower() for e in validation.errors)

    def test_validate_percentage_with_formula_valid(self, service: MetricSourcesService) -> None:
        """Test percentage with formula is valid without num/denom."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.PERCENTAGE,
            formula="COUNT(passed) / COUNT(*) * 100",
        )
        validation = service.validate_source(source)
        assert validation.is_valid is True

    def test_validate_duration_missing_start(self, service: MetricSourcesService) -> None:
        """Test validation catches missing start timestamp."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.DURATION,
            end_timestamp="completed_at",
        )
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("start_timestamp" in e for e in validation.errors)

    def test_validate_duration_missing_end(self, service: MetricSourcesService) -> None:
        """Test validation catches missing end timestamp."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.DURATION,
            start_timestamp="started_at",
        )
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("end_timestamp" in e for e in validation.errors)

    def test_validate_formula_missing_formula(self, service: MetricSourcesService) -> None:
        """Test validation catches missing formula."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.FORMULA,
        )
        validation = service.validate_source(source)
        assert validation.is_valid is False
        assert any("formula" in e.lower() for e in validation.errors)

    def test_validate_warning_no_events(self, service: MetricSourcesService) -> None:
        """Test warning for missing trigger events."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.COUNT,
            trigger_events=[],
        )
        validation = service.validate_source(source)
        assert any("trigger_events" in w for w in validation.warnings)

    def test_validate_warning_no_field_mappings(self, service: MetricSourcesService) -> None:
        """Test warning for missing field mappings."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.COUNT,
            field_mappings=[],
        )
        validation = service.validate_source(source)
        assert any("field_mappings" in w for w in validation.warnings)

    def test_validate_warning_no_unit(self, service: MetricSourcesService) -> None:
        """Test warning for missing unit."""
        source = MetricSourceDefinition(
            kpi_id="test",
            name="Test",
            calculation_method=CalculationMethod.COUNT,
            unit="",
        )
        validation = service.validate_source(source)
        assert any("unit" in w.lower() for w in validation.warnings)

    def test_validate_all_sources(self, service: MetricSourcesService) -> None:
        """Test validating all registered sources."""
        results = service.validate_all_sources()
        assert len(results) > 0

        # All default sources should be valid
        for kpi_id, validation in results.items():
            assert validation.is_valid, f"Source {kpi_id} is invalid: {validation.errors}"


# ============================================================
# Usage Tracking Tests
# ============================================================


class TestUsageTracking:
    """Test usage tracking functionality."""

    def test_record_first_calculation(self, service: MetricSourcesService) -> None:
        """Test recording first calculation."""
        service.record_calculation("quote-cycle-time", 45.5, 12.3)

        usage = service.get_usage("quote-cycle-time")
        assert usage is not None
        assert usage.calculation_count == 1
        assert usage.last_value == 45.5
        assert usage.avg_calculation_time_ms == 12.3

    def test_record_multiple_calculations(self, service: MetricSourcesService) -> None:
        """Test recording multiple calculations."""
        service.record_calculation("quote-cycle-time", 10.0, 10.0)
        service.record_calculation("quote-cycle-time", 20.0, 20.0)
        service.record_calculation("quote-cycle-time", 30.0, 30.0)

        usage = service.get_usage("quote-cycle-time")
        assert usage is not None
        assert usage.calculation_count == 3
        assert usage.last_value == 30.0
        assert usage.avg_calculation_time_ms == 20.0  # Average of 10, 20, 30

    def test_record_updates_timestamp(self, service: MetricSourcesService) -> None:
        """Test that recording updates timestamp."""
        before = datetime.now(timezone.utc)
        service.record_calculation("test-kpi", 100.0, 5.0)
        after = datetime.now(timezone.utc)

        usage = service.get_usage("test-kpi")
        assert usage is not None
        assert before <= usage.last_calculated_at <= after

    def test_get_usage_nonexistent(self, service: MetricSourcesService) -> None:
        """Test getting usage for non-tracked KPI."""
        usage = service.get_usage("never-calculated")
        assert usage is None

    def test_get_all_usage(self, service: MetricSourcesService) -> None:
        """Test getting all usage statistics."""
        service.record_calculation("kpi-1", 10.0, 5.0)
        service.record_calculation("kpi-2", 20.0, 10.0)
        service.record_calculation("kpi-3", 30.0, 15.0)

        all_usage = service.get_all_usage()
        assert len(all_usage) >= 3

    def test_running_average_calculation(self, service: MetricSourcesService) -> None:
        """Test running average of calculation time."""
        # Record 5 calculations with times: 10, 20, 30, 40, 50
        # Running average: 10, 15, 20, 25, 30
        times = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, t in enumerate(times):
            service.record_calculation("avg-test", float(i), t)

        usage = service.get_usage("avg-test")
        assert usage is not None
        assert usage.calculation_count == 5
        assert usage.avg_calculation_time_ms == 30.0


# ============================================================
# Documentation Tests
# ============================================================


class TestDocumentation:
    """Test documentation functionality."""

    def test_get_field_documentation(self, service: MetricSourcesService) -> None:
        """Test getting field documentation for a KPI."""
        doc = service.get_field_documentation("quote-cycle-time")

        assert doc["kpi_id"] == "quote-cycle-time"
        assert doc["name"] == "Quote Cycle Time"
        assert "entity_type" in doc
        assert "calculation_method" in doc
        assert "fields" in doc
        assert "filters" in doc
        assert "trigger_events" in doc
        assert "unit" in doc

    def test_get_field_documentation_includes_fields(self, service: MetricSourcesService) -> None:
        """Test that field documentation includes field details."""
        doc = service.get_field_documentation("quote-cycle-time")

        assert len(doc["fields"]) >= 2
        field = doc["fields"][0]
        assert "name" in field
        assert "description" in field
        assert "type" in field

    def test_get_field_documentation_includes_filters(self, service: MetricSourcesService) -> None:
        """Test that field documentation includes filter details."""
        doc = service.get_field_documentation("quote-cycle-time")

        if doc["filters"]:
            filter_doc = doc["filters"][0]
            assert "field" in filter_doc
            assert "operator" in filter_doc
            assert "value" in filter_doc

    def test_get_field_documentation_nonexistent(self, service: MetricSourcesService) -> None:
        """Test getting documentation for non-existent KPI."""
        doc = service.get_field_documentation("nonexistent")
        assert doc == {}

    def test_get_documentation_report(self, service: MetricSourcesService) -> None:
        """Test getting full documentation report."""
        report = service.get_documentation_report()

        assert isinstance(report, list)
        assert len(report) >= 17  # Default sources

        # Each item should have key fields
        for item in report:
            assert "kpi_id" in item
            assert "name" in item
            assert "description" in item

    def test_documentation_includes_formula_description(self, service: MetricSourcesService) -> None:
        """Test that documentation includes formula description."""
        doc = service.get_field_documentation("oee")
        assert "formula" in doc
        assert "formula_description" in doc


# ============================================================
# Summary Tests
# ============================================================


class TestSummary:
    """Test summary functionality."""

    def test_get_sources_summary(self, service: MetricSourcesService) -> None:
        """Test getting sources summary."""
        summary = service.get_sources_summary()

        assert "total_sources" in summary
        assert "by_entity_type" in summary
        assert "by_calculation_method" in summary
        assert "active_sources" in summary

    def test_summary_counts(self, service: MetricSourcesService) -> None:
        """Test that summary counts are accurate."""
        summary = service.get_sources_summary()
        all_sources = service.get_all_sources()

        assert summary["total_sources"] == len(all_sources)
        assert summary["active_sources"] == len([s for s in all_sources if s.is_active])

    def test_summary_by_entity_type(self, service: MetricSourcesService) -> None:
        """Test summary by entity type."""
        summary = service.get_sources_summary()

        total_by_entity = sum(summary["by_entity_type"].values())
        assert total_by_entity == summary["total_sources"]

    def test_summary_by_calculation_method(self, service: MetricSourcesService) -> None:
        """Test summary by calculation method."""
        summary = service.get_sources_summary()

        total_by_method = sum(summary["by_calculation_method"].values())
        assert total_by_method == summary["total_sources"]


# ============================================================
# Default Source Tests
# ============================================================


class TestDefaultSources:
    """Test default metric sources."""

    def test_rfq_completeness(self, service: MetricSourcesService) -> None:
        """Test RFQ completeness source."""
        source = service.get_source("rfq-completeness")
        assert source is not None
        assert source.entity_type == SourceEntityType.RFQ
        assert source.calculation_method == CalculationMethod.AVERAGE
        assert source.unit == "percentage"

    def test_quote_cycle_time(self, service: MetricSourcesService) -> None:
        """Test quote cycle time source."""
        source = service.get_source("quote-cycle-time")
        assert source is not None
        assert source.entity_type == SourceEntityType.QUOTE
        assert source.calculation_method == CalculationMethod.DURATION
        assert source.start_timestamp == "rfq_created_at"
        assert source.end_timestamp == "released_at"

    def test_first_pass_yield(self, service: MetricSourcesService) -> None:
        """Test first pass yield source."""
        source = service.get_source("first-pass-yield")
        assert source is not None
        assert source.entity_type == SourceEntityType.INSPECTION_RECORD
        assert source.calculation_method == CalculationMethod.PERCENTAGE
        assert source.unit == "percentage"

    def test_capa_closure_rate(self, service: MetricSourcesService) -> None:
        """Test CAPA closure rate source."""
        source = service.get_source("capa-closure-rate")
        assert source is not None
        assert source.entity_type == SourceEntityType.CAPA
        assert EventType.CLOSED in source.trigger_events

    def test_andon_mttr(self, service: MetricSourcesService) -> None:
        """Test Andon MTTR source."""
        source = service.get_source("andon-mttr")
        assert source is not None
        assert source.entity_type == SourceEntityType.ANDON_EVENT
        assert source.calculation_method == CalculationMethod.DURATION
        assert source.unit == "minutes"

    def test_training_compliance(self, service: MetricSourcesService) -> None:
        """Test training compliance source."""
        source = service.get_source("training-compliance")
        assert source is not None
        assert source.entity_type == SourceEntityType.USER_SKILL
        assert source.unit == "percentage"

    def test_oee(self, service: MetricSourcesService) -> None:
        """Test OEE source."""
        source = service.get_source("oee")
        assert source is not None
        assert source.entity_type == SourceEntityType.PRODUCTION_CELL
        assert source.calculation_method == CalculationMethod.FORMULA
        assert "availability" in source.formula

    def test_kanban_lead_time(self, service: MetricSourcesService) -> None:
        """Test Kanban lead time source."""
        source = service.get_source("kanban-lead-time")
        assert source is not None
        assert source.entity_type == SourceEntityType.KANBAN_CARD
        assert source.calculation_method == CalculationMethod.DURATION

    def test_win_rate(self, service: MetricSourcesService) -> None:
        """Test win rate source."""
        source = service.get_source("win-rate")
        assert source is not None
        assert source.entity_type == SourceEntityType.OPPORTUNITY
        assert source.calculation_method == CalculationMethod.PERCENTAGE

    def test_work_order_on_time(self, service: MetricSourcesService) -> None:
        """Test work order on-time source."""
        source = service.get_source("wo-on-time")
        assert source is not None
        assert source.entity_type == SourceEntityType.WORK_ORDER
        assert EventType.COMPLETED in source.trigger_events


# ============================================================
# Edge Cases and Error Handling
# ============================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_field_mappings_list(self, service: MetricSourcesService) -> None:
        """Test source with empty field mappings list."""
        source = service.register_source(
            kpi_id="empty-mappings",
            name="Empty Mappings",
            description="Has empty field mappings",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
            field_mappings=[],
        )
        assert source.field_mappings == []

    def test_empty_filters_list(self, service: MetricSourcesService) -> None:
        """Test source with empty filters list."""
        source = service.register_source(
            kpi_id="empty-filters",
            name="Empty Filters",
            description="Has empty filters",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
            filters=[],
        )
        assert source.filters == []

    def test_special_characters_in_formula(self, service: MetricSourcesService) -> None:
        """Test formula with special characters."""
        source = service.register_source(
            kpi_id="special-formula",
            name="Special Formula",
            description="Has special chars in formula",
            entity_type=SourceEntityType.QUOTE,
            calculation_method=CalculationMethod.FORMULA,
            formula="SUM(a.field) / COUNT(*) * 100.0 WHERE x >= 0",
        )
        assert ">=" in source.formula

    def test_unicode_in_description(self, service: MetricSourcesService) -> None:
        """Test Unicode in source description."""
        source = service.register_source(
            kpi_id="unicode-test",
            name="Unicode Test ñ é ü",
            description="Description with émojis 📊 and accénts",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
        )
        assert "📊" in source.description
        assert "é" in source.name

    def test_very_long_formula(self, service: MetricSourcesService) -> None:
        """Test very long formula."""
        long_formula = "CASE " + " ".join([f"WHEN x = {i} THEN {i * 10}" for i in range(100)]) + " END"
        source = service.register_source(
            kpi_id="long-formula",
            name="Long Formula",
            description="Has a very long formula",
            entity_type=SourceEntityType.QUOTE,
            calculation_method=CalculationMethod.FORMULA,
            formula=long_formula,
        )
        assert len(source.formula) > 1000

    def test_many_group_by_fields(self, service: MetricSourcesService) -> None:
        """Test many group by fields."""
        fields = [f"field_{i}" for i in range(20)]
        source = service.register_source(
            kpi_id="many-groups",
            name="Many Groups",
            description="Has many group by fields",
            entity_type=SourceEntityType.WORK_ORDER,
            calculation_method=CalculationMethod.SUM,
            group_by_fields=fields,
        )
        assert len(source.group_by_fields) == 20

    def test_filter_with_none_value(self, service: MetricSourcesService) -> None:
        """Test filter with None value."""
        source = service.register_source(
            kpi_id="none-filter",
            name="None Filter",
            description="Has filter with None value",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
            filters=[FilterCondition("deleted_at", "is_null", None)],
        )
        assert source.filters[0].value is None

    def test_calculation_with_zero_time(self, service: MetricSourcesService) -> None:
        """Test recording calculation with zero time."""
        service.record_calculation("zero-time", 100.0, 0.0)
        usage = service.get_usage("zero-time")
        assert usage is not None
        assert usage.avg_calculation_time_ms == 0.0

    def test_calculation_with_negative_value(self, service: MetricSourcesService) -> None:
        """Test recording calculation with negative value."""
        service.record_calculation("negative", -50.0, 5.0)
        usage = service.get_usage("negative")
        assert usage is not None
        assert usage.last_value == -50.0


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests for metric sources."""

    def test_register_validate_use_flow(self, service: MetricSourcesService) -> None:
        """Test full flow: register, validate, use."""
        # Register
        source = service.register_source(
            kpi_id="integration-test",
            name="Integration Test KPI",
            description="For integration testing",
            entity_type=SourceEntityType.WORK_ORDER,
            calculation_method=CalculationMethod.PERCENTAGE,
            numerator_field="completed_count",
            denominator_field="total_count",
            field_mappings=[
                FieldMapping("status", "Work order status", "enum"),
                FieldMapping("completed_at", "Completion timestamp", "timestamp"),
            ],
            filters=[
                FilterCondition("is_active", "eq", True),
            ],
            trigger_events=[EventType.COMPLETED, EventType.STATUS_CHANGED],
            unit="percentage",
        )

        # Validate
        validation = service.validate_source(source)
        assert validation.is_valid is True

        # Use (record calculation)
        service.record_calculation("integration-test", 85.5, 23.4)

        # Verify
        usage = service.get_usage("integration-test")
        assert usage is not None
        assert usage.last_value == 85.5

        # Get documentation
        doc = service.get_field_documentation("integration-test")
        assert doc["name"] == "Integration Test KPI"

    def test_update_and_revalidate(self, service: MetricSourcesService) -> None:
        """Test updating and revalidating."""
        # Create with missing fields for warnings
        source = service.register_source(
            kpi_id="update-validate",
            name="Update Validate",
            description="Test",
            entity_type=SourceEntityType.TASK,
            calculation_method=CalculationMethod.COUNT,
        )

        # Initial validation has warnings
        v1 = service.validate_source(source)
        assert len(v1.warnings) > 0

        # Update with trigger events
        service.update_source(
            "update-validate",
            # Note: update_source doesn't update trigger_events, so warnings remain
            description="Updated description",
        )

        # Get updated source
        updated = service.get_source("update-validate")
        assert updated is not None
        assert updated.description == "Updated description"

    def test_multiple_sources_same_entity(self, service: MetricSourcesService) -> None:
        """Test multiple sources for same entity type."""
        service.register_source(
            kpi_id="wo-metric-1",
            name="WO Metric 1",
            description="First WO metric",
            entity_type=SourceEntityType.WORK_ORDER,
            calculation_method=CalculationMethod.COUNT,
        )

        service.register_source(
            kpi_id="wo-metric-2",
            name="WO Metric 2",
            description="Second WO metric",
            entity_type=SourceEntityType.WORK_ORDER,
            calculation_method=CalculationMethod.AVERAGE,
        )

        wo_sources = service.get_sources_by_entity(SourceEntityType.WORK_ORDER)
        kpi_ids = [s.kpi_id for s in wo_sources]
        assert "wo-metric-1" in kpi_ids
        assert "wo-metric-2" in kpi_ids

    def test_deactivate_and_exclude(self, service: MetricSourcesService) -> None:
        """Test deactivating sources."""
        service.update_source("quote-cycle-time", is_active=False)

        summary = service.get_sources_summary()
        all_sources = service.get_all_sources()

        assert summary["active_sources"] < summary["total_sources"]
        deactivated = [s for s in all_sources if not s.is_active]
        assert len(deactivated) >= 1
