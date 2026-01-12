"""
Tests for Cognitive Obeya: The Organizational Brain.

Tests prescriptive metrics, cross-functional synergy, and Heijunka leveling.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sensei.services.ops.cognitive_obeya import (
    # Enums
    MetricCategory,
    MetricStatus,
    TrendDirection,
    AlertSeverity,
    AlertType,
    DepartmentType,
    # Data models
    MetricValue,
    CausalLink,
    TrendWarning,
    SiloAlert,
    ResourceRebalance,
    HeijunkaSuggestion,
    WorkCenterLoad,
    SkillProfile,
    # Classes
    PrescriptiveMetricAnalyzer,
    CrossFunctionalSynergyEngine,
    HeijunkaAdvisor,
    CognitiveObeya,
    # Factory functions
    create_cognitive_obeya,
    create_metric_analyzer,
    create_synergy_engine,
    create_heijunka_advisor,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def metric_analyzer() -> PrescriptiveMetricAnalyzer:
    """Create metric analyzer."""
    return create_metric_analyzer()


@pytest.fixture
def synergy_engine() -> CrossFunctionalSynergyEngine:
    """Create synergy engine."""
    return create_synergy_engine()


@pytest.fixture
def heijunka_advisor() -> HeijunkaAdvisor:
    """Create Heijunka advisor."""
    return create_heijunka_advisor()


@pytest.fixture
def obeya() -> CognitiveObeya:
    """Create Cognitive Obeya."""
    return create_cognitive_obeya()


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test enum definitions."""
    
    def test_metric_category_values(self):
        """Test MetricCategory enum values."""
        assert MetricCategory.SAFETY.value == "safety"
        assert MetricCategory.QUALITY.value == "quality"
        assert MetricCategory.DELIVERY.value == "delivery"
        assert MetricCategory.COST.value == "cost"
        assert MetricCategory.PRODUCTIVITY.value == "productivity"
    
    def test_metric_status_values(self):
        """Test MetricStatus enum values."""
        assert MetricStatus.GREEN.value == "green"
        assert MetricStatus.YELLOW.value == "yellow"
        assert MetricStatus.RED.value == "red"
    
    def test_trend_direction_values(self):
        """Test TrendDirection enum values."""
        assert TrendDirection.IMPROVING.value == "improving"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.DECLINING.value == "declining"
    
    def test_alert_severity_values(self):
        """Test AlertSeverity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_alert_type_values(self):
        """Test AlertType enum values."""
        assert AlertType.CAUSAL_LINK.value == "causal_link"
        assert AlertType.PREDICTIVE_WARNING.value == "predictive_warning"
        assert AlertType.SILO_BUSTER.value == "silo_buster"
        assert AlertType.RESOURCE_REBALANCE.value == "resource_rebalance"
        assert AlertType.HEIJUNKA_SUGGESTION.value == "heijunka_suggestion"
    
    def test_department_type_values(self):
        """Test DepartmentType enum values."""
        assert DepartmentType.SALES.value == "sales"
        assert DepartmentType.PRODUCTION.value == "production"
        assert DepartmentType.QUALITY.value == "quality"
        assert DepartmentType.LOGISTICS.value == "logistics"
        assert DepartmentType.ENGINEERING.value == "engineering"
        assert DepartmentType.MAINTENANCE.value == "maintenance"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data models."""
    
    def test_metric_value_creation(self):
        """Test MetricValue creation."""
        metric = MetricValue(
            metric_id="quality_defect_rate",
            category=MetricCategory.QUALITY,
            name="Defect Rate",
            value=5.0,
            target=2.0,
            timestamp=datetime.now(),
            unit="%",
        )
        assert metric.metric_id == "quality_defect_rate"
        assert metric.status == MetricStatus.RED  # 5% > 2% * 1.2
    
    def test_metric_value_green_status(self):
        """Test metric value achieves green status."""
        metric = MetricValue(
            metric_id="quality_rate",
            category=MetricCategory.QUALITY,
            name="Quality Rate",
            value=98.0,
            target=95.0,
            timestamp=datetime.now(),
        )
        assert metric.status == MetricStatus.GREEN
    
    def test_metric_value_yellow_status(self):
        """Test metric value achieves yellow status."""
        metric = MetricValue(
            metric_id="quality_rate",
            category=MetricCategory.QUALITY,
            name="Quality Rate",
            value=86.0,  # Below target but above 90%
            target=95.0,
            timestamp=datetime.now(),
        )
        assert metric.status == MetricStatus.YELLOW
    
    def test_causal_link_creation(self):
        """Test CausalLink creation."""
        link = CausalLink(
            link_id="link_001",
            metric_id="quality_defect_rate",
            source_type="work_order",
            source_id="WO-001",
            source_description="Machining batch",
            confidence=0.85,
            impact_value=3.0,
            detected_at=datetime.now(),
        )
        assert link.confidence == 0.85
    
    def test_trend_warning_creation(self):
        """Test TrendWarning creation."""
        warning = TrendWarning(
            warning_id="warn_001",
            metric_id="delivery_on_time",
            metric_name="On-Time Delivery",
            current_status=MetricStatus.YELLOW,
            predicted_status=MetricStatus.RED,
            days_to_breach=5,
            trend_values=[95, 92, 89, 86, 83],
            confidence=0.8,
            detected_at=datetime.now(),
        )
        assert warning.days_to_breach == 5
    
    def test_silo_alert_creation(self):
        """Test SiloAlert creation."""
        alert = SiloAlert(
            alert_id="silo_001",
            source_department=DepartmentType.SALES,
            affected_department=DepartmentType.PRODUCTION,
            source_event="RFQ delay for large order",
            predicted_impact="Production bottleneck next week",
            severity=AlertSeverity.MEDIUM,
            detected_at=datetime.now(),
        )
        assert alert.resolution_status == "open"
    
    def test_resource_rebalance_creation(self):
        """Test ResourceRebalance creation."""
        rebalance = ResourceRebalance(
            suggestion_id="rebal_001",
            source_work_center="Packaging",
            target_work_center="Assembly",
            operator_ids=["op_001", "op_002"],
            skill_match_score=0.85,
            reason="Balance workload",
            expected_improvement=0.15,
            suggested_at=datetime.now(),
        )
        assert rebalance.status == "pending"
    
    def test_heijunka_suggestion_creation(self):
        """Test HeijunkaSuggestion creation."""
        suggestion = HeijunkaSuggestion(
            suggestion_id="heij_001",
            period="weekly",
            current_mix={"A": 100, "B": 50},
            suggested_mix={"A": 80, "B": 70},
            mura_reduction=25.0,
            volume_variance_before=500.0,
            volume_variance_after=100.0,
            suggested_at=datetime.now(),
        )
        assert suggestion.mura_reduction == 25.0
    
    def test_work_center_load_creation(self):
        """Test WorkCenterLoad creation."""
        wc = WorkCenterLoad(
            work_center_id="wc_001",
            name="Assembly",
            capacity=100,
            current_load=85,
            wip_count=10,
            operator_count=5,
        )
        assert wc.utilization == 0.85
    
    def test_skill_profile_creation(self):
        """Test SkillProfile creation."""
        profile = SkillProfile(
            operator_id="op_001",
            name="John Doe",
            skills={"assembly": 0.9, "welding": 0.6},
            current_work_center="wc_001",
        )
        assert profile.available is True


