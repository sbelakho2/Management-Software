"""Job Health Monitoring Service.

Provides monitoring, tracking, and health checking for
background jobs, scheduled tasks, and async workers.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Any
import uuid


class JobType(Enum):
    """Types of jobs."""

    SCHEDULED = "scheduled"
    ASYNC = "async"
    BATCH = "batch"
    WORKER = "worker"
    CRON = "cron"
    TRIGGER = "trigger"


class JobStatus(Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMEOUT = "timeout"


class JobPriority(Enum):
    """Job priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class HealthStatus(Enum):
    """Health status for job systems."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class JobDefinition:
    """Definition of a job type."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    job_type: JobType = JobType.ASYNC
    queue: str = "default"
    handler: str = ""  # Handler function/class name
    default_priority: JobPriority = JobPriority.NORMAL
    max_retries: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    expected_duration_seconds: int = 60
    schedule: str = ""  # Cron expression for scheduled jobs
    is_active: bool = True
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobExecution:
    """A single job execution instance."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""  # Reference to JobDefinition
    job_name: str = ""
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    queue: str = "default"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    attempt: int = 1
    max_attempts: int = 3
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    error_trace: str = ""
    worker_id: str = ""
    progress_percent: int = 0
    progress_message: str = ""
    duration_ms: int = 0
    parent_execution_id: str = ""  # For child jobs
    tags: list[str] = field(default_factory=list)


@dataclass
class Worker:
    """A worker process."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    queues: list[str] = field(default_factory=list)
    hostname: str = ""
    pid: int = 0
    status: HealthStatus = HealthStatus.HEALTHY
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_heartbeat: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    current_job_id: str = ""
    jobs_processed: int = 0
    jobs_failed: int = 0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    is_active: bool = True


@dataclass
class Queue:
    """A job queue."""

    name: str = ""
    pending_count: int = 0
    processing_count: int = 0
    failed_count: int = 0
    completed_count: int = 0
    oldest_job_age_seconds: int = 0
    workers_count: int = 0
    is_paused: bool = False


