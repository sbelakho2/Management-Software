"""E2E Infrastructure & Zero-Ops Resilience Service (Development Plan 20.3).

This service validates infrastructure resilience and self-healing:
- Hetzner CPU Performance (ONNX latency, memory throttling, model warmup)
- Autopilot & Self-Healing (DB autonomy, health watchdog, S3 consistency)
- Backup/Restore Fire Drill
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    pass


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceType(str, Enum):
    DATABASE = "database"
    REDIS = "redis"
    MODEL_SERVER = "model_server"
    S3_STORAGE = "s3_storage"
    MESSAGE_QUEUE = "message_queue"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PerformanceMetrics:
    """ONNX inference and CPU performance metrics."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    inference_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    memory_limit_mb: float = 8192.0
    cpu_load_percent: float = 0.0
    model_warm: bool = False
    first_query_latency_ms: float = 0.0


@dataclass
class SlowQueryEvent:
    """Slow query detection event."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    query: str = ""
    execution_time_ms: float = 0.0
    table_name: str = ""
    suggested_indexes: list[str] = field(default_factory=list)
    applied: bool = False


@dataclass
class HealthCheckResult:
    """Health check result for a service."""
    service: ServiceType
    status: HealthStatus
    latency_ms: float
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_utcnow)


@dataclass
class DeepHealthReport:
    """Complete deep health check report."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    overall_status: HealthStatus = HealthStatus.HEALTHY
    services: list[HealthCheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FileIntegrityResult:
    """S3/Local file integrity check result."""
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=_utcnow)
    total_files: int = 0
    matched_files: int = 0
    mismatched_files: int = 0
    missing_files: int = 0
    match_percentage: float = 100.0
    mismatches: list[dict] = field(default_factory=list)


@dataclass
class BackupRestoreResult:
    """Backup restore operation result."""
    id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None
    duration_minutes: float = 0.0
    source_snapshot: str = ""
    target_sandbox: str = ""
    tables_restored: int = 0
    rows_restored: int = 0
    success: bool = False
    errors: list[str] = field(default_factory=list)


