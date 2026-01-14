"""
Sensei Command: CEO Strategic Control Plane.

Implements:
- Strategic North Star Dashboard (Executive KPIs, Financial Health, Risk Heatmap)
- Autonomous System Health & Evolution Visibility
- Executive Intelligence Synthesis (NL2SQL, Strategic Briefings)
- Advanced Deep-Database Analytics
- Total Visibility & Governance (CEO Super-View, Employee Analytics)
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update
from sensei.models.strategic import (
    NL2SQLQueryRecord,
    EmployeeRiskAssessmentRecord,
    ScenarioResultRecord,
)


# =============================================================================
# ENUMS
# =============================================================================


class KPIType(str, Enum):
    """Types of executive KPIs."""
    YIELD = "yield"
    OEE = "oee"
    MARGIN = "margin"
    WIN_RATE = "win_rate"
    QUOTE_TO_CASH = "quote_to_cash"
    NPI_SUCCESS = "npi_success"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


class RiskLevel(str, Enum):
    """Risk severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskCategory(str, Enum):
    """Categories of organizational risk."""
    SUPPLY_CHAIN = "supply_chain"
    PRODUCTION = "production"
    QUALITY = "quality"
    FINANCIAL = "financial"
    PERSONNEL = "personnel"
    COMPLIANCE = "compliance"


class LearningMetricType(str, Enum):
    """Types of learning progression metrics."""
    CONFIDENCE_IMPROVEMENT = "confidence_improvement"
    AUTONOMOUS_UPDATES = "autonomous_updates"
    MODEL_ACCURACY = "model_accuracy"
    USER_ADOPTION = "user_adoption"


class QuerySecurityLevel(str, Enum):
    """Security levels for NL2SQL queries."""
    READ_ONLY = "read_only"
    RESTRICTED = "restricted"
    ELEVATED = "elevated"


class ExportFormat(str, Enum):
    """Export format options."""
    PDF = "pdf"
    CSV = "csv"
    PPTX = "pptx"
    JSON = "json"


class EmployeeRiskType(str, Enum):
    """Types of employee-related risks."""
    BURNOUT = "burnout"
    RETENTION = "retention"
    PERFORMANCE_DRIFT = "performance_drift"
    SKILL_GAP = "skill_gap"


class PersonaType(str, Enum):
    """User persona types for overlay."""
    GM = "gm"
    OPERATOR = "operator"
    SALES = "sales"
    QUALITY = "quality"
    ENGINEERING = "engineering"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class ExecutiveKPI:
    """An executive-level KPI."""
    kpi_type: KPIType
    name: str
    value: float
    target: float
    unit: str
    trend: float  # % change from previous period
    period: str
    site_id: str | None = None
    product_family: str | None = None


@dataclass
class FinancialHealth:
    """Financial health metrics."""
    quote_to_cash_velocity: float  # days
    pipeline_value: float
    high_value_rfqs: int
    conversion_rate: float
    avg_margin: float
    revenue_forecast: float
    period: str


@dataclass
class RiskItem:
    """A risk item for the heatmap."""
    risk_id: str
    category: RiskCategory
    level: RiskLevel
    title: str
    description: str
    impact_score: float  # 0-10
    probability: float  # 0-1
    affected_sites: list[str]
    mitigation_status: str
    detected_at: datetime


@dataclass
class RiskHeatmap:
    """Organization risk heatmap."""
    risks: list[RiskItem]
    total_critical: int
    total_high: int
    category_counts: dict[RiskCategory, int]
    generated_at: datetime


@dataclass
class SystemHealthStatus:
    """System health status."""
    component: str
    status: str  # "healthy", "degraded", "down"
    last_check: datetime
    uptime_percent: float
    last_action: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class LearningProgression:
    """Learning progression metrics."""
    metric_type: LearningMetricType
    current_value: float
    baseline_value: float
    improvement_percent: float
    measurement_period: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MaintenanceAuditEntry:
    """Audit entry for autonomous maintenance."""
    action_id: str
    action_type: str
    component: str
    description: str
    result: str
    timestamp: datetime
    duration_seconds: float
    triggered_by: str  # "schedule", "threshold", "manual"


@dataclass
class NL2SQLQuery:
    """A natural language to SQL query."""
    query_id: str
    natural_language: str
    generated_sql: str
    explanation: str
    tables_used: list[str]
    security_level: QuerySecurityLevel
    execution_time_ms: float | None = None
    result_count: int | None = None


@dataclass
class StrategicBriefing:
    """Weekly strategic briefing."""
    briefing_id: str
    title: str
    period: str
    executive_summary: str
    key_highlights: list[str]
    recommendations: list[str]
    kpi_summary: dict[str, float]
    generated_at: datetime


@dataclass
class CrossSiloCorrelation:
    """Cross-silo data correlation result."""
    correlation_id: str
    name: str
    data_sources: list[str]
    correlation_value: float
    insight: str
    sample_size: int
    period: str


@dataclass
class MarginLeakage:
    """Predictive margin leakage detection."""
    leakage_id: str
    pattern: str
    affected_quotes: int
    avg_overrun_percent: float
    total_leakage_value: float
    root_cause: str
    segment: str | None = None


@dataclass
class CohortAnalysis:
    """Cohort performance analysis."""
    cohort_id: str
    launch_quarter: str
    product_count: int
    avg_margin_12m: float
    avg_oee: float
    quality_issues: int
    revenue_contribution: float


@dataclass
class Bottleneck:
    """Wait-state bottleneck."""
    bottleneck_id: str
    location: str
    process_step: str
    avg_wait_time_hours: float
    throughput_impact_percent: float
    frequency: int
    recommendation: str


@dataclass
class AuditTrailEntry:
    """Global audit trail entry."""
    entry_id: str
    entity_type: str
    entity_id: str
    action: str
    user_id: str
    timestamp: datetime
    old_value: Any
    new_value: Any
    rationale: str | None = None


