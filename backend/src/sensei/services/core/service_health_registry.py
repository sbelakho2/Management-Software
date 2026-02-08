"""
Per-Service Health Check Registry.

Extends the infrastructure-level health_checks.py with business-service-level
health probes.  Each in-memory service can register a lightweight health check
that verifies its internal consistency, data freshness, and operational status.

Usage::

    registry = ServiceHealthRegistry()

    # Services self-register
    registry.register("maintenance_tpm", lambda: {
        "healthy": True,
        "assets": len(svc._assets),
        "work_orders": len(svc._work_orders),
    })

    # Aggregate
    report = await registry.check_all()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealthResult:
    """Health check result for a single service."""

    service: str
    healthy: bool
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class HealthReport:
    """Aggregate health report across all services."""

    overall_healthy: bool = True
    total_services: int = 0
    healthy_count: int = 0
    unhealthy_count: int = 0
    results: list[ServiceHealthResult] = field(default_factory=list)
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    total_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_healthy": self.overall_healthy,
            "total_services": self.total_services,
            "healthy": self.healthy_count,
            "unhealthy": self.unhealthy_count,
            "generated_at": self.generated_at.isoformat(),
            "total_latency_ms": round(self.total_latency_ms, 2),
            "services": {
                r.service: {
                    "healthy": r.healthy,
                    "latency_ms": round(r.latency_ms, 2),
                    "error": r.error,
                    **r.details,
                }
                for r in self.results
            },
        }


class ServiceHealthRegistry:
    """Registry for per-service health checks."""

    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        self._checks: dict[
            str, Callable[[], dict[str, Any] | bool]
        ] = {}
        self._timeout = timeout_seconds
        self._last_report: HealthReport | None = None

    def register(
        self,
        service_name: str,
        check_fn: Callable[[], dict[str, Any] | bool],
    ) -> None:
        """Register a health check for a service.

        The *check_fn* should return either:
        - A bool (True = healthy)
        - A dict with at least a ``healthy`` key and optional details
        """
        self._checks[service_name] = check_fn
        logger.debug("Registered health check for %s", service_name)

    def unregister(self, service_name: str) -> None:
        """Remove a registered health check."""
        self._checks.pop(service_name, None)

    def check_one(self, service_name: str) -> ServiceHealthResult:
        """Run health check for a single service."""
        check_fn = self._checks.get(service_name)
        if not check_fn:
            return ServiceHealthResult(
                service=service_name,
                healthy=False,
                error="Service not registered",
            )

        start = time.monotonic()
        try:
            result = check_fn()
            elapsed = (time.monotonic() - start) * 1000

            if isinstance(result, bool):
                return ServiceHealthResult(
                    service=service_name,
                    healthy=result,
                    latency_ms=elapsed,
                )
            elif isinstance(result, dict):
                return ServiceHealthResult(
                    service=service_name,
                    healthy=result.get("healthy", True),
                    latency_ms=elapsed,
                    details={
                        k: v for k, v in result.items() if k != "healthy"
                    },
                )
            else:
                return ServiceHealthResult(
                    service=service_name,
                    healthy=True,
                    latency_ms=elapsed,
                )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning(
                "Health check failed for %s: %s", service_name, exc
            )
            return ServiceHealthResult(
                service=service_name,
                healthy=False,
                latency_ms=elapsed,
                error=str(exc),
            )

    async def check_all(self) -> HealthReport:
        """Run all registered health checks concurrently."""
        report = HealthReport(total_services=len(self._checks))
        start = time.monotonic()

        # Run checks concurrently via asyncio
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, self.check_one, name)
            for name in self._checks
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                report.results.append(
                    ServiceHealthResult(
                        service="unknown",
                        healthy=False,
                        error=str(result),
                    )
                )
                report.unhealthy_count += 1
            elif isinstance(result, ServiceHealthResult):
                report.results.append(result)
                if result.healthy:
                    report.healthy_count += 1
                else:
                    report.unhealthy_count += 1

        report.overall_healthy = report.unhealthy_count == 0
        report.total_latency_ms = (time.monotonic() - start) * 1000
        self._last_report = report
        return report

    def check_all_sync(self) -> HealthReport:
        """Synchronous version of check_all."""
        report = HealthReport(total_services=len(self._checks))
        start = time.monotonic()

        for name in self._checks:
            result = self.check_one(name)
            report.results.append(result)
            if result.healthy:
                report.healthy_count += 1
            else:
                report.unhealthy_count += 1

        report.overall_healthy = report.unhealthy_count == 0
        report.total_latency_ms = (time.monotonic() - start) * 1000
        self._last_report = report
        return report

    @property
    def last_report(self) -> HealthReport | None:
        return self._last_report

    @property
    def registered_services(self) -> list[str]:
        return list(self._checks.keys())