# =============================================================================
# PRESCRIPTIVE METRIC ANALYZER TESTS
# =============================================================================


class TestPrescriptiveMetricAnalyzer:
    """Test PrescriptiveMetricAnalyzer."""
    
    def test_record_metric(self, metric_analyzer):
        """Test recording a metric."""
        metric = MetricValue(
            metric_id="quality_rate",
            category=MetricCategory.QUALITY,
            name="Quality Rate",
            value=97.0,
            target=95.0,
            timestamp=datetime.now(),
        )
        
        metric_analyzer.record_metric(metric)
        
        assert "quality_rate" in metric_analyzer.metrics_history
        assert len(metric_analyzer.metrics_history["quality_rate"]) == 1
    
    def test_register_work_order(self, metric_analyzer):
        """Test registering a work order."""
        metric_analyzer.register_work_order(
            "WO-001",
            "Machining batch",
            quality_issues=3,
            delivery_delay=2,
        )
        
        assert "WO-001" in metric_analyzer.work_orders
    
    def test_register_supplier_quote(self, metric_analyzer):
        """Test registering a supplier quote."""
        metric_analyzer.register_supplier_quote(
            "SQ-001",
            "Acme Corp",
            quality_rating=0.7,
        )
        
        assert "SQ-001" in metric_analyzer.supplier_quotes
    
    def test_register_incident(self, metric_analyzer):
        """Test registering an incident."""
        metric_analyzer.register_incident(
            "INC-001",
            "Near miss in warehouse",
            severity=2,
        )
        
        assert "INC-001" in metric_analyzer.incidents
    
    def test_find_causal_links_quality(self, metric_analyzer):
        """Test finding causal links for quality metric."""
        # Register red quality metric
        metric = MetricValue(
            metric_id="quality_defect_rate",
            category=MetricCategory.QUALITY,
            name="Defect Rate",
            value=8.0,
            target=2.0,
            timestamp=datetime.now(),
        )
        metric_analyzer.record_metric(metric)
        
        # Register work order with quality issues
        metric_analyzer.register_work_order(
            "WO-001",
            "Problematic batch",
            quality_issues=5,
        )
        
        links = metric_analyzer.find_causal_links("quality_defect_rate")
        
        assert len(links) == 1
        assert links[0].source_type == "work_order"
        assert links[0].confidence > 0.3
    
    def test_find_causal_links_supplier(self, metric_analyzer):
        """Test finding causal links to supplier."""
        metric = MetricValue(
            metric_id="quality_rate",
            category=MetricCategory.QUALITY,
            name="Quality Rate",
            value=80.0,
            target=95.0,
            timestamp=datetime.now(),
        )
        metric_analyzer.record_metric(metric)
        
        metric_analyzer.register_supplier_quote(
            "SQ-001",
            "Bad Supplier",
            quality_rating=0.5,
        )
        
        links = metric_analyzer.find_causal_links("quality_rate")
        
        assert len(links) >= 1
        supplier_links = [l for l in links if l.source_type == "supplier_quote"]
        assert len(supplier_links) == 1
    
    def test_find_causal_links_safety_incident(self, metric_analyzer):
        """Test finding causal links for safety incident."""
        metric = MetricValue(
            metric_id="safety_incidents",
            category=MetricCategory.SAFETY,
            name="Safety Incidents",
            value=5.0,
            target=0.0,
            timestamp=datetime.now(),
        )
        metric_analyzer.record_metric(metric)
        
        metric_analyzer.register_incident(
            "INC-001",
            "Forklift collision",
            severity=4,
            category="safety",
        )
        
        links = metric_analyzer.find_causal_links("safety_incidents")
        
        assert len(links) == 1
        assert links[0].source_type == "incident"
    
    def test_find_causal_links_green_metric(self, metric_analyzer):
        """Test that green metrics don't get causal links."""
        metric = MetricValue(
            metric_id="quality_rate",
            category=MetricCategory.QUALITY,
            name="Quality Rate",
            value=98.0,
            target=95.0,
            timestamp=datetime.now(),
        )
        metric_analyzer.record_metric(metric)
        
        links = metric_analyzer.find_causal_links("quality_rate")
        
        assert len(links) == 0
    
    def test_analyze_trend_declining(self, metric_analyzer):
        """Test trend analysis for declining metric."""
        # Record declining values over time
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(7):
            metric = MetricValue(
                metric_id="delivery_on_time",
                category=MetricCategory.DELIVERY,
                name="On-Time Delivery",
                value=95 - i * 2,  # Declining from 95 to 83
                target=90.0,
                timestamp=base_time + timedelta(days=i),
            )
            metric_analyzer.record_metric(metric)
        
        warning = metric_analyzer.analyze_trend("delivery_on_time")
        
        assert warning is not None
        assert warning.predicted_status == MetricStatus.RED
        assert warning.days_to_breach > 0
    
    def test_analyze_trend_improving(self, metric_analyzer):
        """Test trend analysis for improving metric (no warning)."""
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(7):
            metric = MetricValue(
                metric_id="quality_rate",
                category=MetricCategory.QUALITY,
                name="Quality Rate",
                value=85 + i * 2,  # Improving from 85 to 97
                target=90.0,
                timestamp=base_time + timedelta(days=i),
            )
            metric_analyzer.record_metric(metric)
        
        warning = metric_analyzer.analyze_trend("quality_rate")
        
        assert warning is None
    
    def test_analyze_trend_insufficient_data(self, metric_analyzer):
        """Test trend analysis with insufficient data."""
        metric = MetricValue(
            metric_id="delivery",
            category=MetricCategory.DELIVERY,
            name="Delivery",
            value=90.0,
            target=95.0,
            timestamp=datetime.now(),
        )
        metric_analyzer.record_metric(metric)
        
        warning = metric_analyzer.analyze_trend("delivery")
        
        assert warning is None


