"""
Tests for KPI Metric Sources Configuration Service.

Verifies:
- Default metric definitions
- Metric CRUD operations
- Field and event source management
- Value recording and retrieval
- Trend calculation
- Threshold-based status
- Source documentation
- Validation
- Dashboard summary
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.ops.kpi_metric_sources import (
    AggregationPeriod,
    ComputationFormula,
    DataSourceType,
    EventSource,
    FieldSource,
    KPIMetricSourcesService,
    MetricCategory,
    MetricDefinition,
    MetricTrend,
    MetricType,
    MetricValue,
)


class TestDefaultMetrics:
    """Tests for default metric definitions."""

    def test_default_metrics_exist(self) -> None:
        """Test that default metrics are created."""
        service = KPIMetricSourcesService()

        metrics = service.get_metrics()

        assert len(metrics) > 0

    def test_rfq_completeness_metric(self) -> None:
        """Test RFQ completeness metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("rfq-completeness")

        assert metric is not None
        assert metric.category == MetricCategory.RFQ
        assert metric.metric_type == MetricType.AVERAGE

    def test_quote_cycle_time_metric(self) -> None:
        """Test quote cycle time metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("quote-cycle-time")

        assert metric is not None
        assert metric.metric_type == MetricType.DURATION
        assert metric.is_higher_better is False

    def test_margin_protection_metric(self) -> None:
        """Test margin protection metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("margin-protection")

        assert metric is not None
        assert metric.unit == "percent"
        assert metric.target_value == 95.0

    def test_win_rate_metric(self) -> None:
        """Test win rate metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("win-rate")

        assert metric is not None
        assert metric.category == MetricCategory.SALES

    def test_cadence_adherence_metric(self) -> None:
        """Test cadence adherence metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("cadence-adherence")

        assert metric is not None
        assert metric.category == MetricCategory.CADENCE

    def test_andon_mttr_metric(self) -> None:
        """Test Andon MTTR metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("andon-mttr")

        assert metric is not None
        assert metric.unit == "minutes"
        assert metric.is_higher_better is False

    def test_oee_metric(self) -> None:
        """Test OEE metric exists."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("oee")

        assert metric is not None
        assert metric.category == MetricCategory.PRODUCTION


class TestMetricManagement:
    """Tests for metric CRUD operations."""

    def test_create_metric(self) -> None:
        """Test creating a custom metric."""
        service = KPIMetricSourcesService()

        metric = service.create_metric(
            name="Custom Metric",
            code="custom-metric",
            description="A custom test metric",
            category=MetricCategory.QUALITY,
            metric_type=MetricType.COUNT,
            unit="items",
            field_sources=[
                FieldSource(
                    table="test_table",
                    field="test_field",
                    description="Test field",
                    data_type="integer",
                )
            ],
            event_sources=[
                EventSource(
                    event_name="test.event",
                    description="Test event",
                    payload_fields=["id"],
                )
            ],
            computation=ComputationFormula(
                formula="COUNT(*)",
                description="Count all records",
                inputs=["test_field"],
                output_type="integer",
            ),
            aggregation_period=AggregationPeriod.DAILY,
            target_value=100.0,
        )

        assert metric.id is not None
        assert metric.code == "custom-metric"
        assert metric.is_active is True

    def test_get_metric(self) -> None:
        """Test retrieving a metric by ID."""
        service = KPIMetricSourcesService()

        metrics = service.get_metrics()
        metric_id = metrics[0].id

        retrieved = service.get_metric(metric_id)

        assert retrieved is not None
        assert retrieved.id == metric_id

    def test_get_metric_by_code(self) -> None:
        """Test retrieving a metric by code."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("quote-cycle-time")

        assert metric is not None
        assert metric.code == "quote-cycle-time"

    def test_update_metric(self) -> None:
        """Test updating a metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("rfq-completeness")

        updated = service.update_metric(
            metric.id,
            description="Updated description",
            target_value=90.0,
        )

        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.target_value == 90.0

    def test_delete_metric(self) -> None:
        """Test deleting a metric."""
        service = KPIMetricSourcesService()

        metric = service.create_metric(
            name="To Delete",
            code="delete-me",
            description="Test",
            category=MetricCategory.RFQ,
            metric_type=MetricType.COUNT,
            unit="count",
            field_sources=[],
            event_sources=[],
            computation=ComputationFormula(
                formula="COUNT(*)",
                description="Count",
                inputs=[],
                output_type="integer",
            ),
            aggregation_period=AggregationPeriod.DAILY,
        )

        result = service.delete_metric(metric.id)

        assert result is True
        assert service.get_metric(metric.id) is None

    def test_deactivate_metric(self) -> None:
        """Test deactivating a metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("win-rate")

        deactivated = service.deactivate_metric(metric.id)

        assert deactivated is not None
        assert deactivated.is_active is False

    def test_activate_metric(self) -> None:
        """Test activating a metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("win-rate")
        service.deactivate_metric(metric.id)

        activated = service.activate_metric(metric.id)

        assert activated is not None
        assert activated.is_active is True


