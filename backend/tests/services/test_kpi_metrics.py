"""
Tests for KPI Definitions & Metrics Service.
"""

import pytest
from datetime import date, datetime, timedelta

from sensei.services.ops.kpi_metrics import (
    KPIService,
    KPIDefinition,
    KPIValue,
    KPITrend,
    KPIDashboard,
    KPIThreshold,
    KPIDataSource,
    KPICalculationResult,
    KPICategory,
    KPIUnit,
    KPIDirection,
    KPIStatus,
    AggregationType,
    TrendDirection,
    build_kpi_definition,
    get_default_kpi_ids,
    get_default_dashboard_ids,
)


@pytest.fixture
def service():
    """Create a fresh KPI service instance."""
    return KPIService()


@pytest.fixture
def custom_kpi():
    """Create a custom KPI definition for testing."""
    return KPIDefinition(
        id="test-kpi",
        name="Test KPI",
        description="A test KPI",
        category=KPICategory.CUSTOM,
        unit=KPIUnit.PERCENTAGE,
        direction=KPIDirection.HIGHER_IS_BETTER,
        threshold=KPIThreshold(
            target=90.0,
            warning_threshold=10.0,
            critical_threshold=20.0,
        ),
        tags=["test"],
    )


# --------------------------------------------------------------------------
# Enum Tests
# --------------------------------------------------------------------------