@dataclass
class JobMetrics:
    """Metrics for job monitoring."""

    total_jobs: int = 0
    pending_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    retrying_jobs: int = 0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    success_rate: float = 0.0
    throughput_per_minute: float = 0.0
    by_status: dict[str, int] = field(default_factory=dict)
    by_queue: dict[str, int] = field(default_factory=dict)
    by_job_type: dict[str, int] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """Health check result."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""  # queue, worker, job
    component_id: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Job system alert."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    alert_type: str = ""  # queue_backlog, job_failure_spike, worker_down
    severity: str = "medium"  # critical, high, medium, low
    message: str = ""
    component: str = ""
    component_id: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Optional[datetime] = None
    is_active: bool = True
    details: dict[str, Any] = field(default_factory=dict)


# Default job definitions
DEFAULT_JOBS: list[dict] = [
    {
        "name": "data_cleanup",
        "description": "Clean up expired data and temporary files",
        "job_type": JobType.CRON,
        "schedule": "0 2 * * *",  # Daily at 2 AM
        "timeout_seconds": 3600,
        "expected_duration_seconds": 600,
        "tags": ["maintenance", "cleanup"],
    },
    {
        "name": "report_generation",
        "description": "Generate daily reports",
        "job_type": JobType.SCHEDULED,
        "schedule": "0 6 * * *",  # Daily at 6 AM
        "timeout_seconds": 1800,
        "expected_duration_seconds": 300,
        "tags": ["reports", "analytics"],
    },
    {
        "name": "email_digest",
        "description": "Send email digests to users",
        "job_type": JobType.BATCH,
        "timeout_seconds": 3600,
        "expected_duration_seconds": 900,
        "tags": ["email", "notifications"],
    },
    {
        "name": "data_sync",
        "description": "Sync data with external systems",
        "job_type": JobType.SCHEDULED,
        "schedule": "*/15 * * * *",  # Every 15 minutes
        "timeout_seconds": 600,
        "expected_duration_seconds": 120,
        "tags": ["sync", "integration"],
    },
    {
        "name": "async_task_processor",
        "description": "Process async tasks from queue",
        "job_type": JobType.WORKER,
        "queue": "tasks",
        "timeout_seconds": 300,
        "expected_duration_seconds": 30,
        "tags": ["async", "tasks"],
    },
]


class JobHealthService:
    """Service for monitoring job health."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._jobs: dict[str, JobDefinition] = {}
        self._executions: dict[str, JobExecution] = {}
        self._workers: dict[str, Worker] = {}
        self._alerts: dict[str, Alert] = {}
        self._health_checks: list[HealthCheck] = []
        self._max_executions: int = 5000
        self._execution_ttl: timedelta = timedelta(days=30)
        self._initialize_defaults()

    def _prune_executions(self) -> None:
        """Prune old job executions to prevent unbounded growth."""
        cutoff = datetime.now(timezone.utc) - self._execution_ttl

        stale_ids = [
            eid for eid, execution in self._executions.items()
            if execution.completed_at and execution.completed_at < cutoff
        ]
        for eid in stale_ids:
            del self._executions[eid]

        excess = len(self._executions) - self._max_executions
        if excess > 0:
            oldest = sorted(self._executions.items(), key=lambda item: item[1].created_at)
            for eid, _ in oldest[:excess]:
                del self._executions[eid]

    def _initialize_defaults(self) -> None:
        """Initialize default configuration."""
        for job_data in DEFAULT_JOBS:
            job = JobDefinition(
                name=job_data["name"],
                description=job_data["description"],
                job_type=job_data["job_type"],
                schedule=job_data.get("schedule", ""),
                timeout_seconds=job_data.get("timeout_seconds", 300),
                expected_duration_seconds=job_data.get("expected_duration_seconds", 60),
                tags=job_data.get("tags", []),
                queue=job_data.get("queue", "default"),
            )
            self._jobs[job.id] = job

    # ========================================
    # Job Definition Management
    # ========================================

    def register_job(
        self,
        name: str,
        handler: str = "",
        job_type: JobType = JobType.ASYNC,
        description: str = "",
        queue: str = "default",
        default_priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3,
        retry_delay_seconds: int = 60,
        timeout_seconds: int = 300,
        expected_duration_seconds: int = 60,
        schedule: str = "",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> JobDefinition:
        """Register a new job definition."""
        job = JobDefinition(
            name=name,
            description=description,
            job_type=job_type,
            queue=queue,
            handler=handler,
            default_priority=default_priority,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            timeout_seconds=timeout_seconds,
            expected_duration_seconds=expected_duration_seconds,
            schedule=schedule,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobDefinition]:
        """Get a job definition by ID."""
        return self._jobs.get(job_id)

    def get_job_by_name(self, name: str) -> Optional[JobDefinition]:
        """Get a job definition by name."""
        return next((j for j in self._jobs.values() if j.name == name), None)

    def get_all_jobs(self) -> list[JobDefinition]:
        """Get all job definitions."""
        return list(self._jobs.values())

    def get_jobs_by_type(self, job_type: JobType) -> list[JobDefinition]:
        """Get jobs by type."""
        return [j for j in self._jobs.values() if j.job_type == job_type]

    def get_jobs_by_queue(self, queue: str) -> list[JobDefinition]:
        """Get jobs by queue."""
        return [j for j in self._jobs.values() if j.queue == queue]

    def get_scheduled_jobs(self) -> list[JobDefinition]:
        """Get all scheduled jobs (with cron schedule)."""
        return [j for j in self._jobs.values() if j.schedule]

    def update_job(
        self,
        job_id: str,
        description: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        schedule: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[JobDefinition]:
        """Update a job definition."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        if description is not None:
            job.description = description
        if max_retries is not None:
            job.max_retries = max_retries
        if timeout_seconds is not None:
            job.timeout_seconds = timeout_seconds
        if schedule is not None:
            job.schedule = schedule
        if is_active is not None:
            job.is_active = is_active

        return job

    def delete_job(self, job_id: str) -> bool:
        """Delete a job definition."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    # ========================================
    # Execution Management
    # ========================================

    def enqueue_job(
        self,
        job_id: str,
        input_data: Optional[dict[str, Any]] = None,
        priority: Optional[JobPriority] = None,
        scheduled_at: Optional[datetime] = None,
        parent_execution_id: str = "",
    ) -> Optional[JobExecution]:
        """Enqueue a job for execution."""
        job = self._jobs.get(job_id)
        if not job or not job.is_active:
            return None

        execution = JobExecution(
            job_id=job_id,
            job_name=job.name,
            status=JobStatus.PENDING,
            priority=priority or job.default_priority,
            queue=job.queue,
            max_attempts=job.max_retries + 1,
            input_data=input_data or {},
            scheduled_at=scheduled_at,
            parent_execution_id=parent_execution_id,
            tags=list(job.tags),
        )
        self._executions[execution.id] = execution
        self._prune_executions()
        return execution

    def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get an execution by ID."""
        return self._executions.get(execution_id)

    def get_all_executions(self) -> list[JobExecution]:
        """Get all executions."""
        return list(self._executions.values())

    def get_executions_by_status(self, status: JobStatus) -> list[JobExecution]:
        """Get executions by status."""
        return [e for e in self._executions.values() if e.status == status]

    def get_executions_by_job(self, job_id: str) -> list[JobExecution]:
        """Get executions for a specific job."""
        return [e for e in self._executions.values() if e.job_id == job_id]

    def get_executions_by_queue(self, queue: str) -> list[JobExecution]:
        """Get executions in a queue."""
        return [e for e in self._executions.values() if e.queue == queue]

    def get_pending_executions(self) -> list[JobExecution]:
        """Get pending executions."""
        return self.get_executions_by_status(JobStatus.PENDING)

    def get_running_executions(self) -> list[JobExecution]:
        """Get running executions."""
        return self.get_executions_by_status(JobStatus.RUNNING)

    def get_failed_executions(self) -> list[JobExecution]:
        """Get failed executions."""
        return self.get_executions_by_status(JobStatus.FAILED)

    def get_recent_executions(
        self,
        limit: int = 100,
        job_id: Optional[str] = None,
    ) -> list[JobExecution]:
        """Get recent executions."""
        executions = (
            [e for e in self._executions.values() if e.job_id == job_id]
            if job_id
            else list(self._executions.values())
        )
        sorted_executions = sorted(
            executions,
            key=lambda e: e.created_at,
            reverse=True,
        )
        return sorted_executions[:limit]

    def start_execution(
        self,
        execution_id: str,
        worker_id: str = "",
    ) -> Optional[JobExecution]:
        """Mark execution as started."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.status = JobStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        execution.worker_id = worker_id
        return execution

    def update_progress(
        self,
        execution_id: str,
        progress_percent: int,
        progress_message: str = "",
    ) -> Optional[JobExecution]:
        """Update execution progress."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.progress_percent = min(100, max(0, progress_percent))
        execution.progress_message = progress_message
        return execution

    def complete_execution(
        self,
        execution_id: str,
        output_data: Optional[dict[str, Any]] = None,
    ) -> Optional[JobExecution]:
        """Mark execution as completed."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.status = JobStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)
        execution.progress_percent = 100
        execution.output_data = output_data or {}

        if execution.started_at:
            duration = execution.completed_at - execution.started_at
            execution.duration_ms = int(duration.total_seconds() * 1000)

        return execution

    def fail_execution(
        self,
        execution_id: str,
        error_message: str,
        error_trace: str = "",
    ) -> Optional[JobExecution]:
        """Mark execution as failed."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.error_message = error_message
        execution.error_trace = error_trace
        execution.completed_at = datetime.now(timezone.utc)

        if execution.started_at:
            duration = execution.completed_at - execution.started_at
            execution.duration_ms = int(duration.total_seconds() * 1000)

        # Check if can retry
        if execution.attempt < execution.max_attempts:
            execution.status = JobStatus.RETRYING
            execution.attempt += 1
        else:
            execution.status = JobStatus.FAILED

        return execution

    def cancel_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Cancel an execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        if execution.status in (JobStatus.PENDING, JobStatus.RUNNING):
            execution.status = JobStatus.CANCELLED
            execution.completed_at = datetime.now(timezone.utc)

        return execution

    def timeout_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Mark execution as timed out."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.status = JobStatus.TIMEOUT
        execution.completed_at = datetime.now(timezone.utc)
        execution.error_message = "Job execution timed out"

        return execution

    def retry_execution(
        self,
        execution_id: str,
    ) -> Optional[JobExecution]:
        """Create a retry execution for a failed job."""
        original = self._executions.get(execution_id)
        if not original:
            return None

        # Can only retry if status is RETRYING (set by fail_execution when retries remain)
        if original.status != JobStatus.RETRYING:
            return None

        # Create new execution as retry
        new_execution = JobExecution(
            job_id=original.job_id,
            job_name=original.job_name,
            status=JobStatus.PENDING,
            priority=original.priority,
            queue=original.queue,
            attempt=original.attempt,  # Keep same attempt (fail_execution incremented it)
            max_attempts=original.max_attempts,
            input_data=dict(original.input_data),
            parent_execution_id=original.parent_execution_id,
            tags=list(original.tags),
        )
        self._executions[new_execution.id] = new_execution
        self._prune_executions()
        return new_execution

    # ========================================
    # Worker Management
    # ========================================

    def register_worker(
        self,
        name: str,
        queues: list[str],
        hostname: str = "",
        pid: int = 0,
    ) -> Worker:
        """Register a new worker."""
        worker = Worker(
            name=name,
            queues=queues,
            hostname=hostname,
            pid=pid,
        )
        self._workers[worker.id] = worker
        return worker

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def get_all_workers(self) -> list[Worker]:
        """Get all workers."""
        return list(self._workers.values())

    def get_active_workers(self) -> list[Worker]:
        """Get active workers."""
        return [w for w in self._workers.values() if w.is_active]

    def get_workers_by_queue(self, queue: str) -> list[Worker]:
        """Get workers for a queue."""
        return [w for w in self._workers.values() if queue in w.queues]

    def heartbeat(
        self,
        worker_id: str,
        current_job_id: str = "",
        cpu_usage_percent: float = 0.0,
        memory_usage_mb: float = 0.0,
    ) -> Optional[Worker]:
        """Update worker heartbeat."""
        worker = self._workers.get(worker_id)
        if not worker:
            return None

        worker.last_heartbeat = datetime.now(timezone.utc)
        worker.current_job_id = current_job_id
        worker.cpu_usage_percent = cpu_usage_percent
        worker.memory_usage_mb = memory_usage_mb
        worker.status = HealthStatus.HEALTHY

        return worker

    def increment_job_count(
        self,
        worker_id: str,
        is_success: bool = True,
    ) -> Optional[Worker]:
        """Increment worker job count."""
        worker = self._workers.get(worker_id)
        if not worker:
            return None

        worker.jobs_processed += 1
        if not is_success:
            worker.jobs_failed += 1

        return worker

    def deactivate_worker(self, worker_id: str) -> Optional[Worker]:
        """Deactivate a worker."""
        worker = self._workers.get(worker_id)
        if not worker:
            return None

        worker.is_active = False
        worker.status = HealthStatus.UNKNOWN
        return worker

    def check_stale_workers(
        self,
        stale_threshold_seconds: int = 60,
    ) -> list[Worker]:
        """Check for stale workers."""
        now = datetime.now(timezone.utc)
        threshold = timedelta(seconds=stale_threshold_seconds)
        stale = []

        for worker in self._workers.values():
            if worker.is_active and (now - worker.last_heartbeat) > threshold:
                worker.status = HealthStatus.UNHEALTHY
                stale.append(worker)

        return stale

    # ========================================
    # Queue Management
    # ========================================

    def get_queue_stats(self, queue_name: str) -> Queue:
        """Get statistics for a queue."""
        executions = self.get_executions_by_queue(queue_name)
        workers = self.get_workers_by_queue(queue_name)

        pending = [e for e in executions if e.status == JobStatus.PENDING]
        running = [e for e in executions if e.status == JobStatus.RUNNING]
        failed = [e for e in executions if e.status == JobStatus.FAILED]
        completed = [e for e in executions if e.status == JobStatus.COMPLETED]

        oldest_age = 0
        if pending:
            now = datetime.now(timezone.utc)
            ages = [(now - e.created_at).total_seconds() for e in pending]
            oldest_age = int(max(ages)) if ages else 0

        return Queue(
            name=queue_name,
            pending_count=len(pending),
            processing_count=len(running),
            failed_count=len(failed),
            completed_count=len(completed),
            oldest_job_age_seconds=oldest_age,
            workers_count=len([w for w in workers if w.is_active]),
        )

    def get_all_queues(self) -> list[str]:
        """Get all queue names."""
        queues = set()
        for job in self._jobs.values():
            queues.add(job.queue)
        for execution in self._executions.values():
            queues.add(execution.queue)
        return sorted(queues)

    # ========================================
    # Health Checking
    # ========================================

    def check_health(self) -> dict[str, Any]:
        """Perform overall health check."""
        checks = []
        overall_status = HealthStatus.HEALTHY

        # Check workers
        workers = self.get_all_workers()
        active_workers = [w for w in workers if w.is_active]
        stale_workers = self.check_stale_workers()

        worker_check = HealthCheck(
            component="workers",
            status=(
                HealthStatus.HEALTHY if not stale_workers
                else HealthStatus.DEGRADED if active_workers
                else HealthStatus.UNHEALTHY
            ),
            message=(
                f"{len(active_workers)} active workers"
                if not stale_workers
                else f"{len(stale_workers)} stale workers detected"
            ),
            details={
                "total": len(workers),
                "active": len(active_workers),
                "stale": len(stale_workers),
            },
        )
        checks.append(worker_check)
        self._health_checks.append(worker_check)

        # Check queues
        for queue_name in self.get_all_queues():
            stats = self.get_queue_stats(queue_name)

            queue_status = HealthStatus.HEALTHY
            if stats.pending_count > 1000:
                queue_status = HealthStatus.UNHEALTHY
            elif stats.pending_count > 100:
                queue_status = HealthStatus.DEGRADED

            if stats.workers_count == 0 and stats.pending_count > 0:
                queue_status = HealthStatus.UNHEALTHY

            queue_check = HealthCheck(
                component="queue",
                component_id=queue_name,
                status=queue_status,
                message=f"Queue {queue_name}: {stats.pending_count} pending",
                details={
                    "pending": stats.pending_count,
                    "processing": stats.processing_count,
                    "workers": stats.workers_count,
                },
            )
            checks.append(queue_check)
            self._health_checks.append(queue_check)

            if queue_status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif (
                queue_status == HealthStatus.DEGRADED
                and overall_status != HealthStatus.UNHEALTHY
            ):
                overall_status = HealthStatus.DEGRADED

        # Check for stuck jobs
        running = self.get_running_executions()
        stuck_jobs = []
        now = datetime.now(timezone.utc)
        for execution in running:
            if execution.started_at:
                job = self._jobs.get(execution.job_id)
                timeout = job.timeout_seconds if job else 300
                if (now - execution.started_at).total_seconds() > timeout:
                    stuck_jobs.append(execution)

        if stuck_jobs:
            stuck_check = HealthCheck(
                component="executions",
                status=HealthStatus.DEGRADED,
                message=f"{len(stuck_jobs)} stuck jobs detected",
                details={"stuck_job_ids": [j.id for j in stuck_jobs]},
            )
            checks.append(stuck_check)
            self._health_checks.append(stuck_check)
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        if worker_check.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        elif (
            worker_check.status == HealthStatus.DEGRADED
            and overall_status == HealthStatus.HEALTHY
        ):
            overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "checks": [
                {
                    "component": c.component,
                    "component_id": c.component_id,
                    "status": c.status.value,
                    "message": c.message,
                }
                for c in checks
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_health_history(
        self,
        limit: int = 100,
        component: Optional[str] = None,
    ) -> list[HealthCheck]:
        """Get health check history."""
        history = (
            [h for h in self._health_checks if h.component == component]
            if component
            else self._health_checks
        )
        sorted_history = sorted(
            history,
            key=lambda h: h.checked_at,
            reverse=True,
        )
        return sorted_history[:limit]

    # ========================================
    # Alerts
    # ========================================

    def create_alert(
        self,
        alert_type: str,
        message: str,
        component: str = "",
        component_id: str = "",
        severity: str = "medium",
        details: Optional[dict[str, Any]] = None,
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            alert_type=alert_type,
            message=message,
            component=component,
            component_id=component_id,
            severity=severity,
            details=details or {},
        )
        self._alerts[alert.id] = alert
        return alert

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def get_active_alerts(self) -> list[Alert]:
        """Get active alerts."""
        return [a for a in self._alerts.values() if a.is_active]

    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        alert.is_active = False
        alert.resolved_at = datetime.now(timezone.utc)
        return alert

    def check_alerts(self) -> list[Alert]:
        """Check for alert conditions and create alerts."""
        new_alerts = []

        # Check queue backlog
        for queue_name in self.get_all_queues():
            stats = self.get_queue_stats(queue_name)
            if stats.pending_count > 500:
                # Check if alert already exists
                existing = next(
                    (a for a in self._alerts.values()
                     if a.is_active
                     and a.alert_type == "queue_backlog"
                     and a.component_id == queue_name),
                    None
                )
                if not existing:
                    alert = self.create_alert(
                        alert_type="queue_backlog",
                        message=f"Queue {queue_name} has {stats.pending_count} pending jobs",
                        component="queue",
                        component_id=queue_name,
                        severity="high" if stats.pending_count > 1000 else "medium",
                        details={"pending_count": stats.pending_count},
                    )
                    new_alerts.append(alert)

        # Check for stale workers
        stale = self.check_stale_workers()
        for worker in stale:
            existing = next(
                (a for a in self._alerts.values()
                 if a.is_active
                 and a.alert_type == "worker_stale"
                 and a.component_id == worker.id),
                None
            )
            if not existing:
                alert = self.create_alert(
                    alert_type="worker_stale",
                    message=f"Worker {worker.name} is not responding",
                    component="worker",
                    component_id=worker.id,
                    severity="high",
                )
                new_alerts.append(alert)

        return new_alerts

    # ========================================
    # Metrics
    # ========================================

    def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> JobMetrics:
        """Get job metrics."""
        executions = list(self._executions.values())

        if start_time:
            executions = [e for e in executions if e.created_at >= start_time]
        if end_time:
            executions = [e for e in executions if e.created_at <= end_time]

        total = len(executions)
        pending = len([e for e in executions if e.status == JobStatus.PENDING])
        running = len([e for e in executions if e.status == JobStatus.RUNNING])
        completed = len([e for e in executions if e.status == JobStatus.COMPLETED])
        failed = len([e for e in executions if e.status == JobStatus.FAILED])
        retrying = len([e for e in executions if e.status == JobStatus.RETRYING])

        # Calculate durations
        completed_executions = [
            e for e in executions
            if e.status == JobStatus.COMPLETED and e.duration_ms > 0
        ]
        durations = [e.duration_ms for e in completed_executions]

        avg_duration = sum(durations) / len(durations) if durations else 0
        sorted_durations = sorted(durations)
        p95_duration = (
            sorted_durations[int(len(sorted_durations) * 0.95)]
            if len(sorted_durations) > 20
            else max(sorted_durations) if sorted_durations else 0
        )

        # Success rate
        finished = completed + failed
        success_rate = (completed / finished * 100) if finished > 0 else 0

        # Throughput
        if completed_executions and start_time:
            time_range = (end_time or datetime.now(timezone.utc)) - start_time
            minutes = time_range.total_seconds() / 60
            throughput = completed / minutes if minutes > 0 else 0
        else:
            throughput = 0

        # By status
        by_status = {}
        for status in JobStatus:
            count = len([e for e in executions if e.status == status])
            if count > 0:
                by_status[status.value] = count

        # By queue
        by_queue: dict[str, int] = {}
        for e in executions:
            by_queue[e.queue] = by_queue.get(e.queue, 0) + 1

        # By job type
        by_job_type: dict[str, int] = {}
        for e in executions:
            job = self._jobs.get(e.job_id)
            if job:
                jt = job.job_type.value
                by_job_type[jt] = by_job_type.get(jt, 0) + 1

        return JobMetrics(
            total_jobs=total,
            pending_jobs=pending,
            running_jobs=running,
            completed_jobs=completed,
            failed_jobs=failed,
            retrying_jobs=retrying,
            avg_duration_ms=avg_duration,
            p95_duration_ms=float(p95_duration),
            success_rate=success_rate,
            throughput_per_minute=throughput,
            by_status=by_status,
            by_queue=by_queue,
            by_job_type=by_job_type,
        )

    # ========================================
    # Summary
    # ========================================

    def get_summary(self) -> dict[str, Any]:
        """Get overall summary."""
        health = self.check_health()
        metrics = self.get_metrics()
        active_alerts = self.get_active_alerts()

        return {
            "health_status": health["status"],
            "total_jobs_defined": len(self._jobs),
            "total_executions": len(self._executions),
            "total_workers": len(self._workers),
            "active_workers": len(self.get_active_workers()),
            "pending_executions": metrics.pending_jobs,
            "running_executions": metrics.running_jobs,
            "completed_executions": metrics.completed_jobs,
            "failed_executions": metrics.failed_jobs,
            "success_rate_percent": round(metrics.success_rate, 2),
            "active_alerts": len(active_alerts),
            "queues": len(self.get_all_queues()),
        }