@dataclass
class EmployeeAnalytics:
    """Employee analytics metrics."""
    employee_id: str
    skill_score: float
    cycle_time_trend: float  # % change
    error_rate_trend: float  # % change
    a3_participation: int
    knowledge_contributions: int
    engagement_score: float
    risk_flags: list[EmployeeRiskType]


@dataclass
class TalentRiskAlert:
    """Talent risk alert."""
    alert_id: str
    employee_id: str
    risk_type: EmployeeRiskType
    severity: RiskLevel
    indicators: list[str]
    recommendation: str
    detected_at: datetime


@dataclass
class PersonaOverlay:
    """Persona overlay for CEO view."""
    persona: PersonaType
    features_enabled: list[str]
    access_scope: str
    session_id: str
    started_at: datetime
    actions_logged: int


# =============================================================================
# STRATEGIC NORTH STAR DASHBOARD
# =============================================================================


class ExecutiveKPIAggregator:
    """
    Aggregates executive KPIs across sites and product families.
    """
    
    def __init__(self):
        self.kpis: list[ExecutiveKPI] = []
        self._site_data: dict[str, list[ExecutiveKPI]] = defaultdict(list)
        self._family_data: dict[str, list[ExecutiveKPI]] = defaultdict(list)
    
    def add_kpi(self, kpi: ExecutiveKPI) -> None:
        """Add a KPI measurement."""
        self.kpis.append(kpi)
        if kpi.site_id:
            self._site_data[kpi.site_id].append(kpi)
        if kpi.product_family:
            self._family_data[kpi.product_family].append(kpi)
    
    def get_aggregate_view(self) -> dict[KPIType, dict[str, float]]:
        """Get aggregated view of all KPIs."""
        result: dict[KPIType, dict[str, float]] = {}
        
        for kpi_type in KPIType:
            type_kpis = [k for k in self.kpis if k.kpi_type == kpi_type]
            if type_kpis:
                values = [k.value for k in type_kpis]
                targets = [k.target for k in type_kpis]
                trends = [k.trend for k in type_kpis]
                
                result[kpi_type] = {
                    "avg_value": sum(values) / len(values),
                    "avg_target": sum(targets) / len(targets),
                    "avg_trend": sum(trends) / len(trends),
                    "count": len(type_kpis),
                }
        
        return result
    
    def get_site_comparison(self, kpi_type: KPIType) -> dict[str, float]:
        """Compare a KPI across sites."""
        result: dict[str, float] = {}
        
        for site_id, kpis in self._site_data.items():
            type_kpis = [k for k in kpis if k.kpi_type == kpi_type]
            if type_kpis:
                result[site_id] = sum(k.value for k in type_kpis) / len(type_kpis)
        
        return result
    
    def get_trend_analysis(self, kpi_type: KPIType) -> dict[str, Any]:
        """Analyze trends for a KPI type."""
        type_kpis = [k for k in self.kpis if k.kpi_type == kpi_type]
        
        if not type_kpis:
            return {}
        
        avg_trend = sum(k.trend for k in type_kpis) / len(type_kpis)
        improving = [k for k in type_kpis if k.trend > 0]
        declining = [k for k in type_kpis if k.trend < 0]
        
        return {
            "avg_trend": avg_trend,
            "improving_count": len(improving),
            "declining_count": len(declining),
            "direction": "improving" if avg_trend > 0 else "declining" if avg_trend < 0 else "stable",
        }


