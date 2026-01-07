"""Tests for Job Health Monitoring Service.

Tests job definitions, executions, workers, queues,
health checking, and metrics.
"""

import pytest
from datetime import datetime, timezone, timedelta

from sensei.services.job_health import (
    JobHealthService,
    JobDefinition,
    JobExecution,
    Worker,
    Queue,
    JobMetrics,
    HealthCheck,
    Alert,
    JobType,
    JobStatus,
    JobPriority,
    HealthStatus,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def service() -> JobHealthService:
    """Create a fresh JobHealthService instance."""
    return JobHealthService()


@pytest.fixture
def sample_job(service: JobHealthService) -> JobDefinition:
    """Create a sample job definition."""
    return service.register_job(
        name="test_job",
        handler="test.handler.run",
        job_type=JobType.ASYNC,
        description="A test job",
        queue="test",
        max_retries=3,
        timeout_seconds=300,
        tags=["test", "sample"],
    )


@pytest.fixture
def sample_execution(
    service: JobHealthService,
    sample_job: JobDefinition,
) -> JobExecution:
    """Create a sample job execution."""
    return service.enqueue_job(
        job_id=sample_job.id,
        input_data={"key": "value"},
    )


@pytest.fixture
def sample_worker(service: JobHealthService) -> Worker:
    """Create a sample worker."""
    return service.register_worker(
        name="worker-1",
        queues=["default", "test"],
        hostname="localhost",
        pid=12345,
    )


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Test enum values."""

    def test_job_types(self) -> None:
        """Verify all job types exist."""
        expected = {"scheduled", "async", "batch", "worker", "cron", "trigger"}
        actual = {t.value for t in JobType}
        assert actual == expected

    def test_job_statuses(self) -> None:
        """Verify all job statuses exist."""
        expected = {
            "pending", "running", "completed", "failed",
            "cancelled", "retrying", "timeout",
        }
        actual = {s.value for s in JobStatus}
        assert actual == expected

    def test_job_priorities(self) -> None:
        """Verify all priorities exist."""
        expected = {"critical", "high", "normal", "low", "background"}
        actual = {p.value for p in JobPriority}
        assert actual == expected

    def test_health_statuses(self) -> None:
        """Verify all health statuses exist."""
        expected = {"healthy", "degraded", "unhealthy", "unknown"}
        actual = {h.value for h in HealthStatus}
        assert actual == expected


# ============================================================
# Job Definition Tests
# ============================================================


class TestJobDefinition:
    """Test job definition management."""

    def test_default_jobs_loaded(self, service: JobHealthService) -> None:
        """Test that default jobs are loaded."""
        jobs = service.get_all_jobs()
        assert len(jobs) >= 5  # We defined 5 default jobs

    def test_register_job(self, service: JobHealthService) -> None:
        """Test registering a job."""
        job = service.register_job(
            name="new_job",
            handler="handler.run",
            job_type=JobType.BATCH,
            description="New batch job",
        )

        assert job.name == "new_job"
        assert job.job_type == JobType.BATCH
        assert job.is_active is True

    def test_register_job_with_all_options(self, service: JobHealthService) -> None:
        """Test registering job with all options."""
        job = service.register_job(
            name="full_job",
            handler="handler.full",
            job_type=JobType.SCHEDULED,
            description="Full options job",
            queue="high-priority",
            default_priority=JobPriority.HIGH,
            max_retries=5,
            retry_delay_seconds=120,
            timeout_seconds=600,
            expected_duration_seconds=180,
            schedule="0 * * * *",
            tags=["hourly", "important"],
            metadata={"owner": "team-a"},
        )

        assert job.max_retries == 5
        assert job.schedule == "0 * * * *"
        assert "hourly" in job.tags

    def test_get_job(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test getting a job."""
        retrieved = service.get_job(sample_job.id)
        assert retrieved is not None
        assert retrieved.id == sample_job.id

    def test_get_job_nonexistent(self, service: JobHealthService) -> None:
        """Test getting non-existent job."""
        job = service.get_job("nonexistent")
        assert job is None

    def test_get_job_by_name(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test getting job by name."""
        retrieved = service.get_job_by_name("test_job")
        assert retrieved is not None
        assert retrieved.name == "test_job"

    def test_get_jobs_by_type(self, service: JobHealthService) -> None:
        """Test getting jobs by type."""
        cron_jobs = service.get_jobs_by_type(JobType.CRON)
        assert len(cron_jobs) >= 1

    def test_get_jobs_by_queue(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test getting jobs by queue."""
        test_jobs = service.get_jobs_by_queue("test")
        assert sample_job.id in [j.id for j in test_jobs]

    def test_get_scheduled_jobs(self, service: JobHealthService) -> None:
        """Test getting scheduled jobs."""
        scheduled = service.get_scheduled_jobs()
        assert len(scheduled) >= 1
        assert all(j.schedule for j in scheduled)

    def test_update_job(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test updating a job."""
        updated = service.update_job(
            sample_job.id,
            description="Updated description",
            max_retries=5,
            timeout_seconds=600,
        )

        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.max_retries == 5

    def test_update_job_nonexistent(self, service: JobHealthService) -> None:
        """Test updating non-existent job."""
        result = service.update_job("nonexistent", description="Test")
        assert result is None

    def test_delete_job(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test deleting a job."""
        result = service.delete_job(sample_job.id)
        assert result is True
        assert service.get_job(sample_job.id) is None


# ============================================================
# Execution Tests
# ============================================================


class TestExecution:
    """Test job execution management."""

    def test_enqueue_job(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test enqueueing a job."""
        execution = service.enqueue_job(
            sample_job.id,
            input_data={"param": "value"},
        )

        assert execution is not None
        assert execution.status == JobStatus.PENDING
        assert execution.job_id == sample_job.id
        assert execution.input_data["param"] == "value"

    def test_enqueue_job_with_priority(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test enqueueing job with priority."""
        execution = service.enqueue_job(
            sample_job.id,
            priority=JobPriority.CRITICAL,
        )

        assert execution.priority == JobPriority.CRITICAL

    def test_enqueue_job_scheduled(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test enqueueing scheduled job."""
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
        execution = service.enqueue_job(
            sample_job.id,
            scheduled_at=scheduled_time,
        )

        assert execution.scheduled_at == scheduled_time

    def test_enqueue_inactive_job(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test enqueueing inactive job."""
        service.update_job(sample_job.id, is_active=False)
        execution = service.enqueue_job(sample_job.id)
        assert execution is None

    def test_get_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test getting an execution."""
        retrieved = service.get_execution(sample_execution.id)
        assert retrieved is not None
        assert retrieved.id == sample_execution.id

    def test_get_executions_by_status(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test getting executions by status."""
        pending = service.get_executions_by_status(JobStatus.PENDING)
        assert sample_execution.id in [e.id for e in pending]

    def test_get_executions_by_job(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
        sample_execution: JobExecution,
    ) -> None:
        """Test getting executions by job."""
        executions = service.get_executions_by_job(sample_job.id)
        assert sample_execution.id in [e.id for e in executions]

    def test_get_pending_executions(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test getting pending executions."""
        pending = service.get_pending_executions()
        assert sample_execution.id in [e.id for e in pending]

    def test_get_recent_executions(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test getting recent executions."""
        for i in range(5):
            service.enqueue_job(sample_job.id)

        recent = service.get_recent_executions(limit=3)
        assert len(recent) == 3

    def test_start_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
        sample_worker: Worker,
    ) -> None:
        """Test starting an execution."""
        updated = service.start_execution(
            sample_execution.id,
            worker_id=sample_worker.id,
        )

        assert updated is not None
        assert updated.status == JobStatus.RUNNING
        assert updated.started_at is not None
        assert updated.worker_id == sample_worker.id

    def test_update_progress(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test updating progress."""
        service.start_execution(sample_execution.id)
        updated = service.update_progress(
            sample_execution.id,
            progress_percent=50,
            progress_message="Halfway done",
        )

        assert updated is not None
        assert updated.progress_percent == 50
        assert updated.progress_message == "Halfway done"

    def test_update_progress_clamps_value(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test that progress is clamped to 0-100."""
        service.update_progress(sample_execution.id, 150)
        execution = service.get_execution(sample_execution.id)
        assert execution.progress_percent == 100

        service.update_progress(sample_execution.id, -10)
        execution = service.get_execution(sample_execution.id)
        assert execution.progress_percent == 0

    def test_complete_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test completing an execution."""
        service.start_execution(sample_execution.id)
        updated = service.complete_execution(
            sample_execution.id,
            output_data={"result": "success"},
        )

        assert updated is not None
        assert updated.status == JobStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.progress_percent == 100
        assert updated.output_data["result"] == "success"

    def test_complete_execution_calculates_duration(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test that completion calculates duration."""
        service.start_execution(sample_execution.id)
        updated = service.complete_execution(sample_execution.id)

        assert updated.duration_ms >= 0

    def test_fail_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test failing an execution."""
        service.start_execution(sample_execution.id)
        updated = service.fail_execution(
            sample_execution.id,
            error_message="Something went wrong",
            error_trace="Traceback...",
        )

        assert updated is not None
        assert updated.error_message == "Something went wrong"
        # Should retry since attempts remaining
        assert updated.status == JobStatus.RETRYING
        assert updated.attempt == 2

    def test_fail_execution_max_attempts(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test failing execution at max attempts."""
        execution = service.enqueue_job(sample_job.id)
        execution.attempt = execution.max_attempts  # At max

        service.start_execution(execution.id)
        updated = service.fail_execution(execution.id, "Final failure")

        assert updated.status == JobStatus.FAILED

    def test_cancel_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test cancelling an execution."""
        updated = service.cancel_execution(sample_execution.id)

        assert updated is not None
        assert updated.status == JobStatus.CANCELLED
        assert updated.completed_at is not None

    def test_timeout_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test timing out an execution."""
        service.start_execution(sample_execution.id)
        updated = service.timeout_execution(sample_execution.id)

        assert updated is not None
        assert updated.status == JobStatus.TIMEOUT
        assert "timed out" in updated.error_message.lower()

    def test_retry_execution(
        self,
        service: JobHealthService,
        sample_execution: JobExecution,
    ) -> None:
        """Test creating retry execution."""
        service.start_execution(sample_execution.id)
        service.fail_execution(sample_execution.id, "Error")

        # fail_execution already incremented attempt
        failed_exec = service.get_execution(sample_execution.id)
        new_execution = service.retry_execution(sample_execution.id)

        assert new_execution is not None
        assert new_execution.id != sample_execution.id
        assert new_execution.attempt == failed_exec.attempt
        assert new_execution.status == JobStatus.PENDING


# ============================================================
# Worker Tests
# ============================================================


class TestWorker:
    """Test worker management."""

    def test_register_worker(self, service: JobHealthService) -> None:
        """Test registering a worker."""
        worker = service.register_worker(
            name="new-worker",
            queues=["default", "high"],
            hostname="server1",
            pid=9999,
        )

        assert worker.name == "new-worker"
        assert "default" in worker.queues
        assert worker.is_active is True

    def test_get_worker(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test getting a worker."""
        retrieved = service.get_worker(sample_worker.id)
        assert retrieved is not None
        assert retrieved.id == sample_worker.id

    def test_get_active_workers(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test getting active workers."""
        active = service.get_active_workers()
        assert sample_worker.id in [w.id for w in active]

    def test_get_workers_by_queue(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test getting workers by queue."""
        workers = service.get_workers_by_queue("test")
        assert sample_worker.id in [w.id for w in workers]

    def test_heartbeat(
        self,
        service: JobHealthService,
        sample_worker: Worker,
        sample_execution: JobExecution,
    ) -> None:
        """Test worker heartbeat."""
        service.start_execution(sample_execution.id, sample_worker.id)

        updated = service.heartbeat(
            sample_worker.id,
            current_job_id=sample_execution.id,
            cpu_usage_percent=45.5,
            memory_usage_mb=512.0,
        )

        assert updated is not None
        assert updated.current_job_id == sample_execution.id
        assert updated.cpu_usage_percent == 45.5
        assert updated.status == HealthStatus.HEALTHY

    def test_increment_job_count(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test incrementing job count."""
        service.increment_job_count(sample_worker.id, is_success=True)
        service.increment_job_count(sample_worker.id, is_success=True)
        service.increment_job_count(sample_worker.id, is_success=False)

        worker = service.get_worker(sample_worker.id)
        assert worker.jobs_processed == 3
        assert worker.jobs_failed == 1

    def test_deactivate_worker(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test deactivating a worker."""
        updated = service.deactivate_worker(sample_worker.id)

        assert updated is not None
        assert updated.is_active is False
        assert updated.status == HealthStatus.UNKNOWN

    def test_check_stale_workers(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test checking for stale workers."""
        # Make worker stale by setting old heartbeat
        sample_worker.last_heartbeat = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        )

        stale = service.check_stale_workers(stale_threshold_seconds=60)

        assert sample_worker.id in [w.id for w in stale]
        assert sample_worker.status == HealthStatus.UNHEALTHY


# ============================================================
# Queue Tests
# ============================================================


class TestQueue:
    """Test queue management."""

    def test_get_queue_stats(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
        sample_worker: Worker,
    ) -> None:
        """Test getting queue stats."""
        # Add some executions
        for i in range(5):
            service.enqueue_job(sample_job.id)

        stats = service.get_queue_stats("test")

        assert stats.name == "test"
        assert stats.pending_count == 5
        assert stats.workers_count >= 1

    def test_get_queue_stats_with_running(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test queue stats with running jobs."""
        exec1 = service.enqueue_job(sample_job.id)
        service.enqueue_job(sample_job.id)
        service.start_execution(exec1.id)

        stats = service.get_queue_stats("test")

        assert stats.pending_count == 1
        assert stats.processing_count == 1

    def test_get_all_queues(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test getting all queue names."""
        queues = service.get_all_queues()
        assert "default" in queues
        assert "test" in queues


# ============================================================
# Health Check Tests
# ============================================================


class TestHealthCheck:
    """Test health checking."""

    def test_check_health(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test health check."""
        health = service.check_health()

        assert "status" in health
        assert "checks" in health
        assert "timestamp" in health

    def test_check_health_healthy_system(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test health check on healthy system."""
        service.heartbeat(sample_worker.id)

        health = service.check_health()
        assert health["status"] in ["healthy", "degraded"]

    def test_check_health_stale_workers(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test health check with stale workers."""
        sample_worker.last_heartbeat = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        )

        health = service.check_health()
        assert health["status"] in ["degraded", "unhealthy"]

    def test_check_health_queue_backlog(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test health check with queue backlog."""
        # Create many pending jobs (but not enough to trigger warning)
        for i in range(50):
            service.enqueue_job(sample_job.id)

        health = service.check_health()
        # Should still be healthy with 50 jobs
        assert "checks" in health

    def test_get_health_history(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test getting health history."""
        service.check_health()
        service.check_health()

        history = service.get_health_history(limit=5)
        assert len(history) >= 2

    def test_get_health_history_by_component(
        self,
        service: JobHealthService,
        sample_worker: Worker,
    ) -> None:
        """Test getting health history by component."""
        service.check_health()

        history = service.get_health_history(component="workers")
        assert all(h.component == "workers" for h in history)


# ============================================================
# Alert Tests
# ============================================================


class TestAlerts:
    """Test alert management."""

    def test_create_alert(self, service: JobHealthService) -> None:
        """Test creating an alert."""
        alert = service.create_alert(
            alert_type="test_alert",
            message="Test alert message",
            component="test",
            severity="high",
        )

        assert alert.alert_type == "test_alert"
        assert alert.severity == "high"
        assert alert.is_active is True

    def test_get_alert(self, service: JobHealthService) -> None:
        """Test getting an alert."""
        created = service.create_alert(
            alert_type="test",
            message="Test",
        )
        retrieved = service.get_alert(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_active_alerts(self, service: JobHealthService) -> None:
        """Test getting active alerts."""
        service.create_alert(alert_type="active", message="Active")
        alert2 = service.create_alert(alert_type="resolved", message="Resolved")
        service.resolve_alert(alert2.id)

        active = service.get_active_alerts()
        alert_types = [a.alert_type for a in active]

        assert "active" in alert_types
        assert "resolved" not in alert_types

    def test_resolve_alert(self, service: JobHealthService) -> None:
        """Test resolving an alert."""
        alert = service.create_alert(
            alert_type="test",
            message="Test",
        )
        updated = service.resolve_alert(alert.id)

        assert updated is not None
        assert updated.is_active is False
        assert updated.resolved_at is not None

    def test_check_alerts_queue_backlog(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test that check_alerts creates queue backlog alerts."""
        # Create many pending jobs
        for i in range(600):
            service.enqueue_job(sample_job.id)

        new_alerts = service.check_alerts()

        queue_alerts = [a for a in new_alerts if a.alert_type == "queue_backlog"]
        assert len(queue_alerts) >= 1

    def test_check_alerts_no_duplicates(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test that check_alerts doesn't create duplicate alerts."""
        for i in range(600):
            service.enqueue_job(sample_job.id)

        first_alerts = service.check_alerts()
        second_alerts = service.check_alerts()

        # Second call shouldn't create duplicates
        assert len(second_alerts) == 0 or len(second_alerts) < len(first_alerts)


# ============================================================
# Metrics Tests
# ============================================================


class TestMetrics:
    """Test metrics functionality."""

    def test_get_metrics_empty(self, service: JobHealthService) -> None:
        """Test metrics with no executions."""
        metrics = service.get_metrics()
        assert metrics.total_jobs == 0

    def test_get_metrics(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test getting metrics."""
        # Create some executions
        exec1 = service.enqueue_job(sample_job.id)
        exec2 = service.enqueue_job(sample_job.id)
        exec3 = service.enqueue_job(sample_job.id)

        service.start_execution(exec1.id)
        service.complete_execution(exec1.id)

        service.start_execution(exec2.id)
        service.fail_execution(exec2.id, "Error")

        metrics = service.get_metrics()

        assert metrics.total_jobs == 3
        assert metrics.completed_jobs == 1
        assert metrics.pending_jobs == 1  # exec3

    def test_get_metrics_success_rate(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test success rate calculation."""
        # Complete 3, fail 1
        for i in range(3):
            e = service.enqueue_job(sample_job.id)
            service.start_execution(e.id)
            service.complete_execution(e.id)

        e = service.enqueue_job(sample_job.id)
        e.attempt = e.max_attempts  # Max attempts so it fails
        service.start_execution(e.id)
        service.fail_execution(e.id, "Error")

        metrics = service.get_metrics()
        assert metrics.success_rate == 75.0  # 3/4

    def test_get_metrics_by_status(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test metrics grouped by status."""
        e1 = service.enqueue_job(sample_job.id)
        service.start_execution(e1.id)
        service.complete_execution(e1.id)

        service.enqueue_job(sample_job.id)

        metrics = service.get_metrics()

        assert "completed" in metrics.by_status
        assert "pending" in metrics.by_status

    def test_get_metrics_by_queue(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test metrics grouped by queue."""
        service.enqueue_job(sample_job.id)

        metrics = service.get_metrics()

        assert "test" in metrics.by_queue

    def test_get_metrics_with_time_filter(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
    ) -> None:
        """Test metrics with time filtering."""
        service.enqueue_job(sample_job.id)

        future = datetime.now(timezone.utc) + timedelta(hours=1)
        metrics = service.get_metrics(start_time=future)

        assert metrics.total_jobs == 0


# ============================================================
# Summary Tests
# ============================================================


class TestSummary:
    """Test summary functionality."""

    def test_get_summary(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
        sample_worker: Worker,
    ) -> None:
        """Test getting summary."""
        service.enqueue_job(sample_job.id)

        summary = service.get_summary()

        assert "health_status" in summary
        assert "total_jobs_defined" in summary
        assert "total_executions" in summary
        assert "total_workers" in summary
        assert "active_workers" in summary
        assert "success_rate_percent" in summary
        assert "queues" in summary

    def test_summary_counts(
        self,
        service: JobHealthService,
        sample_job: JobDefinition,
        sample_worker: Worker,
    ) -> None:
        """Test summary counts are accurate."""
        # Create some executions
        for i in range(3):
            e = service.enqueue_job(sample_job.id)
            service.start_execution(e.id)
            service.complete_execution(e.id)

        service.enqueue_job(sample_job.id)  # Pending

        summary = service.get_summary()

        assert summary["total_executions"] >= 4
        assert summary["completed_executions"] >= 3
        assert summary["pending_executions"] >= 1


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests."""

    def test_full_job_lifecycle(
        self,
        service: JobHealthService,
    ) -> None:
        """Test complete job lifecycle."""
        # Register job
        job = service.register_job(
            name="lifecycle_job",
            handler="handler.lifecycle",
            job_type=JobType.ASYNC,
            max_retries=2,
        )

        # Register worker
        worker = service.register_worker(
            name="lifecycle-worker",
            queues=["default"],
        )

        # Enqueue job
        execution = service.enqueue_job(
            job.id,
            input_data={"key": "value"},
        )
        assert execution.status == JobStatus.PENDING

        # Start job
        service.start_execution(execution.id, worker.id)
        assert service.get_execution(execution.id).status == JobStatus.RUNNING

        # Update progress
        service.update_progress(execution.id, 50, "Halfway")

        # Complete job
        service.complete_execution(execution.id, {"result": "done"})

        final = service.get_execution(execution.id)
        assert final.status == JobStatus.COMPLETED
        assert final.output_data["result"] == "done"

        # Update worker
        service.increment_job_count(worker.id, is_success=True)
        updated_worker = service.get_worker(worker.id)
        assert updated_worker.jobs_processed == 1

        # Check metrics
        metrics = service.get_metrics()
        assert metrics.completed_jobs >= 1

    def test_failure_and_retry_workflow(
        self,
        service: JobHealthService,
    ) -> None:
        """Test failure and retry workflow."""
        job = service.register_job(
            name="retry_job",
            max_retries=2,
        )

        execution = service.enqueue_job(job.id)
        service.start_execution(execution.id)

        # First failure - should retry
        service.fail_execution(execution.id, "First error")
        assert service.get_execution(execution.id).status == JobStatus.RETRYING

        # Create retry
        retry = service.retry_execution(execution.id)
        assert retry.attempt == 2

        # Second failure - should retry
        service.start_execution(retry.id)
        service.fail_execution(retry.id, "Second error")

        # Create another retry
        retry2 = service.retry_execution(retry.id)
        assert retry2.attempt == 3

        # Third failure - max attempts reached
        retry2.attempt = 3
        retry2.max_attempts = 3
        service.start_execution(retry2.id)
        service.fail_execution(retry2.id, "Final error")

        assert service.get_execution(retry2.id).status == JobStatus.FAILED

    def test_monitoring_workflow(
        self,
        service: JobHealthService,
    ) -> None:
        """Test monitoring workflow."""
        # Setup
        job = service.register_job(name="monitor_job")
        worker = service.register_worker(
            name="monitor-worker",
            queues=["default"],
        )

        # Create some activity
        for i in range(5):
            e = service.enqueue_job(job.id)
            service.start_execution(e.id, worker.id)
            if i % 2 == 0:
                service.complete_execution(e.id)
            else:
                e.attempt = e.max_attempts
                service.fail_execution(e.id, "Error")
            service.increment_job_count(worker.id, is_success=(i % 2 == 0))

        # Update worker heartbeat
        service.heartbeat(
            worker.id,
            cpu_usage_percent=25.0,
            memory_usage_mb=256.0,
        )

        # Check health
        health = service.check_health()
        assert health["status"] in ["healthy", "degraded"]

        # Get metrics
        metrics = service.get_metrics()
        assert metrics.total_jobs == 5
        assert metrics.completed_jobs == 3
        assert metrics.success_rate == 60.0  # 3/5

        # Get summary
        summary = service.get_summary()
        assert summary["total_executions"] == 5
        assert summary["success_rate_percent"] == 60.0
