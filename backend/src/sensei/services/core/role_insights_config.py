"""
Role-Based AI Insights Configuration.

This module defines which AI-generated insights each role can access,
ensuring proper data segregation and the principle of least privilege.

The CEO and Admin roles have full access to all insights.
Each other role has access only to insights relevant to their function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, FrozenSet


# =============================================================================
# Insight Categories
# =============================================================================


class InsightCategory(str, Enum):
    """Categories of AI-generated insights."""
    
    # Executive Insights (CEO, GM, Exec only)
    STRATEGIC_OVERVIEW = "strategic_overview"
    COMPANY_HEALTH = "company_health"
    MARKET_ANALYSIS = "market_analysis"
    COMPETITIVE_INTEL = "competitive_intel"
    RISK_ASSESSMENT = "risk_assessment"
    GROWTH_OPPORTUNITIES = "growth_opportunities"
    
    # Financial Insights (Finance, Accountant, Exec)
    FINANCIAL_KPIs = "financial_kpis"
    CASH_FLOW_FORECAST = "cash_flow_forecast"
    MARGIN_ANALYSIS = "margin_analysis"
    COST_OPTIMIZATION = "cost_optimization"
    REVENUE_TRENDS = "revenue_trends"
    BUDGET_VARIANCE = "budget_variance"
    
    # Sales Insights (Sales, Sales Engineer, Estimator)
    PIPELINE_HEALTH = "pipeline_health"
    WIN_LOSS_ANALYSIS = "win_loss_analysis"
    CUSTOMER_CHURN_RISK = "customer_churn_risk"
    QUOTE_RECOMMENDATIONS = "quote_recommendations"
    PRICING_OPTIMIZATION = "pricing_optimization"
    LEAD_SCORING = "lead_scoring"
    
    # Operations Insights (Ops, Supervisor, Quality)
    PRODUCTION_EFFICIENCY = "production_efficiency"
    CAPACITY_PLANNING = "capacity_planning"
    BOTTLENECK_DETECTION = "bottleneck_detection"
    SCHEDULE_OPTIMIZATION = "schedule_optimization"
    RESOURCE_UTILIZATION = "resource_utilization"
    THROUGHPUT_TRENDS = "throughput_trends"
    
    # Quality Insights (Quality, Auditor)
    QUALITY_TRENDS = "quality_trends"
    DEFECT_PREDICTION = "defect_prediction"
    SPC_ALERTS = "spc_alerts"
    CAPA_RECOMMENDATIONS = "capa_recommendations"
    COMPLIANCE_STATUS = "compliance_status"
    AUDIT_READINESS = "audit_readiness"
    
    # HR Insights (HR, Supervisor)
    WORKFORCE_ANALYTICS = "workforce_analytics"
    RETENTION_RISK = "retention_risk"
    TRAINING_GAPS = "training_gaps"
    PERFORMANCE_TRENDS = "performance_trends"
    COMPENSATION_ANALYSIS = "compensation_analysis"
    HEADCOUNT_PLANNING = "headcount_planning"
    
    # Supply Chain Insights (Supply Chain, Warehouse, Purchasing)
    INVENTORY_OPTIMIZATION = "inventory_optimization"
    SUPPLIER_PERFORMANCE = "supplier_performance"
    DEMAND_FORECAST = "demand_forecast"
    LEAD_TIME_ANALYSIS = "lead_time_analysis"
    REORDER_RECOMMENDATIONS = "reorder_recommendations"
    LOGISTICS_EFFICIENCY = "logistics_efficiency"
    
    # Maintenance Insights (Maintenance, Ops)
    PREDICTIVE_MAINTENANCE = "predictive_maintenance"
    EQUIPMENT_HEALTH = "equipment_health"
    MTBF_ANALYSIS = "mtbf_analysis"
    SPARE_PARTS_FORECAST = "spare_parts_forecast"
    DOWNTIME_PREDICTION = "downtime_prediction"
    MAINTENANCE_SCHEDULE = "maintenance_schedule"
    
    # IT Insights (IT only)
    SYSTEM_HEALTH = "system_health"
    SECURITY_ALERTS = "security_alerts"
    USAGE_ANALYTICS = "usage_analytics"
    PERFORMANCE_METRICS = "performance_metrics"
    INTEGRATION_STATUS = "integration_status"
    
    # General Insights (All authenticated users)
    TASK_RECOMMENDATIONS = "task_recommendations"
    PERSONAL_PRODUCTIVITY = "personal_productivity"
    UPCOMING_DEADLINES = "upcoming_deadlines"
    NOTIFICATION_SUMMARY = "notification_summary"


# =============================================================================
# Role-to-Insight Mapping
# =============================================================================


# Roles with full access to all insights
FULL_ACCESS_ROLES = frozenset({"admin", "ceo"})

# Role-specific insight access
ROLE_INSIGHT_ACCESS: dict[str, FrozenSet[InsightCategory]] = {
    # Executive & Admin - Full access
    "admin": frozenset(InsightCategory),
    "ceo": frozenset(InsightCategory),
    
    # GM - Almost full access (no IT-only insights)
    "gm": frozenset({
        # Strategic
        InsightCategory.STRATEGIC_OVERVIEW,
        InsightCategory.COMPANY_HEALTH,
        InsightCategory.MARKET_ANALYSIS,
        InsightCategory.COMPETITIVE_INTEL,
        InsightCategory.RISK_ASSESSMENT,
        InsightCategory.GROWTH_OPPORTUNITIES,
        # Financial
        InsightCategory.FINANCIAL_KPIs,
        InsightCategory.CASH_FLOW_FORECAST,
        InsightCategory.MARGIN_ANALYSIS,
        InsightCategory.COST_OPTIMIZATION,
        InsightCategory.REVENUE_TRENDS,
        InsightCategory.BUDGET_VARIANCE,
        # Sales
        InsightCategory.PIPELINE_HEALTH,
        InsightCategory.WIN_LOSS_ANALYSIS,
        InsightCategory.CUSTOMER_CHURN_RISK,
        InsightCategory.QUOTE_RECOMMENDATIONS,
        InsightCategory.PRICING_OPTIMIZATION,
        InsightCategory.LEAD_SCORING,
        # Operations
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.CAPACITY_PLANNING,
        InsightCategory.BOTTLENECK_DETECTION,
        InsightCategory.SCHEDULE_OPTIMIZATION,
        InsightCategory.RESOURCE_UTILIZATION,
        InsightCategory.THROUGHPUT_TRENDS,
        # Quality
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.DEFECT_PREDICTION,
        InsightCategory.CAPA_RECOMMENDATIONS,
        InsightCategory.COMPLIANCE_STATUS,
        InsightCategory.AUDIT_READINESS,
        # HR
        InsightCategory.WORKFORCE_ANALYTICS,
        InsightCategory.RETENTION_RISK,
        InsightCategory.TRAINING_GAPS,
        InsightCategory.PERFORMANCE_TRENDS,
        InsightCategory.HEADCOUNT_PLANNING,
        # Supply Chain
        InsightCategory.INVENTORY_OPTIMIZATION,
        InsightCategory.SUPPLIER_PERFORMANCE,
        InsightCategory.DEMAND_FORECAST,
        # Maintenance
        InsightCategory.PREDICTIVE_MAINTENANCE,
        InsightCategory.EQUIPMENT_HEALTH,
        InsightCategory.DOWNTIME_PREDICTION,
        # General
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Exec - Strategic and financial focus
    "exec": frozenset({
        InsightCategory.STRATEGIC_OVERVIEW,
        InsightCategory.COMPANY_HEALTH,
        InsightCategory.MARKET_ANALYSIS,
        InsightCategory.RISK_ASSESSMENT,
        InsightCategory.GROWTH_OPPORTUNITIES,
        InsightCategory.FINANCIAL_KPIs,
        InsightCategory.REVENUE_TRENDS,
        InsightCategory.PIPELINE_HEALTH,
        InsightCategory.WIN_LOSS_ANALYSIS,
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.COMPLIANCE_STATUS,
        InsightCategory.WORKFORCE_ANALYTICS,
        InsightCategory.RETENTION_RISK,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Finance & Accountant - Financial focus
    "finance": frozenset({
        InsightCategory.FINANCIAL_KPIs,
        InsightCategory.CASH_FLOW_FORECAST,
        InsightCategory.MARGIN_ANALYSIS,
        InsightCategory.COST_OPTIMIZATION,
        InsightCategory.REVENUE_TRENDS,
        InsightCategory.BUDGET_VARIANCE,
        InsightCategory.PIPELINE_HEALTH,  # For revenue forecasting
        InsightCategory.INVENTORY_OPTIMIZATION,  # For inventory valuation
        InsightCategory.COMPENSATION_ANALYSIS,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "accountant": frozenset({
        InsightCategory.FINANCIAL_KPIs,
        InsightCategory.CASH_FLOW_FORECAST,
        InsightCategory.BUDGET_VARIANCE,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # HR - People analytics
    "hr": frozenset({
        InsightCategory.WORKFORCE_ANALYTICS,
        InsightCategory.RETENTION_RISK,
        InsightCategory.TRAINING_GAPS,
        InsightCategory.PERFORMANCE_TRENDS,
        InsightCategory.COMPENSATION_ANALYSIS,
        InsightCategory.HEADCOUNT_PLANNING,
        InsightCategory.COMPLIANCE_STATUS,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Operations - Production & efficiency
    "ops": frozenset({
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.CAPACITY_PLANNING,
        InsightCategory.BOTTLENECK_DETECTION,
        InsightCategory.SCHEDULE_OPTIMIZATION,
        InsightCategory.RESOURCE_UTILIZATION,
        InsightCategory.THROUGHPUT_TRENDS,
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.DEFECT_PREDICTION,
        InsightCategory.INVENTORY_OPTIMIZATION,
        InsightCategory.DEMAND_FORECAST,
        InsightCategory.PREDICTIVE_MAINTENANCE,
        InsightCategory.EQUIPMENT_HEALTH,
        InsightCategory.DOWNTIME_PREDICTION,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Quality - Quality & compliance
    "quality": frozenset({
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.DEFECT_PREDICTION,
        InsightCategory.SPC_ALERTS,
        InsightCategory.CAPA_RECOMMENDATIONS,
        InsightCategory.COMPLIANCE_STATUS,
        InsightCategory.AUDIT_READINESS,
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.SUPPLIER_PERFORMANCE,
        InsightCategory.TRAINING_GAPS,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Auditor - Compliance & audit
    "auditor": frozenset({
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.COMPLIANCE_STATUS,
        InsightCategory.AUDIT_READINESS,
        InsightCategory.FINANCIAL_KPIs,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # IT - System & security
    "it": frozenset({
        InsightCategory.SYSTEM_HEALTH,
        InsightCategory.SECURITY_ALERTS,
        InsightCategory.USAGE_ANALYTICS,
        InsightCategory.PERFORMANCE_METRICS,
        InsightCategory.INTEGRATION_STATUS,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Sales & Sales Engineer - Sales focus
    "sales": frozenset({
        InsightCategory.PIPELINE_HEALTH,
        InsightCategory.WIN_LOSS_ANALYSIS,
        InsightCategory.CUSTOMER_CHURN_RISK,
        InsightCategory.QUOTE_RECOMMENDATIONS,
        InsightCategory.PRICING_OPTIMIZATION,
        InsightCategory.LEAD_SCORING,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "sales_engineer": frozenset({
        InsightCategory.PIPELINE_HEALTH,
        InsightCategory.WIN_LOSS_ANALYSIS,
        InsightCategory.CUSTOMER_CHURN_RISK,
        InsightCategory.QUOTE_RECOMMENDATIONS,
        InsightCategory.PRICING_OPTIMIZATION,
        InsightCategory.LEAD_SCORING,
        InsightCategory.PRODUCTION_EFFICIENCY,  # For quote feasibility
        InsightCategory.CAPACITY_PLANNING,  # For delivery estimates
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "estimator": frozenset({
        InsightCategory.QUOTE_RECOMMENDATIONS,
        InsightCategory.PRICING_OPTIMIZATION,
        InsightCategory.COST_OPTIMIZATION,
        InsightCategory.MARGIN_ANALYSIS,
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.CAPACITY_PLANNING,
        InsightCategory.SUPPLIER_PERFORMANCE,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Supply Chain - Procurement & logistics
    "supply_chain": frozenset({
        InsightCategory.INVENTORY_OPTIMIZATION,
        InsightCategory.SUPPLIER_PERFORMANCE,
        InsightCategory.DEMAND_FORECAST,
        InsightCategory.LEAD_TIME_ANALYSIS,
        InsightCategory.REORDER_RECOMMENDATIONS,
        InsightCategory.LOGISTICS_EFFICIENCY,
        InsightCategory.COST_OPTIMIZATION,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "purchasing": frozenset({
        InsightCategory.SUPPLIER_PERFORMANCE,
        InsightCategory.COST_OPTIMIZATION,
        InsightCategory.LEAD_TIME_ANALYSIS,
        InsightCategory.REORDER_RECOMMENDATIONS,
        InsightCategory.INVENTORY_OPTIMIZATION,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "logistics": frozenset({
        InsightCategory.LOGISTICS_EFFICIENCY,
        InsightCategory.LEAD_TIME_ANALYSIS,
        InsightCategory.INVENTORY_OPTIMIZATION,
        InsightCategory.DEMAND_FORECAST,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "warehouse": frozenset({
        InsightCategory.INVENTORY_OPTIMIZATION,
        InsightCategory.REORDER_RECOMMENDATIONS,
        InsightCategory.LOGISTICS_EFFICIENCY,
        InsightCategory.DEMAND_FORECAST,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Maintenance - Equipment & preventive
    "maintenance": frozenset({
        InsightCategory.PREDICTIVE_MAINTENANCE,
        InsightCategory.EQUIPMENT_HEALTH,
        InsightCategory.MTBF_ANALYSIS,
        InsightCategory.SPARE_PARTS_FORECAST,
        InsightCategory.DOWNTIME_PREDICTION,
        InsightCategory.MAINTENANCE_SCHEDULE,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Engineering - Technical & design
    "engineering": frozenset({
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.DEFECT_PREDICTION,
        InsightCategory.CAPACITY_PLANNING,
        InsightCategory.BOTTLENECK_DETECTION,
        InsightCategory.EQUIPMENT_HEALTH,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Supervisor & Team Lead - Team management
    "supervisor": frozenset({
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.RESOURCE_UTILIZATION,
        InsightCategory.THROUGHPUT_TRENDS,
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.TRAINING_GAPS,
        InsightCategory.PERFORMANCE_TRENDS,
        InsightCategory.RETENTION_RISK,
        InsightCategory.SCHEDULE_OPTIMIZATION,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    "team_lead": frozenset({
        InsightCategory.PRODUCTION_EFFICIENCY,
        InsightCategory.RESOURCE_UTILIZATION,
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.TRAINING_GAPS,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Operator - Limited to personal & immediate needs
    "operator": frozenset({
        InsightCategory.SPC_ALERTS,
        InsightCategory.QUALITY_TRENDS,
        InsightCategory.EQUIPMENT_HEALTH,
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
    
    # Viewer - Minimal access
    "viewer": frozenset({
        InsightCategory.TASK_RECOMMENDATIONS,
        InsightCategory.PERSONAL_PRODUCTIVITY,
        InsightCategory.UPCOMING_DEADLINES,
        InsightCategory.NOTIFICATION_SUMMARY,
    }),
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class InsightAccessResult:
    """Result of insight access check."""
    allowed: bool
    role: str
    insight_category: InsightCategory
    reason: str = ""


@dataclass
class RoleInsightProfile:
    """Complete insight profile for a role."""
    role: str
    allowed_insights: FrozenSet[InsightCategory]
    denied_insights: FrozenSet[InsightCategory]
    has_full_access: bool
    insight_count: int


# =============================================================================
# Service Functions
# =============================================================================


def can_access_insight(role: str, insight: InsightCategory) -> InsightAccessResult:
    """
    Check if a role can access a specific insight category.
    
    Args:
        role: User's role (lowercase)
        insight: The insight category to check
        
    Returns:
        InsightAccessResult with access decision and reason
    """
    role_lower = role.lower().strip()
    
    # Full access roles
    if role_lower in FULL_ACCESS_ROLES:
        return InsightAccessResult(
            allowed=True,
            role=role_lower,
            insight_category=insight,
            reason="Full access role"
        )
    
    # Check role-specific access
    allowed_insights = ROLE_INSIGHT_ACCESS.get(role_lower, frozenset())
    
    if insight in allowed_insights:
        return InsightAccessResult(
            allowed=True,
            role=role_lower,
            insight_category=insight,
            reason="Insight allowed for role"
        )
    
    return InsightAccessResult(
        allowed=False,
        role=role_lower,
        insight_category=insight,
        reason=f"Insight '{insight.value}' not accessible to role '{role_lower}'"
    )


def get_role_insight_profile(role: str) -> RoleInsightProfile:
    """
    Get the complete insight profile for a role.
    
    Args:
        role: User's role (lowercase)
        
    Returns:
        RoleInsightProfile with all accessible and denied insights
    """
    role_lower = role.lower().strip()
    all_insights = frozenset(InsightCategory)
    
    # Full access roles
    if role_lower in FULL_ACCESS_ROLES:
        return RoleInsightProfile(
            role=role_lower,
            allowed_insights=all_insights,
            denied_insights=frozenset(),
            has_full_access=True,
            insight_count=len(all_insights)
        )
    
    allowed = ROLE_INSIGHT_ACCESS.get(role_lower, frozenset())
    denied = all_insights - allowed
    
    return RoleInsightProfile(
        role=role_lower,
        allowed_insights=allowed,
        denied_insights=denied,
        has_full_access=False,
        insight_count=len(allowed)
    )


def get_accessible_insights(roles: list[str]) -> FrozenSet[InsightCategory]:
    """
    Get all accessible insights for a list of roles (union of all role permissions).
    
    Args:
        roles: List of user's roles
        
    Returns:
        FrozenSet of accessible InsightCategory values
    """
    accessible = set()
    
    for role in roles:
        role_lower = role.lower().strip()
        
        # Full access roles get everything
        if role_lower in FULL_ACCESS_ROLES:
            return frozenset(InsightCategory)
        
        role_insights = ROLE_INSIGHT_ACCESS.get(role_lower, frozenset())
        accessible.update(role_insights)
    
    return frozenset(accessible)


def filter_insights_for_role(
    insights: list[dict[str, Any]],
    roles: list[str],
    category_field: str = "category"
) -> list[dict[str, Any]]:
    """
    Filter a list of insights based on role access.
    
    Args:
        insights: List of insight dictionaries
        roles: User's roles
        category_field: Field name containing the insight category
        
    Returns:
        Filtered list containing only accessible insights
    """
    accessible = get_accessible_insights(roles)
    
    filtered = []
    for insight in insights:
        category_value = insight.get(category_field)
        if category_value:
            try:
                category = InsightCategory(category_value)
                if category in accessible:
                    filtered.append(insight)
            except ValueError:
                # Unknown category - include for safety (may need review)
                filtered.append(insight)
        else:
            # No category - include by default
            filtered.append(insight)
    
    return filtered


# =============================================================================
# Insight Descriptions (for documentation)
# =============================================================================


INSIGHT_DESCRIPTIONS: dict[InsightCategory, str] = {
    # Executive Insights
    InsightCategory.STRATEGIC_OVERVIEW: "High-level business performance summary",
    InsightCategory.COMPANY_HEALTH: "Overall company health metrics and trends",
    InsightCategory.MARKET_ANALYSIS: "Market trends and competitive positioning",
    InsightCategory.COMPETITIVE_INTEL: "Competitor analysis and industry benchmarks",
    InsightCategory.RISK_ASSESSMENT: "Business risk identification and mitigation",
    InsightCategory.GROWTH_OPPORTUNITIES: "Potential growth areas and opportunities",
    
    # Financial Insights
    InsightCategory.FINANCIAL_KPIs: "Key financial performance indicators",
    InsightCategory.CASH_FLOW_FORECAST: "Cash flow predictions and planning",
    InsightCategory.MARGIN_ANALYSIS: "Product/customer margin analysis",
    InsightCategory.COST_OPTIMIZATION: "Cost reduction opportunities",
    InsightCategory.REVENUE_TRENDS: "Revenue patterns and forecasts",
    InsightCategory.BUDGET_VARIANCE: "Budget vs actual performance",
    
    # Sales Insights
    InsightCategory.PIPELINE_HEALTH: "Sales pipeline status and forecast",
    InsightCategory.WIN_LOSS_ANALYSIS: "Quote win/loss pattern analysis",
    InsightCategory.CUSTOMER_CHURN_RISK: "Customer retention risk assessment",
    InsightCategory.QUOTE_RECOMMENDATIONS: "AI-recommended quote improvements",
    InsightCategory.PRICING_OPTIMIZATION: "Optimal pricing suggestions",
    InsightCategory.LEAD_SCORING: "Lead quality and priority scoring",
    
    # Operations Insights
    InsightCategory.PRODUCTION_EFFICIENCY: "Production efficiency metrics",
    InsightCategory.CAPACITY_PLANNING: "Capacity utilization and planning",
    InsightCategory.BOTTLENECK_DETECTION: "Production bottleneck identification",
    InsightCategory.SCHEDULE_OPTIMIZATION: "Scheduling recommendations",
    InsightCategory.RESOURCE_UTILIZATION: "Resource usage optimization",
    InsightCategory.THROUGHPUT_TRENDS: "Production throughput analysis",
    
    # Quality Insights
    InsightCategory.QUALITY_TRENDS: "Quality metric trends over time",
    InsightCategory.DEFECT_PREDICTION: "Predictive defect analysis",
    InsightCategory.SPC_ALERTS: "Statistical process control alerts",
    InsightCategory.CAPA_RECOMMENDATIONS: "Corrective action recommendations",
    InsightCategory.COMPLIANCE_STATUS: "Regulatory compliance status",
    InsightCategory.AUDIT_READINESS: "Audit preparation assessment",
    
    # HR Insights
    InsightCategory.WORKFORCE_ANALYTICS: "Workforce composition and trends",
    InsightCategory.RETENTION_RISK: "Employee retention risk assessment",
    InsightCategory.TRAINING_GAPS: "Skill/training gap analysis",
    InsightCategory.PERFORMANCE_TRENDS: "Employee performance trends",
    InsightCategory.COMPENSATION_ANALYSIS: "Compensation benchmarking",
    InsightCategory.HEADCOUNT_PLANNING: "Workforce planning recommendations",
    
    # Supply Chain Insights
    InsightCategory.INVENTORY_OPTIMIZATION: "Inventory level optimization",
    InsightCategory.SUPPLIER_PERFORMANCE: "Supplier performance metrics",
    InsightCategory.DEMAND_FORECAST: "Demand prediction and planning",
    InsightCategory.LEAD_TIME_ANALYSIS: "Lead time trends and optimization",
    InsightCategory.REORDER_RECOMMENDATIONS: "Reorder point suggestions",
    InsightCategory.LOGISTICS_EFFICIENCY: "Logistics and shipping efficiency",
    
    # Maintenance Insights
    InsightCategory.PREDICTIVE_MAINTENANCE: "Predictive equipment maintenance",
    InsightCategory.EQUIPMENT_HEALTH: "Equipment condition monitoring",
    InsightCategory.MTBF_ANALYSIS: "Mean time between failures analysis",
    InsightCategory.SPARE_PARTS_FORECAST: "Spare parts inventory needs",
    InsightCategory.DOWNTIME_PREDICTION: "Planned/unplanned downtime forecast",
    InsightCategory.MAINTENANCE_SCHEDULE: "Optimized maintenance scheduling",
    
    # IT Insights
    InsightCategory.SYSTEM_HEALTH: "System performance and health",
    InsightCategory.SECURITY_ALERTS: "Security threat notifications",
    InsightCategory.USAGE_ANALYTICS: "Application usage patterns",
    InsightCategory.PERFORMANCE_METRICS: "System performance metrics",
    InsightCategory.INTEGRATION_STATUS: "Integration health and status",
    
    # General Insights
    InsightCategory.TASK_RECOMMENDATIONS: "Prioritized task suggestions",
    InsightCategory.PERSONAL_PRODUCTIVITY: "Personal productivity metrics",
    InsightCategory.UPCOMING_DEADLINES: "Deadline reminders and alerts",
    InsightCategory.NOTIFICATION_SUMMARY: "Consolidated notification digest",
}
