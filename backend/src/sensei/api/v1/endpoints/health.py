"""Health Check Endpoints (#406).

Provides distinct liveness and readiness probes for k8s:
- /live  — Always returns 200 if the process is running (liveness).
- /ready — Checks DB and Redis connectivity before returning 200 (readiness).
"""

import logging
import time

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/ready")
async def readiness_check() -> Response:
    """Readiness probe — verifies DB and Redis are reachable."""
    checks: dict[str, str] = {}
    all_ok = True

    # Check database
    try:
        from sensei.core.database import engine  # noqa: WPS433

        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("Readiness: database check failed: %s", exc)
        checks["database"] = f"error: {exc}"
        all_ok = False

    # Check Redis
    try:
        from sensei.core.redis import redis_client as _redis  # noqa: WPS433

        await _redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("Readiness: redis check failed: %s", exc)
        checks["redis"] = f"error: {exc}"
        all_ok = False

    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks, "timestamp": time.time()},
        status_code=status_code,
    )


@router.get("/live")
async def liveness_check() -> dict:
    """Liveness probe — confirms process is running."""
    return {"status": "alive", "timestamp": time.time()}


# -------------------------------------------------------------------------
# Prometheus-compatible /metrics endpoint (#421)
# -------------------------------------------------------------------------

import os
import resource

_START_TIME = time.monotonic()


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Expose basic application metrics in Prometheus text exposition format.

    Provides process-level metrics (CPU, memory, uptime) and application
    health indicators without requiring a full Prometheus client library.
    """
    uptime = time.monotonic() - _START_TIME
    usage = resource.getrusage(resource.RUSAGE_SELF)
    pid = os.getpid()

    # Gather DB / Redis health (lightweight)
    db_up = 1
    redis_up = 1
    try:
        from sensei.core.database import engine  # noqa: WPS433
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_up = 0
    try:
        from sensei.core.redis import redis_client as _redis  # noqa: WPS433
        await _redis.ping()
    except Exception:
        redis_up = 0

    lines = [
        "# HELP process_uptime_seconds Time since process start.",
        "# TYPE process_uptime_seconds gauge",
        f"process_uptime_seconds {uptime:.2f}",
        "# HELP process_cpu_seconds_total Total user + system CPU time.",
        "# TYPE process_cpu_seconds_total counter",
        f"process_cpu_seconds_total {usage.ru_utime + usage.ru_stime:.4f}",
        "# HELP process_resident_memory_bytes Resident set size in bytes.",
        "# TYPE process_resident_memory_bytes gauge",
        f"process_resident_memory_bytes {usage.ru_maxrss * 1024}",
        "# HELP process_pid Current process ID.",
        "# TYPE process_pid gauge",
        f"process_pid {pid}",
        "# HELP app_database_up Whether the database is reachable (1=yes, 0=no).",
        "# TYPE app_database_up gauge",
        f"app_database_up {db_up}",
        "# HELP app_redis_up Whether Redis is reachable (1=yes, 0=no).",
        "# TYPE app_redis_up gauge",
        f"app_redis_up {redis_up}",
        "",
    ]
    return Response(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
