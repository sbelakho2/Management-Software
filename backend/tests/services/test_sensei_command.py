"""
Tests for Sensei Command: CEO Strategic Control Plane.

Tests cover:
- Strategic North Star Dashboard (Executive KPIs, Financial Health, Risk Heatmap)
- Autonomous System Health & Evolution Visibility
- Executive Intelligence Synthesis (NL2SQL, Strategic Briefings)
- Advanced Deep-Database Analytics
- Total Visibility & Governance (CEO Super-View, Employee Analytics)
"""

from datetime import datetime, timedelta

import pytest

from sensei.services.sensei_command import (
    # Enums
    KPIType,
    RiskLevel,
    RiskCategory,
    LearningMetricType,
    QuerySecurityLevel,
    ExportFormat,
    EmployeeRiskType,
    PersonaType,
    # Data models
    ExecutiveKPI,
    FinancialHealth,
    RiskItem,
    RiskHeatmap,
    SystemHealthStatus,
    LearningProgression,
    MaintenanceAuditEntry,
    NL2SQLQuery,
    StrategicBriefing,
    CrossSiloCorrelation,
    MarginLeakage,
    CohortAnalysis,
    Bottleneck,
    AuditTrailEntry,
    EmployeeAnalytics,
    TalentRiskAlert,
    PersonaOverlay,
    # Components
    ExecutiveKPIAggregator,
    FinancialHealthMonitor,
    RiskHeatmapGenerator,
    BrainHealthDashboard,
    LearningProgressionAnalytics,
    MaintenanceAuditLog,
    NL2SQLEngine,
    StrategicBriefingGenerator,
    DeepDatabaseAnalytics,
    GlobalAuditTrail,
    CEOSuperView,
    EmployeeIntelligenceAnalytics,
    SenseiCommand,
    # Factories
    create_kpi_aggregator,
    create_financial_monitor,
    create_risk_generator,
    create_brain_dashboard,
    create_nl2sql_engine,
    create_briefing_generator,
    create_deep_analytics,
    create_audit_trail,
    create_ceo_view,
    create_employee_analytics,
    create_sensei_command,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_kpis():
    """Sample executive KPIs."""
    return [
        ExecutiveKPI(
            kpi_type=KPIType.MARGIN,
            name="Gross Margin",
            value=0.22,
            target=0.25,
            unit="%",
            trend=2.5,
            period="2024-Q1",
            site_id="site_1",
            product_family="automotive",
        ),
        ExecutiveKPI(
            kpi_type=KPIType.MARGIN,
            name="Gross Margin",
            value=0.28,
            target=0.25,
            unit="%",
            trend=3.2,
            period="2024-Q1",
            site_id="site_2",
            product_family="aerospace",
        ),
        ExecutiveKPI(
            kpi_type=KPIType.OEE,
            name="Overall Equipment Effectiveness",
            value=0.82,
            target=0.85,
            unit="%",
            trend=-1.5,
            period="2024-Q1",
            site_id="site_1",
        ),
        ExecutiveKPI(
            kpi_type=KPIType.WIN_RATE,
            name="Quote Win Rate",
            value=0.35,
            target=0.40,
            unit="%",
            trend=5.0,
            period="2024-Q1",
        ),
    ]


@pytest.fixture
def sample_financial_health():
    """Sample financial health data."""
    return FinancialHealth(
        quote_to_cash_velocity=42.5,
        pipeline_value=2500000.0,
        high_value_rfqs=15,
        conversion_rate=0.28,
        avg_margin=0.23,
        revenue_forecast=5000000.0,
        period="2024-Q1",
    )


@pytest.fixture
def sample_risks():
    """Sample risk items."""
    return [
        RiskItem(
            risk_id="risk_1",
            category=RiskCategory.SUPPLY_CHAIN,
            level=RiskLevel.CRITICAL,
            title="Single source dependency: Acme Parts",
            description="Critical component relies on single supplier",
            impact_score=9.0,
            probability=0.4,
            affected_sites=["site_1", "site_2"],
            mitigation_status="pending",
            detected_at=datetime.now(),
        ),
        RiskItem(
            risk_id="risk_2",
            category=RiskCategory.PRODUCTION,
            level=RiskLevel.HIGH,
            title="OEE below target at Site 1",
            description="Equipment availability issues",
            impact_score=7.0,
            probability=0.6,
            affected_sites=["site_1"],
            mitigation_status="in_progress",
            detected_at=datetime.now(),
        ),
        RiskItem(
            risk_id="risk_3",
            category=RiskCategory.QUALITY,
            level=RiskLevel.MEDIUM,
            title="Elevated defect rate in Line 3",
            description="Quality issues detected",
            impact_score=5.0,
            probability=0.3,
            affected_sites=["site_1"],
            mitigation_status="monitoring",
            detected_at=datetime.now(),
        ),
    ]


@pytest.fixture
def sample_employees():
    """Sample employee analytics data."""
    return [
        EmployeeAnalytics(
            employee_id="emp_1",
            skill_score=0.85,
            cycle_time_trend=-0.05,
            error_rate_trend=-0.02,
            a3_participation=5,
            knowledge_contributions=12,
            engagement_score=0.88,
            risk_flags=[],
        ),
        EmployeeAnalytics(
            employee_id="emp_2",
            skill_score=0.65,
            cycle_time_trend=0.20,  # Drift above threshold
            error_rate_trend=0.18,
            a3_participation=0,
            knowledge_contributions=1,
            engagement_score=0.35,  # Low engagement
            risk_flags=[EmployeeRiskType.BURNOUT],
        ),
        EmployeeAnalytics(
            employee_id="emp_3",
            skill_score=0.75,
            cycle_time_trend=0.08,
            error_rate_trend=0.05,
            a3_participation=2,
            knowledge_contributions=5,
            engagement_score=0.72,
            risk_flags=[],
        ),
    ]


# =============================================================================
# ENUM TESTS
# =============================================================================


class TestEnums:
    """Test all enums."""
    
    def test_kpi_type_values(self):
        assert KPIType.YIELD.value == "yield"
        assert KPIType.OEE.value == "oee"
        assert KPIType.MARGIN.value == "margin"
        assert KPIType.WIN_RATE.value == "win_rate"
        assert KPIType.QUOTE_TO_CASH.value == "quote_to_cash"
    
    def test_risk_level_values(self):
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"
    
    def test_risk_category_values(self):
        assert RiskCategory.SUPPLY_CHAIN.value == "supply_chain"
        assert RiskCategory.PRODUCTION.value == "production"
        assert RiskCategory.QUALITY.value == "quality"
        assert RiskCategory.FINANCIAL.value == "financial"
    
    def test_learning_metric_type_values(self):
        assert LearningMetricType.CONFIDENCE_IMPROVEMENT.value == "confidence_improvement"
        assert LearningMetricType.AUTONOMOUS_UPDATES.value == "autonomous_updates"
    
    def test_query_security_level_values(self):
        assert QuerySecurityLevel.READ_ONLY.value == "read_only"
        assert QuerySecurityLevel.RESTRICTED.value == "restricted"
        assert QuerySecurityLevel.ELEVATED.value == "elevated"
    
    def test_export_format_values(self):
        assert ExportFormat.PDF.value == "pdf"
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.PPTX.value == "pptx"
        assert ExportFormat.JSON.value == "json"
    
    def test_employee_risk_type_values(self):
        assert EmployeeRiskType.BURNOUT.value == "burnout"
        assert EmployeeRiskType.RETENTION.value == "retention"
        assert EmployeeRiskType.PERFORMANCE_DRIFT.value == "performance_drift"
    
    def test_persona_type_values(self):
        assert PersonaType.GM.value == "gm"
        assert PersonaType.OPERATOR.value == "operator"
        assert PersonaType.SALES.value == "sales"


# =============================================================================
# EXECUTIVE KPI AGGREGATOR TESTS
# =============================================================================


class TestExecutiveKPIAggregator:
    """Test KPI aggregation functionality."""
    
    def test_init(self):
        agg = ExecutiveKPIAggregator()
        assert len(agg.kpis) == 0
    
    def test_add_kpi(self, sample_kpis):
        agg = ExecutiveKPIAggregator()
        for kpi in sample_kpis:
            agg.add_kpi(kpi)
        
        assert len(agg.kpis) == 4
    
    def test_get_aggregate_view(self, sample_kpis):
        agg = ExecutiveKPIAggregator()
        for kpi in sample_kpis:
            agg.add_kpi(kpi)
        
        view = agg.get_aggregate_view()
        
        assert KPIType.MARGIN in view
        assert view[KPIType.MARGIN]["count"] == 2
        assert view[KPIType.MARGIN]["avg_value"] == 0.25  # (0.22 + 0.28) / 2
    
    def test_get_site_comparison(self, sample_kpis):
        agg = ExecutiveKPIAggregator()
        for kpi in sample_kpis:
            agg.add_kpi(kpi)
        
        comparison = agg.get_site_comparison(KPIType.MARGIN)
        
        assert "site_1" in comparison
        assert comparison["site_1"] == 0.22
        assert comparison["site_2"] == 0.28
    
    def test_get_trend_analysis_improving(self, sample_kpis):
        agg = ExecutiveKPIAggregator()
        for kpi in sample_kpis:
            agg.add_kpi(kpi)
        
        analysis = agg.get_trend_analysis(KPIType.MARGIN)
        
        assert analysis["direction"] == "improving"
        assert analysis["improving_count"] == 2
        assert analysis["declining_count"] == 0
    
    def test_get_trend_analysis_declining(self, sample_kpis):
        agg = ExecutiveKPIAggregator()
        for kpi in sample_kpis:
            agg.add_kpi(kpi)
        
        analysis = agg.get_trend_analysis(KPIType.OEE)
        
        assert analysis["direction"] == "declining"
        assert analysis["declining_count"] == 1
    
    def test_get_trend_analysis_empty(self):
        agg = ExecutiveKPIAggregator()
        analysis = agg.get_trend_analysis(KPIType.YIELD)
        
        assert analysis == {}


# =============================================================================
# FINANCIAL HEALTH MONITOR TESTS
# =============================================================================


class TestFinancialHealthMonitor:
    """Test financial health monitoring."""
    
    def test_init(self):
        monitor = FinancialHealthMonitor()
        assert monitor.current_health is None
    
    def test_update_health(self, sample_financial_health):
        monitor = FinancialHealthMonitor()
        monitor.update_health(sample_financial_health)
        
        assert monitor.current_health is not None
        assert monitor.current_health.pipeline_value == 2500000.0
    
    def test_get_quote_to_cash_trend(self, sample_financial_health):
        monitor = FinancialHealthMonitor()
        
        for i in range(5):
            health = FinancialHealth(
                quote_to_cash_velocity=40 + i * 2,
                pipeline_value=2000000.0,
                high_value_rfqs=10,
                conversion_rate=0.25,
                avg_margin=0.20,
                revenue_forecast=4000000.0,
                period=f"2024-M{i+1}",
            )
            monitor.update_health(health)
        
        trend = monitor.get_quote_to_cash_trend(periods=3)
        
        assert len(trend) == 3
        assert trend[-1] == 48  # Last value
    
    def test_get_pipeline_health(self, sample_financial_health):
        monitor = FinancialHealthMonitor()
        monitor.update_health(sample_financial_health)
        
        health = monitor.get_pipeline_health()
        
        assert "pipeline_value" in health
        assert "health_score" in health
        assert health["pipeline_value"] == 2500000.0
    
    def test_get_pipeline_health_empty(self):
        monitor = FinancialHealthMonitor()
        health = monitor.get_pipeline_health()
        
        assert health == {}
    
    def test_health_score_calculation(self, sample_financial_health):
        monitor = FinancialHealthMonitor()
        monitor.update_health(sample_financial_health)
        
        health = monitor.get_pipeline_health()
        
        assert 0 <= health["health_score"] <= 100


# =============================================================================
# RISK HEATMAP GENERATOR TESTS
# =============================================================================


class TestRiskHeatmapGenerator:
    """Test risk heatmap generation."""
    
    def test_init(self):
        gen = RiskHeatmapGenerator()
        assert len(gen.risks) == 0
    
    def test_add_risk(self, sample_risks):
        gen = RiskHeatmapGenerator()
        for risk in sample_risks:
            gen.add_risk(risk)
        
        assert len(gen.risks) == 3
    
    def test_detect_supply_chain_risks(self):
        gen = RiskHeatmapGenerator()
        
        suppliers = [
            {"id": "s1", "name": "Acme", "is_single_source": True, "sites": ["site_1"]},
            {"id": "s2", "name": "Beta", "on_time_rate": 0.75, "sites": ["site_2"]},
            {"id": "s3", "name": "Gamma", "on_time_rate": 0.95},
        ]
        
        detected = gen.detect_supply_chain_risks(suppliers)
        
        assert len(detected) == 2  # Single source + low on-time rate
    
    def test_generate_heatmap(self, sample_risks):
        gen = RiskHeatmapGenerator()
        for risk in sample_risks:
            gen.add_risk(risk)
        
        heatmap = gen.generate_heatmap()
        
        assert isinstance(heatmap, RiskHeatmap)
        assert heatmap.total_critical == 1
        assert heatmap.total_high == 1
        assert RiskCategory.SUPPLY_CHAIN in heatmap.category_counts
    
    def test_get_risks_by_category(self, sample_risks):
        gen = RiskHeatmapGenerator()
        for risk in sample_risks:
            gen.add_risk(risk)
        
        supply_chain = gen.get_risks_by_category(RiskCategory.SUPPLY_CHAIN)
        
        assert len(supply_chain) == 1
        assert supply_chain[0].risk_id == "risk_1"
    
    def test_get_risks_by_level(self, sample_risks):
        gen = RiskHeatmapGenerator()
        for risk in sample_risks:
            gen.add_risk(risk)
        
        critical = gen.get_risks_by_level(RiskLevel.CRITICAL)
        
        assert len(critical) == 1


# =============================================================================
# BRAIN HEALTH DASHBOARD TESTS
# =============================================================================


class TestBrainHealthDashboard:
    """Test brain health dashboard functionality."""
    
    def test_init(self):
        dashboard = BrainHealthDashboard()
        assert len(dashboard.component_status) == 0
    
    def test_update_component(self):
        dashboard = BrainHealthDashboard()
        
        status = SystemHealthStatus(
            component="database",
            status="healthy",
            last_check=datetime.now(),
            uptime_percent=99.9,
        )
        dashboard.update_component(status)
        
        assert "database" in dashboard.component_status
    
    def test_get_overall_health_healthy(self):
        dashboard = BrainHealthDashboard()
        
        for comp in ["database", "api", "worker"]:
            dashboard.update_component(SystemHealthStatus(
                component=comp,
                status="healthy",
                last_check=datetime.now(),
                uptime_percent=99.5,
            ))
        
        health = dashboard.get_overall_health()
        
        assert health["status"] == "healthy"
        assert health["components"] == 3
        assert health["healthy_count"] == 3
    
    def test_get_overall_health_degraded(self):
        dashboard = BrainHealthDashboard()
        
        dashboard.update_component(SystemHealthStatus(
            component="database",
            status="healthy",
            last_check=datetime.now(),
            uptime_percent=99.9,
        ))
        dashboard.update_component(SystemHealthStatus(
            component="api",
            status="down",
            last_check=datetime.now(),
            uptime_percent=85.0,
        ))
        
        health = dashboard.get_overall_health()
        
        assert health["status"] == "degraded"
        assert health["down_count"] == 1
    
    def test_get_component_details(self):
        dashboard = BrainHealthDashboard()
        
        status = SystemHealthStatus(
            component="ml_engine",
            status="healthy",
            last_check=datetime.now(),
            uptime_percent=99.0,
            metrics={"inference_time_ms": 50},
        )
        dashboard.update_component(status)
        
        details = dashboard.get_component_details("ml_engine")
        
        assert details is not None
        assert details.uptime_percent == 99.0
    
    def test_take_snapshot(self):
        dashboard = BrainHealthDashboard()
        
        dashboard.update_component(SystemHealthStatus(
            component="test",
            status="healthy",
            last_check=datetime.now(),
            uptime_percent=100.0,
        ))
        
        dashboard.take_snapshot()
        
        assert len(dashboard._status_history) == 1


# =============================================================================
# LEARNING PROGRESSION ANALYTICS TESTS
# =============================================================================


class TestLearningProgressionAnalytics:
    """Test learning progression analytics."""
    
    def test_init(self):
        analytics = LearningProgressionAnalytics()
        assert len(analytics.progressions) == 0
    
    def test_add_progression(self):
        analytics = LearningProgressionAnalytics()
        
        prog = LearningProgression(
            metric_type=LearningMetricType.CONFIDENCE_IMPROVEMENT,
            current_value=0.92,
            baseline_value=0.85,
            improvement_percent=8.2,
            measurement_period="2024-Q1",
        )
        analytics.add_progression(prog)
        
        assert len(analytics.progressions) == 1
    
    def test_get_summary(self):
        analytics = LearningProgressionAnalytics()
        
        for metric in [LearningMetricType.CONFIDENCE_IMPROVEMENT, LearningMetricType.MODEL_ACCURACY]:
            analytics.add_progression(LearningProgression(
                metric_type=metric,
                current_value=0.9,
                baseline_value=0.8,
                improvement_percent=12.5,
                measurement_period="2024-Q1",
            ))
        
        summary = analytics.get_summary()
        
        assert "confidence_improvement" in summary
        assert summary["confidence_improvement"]["trend"] == "improving"
    
    def test_calculate_intelligence_index(self):
        analytics = LearningProgressionAnalytics()
        
        analytics.add_progression(LearningProgression(
            metric_type=LearningMetricType.CONFIDENCE_IMPROVEMENT,
            current_value=0.9,
            baseline_value=0.85,
            improvement_percent=15.0,
            measurement_period="2024-Q1",
        ))
        analytics.add_progression(LearningProgression(
            metric_type=LearningMetricType.MODEL_ACCURACY,
            current_value=0.92,
            baseline_value=0.88,
            improvement_percent=10.0,
            measurement_period="2024-Q1",
        ))
        
        index = analytics.calculate_intelligence_index()
        
        assert 0 <= index <= 100
        assert index > 50  # Positive improvement


# =============================================================================
# MAINTENANCE AUDIT LOG TESTS
# =============================================================================


class TestMaintenanceAuditLog:
    """Test maintenance audit logging."""
    
    def test_init(self):
        log = MaintenanceAuditLog()
        assert len(log.entries) == 0
    
    def test_log_action(self):
        log = MaintenanceAuditLog()
        
        entry = MaintenanceAuditEntry(
            action_id="action_1",
            action_type="vacuum",
            component="database",
            description="Vacuum old records",
            result="success",
            timestamp=datetime.now(),
            duration_seconds=45.2,
            triggered_by="schedule",
        )
        log.log_action(entry)
        
        assert len(log.entries) == 1
    
    def test_get_recent_actions(self):
        log = MaintenanceAuditLog()
        
        for i in range(10):
            log.log_action(MaintenanceAuditEntry(
                action_id=f"action_{i}",
                action_type="check",
                component="test",
                description=f"Check {i}",
                result="success",
                timestamp=datetime.now(),
                duration_seconds=1.0,
                triggered_by="manual",
            ))
        
        recent = log.get_recent_actions(limit=5)
        
        assert len(recent) == 5
    
    def test_get_actions_by_component(self):
        log = MaintenanceAuditLog()
        
        log.log_action(MaintenanceAuditEntry(
            action_id="a1",
            action_type="restart",
            component="database",
            description="Restart DB",
            result="success",
            timestamp=datetime.now(),
            duration_seconds=30.0,
            triggered_by="threshold",
        ))
        log.log_action(MaintenanceAuditEntry(
            action_id="a2",
            action_type="restart",
            component="api",
            description="Restart API",
            result="success",
            timestamp=datetime.now(),
            duration_seconds=10.0,
            triggered_by="manual",
        ))
        
        db_actions = log.get_actions_by_component("database")
        
        assert len(db_actions) == 1
    
    def test_get_action_summary(self):
        log = MaintenanceAuditLog()
        
        for i in range(5):
            log.log_action(MaintenanceAuditEntry(
                action_id=f"a{i}",
                action_type="vacuum" if i % 2 == 0 else "check",
                component="database",
                description=f"Action {i}",
                result="success",
                timestamp=datetime.now(),
                duration_seconds=10.0,
                triggered_by="schedule",
            ))
        
        summary = log.get_action_summary(days=7)
        
        assert summary["total_actions"] == 5
        assert "vacuum" in summary["by_type"]
        assert "check" in summary["by_type"]


# =============================================================================
# NL2SQL ENGINE TESTS
# =============================================================================


class TestNL2SQLEngine:
    """Test NL2SQL engine functionality."""
    
    def test_init(self):
        engine = NL2SQLEngine()
        assert engine.security_level == QuerySecurityLevel.READ_ONLY
    
    def test_init_custom_security(self):
        engine = NL2SQLEngine(security_level=QuerySecurityLevel.ELEVATED)
        assert engine.security_level == QuerySecurityLevel.ELEVATED
    
    def test_generate_sql_margin_query(self):
        engine = NL2SQLEngine()
        
        query = engine.generate_sql("Show me margin by segment")
        
        assert isinstance(query, NL2SQLQuery)
        assert "margin" in query.natural_language.lower()
        assert "SELECT" in query.generated_sql.upper()
    
    def test_generate_sql_oee_query(self):
        engine = NL2SQLEngine()
        
        query = engine.generate_sql("What is our OEE by site?")
        
        assert "site" in query.generated_sql.lower() or "production" in query.generated_sql.lower()
    
    def test_generate_sql_explanation(self):
        engine = NL2SQLEngine()
        
        query = engine.generate_sql("Show margin by segment")
        
        assert query.explanation is not None
        assert len(query.explanation) > 0
    
    def test_get_schema_context(self):
        engine = NL2SQLEngine()
        
        schema = engine.get_schema_context()
        
        assert "quotes" in schema
        assert "production" in schema
        assert "margin" in schema["quotes"]
    
    def test_validate_query_valid(self):
        engine = NL2SQLEngine()
        
        valid, message = engine.validate_query("SELECT * FROM quotes")
        
        assert valid is True
    
    def test_validate_query_blocked(self):
        engine = NL2SQLEngine()
        
        valid, message = engine.validate_query("DELETE FROM quotes")
        
        assert valid is False
        assert "DELETE" in message
    
    def test_validate_query_empty(self):
        engine = NL2SQLEngine()
        
        valid, message = engine.validate_query("")
        
        assert valid is False
        assert "Empty" in message


# =============================================================================
# STRATEGIC BRIEFING GENERATOR TESTS
# =============================================================================


class TestStrategicBriefingGenerator:
    """Test strategic briefing generation."""
    
    def test_init(self):
        gen = StrategicBriefingGenerator()
        assert len(gen.briefings) == 0
    
    def test_generate_briefing(self, sample_risks):
        gen = StrategicBriefingGenerator()
        
        kpis = {"margin": 0.22, "oee": 0.82, "win_rate": 0.35}
        
        briefing = gen.generate_briefing(
            kpis=kpis,
            risks=sample_risks,
            opportunities=["Expand market share"],
        )
        
        assert isinstance(briefing, StrategicBriefing)
        assert briefing.executive_summary is not None
        assert len(briefing.recommendations) > 0
    
    def test_generate_briefing_low_margin_warning(self):
        gen = StrategicBriefingGenerator()
        
        kpis = {"margin": 0.12, "oee": 0.85, "win_rate": 0.30}
        
        briefing = gen.generate_briefing(kpis=kpis, risks=[], opportunities=[])
        
        assert "margin" in briefing.executive_summary.lower() or "pressure" in briefing.executive_summary.lower()
    
    def test_export_briefing_json(self, sample_risks):
        gen = StrategicBriefingGenerator()
        
        kpis = {"margin": 0.25, "win_rate": 0.35}
        briefing = gen.generate_briefing(kpis=kpis, risks=[], opportunities=[])
        
        export = gen.export_briefing(briefing.briefing_id, ExportFormat.JSON)
        
        assert export["format"] == "json"
        assert "content" in export
    
    def test_export_briefing_csv(self, sample_risks):
        gen = StrategicBriefingGenerator()
        
        kpis = {"margin": 0.25, "win_rate": 0.35}
        briefing = gen.generate_briefing(kpis=kpis, risks=[], opportunities=[])
        
        export = gen.export_briefing(briefing.briefing_id, ExportFormat.CSV)
        
        assert export["format"] == "csv"
        assert "margin" in export["content"]
    
    def test_export_briefing_not_found(self):
        gen = StrategicBriefingGenerator()
        
        export = gen.export_briefing("nonexistent", ExportFormat.PDF)
        
        assert "error" in export


# =============================================================================
# DEEP DATABASE ANALYTICS TESTS
# =============================================================================


class TestDeepDatabaseAnalytics:
    """Test deep database analytics."""
    
    def test_init(self):
        analytics = DeepDatabaseAnalytics()
        assert len(analytics.correlations) == 0
    
    def test_analyze_cross_silo_correlation(self):
        analytics = DeepDatabaseAnalytics()
        
        rfqs = [{"id": 1, "completeness": 0.9}, {"id": 2, "completeness": 0.8}]
        production = [{"id": 1, "oee": 0.85}, {"id": 2, "oee": 0.82}]
        quotes = [{"id": 1, "margin": 0.22}]
        
        correlations = analytics.analyze_cross_silo_correlation(rfqs, production, quotes)
        
        assert len(correlations) >= 1
        assert correlations[0].data_sources is not None
    
    def test_detect_margin_leakage(self):
        analytics = DeepDatabaseAnalytics()
        
        quotes = [
            {"id": "q1", "cost": 1000, "segment": "auto"},
            {"id": "q2", "cost": 1500, "segment": "auto"},
            {"id": "q3", "cost": 2000, "segment": "auto"},
        ]
        actuals = [
            {"quote_id": "q1", "actual_cost": 1150},  # 15% overrun
            {"quote_id": "q2", "actual_cost": 1700},  # 13% overrun
            {"quote_id": "q3", "actual_cost": 2300},  # 15% overrun
        ]
        
        leakages = analytics.detect_margin_leakage(quotes, actuals)
        
        assert len(leakages) >= 1
        assert leakages[0].segment == "auto"
    
    def test_analyze_cohort_performance(self):
        analytics = DeepDatabaseAnalytics()
        
        products = [
            {"id": "p1", "launch_date": "2024-02-15", "margin_12m": 0.20, "oee": 0.82, "revenue": 100000},
            {"id": "p2", "launch_date": "2024-03-01", "margin_12m": 0.18, "oee": 0.78, "revenue": 80000},
            {"id": "p3", "launch_date": "2024-06-10", "margin_12m": 0.25, "oee": 0.85, "revenue": 120000},
        ]
        
        cohorts = analytics.analyze_cohort_performance(products)
        
        assert len(cohorts) >= 1
    
    def test_detect_bottlenecks(self):
        analytics = DeepDatabaseAnalytics()
        
        process_data = [
            {"step": "assembly_line1", "wait_time_hours": 3.5},
            {"step": "assembly_line1", "wait_time_hours": 4.0},
            {"step": "assembly_line1", "wait_time_hours": 3.2},
            {"step": "inspection", "wait_time_hours": 0.5},
        ]
        
        bottlenecks = analytics.detect_bottlenecks(process_data)
        
        assert len(bottlenecks) >= 1
        assert bottlenecks[0].avg_wait_time_hours > 2.0


# =============================================================================
# GLOBAL AUDIT TRAIL TESTS
# =============================================================================


class TestGlobalAuditTrail:
    """Test global audit trail functionality."""
    
    def test_init(self):
        trail = GlobalAuditTrail()
        assert len(trail.entries) == 0
    
    def test_log_entry(self):
        trail = GlobalAuditTrail()
        
        entry = AuditTrailEntry(
            entry_id="entry_1",
            entity_type="quote",
            entity_id="q123",
            action="update",
            user_id="user_1",
            timestamp=datetime.now(),
            old_value={"status": "draft"},
            new_value={"status": "submitted"},
            rationale="Ready for review",
        )
        trail.log_entry(entry)
        
        assert len(trail.entries) == 1
    
    def test_get_entity_history(self):
        trail = GlobalAuditTrail()
        
        for i in range(3):
            trail.log_entry(AuditTrailEntry(
                entry_id=f"e{i}",
                entity_type="quote",
                entity_id="q123",
                action=f"action_{i}",
                user_id="user_1",
                timestamp=datetime.now(),
                old_value=None,
                new_value=None,
            ))
        
        history = trail.get_entity_history("quote", "q123")
        
        assert len(history) == 3
    
    def test_get_user_actions(self):
        trail = GlobalAuditTrail()
        
        for i in range(5):
            trail.log_entry(AuditTrailEntry(
                entry_id=f"e{i}",
                entity_type="quote",
                entity_id=f"q{i}",
                action="view",
                user_id="user_1" if i < 3 else "user_2",
                timestamp=datetime.now(),
                old_value=None,
                new_value=None,
            ))
        
        actions = trail.get_user_actions("user_1")
        
        assert len(actions) == 3
    
    def test_search_by_entity_type(self):
        trail = GlobalAuditTrail()
        
        trail.log_entry(AuditTrailEntry(
            entry_id="e1", entity_type="quote", entity_id="q1",
            action="create", user_id="u1", timestamp=datetime.now(),
            old_value=None, new_value=None,
        ))
        trail.log_entry(AuditTrailEntry(
            entry_id="e2", entity_type="rfq", entity_id="r1",
            action="create", user_id="u1", timestamp=datetime.now(),
            old_value=None, new_value=None,
        ))
        
        results = trail.search(entity_type="quote")
        
        assert len(results) == 1
        assert results[0].entity_type == "quote"


# =============================================================================
# CEO SUPER VIEW TESTS
# =============================================================================


class TestCEOSuperView:
    """Test CEO super view functionality."""
    
    def test_init(self):
        view = CEOSuperView("ceo_user")
        assert view.ceo_user_id == "ceo_user"
        assert view.active_overlay is None
    
    def test_enable_persona_overlay(self):
        view = CEOSuperView("ceo_user")
        
        overlay = view.enable_persona_overlay(PersonaType.GM)
        
        assert overlay is not None
        assert overlay.persona == PersonaType.GM
        assert "a3_creator" in overlay.features_enabled
    
    def test_disable_persona_overlay(self):
        view = CEOSuperView("ceo_user")
        
        view.enable_persona_overlay(PersonaType.SALES)
        view.disable_persona_overlay()
        
        assert view.active_overlay is None
        assert len(view.overlay_history) == 1
    
    def test_switch_persona_overlay(self):
        view = CEOSuperView("ceo_user")
        
        view.enable_persona_overlay(PersonaType.GM)
        view.enable_persona_overlay(PersonaType.OPERATOR)
        
        assert view.active_overlay.persona == PersonaType.OPERATOR
        assert len(view.overlay_history) == 1
    
    def test_drill_to_source(self):
        view = CEOSuperView("ceo_user")
        
        result = view.drill_to_source("margin_kpi", 0.25)
        
        assert "underlying_records" in result
        assert "sample_records" in result
        assert len(result["sample_records"]) == 3
    
    def test_get_action_log(self):
        view = CEOSuperView("ceo_user")
        
        view.enable_persona_overlay(PersonaType.GM)
        view.drill_to_source("oee_kpi", 0.82)
        view.disable_persona_overlay()
        
        log = view.get_action_log()
        
        assert len(log) >= 3  # enable, drill, close


# =============================================================================
# EMPLOYEE INTELLIGENCE ANALYTICS TESTS
# =============================================================================


class TestEmployeeIntelligenceAnalytics:
    """Test employee analytics functionality."""
    
    def test_init(self):
        analytics = EmployeeIntelligenceAnalytics()
        assert analytics.gdpr_compliant is True
    
    def test_update_employee_analytics(self, sample_employees):
        analytics = EmployeeIntelligenceAnalytics()
        
        for emp in sample_employees:
            analytics.update_employee_analytics(emp)
        
        assert len(analytics.analytics) == 3
    
    def test_detect_performance_drift(self, sample_employees):
        analytics = EmployeeIntelligenceAnalytics()
        
        for emp in sample_employees:
            analytics.update_employee_analytics(emp)
        
        alerts = analytics.detect_performance_drift()
        
        # emp_2 has drift above threshold
        assert len(alerts) >= 1
        drift_alerts = [a for a in alerts if a.employee_id == "emp_2"]
        assert len(drift_alerts) >= 1
    
    def test_detect_burnout_risk(self, sample_employees):
        analytics = EmployeeIntelligenceAnalytics()
        
        for emp in sample_employees:
            analytics.update_employee_analytics(emp)
        
        alerts = analytics.detect_burnout_risk()
        
        # emp_2 has burnout indicators
        burnout_alerts = [a for a in alerts if a.risk_type == EmployeeRiskType.BURNOUT]
        assert len(burnout_alerts) >= 1
    
    def test_identify_mentors(self, sample_employees):
        analytics = EmployeeIntelligenceAnalytics()
        
        for emp in sample_employees:
            analytics.update_employee_analytics(emp)
        
        mentors = analytics.identify_mentors()
        
        # emp_1 has high skill score and contributions
        assert "emp_1" in mentors
    
    def test_get_retention_risk_score(self, sample_employees):
        analytics = EmployeeIntelligenceAnalytics()
        
        for emp in sample_employees:
            analytics.update_employee_analytics(emp)
        
        risk_1 = analytics.get_retention_risk_score("emp_1")
        risk_2 = analytics.get_retention_risk_score("emp_2")
        
        # emp_2 should have higher risk
        assert risk_2 > risk_1
    
    def test_get_retention_risk_unknown_employee(self):
        analytics = EmployeeIntelligenceAnalytics()
        
        risk = analytics.get_retention_risk_score("unknown")
        
        assert risk == 0.5  # Default for unknown


# =============================================================================
# SENSEI COMMAND ORCHESTRATOR TESTS
# =============================================================================


class TestSenseiCommand:
    """Test Sensei Command orchestrator."""
    
    def test_init(self):
        cmd = SenseiCommand("ceo_user")
        assert cmd.ceo_user_id == "ceo_user"
        assert cmd.kpi_aggregator is not None
        assert cmd.nl2sql_engine is not None
    
    def test_get_executive_dashboard(self):
        cmd = SenseiCommand("ceo_user")
        
        dashboard = cmd.get_executive_dashboard()
        
        assert "kpis" in dashboard
        assert "financial_health" in dashboard
        assert "risk_heatmap" in dashboard
        assert "system_health" in dashboard
    
    def test_query_database(self):
        cmd = SenseiCommand("ceo_user")
        
        query = cmd.query_database("Show me margin by segment")
        
        assert isinstance(query, NL2SQLQuery)
        assert query.generated_sql is not None
    
    def test_generate_weekly_briefing(self, sample_kpis):
        cmd = SenseiCommand("ceo_user")
        
        for kpi in sample_kpis:
            cmd.kpi_aggregator.add_kpi(kpi)
        
        briefing = cmd.generate_weekly_briefing()
        
        assert isinstance(briefing, StrategicBriefing)
    
    def test_enable_persona_view(self):
        cmd = SenseiCommand("ceo_user")
        
        overlay = cmd.enable_persona_view(PersonaType.GM)
        
        assert overlay.persona == PersonaType.GM
    
    def test_get_talent_insights(self, sample_employees):
        cmd = SenseiCommand("ceo_user")
        
        for emp in sample_employees:
            cmd.employee_analytics.update_employee_analytics(emp)
        
        insights = cmd.get_talent_insights()
        
        assert "performance_drift_alerts" in insights
        assert "burnout_alerts" in insights
        assert "mentor_candidates" in insights
    
    def test_run_deep_analytics(self):
        cmd = SenseiCommand("ceo_user")
        
        rfq_data = [{"id": 1, "completeness": 0.9}]
        production_data = [{"id": 1, "oee": 0.85}]
        quote_data = [{"id": 1, "margin": 0.22}]
        
        results = cmd.run_deep_analytics(rfq_data, production_data, quote_data)
        
        assert "correlations" in results
        assert "margin_leakages" in results
        assert "bottlenecks" in results


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_kpi_aggregator(self):
        agg = create_kpi_aggregator()
        assert isinstance(agg, ExecutiveKPIAggregator)
    
    def test_create_financial_monitor(self):
        monitor = create_financial_monitor()
        assert isinstance(monitor, FinancialHealthMonitor)
    
    def test_create_risk_generator(self):
        gen = create_risk_generator()
        assert isinstance(gen, RiskHeatmapGenerator)
    
    def test_create_brain_dashboard(self):
        dashboard = create_brain_dashboard()
        assert isinstance(dashboard, BrainHealthDashboard)
    
    def test_create_nl2sql_engine(self):
        engine = create_nl2sql_engine()
        assert engine.security_level == QuerySecurityLevel.READ_ONLY
        
        elevated = create_nl2sql_engine(QuerySecurityLevel.ELEVATED)
        assert elevated.security_level == QuerySecurityLevel.ELEVATED
    
    def test_create_briefing_generator(self):
        gen = create_briefing_generator()
        assert isinstance(gen, StrategicBriefingGenerator)
    
    def test_create_deep_analytics(self):
        analytics = create_deep_analytics()
        assert isinstance(analytics, DeepDatabaseAnalytics)
    
    def test_create_audit_trail(self):
        trail = create_audit_trail()
        assert trail.max_entries == 100000
        
        custom = create_audit_trail(max_entries=5000)
        assert custom.max_entries == 5000
    
    def test_create_ceo_view(self):
        view = create_ceo_view("test_ceo")
        assert view.ceo_user_id == "test_ceo"
    
    def test_create_employee_analytics(self):
        analytics = create_employee_analytics()
        assert analytics.gdpr_compliant is True
        
        non_gdpr = create_employee_analytics(gdpr_compliant=False)
        assert non_gdpr.gdpr_compliant is False
    
    def test_create_sensei_command(self):
        cmd = create_sensei_command("ceo_id")
        assert cmd.ceo_user_id == "ceo_id"


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestDataModels:
    """Test data model instantiation."""
    
    def test_executive_kpi(self):
        kpi = ExecutiveKPI(
            kpi_type=KPIType.MARGIN,
            name="Gross Margin",
            value=0.25,
            target=0.30,
            unit="%",
            trend=2.5,
            period="2024-Q1",
        )
        assert kpi.value == 0.25
    
    def test_financial_health(self):
        health = FinancialHealth(
            quote_to_cash_velocity=35.0,
            pipeline_value=1000000.0,
            high_value_rfqs=10,
            conversion_rate=0.30,
            avg_margin=0.22,
            revenue_forecast=3000000.0,
            period="2024-Q1",
        )
        assert health.pipeline_value == 1000000.0
    
    def test_risk_item(self):
        risk = RiskItem(
            risk_id="r1",
            category=RiskCategory.SUPPLY_CHAIN,
            level=RiskLevel.HIGH,
            title="Supply Risk",
            description="Description",
            impact_score=7.5,
            probability=0.4,
            affected_sites=["site_1"],
            mitigation_status="pending",
            detected_at=datetime.now(),
        )
        assert risk.level == RiskLevel.HIGH
    
    def test_nl2sql_query(self):
        query = NL2SQLQuery(
            query_id="q1",
            natural_language="Show margin",
            generated_sql="SELECT margin FROM quotes",
            explanation="Gets margin data",
            tables_used=["quotes"],
            security_level=QuerySecurityLevel.READ_ONLY,
        )
        assert query.security_level == QuerySecurityLevel.READ_ONLY
    
    def test_employee_analytics(self):
        emp = EmployeeAnalytics(
            employee_id="e1",
            skill_score=0.8,
            cycle_time_trend=-0.05,
            error_rate_trend=-0.02,
            a3_participation=3,
            knowledge_contributions=8,
            engagement_score=0.85,
            risk_flags=[],
        )
        assert emp.skill_score == 0.8


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_kpi_aggregation(self):
        agg = ExecutiveKPIAggregator()
        view = agg.get_aggregate_view()
        assert view == {}
    
    def test_empty_risk_heatmap(self):
        gen = RiskHeatmapGenerator()
        heatmap = gen.generate_heatmap()
        
        assert heatmap.total_critical == 0
        assert len(heatmap.risks) == 0
    
    def test_brain_dashboard_unknown_component(self):
        dashboard = BrainHealthDashboard()
        details = dashboard.get_component_details("nonexistent")
        
        assert details is None
    
    def test_learning_analytics_empty(self):
        analytics = LearningProgressionAnalytics()
        
        summary = analytics.get_summary()
        index = analytics.calculate_intelligence_index()
        
        assert summary == {}
        assert index == 50.0  # Baseline
    
    def test_maintenance_log_trim(self):
        log = MaintenanceAuditLog(max_entries=5)
        
        for i in range(10):
            log.log_action(MaintenanceAuditEntry(
                action_id=f"a{i}",
                action_type="test",
                component="test",
                description="test",
                result="success",
                timestamp=datetime.now(),
                duration_seconds=1.0,
                triggered_by="manual",
            ))
        
        assert len(log.entries) == 5
    
    def test_nl2sql_default_query(self):
        engine = NL2SQLEngine()
        query = engine.generate_sql("Something random that doesn't match")
        
        # Should return default query
        assert "SELECT" in query.generated_sql
        assert "quotes" in query.generated_sql.lower()
    
    def test_cohort_analysis_invalid_date(self):
        analytics = DeepDatabaseAnalytics()
        
        products = [
            {"id": "p1", "launch_date": "invalid-date"},
        ]
        
        cohorts = analytics.analyze_cohort_performance(products)
        
        assert len(cohorts) == 0  # Invalid date skipped
    
    def test_employee_analytics_empty_detection(self):
        analytics = EmployeeIntelligenceAnalytics()
        
        drift_alerts = analytics.detect_performance_drift()
        burnout_alerts = analytics.detect_burnout_risk()
        mentors = analytics.identify_mentors()
        
        assert drift_alerts == []
        assert burnout_alerts == []
        assert mentors == []
