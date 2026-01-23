"""SPC & Scrap/Rework Accounting Service (Development Plan 22.7).

Implements:
- SPC / Statistical Quality: control charts (X̄/R, p-chart), out-of-control triggers
  to NC/CAPA.
- Scrap/Rework Accounting Hooks: standardized reasons and cost capture (feeds COPQ
  and GL postings).

This module is in-memory and pure-Python to match other services.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Protocol
from uuid import UUID, uuid4


class ControlChartType(str, Enum):
    XBAR_R = "xbar_r"  # X-bar and Range chart
    XBAR_S = "xbar_s"  # X-bar and Std Dev chart
    P_CHART = "p_chart"  # Proportion defective
    NP_CHART = "np_chart"  # Number defective
    C_CHART = "c_chart"  # Count of defects
    U_CHART = "u_chart"  # Defects per unit


class ViolationType(str, Enum):
    ABOVE_UCL = "above_ucl"
    BELOW_LCL = "below_lcl"
    TREND = "trend"  # 7 points trending up or down
    RUN = "run"  # 7 points on one side of center
    STRATIFICATION = "stratification"  # Points hugging center line


class ScrapReason(str, Enum):
    MATERIAL_DEFECT = "material_defect"
    PROCESS_ERROR = "process_error"
    EQUIPMENT_MALFUNCTION = "equipment_malfunction"
    OPERATOR_ERROR = "operator_error"
    DESIGN_ISSUE = "design_issue"
    HANDLING_DAMAGE = "handling_damage"
    CONTAMINATION = "contamination"
    MEASUREMENT_ERROR = "measurement_error"
    OTHER = "other"


class ReworkReason(str, Enum):
    DIMENSIONAL_OOS = "dimensional_oos"  # Out of spec
    COSMETIC_DEFECT = "cosmetic_defect"
    MISSING_OPERATION = "missing_operation"
    INCORRECT_ASSEMBLY = "incorrect_assembly"
    SURFACE_FINISH = "surface_finish"
    FUNCTIONAL_FAILURE = "functional_failure"
    DOCUMENTATION_ERROR = "documentation_error"
    OTHER = "other"


class DispositionType(str, Enum):
    SCRAP = "scrap"
    REWORK = "rework"
    USE_AS_IS = "use_as_is"
    RETURN_TO_SUPPLIER = "return_to_supplier"


# RBAC
_QUALITY_WRITE_ROLES: set[str] = {"admin", "quality", "ops", "ceo", "gm"}
_QUALITY_READ_ROLES: set[str] = {"admin", "quality", "ops", "ceo", "gm", "finance", "auditor", "supervisor"}
_FINANCE_ROLES: set[str] = {"admin", "finance", "accountant", "ceo"}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_any(roles: set[str], allowed: set[str], msg: str) -> None:
    if not roles.intersection(allowed):
        raise PermissionError(msg)


@dataclass(frozen=True)
class AuditEvent:
    id: UUID
    ts: datetime
    actor_id: str
    actor_roles: tuple[str, ...]
    action: str
    entity_type: str
    entity_id: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================
# SPC Models
# ============================================================


@dataclass(frozen=True)
class ControlChart:
    """Definition of a control chart for a measurement."""

    id: UUID
    name: str
    chart_type: ControlChartType
    characteristic: str  # What's being measured
    station_id: str
    product_id: str | None = None
    operation_id: str | None = None
    subgroup_size: int = 5
    ucl: float | None = None  # Upper Control Limit
    lcl: float | None = None  # Lower Control Limit
    center_line: float | None = None
    usl: float | None = None  # Upper Spec Limit
    lsl: float | None = None  # Lower Spec Limit
    target: float | None = None
    is_active: bool = True


@dataclass(frozen=True)
class SPCDataPoint:
    """A single data point for SPC analysis."""

    id: UUID
    chart_id: UUID
    timestamp: datetime
    value: float
    subgroup_id: str | None = None
    operator_id: str | None = None
    lot_number: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlViolation:
    """A control chart violation event."""

    id: UUID
    chart_id: UUID
    violation_type: ViolationType
    detected_at: datetime
    data_point_ids: tuple[str, ...]
    value: float | None = None
    ucl: float | None = None
    lcl: float | None = None
    notes: str = ""
    nc_id: UUID | None = None  # Link to non-conformance


# ============================================================
# Scrap/Rework Models
# ============================================================


@dataclass(frozen=True)
class ScrapRecord:
    """Record of scrapped material/product."""

    id: UUID
    work_order_id: str
    product_id: str
    lot_number: str
    quantity: int
    unit: str
    reason: ScrapReason
    reason_detail: str
    station_id: str
    operation_id: str | None = None
    operator_id: str | None = None
    material_cost: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    recorded_at: datetime = field(default_factory=_utcnow)
    recorded_by: str = ""
    nc_id: UUID | None = None  # Link to non-conformance
    gl_posted: bool = False
    gl_journal_id: UUID | None = None


@dataclass(frozen=True)
class ReworkRecord:
    """Record of rework activity."""

    id: UUID
    work_order_id: str
    product_id: str
    lot_number: str
    quantity: int
    unit: str
    reason: ReworkReason
    reason_detail: str
    station_id: str
    original_operation_id: str | None = None
    rework_instructions: str = ""
    operator_id: str | None = None
    labor_hours: Decimal = Decimal("0")
    labor_cost: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    started_at: datetime | None = None
    completed_at: datetime | None = None
    recorded_at: datetime = field(default_factory=_utcnow)
    recorded_by: str = ""
    nc_id: UUID | None = None
    gl_posted: bool = False
    gl_journal_id: UUID | None = None


@dataclass(frozen=True)
class COPQSummary:
    """Cost of Poor Quality summary."""

    period_start: datetime
    period_end: datetime
    total_scrap_cost: Decimal
    total_rework_cost: Decimal
    total_copq: Decimal
    scrap_count: int
    rework_count: int
    by_reason: dict[str, Decimal] = field(default_factory=dict)
    by_station: dict[str, Decimal] = field(default_factory=dict)
    by_product: dict[str, Decimal] = field(default_factory=dict)


# ============================================================
# Provider Protocols
# ============================================================


class AccountingLedgerProvider(Protocol):
    def post_journal_entry(
        self,
        *,
        description: str,
        entries: list[tuple[str, Decimal, Decimal]],  # (account, debit, credit)
        correlation_id: str,
    ) -> UUID: ...


class NCProvider(Protocol):
    def create_nonconformance(
        self,
        *,
        description: str,
        source: str,
        metadata: dict[str, Any],
    ) -> UUID: ...


# ============================================================
# Service
# ============================================================


class SPCScrapReworkService:
    """In-memory SPC and Scrap/Rework accounting service."""

    def __init__(
        self,
        *,
        accounting_provider: AccountingLedgerProvider | None = None,
        nc_provider: NCProvider | None = None,
        scrap_expense_account: str = "5200-SCRAP",
        rework_expense_account: str = "5210-REWORK",
        wip_account: str = "1400-WIP",
    ) -> None:
        # SPC data
        self._charts: dict[UUID, ControlChart] = {}
        self._data_points: dict[UUID, SPCDataPoint] = {}
        self._violations: dict[UUID, ControlViolation] = {}

        # Scrap/Rework data
        self._scrap_records: dict[UUID, ScrapRecord] = {}
        self._rework_records: dict[UUID, ReworkRecord] = {}

        # Providers
        self._accounting_provider = accounting_provider
        self._nc_provider = nc_provider

        # GL accounts
        self._scrap_expense_account = scrap_expense_account
        self._rework_expense_account = rework_expense_account
        self._wip_account = wip_account

        self._audit: list[AuditEvent] = []

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _audit_event(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        action: str,
        entity_type: str,
        entity_id: str,
        correlation_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ev = AuditEvent(
            id=uuid4(),
            ts=_utcnow(),
            actor_id=actor_id,
            actor_roles=tuple(sorted(_norm_roles(actor_roles))),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._audit.append(ev)

    def _check_control_limits(
        self, chart: ControlChart, value: float
    ) -> ViolationType | None:
        """Check if value violates control limits."""
        if chart.ucl is not None and value > chart.ucl:
            return ViolationType.ABOVE_UCL
        if chart.lcl is not None and value < chart.lcl:
            return ViolationType.BELOW_LCL
        return None

    def _check_trend(
        self, chart_id: UUID, new_value: float
    ) -> ViolationType | None:
        """Check for 7-point trend (Western Electric Rule 3)."""
        points = sorted(
            [p for p in self._data_points.values() if p.chart_id == chart_id],
            key=lambda p: p.timestamp,
        )[-6:]  # Last 6 + new = 7

        if len(points) < 6:
            return None

        values = [p.value for p in points] + [new_value]

        # Check increasing trend
        increasing = all(values[i] < values[i + 1] for i in range(6))
        if increasing:
            return ViolationType.TREND

        # Check decreasing trend
        decreasing = all(values[i] > values[i + 1] for i in range(6))
        if decreasing:
            return ViolationType.TREND

        return None

    def _check_run(
        self, chart: ControlChart, chart_id: UUID, new_value: float
    ) -> ViolationType | None:
        """Check for 7 points on one side of center line (Western Electric Rule 4)."""
        if chart.center_line is None:
            return None

        points = sorted(
            [p for p in self._data_points.values() if p.chart_id == chart_id],
            key=lambda p: p.timestamp,
        )[-6:]

        if len(points) < 6:
            return None

        values = [p.value for p in points] + [new_value]
        center = chart.center_line

        # All above center
        if all(v > center for v in values):
            return ViolationType.RUN
        # All below center
        if all(v < center for v in values):
            return ViolationType.RUN

        return None

    # ----------------------------------------------------------------
    # Audit API
    # ----------------------------------------------------------------

    def list_audit_events(self, *, actor_roles: Iterable[str]) -> list[AuditEvent]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")
        return list(self._audit)

    # ----------------------------------------------------------------
    # Control Chart Management
    # ----------------------------------------------------------------

    def create_control_chart(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        name: str,
        chart_type: ControlChartType,
        characteristic: str,
        station_id: str,
        product_id: str | None = None,
        subgroup_size: int = 5,
        ucl: float | None = None,
        lcl: float | None = None,
        center_line: float | None = None,
        usl: float | None = None,
        lsl: float | None = None,
        target: float | None = None,
    ) -> ControlChart:
        """Create a control chart definition."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_WRITE_ROLES, "Quality write role required")

        if not name or not name.strip():
            raise ValueError("name required")
        if not characteristic or not characteristic.strip():
            raise ValueError("characteristic required")
        if subgroup_size < 1:
            raise ValueError("subgroup_size must be >= 1")

        chart = ControlChart(
            id=uuid4(),
            name=name.strip(),
            chart_type=chart_type,
            characteristic=characteristic.strip(),
            station_id=station_id,
            product_id=product_id,
            subgroup_size=subgroup_size,
            ucl=ucl,
            lcl=lcl,
            center_line=center_line,
            usl=usl,
            lsl=lsl,
            target=target,
        )
        self._charts[chart.id] = chart

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="spc.chart.create",
            entity_type="control_chart",
            entity_id=str(chart.id),
            correlation_id=correlation_id,
            metadata={"chart_type": chart_type.value, "characteristic": characteristic},
        )

        return chart

    def get_control_chart(
        self, *, actor_roles: Iterable[str], chart_id: UUID
    ) -> ControlChart | None:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")
        return self._charts.get(chart_id)

    def list_control_charts(
        self,
        *,
        actor_roles: Iterable[str],
        station_id: str | None = None,
        product_id: str | None = None,
        active_only: bool = True,
    ) -> list[ControlChart]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        result = []
        for chart in self._charts.values():
            if active_only and not chart.is_active:
                continue
            if station_id and chart.station_id != station_id:
                continue
            if product_id and chart.product_id != product_id:
                continue
            result.append(chart)

        return sorted(result, key=lambda c: c.name)

    # ----------------------------------------------------------------
    # SPC Data Collection
    # ----------------------------------------------------------------

    def record_measurement(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        chart_id: UUID,
        value: float,
        subgroup_id: str | None = None,
        operator_id: str | None = None,
        lot_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[SPCDataPoint, ControlViolation | None]:
        """Record a measurement and check for control violations."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_WRITE_ROLES, "Quality write role required")

        chart = self._charts.get(chart_id)
        if not chart:
            raise ValueError("chart_id not found")

        # Check for violations BEFORE storing the data point
        violation = None
        violation_type = self._check_control_limits(chart, value)

        if not violation_type:
            violation_type = self._check_trend(chart_id, value)

        if not violation_type:
            violation_type = self._check_run(chart, chart_id, value)

        data_point = SPCDataPoint(
            id=uuid4(),
            chart_id=chart_id,
            timestamp=_utcnow(),
            value=value,
            subgroup_id=subgroup_id,
            operator_id=operator_id,
            lot_number=lot_number,
            metadata=metadata or {},
        )
        self._data_points[data_point.id] = data_point

        if violation_type:
            violation = ControlViolation(
                id=uuid4(),
                chart_id=chart_id,
                violation_type=violation_type,
                detected_at=_utcnow(),
                data_point_ids=(str(data_point.id),),
                value=value,
                ucl=chart.ucl,
                lcl=chart.lcl,
            )
            self._violations[violation.id] = violation

            # Create NC if provider available
            if self._nc_provider:
                nc_id = self._nc_provider.create_nonconformance(
                    description=f"SPC violation: {violation_type.value} on {chart.name}",
                    source="spc",
                    metadata={"chart_id": str(chart_id), "value": value},
                )
                violation = ControlViolation(
                    id=violation.id,
                    chart_id=violation.chart_id,
                    violation_type=violation.violation_type,
                    detected_at=violation.detected_at,
                    data_point_ids=violation.data_point_ids,
                    value=violation.value,
                    ucl=violation.ucl,
                    lcl=violation.lcl,
                    nc_id=nc_id,
                )
                self._violations[violation.id] = violation

            self._audit_event(
                actor_id=actor_id,
                actor_roles=roles,
                action="spc.violation.detected",
                entity_type="control_violation",
                entity_id=str(violation.id),
                correlation_id=correlation_id,
                metadata={"type": violation_type.value, "value": value},
            )

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="spc.measurement.record",
            entity_type="spc_data_point",
            entity_id=str(data_point.id),
            correlation_id=correlation_id,
            metadata={"value": value, "chart_name": chart.name},
        )

        return data_point, violation

    def get_chart_data(
        self,
        *,
        actor_roles: Iterable[str],
        chart_id: UUID,
        limit: int = 100,
    ) -> list[SPCDataPoint]:
        """Get recent data points for a chart."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        points = [p for p in self._data_points.values() if p.chart_id == chart_id]
        return sorted(points, key=lambda p: p.timestamp, reverse=True)[:limit]

    def get_violations(
        self,
        *,
        actor_roles: Iterable[str],
        chart_id: UUID | None = None,
    ) -> list[ControlViolation]:
        """Get control violations."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        result = []
        for v in self._violations.values():
            if chart_id and v.chart_id != chart_id:
                continue
            result.append(v)

        return sorted(result, key=lambda v: v.detected_at, reverse=True)

    def calculate_process_capability(
        self,
        *,
        actor_roles: Iterable[str],
        chart_id: UUID,
    ) -> dict[str, float]:
        """Calculate Cp and Cpk indices."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        chart = self._charts.get(chart_id)
        if not chart:
            raise ValueError("chart_id not found")

        if chart.usl is None or chart.lsl is None:
            raise ValueError("Spec limits required for capability calculation")

        points = [p for p in self._data_points.values() if p.chart_id == chart_id]
        if len(points) < 2:
            raise ValueError("Not enough data for capability calculation")

        values = [p.value for p in points]
        mean = sum(values) / len(values)
        std_dev = math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))

        if std_dev == 0:
            return {"cp": float("inf"), "cpk": float("inf"), "mean": mean, "std_dev": 0}

        cp = (chart.usl - chart.lsl) / (6 * std_dev)
        cpu = (chart.usl - mean) / (3 * std_dev)
        cpl = (mean - chart.lsl) / (3 * std_dev)
        cpk = min(cpu, cpl)

        return {
            "cp": round(cp, 3),
            "cpk": round(cpk, 3),
            "cpu": round(cpu, 3),
            "cpl": round(cpl, 3),
            "mean": round(mean, 4),
            "std_dev": round(std_dev, 4),
            "sample_size": len(values),
        }

    # ----------------------------------------------------------------
    # Scrap Recording
    # ----------------------------------------------------------------

    def record_scrap(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        product_id: str,
        lot_number: str,
        quantity: int,
        unit: str,
        reason: ScrapReason,
        reason_detail: str,
        station_id: str,
        operation_id: str | None = None,
        operator_id: str | None = None,
        material_cost: Decimal = Decimal("0"),
        labor_cost: Decimal = Decimal("0"),
        overhead_cost: Decimal = Decimal("0"),
        nc_id: UUID | None = None,
    ) -> ScrapRecord:
        """Record scrapped material/product."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_WRITE_ROLES, "Quality write role required")

        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        if not reason_detail or not reason_detail.strip():
            raise ValueError("reason_detail required")

        total_cost = material_cost + labor_cost + overhead_cost

        record = ScrapRecord(
            id=uuid4(),
            work_order_id=work_order_id,
            product_id=product_id,
            lot_number=lot_number,
            quantity=quantity,
            unit=unit,
            reason=reason,
            reason_detail=reason_detail.strip(),
            station_id=station_id,
            operation_id=operation_id,
            operator_id=operator_id,
            material_cost=material_cost,
            labor_cost=labor_cost,
            overhead_cost=overhead_cost,
            total_cost=total_cost,
            recorded_at=_utcnow(),
            recorded_by=actor_id,
            nc_id=nc_id,
        )
        self._scrap_records[record.id] = record

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="scrap.record",
            entity_type="scrap_record",
            entity_id=str(record.id),
            correlation_id=correlation_id,
            metadata={
                "reason": reason.value,
                "quantity": quantity,
                "total_cost": str(total_cost),
            },
        )

        return record

    def post_scrap_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        scrap_id: UUID,
    ) -> ScrapRecord:
        """Post scrap cost to GL (debit scrap expense, credit WIP)."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_ROLES, "Finance role required")

        record = self._scrap_records.get(scrap_id)
        if not record:
            raise ValueError("scrap_id not found")
        if record.gl_posted:
            raise ValueError("Already posted to GL")
        if record.total_cost <= 0:
            raise ValueError("No cost to post")

        journal_id: UUID | None = None
        if self._accounting_provider:
            journal_id = self._accounting_provider.post_journal_entry(
                description=f"Scrap: {record.reason.value} - {record.product_id}",
                entries=[
                    (self._scrap_expense_account, record.total_cost, Decimal("0")),
                    (self._wip_account, Decimal("0"), record.total_cost),
                ],
                correlation_id=correlation_id,
            )

        updated = ScrapRecord(
            id=record.id,
            work_order_id=record.work_order_id,
            product_id=record.product_id,
            lot_number=record.lot_number,
            quantity=record.quantity,
            unit=record.unit,
            reason=record.reason,
            reason_detail=record.reason_detail,
            station_id=record.station_id,
            operation_id=record.operation_id,
            operator_id=record.operator_id,
            material_cost=record.material_cost,
            labor_cost=record.labor_cost,
            overhead_cost=record.overhead_cost,
            total_cost=record.total_cost,
            recorded_at=record.recorded_at,
            recorded_by=record.recorded_by,
            nc_id=record.nc_id,
            gl_posted=True,
            gl_journal_id=journal_id,
        )
        self._scrap_records[record.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="scrap.gl_post",
            entity_type="scrap_record",
            entity_id=str(scrap_id),
            correlation_id=correlation_id,
            metadata={"total_cost": str(record.total_cost)},
        )

        return updated

    # ----------------------------------------------------------------
    # Rework Recording
    # ----------------------------------------------------------------

    def record_rework(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        work_order_id: str,
        product_id: str,
        lot_number: str,
        quantity: int,
        unit: str,
        reason: ReworkReason,
        reason_detail: str,
        station_id: str,
        original_operation_id: str | None = None,
        rework_instructions: str = "",
        operator_id: str | None = None,
        nc_id: UUID | None = None,
    ) -> ReworkRecord:
        """Record rework activity."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_WRITE_ROLES, "Quality write role required")

        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        if not reason_detail or not reason_detail.strip():
            raise ValueError("reason_detail required")

        record = ReworkRecord(
            id=uuid4(),
            work_order_id=work_order_id,
            product_id=product_id,
            lot_number=lot_number,
            quantity=quantity,
            unit=unit,
            reason=reason,
            reason_detail=reason_detail.strip(),
            station_id=station_id,
            original_operation_id=original_operation_id,
            rework_instructions=rework_instructions,
            operator_id=operator_id,
            recorded_at=_utcnow(),
            recorded_by=actor_id,
            nc_id=nc_id,
        )
        self._rework_records[record.id] = record

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="rework.record",
            entity_type="rework_record",
            entity_id=str(record.id),
            correlation_id=correlation_id,
            metadata={"reason": reason.value, "quantity": quantity},
        )

        return record

    def complete_rework(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        rework_id: UUID,
        labor_hours: Decimal,
        labor_cost: Decimal,
        material_cost: Decimal = Decimal("0"),
    ) -> ReworkRecord:
        """Complete rework and record costs."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_WRITE_ROLES, "Quality write role required")

        record = self._rework_records.get(rework_id)
        if not record:
            raise ValueError("rework_id not found")
        if record.completed_at:
            raise ValueError("Rework already completed")

        total_cost = labor_cost + material_cost

        updated = ReworkRecord(
            id=record.id,
            work_order_id=record.work_order_id,
            product_id=record.product_id,
            lot_number=record.lot_number,
            quantity=record.quantity,
            unit=record.unit,
            reason=record.reason,
            reason_detail=record.reason_detail,
            station_id=record.station_id,
            original_operation_id=record.original_operation_id,
            rework_instructions=record.rework_instructions,
            operator_id=record.operator_id,
            labor_hours=labor_hours,
            labor_cost=labor_cost,
            material_cost=material_cost,
            total_cost=total_cost,
            started_at=record.started_at or record.recorded_at,
            completed_at=_utcnow(),
            recorded_at=record.recorded_at,
            recorded_by=record.recorded_by,
            nc_id=record.nc_id,
        )
        self._rework_records[record.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="rework.complete",
            entity_type="rework_record",
            entity_id=str(rework_id),
            correlation_id=correlation_id,
            metadata={"labor_hours": str(labor_hours), "total_cost": str(total_cost)},
        )

        return updated

    def post_rework_to_gl(
        self,
        *,
        actor_id: str,
        actor_roles: Iterable[str],
        correlation_id: str,
        rework_id: UUID,
    ) -> ReworkRecord:
        """Post rework cost to GL."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _FINANCE_ROLES, "Finance role required")

        record = self._rework_records.get(rework_id)
        if not record:
            raise ValueError("rework_id not found")
        if not record.completed_at:
            raise ValueError("Rework not completed")
        if record.gl_posted:
            raise ValueError("Already posted to GL")
        if record.total_cost <= 0:
            raise ValueError("No cost to post")

        journal_id: UUID | None = None
        if self._accounting_provider:
            journal_id = self._accounting_provider.post_journal_entry(
                description=f"Rework: {record.reason.value} - {record.product_id}",
                entries=[
                    (self._rework_expense_account, record.total_cost, Decimal("0")),
                    (self._wip_account, Decimal("0"), record.total_cost),
                ],
                correlation_id=correlation_id,
            )

        updated = ReworkRecord(
            id=record.id,
            work_order_id=record.work_order_id,
            product_id=record.product_id,
            lot_number=record.lot_number,
            quantity=record.quantity,
            unit=record.unit,
            reason=record.reason,
            reason_detail=record.reason_detail,
            station_id=record.station_id,
            original_operation_id=record.original_operation_id,
            rework_instructions=record.rework_instructions,
            operator_id=record.operator_id,
            labor_hours=record.labor_hours,
            labor_cost=record.labor_cost,
            material_cost=record.material_cost,
            total_cost=record.total_cost,
            started_at=record.started_at,
            completed_at=record.completed_at,
            recorded_at=record.recorded_at,
            recorded_by=record.recorded_by,
            nc_id=record.nc_id,
            gl_posted=True,
            gl_journal_id=journal_id,
        )
        self._rework_records[record.id] = updated

        self._audit_event(
            actor_id=actor_id,
            actor_roles=roles,
            action="rework.gl_post",
            entity_type="rework_record",
            entity_id=str(rework_id),
            correlation_id=correlation_id,
        )

        return updated

    # ----------------------------------------------------------------
    # COPQ Reporting
    # ----------------------------------------------------------------

    def get_copq_summary(
        self,
        *,
        actor_roles: Iterable[str],
        start_date: datetime,
        end_date: datetime,
    ) -> COPQSummary:
        """Get Cost of Poor Quality summary for a period."""
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        total_scrap = Decimal("0")
        total_rework = Decimal("0")
        scrap_count = 0
        rework_count = 0
        by_reason: dict[str, Decimal] = {}
        by_station: dict[str, Decimal] = {}
        by_product: dict[str, Decimal] = {}

        for scrap_rec in self._scrap_records.values():
            if start_date <= scrap_rec.recorded_at <= end_date:
                total_scrap += scrap_rec.total_cost
                scrap_count += 1

                key = f"scrap:{scrap_rec.reason.value}"
                by_reason[key] = by_reason.get(key, Decimal("0")) + scrap_rec.total_cost
                by_station[scrap_rec.station_id] = by_station.get(scrap_rec.station_id, Decimal("0")) + scrap_rec.total_cost
                by_product[scrap_rec.product_id] = by_product.get(scrap_rec.product_id, Decimal("0")) + scrap_rec.total_cost

        for rework_rec in self._rework_records.values():
            if rework_rec.completed_at and start_date <= rework_rec.completed_at <= end_date:
                total_rework += rework_rec.total_cost
                rework_count += 1

                key = f"rework:{rework_rec.reason.value}"
                by_reason[key] = by_reason.get(key, Decimal("0")) + rework_rec.total_cost
                by_station[rework_rec.station_id] = by_station.get(rework_rec.station_id, Decimal("0")) + rework_rec.total_cost
                by_product[rework_rec.product_id] = by_product.get(rework_rec.product_id, Decimal("0")) + rework_rec.total_cost

        return COPQSummary(
            period_start=start_date,
            period_end=end_date,
            total_scrap_cost=total_scrap,
            total_rework_cost=total_rework,
            total_copq=total_scrap + total_rework,
            scrap_count=scrap_count,
            rework_count=rework_count,
            by_reason=by_reason,
            by_station=by_station,
            by_product=by_product,
        )

    def list_scrap_records(
        self,
        *,
        actor_roles: Iterable[str],
        station_id: str | None = None,
        product_id: str | None = None,
    ) -> list[ScrapRecord]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        result = []
        for rec in self._scrap_records.values():
            if station_id and rec.station_id != station_id:
                continue
            if product_id and rec.product_id != product_id:
                continue
            result.append(rec)

        return sorted(result, key=lambda r: r.recorded_at, reverse=True)

    def list_rework_records(
        self,
        *,
        actor_roles: Iterable[str],
        station_id: str | None = None,
        product_id: str | None = None,
    ) -> list[ReworkRecord]:
        roles = _norm_roles(actor_roles)
        _require_any(roles, _QUALITY_READ_ROLES, "Quality read role required")

        result = []
        for rec in self._rework_records.values():
            if station_id and rec.station_id != station_id:
                continue
            if product_id and rec.product_id != product_id:
                continue
            result.append(rec)

        return sorted(result, key=lambda r: r.recorded_at, reverse=True)