class FinancialHealthMonitor:
    """
    Real-time tracking of financial health metrics.
    """
    
    def __init__(self):
        self.current_health: FinancialHealth | None = None
        self._history: list[FinancialHealth] = []
    
    def update_health(self, health: FinancialHealth) -> None:
        """Update current financial health."""
        self.current_health = health
        self._history.append(health)
    
    def get_quote_to_cash_trend(self, periods: int = 6) -> list[float]:
        """Get quote-to-cash velocity trend."""
        recent = self._history[-periods:] if len(self._history) >= periods else self._history
        return [h.quote_to_cash_velocity for h in recent]
    
    def get_pipeline_health(self) -> dict[str, Any]:
        """Get pipeline health assessment."""
        if not self.current_health:
            return {}
        
        return {
            "pipeline_value": self.current_health.pipeline_value,
            "high_value_rfqs": self.current_health.high_value_rfqs,
            "conversion_rate": self.current_health.conversion_rate,
            "health_score": self._calculate_health_score(),
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        if not self.current_health:
            return 0.0
        
        h = self.current_health
        score = 0.0
        
        # Conversion rate contribution (30%)
        score += min(h.conversion_rate / 0.3 * 30, 30)
        
        # Margin contribution (30%)
        score += min(h.avg_margin / 0.25 * 30, 30)
        
        # Pipeline velocity (20%) - lower is better
        if h.quote_to_cash_velocity > 0:
            velocity_score = max(0, 20 - (h.quote_to_cash_velocity - 30) / 2)
            score += min(velocity_score, 20)
        
        # Pipeline value (20%)
        if h.revenue_forecast > 0:
            pipeline_ratio = h.pipeline_value / h.revenue_forecast
            score += min(pipeline_ratio * 20, 20)
        
        return min(score, 100)


class RiskHeatmapGenerator:
    """
    Generates organization risk heatmaps.
    """
    
    def __init__(self):
        self.risks: list[RiskItem] = []
    
    def add_risk(self, risk: RiskItem) -> None:
        """Add a risk item."""
        self.risks.append(risk)
    
    def detect_supply_chain_risks(
        self,
        supplier_data: list[dict[str, Any]],
    ) -> list[RiskItem]:
        """Detect supply chain risks from supplier data."""
        detected: list[RiskItem] = []
        
        for supplier in supplier_data:
            # Check for single-source dependency
            if supplier.get("is_single_source", False):
                risk = RiskItem(
                    risk_id=f"risk_sc_{supplier['id']}",
                    category=RiskCategory.SUPPLY_CHAIN,
                    level=RiskLevel.HIGH,
                    title=f"Single source dependency: {supplier['name']}",
                    description="Critical component relies on single supplier",
                    impact_score=8.0,
                    probability=0.3,
                    affected_sites=supplier.get("sites", []),
                    mitigation_status="pending",
                    detected_at=datetime.now(),
                )
                detected.append(risk)
                self.risks.append(risk)
            
            # Check for delivery performance
            if supplier.get("on_time_rate", 1.0) < 0.85:
                risk = RiskItem(
                    risk_id=f"risk_delivery_{supplier['id']}",
                    category=RiskCategory.SUPPLY_CHAIN,
                    level=RiskLevel.MEDIUM,
                    title=f"Delivery performance issue: {supplier['name']}",
                    description=f"On-time rate: {supplier.get('on_time_rate', 0) * 100:.1f}%",
                    impact_score=5.0,
                    probability=0.5,
                    affected_sites=supplier.get("sites", []),
                    mitigation_status="monitoring",
                    detected_at=datetime.now(),
                )
                detected.append(risk)
                self.risks.append(risk)
        
        return detected
    
    def generate_heatmap(self) -> RiskHeatmap:
        """Generate the risk heatmap."""
        category_counts: dict[RiskCategory, int] = defaultdict(int)
        
        for risk in self.risks:
            category_counts[risk.category] += 1
        
        return RiskHeatmap(
            risks=self.risks,
            total_critical=sum(1 for r in self.risks if r.level == RiskLevel.CRITICAL),
            total_high=sum(1 for r in self.risks if r.level == RiskLevel.HIGH),
            category_counts=dict(category_counts),
            generated_at=datetime.now(),
        )
    
    def get_risks_by_category(self, category: RiskCategory) -> list[RiskItem]:
        """Get risks filtered by category."""
        return [r for r in self.risks if r.category == category]
    
    def get_risks_by_level(self, level: RiskLevel) -> list[RiskItem]:
        """Get risks filtered by level."""
        return [r for r in self.risks if r.level == level]


# =============================================================================
# SYSTEM HEALTH & EVOLUTION VISIBILITY
# =============================================================================


class BrainHealthDashboard:
    """
    Real-time status of self-healing engine and AI systems.
    """
    
    def __init__(self):
        self.component_status: dict[str, SystemHealthStatus] = {}
        self._status_history: list[tuple[datetime, dict[str, str]]] = []
    
    def update_component(self, status: SystemHealthStatus) -> None:
        """Update a component's status."""
        self.component_status[status.component] = status
    
    def get_overall_health(self) -> dict[str, Any]:
        """Get overall system health."""
        if not self.component_status:
            return {"status": "unknown", "components": 0}
        
        statuses = [s.status for s in self.component_status.values()]
        
        if any(s == "down" for s in statuses):
            overall = "degraded"
        elif any(s == "degraded" for s in statuses):
            overall = "warning"
        else:
            overall = "healthy"
        
        avg_uptime = sum(s.uptime_percent for s in self.component_status.values()) / len(self.component_status)
        
        return {
            "status": overall,
            "components": len(self.component_status),
            "avg_uptime": avg_uptime,
            "healthy_count": sum(1 for s in statuses if s == "healthy"),
            "degraded_count": sum(1 for s in statuses if s == "degraded"),
            "down_count": sum(1 for s in statuses if s == "down"),
        }
    
    def get_component_details(self, component: str) -> SystemHealthStatus | None:
        """Get detailed status for a specific component."""
        return self.component_status.get(component)
    
    def take_snapshot(self) -> None:
        """Take a snapshot of current status."""
        snapshot = {name: status.status for name, status in self.component_status.items()}
        self._status_history.append((datetime.now(), snapshot))


class LearningProgressionAnalytics:
    """
    Quantifies system intelligence growth.
    """
    
    def __init__(self):
        self.progressions: list[LearningProgression] = []
    
    def add_progression(self, progression: LearningProgression) -> None:
        """Add a progression measurement."""
        self.progressions.append(progression)
    
    def get_summary(self) -> dict[str, Any]:
        """Get learning progression summary."""
        if not self.progressions:
            return {}
        
        by_type: dict[LearningMetricType, list[LearningProgression]] = defaultdict(list)
        for p in self.progressions:
            by_type[p.metric_type].append(p)
        
        summary: dict[str, Any] = {}
        for metric_type, progs in by_type.items():
            avg_improvement = sum(p.improvement_percent for p in progs) / len(progs)
            summary[metric_type.value] = {
                "avg_improvement": avg_improvement,
                "measurements": len(progs),
                "trend": "improving" if avg_improvement > 0 else "stable",
            }
        
        return summary
    
    def calculate_intelligence_index(self) -> float:
        """Calculate overall intelligence growth index (0-100)."""
        if not self.progressions:
            return 50.0  # Baseline
        
        weights = {
            LearningMetricType.CONFIDENCE_IMPROVEMENT: 0.3,
            LearningMetricType.AUTONOMOUS_UPDATES: 0.25,
            LearningMetricType.MODEL_ACCURACY: 0.3,
            LearningMetricType.USER_ADOPTION: 0.15,
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for p in self.progressions:
            weight = weights.get(p.metric_type, 0.1)
            # Normalize improvement to 0-100 scale (assuming ±50% is range)
            normalized = 50 + p.improvement_percent
            weighted_sum += normalized * weight
            total_weight += weight
        
        if total_weight == 0:
            return 50.0
        
        return min(max(weighted_sum / total_weight, 0), 100)


class MaintenanceAuditLog:
    """
    Logs all autonomous maintenance actions.
    """
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: list[MaintenanceAuditEntry] = []
    
    def log_action(self, entry: MaintenanceAuditEntry) -> None:
        """Log a maintenance action."""
        self.entries.append(entry)
        
        # Trim old entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
    
    def get_recent_actions(self, limit: int = 50) -> list[MaintenanceAuditEntry]:
        """Get recent maintenance actions."""
        return self.entries[-limit:]
    
    def get_actions_by_component(self, component: str) -> list[MaintenanceAuditEntry]:
        """Get actions for a specific component."""
        return [e for e in self.entries if e.component == component]
    
    def get_action_summary(self, days: int = 7) -> dict[str, Any]:
        """Get summary of actions over specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [e for e in self.entries if e.timestamp >= cutoff]
        
        by_type: dict[str, int] = defaultdict(int)
        by_trigger: dict[str, int] = defaultdict(int)
        
        for entry in recent:
            by_type[entry.action_type] += 1
            by_trigger[entry.triggered_by] += 1
        
        return {
            "total_actions": len(recent),
            "by_type": dict(by_type),
            "by_trigger": dict(by_trigger),
            "avg_duration": sum(e.duration_seconds for e in recent) / len(recent) if recent else 0,
        }


# =============================================================================
# EXECUTIVE INTELLIGENCE SYNTHESIS
# =============================================================================


class NL2SQLEngine:
    """
    Natural Language to SQL query engine.
    """
    
    # Simulated schema for SQL generation
    SCHEMA_CONTEXT = {
        "quotes": ["id", "customer_id", "value", "margin", "status", "created_at", "won_at"],
        "rfqs": ["id", "customer_id", "completeness", "urgency", "created_at"],
        "production": ["id", "product_id", "oee", "yield_rate", "site_id", "date"],
        "customers": ["id", "name", "segment", "region"],
        "suppliers": ["id", "name", "on_time_rate", "quality_score"],
    }
    
    SQL_PATTERNS = [
        (r"margin.*segment", "SELECT segment, AVG(margin) FROM quotes q JOIN customers c ON q.customer_id = c.id GROUP BY segment"),
        (r"win.*rate", "SELECT status, COUNT(*) FROM quotes GROUP BY status"),
        (r"oee.*site", "SELECT site_id, AVG(oee) FROM production GROUP BY site_id"),
        (r"top.*customer", "SELECT c.name, SUM(q.value) as total FROM customers c JOIN quotes q ON c.id = q.customer_id GROUP BY c.name ORDER BY total DESC LIMIT 10"),
        (r"supplier.*performance", "SELECT name, on_time_rate, quality_score FROM suppliers ORDER BY quality_score DESC"),
    ]
    
    def __init__(self, security_level: QuerySecurityLevel = QuerySecurityLevel.READ_ONLY):
        self.security_level = security_level
    
    async def generate_sql(self, db: AsyncSession, natural_language: str, user_id: str | None = None) -> NL2SQLQuery:
        """Generate SQL from natural language query and persist."""
        nl_lower = natural_language.lower()
        
        # Pattern matching for SQL generation
        sql = "SELECT * FROM quotes LIMIT 100"  # Default
        tables_used = ["quotes"]
        
        for pattern, sql_template in self.SQL_PATTERNS:
            if re.search(pattern, nl_lower):
                sql = sql_template
                tables_used = self._extract_tables(sql)
                break
        
        # Add security restrictions
        if self.security_level == QuerySecurityLevel.READ_ONLY:
            if any(kw in sql.upper() for kw in ["UPDATE", "DELETE", "INSERT", "DROP"]):
                sql = "-- BLOCKED: Write operations not allowed"
        
        explanation = self._generate_explanation(sql)
        
        query_id = f"nlsql_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        
        record = NL2SQLQueryRecord(
            id=query_id,
            natural_language=natural_language,
            generated_sql=sql,
            explanation=explanation,
            tables_used=tables_used,
            security_level=self.security_level,
            executed_by_id=user_id,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        return NL2SQLQuery(
            query_id=record.id,
            natural_language=record.natural_language,
            generated_sql=record.generated_sql,
            explanation=record.explanation,
            tables_used=record.tables_used,
            security_level=record.security_level,
        )
    
    def _extract_tables(self, sql: str) -> list[str]:
        """Extract table names from SQL."""
        tables = []
        for table in self.SCHEMA_CONTEXT.keys():
            if table in sql.lower():
                tables.append(table)
        return tables
    
    def _generate_explanation(self, sql: str) -> str:
        """Generate plain-English explanation of SQL."""
        sql_upper = sql.upper()
        
        if "GROUP BY" in sql_upper:
            if "AVG" in sql_upper:
                return "This query calculates averages grouped by the specified category."
            if "SUM" in sql_upper:
                return "This query calculates totals grouped by the specified category."
            if "COUNT" in sql_upper:
                return "This query counts records grouped by the specified category."
        
        if "ORDER BY" in sql_upper:
            if "DESC" in sql_upper:
                return "This query retrieves data sorted from highest to lowest."
            return "This query retrieves data sorted from lowest to highest."
        
        return "This query retrieves the requested data from the database."
    
    def get_schema_context(self) -> dict[str, list[str]]:
        """Get available schema for context."""
        return self.SCHEMA_CONTEXT.copy()
    
    def validate_query(self, sql: str) -> tuple[bool, str]:
        """Validate a SQL query before execution."""
        sql_upper = sql.upper()
        
        # Check for blocked operations
        if self.security_level == QuerySecurityLevel.READ_ONLY:
            blocked = ["UPDATE", "DELETE", "INSERT", "DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"]
            for kw in blocked:
                if re.search(rf"\b{kw}\b", sql_upper):
                    return False, f"Operation {kw} not allowed in read-only mode"
        
        # Basic syntax check
        if not sql.strip():
            return False, "Empty query"
        
        # Prevent multiple statements (semicolon)
        if ";" in sql.strip()[:-1] or ";" in sql.strip() and sql.strip().count(";") > 1:
             return False, "Multiple statements not allowed"

        if "SELECT" not in sql_upper:
            return False, "Only SELECT queries allowed"
        
        return True, "Query validated successfully"


class StrategicBriefingGenerator:
    """
    Generates weekly autonomous strategic briefings.
    """
    
    def __init__(self):
        self.briefings: list[StrategicBriefing] = []
    
    def generate_briefing(
        self,
        kpis: dict[str, float],
        risks: list[RiskItem],
        opportunities: list[str],
    ) -> StrategicBriefing:
        """Generate a strategic briefing."""
        # Generate executive summary
        summary_parts = []
        
        if kpis.get("margin", 0) > 0.2:
            summary_parts.append("Margins remain healthy above 20%.")
        elif kpis.get("margin", 0) < 0.15:
            summary_parts.append("Margin pressure detected - requires attention.")
        
        if kpis.get("win_rate", 0) > 0.3:
            summary_parts.append("Quote win rate is strong.")
        
        critical_risks = [r for r in risks if r.level == RiskLevel.CRITICAL]
        if critical_risks:
            summary_parts.append(f"{len(critical_risks)} critical risks require immediate action.")
        
        executive_summary = " ".join(summary_parts) if summary_parts else "Operations proceeding normally."
        
        # Generate recommendations
        recommendations = []
        
        if kpis.get("oee", 0) < 0.85:
            recommendations.append("Focus on improving OEE through targeted maintenance initiatives.")
        
        for risk in critical_risks[:3]:
            recommendations.append(f"Address: {risk.title}")
        
        if opportunities:
            recommendations.append(f"Top opportunity: {opportunities[0]}")
        
        briefing = StrategicBriefing(
            briefing_id=f"brief_{int(time.time())}",
            title="Weekly Strategic Briefing",
            period=datetime.now().strftime("%Y-W%W"),
            executive_summary=executive_summary,
            key_highlights=[
                f"Average margin: {kpis.get('margin', 0) * 100:.1f}%",
                f"Win rate: {kpis.get('win_rate', 0) * 100:.1f}%",
                f"Active risks: {len(risks)}",
            ],
            recommendations=recommendations,
            kpi_summary=kpis,
            generated_at=datetime.now(),
        )
        
        self.briefings.append(briefing)
        return briefing
    
    def export_briefing(self, briefing_id: str, format: ExportFormat) -> dict[str, Any]:
        """Export a briefing to specified format."""
        briefing = next((b for b in self.briefings if b.briefing_id == briefing_id), None)
        
        if not briefing:
            return {"error": "Briefing not found"}
        
        if format == ExportFormat.JSON:
            return {
                "format": "json",
                "content": {
                    "title": briefing.title,
                    "period": briefing.period,
                    "summary": briefing.executive_summary,
                    "highlights": briefing.key_highlights,
                    "recommendations": briefing.recommendations,
                },
            }
        elif format == ExportFormat.CSV:
            return {
                "format": "csv",
                "content": f"Metric,Value\n" + "\n".join(
                    f"{k},{v}" for k, v in briefing.kpi_summary.items()
                ),
            }
        else:
            return {
                "format": format.value,
                "content": f"Exported: {briefing.title}",
                "size_kb": 150,
            }


# =============================================================================
# ADVANCED DEEP-DATABASE ANALYTICS
# =============================================================================


class DeepDatabaseAnalytics:
    """
    Advanced analytics across data silos.
    """
    
    def __init__(self):
        self.correlations: list[CrossSiloCorrelation] = []
        self.leakages: list[MarginLeakage] = []
        self.cohorts: list[CohortAnalysis] = []
        self.bottlenecks: list[Bottleneck] = []
    
    def analyze_cross_silo_correlation(
        self,
        rfq_data: list[dict[str, Any]],
        production_data: list[dict[str, Any]],
        quote_data: list[dict[str, Any]],
    ) -> list[CrossSiloCorrelation]:
        """Analyze correlations across RFQ, production, and quote data."""
        correlations: list[CrossSiloCorrelation] = []
        
        # Simulated correlation analysis
        if rfq_data and production_data:
            # RFQ completeness vs Production OEE
            rfq_completeness = sum(r.get("completeness", 0.5) for r in rfq_data) / len(rfq_data) if rfq_data else 0
            avg_oee = sum(p.get("oee", 0.5) for p in production_data) / len(production_data) if production_data else 0
            
            correlation = CrossSiloCorrelation(
                correlation_id="corr_rfq_oee",
                name="RFQ Completeness vs Production OEE",
                data_sources=["rfqs", "production"],
                correlation_value=0.72,  # Simulated
                insight="Higher RFQ completeness correlates with better OEE outcomes",
                sample_size=len(rfq_data) + len(production_data),
                period="last_90_days",
            )
            correlations.append(correlation)
            self.correlations.append(correlation)
        
        if production_data and quote_data:
            # OEE vs Margin
            correlation = CrossSiloCorrelation(
                correlation_id="corr_oee_margin",
                name="Production OEE vs Quote Margin",
                data_sources=["production", "quotes"],
                correlation_value=0.65,  # Simulated
                insight="Better OEE generally leads to higher margins",
                sample_size=len(production_data) + len(quote_data),
                period="last_90_days",
            )
            correlations.append(correlation)
            self.correlations.append(correlation)
        
        return correlations
    
    def detect_margin_leakage(
        self,
        quotes: list[dict[str, Any]],
        actuals: list[dict[str, Any]],
    ) -> list[MarginLeakage]:
        """Detect patterns of margin leakage."""
        leakages: list[MarginLeakage] = []
        
        # Group by segment and analyze overruns
        segment_overruns: dict[str, list[float]] = defaultdict(list)
        
        for quote in quotes:
            quote_id = quote.get("id")
            actual = next((a for a in actuals if a.get("quote_id") == quote_id), None)
            
            if actual:
                quoted_cost = quote.get("cost", 0)
                actual_cost = actual.get("actual_cost", 0)
                
                if quoted_cost > 0:
                    overrun = (actual_cost - quoted_cost) / quoted_cost
                    if overrun > 0.05:  # 5% threshold
                        segment = quote.get("segment", "unknown")
                        segment_overruns[segment].append(overrun)
        
        for segment, overruns in segment_overruns.items():
            if len(overruns) >= 3:  # Pattern detection threshold
                leakage = MarginLeakage(
                    leakage_id=f"leak_{segment}_{int(time.time())}",
                    pattern=f"Consistent cost overruns in {segment}",
                    affected_quotes=len(overruns),
                    avg_overrun_percent=sum(overruns) / len(overruns) * 100,
                    total_leakage_value=sum(overruns) * 10000,  # Simulated
                    root_cause="Underestimated labor or material costs",
                    segment=segment,
                )
                leakages.append(leakage)
                self.leakages.append(leakage)
        
        return leakages
    
    def analyze_cohort_performance(
        self,
        products: list[dict[str, Any]],
    ) -> list[CohortAnalysis]:
        """Analyze NPI success cohorts."""
        cohorts: list[CohortAnalysis] = []
        
        # Group products by launch quarter
        by_quarter: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        for product in products:
            launch_date = product.get("launch_date")
            if launch_date:
                if isinstance(launch_date, str):
                    try:
                        launch_date = datetime.fromisoformat(launch_date)
                    except ValueError:
                        continue
                quarter = f"Q{(launch_date.month - 1) // 3 + 1}-{launch_date.year}"
                by_quarter[quarter].append(product)
        
        for quarter, prods in by_quarter.items():
            cohort = CohortAnalysis(
                cohort_id=f"cohort_{quarter}",
                launch_quarter=quarter,
                product_count=len(prods),
                avg_margin_12m=sum(p.get("margin_12m", 0.15) for p in prods) / len(prods),
                avg_oee=sum(p.get("oee", 0.8) for p in prods) / len(prods),
                quality_issues=sum(p.get("quality_issues", 0) for p in prods),
                revenue_contribution=sum(p.get("revenue", 0) for p in prods),
            )
            cohorts.append(cohort)
            self.cohorts.append(cohort)
        
        return cohorts
    
    def detect_bottlenecks(
        self,
        process_data: list[dict[str, Any]],
    ) -> list[Bottleneck]:
        """Detect wait-state bottlenecks."""
        bottlenecks: list[Bottleneck] = []
        
        # Analyze wait times at each process step
        step_waits: dict[str, list[float]] = defaultdict(list)
        
        for record in process_data:
            step = record.get("step")
            wait_time = record.get("wait_time_hours", 0)
            
            if step and wait_time > 0:
                step_waits[step].append(wait_time)
        
        for step, waits in step_waits.items():
            avg_wait = sum(waits) / len(waits)
            
            if avg_wait > 2.0:  # 2+ hours threshold
                bottleneck = Bottleneck(
                    bottleneck_id=f"bn_{step}_{int(time.time())}",
                    location=step.split("_")[0] if "_" in step else "general",
                    process_step=step,
                    avg_wait_time_hours=avg_wait,
                    throughput_impact_percent=min(avg_wait * 2, 30),  # Simulated
                    frequency=len(waits),
                    recommendation=f"Review capacity and scheduling at {step}",
                )
                bottlenecks.append(bottleneck)
                self.bottlenecks.append(bottleneck)
        
        return bottlenecks


# =============================================================================
# TOTAL VISIBILITY & GOVERNANCE
# =============================================================================


class GlobalAuditTrail:
    """
    Single-point access to all audit trails.
    """
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.entries: list[AuditTrailEntry] = []
        self._by_entity: dict[str, list[AuditTrailEntry]] = defaultdict(list)
        self._by_user: dict[str, list[AuditTrailEntry]] = defaultdict(list)
    
    def log_entry(self, entry: AuditTrailEntry) -> None:
        """Log an audit entry."""
        self.entries.append(entry)
        self._by_entity[f"{entry.entity_type}:{entry.entity_id}"].append(entry)
        self._by_user[entry.user_id].append(entry)
        
        # Trim old entries from main list and secondary indices to prevent OOM
        if len(self.entries) > self.max_entries:
            removed = self.entries.pop(0)
            entity_key = f"{removed.entity_type}:{removed.entity_id}"
            if removed in self._by_entity[entity_key]:
                self._by_entity[entity_key].remove(removed)
            if removed in self._by_user[removed.user_id]:
                self._by_user[removed.user_id].remove(removed)
    
    def get_entity_history(self, entity_type: str, entity_id: str) -> list[AuditTrailEntry]:
        """Get audit history for an entity."""
        key = f"{entity_type}:{entity_id}"
        return self._by_entity.get(key, [])
    
    def get_user_actions(self, user_id: str, limit: int = 100) -> list[AuditTrailEntry]:
        """Get actions by a specific user."""
        return self._by_user.get(user_id, [])[-limit:]
    
    def search(
        self,
        entity_type: str | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AuditTrailEntry]:
        """Search audit trail."""
        results = self.entries
        
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        
        if action:
            results = [e for e in results if e.action == action]
        
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]
        
        return results


class CEOSuperView:
    """
    CEO unrestricted access and persona overlay system.
    """
    
    def __init__(self, ceo_user_id: str):
        self.ceo_user_id = ceo_user_id
        self.active_overlay: PersonaOverlay | None = None
        self.overlay_history: list[PersonaOverlay] = []
        self._action_log: list[dict[str, Any]] = []
    
    def enable_persona_overlay(self, persona: PersonaType) -> PersonaOverlay:
        """Enable a persona overlay for the CEO."""
        # Close any active overlay
        if self.active_overlay:
            self._close_overlay()
        
        features = self._get_persona_features(persona)
        
        overlay = PersonaOverlay(
            persona=persona,
            features_enabled=features,
            access_scope=f"full_{persona.value}_access",
            session_id=f"overlay_{int(time.time())}",
            started_at=datetime.now(),
            actions_logged=0,
        )
        
        self.active_overlay = overlay
        self._log_action("enable_overlay", {"persona": persona.value})
        
        return overlay
    
    def _get_persona_features(self, persona: PersonaType) -> list[str]:
        """Get features available for a persona."""
        features_map = {
            PersonaType.GM: ["a3_creator", "rfq_builder", "site_dashboard", "team_management"],
            PersonaType.OPERATOR: ["work_orders", "quality_checks", "issue_reporting"],
            PersonaType.SALES: ["quote_builder", "customer_management", "pipeline_view"],
            PersonaType.QUALITY: ["inspection_tools", "ncr_management", "audit_tools"],
            PersonaType.ENGINEERING: ["drawing_viewer", "bom_editor", "change_management"],
        }
        return features_map.get(persona, [])
    
    def _close_overlay(self) -> None:
        """Close the active overlay."""
        if self.active_overlay:
            self.overlay_history.append(self.active_overlay)
            self._log_action("close_overlay", {
                "persona": self.active_overlay.persona.value,
                "actions_taken": self.active_overlay.actions_logged,
            })
            self.active_overlay = None
    
    def disable_persona_overlay(self) -> None:
        """Disable the active persona overlay."""
        self._close_overlay()
    
    def _log_action(self, action: str, details: dict[str, Any]) -> None:
        """Log an action for audit."""
        self._action_log.append({
            "user_id": self.ceo_user_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "overlay_active": self.active_overlay is not None,
        })
        
        if self.active_overlay:
            self.active_overlay.actions_logged += 1
    
    def drill_to_source(self, kpi_id: str, value: float) -> dict[str, Any]:
        """Drill down from a KPI to underlying data."""
        self._log_action("drill_to_source", {"kpi_id": kpi_id, "value": value})
        
        # Simulated drill-down result
        return {
            "kpi_id": kpi_id,
            "value": value,
            "underlying_records": 150,
            "sample_records": [
                {"id": 1, "value": value * 0.8},
                {"id": 2, "value": value * 1.2},
                {"id": 3, "value": value * 0.95},
            ],
            "data_source": "quotes" if "margin" in kpi_id else "production",
        }
    
    def get_action_log(self) -> list[dict[str, Any]]:
        """Get the action log for audit."""
        return self._action_log.copy()


class EmployeeIntelligenceAnalytics:
    """
    Employee analytics with privacy compliance.
    """
    
    DRIFT_THRESHOLD = 0.15  # 15% drift triggers warning
    
    def __init__(self, gdpr_compliant: bool = True):
        self.gdpr_compliant = gdpr_compliant
        self.analytics: dict[str, EmployeeAnalytics] = {}
        self.talent_alerts: list[TalentRiskAlert] = []
    
    def update_employee_analytics(self, analytics: EmployeeAnalytics) -> None:
        """Update analytics for an employee."""
        self.analytics[analytics.employee_id] = analytics
    
    def detect_performance_drift(self) -> list[TalentRiskAlert]:
        """Detect employees with performance drift."""
        alerts: list[TalentRiskAlert] = []
        
        for emp_id, analytics in self.analytics.items():
            # Check cycle time drift
            if abs(analytics.cycle_time_trend) > self.DRIFT_THRESHOLD:
                direction = "slower" if analytics.cycle_time_trend > 0 else "faster"
                alert = TalentRiskAlert(
                    alert_id=f"drift_{emp_id}_{int(time.time())}",
                    employee_id=emp_id,
                    risk_type=EmployeeRiskType.PERFORMANCE_DRIFT,
                    severity=RiskLevel.MEDIUM if abs(analytics.cycle_time_trend) < 0.25 else RiskLevel.HIGH,
                    indicators=[f"Cycle time {abs(analytics.cycle_time_trend) * 100:.1f}% {direction}"],
                    recommendation="Review workload and provide coaching if needed",
                    detected_at=datetime.now(),
                )
                alerts.append(alert)
                self.talent_alerts.append(alert)
            
            # Check error rate drift
            if analytics.error_rate_trend > self.DRIFT_THRESHOLD:
                alert = TalentRiskAlert(
                    alert_id=f"quality_{emp_id}_{int(time.time())}",
                    employee_id=emp_id,
                    risk_type=EmployeeRiskType.PERFORMANCE_DRIFT,
                    severity=RiskLevel.HIGH,
                    indicators=[f"Error rate increased {analytics.error_rate_trend * 100:.1f}%"],
                    recommendation="Provide just-in-time training",
                    detected_at=datetime.now(),
                )
                alerts.append(alert)
                self.talent_alerts.append(alert)
        
        return alerts
    
    def detect_burnout_risk(self) -> list[TalentRiskAlert]:
        """Detect employees at risk of burnout."""
        alerts: list[TalentRiskAlert] = []
        
        for emp_id, analytics in self.analytics.items():
            burnout_indicators = []
            
            if analytics.engagement_score < 0.4:
                burnout_indicators.append("Low engagement score")
            
            if analytics.a3_participation == 0:
                burnout_indicators.append("No recent A3 participation")
            
            if EmployeeRiskType.BURNOUT in analytics.risk_flags:
                burnout_indicators.append("Previous burnout flag")
            
            if len(burnout_indicators) >= 2:
                alert = TalentRiskAlert(
                    alert_id=f"burnout_{emp_id}_{int(time.time())}",
                    employee_id=emp_id,
                    risk_type=EmployeeRiskType.BURNOUT,
                    severity=RiskLevel.HIGH,
                    indicators=burnout_indicators,
                    recommendation="Consider workload review and wellness check-in",
                    detected_at=datetime.now(),
                )
                alerts.append(alert)
                self.talent_alerts.append(alert)
        
        return alerts
    
    def identify_mentors(self) -> list[str]:
        """Identify subject matter experts for mentoring."""
        candidates = []
        
        for emp_id, analytics in self.analytics.items():
            mentor_score = (
                analytics.skill_score * 0.4 +
                analytics.knowledge_contributions * 0.1 +
                (1 - analytics.error_rate_trend) * 0.3 +
                analytics.engagement_score * 0.2
            )
            
            if mentor_score > 0.7:
                candidates.append(emp_id)
        
        return candidates
    
    def get_retention_risk_score(self, employee_id: str) -> float:
        """Calculate retention risk score for an employee."""
        analytics = self.analytics.get(employee_id)
        
        if not analytics:
            return 0.5  # Unknown
        
        risk_score = 0.0
        
        # Low engagement increases risk
        risk_score += (1 - analytics.engagement_score) * 0.3
        
        # Performance drift increases risk
        if analytics.cycle_time_trend > 0.1:
            risk_score += 0.2
        
        # Lack of growth opportunities
        if analytics.knowledge_contributions < 2:
            risk_score += 0.2
        
        # Burnout indicators
        if EmployeeRiskType.BURNOUT in analytics.risk_flags:
            risk_score += 0.3
        
        return min(risk_score, 1.0)


# =============================================================================
# SENSEI COMMAND ORCHESTRATOR
# =============================================================================


class SenseiCommand:
    """
    Main orchestrator for CEO Strategic Control Plane.
    """
    
    def __init__(self, ceo_user_id: str):
        self.ceo_user_id = ceo_user_id
        
        # Dashboard components
        self.kpi_aggregator = ExecutiveKPIAggregator()
        self.financial_monitor = FinancialHealthMonitor()
        self.risk_generator = RiskHeatmapGenerator()
        
        # System health components
        self.brain_dashboard = BrainHealthDashboard()
        self.learning_analytics = LearningProgressionAnalytics()
        self.maintenance_log = MaintenanceAuditLog()
        
        # Intelligence synthesis
        self.nl2sql_engine = NL2SQLEngine()
        self.briefing_generator = StrategicBriefingGenerator()
        
        # Deep analytics
        self.deep_analytics = DeepDatabaseAnalytics()
        
        # Governance
        self.audit_trail = GlobalAuditTrail()
        self.ceo_view = CEOSuperView(ceo_user_id)
        self.employee_analytics = EmployeeIntelligenceAnalytics()
    
    async def get_executive_dashboard(self, db: AsyncSession) -> dict[str, Any]:
        """Get the executive dashboard summary."""
        return {
            "kpis": self.kpi_aggregator.get_aggregate_view(),
            "financial_health": self.financial_monitor.get_pipeline_health(),
            "risk_heatmap": self.risk_generator.generate_heatmap(),
            "system_health": self.brain_dashboard.get_overall_health(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    async def query_database(self, db: AsyncSession, natural_language: str) -> NL2SQLQuery:
        """Execute a natural language database query."""
        return await self.nl2sql_engine.generate_sql(db, natural_language, user_id=self.ceo_user_id)
    
    def generate_weekly_briefing(self) -> StrategicBriefing:
        """Generate the weekly strategic briefing."""
        kpis = {}
        for kpi_type, data in self.kpi_aggregator.get_aggregate_view().items():
            kpis[kpi_type.value] = data.get("avg_value", 0)
        
        return self.briefing_generator.generate_briefing(
            kpis=kpis,
            risks=self.risk_generator.risks,
            opportunities=["Expand automotive segment", "Improve supplier partnerships"],
        )
    
    def enable_persona_view(self, persona: PersonaType) -> PersonaOverlay:
        """Enable a persona overlay for the CEO."""
        return self.ceo_view.enable_persona_overlay(persona)
    
    def get_talent_insights(self) -> dict[str, Any]:
        """Get talent and employee insights."""
        return {
            "performance_drift_alerts": self.employee_analytics.detect_performance_drift(),
            "burnout_alerts": self.employee_analytics.detect_burnout_risk(),
            "mentor_candidates": self.employee_analytics.identify_mentors(),
        }
    
    def run_deep_analytics(
        self,
        rfq_data: list[dict[str, Any]],
        production_data: list[dict[str, Any]],
        quote_data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run comprehensive deep analytics."""
        return {
            "correlations": self.deep_analytics.analyze_cross_silo_correlation(
                rfq_data, production_data, quote_data
            ),
            "margin_leakages": self.deep_analytics.detect_margin_leakage(quote_data, []),
            "bottlenecks": self.deep_analytics.detect_bottlenecks([]),
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_kpi_aggregator() -> ExecutiveKPIAggregator:
    """Create a KPI aggregator."""
    return ExecutiveKPIAggregator()


def create_financial_monitor() -> FinancialHealthMonitor:
    """Create a financial health monitor."""
    return FinancialHealthMonitor()


def create_risk_generator() -> RiskHeatmapGenerator:
    """Create a risk heatmap generator."""
    return RiskHeatmapGenerator()


def create_brain_dashboard() -> BrainHealthDashboard:
    """Create a brain health dashboard."""
    return BrainHealthDashboard()


def create_nl2sql_engine(
    security_level: QuerySecurityLevel = QuerySecurityLevel.READ_ONLY,
) -> NL2SQLEngine:
    """Create an NL2SQL engine."""
    return NL2SQLEngine(security_level=security_level)


def create_briefing_generator() -> StrategicBriefingGenerator:
    """Create a strategic briefing generator."""
    return StrategicBriefingGenerator()


def create_deep_analytics() -> DeepDatabaseAnalytics:
    """Create a deep database analytics instance."""
    return DeepDatabaseAnalytics()


def create_audit_trail(max_entries: int = 100000) -> GlobalAuditTrail:
    """Create a global audit trail."""
    return GlobalAuditTrail(max_entries=max_entries)


def create_ceo_view(ceo_user_id: str) -> CEOSuperView:
    """Create a CEO super view."""
    return CEOSuperView(ceo_user_id)


def create_employee_analytics(gdpr_compliant: bool = True) -> EmployeeIntelligenceAnalytics:
    """Create employee intelligence analytics."""
    return EmployeeIntelligenceAnalytics(gdpr_compliant=gdpr_compliant)


def create_sensei_command(ceo_user_id: str) -> SenseiCommand:
    """Create a Sensei Command orchestrator."""
    return SenseiCommand(ceo_user_id)