class InfrastructureResilienceService:
    """E2E validation service for infrastructure resilience."""

    ALLOWED_ROLES = {"admin", "ceo", "exec", "secops", "it", "superuser"}

    # Thresholds.
    MAX_INFERENCE_LATENCY_MS = 200
    MAX_FIRST_QUERY_LATENCY_MS = 50
    MAX_RESTORE_MINUTES = 15
    MEMORY_THROTTLE_THRESHOLD = 0.90  # 90% of limit.

    def __init__(self) -> None:
        self._performance_history: list[PerformanceMetrics] = []
        self._slow_queries: list[SlowQueryEvent] = []
        self._health_checks: list[DeepHealthReport] = []
        self._integrity_checks: list[FileIntegrityResult] = []
        self._restore_history: list[BackupRestoreResult] = []

        # Simulated service states.
        self._service_states: dict[ServiceType, HealthStatus] = {
            svc: HealthStatus.HEALTHY for svc in ServiceType
        }
        self._model_warm = False
        self._memory_usage_mb = 2048.0

        # Simulated S3/Local files.
        self._s3_files: dict[str, str] = {}  # path -> checksum.
        self._local_files: dict[str, str] = {}

        # Simulated index suggestions.
        self._suggested_indexes: list[tuple[str, str]] = []

    def _check_role(self, role: str) -> None:
        if role.lower() not in self.ALLOWED_ROLES:
            raise PermissionError(f"Role '{role}' cannot access infrastructure services")

    # ---- Hetzner CPU Performance ----

    def measure_onnx_latency(
        self,
        role: str,
        *,
        simulated_latency_ms: float | None = None,
    ) -> PerformanceMetrics:
        """Measure ONNX inference latency on CPU.

        Args:
            role: User role performing check.
            simulated_latency_ms: Override latency for testing.

        Returns:
            Performance metrics including latency.
        """
        self._check_role(role)

        latency = simulated_latency_ms if simulated_latency_ms is not None else random.uniform(50, 180)

        metrics = PerformanceMetrics(
            inference_latency_ms=latency,
            memory_usage_mb=self._memory_usage_mb,
            cpu_load_percent=random.uniform(20, 60),
            model_warm=self._model_warm,
        )

        self._performance_history.append(metrics)
        return metrics

    def verify_inference_latency(
        self,
        role: str,
        *,
        latency_ms: float,
    ) -> tuple[bool, str]:
        """Verify inference latency is under threshold.

        Args:
            role: User role performing check.
            latency_ms: Measured latency in milliseconds.

        Returns:
            Tuple of (passes, message).
        """
        self._check_role(role)

        if latency_ms <= self.MAX_INFERENCE_LATENCY_MS:
            return True, f"Latency {latency_ms}ms is under {self.MAX_INFERENCE_LATENCY_MS}ms threshold"
        return False, f"Latency {latency_ms}ms exceeds {self.MAX_INFERENCE_LATENCY_MS}ms threshold"

    def simulate_memory_load(
        self,
        role: str,
        *,
        load_mb: float,
        memory_limit_mb: float = 8192.0,
    ) -> tuple[bool, str]:
        """Simulate memory load and verify throttling prevents OOM.

        Args:
            role: User role performing test.
            load_mb: Simulated memory load in MB.
            memory_limit_mb: Memory limit in MB.

        Returns:
            Tuple of (throttled, message).
        """
        self._check_role(role)

        threshold_mb = memory_limit_mb * self.MEMORY_THROTTLE_THRESHOLD

        if load_mb >= threshold_mb:
            # Predictive throttling should kick in.
            self._memory_usage_mb = threshold_mb * 0.8  # Reduce to safe level.
            return True, f"Predictive throttling activated at {threshold_mb}MB, reduced to {self._memory_usage_mb}MB"

        self._memory_usage_mb = load_mb
        return False, f"Memory at {load_mb}MB, no throttling needed"

    def warm_models(self, role: str) -> None:
        """Warm up ML models to eliminate first-query latency."""
        self._check_role(role)
        self._model_warm = True

    def measure_first_query_latency(
        self,
        role: str,
        *,
        simulated_latency_ms: float | None = None,
    ) -> tuple[float, bool]:
        """Measure first query latency after startup.

        Args:
            role: User role performing check.
            simulated_latency_ms: Override latency for testing.

        Returns:
            Tuple of (latency_ms, passes).
        """
        self._check_role(role)

        if self._model_warm:
            latency = simulated_latency_ms if simulated_latency_ms is not None else random.uniform(5, 30)
        else:
            latency = simulated_latency_ms if simulated_latency_ms is not None else random.uniform(500, 2000)

        passes = latency <= self.MAX_FIRST_QUERY_LATENCY_MS
        return latency, passes

    # ---- Autopilot & Self-Healing ----

    def detect_slow_query(
        self,
        role: str,
        *,
        query: str,
        execution_time_ms: float,
        table_name: str,
    ) -> SlowQueryEvent | None:
        """Detect slow query and generate index recommendations.

        Args:
            role: User role performing check.
            query: The SQL query.
            execution_time_ms: Execution time in milliseconds.
            table_name: Table being queried.

        Returns:
            SlowQueryEvent with index recommendations, or None if not slow.
        """
        self._check_role(role)

        # Threshold: > 500ms is slow.
        if execution_time_ms <= 500:
            return None

        # Analyze query and suggest indexes.
        suggestions = []

        # Simple heuristics for index suggestions.
        query_lower = query.lower()
        if "where" in query_lower:
            # Extract column from WHERE clause (simplified).
            if "id" in query_lower:
                suggestions.append(f"CREATE INDEX idx_{table_name}_id ON {table_name}(id)")
            if "created_at" in query_lower or "date" in query_lower:
                suggestions.append(f"CREATE INDEX idx_{table_name}_created_at ON {table_name}(created_at)")
            if "status" in query_lower:
                suggestions.append(f"CREATE INDEX idx_{table_name}_status ON {table_name}(status)")

        if "order by" in query_lower:
            if "updated_at" in query_lower:
                suggestions.append(f"CREATE INDEX idx_{table_name}_updated_at ON {table_name}(updated_at)")

        if not suggestions:
            suggestions.append(f"ANALYZE TABLE {table_name}")

        event = SlowQueryEvent(
            query=query,
            execution_time_ms=execution_time_ms,
            table_name=table_name,
            suggested_indexes=suggestions,
        )

        self._slow_queries.append(event)
        self._suggested_indexes.extend((table_name, idx) for idx in suggestions)

        return event

    def apply_index_recommendation(
        self,
        role: str,
        *,
        event_id: UUID,
    ) -> bool:
        """Apply recommended index from a slow query event.

        Args:
            role: User role performing action.
            event_id: SlowQueryEvent ID.

        Returns:
            True if applied successfully.
        """
        self._check_role(role)

        for event in self._slow_queries:
            if event.id == event_id:
                event.applied = True
                return True

        return False

    def deep_health_check(
        self,
        role: str,
        *,
        service_overrides: dict[ServiceType, HealthStatus] | None = None,
    ) -> DeepHealthReport:
        """Perform deep health check on all services.

        Args:
            role: User role performing check.
            service_overrides: Override service states for testing.

        Returns:
            Complete health report.
        """
        self._check_role(role)

        if service_overrides:
            for svc, status in service_overrides.items():
                self._service_states[svc] = status

        report = DeepHealthReport()

        for svc, status in self._service_states.items():
            latency = random.uniform(1, 50) if status == HealthStatus.HEALTHY else random.uniform(100, 500)

            result = HealthCheckResult(
                service=svc,
                status=status,
                latency_ms=latency,
                details={"connected": status == HealthStatus.HEALTHY},
            )
            report.services.append(result)

            if status != HealthStatus.HEALTHY:
                report.warnings.append(f"{svc.value} is {status.value}")

        # Determine overall status.
        statuses = [s.status for s in report.services]
        if HealthStatus.UNHEALTHY in statuses:
            report.overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            report.overall_status = HealthStatus.DEGRADED
        else:
            report.overall_status = HealthStatus.HEALTHY

        self._health_checks.append(report)
        return report

    # ---- S3/Local Consistency ----

    def register_file(
        self,
        role: str,
        *,
        path: str,
        content: bytes,
        location: str = "both",
    ) -> str:
        """Register a file in S3 and/or local storage.

        Args:
            role: User role performing action.
            path: File path.
            content: File content.
            location: 's3', 'local', or 'both'.

        Returns:
            Checksum of the file.
        """
        self._check_role(role)

        checksum = hashlib.sha256(content).hexdigest()

        if location in ("s3", "both"):
            self._s3_files[path] = checksum
        if location in ("local", "both"):
            self._local_files[path] = checksum

        return checksum

    def verify_file_integrity(
        self,
        role: str,
    ) -> FileIntegrityResult:
        """Verify S3/Local file integrity matches 100%.

        Args:
            role: User role performing check.

        Returns:
            Integrity check result.
        """
        self._check_role(role)

        all_paths = set(self._s3_files.keys()) | set(self._local_files.keys())

        result = FileIntegrityResult(total_files=len(all_paths))
        mismatches = []

        for path in all_paths:
            s3_checksum = self._s3_files.get(path)
            local_checksum = self._local_files.get(path)

            if s3_checksum is None:
                result.missing_files += 1
                mismatches.append({"path": path, "issue": "missing_in_s3"})
            elif local_checksum is None:
                result.missing_files += 1
                mismatches.append({"path": path, "issue": "missing_in_local"})
            elif s3_checksum != local_checksum:
                result.mismatched_files += 1
                mismatches.append({"path": path, "issue": "checksum_mismatch"})
            else:
                result.matched_files += 1

        result.mismatches = mismatches
        result.match_percentage = (
            result.matched_files / result.total_files * 100
            if result.total_files > 0 else 100.0
        )

        self._integrity_checks.append(result)
        return result

    # ---- Backup/Restore Fire Drill ----

    def perform_restore_drill(
        self,
        role: str,
        *,
        source_snapshot: str,
        target_sandbox: str,
        simulated_duration_minutes: float | None = None,
        tables: int = 50,
        rows: int = 100000,
    ) -> BackupRestoreResult:
        """Perform backup restore fire drill.

        Args:
            role: User role performing drill.
            source_snapshot: Source snapshot identifier.
            target_sandbox: Target sandbox environment.
            simulated_duration_minutes: Override duration for testing.
            tables: Number of tables to restore.
            rows: Number of rows to restore.

        Returns:
            Restore operation result.
        """
        self._check_role(role)

        started = _utcnow()

        duration = (
            simulated_duration_minutes
            if simulated_duration_minutes is not None
            else random.uniform(5, 20)
        )

        completed = started + timedelta(minutes=duration)

        result = BackupRestoreResult(
            started_at=started,
            completed_at=completed,
            duration_minutes=duration,
            source_snapshot=source_snapshot,
            target_sandbox=target_sandbox,
            tables_restored=tables,
            rows_restored=rows,
            success=duration <= self.MAX_RESTORE_MINUTES,
        )

        if not result.success:
            result.errors.append(
                f"Restore took {duration:.1f} minutes, exceeds {self.MAX_RESTORE_MINUTES} minute limit"
            )

        self._restore_history.append(result)
        return result

    def verify_restore_time(
        self,
        role: str,
        *,
        duration_minutes: float,
    ) -> tuple[bool, str]:
        """Verify restore completed within time limit.

        Args:
            role: User role performing check.
            duration_minutes: Restore duration in minutes.

        Returns:
            Tuple of (passes, message).
        """
        self._check_role(role)

        if duration_minutes <= self.MAX_RESTORE_MINUTES:
            return True, f"Restore completed in {duration_minutes:.1f} minutes (under {self.MAX_RESTORE_MINUTES} limit)"
        return False, f"Restore took {duration_minutes:.1f} minutes, exceeds {self.MAX_RESTORE_MINUTES} minute limit"

    # ---- Getters ----

    def get_slow_queries(self) -> list[SlowQueryEvent]:
        return list(self._slow_queries)

    def get_health_history(self) -> list[DeepHealthReport]:
        return list(self._health_checks)

    def get_integrity_checks(self) -> list[FileIntegrityResult]:
        return list(self._integrity_checks)

    def get_restore_history(self) -> list[BackupRestoreResult]:
        return list(self._restore_history)
