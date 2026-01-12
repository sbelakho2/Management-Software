"""Metric Sources Service.

Defines exactly which events/fields power each KPI.
Provides a registry of metric source configurations with
field mappings, event triggers, and calculation formulas.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class SourceEntityType(Enum):
    """Entity types that can be metric sources."""

    RFQ = "rfq"
    QUOTE = "quote"
    QUOTE_VERSION = "quote_version"
    OPPORTUNITY = "opportunity"
    QUALIFICATION = "qualification"
    WORK_ORDER = "work_order"
    NON_CONFORMANCE = "non_conformance"
    CAPA = "capa"
    ANDON_EVENT = "andon_event"
    INSPECTION_RECORD = "inspection_record"
    TRAINING = "training"
    USER_SKILL = "user_skill"
    A3 = "a3"
    TASK = "task"
    LSW_ITEM = "lsw_item"
    KANBAN_CARD = "kanban_card"
    PRODUCTION_CELL = "production_cell"
    OBEYA_ITEM = "obeya_item"


class EventType(Enum):
    """Event types that trigger metric updates."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CLOSED = "closed"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    STARTED = "started"
    RESOLVED = "resolved"


class CalculationMethod(Enum):
    """Methods for calculating metric values."""

    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    RATE = "rate"
    DURATION = "duration"
    DIFFERENCE = "difference"
    FORMULA = "formula"


class TimestampField(Enum):
    """Standard timestamp fields used in calculations."""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    COMPLETED_AT = "completed_at"
    STARTED_AT = "started_at"
    CLOSED_AT = "closed_at"
    RESOLVED_AT = "resolved_at"
    APPROVED_AT = "approved_at"
    RELEASED_AT = "released_at"
    DUE_DATE = "due_date"
    SCHEDULED_START = "scheduled_start"
    SCHEDULED_END = "scheduled_end"
    ACTUAL_START = "actual_start"
    ACTUAL_END = "actual_end"


@dataclass
class FieldMapping:
    """Maps a source field to a metric value."""

    source_field: str
    description: str
    data_type: str = "numeric"
    transformation: Optional[str] = None
    default_value: Any = None


@dataclass
class FilterCondition:
    """Condition for filtering source data."""

    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, not_in, contains, is_null
    value: Any
    description: str = ""