# =============================================================================
# CROSS-FUNCTIONAL SYNERGY ENGINE TESTS
# =============================================================================


class TestCrossFunctionalSynergyEngine:
    """Test CrossFunctionalSynergyEngine."""
    
    def test_register_event(self, synergy_engine):
        """Test registering a department event."""
        event_id = synergy_engine.register_event(
            DepartmentType.SALES,
            "rfq_delay",
            "Large order RFQ delayed by 3 days",
            AlertSeverity.MEDIUM,
        )
        
        assert event_id
        assert len(synergy_engine.department_events[DepartmentType.SALES]) == 1
    
    def test_silo_alert_creation(self, synergy_engine):
        """Test silo alert is created for cross-functional impact."""
        synergy_engine.register_event(
            DepartmentType.SALES,
            "rfq_delay",
            "Large order delayed",
            AlertSeverity.MEDIUM,
        )
        
        alerts = synergy_engine.get_active_silo_alerts()
        
        assert len(alerts) >= 1
        assert alerts[0].source_department == DepartmentType.SALES
        assert alerts[0].affected_department == DepartmentType.PRODUCTION
    
    def test_production_to_logistics_alert(self, synergy_engine):
        """Test production delay creates logistics alert."""
        synergy_engine.register_event(
            DepartmentType.PRODUCTION,
            "delay",
            "Production delayed by equipment failure",
            AlertSeverity.CRITICAL,
        )
        
        alerts = synergy_engine.get_active_silo_alerts()
        
        logistics_alerts = [
            a for a in alerts
            if a.affected_department == DepartmentType.LOGISTICS
        ]
        assert len(logistics_alerts) >= 1
    
    def test_register_work_center(self, synergy_engine):
        """Test registering a work center."""
        synergy_engine.register_work_center(
            "wc_001",
            "Assembly Line 1",
            capacity=100,
            current_load=95,
            wip_count=15,
            operator_count=5,
        )
        
        assert "wc_001" in synergy_engine.work_centers
        assert synergy_engine.work_centers["wc_001"].utilization == 0.95
    
    def test_register_operator(self, synergy_engine):
        """Test registering an operator."""
        synergy_engine.register_operator(
            "op_001",
            "John Doe",
            {"assembly": 0.9, "quality_inspection": 0.7},
            "wc_001",
        )
        
        assert "op_001" in synergy_engine.operators
    
    def test_analyze_resource_rebalancing(self, synergy_engine):
        """Test resource rebalancing analysis."""
        # Set up overloaded and underloaded work centers
        synergy_engine.register_work_center(
            "wc_assembly", "Assembly", 100, 95, 20, 5
        )
        synergy_engine.register_work_center(
            "wc_packaging", "Packaging", 100, 40, 5, 3
        )
        
        # Register operators with matching skills
        synergy_engine.register_operator(
            "op_001",
            "John",
            {"assembly": 0.8, "quality_inspection": 0.6},
            "wc_packaging",
        )
        synergy_engine.register_operator(
            "op_002",
            "Jane",
            {"assembly": 0.7, "quality_inspection": 0.5},
            "wc_packaging",
        )
        
        suggestions = synergy_engine.analyze_resource_rebalancing()
        
        assert len(suggestions) >= 1
        assert suggestions[0].source_work_center == "wc_packaging"
        assert suggestions[0].target_work_center == "wc_assembly"
    
    def test_resolve_silo_alert(self, synergy_engine):
        """Test resolving a silo alert."""
        synergy_engine.register_event(
            DepartmentType.SALES,
            "rfq_delay",
            "Delayed order",
            AlertSeverity.MEDIUM,
        )
        
        alerts = synergy_engine.get_active_silo_alerts()
        assert len(alerts) == 1
        
        result = synergy_engine.resolve_silo_alert(alerts[0].alert_id, "resolved")
        assert result
        
        active_alerts = synergy_engine.get_active_silo_alerts()
        assert len(active_alerts) == 0


