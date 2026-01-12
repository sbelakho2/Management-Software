"""
Tests for Chaos/Failure Mode Testing Service.

Tests system resilience capabilities including:
- Failure scenario management
- Job retry behavior verification
- Graceful degradation testing
- Circuit breaker validation
- Recovery metrics tracking
"""

from datetime import datetime, timezone

import pytest

from sensei.services.utils.chaos_testing import (
    ChaosTestingService,
    CircuitState,
    ComponentType,
    DegradationLevel,
    FailureType,
    TestStatus,
    get_chaos_testing_service,
    reset_chaos_testing_service,
)


@pytest.fixture
def service():
    """Create a fresh chaos testing service for each test."""
    reset_chaos_testing_service()
    svc = get_chaos_testing_service()
    yield svc
    reset_chaos_testing_service()


# ===== Scenario Management Tests =====


class TestScenarioManagement:
    """Tests for failure scenario management."""
    
    def test_create_scenario(self, service: ChaosTestingService):
        """Test creating a failure scenario."""
        scenario = service.create_scenario(
            name="Storage Outage",
            description="Simulate complete storage failure",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
            duration_seconds=60,
            intensity=1.0,
        )
        
        assert scenario.id is not None
        assert scenario.name == "Storage Outage"
        assert scenario.failure_type == FailureType.STORAGE_DOWN
        assert scenario.target_component == ComponentType.STORAGE
        assert scenario.duration_seconds == 60
        assert scenario.intensity == 1.0
    
    def test_create_scenario_with_parameters(self, service: ChaosTestingService):
        """Test creating a scenario with custom parameters."""
        scenario = service.create_scenario(
            name="Network Latency",
            description="Inject network latency",
            failure_type=FailureType.NETWORK_LATENCY,
            target_component=ComponentType.API,
            duration_seconds=120,
            intensity=0.5,
            parameters={"latency_ms": 3000},
        )
        
        assert scenario.parameters["latency_ms"] == 3000
        assert scenario.intensity == 0.5
    
    def test_create_scenario_invalid_intensity(self, service: ChaosTestingService):
        """Test that invalid intensity is rejected."""
        with pytest.raises(ValueError, match="Intensity must be"):
            service.create_scenario(
                name="Test",
                description="Test",
                failure_type=FailureType.STORAGE_DOWN,
                target_component=ComponentType.STORAGE,
                intensity=1.5,
            )
    
    def test_create_scenario_invalid_duration(self, service: ChaosTestingService):
        """Test that invalid duration is rejected."""
        with pytest.raises(ValueError, match="Duration must be"):
            service.create_scenario(
                name="Test",
                description="Test",
                failure_type=FailureType.STORAGE_DOWN,
                target_component=ComponentType.STORAGE,
                duration_seconds=0,
            )
    
    def test_get_scenario(self, service: ChaosTestingService):
        """Test getting a scenario by ID."""
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.DATABASE_DOWN,
            target_component=ComponentType.DATABASE,
        )
        
        retrieved = service.get_scenario(scenario.id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_get_scenario_not_found(self, service: ChaosTestingService):
        """Test getting a non-existent scenario."""
        assert service.get_scenario("nonexistent") is None
    
    def test_list_scenarios(self, service: ChaosTestingService):
        """Test listing all scenarios."""
        for i in range(3):
            service.create_scenario(
                name=f"Scenario {i}",
                description=f"Description {i}",
                failure_type=FailureType.STORAGE_DOWN,
                target_component=ComponentType.STORAGE,
            )
        
        scenarios = service.list_scenarios()
        assert len(scenarios) == 3
    
    def test_delete_scenario(self, service: ChaosTestingService):
        """Test deleting a scenario."""
        scenario = service.create_scenario(
            name="Delete Me",
            description="To be deleted",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        deleted = service.delete_scenario(scenario.id)
        assert deleted is True
        assert service.get_scenario(scenario.id) is None
    
    def test_delete_scenario_not_found(self, service: ChaosTestingService):
        """Test deleting a non-existent scenario."""
        deleted = service.delete_scenario("nonexistent")
        assert deleted is False


# ===== Failure Injection Tests =====


class TestFailureInjection:
    """Tests for failure injection."""
    
    def test_inject_storage_failure(self, service: ChaosTestingService):
        """Test injecting a storage failure."""
        scenario = service.create_scenario(
            name="Storage Down",
            description="Storage failure",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        result = service.inject_failure(scenario.id)
        
        assert result["scenario_id"] == scenario.id
        assert result["failure_type"] == "storage_down"
        assert result["state"]["storage_available"] is False
    
    def test_inject_database_failure(self, service: ChaosTestingService):
        """Test injecting a database failure."""
        scenario = service.create_scenario(
            name="Database Down",
            description="Database failure",
            failure_type=FailureType.DATABASE_DOWN,
            target_component=ComponentType.DATABASE,
        )
        
        result = service.inject_failure(scenario.id)
        
        assert result["state"]["database_available"] is False
    
    def test_inject_network_latency(self, service: ChaosTestingService):
        """Test injecting network latency."""
        scenario = service.create_scenario(
            name="Network Latency",
            description="High latency",
            failure_type=FailureType.NETWORK_LATENCY,
            target_component=ComponentType.API,
            parameters={"latency_ms": 5000},
        )
        
        result = service.inject_failure(scenario.id)
        
        assert result["state"]["network_latency_ms"] == 5000
    
    def test_inject_memory_pressure(self, service: ChaosTestingService):
        """Test injecting memory pressure."""
        scenario = service.create_scenario(
            name="Memory Pressure",
            description="High memory usage",
            failure_type=FailureType.MEMORY_PRESSURE,
            target_component=ComponentType.ML_MODEL,
            parameters={"usage_percent": 95},
        )
        
        result = service.inject_failure(scenario.id)
        
        assert result["state"]["memory_usage_percent"] == 95
    
    def test_inject_failure_not_found(self, service: ChaosTestingService):
        """Test injecting a failure for non-existent scenario."""
        with pytest.raises(ValueError, match="not found"):
            service.inject_failure("nonexistent")
    
    def test_remove_failure(self, service: ChaosTestingService):
        """Test removing an injected failure."""
        scenario = service.create_scenario(
            name="Storage Down",
            description="Storage failure",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        service.inject_failure(scenario.id)
        assert service.get_system_state()["storage_available"] is False
        
        result = service.remove_failure(scenario.id)
        
        assert result["scenario_id"] == scenario.id
        assert result["state"]["storage_available"] is True
    
    def test_remove_failure_not_active(self, service: ChaosTestingService):
        """Test removing a non-active failure."""
        with pytest.raises(ValueError, match="No active failure"):
            service.remove_failure("nonexistent")
    
    def test_get_active_failures(self, service: ChaosTestingService):
        """Test getting active failures."""
        s1 = service.create_scenario(
            name="Storage",
            description="Storage down",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        s2 = service.create_scenario(
            name="Database",
            description="Database down",
            failure_type=FailureType.DATABASE_DOWN,
            target_component=ComponentType.DATABASE,
        )
        
        service.inject_failure(s1.id)
        service.inject_failure(s2.id)
        
        active = service.get_active_failures()
        assert len(active) == 2
    
    def test_cannot_delete_active_failure_scenario(self, service: ChaosTestingService):
        """Test that active failure scenarios cannot be deleted."""
        scenario = service.create_scenario(
            name="Active",
            description="Active scenario",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        service.inject_failure(scenario.id)
        
        with pytest.raises(ValueError, match="Cannot delete active"):
            service.delete_scenario(scenario.id)


# ===== Job Retry Testing =====


class TestJobRetryTesting:
    """Tests for job retry behavior verification."""
    
    def test_create_job_retry_test(self, service: ChaosTestingService):
        """Test creating a job retry test."""
        test = service.create_job_retry_test(
            job_type="pdf_generation",
            failure_point="storage_write",
            max_retries=3,
            retry_delay_seconds=5,
            expected_recovery=True,
        )
        
        assert test.id is not None
        assert test.job_type == "pdf_generation"
        assert test.failure_point == "storage_write"
        assert test.max_retries == 3
        assert test.expected_recovery is True
    
    def test_simulate_job_execution_with_recovery(self, service: ChaosTestingService):
        """Test simulating job execution that recovers."""
        test = service.create_job_retry_test(
            job_type="email_send",
            failure_point="smtp_connect",
            max_retries=3,
            expected_recovery=True,
        )
        
        result = service.simulate_job_execution(test.id, fail_until_attempt=2)
        
        assert result.final_status == "recovered"
        assert result.failure_count == 1
        assert result.success_count == 1
        assert len(result.attempts) == 2
    
    def test_simulate_job_execution_exhausted(self, service: ChaosTestingService):
        """Test simulating job execution that exhausts retries."""
        test = service.create_job_retry_test(
            job_type="external_api",
            failure_point="api_call",
            max_retries=2,
            expected_recovery=False,
        )
        
        result = service.simulate_job_execution(test.id, fail_until_attempt=10)
        
        assert result.final_status == "exhausted_retries"
        assert result.failure_count > 0
        assert result.success_count == 0
    
    def test_simulate_job_execution_not_found(self, service: ChaosTestingService):
        """Test simulating execution for non-existent test."""
        with pytest.raises(ValueError, match="not found"):
            service.simulate_job_execution("nonexistent")
    
    def test_validate_job_retry_behavior_passed(self, service: ChaosTestingService):
        """Test validating successful job retry behavior."""
        test = service.create_job_retry_test(
            job_type="backup",
            failure_point="disk_write",
            max_retries=3,
            expected_recovery=True,
        )
        
        service.simulate_job_execution(test.id, fail_until_attempt=2)
        
        validation = service.validate_job_retry_behavior(test.id)
        
        assert validation["passed"] is True
        assert len(validation["checks"]) == 3
    
    def test_validate_job_retry_behavior_failed(self, service: ChaosTestingService):
        """Test validating failed job retry behavior."""
        test = service.create_job_retry_test(
            job_type="sync",
            failure_point="network",
            max_retries=2,
            expected_recovery=True,  # We expect recovery
        )
        
        # But make it fail (never recovers)
        service.simulate_job_execution(test.id, fail_until_attempt=10)
        
        validation = service.validate_job_retry_behavior(test.id)
        
        # Should fail because we expected recovery but didn't get it
        assert validation["passed"] is False
    
    def test_get_job_retry_test(self, service: ChaosTestingService):
        """Test getting a job retry test."""
        test = service.create_job_retry_test(
            job_type="test",
            failure_point="test",
        )
        
        retrieved = service.get_job_retry_test(test.id)
        assert retrieved is not None
        assert retrieved.job_type == "test"
    
    def test_list_job_retry_tests(self, service: ChaosTestingService):
        """Test listing job retry tests."""
        for i in range(3):
            service.create_job_retry_test(
                job_type=f"job_{i}",
                failure_point=f"point_{i}",
            )
        
        tests = service.list_job_retry_tests()
        assert len(tests) == 3


# ===== Graceful Degradation Testing =====


class TestGracefulDegradation:
    """Tests for graceful degradation testing."""
    
    def test_create_degradation_test(self, service: ChaosTestingService):
        """Test creating a degradation test."""
        scenario = service.create_scenario(
            name="Storage Down",
            description="Storage failure",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        test = service.create_degradation_test(scenario.id)
        
        assert test.id is not None
        assert test.scenario_id == scenario.id
        assert test.expected_behavior.expected_level == DegradationLevel.READ_ONLY
    
    def test_create_degradation_test_scenario_not_found(
        self, service: ChaosTestingService
    ):
        """Test creating degradation test for non-existent scenario."""
        with pytest.raises(ValueError, match="not found"):
            service.create_degradation_test("nonexistent")
    
    def test_execute_degradation_test_storage(self, service: ChaosTestingService):
        """Test executing degradation test for storage failure."""
        scenario = service.create_scenario(
            name="Storage Down",
            description="Storage failure",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        test = service.create_degradation_test(scenario.id)
        result = service.execute_degradation_test(test.id)
        
        assert result.actual_level == DegradationLevel.READ_ONLY
        assert len(result.fallbacks_triggered) > 0
        assert result.passed is True
        assert result.test_duration_ms >= 0
    
    def test_execute_degradation_test_database(self, service: ChaosTestingService):
        """Test executing degradation test for database failure."""
        scenario = service.create_scenario(
            name="Database Down",
            description="Database failure",
            failure_type=FailureType.DATABASE_DOWN,
            target_component=ComponentType.DATABASE,
        )
        
        test = service.create_degradation_test(scenario.id)
        result = service.execute_degradation_test(test.id)
        
        assert result.actual_level == DegradationLevel.CACHED_DATA
        assert "Serve cached data" in result.fallbacks_triggered
    
    def test_execute_degradation_test_memory_pressure(
        self, service: ChaosTestingService
    ):
        """Test executing degradation test for memory pressure."""
        scenario = service.create_scenario(
            name="Memory Pressure",
            description="High memory",
            failure_type=FailureType.MEMORY_PRESSURE,
            target_component=ComponentType.ML_MODEL,
            parameters={"usage_percent": 95},
        )
        
        test = service.create_degradation_test(scenario.id)
        result = service.execute_degradation_test(test.id)
        
        assert result.actual_level == DegradationLevel.REDUCED_FEATURES
    
    def test_execute_degradation_test_not_found(self, service: ChaosTestingService):
        """Test executing non-existent degradation test."""
        with pytest.raises(ValueError, match="not found"):
            service.execute_degradation_test("nonexistent")
    
    def test_get_degradation_test(self, service: ChaosTestingService):
        """Test getting a degradation test."""
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        test = service.create_degradation_test(scenario.id)
        retrieved = service.get_degradation_test(test.id)
        
        assert retrieved is not None
    
    def test_list_degradation_tests(self, service: ChaosTestingService):
        """Test listing degradation tests."""
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        service.create_degradation_test(scenario.id)
        service.create_degradation_test(scenario.id)
        
        tests = service.list_degradation_tests()
        assert len(tests) == 2


# ===== Circuit Breaker Testing =====


class TestCircuitBreaker:
    """Tests for circuit breaker behavior."""
    
    def test_register_circuit_breaker(self, service: ChaosTestingService):
        """Test registering a circuit breaker."""
        breaker = service.register_circuit_breaker(
            component="external_api",
            recovery_threshold=5,
        )
        
        assert breaker.id is not None
        assert breaker.component == "external_api"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.recovery_threshold == 5
    
    def test_record_circuit_breaker_failure(self, service: ChaosTestingService):
        """Test recording failures on circuit breaker."""
        breaker = service.register_circuit_breaker(component="api")
        
        for _ in range(3):
            service.record_circuit_breaker_failure(breaker.id)
        
        updated = service.get_circuit_breaker(breaker.id)
        assert updated.failure_count == 3
        assert updated.state == CircuitState.CLOSED  # Not yet open
    
    def test_circuit_breaker_opens_after_threshold(self, service: ChaosTestingService):
        """Test that circuit breaker opens after failure threshold."""
        breaker = service.register_circuit_breaker(component="api")
        
        # 5 failures should open the circuit
        for _ in range(5):
            service.record_circuit_breaker_failure(breaker.id)
        
        updated = service.get_circuit_breaker(breaker.id)
        assert updated.state == CircuitState.OPEN
    
    def test_record_circuit_breaker_success(self, service: ChaosTestingService):
        """Test recording success on circuit breaker."""
        breaker = service.register_circuit_breaker(component="api")
        
        service.record_circuit_breaker_success(breaker.id)
        
        updated = service.get_circuit_breaker(breaker.id)
        assert updated.success_count == 1
    
    def test_circuit_breaker_half_open(self, service: ChaosTestingService):
        """Test circuit breaker half-open state."""
        breaker = service.register_circuit_breaker(component="api")
        
        # Open the circuit
        for _ in range(5):
            service.record_circuit_breaker_failure(breaker.id)
        
        assert service.get_circuit_breaker(breaker.id).state == CircuitState.OPEN
        
        # Attempt reset to half-open
        service.attempt_circuit_breaker_reset(breaker.id)
        
        assert service.get_circuit_breaker(breaker.id).state == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_closes_from_half_open(self, service: ChaosTestingService):
        """Test circuit breaker closes from half-open after successes."""
        breaker = service.register_circuit_breaker(
            component="api",
            recovery_threshold=3,
        )
        
        # Open the circuit
        for _ in range(5):
            service.record_circuit_breaker_failure(breaker.id)
        
        # Move to half-open
        service.attempt_circuit_breaker_reset(breaker.id)
        
        # Record enough successes to close
        for _ in range(3):
            service.record_circuit_breaker_success(breaker.id)
        
        updated = service.get_circuit_breaker(breaker.id)
        assert updated.state == CircuitState.CLOSED
        assert updated.failure_count == 0
    
    def test_circuit_breaker_reopens_on_failure_in_half_open(
        self, service: ChaosTestingService
    ):
        """Test circuit breaker reopens if failure in half-open."""
        breaker = service.register_circuit_breaker(component="api")
        
        # Open the circuit
        for _ in range(5):
            service.record_circuit_breaker_failure(breaker.id)
        
        # Move to half-open
        service.attempt_circuit_breaker_reset(breaker.id)
        
        # Fail in half-open
        service.record_circuit_breaker_failure(breaker.id)
        
        updated = service.get_circuit_breaker(breaker.id)
        assert updated.state == CircuitState.OPEN
    
    def test_circuit_breaker_failure_not_found(self, service: ChaosTestingService):
        """Test recording failure for non-existent breaker."""
        with pytest.raises(ValueError, match="not found"):
            service.record_circuit_breaker_failure("nonexistent")
    
    def test_circuit_breaker_success_not_found(self, service: ChaosTestingService):
        """Test recording success for non-existent breaker."""
        with pytest.raises(ValueError, match="not found"):
            service.record_circuit_breaker_success("nonexistent")
    
    def test_list_circuit_breakers(self, service: ChaosTestingService):
        """Test listing circuit breakers."""
        service.register_circuit_breaker(component="api1")
        service.register_circuit_breaker(component="api2")
        
        breakers = service.list_circuit_breakers()
        assert len(breakers) == 2
    
    def test_create_circuit_breaker_test(self, service: ChaosTestingService):
        """Test creating a circuit breaker test."""
        breaker = service.register_circuit_breaker(component="test_api")
        
        test = service.create_circuit_breaker_test(
            breaker_id=breaker.id,
            injected_failures=5,
            expected_state_after=CircuitState.OPEN,
        )
        
        assert test.id is not None
        assert test.component == "test_api"
        assert test.injected_failures == 5
    
    def test_execute_circuit_breaker_test(self, service: ChaosTestingService):
        """Test executing a circuit breaker test."""
        breaker = service.register_circuit_breaker(component="test_api")
        
        test = service.create_circuit_breaker_test(
            breaker_id=breaker.id,
            injected_failures=5,
            expected_state_after=CircuitState.OPEN,
        )
        
        result = service.execute_circuit_breaker_test(test.id, breaker.id)
        
        assert result.actual_state_after == CircuitState.OPEN
        assert result.passed is True
        assert len(result.state_transitions) > 0


# ===== Test Run Management =====


class TestTestRunManagement:
    """Tests for chaos test run management."""
    
    def test_create_test_run(self, service: ChaosTestingService):
        """Test creating a test run."""
        run = service.create_test_run(
            name="Full Chaos Test",
            description="Test all failure modes",
        )
        
        assert run.id is not None
        assert run.name == "Full Chaos Test"
        assert run.status == TestStatus.PENDING
    
    def test_create_test_run_with_scenarios(self, service: ChaosTestingService):
        """Test creating a test run with scenarios."""
        s1 = service.create_scenario(
            name="Storage",
            description="Storage down",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        run = service.create_test_run(
            name="Test Run",
            description="Test",
            scenario_ids=[s1.id],
        )
        
        assert len(run.scenarios) == 1
    
    def test_start_test_run(self, service: ChaosTestingService):
        """Test starting a test run."""
        s1 = service.create_scenario(
            name="Storage",
            description="Storage down",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        run = service.create_test_run(
            name="Test Run",
            description="Test",
            scenario_ids=[s1.id],
        )
        
        result = service.start_test_run(run.id)
        
        assert result.status == TestStatus.COMPLETED
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.total_tests > 0
    
    def test_start_test_run_not_found(self, service: ChaosTestingService):
        """Test starting a non-existent test run."""
        with pytest.raises(ValueError, match="not found"):
            service.start_test_run("nonexistent")
    
    def test_get_test_run(self, service: ChaosTestingService):
        """Test getting a test run."""
        run = service.create_test_run(name="Test", description="Test")
        
        retrieved = service.get_test_run(run.id)
        assert retrieved is not None
    
    def test_list_test_runs(self, service: ChaosTestingService):
        """Test listing test runs."""
        for i in range(3):
            service.create_test_run(name=f"Run {i}", description=f"Desc {i}")
        
        runs = service.list_test_runs()
        assert len(runs) == 3


# ===== Recovery Metrics Tests =====


class TestRecoveryMetrics:
    """Tests for recovery metrics tracking."""
    
    def test_record_recovery_metrics(self, service: ChaosTestingService):
        """Test recording recovery metrics."""
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        metrics = service.record_recovery_metrics(
            scenario_id=scenario.id,
            detection_time_ms=100,
            isolation_time_ms=200,
            recovery_time_ms=5000,
            data_loss=False,
            requests_affected=50,
            requests_failed=5,
            requests_degraded=45,
        )
        
        assert metrics.scenario_id == scenario.id
        assert metrics.recovery_time_ms == 5000
        assert metrics.data_loss is False
        assert metrics.requests_affected == 50
    
    def test_record_recovery_metrics_with_data_loss(
        self, service: ChaosTestingService
    ):
        """Test recording recovery metrics with data loss."""
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.DATABASE_DOWN,
            target_component=ComponentType.DATABASE,
        )
        
        metrics = service.record_recovery_metrics(
            scenario_id=scenario.id,
            detection_time_ms=50,
            isolation_time_ms=100,
            recovery_time_ms=10000,
            data_loss=True,
            data_loss_details="Lost 2 pending transactions",
        )
        
        assert metrics.data_loss is True
        assert "2 pending transactions" in metrics.data_loss_details
    
    def test_get_recovery_metrics(self, service: ChaosTestingService):
        """Test getting recovery metrics."""
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        service.record_recovery_metrics(
            scenario_id=scenario.id,
            detection_time_ms=100,
            isolation_time_ms=200,
            recovery_time_ms=5000,
        )
        
        metrics = service.get_recovery_metrics(scenario.id)
        assert metrics is not None
        assert metrics.recovery_time_ms == 5000
    
    def test_list_recovery_metrics(self, service: ChaosTestingService):
        """Test listing recovery metrics."""
        for i in range(3):
            scenario = service.create_scenario(
                name=f"Test {i}",
                description=f"Desc {i}",
                failure_type=FailureType.STORAGE_DOWN,
                target_component=ComponentType.STORAGE,
            )
            service.record_recovery_metrics(
                scenario_id=scenario.id,
                detection_time_ms=100,
                isolation_time_ms=200,
                recovery_time_ms=5000 * (i + 1),
            )
        
        metrics = service.list_recovery_metrics()
        assert len(metrics) == 3


# ===== Summary Tests =====


class TestSummary:
    """Tests for chaos testing summary."""
    
    def test_get_summary_empty(self, service: ChaosTestingService):
        """Test getting summary with no data."""
        summary = service.get_summary()
        
        assert summary.total_runs == 0
        assert summary.total_scenarios == 0
        assert summary.job_retry_pass_rate == 0.0
    
    def test_get_summary_with_data(self, service: ChaosTestingService):
        """Test getting summary with test data."""
        # Create scenario and run
        scenario = service.create_scenario(
            name="Storage",
            description="Storage down",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        run = service.create_test_run(
            name="Test",
            description="Test",
            scenario_ids=[scenario.id],
        )
        service.start_test_run(run.id)
        
        # Create job retry test
        test = service.create_job_retry_test(
            job_type="backup",
            failure_point="disk",
            expected_recovery=True,
        )
        service.simulate_job_execution(test.id, fail_until_attempt=2)
        
        summary = service.get_summary()
        
        assert summary.total_runs == 1
        assert summary.completed_runs == 1
        assert summary.total_scenarios == 1
        assert summary.total_job_retry_tests == 1
        assert "storage" in summary.components_tested
    
    def test_get_summary_recommendations(self, service: ChaosTestingService):
        """Test that summary includes recommendations."""
        # Create a failing job retry test
        test = service.create_job_retry_test(
            job_type="sync",
            failure_point="network",
            expected_recovery=True,
        )
        service.simulate_job_execution(test.id, fail_until_attempt=100)  # Never recovers
        
        summary = service.get_summary()
        
        # Should recommend reviewing job retry config
        assert any("job retry" in r.lower() for r in summary.recommendations)


# ===== Singleton Tests =====


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_service_returns_same_instance(self):
        """Test that get_chaos_testing_service returns same instance."""
        reset_chaos_testing_service()
        
        s1 = get_chaos_testing_service()
        s2 = get_chaos_testing_service()
        
        assert s1 is s2
    
    def test_reset_clears_data(self):
        """Test that reset clears all data."""
        service = get_chaos_testing_service()
        service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        
        reset_chaos_testing_service()
        
        new_service = get_chaos_testing_service()
        assert len(new_service.list_scenarios()) == 0


# ===== Clear Data Tests =====


class TestClearData:
    """Tests for clearing all data."""
    
    def test_clear_all_data(self, service: ChaosTestingService):
        """Test clearing all data."""
        # Create various data
        scenario = service.create_scenario(
            name="Test",
            description="Test",
            failure_type=FailureType.STORAGE_DOWN,
            target_component=ComponentType.STORAGE,
        )
        service.create_job_retry_test(job_type="test", failure_point="test")
        service.register_circuit_breaker(component="test")
        service.create_test_run(name="Test", description="Test")
        
        service.clear_all_data()
        
        assert len(service.list_scenarios()) == 0
        assert len(service.list_job_retry_tests()) == 0
        assert len(service.list_circuit_breakers()) == 0
        assert len(service.list_test_runs()) == 0
