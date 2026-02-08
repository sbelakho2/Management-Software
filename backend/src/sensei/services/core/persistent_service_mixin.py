"""Mixin and helpers for persisting in-memory service state to PostgreSQL.

Provides two persistence strategies:

1. **Dedicated-table strategy** (for domain services with proper table schemas):
   Subclass creates SQLAlchemy models and uses BaseRepository directly.

2. **Generic key-value strategy** (for remaining services without dedicated tables):
   Uses the ``service_state`` table to persist arbitrary JSON keyed by
   (tenant_id, service_name, state_key). Good for services that only need
   to save/load a handful of config or state dicts.

Checklist items addressed: #1-42, #44-64

Example usage::

    class CompensationService(PersistentServiceMixin):
        SERVICE_NAME = "compensation_management"

        async def get_bands(self, tenant_id: UUID) -> list[dict]:
            # Try DB first
            bands = await self.load_state(tenant_id, "pay_bands")
            if bands:
                return bands["items"]
            # Fallback to in-memory
            return self._in_memory_bands.get(str(tenant_id), [])

        async def save_bands(self, tenant_id: UUID, bands: list[dict]):
            self._in_memory_bands[str(tenant_id)] = bands
            # Persist to DB asynchronously
            await self.save_state(tenant_id, "pay_bands", {"items": bands})
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)


class PersistentServiceMixin:
    """Mixin that adds PostgreSQL persistence to any in-memory service.

    Subclasses set ``SERVICE_NAME`` and optionally override ``_get_session``
    to provide the async SQLAlchemy session factory.

    The mixin uses the ``service_state`` table (a generic key-value store)
    for services that don't yet have dedicated tables. Services with
    dedicated tables should use BaseRepository instead.
    """

    SERVICE_NAME: str = "unknown_service"

    # Injected by DI container or overridden in __init__
    _session_factory: Any = None

    def set_session_factory(self, session_factory: Any) -> None:
        """Inject the async session factory (e.g. ``async_sessionmaker``)."""
        self._session_factory = session_factory

    async def _get_session(self):
        """Get an async session. Override for custom session management."""
        if self._session_factory is None:
            raise RuntimeError(
                f"{self.SERVICE_NAME}: No session factory configured. "
                "Call set_session_factory() or override _get_session()."
            )
        return self._session_factory()

    # -----------------------------------------------------------------
    # Generic state persistence (service_state table)
    # -----------------------------------------------------------------

    async def save_state(
        self,
        tenant_id: UUID,
        state_key: str,
        state_data: dict,
    ) -> None:
        """Upsert a state entry in the service_state table.

        Uses PostgreSQL ON CONFLICT for atomic upsert with version bump.
        """
        try:
            async with await self._get_session() as session:
                stmt = text("""
                    INSERT INTO service_state (tenant_id, service_name, state_key, state_data, version, updated_at)
                    VALUES (:tenant_id, :service_name, :state_key, :state_data::jsonb, 1, NOW())
                    ON CONFLICT (tenant_id, service_name, state_key)
                    DO UPDATE SET
                        state_data = EXCLUDED.state_data,
                        version = service_state.version + 1,
                        updated_at = NOW()
                """)
                await session.execute(
                    stmt,
                    {
                        "tenant_id": str(tenant_id),
                        "service_name": self.SERVICE_NAME,
                        "state_key": state_key,
                        "state_data": _to_json(state_data),
                    },
                )
                await session.commit()
        except Exception:
            logger.warning(
                "Failed to persist state for %s/%s — falling back to in-memory",
                self.SERVICE_NAME,
                state_key,
                exc_info=True,
            )

    async def load_state(
        self,
        tenant_id: UUID,
        state_key: str,
    ) -> Optional[dict]:
        """Load a state entry from the service_state table.

        Returns ``None`` if not found.
        """
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT state_data FROM service_state
                        WHERE tenant_id = :tenant_id
                          AND service_name = :service_name
                          AND state_key = :state_key
                    """),
                    {
                        "tenant_id": str(tenant_id),
                        "service_name": self.SERVICE_NAME,
                        "state_key": state_key,
                    },
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception:
            logger.warning(
                "Failed to load state for %s/%s — using in-memory only",
                self.SERVICE_NAME,
                state_key,
                exc_info=True,
            )
            return None

    async def load_all_states(
        self,
        tenant_id: UUID,
    ) -> dict[str, dict]:
        """Load all state entries for this service and tenant."""
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT state_key, state_data FROM service_state
                        WHERE tenant_id = :tenant_id
                          AND service_name = :service_name
                        ORDER BY state_key
                    """),
                    {
                        "tenant_id": str(tenant_id),
                        "service_name": self.SERVICE_NAME,
                    },
                )
                return {row[0]: row[1] for row in result.fetchall()}
        except Exception:
            logger.warning(
                "Failed to load all states for %s — using in-memory only",
                self.SERVICE_NAME,
                exc_info=True,
            )
            return {}

    async def delete_state(
        self,
        tenant_id: UUID,
        state_key: str,
    ) -> None:
        """Delete a state entry."""
        try:
            async with await self._get_session() as session:
                await session.execute(
                    text("""
                        DELETE FROM service_state
                        WHERE tenant_id = :tenant_id
                          AND service_name = :service_name
                          AND state_key = :state_key
                    """),
                    {
                        "tenant_id": str(tenant_id),
                        "service_name": self.SERVICE_NAME,
                        "state_key": state_key,
                    },
                )
                await session.commit()
        except Exception:
            logger.warning(
                "Failed to delete state for %s/%s",
                self.SERVICE_NAME,
                state_key,
                exc_info=True,
            )

    # -----------------------------------------------------------------
    # Bulk operations for initial migration / sync
    # -----------------------------------------------------------------

    async def sync_in_memory_to_db(
        self,
        tenant_id: UUID,
        in_memory_data: dict[str, dict],
    ) -> int:
        """Bulk-sync all in-memory state entries to the database.

        Useful for one-time migration of existing in-memory data.
        Returns count of entries synced.
        """
        count = 0
        for key, data in in_memory_data.items():
            await self.save_state(tenant_id, key, data)
            count += 1
        logger.info(
            "Synced %d state entries for %s (tenant %s)",
            count,
            self.SERVICE_NAME,
            tenant_id,
        )
        return count

    async def hydrate_from_db(
        self,
        tenant_id: UUID,
    ) -> dict[str, dict]:
        """Load all persisted state back into memory on startup.

        Subclasses can override this to populate their specific
        in-memory data structures.
        """
        return await self.load_all_states(tenant_id)


class DedicatedTableRepository:
    """Base for services that use their own tables (not service_state).

    Provides common async CRUD patterns with tenant isolation.
    Services with dedicated migration tables should extend this
    instead of using PersistentServiceMixin's generic key-value store.
    """

    TABLE_NAME: str = ""

    def __init__(self, session_factory: Any = None):
        self._session_factory = session_factory

    async def _get_session(self):
        if self._session_factory is None:
            raise RuntimeError(
                f"No session factory configured for {self.TABLE_NAME}"
            )
        return self._session_factory()

    async def insert_row(
        self, tenant_id: UUID, data: dict
    ) -> Optional[str]:
        """Insert a row and return the generated UUID."""
        columns = ["tenant_id"] + list(data.keys())
        placeholders = [":tenant_id"] + [f":{k}" for k in data.keys()]
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text(
                        f"INSERT INTO {self.TABLE_NAME} "
                        f"({', '.join(columns)}) "
                        f"VALUES ({', '.join(placeholders)}) "
                        f"RETURNING id"
                    ),
                    {"tenant_id": str(tenant_id), **_stringify_uuids(data)},
                )
                row = result.fetchone()
                await session.commit()
                return str(row[0]) if row else None
        except Exception:
            logger.warning("insert_row failed for %s", self.TABLE_NAME, exc_info=True)
            return None

    async def update_row(
        self, row_id: UUID, data: dict
    ) -> bool:
        """Update a row by ID."""
        set_clause = ", ".join(f"{k} = :{k}" for k in data.keys())
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text(
                        f"UPDATE {self.TABLE_NAME} "
                        f"SET {set_clause}, updated_at = NOW() "
                        f"WHERE id = :id"
                    ),
                    {"id": str(row_id), **_stringify_uuids(data)},
                )
                await session.commit()
                return result.rowcount > 0
        except Exception:
            logger.warning("update_row failed for %s", self.TABLE_NAME, exc_info=True)
            return False

    async def soft_delete(self, row_id: UUID) -> bool:
        """Soft-delete a row by setting deleted_at."""
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text(
                        f"UPDATE {self.TABLE_NAME} "
                        f"SET deleted_at = NOW() "
                        f"WHERE id = :id AND deleted_at IS NULL"
                    ),
                    {"id": str(row_id)},
                )
                await session.commit()
                return result.rowcount > 0
        except Exception:
            logger.warning("soft_delete failed for %s", self.TABLE_NAME, exc_info=True)
            return False

    async def get_by_id(
        self, row_id: UUID
    ) -> Optional[dict]:
        """Get a single row by ID."""
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text(
                        f"SELECT * FROM {self.TABLE_NAME} "
                        f"WHERE id = :id AND (deleted_at IS NULL OR deleted_at > NOW())"
                    ),
                    {"id": str(row_id)},
                )
                row = result.mappings().fetchone()
                return dict(row) if row else None
        except Exception:
            logger.warning("get_by_id failed for %s", self.TABLE_NAME, exc_info=True)
            return None

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at DESC",
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """List rows for a tenant with pagination and optional filters."""
        where_clauses = ["tenant_id = :tenant_id", "(deleted_at IS NULL OR deleted_at > NOW())"]
        params: dict = {"tenant_id": str(tenant_id), "limit": limit, "offset": offset}

        if filters:
            for i, (col, val) in enumerate(filters.items()):
                param_name = f"filter_{i}"
                where_clauses.append(f"{col} = :{param_name}")
                params[param_name] = val

        where_sql = " AND ".join(where_clauses)
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text(
                        f"SELECT * FROM {self.TABLE_NAME} "
                        f"WHERE {where_sql} "
                        f"ORDER BY {order_by} "
                        f"LIMIT :limit OFFSET :offset"
                    ),
                    params,
                )
                return [dict(row) for row in result.mappings().fetchall()]
        except Exception:
            logger.warning("list_for_tenant failed for %s", self.TABLE_NAME, exc_info=True)
            return []

    async def count_for_tenant(
        self,
        tenant_id: UUID,
        filters: Optional[dict] = None,
    ) -> int:
        """Count rows for a tenant."""
        where_clauses = ["tenant_id = :tenant_id", "(deleted_at IS NULL OR deleted_at > NOW())"]
        params: dict = {"tenant_id": str(tenant_id)}

        if filters:
            for i, (col, val) in enumerate(filters.items()):
                param_name = f"filter_{i}"
                where_clauses.append(f"{col} = :{param_name}")
                params[param_name] = val

        where_sql = " AND ".join(where_clauses)
        try:
            async with await self._get_session() as session:
                result = await session.execute(
                    text(
                        f"SELECT COUNT(*) FROM {self.TABLE_NAME} "
                        f"WHERE {where_sql}"
                    ),
                    params,
                )
                row = result.fetchone()
                return row[0] if row else 0
        except Exception:
            logger.warning("count_for_tenant failed for %s", self.TABLE_NAME, exc_info=True)
            return 0


# -----------------------------------------------------------------
# Concrete repositories for each service domain
# -----------------------------------------------------------------

class GLAccountRepository(DedicatedTableRepository):
    TABLE_NAME = "gl_accounts"

class JournalEntryRepository(DedicatedTableRepository):
    TABLE_NAME = "journal_entries"

class APInvoiceRepository(DedicatedTableRepository):
    TABLE_NAME = "ap_invoices"

class APPaymentRepository(DedicatedTableRepository):
    TABLE_NAME = "ap_payments"

class PurchaseOrderRepository(DedicatedTableRepository):
    TABLE_NAME = "purchase_orders"

class GoodsReceiptRepository(DedicatedTableRepository):
    TABLE_NAME = "goods_receipts"

class ARInvoiceRepository(DedicatedTableRepository):
    TABLE_NAME = "ar_invoices"

class ARPaymentRepository(DedicatedTableRepository):
    TABLE_NAME = "ar_payments"

class CreditMemoRepository(DedicatedTableRepository):
    TABLE_NAME = "credit_memos"

class CostCenterRepository(DedicatedTableRepository):
    TABLE_NAME = "cost_centers"

class CostAllocationRepository(DedicatedTableRepository):
    TABLE_NAME = "cost_allocations"

class FixedAssetRepository(DedicatedTableRepository):
    TABLE_NAME = "fixed_assets"

class DepreciationScheduleRepository(DedicatedTableRepository):
    TABLE_NAME = "depreciation_schedules"

class LaborRateRepository(DedicatedTableRepository):
    TABLE_NAME = "labor_rates"

class TimeEntryRepository(DedicatedTableRepository):
    TABLE_NAME = "time_entries"

class PayrollBatchRepository(DedicatedTableRepository):
    TABLE_NAME = "payroll_batches"

class TaxRateRepository(DedicatedTableRepository):
    TABLE_NAME = "tax_rates"

class CostRollupRepository(DedicatedTableRepository):
    TABLE_NAME = "cost_rollups"

class CompensationRecordRepository(DedicatedTableRepository):
    TABLE_NAME = "compensation_records"

class PayBandRepository(DedicatedTableRepository):
    TABLE_NAME = "pay_bands"

class LeaveBalanceRepository(DedicatedTableRepository):
    TABLE_NAME = "leave_balances"

class LeaveRequestRepository(DedicatedTableRepository):
    TABLE_NAME = "leave_requests"

class EmployeeLifecycleRepository(DedicatedTableRepository):
    TABLE_NAME = "employee_lifecycle_events"

class JobPostingRepository(DedicatedTableRepository):
    TABLE_NAME = "job_postings"

class ShiftScheduleRepository(DedicatedTableRepository):
    TABLE_NAME = "shift_schedules"

class RosterAssignmentRepository(DedicatedTableRepository):
    TABLE_NAME = "roster_assignments"

class PerformanceReviewRepository(DedicatedTableRepository):
    TABLE_NAME = "performance_reviews"

class PerformanceGoalRepository(DedicatedTableRepository):
    TABLE_NAME = "performance_goals"

class HRCaseRepository(DedicatedTableRepository):
    TABLE_NAME = "hr_cases"

class MRPRunRepository(DedicatedTableRepository):
    TABLE_NAME = "mrp_runs"

class WMSLocationRepository(DedicatedTableRepository):
    TABLE_NAME = "wms_locations"

class WMSInventoryRepository(DedicatedTableRepository):
    TABLE_NAME = "wms_inventory"

class WMSPickTaskRepository(DedicatedTableRepository):
    TABLE_NAME = "wms_pick_tasks"

class WMSShipmentRepository(DedicatedTableRepository):
    TABLE_NAME = "wms_shipments"

class LotRecordRepository(DedicatedTableRepository):
    TABLE_NAME = "lot_records"

class SPCMeasurementRepository(DedicatedTableRepository):
    TABLE_NAME = "spc_measurements"

class COPQRecordRepository(DedicatedTableRepository):
    TABLE_NAME = "copq_records"

class DispatchTravelerRepository(DedicatedTableRepository):
    TABLE_NAME = "dispatch_travelers"

class LabelTemplateRepository(DedicatedTableRepository):
    TABLE_NAME = "label_templates"

class ProductionScheduleRepository(DedicatedTableRepository):
    TABLE_NAME = "production_schedules"

class TPMAssetRepository(DedicatedTableRepository):
    TABLE_NAME = "tpm_assets"

class PMScheduleRepository(DedicatedTableRepository):
    TABLE_NAME = "pm_schedules"

class TPMWorkOrderRepository(DedicatedTableRepository):
    TABLE_NAME = "tpm_work_orders"

class DowntimeEventRepository(DedicatedTableRepository):
    TABLE_NAME = "downtime_events"

class SparePartRepository(DedicatedTableRepository):
    TABLE_NAME = "spare_parts_inventory"

class QualityDocumentRepository(DedicatedTableRepository):
    TABLE_NAME = "quality_documents"

class InternalAuditRepository(DedicatedTableRepository):
    TABLE_NAME = "internal_audits"

class AuditFindingRepository(DedicatedTableRepository):
    TABLE_NAME = "audit_findings"

class GaugeCalibrRepository(DedicatedTableRepository):
    TABLE_NAME = "gauge_calibrations"

class SupplierCARRepository(DedicatedTableRepository):
    TABLE_NAME = "supplier_corrective_actions"

class RiskAssessmentRepository(DedicatedTableRepository):
    TABLE_NAME = "risk_assessments"

class ECORepository(DedicatedTableRepository):
    TABLE_NAME = "engineering_change_orders"

class SearchDocumentRepository(DedicatedTableRepository):
    TABLE_NAME = "search_documents"

class AIPatternRepository(DedicatedTableRepository):
    TABLE_NAME = "ai_patterns"

class RAGChunkRepository(DedicatedTableRepository):
    TABLE_NAME = "rag_chunks"

class RAGFeedbackRepository(DedicatedTableRepository):
    TABLE_NAME = "rag_feedback"

class AnomalyAlertRepository(DedicatedTableRepository):
    TABLE_NAME = "anomaly_alerts"

class AITrainingJobRepository(DedicatedTableRepository):
    TABLE_NAME = "ai_training_jobs"

class BackupScheduleRepository(DedicatedTableRepository):
    TABLE_NAME = "backup_schedules"

class BackupHistoryRepository(DedicatedTableRepository):
    TABLE_NAME = "backup_history"

class NotificationRuleRepository(DedicatedTableRepository):
    TABLE_NAME = "notification_rules"

class NotificationLogRepository(DedicatedTableRepository):
    TABLE_NAME = "notification_log"

class EmailDraftRepository(DedicatedTableRepository):
    TABLE_NAME = "email_drafts"

class TaskTimingRepository(DedicatedTableRepository):
    TABLE_NAME = "task_timing_sessions"

class SupplierTokenRepository(DedicatedTableRepository):
    TABLE_NAME = "supplier_tokens"

class ServiceStateRepository(DedicatedTableRepository):
    TABLE_NAME = "service_state"


# -----------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------

def _to_json(data: Any) -> str:
    """Convert data to a JSON string safe for PostgreSQL."""
    import json
    return json.dumps(data, default=str)


def _stringify_uuids(data: dict) -> dict:
    """Convert UUID values to strings for raw SQL params."""
    return {
        k: str(v) if isinstance(v, UUID) else v
        for k, v in data.items()
    }


# -----------------------------------------------------------------
# Registry of service names → repositories for DI
# -----------------------------------------------------------------

SERVICE_REPOSITORY_MAP: dict[str, type[DedicatedTableRepository]] = {
    "accounting_ledger": GLAccountRepository,
    "accounts_payable": APInvoiceRepository,
    "accounts_receivable": ARInvoiceRepository,
    "cost_accounting": CostCenterRepository,
    "fixed_assets": FixedAssetRepository,
    "payroll_labor": LaborRateRepository,
    "tax_service": TaxRateRepository,
    "cost_rollup": CostRollupRepository,
    "compensation": CompensationRecordRepository,
    "leave_management": LeaveBalanceRepository,
    "employee_lifecycle": EmployeeLifecycleRepository,
    "recruiting": JobPostingRepository,
    "staffing_roster": ShiftScheduleRepository,
    "talent_performance": PerformanceReviewRepository,
    "hr_cases": HRCaseRepository,
    "mrp_lite": MRPRunRepository,
    "wms_integration": WMSInventoryRepository,
    "lot_traceability": LotRecordRepository,
    "spc_scrap_rework": SPCMeasurementRepository,
    "dispatch_traveler": DispatchTravelerRepository,
    "label_printing": LabelTemplateRepository,
    "production_scheduling": ProductionScheduleRepository,
    "maintenance_tpm": TPMAssetRepository,
    "quality_documents": QualityDocumentRepository,
    "internal_audits": InternalAuditRepository,
    "gauge_calibration": GaugeCalibrRepository,
    "supplier_car": SupplierCARRepository,
    "risk_assessment": RiskAssessmentRepository,
    "eco": ECORepository,
    "hybrid_search": SearchDocumentRepository,
    "ai_reasoning": AIPatternRepository,
    "rag": RAGChunkRepository,
    "anomaly_detection": AnomalyAlertRepository,
    "ai_training": AITrainingJobRepository,
    "backup_restore": BackupScheduleRepository,
    "notifications": NotificationRuleRepository,
    "email": EmailDraftRepository,
    "task_timing": TaskTimingRepository,
    "supplier_portal": SupplierTokenRepository,
}


def get_repository(
    service_name: str,
    session_factory: Any,
) -> DedicatedTableRepository:
    """Factory: get the right repository for a service name."""
    repo_cls = SERVICE_REPOSITORY_MAP.get(service_name)
    if repo_cls is None:
        # Fall back to generic ServiceState
        repo = ServiceStateRepository(session_factory)
        return repo
    return repo_cls(session_factory)
