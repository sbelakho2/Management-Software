"""Analytics Warehouse Celery Tasks.

Provides scheduled background tasks for:
- Daily analytics snapshot creation
- Cross-domain KPI computation & caching
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from uuid import UUID

from celery import shared_task

logger = logging.getLogger(__name__)

_SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
_SYSTEM_ROLES: tuple[str, ...] = ("admin", "ceo")


def _run_async(coro):
    """Run an async coroutine from synchronous Celery context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    name="sensei.tasks.analytics_tasks.daily_analytics_snapshot",
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def daily_analytics_snapshot(self, snapshot_date_iso: str | None = None):
    """Create or complete a daily analytics snapshot.

    Runs nightly via Celery beat. Creates a DailySnapshot row, then
    pulls cross-domain summaries (finance, HR, inventory) and stores
    them as exported records in the analytics warehouse.
    """
    logger.info("Starting daily analytics snapshot task")

    async def _run():
        from sensei.core.database import async_session_factory
        from sensei.services.ops.analytics_warehouse import (
            AnalyticsWarehouseService,
            FactType,
        )

        warehouse = AnalyticsWarehouseService()
        target_date = (
            date.fromisoformat(snapshot_date_iso)
            if snapshot_date_iso
            else date.today()
        )

        async with async_session_factory() as session:
            # 1. Create snapshot
            snapshot = await warehouse.get_or_create_snapshot(
                session,
                snapshot_date=target_date,
                actor_user_id=_SYSTEM_USER_ID,
                actor_roles=_SYSTEM_ROLES,
            )

            # 2. Extract cross-domain summaries
            summary = await warehouse.build_cross_domain_summary(
                session,
                actor_roles=_SYSTEM_ROLES,
            )

            # 3. Store each domain summary as an exported record
            record_count = 0
            for domain, data in summary.items():
                fact_type_map = {
                    "finance": FactType.FINANCIAL_TRANSACTION,
                    "hr": FactType.HEADCOUNT_SNAPSHOT,
                    "inventory": FactType.INVENTORY_LEVEL,
                    "quality": FactType.QUALITY_METRIC,
                    "operations": FactType.WORK_ORDER,
                    "sales": FactType.OPPORTUNITY,
                    "projects": FactType.PROJECT_FACT,
                    "maintenance": FactType.WORK_ORDER,
                    "obeya": FactType.OBEYA_METRIC,
                    "ai": FactType.ANOMALY_DETECTION,
                }
                ft = fact_type_map.get(domain, FactType.QUALITY_METRIC)
                await warehouse.append_exported_record(
                    session,
                    actor_roles=_SYSTEM_ROLES,
                    actor_user_id=_SYSTEM_USER_ID,
                    fact_type=ft,
                    data={
                        "source": "daily_snapshot",
                        "domain": domain,
                        "snapshot_date": target_date.isoformat(),
                        "payload": data,
                    },
                )
                record_count += 1

            await session.commit()

        logger.info(
            "Daily snapshot completed: date=%s, records=%d",
            target_date.isoformat(),
            record_count,
        )
        return {
            "snapshot_date": target_date.isoformat(),
            "records_exported": record_count,
        }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("Daily snapshot failed, retrying")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="sensei.tasks.analytics_tasks.compute_warehouse_kpis",
    max_retries=1,
    default_retry_delay=120,
    acks_late=True,
)
def compute_warehouse_kpis(self):
    """Compute and cache aggregate KPI values from exported records.

    Runs every 4 hours via Celery beat. Aggregates fact counts by type
    and caches results in Redis so the CEO dashboard can serve pre-computed values instantly.
    """
    logger.info("Computing warehouse KPIs")

    async def _run():
        import json
        from sensei.core.database import async_session_factory
        from sensei.core.redis import get_cache, set_cache
        from sensei.services.ops.analytics_warehouse import AnalyticsWarehouseService, FactType

        warehouse = AnalyticsWarehouseService()

        async with async_session_factory() as session:
            counts = await warehouse.get_fact_counts(
                session,
                actor_roles=_SYSTEM_ROLES,
            )
            latest = await warehouse.get_latest_snapshot(
                session,
                actor_roles=_SYSTEM_ROLES,
            )

            # Persist KPI results as an exported record for historical tracking
            kpi_data = {
                "source": "warehouse_kpi_computation",
                "computed_at": datetime.now(timezone.utc).isoformat(),
                "fact_counts": counts,
                "latest_snapshot_date": (
                    latest.snapshot_date.isoformat() if latest else None
                ),
            }
            await warehouse.append_exported_record(
                session,
                actor_roles=_SYSTEM_ROLES,
                actor_user_id=_SYSTEM_USER_ID,
                fact_type=FactType.QUALITY_METRIC,
                data=kpi_data,
            )
            await session.commit()

        # Cache results in Redis for instant retrieval
        cache_key = "warehouse:kpi:latest"
        cache_value = json.dumps(kpi_data)
        try:
            await set_cache(cache_key, cache_value, ttl=14400)  # 4 hour TTL
        except Exception as e:
            logger.warning("Failed to cache KPI results in Redis: %s", e)

        logger.info("Warehouse KPIs computed and cached: %s", kpi_data)
        return kpi_data

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("KPI computation failed, retrying")
        raise self.retry(exc=exc)