@dataclass
class MetricSourceDefinition:
    """Complete definition of a metric source."""

    id: str = field(default_factory=lambda: str(uuid4()))
    kpi_id: str = ""
    name: str = ""
    description: str = ""
    entity_type: SourceEntityType = SourceEntityType.RFQ
    calculation_method: CalculationMethod = CalculationMethod.COUNT
    numerator_field: Optional[str] = None
    denominator_field: Optional[str] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    field_mappings: list[FieldMapping] = field(default_factory=list)
    filters: list[FilterCondition] = field(default_factory=list)
    trigger_events: list[EventType] = field(default_factory=list)
    formula: str = ""
    formula_description: str = ""
    group_by_fields: list[str] = field(default_factory=list)
    unit: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class MetricSourceValidation:
    """Validation result for a metric source."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MetricSourceUsage:
    """Tracks how a metric source is used."""

    source_id: str = ""
    kpi_id: str = ""
    last_calculated_at: Optional[datetime] = None
    calculation_count: int = 0
    last_value: Optional[float] = None
    avg_calculation_time_ms: float = 0.0


class MetricSourcesService:
    """Service for managing metric source configurations.

    Provides a registry of metric sources that define exactly
    which fields/events power each KPI.
    """

    def __init__(self) -> None:
        """Initialize the metric sources service."""
        self._sources: dict[str, MetricSourceDefinition] = {}
        self._usage: dict[str, MetricSourceUsage] = {}
        self._setup_default_sources()

    def _setup_default_sources(self) -> None:
        """Set up default metric source definitions."""
        sources = [
            # RFQ Completeness
            MetricSourceDefinition(
                kpi_id="rfq-completeness",
                name="RFQ Completeness Score",
                description="Measures completeness of RFQ data entry (0-100 score)",
                entity_type=SourceEntityType.RFQ,
                calculation_method=CalculationMethod.AVERAGE,
                field_mappings=[
                    FieldMapping("completeness_score", "Score from RFQ completeness calculation", "numeric"),
                ],
                filters=[
                    FilterCondition("status", "ne", "draft", "Exclude drafts"),
                ],
                trigger_events=[EventType.UPDATED, EventType.STATUS_CHANGED],
                unit="percentage",
            ),
            # Quote Cycle Time
            MetricSourceDefinition(
                kpi_id="quote-cycle-time",
                name="Quote Cycle Time",
                description="Time from RFQ creation to quote release",
                entity_type=SourceEntityType.QUOTE,
                calculation_method=CalculationMethod.DURATION,
                start_timestamp="rfq_created_at",
                end_timestamp="released_at",
                field_mappings=[
                    FieldMapping("rfq_created_at", "RFQ creation timestamp (via RFQ relation)", "timestamp"),
                    FieldMapping("released_at", "Quote release timestamp", "timestamp"),
                ],
                filters=[
                    FilterCondition("status", "eq", "released", "Only released quotes"),
                ],
                trigger_events=[EventType.APPROVED, EventType.STATUS_CHANGED],
                formula_description="released_at - rfq.created_at (in hours/days)",
                unit="hours",
            ),
            # Qualification Discipline
            MetricSourceDefinition(
                kpi_id="qualification-discipline",
                name="Qualification Discipline Rate",
                description="Percentage of RFQs with proper qualification decision",
                entity_type=SourceEntityType.QUALIFICATION,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="decision_with_rationale_count",
                denominator_field="total_qualifications",
                field_mappings=[
                    FieldMapping("decision", "Qualification decision (quote/no_quote/quote_with_conditions)", "enum"),
                    FieldMapping("rationale", "Mandatory rationale text", "text"),
                ],
                filters=[
                    FilterCondition("status", "eq", "completed", "Only completed qualifications"),
                    FilterCondition("rationale", "is_null", False, "Has rationale"),
                ],
                trigger_events=[EventType.COMPLETED, EventType.APPROVED],
                formula="COUNT(decision IS NOT NULL AND rationale IS NOT NULL) / COUNT(*) * 100",
                unit="percentage",
            ),
            # Quote Revision Rate
            MetricSourceDefinition(
                kpi_id="quote-revision-rate",
                name="Quote Revision Rate",
                description="Average number of revisions per quote before release",
                entity_type=SourceEntityType.QUOTE_VERSION,
                calculation_method=CalculationMethod.AVERAGE,
                field_mappings=[
                    FieldMapping("version_number", "Version number of the quote", "integer"),
                    FieldMapping("quote_id", "Parent quote ID", "uuid"),
                ],
                filters=[
                    FilterCondition("is_released", "eq", True, "Only released versions"),
                ],
                trigger_events=[EventType.CREATED],
                formula="MAX(version_number) per quote_id",
                formula_description="Average of max version number across all quotes",
                unit="count",
            ),
            # Margin Protection
            MetricSourceDefinition(
                kpi_id="margin-protection",
                name="Margin Protection Rate",
                description="Percentage of quotes meeting margin floor requirements",
                entity_type=SourceEntityType.QUOTE,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="quotes_meeting_margin",
                denominator_field="total_quotes",
                field_mappings=[
                    FieldMapping("gross_margin", "Quote gross margin percentage", "numeric"),
                    FieldMapping("margin_floor", "Applicable margin floor", "numeric"),
                ],
                filters=[
                    FilterCondition("status", "in", ["released", "approved"], "Released/approved quotes"),
                ],
                trigger_events=[EventType.APPROVED, EventType.STATUS_CHANGED],
                formula="COUNT(gross_margin >= margin_floor) / COUNT(*) * 100",
                unit="percentage",
            ),
            # Win Rate
            MetricSourceDefinition(
                kpi_id="win-rate",
                name="Win Rate",
                description="Percentage of released quotes that result in won opportunities",
                entity_type=SourceEntityType.OPPORTUNITY,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="won_opportunities",
                denominator_field="total_quoted_opportunities",
                field_mappings=[
                    FieldMapping("stage", "Opportunity stage", "enum"),
                    FieldMapping("has_quote", "Whether opportunity has an associated quote", "boolean"),
                ],
                filters=[
                    FilterCondition("has_quote", "eq", True, "Only quoted opportunities"),
                    FilterCondition("stage", "in", ["won", "lost"], "Closed opportunities"),
                ],
                trigger_events=[EventType.STATUS_CHANGED],
                formula="COUNT(stage = 'won') / COUNT(stage IN ('won', 'lost')) * 100",
                unit="percentage",
            ),
            # Work Order On-Time Completion
            MetricSourceDefinition(
                kpi_id="wo-on-time",
                name="Work Order On-Time Completion",
                description="Percentage of work orders completed by scheduled end date",
                entity_type=SourceEntityType.WORK_ORDER,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="on_time_completions",
                denominator_field="total_completions",
                field_mappings=[
                    FieldMapping("scheduled_end", "Scheduled completion date", "timestamp"),
                    FieldMapping("actual_end", "Actual completion date", "timestamp"),
                    FieldMapping("status", "Work order status", "enum"),
                ],
                filters=[
                    FilterCondition("status", "eq", "completed", "Only completed orders"),
                ],
                trigger_events=[EventType.COMPLETED],
                formula="COUNT(actual_end <= scheduled_end) / COUNT(*) * 100",
                unit="percentage",
            ),
            # First Pass Yield
            MetricSourceDefinition(
                kpi_id="first-pass-yield",
                name="First Pass Yield",
                description="Percentage of units passing first inspection",
                entity_type=SourceEntityType.INSPECTION_RECORD,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="first_pass_units",
                denominator_field="total_inspected",
                field_mappings=[
                    FieldMapping("overall_result", "Inspection result (pass/fail)", "enum"),
                    FieldMapping("is_first_inspection", "Whether this is the first inspection", "boolean"),
                    FieldMapping("sample_size", "Number of units in sample", "integer"),
                ],
                filters=[
                    FilterCondition("is_first_inspection", "eq", True, "First inspection only"),
                ],
                trigger_events=[EventType.COMPLETED],
                formula="SUM(passed_count) / SUM(sample_size) * 100",
                unit="percentage",
            ),
            # NC Rate (PPM)
            MetricSourceDefinition(
                kpi_id="nc-rate-ppm",
                name="Non-Conformance Rate (PPM)",
                description="Non-conformances per million units produced",
                entity_type=SourceEntityType.NON_CONFORMANCE,
                calculation_method=CalculationMethod.RATE,
                numerator_field="nc_count",
                denominator_field="units_produced",
                field_mappings=[
                    FieldMapping("quantity_affected", "Number of non-conforming units", "integer"),
                    FieldMapping("severity", "NC severity level", "enum"),
                ],
                trigger_events=[EventType.CREATED],
                formula="COUNT(*) / (total_units_produced / 1000000)",
                formula_description="NC count per million units, requires cross-reference to production data",
                unit="ppm",
            ),
            # CAPA Closure Rate
            MetricSourceDefinition(
                kpi_id="capa-closure-rate",
                name="CAPA On-Time Closure Rate",
                description="Percentage of CAPAs closed by due date",
                entity_type=SourceEntityType.CAPA,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="on_time_closures",
                denominator_field="total_due",
                field_mappings=[
                    FieldMapping("due_date", "CAPA due date", "date"),
                    FieldMapping("closed_at", "Actual closure date", "timestamp"),
                    FieldMapping("status", "CAPA status", "enum"),
                ],
                filters=[
                    FilterCondition("status", "in", ["closed", "effective"], "Closed CAPAs"),
                ],
                trigger_events=[EventType.CLOSED, EventType.STATUS_CHANGED],
                formula="COUNT(closed_at <= due_date) / COUNT(*) * 100",
                unit="percentage",
            ),
            # Andon MTTR
            MetricSourceDefinition(
                kpi_id="andon-mttr",
                name="Andon Mean Time To Resolution",
                description="Average time from Andon trigger to resolution",
                entity_type=SourceEntityType.ANDON_EVENT,
                calculation_method=CalculationMethod.DURATION,
                start_timestamp="reported_at",
                end_timestamp="resolved_at",
                field_mappings=[
                    FieldMapping("reported_at", "When Andon was triggered", "timestamp"),
                    FieldMapping("resolved_at", "When Andon was resolved", "timestamp"),
                    FieldMapping("status", "Andon status", "enum"),
                ],
                filters=[
                    FilterCondition("status", "eq", "resolved", "Only resolved events"),
                ],
                trigger_events=[EventType.RESOLVED],
                formula_description="AVG(resolved_at - reported_at) in minutes",
                unit="minutes",
            ),
            # Andon Acknowledgement SLA
            MetricSourceDefinition(
                kpi_id="andon-ack-sla",
                name="Andon Acknowledgement SLA Compliance",
                description="Percentage of Andon events acknowledged within SLA",
                entity_type=SourceEntityType.ANDON_EVENT,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="acknowledged_in_sla",
                denominator_field="total_acknowledged",
                field_mappings=[
                    FieldMapping("reported_at", "When Andon was triggered", "timestamp"),
                    FieldMapping("acknowledged_at", "When Andon was acknowledged", "timestamp"),
                    FieldMapping("severity", "Andon severity (red/yellow/blue)", "enum"),
                    FieldMapping("station_id", "Station with SLA config", "uuid"),
                ],
                trigger_events=[EventType.STATUS_CHANGED],
                formula="COUNT(ack_time <= sla_target) / COUNT(*) * 100",
                formula_description="SLA target varies by severity and station configuration",
                unit="percentage",
            ),
            # Training Compliance
            MetricSourceDefinition(
                kpi_id="training-compliance",
                name="Training Compliance Rate",
                description="Percentage of required certifications that are current",
                entity_type=SourceEntityType.USER_SKILL,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="current_certifications",
                denominator_field="required_certifications",
                field_mappings=[
                    FieldMapping("certification_status", "Current certification status", "enum"),
                    FieldMapping("expiration_date", "Certification expiration date", "date"),
                    FieldMapping("skill_id", "Related skill ID", "uuid"),
                ],
                filters=[
                    FilterCondition("certification_status", "in", ["certified", "expired"], "Has certification record"),
                ],
                trigger_events=[EventType.UPDATED, EventType.EXPIRED],
                formula="COUNT(certification_status = 'certified' AND expiration_date > NOW()) / COUNT(*) * 100",
                unit="percentage",
            ),
            # Skill Gap Index
            MetricSourceDefinition(
                kpi_id="skill-gap-index",
                name="Skill Gap Index",
                description="Required skills minus available skills per station",
                entity_type=SourceEntityType.USER_SKILL,
                calculation_method=CalculationMethod.DIFFERENCE,
                field_mappings=[
                    FieldMapping("station_id", "Station ID", "uuid"),
                    FieldMapping("required_skills", "Skills required for station", "count"),
                    FieldMapping("available_skills", "Certified users for each skill", "count"),
                ],
                group_by_fields=["station_id"],
                formula="SUM(required_skills) - SUM(available_qualified_users)",
                formula_description="Negative indicates overstaffing, positive indicates gaps",
                unit="count",
            ),
            # LSW Cadence Adherence
            MetricSourceDefinition(
                kpi_id="lsw-adherence",
                name="LSW Cadence Adherence",
                description="Percentage of LSW items completed on schedule",
                entity_type=SourceEntityType.LSW_ITEM,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="completed_on_time",
                denominator_field="total_scheduled",
                field_mappings=[
                    FieldMapping("scheduled_date", "When LSW item was due", "date"),
                    FieldMapping("completed_at", "When LSW item was completed", "timestamp"),
                    FieldMapping("status", "LSW item status", "enum"),
                ],
                filters=[
                    FilterCondition("status", "eq", "completed", "Completed items only"),
                ],
                trigger_events=[EventType.COMPLETED],
                formula="COUNT(completed_at::date <= scheduled_date) / COUNT(*) * 100",
                unit="percentage",
            ),
            # A3 Escalation Rate
            MetricSourceDefinition(
                kpi_id="a3-escalation-rate",
                name="A3 Escalation Rate",
                description="Percentage of Andon events escalated to A3",
                entity_type=SourceEntityType.ANDON_EVENT,
                calculation_method=CalculationMethod.PERCENTAGE,
                numerator_field="escalated_to_a3",
                denominator_field="total_andon",
                field_mappings=[
                    FieldMapping("escalated_to_a3_id", "Linked A3 ID if escalated", "uuid"),
                    FieldMapping("status", "Andon status", "enum"),
                ],
                trigger_events=[EventType.ESCALATED],
                formula="COUNT(escalated_to_a3_id IS NOT NULL) / COUNT(*) * 100",
                unit="percentage",
            ),
            # OEE
            MetricSourceDefinition(
                kpi_id="oee",
                name="Overall Equipment Effectiveness",
                description="OEE = Availability × Performance × Quality",
                entity_type=SourceEntityType.PRODUCTION_CELL,
                calculation_method=CalculationMethod.FORMULA,
                field_mappings=[
                    FieldMapping("availability", "Operating time / Planned time", "numeric"),
                    FieldMapping("performance", "Actual output / Theoretical output", "numeric"),
                    FieldMapping("quality", "Good units / Total units", "numeric"),
                ],
                group_by_fields=["cell_id", "shift_date"],
                formula="availability * performance * quality * 100",
                formula_description="All three components are ratios (0-1), result is percentage",
                unit="percentage",
            ),
            # Kanban Lead Time
            MetricSourceDefinition(
                kpi_id="kanban-lead-time",
                name="Kanban Lead Time",
                description="Time from card creation to completion",
                entity_type=SourceEntityType.KANBAN_CARD,
                calculation_method=CalculationMethod.DURATION,
                start_timestamp="created_at",
                end_timestamp="cycle_completed_at",
                field_mappings=[
                    FieldMapping("created_at", "Card creation time", "timestamp"),
                    FieldMapping("cycle_completed_at", "Card completion time", "timestamp"),
                    FieldMapping("board_id", "Kanban board", "uuid"),
                ],
                filters=[
                    FilterCondition("status", "eq", "completed", "Completed cards only"),
                ],
                trigger_events=[EventType.COMPLETED],
                group_by_fields=["board_id"],
                unit="hours",
            ),
        ]

        for source in sources:
            self._sources[source.kpi_id] = source

    # --- Source Management ---

    def register_source(
        self,
        kpi_id: str,
        name: str,
        description: str,
        entity_type: SourceEntityType,
        calculation_method: CalculationMethod,
        field_mappings: Optional[list[FieldMapping]] = None,
        filters: Optional[list[FilterCondition]] = None,
        trigger_events: Optional[list[EventType]] = None,
        formula: str = "",
        formula_description: str = "",
        numerator_field: Optional[str] = None,
        denominator_field: Optional[str] = None,
        start_timestamp: Optional[str] = None,
        end_timestamp: Optional[str] = None,
        group_by_fields: Optional[list[str]] = None,
        unit: str = "",
    ) -> MetricSourceDefinition:
        """Register a new metric source definition."""
        source = MetricSourceDefinition(
            kpi_id=kpi_id,
            name=name,
            description=description,
            entity_type=entity_type,
            calculation_method=calculation_method,
            field_mappings=field_mappings or [],
            filters=filters or [],
            trigger_events=trigger_events or [],
            formula=formula,
            formula_description=formula_description,
            numerator_field=numerator_field,
            denominator_field=denominator_field,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            group_by_fields=group_by_fields or [],
            unit=unit,
        )

        self._sources[kpi_id] = source
        return source

    def get_source(self, kpi_id: str) -> Optional[MetricSourceDefinition]:
        """Get a metric source by KPI ID."""
        return self._sources.get(kpi_id)

    def get_all_sources(self) -> list[MetricSourceDefinition]:
        """Get all registered metric sources."""
        return list(self._sources.values())

    def get_sources_by_entity(
        self,
        entity_type: SourceEntityType,
    ) -> list[MetricSourceDefinition]:
        """Get all metric sources for a specific entity type."""
        return [s for s in self._sources.values() if s.entity_type == entity_type]

    def get_sources_by_event(
        self,
        event_type: EventType,
    ) -> list[MetricSourceDefinition]:
        """Get all metric sources triggered by a specific event."""
        return [s for s in self._sources.values() if event_type in s.trigger_events]

    def update_source(
        self,
        kpi_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        filters: Optional[list[FilterCondition]] = None,
        formula: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[MetricSourceDefinition]:
        """Update a metric source definition."""
        source = self._sources.get(kpi_id)
        if not source:
            return None

        if name is not None:
            source.name = name
        if description is not None:
            source.description = description
        if filters is not None:
            source.filters = filters
        if formula is not None:
            source.formula = formula
        if is_active is not None:
            source.is_active = is_active

        source.updated_at = datetime.now(timezone.utc)
        return source

    def delete_source(self, kpi_id: str) -> bool:
        """Delete a metric source definition."""
        if kpi_id in self._sources:
            del self._sources[kpi_id]
            return True
        return False

    # --- Validation ---

    def validate_source(
        self,
        source: MetricSourceDefinition,
    ) -> MetricSourceValidation:
        """Validate a metric source definition."""
        validation = MetricSourceValidation()

        # Check required fields
        if not source.kpi_id:
            validation.errors.append("kpi_id is required")
            validation.is_valid = False

        if not source.name:
            validation.errors.append("name is required")
            validation.is_valid = False

        # Check calculation method requirements
        if source.calculation_method == CalculationMethod.PERCENTAGE:
            if not source.numerator_field and not source.formula:
                validation.errors.append("PERCENTAGE calculation requires numerator_field or formula")
                validation.is_valid = False
            if not source.denominator_field and not source.formula:
                validation.errors.append("PERCENTAGE calculation requires denominator_field or formula")
                validation.is_valid = False

        if source.calculation_method == CalculationMethod.DURATION:
            if not source.start_timestamp:
                validation.errors.append("DURATION calculation requires start_timestamp")
                validation.is_valid = False
            if not source.end_timestamp:
                validation.errors.append("DURATION calculation requires end_timestamp")
                validation.is_valid = False

        if source.calculation_method == CalculationMethod.FORMULA:
            if not source.formula:
                validation.errors.append("FORMULA calculation requires formula")
                validation.is_valid = False

        # Warnings
        if not source.trigger_events:
            validation.warnings.append("No trigger_events defined - metric won't auto-update")

        if not source.field_mappings:
            validation.warnings.append("No field_mappings defined - documentation incomplete")

        if not source.unit:
            validation.warnings.append("No unit defined - display may be unclear")

        return validation

    def validate_all_sources(self) -> dict[str, MetricSourceValidation]:
        """Validate all registered metric sources."""
        results = {}
        for kpi_id, source in self._sources.items():
            results[kpi_id] = self.validate_source(source)
        return results

    # --- Usage Tracking ---

    def record_calculation(
        self,
        kpi_id: str,
        value: float,
        calculation_time_ms: float,
    ) -> None:
        """Record a metric calculation for usage tracking."""
        if kpi_id not in self._usage:
            self._usage[kpi_id] = MetricSourceUsage(
                source_id=kpi_id,
                kpi_id=kpi_id,
            )

        usage = self._usage[kpi_id]
        usage.last_calculated_at = datetime.now(timezone.utc)
        usage.calculation_count += 1
        usage.last_value = value

        # Running average of calculation time
        if usage.calculation_count == 1:
            usage.avg_calculation_time_ms = calculation_time_ms
        else:
            usage.avg_calculation_time_ms = (
                (usage.avg_calculation_time_ms * (usage.calculation_count - 1) + calculation_time_ms)
                / usage.calculation_count
            )

    def get_usage(self, kpi_id: str) -> Optional[MetricSourceUsage]:
        """Get usage statistics for a metric source."""
        return self._usage.get(kpi_id)

    def get_all_usage(self) -> list[MetricSourceUsage]:
        """Get all usage statistics."""
        return list(self._usage.values())

    # --- Query Helpers ---

    def get_field_documentation(self, kpi_id: str) -> dict:
        """Get field documentation for a KPI."""
        source = self._sources.get(kpi_id)
        if not source:
            return {}

        return {
            "kpi_id": source.kpi_id,
            "name": source.name,
            "description": source.description,
            "entity_type": source.entity_type.value,
            "calculation_method": source.calculation_method.value,
            "formula": source.formula,
            "formula_description": source.formula_description,
            "fields": [
                {
                    "name": fm.source_field,
                    "description": fm.description,
                    "type": fm.data_type,
                }
                for fm in source.field_mappings
            ],
            "filters": [
                {
                    "field": f.field,
                    "operator": f.operator,
                    "value": f.value,
                    "description": f.description,
                }
                for f in source.filters
            ],
            "trigger_events": [e.value for e in source.trigger_events],
            "unit": source.unit,
        }

    def get_documentation_report(self) -> list[dict]:
        """Get documentation for all KPIs."""
        return [self.get_field_documentation(kpi_id) for kpi_id in self._sources]

    def get_sources_summary(self) -> dict:
        """Get a summary of all metric sources."""
        by_entity: dict[str, int] = {}
        by_method: dict[str, int] = {}

        for source in self._sources.values():
            entity = source.entity_type.value
            by_entity[entity] = by_entity.get(entity, 0) + 1

            method = source.calculation_method.value
            by_method[method] = by_method.get(method, 0) + 1

        return {
            "total_sources": len(self._sources),
            "by_entity_type": by_entity,
            "by_calculation_method": by_method,
            "active_sources": len([s for s in self._sources.values() if s.is_active]),
        }