class TestFiltering:
    """Tests for metric filtering."""

    def test_filter_by_category(self) -> None:
        """Test filtering metrics by category."""
        service = KPIMetricSourcesService()

        quote_metrics = service.get_metrics(category=MetricCategory.QUOTE)

        assert len(quote_metrics) > 0
        assert all(m.category == MetricCategory.QUOTE for m in quote_metrics)

    def test_filter_by_type(self) -> None:
        """Test filtering metrics by type."""
        service = KPIMetricSourcesService()

        percentage_metrics = service.get_metrics(metric_type=MetricType.PERCENTAGE)

        assert len(percentage_metrics) > 0
        assert all(m.metric_type == MetricType.PERCENTAGE for m in percentage_metrics)

    def test_filter_active_only(self) -> None:
        """Test filtering active metrics only."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("win-rate")
        service.deactivate_metric(metric.id)

        active_metrics = service.get_metrics(active_only=True)
        all_metrics = service.get_metrics(active_only=False)

        assert len(active_metrics) < len(all_metrics)


class TestFieldSources:
    """Tests for field source management."""

    def test_get_field_sources(self) -> None:
        """Test getting field sources for a metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("rfq-completeness")
        sources = service.get_field_sources(metric.id)

        assert len(sources) > 0
        assert any(s.table == "rfq" for s in sources)

    def test_field_source_properties(self) -> None:
        """Test field source properties."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("quote-cycle-time")
        sources = service.get_field_sources(metric.id)

        for source in sources:
            assert source.table is not None
            assert source.field is not None
            assert source.data_type is not None


class TestEventSources:
    """Tests for event source management."""

    def test_get_event_sources(self) -> None:
        """Test getting event sources for a metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("quote-cycle-time")
        sources = service.get_event_sources(metric.id)

        assert len(sources) > 0

    def test_event_source_properties(self) -> None:
        """Test event source properties."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("win-rate")
        sources = service.get_event_sources(metric.id)

        for source in sources:
            assert source.event_name is not None
            assert source.description is not None
            assert isinstance(source.payload_fields, list)


class TestValueRecording:
    """Tests for metric value recording."""

    def test_record_value(self) -> None:
        """Test recording a metric value."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=7)

        value = service.record_value(
            metric_code="rfq-completeness",
            value=85.5,
            period_start=period_start,
            period_end=now,
        )

        assert value is not None
        assert value.value == 85.5
        assert value.metric_code == "rfq-completeness"

    def test_record_value_with_raw_data(self) -> None:
        """Test recording value with raw data."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        value = service.record_value(
            metric_code="quote-cycle-time",
            value=4.5,
            period_start=now - timedelta(days=30),
            period_end=now,
            raw_data={"total_quotes": 50, "avg_days": 4.5},
        )

        assert value is not None
        assert value.raw_data is not None
        assert value.raw_data["total_quotes"] == 50

    def test_value_status_normal(self) -> None:
        """Test value status is normal when above target."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        value = service.record_value(
            metric_code="margin-protection",
            value=96.0,  # Above target of 95%
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert value.status == "normal"

    def test_value_status_warning(self) -> None:
        """Test value status is warning when below threshold."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        value = service.record_value(
            metric_code="margin-protection",
            value=80.0,  # Below warning threshold of 85%
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert value.status == "warning"

    def test_value_status_critical(self) -> None:
        """Test value status is critical when below threshold."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        value = service.record_value(
            metric_code="margin-protection",
            value=65.0,  # Below critical threshold of 70%
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert value.status == "critical"

    def test_value_status_for_lower_is_better(self) -> None:
        """Test value status for metrics where lower is better."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        # Quote cycle time: lower is better, critical > 14 days
        value = service.record_value(
            metric_code="quote-cycle-time",
            value=20.0,  # Above critical threshold
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert value.status == "critical"


class TestValueRetrieval:
    """Tests for metric value retrieval."""

    def test_get_values(self) -> None:
        """Test getting recorded values."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        # Record multiple values
        for i in range(3):
            service.record_value(
                metric_code="rfq-completeness",
                value=80 + i * 5,
                period_start=now - timedelta(days=7 * (i + 1)),
                period_end=now - timedelta(days=7 * i),
            )

        values = service.get_values("rfq-completeness")

        assert len(values) == 3

    def test_get_values_with_date_filter(self) -> None:
        """Test getting values with date filter."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        # Record values
        service.record_value(
            metric_code="win-rate",
            value=40.0,
            period_start=now - timedelta(days=30),
            period_end=now - timedelta(days=23),
        )
        service.record_value(
            metric_code="win-rate",
            value=42.0,
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        values = service.get_values(
            "win-rate",
            start_date=now - timedelta(days=10),
        )

        assert len(values) == 1

    def test_get_latest_value(self) -> None:
        """Test getting the latest value."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        service.record_value(
            metric_code="cadence-adherence",
            value=85.0,
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        )
        service.record_value(
            metric_code="cadence-adherence",
            value=90.0,
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        latest = service.get_latest_value("cadence-adherence")

        assert latest is not None
        assert latest.value == 90.0


class TestTrendCalculation:
    """Tests for trend calculation."""

    def test_calculate_trend_up(self) -> None:
        """Test trend calculation when value is increasing."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        service.record_value(
            metric_code="win-rate",
            value=35.0,
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        )
        service.record_value(
            metric_code="win-rate",
            value=42.0,
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        trend = service.calculate_trend("win-rate")

        assert trend is not None
        assert trend.direction == "up"
        assert trend.current_value == 42.0
        assert trend.previous_value == 35.0
        assert trend.is_improving is True  # Higher is better for win rate

    def test_calculate_trend_down(self) -> None:
        """Test trend calculation when value is decreasing."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        service.record_value(
            metric_code="quote-cycle-time",
            value=6.0,
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        )
        service.record_value(
            metric_code="quote-cycle-time",
            value=4.0,
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        trend = service.calculate_trend("quote-cycle-time")

        assert trend is not None
        assert trend.direction == "down"
        assert trend.is_improving is True  # Lower is better for cycle time

    def test_calculate_trend_stable(self) -> None:
        """Test trend calculation when value is stable."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        service.record_value(
            metric_code="oee",
            value=80.0,
            period_start=now - timedelta(days=14),
            period_end=now - timedelta(days=7),
        )
        service.record_value(
            metric_code="oee",
            value=80.5,  # Less than 1% change
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        trend = service.calculate_trend("oee")

        assert trend is not None
        assert trend.direction == "stable"

    def test_trend_insufficient_data(self) -> None:
        """Test trend calculation with insufficient data."""
        service = KPIMetricSourcesService()

        trend = service.calculate_trend("first-pass-yield")

        assert trend is None


class TestRefresh:
    """Tests for metric refresh tracking."""

    def test_metrics_needing_refresh_initial(self) -> None:
        """Test that all metrics need refresh initially."""
        service = KPIMetricSourcesService()

        needing_refresh = service.get_metrics_needing_refresh()

        # All active metrics should need refresh since never computed
        assert len(needing_refresh) > 0

    def test_metrics_needing_refresh_after_record(self) -> None:
        """Test that metric doesn't need refresh after recording."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        # Record value to update last_computed
        service.record_value(
            metric_code="rfq-completeness",
            value=85.0,
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        metric = service.get_metric_by_code("rfq-completeness")

        assert metric.last_computed is not None


class TestSourceDocumentation:
    """Tests for source documentation."""

    def test_get_source_documentation(self) -> None:
        """Test getting complete source documentation."""
        service = KPIMetricSourcesService()

        doc = service.get_source_documentation("quote-cycle-time")

        assert "metric" in doc
        assert doc["metric"]["code"] == "quote-cycle-time"
        assert "field_sources" in doc
        assert "event_sources" in doc
        assert "computation" in doc
        assert "thresholds" in doc

    def test_documentation_includes_all_sources(self) -> None:
        """Test that documentation includes all field sources."""
        service = KPIMetricSourcesService()

        doc = service.get_source_documentation("quote-cycle-time")

        assert len(doc["field_sources"]) > 0
        for source in doc["field_sources"]:
            assert "table" in source
            assert "field" in source
            assert "description" in source


class TestValidation:
    """Tests for metric validation."""

    def test_validate_valid_metric(self) -> None:
        """Test validating a properly configured metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("rfq-completeness")
        issues = service.validate_metric_sources(metric.id)

        # Should have no major issues
        assert not any("missing" in issue.lower() for issue in issues)

    def test_validate_metric_no_sources(self) -> None:
        """Test validating a metric with no field sources."""
        service = KPIMetricSourcesService()

        metric = service.create_metric(
            name="Empty Sources",
            code="empty-sources",
            description="Test",
            category=MetricCategory.RFQ,
            metric_type=MetricType.COUNT,
            unit="count",
            field_sources=[],
            event_sources=[],
            computation=ComputationFormula(
                formula="COUNT(*)",
                description="Count",
                inputs=["test_field"],
                output_type="integer",
            ),
            aggregation_period=AggregationPeriod.DAILY,
        )

        issues = service.validate_metric_sources(metric.id)

        assert any("No field sources" in issue for issue in issues)

    def test_validate_threshold_consistency(self) -> None:
        """Test threshold consistency validation."""
        service = KPIMetricSourcesService()

        # Create metric with inconsistent thresholds
        metric = service.create_metric(
            name="Bad Thresholds",
            code="bad-thresholds",
            description="Test",
            category=MetricCategory.QUALITY,
            metric_type=MetricType.PERCENTAGE,
            unit="percent",
            field_sources=[
                FieldSource(
                    table="test",
                    field="value",
                    description="Test",
                    data_type="float",
                )
            ],
            event_sources=[],
            computation=ComputationFormula(
                formula="AVG(value)",
                description="Average",
                inputs=["value"],
                output_type="float",
            ),
            aggregation_period=AggregationPeriod.DAILY,
            warning_threshold=50.0,
            critical_threshold=80.0,  # Should be lower for higher is better
            is_higher_better=True,
        )

        issues = service.validate_metric_sources(metric.id)

        assert any("threshold" in issue.lower() for issue in issues)


class TestMetricsBySource:
    """Tests for finding metrics by source."""

    def test_get_metrics_by_table(self) -> None:
        """Test finding metrics that use a table."""
        service = KPIMetricSourcesService()

        metrics = service.get_metrics_by_table("rfq")

        assert len(metrics) > 0
        for m in metrics:
            assert any(fs.table == "rfq" for fs in m.field_sources)

    def test_get_metrics_by_event(self) -> None:
        """Test finding metrics that use an event."""
        service = KPIMetricSourcesService()

        metrics = service.get_metrics_by_event("quote.released")

        assert len(metrics) > 0


class TestExportImport:
    """Tests for export functionality."""

    def test_export_metrics(self) -> None:
        """Test exporting metric definitions."""
        service = KPIMetricSourcesService()

        exported = service.export_metrics()

        assert len(exported) > 0
        for m in exported:
            assert "code" in m
            assert "field_sources" in m
            assert "computation" in m


class TestDashboardSummary:
    """Tests for dashboard summary."""

    def test_get_dashboard_summary(self) -> None:
        """Test getting dashboard summary."""
        service = KPIMetricSourcesService()

        summary = service.get_dashboard_summary()

        assert "total_metrics" in summary
        assert "active_metrics" in summary
        assert "by_category" in summary
        assert "by_type" in summary
        assert "status_counts" in summary

    def test_summary_counts_match(self) -> None:
        """Test that summary counts are accurate."""
        service = KPIMetricSourcesService()

        summary = service.get_dashboard_summary()
        all_metrics = service.get_metrics(active_only=False)
        active_metrics = service.get_metrics(active_only=True)

        assert summary["total_metrics"] == len(all_metrics)
        assert summary["active_metrics"] == len(active_metrics)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_get_nonexistent_metric(self) -> None:
        """Test getting non-existent metric."""
        service = KPIMetricSourcesService()

        metric = service.get_metric(uuid4())

        assert metric is None

    def test_get_nonexistent_metric_by_code(self) -> None:
        """Test getting non-existent metric by code."""
        service = KPIMetricSourcesService()

        metric = service.get_metric_by_code("nonexistent")

        assert metric is None

    def test_record_value_invalid_metric(self) -> None:
        """Test recording value for invalid metric."""
        service = KPIMetricSourcesService()

        now = datetime.now(timezone.utc)

        value = service.record_value(
            metric_code="nonexistent",
            value=50.0,
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        assert value is None

    def test_update_nonexistent_metric(self) -> None:
        """Test updating non-existent metric."""
        service = KPIMetricSourcesService()

        result = service.update_metric(uuid4(), name="New Name")

        assert result is None

    def test_delete_nonexistent_metric(self) -> None:
        """Test deleting non-existent metric."""
        service = KPIMetricSourcesService()

        result = service.delete_metric(uuid4())

        assert result is False

    def test_validate_nonexistent_metric(self) -> None:
        """Test validating non-existent metric."""
        service = KPIMetricSourcesService()

        issues = service.validate_metric_sources(uuid4())

        assert "not found" in issues[0].lower()

    def test_get_documentation_nonexistent_metric(self) -> None:
        """Test getting documentation for non-existent metric."""
        service = KPIMetricSourcesService()

        doc = service.get_source_documentation("nonexistent")

        assert doc == {}

    def test_trend_nonexistent_metric(self) -> None:
        """Test trend for non-existent metric."""
        service = KPIMetricSourcesService()

        trend = service.calculate_trend("nonexistent")

        assert trend is None

    def test_get_field_sources_nonexistent(self) -> None:
        """Test getting field sources for non-existent metric."""
        service = KPIMetricSourcesService()

        sources = service.get_field_sources(uuid4())

        assert sources == []
