"""
KPI Metric Sources Configuration Service.

Defines exactly which events and fields power each KPI metric.
Provides mapping between raw data sources and computed metrics.

Features:
- Metric source definitions
- Field-to-KPI mappings
- Event-to-metric mappings
- Computation formulas
- Data freshness tracking
- Metric validation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable
from uuid import UUID, uuid4


class MetricType(str, Enum):
    """Types of metrics."""

    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    DURATION = "duration"
    RATE = "rate"
    TREND = "trend"


class DataSourceType(str, Enum):
    """Types of data sources."""

    TABLE = "table"
    EVENT = "event"
    COMPUTED = "computed"
    AGGREGATE = "aggregate"
    EXTERNAL = "external"


class AggregationPeriod(str, Enum):
    """Time periods for aggregation."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ROLLING_7D = "rolling_7d"
    ROLLING_30D = "rolling_30d"
    ROLLING_90D = "rolling_90d"


class MetricCategory(str, Enum):
    """Categories of metrics."""

    RFQ = "rfq"
    QUOTE = "quote"
    QUALIFICATION = "qualification"
    SALES = "sales"
    PRODUCTION = "production"
    QUALITY = "quality"
    TRAINING = "training"
    CADENCE = "cadence"
    KNOWLEDGE = "knowledge"
    ANDON = "andon"
    DELIVERY = "delivery"
    COST = "cost"


@dataclass
class FieldSource:
    """A field that contributes to a metric."""

    table: str
    field: str
    description: str
    data_type: str  # integer, float, datetime, string, boolean
    nullable: bool = False
    transform: str | None = None  # Optional transformation (e.g., "date_diff", "count_distinct")


@dataclass
class EventSource:
    """An event that triggers metric updates."""

    event_name: str
    description: str
    payload_fields: list[str]
    timestamp_field: str = "created_at"


@dataclass
class ComputationFormula:
    """Formula for computing a metric."""

    formula: str
    description: str
    inputs: list[str]
    output_type: str


@dataclass
class MetricDefinition:
    """Complete definition of a KPI metric."""

    id: UUID
    name: str
    code: str
    description: str
    category: MetricCategory
    metric_type: MetricType
    unit: str
    field_sources: list[FieldSource]
    event_sources: list[EventSource]
    computation: ComputationFormula
    aggregation_period: AggregationPeriod
    target_value: float | None = None
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    is_higher_better: bool = True
    is_active: bool = True
    refresh_interval_minutes: int = 60
    last_computed: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MetricValue:
    """A computed metric value."""

    metric_id: UUID
    metric_code: str
    value: float
    unit: str
    period_start: datetime
    period_end: datetime
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_data: dict[str, Any] | None = None
    status: str = "normal"  # normal, warning, critical


@dataclass
class MetricTrend:
    """Trend information for a metric."""

    metric_id: UUID
    current_value: float
    previous_value: float
    change_absolute: float
    change_percentage: float
    direction: str  # up, down, stable
    is_improving: bool


