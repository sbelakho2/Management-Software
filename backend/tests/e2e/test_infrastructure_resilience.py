"""E2E Tests for Infrastructure Resilience Service (Development Plan 20.3)."""

from __future__ import annotations

import pytest

from sensei.services.infrastructure_resilience import (
    BackupRestoreResult,
    DeepHealthReport,
    FileIntegrityResult,
    HealthStatus,
    InfrastructureResilienceService,
    PerformanceMetrics,
    ServiceType,
    SlowQueryEvent,
)


@pytest.fixture
def svc() -> InfrastructureResilienceService:
    return InfrastructureResilienceService()


class TestONNXInferenceLatency:
    def test_latency_under_threshold(self, svc: InfrastructureResilienceService) -> None:
        metrics = svc.measure_onnx_latency("admin", simulated_latency_ms=150)

        assert metrics.inference_latency_ms == 150
        passes, message = svc.verify_inference_latency("admin", latency_ms=150)
        assert passes
        assert "under" in message.lower()

    def test_latency_over_threshold(self, svc: InfrastructureResilienceService) -> None:
        metrics = svc.measure_onnx_latency("admin", simulated_latency_ms=250)

        assert metrics.inference_latency_ms == 250
        passes, message = svc.verify_inference_latency("admin", latency_ms=250)
        assert not passes
        assert "exceeds" in message.lower()

    def test_latency_at_exact_threshold(self, svc: InfrastructureResilienceService) -> None:
        passes, _ = svc.verify_inference_latency("admin", latency_ms=200)
        assert passes  # 200ms is exactly the threshold.


class TestMemoryThrottling:
    def test_throttling_activates_at_threshold(self, svc: InfrastructureResilienceService) -> None:
        # 90% of 8192 = 7372.8 MB.
        throttled, message = svc.simulate_memory_load(
            "admin",
            load_mb=7500,
            memory_limit_mb=8192,
        )

        assert throttled
        assert "throttling activated" in message.lower()

    def test_no_throttling_below_threshold(self, svc: InfrastructureResilienceService) -> None:
        throttled, message = svc.simulate_memory_load(
            "admin",
            load_mb=4000,
            memory_limit_mb=8192,
        )

        assert not throttled
        assert "no throttling needed" in message.lower()

    def test_prevents_oom(self, svc: InfrastructureResilienceService) -> None:
        # Try to load at 95% of limit.
        throttled, _ = svc.simulate_memory_load(
            "admin",
            load_mb=7800,
            memory_limit_mb=8192,
        )

        assert throttled
        # Memory should be reduced below threshold.
        assert svc._memory_usage_mb < 7372.8


class TestModelWarmup:
    def test_warm_models_reduces_latency(self, svc: InfrastructureResilienceService) -> None:
        # Before warmup.
        latency_cold, passes_cold = svc.measure_first_query_latency(
            "admin",
            simulated_latency_ms=800,
        )
        assert latency_cold == 800
        assert not passes_cold

        # After warmup.
        svc.warm_models("admin")
        latency_warm, passes_warm = svc.measure_first_query_latency(
            "admin",
            simulated_latency_ms=20,
        )
        assert latency_warm == 20
        assert passes_warm

    def test_zero_first_query_latency_after_warmup(self, svc: InfrastructureResilienceService) -> None:
        svc.warm_models("admin")
        latency, passes = svc.measure_first_query_latency(
            "admin",
            simulated_latency_ms=10,
        )

        assert latency <= 50  # Under threshold.
        assert passes


class TestDBAutonomy:
    def test_slow_query_detection(self, svc: InfrastructureResilienceService) -> None:
        event = svc.detect_slow_query(
            "admin",
            query="SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at",
            execution_time_ms=1500,
            table_name="orders",
        )

        assert event is not None
        assert event.execution_time_ms == 1500
        assert len(event.suggested_indexes) > 0
        assert any("idx_orders_status" in idx for idx in event.suggested_indexes)

    def test_fast_query_no_event(self, svc: InfrastructureResilienceService) -> None:
        event = svc.detect_slow_query(
            "admin",
            query="SELECT * FROM orders WHERE id = 1",
            execution_time_ms=50,
            table_name="orders",
        )

        assert event is None

    def test_apply_index_recommendation(self, svc: InfrastructureResilienceService) -> None:
        event = svc.detect_slow_query(
            "admin",
            query="SELECT * FROM products WHERE status = 'active'",
            execution_time_ms=800,
            table_name="products",
        )

        assert event is not None
        assert not event.applied

        success = svc.apply_index_recommendation("admin", event_id=event.id)
        assert success

        # Verify applied flag.
        slow_queries = svc.get_slow_queries()
        assert any(q.id == event.id and q.applied for q in slow_queries)