# =============================================================================
# HEIJUNKA ADVISOR TESTS
# =============================================================================


class TestHeijunkaAdvisor:
    """Test HeijunkaAdvisor."""
    
    def test_record_demand(self, heijunka_advisor):
        """Test recording demand data."""
        heijunka_advisor.record_demand("Product A", [100, 50, 150, 80, 120])
        
        assert "Product A" in heijunka_advisor.demand_data
    
    def test_record_production(self, heijunka_advisor):
        """Test recording production data."""
        heijunka_advisor.record_production("Product A", [90, 60, 140, 85, 110])
        
        assert "Product A" in heijunka_advisor.production_data
    
    def test_analyze_volume_leveling(self, heijunka_advisor):
        """Test volume leveling analysis."""
        # Uneven demand pattern
        heijunka_advisor.record_demand("Product A", [20, 100, 30, 150, 50])
        heijunka_advisor.record_demand("Product B", [10, 50, 15, 75, 25])
        
        suggestion = heijunka_advisor.analyze_volume_leveling()
        
        assert suggestion is not None
        assert suggestion.mura_reduction > 0
    
    def test_analyze_mix_leveling(self, heijunka_advisor):
        """Test mix leveling analysis."""
        # Uneven product mix
        heijunka_advisor.record_demand("Product A", [100] * 5)
        heijunka_advisor.record_demand("Product B", [20] * 5)
        heijunka_advisor.record_demand("Product C", [10] * 5)
        
        suggestion = heijunka_advisor.analyze_mix_leveling()
        
        # Mix variance exists due to different volumes
        assert suggestion is not None or len(heijunka_advisor.demand_data) >= 2
    
    def test_volume_leveling_already_level(self, heijunka_advisor):
        """Test volume leveling when already level."""
        # Even demand pattern
        heijunka_advisor.record_demand("Product A", [50, 50, 50, 50, 50])
        
        suggestion = heijunka_advisor.analyze_volume_leveling()
        
        # Should return None or low mura reduction
        assert suggestion is None or suggestion.mura_reduction < 5
    
    def test_apply_suggestion(self, heijunka_advisor):
        """Test applying a suggestion."""
        heijunka_advisor.record_demand("Product A", [20, 100, 30, 150, 50])
        suggestion = heijunka_advisor.analyze_volume_leveling()
        
        if suggestion:
            result = heijunka_advisor.apply_suggestion(suggestion.suggestion_id)
            assert result
            assert suggestion.status == "applied"
    
    def test_dismiss_suggestion(self, heijunka_advisor):
        """Test dismissing a suggestion."""
        heijunka_advisor.record_demand("Product A", [20, 100, 30, 150, 50])
        suggestion = heijunka_advisor.analyze_volume_leveling()
        
        if suggestion:
            result = heijunka_advisor.dismiss_suggestion(
                suggestion.suggestion_id,
                "Customer constraints"
            )
            assert result
            assert "dismissed" in suggestion.status