class KPIMetricSourcesService:
    """
    Service for managing KPI metric source configurations.

    Defines the mapping between raw data sources and computed metrics,
    enabling transparent understanding of what powers each KPI.
    """

    def __init__(self) -> None:
        """Initialize the KPI Metric Sources service."""
        self._metrics: dict[UUID, MetricDefinition] = {}
        self._values: dict[UUID, list[MetricValue]] = {}
        self._custom_computations: dict[str, Callable[..., float]] = {}

        self._setup_default_metrics()

    def _setup_default_metrics(self) -> None:
        """Set up default metric definitions."""
        default_metrics = [
            # RFQ Completeness
            MetricDefinition(
                id=uuid4(),
                name="RFQ Completeness Score",
                code="rfq-completeness",
                description="Average completeness score of RFQs at submission",
                category=MetricCategory.RFQ,
                metric_type=MetricType.AVERAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="rfq",
                        field="completeness_score",
                        description="Calculated completeness score (0-100)",
                        data_type="float",
                    ),
                    FieldSource(
                        table="rfq",
                        field="status",
                        description="RFQ status to filter submitted RFQs",
                        data_type="string",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="rfq.submitted",
                        description="Triggered when RFQ is submitted for qualification",
                        payload_fields=["rfq_id", "completeness_score"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="AVG(completeness_score) WHERE status != 'draft'",
                    description="Average completeness score of non-draft RFQs",
                    inputs=["completeness_score", "status"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.WEEKLY,
                target_value=85.0,
                warning_threshold=70.0,
                critical_threshold=50.0,
                is_higher_better=True,
            ),
            # Qualification Discipline
            MetricDefinition(
                id=uuid4(),
                name="Qualification Discipline",
                code="qual-discipline",
                description="Percentage of qualifications completed with rationale",
                category=MetricCategory.QUALIFICATION,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="qualification",
                        field="rationale",
                        description="Qualification decision rationale",
                        data_type="string",
                        nullable=True,
                    ),
                    FieldSource(
                        table="qualification",
                        field="decision",
                        description="Qualification decision (quote/no_quote/conditional)",
                        data_type="string",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="qualification.completed",
                        description="Triggered when qualification decision is made",
                        payload_fields=["qualification_id", "decision", "has_rationale"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(rationale IS NOT NULL) / COUNT(*) * 100",
                    description="Percentage of qualifications with documented rationale",
                    inputs=["rationale"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.WEEKLY,
                target_value=100.0,
                warning_threshold=90.0,
                critical_threshold=75.0,
                is_higher_better=True,
            ),
            # Quote Cycle Time
            MetricDefinition(
                id=uuid4(),
                name="Quote Cycle Time",
                code="quote-cycle-time",
                description="Average time from RFQ creation to quote release",
                category=MetricCategory.QUOTE,
                metric_type=MetricType.DURATION,
                unit="days",
                field_sources=[
                    FieldSource(
                        table="rfq",
                        field="created_at",
                        description="RFQ creation timestamp",
                        data_type="datetime",
                    ),
                    FieldSource(
                        table="quote",
                        field="released_at",
                        description="Quote release timestamp",
                        data_type="datetime",
                        nullable=True,
                    ),
                    FieldSource(
                        table="quote",
                        field="rfq_id",
                        description="Link to originating RFQ",
                        data_type="uuid",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="quote.released",
                        description="Triggered when quote is released to customer",
                        payload_fields=["quote_id", "rfq_id", "released_at"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="AVG(quote.released_at - rfq.created_at)",
                    description="Average days from RFQ creation to quote release",
                    inputs=["rfq.created_at", "quote.released_at"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.MONTHLY,
                target_value=5.0,
                warning_threshold=7.0,
                critical_threshold=14.0,
                is_higher_better=False,
            ),
            # Quote Revision Rate
            MetricDefinition(
                id=uuid4(),
                name="Quote Revision Rate",
                code="quote-revision-rate",
                description="Average number of revisions per quote before release",
                category=MetricCategory.QUOTE,
                metric_type=MetricType.AVERAGE,
                unit="revisions",
                field_sources=[
                    FieldSource(
                        table="quote_version",
                        field="version_number",
                        description="Quote version number",
                        data_type="integer",
                    ),
                    FieldSource(
                        table="quote",
                        field="id",
                        description="Quote ID for grouping",
                        data_type="uuid",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="quote.version_created",
                        description="Triggered when a new quote version is created",
                        payload_fields=["quote_id", "version_number"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="AVG(MAX(version_number) GROUP BY quote_id)",
                    description="Average maximum version number per quote",
                    inputs=["version_number", "quote_id"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.MONTHLY,
                target_value=1.5,
                warning_threshold=2.5,
                critical_threshold=4.0,
                is_higher_better=False,
            ),
            # Margin Protection
            MetricDefinition(
                id=uuid4(),
                name="Margin Protection",
                code="margin-protection",
                description="Percentage of quotes meeting margin threshold",
                category=MetricCategory.QUOTE,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="quote",
                        field="margin_percentage",
                        description="Quote margin percentage",
                        data_type="float",
                    ),
                    FieldSource(
                        table="quote",
                        field="status",
                        description="Quote status (filter to released)",
                        data_type="string",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="quote.released",
                        description="Triggered when quote is released",
                        payload_fields=["quote_id", "margin_percentage"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(margin_percentage >= 15) / COUNT(*) * 100",
                    description="Percentage of quotes with margin >= 15%",
                    inputs=["margin_percentage"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.MONTHLY,
                target_value=95.0,
                warning_threshold=85.0,
                critical_threshold=70.0,
                is_higher_better=True,
            ),
            # Win Rate
            MetricDefinition(
                id=uuid4(),
                name="Win Rate",
                code="win-rate",
                description="Percentage of quotes resulting in won opportunities",
                category=MetricCategory.SALES,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="opportunity",
                        field="stage",
                        description="Opportunity stage (won/lost/open)",
                        data_type="string",
                    ),
                    FieldSource(
                        table="quote",
                        field="opportunity_id",
                        description="Link to opportunity",
                        data_type="uuid",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="opportunity.won",
                        description="Triggered when opportunity is marked as won",
                        payload_fields=["opportunity_id", "value"],
                    ),
                    EventSource(
                        event_name="opportunity.lost",
                        description="Triggered when opportunity is marked as lost",
                        payload_fields=["opportunity_id", "lost_reason"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(stage = 'won') / COUNT(stage IN ('won', 'lost')) * 100",
                    description="Percentage of closed opportunities that were won",
                    inputs=["stage"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.QUARTERLY,
                target_value=40.0,
                warning_threshold=30.0,
                critical_threshold=20.0,
                is_higher_better=True,
            ),
            # Bad Win Rate
            MetricDefinition(
                id=uuid4(),
                name="Bad Win Rate",
                code="bad-win-rate",
                description="Percentage of won deals with issues (margin below target or quality issues)",
                category=MetricCategory.SALES,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="opportunity",
                        field="stage",
                        description="Opportunity stage",
                        data_type="string",
                    ),
                    FieldSource(
                        table="quote",
                        field="margin_percentage",
                        description="Final quote margin",
                        data_type="float",
                    ),
                    FieldSource(
                        table="non_conformance",
                        field="opportunity_id",
                        description="NCs linked to opportunity",
                        data_type="uuid",
                        nullable=True,
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="opportunity.won",
                        description="Triggered when opportunity is won",
                        payload_fields=["opportunity_id", "margin_percentage"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(stage = 'won' AND (margin < 10 OR has_nc)) / COUNT(stage = 'won') * 100",
                    description="Percentage of won deals with issues",
                    inputs=["stage", "margin_percentage", "has_nc"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.QUARTERLY,
                target_value=5.0,
                warning_threshold=10.0,
                critical_threshold=20.0,
                is_higher_better=False,
            ),
            # Cadence Adherence
            MetricDefinition(
                id=uuid4(),
                name="Cadence Adherence",
                code="cadence-adherence",
                description="Percentage of LSW items completed on time",
                category=MetricCategory.CADENCE,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="lsw_checklist_item",
                        field="status",
                        description="Checklist item status",
                        data_type="string",
                    ),
                    FieldSource(
                        table="lsw_checklist_item",
                        field="due_date",
                        description="Item due date",
                        data_type="datetime",
                    ),
                    FieldSource(
                        table="lsw_checklist_item",
                        field="completed_at",
                        description="Item completion timestamp",
                        data_type="datetime",
                        nullable=True,
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="lsw.item_completed",
                        description="Triggered when LSW item is completed",
                        payload_fields=["item_id", "completed_at", "was_on_time"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(completed_at <= due_date) / COUNT(completed_at IS NOT NULL) * 100",
                    description="Percentage of completed items that were on time",
                    inputs=["completed_at", "due_date"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.WEEKLY,
                target_value=95.0,
                warning_threshold=80.0,
                critical_threshold=60.0,
                is_higher_better=True,
            ),
            # Knowledge Capture Rate
            MetricDefinition(
                id=uuid4(),
                name="Knowledge Capture Rate",
                code="knowledge-capture",
                description="Rate of learning reflections captured per closed A3",
                category=MetricCategory.KNOWLEDGE,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="a3",
                        field="status",
                        description="A3 status",
                        data_type="string",
                    ),
                    FieldSource(
                        table="a3",
                        field="reflection",
                        description="A3 reflection/lessons learned",
                        data_type="string",
                        nullable=True,
                    ),
                    FieldSource(
                        table="a3",
                        field="standard_update",
                        description="Standard work update reference",
                        data_type="string",
                        nullable=True,
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="a3.closed",
                        description="Triggered when A3 is closed",
                        payload_fields=["a3_id", "has_reflection", "has_standard_update"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(reflection IS NOT NULL AND standard_update IS NOT NULL) / COUNT(status = 'closed') * 100",
                    description="Percentage of closed A3s with reflection and standard update",
                    inputs=["reflection", "standard_update", "status"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.MONTHLY,
                target_value=100.0,
                warning_threshold=85.0,
                critical_threshold=70.0,
                is_higher_better=True,
            ),
            # Andon MTTR
            MetricDefinition(
                id=uuid4(),
                name="Andon MTTR",
                code="andon-mttr",
                description="Mean time to resolution for Andon events",
                category=MetricCategory.ANDON,
                metric_type=MetricType.DURATION,
                unit="minutes",
                field_sources=[
                    FieldSource(
                        table="andon_event",
                        field="reported_at",
                        description="When Andon was triggered",
                        data_type="datetime",
                    ),
                    FieldSource(
                        table="andon_event",
                        field="resolved_at",
                        description="When Andon was resolved",
                        data_type="datetime",
                        nullable=True,
                    ),
                    FieldSource(
                        table="andon_event",
                        field="severity",
                        description="Andon severity (yellow/red)",
                        data_type="string",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="andon.resolved",
                        description="Triggered when Andon is resolved",
                        payload_fields=["event_id", "resolution_time_minutes"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="AVG(resolved_at - reported_at) IN MINUTES",
                    description="Average resolution time in minutes",
                    inputs=["reported_at", "resolved_at"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.WEEKLY,
                target_value=30.0,
                warning_threshold=60.0,
                critical_threshold=120.0,
                is_higher_better=False,
            ),
            # First Pass Yield
            MetricDefinition(
                id=uuid4(),
                name="First Pass Yield",
                code="first-pass-yield",
                description="Percentage of units passing inspection on first attempt",
                category=MetricCategory.QUALITY,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="inspection_record",
                        field="overall_result",
                        description="Inspection result (pass/fail)",
                        data_type="string",
                    ),
                    FieldSource(
                        table="inspection_record",
                        field="is_reinspection",
                        description="Whether this is a reinspection",
                        data_type="boolean",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="inspection.completed",
                        description="Triggered when inspection is completed",
                        payload_fields=["record_id", "result", "is_reinspection"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(result = 'pass' AND is_reinspection = false) / COUNT(is_reinspection = false) * 100",
                    description="Percentage of first-time inspections that pass",
                    inputs=["result", "is_reinspection"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.WEEKLY,
                target_value=98.0,
                warning_threshold=95.0,
                critical_threshold=90.0,
                is_higher_better=True,
            ),
            # Training Compliance
            MetricDefinition(
                id=uuid4(),
                name="Training Compliance",
                code="training-compliance",
                description="Percentage of required certifications that are current",
                category=MetricCategory.TRAINING,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="user_skill",
                        field="certification_status",
                        description="Certification status",
                        data_type="string",
                    ),
                    FieldSource(
                        table="user_skill",
                        field="expiration_date",
                        description="Certification expiration date",
                        data_type="datetime",
                        nullable=True,
                    ),
                    FieldSource(
                        table="skill_requirement",
                        field="is_mandatory",
                        description="Whether skill is mandatory",
                        data_type="boolean",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="certification.expired",
                        description="Triggered when a certification expires",
                        payload_fields=["user_id", "skill_id"],
                    ),
                    EventSource(
                        event_name="certification.renewed",
                        description="Triggered when certification is renewed",
                        payload_fields=["user_id", "skill_id", "new_expiry"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(status = 'certified' AND expiry > now()) / COUNT(is_mandatory = true) * 100",
                    description="Percentage of mandatory certifications that are current",
                    inputs=["certification_status", "expiration_date", "is_mandatory"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.MONTHLY,
                target_value=100.0,
                warning_threshold=95.0,
                critical_threshold=85.0,
                is_higher_better=True,
            ),
            # CAPA Closure Rate
            MetricDefinition(
                id=uuid4(),
                name="CAPA Closure Rate",
                code="capa-closure-rate",
                description="Percentage of CAPAs closed on time",
                category=MetricCategory.QUALITY,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="capa",
                        field="status",
                        description="CAPA status",
                        data_type="string",
                    ),
                    FieldSource(
                        table="capa",
                        field="due_date",
                        description="CAPA due date",
                        data_type="datetime",
                    ),
                    FieldSource(
                        table="capa",
                        field="closed_at",
                        description="CAPA closure timestamp",
                        data_type="datetime",
                        nullable=True,
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="capa.closed",
                        description="Triggered when CAPA is closed",
                        payload_fields=["capa_id", "was_on_time"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="COUNT(closed_at <= due_date) / COUNT(status = 'closed') * 100",
                    description="Percentage of closed CAPAs that were on time",
                    inputs=["closed_at", "due_date", "status"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.MONTHLY,
                target_value=95.0,
                warning_threshold=85.0,
                critical_threshold=70.0,
                is_higher_better=True,
            ),
            # OEE
            MetricDefinition(
                id=uuid4(),
                name="Overall Equipment Effectiveness",
                code="oee",
                description="OEE = Availability × Performance × Quality",
                category=MetricCategory.PRODUCTION,
                metric_type=MetricType.PERCENTAGE,
                unit="percent",
                field_sources=[
                    FieldSource(
                        table="cell_performance",
                        field="availability_percentage",
                        description="Equipment availability",
                        data_type="float",
                    ),
                    FieldSource(
                        table="cell_performance",
                        field="performance_percentage",
                        description="Performance efficiency",
                        data_type="float",
                    ),
                    FieldSource(
                        table="cell_performance",
                        field="quality_percentage",
                        description="Quality rate",
                        data_type="float",
                    ),
                ],
                event_sources=[
                    EventSource(
                        event_name="shift.completed",
                        description="Triggered when a shift ends",
                        payload_fields=["cell_id", "shift_id", "oee"],
                    ),
                ],
                computation=ComputationFormula(
                    formula="AVG(availability * performance * quality / 10000)",
                    description="Average OEE across production cells",
                    inputs=["availability_percentage", "performance_percentage", "quality_percentage"],
                    output_type="float",
                ),
                aggregation_period=AggregationPeriod.WEEKLY,
                target_value=85.0,
                warning_threshold=75.0,
                critical_threshold=60.0,
                is_higher_better=True,
            ),
        ]

        for metric in default_metrics:
            self._metrics[metric.id] = metric

    def create_metric(
        self,
        name: str,
        code: str,
        description: str,
        category: MetricCategory,
        metric_type: MetricType,
        unit: str,
        field_sources: list[FieldSource],
        event_sources: list[EventSource],
        computation: ComputationFormula,
        aggregation_period: AggregationPeriod,
        target_value: float | None = None,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        is_higher_better: bool = True,
    ) -> MetricDefinition:
        """Create a new metric definition."""
        metric = MetricDefinition(
            id=uuid4(),
            name=name,
            code=code,
            description=description,
            category=category,
            metric_type=metric_type,
            unit=unit,
            field_sources=field_sources,
            event_sources=event_sources,
            computation=computation,
            aggregation_period=aggregation_period,
            target_value=target_value,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            is_higher_better=is_higher_better,
        )
        self._metrics[metric.id] = metric
        return metric

    def get_metric(self, metric_id: UUID) -> MetricDefinition | None:
        """Get a metric by ID."""
        return self._metrics.get(metric_id)

    def get_metric_by_code(self, code: str) -> MetricDefinition | None:
        """Get a metric by code."""
        for metric in self._metrics.values():
            if metric.code == code:
                return metric
        return None

    def get_metrics(
        self,
        category: MetricCategory | None = None,
        metric_type: MetricType | None = None,
        active_only: bool = True,
    ) -> list[MetricDefinition]:
        """Get metrics matching filters."""
        metrics = list(self._metrics.values())

        if category:
            metrics = [m for m in metrics if m.category == category]

        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]

        if active_only:
            metrics = [m for m in metrics if m.is_active]

        return sorted(metrics, key=lambda m: (m.category.value, m.name))

    def update_metric(
        self,
        metric_id: UUID,
        **updates: Any,
    ) -> MetricDefinition | None:
        """Update a metric definition."""
        metric = self._metrics.get(metric_id)
        if not metric:
            return None

        for key, value in updates.items():
            if hasattr(metric, key):
                setattr(metric, key, value)

        return metric

    def delete_metric(self, metric_id: UUID) -> bool:
        """Delete a metric."""
        if metric_id in self._metrics:
            del self._metrics[metric_id]
            return True
        return False

    def deactivate_metric(self, metric_id: UUID) -> MetricDefinition | None:
        """Deactivate a metric."""
        metric = self._metrics.get(metric_id)
        if metric:
            metric.is_active = False
        return metric

    def activate_metric(self, metric_id: UUID) -> MetricDefinition | None:
        """Activate a metric."""
        metric = self._metrics.get(metric_id)
        if metric:
            metric.is_active = True
        return metric

    def get_field_sources(self, metric_id: UUID) -> list[FieldSource]:
        """Get field sources for a metric."""
        metric = self._metrics.get(metric_id)
        return metric.field_sources if metric else []

    def get_event_sources(self, metric_id: UUID) -> list[EventSource]:
        """Get event sources for a metric."""
        metric = self._metrics.get(metric_id)
        return metric.event_sources if metric else []

    def record_value(
        self,
        metric_code: str,
        value: float,
        period_start: datetime,
        period_end: datetime,
        raw_data: dict[str, Any] | None = None,
    ) -> MetricValue | None:
        """Record a computed metric value."""
        metric = self.get_metric_by_code(metric_code)
        if not metric:
            return None

        # Determine status based on thresholds
        status = "normal"
        if metric.warning_threshold is not None and metric.critical_threshold is not None:
            if metric.is_higher_better:
                if value < metric.critical_threshold:
                    status = "critical"
                elif value < metric.warning_threshold:
                    status = "warning"
            else:
                if value > metric.critical_threshold:
                    status = "critical"
                elif value > metric.warning_threshold:
                    status = "warning"

        metric_value = MetricValue(
            metric_id=metric.id,
            metric_code=metric_code,
            value=value,
            unit=metric.unit,
            period_start=period_start,
            period_end=period_end,
            raw_data=raw_data,
            status=status,
        )

        if metric.id not in self._values:
            self._values[metric.id] = []
        self._values[metric.id].append(metric_value)

        # Update last computed timestamp
        metric.last_computed = datetime.now(timezone.utc)

        return metric_value

    def get_values(
        self,
        metric_code: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
    ) -> list[MetricValue]:
        """Get recorded values for a metric."""
        metric = self.get_metric_by_code(metric_code)
        if not metric:
            return []

        values = self._values.get(metric.id, [])

        if start_date:
            values = [v for v in values if v.period_start >= start_date]

        if end_date:
            values = [v for v in values if v.period_end <= end_date]

        values = sorted(values, key=lambda v: v.period_end, reverse=True)

        if limit:
            values = values[:limit]

        return values

    def get_latest_value(self, metric_code: str) -> MetricValue | None:
        """Get the most recent value for a metric."""
        values = self.get_values(metric_code, limit=1)
        return values[0] if values else None

    def calculate_trend(self, metric_code: str) -> MetricTrend | None:
        """Calculate trend for a metric based on recent values."""
        metric = self.get_metric_by_code(metric_code)
        if not metric:
            return None

        values = self.get_values(metric_code, limit=2)
        if len(values) < 2:
            return None

        current = values[0].value
        previous = values[1].value

        change_absolute = current - previous
        change_percentage = ((current - previous) / previous * 100) if previous != 0 else 0

        if abs(change_percentage) < 1:
            direction = "stable"
        elif change_absolute > 0:
            direction = "up"
        else:
            direction = "down"

        # Determine if improving based on whether higher is better
        is_improving = (
            (direction == "up" and metric.is_higher_better) or
            (direction == "down" and not metric.is_higher_better)
        )

        return MetricTrend(
            metric_id=metric.id,
            current_value=current,
            previous_value=previous,
            change_absolute=change_absolute,
            change_percentage=change_percentage,
            direction=direction,
            is_improving=is_improving,
        )

    def get_metrics_needing_refresh(self) -> list[MetricDefinition]:
        """Get metrics that need to be refreshed based on their interval."""
        now = datetime.now(timezone.utc)
        needing_refresh = []

        for metric in self._metrics.values():
            if not metric.is_active:
                continue

            if metric.last_computed is None:
                needing_refresh.append(metric)
            else:
                age = now - metric.last_computed
                if age > timedelta(minutes=metric.refresh_interval_minutes):
                    needing_refresh.append(metric)

        return needing_refresh

    def get_source_documentation(self, metric_code: str) -> dict[str, Any]:
        """Get complete source documentation for a metric."""
        metric = self.get_metric_by_code(metric_code)
        if not metric:
            return {}

        return {
            "metric": {
                "code": metric.code,
                "name": metric.name,
                "description": metric.description,
                "category": metric.category.value,
                "type": metric.metric_type.value,
                "unit": metric.unit,
            },
            "field_sources": [
                {
                    "table": fs.table,
                    "field": fs.field,
                    "description": fs.description,
                    "data_type": fs.data_type,
                    "nullable": fs.nullable,
                    "transform": fs.transform,
                }
                for fs in metric.field_sources
            ],
            "event_sources": [
                {
                    "event": es.event_name,
                    "description": es.description,
                    "payload_fields": es.payload_fields,
                }
                for es in metric.event_sources
            ],
            "computation": {
                "formula": metric.computation.formula,
                "description": metric.computation.description,
                "inputs": metric.computation.inputs,
            },
            "thresholds": {
                "target": metric.target_value,
                "warning": metric.warning_threshold,
                "critical": metric.critical_threshold,
                "is_higher_better": metric.is_higher_better,
            },
        }

    def validate_metric_sources(self, metric_id: UUID) -> list[str]:
        """Validate that a metric's sources are properly configured."""
        metric = self._metrics.get(metric_id)
        if not metric:
            return ["Metric not found"]

        issues = []

        # Check field sources
        if not metric.field_sources:
            issues.append("No field sources defined")
        else:
            for fs in metric.field_sources:
                if not fs.table:
                    issues.append(f"Field source missing table: {fs.field}")
                if not fs.field:
                    issues.append(f"Field source missing field name")

        # Check computation
        if not metric.computation.formula:
            issues.append("Computation formula is empty")

        # Check computation inputs match field sources
        source_fields = {f"{fs.table}.{fs.field}" for fs in metric.field_sources}
        source_fields.update({fs.field for fs in metric.field_sources})

        for input_field in metric.computation.inputs:
            if input_field not in source_fields:
                issues.append(f"Computation input '{input_field}' not found in field sources")

        # Check thresholds consistency
        if metric.warning_threshold is not None and metric.critical_threshold is not None:
            if metric.is_higher_better:
                if metric.warning_threshold < metric.critical_threshold:
                    issues.append("Warning threshold should be >= critical threshold when higher is better")
            else:
                if metric.warning_threshold > metric.critical_threshold:
                    issues.append("Warning threshold should be <= critical threshold when lower is better")

        return issues

    def get_metrics_by_table(self, table_name: str) -> list[MetricDefinition]:
        """Get all metrics that use a specific table as a source."""
        result = []

        for metric in self._metrics.values():
            for fs in metric.field_sources:
                if fs.table == table_name:
                    result.append(metric)
                    break

        return result

    def get_metrics_by_event(self, event_name: str) -> list[MetricDefinition]:
        """Get all metrics that use a specific event as a source."""
        result = []

        for metric in self._metrics.values():
            for es in metric.event_sources:
                if es.event_name == event_name:
                    result.append(metric)
                    break

        return result

    def export_metrics(self) -> list[dict[str, Any]]:
        """Export all metric definitions."""
        return [
            {
                "id": str(m.id),
                "name": m.name,
                "code": m.code,
                "description": m.description,
                "category": m.category.value,
                "metric_type": m.metric_type.value,
                "unit": m.unit,
                "field_sources": [
                    {
                        "table": fs.table,
                        "field": fs.field,
                        "description": fs.description,
                        "data_type": fs.data_type,
                        "nullable": fs.nullable,
                        "transform": fs.transform,
                    }
                    for fs in m.field_sources
                ],
                "event_sources": [
                    {
                        "event_name": es.event_name,
                        "description": es.description,
                        "payload_fields": es.payload_fields,
                    }
                    for es in m.event_sources
                ],
                "computation": {
                    "formula": m.computation.formula,
                    "description": m.computation.description,
                    "inputs": m.computation.inputs,
                    "output_type": m.computation.output_type,
                },
                "aggregation_period": m.aggregation_period.value,
                "target_value": m.target_value,
                "warning_threshold": m.warning_threshold,
                "critical_threshold": m.critical_threshold,
                "is_higher_better": m.is_higher_better,
                "is_active": m.is_active,
                "refresh_interval_minutes": m.refresh_interval_minutes,
            }
            for m in self._metrics.values()
        ]

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Get summary for dashboard display."""
        metrics = list(self._metrics.values())
        active_metrics = [m for m in metrics if m.is_active]

        by_category: dict[str, int] = {}
        by_type: dict[str, int] = {}

        for m in active_metrics:
            by_category[m.category.value] = by_category.get(m.category.value, 0) + 1
            by_type[m.metric_type.value] = by_type.get(m.metric_type.value, 0) + 1

        # Get status counts from recent values
        status_counts = {"normal": 0, "warning": 0, "critical": 0}
        for metric in active_metrics:
            latest = self.get_latest_value(metric.code)
            if latest:
                status_counts[latest.status] = status_counts.get(latest.status, 0) + 1

        return {
            "total_metrics": len(metrics),
            "active_metrics": len(active_metrics),
            "by_category": by_category,
            "by_type": by_type,
            "status_counts": status_counts,
            "needing_refresh": len(self.get_metrics_needing_refresh()),
        }