class TestEnums:
    """Tests for KPI enums."""
    
    def test_kpi_category_values(self):
        """Test KPICategory enum values."""
        assert KPICategory.SALES.value == "sales"
        assert KPICategory.QUOTING.value == "quoting"
        assert KPICategory.PRODUCTION.value == "production"
        assert KPICategory.QUALITY.value == "quality"
        assert KPICategory.TRAINING.value == "training"
        assert KPICategory.ANDON.value == "andon"
        assert KPICategory.LSW.value == "lsw"
    
    def test_kpi_unit_values(self):
        """Test KPIUnit enum values."""
        assert KPIUnit.PERCENTAGE.value == "percentage"
        assert KPIUnit.DAYS.value == "days"
        assert KPIUnit.COUNT.value == "count"
        assert KPIUnit.PPM.value == "ppm"
        assert KPIUnit.CURRENCY.value == "currency"
    
    def test_kpi_direction_values(self):
        """Test KPIDirection enum values."""
        assert KPIDirection.HIGHER_IS_BETTER.value == "higher_is_better"
        assert KPIDirection.LOWER_IS_BETTER.value == "lower_is_better"
        assert KPIDirection.TARGET_IS_BEST.value == "target_is_best"
    
    def test_kpi_status_values(self):
        """Test KPIStatus enum values."""
        assert KPIStatus.ON_TARGET.value == "on_target"
        assert KPIStatus.WITHIN_TOLERANCE.value == "within_tolerance"
        assert KPIStatus.OFF_TARGET.value == "off_target"
        assert KPIStatus.CRITICAL.value == "critical"
        assert KPIStatus.NO_DATA.value == "no_data"
    
    def test_aggregation_type_values(self):
        """Test AggregationType enum values."""
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.AVERAGE.value == "average"
        assert AggregationType.MIN.value == "min"
        assert AggregationType.MAX.value == "max"
        assert AggregationType.COUNT.value == "count"
    
    def test_trend_direction_values(self):
        """Test TrendDirection enum values."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DECLINING.value == "declining"


# --------------------------------------------------------------------------
# KPI Definition Tests
# --------------------------------------------------------------------------

class TestKPIDefinitionManagement:
    """Tests for KPI definition CRUD."""
    
    def test_create_definition(self, service, custom_kpi):
        """Test creating a KPI definition."""
        result = service.create_definition(custom_kpi)
        
        assert result.id == "test-kpi"
        assert result.name == "Test KPI"
        assert result.category == KPICategory.CUSTOM
    
    def test_create_definition_auto_id(self, service):
        """Test creating a definition auto-generates ID."""
        kpi = KPIDefinition(
            id="",
            name="Auto ID KPI",
            description="Test",
            category=KPICategory.CUSTOM,
            unit=KPIUnit.COUNT,
            direction=KPIDirection.HIGHER_IS_BETTER,
        )
        
        result = service.create_definition(kpi)
        assert result.id != ""
        assert len(result.id) > 0
    
    def test_get_definition(self, service, custom_kpi):
        """Test getting a KPI definition."""
        service.create_definition(custom_kpi)
        
        result = service.get_definition("test-kpi")
        
        assert result is not None
        assert result.name == "Test KPI"
    
    def test_get_definition_not_found(self, service):
        """Test getting non-existent definition."""
        result = service.get_definition("non-existent")
        assert result is None
    
    def test_update_definition(self, service, custom_kpi):
        """Test updating a KPI definition."""
        service.create_definition(custom_kpi)
        
        result = service.update_definition(
            "test-kpi",
            {"name": "Updated KPI", "description": "Updated description"},
        )
        
        assert result is not None
        assert result.name == "Updated KPI"
        assert result.description == "Updated description"
    
    def test_update_definition_not_found(self, service):
        """Test updating non-existent definition."""
        result = service.update_definition("non-existent", {"name": "New"})
        assert result is None
    
    def test_delete_definition(self, service, custom_kpi):
        """Test deleting a KPI definition."""
        service.create_definition(custom_kpi)
        
        result = service.delete_definition("test-kpi")
        
        assert result is True
        assert service.get_definition("test-kpi") is None
    
    def test_delete_definition_not_found(self, service):
        """Test deleting non-existent definition."""
        result = service.delete_definition("non-existent")
        assert result is False
    
    def test_list_definitions(self, service):
        """Test listing KPI definitions."""
        definitions = service.list_definitions()
        
        # Should have default KPIs registered
        assert len(definitions) > 0
    
    def test_list_definitions_by_category(self, service):
        """Test filtering definitions by category."""
        definitions = service.list_definitions(category=KPICategory.QUOTING)
        
        for d in definitions:
            assert d.category == KPICategory.QUOTING
    
    def test_list_definitions_by_tags(self, service, custom_kpi):
        """Test filtering definitions by tags."""
        custom_kpi.tags = ["custom-tag"]
        service.create_definition(custom_kpi)
        
        definitions = service.list_definitions(tags=["custom-tag"])
        
        assert len(definitions) >= 1
        assert any(d.id == "test-kpi" for d in definitions)
    
    def test_list_definitions_active_only(self, service, custom_kpi):
        """Test filtering only active definitions."""
        custom_kpi.is_active = False
        service.create_definition(custom_kpi)
        
        active = service.list_definitions(active_only=True)
        all_defs = service.list_definitions(active_only=False)
        
        assert len(all_defs) > len(active)


# --------------------------------------------------------------------------
# Default KPIs Tests
# --------------------------------------------------------------------------

class TestDefaultKPIs:
    """Tests for default Phase 1 KPIs."""
    
    def test_rfq_completeness_kpi_exists(self, service):
        """Test RFQ completeness KPI is registered."""
        kpi = service.get_definition("rfq-completeness")
        
        assert kpi is not None
        assert kpi.category == KPICategory.RFQ
        assert kpi.unit == KPIUnit.PERCENTAGE
        assert kpi.direction == KPIDirection.HIGHER_IS_BETTER
    
    def test_quote_cycle_time_kpi_exists(self, service):
        """Test quote cycle time KPI is registered."""
        kpi = service.get_definition("quote-cycle-time")
        
        assert kpi is not None
        assert kpi.category == KPICategory.QUOTING
        assert kpi.unit == KPIUnit.DAYS
        assert kpi.direction == KPIDirection.LOWER_IS_BETTER
    
    def test_oee_kpi_exists(self, service):
        """Test OEE KPI is registered."""
        kpi = service.get_definition("oee")
        
        assert kpi is not None
        assert kpi.category == KPICategory.OEE
        assert kpi.unit == KPIUnit.PERCENTAGE
        assert kpi.custom_calculator == "oee_calculator"
    
    def test_andon_mttr_kpi_exists(self, service):
        """Test Andon MTTR KPI is registered."""
        kpi = service.get_definition("andon-mttr")
        
        assert kpi is not None
        assert kpi.category == KPICategory.ANDON
        assert kpi.unit == KPIUnit.MINUTES
    
    def test_training_compliance_kpi_exists(self, service):
        """Test training compliance KPI is registered."""
        kpi = service.get_definition("training-compliance")
        
        assert kpi is not None
        assert kpi.category == KPICategory.TRAINING
        assert kpi.threshold.target == 100
    
    def test_all_phase1_kpis_have_thresholds(self, service):
        """Test all Phase 1 KPIs have thresholds defined."""
        phase1_ids = [
            "rfq-completeness",
            "qualification-discipline",
            "quote-cycle-time",
            "quote-revision-rate",
            "margin-protection",
            "win-rate",
            "bad-win-rate",
            "cadence-adherence",
            "lsw-compliance",
            "knowledge-capture",
        ]
        
        for kpi_id in phase1_ids:
            kpi = service.get_definition(kpi_id)
            assert kpi is not None, f"KPI {kpi_id} not found"
            assert kpi.threshold is not None, f"KPI {kpi_id} has no threshold"


# --------------------------------------------------------------------------
# KPI Value Tests
# --------------------------------------------------------------------------

class TestKPIValues:
    """Tests for KPI value management."""
    
    def test_record_value(self, service):
        """Test recording a KPI value."""
        value = KPIValue(
            id="val-1",
            kpi_id="rfq-completeness",
            value=87.5,
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        
        assert result.id == "val-1"
        assert result.value == 87.5
        # Status should be calculated
        assert result.status in [KPIStatus.ON_TARGET, KPIStatus.WITHIN_TOLERANCE]
    
    def test_record_value_with_dimensions(self, service):
        """Test recording a value with dimensions."""
        value = KPIValue(
            id="val-2",
            kpi_id="rfq-completeness",
            value=92.0,
            timestamp=datetime.now(),
            dimensions={"customer_segment": "automotive"},
        )
        
        result = service.record_value(value)
        assert result.dimensions["customer_segment"] == "automotive"
    
    def test_get_latest_value(self, service):
        """Test getting the most recent value."""
        # Record multiple values
        for i, val in enumerate([85.0, 88.0, 92.0]):
            service.record_value(KPIValue(
                id=f"val-{i}",
                kpi_id="rfq-completeness",
                value=val,
                timestamp=datetime.now() + timedelta(seconds=i),
            ))
        
        latest = service.get_latest_value("rfq-completeness")
        
        assert latest is not None
        assert latest.value == 92.0
    
    def test_get_latest_value_with_dimensions(self, service):
        """Test getting latest value filtered by dimensions."""
        # Record values with different dimensions
        service.record_value(KPIValue(
            id="val-auto",
            kpi_id="rfq-completeness",
            value=88.0,
            timestamp=datetime.now(),
            dimensions={"segment": "automotive"},
        ))
        service.record_value(KPIValue(
            id="val-aero",
            kpi_id="rfq-completeness",
            value=92.0,
            timestamp=datetime.now(),
            dimensions={"segment": "aerospace"},
        ))
        
        auto_latest = service.get_latest_value(
            "rfq-completeness",
            dimensions={"segment": "automotive"},
        )
        
        assert auto_latest is not None
        assert auto_latest.value == 88.0
    
    def test_get_values_date_range(self, service):
        """Test getting values within a date range."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Record values
        service.record_value(KPIValue(
            id="val-today",
            kpi_id="rfq-completeness",
            value=90.0,
            timestamp=datetime.combine(today, datetime.min.time()),
        ))
        service.record_value(KPIValue(
            id="val-yesterday",
            kpi_id="rfq-completeness",
            value=88.0,
            timestamp=datetime.combine(yesterday, datetime.min.time()),
        ))
        
        # Get only today's values
        values = service.get_values(
            "rfq-completeness",
            start_date=today,
            end_date=today,
        )
        
        assert len(values) >= 1
        assert all(v.timestamp.date() >= today for v in values)
    
    def test_get_values_with_limit(self, service):
        """Test limiting the number of values returned."""
        # Record many values
        for i in range(10):
            service.record_value(KPIValue(
                id=f"val-{i}",
                kpi_id="rfq-completeness",
                value=80.0 + i,
                timestamp=datetime.now() + timedelta(seconds=i),
            ))
        
        values = service.get_values("rfq-completeness", limit=5)
        
        assert len(values) == 5