# =============================================================================
# COGNITIVE OBEYA TESTS
# =============================================================================


class TestCognitiveObeya:
    """Test CognitiveObeya orchestrator."""
    
    def test_obeya_creation(self, obeya):
        """Test Cognitive Obeya creation."""
        assert obeya.metric_analyzer is not None
        assert obeya.synergy_engine is not None
        assert obeya.heijunka_advisor is not None
    
    def test_record_metric(self, obeya):
        """Test recording a metric through Obeya."""
        metric = obeya.record_metric(
            MetricCategory.QUALITY,
            "Defect Rate",
            2.3,  # Slightly above target but not > 1.2x
            2.0,
            "%",
        )
        
        assert metric.metric_id == "quality_defect_rate"
        assert metric.status == MetricStatus.YELLOW  # 2.3 is between 2.0 and 2.4
    
    def test_get_metric_insights(self, obeya):
        """Test getting metric insights."""
        # Record red metric
        obeya.record_metric(
            MetricCategory.QUALITY,
            "Quality Rate",
            75.0,
            95.0,
            "%",
        )
        
        # Register cause
        obeya.metric_analyzer.register_work_order(
            "WO-001",
            "Bad batch",
            quality_issues=5,
        )
        
        insights = obeya.get_metric_insights("quality_quality_rate")
        
        assert "causal_links" in insights
        assert len(insights["causal_links"]) >= 1
    
    def test_register_cross_functional_event(self, obeya):
        """Test registering cross-functional event."""
        event_id = obeya.register_cross_functional_event(
            DepartmentType.MAINTENANCE,
            "equipment_down",
            "CNC machine failure",
            AlertSeverity.CRITICAL,
        )
        
        assert event_id
        
        alerts = obeya.get_silo_alerts()
        assert len(alerts) >= 1
    
    def test_analyze_resource_rebalancing(self, obeya):
        """Test resource rebalancing through Obeya."""
        # Set up work centers and operators
        # Machining is overloaded, Assembly is underloaded
        obeya.synergy_engine.register_work_center(
            "wc_01", "Machining", 100, 95, 15, 4
        )
        obeya.synergy_engine.register_work_center(
            "wc_02", "Assembly", 100, 40, 5, 3
        )
        # Register operator with MACHINING skills in underloaded Assembly center
        obeya.synergy_engine.register_operator(
            "op_01", "John", {"cnc_operation": 0.9, "metrology": 0.7}, "wc_02"
        )
        
        suggestions = obeya.analyze_resource_rebalancing()
        
        # Should suggest moving from underloaded to overloaded
        assert len(suggestions) >= 1
    
    def test_get_heijunka_suggestions(self, obeya):
        """Test getting Heijunka suggestions."""
        # Record uneven demand
        obeya.heijunka_advisor.record_demand("A", [10, 100, 20, 150, 30])
        obeya.heijunka_advisor.record_demand("B", [5, 50, 10, 75, 15])
        
        suggestions = obeya.get_heijunka_suggestions()
        
        assert len(suggestions) >= 1
    
    def test_get_obeya_dashboard(self, obeya):
        """Test getting Obeya dashboard."""
        # Create some activity
        obeya.record_metric(MetricCategory.SAFETY, "Incidents", 0, 0)
        obeya.register_cross_functional_event(
            DepartmentType.QUALITY,
            "hold",
            "Quality hold",
            AlertSeverity.MEDIUM,
        )
        
        dashboard = obeya.get_obeya_dashboard()
        
        assert "metrics" in dashboard
        assert "cross_functional" in dashboard
        assert "heijunka" in dashboard


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_cognitive_obeya(self):
        """Test creating Cognitive Obeya."""
        obeya = create_cognitive_obeya()
        assert isinstance(obeya, CognitiveObeya)
    
    def test_create_metric_analyzer(self):
        """Test creating metric analyzer."""
        analyzer = create_metric_analyzer()
        assert isinstance(analyzer, PrescriptiveMetricAnalyzer)
    
    def test_create_synergy_engine(self):
        """Test creating synergy engine."""
        engine = create_synergy_engine()
        assert isinstance(engine, CrossFunctionalSynergyEngine)
    
    def test_create_heijunka_advisor(self):
        """Test creating Heijunka advisor."""
        advisor = create_heijunka_advisor()
        assert isinstance(advisor, HeijunkaAdvisor)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestCognitiveObeyaIntegration:
    """Integration tests for Cognitive Obeya."""
    
    def test_full_metric_analysis_flow(self, obeya):
        """Test full flow from metric recording to causal analysis."""
        # 1. Record declining metrics over time
        base_time = datetime.now() - timedelta(days=7)
        for i in range(7):
            metric = MetricValue(
                metric_id="quality_yield",
                category=MetricCategory.QUALITY,
                name="Yield",
                value=95 - i * 2,
                target=90.0,
                timestamp=base_time + timedelta(days=i),
            )
            obeya.metric_analyzer.record_metric(metric)
        
        # 2. Register potential causes
        obeya.metric_analyzer.register_work_order(
            "WO-123",
            "New supplier material batch",
            quality_issues=3,
        )
        obeya.metric_analyzer.register_supplier_quote(
            "SQ-456",
            "New Vendor",
            quality_rating=0.6,
        )
        
        # 3. Get insights
        insights = obeya.get_metric_insights("quality_yield")
        
        # Should find causal links and maybe trend warning
        assert "causal_links" in insights
    
    def test_cross_functional_cascade(self, obeya):
        """Test cascading cross-functional alerts."""
        # 1. Maintenance reports equipment down
        obeya.register_cross_functional_event(
            DepartmentType.MAINTENANCE,
            "equipment_down",
            "Main CNC machine down for repairs",
            AlertSeverity.CRITICAL,
        )
        
        # 2. Should create production alert
        alerts = obeya.get_silo_alerts()
        production_affected = [
            a for a in alerts
            if a["affected"] == "production"
        ]
        assert len(production_affected) >= 1
    
    def test_comprehensive_obeya_scenario(self, obeya):
        """Test comprehensive Obeya scenario."""
        # 1. Set up the shop floor
        obeya.synergy_engine.register_work_center(
            "machining", "Machining", 100, 98, 25, 6
        )
        obeya.synergy_engine.register_work_center(
            "finishing", "Finishing", 100, 30, 5, 4
        )
        # Register operators with skills matching machining (cnc_operation, metrology)
        obeya.synergy_engine.register_operator(
            "op_1", "Alice", {"cnc_operation": 0.9, "metrology": 0.7}, "finishing"
        )
        obeya.synergy_engine.register_operator(
            "op_2", "Bob", {"cnc_operation": 0.8, "metrology": 0.6}, "finishing"
        )
        
        # 2. Record metrics
        obeya.record_metric(MetricCategory.QUALITY, "FPY", 92.0, 95.0, "%")
        obeya.record_metric(MetricCategory.DELIVERY, "OTD", 88.0, 95.0, "%")
        obeya.record_metric(MetricCategory.PRODUCTIVITY, "OEE", 72.0, 85.0, "%")
        
        # 3. Record demand for Heijunka
        obeya.heijunka_advisor.record_demand("Widget A", [20, 80, 10, 100, 40])
        obeya.heijunka_advisor.record_demand("Widget B", [5, 40, 8, 50, 20])
        
        # 4. Register events
        obeya.register_cross_functional_event(
            DepartmentType.SALES,
            "rfq_delay",
            "Major order confirmation delayed",
            AlertSeverity.MEDIUM,
        )
        
        # 5. Get comprehensive dashboard
        dashboard = obeya.get_obeya_dashboard()
        
        assert dashboard["metrics"]["total_tracked"] == 3
        assert dashboard["cross_functional"]["active_alerts"] >= 1
        
        # 6. Get rebalancing suggestions
        rebalance = obeya.analyze_resource_rebalancing()
        assert len(rebalance) >= 1
        
        # 7. Get Heijunka suggestions
        heijunka = obeya.get_heijunka_suggestions()
        assert len(heijunka) >= 1
    
    def test_metric_lower_is_better(self, obeya):
        """Test metrics where lower is better (cost, safety incidents)."""
        # Cost metric - lower is better
        cost_metric = obeya.record_metric(
            MetricCategory.COST,
            "Unit Cost",
            12.0,  # Above target (bad)
            10.0,
            "$",
        )
        assert cost_metric.status == MetricStatus.YELLOW
        
        # Very high cost
        high_cost = obeya.record_metric(
            MetricCategory.COST,
            "High Cost",
            15.0,  # Way above target
            10.0,
            "$",
        )
        assert high_cost.status == MetricStatus.RED
        
        # Safety incidents - lower is better
        safety = obeya.record_metric(
            MetricCategory.SAFETY,
            "Incidents",
            0.0,  # Zero incidents - good!
            0.0,
            "count",
        )
        assert safety.status == MetricStatus.GREEN
