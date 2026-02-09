"""
KPI Repository — Database-backed CRUD for KPI definitions, values, and dashboards.

All operations go through SQLAlchemy async session against the kpi_definitions,
kpi_values, and kpi_dashboards tables.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.kpi import (
    KPICategoryDB,
    KPIDashboardRow,
    KPIDefinitionRow,
    KPIDirectionDB,
    KPIStatusDB,
    KPIUnitDB,
    KPIValueRow,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_from_threshold(
    value: float,
    target: float | None,
    warning: float,
    critical: float,
    direction: str,
) -> KPIStatusDB:
    """Calculate KPI status from value and threshold config."""
    if target is None:
        return KPIStatusDB.NO_DATA
    if direction == "lower_is_better":
        deviation = value - target
    elif direction == "target_is_best":
        deviation = abs(value - target)
    else:  # higher_is_better
        deviation = target - value
    deviation_pct = (deviation / target * 100) if target != 0 else 0
    if deviation_pct >= critical:
        return KPIStatusDB.CRITICAL
    if deviation_pct >= warning:
        return KPIStatusDB.WARNING
    return KPIStatusDB.ON_TARGET


# ---------------------------------------------------------------------------
# Definition CRUD
# ---------------------------------------------------------------------------

async def create_definition(
    db: AsyncSession,
    *,
    name: str,
    description: str = "",
    category: str = "custom",
    unit: str = "count",
    direction: str = "higher_is_better",
    data_source: dict | None = None,
    formula: str = "",
    component_kpis: list[str] | None = None,
    threshold_target: float | None = None,
    threshold_warning: float = 10.0,
    threshold_critical: float = 20.0,
    threshold_min: float | None = None,
    threshold_max: float | None = None,
    decimal_places: int = 2,
    display_format: str = "",
    owner_role: str = "",
    frequency: str = "daily",
    is_active: bool = True,
    tags: list[str] | None = None,
    custom_calculator: str = "",
    is_default: bool = False,
    definition_id: UUID | None = None,
) -> KPIDefinitionRow:
    """Insert a new KPI definition into the database."""
    row = KPIDefinitionRow(
        id=definition_id or uuid4(),
        name=name,
        description=description,
        category=KPICategoryDB(category),
        unit=KPIUnitDB(unit),
        direction=KPIDirectionDB(direction),
        data_source=data_source,
        formula=formula,
        component_kpis=component_kpis or [],
        threshold_target=threshold_target,
        threshold_warning=threshold_warning,
        threshold_critical=threshold_critical,
        threshold_min=threshold_min,
        threshold_max=threshold_max,
        decimal_places=decimal_places,
        display_format=display_format,
        owner_role=owner_role,
        frequency=frequency,
        is_active=is_active,
        tags=tags or [],
        custom_calculator=custom_calculator,
        is_default=is_default,
    )
    db.add(row)
    await db.flush()
    return row


async def get_definition(db: AsyncSession, kpi_id: UUID) -> KPIDefinitionRow | None:
    """Fetch a single KPI definition by ID."""
    return await db.get(KPIDefinitionRow, kpi_id)


async def list_definitions(
    db: AsyncSession,
    *,
    category: str | None = None,
    active_only: bool = True,
    tags: list[str] | None = None,
) -> list[KPIDefinitionRow]:
    """List KPI definitions with optional filters."""
    stmt = select(KPIDefinitionRow)
    if active_only:
        stmt = stmt.where(KPIDefinitionRow.is_active.is_(True))
    if category:
        stmt = stmt.where(KPIDefinitionRow.category == KPICategoryDB(category))
    stmt = stmt.order_by(KPIDefinitionRow.name)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if tags:
        # JSONB array containment filter in Python (could also use @> operator)
        rows = [r for r in rows if any(t in (r.tags or []) for t in tags)]
    return rows


async def update_definition(
    db: AsyncSession,
    kpi_id: UUID,
    updates: dict[str, Any],
) -> KPIDefinitionRow | None:
    """Update a KPI definition in the database."""
    row = await db.get(KPIDefinitionRow, kpi_id)
    if not row:
        return None
    for key, value in updates.items():
        if key == "category" and isinstance(value, str):
            value = KPICategoryDB(value)
        elif key == "unit" and isinstance(value, str):
            value = KPIUnitDB(value)
        elif key == "direction" and isinstance(value, str):
            value = KPIDirectionDB(value)
        if hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    return row


async def delete_definition(db: AsyncSession, kpi_id: UUID) -> bool:
    """Delete a KPI definition and all its values."""
    row = await db.get(KPIDefinitionRow, kpi_id)
    if not row:
        return False
    await db.delete(row)
    await db.flush()
    return True


# ---------------------------------------------------------------------------
# Value CRUD
# ---------------------------------------------------------------------------

async def record_value(
    db: AsyncSession,
    *,
    kpi_id: UUID,
    value: float,
    recorded_at: datetime | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    dimensions: dict[str, str] | None = None,
    sample_size: int = 0,
    confidence: float = 1.0,
) -> KPIValueRow:
    """Record a new KPI value in the database."""
    # Calculate status from definition threshold
    defn = await db.get(KPIDefinitionRow, kpi_id)
    status = KPIStatusDB.NO_DATA
    if defn and defn.threshold_target is not None:
        status = _status_from_threshold(
            value,
            defn.threshold_target,
            defn.threshold_warning,
            defn.threshold_critical,
            defn.direction.value if isinstance(defn.direction, KPIDirectionDB) else str(defn.direction),
        )

    row = KPIValueRow(
        id=uuid4(),
        kpi_id=kpi_id,
        value=value,
        recorded_at=recorded_at or datetime.now(timezone.utc),
        period_start=period_start,
        period_end=period_end,
        status=status,
        dimensions=dimensions or {},
        sample_size=sample_size,
        confidence=confidence,
    )
    db.add(row)
    await db.flush()
    return row


async def get_latest_value(
    db: AsyncSession,
    kpi_id: UUID,
    dimensions: dict[str, str] | None = None,
) -> KPIValueRow | None:
    """Get the most recent value for a KPI."""
    stmt = (
        select(KPIValueRow)
        .where(KPIValueRow.kpi_id == kpi_id)
        .order_by(KPIValueRow.recorded_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_values(
    db: AsyncSession,
    kpi_id: UUID,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
) -> list[KPIValueRow]:
    """Get KPI values with optional date range filter."""
    stmt = (
        select(KPIValueRow)
        .where(KPIValueRow.kpi_id == kpi_id)
        .order_by(KPIValueRow.recorded_at.desc())
        .limit(limit)
    )
    if start_date:
        stmt = stmt.where(KPIValueRow.recorded_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        stmt = stmt.where(KPIValueRow.recorded_at <= datetime.combine(end_date, datetime.max.time()))
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Dashboard CRUD
# ---------------------------------------------------------------------------

async def create_dashboard(
    db: AsyncSession,
    *,
    name: str,
    description: str = "",
    kpi_ids: list[str] | None = None,
    layout: dict | None = None,
    default_time_range: str = "last_30_days",
    dimension_filters: dict | None = None,
    owner_id: str = "",
    is_public: bool = False,
    is_default: bool = False,
    dashboard_id: UUID | None = None,
) -> KPIDashboardRow:
    """Create a new dashboard in the database."""
    row = KPIDashboardRow(
        id=dashboard_id or uuid4(),
        name=name,
        description=description,
        kpi_ids=kpi_ids or [],
        layout=layout or {},
        default_time_range=default_time_range,
        dimension_filters=dimension_filters or {},
        owner_id=owner_id,
        is_public=is_public,
        is_default=is_default,
    )
    db.add(row)
    await db.flush()
    return row


async def get_dashboard(db: AsyncSession, dashboard_id: UUID) -> KPIDashboardRow | None:
    """Fetch a single dashboard by ID."""
    return await db.get(KPIDashboardRow, dashboard_id)


async def list_dashboards(
    db: AsyncSession,
    *,
    owner_id: str | None = None,
    include_public: bool = True,
) -> list[KPIDashboardRow]:
    """List dashboards with optional owner filter."""
    stmt = select(KPIDashboardRow)
    if owner_id and include_public:
        stmt = stmt.where(
            (KPIDashboardRow.owner_id == owner_id) | (KPIDashboardRow.is_public.is_(True))
        )
    elif owner_id:
        stmt = stmt.where(KPIDashboardRow.owner_id == owner_id)
    stmt = stmt.order_by(KPIDashboardRow.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_dashboard(
    db: AsyncSession,
    dashboard_id: UUID,
    updates: dict[str, Any],
) -> KPIDashboardRow | None:
    """Update a dashboard."""
    row = await db.get(KPIDashboardRow, dashboard_id)
    if not row:
        return None
    for key, value in updates.items():
        if hasattr(row, key):
            setattr(row, key, value)
    await db.flush()
    return row


async def delete_dashboard(db: AsyncSession, dashboard_id: UUID) -> bool:
    """Delete a dashboard."""
    row = await db.get(KPIDashboardRow, dashboard_id)
    if not row:
        return False
    await db.delete(row)
    await db.flush()
    return True


# ---------------------------------------------------------------------------
# Seed default KPIs (run once on first startup or migration)
# ---------------------------------------------------------------------------

_DEFAULT_KPIS: list[dict[str, Any]] = [
    {
        "name": "RFQ Completeness Score",
        "description": "Average completeness score of RFQs at qualification gate",
        "category": "rfq", "unit": "percentage", "direction": "higher_is_better",
        "threshold_target": 85, "threshold_warning": 10, "threshold_critical": 20,
        "data_source": {"entity_type": "rfq", "fields": ["completeness_score"], "aggregation": "average"},
        "tags": ["phase1", "quote-to-cash"],
    },
    {
        "name": "Quote Cycle Time",
        "description": "Average days from RFQ receipt to quote submission",
        "category": "quoting", "unit": "days", "direction": "lower_is_better",
        "threshold_target": 5, "threshold_warning": 20, "threshold_critical": 40,
        "tags": ["phase1", "quote-to-cash"],
    },
    {
        "name": "Quote Win Rate",
        "description": "Percentage of submitted quotes resulting in orders",
        "category": "quoting", "unit": "percentage", "direction": "higher_is_better",
        "threshold_target": 35, "threshold_warning": 15, "threshold_critical": 30,
        "tags": ["phase1", "quote-to-cash"],
    },
    {
        "name": "First Pass Yield",
        "description": "Percentage of units passing quality inspection on first attempt",
        "category": "quality", "unit": "percentage", "direction": "higher_is_better",
        "threshold_target": 95, "threshold_warning": 5, "threshold_critical": 10,
        "tags": ["phase1", "quality"],
    },
    {
        "name": "On-Time Delivery",
        "description": "Percentage of orders delivered on or before committed date",
        "category": "delivery", "unit": "percentage", "direction": "higher_is_better",
        "threshold_target": 98, "threshold_warning": 3, "threshold_critical": 8,
        "tags": ["phase1", "delivery"],
    },
    {
        "name": "OEE (Overall Equipment Effectiveness)",
        "description": "Combined availability × performance × quality metric",
        "category": "production", "unit": "percentage", "direction": "higher_is_better",
        "threshold_target": 85, "threshold_warning": 10, "threshold_critical": 20,
        "tags": ["phase1", "production"],
    },
    {
        "name": "Cost of Quality",
        "description": "Total cost attributed to non-conformances and rework",
        "category": "quality", "unit": "currency", "direction": "lower_is_better",
        "threshold_target": 5000, "threshold_warning": 20, "threshold_critical": 50,
        "tags": ["phase1", "quality", "finance"],
    },
    {
        "name": "Safety Incident Rate",
        "description": "Number of recordable safety incidents per 200,000 work hours",
        "category": "safety", "unit": "ratio", "direction": "lower_is_better",
        "threshold_target": 2.0, "threshold_warning": 25, "threshold_critical": 50,
        "tags": ["phase1", "safety"],
    },
]


async def seed_default_definitions(db: AsyncSession) -> int:
    """Insert default KPI definitions if the table is empty.

    Returns the number of definitions seeded.
    """
    count = (await db.execute(select(func.count()).select_from(KPIDefinitionRow))).scalar() or 0
    if count > 0:
        return 0

    created = 0
    for kpi in _DEFAULT_KPIS:
        await create_definition(db, is_default=True, **kpi)
        created += 1

    await db.commit()
    logger.info("Seeded %d default KPI definitions", created)
    return created
