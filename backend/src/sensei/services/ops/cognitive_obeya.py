"""
Cognitive Obeya: The Organizational Brain.

Moves the Obeya Room from passive monitoring to active, prescriptive intelligence.
Provides causal linking, predictive warnings, cross-functional synergy, and Heijunka leveling.
"""

from __future__ import annotations

import logging
import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
import asyncio
from sensei.core.websocket import get_websocket_manager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sql_update
from sensei.models.cognitive_obeya import (
    MetricRecord,
    CausalLinkRecord,
    TrendWarningRecord,
    SiloAlertRecord,
    ResourceRebalanceRecord,
    HeijunkaSuggestionRecord,
)

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================


from sensei.core.enums import MetricStatus, Severity as AlertSeverity, MetricCategory, DepartmentType


class TrendDirection(Enum):
    """Trend direction for metrics."""
    
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class AlertType(Enum):
    """Types of Obeya alerts."""
    
    CAUSAL_LINK = "causal_link"
    PREDICTIVE_WARNING = "predictive_warning"
    SILO_BUSTER = "silo_buster"
    RESOURCE_REBALANCE = "resource_rebalance"
    HEIJUNKA_SUGGESTION = "heijunka_suggestion"


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class MetricValue:
    """A metric measurement at a point in time."""
    
    metric_id: str
    category: MetricCategory
    name: str
    value: float
    target: float
    timestamp: datetime
    unit: str = ""
    status: MetricStatus = MetricStatus.GREEN
    
    def __post_init__(self):
        """Compute status from value and target."""
        if not self.status or self.status == MetricStatus.GREEN:
            self._compute_status()
    
    def _compute_status(self):
        """Compute status based on value vs target."""
        # For metrics where lower is better (defects, costs, incidents)
        lower_is_better = self.category in [
            MetricCategory.SAFETY,
            MetricCategory.COST,
        ] or "defect" in self.name.lower() or "incident" in self.name.lower()
        
        if lower_is_better:
            if self.value <= self.target:
                self.status = MetricStatus.GREEN
            elif self.value <= self.target * 1.2:
                self.status = MetricStatus.YELLOW
            else:
                self.status = MetricStatus.RED
        else:
            # Higher is better (quality %, productivity, delivery %)
            if self.value >= self.target:
                self.status = MetricStatus.GREEN
            elif self.value >= self.target * 0.9:
                self.status = MetricStatus.YELLOW
            else:
                self.status = MetricStatus.RED


@dataclass
class CausalLink:
    """A causal relationship between a metric and a source."""
    
    link_id: str
    metric_id: str
    source_type: str  # "work_order", "supplier_quote", "incident", etc.
    source_id: str
    source_description: str
    confidence: float  # 0.0 to 1.0
    impact_value: float
    detected_at: datetime
    explanation: str = ""


@dataclass
class TrendWarning:
    """A predictive warning about metric trends."""
    
    warning_id: str
    metric_id: str
    metric_name: str
    current_status: MetricStatus
    predicted_status: MetricStatus
    days_to_breach: int
    trend_values: list[float]
    confidence: float
    detected_at: datetime
    recommendation: str = ""


@dataclass
class SiloAlert:
    """Cross-functional silo-busting alert."""
    
    alert_id: str
    source_department: DepartmentType
    affected_department: DepartmentType
    source_event: str
    predicted_impact: str
    severity: AlertSeverity
    detected_at: datetime
    owners_notified: list[str] = field(default_factory=list)
    resolution_status: str = "open"


@dataclass
class ResourceRebalance:
    """Resource rebalancing suggestion."""
    
    suggestion_id: str
    source_work_center: str
    target_work_center: str
    operator_ids: list[str]
    skill_match_score: float
    reason: str
    expected_improvement: float
    suggested_at: datetime
    status: str = "pending"


@dataclass
class HeijunkaSuggestion:
    """Heijunka (production leveling) suggestion."""
    
    suggestion_id: str
    period: str  # "daily", "weekly", "monthly"
    current_mix: dict[str, int]  # product -> quantity
    suggested_mix: dict[str, int]
    mura_reduction: float  # % reduction in unevenness
    volume_variance_before: float
    volume_variance_after: float
    suggested_at: datetime
    reasoning: str = ""
    status: str = "pending"


@dataclass
class WorkCenterLoad:
    """Work center load status."""
    
    work_center_id: str
    name: str
    capacity: int
    current_load: int
    wip_count: int
    operator_count: int
    utilization: float = 0.0
    
    def __post_init__(self):
        if self.capacity > 0:
            self.utilization = self.current_load / self.capacity


@dataclass
class SkillProfile:
    """Operator skill profile."""
    
    operator_id: str
    name: str
    skills: dict[str, float]  # skill_name -> proficiency (0-1)
    current_work_center: str
    available: bool = True


# =============================================================================
# PRESCRIPTIVE METRIC ANALYSIS
# =============================================================================


