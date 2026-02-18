"""Analytics Warehouse Export (Development Plan 21.9).

Implements:
- Daily Snapshots: automated state export to reporting-optimized store (Parquet-like).
- Dimensional Modeling: Fact/Dimension schemas for WO operations, NCs, Andon history.
- Cross-Domain Extraction: Finance, HR, Inventory, Quality, Ops, Sales, Maintenance, Projects pipelines for CEO dashboard.

Production-grade service using SQLAlchemy.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from sensei.models.analytics import (
    DailySnapshot as DailySnapshotModel,
    DimensionSchema as DimensionSchemaModel,
    FactSchema as FactSchemaModel,
    ExportedRecord as ExportedRecordModel,
)

logger = logging.getLogger(__name__)

DailySnapshot = DailySnapshotModel
DimensionSchema = DimensionSchemaModel
FactSchema = FactSchemaModel
ExportedRecord = ExportedRecordModel


class SnapshotStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DimensionType(str, Enum):
    TIME = "time"
    PART = "part"
    STATION = "station"
    OPERATOR = "operator"
    SHIFT = "shift"
    CUSTOMER = "customer"


class FactType(str, Enum):
    WORK_ORDER = "work_order"
    NON_CONFORMANCE = "non_conformance"
    ANDON_EVENT = "andon_event"
    CYCLE_TIME = "cycle_time"
    QUALITY_METRIC = "quality_metric"
    # Finance
    FINANCIAL_TRANSACTION = "financial_transaction"
    AP_INVOICE = "ap_invoice"
    AR_INVOICE = "ar_invoice"
    COST_ROLLUP = "cost_rollup"
    # HR
    HEADCOUNT_SNAPSHOT = "headcount_snapshot"
    EMPLOYEE_TURNOVER = "employee_turnover"
    TIME_TO_HIRE = "time_to_hire"
    TRAINING_COMPLIANCE = "training_compliance"
    # Inventory/Supply Chain
    INVENTORY_LEVEL = "inventory_level"
    STOCK_MOVEMENT = "stock_movement"
    MRP_EXCEPTION = "mrp_exception"
    # CRM / Sales
    OPPORTUNITY = "opportunity"
    RFQ_FACT = "rfq"
    QUOTE_FACT = "quote"
    SALES_ORDER_FACT = "sales_order"
    # Project Management
    PROJECT_FACT = "project"
    # A3 / Problem Solving
    A3_FACT = "a3"
    # Kanban
    KANBAN_FACT = "kanban"
    # Risk
    RISK_EVENT = "risk_event"
    # AI / ML
    ANOMALY_DETECTION = "anomaly_detection"
    MODEL_RETRAIN = "model_retrain"
    # Obeya / Visual Management
    OBEYA_METRIC = "obeya_metric"


_WAREHOUSE_ADMIN_ROLES: set[str] = {"admin", "bi", "exec", "ceo", "gm", "analyst", "finance", "hr"}

# RBAC scoping: map roles → which FactType categories they may query
_ROLE_FACT_ACCESS: dict[str, set[str]] = {
    # Full access
    "admin": {ft.value for ft in FactType},
    "ceo": {ft.value for ft in FactType},
    "gm": {ft.value for ft in FactType},
    "exec": {ft.value for ft in FactType},
    "bi": {ft.value for ft in FactType},
    "analyst": {ft.value for ft in FactType},
    # Finance scoped
    "finance": {
        FactType.FINANCIAL_TRANSACTION.value,
        FactType.AP_INVOICE.value,
        FactType.AR_INVOICE.value,
        FactType.COST_ROLLUP.value,
    },
    # HR scoped
    "hr": {
        FactType.HEADCOUNT_SNAPSHOT.value,
        FactType.EMPLOYEE_TURNOVER.value,
        FactType.TIME_TO_HIRE.value,
        FactType.TRAINING_COMPLIANCE.value,
    },
    # Ops scoped
    "ops": {
        FactType.WORK_ORDER.value,
        FactType.CYCLE_TIME.value,
        FactType.ANDON_EVENT.value,
        FactType.NON_CONFORMANCE.value,
        FactType.QUALITY_METRIC.value,
        FactType.INVENTORY_LEVEL.value,
        FactType.STOCK_MOVEMENT.value,
        FactType.MRP_EXCEPTION.value,
    },
    "quality": {
        FactType.WORK_ORDER.value,
        FactType.NON_CONFORMANCE.value,
        FactType.QUALITY_METRIC.value,
    },
    # Maintenance scoped
    "maintenance": {
        FactType.WORK_ORDER.value,
        FactType.CYCLE_TIME.value,
        FactType.ANDON_EVENT.value,
        FactType.QUALITY_METRIC.value,
    },
    # Supply chain scoped
    "supply_chain": {
        FactType.INVENTORY_LEVEL.value,
        FactType.STOCK_MOVEMENT.value,
        FactType.MRP_EXCEPTION.value,
        FactType.AP_INVOICE.value,
    },
    "purchasing": {
        FactType.AP_INVOICE.value,
        FactType.COST_ROLLUP.value,
        FactType.INVENTORY_LEVEL.value,
        FactType.STOCK_MOVEMENT.value,
        FactType.MRP_EXCEPTION.value,
    },
    "logistics": {
        FactType.INVENTORY_LEVEL.value,
        FactType.STOCK_MOVEMENT.value,
    },
    "warehouse": {
        FactType.INVENTORY_LEVEL.value,
        FactType.STOCK_MOVEMENT.value,
        FactType.MRP_EXCEPTION.value,
    },
    # Sales scoped
    "sales": {
        FactType.AR_INVOICE.value,
        FactType.FINANCIAL_TRANSACTION.value,
        FactType.OPPORTUNITY.value,
        FactType.RFQ_FACT.value,
        FactType.QUOTE_FACT.value,
        FactType.SALES_ORDER_FACT.value,
    },
    "sales_engineer": {
        FactType.OPPORTUNITY.value,
        FactType.RFQ_FACT.value,
        FactType.QUOTE_FACT.value,
        FactType.SALES_ORDER_FACT.value,
        FactType.COST_ROLLUP.value,
    },
    "estimator": {
        FactType.RFQ_FACT.value,
        FactType.QUOTE_FACT.value,
        FactType.COST_ROLLUP.value,
    },
    # Engineering scoped
    "engineering": {
        FactType.WORK_ORDER.value,
        FactType.CYCLE_TIME.value,
        FactType.QUALITY_METRIC.value,
        FactType.NON_CONFORMANCE.value,
        FactType.COST_ROLLUP.value,
        FactType.PROJECT_FACT.value,
        FactType.A3_FACT.value,
    },
    # Supervisor scoped
    "supervisor": {
        FactType.WORK_ORDER.value,
        FactType.CYCLE_TIME.value,
        FactType.ANDON_EVENT.value,
        FactType.NON_CONFORMANCE.value,
        FactType.QUALITY_METRIC.value,
        FactType.HEADCOUNT_SNAPSHOT.value,
        FactType.TRAINING_COMPLIANCE.value,
        FactType.PROJECT_FACT.value,
        FactType.A3_FACT.value,
        FactType.KANBAN_FACT.value,
        FactType.OBEYA_METRIC.value,
    },
    # Team lead scoped
    "team_lead": {
        FactType.WORK_ORDER.value,
        FactType.CYCLE_TIME.value,
        FactType.ANDON_EVENT.value,
        FactType.QUALITY_METRIC.value,
        FactType.KANBAN_FACT.value,
    },
    # Operator scoped
    "operator": {
        FactType.WORK_ORDER.value,
        FactType.QUALITY_METRIC.value,
        FactType.KANBAN_FACT.value,
    },
    # IT scoped
    "it": {
        FactType.QUALITY_METRIC.value,
        FactType.ANOMALY_DETECTION.value,
        FactType.MODEL_RETRAIN.value,
        FactType.PROJECT_FACT.value,
    },
    # Auditor — full read access
    "auditor": {ft.value for ft in FactType},
    # Risk scoped
    "risk": {
        FactType.RISK_EVENT.value,
        FactType.NON_CONFORMANCE.value,
        FactType.QUALITY_METRIC.value,
        FactType.A3_FACT.value,
    },
    # Project management scoped
    "project_manager": {
        FactType.PROJECT_FACT.value,
        FactType.A3_FACT.value,
        FactType.KANBAN_FACT.value,
        FactType.WORK_ORDER.value,
        FactType.CYCLE_TIME.value,
    },
}


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalyticsWarehouseService:
    """Production analytics warehouse export service."""

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_WAREHOUSE_ADMIN_ROLES)) > 0

    # ---- Daily Snapshots ----

    async def create_snapshot(
        self,
        db: AsyncSession,
        *,
        snapshot_date: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> DailySnapshotModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create snapshots")

        # Check idempotency.
        stmt = select(DailySnapshotModel).where(
            and_(
                DailySnapshotModel.snapshot_date == snapshot_date,
                DailySnapshotModel.status != SnapshotStatus.FAILED.value
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        snapshot = DailySnapshotModel(
            id=uuid4(),
            snapshot_date=snapshot_date,
            status=SnapshotStatus.PENDING.value,
            record_count=0,
            created_by_id=actor_user_id,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot

    async def get_or_create_snapshot(
        self,
        db: AsyncSession,
        *,
        snapshot_date: date,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> DailySnapshotModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to create snapshots")

        stmt = select(DailySnapshotModel).where(
            and_(
                DailySnapshotModel.snapshot_date == snapshot_date,
                DailySnapshotModel.status != SnapshotStatus.FAILED.value,
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        return await self.create_snapshot(
            db,
            snapshot_date=snapshot_date,
            actor_user_id=actor_user_id,
            actor_roles=actor_roles,
        )

    async def run_snapshot(
        self,
        db: AsyncSession,
        snapshot_id: UUID,
        *,
        actor_roles: Iterable[str],
        records: list[dict[str, Any]] | None = None,
    ) -> DailySnapshotModel:
        """Execute the snapshot export."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to run snapshots")
        
        stmt = select(DailySnapshotModel).where(DailySnapshotModel.id == snapshot_id)
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            raise KeyError("Snapshot not found")

        snapshot.status = SnapshotStatus.RUNNING.value
        snapshot.started_at = _utcnow()
        await db.flush()

        try:
            # Export records.
            for rec in records or []:
                fact_type = rec.get("_fact_type", FactType.WORK_ORDER.value)
                if isinstance(fact_type, FactType):
                    fact_type = fact_type.value
                
                exported = ExportedRecordModel(
                    id=uuid4(),
                    snapshot_id=snapshot_id,
                    fact_type=fact_type,
                    data=rec,
                )
                db.add(exported)

            snapshot.record_count = len(records or [])
            snapshot.status = SnapshotStatus.COMPLETED.value
            snapshot.completed_at = _utcnow()
            await db.flush()
        except Exception as e:
            snapshot.status = SnapshotStatus.FAILED.value
            snapshot.error_message = str(e)
            await db.flush()

        return snapshot

    async def append_exported_record(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        actor_user_id: UUID,
        fact_type: FactType,
        data: dict[str, Any],
        occurred_at: datetime | None = None,
    ) -> ExportedRecordModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to export records")

        snapshot_date = (occurred_at or _utcnow()).date()
        snapshot = await self.get_or_create_snapshot(
            db,
            snapshot_date=snapshot_date,
            actor_user_id=actor_user_id,
            actor_roles=actor_roles,
        )

        exported = ExportedRecordModel(
            id=uuid4(),
            snapshot_id=snapshot.id,
            fact_type=fact_type.value,
            data=data,
        )
        db.add(exported)

        snapshot.record_count = int(snapshot.record_count or 0) + 1
        if snapshot.status == SnapshotStatus.PENDING.value:
            snapshot.status = SnapshotStatus.COMPLETED.value
            snapshot.started_at = snapshot.started_at or _utcnow()
            snapshot.completed_at = _utcnow()

        await db.flush()
        return exported

    async def list_snapshots(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        status: SnapshotStatus | None = None,
    ) -> list[DailySnapshotModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view snapshots")

        stmt = select(DailySnapshotModel)
        if status:
            stmt = stmt.where(DailySnapshotModel.status == status.value)
        stmt = stmt.order_by(DailySnapshotModel.snapshot_date.desc())
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Dimensional Modeling ----

    async def register_dimension(
        self,
        db: AsyncSession,
        *,
        name: str,
        dim_type: DimensionType,
        key_column: str,
        attribute_columns: list[str],
        actor_roles: Iterable[str],
    ) -> DimensionSchemaModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage dimensions")

        dimension = DimensionSchemaModel(
            id=uuid4(),
            name=name.strip(),
            dim_type=dim_type.value,
            key_column=key_column,
            attribute_columns=list(attribute_columns),
        )
        db.add(dimension)
        await db.flush()
        return dimension

    async def register_fact(
        self,
        db: AsyncSession,
        *,
        name: str,
        fact_type: FactType,
        dimension_keys: list[str],
        measure_columns: list[str],
        actor_roles: Iterable[str],
    ) -> FactSchemaModel:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage facts")

        fact = FactSchemaModel(
            id=uuid4(),
            name=name.strip(),
            fact_type=fact_type.value,
            dimension_keys=list(dimension_keys),
            measure_columns=list(measure_columns),
        )
        db.add(fact)
        await db.flush()
        return fact

    async def list_dimensions(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> list[DimensionSchemaModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view dimensions")

        stmt = select(DimensionSchemaModel).order_by(DimensionSchemaModel.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def list_facts(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> list[FactSchemaModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view facts")

        stmt = select(FactSchemaModel).order_by(FactSchemaModel.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_snapshot(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> DailySnapshotModel | None:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view snapshots")

        stmt = (
            select(DailySnapshotModel)
            .order_by(DailySnapshotModel.snapshot_date.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_fact_counts(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        snapshot_id: UUID | None = None,
    ) -> dict[str, int]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view exported records")

        stmt = select(ExportedRecordModel.fact_type, func.count())
        if snapshot_id:
            stmt = stmt.where(ExportedRecordModel.snapshot_id == snapshot_id)
        stmt = stmt.group_by(ExportedRecordModel.fact_type)

        rows = (await db.execute(stmt)).all()
        return {str(row[0]): int(row[1]) for row in rows}

    async def get_exported_records(
        self,
        db: AsyncSession,
        snapshot_id: UUID | None = None,
        *,
        actor_roles: Iterable[str],
        fact_type: FactType | None = None,
    ) -> list[ExportedRecordModel]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view exported records")

        stmt = select(ExportedRecordModel)
        if snapshot_id:
            stmt = stmt.where(ExportedRecordModel.snapshot_id == snapshot_id)
        if fact_type:
            stmt = stmt.where(ExportedRecordModel.fact_type == fact_type.value)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- RBAC-Scoped Access ----

    def allowed_fact_types(self, *, actor_roles: Iterable[str]) -> set[str]:
        """Return the set of fact_type values the caller may query."""
        roles = _norm_roles(actor_roles)
        allowed: set[str] = set()
        for r in roles:
            allowed |= _ROLE_FACT_ACCESS.get(r, set())
        return allowed

    async def get_role_scoped_fact_counts(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        snapshot_id: UUID | None = None,
    ) -> dict[str, int]:
        """Like get_fact_counts but filters to only the fact types the caller may see."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view exported records")

        allowed = self.allowed_fact_types(actor_roles=actor_roles)
        if not allowed:
            return {}

        stmt = select(ExportedRecordModel.fact_type, func.count())
        if snapshot_id:
            stmt = stmt.where(ExportedRecordModel.snapshot_id == snapshot_id)
        stmt = stmt.where(ExportedRecordModel.fact_type.in_(allowed))
        stmt = stmt.group_by(ExportedRecordModel.fact_type)

        rows = (await db.execute(stmt)).all()
        return {str(row[0]): int(row[1]) for row in rows}

    async def get_role_scoped_records(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
        snapshot_id: UUID | None = None,
        fact_type: FactType | None = None,
        limit: int = 200,
    ) -> list[ExportedRecordModel]:
        """Return exported records filtered by the caller's RBAC scope."""
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view exported records")

        allowed = self.allowed_fact_types(actor_roles=actor_roles)
        if not allowed:
            return []

        stmt = select(ExportedRecordModel)
        if snapshot_id:
            stmt = stmt.where(ExportedRecordModel.snapshot_id == snapshot_id)
        if fact_type:
            if fact_type.value not in allowed:
                return []
            stmt = stmt.where(ExportedRecordModel.fact_type == fact_type.value)
        else:
            stmt = stmt.where(ExportedRecordModel.fact_type.in_(allowed))
        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ---- Cross-Domain Live Extraction (non-snapshot) ----

    async def extract_finance_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live finance KPIs from domain tables."""
        from sensei.models.finance import JournalEntry, JournalLine
        from sensei.models.accounts_payable import SupplierInvoice, PurchaseOrder
        from sensei.models.accounts_receivable import CustomerInvoice

        # AR: outstanding receivables
        ar_outstanding = int((await db.execute(
            select(func.count()).select_from(CustomerInvoice).where(
                CustomerInvoice.status.in_(["issued"])
            )
        )).scalar() or 0)

        ar_overdue = int((await db.execute(
            select(func.count()).select_from(CustomerInvoice).where(
                and_(
                    CustomerInvoice.status == "issued",
                    CustomerInvoice.due_date < _utcnow(),
                )
            )
        )).scalar() or 0)

        # AP: unpaid supplier invoices
        ap_unpaid = int((await db.execute(
            select(func.count()).select_from(SupplierInvoice).where(
                SupplierInvoice.status.in_(["draft", "submitted", "approved", "posted"])
            )
        )).scalar() or 0)

        # Open POs
        open_pos = int((await db.execute(
            select(func.count()).select_from(PurchaseOrder).where(
                PurchaseOrder.status.in_(["draft", "approved", "sent", "partially_received"])
            )
        )).scalar() or 0)

        # Journal entries this month
        month_start = _utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        journal_count = int((await db.execute(
            select(func.count()).select_from(JournalEntry).where(
                JournalEntry.created_at >= month_start
            )
        )).scalar() or 0)

        return {
            "ar_outstanding_count": ar_outstanding,
            "ar_overdue_count": ar_overdue,
            "ap_unpaid_count": ap_unpaid,
            "open_po_count": open_pos,
            "journal_entries_mtd": journal_count,
        }

    async def extract_hr_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live HR KPIs from domain tables."""
        from sensei.models.hr import EmployeeProfile, HRJobOpening, HRJobApplication, HRLeaveRequest

        active_employees = int((await db.execute(
            select(func.count()).select_from(EmployeeProfile).where(
                EmployeeProfile.status == "active"
            )
        )).scalar() or 0)

        terminated_recent = int((await db.execute(
            select(func.count()).select_from(EmployeeProfile).where(
                and_(
                    EmployeeProfile.status == "terminated",
                    EmployeeProfile.termination_date >= (_utcnow() - timedelta(days=90)),
                )
            )
        )).scalar() or 0)

        open_positions = int((await db.execute(
            select(func.count()).select_from(HRJobOpening).where(
                HRJobOpening.status == "open"
            )
        )).scalar() or 0)

        active_applications = int((await db.execute(
            select(func.count()).select_from(HRJobApplication).where(
                HRJobApplication.status.in_(["received", "screening", "interview", "offer"])
            )
        )).scalar() or 0)

        pending_leave = int((await db.execute(
            select(func.count()).select_from(HRLeaveRequest).where(
                HRLeaveRequest.status == "pending"
            )
        )).scalar() or 0)

        turnover_rate = round(
            (terminated_recent / max(active_employees, 1)) * 100, 1
        )

        return {
            "active_employees": active_employees,
            "terminated_last_90d": terminated_recent,
            "turnover_rate_pct": turnover_rate,
            "open_positions": open_positions,
            "active_applications": active_applications,
            "pending_leave_requests": pending_leave,
        }

    async def extract_inventory_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live inventory KPIs from domain tables."""
        from sensei.models.inventory import InventoryLevel, StockMove
        from sensei.models.mrp import MRPSuggestion

        total_skus = int((await db.execute(
            select(func.count(func.distinct(InventoryLevel.product_id)))
        )).scalar() or 0)

        low_stock_items = int((await db.execute(
            select(func.count()).select_from(InventoryLevel).where(
                InventoryLevel.quantity_on_hand <= 0
            )
        )).scalar() or 0)

        pending_moves = int((await db.execute(
            select(func.count()).select_from(StockMove).where(
                StockMove.status.in_(["draft", "waiting", "confirmed"])
            )
        )).scalar() or 0)

        open_mrp_suggestions = int((await db.execute(
            select(func.count()).select_from(MRPSuggestion).where(
                MRPSuggestion.status == "pending"
            )
        )).scalar() or 0)

        return {
            "tracked_skus": total_skus,
            "zero_stock_items": low_stock_items,
            "pending_stock_moves": pending_moves,
            "open_mrp_suggestions": open_mrp_suggestions,
        }

    async def extract_quality_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live quality KPIs from domain tables."""
        from sensei.models.quality import NonConformance, CAPA, NCStatus, NCSeverity, CAPAStatus

        open_ncs = int((await db.execute(
            select(func.count()).select_from(NonConformance).where(
                NonConformance.status == NCStatus.OPEN
            )
        )).scalar() or 0)

        critical_ncs = int((await db.execute(
            select(func.count()).select_from(NonConformance).where(
                NonConformance.severity == NCSeverity.CRITICAL
            )
        )).scalar() or 0)

        open_capas = int((await db.execute(
            select(func.count()).select_from(CAPA).where(
                CAPA.status.in_([CAPAStatus.OPEN, CAPAStatus.IN_PROGRESS, CAPAStatus.INVESTIGATING])
            )
        )).scalar() or 0)

        overdue_capas = int((await db.execute(
            select(func.count()).select_from(CAPA).where(
                and_(
                    CAPA.status.in_([CAPAStatus.OPEN, CAPAStatus.IN_PROGRESS]),
                    CAPA.due_date < _utcnow(),
                )
            )
        )).scalar() or 0)

        closed_capas_90d = int((await db.execute(
            select(func.count()).select_from(CAPA).where(
                and_(
                    CAPA.status == CAPAStatus.CLOSED,
                    CAPA.closed_at >= (_utcnow() - timedelta(days=90)),
                )
            )
        )).scalar() or 0)

        return {
            "open_ncs": open_ncs,
            "critical_ncs": critical_ncs,
            "open_capas": open_capas,
            "overdue_capas": overdue_capas,
            "closed_capas_last_90d": closed_capas_90d,
        }

    async def extract_operations_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live operations KPIs from domain tables."""
        from sensei.models.work_order import WorkOrder, WorkOrderStatus
        from sensei.models.andon import AndonEvent, AndonStatus

        active_wos = int((await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status.in_([WorkOrderStatus.RELEASED, WorkOrderStatus.IN_PROGRESS])
            )
        )).scalar() or 0)

        on_hold_wos = int((await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                WorkOrder.status == WorkOrderStatus.ON_HOLD
            )
        )).scalar() or 0)

        completed_wos_30d = int((await db.execute(
            select(func.count()).select_from(WorkOrder).where(
                and_(
                    WorkOrder.status == WorkOrderStatus.COMPLETED,
                    WorkOrder.actual_end >= (_utcnow() - timedelta(days=30)),
                )
            )
        )).scalar() or 0)

        active_andons = int((await db.execute(
            select(func.count()).select_from(AndonEvent).where(
                AndonEvent.status.in_([AndonStatus.OPEN, AndonStatus.ACKNOWLEDGED, AndonStatus.ESCALATED])
            )
        )).scalar() or 0)

        resolved_andons_7d = int((await db.execute(
            select(func.count()).select_from(AndonEvent).where(
                and_(
                    AndonEvent.status == AndonStatus.RESOLVED,
                    AndonEvent.resolved_at >= (_utcnow() - timedelta(days=7)),
                )
            )
        )).scalar() or 0)

        return {
            "active_work_orders": active_wos,
            "on_hold_work_orders": on_hold_wos,
            "completed_work_orders_30d": completed_wos_30d,
            "active_andons": active_andons,
            "resolved_andons_7d": resolved_andons_7d,
        }

    async def extract_sales_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live sales KPIs from domain tables."""
        from sensei.models.opportunity import Opportunity, OpportunityStage
        from sensei.models.rfq import RFQ, RFQStatus
        from sensei.models.quote import Quote, QuoteStatus

        open_opportunities = int((await db.execute(
            select(func.count()).select_from(Opportunity).where(
                Opportunity.stage.in_([
                    OpportunityStage.PROSPECTING,
                    OpportunityStage.QUALIFICATION,
                    OpportunityStage.NEEDS_ANALYSIS,
                    OpportunityStage.VALUE_PROPOSITION,
                    OpportunityStage.PROPOSAL,
                    OpportunityStage.NEGOTIATION,
                ])
            )
        )).scalar() or 0)

        won_opportunities_90d = int((await db.execute(
            select(func.count()).select_from(Opportunity).where(
                and_(
                    Opportunity.stage == OpportunityStage.CLOSED_WON,
                    Opportunity.closed_at >= (_utcnow() - timedelta(days=90)),
                )
            )
        )).scalar() or 0)

        active_rfqs = int((await db.execute(
            select(func.count()).select_from(RFQ).where(
                RFQ.status.in_([RFQStatus.DRAFT, RFQStatus.SUBMITTED, RFQStatus.UNDER_REVIEW, RFQStatus.CLARIFICATION_NEEDED])
            )
        )).scalar() or 0)

        pending_quotes = int((await db.execute(
            select(func.count()).select_from(Quote).where(
                Quote.status.in_([QuoteStatus.DRAFT, QuoteStatus.PENDING_REVIEW, QuoteStatus.PENDING_APPROVAL])
            )
        )).scalar() or 0)

        submitted_quotes_30d = int((await db.execute(
            select(func.count()).select_from(Quote).where(
                and_(
                    Quote.status == QuoteStatus.SUBMITTED,
                    Quote.submitted_at >= (_utcnow() - timedelta(days=30)),
                )
            )
        )).scalar() or 0)

        return {
            "open_opportunities": open_opportunities,
            "won_opportunities_90d": won_opportunities_90d,
            "active_rfqs": active_rfqs,
            "pending_quotes": pending_quotes,
            "submitted_quotes_30d": submitted_quotes_30d,
        }

    async def extract_maintenance_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live maintenance KPIs from domain tables."""
        from sensei.models.maintenance import (
            Asset,
            MaintenanceWorkOrder,
            PMSchedule,
            DowntimeEvent,
        )

        total_assets = int((await db.execute(
            select(func.count()).select_from(Asset).where(
                Asset.status == "active"
            )
        )).scalar() or 0)

        open_mwos = int((await db.execute(
            select(func.count()).select_from(MaintenanceWorkOrder).where(
                MaintenanceWorkOrder.status.in_(["draft", "scheduled", "in_progress"])
            )
        )).scalar() or 0)

        overdue_pms = int((await db.execute(
            select(func.count()).select_from(PMSchedule).where(
                PMSchedule.next_due_date < _utcnow()
            )
        )).scalar() or 0)

        active_downtime = int((await db.execute(
            select(func.count()).select_from(DowntimeEvent).where(
                DowntimeEvent.end_time.is_(None)
            )
        )).scalar() or 0)

        return {
            "active_assets": total_assets,
            "open_maintenance_work_orders": open_mwos,
            "overdue_pm_schedules": overdue_pms,
            "active_downtime_events": active_downtime,
        }

    async def extract_project_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live project management KPIs from domain tables."""
        from sensei.models.project_management import (
            Project,
            ProjectStatus,
            UserStory,
            UserStoryStatus,
            Sprint,
            SprintStatus,
            Issue,
            IssueStatus,
        )

        active_projects = int((await db.execute(
            select(func.count()).select_from(Project).where(
                Project.status.in_([ProjectStatus.ACTIVE, ProjectStatus.IN_PROGRESS])
            )
        )).scalar() or 0)

        open_stories = int((await db.execute(
            select(func.count()).select_from(UserStory).where(
                UserStory.status.in_([UserStoryStatus.BACKLOG, UserStoryStatus.TODO, UserStoryStatus.IN_PROGRESS])
            )
        )).scalar() or 0)

        active_sprints = int((await db.execute(
            select(func.count()).select_from(Sprint).where(
                Sprint.status == SprintStatus.ACTIVE
            )
        )).scalar() or 0)

        open_issues = int((await db.execute(
            select(func.count()).select_from(Issue).where(
                Issue.status.in_([IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.BLOCKED])
            )
        )).scalar() or 0)

        return {
            "active_projects": active_projects,
            "open_user_stories": open_stories,
            "active_sprints": active_sprints,
            "open_issues": open_issues,
        }

    async def extract_obeya_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull live Obeya SQDCP metrics for visual management dashboard."""
        from sensei.models.cognitive_obeya import MetricRecord
        from sensei.core.enums import MetricStatus, MetricCategory

        now = _utcnow()
        seven_days_ago = now - timedelta(days=7)

        # Get overall metric health (Red/Yellow/Green counts)
        red_metrics = int((await db.execute(
            select(func.count()).select_from(MetricRecord).where(
                and_(
                    MetricRecord.status == MetricStatus.RED,
                    MetricRecord.timestamp >= seven_days_ago,
                )
            )
        )).scalar() or 0)

        yellow_metrics = int((await db.execute(
            select(func.count()).select_from(MetricRecord).where(
                and_(
                    MetricRecord.status == MetricStatus.YELLOW,
                    MetricRecord.timestamp >= seven_days_ago,
                )
            )
        )).scalar() or 0)

        green_metrics = int((await db.execute(
            select(func.count()).select_from(MetricRecord).where(
                and_(
                    MetricRecord.status == MetricStatus.GREEN,
                    MetricRecord.timestamp >= seven_days_ago,
                )
            )
        )).scalar() or 0)

        # Counts by SQDCP category
        category_counts: dict[str, int] = {}
        for cat in [MetricCategory.SAFETY, MetricCategory.QUALITY, MetricCategory.DELIVERY, MetricCategory.COST, MetricCategory.PEOPLE]:
            cat_count = int((await db.execute(
                select(func.count()).select_from(MetricRecord).where(
                    and_(
                        MetricRecord.category == cat,
                        MetricRecord.timestamp >= seven_days_ago,
                    )
                )
            )).scalar() or 0)
            category_counts[cat.value] = cat_count

        total_metrics_7d = red_metrics + yellow_metrics + green_metrics

        return {
            "red_metrics_7d": red_metrics,
            "yellow_metrics_7d": yellow_metrics,
            "green_metrics_7d": green_metrics,
            "total_metrics_7d": total_metrics_7d,
            "category_counts": category_counts,
            "health_score": round((green_metrics / max(total_metrics_7d, 1)) * 100, 1),
        }

    async def extract_ai_summary(self, db: AsyncSession) -> dict[str, Any]:
        """Pull AI/ML activity summary for analytics dashboard."""
        from sensei.models.reasoning_trace import ReasoningTrace
        from sensei.models.service_persistence import EmailDraftDB

        now = _utcnow()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # AI reasoning traces (suggestions made by AI)
        ai_suggestions_7d = int((await db.execute(
            select(func.count()).select_from(ReasoningTrace).where(
                ReasoningTrace.created_at >= seven_days_ago
            )
        )).scalar() or 0)

        ai_suggestions_30d = int((await db.execute(
            select(func.count()).select_from(ReasoningTrace).where(
                ReasoningTrace.created_at >= thirty_days_ago
            )
        )).scalar() or 0)

        # AI email drafts generated
        email_drafts_7d = int((await db.execute(
            select(func.count()).select_from(EmailDraftDB).where(
                EmailDraftDB.created_at >= seven_days_ago
            )
        )).scalar() or 0)

        email_drafts_30d = int((await db.execute(
            select(func.count()).select_from(EmailDraftDB).where(
                EmailDraftDB.created_at >= thirty_days_ago
            )
        )).scalar() or 0)

        # Total AI activity
        total_ai_activity_7d = ai_suggestions_7d + email_drafts_7d
        total_ai_activity_30d = ai_suggestions_30d + email_drafts_30d

        return {
            "ai_suggestions_7d": ai_suggestions_7d,
            "ai_suggestions_30d": ai_suggestions_30d,
            "email_drafts_7d": email_drafts_7d,
            "email_drafts_30d": email_drafts_30d,
            "total_ai_activity_7d": total_ai_activity_7d,
            "total_ai_activity_30d": total_ai_activity_30d,
        }

    async def build_cross_domain_summary(
        self,
        db: AsyncSession,
        *,
        actor_roles: Iterable[str],
    ) -> dict[str, Any]:
        """Unified cross-domain summary respecting RBAC.

        CEO/admin/exec see everything; finance role sees only finance; etc.
        """
        roles = _norm_roles(actor_roles)
        allowed = self.allowed_fact_types(actor_roles=actor_roles)
        summary: dict[str, Any] = {}

        # Check if role may see finance facts
        if FactType.FINANCIAL_TRANSACTION.value in allowed:
            try:
                summary["finance"] = await self.extract_finance_summary(db)
            except Exception as e:
                logger.warning("Failed to extract finance summary: %s", e)
                summary["finance"] = {"error": str(e)}

        # Check if role may see HR facts
        if FactType.HEADCOUNT_SNAPSHOT.value in allowed:
            try:
                summary["hr"] = await self.extract_hr_summary(db)
            except Exception as e:
                logger.warning("Failed to extract HR summary: %s", e)
                summary["hr"] = {"error": str(e)}

        # Check if role may see inventory facts
        if FactType.INVENTORY_LEVEL.value in allowed:
            try:
                summary["inventory"] = await self.extract_inventory_summary(db)
            except Exception as e:
                logger.warning("Failed to extract inventory summary: %s", e)
                summary["inventory"] = {"error": str(e)}

        # Check if role may see quality facts
        if FactType.NON_CONFORMANCE.value in allowed or FactType.QUALITY_METRIC.value in allowed:
            try:
                summary["quality"] = await self.extract_quality_summary(db)
            except Exception as e:
                logger.warning("Failed to extract quality summary: %s", e)
                summary["quality"] = {"error": str(e)}

        # Check if role may see operations facts
        if FactType.WORK_ORDER.value in allowed or FactType.ANDON_EVENT.value in allowed:
            try:
                summary["operations"] = await self.extract_operations_summary(db)
            except Exception as e:
                logger.warning("Failed to extract operations summary: %s", e)
                summary["operations"] = {"error": str(e)}

        # Check if role may see sales facts
        if FactType.OPPORTUNITY.value in allowed or FactType.RFQ_FACT.value in allowed:
            try:
                summary["sales"] = await self.extract_sales_summary(db)
            except Exception as e:
                logger.warning("Failed to extract sales summary: %s", e)
                summary["sales"] = {"error": str(e)}

        # Check if role may see project facts
        if FactType.PROJECT_FACT.value in allowed or FactType.A3_FACT.value in allowed:
            try:
                summary["projects"] = await self.extract_project_summary(db)
            except Exception as e:
                logger.warning("Failed to extract project summary: %s", e)
                summary["projects"] = {"error": str(e)}

        # Check if role may see maintenance facts (related to operations)
        if FactType.WORK_ORDER.value in allowed:
            try:
                summary["maintenance"] = await self.extract_maintenance_summary(db)
            except Exception as e:
                logger.warning("Failed to extract maintenance summary: %s", e)
                summary["maintenance"] = {"error": str(e)}

        # Check if role may see Obeya metrics
        if FactType.OBEYA_METRIC.value in allowed:
            try:
                summary["obeya"] = await self.extract_obeya_summary(db)
            except Exception as e:
                logger.warning("Failed to extract Obeya summary: %s", e)
                summary["obeya"] = {"error": str(e)}

        # Check if role may see AI/ML facts
        if FactType.ANOMALY_DETECTION.value in allowed or FactType.MODEL_RETRAIN.value in allowed:
            try:
                summary["ai"] = await self.extract_ai_summary(db)
            except Exception as e:
                logger.warning("Failed to extract AI summary: %s", e)
                summary["ai"] = {"error": str(e)}

        return summary