# --------------------------------------------------------------------------
# Status Calculation Tests
# --------------------------------------------------------------------------

class TestStatusCalculation:
    """Tests for KPI status calculation."""
    
    def test_status_on_target_higher_is_better(self, service):
        """Test on-target status for higher-is-better KPI."""
        # RFQ completeness target is 85%
        value = KPIValue(
            id="val-1",
            kpi_id="rfq-completeness",
            value=90.0,  # Above target
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        assert result.status == KPIStatus.ON_TARGET
    
    def test_status_within_tolerance_higher_is_better(self, service):
        """Test within-tolerance status."""
        # Target 85%, warning at 10% = 76.5
        value = KPIValue(
            id="val-1",
            kpi_id="rfq-completeness",
            value=78.0,  # Below target but within warning
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        assert result.status == KPIStatus.WITHIN_TOLERANCE
    
    def test_status_off_target(self, service):
        """Test off-target status."""
        # Target 85%, critical at 20% = 68
        value = KPIValue(
            id="val-1",
            kpi_id="rfq-completeness",
            value=72.0,  # Below warning but above critical
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        assert result.status == KPIStatus.OFF_TARGET
    
    def test_status_critical(self, service):
        """Test critical status."""
        value = KPIValue(
            id="val-1",
            kpi_id="rfq-completeness",
            value=60.0,  # Way below target
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        assert result.status == KPIStatus.CRITICAL
    
    def test_status_lower_is_better_on_target(self, service):
        """Test on-target for lower-is-better KPI."""
        # Quote cycle time target is 5 days
        value = KPIValue(
            id="val-1",
            kpi_id="quote-cycle-time",
            value=4.0,  # Below target (good)
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        assert result.status == KPIStatus.ON_TARGET
    
    def test_status_lower_is_better_critical(self, service):
        """Test critical for lower-is-better KPI."""
        # Quote cycle time target is 5 days, critical at 40% = 7 days
        value = KPIValue(
            id="val-1",
            kpi_id="quote-cycle-time",
            value=10.0,  # Way above target (bad)
            timestamp=datetime.now(),
        )
        
        result = service.record_value(value)
        assert result.status == KPIStatus.CRITICAL


# --------------------------------------------------------------------------
# KPI Calculation Tests
# --------------------------------------------------------------------------

class TestKPICalculation:
    """Tests for KPI calculation."""
    
    def test_calculate_kpi_not_found(self, service):
        """Test calculating non-existent KPI."""
        result = service.calculate_kpi(
            "non-existent",
            date.today() - timedelta(days=7),
            date.today(),
        )
        
        assert result.success is False
        assert "not found" in result.error
    
    def test_calculate_kpi_with_custom_calculator(self, service):
        """Test calculating KPI with custom calculator."""
        result = service.calculate_kpi(
            "oee",
            date.today() - timedelta(days=7),
            date.today(),
        )
        
        assert result.success is True
        assert result.value is not None
        # OEE should be between 0 and 100
        assert 0 <= result.value.value <= 100
    
    def test_calculate_kpi_records_value(self, service):
        """Test that calculation records the value."""
        kpi_id = "rfq-completeness"
        
        result = service.calculate_kpi(
            kpi_id,
            date.today() - timedelta(days=7),
            date.today(),
        )
        
        assert result.success is True
        
        # Value should be recorded
        latest = service.get_latest_value(kpi_id)
        assert latest is not None
    
    def test_calculate_kpi_with_dimensions(self, service):
        """Test calculating KPI with dimension filters."""
        result = service.calculate_kpi(
            "rfq-completeness",
            date.today() - timedelta(days=7),
            date.today(),
            dimensions={"segment": "automotive"},
        )
        
        assert result.success is True
        assert result.value.dimensions["segment"] == "automotive"
    
    def test_calculation_time_recorded(self, service):
        """Test that calculation time is recorded."""
        result = service.calculate_kpi(
            "oee",
            date.today() - timedelta(days=7),
            date.today(),
        )
        
        assert result.calculation_time_ms >= 0


# --------------------------------------------------------------------------
# Trend Analysis Tests
# --------------------------------------------------------------------------

class TestTrendAnalysis:
    """Tests for KPI trend analysis."""
    
    def test_analyze_trend_no_data(self, service):
        """Test trend analysis with no data."""
        trend = service.analyze_trend(
            "rfq-completeness",
            date.today() - timedelta(days=7),
            date.today(),
        )
        
        assert trend is not None
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA
    
    def test_analyze_trend_improving(self, service):
        """Test detecting improving trend."""
        kpi_id = "rfq-completeness"
        today = date.today()
        
        # Record values for previous period (lower)
        for i in range(7):
            service.record_value(KPIValue(
                id=f"prev-{i}",
                kpi_id=kpi_id,
                value=80.0,
                timestamp=datetime.combine(today - timedelta(days=14-i), datetime.min.time()),
            ))
        
        # Record values for current period (higher)
        for i in range(7):
            service.record_value(KPIValue(
                id=f"curr-{i}",
                kpi_id=kpi_id,
                value=90.0,
                timestamp=datetime.combine(today - timedelta(days=6-i), datetime.min.time()),
            ))
        
        trend = service.analyze_trend(
            kpi_id,
            today - timedelta(days=6),
            today,
        )
        
        assert trend is not None
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.change_percentage > 0
    
    def test_analyze_trend_declining(self, service):
        """Test detecting declining trend."""
        kpi_id = "rfq-completeness"
        today = date.today()
        
        # Record values for previous period (higher)
        for i in range(7):
            service.record_value(KPIValue(
                id=f"prev-{i}",
                kpi_id=kpi_id,
                value=95.0,
                timestamp=datetime.combine(today - timedelta(days=14-i), datetime.min.time()),
            ))
        
        # Record values for current period (lower)
        for i in range(7):
            service.record_value(KPIValue(
                id=f"curr-{i}",
                kpi_id=kpi_id,
                value=80.0,
                timestamp=datetime.combine(today - timedelta(days=6-i), datetime.min.time()),
            ))
        
        trend = service.analyze_trend(
            kpi_id,
            today - timedelta(days=6),
            today,
        )
        
        assert trend is not None
        assert trend.direction == TrendDirection.DECLINING
        assert trend.change_percentage < 0
    
    def test_analyze_trend_statistics(self, service):
        """Test trend analysis calculates statistics."""
        kpi_id = "rfq-completeness"
        today = date.today()
        
        # Record some values
        for i in range(14):
            service.record_value(KPIValue(
                id=f"val-{i}",
                kpi_id=kpi_id,
                value=85.0 + (i % 5),
                timestamp=datetime.combine(today - timedelta(days=13-i), datetime.min.time()),
            ))
        
        trend = service.analyze_trend(
            kpi_id,
            today - timedelta(days=6),
            today,
        )
        
        assert trend is not None
        assert trend.moving_average is not None
        assert trend.standard_deviation is not None


# --------------------------------------------------------------------------
# Dashboard Tests
# --------------------------------------------------------------------------

class TestDashboards:
    """Tests for KPI dashboard management."""
    
    def test_create_dashboard(self, service):
        """Test creating a dashboard."""
        dashboard = KPIDashboard(
            id="test-dashboard",
            name="Test Dashboard",
            description="A test dashboard",
            kpi_ids=["rfq-completeness", "quote-cycle-time"],
        )
        
        result = service.create_dashboard(dashboard)
        
        assert result.id == "test-dashboard"
        assert len(result.kpi_ids) == 2
    
    def test_create_dashboard_auto_id(self, service):
        """Test creating dashboard with auto-generated ID."""
        dashboard = KPIDashboard(
            id="",
            name="Auto ID Dashboard",
            description="Test",
        )
        
        result = service.create_dashboard(dashboard)
        assert result.id != ""
    
    def test_get_dashboard(self, service):
        """Test getting a dashboard."""
        dashboard = service.get_dashboard("quote-to-cash")
        
        assert dashboard is not None
        assert dashboard.name == "Quote-to-Cash Performance"
    
    def test_update_dashboard(self, service):
        """Test updating a dashboard."""
        result = service.update_dashboard(
            "quote-to-cash",
            {"name": "Updated Dashboard"},
        )
        
        assert result is not None
        assert result.name == "Updated Dashboard"
    
    def test_delete_dashboard(self, service):
        """Test deleting a dashboard."""
        dashboard = KPIDashboard(
            id="to-delete",
            name="Delete Me",
            description="Test",
        )
        service.create_dashboard(dashboard)
        
        result = service.delete_dashboard("to-delete")
        
        assert result is True
        assert service.get_dashboard("to-delete") is None
    
    def test_list_dashboards(self, service):
        """Test listing dashboards."""
        dashboards = service.list_dashboards()
        
        # Should have default dashboards
        assert len(dashboards) >= 5
    
    def test_list_dashboards_by_owner(self, service):
        """Test filtering dashboards by owner."""
        dashboard = KPIDashboard(
            id="owned",
            name="Owned Dashboard",
            description="Test",
            owner_id="user-1",
            is_public=False,
        )
        service.create_dashboard(dashboard)
        
        owned = service.list_dashboards(owner_id="user-1", include_public=False)
        
        assert len(owned) >= 1
        assert all(d.owner_id == "user-1" for d in owned)
    
    def test_get_dashboard_data(self, service):
        """Test getting data for a dashboard."""
        data = service.get_dashboard_data(
            "quote-to-cash",
            date.today() - timedelta(days=30),
            date.today(),
        )
        
        assert "dashboard" in data
        assert "kpis" in data
        assert "period" in data
        
        # Should have data for the KPIs
        assert len(data["kpis"]) > 0


# --------------------------------------------------------------------------
# Default Dashboards Tests
# --------------------------------------------------------------------------

class TestDefaultDashboards:
    """Tests for default dashboards."""
    
    def test_quote_to_cash_dashboard_exists(self, service):
        """Test Quote-to-Cash dashboard exists."""
        dashboard = service.get_dashboard("quote-to-cash")
        
        assert dashboard is not None
        assert "rfq-completeness" in dashboard.kpi_ids
        assert "quote-cycle-time" in dashboard.kpi_ids
    
    def test_production_dashboard_exists(self, service):
        """Test Production dashboard exists."""
        dashboard = service.get_dashboard("production")
        
        assert dashboard is not None
        assert "oee" in dashboard.kpi_ids
        assert "first-pass-yield" in dashboard.kpi_ids
    
    def test_quality_dashboard_exists(self, service):
        """Test Quality dashboard exists."""
        dashboard = service.get_dashboard("quality")
        
        assert dashboard is not None
        assert "nc-rate-ppm" in dashboard.kpi_ids
    
    def test_training_dashboard_exists(self, service):
        """Test Training dashboard exists."""
        dashboard = service.get_dashboard("training")
        
        assert dashboard is not None
        assert "training-compliance" in dashboard.kpi_ids
    
    def test_andon_dashboard_exists(self, service):
        """Test Andon dashboard exists."""
        dashboard = service.get_dashboard("andon")
        
        assert dashboard is not None
        assert "andon-mttr" in dashboard.kpi_ids
    
    def test_executive_dashboard_exists(self, service):
        """Test Executive dashboard exists."""
        dashboard = service.get_dashboard("executive")
        
        assert dashboard is not None
        # Should have a mix of high-level KPIs
        assert len(dashboard.kpi_ids) >= 6


# --------------------------------------------------------------------------
# Helper Function Tests
# --------------------------------------------------------------------------

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_build_kpi_definition(self):
        """Test building a KPI definition."""
        kpi = build_kpi_definition(
            name="Test KPI",
            description="A test",
            category="quality",
            unit="percentage",
            direction="higher_is_better",
            target=95.0,
        )
        
        assert kpi.name == "Test KPI"
        assert kpi.category == KPICategory.QUALITY
        assert kpi.unit == KPIUnit.PERCENTAGE
        assert kpi.threshold.target == 95.0
    
    def test_build_kpi_definition_no_target(self):
        """Test building KPI without target."""
        kpi = build_kpi_definition(
            name="No Target KPI",
            description="A test",
            category="custom",
            unit="count",
            direction="higher_is_better",
        )
        
        assert kpi.threshold is None
    
    def test_get_default_kpi_ids(self):
        """Test getting default KPI IDs."""
        ids = get_default_kpi_ids()
        
        assert len(ids) > 0
        assert "rfq-completeness" in ids
        assert "oee" in ids
        assert "training-compliance" in ids
    
    def test_get_default_dashboard_ids(self):
        """Test getting default dashboard IDs."""
        ids = get_default_dashboard_ids()
        
        assert len(ids) == 6
        assert "quote-to-cash" in ids
        assert "executive" in ids


# --------------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_kpi_lifecycle(self, service):
        """Test complete KPI lifecycle."""
        # 1. Create custom KPI
        kpi = build_kpi_definition(
            id="lifecycle-kpi",
            name="Lifecycle Test KPI",
            description="Testing full lifecycle",
            category="custom",
            unit="percentage",
            direction="higher_is_better",
            target=90.0,
        )
        created = service.create_definition(kpi)
        assert created.id == "lifecycle-kpi"
        
        # 2. Calculate values over time
        today = date.today()
        for i in range(7):
            service.calculate_kpi(
                "lifecycle-kpi",
                today - timedelta(days=i+7),
                today - timedelta(days=i),
            )
        
        # 3. Get latest value
        latest = service.get_latest_value("lifecycle-kpi")
        assert latest is not None
        
        # 4. Analyze trend
        trend = service.analyze_trend(
            "lifecycle-kpi",
            today - timedelta(days=6),
            today,
        )
        assert trend is not None
        
        # 5. Add to dashboard
        dashboard = KPIDashboard(
            id="lifecycle-dashboard",
            name="Lifecycle Dashboard",
            description="Test",
            kpi_ids=["lifecycle-kpi"],
        )
        service.create_dashboard(dashboard)
        
        # 6. Get dashboard data
        data = service.get_dashboard_data(
            "lifecycle-dashboard",
            today - timedelta(days=30),
            today,
        )
        assert "lifecycle-kpi" in data["kpis"]
    
    def test_multi_dimension_tracking(self, service):
        """Test tracking KPI across multiple dimensions."""
        kpi_id = "rfq-completeness"
        segments = ["automotive", "aerospace", "industrial"]
        
        # Record values for each segment
        for segment in segments:
            for i in range(5):
                service.record_value(KPIValue(
                    id=f"{segment}-{i}",
                    kpi_id=kpi_id,
                    value=80.0 + i * 2,
                    timestamp=datetime.now() + timedelta(seconds=i),
                    dimensions={"segment": segment},
                ))
        
        # Get latest for each segment
        for segment in segments:
            latest = service.get_latest_value(kpi_id, {"segment": segment})
            assert latest is not None
            assert latest.dimensions["segment"] == segment
    
    def test_data_driven_calculation(self, service):
        """Test KPI calculation with data provider."""
        def mock_data_provider(source, start, end):
            return [
                {"completeness_score": 85},
                {"completeness_score": 88},
                {"completeness_score": 92},
            ]
        
        result = service.calculate_kpi(
            "rfq-completeness",
            date.today() - timedelta(days=7),
            date.today(),
            data_provider=mock_data_provider,
        )
        
        assert result.success is True
        # Average of 85, 88, 92 = 88.33
        assert 88 <= result.value.value <= 89