class TestHealthWatchdog:
    def test_all_services_healthy(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check("admin")

        assert report.overall_status == HealthStatus.HEALTHY
        assert len(report.services) == len(ServiceType)
        assert len(report.warnings) == 0

    def test_degraded_service(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check(
            "admin",
            service_overrides={ServiceType.REDIS: HealthStatus.DEGRADED},
        )

        assert report.overall_status == HealthStatus.DEGRADED
        assert any("redis" in w.lower() for w in report.warnings)

    def test_unhealthy_service(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check(
            "admin",
            service_overrides={ServiceType.DATABASE: HealthStatus.UNHEALTHY},
        )

        assert report.overall_status == HealthStatus.UNHEALTHY
        assert any("database" in w.lower() for w in report.warnings)

    def test_multiple_degraded_services(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check(
            "admin",
            service_overrides={
                ServiceType.REDIS: HealthStatus.DEGRADED,
                ServiceType.MODEL_SERVER: HealthStatus.DEGRADED,
            },
        )

        assert report.overall_status == HealthStatus.DEGRADED
        assert len(report.warnings) == 2

    def test_health_check_includes_all_services(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check("admin")

        service_types = {s.service for s in report.services}
        assert service_types == set(ServiceType)


class TestS3LocalConsistency:
    def test_all_files_match(self, svc: InfrastructureResilienceService) -> None:
        # Register files in both locations.
        svc.register_file("admin", path="/docs/file1.pdf", content=b"file1content", location="both")
        svc.register_file("admin", path="/docs/file2.pdf", content=b"file2content", location="both")

        result = svc.verify_file_integrity("admin")

        assert result.total_files == 2
        assert result.matched_files == 2
        assert result.mismatched_files == 0
        assert result.missing_files == 0
        assert result.match_percentage == 100.0

    def test_missing_in_s3(self, svc: InfrastructureResilienceService) -> None:
        svc.register_file("admin", path="/docs/file1.pdf", content=b"content", location="local")

        result = svc.verify_file_integrity("admin")

        assert result.missing_files == 1
        assert any(m["issue"] == "missing_in_s3" for m in result.mismatches)

    def test_missing_in_local(self, svc: InfrastructureResilienceService) -> None:
        svc.register_file("admin", path="/docs/file1.pdf", content=b"content", location="s3")

        result = svc.verify_file_integrity("admin")

        assert result.missing_files == 1
        assert any(m["issue"] == "missing_in_local" for m in result.mismatches)

    def test_checksum_mismatch(self, svc: InfrastructureResilienceService) -> None:
        svc.register_file("admin", path="/docs/file1.pdf", content=b"content_s3", location="s3")
        svc.register_file("admin", path="/docs/file1.pdf", content=b"content_local", location="local")

        result = svc.verify_file_integrity("admin")

        assert result.mismatched_files == 1
        assert any(m["issue"] == "checksum_mismatch" for m in result.mismatches)


class TestBackupRestoreFireDrill:
    def test_restore_under_15_minutes(self, svc: InfrastructureResilienceService) -> None:
        result = svc.perform_restore_drill(
            "admin",
            source_snapshot="prod-2024-01-15",
            target_sandbox="sandbox-qa",
            simulated_duration_minutes=10,
        )

        assert result.success
        assert result.duration_minutes == 10
        assert len(result.errors) == 0

    def test_restore_over_15_minutes_fails(self, svc: InfrastructureResilienceService) -> None:
        result = svc.perform_restore_drill(
            "admin",
            source_snapshot="prod-2024-01-15",
            target_sandbox="sandbox-qa",
            simulated_duration_minutes=20,
        )

        assert not result.success
        assert len(result.errors) == 1
        assert "exceeds" in result.errors[0].lower()

    def test_verify_restore_time(self, svc: InfrastructureResilienceService) -> None:
        passes, message = svc.verify_restore_time("admin", duration_minutes=12)
        assert passes
        assert "under" in message.lower()

        passes, message = svc.verify_restore_time("admin", duration_minutes=18)
        assert not passes
        assert "exceeds" in message.lower()

    def test_restore_result_contains_details(self, svc: InfrastructureResilienceService) -> None:
        result = svc.perform_restore_drill(
            "admin",
            source_snapshot="prod-2024-01-15",
            target_sandbox="sandbox-qa",
            simulated_duration_minutes=8,
            tables=100,
            rows=500000,
        )

        assert result.source_snapshot == "prod-2024-01-15"
        assert result.target_sandbox == "sandbox-qa"
        assert result.tables_restored == 100
        assert result.rows_restored == 500000


class TestRBACEnforcement:
    def test_viewer_cannot_access(self, svc: InfrastructureResilienceService) -> None:
        with pytest.raises(PermissionError):
            svc.measure_onnx_latency("viewer")

    def test_operator_cannot_access(self, svc: InfrastructureResilienceService) -> None:
        with pytest.raises(PermissionError):
            svc.deep_health_check("operator")

    def test_admin_can_access(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check("admin")
        assert report is not None

    def test_secops_can_access(self, svc: InfrastructureResilienceService) -> None:
        report = svc.deep_health_check("secops")
        assert report is not None

    def test_it_can_access(self, svc: InfrastructureResilienceService) -> None:
        result = svc.verify_file_integrity("it")
        assert result is not None

    def test_ceo_can_access(self, svc: InfrastructureResilienceService) -> None:
        metrics = svc.measure_onnx_latency("ceo", simulated_latency_ms=100)
        assert metrics is not None