class AsyncPrescriptiveMetricAnalyzer:
    """
    Prescriptive Metric Analysis engine.
    
    Provides causal linking and predictive trend warnings for SQDCP metrics.
    """
    
    def __init__(self):
        """Initialize analyzer."""
        self.detection_rules: dict[str, Any] = {}
    
    async def record_metric(self, db: AsyncSession, metric: MetricValue) -> None:
        """Record a metric measurement."""
        record = MetricRecord(
            metric_id=metric.metric_id,
            category=metric.category,
            name=metric.name,
            value=metric.value,
            target=metric.target,
            timestamp=metric.timestamp,
            unit=metric.unit,
            status=metric.status,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    
    async def get_metric_history(self, db: AsyncSession, metric_id: str, days: int = 90) -> list[MetricValue]:
        """Retrieve metric history from database."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(MetricRecord)
            .where(MetricRecord.metric_id == metric_id, MetricRecord.timestamp > cutoff)
            .order_by(MetricRecord.timestamp.asc())
        )
        records = result.scalars().all()
        return [
            MetricValue(
                metric_id=r.metric_id,
                category=r.category,
                name=r.name,
                value=r.value,
                target=r.target,
                timestamp=r.timestamp,
                unit=r.unit,
                status=r.status,
            )
            for r in records
        ]

    async def find_causal_links(self, db: AsyncSession, metric_id: str) -> list[CausalLink]:
        """
        Find causal links for a RED metric.
        
        Automatically links a 'Red' metric to specific recent Work Orders
        or Supplier Quotes to provide an instant "Why".
        """
        history = await self.get_metric_history(db, metric_id)
        if not history:
            return []
        
        latest = history[-1]
        if latest.status != MetricStatus.RED:
            return []
        
        # Query persisted links
        result = await db.execute(select(CausalLinkRecord).where(CausalLinkRecord.metric_id == metric_id))
        records = result.scalars().all()
        
        if records:
            return [
                CausalLink(
                    link_id=r.id,
                    metric_id=r.metric_id,
                    source_type=r.source_type,
                    source_id=r.source_id,
                    source_description=r.source_description,
                    confidence=r.confidence,
                    impact_value=r.impact_value,
                    detected_at=r.detected_at,
                    explanation=r.explanation,
                )
                for r in records
            ]

        # Perform automated causal discovery by querying related models
        from sqlalchemy.orm import selectinload
        from sensei.models.work_order import WorkOrder
        from sensei.models.rfq import RFQ
        from sensei.models.quality import NonConformance
        
        discovered_links: list[CausalLink] = []
        lookback = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Discover links from Work Orders (eager-load non_conformances for quality metric)
        wo_result = await db.execute(
            select(WorkOrder)
            .options(selectinload(WorkOrder.non_conformances))
            .where(WorkOrder.updated_at > lookback)
            .limit(50)
        )
        for wo in wo_result.scalars().all():
            # Use quantity_scrapped as a proxy for defects, and count non-conformances
            quality_issues = int(wo.quantity_scrapped) + len(wo.non_conformances)
            wo_dict = {
                "id": str(wo.id),
                "description": wo.notes or f"Work Order {wo.work_order_number}",
                "quality_issues": quality_issues,
                "delivery_delay": max(0, (wo.actual_end - wo.scheduled_end).days) if wo.actual_end and wo.scheduled_end else 0,
                "cost_overrun": 0.0,  # Cost tracking not implemented on WorkOrder model
                "safety_incidents": 0,  # Safety tracking not implemented on WorkOrder model
            }
            link = self._evaluate_work_order_link(latest, wo_dict)
            if link:
                discovered_links.append(link)
        
        # Discover links from RFQs (using actual RFQ model fields)
        rfq_result = await db.execute(
            select(RFQ).where(
                RFQ.updated_at > lookback
            ).limit(50)
        )
        for rfq in rfq_result.scalars().all():
            # Use customer_notes for supplier description, and status-based heuristics for ratings
            # Since RFQ doesn't have supplier ratings, we use defaults
            quote_dict = {
                "id": str(rfq.id),
                "supplier": rfq.customer_notes or rfq.title or "Unknown",
                "quality_rating": 1.0,  # Supplier quality rating not tracked on RFQ model
                "delivery_rating": 1.0,  # Supplier delivery rating not tracked on RFQ model
                "cost_variance": 0.0,  # Cost variance not tracked on RFQ model
            }
            link = self._evaluate_supplier_link(latest, quote_dict)
            if link:
                discovered_links.append(link)
        
        # Discover links from Non-Conformances (as incidents)
        nc_result = await db.execute(
            select(NonConformance).where(
                NonConformance.created_at > lookback,
                NonConformance.status != "closed"
            ).limit(50)
        )
        for nc in nc_result.scalars().all():
            # Map severity enum to numeric score for analysis
            severity_map = {"minor": 1, "major": 2, "critical": 3}
            severity_score = severity_map.get(nc.severity.value if nc.severity else "minor", 1)
            incident_dict = {
                "id": str(nc.id),
                "description": nc.description or f"NCR {nc.nc_number}",
                "severity": severity_score,
                "category": "quality" if latest.category == MetricCategory.QUALITY else "safety",
            }
            link = self._evaluate_incident_link(latest, incident_dict)
            if link:
                discovered_links.append(link)
        
        # Persist discovered links for future queries
        for link in discovered_links:
            record = CausalLinkRecord(
                id=link.link_id,
                metric_id=link.metric_id,
                source_type=link.source_type,
                source_id=link.source_id,
                source_description=link.source_description,
                confidence=link.confidence,
                impact_value=link.impact_value,
                detected_at=link.detected_at,
                explanation=link.explanation,
            )
            db.add(record)
        
        if discovered_links:
            await db.commit()
        
        return discovered_links
    
    def _evaluate_work_order_link(
        self,
        metric: MetricValue,
        work_order: dict[str, Any],
    ) -> CausalLink | None:
        """Evaluate if a work order caused the metric issue."""
        impact = 0.0
        confidence = 0.0
        
        if metric.category == MetricCategory.QUALITY:
            if work_order["quality_issues"] > 0:
                impact = work_order["quality_issues"]
                confidence = min(0.9, 0.3 + work_order["quality_issues"] * 0.1)
        elif metric.category == MetricCategory.DELIVERY:
            if work_order["delivery_delay"] > 0:
                impact = work_order["delivery_delay"]
                confidence = min(0.9, 0.3 + work_order["delivery_delay"] * 0.05)
        elif metric.category == MetricCategory.COST:
            if work_order["cost_overrun"] > 0:
                impact = work_order["cost_overrun"]
                confidence = min(0.9, 0.3 + work_order["cost_overrun"] / 1000)
        elif metric.category == MetricCategory.SAFETY:
            if work_order["safety_incidents"] > 0:
                impact = work_order["safety_incidents"]
                confidence = min(0.95, 0.5 + work_order["safety_incidents"] * 0.2)
        
        if confidence > 0.3:
            return CausalLink(
                link_id=str(uuid.uuid4()),
                metric_id=metric.metric_id,
                source_type="work_order",
                source_id=work_order["id"],
                source_description=work_order["description"],
                confidence=confidence,
                impact_value=impact,
                detected_at=datetime.now(timezone.utc),
                explanation=f"Work Order {work_order['id']} had issues affecting {metric.category.value}",
            )
        return None
    
    def _evaluate_supplier_link(
        self,
        metric: MetricValue,
        quote: dict[str, Any],
    ) -> CausalLink | None:
        """Evaluate if a supplier quote caused the metric issue."""
        impact = 0.0
        confidence = 0.0
        
        if metric.category == MetricCategory.QUALITY:
            if quote["quality_rating"] < 0.8:
                impact = 1.0 - quote["quality_rating"]
                confidence = min(0.85, 0.3 + (1.0 - quote["quality_rating"]))
        elif metric.category == MetricCategory.DELIVERY:
            if quote["delivery_rating"] < 0.9:
                impact = 1.0 - quote["delivery_rating"]
                confidence = min(0.85, 0.2 + (1.0 - quote["delivery_rating"]))
        elif metric.category == MetricCategory.COST:
            if quote["cost_variance"] > 0.05:
                impact = quote["cost_variance"]
                confidence = min(0.8, 0.3 + quote["cost_variance"])
        
        if confidence > 0.3:
            return CausalLink(
                link_id=str(uuid.uuid4()),
                metric_id=metric.metric_id,
                source_type="supplier_quote",
                source_id=quote["id"],
                source_description=f"Supplier: {quote['supplier']}",
                confidence=confidence,
                impact_value=impact,
                detected_at=datetime.now(timezone.utc),
                explanation=f"Supplier {quote['supplier']} rating affected {metric.category.value}",
            )
        return None
    
    def _evaluate_incident_link(
        self,
        metric: MetricValue,
        incident: dict[str, Any],
    ) -> CausalLink | None:
        """Evaluate if an incident caused the metric issue."""
        if metric.category != MetricCategory.SAFETY:
            return None
        
        if incident["category"] != "safety":
            return None
        
        confidence = min(0.95, 0.4 + incident["severity"] * 0.15)
        
        return CausalLink(
            link_id=str(uuid.uuid4()),
            metric_id=metric.metric_id,
            source_type="incident",
            source_id=incident["id"],
            source_description=incident["description"],
            confidence=confidence,
            impact_value=float(incident["severity"]),
            detected_at=datetime.now(timezone.utc),
            explanation=f"Safety incident {incident['id']} directly impacted safety metrics",
        )
    
    async def analyze_trend(self, db: AsyncSession, metric_id: str, days: int = 7) -> TrendWarning | None:
        """
        Analyze metric trend and predict if it will breach target.
        
        Alerts the Obeya team *before* a metric turns red by analyzing
        7-day variance trends.
        """
        history = await self.get_metric_history(db, metric_id, days=days)
        if len(history) < 3:
            return None
        
        latest = history[-1]
        
        # Already red - no need to predict
        if latest.status == MetricStatus.RED:
            return None
        
        # Extract values and compute trend
        values = [m.value for m in history]
        
        # Compute linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine if declining (for higher-is-better) or increasing (for lower-is-better)
        lower_is_better = latest.category in [
            MetricCategory.SAFETY,
            MetricCategory.COST,
        ] or "defect" in latest.name.lower()
        
        # Calculate variance
        variance = statistics.variance(values) if len(values) > 1 else 0
        
        # Predict days to breach
        if lower_is_better:
            # Bad if trending up
            if slope <= 0:
                return None  # Improving or stable
            threshold = latest.target * 1.2  # Red threshold
            days_to_breach = int((threshold - latest.value) / slope) if slope > 0 else 999
        else:
            # Bad if trending down
            if slope >= 0:
                return None  # Improving or stable
            threshold = latest.target * 0.9  # Red threshold
            days_to_breach = int((latest.value - threshold) / abs(slope)) if slope < 0 else 999
        
        # Only warn if breach is within 14 days
        if days_to_breach > 14 or days_to_breach <= 0:
            return None
        
        # Compute confidence based on variance and days
        confidence = max(0.5, min(0.95, 1.0 - variance / (abs(y_mean) + 0.01)))
        
        warning_id = str(uuid.uuid4())
        record = TrendWarningRecord(
            id=warning_id,
            metric_id=metric_id,
            metric_name=latest.name,
            current_status=latest.status,
            predicted_status=MetricStatus.RED,
            days_to_breach=days_to_breach,
            trend_values=values,
            confidence=confidence,
            detected_at=datetime.now(timezone.utc),
            recommendation=f"Review {latest.category.value} processes to prevent metric degradation",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        return self._record_to_warning(record)
    
    def _record_to_warning(self, r: TrendWarningRecord) -> TrendWarning:
        return TrendWarning(
            warning_id=r.id,
            metric_id=r.metric_id,
            metric_name=r.metric_name,
            current_status=r.current_status,
            predicted_status=r.predicted_status,
            days_to_breach=r.days_to_breach,
            trend_values=r.trend_values,
            confidence=r.confidence,
            detected_at=r.detected_at,
            recommendation=r.recommendation,
        )

    async def get_all_warnings(self, db: AsyncSession) -> list[TrendWarning]:
        """Get all active trend warnings."""
        result = await db.execute(select(TrendWarningRecord).order_by(TrendWarningRecord.detected_at.desc()))
        return [self._record_to_warning(r) for r in result.scalars().all()]
    
    async def get_causal_links_for_metric(self, db: AsyncSession, metric_id: str) -> list[CausalLink]:
        """Get causal links for a specific metric."""
        result = await db.execute(select(CausalLinkRecord).where(CausalLinkRecord.metric_id == metric_id))
        records = result.scalars().all()
        return [
            CausalLink(
                link_id=r.id,
                metric_id=r.metric_id,
                source_type=r.source_type,
                source_id=r.source_id,
                source_description=r.source_description,
                confidence=r.confidence,
                impact_value=r.impact_value,
                detected_at=r.detected_at,
                explanation=r.explanation,
            )
            for r in records
        ]


class PrescriptiveMetricAnalyzer:
    """In-memory Prescriptive Metric Analyzer for sync use cases and tests."""

    def __init__(self):
        self.detection_rules: dict[str, Any] = {}
        self.metrics_history: dict[str, list[MetricValue]] = {}
        self.work_orders: dict[str, dict[str, Any]] = {}
        self.supplier_quotes: dict[str, dict[str, Any]] = {}
        self.incidents: dict[str, dict[str, Any]] = {}

    def record_metric(self, metric: MetricValue) -> None:
        self.metrics_history.setdefault(metric.metric_id, []).append(metric)

    def get_metric_history(self, metric_id: str, days: int = 90) -> list[MetricValue]:
        history = self.metrics_history.get(metric_id, [])
        if not history:
            return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        if history and history[0].timestamp.tzinfo is None:
            cutoff = datetime.now() - timedelta(days=days)
        return [m for m in history if m.timestamp >= cutoff]

    def register_work_order(
        self,
        work_order_id: str,
        description: str,
        quality_issues: int = 0,
        delivery_delay: int = 0,
        cost_overrun: float = 0.0,
        safety_incidents: int = 0,
    ) -> None:
        self.work_orders[work_order_id] = {
            "id": work_order_id,
            "description": description,
            "quality_issues": quality_issues,
            "delivery_delay": delivery_delay,
            "cost_overrun": cost_overrun,
            "safety_incidents": safety_incidents,
        }

    def register_supplier_quote(
        self,
        quote_id: str,
        supplier: str,
        quality_rating: float = 1.0,
        delivery_rating: float = 1.0,
        cost_variance: float = 0.0,
    ) -> None:
        self.supplier_quotes[quote_id] = {
            "id": quote_id,
            "supplier": supplier,
            "quality_rating": quality_rating,
            "delivery_rating": delivery_rating,
            "cost_variance": cost_variance,
        }

    def register_incident(
        self,
        incident_id: str,
        description: str,
        severity: int,
        category: str = "safety",
    ) -> None:
        self.incidents[incident_id] = {
            "id": incident_id,
            "description": description,
            "severity": severity,
            "category": category,
        }

    def _evaluate_work_order_link(
        self,
        metric: MetricValue,
        work_order: dict[str, Any],
    ) -> CausalLink | None:
        """Evaluate if a work order caused the metric issue."""
        impact = 0.0
        confidence = 0.0
        
        if metric.category == MetricCategory.QUALITY:
            if work_order["quality_issues"] > 0:
                impact = work_order["quality_issues"]
                confidence = min(0.9, 0.3 + work_order["quality_issues"] * 0.1)
        elif metric.category == MetricCategory.DELIVERY:
            if work_order["delivery_delay"] > 0:
                impact = work_order["delivery_delay"]
                confidence = min(0.9, 0.3 + work_order["delivery_delay"] * 0.05)
        elif metric.category == MetricCategory.COST:
            if work_order["cost_overrun"] > 0:
                impact = work_order["cost_overrun"]
                confidence = min(0.9, 0.3 + work_order["cost_overrun"] / 1000)
        elif metric.category == MetricCategory.SAFETY:
            if work_order["safety_incidents"] > 0:
                impact = work_order["safety_incidents"]
                confidence = min(0.95, 0.5 + work_order["safety_incidents"] * 0.2)
        
        if confidence > 0.3:
            return CausalLink(
                link_id=str(uuid.uuid4()),
                metric_id=metric.metric_id,
                source_type="work_order",
                source_id=work_order["id"],
                source_description=work_order["description"],
                confidence=confidence,
                impact_value=impact,
                detected_at=datetime.now(timezone.utc),
                explanation=f"Work Order {work_order['id']} had issues affecting {metric.category.value}",
            )
        return None

    def _evaluate_supplier_link(
        self,
        metric: MetricValue,
        quote: dict[str, Any],
    ) -> CausalLink | None:
        """Evaluate if a supplier quote caused the metric issue."""
        impact = 0.0
        confidence = 0.0
        
        if metric.category == MetricCategory.QUALITY:
            if quote["quality_rating"] < 0.8:
                impact = 1.0 - quote["quality_rating"]
                confidence = min(0.85, 0.3 + (1.0 - quote["quality_rating"]))
        elif metric.category == MetricCategory.DELIVERY:
            if quote["delivery_rating"] < 0.9:
                impact = 1.0 - quote["delivery_rating"]
                confidence = min(0.85, 0.2 + (1.0 - quote["delivery_rating"]))
        elif metric.category == MetricCategory.COST:
            if quote["cost_variance"] > 0.05:
                impact = quote["cost_variance"]
                confidence = min(0.8, 0.3 + quote["cost_variance"])
        
        if confidence > 0.3:
            return CausalLink(
                link_id=str(uuid.uuid4()),
                metric_id=metric.metric_id,
                source_type="supplier_quote",
                source_id=quote["id"],
                source_description=f"Supplier: {quote['supplier']}",
                confidence=confidence,
                impact_value=impact,
                detected_at=datetime.now(timezone.utc),
                explanation=f"Supplier {quote['supplier']} rating affected {metric.category.value}",
            )
        return None

    def _evaluate_incident_link(
        self,
        metric: MetricValue,
        incident: dict[str, Any],
    ) -> CausalLink | None:
        """Evaluate if an incident caused the metric issue."""
        if metric.category != MetricCategory.SAFETY:
            return None
        
        if incident["category"] != "safety":
            return None
        
        confidence = min(0.95, 0.4 + incident["severity"] * 0.15)
        
        return CausalLink(
            link_id=str(uuid.uuid4()),
            metric_id=metric.metric_id,
            source_type="incident",
            source_id=incident["id"],
            source_description=incident["description"],
            confidence=confidence,
            impact_value=float(incident["severity"]),
            detected_at=datetime.now(timezone.utc),
            explanation=f"Safety incident {incident['id']} directly impacted safety metrics",
        )

    def find_causal_links(self, metric_id: str) -> list[CausalLink]:
        history = self.get_metric_history(metric_id)
        if not history:
            return []
        latest = history[-1]
        if latest.status != MetricStatus.RED:
            return []

        links: list[CausalLink] = []
        for work_order in self.work_orders.values():
            link = self._evaluate_work_order_link(latest, work_order)
            if link:
                links.append(link)

        for quote in self.supplier_quotes.values():
            link = self._evaluate_supplier_link(latest, quote)
            if link:
                links.append(link)

        for incident in self.incidents.values():
            link = self._evaluate_incident_link(latest, incident)
            if link:
                links.append(link)

        return links

    def analyze_trend(self, metric_id: str, days: int = 7) -> TrendWarning | None:
        history = self.get_metric_history(metric_id, days=days)
        if len(history) < 3:
            return None

        latest = history[-1]
        if latest.status == MetricStatus.RED:
            return None

        values = [m.value for m in history]
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0

        lower_is_better = latest.category in [
            MetricCategory.SAFETY,
            MetricCategory.COST,
        ] or "defect" in latest.name.lower()

        variance = statistics.variance(values) if len(values) > 1 else 0

        if lower_is_better:
            if slope <= 0:
                return None
            threshold = latest.target * 1.2
            days_to_breach = int((threshold - latest.value) / slope) if slope > 0 else 999
        else:
            if slope >= 0:
                return None
            threshold = latest.target * 0.9
            days_to_breach = int((latest.value - threshold) / abs(slope)) if slope < 0 else 999

        if days_to_breach > 14 or days_to_breach <= 0:
            return None

        confidence = max(0.5, min(0.95, 1.0 - variance / (abs(y_mean) + 0.01)))

        return TrendWarning(
            warning_id=str(uuid.uuid4()),
            metric_id=metric_id,
            metric_name=latest.name,
            current_status=latest.status,
            predicted_status=MetricStatus.RED,
            days_to_breach=days_to_breach,
            trend_values=values,
            confidence=confidence,
            detected_at=datetime.now(timezone.utc),
            recommendation=f"Review {latest.category.value} processes to prevent metric degradation",
        )


# =============================================================================
# CROSS-FUNCTIONAL SYNERGY ENGINE
# =============================================================================


class AsyncCrossFunctionalSynergyEngine:
    """
    Cross-Functional Synergy Engine.
    
    Detects silo-busting opportunities and resource rebalancing needs.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.department_events: dict[DepartmentType, list[dict[str, Any]]] = {
            dept: [] for dept in DepartmentType
        }
        self.silo_alerts: list[SiloAlert] = []
        self.work_centers: dict[str, WorkCenterLoad] = {}
        self.operators: dict[str, SkillProfile] = {}
        self.rebalance_suggestions: list[ResourceRebalance] = []
    
    async def register_event(
        self,
        db: AsyncSession,
        department: DepartmentType,
        event_type: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        data: dict[str, Any] | None = None,
    ) -> str:
        """Register a department event."""
        # For now, we still check cross-functional impact and create SiloAlertRecords
        await self._check_cross_functional_impact(db, department, event_type, description, severity)
        return str(uuid.uuid4())
    
    async def _check_cross_functional_impact(
        self,
        db: AsyncSession,
        source_dept: DepartmentType,
        event_type: str,
        description: str,
        severity: AlertSeverity,
    ) -> None:
        """Check if an event impacts other departments."""
        # Define impact relationships
        impact_map: dict[DepartmentType, list[tuple[DepartmentType, str, str]]] = {
            DepartmentType.SALES: [
                (DepartmentType.PRODUCTION, "rfq_delay", "production bottleneck"),
                (DepartmentType.ENGINEERING, "new_product", "design capacity"),
            ],
            DepartmentType.PRODUCTION: [
                (DepartmentType.LOGISTICS, "delay", "shipping schedule"),
                (DepartmentType.QUALITY, "rush_order", "inspection backlog"),
            ],
            DepartmentType.QUALITY: [
                (DepartmentType.PRODUCTION, "hold", "line stoppage"),
                (DepartmentType.LOGISTICS, "reject", "return processing"),
            ],
            DepartmentType.LOGISTICS: [
                (DepartmentType.PRODUCTION, "material_delay", "production halt"),
            ],
            DepartmentType.ENGINEERING: [
                (DepartmentType.PRODUCTION, "design_change", "process update"),
            ],
            DepartmentType.MAINTENANCE: [
                (DepartmentType.PRODUCTION, "equipment_down", "capacity loss"),
            ],
        }
        
        if source_dept not in impact_map:
            return
        
        for affected_dept, trigger, impact in impact_map[source_dept]:
            if trigger in event_type.lower() or trigger in description.lower():
                alert_id = str(uuid.uuid4())
                record = SiloAlertRecord(
                    id=alert_id,
                    source_department=source_dept,
                    affected_department=affected_dept,
                    source_event=f"{event_type}: {description}",
                    predicted_impact=f"Potential {impact} in {affected_dept.value}",
                    severity=severity,
                    detected_at=datetime.now(timezone.utc),
                    owners_notified=[],
                    resolution_status="open",
                )
                db.add(record)
                await db.commit()
                await db.refresh(record)
    
    async def get_silo_alerts(self, db: AsyncSession) -> list[SiloAlert]:
        """Get all active silo alerts."""
        result = await db.execute(select(SiloAlertRecord).where(SiloAlertRecord.resolution_status == "open"))
        return [
            SiloAlert(
                alert_id=r.id,
                source_department=r.source_department,
                affected_department=r.affected_department,
                source_event=r.source_event,
                predicted_impact=r.predicted_impact,
                severity=r.severity,
                detected_at=r.detected_at,
                owners_notified=r.owners_notified,
                resolution_status=r.resolution_status,
            )
            for r in result.scalars().all()
        ]

    def analyze_resource_rebalancing(self, db: AsyncSession | None = None) -> list[ResourceRebalance]:
        """
        Analyze and suggest resource rebalancing.
        
        Suggests moving operators between Work Centers based on
        real-time Skill Gap Index and current WIP volume.
        """
        suggestions: list[ResourceRebalance] = []
        
        # Find overloaded and underloaded work centers
        overloaded = [
            wc for wc in self.work_centers.values()
            if wc.utilization > 0.9
        ]
        underloaded = [
            wc for wc in self.work_centers.values()
            if wc.utilization < 0.6
        ]
        
        if not overloaded or not underloaded:
            return suggestions
        
        for over_wc in overloaded:
            for under_wc in underloaded:
                # Find available operators in underloaded center
                available_operators = [
                    op for op in self.operators.values()
                    if op.current_work_center == under_wc.work_center_id
                    and op.available
                ]
                
                if not available_operators:
                    continue
                
                # Check skill match
                required_skills = self._infer_required_skills(over_wc.name)
                
                matching_operators: list[tuple[SkillProfile, float]] = []
                for op in available_operators:
                    match_score = self._calculate_skill_match(list(op.skills.keys()), required_skills)
                    if match_score >= 0.6:
                        matching_operators.append((op, match_score))
                
                if matching_operators:
                    matching_operators.sort(key=lambda x: x[1], reverse=True)
                    top_matches = matching_operators[:2]
                    
                    avg_score = sum(m[1] for m in top_matches) / len(top_matches)
                    expected_improvement = min(
                        0.2,
                        (over_wc.utilization - 0.8) * len(top_matches) * 0.1
                    )
                    
                    suggestion = ResourceRebalance(
                        suggestion_id=str(uuid.uuid4()),
                        source_work_center=under_wc.work_center_id,
                        target_work_center=over_wc.work_center_id,
                        operator_ids=[m[0].operator_id for m in top_matches],
                        skill_match_score=avg_score,
                        reason=f"Rebalance from {under_wc.name} ({under_wc.utilization:.0%} util) "
                               f"to {over_wc.name} ({over_wc.utilization:.0%} util)",
                        expected_improvement=expected_improvement,
                        suggested_at=datetime.now(timezone.utc),
                    )
                    suggestions.append(suggestion)
        
        self.rebalance_suggestions.extend(suggestions)
        return suggestions

    def _infer_required_skills(self, work_center_name: str) -> list[str]:
        """Infer required skills from work center name."""
        skill_map = {
            "assembly": ["assembly", "hand_tools", "quality_inspection"],
            "welding": ["welding", "metal_fabrication", "safety"],
            "machining": ["cnc", "manual_machining", "measurement"],
            "painting": ["painting", "surface_prep", "safety"],
            "inspection": ["quality_inspection", "measurement", "documentation"],
        }
        name_lower = work_center_name.lower()
        for key, skills in skill_map.items():
            if key in name_lower:
                return skills
        return ["general_manufacturing"]

    def _calculate_skill_match(self, operator_skills: list[str], required_skills: list[str]) -> float:
        """Calculate skill match score."""
        if not required_skills:
            return 1.0
        matches = sum(1 for skill in required_skills if skill in operator_skills)
        return matches / len(required_skills)


class CrossFunctionalSynergyEngine:
    """In-memory Cross-Functional Synergy Engine for sync use cases and tests."""

    def __init__(self):
        self.department_events: dict[DepartmentType, list[dict[str, Any]]] = {
            dept: [] for dept in DepartmentType
        }
        self.silo_alerts: list[SiloAlert] = []
        self.work_centers: dict[str, WorkCenterLoad] = {}
        self.operators: dict[str, SkillProfile] = {}
        self.rebalance_suggestions: list[ResourceRebalance] = []

    def register_event(
        self,
        department: DepartmentType,
        event_type: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        data: dict[str, Any] | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        self.department_events.setdefault(department, []).append({
            "event_id": event_id,
            "type": event_type,
            "description": description,
            "severity": severity,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc),
        })
        self._check_cross_functional_impact_sync(department, event_type, description, severity)
        return event_id

    def _check_cross_functional_impact_sync(
        self,
        source_dept: DepartmentType,
        event_type: str,
        description: str,
        severity: AlertSeverity,
    ) -> None:
        impact_map: dict[DepartmentType, list[tuple[DepartmentType, str, str]]] = {
            DepartmentType.SALES: [
                (DepartmentType.PRODUCTION, "rfq_delay", "production bottleneck"),
                (DepartmentType.ENGINEERING, "new_product", "design capacity"),
            ],
            DepartmentType.PRODUCTION: [
                (DepartmentType.LOGISTICS, "delay", "shipping schedule"),
                (DepartmentType.QUALITY, "rush_order", "inspection backlog"),
            ],
            DepartmentType.QUALITY: [
                (DepartmentType.PRODUCTION, "hold", "line stoppage"),
                (DepartmentType.LOGISTICS, "reject", "return processing"),
            ],
            DepartmentType.LOGISTICS: [
                (DepartmentType.PRODUCTION, "material_delay", "production halt"),
            ],
            DepartmentType.ENGINEERING: [
                (DepartmentType.PRODUCTION, "design_change", "process update"),
            ],
            DepartmentType.MAINTENANCE: [
                (DepartmentType.PRODUCTION, "equipment_down", "capacity loss"),
            ],
        }

        if source_dept not in impact_map:
            return

        for affected_dept, trigger, impact in impact_map[source_dept]:
            if trigger in event_type.lower() or trigger in description.lower():
                alert = SiloAlert(
                    alert_id=str(uuid.uuid4()),
                    source_department=source_dept,
                    affected_department=affected_dept,
                    source_event=f"{event_type}: {description}",
                    predicted_impact=f"Potential {impact} in {affected_dept.value}",
                    severity=severity,
                    detected_at=datetime.now(timezone.utc),
                    owners_notified=[],
                    resolution_status="open",
                )
                self.silo_alerts.append(alert)
    
    def register_work_center(
        self,
        work_center_id: str,
        name: str,
        capacity: int,
        current_load: int,
        wip_count: int,
        operator_count: int,
    ) -> None:
        """Register a work center."""
        self.work_centers[work_center_id] = WorkCenterLoad(
            work_center_id=work_center_id,
            name=name,
            capacity=capacity,
            current_load=current_load,
            wip_count=wip_count,
            operator_count=operator_count,
        )
    
    def register_operator(
        self,
        operator_id: str,
        name: str,
        skills: dict[str, float],
        current_work_center: str,
        available: bool = True,
    ) -> None:
        """Register an operator skill profile."""
        self.operators[operator_id] = SkillProfile(
            operator_id=operator_id,
            name=name,
            skills=skills,
            current_work_center=current_work_center,
            available=available,
        )
    
    def analyze_resource_rebalancing(self, db: AsyncSession | None = None) -> list[ResourceRebalance]:
        """
        Analyze and suggest resource rebalancing.
        
        Suggests moving operators between Work Centers based on
        real-time Skill Gap Index and current WIP volume.
        """
        suggestions: list[ResourceRebalance] = []
        
        # Find overloaded and underloaded work centers
        overloaded = [
            wc for wc in self.work_centers.values()
            if wc.utilization > 0.9
        ]
        underloaded = [
            wc for wc in self.work_centers.values()
            if wc.utilization < 0.6
        ]
        
        if not overloaded or not underloaded:
            return suggestions
        
        for over_wc in overloaded:
            for under_wc in underloaded:
                # Find available operators in underloaded center
                available_operators = [
                    op for op in self.operators.values()
                    if op.current_work_center == under_wc.work_center_id
                    and op.available
                ]
                
                if not available_operators:
                    continue
                
                # Check skill match
                required_skills = self._infer_required_skills(over_wc.name)
                
                matching_operators: list[tuple[SkillProfile, float]] = []
                for op in available_operators:
                    match_score = self._calculate_skill_match(op.skills, required_skills)
                    if match_score >= 0.6:
                        matching_operators.append((op, match_score))
                
                if matching_operators:
                    # Take top matches
                    matching_operators.sort(key=lambda x: x[1], reverse=True)
                    top_matches = matching_operators[:2]
                    
                    avg_score = sum(m[1] for m in top_matches) / len(top_matches)
                    expected_improvement = min(
                        0.2,
                        (over_wc.utilization - 0.8) * len(top_matches) * 0.1
                    )
                    
                    suggestion = ResourceRebalance(
                        suggestion_id=str(uuid.uuid4()),
                        source_work_center=under_wc.work_center_id,
                        target_work_center=over_wc.work_center_id,
                        operator_ids=[m[0].operator_id for m in top_matches],
                        skill_match_score=avg_score,
                        reason=f"Rebalance from {under_wc.name} ({under_wc.utilization:.0%} util) "
                               f"to {over_wc.name} ({over_wc.utilization:.0%} util)",
                        expected_improvement=expected_improvement,
                        suggested_at=datetime.now(timezone.utc),
                    )
                    suggestions.append(suggestion)
        
        self.rebalance_suggestions.extend(suggestions)
        return suggestions
    
    def _infer_required_skills(self, work_center_name: str) -> dict[str, float]:
        """Infer required skills from work center name."""
        skill_map: dict[str, dict[str, float]] = {
            "assembly": {"assembly": 0.8, "quality_inspection": 0.5},
            "machining": {"cnc_operation": 0.9, "metrology": 0.6},
            "welding": {"welding": 0.9, "safety": 0.7},
            "painting": {"painting": 0.8, "surface_prep": 0.6},
            "packaging": {"packaging": 0.7, "forklift": 0.5},
        }
        
        for key, skills in skill_map.items():
            if key in work_center_name.lower():
                return skills
        
        return {"general": 0.5}
    
    def _calculate_skill_match(
        self,
        operator_skills: dict[str, float],
        required_skills: dict[str, float],
    ) -> float:
        """Calculate skill match score."""
        if not required_skills:
            return 0.5
        
        total_match = 0.0
        total_weight = 0.0
        
        for skill, required_level in required_skills.items():
            operator_level = operator_skills.get(skill, 0.0)
            match = min(1.0, operator_level / required_level) if required_level > 0 else 0.0
            total_match += match * required_level
            total_weight += required_level
        
        return total_match / total_weight if total_weight > 0 else 0.0
    
    def get_active_silo_alerts(self) -> list[SiloAlert]:
        """Get active silo alerts."""
        return [a for a in self.silo_alerts if a.resolution_status == "open"]
    
    def resolve_silo_alert(self, alert_id: str, resolution: str) -> bool:
        """Resolve a silo alert."""
        for alert in self.silo_alerts:
            if alert.alert_id == alert_id:
                alert.resolution_status = resolution
                return True
        return False
    
    def get_pending_rebalance_suggestions(self) -> list[ResourceRebalance]:
        """Get pending rebalance suggestions."""
        return [s for s in self.rebalance_suggestions if s.status == "pending"]


# =============================================================================
# AUTONOMOUS HEIJUNKA ADVISOR
# =============================================================================


class AsyncHeijunkaAdvisor:
    """
    Autonomous Heijunka (Leveling) Advisor.
    
    Analyzes production pipeline to suggest adjustments that minimize
    "Mura" (unevenness) in volume and mix.
    """
    
    def __init__(self):
        """Initialize advisor."""
        self.demand_data: dict[str, list[int]] = {}
        self.production_data: dict[str, list[int]] = {}
        self.suggestions: list[HeijunkaSuggestion] = []
    
    async def analyze_volume_leveling(self, db: AsyncSession, demand_data: dict[str, list[int]]) -> HeijunkaSuggestion | None:
        """
        Analyze and suggest volume leveling.
        
        Analyzes the RFQ pipeline to suggest adjustments to the production
        schedule to minimize "Mura" (Unevenness).
        """
        if not demand_data:
            return None
        
        # Calculate total daily demand variance
        all_daily_totals = []
        max_days = max(len(v) for v in demand_data.values())
        
        for day in range(max_days):
            daily_total = sum(
                data[day] if day < len(data) else 0
                for data in demand_data.values()
            )
            all_daily_totals.append(daily_total)
        
        if len(all_daily_totals) < 2:
            return None
        
        # Current variance
        current_variance = statistics.variance(all_daily_totals)
        
        # Suggest leveled production (moving average smoothing)
        suggested_totals = self._smooth_production(all_daily_totals)
        suggested_variance = statistics.variance(suggested_totals)
        
        mura_reduction = (
            (current_variance - suggested_variance) / current_variance * 100
            if current_variance > 0 else 0
        )
        
        if mura_reduction < 5:
            return None  # Not worth suggesting
        
        # Calculate suggested mix per product
        current_mix = {
            product: sum(quantities)
            for product, quantities in demand_data.items()
        }
        
        # Suggested: flatten to equal daily batches
        suggested_mix = {
            product: int(qty / max_days * max_days)  # Round to level batches
            for product, qty in current_mix.items()
        }
        
        suggestion_id = str(uuid.uuid4())
        record = HeijunkaSuggestionRecord(
            id=suggestion_id,
            period="weekly",
            current_mix=current_mix,
            suggested_mix=suggested_mix,
            mura_reduction=mura_reduction,
            volume_variance_before=current_variance,
            volume_variance_after=suggested_variance,
            suggested_at=datetime.now(timezone.utc),
            reasoning=f"Volume leveling can reduce production unevenness by {mura_reduction:.1f}%. "
                     f"Current daily variance: {current_variance:.0f}, "
                     f"Suggested variance: {suggested_variance:.0f}",
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        return self._record_to_suggestion(record)
    
    def _record_to_suggestion(self, r: HeijunkaSuggestionRecord) -> HeijunkaSuggestion:
        return HeijunkaSuggestion(
            suggestion_id=r.id,
            period=r.period,
            current_mix=r.current_mix,
            suggested_mix=r.suggested_mix,
            mura_reduction=r.mura_reduction,
            volume_variance_before=r.volume_variance_before,
            volume_variance_after=r.volume_variance_after,
            suggested_at=r.suggested_at,
            reasoning=r.reasoning,
        )

    async def get_all_suggestions(self, db: AsyncSession) -> list[HeijunkaSuggestion]:
        """Get all Heijunka suggestions."""
        result = await db.execute(select(HeijunkaSuggestionRecord).order_by(HeijunkaSuggestionRecord.suggested_at.desc()))
        return [self._record_to_suggestion(r) for r in result.scalars().all()]
    
    def _smooth_production(self, values: list[int]) -> list[float]:
        """Apply moving average smoothing."""
        window = min(3, len(values))
        smoothed = []
        
        for i in range(len(values)):
            start = max(0, i - window // 2)
            end = min(len(values), i + window // 2 + 1)
            avg = statistics.mean(values[start:end])
            smoothed.append(avg)
        
        return smoothed
    
    def analyze_mix_leveling(self) -> HeijunkaSuggestion | None:
        """
        Analyze and suggest mix leveling.
        
        Suggests spreading product variety evenly across production periods.
        """
        if len(self.demand_data) < 2:
            return None
        
        # Current: products may be batched (high variance in when they're made)
        # Suggested: interleave products more evenly
        
        current_mix = {
            product: sum(quantities)
            for product, quantities in self.demand_data.items()
        }
        
        total_qty = sum(current_mix.values())
        products = list(current_mix.keys())
        
        # Calculate ideal leveled sequence
        # For simplicity, suggest proportional distribution
        suggested_mix = {}
        for product, qty in current_mix.items():
            # Keep same total but suggest spreading
            suggested_mix[product] = qty
        
        # Calculate mix variance
        current_ratios = [q / total_qty for q in current_mix.values()]
        target_ratio = 1 / len(products)  # Ideal equal mix
        
        mix_variance_before = statistics.variance(current_ratios) if len(current_ratios) > 1 else 0
        mix_variance_after = 0  # Perfect leveling target
        
        mura_reduction = 100 * (1 - mix_variance_after / max(mix_variance_before, 0.01))
        
        if mix_variance_before < 0.01:
            return None  # Already well mixed
        
        suggestion = HeijunkaSuggestion(
            suggestion_id=str(uuid.uuid4()),
            period="daily",
            current_mix=current_mix,
            suggested_mix=suggested_mix,
            mura_reduction=mura_reduction,
            volume_variance_before=mix_variance_before * 1000,  # Scale for readability
            volume_variance_after=mix_variance_after,
            suggested_at=datetime.now(timezone.utc),
            reasoning=f"Mix leveling to reduce product variety unevenness. "
                     f"Spread {len(products)} products more evenly across production.",
        )
        
        self.suggestions.append(suggestion)
        return suggestion


class HeijunkaAdvisor:
    """In-memory Heijunka Advisor for sync use cases and tests."""

    def __init__(self):
        """Initialize advisor."""
        self.demand_data: dict[str, list[int]] = {}
        self.production_data: dict[str, list[int]] = {}
        self.suggestions: list[HeijunkaSuggestion] = []

    def get_all_suggestions(self) -> list[HeijunkaSuggestion]:
        """Get all Heijunka suggestions from in-memory store."""
        return self.suggestions
    
    def apply_suggestion(self, suggestion_id: str) -> bool:
        """Mark a suggestion as applied."""
        for suggestion in self.suggestions:
            if suggestion.suggestion_id == suggestion_id:
                suggestion.status = "applied"
                return True
        return False
    
    def dismiss_suggestion(self, suggestion_id: str, reason: str) -> bool:
        """Dismiss a suggestion."""
        for suggestion in self.suggestions:
            if suggestion.suggestion_id == suggestion_id:
                suggestion.status = f"dismissed: {reason}"
                return True
        return False

    def record_demand(self, product: str, quantities: list[int]) -> None:
        self.demand_data[product] = quantities

    def record_production(self, product: str, quantities: list[int]) -> None:
        self.production_data[product] = quantities

    def _smooth_production(self, values: list[int]) -> list[float]:
        """Apply moving average smoothing."""
        window = min(3, len(values))
        smoothed = []
        
        for i in range(len(values)):
            start = max(0, i - window // 2)
            end = min(len(values), i + window // 2 + 1)
            avg = statistics.mean(values[start:end])
            smoothed.append(avg)
        
        return smoothed

    def analyze_volume_leveling(self) -> HeijunkaSuggestion | None:
        demand_data = self.demand_data
        if not demand_data:
            return None

        all_daily_totals = []
        max_days = max(len(v) for v in demand_data.values())

        for day in range(max_days):
            daily_total = sum(
                data[day] if day < len(data) else 0
                for data in demand_data.values()
            )
            all_daily_totals.append(daily_total)

        if len(all_daily_totals) < 2:
            return None

        current_variance = statistics.variance(all_daily_totals)
        suggested_totals = self._smooth_production(all_daily_totals)
        suggested_variance = statistics.variance(suggested_totals)

        mura_reduction = (
            (current_variance - suggested_variance) / current_variance * 100
            if current_variance > 0 else 0
        )

        if mura_reduction < 5:
            return None

        current_mix = {
            product: sum(quantities)
            for product, quantities in demand_data.items()
        }
        suggested_mix = {
            product: int(qty / max_days * max_days)
            for product, qty in current_mix.items()
        }

        suggestion = HeijunkaSuggestion(
            suggestion_id=str(uuid.uuid4()),
            period="weekly",
            current_mix=current_mix,
            suggested_mix=suggested_mix,
            mura_reduction=mura_reduction,
            volume_variance_before=current_variance,
            volume_variance_after=suggested_variance,
            suggested_at=datetime.now(timezone.utc),
            reasoning=f"Volume leveling can reduce production unevenness by {mura_reduction:.1f}%. "
                     f"Current daily variance: {current_variance:.0f}, "
                     f"Suggested variance: {suggested_variance:.0f}",
        )

        self.suggestions.append(suggestion)
        return suggestion

    def analyze_mix_leveling(self) -> HeijunkaSuggestion | None:
        """
        Analyze and suggest mix leveling.
        
        Suggests spreading product variety evenly across production periods.
        """
        if len(self.demand_data) < 2:
            return None
        
        current_mix = {
            product: sum(quantities)
            for product, quantities in self.demand_data.items()
        }
        
        total_qty = sum(current_mix.values())
        products = list(current_mix.keys())
        
        suggested_mix = {product: qty for product, qty in current_mix.items()}
        
        current_ratios = [q / total_qty for q in current_mix.values()]
        
        mix_variance_before = statistics.variance(current_ratios) if len(current_ratios) > 1 else 0
        mix_variance_after = 0
        
        mura_reduction = 100 * (1 - mix_variance_after / max(mix_variance_before, 0.01))
        
        if mix_variance_before < 0.01:
            return None
        
        suggestion = HeijunkaSuggestion(
            suggestion_id=str(uuid.uuid4()),
            period="daily",
            current_mix=current_mix,
            suggested_mix=suggested_mix,
            mura_reduction=mura_reduction,
            volume_variance_before=mix_variance_before * 1000,
            volume_variance_after=mix_variance_after,
            suggested_at=datetime.now(timezone.utc),
            reasoning=f"Mix leveling to reduce product variety unevenness. "
                     f"Spread {len(products)} products more evenly across production.",
        )
        
        self.suggestions.append(suggestion)
        return suggestion


# =============================================================================
# COGNITIVE OBEYA ORCHESTRATOR
# =============================================================================


class AsyncCognitiveObeya:
    """
    Cognitive Obeya: The Organizational Brain.
    
    Orchestrates prescriptive metrics, cross-functional synergy,
    and Heijunka leveling.
    """
    
    def __init__(
        self,
        metric_analyzer: AsyncPrescriptiveMetricAnalyzer | None = None,
        synergy_engine: AsyncCrossFunctionalSynergyEngine | None = None,
        heijunka_advisor: AsyncHeijunkaAdvisor | None = None,
    ):
        """Initialize Cognitive Obeya."""
        self.metric_analyzer = metric_analyzer or AsyncPrescriptiveMetricAnalyzer()
        self.synergy_engine = synergy_engine or AsyncCrossFunctionalSynergyEngine()
        self.heijunka_advisor = heijunka_advisor or AsyncHeijunkaAdvisor()
    
    def _broadcast_update(self, type: str, payload: Any):
        """Broadcast an update via WebSocket."""
        manager = get_websocket_manager()
        # Use asyncio.create_task to not block the main thread if called from non-async context
        # (Though most of our endpoints are async)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast({"type": type, "payload": payload}))
        except Exception:
            logger.exception("Failed to broadcast Cognitive Obeya update")

    async def record_metric(
        self,
        db: AsyncSession,
        category: MetricCategory,
        name: str,
        value: float,
        target: float,
        unit: str = "",
    ) -> MetricValue:
        """Record a SQDCP metric."""
        metric = MetricValue(
            metric_id=f"{category.value}_{name}".replace(" ", "_").lower(),
            category=category,
            name=name,
            value=value,
            target=target,
            timestamp=datetime.now(timezone.utc),
            unit=unit,
        )
        await self.metric_analyzer.record_metric(db, metric)
        self._broadcast_update("metric_update", {
            "metric_id": metric.metric_id,
            "category": metric.category.value,
            "name": metric.name,
            "value": metric.value,
            "target": metric.target,
            "status": metric.status.value,
            "unit": metric.unit
        })
        return metric
    
    async def get_metric_insights(self, db: AsyncSession, metric_id: str) -> dict[str, Any]:
        """Get comprehensive insights for a metric."""
        causal_links = await self.metric_analyzer.find_causal_links(db, metric_id)
        trend_warning = await self.metric_analyzer.analyze_trend(db, metric_id)
        
        return {
            "metric_id": metric_id,
            "causal_links": [
                {
                    "source_type": link.source_type,
                    "source_id": link.source_id,
                    "description": link.source_description,
                    "confidence": link.confidence,
                    "explanation": link.explanation,
                }
                for link in causal_links
            ],
            "trend_warning": {
                "days_to_breach": trend_warning.days_to_breach,
                "confidence": trend_warning.confidence,
                "recommendation": trend_warning.recommendation,
            } if trend_warning else None,
        }
    
    async def register_cross_functional_event(
        self,
        db: AsyncSession,
        department: DepartmentType,
        event_type: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> str:
        """Register an event and check for cross-functional impact."""
        event_id = await self.synergy_engine.register_event(
            db,
            department,
            event_type,
            description,
            severity,
        )
        self._broadcast_update("silo_alert", {
            "event_id": event_id,
            "department": department.value,
            "event_type": event_type,
            "description": description,
            "severity": severity.value
        })
        return event_id
    
    async def get_silo_alerts(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Get active silo-busting alerts."""
        alerts = await self.synergy_engine.get_silo_alerts(db)
        return [
            {
                "alert_id": a.alert_id,
                "source": a.source_department.value,
                "affected": a.affected_department.value,
                "event": a.source_event,
                "impact": a.predicted_impact,
                "severity": a.severity.value,
                "detected_at": a.detected_at.isoformat(),
            }
            for a in alerts
        ]
    
    async def analyze_resource_rebalancing(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Analyze and get resource rebalancing suggestions."""
        suggestions = self.synergy_engine.analyze_resource_rebalancing(db)
        if asyncio.iscoroutine(suggestions):
            suggestions = await suggestions
        return [
            {
                "suggestion_id": s.suggestion_id,
                "from_work_center": s.source_work_center,
                "to_work_center": s.target_work_center,
                "operators": s.operator_ids,
                "skill_match": s.skill_match_score,
                "reason": s.reason,
                "expected_improvement": s.expected_improvement,
            }
            for s in suggestions
        ]
    
    async def get_heijunka_suggestions(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Get Heijunka leveling suggestions."""
        # Note: analyze_volume_leveling requires demand_data, 
        # normally fetched from RFQ service. Using empty for auto-trigger check.
        suggestions = await self.heijunka_advisor.get_all_suggestions(db)
        return [
            {
                "suggestion_id": s.suggestion_id,
                "period": s.period,
                "current_mix": s.current_mix,
                "suggested_mix": s.suggested_mix,
                "mura_reduction": s.mura_reduction,
                "reasoning": s.reasoning,
                "status": s.status,
            }
            for s in suggestions
            if s.status == "pending"
        ]
    
    async def get_obeya_dashboard(self, db: AsyncSession) -> dict[str, Any]:
        """Get comprehensive Obeya dashboard data."""
        from sqlalchemy import func
        
        # Count metrics
        metric_count_stmt = select(func.count(MetricRecord.id))
        metric_count = (await db.execute(metric_count_stmt)).scalar() or 0
        
        # Count active silo alerts
        silo_count_stmt = select(func.count(SiloAlertRecord.id)).where(SiloAlertRecord.resolution_status == "open")
        silo_count = (await db.execute(silo_count_stmt)).scalar() or 0
        
        # Count pending heijunka suggestions
        heijunka_count_stmt = select(func.count(HeijunkaSuggestionRecord.id)).where(HeijunkaSuggestionRecord.status == "pending")
        heijunka_count = (await db.execute(heijunka_count_stmt)).scalar() or 0
        
        # Count active trend warnings (within last 14 days and not resolved)
        warning_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        warning_count_stmt = select(func.count(TrendWarningRecord.id)).where(
            TrendWarningRecord.detected_at > warning_cutoff
        )
        warning_count = (await db.execute(warning_count_stmt)).scalar() or 0
        
        return {
            "metrics": {
                "total_recorded": metric_count,
                "active_trend_warnings": warning_count,
            },
            "cross_functional": {
                "active_silo_alerts": silo_count,
            },
            "heijunka": {
                "pending_suggestions": heijunka_count,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class CognitiveObeya:
    """Sync Cognitive Obeya orchestrator for in-memory workflows and tests."""

    def __init__(
        self,
        metric_analyzer: PrescriptiveMetricAnalyzer | None = None,
        synergy_engine: CrossFunctionalSynergyEngine | None = None,
        heijunka_advisor: HeijunkaAdvisor | None = None,
    ):
        self.metric_analyzer = metric_analyzer or PrescriptiveMetricAnalyzer()
        self.synergy_engine = synergy_engine or CrossFunctionalSynergyEngine()
        self.heijunka_advisor = heijunka_advisor or HeijunkaAdvisor()

    def record_metric(
        self,
        category: MetricCategory,
        name: str,
        value: float,
        target: float,
        unit: str = "",
    ) -> MetricValue:
        metric = MetricValue(
            metric_id=f"{category.value}_{name}".replace(" ", "_").lower(),
            category=category,
            name=name,
            value=value,
            target=target,
            timestamp=datetime.now(timezone.utc),
            unit=unit,
        )
        self.metric_analyzer.record_metric(metric)
        return metric

    def get_metric_insights(self, metric_id: str) -> dict[str, Any]:
        causal_links = self.metric_analyzer.find_causal_links(metric_id)
        trend_warning = self.metric_analyzer.analyze_trend(metric_id)

        return {
            "metric_id": metric_id,
            "causal_links": causal_links,
            "trend_warning": trend_warning,
        }

    def register_cross_functional_event(
        self,
        department: DepartmentType,
        event_type: str,
        description: str,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> str:
        return self.synergy_engine.register_event(
            department,
            event_type,
            description,
            severity,
        )

    def get_silo_alerts(self) -> list[dict[str, Any]]:
        alerts = self.synergy_engine.get_active_silo_alerts()
        return [
            {
                "alert_id": a.alert_id,
                "source": a.source_department.value,
                "affected": a.affected_department.value,
                "event": a.source_event,
                "impact": a.predicted_impact,
                "severity": a.severity.value,
                "detected_at": a.detected_at.isoformat(),
            }
            for a in alerts
        ]

    def analyze_resource_rebalancing(self, db: AsyncSession | None = None) -> list[ResourceRebalance]:
        return self.synergy_engine.analyze_resource_rebalancing()

    def get_heijunka_suggestions(self) -> list[HeijunkaSuggestion]:
        pending = [s for s in self.heijunka_advisor.get_all_suggestions() if s.status == "pending"]
        if pending:
            return pending

        suggestion = self.heijunka_advisor.analyze_volume_leveling()
        if suggestion:
            return [suggestion]

        suggestion = self.heijunka_advisor.analyze_mix_leveling()
        if suggestion:
            return [suggestion]

        return []

    def get_obeya_dashboard(self) -> dict[str, Any]:
        return {
            "metrics": {
                "total_recorded": sum(len(v) for v in self.metric_analyzer.metrics_history.values()),
                "total_tracked": len(self.metric_analyzer.metrics_history),
                "active_trend_warnings": 0,
            },
            "cross_functional": {
                "active_silo_alerts": len(self.synergy_engine.get_active_silo_alerts()),
                "active_alerts": len(self.synergy_engine.get_active_silo_alerts()),
            },
            "heijunka": {
                "pending_suggestions": len(self.get_heijunka_suggestions()),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# SINGLETON & FACTORY FUNCTIONS
# =============================================================================


_cognitive_obeya: AsyncCognitiveObeya | None = None


def get_cognitive_obeya() -> AsyncCognitiveObeya:
    """Get the Cognitive Obeya singleton."""
    global _cognitive_obeya
    if _cognitive_obeya is None:
        _cognitive_obeya = AsyncCognitiveObeya()
    return _cognitive_obeya


def create_cognitive_obeya() -> CognitiveObeya:
    """Create the Cognitive Obeya orchestrator (for testing)."""
    return CognitiveObeya()


def create_metric_analyzer() -> PrescriptiveMetricAnalyzer:
    """Create prescriptive metric analyzer."""
    return PrescriptiveMetricAnalyzer()


def create_synergy_engine() -> CrossFunctionalSynergyEngine:
    """Create cross-functional synergy engine."""
    return CrossFunctionalSynergyEngine()


def create_heijunka_advisor() -> HeijunkaAdvisor:
    """Create Heijunka advisor."""
    return HeijunkaAdvisor()
